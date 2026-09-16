from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy.util import await_only

from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyNativeRunAdmissionUnitOfWork, NATIVE_ADMISSION_LOCK as LOCK
from tests.integration.test_mysql_run_protocol_binding import SCRIPT, _ConnectionView as _S3ConnectionView, _kill
from tests.integration.test_mysql_native_run_admission import native_runtime, upgrade_head, family_bytes

pytestmark = pytest.mark.integration
MIGRATION = SCRIPT.get_revision("20260916_0007").module
TABLE = "run_entry_world_bindings"
REFUSAL = "Refusing to downgrade P3.3-S4: native admission data exists; recovery must be forward-only"
STEPS = ("WORLD_PROBE", "EVIDENCE_PROBE", "DDL_PROTOCOL_FK", "DDL_REVISION_FK", "DDL_INDEX", "DDL_TABLE")


class _ConnectionView(_S3ConnectionView):
    @property
    def connection(self):
        return self.sync.connection


async def migrate(connection, direction, configure=None):
    def execute(sync):
        operations = Operations(MigrationContext.configure(sync))
        trace = []
        proxy = SimpleNamespace(get_bind=lambda: sync, create_table=operations.create_table, create_index=operations.create_index)
        for name in ("drop_constraint", "drop_index", "drop_table"):
            original = getattr(operations, name)
            def delegate(*args, _original=original, _name=name, **kwargs):
                trace.append((_name, args[0]))
                return _original(*args, **kwargs)
            setattr(proxy, name, delegate)
        if configure:
            configure(sync, proxy, trace)
        previous = MIGRATION.op
        MIGRATION.op = proxy
        try:
            getattr(MIGRATION, direction)()
        finally:
            MIGRATION.op = previous
        return trace
    return await connection.run_sync(execute)


async def observe(engine, owner=None):
    async with engine.connect() as connection:
        async with asyncio.timeout(5):
            while await connection.scalar(sa.text(f"SELECT IS_USED_LOCK('{LOCK}')")) is not None:
                await asyncio.sleep(0.01)
        assert await connection.scalar(sa.text(f"SELECT IS_FREE_LOCK('{LOCK}')")) == 1
        if owner is not None:
            assert await connection.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=:id"), {"id": owner}) == 0


async def restore_empty_world(engine):
    # Test-owned schema restoration only after checking that no admitted data exists.
    async with engine.connect() as connection:
        assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_creation_receipts WHERE LEFT(operation_evidence_canonical,1)=X'8A'")) == 0
        present = await connection.run_sync(lambda sync: sa.inspect(sync).has_table(TABLE))
        if present:
            assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_entry_world_bindings")) == 0
            await connection.execute(sa.text("DROP TABLE run_entry_world_bindings"))
        await migrate(connection, "upgrade")
        await connection.run_sync(lambda sync: MigrationContext.configure(sync).stamp(SCRIPT, "20260916_0007"))
        await connection.commit()
    await observe(engine)


@pytest.fixture
async def migration_db(mysql_engine):
    await upgrade_head(mysql_engine)
    try:
        yield mysql_engine
    finally:
        await restore_empty_world(mysql_engine)


async def test_007_schema_parity_and_old_row_preservation(migration_db):
    from deviation_protocol.application.run_entry_service import RunEntryCommand
    async with native_runtime(migration_db) as case:
        await case.runtime.services.run_entry_service.enter(case.runtime.principal, command=RunEntryCommand(
            public_operation_key=case.command.public_operation_key, player_character_id=case.command.player_character_id,
            expected_record_revision=case.command.expected_record_revision, scenario_id="death_certificate"))
        before = await family_bytes(case)
        assert len(before["run_revisions"]) == 3 and len(before["game_sessions"]) == 1
        async with migration_db.connect() as connection:
            trace = await migrate(connection, "downgrade")
            assert trace == [("drop_constraint", "fk_run_entry_world_bindings_protocol"),
                             ("drop_constraint", "fk_run_entry_world_bindings_revision"),
                             ("drop_index", "ix_run_entry_world_bindings_revision"), ("drop_table", TABLE)]
            captured = {}
            def capture(sync, proxy, trace):
                original = proxy.create_table
                def create(*args, **kwargs):
                    table = original(*args, **kwargs)
                    captured["table"] = table
                    return table
                proxy.create_table = create
            await migrate(connection, "upgrade", capture)
            await connection.commit()
            def signature(table):
                return [(c.name, str(c.type.compile(dialect=connection.dialect)), c.nullable, c.default, c.server_default) for c in table.columns]
            assert signature(captured["table"]) == signature(orm.RunEntryWorldBindingRow.__table__)
            assert {c.name: str(c.sqltext) for c in captured["table"].constraints if isinstance(c, sa.CheckConstraint)} == {
                c.name: str(c.sqltext) for c in orm.RunEntryWorldBindingRow.__table__.constraints if isinstance(c, sa.CheckConstraint)}
            def inspect(sync):
                inspector = sa.inspect(sync)
                assert {v["name"] for v in inspector.get_check_constraints(TABLE)} == {"ck_run_entry_world_bindings_identity", "ck_run_entry_world_bindings_versions", "ck_run_entry_world_bindings_epoch"}
                assert inspector.get_pk_constraint(TABLE)["constrained_columns"] == ["run_id"]
                fks = inspector.get_foreign_keys(TABLE)
                assert {fk["name"] for fk in fks} == {"fk_run_entry_world_bindings_protocol", "fk_run_entry_world_bindings_revision"}
                assert all(fk["options"] == {"onupdate": "RESTRICT", "ondelete": "RESTRICT"} for fk in fks)
                assert {fk["name"]: (fk["constrained_columns"], fk["referred_table"], fk["referred_columns"]) for fk in fks} == {
                    "fk_run_entry_world_bindings_protocol": (["run_id"], "run_protocol_bindings", ["run_id"]),
                    "fk_run_entry_world_bindings_revision": (["run_id", "continuous_story_line_id", "bound_state_version"],
                        "run_revisions", ["run_id", "continuous_story_line_id", "state_version"])}
                assert inspector.get_indexes(TABLE)[0]["column_names"] == ["run_id", "continuous_story_line_id", "bound_state_version"]
            await connection.run_sync(inspect)
            physical = (await connection.execute(sa.text("SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,CHARACTER_SET_NAME,COLLATION_NAME,DATETIME_PRECISION,EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='run_entry_world_bindings' ORDER BY ORDINAL_POSITION"))).all()
            assert [(row[0], row[1]) for row in physical] == [
                ("run_id", "varchar(128)"), ("continuous_story_line_id", "varchar(128)"),
                ("bound_state_version", "bigint"), ("binding_epoch", "varchar(64)"),
                ("binding_record_version", "bigint"), ("entry_world_id", "varchar(128)"),
                ("entry_world_version", "bigint"), ("scenario_id", "varchar(128)"),
                ("scenario_content_version", "varchar(32)"), ("default_character_definition_id", "varchar(128)"),
                ("created_at", "datetime(6)")]
            for column, row in zip(orm.RunEntryWorldBindingRow.__table__.columns, physical, strict=True):
                assert row[0] == column.name and row[2] == "NO" and row[3] is None and row[7] == ""
                if isinstance(column.type, sa.String):
                    assert row[4:6] == ("ascii", "ascii_bin")
                elif column.name == "created_at":
                    assert row[1] == "datetime(6)" and row[6] == 6
                else:
                    assert row[1] == "bigint"
            assert tuple((await connection.execute(sa.text("SELECT ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='run_entry_world_bindings'"))).one()) == ("InnoDB", "utf8mb4_bin")
        assert await family_bytes(case) == before


@pytest.mark.parametrize("missing_world", [False, True])
async def test_007_refuses_native_evidence_without_deleting_data(migration_db, missing_world):
    async with native_runtime(migration_db) as case:
        result = await case.service.enter(case.runtime.principal, command=case.command)
        if missing_world:
            async with case.factory.begin() as session:
                await session.execute(sa.delete(orm.RunEntryWorldBindingRow).where(orm.RunEntryWorldBindingRow.run_id == result.run_id.value))
                await session.execute(sa.update(orm.RunCreationReceiptRow).where(orm.RunCreationReceiptRow.result_run_id == result.run_id.value).values(operation_evidence_canonical=b"\x8a malformed"))
        before = await family_bytes(case)
        async with migration_db.connect() as connection:
            captured = []
            with pytest.raises(RuntimeError) as caught:
                await migrate(connection, "downgrade", lambda sync, proxy, trace: captured.append(trace))
            assert type(caught.value) is RuntimeError and str(caught.value) == REFUSAL and caught.value.__cause__ is None
            assert captured == [[]]
            await connection.rollback()
            old = SCRIPT.get_revision("20260828_0006").module
            original = old.op
            old.op = Operations(MigrationContext.configure(connection.sync_connection))
            try:
                with pytest.raises(RuntimeError, match="Refusing to downgrade P3.3-S3"):
                    await connection.run_sync(lambda sync: old.downgrade())
            finally:
                old.op = original
            await connection.rollback()
        assert await family_bytes(case) == before


@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize("mode", ["state", "disconnect", "exception"])
async def test_007_issued_and_unissued_body_failure_distinctions(migration_db, step, mode, monkeypatch):
    captured = {}
    index = STEPS.index(step)
    async with migration_db.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, migration_db, owner)
            proxy.get_bind = lambda: view
            captured.update(view=view, trace=trace)
            if mode == "state":
                view.state_check = 4 + index
            elif index < 2:
                view.sql_fault = ("FROM run_entry_world_bindings" if index == 0 else "FROM run_creation_receipts", mode)
            else:
                name = "drop_constraint" if index < 4 else "drop_index" if index == 4 else "drop_table"
                original = getattr(proxy, name)
                def fail(*args, **kwargs):
                    target = index != 3 or args[0] == "fk_run_entry_world_bindings_revision"
                    if target:
                        if mode == "exception":
                            trace.append((name, args[0]))
                            raise view.failure
                        view.kill(invalidate=False)
                    try:
                        return original(*args, **kwargs)
                    except BaseException as error:
                        view.observed = error
                        raise
                setattr(proxy, name, fail)
        with pytest.raises(Exception) as caught:
            await migrate(connection, "downgrade", configure)
        view = captured["view"]
        if mode == "exception":
            assert caught.value is view.failure and caught.value.cleanup_error is None
        else:
            assert type(caught.value) is RuntimeError
            assert str(caught.value) == "P3.3-S4 downgrade BODY_CONNECTION_LOST_" + ("BEFORE_" if mode == "state" else "") + step
            assert caught.value.__cause__ is (None if mode == "state" else view.observed)
            assert not any("RELEASE_LOCK" in sql for sql in view.sql)
        assert len(captured["trace"]) == max(0, index - 2 + (mode != "state"))
        if not connection.closed:
            await connection.rollback()
    await observe(migration_db, owner if mode != "exception" else None)


@pytest.mark.parametrize("phase", ["GET_LOCK", "RELEASE_LOCK"])
@pytest.mark.parametrize("mode", ["zero", "null", "invalid", "exception", "disconnect", "discard"])
async def test_007_lock_scalar_statement_and_discard_failures(migration_db, phase, mode):
    captured = {}
    async with migration_db.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, migration_db, owner)
            captured.update(view=view, trace=trace)
            proxy.get_bind = lambda: view
            if mode in ("exception", "disconnect"):
                view.sql_fault = (phase, mode)
            else:
                view.result_override = (phase, {"zero": 0, "null": None, "invalid": True, "discard": None}[mode])
                view.close_failure = mode == "discard"
            if phase == "GET_LOCK" and mode == "zero":
                # The real timeout does not own the lock; undo only this test's injected acquisition.
                execute = view.execute
                def fake_timeout(statement, *args, **kwargs):
                    if "GET_LOCK" in str(statement):
                        view.sql.append(str(statement))
                        return SimpleNamespace(scalar_one=lambda: 0)
                    return execute(statement, *args, **kwargs)
                view.execute = fake_timeout
        with pytest.raises(RuntimeError) as caught:
            await migrate(connection, "downgrade", configure)
        prefix = "ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_"
        code = {"zero": "TIMEOUT" if phase == "GET_LOCK" else "NOT_OWNER", "null": "NULL", "invalid": "INVALID_RESULT",
                "exception": "STATEMENT_FAILED", "disconnect": "CONNECTION_LOST_PENDING", "discard": "NULL"}[mode]
        assert str(caught.value) == "P3.3-S4 downgrade " + prefix + code
        assert caught.value.__cause__ is captured["view"].observed
        if mode == "discard":
            assert caught.value.close_error is captured["view"].close_error
        if phase == "GET_LOCK":
            assert captured["trace"] == []
        if not connection.closed:
            await connection.rollback()
    await observe(migration_db, None if phase == "GET_LOCK" and mode == "zero" else owner)


@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("different_lock", [False, True])
async def test_downgrade_excludes_real_writer_with_discriminating_negative_control(migration_db, fail, different_lock, monkeypatch):
    from deviation_protocol.infrastructure import unit_of_work as uow_module
    async with native_runtime(migration_db) as case:
        protected, allow_ddl, closed, acquired = (asyncio.Event() for _ in range(4))
        units = []
        primary = RuntimeError("DDL sentinel")
        if different_lock:
            monkeypatch.setattr(uow_module, "NATIVE_ADMISSION_LOCK", "deviation_protocol:s4:negative")
        class Writer(SqlAlchemyNativeRunAdmissionUnitOfWork):
            async def __aenter__(self):
                units.append(self)
                await super().__aenter__()
                acquired.set()
                await closed.wait()
                return self
        case.service.uow_factory = lambda: Writer(migration_db)
        async with migration_db.connect() as connection:
            migration_id = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def configure(sync, proxy, trace):
                original = proxy.drop_constraint
                def pause(*args, **kwargs):
                    if args[0] == "fk_run_entry_world_bindings_protocol":
                        protected.set()
                        await_only(allow_ddl.wait())
                        if fail:
                            raise primary
                    return original(*args, **kwargs)
                proxy.drop_constraint = pause
            async def migration():
                try:
                    await migrate(connection, "downgrade", configure)
                    await connection.commit()
                finally:
                    await connection.rollback()
                    closed.set()
            migration_task = asyncio.create_task(migration())
            writer_task = None
            try:
                await asyncio.wait_for(protected.wait(), 5)
                writer_task = asyncio.create_task(case.service.enter(case.runtime.principal, command=case.command))
                async def exclusion_assertion():
                    async with migration_db.connect() as observer:
                        async with asyncio.timeout(5):
                            while True:
                                assert not acquired.is_set(), "native writer acquired during protected DDL interval"
                                if units and units[0].connection_id is not None:
                                    writer_id = units[0].connection_id
                                    assert await observer.scalar(sa.text("SELECT CONNECTION_ID()")) not in (writer_id, migration_id)
                                    row = (await observer.execute(sa.text("SELECT STATE,INFO FROM information_schema.PROCESSLIST WHERE ID=:id"), {"id": writer_id})).one()
                                    owner = await observer.scalar(sa.text(f"SELECT IS_USED_LOCK('{LOCK}')"))
                                    if row.STATE == "User lock" and row.INFO == f"SELECT GET_LOCK('{LOCK}', 30)":
                                        assert owner == migration_id
                                        return
                                await asyncio.sleep(0.01)
                if different_lock:
                    with pytest.raises(AssertionError, match="native writer acquired during protected DDL interval"):
                        await exclusion_assertion()
                else:
                    await exclusion_assertion()
                assert case.runtime.run_issuer.calls == 0
                allow_ddl.set()
                if fail:
                    with pytest.raises(RuntimeError) as caught:
                        await asyncio.wait_for(migration_task, 5)
                    assert caught.value is primary
                    result = await asyncio.wait_for(writer_task, 5)
                    assert result.admitted_run_revision.value == 3
                else:
                    await asyncio.wait_for(migration_task, 5)
                    with pytest.raises(sa.exc.ProgrammingError) as caught:
                        await asyncio.wait_for(writer_task, 5)
                    assert caught.value.orig.args[0] == 1146
                    assert case.runtime.run_issuer.calls == 1
            finally:
                allow_ddl.set()
                await asyncio.gather(*(t for t in (migration_task, writer_task) if t), return_exceptions=True)
                if not fail:
                    await restore_empty_world(migration_db)


@pytest.mark.parametrize("commit", [False, True])
async def test_current_locking_probes_see_native_writer_after_old_rr_snapshot(migration_db, commit):
    async with native_runtime(migration_db) as case:
        flushed, finish = asyncio.Event(), asyncio.Event()
        class Writer(SqlAlchemyNativeRunAdmissionUnitOfWork):
            async def commit(self):
                flushed.set()
                await finish.wait()
                if commit:
                    await super().commit()
                else:
                    raise RuntimeError("roll back native writer")
        case.service.uow_factory = lambda: Writer(migration_db)
        async with migration_db.connect() as connection:
            await connection.execution_options(isolation_level="REPEATABLE READ")
            assert (await connection.execute(sa.text("SELECT 1 FROM run_entry_world_bindings LIMIT 1"))).first() is None
            writer = asyncio.create_task(case.service.enter(case.runtime.principal, command=case.command))
            migration = None
            started = asyncio.Event()
            captured = {}
            def configure(sync, proxy, trace):
                view = _ConnectionView(sync, migration_db, None)
                execute = view.execute
                def observe_get(statement, *args, **kwargs):
                    if "GET_LOCK" in str(statement):
                        started.set()
                    return execute(statement, *args, **kwargs)
                view.execute = observe_get
                proxy.get_bind = lambda: view
                captured["view"] = view
            try:
                await asyncio.wait_for(flushed.wait(), 5)
                migration = asyncio.create_task(migrate(connection, "downgrade", configure))
                await asyncio.wait_for(started.wait(), 5)
                assert not any("FOR UPDATE" in sql for sql in captured["view"].sql)
                finish.set()
                if commit:
                    await asyncio.wait_for(writer, 5)
                    with pytest.raises(RuntimeError) as caught:
                        await asyncio.wait_for(migration, 5)
                    assert str(caught.value) == REFUSAL
                else:
                    with pytest.raises(RuntimeError, match="roll back native writer"):
                        await writer
                    await asyncio.wait_for(migration, 5)
                await connection.rollback()
                probes = [sql for sql in captured["view"].sql if "FOR UPDATE" in sql]
                assert probes[0] == "SELECT 1 FROM run_entry_world_bindings LIMIT 1 FOR UPDATE"
                if not commit:
                    assert probes[1] == "SELECT 1 FROM run_creation_receipts WHERE LEFT(operation_evidence_canonical, 1) = X'8A' LIMIT 1 FOR UPDATE"
            finally:
                finish.set()
                await asyncio.gather(*(t for t in (writer, migration) if t), return_exceptions=True)
                if not commit:
                    await restore_empty_world(migration_db)


@pytest.mark.parametrize("check,code", [(1, "ACQUIRE_CONNECTION_LOST_BEFORE"), (3, "ACQUIRE_CONNECTION_LOST_AFTER"),
    (10, "BODY_CONNECTION_LOST_AFTER_TABLE"), (11, "RELEASE_CONNECTION_LOST_BEFORE")])
async def test_007_state_only_acquisition_and_post_table_loss(migration_db, check, code):
    async with migration_db.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        captured = {}
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, migration_db, owner, state_check=check)
            proxy.get_bind = lambda: view
            captured.update(view=view, trace=trace)
        with pytest.raises(RuntimeError) as caught:
            await migrate(connection, "downgrade", configure)
        assert type(caught.value) is RuntimeError and str(caught.value) == "P3.3-S4 downgrade " + code
        assert caught.value.__cause__ is None
        assert len(captured["trace"]) == (0 if check <= 3 else 4)
        assert not any("RELEASE_LOCK" in sql for sql in captured["view"].sql)
        if not connection.closed:
            await connection.rollback()
    await observe(migration_db, owner)


async def test_007_primary_error_survives_release_and_discard_failure(migration_db):
    async with migration_db.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        primary = RuntimeError("body sentinel")
        captured = {}
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, migration_db, owner, result_override=("RELEASE_LOCK", None), close_failure=True)
            execute = view.execute
            def fail(statement, *args, **kwargs):
                if "FROM run_entry_world_bindings" in str(statement):
                    raise primary
                return execute(statement, *args, **kwargs)
            view.execute = fail
            captured["view"] = view
            proxy.get_bind = lambda: view
        with pytest.raises(RuntimeError) as caught:
            await migrate(connection, "downgrade", configure)
        assert caught.value is primary and primary.__cause__ is None
        assert str(primary.cleanup_error) == "P3.3-S4 downgrade RELEASE_NULL"
        assert primary.cleanup_error.close_error is captured["view"].close_error
    await observe(migration_db, owner)


@pytest.mark.parametrize("acquisition_failure", ["null", "statement"])
@pytest.mark.parametrize("physical_close_failure", [False, True])
async def test_007_failed_invalidation_terminates_live_owner(migration_db, acquisition_failure, physical_close_failure):
    invalidation_error = RuntimeError("invalidation failed with owner still alive")
    statement_error = RuntimeError("acquisition result failed after real GET_LOCK")
    physical_error = RuntimeError("physical close failed with detached owner still alive")
    evidence = {}
    owner = None
    # Hold an independent observer throughout: no pool checkout or teardown can
    # accidentally supply the physical disposal under test.
    async with migration_db.connect() as observer:
        async with migration_db.connect() as connection:
            owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()

            async def owner_state():
                return (
                    await observer.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=:id"), {"id": owner}),
                    await observer.scalar(sa.text(f"SELECT IS_USED_LOCK('{LOCK}')")),
                )

            def configure(sync, proxy, trace):
                retained = sync.connection
                driver = retained.driver_connection
                evidence["pool_connection"] = retained
                evidence["driver"] = driver

                def fail_physical_close():
                    assert retained.is_detached
                    evidence["physical_close_failure"] = await_only(owner_state())
                    assert evidence["physical_close_failure"] == (1, owner)
                    raise physical_error

                class LiveOwnerView:
                    def __getattr__(self, name):
                        return getattr(sync, name)

                    @property
                    def connection(self):
                        if physical_close_failure:
                            return SimpleNamespace(detach=retained.detach, invalidate=retained.invalidate,
                                                   driver_connection=SimpleNamespace(close=fail_physical_close))
                        return retained

                    def execute(self, statement, *args, **kwargs):
                        result = sync.execute(statement, *args, **kwargs)
                        if "GET_LOCK" in str(statement):
                            assert result.scalar_one() == 1
                            if acquisition_failure == "statement":
                                raise statement_error
                            return SimpleNamespace(scalar_one=lambda: None)
                        return result

                    def invalidate(self):
                        evidence["before_fallback"] = await_only(owner_state())
                        assert evidence["before_fallback"] == (1, owner)
                        raise invalidation_error

                evidence["trace"] = trace
                proxy.get_bind = LiveOwnerView

            try:
                with pytest.raises(RuntimeError) as caught:
                    await migrate(connection, "downgrade", configure)
                primary = caught.value
                assert type(primary) is RuntimeError
                assert str(primary) == "P3.3-S4 downgrade ACQUIRE_" + (
                    "NULL" if acquisition_failure == "null" else "STATEMENT_FAILED")
                assert primary.__cause__ is (None if acquisition_failure == "null" else statement_error)
                assert primary.close_error is invalidation_error
                assert evidence["before_fallback"] == (1, owner)
                assert evidence["trace"] == []
                assert evidence["pool_connection"].is_detached
                assert not evidence["pool_connection"].is_valid
                # A closed SQLAlchemy wrapper alone is explicitly insufficient.
                if physical_close_failure:
                    assert primary.disposal_errors == (physical_error,)
                    assert evidence["physical_close_failure"] == (1, owner)
                    assert await owner_state() == (1, owner)
                else:
                    async with asyncio.timeout(5):
                        while (await owner_state())[0]:
                            await asyncio.sleep(0.05)
                    assert await owner_state() == (0, None)
                    assert await observer.scalar(sa.text(f"SELECT IS_FREE_LOCK('{LOCK}')")) == 1
                assert connection.closed
                async with migration_db.connect() as subsequent:
                    next_owner = await subsequent.scalar(sa.text("SELECT CONNECTION_ID()"))
                    assert next_owner != owner
                    assert await subsequent.scalar(sa.text("SELECT 41 + 1")) == 42
                    assert await subsequent.scalar(sa.text(f"SELECT GET_LOCK('{LOCK}', 0)")) == (0 if physical_close_failure else 1)
                    if not physical_close_failure:
                        assert await subsequent.scalar(sa.text(f"SELECT RELEASE_LOCK('{LOCK}')")) == 1
                print({"acquisition_failure": acquisition_failure, "alive_before_fallback": evidence["before_fallback"],
                       "physical_close_failure": physical_close_failure, "owner_state_before_teardown": await owner_state(),
                       "usable_subsequent_owner": next_owner})
            finally:
                # Diagnostic cleanup is deliberately after every disposal assertion;
                # it cannot convert failed production cleanup into a passing test.
                if (await owner_state())[0]:
                    await observer.execute(sa.text(f"KILL CONNECTION {owner}"))
                if not connection.closed:
                    await connection.invalidate()
                if "driver" in evidence:
                    evidence["driver"].close()
                async with asyncio.timeout(5):
                    while (await owner_state())[0]:
                        await asyncio.sleep(0.05)
                assert await observer.scalar(sa.text(f"SELECT IS_FREE_LOCK('{LOCK}')")) == 1
                print({"diagnostic_teardown": "owner absent and shared lock free", "owner": owner})
