"""Real 010 persistence, public actions, and independent database observations."""
import asyncio
from dataclasses import replace

import pytest
import sqlalchemy as sa

from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK
from tests.integration.test_mysql_world_continuation import continuation_case, continue_source
from tests.integration.test_mysql_native_run_exit import wait_for_named_lock_waiters
from tests.integration.test_mysql_world_continuation_migration import schema_state, migrate_to
from tests.unit.test_run_revisit_api import action, view

pytestmark = pytest.mark.integration


async def held_source(case, profile="difficulty.silent-hunting-ground"):
    entered, request, ended, _, old_body, continued = await continue_source(case, profile=profile)
    sid = continued["session_id"]
    await action(case.client, sid, "regional.observe", action_type="OBSERVE", description="核对收件台")
    await action(case.client, sid, "regional.talk", action_type="TALK", target_ids=["scenario-npc-1"], dialogue="核对排程")
    decision = await view(case.client, sid)
    await action(case.client, sid, "regional.hold", action_type="CHOOSE",
        decision_id=decision["narrative_frame"]["decision_id"], choice_id="undelivered_receipt.action.hold")
    held = await view(case.client, sid)
    assert held["ending_id"] == "undelivered_receipt.ending.receipt_held"
    return entered, request, ended, old_body, continued, held


def revisit_body(held):
    return dict(expected_run_state_version=4, expected_session_state_version=held["metadata"]["state_version"])


async def revisit(case, held, key="mysql.revisit"):
    return await case.client.post(f'/v1/sessions/{held["metadata"]["session_id"]}/run-revisit',
        json=revisit_body(held), headers={"Idempotency-Key": key})


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r01_r02_actual_mysql_journey(mysql_engine, monkeypatch, profile, choice):
    async with continuation_case(mysql_engine, monkeypatch, head="20260918_0010") as case:
        entered, request, first_end, old_body, continued, held = await held_source(case, profile)
        before = await schema_state(mysql_engine)
        offer = await case.client.get(f'/v1/sessions/{continued["session_id"]}/run-journey')
        assert offer.status_code == 200 and offer.json()["next_transition"]["kind"] == "regional_revisit", offer.text
        assert await schema_state(mysql_engine) == before
        response = await revisit(case, held)
        assert response.status_code == 200, response.text
        result = response.json()
        sid = result["session_id"]
        case.scope.session_ids.add(sid)
        async with mysql_engine.connect() as observer:
            carried = await observer.scalar(sa.select(orm.GameSnapshotRow.state_json).where(orm.GameSnapshotRow.session_id == sid))
            source = await observer.scalar(sa.select(orm.GameSnapshotRow.state_json).where(orm.GameSnapshotRow.session_id == continued["session_id"]))
            assert carried["player"] == source["player"]
            for model, count in ((orm.RunWorldStateRow, 2), (orm.RunWorldVisitRow, 3), (orm.RunWorldVisitEntryRow, 1)):
                assert await observer.scalar(sa.select(sa.func.count()).select_from(model).where(model.run_id == result["run_id"])) == count
        await action(case.client, sid, "archive.observe", action_type="OBSERVE", description="查看待核记录")
        decision = await view(case.client, sid)
        assert decision["metadata"]["state_version"] == 1 and not decision["public_clocks"]
        history_before = await schema_state(mysql_engine)
        for path in (sid, continued["session_id"], entered["session_id"], continued["session_id"], sid):
            journey = await case.client.get(f"/v1/sessions/{path}/run-journey")
            assert journey.status_code == 200 and journey.json()["current"]["session_id"] == sid, journey.text
            await view(case.client, path)
        assert await schema_state(mysql_engine) == history_before
        assert await view(case.client, entered["session_id"]) == first_end
        assert await view(case.client, continued["session_id"]) == held
        with pytest.raises(RuntimeError, match="regional"):
            await migrate_to(mysql_engine, "20260918_0009")
        assert await schema_state(mysql_engine) == history_before
        await action(case.client, sid, "archive.choice", action_type="CHOOSE",
            decision_id=decision["narrative_frame"]["decision_id"], choice_id="receipt_archive.action." + choice)
        ended = await view(case.client, sid)
        assert ended["ending_status"] == ("RESOLVED" if choice == "seal" else "FAILED")
        exit_response = await case.client.post(f"/v1/sessions/{sid}/run-exit", json=dict(expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"]), headers={"Idempotency-Key": "archive.exit"})
        assert exit_response.status_code == 200 and exit_response.json()["run_state_version"] == 6, exit_response.text
        fresh = await case.client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": "archive.fresh"})
        assert fresh.status_code == 200, fresh.text
        case.scope.run_ids.add(fresh.json()["run_context"]["run_id"])
        case.scope.session_ids.add(fresh.json()["session_id"])
        await action(case.client, fresh.json()["session_id"], "fresh.observe", action_type="OBSERVE", description="查看环境")
        before_replay = await schema_state(mysql_engine)
        assert (await revisit(case, held)).json() == result
        replay = await case.client.post(f'/v1/sessions/{entered["session_id"]}/run-continuation',
            json=old_body, headers={"Idempotency-Key": "s7.2.continue"})
        assert replay.status_code == 200 and replay.json() == continued, replay.text
        assert await schema_state(mysql_engine) == before_replay


@pytest.mark.parametrize("same_key", [True, False])
async def test_r06_mysql_observed_connection_waiters(mysql_engine, monkeypatch, same_key):
    async with continuation_case(mysql_engine, monkeypatch, head="20260918_0010") as case:
        *_, held = await held_source(case)
        async with mysql_engine.connect() as blocker:
            assert await blocker.scalar(sa.text("SELECT GET_LOCK(:name,30)"), {"name": NATIVE_ADMISSION_LOCK}) == 1
            tasks = []
            try:
                tasks = [asyncio.create_task(revisit(case, held, key)) for key in ("race", "race" if same_key else "other")]
                assert await wait_for_named_lock_waiters(mysql_engine, 2) >= 2
                assert not any(t.done() for t in tasks)
            finally:
                assert await blocker.scalar(sa.text("SELECT RELEASE_LOCK(:name)"), {"name": NATIVE_ADMISSION_LOCK}) == 1
        results = await asyncio.wait_for(asyncio.gather(*tasks), 60)
        assert sorted(r.status_code for r in results) == ([200, 200] if same_key else [200, 409]), [r.text for r in results]
        if same_key:
            assert results[0].json() == results[1].json()


async def test_r05_r08_mysql_corruption_checks_and_partial_downgrade_refusal(mysql_engine, monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    module = SCRIPT.get_revision("20260918_0010").module
    async with continuation_case(mysql_engine, monkeypatch, head="20260918_0010") as case:
        entered, _, _, _, continued, held = await held_source(case)
        response = await revisit(case, held)
        assert response.status_code == 200, response.text
        result = response.json()
        rid, sid = result["run_id"], result["session_id"]
        case.scope.session_ids.add(sid)
        before = await schema_state(mysql_engine)
        required = ("prior_state_version", "binding_player_character_id", "binding_contract_version",
            "binding_record_revision", "binding_state", "binding_operation_id", "binding_authority_source_ref",
            "bound_at", "active_player_character_id")
        for model in (orm.RunCurrentRow, orm.RunRevisionRow):
            clause = next(new for table, _, _, new in module._CONSTRAINTS if table == model.__tablename__)
            for field in required:
                if field not in model.__table__.columns:
                    continue
                projection = ",".join("NULL AS " + c.name if c.name == field else c.name for c in model.__table__.columns)
                async with mysql_engine.connect() as probe:
                    assert await probe.scalar(sa.text(f"SELECT ({clause}) FROM (SELECT {projection} FROM {model.__tablename__} WHERE run_id=:rid AND state_version=5) candidate"), {"rid": rid}) == 0
                    await probe.rollback()
                    with pytest.raises(DBAPIError) as caught:
                        await probe.execute(sa.update(model).where(model.run_id == rid, model.state_version == 5).values(**{field: None}))
                    assert caught.value.orig.args[0] in (3819, 1048)
                    await probe.rollback()
        for model, field, value, code in (
            (orm.RunWorldVisitEntryRow, "joined_state_version", 4, 3819),
            (orm.RunWorldVisitEntryRow, "entry_schema", "run-world-state/v1", 3819),
            (orm.RunWorldVisitEntryRow, "entry_canonical", b"", 3819),
            (orm.RunWorldVisitEntryRow, "entry_canonical", b"x" * 1048577, 3819),
            (orm.RunWorldVisitEntryRow, "visit_id", "absent.visit", 1452),
            (orm.RunWorldVisitRow, "visit_ordinal", 4, 3819),
            (orm.RunWorldVisitRow, "materialized_state_version", 4, 3819),
            (orm.RunWorldPositionRow, "position_state_version", 6, 3819),
        ):
            async with mysql_engine.connect() as probe:
                with pytest.raises(DBAPIError) as caught:
                    await probe.execute(sa.update(model).where(model.run_id == rid, model.session_id == sid).values(**{field: value}))
                assert caught.value.orig.args[0] == code
                await probe.rollback()
        assert await schema_state(mysql_engine) == before
        async with case.factory() as session:
            row = (await session.execute(sa.select(orm.RunWorldVisitEntryRow.__table__).where(orm.RunWorldVisitEntryRow.run_id == rid))).mappings().one()
            original = dict(row)
        try:
            for patch in (dict(entry_sha256=b"x" * 32), dict(entry_canonical=b"{}")):
                async with case.factory.begin() as session:
                    await session.execute(sa.update(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id == rid).values(**patch))
                corrupt = await schema_state(mysql_engine)
                for path in (entered["session_id"], continued["session_id"], sid):
                    for endpoint in ("view", "run-journey"):
                        reply = await case.client.get(f"/v1/sessions/{path}/{endpoint}")
                        assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
                assert await schema_state(mysql_engine) == corrupt
                async with case.factory.begin() as session:
                    await session.execute(sa.update(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id == rid).values(**original))
            async with case.factory.begin() as session:
                await session.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id == rid))
            partial = await schema_state(mysql_engine)
            with pytest.raises(RuntimeError, match="regional"):
                await migrate_to(mysql_engine, "20260918_0009")
            assert await schema_state(mysql_engine) == partial
        finally:
            async with case.factory.begin() as session:
                await session.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id == rid))
                await session.execute(sa.insert(orm.RunWorldVisitEntryRow).values(**original))
        assert await schema_state(mysql_engine) == before


async def test_r08_old_terminal_five_permits_safe_downgrade(mysql_engine, monkeypatch):
    async with continuation_case(mysql_engine, monkeypatch, head="20260918_0010") as case:
        *_, held = await held_source(case)
        sid = held["metadata"]["session_id"]
        exited = await case.client.post(f"/v1/sessions/{sid}/run-exit", json=revisit_body(held), headers={"Idempotency-Key": "old.exit"})
        assert exited.status_code == 200 and exited.json()["run_state_version"] == 5, exited.text
        before = await schema_state(mysql_engine)
        await migrate_to(mysql_engine, "20260918_0009")
        await migrate_to(mysql_engine, "20260918_0010")
        assert await schema_state(mysql_engine) == before
        assert await view(case.client, sid) == held


async def test_r05_mysql_initial_event_memory_and_double_corruption_precedence(mysql_engine, monkeypatch):
    from copy import deepcopy
    async with continuation_case(mysql_engine, monkeypatch) as case:
        entered, _, _, _, continued, held = await held_source(case)
        result = (await revisit(case, held)).json()
        sid, rid = result["session_id"], result["run_id"]
        async with case.factory() as session:
            event = dict((await session.execute(sa.select(orm.DomainEventRow.__table__).where(orm.DomainEventRow.session_id==sid, orm.DomainEventRow.sequence_no==1))).mappings().one())
            snapshot_row = dict((await session.execute(sa.select(orm.GameSnapshotRow.__table__).where(orm.GameSnapshotRow.session_id==sid))).mappings().one())
            snapshot = deepcopy(snapshot_row["state_json"])
            entry = dict((await session.execute(sa.select(orm.RunWorldVisitEntryRow.__table__).where(orm.RunWorldVisitEntryRow.run_id==rid))).mappings().one())
        before = await schema_state(mysql_engine)
        for fault in ("missing_event", "event", "memory", "double"):
            try:
                async with case.factory.begin() as session:
                    if fault=="missing_event":
                        await session.execute(sa.delete(orm.DomainEventRow).where(orm.DomainEventRow.event_id==event["event_id"]))
                    elif fault=="event":
                        await session.execute(sa.update(orm.DomainEventRow).where(orm.DomainEventRow.event_id==event["event_id"]).values(payload_json={"scenario_id":"foreign"}))
                    else:
                        bad=deepcopy(snapshot);bad["player_memory"]={}
                        await session.execute(sa.update(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id==sid).values(state_json=bad))
                    if fault=="double":
                        await session.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id==rid))
                corrupt=await schema_state(mysql_engine)
                assert (await case.client.get("/v1/sessions/foreign.session/run-journey")).status_code==404
                for path in (entered["session_id"],continued["session_id"],sid):
                    for endpoint in ("view","run-journey"):
                        reply=await case.client.get(f"/v1/sessions/{path}/{endpoint}")
                        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",reply.text
                reply=await case.client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id="corrupt",client_request_id="corrupt",action_type="OBSERVE",description="查看待核记录"))
                assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",reply.text
                assert await schema_state(mysql_engine)==corrupt
            finally:
                async with case.factory.begin() as session:
                    await session.execute(sa.delete(orm.DomainEventRow).where(orm.DomainEventRow.event_id==event["event_id"]))
                    await session.execute(sa.insert(orm.DomainEventRow).values(**event))
                    await session.execute(sa.update(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id==sid).values(**snapshot_row))
                    await session.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id==rid))
                    await session.execute(sa.insert(orm.RunWorldVisitEntryRow).values(**entry))
            assert await schema_state(mysql_engine)==before


@pytest.mark.parametrize("stage",["session_row","event","session","revision","participation","cas","receipt","worlds","finalization",
    "world_row_1","world_row_2"])
@pytest.mark.parametrize("cancel",[False,True])
async def test_r07_mysql_rollback_and_cancellation(mysql_engine,monkeypatch,stage,cancel):
    from deviation_protocol.infrastructure import repositories as r
    from deviation_protocol.application.run_revisit_service import RunRevisitCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    async with continuation_case(mysql_engine,monkeypatch,head="20260918_0010") as case:
        *_,ended=await held_source(case)
        sid=ended["metadata"]["session_id"]
        before=await schema_state(mysql_engine)
        owner,method=(r,"_flush_native_binding") if stage.startswith("world_row_") else {"session_row":(r.SqlAlchemyGameSessionRepository,"add_initial_session"),
            "event":(r.SqlAlchemyGameSessionRepository,"persist_events"),
            "session":(r.SqlAlchemyGameSessionRepository,"add_initial_snapshot"),
            "revision":(r.SqlAlchemyRunRepository,"append_revision"),"participation":(r.SqlAlchemyRunSessionParticipationRepository,"add"),
            "cas":(r.SqlAlchemyRunRepository,"compare_and_swap_current"),"receipt":(r.SqlAlchemyRunMutationReceiptRepository,"add"),
            "worlds":(r.SqlAlchemyRunWorldRevisitRepository,"add"),"finalization":(r.SqlAlchemyRunProtocolBindingRepository,"get_classified_for_update")}[stage]
        original=getattr(owner,method)
        sentinel=asyncio.CancelledError("continuation cancelled") if cancel else RuntimeError("continuation fault")
        world_rows=0
        async def fail(*args,**kwargs):
            nonlocal world_rows
            result=await original(*args,**kwargs)
            if stage.startswith("world_row_"):
                if type(args[1]).__name__ in ("RunWorldVisitRow","RunWorldVisitEntryRow"):
                    world_rows+=1
                    if world_rows==int(stage.rsplit("_",1)[1]):raise sentinel
                return result
            if stage!="finalization" or result.canonical_run.state_version.value==5:raise sentinel
            return result
        command=RunRevisitCommand(public_operation_key=RunEntryPublicOperationKey(value="fault.continue"),expected_run_state_version=4,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(owner,method,fail)
            with pytest.raises(type(sentinel)) as caught:
                await case.services.run_revisit_service.revisit(case.runtime.principal,session_id=sid,command=command)
            assert caught.value is sentinel
        assert await schema_state(mysql_engine)==before


@pytest.mark.parametrize("committed",[False,True])
@pytest.mark.parametrize("cancel",[False,True])
async def test_r07_mysql_unknown_commit_and_exact_retry(mysql_engine,monkeypatch,committed,cancel):
    from sqlalchemy.ext.asyncio import AsyncTransaction
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_revisit_service import RunRevisitCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    async with continuation_case(mysql_engine,monkeypatch,head="20260918_0010") as case:
        *_,ended=await held_source(case)
        sid=ended["metadata"]["session_id"]
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_revisit_service,continuation=replace(case.services.run_revisit_service.continuation,authority=replace(case.services.run_revisit_service.authority,uow_factory=lambda:unit)))
        original=AsyncTransaction.commit
        sentinel=asyncio.CancelledError("lost commit acknowledgement") if cancel else RuntimeError("lost commit acknowledgement")
        attempts=[]
        async def commit(transaction):
            if transaction is unit._transaction:
                attempts.append(transaction)
                if committed:await original(transaction)
                raise sentinel
            return await original(transaction)
        command=RunRevisitCommand(public_operation_key=RunEntryPublicOperationKey(value="unknown.continue"),expected_run_state_version=4,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(AsyncTransaction,"commit",commit)
            with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError) as caught:
                await service.revisit(case.runtime.principal,session_id=sid,command=command)
            if cancel:assert caught.value is sentinel and sentinel.commit_outcome_unknown
        assert len(attempts)==1 and unit._connection.closed
        status=await case.services.run_revisit_service.journey(case.runtime.principal,session_id=sid)
        assert (status["current"]["session_id"] != sid)==committed
        result=await case.services.run_revisit_service.revisit(case.runtime.principal,session_id=sid,command=command)
        if committed:assert result["session_id"]==status["current"]["session_id"]
        before=await schema_state(mysql_engine)
        assert await case.services.run_revisit_service.revisit(case.runtime.principal,session_id=sid,command=command)==result
        assert await schema_state(mysql_engine)==before



@pytest.mark.parametrize("competitor", ["exit", "admission", "retirement", "changed_same_key"])
async def test_r06_mysql_revisit_excludes_competing_writes(mysql_engine, monkeypatch, competitor):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from tests.integration.test_mysql_native_run_exit import wait_for_row_lock_waiter
    async with continuation_case(mysql_engine, monkeypatch, head="20260918_0010") as case:
        first, request, _, _, continued, ended = await held_source(case)
        sid = continued["session_id"]
        body=dict(expected_run_state_version=4,expected_session_state_version=ended["metadata"]["state_version"])
        staged, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyRunRepository.compare_and_swap_current
        async def pause(repository,run,**kwargs):
            result=await original(repository,run,**kwargs)
            if run.state_version.value==5:
                staged.set();await release.wait()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
            continuing=asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-revisit",json=body,headers={"Idempotency-Key":"compete.continue"}))
            await asyncio.wait_for(staged.wait(),15)
            if competitor=="exit":
                operation=case.client.post(f"/v1/sessions/{sid}/run-exit",json=body,headers={"Idempotency-Key":"compete.exit"})
            elif competitor=="changed_same_key":
                operation=case.client.post(f"/v1/sessions/{sid}/run-revisit",json={**body,"expected_session_state_version":body["expected_session_state_version"]+1},headers={"Idempotency-Key":"compete.continue"})
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
            finally:
                release.set()
                results=await asyncio.wait_for(asyncio.gather(continuing,competing),30)
        assert [r.status_code for r in results]==[200,409],[r.text for r in results]
        if competitor=="changed_same_key":assert results[1].json()["error"]["error_code"]=="IDEMPOTENCY_CONFLICT"
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json()==ended
        assert (await case.client.get(f"/v1/sessions/{results[0].json()['session_id']}/run-status")).json()["run_state_version"]==5


@pytest.mark.parametrize("cancel",[False,True])
async def test_r07_mysql_regional_postcommit_cleanup_unknown(mysql_engine,monkeypatch,cancel):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_revisit_service import RunRevisitCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    from tests.integration.test_mysql_native_run_migration import observe
    async with continuation_case(mysql_engine,monkeypatch) as case:
        *_,ended=await held_source(case)
        sid=ended["metadata"]["session_id"]
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_revisit_service,continuation=replace(case.services.run_revisit_service.continuation,authority=replace(case.services.run_revisit_service.authority,uow_factory=lambda:unit)))
        sentinel=asyncio.CancelledError("cleanup cancellation") if cancel else RuntimeError("cleanup failure")
        async def fail():raise sentinel
        monkeypatch.setattr(unit,"_cleanup",fail)
        command=RunRevisitCommand(public_operation_key=RunEntryPublicOperationKey(value="cleanup.continue"),expected_run_state_version=4,
            expected_session_state_version=ended["metadata"]["state_version"])
        with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError):
            await service.revisit(case.runtime.principal,session_id=sid,command=command)
        assert unit._connection.closed
        await observe(mysql_engine,unit.connection_id)
        status=await case.services.run_revisit_service.journey(case.runtime.principal,session_id=sid)
        before=await schema_state(mysql_engine)
        assert (await case.services.run_revisit_service.revisit(case.runtime.principal,session_id=sid,command=command))["session_id"]==status["current"]["session_id"]
        assert await schema_state(mysql_engine)==before


@pytest.mark.parametrize("migration_first",[False,True])
async def test_r06_mysql_010_migration_and_revisit_share_physical_lock(mysql_engine,monkeypatch,migration_first):
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from sqlalchemy.util import await_only
    async with continuation_case(mysql_engine,monkeypatch) as case:
        *_,ended=await held_source(case)
        sid=ended["metadata"]["session_id"]
        body=dict(expected_run_state_version=4,expected_session_state_version=ended["metadata"]["state_version"])
        held,release=asyncio.Event(),asyncio.Event()
        async def write():return await case.client.post(f"/v1/sessions/{sid}/run-revisit",json=body,headers={"Idempotency-Key":"ddl.continue"})
        with monkeypatch.context() as patch:
            if migration_first:
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
                    if run.state_version.value==5:held.set();await release.wait()
                    return result
                patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
                first=asyncio.create_task(write())
            await asyncio.wait_for(held.wait(),20)
            second=asyncio.create_task(write() if migration_first else migrate_to(mysql_engine,"20260918_0009"))
            try:
                await wait_for_named_lock_waiters(mysql_engine,1)
                assert not second.done()
            finally:release.set()
            outcomes=await asyncio.wait_for(asyncio.gather(first,second,return_exceptions=True),30)
        if migration_first:
            assert outcomes[0] is None and outcomes[1].status_code==200,outcomes
        else:
            assert outcomes[0].status_code==200,outcomes[0].text
            assert isinstance(outcomes[1],RuntimeError) and "regional" in str(outcomes[1]),outcomes[1]
        assert (await case.client.get(f"/v1/sessions/{sid}/run-journey")).json()["current"]["session_id"] != sid



async def test_r07_actual_zero_row_position_cas_rolls_back(mysql_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.dml import Update
    async with continuation_case(mysql_engine, monkeypatch) as case:
        *_, held = await held_source(case)
        before = await schema_state(mysql_engine)
        original = AsyncSession.execute
        observed = []
        async def execute(session, statement, *args, **kwargs):
            if isinstance(statement, Update) and statement.table.name == "run_world_positions":
                statement = statement.where(sa.false())
                result = await original(session, statement, *args, **kwargs)
                observed.append(result.rowcount)
                return result
            return await original(session, statement, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(AsyncSession, "execute", execute)
            reply = await revisit(case, held)
        assert observed == [0]
        assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "RUN_REVISIT_CONFLICT", reply.text
        assert await schema_state(mysql_engine) == before
        assert (await revisit(case, held)).status_code == 200


async def test_r08_terminal_six_nullable_operands_are_false_not_unknown(mysql_engine, monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    module = SCRIPT.get_revision("20260918_0010").module
    async with continuation_case(mysql_engine, monkeypatch) as case:
        *_, held = await held_source(case)
        result = (await revisit(case, held)).json()
        sid, rid = result["session_id"], result["run_id"]
        await action(case.client, sid, "terminal.observe", action_type="OBSERVE", description="查看待核记录")
        decision = await view(case.client, sid)
        await action(case.client, sid, "terminal.seal", action_type="CHOOSE", decision_id=decision["narrative_frame"]["decision_id"], choice_id="receipt_archive.action.seal")
        ended = await view(case.client, sid)
        response = await case.client.post(f"/v1/sessions/{sid}/run-exit", json=dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"]), headers={"Idempotency-Key":"terminal.exit"})
        assert response.status_code == 200, response.text
        before = await schema_state(mysql_engine)
        for model in (orm.RunCurrentRow, orm.RunRevisionRow):
            clause = next(new for table, _, _, new in module._CONSTRAINTS if table == model.__tablename__)
            for field in ("prior_state_version", "binding_player_character_id", "binding_contract_version", "binding_record_revision", "binding_state", "binding_operation_id", "binding_authority_source_ref", "bound_at", "inactivated_at"):
                projection = ",".join("NULL AS " + c.name if c.name == field else c.name for c in model.__table__.columns)
                async with mysql_engine.connect() as c:
                    assert await c.scalar(sa.text(f"SELECT ({clause}) FROM (SELECT {projection} FROM {model.__tablename__} WHERE run_id=:rid AND state_version=6) candidate"), {"rid":rid}) == 0
                    await c.rollback()
                    with pytest.raises(DBAPIError) as caught:
                        await c.execute(sa.update(model).where(model.run_id==rid, model.state_version==6).values(**{field:None}))
                    assert caught.value.orig.args[0] in (3819,1048)
                    await c.rollback()
        assert await schema_state(mysql_engine) == before


async def test_r08_regional_downgrade_probes_current_rows_not_old_snapshot(mysql_engine, monkeypatch):
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    module = SCRIPT.get_revision("20260918_0010").module
    async with continuation_case(mysql_engine, monkeypatch) as case:
        *_, held = await held_source(case)
        async with mysql_engine.connect() as stale:
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_world_visit_entries")) == 0
            assert (await revisit(case, held)).status_code == 200
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_world_visit_entries")) == 0
            before = await schema_state(mysql_engine)
            statements = []
            def run(sync):
                class Owner:
                    def __getattr__(self, name): return getattr(sync, name)
                    def execute(self, statement, *args, **kwargs):
                        statements.append(str(statement))
                        return sync.execute(statement, *args, **kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(module.op, "get_bind", lambda: Owner())
                    module.downgrade()
            with pytest.raises(RuntimeError, match="regional"):
                await stale.run_sync(run)
            await stale.rollback()
            assert any("FOR UPDATE" in sql for sql in statements)
            assert not any(sql.lstrip().startswith(("ALTER TABLE", "DROP TABLE")) for sql in statements)
            assert await schema_state(mysql_engine) == before


async def test_r06_inflight_final_hold_is_unavailable_until_actual_commit(mysql_engine, monkeypatch):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
    from tests.integration.test_mysql_native_run_exit import wait_for_row_lock_waiter
    async with continuation_case(mysql_engine, monkeypatch) as case:
        *_, continued = await continue_source(case, profile="difficulty.silent-hunting-ground")
        sid = continued["session_id"]
        await action(case.client, sid, "final.observe", action_type="OBSERVE", description="核对收件台")
        await action(case.client, sid, "final.talk", action_type="TALK", target_ids=["scenario-npc-1"], dialogue="核对排程")
        decision = await view(case.client, sid)
        staged, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyUnitOfWork.commit
        async def pause(unit):
            snapshot = await unit.sessions.get_latest_snapshot(sid)
            if snapshot and snapshot.state["scenario_runtime"]["ending_id"] == "undelivered_receipt.ending.receipt_held":
                staged.set()
                await release.wait()
            return await original(unit)
        async def observe_locked_source():
            async with mysql_engine.connect() as observer:
                return await observer.scalar(sa.select(orm.GameSessionRow.state_version).where(orm.GameSessionRow.session_id==sid).with_for_update())
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyUnitOfWork, "commit", pause)
            playing = asyncio.create_task(action(case.client, sid, "final.hold", action_type="CHOOSE", decision_id=decision["narrative_frame"]["decision_id"], choice_id="undelivered_receipt.action.hold"))
            await asyncio.wait_for(staged.wait(), 20)
            observer = asyncio.create_task(observe_locked_source())
            try:
                await wait_for_row_lock_waiter(mysql_engine)
                assert not observer.done() and not playing.done()
                reply = await case.client.post(f"/v1/sessions/{sid}/run-revisit", json=dict(expected_run_state_version=4, expected_session_state_version=decision["metadata"]["state_version"]+1), headers={"Idempotency-Key":"final.revisit"})
                assert reply.status_code==409 and reply.json()["error"]["error_code"]=="RUN_REVISIT_NOT_AVAILABLE", reply.text
            finally:
                release.set()
                await asyncio.wait_for(asyncio.gather(playing,observer),30)
        held = await view(case.client, sid)
        assert held["ending_id"]=="undelivered_receipt.ending.receipt_held"
        assert (await revisit(case,held,"final.revisit")).status_code==200
