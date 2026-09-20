"""Completion through production API/UoW and real dedicated MySQL connections."""
import asyncio

import pytest
import sqlalchemy as sa

from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK
from tests.integration.test_mysql_world_continuation import continuation_case
from tests.integration.test_mysql_world_revisit import held_source, revisit
from tests.integration.test_mysql_native_run_exit import wait_for_named_lock_waiters
from tests.integration.test_mysql_world_continuation_migration import schema_state
from tests.unit.test_run_revisit_api import action, view
from deviation_protocol.infrastructure import orm_models as orm

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("completed", [False, True])
async def test_r1_mysql_ended_live_job_readers_replay_and_current_locking(mysql_engine, monkeypatch, completed):
    from deviation_protocol.application.narrative_jobs import LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION
    from deviation_protocol.domain.run import RunId
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunProtocolBindingRepository
    from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
    async with continuation_case(mysql_engine, monkeypatch, head="20260920_0011") as case:
        history, regional, ended = await sealed_source(case, "difficulty.silent-hunting-ground")
        paths = (history[0]["session_id"], history[4]["session_id"], regional["session_id"])
        if completed: assert (await complete(case, ended)).status_code == 200
        clean = await schema_state(mysql_engine)
        readers = [(sid, route) for sid in paths for route in ("view", "run-journey", "run-status", "run-completion", "run-continuation")]
        for sid, route in readers:
            reply = await case.client.get(f"/v1/sessions/{sid}/{route}")
            if route == "run-continuation":
                assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "RUN_CONTINUATION_NOT_AVAILABLE", reply.text
            else: assert reply.status_code == 200, reply.text
        assert await schema_state(mysql_engine) == clean
        for source in paths:
            async with case.factory() as session:
                row = (await session.execute(sa.select(orm.NarrativeJobRow.__table__).where(
                    orm.NarrativeJobRow.session_id == source,
                    orm.NarrativeJobRow.prompt_schema_version != LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION))).mappings().first()
                saved = dict(row)
            values = dict(status="PREPARED", attempt_count=0, lease_token=None, lease_owner=None,
                lease_expires_at=None, validated_proposal_json=None, validated_proposal_digest=None,
                outcome_rule_id=None, accepted_narrative_text=None, error_code=None)
            try:
                # Start a consistent snapshot before another connection commits
                # the corruption; the locking family read must see the new job.
                async with case.factory() as stale:
                    stale.info["session_content_registry"] = case.services.content_registry
                    assert await stale.scalar(sa.select(orm.NarrativeJobRow.status).where(orm.NarrativeJobRow.job_id == saved["job_id"])) == saved["status"]
                    async with case.factory.begin() as writer:
                        await writer.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.job_id == saved["job_id"]).values(**values))
                    assert await stale.scalar(sa.select(orm.NarrativeJobRow.status).where(orm.NarrativeJobRow.job_id == saved["job_id"])) == saved["status"]
                    with pytest.raises(RunProtocolBindingStoredIntegrityError, match="active narrative job"):
                        await SqlAlchemyRunProtocolBindingRepository(stale).get_classified_for_update(run_id=RunId(value=regional["run_id"]))
                    await stale.rollback()
                before = await schema_state(mysql_engine)
                for sid, route in readers:
                    reply = await case.client.get(f"/v1/sessions/{sid}/{route}")
                    assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", (source, sid, route, reply.text)
                replays = [("/v1/runs/native", history[1], "s7.2.admit"),
                    (f"/v1/sessions/{paths[0]}/run-continuation", history[3], "s7.2.continue"),
                    (f"/v1/sessions/{paths[1]}/run-revisit", dict(expected_run_state_version=4, expected_session_state_version=history[-1]["metadata"]["state_version"]), "mysql.revisit")]
                for route, request, key in replays:
                    reply = await case.client.post(route, json=request, headers={"Idempotency-Key": key})
                    assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
                reply = await complete(case, ended)
                assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
                assert await schema_state(mysql_engine) == before
            finally:
                async with case.factory.begin() as session:
                    await session.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.job_id == saved["job_id"]).values(**saved))
        assert await schema_state(mysql_engine) == clean


async def test_r1_mysql_active_archive_live_job_control(mysql_engine, monkeypatch):
    from deviation_protocol.application.narrative_jobs import LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION
    async with continuation_case(mysql_engine, monkeypatch, head="20260920_0011") as case:
        history, regional, current = await sealed_source(case, "difficulty.silent-hunting-ground", choice=None)
        assert current["scenario_status"] == "ACTIVE"
        async with case.factory() as session:
            saved = dict((await session.execute(sa.select(orm.NarrativeJobRow.__table__).where(
                orm.NarrativeJobRow.session_id == regional["session_id"],
                orm.NarrativeJobRow.prompt_schema_version != LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION))).mappings().one())
        try:
            async with case.factory.begin() as session:
                await session.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.job_id == saved["job_id"]).values(
                    status="PREPARED", attempt_count=0, lease_token=None, lease_owner=None, lease_expires_at=None,
                    validated_proposal_json=None, validated_proposal_digest=None, outcome_rule_id=None, accepted_narrative_text=None, error_code=None))
            before = await schema_state(mysql_engine)
            for sid in (history[0]["session_id"], history[4]["session_id"], regional["session_id"]):
                for route in ("view", "run-journey", "run-status", "run-completion"):
                    reply = await case.client.get(f"/v1/sessions/{sid}/{route}")
                    assert reply.status_code == 200, reply.text
            assert await schema_state(mysql_engine) == before
        finally:
            async with case.factory.begin() as session:
                await session.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.job_id == saved["job_id"]).values(**saved))


async def test_a07_mysql_all_precommit_boundaries_and_zero_row_cas(mysql_engine,monkeypatch):
    from deviation_protocol.infrastructure import repositories as r
    from deviation_protocol.application.run_completion_service import RunCompletionCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql.dml import Update
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,_,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        sid=ended["metadata"]["session_id"];before=await schema_state(mysql_engine)
        command=RunCompletionCommand(public_operation_key=RunEntryPublicOperationKey(value="precommit.complete"),expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"])
        for stage in ("revision","cas","receipt","reconstruction"):
            owner,method={"revision":(r.SqlAlchemyRunRepository,"append_revision"),"cas":(r.SqlAlchemyRunRepository,"compare_and_swap_current"),
                "receipt":(r.SqlAlchemyRunMutationReceiptRepository,"add"),"reconstruction":(r.SqlAlchemyRunProtocolBindingRepository,"get_classified_for_update")}[stage]
            original=getattr(owner,method)
            for cancel in (False,True):
                sentinel=asyncio.CancelledError("precommit cancellation") if cancel else RuntimeError("precommit failure")
                async def fail(*args,**kwargs):
                    result=await original(*args,**kwargs)
                    if stage!="reconstruction" or result.canonical_run.lifecycle_status.value=="completed":raise sentinel
                    return result
                with monkeypatch.context() as patch:
                    patch.setattr(owner,method,fail)
                    with pytest.raises(type(sentinel)) as caught:
                        await case.services.run_completion_service.complete(case.runtime.principal,session_id=sid,command=command)
                    assert caught.value is sentinel
                assert await schema_state(mysql_engine)==before
        original=AsyncSession.execute;observed=[]
        async def zero(session,statement,*args,**kwargs):
            if isinstance(statement,Update) and statement.table.name=="run_current":
                result=await original(session,statement.where(sa.false()),*args,**kwargs);observed.append(result.rowcount);return result
            return await original(session,statement,*args,**kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(AsyncSession,"execute",zero)
            reply=await complete(case,ended)
        assert observed==[0]
        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="RUN_COMPLETION_CONFLICT",reply.text
        assert await schema_state(mysql_engine)==before
        # Force a real MySQL duplicate receipt insert in the same transaction;
        # do not simulate the repository's known uniqueness exception.
        from deviation_protocol.application.ports import RunReceiptUniquenessConflictError
        original_flush=r._SqlAlchemyRunRepositorySupport._flush_run_row
        duplicate_codes=[]
        async def duplicate(repository,row,**kwargs):
            await original_flush(repository,row,**kwargs)
            if isinstance(row,orm.RunMutationReceiptRow) and row.command_kind=="COMPLETE_REVISITED_NATIVE_RUN":
                clone=orm.RunMutationReceiptRow(**{c.name:getattr(row,c.name) for c in row.__table__.columns})
                try:
                    await original_flush(repository,clone,**kwargs)
                except RunReceiptUniquenessConflictError as error:
                    duplicate_codes.append(error.__cause__.orig.args[0])
                    raise
        with monkeypatch.context() as patch:
            patch.setattr(r.SqlAlchemyRunMutationReceiptRepository,"_flush_run_row",duplicate)
            reply=await complete(case,ended)
        assert duplicate_codes==[1062]
        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="RUN_COMPLETION_CONFLICT",reply.text
        assert await schema_state(mysql_engine)==before
        assert (await complete(case,ended)).status_code==200


async def test_a09_completion_nullable_matrix_and_current_downgrade_refusal(mysql_engine,monkeypatch):
    from sqlalchemy.exc import DBAPIError
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    module=SCRIPT.get_revision("20260920_0011").module
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,regional,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        rid=regional["run_id"]
        async with mysql_engine.connect() as stale:
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_current WHERE lifecycle_status='completed'"))==0
            assert (await complete(case,ended)).status_code==200
            assert await stale.scalar(sa.text("SELECT COUNT(*) FROM run_current WHERE lifecycle_status='completed'"))==0
            before=await schema_state(mysql_engine)
            statements=[]
            def downgrade(sync):
                class Owner:
                    def __getattr__(self,name):return getattr(sync,name)
                    def execute(self,statement,*args,**kwargs):
                        statements.append(str(statement));return sync.execute(statement,*args,**kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:Owner());module.downgrade()
            with pytest.raises(RuntimeError):await stale.run_sync(downgrade)
            await stale.rollback()
            assert any("FOR UPDATE" in sql for sql in statements)
            assert not any(sql.lstrip().startswith("ALTER TABLE") for sql in statements)
        for model in (orm.RunCurrentRow,orm.RunRevisionRow):
            clause=next(new for table,_,_,new in module._CONSTRAINTS if table==model.__tablename__)
            for field in ("prior_state_version","binding_player_character_id","binding_contract_version","binding_record_revision",
                          "binding_state","binding_operation_id","binding_authority_source_ref","bound_at","inactivated_at"):
                projection=",".join("NULL AS "+c.name if c.name==field else c.name for c in model.__table__.columns)
                async with mysql_engine.connect() as c:
                    assert await c.scalar(sa.text(f"SELECT ({clause}) FROM (SELECT {projection} FROM {model.__tablename__} WHERE run_id=:rid AND state_version=6) candidate"),{"rid":rid})==0
                    await c.rollback()
                    with pytest.raises(DBAPIError) as caught:
                        await c.execute(sa.update(model).where(model.run_id==rid,model.state_version==6).values(**{field:None}))
                    assert caught.value.orig.args[0] in (3819,1048);await c.rollback()
        for field in ("participation_session_id","participation_operation_id","participation_source_reference","result_player_character_id","result_character_contract_version","result_character_record_revision"):
            column=orm.RunMutationReceiptRow.__table__.columns[field]
            value=1 if isinstance(column.type,sa.Integer) else "wrong"
            async with mysql_engine.connect() as c:
                with pytest.raises(DBAPIError) as caught:
                    await c.execute(sa.update(orm.RunMutationReceiptRow).where(orm.RunMutationReceiptRow.run_id==rid,orm.RunMutationReceiptRow.resulting_state_version==6).values(**{field:value}))
                assert caught.value.orig.args[0]==3819;await c.rollback()
        assert await schema_state(mysql_engine)==before


async def test_a09_old_terminated_six_preserved_and_partial_evidence_refused(mysql_engine,monkeypatch):
    from tests.integration.test_mysql_world_continuation_migration import migrate_to
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,regional,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        reply=await complete(case,ended,key="complete-revisited-native",route="run-exit")
        assert reply.status_code==200 and reply.json()["lifecycle_status"]=="terminated",reply.text
        # Preserve populated original-terminal4, continued-terminal5, revisited-
        # terminal6 and legacy families in the same 010/011 round trip.
        from tests.integration.test_mysql_native_run_exit import public_admit
        from tests.unit.test_run_exit_api import play_to_ending
        for continued in (False,True):
            admitted,_=await public_admit(case,"old.family."+str(continued),"difficulty.silent-hunting-ground")
            sid=admitted["session_id"];old_ending,_=await play_to_ending(case.client,sid)
            if continued:
                response=await case.client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=3,
                        expected_session_state_version=old_ending["metadata"]["state_version"]),headers={"Idempotency-Key":"old.complete-revisited-native.continue"})
                assert response.status_code==200,response.text
                sid=response.json()["session_id"];case.scope.session_ids.add(sid)
                await action(case.client,sid,"old.observe",action_type="OBSERVE",description="核对记录")
                await action(case.client,sid,"old.talk",action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对排程")
                current=await view(case.client,sid)
                await action(case.client,sid,"old.hold",action_type="CHOOSE",decision_id=current["narrative_frame"]["decision_id"],choice_id="undelivered_receipt.action.hold")
                old_ending=await view(case.client,sid)
            result=await case.client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=4 if continued else 3,
                expected_session_state_version=old_ending["metadata"]["state_version"]),headers={"Idempotency-Key":"old.exit."+str(continued)})
            assert result.status_code==200,result.text
        from tests.integration.test_mysql_run_entry_playthrough import _entry
        from deviation_protocol.domain.run import RunAuthoritySourceRef
        # Completion-like text is also legal in a trusted opaque source.
        # Produce genuine coherent legacy rows through the public entry service.
        with monkeypatch.context() as source_patch:
            source_patch.setattr(case.services.run_entry_service, "source_reference",
                RunAuthoritySourceRef(value="source.complete-revisited-native"))
            legacy=await _entry(case.client,key="legacy.complete-revisited-native",character_id=case.runtime.character_ids[1].value)
        assert legacy.status_code==200,legacy.text
        case.scope.run_ids.add(legacy.json()["run_id"]);case.scope.session_ids.add(legacy.json()["session_id"])
        before=await schema_state(mysql_engine)
        await migrate_to(mysql_engine,"20260918_0010")
        await migrate_to(mysql_engine,"20260920_0011")
        assert await schema_state(mysql_engine)==before
        # Each stored location alone can establish partial completion evidence;
        # keep the other two locations as the genuine terminated-six family.
        for model,changes in (
            (orm.RunCurrentRow,dict(lifecycle_status="completed",mutation_kind="COMPLETE_REVISITED_NATIVE_RUN")),
            (orm.RunRevisionRow,dict(lifecycle_status="completed",mutation_kind="COMPLETE_REVISITED_NATIVE_RUN")),
            (orm.RunMutationReceiptRow,dict(resulting_lifecycle_status="completed",command_kind="COMPLETE_REVISITED_NATIVE_RUN",
                operation_namespace="run.complete-revisited-native/v1",result_schema_version="run.complete-revisited-native-result/v1"))):
            version=model.resulting_state_version if model is orm.RunMutationReceiptRow else model.state_version
            async with case.factory() as session:
                row=(await session.execute(sa.select(model.__table__).where(model.run_id==regional["run_id"],version==6))).mappings().one()
                saved={key:row[key] for key in changes}
            try:
                async with case.factory.begin() as session:
                    await session.execute(sa.update(model).where(model.run_id==regional["run_id"],version==6).values(**changes))
                partial=await schema_state(mysql_engine)
                with pytest.raises(RuntimeError,match="complete, partial"):
                    await migrate_to(mysql_engine,"20260918_0010")
                assert await schema_state(mysql_engine)==partial
            finally:
                async with case.factory.begin() as session:
                    await session.execute(sa.update(model).where(model.run_id==regional["run_id"],version==6).values(**saved))
        model=orm.RunMutationReceiptRow
        async with case.factory() as session:
            original=await session.scalar(sa.select(model.operation_evidence_canonical).where(model.run_id==regional["run_id"],model.resulting_state_version==6))
        import json
        crossed = json.loads(original); crossed["schema"] = "run.complete-revisited-native-evidence/v1"
        extra = json.loads(original); extra["transition"] = {"schema": "run.canon-transition/v1"}
        for payload in (b'{"schema":"run.complete-revisited-native-evidence/v1"}',b'{}',b'{"schema":"unsupported/v1"}',b'\xff',original+b' ',
                        json.dumps(crossed,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(),
                        json.dumps(extra,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()):
            try:
                async with case.factory.begin() as session:
                    await session.execute(sa.update(model).where(model.run_id==regional["run_id"],model.resulting_state_version==6).values(operation_evidence_canonical=payload))
                corrupted=await schema_state(mysql_engine)
                with pytest.raises(RuntimeError):await migrate_to(mysql_engine,"20260918_0010")
                assert await schema_state(mysql_engine)==corrupted
            finally:
                async with case.factory.begin() as session:
                    await session.execute(sa.update(model).where(model.run_id==regional["run_id"],model.resulting_state_version==6).values(operation_evidence_canonical=original))
        # Canonical JSON with the old discriminator/keys is still malformed
        # when its typed carrier values are corrupt. Refuse before any DDL.
        import json
        async with case.factory() as session:
            carriers=(await session.execute(sa.select(model.run_id,model.resulting_state_version,
                model.command_kind,model.operation_evidence_canonical).where(
                    model.run_id==legacy.json()["run_id"],
                    model.command_kind.in_(("ATTACH_SESSION","BIND_PLAYER_CHARACTER"))))).all()
        assert {row.command_kind for row in carriers}=={"ATTACH_SESSION","BIND_PLAYER_CHARACTER"}
        for row in carriers:
            for field in json.loads(row.operation_evidence_canonical):
                decoded=json.loads(row.operation_evidence_canonical);decoded[field]=None
                payload=json.dumps(decoded,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
                try:
                    async with case.factory.begin() as session:
                        await session.execute(sa.update(model).where(model.run_id==row.run_id,
                            model.resulting_state_version==row.resulting_state_version).values(operation_evidence_canonical=payload))
                    corrupted=await schema_state(mysql_engine)
                    with pytest.raises(RuntimeError,match="complete, partial"):
                        await migrate_to(mysql_engine,"20260918_0010")
                    assert await schema_state(mysql_engine)==corrupted
                finally:
                    async with case.factory.begin() as session:
                        await session.execute(sa.update(model).where(model.run_id==row.run_id,
                            model.resulting_state_version==row.resulting_state_version).values(operation_evidence_canonical=row.operation_evidence_canonical))
        assert await schema_state(mysql_engine)==before


async def sealed_source(case, profile="difficulty.open-expedition", choice="seal"):
    history = await held_source(case, profile)
    response = await revisit(case, history[-1])
    assert response.status_code == 200, response.text
    sid = response.json()["session_id"]
    case.scope.session_ids.add(sid)
    await action(case.client, sid, "complete.observe", action_type="OBSERVE", description="核验封存记录")
    decision = await view(case.client, sid)
    if choice is None:
        return history, response.json(), decision
    await action(case.client, sid, "complete.seal", action_type="CHOOSE",
        decision_id=decision["narrative_frame"]["decision_id"], choice_id="receipt_archive.action." + choice)
    return history, response.json(), await view(case.client, sid)


async def complete(case, ended, key="mysql.complete", route="run-complete"):
    return await case.client.post(f'/v1/sessions/{ended["metadata"]["session_id"]}/{route}',
        json=dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"]),
        headers={"Idempotency-Key": key})


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.silent-hunting-ground", "difficulty.fragile-alliance"])
async def test_s7_4_mysql_public_completion_replay_and_fresh_admission(mysql_engine, monkeypatch, profile):
    async with continuation_case(mysql_engine, monkeypatch, head="20260920_0011") as case:
        history, regional, ended = await sealed_source(case, profile)
        before = await schema_state(mysql_engine)
        result = await complete(case, ended)
        assert result.status_code == 200, result.text
        after = await schema_state(mysql_engine)
        for table, value in before[0].items():
            if table not in {"run_revisions", "run_current", "run_mutation_receipts"}:
                assert after[0][table] == value
        for sid in (history[0]["session_id"], history[4]["session_id"], regional["session_id"]):
            reply = await case.client.get(f"/v1/sessions/{sid}/run-completion")
            assert reply.status_code == 200, reply.text
            assert reply.json()["completion"] == result.json()["completion"]
        assert (await complete(case, ended)).json() == result.json()
        assert await schema_state(mysql_engine) == after
        fresh = await case.client.post("/v1/runs/native", json=history[1], headers={"Idempotency-Key": "completion.fresh"})
        assert fresh.status_code == 200, fresh.text
        new = fresh.json()
        case.scope.run_ids.add(new["run_context"]["run_id"])
        case.scope.session_ids.add(new["session_id"])
        assert new["run_context"]["run_id"] != result.json()["run_id"]
        await action(case.client, new["session_id"], "completion.first", action_type="OBSERVE", description="查看病房")
        progressed = await schema_state(mysql_engine)
        assert (await complete(case, ended)).json() == result.json()
        assert await schema_state(mysql_engine) == progressed


@pytest.mark.parametrize("competitor", ["same_key", "different_key", "exit"])
async def test_s7_4_mysql_observed_completion_races(mysql_engine, monkeypatch, competitor):
    async with continuation_case(mysql_engine, monkeypatch, head="20260920_0011") as case:
        _, _, ended = await sealed_source(case, "difficulty.silent-hunting-ground")
        tasks = []
        async with mysql_engine.connect() as blocker:
            assert await blocker.scalar(sa.text("SELECT GET_LOCK(:lock,30)"), {"lock": NATIVE_ADMISSION_LOCK}) == 1
            try:
                tasks = [asyncio.create_task(complete(case, ended)), asyncio.create_task(complete(case, ended,
                    "mysql.complete" if competitor == "same_key" else "other",
                    "run-exit" if competitor == "exit" else "run-complete"))]
                assert await wait_for_named_lock_waiters(mysql_engine, 2) >= 2
                assert not any(task.done() for task in tasks)
            finally:
                assert await blocker.scalar(sa.text("SELECT RELEASE_LOCK(:lock)"), {"lock": NATIVE_ADMISSION_LOCK}) == 1
        replies = await asyncio.wait_for(asyncio.gather(*tasks), 90)
        assert sorted(r.status_code for r in replies) == ([200, 200] if competitor == "same_key" else [200, 409]), [r.text for r in replies]
        if competitor == "same_key":
            assert replies[0].json() == replies[1].json()
        status = await case.client.get(f'/v1/sessions/{ended["metadata"]["session_id"]}/run-completion')
        assert status.status_code == 200, status.text
        assert status.json()["lifecycle_status"] in ("completed", "terminated")


from dataclasses import replace


@pytest.mark.parametrize("competitor",["admission","retirement"])
async def test_a08_character_first_completion_and_later_operation(mysql_engine,monkeypatch,competitor):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from tests.integration.test_mysql_native_run_exit import wait_for_row_lock_waiter
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        history,_,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        staged,release=asyncio.Event(),asyncio.Event();original=SqlAlchemyRunRepository.compare_and_swap_current
        async def pause(repository,run,**kwargs):
            result=await original(repository,run,**kwargs)
            if run.lifecycle_status.value=="completed":staged.set();await release.wait()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
            completing=asyncio.create_task(complete(case,ended))
            await asyncio.wait_for(staged.wait(),30)
            if competitor=="admission":
                competing=asyncio.create_task(case.client.post("/v1/runs/native",json=history[1],headers={"Idempotency-Key":"racing.new"}))
            else:
                competing=asyncio.create_task(case.client.post(f"/v1/player-characters/{case.runtime.character_ids[0].value}/retirement",
                    headers={"Idempotency-Key":"racing.retire"},json=dict(contract_version="structured-player-character/v1",expected_revision={"value":1},confirm_retirement=True)))
            try:
                if competitor=="admission":await wait_for_named_lock_waiters(mysql_engine,1)
                else:await wait_for_row_lock_waiter(mysql_engine)
                assert not competing.done()
            finally:release.set()
            results=await asyncio.wait_for(asyncio.gather(completing,competing),90)
        assert [r.status_code for r in results]==[200,200],[r.text for r in results]
        if competitor=="admission":
            new=results[1].json();case.scope.run_ids.add(new["run_context"]["run_id"]);case.scope.session_ids.add(new["session_id"])
        before=await schema_state(mysql_engine)
        assert (await complete(case,ended)).json()==results[0].json()
        assert await schema_state(mysql_engine)==before


async def test_a08_final_seal_wait_uses_committed_current_state_and_requires_fresh_consent(mysql_engine,monkeypatch):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
    from tests.integration.test_mysql_native_run_exit import wait_for_row_lock_waiter
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,regional,decision=await sealed_source(case,"difficulty.silent-hunting-ground",choice=None)
        sid=regional["session_id"];staged,release=asyncio.Event(),asyncio.Event();original=SqlAlchemyUnitOfWork.commit
        async def pause(unit):
            snapshot=await unit.sessions.get_latest_snapshot(sid)
            if snapshot and snapshot.state["scenario_runtime"]["ending_id"]=="receipt_archive.ending.unresolved_sealed":
                staged.set();await release.wait()
            return await original(unit)
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyUnitOfWork,"commit",pause)
            playing=asyncio.create_task(action(case.client,sid,"last.seal",action_type="CHOOSE",decision_id=decision["narrative_frame"]["decision_id"],choice_id="receipt_archive.action.seal"))
            await asyncio.wait_for(staged.wait(),30)
            completing=asyncio.create_task(complete(case,decision))
            try:
                await wait_for_row_lock_waiter(mysql_engine)
                assert not playing.done() and not completing.done()
            finally:release.set()
            _,reply=await asyncio.wait_for(asyncio.gather(playing,completing),90)
        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="RUN_COMPLETION_STALE",reply.text
        settled=await view(case.client,sid)
        assert settled["metadata"]["state_version"]==decision["metadata"]["state_version"]+1
        assert (await complete(case,settled,"new.consent")).status_code==200


@pytest.mark.parametrize("migration_first",[False,True])
async def test_a09_writer_and_downgrade_share_physical_lock(mysql_engine,monkeypatch,migration_first):
    from tests.integration.test_mysql_run_protocol_binding import SCRIPT
    from tests.integration.test_mysql_world_continuation_migration import migrate_to
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from sqlalchemy.util import await_only
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,_,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        held,release=asyncio.Event(),asyncio.Event()
        with monkeypatch.context() as patch:
            if migration_first:
                module=SCRIPT.get_revision("20260920_0011").module;original_bind=module.op.get_bind
                class Owner:
                    def __init__(self,connection):self.connection=connection
                    def __getattr__(self,name):return getattr(self.connection,name)
                    def execute(self,statement,*args,**kwargs):
                        if "RELEASE_LOCK" in str(statement):held.set();await_only(release.wait())
                        return self.connection.execute(statement,*args,**kwargs)
                patch.setattr(module.op,"get_bind",lambda:Owner(original_bind()))
                first=asyncio.create_task(migrate_to(mysql_engine,"20260918_0010"))
            else:
                original=SqlAlchemyRunRepository.compare_and_swap_current
                async def pause(repository,run,**kwargs):
                    result=await original(repository,run,**kwargs)
                    if run.lifecycle_status.value=="completed":held.set();await release.wait()
                    return result
                patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
                first=asyncio.create_task(complete(case,ended))
            await asyncio.wait_for(held.wait(),30)
            second=asyncio.create_task(complete(case,ended) if migration_first else migrate_to(mysql_engine,"20260918_0010"))
            try:
                await wait_for_named_lock_waiters(mysql_engine,1);assert not second.done()
            finally:release.set()
            results=await asyncio.wait_for(asyncio.gather(first,second,return_exceptions=True),90)
        if migration_first:
            assert results[0] is None and results[1].status_code==409,results
            assert results[1].json()["error"]["error_code"]=="SNAPSHOT_INVALID"
            await migrate_to(mysql_engine,"20260920_0011")
            assert (await complete(case,ended,"fresh.after.upgrade")).status_code==200
        else:
            assert results[0].status_code==200,results[0].text
            assert isinstance(results[1],RuntimeError),results[1]
@pytest.mark.parametrize("committed",[False,True])
@pytest.mark.parametrize("cancel",[False,True])
async def test_a07_mysql_completion_unknown_commit_and_exact_retry(mysql_engine,monkeypatch,committed,cancel):
    from sqlalchemy.ext.asyncio import AsyncTransaction
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_completion_service import RunCompletionCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,_,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        sid=ended["metadata"]["session_id"]
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_completion_service,revisit=replace(case.services.run_revisit_service,continuation=replace(case.services.run_revisit_service.continuation,authority=replace(case.services.run_revisit_service.authority,uow_factory=lambda:unit))))
        original=AsyncTransaction.commit
        sentinel=asyncio.CancelledError("lost commit acknowledgement") if cancel else RuntimeError("lost commit acknowledgement")
        attempts=[]
        async def commit(transaction):
            if transaction is unit._transaction:
                attempts.append(transaction)
                if committed:await original(transaction)
                raise sentinel
            return await original(transaction)
        command=RunCompletionCommand(public_operation_key=RunEntryPublicOperationKey(value="unknown.continue"),expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(AsyncTransaction,"commit",commit)
            with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError) as caught:
                await service.complete(case.runtime.principal,session_id=sid,command=command)
            if cancel:assert caught.value is sentinel and sentinel.commit_outcome_unknown
        assert len(attempts)==1 and unit._connection.closed
        status=await case.services.run_completion_service.status(case.runtime.principal,session_id=sid)
        assert (status["lifecycle_status"]=="completed")==committed
        result=await case.services.run_completion_service.complete(case.runtime.principal,session_id=sid,command=command)
        if committed:assert result["source_session_id"]==status["current"]["session_id"]
        before=await schema_state(mysql_engine)
        assert await case.services.run_completion_service.complete(case.runtime.principal,session_id=sid,command=command)==result
        assert await schema_state(mysql_engine)==before




@pytest.mark.parametrize("cancel",[False,True])
async def test_a07_mysql_completion_postcommit_cleanup_unknown(mysql_engine,monkeypatch,cancel):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_completion_service import RunCompletionCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    from tests.integration.test_mysql_native_run_migration import observe
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        _,_,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        sid=ended["metadata"]["session_id"]
        unit=SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine,content_registry=case.services.content_registry)
        service=replace(case.services.run_completion_service,revisit=replace(case.services.run_revisit_service,continuation=replace(case.services.run_revisit_service.continuation,authority=replace(case.services.run_revisit_service.authority,uow_factory=lambda:unit))))
        sentinel=asyncio.CancelledError("cleanup cancellation") if cancel else RuntimeError("cleanup failure")
        async def fail():raise sentinel
        monkeypatch.setattr(unit,"_cleanup",fail)
        command=RunCompletionCommand(public_operation_key=RunEntryPublicOperationKey(value="cleanup.continue"),expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"])
        with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError):
            await service.complete(case.runtime.principal,session_id=sid,command=command)
        assert unit._connection.closed
        await observe(mysql_engine,unit.connection_id)
        status=await case.services.run_completion_service.status(case.runtime.principal,session_id=sid)
        before=await schema_state(mysql_engine)
        assert (await case.services.run_completion_service.complete(case.runtime.principal,session_id=sid,command=command))["source_session_id"]==status["current"]["session_id"]
        assert await schema_state(mysql_engine)==before




async def test_a08_obsolete_transition_replays_during_uncommitted_completion(mysql_engine,monkeypatch):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    async with continuation_case(mysql_engine,monkeypatch,head="20260920_0011") as case:
        history,regional,ended=await sealed_source(case,"difficulty.silent-hunting-ground")
        staged,release=asyncio.Event(),asyncio.Event();original=SqlAlchemyRunRepository.compare_and_swap_current
        async def pause(repository,run,**kwargs):
            result=await original(repository,run,**kwargs)
            if run.lifecycle_status.value=="completed":staged.set();await release.wait()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
            writer=asyncio.create_task(complete(case,ended))
            await asyncio.wait_for(staged.wait(),30)
            requests=(
                (history[0]["session_id"],"run-continuation",history[3],"s7.2.continue",history[4]),
                (history[4]["session_id"],"run-revisit",dict(expected_run_state_version=4,expected_session_state_version=history[-1]["metadata"]["state_version"]),"mysql.revisit",regional))
            replaying=[asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/{route}",json=body,headers={"Idempotency-Key":key}))
                for sid,route,body,key,_ in requests]
            try:
                # Continuation's established replay path takes the native guard;
                # revisit can use its immutable reader shortcut. Observe the real
                # continuation waiter before releasing the completion writer.
                await wait_for_named_lock_waiters(mysql_engine,1)
                assert not writer.done() and not replaying[0].done()
            finally:release.set()
            assert (await asyncio.wait_for(writer,30)).status_code==200
            for replay,request in zip(await asyncio.wait_for(asyncio.gather(*replaying),30),requests):
                assert replay.status_code==200 and replay.json()==request[-1],replay.text
        before=await schema_state(mysql_engine)
        for sid,route,version in ((history[0]["session_id"],"run-continuation",3),(history[4]["session_id"],"run-revisit",4)):
            current=await view(case.client,sid)
            reply=await case.client.post(f"/v1/sessions/{sid}/{route}",json=dict(expected_run_state_version=version,
                expected_session_state_version=current["metadata"]["state_version"]),headers={"Idempotency-Key":"obsolete.new"})
            assert reply.status_code==409,reply.text
        assert await schema_state(mysql_engine)==before
