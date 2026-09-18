"""Fresh public play and terminal replay on the authorized MySQL test schema."""
from contextlib import asynccontextmanager
import asyncio
from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.infrastructure import orm_models as orm
from tests.integration import test_mysql_native_run_admission as admission_tests
from tests.integration.test_mysql_native_run_admission import native_runtime, family_bytes
from tests.integration.test_mysql_native_turn_mechanics import Renderer
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.unit.test_native_run_entry_api import body
from tests.unit.test_run_exit_api import play_to_ending

pytestmark = pytest.mark.integration


async def migrate_to(engine, target):
    async with engine.connect() as connection:
        assert await connection.scalar(sa.text("SELECT DATABASE()")) == "deviation_protocol_test"
        current = await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        await connection.rollback()
        def run(sync):
            direction = SCRIPT._downgrade_revs if target < current else SCRIPT._upgrade_revs
            context = MigrationContext.configure(sync, opts={"fn": lambda revisions, context: direction(target, revisions)})
            with Operations.context(context), context.begin_transaction():
                context.run_migrations()
        if current != target:
            await connection.run_sync(run)
            await connection.commit()


@asynccontextmanager
async def exit_case(engine, monkeypatch):
    async with engine.connect() as connection:
        original = await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        assert original in ("20260916_0007", "20260917_0008", "20260918_0009")
    with monkeypatch.context() as patch:
        patch.setattr(admission_tests, "HEAD", "20260918_0009")
        try:
            async with native_runtime(engine) as case:
                patch.setattr(main, "create_engine", lambda: engine)
                patch.delenv("DEEPSEEK_API_KEY", raising=False)
                services = main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
                    authentication_scheme=case.runtime.principal.authentication_scheme,
                    player_id=case.runtime.principal.player_id, controller_id=case.runtime.resolver.binding.value),))
                services.turn_orchestrator.narrative_provider = Renderer()
                app = main.create_app(services=services)
                app.state.api_services = services
                app.dependency_overrides[get_current_principal] = lambda: case.runtime.principal
                case.services = services
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
                    case.client = client
                    yield case
        finally:
            await migrate_to(engine, original)


async def public_admit(case, key, profile="difficulty.open-expedition"):
    request = body(case.runtime.character_ids[0].value)
    request["profile_ref"]["profile_id"] = profile
    response = await case.client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    result = response.json()
    case.scope.run_ids.add(result["run_context"]["run_id"])
    case.scope.session_ids.add(result["session_id"])
    return result, request


async def wait_for_named_lock_waiters(engine, count):
    async with engine.connect() as observer:
        async with asyncio.timeout(10):
            while True:
                waiting = await observer.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE STATE = 'User lock' AND INFO LIKE '%p33:s3:run_protocol_bindings%'") )
                if waiting >= count: return waiting
                await asyncio.sleep(0.01)


async def wait_for_row_lock_waiter(engine):
    async with engine.connect() as observer:
        async with asyncio.timeout(10):
            while True:
                # The least-privileged test account can inspect its own live
                # statements, not global performance_schema/INNODB_TRX. The
                # competing FOR UPDATE is executing against a row we still
                # hold, and completes only after our explicit release.
                waiting = await observer.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE TIME >= 1 AND INFO LIKE '%FOR UPDATE' AND (INFO LIKE 'SELECT player_character_current.%' OR INFO LIKE 'SELECT game_sessions.%')"))
                if waiting: return waiting
                await asyncio.sleep(0.01)


@pytest.mark.parametrize("competitor", ["admission", "retirement"])
async def test_e05_exit_serializes_admission_and_retirement(mysql_engine, monkeypatch, competitor):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, request = await public_admit(case, "compete.admit", "difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client, sid)
        staged, release = asyncio.Event(), asyncio.Event()
        original = SqlAlchemyRunRepository.compare_and_swap_current
        async def pause(repository, run, **kw):
            result = await original(repository, run, **kw)
            if run.state_version.value == 4:
                staged.set()
                await release.wait()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyRunRepository, "compare_and_swap_current", pause)
            exiting = asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"compete.exit"},
                json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]}))
            await asyncio.wait_for(staged.wait(), 10)
            if competitor == "admission":
                competing = asyncio.create_task(case.client.post("/v1/runs/native", json=request, headers={"Idempotency-Key":"compete.new"}))
            else:
                competing = asyncio.create_task(case.client.post(f"/v1/player-characters/{case.runtime.character_ids[0].value}/retirement",
                    headers={"Idempotency-Key":"compete.retire"}, json={"contract_version":"structured-player-character/v1",
                    "expected_revision":{"value":1},"confirm_retirement":True}))
            try:
                if competitor == "admission": await wait_for_named_lock_waiters(mysql_engine, 1)
                else: await wait_for_row_lock_waiter(mysql_engine)
                assert not competing.done()
            finally:
                release.set()
            responses = await asyncio.wait_for(asyncio.gather(exiting, competing), 20)
        assert responses[0].status_code == 200, responses[0].text
        assert responses[1].status_code == 200, responses[1].text
        if competitor == "admission":
            admitted = responses[1].json()
            case.scope.run_ids.add(admitted["run_context"]["run_id"])
            case.scope.session_ids.add(admitted["session_id"])
        stored = await family_bytes(case)
        assert len(stored["run_revisions"]) == (7 if competitor == "admission" else 4)
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json() == ended


async def test_e05_final_turn_locks_session_without_reverse_run_write_lock(mysql_engine, monkeypatch):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, _ = await public_admit(case, "final.admit", "difficulty.silent-hunting-ground")
        sid = first["session_id"]
        staged, release = asyncio.Event(), asyncio.Event()
        version = []
        original = SqlAlchemyUnitOfWork.commit
        async def pause(unit):
            snapshot = await unit.sessions.get_latest_snapshot(sid)
            runtime = snapshot.state.get("scenario_runtime") if snapshot else None
            if runtime and runtime["ending_status"] in ("RESOLVED", "FAILED"):
                version.append(snapshot.state_version)
                staged.set()
                await release.wait()
            return await original(unit)
        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyUnitOfWork, "commit", pause)
            playing = asyncio.create_task(play_to_ending(case.client, sid))
            await asyncio.wait_for(staged.wait(), 20)
            exiting = asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"final.exit"},
                json={"expected_run_state_version":3,"expected_session_state_version":version[0]}))
            try:
                await wait_for_row_lock_waiter(mysql_engine)
                assert not exiting.done()
            finally: release.set()
            ended, response = await asyncio.wait_for(asyncio.gather(playing, exiting), 20)
        assert response.status_code == 200, response.text
        assert (await case.client.get(f"/v1/sessions/{sid}/view")).json() == ended[0]


@pytest.mark.parametrize("same_key", [True, False])
async def test_e05_real_exit_connections_wait_and_serialize(mysql_engine, monkeypatch, same_key):
    from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, _ = await public_admit(case, "race.admit", "difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client, sid)
        body = {"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]}
        tasks = []
        async with mysql_engine.connect() as blocker:
            assert await blocker.scalar(sa.text(f"SELECT GET_LOCK('{NATIVE_ADMISSION_LOCK}',30)")) == 1
            try:
                for key in ("race.exit", "race.exit" if same_key else "race.other"):
                    tasks.append(asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-exit", json=body, headers={"Idempotency-Key":key})))
                assert await wait_for_named_lock_waiters(mysql_engine, 2) >= 2
                assert not any(t.done() for t in tasks)
            finally:
                assert await blocker.scalar(sa.text(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')")) == 1
        results = await asyncio.wait_for(asyncio.gather(*tasks), 15)
        assert sorted(r.status_code for r in results) == ([200,200] if same_key else [200,409])
        if same_key: assert results[0].json() == results[1].json()
        else: assert next(r for r in results if r.status_code == 409).json()["error"]["error_code"] == "RUN_EXIT_NOT_AVAILABLE"
        stored = await family_bytes(case)
        assert len(stored["run_revisions"]) == 4 and len(stored["run_mutation_receipts"]) == 3


@pytest.mark.parametrize("stage", ["revision", "cas", "receipt", "before_commit"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_e06_sql_rollback_restores_every_row(mysql_engine, monkeypatch, stage, cancel):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository, SqlAlchemyRunMutationReceiptRepository, SqlAlchemyRunProtocolBindingRepository
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, _ = await public_admit(case, "fault.admit", "difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client, sid)
        before = await family_bytes(case)
        owner, method = {"revision":(SqlAlchemyRunRepository,"append_revision"), "cas":(SqlAlchemyRunRepository,"compare_and_swap_current"),
            "receipt":(SqlAlchemyRunMutationReceiptRepository,"add"), "before_commit":(SqlAlchemyRunProtocolBindingRepository,"get_classified_for_update")}[stage]
        original = getattr(owner, method)
        sentinel = asyncio.CancelledError("exit cancellation") if cancel else RuntimeError("exit rollback fault")
        async def fail(*args, **kwargs):
            result = await original(*args, **kwargs)
            if stage != "before_commit" or result.canonical_run.state_version.value == 4:
                raise sentinel
            return result
        from deviation_protocol.application.run_exit_service import RunExitCommand
        from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
        command = RunExitCommand(public_operation_key=RunEntryPublicOperationKey(value="fault.exit"), expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(owner,method,fail)
            with pytest.raises(type(sentinel)) as caught:
                await case.services.run_exit_service.exit(case.runtime.principal,session_id=sid,command=command)
            assert caught.value is sentinel
        assert await family_bytes(case) == before


@pytest.mark.parametrize("committed", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
async def test_e06_commit_acknowledgement_unknown_and_exact_retry(mysql_engine, monkeypatch, committed, cancel):
    from sqlalchemy.ext.asyncio import AsyncTransaction
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_exit_service import RunExitCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, _ = await public_admit(case, "unknown.admit", "difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client, sid)
        unit = SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine)
        service = replace(case.services.run_exit_service, uow_factory=lambda:unit)
        original = AsyncTransaction.commit
        sentinel = asyncio.CancelledError("lost commit") if cancel else RuntimeError("lost commit")
        async def commit(transaction):
            if transaction is unit._transaction:
                if committed: await original(transaction)
                raise sentinel
            return await original(transaction)
        command = RunExitCommand(public_operation_key=RunEntryPublicOperationKey(value="unknown.exit"), expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with monkeypatch.context() as patch:
            patch.setattr(AsyncTransaction,"commit",commit)
            with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError) as caught:
                await service.exit(case.runtime.principal,session_id=sid,command=command)
            if cancel: assert caught.value is sentinel and sentinel.commit_outcome_unknown
        assert unit._connection.closed
        state = await case.services.run_exit_service.status(case.runtime.principal,session_id=sid)
        assert state["lifecycle_status"] == ("terminated" if committed else "active")
        response = await case.services.run_exit_service.exit(case.runtime.principal,session_id=sid,command=command)
        assert response["lifecycle_status"] == "terminated"
        assert len((await family_bytes(case))["run_revisions"]) == 4


@pytest.mark.parametrize("cancel", [False, True])
async def test_e06_postcommit_cleanup_failure_preserves_uncertainty(mysql_engine, monkeypatch, cancel):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.run_exit_service import RunExitCommand
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    from tests.integration.test_mysql_native_run_migration import observe
    async with exit_case(mysql_engine, monkeypatch) as case:
        first, _ = await public_admit(case,"cleanup.admit","difficulty.silent-hunting-ground")
        sid = first["session_id"]
        ended, _ = await play_to_ending(case.client,sid)
        unit = SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine)
        service = replace(case.services.run_exit_service,uow_factory=lambda:unit)
        sentinel = asyncio.CancelledError("cleanup cancellation") if cancel else RuntimeError("cleanup failure")
        async def fail(): raise sentinel
        monkeypatch.setattr(unit,"_cleanup",fail)
        command = RunExitCommand(public_operation_key=RunEntryPublicOperationKey(value="cleanup.exit"),expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError):
            await service.exit(case.runtime.principal,session_id=sid,command=command)
        assert unit._connection.closed
        await observe(mysql_engine,unit.connection_id)
        before = await family_bytes(case)
        assert (await case.services.run_exit_service.status(case.runtime.principal,session_id=sid))["lifecycle_status"] == "terminated"
        assert (await case.services.run_exit_service.exit(case.runtime.principal,session_id=sid,command=command))["lifecycle_status"] == "terminated"
        assert await family_bytes(case) == before


@pytest.mark.parametrize("corruption", ["source", "binding_source", "receipt_hash", "ending", "memory", "world"])
async def test_e03_sql_terminal_reconstruction_rejects_corruption(mysql_engine, monkeypatch, corruption):
    import json
    async with exit_case(mysql_engine,monkeypatch) as case:
        first, _ = await public_admit(case,"corrupt.admit","difficulty.silent-hunting-ground")
        sid, rid = first["session_id"],first["run_context"]["run_id"]
        ended, _ = await play_to_ending(case.client,sid)
        result = await case.client.post(f"/v1/sessions/{sid}/run-exit",headers={"Idempotency-Key":"corrupt.exit"},
            json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
        assert result.status_code == 200,result.text
        async with case.factory.begin() as session:
            if corruption in ("source","binding_source"):
                row = await session.get(orm.RunCurrentRow,rid)
                setattr(row,"source_reference" if corruption == "source" else "binding_authority_source_ref","other.source")
            elif corruption == "receipt_hash":
                row = await session.scalar(sa.select(orm.RunMutationReceiptRow).where(orm.RunMutationReceiptRow.run_id==rid,orm.RunMutationReceiptRow.resulting_state_version==4))
                data = json.loads(row.operation_evidence_canonical)
                data["snapshot_sha256"] = "a"*64
                row.operation_evidence_canonical = json.dumps(data,sort_keys=True,separators=(",",":")).encode()
            elif corruption == "world":
                row = await session.get(orm.RunEntryWorldBindingRow,rid)
                row.scenario_id = "other.scenario"
            else:
                row = await session.get(orm.GameSnapshotRow,sid)
                data = json.loads(json.dumps(row.state_json))
                if corruption == "ending": data["scenario_runtime"]["ending_id"] = "other.ending"
                else: data["player_memory"]["scenario_records"] = []
                row.state_json = data
        before = await family_bytes(case)
        calls = case.services.turn_orchestrator.narrative_provider.calls
        for path in ("run-status","view"):
            response = await case.client.get(f"/v1/sessions/{sid}/{path}")
            assert response.status_code == 409 and response.json()["error"]["error_code"] == "SNAPSHOT_INVALID",response.text
        assert await family_bytes(case) == before
        assert case.services.turn_orchestrator.narrative_provider.calls == calls


@pytest.mark.parametrize("profile,ending", [("difficulty.open-expedition", "RESOLVED"), ("difficulty.silent-hunting-ground", "FAILED")])
async def test_e01_public_play_exit_reentry_and_e04_historical_replays(mysql_engine, monkeypatch, profile, ending):
    async with exit_case(mysql_engine, monkeypatch) as case:
        client = case.client
        eligible = await client.get("/v1/player-characters/eligible-for-run-entry")
        assert eligible.status_code == 200
        first, request = await public_admit(case, "exit.journey.first", profile)
        sid = first["session_id"]
        ended, actions = await play_to_ending(client, sid)
        assert ended["ending_status"] == ending
        request_statuses = []
        for action, _ in actions:
            status = await client.get(f"/v1/sessions/{sid}/requests/{action['client_request_id']}")
            assert status.status_code == 200 and status.json()["status"] == "COMMITTED", status.text
            request_statuses.append(status.json())
        before = await family_bytes(case)
        response = await client.get(f"/v1/sessions/{sid}/run-status")
        assert response.status_code == 200 and response.json()["can_exit"], response.text
        exit_body = dict(expected_run_state_version=3, expected_session_state_version=ended["metadata"]["state_version"])
        response = await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key":"exit.journey"})
        assert response.status_code == 200, response.text
        terminal = response.json()
        assert terminal["lifecycle_status"] == "terminated" and terminal["run_state_version"] == 4
        after = await family_bytes(case)
        for table in before:
            if table not in ("run_revisions", "run_current", "run_mutation_receipts"):
                assert after[table] == before[table], table
        assert all(row in after["run_revisions"] for row in before["run_revisions"])
        assert len(after["run_revisions"]) == 4 and len(after["run_mutation_receipts"]) == 3
        assert (await client.get(f"/v1/sessions/{sid}/view")).json() == ended
        eligible = (await client.get("/v1/player-characters/eligible-for-run-entry")).json()
        assert case.runtime.character_ids[0].value in [p["player_character_id"]["value"] for p in eligible["eligible_player_characters"]]
        second, _ = await public_admit(case, "exit.journey.second", profile)
        assert first["session_id"] != second["session_id"] and first["run_context"]["run_id"] != second["run_context"]["run_id"]
        fresh = (await client.get(f"/v1/sessions/{second['session_id']}/view")).json()
        first_action = {**actions[0][0], "decision_id":fresh["narrative_frame"]["decision_id"]}
        response = await client.post(f"/v1/sessions/{second['session_id']}/actions", json=first_action)
        assert response.status_code == 200 and response.json()["state_changed"], response.text
        stable = await family_bytes(case)
        calls = case.services.turn_orchestrator.narrative_provider.calls
        assert (await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key":"exit.journey"})).json() == terminal
        assert (await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key":"exit.journey.first"})).json() == first
        for (action, result), status in zip(actions, request_statuses, strict=True):
            assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == result
            assert (await client.get(f"/v1/sessions/{sid}/requests/{action['client_request_id']}")).json() == status
        assert await family_bytes(case) == stable
        assert case.services.turn_orchestrator.narrative_provider.calls == calls
        async with case.factory() as session:
            runs = (await session.scalars(sa.select(orm.RunCurrentRow).where(orm.RunCurrentRow.run_id.in_(case.scope.run_ids)))).all()
            assert len({r.continuous_story_line_id for r in runs}) == 2
            assert sum(r.active_player_character_id is not None for r in runs) == 1
