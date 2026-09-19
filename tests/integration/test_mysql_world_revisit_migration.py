"""Fresh 010 schema proof, with exact restoration of the observed initial state."""
import pytest
import json
import sqlalchemy as sa
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK

from tests.integration.test_mysql_world_continuation_migration import migrate_to, schema_state

pytestmark = pytest.mark.integration


async def test_r08_upgrade_downgrade_preserves_actual_initial_schema(mysql_engine):
    initial = await schema_state(mysql_engine)
    original = initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007", "20260917_0008", "20260918_0009")
    assert not any(rows for name, (_, rows) in initial[0].items() if name != "alembic_version")
    try:
        await migrate_to(mysql_engine, "20260918_0009")
        before = await schema_state(mysql_engine)
        await migrate_to(mysql_engine, "20260918_0010")
        after = await schema_state(mysql_engine)
        assert set(after[0]) - set(before[0]) == {"run_world_visit_entries"}
        for name, (ddl, rows) in before[0].items():
            if name != "alembic_version":
                assert after[0][name][1] == rows
            if name not in {"run_current", "run_revisions", "run_mutation_receipts",
                            "run_world_visits", "run_world_positions", "alembic_version"}:
                assert after[0][name][0] == ddl
        assert all(row[3] == "YES" for row in after[1] if row[2] == "CHECK")
        await migrate_to(mysql_engine, "20260918_0009")
        assert await schema_state(mysql_engine) == before
    finally:
        await migrate_to(mysql_engine, original)
    assert await schema_state(mysql_engine) == initial


async def restore_empty_009_after_inspection(engine,initial):
    """Explicit test-operator repair of a verified empty failed DDL prefix."""
    module=SCRIPT.get_revision("20260918_0010").module
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
            await connection.execute(sa.text("UPDATE alembic_version SET version_num='20260918_0009'"))
            await connection.commit()
        finally:
            assert await connection.scalar(sa.text("SELECT RELEASE_LOCK(:lock)"),{"lock":NATIVE_ADMISSION_LOCK})==1


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("boundary",range(7))
@pytest.mark.parametrize("after",[False,True,"disconnect"])
async def test_r08_010_statement_durable_fault_boundaries(mysql_engine,monkeypatch,upgrading,boundary,after):
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008","20260918_0009")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260918_0010").module
    await migrate_to(mysql_engine,"20260918_0009" if upgrading else "20260918_0010")
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
        await restore_empty_009_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("phase",["GET_LOCK","RELEASE_LOCK"])
@pytest.mark.parametrize("mode",["zero","null","invalid","exception","disconnect","discard"])
async def test_r08_010_lock_and_failed_disposal(mysql_engine,monkeypatch,upgrading,phase,mode):
    from types import SimpleNamespace
    from tests.integration.test_mysql_native_run_migration import _ConnectionView, observe
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260918_0009")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260918_0010").module
    await migrate_to(mysql_engine,"20260918_0009" if upgrading else "20260918_0010")
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
            assert str(caught.value)=="P3.3-S7-3 migration "+prefix+code
            if mode=="discard":assert caught.value.close_error is captured["view"].close_error
            if phase=="GET_LOCK":assert not any(sql.lstrip().startswith(("CREATE TABLE","ALTER TABLE","DROP TABLE")) for sql in captured["view"].sql)
            if not connection.closed:await connection.rollback()
        await observe(mysql_engine,None if phase=="GET_LOCK" and mode=="zero" else owner)
    finally:
        await restore_empty_009_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial



@pytest.mark.parametrize("fault", ["collation", "nullable", "unenforced", "missing_entry"])
async def test_r08_010_contradictory_schema_refuses_before_ddl(mysql_engine, monkeypatch, fault):
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert not any(rows for table,(_,rows) in initial[0].items() if table!="alembic_version")
    module=SCRIPT.get_revision("20260918_0010").module
    await migrate_to(mysql_engine,"20260918_0010")
    valid=await schema_state(mysql_engine)
    alter={"collation":"ALTER TABLE run_world_visit_entries MODIFY entry_schema VARCHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL",
        "nullable":"ALTER TABLE run_world_visit_entries MODIFY created_at DATETIME(6) NULL",
        "unenforced":"ALTER TABLE run_world_visit_entries ALTER CHECK ck_run_world_visit_entries_schema NOT ENFORCED",
        "missing_entry":"DROP TABLE run_world_visit_entries"}[fault]
    restore={"collation":"ALTER TABLE run_world_visit_entries MODIFY entry_schema VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL",
        "nullable":"ALTER TABLE run_world_visit_entries MODIFY created_at DATETIME(6) NOT NULL",
        "unenforced":"ALTER TABLE run_world_visit_entries ALTER CHECK ck_run_world_visit_entries_schema ENFORCED",
        "missing_entry":dict(module._CREATE_TABLES)["run_world_visit_entries"]}[fault]
    try:
        async with mysql_engine.begin() as c:await c.execute(sa.text(alter))
        statements=[]
        async with mysql_engine.connect() as c:
            def run(sync):
                class Owner:
                    def __getattr__(self,name):return getattr(sync,name)
                    def execute(self,statement,*args,**kwargs):
                        statements.append(str(statement));return sync.execute(statement,*args,**kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:Owner());module.downgrade()
            with pytest.raises(RuntimeError):await c.run_sync(run)
            await c.rollback()
        assert not any(sql.lstrip().startswith(("ALTER TABLE","CREATE TABLE","DROP TABLE")) for sql in statements)
    finally:
        async with mysql_engine.begin() as c:
            await c.execute(sa.text(restore))
            if fault in ("collation","nullable","unenforced"):
                await c.execute(sa.text("ALTER TABLE run_world_visit_entries DROP CHECK ck_run_world_visit_entries_schema, ADD CONSTRAINT ck_run_world_visit_entries_schema CHECK (entry_schema = 'run-regional-entry/v1')"))
        assert await schema_state(mysql_engine)==valid
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


def test_r08_frozen_010_table_contracts_match_current_orm_and_exact_009_checks():
    import re
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects import mysql
    from deviation_protocol.infrastructure.orm_models import Base
    module=SCRIPT.get_revision("20260918_0010").module
    previous=SCRIPT.get_revision("20260918_0009").module
    old_checks={(table,name):new for table,name,_,new in previous._CONSTRAINTS}
    for table,ddl in previous._CREATE_TABLES:
        old_checks.update({(table,name):clause for name,clause in re.findall(r"CONSTRAINT (ck_[a-z_]+) CHECK \(([^\n]+)\)",ddl)})
    for table,name,old,new in module._CONSTRAINTS:
        assert module._expression(old)==module._expression(old_checks[(table,name)])
        current=next(c for c in Base.metadata.tables[table].constraints if c.name==name)
        assert module._expression(str(current.sqltext))==module._expression(new)
    def lines(ddl):
        normalized=[]
        for line in ddl.splitlines():
            line=re.sub(r"\s+"," ",line.strip().rstrip(","))
            if not line:
                continue
            # SQLAlchemy emits these independent table options in hash order.
            if line.startswith(")"):
                line=") "+" ".join(sorted(line[1:].strip().split()))
            normalized.append(line)
        return sorted(normalized)
    for name,ddl in module._TABLES_AFTER:
        assert lines(ddl)==lines(str(CreateTable(Base.metadata.tables[name]).compile(dialect=mysql.dialect()))),name


@pytest.mark.parametrize("legacy", [True, False])
async def test_r08_009_legacy_and_pre_admission_native_rows_survive_010(mysql_engine, legacy):
    """Storage-family controls, separate from the genuine public-play cases."""
    from tests.integration.test_mysql_run_protocol_binding import _parents
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    try:
        await migrate_to(mysql_engine,"20260918_0009")
        async with _parents(mysql_engine,legacy=legacy):
            before=await schema_state(mysql_engine)
            assert before[0]["run_current"][1]
            await migrate_to(mysql_engine,"20260918_0010")
            after=await schema_state(mysql_engine)
            for table,(_,rows) in before[0].items():
                if table!="alembic_version":assert after[0][table][1]==rows,table
            assert after[0]["run_world_visit_entries"][1]==()
            await migrate_to(mysql_engine,"20260918_0009")
            assert await schema_state(mysql_engine)==before
    finally:
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial
