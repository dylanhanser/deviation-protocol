"""Isolated 009 migration proof on the dedicated MySQL test database."""
import pytest
import json
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK

pytestmark=pytest.mark.integration


async def migrate_to(engine,target):
    async with engine.connect() as connection:
        assert engine.url.drivername=="mysql+asyncmy"
        assert await connection.scalar(sa.text("SELECT DATABASE()"))=="deviation_protocol_test"
        current=await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        await connection.rollback()
        if current==target:
            return
        def run(sync):
            direction=SCRIPT._upgrade_revs if target>current else SCRIPT._downgrade_revs
            context=MigrationContext.configure(sync,opts={"fn":lambda revisions,context:direction(target,revisions)})
            with Operations.context(context),context.begin_transaction():
                context.run_migrations()
        await connection.run_sync(run)
        await connection.commit()


async def schema_state(engine):
    async with engine.connect() as connection:
        assert await connection.scalar(sa.text("SELECT DATABASE()"))=="deviation_protocol_test"
        names=(await connection.execute(sa.text("SHOW TABLES"))).scalars().all()
        result={}
        for name in sorted(names):
            assert name.replace('_','').isalnum()
            create=(await connection.execute(sa.text(f"SHOW CREATE TABLE `{name}`"))).one()[1]
            rows=(await connection.execute(sa.text(f"SELECT * FROM `{name}`"))).all()
            result[name]=(create,tuple(sorted(tuple(row) for row in rows)))
        constraints=tuple((await connection.execute(sa.text("SELECT TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE,ENFORCED FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() ORDER BY TABLE_NAME,CONSTRAINT_NAME"))).all())
        assert await connection.scalar(sa.text("SELECT IS_USED_LOCK(:name)"),{"name":NATIVE_ADMISSION_LOCK}) is None
        return result,constraints


async def test_s7_2_009_upgrade_downgrade_exact_initial_state(mysql_engine):
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008")
    assert not any(initial[0][name][1] for name in initial[0] if name!="alembic_version")
    try:
        await migrate_to(mysql_engine,"20260917_0008")
        before=await schema_state(mysql_engine)
        await migrate_to(mysql_engine,"20260918_0009")
        after=await schema_state(mysql_engine)
        assert set(after[0])-set(before[0])=={"run_world_states","run_world_visits","run_world_positions"}
        for name,(ddl,rows) in before[0].items():
            if name!="alembic_version":
                assert after[0][name][1]==rows
            if name not in {"run_current","run_revisions","run_mutation_receipts","alembic_version"}:
                assert after[0][name][0]==ddl
        assert all(row[3]=="YES" for row in after[1] if row[2]=="CHECK")
        await migrate_to(mysql_engine,"20260917_0008")
        assert await schema_state(mysql_engine)==before
    finally:
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


@pytest.mark.parametrize("fault",["collation","unenforced","missing_position"])
async def test_s7_2_009_contradictory_schema_refuses_before_ddl(mysql_engine,monkeypatch,fault):
    initial=await schema_state(mysql_engine);original=initial[0]["alembic_version"][1][0][0]
    assert original=="20260916_0007" and not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260918_0009").module
    await migrate_to(mysql_engine,"20260918_0009")
    valid=await schema_state(mysql_engine)
    alter={"collation":"ALTER TABLE run_world_states MODIFY state_schema VARCHAR(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL",
        "unenforced":"ALTER TABLE run_world_states ALTER CHECK ck_run_world_states_schema NOT ENFORCED",
        "missing_position":"DROP TABLE run_world_positions"}[fault]
    restore={"collation":"ALTER TABLE run_world_states MODIFY state_schema VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL",
        "unenforced":"ALTER TABLE run_world_states ALTER CHECK ck_run_world_states_schema ENFORCED",
        "missing_position":dict(module._CREATE_TABLES)["run_world_positions"]}[fault]
    try:
        async with mysql_engine.begin() as connection:await connection.execute(sa.text(alter))
        statements=[]
        async with mysql_engine.connect() as connection:
            def run(sync):
                class Owner:
                    def __getattr__(self,name):return getattr(sync,name)
                    def execute(self,statement,*args,**kwargs):
                        statements.append(str(statement));return sync.execute(statement,*args,**kwargs)
                with monkeypatch.context() as patch:
                    patch.setattr(module.op,"get_bind",lambda:Owner());module.downgrade()
            with pytest.raises(RuntimeError):await connection.run_sync(run)
            await connection.rollback()
        assert not any(sql.lstrip().startswith(("ALTER TABLE","CREATE TABLE","DROP TABLE")) for sql in statements)
    finally:
        # Explicit fixture restoration after observing the refused schema.
        async with mysql_engine.begin() as connection:await connection.execute(sa.text(restore))
        if fault in ("collation","unenforced"):
            # ALTER rewrites the CHECK literal charset as well as its target.
            async with mysql_engine.begin() as connection:
                await connection.execute(sa.text("ALTER TABLE run_world_states DROP CHECK ck_run_world_states_schema, ADD CONSTRAINT ck_run_world_states_schema CHECK (state_schema = 'run-world-state/v1')"))
        try:
            assert await schema_state(mysql_engine)==valid
        finally:
            await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("phase",["GET_LOCK","RELEASE_LOCK"])
@pytest.mark.parametrize("mode",["zero","null","invalid","exception","disconnect","discard"])
async def test_s7_2_009_lock_and_failed_disposal(mysql_engine,monkeypatch,upgrading,phase,mode):
    from types import SimpleNamespace
    from tests.integration.test_mysql_native_run_migration import _ConnectionView, observe
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260918_0009").module
    await migrate_to(mysql_engine,"20260917_0008" if upgrading else "20260918_0009")
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
            assert str(caught.value)=="P3.3-S7-2 migration "+prefix+code
            if mode=="discard":assert caught.value.close_error is captured["view"].close_error
            if phase=="GET_LOCK":assert not any(sql.lstrip().startswith(("CREATE TABLE","ALTER TABLE","DROP TABLE")) for sql in captured["view"].sql)
            if not connection.closed:await connection.rollback()
        await observe(mysql_engine,None if phase=="GET_LOCK" and mode=="zero" else owner)
    finally:
        await restore_empty_008_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial


async def restore_empty_008_after_inspection(engine,initial):
    """Explicit test-operator repair of a verified empty failed DDL prefix."""
    module=SCRIPT.get_revision("20260918_0009").module
    async with engine.connect() as connection:
        assert engine.url.drivername=="mysql+asyncmy"
        assert await connection.scalar(sa.text("SELECT DATABASE()"))=="deviation_protocol_test"
        tables=set((await connection.execute(sa.text("SHOW TABLES"))).scalars())
        assert tables <= set(initial[0])|{name for name,_ in module._CREATE_TABLES}
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
            await connection.execute(sa.text("UPDATE alembic_version SET version_num='20260917_0008'"))
            await connection.commit()
        finally:
            assert await connection.scalar(sa.text("SELECT RELEASE_LOCK(:lock)"),{"lock":NATIVE_ADMISSION_LOCK})==1


@pytest.mark.parametrize("upgrading",[True,False])
@pytest.mark.parametrize("boundary",range(6))
@pytest.mark.parametrize("after",[False,True,"disconnect"])
async def test_s7_2_009_statement_durable_fault_boundaries(mysql_engine,monkeypatch,upgrading,boundary,after):
    initial=await schema_state(mysql_engine)
    original=initial[0]["alembic_version"][1][0][0]
    assert original in ("20260916_0007","20260917_0008")
    assert not any(rows for name,(_,rows) in initial[0].items() if name!="alembic_version")
    module=SCRIPT.get_revision("20260918_0009").module
    await migrate_to(mysql_engine,"20260917_0008" if upgrading else "20260918_0009")
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
        await restore_empty_008_after_inspection(mysql_engine,initial)
        await migrate_to(mysql_engine,original)
    assert await schema_state(mysql_engine)==initial
