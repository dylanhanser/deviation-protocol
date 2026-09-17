"""Migration 008 real-owner, partial-DDL and restoration evidence."""
from types import SimpleNamespace
import asyncio

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from deviation_protocol.infrastructure import orm_models as orm
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.integration.test_mysql_native_run_migration import _ConnectionView, observe
from tests.integration.test_mysql_native_run_exit import exit_case, public_admit, migrate_to
from tests.integration.test_mysql_native_run_admission import family_bytes
from tests.unit.test_run_exit_api import play_to_ending

pytestmark = pytest.mark.integration
MIGRATION = SCRIPT.get_revision("20260917_0008").module


async def amend(engine, direction, configure=None):
    async with engine.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        def run(sync):
            view = _ConnectionView(sync, engine, owner)
            if configure: configure(view)
            previous = MIGRATION.op
            MIGRATION.op = SimpleNamespace(get_bind=lambda:view)
            try:
                getattr(MIGRATION, direction)()
            finally:
                MIGRATION.op = previous
        await connection.run_sync(run)
        if not connection.closed:
            await connection.commit()


async def checks(engine):
    async with engine.connect() as connection:
        rows = (await connection.execute(sa.text("SELECT CONSTRAINT_NAME, CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE()"))).all()
        return {name:expression for name,expression in rows}


async def repair(engine, *, terminating):
    # Explicit test/operator repair: inspect and amend only the three known checks.
    # Never continue a failed migration on its discarded owner.
    async with engine.connect() as connection:
        assert await connection.scalar(sa.text("SELECT DATABASE()")) == "deviation_protocol_test"
        for table, name, old, new in MIGRATION._CONSTRAINTS:
            present = await connection.scalar(sa.text("SELECT COUNT(*) FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_NAME=:name"), {"name":name})
            assert present == 1
            expression = new if terminating else old
            await connection.execute(sa.text(f"ALTER TABLE {table} DROP CHECK {name}, ADD CONSTRAINT {name} CHECK ({expression})"))
        await connection.commit()
    await observe(engine)


@pytest.fixture
async def schema8(mysql_engine):
    async with mysql_engine.connect() as connection:
        original = await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        assert original in ("20260916_0007", "20260917_0008")
    await migrate_to(mysql_engine, "20260917_0008")
    baseline = await checks(mysql_engine)
    try:
        yield mysql_engine, baseline
    finally:
        await repair(mysql_engine, terminating=True)
        assert await checks(mysql_engine) == baseline
        await migrate_to(mysql_engine, original)


async def test_e07_old_native_rows_preserved_and_exact_metadata(mysql_engine, monkeypatch):
    async with exit_case(mysql_engine, monkeypatch) as case:
        await public_admit(case, "migration.old")
        # Preserve a populated legacy family alongside the native family.
        from tests.integration.test_mysql_run_entry_playthrough import _entry
        response = await _entry(case.client, key="migration.legacy", character_id=case.runtime.character_ids[1].value)
        assert response.status_code == 200, response.text
        case.scope.run_ids.add(response.json()["run_id"])
        case.scope.session_ids.add(response.json()["session_id"])
        before = await family_bytes(case)
        new_checks = await checks(mysql_engine)
        await amend(mysql_engine, "downgrade")
        old_checks = await checks(mysql_engine)
        assert {name for name in new_checks if new_checks[name] != old_checks[name]} == {v[1] for v in MIGRATION._CONSTRAINTS}
        assert await family_bytes(case) == before
        await amend(mysql_engine, "upgrade")
        assert await checks(mysql_engine) == new_checks
        assert await family_bytes(case) == before
        for table, name, _, expression in MIGRATION._CONSTRAINTS:
            assert expression == next(str(c.sqltext) for c in orm.Base.metadata.tables[table].constraints if c.name == name)


async def test_e07_empty_upgrade_roundtrip_and_constraint_rejection(schema8):
    engine, baseline = schema8
    async with engine.connect() as connection:
        for table, _, _, _ in MIGRATION._CONSTRAINTS:
            assert await connection.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")) == 0
    await amend(engine, "downgrade")
    await amend(engine, "upgrade")
    assert await checks(engine) == baseline


@pytest.mark.parametrize("mode", ["stale_snapshot", "writer_wait"])
async def test_e07_current_read_and_writer_downgrade_serialization(mysql_engine, monkeypatch, mode):
    from deviation_protocol.infrastructure.repositories import SqlAlchemyRunRepository
    from tests.integration.test_mysql_native_run_exit import wait_for_named_lock_waiters
    async with exit_case(mysql_engine, monkeypatch) as case:
        admitted, _ = await public_admit(case, "probe.admit", "difficulty.silent-hunting-ground")
        sid = admitted["session_id"]
        ended, _ = await play_to_ending(case.client, sid)
        data = {"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]}
        baseline = await checks(mysql_engine)
        if mode == "stale_snapshot":
            async with mysql_engine.connect() as connection:
                assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_current WHERE lifecycle_status='terminated'")) == 0
                response = await case.client.post(f"/v1/sessions/{sid}/run-exit", json=data, headers={"Idempotency-Key":"probe.exit"})
                assert response.status_code == 200, response.text
                assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_current WHERE lifecycle_status='terminated'")) == 0
                def downgrade(sync):
                    with Operations.context(MigrationContext.configure(sync)):
                        MIGRATION.downgrade()
                with pytest.raises(RuntimeError, match="terminal evidence"):
                    await connection.run_sync(downgrade)
                await connection.rollback()
        else:
            staged, release = asyncio.Event(), asyncio.Event()
            original = SqlAlchemyRunRepository.compare_and_swap_current
            async def pause(repository, run, **kw):
                result = await original(repository, run, **kw)
                if run.state_version.value == 4:
                    staged.set()
                    await release.wait()
                return result
            with monkeypatch.context() as patch:
                patch.setattr(SqlAlchemyRunRepository,"compare_and_swap_current",pause)
                writer = asyncio.create_task(case.client.post(f"/v1/sessions/{sid}/run-exit", json=data, headers={"Idempotency-Key":"probe.exit"}))
                await asyncio.wait_for(staged.wait(), 10)
                downgrade = asyncio.create_task(amend(mysql_engine, "downgrade"))
                try:
                    await wait_for_named_lock_waiters(mysql_engine, 1)
                    assert not downgrade.done()
                finally: release.set()
                response = await asyncio.wait_for(writer, 10)
                assert response.status_code == 200, response.text
                with pytest.raises(RuntimeError, match="terminal evidence"):
                    await asyncio.wait_for(downgrade, 10)
        assert await checks(mysql_engine) == baseline
        await observe(mysql_engine)


@pytest.mark.parametrize("table,column,value", [("run_revisions","mutation_kind","TERMINATE_NATIVE_RUN"),
    ("run_current","lifecycle_status","terminated"),("run_mutation_receipts","operation_namespace","run.terminate-native/v1")])
async def test_e07_constraint_rejects_incomplete_terminal_branch(mysql_engine, monkeypatch, table, column, value):
    from sqlalchemy.exc import IntegrityError, OperationalError
    async with exit_case(mysql_engine, monkeypatch) as case:
        admitted, _ = await public_admit(case, "constraint.admit")
        before = await family_bytes(case)
        async with mysql_engine.connect() as connection:
            with pytest.raises((IntegrityError, OperationalError)) as caught:
                await connection.execute(sa.text(f"UPDATE {table} SET {column}=:value WHERE run_id=:run_id"),
                    {"value":value,"run_id":admitted["run_context"]["run_id"]})
            assert caught.value.orig.args[0] == 3819
            await connection.rollback()
        assert await family_bytes(case) == before


@pytest.mark.parametrize("table", ["run_revisions", "run_current"])
@pytest.mark.parametrize("column", ["prior_state_version", "binding_state"])
async def test_e07_terminal_check_rejects_required_null(mysql_engine, monkeypatch, table, column):
    # Each case starts from a separately committed, publicly played terminal
    # family. Change only one operand: NULL must produce FALSE, not UNKNOWN.
    from sqlalchemy.exc import IntegrityError, OperationalError

    async with exit_case(mysql_engine, monkeypatch) as case:
        admitted, _ = await public_admit(case, "nullable.admit", "difficulty.silent-hunting-ground")
        sid, rid = admitted["session_id"], admitted["run_context"]["run_id"]
        ended, _ = await play_to_ending(case.client, sid)
        response = await case.client.post(
            f"/v1/sessions/{sid}/run-exit",
            headers={"Idempotency-Key": "nullable.exit"},
            json={"expected_run_state_version": 3,
                  "expected_session_state_version": ended["metadata"]["state_version"]},
        )
        assert response.status_code == 200, response.text
        status = await case.client.get(f"/v1/sessions/{sid}/run-status")
        assert status.status_code == 200, status.text
        before = await family_bytes(case)
        name = f"ck_{table}_mutation_matrix"
        async with mysql_engine.connect() as connection:
            assert await connection.scalar(sa.text(
                "SELECT ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_NAME=:name"
            ), {"name": name}) == "YES"
            row = (await connection.execute(sa.text(
                f"SELECT prior_state_version, binding_state FROM {table} "
                "WHERE run_id=:rid AND state_version=4"
            ), {"rid": rid})).one()
            assert tuple(row) == (3, "historical")
            await connection.rollback()
            assert not connection.in_transaction()
            try:
                with pytest.raises((IntegrityError, OperationalError)) as caught:
                    await connection.execute(sa.text(
                        f"UPDATE {table} SET {column}=NULL WHERE run_id=:rid AND state_version=4"
                    ), {"rid": rid})
                assert caught.value.orig.args[0] == 3819
                assert name in str(caught.value.orig)
            finally:
                await connection.rollback()
            assert not connection.in_transaction()
        assert await family_bytes(case) == before
        reconstructed = await case.client.get(f"/v1/sessions/{sid}/run-status")
        assert reconstructed.status_code == 200, reconstructed.text
        assert reconstructed.json() == status.json()
        view = await case.client.get(f"/v1/sessions/{sid}/view")
        assert view.status_code == 200, view.text
        assert view.json() == ended


@pytest.mark.parametrize("partial", [False, True])
async def test_e07_terminal_and_partial_evidence_refuse_before_ddl(mysql_engine, monkeypatch, partial):
    async with exit_case(mysql_engine, monkeypatch) as case:
        result, _ = await public_admit(case, "migration.terminal")
        sid, rid = result["session_id"], result["run_context"]["run_id"]
        ended, _ = await play_to_ending(case.client, sid)
        response = await case.client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"migration.exit"},
            json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
        assert response.status_code == 200, response.text
        if partial:
            async with case.factory.begin() as session:
                await session.execute(sa.delete(orm.RunMutationReceiptRow).where(orm.RunMutationReceiptRow.run_id == rid, orm.RunMutationReceiptRow.resulting_state_version == 4))
        before = await family_bytes(case)
        definitions = await checks(mysql_engine)
        captured = []
        with pytest.raises(RuntimeError, match="terminal evidence"):
            await amend(mysql_engine, "downgrade", lambda view:captured.append(view))
        assert not any("ALTER TABLE" in sql for sql in captured[0].sql)
        assert await checks(mysql_engine) == definitions
        assert await family_bytes(case) == before
        await observe(mysql_engine)


@pytest.mark.parametrize("direction", ["upgrade", "downgrade"])
@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("mode", ["exception", "disconnect", "loss_after_ddl"])
async def test_e07_each_ddl_boundary_records_exact_partial_state(schema8, direction, index, mode):
    engine, terminal_checks = schema8
    await amend(engine, "downgrade")
    old_checks = await checks(engine)
    if direction == "downgrade": await amend(engine, "upgrade")
    captured = []
    name = MIGRATION._CONSTRAINTS[index][1]
    def configure(view):
        captured.append(view)
        if mode == "loss_after_ddl":
            execute = view.execute
            def lose_after(statement, *args, **kwargs):
                result = execute(statement, *args, **kwargs)
                if "DROP CHECK " + name in str(statement):
                    view.kill(invalidate=True)
                return result
            view.execute = lose_after
        else:
            view.sql_fault = ("DROP CHECK " + name, mode)
    with pytest.raises(RuntimeError) as caught:
        await amend(engine, direction, configure)
    completed_count = index + (mode == "loss_after_ddl")
    assert caught.value.completed_constraints == tuple(v[1] for v in MIGRATION._CONSTRAINTS[:completed_count])
    assert caught.value.failed_stage == "DDL_" + name
    view = captured[0]
    if mode == "exception": assert caught.value is view.failure
    else: assert not any("RELEASE_LOCK" in sql for sql in view.sql)
    actual = await checks(engine)
    before, after = (old_checks,terminal_checks) if direction == "upgrade" else (terminal_checks,old_checks)
    changed = {v[1] for v in MIGRATION._CONSTRAINTS[:completed_count]}
    assert actual == {key:(after[key] if key in changed else value) for key,value in before.items()}
    assert sum("ALTER TABLE" in sql for sql in view.sql) == index + 1
    await observe(engine, view.owner if mode != "exception" else None)


@pytest.mark.parametrize("phase", ["GET_LOCK", "RELEASE_LOCK"])
@pytest.mark.parametrize("mode", ["zero", "null", "invalid", "exception", "disconnect", "discard"])
async def test_e07_lock_and_disposal_boundaries(schema8, phase, mode):
    engine, _ = schema8
    captured = []
    def configure(view):
        captured.append(view)
        if mode in ("exception", "disconnect"):
            view.sql_fault = (phase, mode)
        else:
            view.result_override = (phase, {"zero":0,"null":None,"invalid":True,"discard":None}[mode])
            view.close_failure = mode == "discard"
        if phase == "GET_LOCK" and mode == "zero":
            execute = view.execute
            def timeout(statement, *args, **kwargs):
                if "GET_LOCK" in str(statement):
                    view.sql.append(str(statement))
                    return SimpleNamespace(scalar_one=lambda:0)
                return execute(statement,*args,**kwargs)
            view.execute = timeout
    with pytest.raises(RuntimeError) as caught:
        await amend(engine,"downgrade",configure)
    view = captured[0]
    prefix = "ACQUIRE_" if phase == "GET_LOCK" else "RELEASE_"
    code = {"zero":"TIMEOUT" if phase == "GET_LOCK" else "NOT_OWNER", "null":"NULL", "invalid":"INVALID_RESULT",
        "exception":"STATEMENT_FAILED", "disconnect":"CONNECTION_LOST_PENDING", "discard":"NULL"}[mode]
    assert str(caught.value) == "P3.3-S7-1 migration " + prefix + code
    if phase == "GET_LOCK": assert not any("ALTER TABLE" in sql for sql in view.sql)
    if mode == "discard": assert caught.value.close_error is view.close_error
    await observe(engine, None if phase == "GET_LOCK" and mode == "zero" else view.owner)
