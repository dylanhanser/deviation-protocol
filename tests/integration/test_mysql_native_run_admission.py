from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

from deviation_protocol.api import main
from deviation_protocol.application.native_run_admission import NativeRunAdmissionResult, NativeRunAdmissionDecision
from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1
from deviation_protocol.domain import run_protocol_resolution as s2
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork, NATIVE_ADMISSION_LOCK
from deviation_protocol.infrastructure.run_protocol_binding_persistence import (
    _stored_binding_from_row, _reconstruct_native_binding, RunProtocolBindingStoredIntegrityError,
)
from tests.integration.test_mysql_run_entry_playthrough import _Scope, _build_runtime, _delete_scope, _scoped_family_predicates
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.unit.test_native_run_admission import command
from tests.unit.test_run_protocol_resolution import RESOLUTION_004

pytestmark = pytest.mark.integration
HEAD = "20260916_0007"


async def upgrade_head(engine):
    async with engine.connect() as connection:
        assert await connection.scalar(sa.text("SELECT DATABASE()")) == "deviation_protocol_test"
        assert str(await connection.scalar(sa.text("SELECT VERSION()"))).startswith("8.")
        await connection.rollback()
        def migrate(sync):
            context = MigrationContext.configure(sync, opts={"fn": lambda revisions, context: SCRIPT._upgrade_revs(HEAD, revisions)})
            with Operations.context(context), context.begin_transaction():
                context.run_migrations()
        await connection.run_sync(migrate)
        await connection.commit()


@asynccontextmanager
async def native_runtime(engine):
    await upgrade_head(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    scope = _Scope()
    try:
        runtime = await _build_runtime(factory, scope, character_count=2, block_first_provider_call=False)
        service = main.build_native_run_admission_service(engine=engine, run_service=runtime.services.run_service,
                                                         session_service=runtime.services.session_service)
        yield SimpleNamespace(runtime=runtime, service=service, scope=scope, factory=factory,
                              command=command(runtime.character_ids[0]), engine=engine)
    finally:
        async with factory.begin() as session:
            for model in (orm.RunEntryWorldBindingRow, orm.RunProtocolBindingRow):
                await session.execute(sa.delete(model).where(model.run_id.in_(scope.run_ids)))
        await _delete_scope(factory, scope)
        async with engine.connect() as connection:
            assert await connection.scalar(sa.text(f"SELECT IS_FREE_LOCK('{NATIVE_ADMISSION_LOCK}')")) == 1
            assert await connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == HEAD
            for model in (orm.RunEntryWorldBindingRow, orm.RunProtocolBindingRow):
                assert await connection.scalar(sa.select(sa.func.count()).select_from(model).where(model.run_id.in_(scope.run_ids))) == 0


async def family_bytes(case):
    result = {}
    predicates = _scoped_family_predicates(case.scope) + tuple(
        (model, model.run_id.in_(case.scope.run_ids)) for model in (orm.RunProtocolBindingRow, orm.RunEntryWorldBindingRow))
    async with case.engine.connect() as connection:
        for model, predicate in predicates:
            rows = (await connection.execute(sa.select(model.__table__).where(predicate))).all()
            result[model.__tablename__] = sorted(map(repr, rows))
    return result


async def test_production_composed_admission_replay_and_complete_detached_family(mysql_engine):
    async with native_runtime(mysql_engine) as case:
        before = await family_bytes(case)
        result = await case.service.enter(case.runtime.principal, command=case.command)
        assert type(result) is NativeRunAdmissionResult
        assert result.admitted_run_revision.value == 3
        assert result.resolved_protocol.final_values.conflict_intensity.value == 60
        first = await family_bytes(case)
        expected = {"run_revisions": 3, "run_current": 1, "run_creation_receipts": 1,
                    "run_mutation_receipts": 2, "run_session_participations": 1, "game_sessions": 1,
                    "domain_events": 1, "game_snapshots": 1, "run_protocol_bindings": 1, "run_entry_world_bindings": 1}
        for table, count in expected.items():
            assert len(first[table]) == count
        for table in before:
            if table.startswith("player_character"):
                assert first[table] == before[table]
        async with SqlAlchemyUnitOfWork(case.factory) as unit:
            classified = await unit.run_protocol_bindings.get_classified(run_id=result.run_id)
            assert type(classified) is NativeRunAdmissionV1
        case.service.run_id_issuer.issue = lambda: pytest.fail("replay issued an ID")
        assert await case.service.enter(case.runtime.principal, command=case.command) == result
        assert await family_bytes(case) == first
        # Progress the persisted Session using the ordinary repository/UoW, then replay original admission.
        async with SqlAlchemyUnitOfWork(case.factory) as unit:
            persisted = await unit.sessions.get_owned_for_update(result.session_id, case.runtime.principal.player_id)
            snapshot = await unit.sessions.get_latest_snapshot_for_update(result.session_id)
            await unit._session.execute(sa.update(orm.GameSessionRow).where(orm.GameSessionRow.session_id == result.session_id).values(state_version=1, turn_number=1))
            state = dict(snapshot.state)
            await unit._session.execute(sa.update(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id == result.session_id).values(state_version=1, state_json=state))
            await unit.commit()
        progressed = await family_bytes(case)
        assert await case.service.enter(case.runtime.principal, command=case.command) == result
        assert await family_bytes(case) == progressed


async def test_valid_ab_substitution_rejected_by_both_complete_boundaries(mysql_engine):
    async with native_runtime(mysql_engine) as case:
        result = await case.service.enter(case.runtime.principal, command=case.command)
        override = s2.RunProtocolObjectiveOverrideV1(parameter=s2.ObjectiveParameterName.CONFLICT_INTENSITY, value=s2.ObjectiveParameterValue(value=65))
        b = s2.resolve_run_protocol_objectives(case.command.protocol,
            s2.RunProtocolOverrideProposalV1(profile_ref=case.command.protocol.profile_ref, entries=(override,)),
            expected_epoch="run-protocol-resolution", expected_version=1)
        assert s2.encode_run_protocol_resolution_input_v1(b.resolution_input) == RESOLUTION_004
        original = await family_bytes(case)
        async with case.factory.begin() as session:
            values = {p.value: getattr(b.final_values, p.value).value for p in s2.RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER}
            values.update(resolution_input_canonical=RESOLUTION_004, resolution_fingerprint=bytes.fromhex(b.fingerprint.value))
            await session.execute(sa.update(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id == result.run_id.value).values(**values))
        substituted = await family_bytes(case)
        assert original["run_creation_receipts"] == substituted["run_creation_receipts"]
        async with SqlAlchemyUnitOfWork(case.factory) as unit:
            run = await unit.runs.get(result.run_id)
            row = await unit._session.scalar(sa.select(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id == result.run_id.value))
            individual = _reconstruct_native_binding(_stored_binding_from_row(row, unit._session), canonical_run=run, legacy_proof=None)
            assert individual.resolved_protocol == b
        for owned in (False, True):
            with pytest.raises(RunProtocolBindingStoredIntegrityError) as caught:
                if owned:
                    await case.service.enter(case.runtime.principal, command=case.command)
                else:
                    async with SqlAlchemyUnitOfWork(case.factory) as unit:
                        await unit.run_protocol_bindings.get_classified(run_id=result.run_id)
            assert type(caught.value) is RunProtocolBindingStoredIntegrityError and caught.value.__cause__ is None
            assert await family_bytes(case) == substituted


@pytest.mark.parametrize("field", ["expected_record_revision", "entry_world", "player_character_id", "overrides", "protocol"])
async def test_intent_conflicts_are_read_only(mysql_engine, field):
    from deviation_protocol.domain.player_character import PlayerCharacterRevision
    from deviation_protocol.domain.entry_world import EntryWorldVersion
    async with native_runtime(mysql_engine) as case:
        await case.service.enter(case.runtime.principal, command=case.command)
        changes = {
            "protocol": case.command.protocol.model_copy(update={"world_tone": type(case.command.protocol.world_tone)("grim")}),
            "expected_record_revision": PlayerCharacterRevision(value=2),
            "entry_world": case.command.entry_world.model_copy(update={"entry_world_version": EntryWorldVersion(value=2)}),
            "player_character_id": case.runtime.character_ids[1],
            "overrides": s2.RunProtocolOverrideProposalV1(profile_ref=case.command.protocol.profile_ref,
                entries=(s2.RunProtocolObjectiveOverrideV1(parameter=s2.ObjectiveParameterName.CONFLICT_INTENSITY, value=s2.ObjectiveParameterValue(value=60)),)),
        }
        before = await family_bytes(case)
        result = await case.service.enter(case.runtime.principal, command=case.command.model_copy(update={field: changes[field]}))
        assert result.code.value == "IDEMPOTENCY_CONFLICT"
        assert await family_bytes(case) == before


async def test_same_key_concurrency_has_one_family(mysql_engine):
    async with native_runtime(mysql_engine) as case:
        results = await asyncio.gather(*(case.service.enter(case.runtime.principal, command=case.command) for _ in range(2)))
        assert type(results[0]) is NativeRunAdmissionResult and results[0] == results[1]
        assert case.runtime.run_issuer.calls == 1
        assert len((await family_bytes(case))["run_revisions"]) == 3


@pytest.mark.parametrize("stage", ["creation", "binding", "session", "activation", "protocol", "world", "reconstruction", "commit"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_staging_faults_rollback_every_row(mysql_engine, stage, cancel):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    async with native_runtime(mysql_engine) as case:
        before = await family_bytes(case)
        primary = asyncio.CancelledError("injected") if cancel else RuntimeError("injected")
        class FaultUnit(SqlAlchemyNativeRunAdmissionUnitOfWork):
            async def __aenter__(self):
                await super().__aenter__()
                port, method = {"creation": (self.run_creation_receipts, "add_native_with_evidence"),
                    "binding": (self.runs, "append_revision"), "session": (self.sessions, "add_initial_session"),
                    "activation": (self.run_participations, "add"), "protocol": (self.run_protocol_bindings, "add_native"),
                    "world": (self.run_entry_world_bindings, "add_native"),
                    "reconstruction": (self.run_protocol_bindings, "get_classified_for_update"), "commit": (self, "commit")}[stage]
                original = getattr(port, method)
                async def fail(*args, **kwargs):
                    if stage != "commit":
                        await original(*args, **kwargs)
                    raise primary
                setattr(port, method, fail)
                return self
        case.service.uow_factory = lambda: FaultUnit(mysql_engine)
        with pytest.raises(type(primary)) as caught:
            await case.service.enter(case.runtime.principal, command=case.command)
        assert caught.value is primary
        assert await family_bytes(case) == before


@pytest.mark.parametrize("commit", [False, True])
async def test_same_physical_connection_owns_work_transaction_and_release(mysql_engine, commit):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    trace = []
    def sql(connection, cursor, statement, parameters, context, executemany):
        trace.append((connection.connection.driver_connection.thread_id(), statement))
    def end(connection):
        trace.append((connection.connection.driver_connection.thread_id(), "transaction-end"))
    sa.event.listen(mysql_engine.sync_engine, "before_cursor_execute", sql)
    sa.event.listen(mysql_engine.sync_engine, "commit" if commit else "rollback", end)
    try:
        async with SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine) as unit:
            owner = unit.connection_id
            assert await unit._session.scalar(sa.text("SELECT CONNECTION_ID()")) == owner
            assert await unit._session.scalar(sa.text(f"SELECT IS_USED_LOCK('{NATIVE_ADMISSION_LOCK}')")) == owner
            if commit:
                await unit.commit()
            else:
                await unit.rollback()
            assert unit._connection.closed is False
        assert all(identity == owner for identity, sql_text in trace)
        texts = [value for _, value in trace]
        assert texts.count(f"SELECT GET_LOCK('{NATIVE_ADMISSION_LOCK}', 30)") == 1
        assert texts.count(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')") == 1
        assert texts.index("transaction-end") < texts.index(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')")
    finally:
        sa.event.remove(mysql_engine.sync_engine, "before_cursor_execute", sql)
        sa.event.remove(mysql_engine.sync_engine, "commit" if commit else "rollback", end)
    async with mysql_engine.connect() as reused:
        assert await reused.scalar(sa.text(f"SELECT IS_FREE_LOCK('{NATIVE_ADMISSION_LOCK}')")) == 1


@pytest.mark.parametrize("committed", [False, True])
@pytest.mark.parametrize("cancel", [False, True])
async def test_commit_uncertainty_preserves_primary_and_explicit_retry(mysql_engine, committed, cancel, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncTransaction
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWorkFactory
    async with native_runtime(mysql_engine) as case:
        primary = asyncio.CancelledError("lost acknowledgement") if cancel else RuntimeError("lost acknowledgement")
        original = AsyncTransaction.commit
        async def uncertain(transaction):
            if committed:
                await original(transaction)
            raise primary
        with monkeypatch.context() as scoped:
            scoped.setattr(AsyncTransaction, "commit", uncertain)
            with pytest.raises(asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError) as caught:
                await case.service.enter(case.runtime.principal, command=case.command)
        if cancel:
            assert caught.value is primary and primary.commit_outcome_unknown is True
        else:
            assert caught.value.__cause__ is primary
        counts = await family_bytes(case)
        assert len(counts["run_revisions"]) == (3 if committed else 0)
        if not committed:
            case.runtime.run_issuer.calls = case.runtime.line_issuer.calls = case.runtime.session_generator.calls = 0
            case.service.session_service.seed_generator.calls = 0
        result = await case.service.enter(case.runtime.principal, command=case.command)
        assert type(result) is NativeRunAdmissionResult
        assert len((await family_bytes(case))["run_revisions"]) == 3


@pytest.mark.parametrize("phase", ["GET_LOCK", "RELEASE_LOCK"])
@pytest.mark.parametrize("mode", ["zero", "null", "invalid", "exception", "disconnect"])
async def test_native_uow_lock_failures_terminate_owner(mysql_engine, phase, mode, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncConnection
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.ports import NativeRunAdmissionLockError
    from tests.integration.test_mysql_run_protocol_binding import _kill
    from tests.integration.test_mysql_native_run_migration import observe
    unit = SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine)
    original = AsyncConnection.execute
    statements, failures = [], []
    sentinel = RuntimeError("statement sentinel")
    async def execute(connection, statement, *args, **kwargs):
        if connection is unit._connection:
            text = str(statement)
            statements.append(text)
            if phase in text:
                if mode == "exception":
                    failures.append(sentinel)
                    raise sentinel
                if mode == "disconnect":
                    await _kill(mysql_engine, unit.connection_id)
                elif mode == "zero" and phase == "GET_LOCK":
                    return SimpleNamespace(scalar_one=lambda: 0)
                try:
                    result = await original(connection, statement, *args, **kwargs)
                except Exception as error:
                    failures.append(error)
                    raise
                if mode in ("zero", "null", "invalid"):
                    return SimpleNamespace(scalar_one=lambda: {"zero": 0, "null": None, "invalid": True}[mode])
                return result
        return await original(connection, statement, *args, **kwargs)
    monkeypatch.setattr(AsyncConnection, "execute", execute)
    with pytest.raises(NativeRunAdmissionLockError) as caught:
        async with unit:
            assert phase == "RELEASE_LOCK"
    code = {"zero": "ACQUIRE_TIMEOUT" if phase == "GET_LOCK" else "RELEASE_NOT_OWNER",
            "null": ("ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_") + "NULL",
            "invalid": ("ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_") + "INVALID_RESULT",
            "exception": ("ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_") + "STATEMENT_FAILED",
            "disconnect": ("ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_") + "CONNECTION_LOST_PENDING"}[mode]
    assert str(caught.value) == code
    assert caught.value.__cause__ is (failures[0] if failures else None)
    if phase == "GET_LOCK":
        assert not any("RELEASE_LOCK" in sql for sql in statements)
    await observe(mysql_engine, None if mode == "zero" and phase == "GET_LOCK" else unit.connection_id)


async def test_repeated_cancellation_waits_for_rollback_and_release(mysql_engine):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from tests.integration.test_mysql_native_run_migration import observe
    started, finish, body = (asyncio.Event() for _ in range(3))
    primary = asyncio.CancelledError("original body cancellation")
    class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
        async def rollback(self):
            started.set()
            await finish.wait()
            await super().rollback()
    unit = Unit(mysql_engine)
    async def work():
        async with unit:
            body.set()
            raise primary
    task = asyncio.create_task(work())
    await asyncio.wait_for(started.wait(), 5)
    task.cancel("second")
    await asyncio.sleep(0)
    task.cancel("third")
    finish.set()
    with pytest.raises(asyncio.CancelledError) as caught:
        await task
    assert caught.value is primary
    assert unit._connection.closed
    await observe(mysql_engine)


async def test_cleanup_deadline_discards_and_retains_primary(mysql_engine):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from tests.integration.test_mysql_native_run_migration import observe
    primary = RuntimeError("body sentinel")
    completed = asyncio.Event()
    class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
        async def rollback(self):
            try:
                await asyncio.Event().wait()
            finally:
                completed.set()
    unit = Unit(mysql_engine)
    with pytest.raises(RuntimeError) as caught:
        async with unit:
            raise primary
    assert caught.value is primary and isinstance(primary.cleanup_error, TimeoutError)
    assert completed.is_set() and unit._connection.closed
    await observe(mysql_engine, unit.connection_id)


async def test_normal_default_services_native_entry_is_usable(mysql_engine, monkeypatch):
    from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
    async with native_runtime(mysql_engine) as case:
        monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
        services = main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
            authentication_scheme=case.runtime.principal.authentication_scheme,
            player_id=case.runtime.principal.player_id, controller_id=case.runtime.resolver.binding.value,
        ),))
        result = await services.native_run_admission_service.enter(case.runtime.principal, command=case.command)
        assert type(result) is NativeRunAdmissionResult
        case.scope.run_ids.add(result.run_id.value)
        case.scope.session_ids.add(result.session_id)
        assert await services.native_run_admission_service.enter(case.runtime.principal, command=case.command) == result
        async with SqlAlchemyUnitOfWork(case.factory) as unit:
            admitted = await unit.run_protocol_bindings.get_classified(run_id=result.run_id)
            assert admitted.canonical_run.creation_provenance.source_reference.value == "source.production-run"


@pytest.mark.parametrize("same_key", [False, True])
async def test_native_concurrent_conflicting_intent_or_occupancy(mysql_engine, same_key):
    async with native_runtime(mysql_engine) as case:
        other = command(case.runtime.character_ids[1] if same_key else case.runtime.character_ids[0],
                        key=case.command.public_operation_key.value if same_key else "other.native.key")
        results = await asyncio.gather(case.service.enter(case.runtime.principal, command=case.command),
                                       case.service.enter(case.runtime.principal, command=other))
        assert sum(type(result) is NativeRunAdmissionResult for result in results) == 1
        decision = next(result for result in results if type(result) is NativeRunAdmissionDecision)
        assert decision.code.value == ("IDEMPOTENCY_CONFLICT" if same_key else "PLAYER_CHARACTER_NOT_ELIGIBLE")
        assert len((await family_bytes(case))["run_revisions"]) == 3


@pytest.mark.parametrize("case_name,expected", [("stale", "PLAYER_CHARACTER_STALE"), ("world", "INVALID_ENTRY_WORLD"),
    ("protocol", "INVALID_PROTOCOL"), ("unauthorized", "AUTHORIZATION_FAILED")])
async def test_authority_and_new_admission_rejections_write_nothing(mysql_engine, case_name, expected):
    from deviation_protocol.domain.player_character import PlayerCharacterRevision
    from deviation_protocol.domain.entry_world import EntryWorldVersion
    async with native_runtime(mysql_engine) as case:
        proposed = case.command
        principal = case.runtime.principal
        if case_name == "stale":
            proposed = proposed.model_copy(update={"expected_record_revision": PlayerCharacterRevision(value=2)})
        elif case_name == "world":
            proposed = proposed.model_copy(update={"entry_world": proposed.entry_world.model_copy(update={"entry_world_version": EntryWorldVersion(value=2)})})
        elif case_name == "protocol":
            proposed = proposed.model_copy(update={"overrides": s2.RunProtocolOverrideProposalV1(profile_ref=proposed.protocol.profile_ref,
                entries=(s2.RunProtocolObjectiveOverrideV1(parameter=s2.ObjectiveParameterName.CONFLICT_INTENSITY, value=s2.ObjectiveParameterValue(value=0)),))})
        else:
            principal = principal.model_copy(update={"player_id": "different.player"})
        before = await family_bytes(case)
        assert (await case.service.enter(principal, command=proposed)).code.value == expected
        assert await family_bytes(case) == before
        assert case.runtime.run_issuer.calls == 0


async def test_native_and_legacy_competition_share_character_exclusion(mysql_engine):
    from deviation_protocol.application.run_entry_service import RunEntryCommand
    async with native_runtime(mysql_engine) as case:
        legacy_command = RunEntryCommand(public_operation_key=case.command.public_operation_key,
            player_character_id=case.command.player_character_id, expected_record_revision=case.command.expected_record_revision,
            scenario_id="death_certificate")
        results = await asyncio.gather(case.service.enter(case.runtime.principal, command=case.command),
            case.runtime.services.run_entry_service.enter(case.runtime.principal, command=legacy_command))
        assert sum(hasattr(result, "run_id") for result in results) == 1
        assert next(result for result in results if hasattr(result, "code")).code.value == "PLAYER_CHARACTER_NOT_ELIGIBLE"
        assert len((await family_bytes(case))["run_revisions"]) == 3


@pytest.mark.parametrize("table", ["run_current", "run_revisions", "run_creation_receipts", "run_mutation_receipts",
    "run_session_participations", "run_protocol_bindings", "run_entry_world_bindings", "game_sessions", "game_snapshots", "domain_events"])
async def test_missing_native_family_rows_never_repair_or_return_component(mysql_engine, table):
    async with native_runtime(mysql_engine) as case:
        result = await case.service.enter(case.runtime.principal, command=case.command)
        model = orm.Base.metadata.tables[table]
        column = model.c.result_run_id if table == "run_creation_receipts" else model.c.session_id if table in ("game_sessions", "game_snapshots", "domain_events") else model.c.run_id
        identity = result.session_id if column.name == "session_id" else result.run_id.value
        async with mysql_engine.connect() as connection:
            await connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
            try:
                await connection.execute(sa.delete(model).where(column == identity))
                await connection.commit()
            finally:
                await connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
                await connection.commit()
        before = await family_bytes(case)
        with pytest.raises(RunProtocolBindingStoredIntegrityError):
            async with SqlAlchemyUnitOfWork(case.factory) as unit:
                await unit.run_protocol_bindings.get_classified(run_id=result.run_id)
        assert await family_bytes(case) == before


async def test_acknowledged_commit_release_failure_withholds_success_then_replays(mysql_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncConnection
    from deviation_protocol.application.ports import NativeRunAdmissionLockError
    async with native_runtime(mysql_engine) as case:
        original = AsyncConnection.execute
        async def release_fault(connection, statement, *args, **kwargs):
            result = await original(connection, statement, *args, **kwargs)
            if "RELEASE_LOCK" in str(statement):
                return SimpleNamespace(scalar_one=lambda: 0)
            return result
        with monkeypatch.context() as scoped:
            scoped.setattr(AsyncConnection, "execute", release_fault)
            with pytest.raises(NativeRunAdmissionLockError, match="RELEASE_NOT_OWNER"):
                await case.service.enter(case.runtime.principal, command=case.command)
        before = await family_bytes(case)
        assert len(before["run_revisions"]) == 3
        result = await case.service.enter(case.runtime.principal, command=case.command)
        assert type(result) is NativeRunAdmissionResult
        assert await family_bytes(case) == before


async def test_native_actual_lock_timeout_and_pending_cancellation(mysql_engine):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.ports import NativeRunAdmissionLockError
    from tests.integration.test_mysql_native_run_migration import observe
    async with mysql_engine.connect() as holder:
        assert await holder.scalar(sa.text(f"SELECT GET_LOCK('{NATIVE_ADMISSION_LOCK}', 30)")) == 1
        try:
            unit = SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine)
            start = asyncio.get_running_loop().time()
            with pytest.raises(NativeRunAdmissionLockError, match="ACQUIRE_TIMEOUT"):
                async with unit:
                    pytest.fail("timeout entered body")
            assert asyncio.get_running_loop().time() - start >= 29
            unit = SqlAlchemyNativeRunAdmissionUnitOfWork(mysql_engine)
            task = asyncio.create_task(unit.__aenter__())
            async with mysql_engine.connect() as observer:
                async with asyncio.timeout(5):
                    while True:
                        if unit.connection_id:
                            state = await observer.scalar(sa.text("SELECT STATE FROM information_schema.PROCESSLIST WHERE ID=:id"), {"id": unit.connection_id})
                            if state == "User lock":
                                break
                        await asyncio.sleep(0.01)
            task.cancel("pending acquire")
            with pytest.raises(asyncio.CancelledError):
                await task
            assert unit._connection.closed
        finally:
            assert await holder.scalar(sa.text(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')")) == 1
            await holder.rollback()
    await observe(mysql_engine, unit.connection_id)


@pytest.mark.parametrize("stage", ["protocol", "world", "receipt", "participation", "cas"])
async def test_real_duplicate_flush_and_cas_loss_reconcile_only_after_rollback(mysql_engine, stage):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    async with native_runtime(mysql_engine) as case:
        before = await family_bytes(case)
        units, failures = [], []
        class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
            async def __aenter__(self):
                await super().__aenter__()
                units.append(self)
                if len(units) == 1:
                    port, method = {"protocol": (self.run_protocol_bindings, "add_native"),
                        "world": (self.run_entry_world_bindings, "add_native"),
                        "receipt": (self.run_creation_receipts, "add_native_with_evidence"),
                        "participation": (self.run_participations, "add"),
                        "cas": (self.runs, "compare_and_swap_current")}[stage]
                    original = getattr(port, method)
                    async def collide(*args, **kwargs):
                        await original(*args, **kwargs)
                        if stage == "cas":
                            return False
                        try:
                            await original(*args, **kwargs)
                        except Exception as error:
                            failures.append(error)
                            raise
                    setattr(port, method, collide)
                else:
                    assert units[0]._connection.closed
                return self
        case.service.uow_factory = lambda: Unit(mysql_engine)
        result = await case.service.enter(case.runtime.principal, command=case.command)
        assert result.code.value == "RUN_ENTRY_CONFLICT"
        assert len(units) == 2 and case.runtime.run_issuer.calls == 1
        assert await family_bytes(case) == before
        if stage != "cas":
            assert failures[0].__cause__.orig.args[0] == 1062


async def test_generated_id_collision_is_not_proof_of_idempotent_winner(mysql_engine):
    from deviation_protocol.application.run_entry_service import RunEntryCommand
    async with native_runtime(mysql_engine) as case:
        legacy = RunEntryCommand(public_operation_key=case.command.public_operation_key,
            player_character_id=case.command.player_character_id, expected_record_revision=case.command.expected_record_revision,
            scenario_id="death_certificate")
        await case.runtime.services.run_entry_service.enter(case.runtime.principal, command=legacy)
        before = await family_bytes(case)
        case.runtime.run_issuer.calls = case.runtime.line_issuer.calls = case.runtime.session_generator.calls = 0
        case.service.session_service.seed_generator.calls = 0
        result = await case.service.enter(case.runtime.principal, command=command(case.runtime.character_ids[1]))
        assert result.code.value == "RUN_ENTRY_CONFLICT"
        assert await family_bytes(case) == before


@pytest.mark.parametrize("check,code", [(2, "ACQUIRE_CONNECTION_LOST_BEFORE"), (3, "ACQUIRE_CONNECTION_LOST_AFTER"),
    (4, "RELEASE_CONNECTION_LOST_BEFORE"), (5, "RELEASE_CONNECTION_LOST_PENDING")])
async def test_native_state_only_connection_loss_has_no_invented_cause(mysql_engine, check, code, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncConnection
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from deviation_protocol.application.ports import NativeRunAdmissionLockError
    from tests.integration.test_mysql_native_run_migration import observe
    class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
        checks = 0
        def _lost(self, error=None):
            self.checks += 1
            return self.checks == check or super()._lost(error)
    unit = Unit(mysql_engine)
    original = AsyncConnection.execute
    statements = []
    async def execute(connection, statement, *args, **kwargs):
        if connection is unit._connection:
            statements.append(str(statement))
        return await original(connection, statement, *args, **kwargs)
    monkeypatch.setattr(AsyncConnection, "execute", execute)
    with pytest.raises(NativeRunAdmissionLockError) as caught:
        async with unit:
            assert check >= 4
    assert str(caught.value) == code and caught.value.__cause__ is None
    assert sum("RELEASE_LOCK" in sql for sql in statements) == (1 if check == 5 else 0)
    await observe(mysql_engine, unit.connection_id)


async def test_native_rollback_and_invalidation_failure_preserve_primary_and_discard(mysql_engine, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncConnection
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    from tests.integration.test_mysql_native_run_migration import observe
    primary, rollback_error, discard_error = (RuntimeError(name) for name in ("body", "rollback", "invalidation"))
    class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
        async def rollback(self):
            raise rollback_error
    unit = Unit(mysql_engine)
    original = AsyncConnection.invalidate
    async def invalidate(connection, *args, **kwargs):
        if connection is unit._connection:
            raise discard_error
        return await original(connection, *args, **kwargs)
    monkeypatch.setattr(AsyncConnection, "invalidate", invalidate)
    with pytest.raises(RuntimeError) as caught:
        async with unit:
            raise primary
    assert caught.value is primary and primary.cleanup_error is rollback_error
    assert rollback_error.close_error is discard_error
    assert unit._connection.closed
    await observe(mysql_engine, unit.connection_id)


@pytest.mark.parametrize("field", ["scenario_id", "entry_world_version", "created_at", "session_player"])
async def test_corrupted_native_associations_reject_at_both_boundaries_without_repair(mysql_engine, field):
    from datetime import timedelta
    async with native_runtime(mysql_engine) as case:
        result = await case.service.enter(case.runtime.principal, command=case.command)
        async with case.factory.begin() as session:
            if field == "session_player":
                await session.execute(sa.update(orm.GameSessionRow).where(orm.GameSessionRow.session_id == result.session_id).values(player_id="wrong.player"))
            else:
                row = await session.scalar(sa.select(orm.RunEntryWorldBindingRow).where(orm.RunEntryWorldBindingRow.run_id == result.run_id.value))
                value = {"scenario_id": "wrong.scenario", "entry_world_version": 2, "created_at": row.created_at + timedelta(seconds=1)}[field]
                await session.execute(sa.update(orm.RunEntryWorldBindingRow).where(orm.RunEntryWorldBindingRow.run_id == result.run_id.value).values(**{field: value}))
        before = await family_bytes(case)
        for owned in (False, True):
            with pytest.raises(RunProtocolBindingStoredIntegrityError) as caught:
                if owned:
                    await case.service.enter(case.runtime.principal, command=case.command)
                else:
                    async with SqlAlchemyUnitOfWork(case.factory) as unit:
                        await unit.run_protocol_bindings.get_classified(run_id=result.run_id)
            assert type(caught.value) is RunProtocolBindingStoredIntegrityError
            assert (caught.value.__cause__ is not None) == (field == "entry_world_version")
            assert await family_bytes(case) == before


async def test_reordered_override_replay_does_not_resolve_defaults_or_prepare(mysql_engine, monkeypatch):
    async with native_runtime(mysql_engine) as case:
        entries = tuple(s2.RunProtocolObjectiveOverrideV1(parameter=parameter, value=s2.ObjectiveParameterValue(value=value))
            for parameter, value in ((s2.ObjectiveParameterName.CONFLICT_INTENSITY, 65), (s2.ObjectiveParameterName.RESOURCE_PRESSURE, 50)))
        proposed = case.command.model_copy(update={"overrides": s2.RunProtocolOverrideProposalV1(profile_ref=case.command.protocol.profile_ref, entries=entries)})
        result = await case.service.enter(case.runtime.principal, command=proposed)
        before = await family_bytes(case)
        def forbidden(*args, **kwargs):
            pytest.fail("replay regenerated admission state")
        # S3 reconstructs the retained versioned objectives; the admission coordinator
        # must not call the fresh-admission resolution/defaulting entry point.
        from deviation_protocol.application import native_run_admission as native
        real_s2 = native.s2
        proxy = SimpleNamespace(**{name: getattr(real_s2, name) for name in dir(real_s2) if not name.startswith("__")})
        proxy.resolve_run_protocol_objectives = forbidden
        monkeypatch.setattr(native, "s2", proxy)
        monkeypatch.setattr(type(case.service.session_service), "prepare_run_entry_initialization", forbidden)
        replay = proposed.model_copy(update={"overrides": s2.RunProtocolOverrideProposalV1(profile_ref=proposed.protocol.profile_ref, entries=tuple(reversed(entries)))})
        assert await case.service.enter(case.runtime.principal, command=replay) == result
        assert await family_bytes(case) == before


@pytest.mark.parametrize("commit", [False, True])
async def test_actual_admission_inserts_share_lock_and_transaction_connection(mysql_engine, commit):
    from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork
    async with native_runtime(mysql_engine) as case:
        units, trace = [], []
        primary = RuntimeError("pre-commit rollback")
        class Unit(SqlAlchemyNativeRunAdmissionUnitOfWork):
            async def __aenter__(self):
                await super().__aenter__()
                units.append(self)
                return self
            async def commit(self):
                if not commit:
                    raise primary
                await super().commit()
        case.service.uow_factory = lambda: Unit(mysql_engine)
        def sql(connection, cursor, statement, parameters, context, executemany):
            trace.append((connection.connection.driver_connection.thread_id(), statement))
        def end(connection):
            trace.append((connection.connection.driver_connection.thread_id(), "transaction-end"))
        sa.event.listen(mysql_engine.sync_engine, "before_cursor_execute", sql)
        sa.event.listen(mysql_engine.sync_engine, "commit" if commit else "rollback", end)
        try:
            if commit:
                assert type(await case.service.enter(case.runtime.principal, command=case.command)) is NativeRunAdmissionResult
            else:
                with pytest.raises(RuntimeError) as caught:
                    await case.service.enter(case.runtime.principal, command=case.command)
                assert caught.value is primary
        finally:
            sa.event.remove(mysql_engine.sync_engine, "before_cursor_execute", sql)
            sa.event.remove(mysql_engine.sync_engine, "commit" if commit else "rollback", end)
        assert len(units) == 1 and all(identity == units[0].connection_id for identity, _ in trace)
        statements = [sql_text for _, sql_text in trace]
        for table in ("run_revisions", "run_current", "run_creation_receipts", "run_mutation_receipts",
                      "run_session_participations", "game_sessions", "domain_events", "game_snapshots",
                      "run_protocol_bindings", "run_entry_world_bindings"):
            assert any(sql_text.startswith("INSERT INTO " + table + " ") for sql_text in statements)
        acquire = statements.index(f"SELECT GET_LOCK('{NATIVE_ADMISSION_LOCK}', 30)")
        release = statements.index(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')")
        assert acquire < next(i for i, sql_text in enumerate(statements) if sql_text.startswith("INSERT INTO"))
        assert statements.index("transaction-end") < release
        assert len((await family_bytes(case))["run_revisions"]) == (3 if commit else 0)
