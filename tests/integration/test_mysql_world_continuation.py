"""Fresh public-play continuation evidence on the dedicated MySQL database."""
from contextlib import asynccontextmanager
from dataclasses import replace
import asyncio
import json
import httpx
import pytest
import sqlalchemy as sa

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK
from tests.integration import test_mysql_native_run_admission as admission
from tests.integration.test_mysql_native_run_exit import public_admit, wait_for_named_lock_waiters, wait_for_row_lock_waiter
from tests.integration.test_mysql_native_turn_mechanics import Renderer
from tests.integration.test_mysql_world_continuation_migration import migrate_to, schema_state
from tests.unit.test_run_exit_api import play_to_ending
from tests.unit.test_run_continuation_api import assert_public_arrival

pytestmark=pytest.mark.integration
WORLD_ROWS=(orm.RunWorldPositionRow,orm.RunWorldVisitRow,orm.RunWorldStateRow)


@asynccontextmanager
async def continuation_case(engine,monkeypatch,*,head="20260918_0010"):
    initial=await schema_state(engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008","20260918_0009")
    with monkeypatch.context() as patch:
        patch.setattr(admission,"HEAD",head)
        try:
            async with admission.native_runtime(engine) as case:
                patch.setattr(main,"create_engine",lambda:engine)
                patch.delenv("DEEPSEEK_API_KEY",raising=False)
                services=main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
                    authentication_scheme=case.runtime.principal.authentication_scheme,
                    player_id=case.runtime.principal.player_id,controller_id=case.runtime.resolver.binding.value),))
                renderer=Renderer()
                services.turn_orchestrator.narrative_provider=renderer
                services.content_registry.resolve("undelivered_receipt","undelivered-receipt-1.0.0").turn_orchestrator.narrative_provider=renderer
                services.content_registry.resolve("receipt_archive","receipt-archive-1.0.0").turn_orchestrator.narrative_provider=renderer
                app=main.create_app(services=services)
                app.state.api_services=services
                app.dependency_overrides[get_current_principal]=lambda:case.runtime.principal
                case.app=app
                case.services=services
                try:
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
                        case.client=client
                        yield case
                finally:
                    async with case.factory.begin() as session:
                        case.scope.session_ids.update((await session.scalars(sa.select(orm.RunSessionParticipationRow.session_id).where(
                            orm.RunSessionParticipationRow.run_id.in_(case.scope.run_ids)))).all())
                        if head == "20260918_0010":
                            await session.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id.in_(case.scope.run_ids)))
                        for model in WORLD_ROWS:
                            await session.execute(sa.delete(model).where(model.run_id.in_(case.scope.run_ids)))
        finally:
            await migrate_to(engine,original)
    assert await schema_state(engine)==initial


async def continue_source(case,*,key="s7.2.continue",profile="difficulty.open-expedition"):
    entered,request=await public_admit(case,"s7.2.admit",profile)
    ended,actions=await play_to_ending(case.client,entered["session_id"])
    body=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
    response=await case.client.post(f'/v1/sessions/{entered["session_id"]}/run-continuation',json=body,headers={"Idempotency-Key":key})
    assert response.status_code==200,response.text
    result=response.json()
    case.scope.session_ids.add(result["session_id"])
    return entered,request,ended,actions,body,result


@pytest.mark.parametrize("profile",["difficulty.open-expedition","difficulty.fragile-alliance","difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("choice",["hold","release"])
async def test_s7_2_mysql_public_journey(mysql_engine,monkeypatch,profile,choice):
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,request,ended,actions,body,result=await continue_source(case,profile=profile)
        source,sid=entered["session_id"],result["session_id"]
        assert result["run_context"]==entered["run_context"]
        assert (await case.client.get(f"/v1/sessions/{source}/view")).json()==ended
        recovered=(await case.client.get(f"/v1/sessions/{sid}/run-continuation")).json()
        assert recovered["predecessor"]["session_id"]==source
        title="规程已中断" if ended["ending_status"]=="RESOLVED" else "记录成为现实"
        await assert_public_arrival(case.client,sid,ended,title)
        assert (await case.client.get(f"/v1/sessions/{source}/run-continuation")).json()["arrival"] is None
        for index,action in enumerate((dict(action_type="OBSERVE",description="核对收件台"),
            dict(action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对发运排程"))):
            response=await case.client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id=f"s7.2.turn.{index}",client_request_id=f"s7.2.action.{index}",**action))
            assert response.status_code==200 and response.json()["state_changed"],response.text
            await assert_public_arrival(case.client,sid,ended,title)
        view=(await case.client.get(f"/v1/sessions/{sid}/view")).json()
        response=await case.client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id="s7.2.choice",client_request_id="s7.2.choice",action_type="CHOOSE",
            decision_id=view["narrative_frame"]["decision_id"],choice_id=f"undelivered_receipt.action.{choice}"))
        assert response.status_code==200 and response.json()["state_changed"],response.text
        final=(await case.client.get(f"/v1/sessions/{sid}/view")).json()
        assert final["scenario_status"]=="ENDED" and final["ending_status"]==("RESOLVED" if choice=="hold" else "FAILED")
        response=await case.client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=4,
            expected_session_state_version=final["metadata"]["state_version"]),headers={"Idempotency-Key":"s7.2.exit"})
        assert response.status_code==200 and response.json()["run_state_version"]==5,response.text
        fresh=await case.client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"s7.2.fresh"})
        assert fresh.status_code==200,fresh.text
        case.scope.run_ids.add(fresh.json()["run_context"]["run_id"]);case.scope.session_ids.add(fresh.json()["session_id"])
        before=await schema_state(mysql_engine)
        assert (await case.client.post(f"/v1/sessions/{source}/run-continuation",json=body,headers={"Idempotency-Key":"s7.2.continue"})).json()==result
        for action,expected in actions:
            assert (await case.client.post(f"/v1/sessions/{source}/actions",json=action)).json()==expected
        assert await schema_state(mysql_engine)==before
        await assert_public_arrival(case.client,sid,ended,title)


@pytest.mark.parametrize("same_key",[True,False])
async def test_s7_2_mysql_real_connections_wait_and_serialize(mysql_engine,monkeypatch,same_key):
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_=await public_admit(case,"s7.2.race.admit","difficulty.silent-hunting-ground")
        sid=entered["session_id"]
        ended,_=await play_to_ending(case.client,sid)
        body=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        tasks=[]
        async with mysql_engine.connect() as blocker:
            assert await blocker.scalar(sa.text("SELECT GET_LOCK(:name,30)"),{"name":NATIVE_ADMISSION_LOCK})==1
            try:
                for key in ("s7.2.race","s7.2.race" if same_key else "s7.2.other"):
                    tasks.append(asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":key})))
                assert await wait_for_named_lock_waiters(mysql_engine,2)>=2
                assert not any(task.done() for task in tasks)
            finally:
                assert await blocker.scalar(sa.text("SELECT RELEASE_LOCK(:name)"),{"name":NATIVE_ADMISSION_LOCK})==1
        results=await asyncio.wait_for(asyncio.gather(*tasks),30)
        assert sorted(r.status_code for r in results)==([200,200] if same_key else [200,409]),[r.text for r in results]
        if same_key:assert results[0].json()==results[1].json()


@pytest.mark.parametrize("stage",["session_row","event","session","revision","participation","cas","receipt","worlds","finalization",
    "world_row_1","world_row_2","world_row_3","world_row_4","world_row_5"])
@pytest.mark.parametrize("cancel",[False,True])
async def test_s7_2_mysql_rollback_and_cancellation(mysql_engine,monkeypatch,stage,cancel):
    from deviation_protocol.infrastructure import repositories as r
    from deviation_protocol.application.run_continuation_service import RunContinuationCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_=await public_admit(case,"fault.admit","difficulty.silent-hunting-ground")
        sid=entered["session_id"]
        ended,_=await play_to_ending(case.client,sid)
        before=await schema_state(mysql_engine)
        owner,method=(r,"_flush_native_binding") if stage.startswith("world_row_") else {"session_row":(r.SqlAlchemyGameSessionRepository,"add_initial_session"),
            "event":(r.SqlAlchemyGameSessionRepository,"persist_events"),
            "session":(r.SqlAlchemyGameSessionRepository,"add_initial_snapshot"),
            "revision":(r.SqlAlchemyRunRepository,"append_revision"),"participation":(r.SqlAlchemyRunSessionParticipationRepository,"add"),
            "cas":(r.SqlAlchemyRunRepository,"compare_and_swap_current"),"receipt":(r.SqlAlchemyRunMutationReceiptRepository,"add"),
            "worlds":(r.SqlAlchemyRunWorldContinuationRepository,"add"),"finalization":(r.SqlAlchemyRunProtocolBindingRepository,"get_classified_for_update")}[stage]
        original=getattr(owner,method)
        sentinel=asyncio.CancelledError("continuation cancelled") if cancel else RuntimeError("continuation fault")
        world_rows=0
        async def fail(*args,**kwargs):
            nonlocal world_rows
            result=await original(*args,**kwargs)
            if stage.startswith("world_row_"):
                if type(args[1]).__name__ in ("RunWorldStateRow","RunWorldVisitRow","RunWorldPositionRow"):
                    world_rows+=1
                    if world_rows==int(stage.rsplit("_",1)[1]):raise sentinel
                return result
            if stage!="finalization" or result.canonical_run.state_version.value==4:raise sentinel
            return result
        command=RunContinuationCommand(public_operation_key=RunEntryPublicOperationKey(value="fault.continue"),expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(owner,method,fail)
            with pytest.raises(type(sentinel)) as caught:
                await case.services.run_continuation_service.continue_run(case.runtime.principal,session_id=sid,command=command)
            assert caught.value is sentinel
        assert await schema_state(mysql_engine)==before


@pytest.mark.parametrize("committed",[False,True])
@pytest.mark.parametrize("cancel",[False,True])
async def test_s7_2_mysql_unknown_commit_and_exact_retry(mysql_engine,monkeypatch,committed,cancel):
    from sqlalchemy.ext.asyncio import AsyncTransaction
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_continuation_service import RunContinuationCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_=await public_admit(case,"unknown.admit","difficulty.silent-hunting-ground")
        sid=entered["session_id"]
        ended,_=await play_to_ending(case.client,sid)
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_continuation_service,authority=replace(case.services.run_continuation_service.authority,uow_factory=lambda:unit))
        original=AsyncTransaction.commit
        sentinel=asyncio.CancelledError("lost commit acknowledgement") if cancel else RuntimeError("lost commit acknowledgement")
        attempts=[]
        async def commit(transaction):
            if transaction is unit._transaction:
                attempts.append(transaction)
                if committed:await original(transaction)
                raise sentinel
            return await original(transaction)
        command=RunContinuationCommand(public_operation_key=RunEntryPublicOperationKey(value="unknown.continue"),expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(AsyncTransaction,"commit",commit)
            with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError) as caught:
                await service.continue_run(case.runtime.principal,session_id=sid,command=command)
            if cancel:assert caught.value is sentinel and sentinel.commit_outcome_unknown
        assert len(attempts)==1 and unit._connection.closed
        status=await case.services.run_continuation_service.status(case.runtime.principal,session_id=sid)
        assert (status["successor"] is not None)==committed
        result=await case.services.run_continuation_service.continue_run(case.runtime.principal,session_id=sid,command=command)
        if committed:assert result==status["successor"]
        before=await schema_state(mysql_engine)
        assert await case.services.run_continuation_service.continue_run(case.runtime.principal,session_id=sid,command=command)==result
        assert await schema_state(mysql_engine)==before


async def test_s7_2_mysql_downgrade_current_read_ignores_stale_snapshot(mysql_engine,monkeypatch):
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,*_=await continue_source(case,profile="difficulty.silent-hunting-ground")
        rid=entered["run_context"]["run_id"]
        # Establish historical 009 before holding a read snapshot. Reinsert only
        # this test's exact genuine public-play rows to exercise a stale reader;
        # current production writers require 010, and DDL cannot cross that reader.
        await migrate_to(mysql_engine,"20260918_0009")
        saved={}
        async with mysql_engine.begin() as connection:
            for model in WORLD_ROWS:
                saved[model]=[dict(row) for row in (await connection.execute(sa.select(model.__table__).where(model.run_id==rid))).mappings()]
                await connection.execute(sa.delete(model).where(model.run_id==rid))
        async with mysql_engine.connect() as stale:
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_world_states"))==0
            async with mysql_engine.begin() as connection:
                for model in reversed(WORLD_ROWS):
                    await connection.execute(sa.insert(model),saved[model])
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_world_states"))==0
            before=await schema_state(mysql_engine)
            module=SCRIPT.get_revision("20260918_0009").module
            statements=[]
            def run(sync):
                class Owner:
                    def __getattr__(self,name):return getattr(sync,name)
                    def execute(self,statement,*args,**kwargs):
                        statements.append(str(statement));return sync.execute(statement,*args,**kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:Owner())
                    module.downgrade()
            with pytest.raises(RuntimeError,match="continuation evidence exists"):
                await stale.run_sync(run)
            await stale.rollback()
            assert any("run_world_states" in sql and "FOR UPDATE" in sql for sql in statements)
            assert not any(sql.lstrip().startswith(("ALTER TABLE","DROP TABLE")) for sql in statements)
            assert await schema_state(mysql_engine)==before
        await migrate_to(mysql_engine,"20260918_0010")


async def test_s7_2_mysql_migration_preserves_old_active_and_terminated_families(mysql_engine,monkeypatch):
    async with continuation_case(mysql_engine,monkeypatch) as case:
        old,request=await public_admit(case,"preserve.old","difficulty.silent-hunting-ground")
        sid=old["session_id"]
        ended,_=await play_to_ending(case.client,sid)
        exited=await case.client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"preserve.exit"})
        assert exited.status_code==200,exited.text
        active=await case.client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"preserve.active"})
        assert active.status_code==200,active.text
        case.scope.run_ids.add(active.json()["run_context"]["run_id"]);case.scope.session_ids.add(active.json()["session_id"])
        before=await schema_state(mysql_engine)
        await migrate_to(mysql_engine,"20260917_0008")
        await migrate_to(mysql_engine,"20260918_0010")
        assert await schema_state(mysql_engine)==before
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json()==ended
        assert (await case.client.get(f'/v1/sessions/{active.json()["session_id"]}/run-status')).json()["run_state_version"]==3


@pytest.mark.parametrize("column",["prior_state_version","binding_player_character_id","binding_contract_version","binding_record_revision",
    "binding_state","binding_operation_id","binding_authority_source_ref","bound_at","active_player_character_id"])
async def test_s7_2_mysql_continued_active_null_checks(mysql_engine,monkeypatch,column):
    from sqlalchemy.exc import DBAPIError
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,*_=await continue_source(case,profile="difficulty.silent-hunting-ground")
        rid=entered["run_context"]["run_id"]
        for model in (orm.RunCurrentRow,orm.RunRevisionRow):
            if column not in model.__table__.columns:continue
            clause=next(new for table,name,old,new in SCRIPT.get_revision("20260918_0009").module._CONSTRAINTS if table==model.__tablename__)
            names=[c.name for c in model.__table__.columns]
            projection=",".join("NULL AS "+name if name==column else name for name in names)
            async with mysql_engine.connect() as connection:
                # MySQL CHECK treats UNKNOWN as success; independently assert FALSE.
                assert await connection.scalar(sa.text(f"SELECT ({clause}) FROM (SELECT {projection} FROM {model.__tablename__} WHERE run_id=:rid AND state_version=4) candidate"),{"rid":rid})==0
                await connection.rollback()
                with pytest.raises(DBAPIError) as caught:
                    await connection.execute(sa.update(model).where(model.run_id==rid,model.state_version==4).values(**{column:None}))
                assert caught.value.orig.args[0] in (3819,1048)
                await connection.rollback()


@pytest.mark.parametrize("corruption",["root_digest","visit_missing","position_missing","crossed_root","receipt","source_memory","destination_memory","content_version"])
async def test_s7_2_mysql_corruption_rejects_owned_history_and_current(mysql_engine,monkeypatch,corruption):
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_,_,_,_,result=await continue_source(case,profile="difficulty.silent-hunting-ground")
        source,sid,rid=entered["session_id"],result["session_id"],entered["run_context"]["run_id"]
        async with case.factory.begin() as session:
            if corruption in ("root_digest","crossed_root"):
                row=await session.get(orm.RunWorldStateRow,(rid,"world.undelivered_receipt"))
                if corruption=="root_digest":row.state_sha256=b"\0"*32
                else:row.first_visit_id="foreign.visit"
            elif corruption=="visit_missing":
                await session.execute(sa.delete(orm.RunWorldVisitRow).where(orm.RunWorldVisitRow.run_id==rid,orm.RunWorldVisitRow.visit_ordinal==1))
            elif corruption=="position_missing":
                await session.execute(sa.delete(orm.RunWorldPositionRow).where(orm.RunWorldPositionRow.run_id==rid))
            elif corruption=="receipt":
                row=await session.scalar(sa.select(orm.RunMutationReceiptRow).where(orm.RunMutationReceiptRow.run_id==rid,orm.RunMutationReceiptRow.resulting_state_version==4))
                row.operation_evidence_canonical=b"{}"
            elif corruption=="content_version":
                row=await session.get(orm.GameSessionRow,sid);row.scenario_version="foreign.1"
            else:
                row=await session.get(orm.GameSnapshotRow,source if corruption=="source_memory" else sid)
                data=json.loads(json.dumps(row.state_json));data["player_memory"]["scenario_records"]=[];row.state_json=data
        before=await schema_state(mysql_engine)
        for target in (source,sid):
            for route in ("view","run-continuation","run-status"):
                response=await case.client.get(f"/v1/sessions/{target}/{route}")
                assert response.status_code==409 and response.json()["error"]["error_code"]=="SNAPSHOT_INVALID",response.text
        assert await schema_state(mysql_engine)==before


@pytest.mark.parametrize("competitor", ["exit", "admission", "retirement"])
async def test_s7_2_mysql_continuation_excludes_competing_writes(mysql_engine, monkeypatch, competitor):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    async with continuation_case(mysql_engine, monkeypatch) as case:
        first, request = await public_admit(case,"compete.admit","difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client,sid)
        body=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        staged, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyRunRepository.compare_and_swap_current
        async def pause(repository,run,**kwargs):
            result=await original(repository,run,**kwargs)
            if run.state_version.value==4:
                staged.set();await release.wait()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
            continuing=asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"compete.continue"}))
            await asyncio.wait_for(staged.wait(),15)
            if competitor=="exit":
                operation=case.client.post(f"/v1/sessions/{sid}/run-exit",json=body,headers={"Idempotency-Key":"compete.exit"})
            elif competitor=="admission":
                operation=case.client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"compete.fresh"})
            else:
                operation=case.client.post(f"/v1/player-characters/{case.runtime.character_ids[0].value}/retirement",
                    headers={"Idempotency-Key":"compete.retire"},json={"contract_version":"structured-player-character/v1",
                        "expected_revision":{"value":1},"confirm_retirement":True})
            competing=asyncio.create_task(operation)
            try:
                if competitor=="retirement":await wait_for_row_lock_waiter(mysql_engine)
                else:await wait_for_named_lock_waiters(mysql_engine,1)
                assert not competing.done()
            finally:release.set()
            results=await asyncio.wait_for(asyncio.gather(continuing,competing),30)
        assert [r.status_code for r in results]==[200,409],[r.text for r in results]
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json()==ended
        assert (await case.client.get(f"/v1/sessions/{results[0].json()['session_id']}/run-status")).json()["run_state_version"]==4


@pytest.mark.parametrize("cancel",[False,True])
async def test_s7_2_mysql_postcommit_cleanup_unknown(mysql_engine,monkeypatch,cancel):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_continuation_service import RunContinuationCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    from tests.integration.test_mysql_native_run_migration import observe
    async with continuation_case(mysql_engine,monkeypatch) as case:
        first,_=await public_admit(case,"cleanup.admit","difficulty.silent-hunting-ground")
        sid=first["session_id"];ended,_=await play_to_ending(case.client,sid)
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_continuation_service,authority=replace(case.services.run_continuation_service.authority,uow_factory=lambda:unit))
        sentinel=asyncio.CancelledError("cleanup cancellation") if cancel else RuntimeError("cleanup failure")
        async def fail():raise sentinel
        monkeypatch.setattr(unit,"_cleanup",fail)
        command=RunContinuationCommand(public_operation_key=RunEntryPublicOperationKey(value="cleanup.continue"),expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError):
            await service.continue_run(case.runtime.principal,session_id=sid,command=command)
        assert unit._connection.closed
        await observe(mysql_engine,unit.connection_id)
        status=await case.services.run_continuation_service.status(case.runtime.principal,session_id=sid)
        before=await schema_state(mysql_engine)
        assert await case.services.run_continuation_service.continue_run(case.runtime.principal,session_id=sid,command=command)==status["successor"]
        assert await schema_state(mysql_engine)==before


async def test_s7_2_mysql_final_turn_revalidation(mysql_engine,monkeypatch):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
    async with continuation_case(mysql_engine,monkeypatch) as case:
        first,_=await public_admit(case,"final.admit","difficulty.silent-hunting-ground")
        sid=first["session_id"];staged,release=asyncio.Event(),asyncio.Event();versions=[]
        original=SqlAlchemyUnitOfWork.commit
        async def pause(unit):
            snapshot=await unit.sessions.get_latest_snapshot(sid)
            runtime=snapshot.state.get("scenario_runtime") if snapshot else None
            if runtime and runtime["ending_status"] in ("RESOLVED","FAILED"):
                versions.append(snapshot.state_version);staged.set();await release.wait()
            return await original(unit)
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyUnitOfWork,"commit",pause)
            playing=asyncio.create_task(play_to_ending(case.client,sid))
            await asyncio.wait_for(staged.wait(),20)
            body=dict(expected_run_state_version=3,expected_session_state_version=versions[0])
            continuing=asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"final.continue"}))
            try:
                await wait_for_row_lock_waiter(mysql_engine)
                assert not continuing.done()
            finally:release.set()
            ended,response=await asyncio.wait_for(asyncio.gather(playing,continuing),30)
        # Preparation saw the pre-ending snapshot. Revalidation must reject that
        # detached preparation; explicit retry can now prepare the committed end.
        assert response.status_code==409 and response.json()["error"]["error_code"]=="RUN_CONTINUATION_STALE",response.text
        response=await case.client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"final.continue"})
        assert response.status_code==200,response.text
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json()==ended[0]


async def test_s7_2_mysql_new_table_constraints_and_terminal_nulls(mysql_engine,monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_,_,_,_,result=await continue_source(case,profile="difficulty.silent-hunting-ground")
        rid,sid=entered["run_context"]["run_id"],result["session_id"]
        invalid=(
            (orm.RunWorldStateRow,"state_schema","unknown",3819,"ck_run_world_states_schema"),
            (orm.RunWorldStateRow,"state_canonical",b"",3819,"ck_run_world_states_payload_size"),
            (orm.RunWorldStateRow,"region_version",0,3819,"ck_run_world_states_versions"),
            (orm.RunWorldVisitRow,"visit_ordinal",0,3819,"ck_run_world_visits_ordinal_join"),
            (orm.RunWorldVisitRow,"region_version",0,3819,"ck_run_world_visits_versions"),
            (orm.RunWorldVisitRow,"world_id","world.unknown",1452,"fk_run_world_visits_world"),
            (orm.RunWorldPositionRow,"position_state_version",3,3819,"ck_run_world_positions_versions"),
            (orm.RunWorldPositionRow,"visit_id","visit.unknown",1452,"fk_run_world_positions_visit"),
        )
        before=await schema_state(mysql_engine)
        for model,column,value,code,name in invalid:
            async with mysql_engine.connect() as connection:
                with pytest.raises(DBAPIError) as caught:
                    await connection.execute(sa.update(model).where(model.run_id==rid).values(**{column:value}))
                assert caught.value.orig.args[0]==code and name in str(caught.value.orig),(column,caught.value.orig)
                await connection.rollback()
            print("C07 rejected",model.__tablename__,column,name,code)
        assert await schema_state(mysql_engine)==before
        for index,action in enumerate((dict(action_type="OBSERVE",description="核对收件台"),
                dict(action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对发运排程"))):
            response=await case.client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id=f"null.{index}",client_request_id=f"null.{index}",**action))
            assert response.status_code==200,response.text
        view=(await case.client.get(f"/v1/sessions/{sid}/view")).json()
        response=await case.client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id="null.choice",client_request_id="null.choice",
            action_type="CHOOSE",decision_id=view["narrative_frame"]["decision_id"],choice_id="undelivered_receipt.action.hold"))
        assert response.status_code==200,response.text
        view=(await case.client.get(f"/v1/sessions/{sid}/view")).json()
        response=await case.client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=4,
            expected_session_state_version=view["metadata"]["state_version"]),headers={"Idempotency-Key":"null.exit"})
        assert response.status_code==200,response.text
        before=await schema_state(mysql_engine)
        for model in (orm.RunCurrentRow,orm.RunRevisionRow):
            clause=next(new for table,name,old,new in SCRIPT.get_revision("20260918_0009").module._CONSTRAINTS if table==model.__tablename__)
            for column in ("prior_state_version","binding_player_character_id","binding_contract_version","binding_record_revision",
                    "binding_state","binding_operation_id","binding_authority_source_ref","bound_at","inactivated_at"):
                projection=",".join("NULL AS "+c.name if c.name==column else c.name for c in model.__table__.columns)
                async with mysql_engine.connect() as connection:
                    assert await connection.scalar(sa.text(f"SELECT ({clause}) FROM (SELECT {projection} FROM {model.__tablename__} WHERE run_id=:rid AND state_version=5) candidate"),{"rid":rid})==0
                    await connection.rollback()
                    with pytest.raises(DBAPIError) as caught:
                        await connection.execute(sa.update(model).where(model.run_id==rid,model.state_version==5).values(**{column:None}))
                    assert caught.value.orig.args[0] in (3819,1048),caught.value.orig
                    await connection.rollback()
                print("C07 terminal NULL rejected",model.__tablename__,column)
        assert await schema_state(mysql_engine)==before


async def test_s7_2_mysql_other_resolved_ending_public_play(mysql_engine,monkeypatch):
    from tests.unit.test_run_continuation_api import play_to_record_challenged
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_=await public_admit(case,"challenge.admit","difficulty.open-expedition")
        sid=entered["session_id"];ended=await play_to_record_challenged(case.client,sid)
        response=await case.client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"challenge.continue"})
        assert response.status_code==200,response.text
        async with case.factory() as session:
            source=await session.get(orm.GameSnapshotRow,sid)
            assert source.state_json["scenario_runtime"]["ending_id"]=="death_certificate.ending.record_challenged"
        successor=response.json()["session_id"]
        await assert_public_arrival(case.client,successor,ended,"记录已被质疑")
        response=await case.client.post(f"/v1/sessions/{successor}/actions",json=dict(action_type="OBSERVE",description="核对收件台",
            turn_id="challenge.arrival",client_request_id="challenge.arrival"))
        assert response.status_code==200 and response.json()["state_changed"],response.text
        await assert_public_arrival(case.client,successor,ended,"记录已被质疑")


@pytest.mark.parametrize("migration_first",[False,True])
async def test_s7_2_mysql_migration_and_writer_share_physical_lock(mysql_engine,monkeypatch,migration_first):
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from sqlalchemy.util import await_only
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_=await public_admit(case,"ddl.admit","difficulty.silent-hunting-ground")
        sid=entered["session_id"];ended,_=await play_to_ending(case.client,sid)
        body=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        held,release=asyncio.Event(),asyncio.Event()
        async def write():return await case.client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"ddl.continue"})
        with monkeypatch.context() as patch:
            if migration_first:
                # Start immediately before the current writer's migration. The
                # shared Alembic op proxy also intercepts earlier migrations;
                # pausing 009 would expose an unfinished 010 schema to the writer.
                await migrate_to(mysql_engine,"20260918_0009")
                module=SCRIPT.get_revision("20260918_0010").module
                original_bind=module.op.get_bind
                class Owner:
                    def __init__(self,connection):self.connection=connection
                    def __getattr__(self,name):return getattr(self.connection,name)
                    def execute(self,statement,*args,**kwargs):
                        if "RELEASE_LOCK" in str(statement):
                            held.set();await_only(release.wait())
                        return self.connection.execute(statement,*args,**kwargs)
                patch.setattr(module.op,"get_bind",lambda:Owner(original_bind()))
                first=asyncio.create_task(migrate_to(mysql_engine,"20260918_0010"))
            else:
                original=SqlAlchemyRunRepository.compare_and_swap_current
                async def pause(repository,run,**kwargs):
                    result=await original(repository,run,**kwargs)
                    if run.state_version.value==4:held.set();await release.wait()
                    return result
                patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
                first=asyncio.create_task(write())
            await asyncio.wait_for(held.wait(),20)
            second=asyncio.create_task(write() if migration_first else migrate_to(mysql_engine,"20260917_0008"))
            try:
                await wait_for_named_lock_waiters(mysql_engine,1)
                assert not second.done()
            finally:
                release.set()
                outcomes=await asyncio.wait_for(asyncio.gather(first,second,return_exceptions=True),30)
                await migrate_to(mysql_engine,"20260918_0010")
        if migration_first:
            assert outcomes[0] is None and outcomes[1].status_code==200,outcomes
        else:
            assert outcomes[0].status_code==200,outcomes[0].text
            assert isinstance(outcomes[1],RuntimeError) and "continuation evidence exists" in str(outcomes[1]),outcomes[1]
        await migrate_to(mysql_engine,"20260918_0010")
        assert (await case.client.get(f"/v1/sessions/{sid}/run-continuation")).json()["successor"] is not None


async def test_s7_2_mysql_foreign_owner_controller_and_missing_session(mysql_engine,monkeypatch):
    from tests.unit.test_run_continuation_api import assert_foreign_continuation_is_opaque
    async with continuation_case(mysql_engine,monkeypatch) as case:
        entered,_,_,_,_,result=await continue_source(case,profile="difficulty.silent-hunting-ground")
        before=await schema_state(mysql_engine)
        await assert_foreign_continuation_is_opaque(case.client,case.app,case.runtime.principal,entered["session_id"],result["session_id"])
        assert await schema_state(mysql_engine)==before
