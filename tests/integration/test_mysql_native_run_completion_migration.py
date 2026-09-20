"""Fresh 011 proof, restored to the observed initial database state."""
import pytest
import sqlalchemy as sa

from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.integration.test_mysql_world_continuation_migration import migrate_to, schema_state
from deviation_protocol.infrastructure import orm_models as orm

pytestmark = pytest.mark.integration


async def test_s7_4_011_roundtrip_and_exact_metadata(mysql_engine):
    initial = await schema_state(mysql_engine)
    original = initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007", "20260917_0008", "20260918_0009", "20260918_0010")
    assert not any(rows for name, (_, rows) in initial[0].items() if name != "alembic_version")
    module = SCRIPT.get_revision("20260920_0011").module
    try:
        await migrate_to(mysql_engine, "20260918_0010")
        before = await schema_state(mysql_engine)
        await migrate_to(mysql_engine, "20260920_0011")
        after = await schema_state(mysql_engine)
        assert set(before[0]) == set(after[0])
        changed = {table for table, *_ in module._CONSTRAINTS}
        assert changed == {"run_current", "run_revisions", "run_mutation_receipts"}
        for table, (ddl, rows) in before[0].items():
            if table != "alembic_version":
                assert after[0][table][1] == rows
            if table not in changed:
                assert after[0][table][0] == ddl
        for table, name, old, new in module._CONSTRAINTS:
            constraint = next(c for c in orm.Base.metadata.tables[table].constraints if c.name == name)
            assert str(constraint.sqltext) == new
            assert new.startswith(old + " OR ")
        assert all(row[3] == "YES" for row in after[1] if row[2] == "CHECK")
        await migrate_to(mysql_engine, "20260918_0010")
        assert await schema_state(mysql_engine) == before
    finally:
        await migrate_to(mysql_engine, original)
    assert await schema_state(mysql_engine) == initial


import json
from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK

async def restore_empty_010_after_inspection(engine,initial):
    """Explicit test-operator repair of a verified empty failed DDL prefix."""
    module=SCRIPT.get_revision("20260920_0011").module
    async with engine.connect() as connection:
        assert engine.url.drivername=="mysql+asyncmy"
        assert await connection.scalar(sa.text("SELECT DATABASE()"))=="deviation_protocol_test"
        tables=set((await connection.execute(sa.text("SHOW TABLES"))).scalars())
        assert tables <= set(initial[0])|{name for name,_ in module._TABLES_AFTER}
        assert await connection.scalar(sa.text("SELECT GET_LOCK(:lock,30)"),{"lock":NATIVE_ADMISSION_LOCK})==1
        try:
            for table in tables-{"alembic_version"}:
                assert await connection.scalar(sa.text(f"SELECT COUNT(*) FROM `{table}`"))==0
            for table,name,old,new in module._CONSTRAINTS:
                actual=await connection.scalar(sa.text("SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_NAME=:name"),{"name":name})
                assert module._expression(actual) in (module._expression(old),module._expression(new))
                if module._expression(actual)!=module._expression(old):
                    await connection.execute(sa.text(f"ALTER TABLE {table} DROP CHECK {name}, ADD CONSTRAINT {name} CHECK ({old})"))
            for table,_ in reversed(module._CREATE_TABLES):
                if table in tables:await connection.execute(sa.text(f"DROP TABLE {table}"))
            await connection.execute(sa.text("UPDATE alembic_version SET version_num='20260918_0010'"))
            await connection.commit()
        finally:
            assert await connection.scalar(sa.text("SELECT RELEASE_LOCK(:lock)"),{"lock":NATIVE_ADMISSION_LOCK})==1


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("boundary",range(3))
@pytest.mark.parametrize("after",[False,True,"disconnect"])
async def test_a09_011_statement_durable_fault_boundaries(mysql_engine,monkeypatch,upgrading,boundary,after):
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008","20260918_0010")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260920_0011").module
    await migrate_to(mysql_engine,"20260918_0010" if upgrading else "20260920_0011")
    sentinel=RuntimeError("injected statement boundary")
    executed=[]
    attempted=[]
    try:
        async with mysql_engine.connect() as connection:
            owner=await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def run(sync):
                class Owner:
                    def __getattr__(self,name):return getattr(sync,name)
                    def execute(self,statement,*args,**kwargs):
                        sql=str(statement)
                        ddl=sql.lstrip().startswith(("CREATE TABLE","ALTER TABLE","DROP TABLE"))
                        if ddl:
                            index=len(attempted);attempted.append(sql)
                            if index==boundary and not after:raise sentinel
                        result=sync.execute(statement,*args,**kwargs)
                        if ddl:
                            executed.append(sql)
                            if index==boundary and after=="disconnect":sync.invalidate()
                            elif index==boundary and after:raise sentinel
                        return result
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:Owner())
                    (module.upgrade if upgrading else module.downgrade)()
            with pytest.raises(RuntimeError) as caught:
                await connection.run_sync(run)
            if after=="disconnect":
                assert "BODY_CONNECTION_LOST_AFTER_" in str(caught.value)
                sentinel=caught.value
            else:assert caught.value is sentinel
            assert len(executed)==boundary+int(after is not False)
            print(json.dumps(dict(direction="upgrade" if upgrading else "downgrade",boundary=boundary,after=after,
                actual_completed_statements=executed,reported_completed=sentinel.completed_constraints,failed_stage=sentinel.failed_stage)))
            # Even a statement error leaves a potentially partial schema. This
            # failed physical owner must not resume normal writers.
            assert connection.closed
        async with mysql_engine.connect() as observer:
            assert await observer.scalar(sa.text("SELECT IS_USED_LOCK(:lock)"),{"lock":NATIVE_ADMISSION_LOCK}) is None
            assert await observer.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=:owner"),{"owner":owner})==0
            tables=set((await observer.execute(sa.text("SHOW TABLES"))).scalars())
            print(json.dumps(dict(remaining_tables=sorted(tables))))
    finally:
        await restore_empty_010_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("phase",["GET_LOCK","RELEASE_LOCK"])
@pytest.mark.parametrize("mode",["zero","null","invalid","exception","disconnect","discard"])
async def test_a09_011_lock_and_failed_disposal(mysql_engine,monkeypatch,upgrading,phase,mode):
    from types import SimpleNamespace
    from tests.integration.test_mysql_native_run_migration import _ConnectionView, observe
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260918_0010")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260920_0011").module
    await migrate_to(mysql_engine,"20260918_0010" if upgrading else "20260920_0011")
    captured={}
    try:
        async with mysql_engine.connect() as connection:
            owner=await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def run(sync):
                view=_ConnectionView(sync,mysql_engine,owner)
                captured["view"]=view
                if mode in ("exception","disconnect"):view.sql_fault=(phase,mode)
                else:view.result_override=(phase,{"zero":0,"null":None,"invalid":True,"discard":None}[mode])
                view.close_failure=mode=="discard"
                if phase=="GET_LOCK" and mode=="zero":
                    original_execute=view.execute
                    def timeout(statement,*args,**kwargs):
                        if "GET_LOCK" in str(statement):return SimpleNamespace(scalar_one=lambda:0)
                        return original_execute(statement,*args,**kwargs)
                    view.execute=timeout
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:view)
                    (module.upgrade if upgrading else module.downgrade)()
            with pytest.raises(RuntimeError) as caught:
                await connection.run_sync(run)
            prefix="ACQUIRE_" if phase=="GET_LOCK" else "RELEASE_"
            code={"zero":"TIMEOUT" if phase=="GET_LOCK" else "NOT_OWNER","null":"NULL","invalid":"INVALID_RESULT",
                "exception":"STATEMENT_FAILED","disconnect":"CONNECTION_LOST_PENDING","discard":"NULL"}[mode]
            assert str(caught.value)=="P3.3-S7-4 migration "+prefix+code
            if mode=="discard":assert caught.value.close_error is captured["view"].close_error
            if phase=="GET_LOCK":assert not any(sql.lstrip().startswith(("CREATE TABLE","ALTER TABLE","DROP TABLE")) for sql in captured["view"].sql)
            if not connection.closed:await connection.rollback()
        await observe(mysql_engine,None if phase=="GET_LOCK" and mode=="zero" else owner)
    finally:
        await restore_empty_010_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


@pytest.mark.parametrize("upgrading", [True, False])
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_a09_011_final_preflight_failure(mysql_engine, monkeypatch, upgrading, cleanup_fails):
    """All three ALTERs are durable before failure inside the final preflight."""
    initial = await schema_state(mysql_engine)
    original = initial[0]["alembic_version"][1][0][0]
    assert not any(rows for name, (_, rows) in initial[0].items() if name != "alembic_version")
    module = SCRIPT.get_revision("20260920_0011").module
    source = "20260918_0010" if upgrading else "20260920_0011"
    primary, cleanup = RuntimeError("final preflight sentinel"), RuntimeError("release sentinel")
    statements, preflights = [], []
    try:
        await migrate_to(mysql_engine, source)
        before = await schema_state(mysql_engine)
        async with mysql_engine.connect() as connection:
            owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def run(sync):
                class Owner:
                    def __getattr__(self, name): return getattr(sync, name)
                    def execute(self, statement, *args, **kwargs):
                        sql = str(statement); statements.append(sql)
                        if "RELEASE_LOCK" in sql and cleanup_fails: raise cleanup
                        return sync.execute(statement, *args, **kwargs)
                real_preflight = module._preflight
                def preflight(bind, **kwargs):
                    preflights.append(kwargs)
                    real_preflight(bind, **kwargs)
                    if len(preflights) == 2:
                        # The real final preflight has inspected the full target
                        # schema while the migration still owns its named lock.
                        assert bind.execute(sa.text("SELECT IS_USED_LOCK(:lock)"), {"lock": NATIVE_ADMISSION_LOCK}).scalar_one() == owner
                        raise primary
                with monkeypatch.context() as patch:
                    patch.setattr(module.op, "get_bind", lambda: Owner())
                    patch.setattr(module, "_preflight", preflight)
                    (module.upgrade if upgrading else module.downgrade)()
            with pytest.raises(RuntimeError) as caught:
                await connection.run_sync(run)
            assert caught.value is primary
            assert primary.failed_stage == "AFTER_DDL_PREFLIGHT"
            ordered = module._CONSTRAINTS if upgrading else tuple(reversed(module._CONSTRAINTS))
            assert primary.completed_constraints == tuple(name for _, name, _, _ in ordered)
            expected = [f"ALTER TABLE {table} DROP CHECK {name}, ADD CONSTRAINT {name} CHECK ({new if upgrading else old})"
                        for table, name, old, new in ordered]
            assert [sql for sql in statements if sql.lstrip().startswith(("ALTER ", "CREATE ", "DROP "))] == expected
            assert preflights == [dict(upgrading=upgrading), dict(upgrading=not upgrading, expected_revision=source)]
            if cleanup_fails:
                assert str(primary.cleanup_error) == "P3.3-S7-4 migration RELEASE_STATEMENT_FAILED"
                assert primary.cleanup_error.__cause__ is cleanup
            else: assert primary.cleanup_error is None
            assert connection.closed
        async with mysql_engine.connect() as observer:
            assert await observer.scalar(sa.text("SELECT IS_USED_LOCK(:lock)"), {"lock": NATIVE_ADMISSION_LOCK}) is None
            assert await observer.scalar(sa.text("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=:owner"), {"owner": owner}) == 0
            for table, name, old, new in module._CONSTRAINTS:
                actual = await observer.scalar(sa.text("SELECT CHECK_CLAUSE FROM information_schema.CHECK_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_NAME=:name"), {"name": name})
                assert module._expression(actual) == module._expression(new if upgrading else old)
        after = await schema_state(mysql_engine)
        assert after[1] == before[1]
        for table, (_, rows) in before[0].items():
            assert after[0][table][1] == rows
            if table not in {row[0] for row in module._CONSTRAINTS}: assert after[0][table] == before[0][table]
        print(json.dumps(dict(direction="upgrade" if upgrading else "downgrade",failed_stage=primary.failed_stage,
            completed_constraints=primary.completed_constraints,ddl=expected,cleanup_fails=cleanup_fails,
            target_constraints_observed=True,owner_disposed=True,free_lock=True,revision_unchanged=source)))
    finally:
        await restore_empty_010_after_inspection(mysql_engine, initial)
        await migrate_to(mysql_engine, original)
    assert await schema_state(mysql_engine) == initial


