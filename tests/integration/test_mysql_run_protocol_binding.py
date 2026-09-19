from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

from deviation_protocol.domain.run import RunId
from deviation_protocol.domain import run_protocol as s1
from deviation_protocol.domain import run_protocol_resolution as s2
from deviation_protocol.domain.run_protocol_binding import NativeRunProtocolBindingV1, LegacyRunCompatibilityV1
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.repositories import SqlAlchemyRunProtocolBindingRepository
from deviation_protocol.infrastructure.run_protocol_binding_persistence import ContradictoryRunFamilyError
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.unit.test_run_protocol_binding_persistence import literal, native_family, legacy_family, NOW

pytestmark = pytest.mark.integration
LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"
REFUSAL = "Refusing to downgrade P3.3-S3: native Run Protocol binding data exists; recovery must be forward-only"
HEAD = "20260828_0006"  # Historical S3 migration target, not current repository head.
CURRENT_HEAD = "20260918_0010"
BASE = "20260729_0005"
TABLE = "run_protocol_bindings"
SCRIPT = ScriptDirectory.from_config(Config(str(Path(__file__).parents[2] / "alembic.ini")))
MIGRATION = SCRIPT.get_revision(HEAD).module


async def _add_native_binding_row(
    session: AsyncSession,
    *,
    run_id: str,
    continuous_story_line_id: str,
    bound_state_version: int,
    family_discriminator: str,
    binding_epoch: str,
    binding_record_version: int,
    envelope_epoch: str,
    envelope_record_version: int,
    envelope_canonical: bytes,
    resolver_epoch: str,
    resolver_record_version: int,
    resolution_input_canonical: bytes,
    resource_pressure: int,
    social_trust: int,
    consequence_severity: int,
    information_opacity: int,
    conflict_intensity: int,
    resolution_fingerprint: bytes,
    created_at: datetime,
    flush: bool,
) -> orm.RunProtocolBindingRow:
    row = orm.RunProtocolBindingRow(
        run_id=run_id,
        continuous_story_line_id=continuous_story_line_id,
        bound_state_version=bound_state_version,
        family_discriminator=family_discriminator,
        binding_epoch=binding_epoch,
        binding_record_version=binding_record_version,
        envelope_epoch=envelope_epoch,
        envelope_record_version=envelope_record_version,
        envelope_canonical=envelope_canonical,
        resolver_epoch=resolver_epoch,
        resolver_record_version=resolver_record_version,
        resolution_input_canonical=resolution_input_canonical,
        resource_pressure=resource_pressure,
        social_trust=social_trust,
        consequence_severity=consequence_severity,
        information_opacity=information_opacity,
        conflict_intensity=conflict_intensity,
        resolution_fingerprint=resolution_fingerprint,
        created_at=created_at,
    )
    session.add(row)
    if flush:
        await session.flush()
    return row


async def _lock(connection):
    result = await connection.scalar(sa.text(f"SELECT GET_LOCK('{LOCK}', 30)"))
    assert type(result) is int and result == 1


async def _release(connection):
    result = await connection.scalar(sa.text(f"SELECT RELEASE_LOCK('{LOCK}')"))
    assert type(result) is int and result == 1


async def _migrate(connection, direction, *, configure=None, direct=False):
    def execute(sync):
        trace = []
        operations = Operations(MigrationContext.configure(sync))
        proxy = SimpleNamespace(
            get_bind=lambda: sync,
            create_table=operations.create_table, create_index=operations.create_index,
            create_foreign_key=operations.create_foreign_key,
        )
        for name in ("drop_constraint", "drop_index", "drop_table"):
            original = getattr(operations, name)
            def delegate(*args, _name=name, _original=original, **kwargs):
                trace.append(_name)
                return _original(*args, **kwargs)
            setattr(proxy, name, delegate)
        if configure:
            configure(sync, proxy, trace)
        original_op = MIGRATION.op
        MIGRATION.op = proxy
        try:
            if direct:
                getattr(MIGRATION, direction)()
            else:
                context = MigrationContext.configure(sync, opts={
                    "fn": lambda revisions, context: (
                        SCRIPT._upgrade_revs(HEAD, revisions) if direction == "upgrade"
                        else SCRIPT._downgrade_revs(BASE, revisions)
                    ),
                })
                with context.begin_transaction():
                    context.run_migrations()
            return trace
        finally:
            MIGRATION.op = original_op
    return await connection.run_sync(execute)


async def _signature(connection):
    def inspect(sync):
        inspector = sa.inspect(sync)
        if not inspector.has_table(TABLE):
            return None
        return {
            "columns": tuple(column["name"] for column in inspector.get_columns(TABLE)),
            "pk": inspector.get_pk_constraint(TABLE),
            "checks": {item["name"] for item in inspector.get_check_constraints(TABLE)},
            "indexes": {item["name"] for item in inspector.get_indexes(TABLE)},
            "foreign_keys": {item["name"] for item in inspector.get_foreign_keys(TABLE)},
            "index_details": inspector.get_indexes(TABLE),
            "foreign_key_details": inspector.get_foreign_keys(TABLE),
        }
    return await connection.run_sync(inspect)


async def _observe(engine, owner=None):
    async with engine.connect() as connection:
        async def owner_gone():
            while True:
                used = await connection.scalar(sa.text(f"SELECT IS_USED_LOCK('{LOCK}')"))
                if owner is None or used != owner:
                    return
                await asyncio.sleep(0.05)
        await asyncio.wait_for(owner_gone(), 5)
        assert await connection.scalar(sa.text(f"SELECT IS_FREE_LOCK('{LOCK}')")) == 1
        signature = await _signature(connection)
        revision = await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        return signature, revision


async def _restore(engine):
    async with engine.connect() as connection:
        signature = await _signature(connection)
        if signature is not None:
            assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_protocol_bindings")) == 0
            if signature["foreign_keys"] and signature["indexes"]:
                return
            await connection.execute(sa.text("DROP TABLE run_protocol_bindings"))
        await _migrate(connection, "upgrade", direct=True)
        await connection.run_sync(lambda sync: MigrationContext.configure(sync).stamp(SCRIPT, HEAD))
        await connection.commit()


async def _schema_target(connection, target):
    def execute(sync):
        context = MigrationContext.configure(sync, opts={"fn": lambda revisions, context:
            SCRIPT._downgrade_revs(target, revisions) if target == HEAD else SCRIPT._upgrade_revs(target, revisions)})
        with Operations.context(context), context.begin_transaction():
            context.run_migrations()
    await connection.run_sync(execute)
    await connection.commit()


@pytest.fixture
async def s3db(mysql_engine, request):
    historical = int(request.node.originalname.split("_v")[1].split("_")[0]) >= 29
    async with mysql_engine.connect() as connection:
        assert str(await connection.scalar(sa.text("SELECT VERSION()"))).startswith("8.")
        assert await connection.scalar(sa.text("SELECT DATABASE()")) == "deviation_protocol_test"
        revision = await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
        assert revision in (BASE, HEAD, "20260916_0007", "20260917_0008", CURRENT_HEAD)
        await connection.rollback()
        if revision != CURRENT_HEAD:
            await _schema_target(connection, CURRENT_HEAD)
        if historical:
            await _schema_target(connection, HEAD)
        assert await connection.scalar(sa.text("SELECT COUNT(*) FROM run_protocol_bindings")) == 0
    try:
        yield mysql_engine
    finally:
        await _restore(mysql_engine)
        async with mysql_engine.connect() as connection:
            await _schema_target(connection, CURRENT_HEAD)
        signature, revision = await _observe(mysql_engine)
        assert signature is not None and revision == CURRENT_HEAD



@asynccontextmanager
async def _parents(engine, *, legacy=False):
    run, family = await legacy_family() if legacy else native_family()
    if legacy:
        character = family[orm.PlayerCharacterRevisionRow][0]
        family[orm.PlayerCharacterIdAllocationRow] = [orm.PlayerCharacterIdAllocationRow(
            player_character_id=character.player_character_id, created_at=NOW,
        )]
    tables = [table for table in orm.Base.metadata.sorted_tables if any(model.__table__ is table and rows for model, rows in family.items())]
    models = {model.__table__: (model, rows) for model, rows in family.items() if rows}
    inserted = []
    async with engine.begin() as connection:
        for table in tables:
            model, rows = models[table]
            for row in rows:
                values = {column.name: vars(row)[column.name] for column in table.columns}
                predicate = sa.and_(*(column == values[column.name] for column in table.primary_key.columns))
                assert await connection.scalar(sa.select(sa.func.count()).select_from(table).where(predicate)) == 0
                await connection.execute(sa.insert(table).values(**values))
                inserted.append((table, predicate))
    try:
        yield run
    finally:
        async with engine.begin() as connection:
            if await connection.run_sync(lambda sync: sa.inspect(sync).has_table(TABLE)):
                await connection.execute(sa.delete(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id == run.run_id.value))
            for table, predicate in reversed(inserted):
                await connection.execute(sa.delete(table).where(predicate))


def _inputs(run, **changes):
    values = asdict(literal())
    values.update(run_id=run.run_id.value, continuous_story_line_id=run.continuous_story_line_id.value,
        bound_state_version=run.state_version.value)
    values.update(changes)
    return values


async def _count(engine, run):
    async with engine.connect() as connection:
        return await connection.scalar(sa.select(sa.func.count()).select_from(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id == run.run_id.value))


async def test_s3_v02(s3db):
    async with _parents(s3db) as run:
        assert await _count(s3db, run) == 0
        inputs = _inputs(run)
        assert len(inputs) == 19
        async with AsyncSession(s3db, expire_on_commit=False) as session:
            add = Mock(wraps=session.add)
            original_flush = session.flush
            async def check_pending():
                assert len(session.new) == 1
                await original_flush()
            flush = Mock(side_effect=check_pending)
            session.add = add
            session.flush = flush
            row = await _add_native_binding_row(session, **inputs, flush=True)
            assert add.call_count == flush.call_count == 1
            result = await SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert type(result) is NativeRunProtocolBindingV1
            assert result.resolved_protocol.fingerprint.value == literal().resolution_fingerprint.hex()
            assert result.run_id == run.run_id and result.continuous_story_line_id == run.continuous_story_line_id
            assert result.bound_state_version == run.state_version
            assert s1.encode_run_protocol_envelope_v1(result.resolved_protocol.resolution_input.envelope) == inputs["envelope_canonical"]
            assert s2.encode_run_protocol_resolution_input_v1(result.resolved_protocol.resolution_input) == inputs["resolution_input_canonical"]
            for name in ("resource_pressure", "social_trust", "consequence_severity", "information_opacity", "conflict_intensity"):
                assert getattr(result.resolved_protocol.final_values, name).value == inputs[name]
            assert {name: vars(row)[name] for name in inputs} == inputs
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id == run.run_id.value)) == 1
            assert add.call_count == flush.call_count == 1
            assert not session.new and not session.dirty and not session.deleted
            await session.rollback()
        assert await _count(s3db, run) == 0


async def test_s3_v14(s3db):
    async with _parents(s3db, legacy=True) as run:
        async with s3db.connect() as connection:
            before = await _old_rows(connection)
        async with AsyncSession(s3db) as session:
            await _add_native_binding_row(session, **_inputs(run), flush=True)
            with pytest.raises(ContradictoryRunFamilyError) as caught:
                await SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert type(caught.value) is ContradictoryRunFamilyError and caught.value.__cause__ is None
            assert not session.new and not session.dirty and not session.deleted
            assert await _old_rows(await session.connection()) == before
            await session.rollback()
        assert await _count(s3db, run) == 0
        async with s3db.connect() as connection:
            assert await _old_rows(connection) == before


async def test_s3_v21_a(s3db):
    async with _parents(s3db) as run:
        async with AsyncSession(s3db) as session:
            with pytest.raises(sa.exc.OperationalError) as caught:
                await _add_native_binding_row(session, **_inputs(run, envelope_canonical=b"x" * 1025), flush=True)
            assert caught.value.orig.args[0] == 3819
            assert not session.is_active
            await session.rollback()
        assert await _count(s3db, run) == 0


async def _compete(engine, *, different=False, concurrent=False):
    async with _parents(engine) as run:
        first_flushed = asyncio.Event()
        allow_commit = asyncio.Event()
        second_lock_started = asyncio.Event()
        second_insert_started = asyncio.Event()
        if not concurrent:
            allow_commit.set()
        async def writer(second):
            async with engine.connect() as connection:
                async with AsyncSession(bind=connection, join_transaction_mode="control_fully", expire_on_commit=False) as session:
                    if second:
                        await first_flushed.wait()
                        second_lock_started.set()
                    await _lock(session)
                    try:
                        values = _inputs(run, resource_pressure=65) if second and different else _inputs(run)
                        if second:
                            second_insert_started.set()
                            with pytest.raises(sa.exc.IntegrityError) as caught:
                                await _add_native_binding_row(session, **values, flush=True)
                            assert caught.value.orig.args[0] == 1062
                            assert not session.is_active
                            await session.rollback()
                        else:
                            await _add_native_binding_row(session, **values, flush=True)
                            first_flushed.set()
                            await allow_commit.wait()
                            await session.commit()
                    finally:
                        await _release(session)
                        await session.rollback()
        if concurrent:
            first = asyncio.create_task(writer(False))
            second = asyncio.create_task(writer(True))
            try:
                await asyncio.wait_for(second_lock_started.wait(), 5)
                await asyncio.sleep(0.25)
                assert not second.done() and not second_insert_started.is_set()
                allow_commit.set()
                await asyncio.wait_for(asyncio.gather(first, second), 10)
            finally:
                allow_commit.set()
                for task in (first, second):
                    if not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        else:
            await writer(False)
            await writer(True)
        assert await _count(engine, run) == 1
        async with engine.connect() as connection:
            values = (await connection.execute(sa.select(orm.RunProtocolBindingRow.__table__).where(orm.RunProtocolBindingRow.run_id == run.run_id.value))).mappings().one()
            assert dict(values) == _inputs(run)


async def test_s3_v22(s3db):
    await _compete(s3db)


async def test_s3_v24(s3db):
    await _compete(s3db, concurrent=True)


async def test_s3_v25(s3db):
    await _compete(s3db, concurrent=True, different=True)


async def test_s3_v26(s3db):
    async with _parents(s3db) as run:
        failure = RuntimeError("test sentinel")
        with pytest.raises(RuntimeError) as caught:
            async with SqlAlchemyUnitOfWork(async_sessionmaker(s3db)) as unit:
                await _add_native_binding_row(unit._session, **_inputs(run), flush=True)
                raise failure
        assert caught.value is failure
        assert await _count(s3db, run) == 0


async def test_s3_v27(s3db):
    async with _parents(s3db) as run:
        ready = asyncio.Event()
        async def work():
            async with SqlAlchemyUnitOfWork(async_sessionmaker(s3db)) as unit:
                await _add_native_binding_row(unit._session, **_inputs(run), flush=True)
                ready.set()
                await asyncio.Event().wait()
        task = asyncio.create_task(work())
        await asyncio.wait_for(ready.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await _count(s3db, run) == 0


async def _old_rows(connection):
    snapshot = {}
    for table in orm.Base.metadata.sorted_tables:
        if table.name in (TABLE, "run_entry_world_bindings"):
            continue
        rows = (await connection.execute(sa.select(table))).all()
        snapshot[table.name] = sorted(
            tuple(hashlib.sha256(value if type(value) is bytes else repr(value).encode("utf-8")).hexdigest() for value in row)
            for row in rows
        )
    return snapshot


async def test_s3_v29(s3db):
    async with _parents(s3db, legacy=True) as run:
        async with s3db.connect() as connection:
            await _migrate(connection, "downgrade")
            await connection.commit()
            before = await _old_rows(connection)
            captured = {}
            def capture_schema(sync, proxy, trace):
                original = proxy.create_table
                def create_table(*args, **kwargs):
                    table = original(*args, **kwargs)
                    captured["table"] = table
                    return table
                proxy.create_table = create_table
            await _migrate(connection, "upgrade", configure=capture_schema)
            await connection.commit()
            assert await _old_rows(connection) == before
            expected = orm.RunProtocolBindingRow.__table__
            actual = captured["table"]
            def columns(table):
                return tuple((column.name, str(column.type.compile(dialect=connection.dialect)), column.nullable,
                    column.default, column.server_default, column.primary_key) for column in table.columns)
            assert columns(actual) == columns(expected)
            assert actual.primary_key.name == expected.primary_key.name == "pk_run_protocol_bindings"
            assert {item.name: str(item.sqltext) for item in actual.constraints if isinstance(item, sa.CheckConstraint)} == {
                item.name: str(item.sqltext) for item in expected.constraints if isinstance(item, sa.CheckConstraint)
            }
            assert dict(actual.dialect_kwargs) == dict(expected.dialect_kwargs)
            signature = await _signature(connection)
            assert signature["columns"] == tuple(column.name for column in orm.RunProtocolBindingRow.__table__.columns)
            assert signature["checks"] == {constraint.name for constraint in orm.RunProtocolBindingRow.__table__.constraints if isinstance(constraint, sa.CheckConstraint)}
            assert signature["foreign_keys"] == {"fk_run_protocol_bindings_revision"}
            assert signature["indexes"] == {"ix_run_protocol_bindings_revision"}
            index = signature["index_details"][0]
            assert index["column_names"] == ["run_id", "continuous_story_line_id", "bound_state_version"]
            assert not index["unique"]
            foreign_key = signature["foreign_key_details"][0]
            assert foreign_key["constrained_columns"] == index["column_names"]
            assert foreign_key["referred_table"] == "run_revisions"
            assert foreign_key["referred_columns"] == ["run_id", "continuous_story_line_id", "state_version"]
            physical = (await connection.execute(sa.text(
                "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, "
                "CHARACTER_SET_NAME, COLLATION_NAME, DATETIME_PRECISION, EXTRA "
                "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() "
                "AND TABLE_NAME='run_protocol_bindings' ORDER BY ORDINAL_POSITION"
            ))).all()
            for column, details in zip(expected.columns, physical, strict=True):
                assert details[0] == column.name and details[2] == "NO" and details[3] is None and details[7] == ""
                if isinstance(column.type, sa.String) and not isinstance(column.type, sa.LargeBinary):
                    assert details[4:6] == ("ascii", "ascii_bin")
                if column.name == "resolution_fingerprint":
                    assert details[1] == "binary(32)"
                if column.name == "created_at":
                    assert details[1] == "datetime(6)" and details[6] == 6
            table_options = (await connection.execute(sa.text(
                "SELECT ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='run_protocol_bindings'"
            ))).one()
            assert tuple(table_options) == ("InnoDB", "utf8mb4_bin")
            rules = (await connection.execute(sa.text(
                "SELECT DELETE_RULE, UPDATE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA=DATABASE() AND CONSTRAINT_NAME='fk_run_protocol_bindings_revision'"
            ))).one()
            assert tuple(rules) == ("RESTRICT", "RESTRICT")
        async with s3db.connect() as connection:
            await _schema_target(connection, CURRENT_HEAD)
        async with AsyncSession(s3db) as session:
            result = await SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert type(result) is LegacyRunCompatibilityV1
            await session.rollback()


async def test_s3_v30_a(s3db):
    async with s3db.connect() as connection:
        trace = await _migrate(connection, "downgrade")
        await connection.commit()
        assert trace == ["drop_constraint", "drop_index", "drop_table"]
    signature, revision = await _observe(s3db)
    assert signature is None and revision == BASE


async def test_s3_v30_b(s3db):
    async with s3db.connect() as connection:
        await _migrate(connection, "downgrade")
        await connection.commit()
        with pytest.raises(sa.exc.ProgrammingError) as caught:
            await _migrate(connection, "downgrade", direct=True)
        assert caught.value.orig.args[0] == 1146
        assert caught.value.cleanup_error is None
        await connection.rollback()
    assert (await _observe(s3db))[0] is None


async def _commit_native(engine, run):
    async with engine.connect() as connection:
        async with AsyncSession(bind=connection, join_transaction_mode="control_fully") as session:
            await _lock(session)
            try:
                await _add_native_binding_row(session, **_inputs(run), flush=True)
                await session.commit()
            finally:
                await _release(session)
                await session.rollback()


async def _refuse(engine, repeats=1):
    async with _parents(engine) as run:
        await _commit_native(engine, run)
        for attempt in range(repeats):
            async with engine.connect() as connection:
                with pytest.raises(RuntimeError) as caught:
                    await _migrate(connection, "downgrade")
                assert str(caught.value) == REFUSAL and caught.value.__cause__ is None
                assert caught.value.cleanup_error is None
                await connection.rollback()
            signature, revision = await _observe(engine)
            assert signature is not None and revision == HEAD and await _count(engine, run) == 1


async def test_s3_v31_a(s3db):
    await _refuse(s3db)


async def test_s3_v31_e(s3db):
    await _refuse(s3db, repeats=2)


async def _kill(engine, owner):
    assert type(owner) is int
    async with engine.connect() as observer:
        await observer.execute(sa.text(f"KILL CONNECTION {owner}"))
        await observer.commit()


class _ConnectionView:
    def __init__(self, sync, engine, owner, *, sql_fault=None, state_check=None, result_override=None, close_failure=False):
        self.sync = sync
        self.engine = engine
        self.owner = owner
        self.sql_fault = sql_fault
        self.state_check = state_check
        self.result_override = result_override
        self.close_failure = close_failure
        self.checks = 0
        self.sql = []
        self.failure = RuntimeError("test statement failure")
        self.observed = None
        self.close_error = RuntimeError("test discard failure")

    def kill(self, *, invalidate):
        from sqlalchemy.util import await_only
        await_only(_kill(self.engine, self.owner))
        if invalidate:
            self.sync.invalidate()

    @property
    def closed(self):
        self.checks += 1
        if self.checks == self.state_check:
            self.kill(invalidate=True)
        return self.sync.closed

    @property
    def invalidated(self):
        return self.sync.invalidated

    def in_transaction(self):
        return self.sync.in_transaction()

    def begin(self):
        return self.sync.begin()

    def execute(self, statement, *args, **kwargs):
        sql = str(statement)
        self.sql.append(sql)
        if self.sql_fault and self.sql_fault[0] in sql:
            if self.sql_fault[1] == "exception":
                self.observed = self.failure
                raise self.failure
            self.kill(invalidate=False)
        try:
            result = self.sync.execute(statement, *args, **kwargs)
        except BaseException as error:
            self.observed = error
            raise
        if self.result_override and self.result_override[0] in sql:
            return SimpleNamespace(scalar_one=lambda: self.result_override[1])
        return result

    def invalidate(self):
        if self.close_failure:
            self.kill(invalidate=False)
            raise self.close_error
        return self.sync.invalidate()

    def close(self):
        return self.sync.close()


async def _body_fault(engine, stage, mode):
    failure = RuntimeError("body sentinel")
    captured = {}
    async with engine.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, engine, owner)
            captured.update(view=view, trace=trace)
            proxy.get_bind = lambda: view
            if stage == "probe":
                if mode == "state":
                    view.state_check = 4
                else:
                    view.sql_fault = ("LIMIT 1 FOR UPDATE", "exception" if mode == "exception" else "disconnect")
                return
            if stage == "before-ddl":
                view.state_check = 5
                return
            target = {"fk": "drop_constraint", "index": "drop_index", "table": "drop_table", "post-table": "drop_table"}[stage]
            if mode == "state" and stage in ("index", "table"):
                preceding = "drop_constraint" if stage == "index" else "drop_index"
                original = getattr(proxy, preceding)
                def after_acknowledgement(*args, **kwargs):
                    result = original(*args, **kwargs)
                    captured["acknowledged"] = preceding
                    view.kill(invalidate=True)
                    return result
                setattr(proxy, preceding, after_acknowledgement)
            elif stage == "post-table":
                original = proxy.drop_table
                def after_table(*args, **kwargs):
                    result = original(*args, **kwargs)
                    view.kill(invalidate=True)
                    return result
                proxy.drop_table = after_table
            else:
                original = getattr(proxy, target)
                def fail(*args, **kwargs):
                    if mode == "exception":
                        trace.append(target)
                        raise failure
                    view.kill(invalidate=False)
                    try:
                        return original(*args, **kwargs)
                    except BaseException as error:
                        view.observed = error
                        raise
                setattr(proxy, target, fail)
        with pytest.raises(Exception) as caught:
            await _migrate(connection, "downgrade", configure=configure)
        view = captured["view"]
        trace = captured["trace"]
        if mode == "exception":
            expected = view.failure if stage == "probe" else failure
            assert caught.value is expected and caught.value.cleanup_error is None
        else:
            codes = {
                ("probe", "state"): "BEFORE_PROBE", ("probe", "disconnect"): "PROBE",
                ("before-ddl", "state"): "BEFORE_DDL",
                ("fk", "disconnect"): "DDL_FK",
                ("index", "disconnect"): "DDL_INDEX", ("index", "state"): "BEFORE_INDEX",
                ("table", "disconnect"): "DDL_TABLE", ("table", "state"): "BEFORE_TABLE",
                ("post-table", "state"): "AFTER_TABLE",
            }
            assert type(caught.value) is RuntimeError
            assert str(caught.value) == "P3.3-S3 downgrade BODY_CONNECTION_LOST_" + codes[stage, mode]
            assert caught.value.__cause__ is (view.observed if mode == "disconnect" else None)
            cleanup = caught.value.cleanup_error
            assert str(cleanup) == "P3.3-S3 downgrade RELEASE_CONNECTION_LOST_BEFORE"
            assert cleanup.__cause__ is caught.value.__cause__
            assert not any("RELEASE_LOCK" in sql for sql in view.sql)
            assert connection.closed or connection.invalidated
        assert trace == {
            "probe": [], "before-ddl": [], "fk": ["drop_constraint"],
            "index": ["drop_constraint"] if mode == "state" else ["drop_constraint", "drop_index"],
            "table": ["drop_constraint", "drop_index"] if mode == "state" else ["drop_constraint", "drop_index", "drop_table"],
            "post-table": ["drop_constraint", "drop_index", "drop_table"],
        }[stage]
        if not connection.closed:
            await connection.rollback()
    signature, revision = await _observe(engine, owner)
    assert revision == HEAD
    if stage == "post-table":
        assert signature is None
    else:
        assert signature is not None
        assert len(signature["checks"]) == 4 and signature["pk"]["constrained_columns"] == ["run_id"]
        assert bool(signature["foreign_keys"]) == (stage in ("probe", "before-ddl", "fk"))
        assert ("ix_run_protocol_bindings_revision" in signature["indexes"]) == (stage not in ("table",))
    await _restore(engine)


async def test_s3_v30_c(s3db):
    for mode in ("exception", "state", "disconnect"):
        await _body_fault(s3db, "probe", mode)


async def test_s3_v30_d1(s3db):
    await _body_fault(s3db, "fk", "exception")
    await _body_fault(s3db, "before-ddl", "state")
    await _body_fault(s3db, "fk", "disconnect")


async def test_s3_v30_d2(s3db):
    for mode in ("exception", "disconnect", "state"):
        await _body_fault(s3db, "index", mode)


async def test_s3_v30_d3(s3db):
    for mode in ("exception", "disconnect", "state"):
        await _body_fault(s3db, "table", mode)


async def _release_fault(engine, mode, body):
    async with _parents(engine) as run:
        if body == "data":
            await _commit_native(engine, run)
        captured = {}
        primary = RuntimeError("protected-body sentinel")
        async with engine.connect() as connection:
            owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def configure(sync, proxy, trace):
                view = _ConnectionView(sync, engine, owner)
                proxy.get_bind = lambda: view
                captured.update(view=view, trace=trace)
                if body == "sentinel":
                    original = view.execute
                    def execute(statement, *args, **kwargs):
                        if "LIMIT 1 FOR UPDATE" in str(statement):
                            view.sql.append(str(statement))
                            raise primary
                        return original(statement, *args, **kwargs)
                    view.execute = execute
                if mode in ("zero", "null", "invalid"):
                    view.result_override = ("RELEASE_LOCK", {"zero": 0, "null": None, "invalid": True}[mode])
                elif mode in ("exception", "disconnect"):
                    view.sql_fault = ("RELEASE_LOCK", mode)
                elif mode == "before":
                    view.state_check = 9 if body == "empty" else 6
                elif mode == "discard":
                    view.result_override = ("RELEASE_LOCK", 0)
                    view.close_failure = True
            with pytest.raises(Exception) as caught:
                await _migrate(connection, "downgrade", configure=configure)
            view = captured["view"]
            selected = caught.value if body == "empty" else caught.value.cleanup_error
            expected_code = {
                "zero": "NOT_OWNER", "null": "NULL", "invalid": "INVALID_RESULT",
                "exception": "STATEMENT_FAILED", "disconnect": "CONNECTION_LOST_PENDING",
                "before": "CONNECTION_LOST_BEFORE", "discard": "NOT_OWNER",
            }[mode]
            assert type(selected) is RuntimeError
            assert str(selected) == "P3.3-S3 downgrade RELEASE_" + expected_code
            assert selected.__cause__ is (view.observed if mode in ("exception", "disconnect") else None)
            if body == "sentinel":
                assert caught.value is primary and caught.value.__cause__ is None
            if body == "data":
                assert str(caught.value) == REFUSAL and caught.value.__cause__ is None
            if mode == "discard":
                assert selected.close_error is view.close_error
            assert connection.closed or connection.invalidated
            assert captured["trace"] == (["drop_constraint", "drop_index", "drop_table"] if body == "empty" else [])
        signature, revision = await _observe(engine, owner)
        assert revision == HEAD and (signature is None) == (body == "empty")
        if body == "data":
            assert await _count(engine, run) == 1
    await _restore(engine)


async def test_s3_v30_e(s3db):
    for mode in ("zero", "null", "invalid", "exception", "disconnect", "before", "discard"):
        for body in ("empty", "sentinel", "data"):
            await _release_fault(s3db, mode, body)
    await _body_fault(s3db, "post-table", "state")
    async with s3db.connect() as holder, s3db.connect() as other:
        await _lock(holder)
        assert await other.scalar(sa.text(f"SELECT RELEASE_LOCK('{LOCK}')")) == 0
        await _release(holder)
        assert await other.scalar(sa.text(f"SELECT RELEASE_LOCK('{LOCK}')")) is None


async def _timeout(engine, repeats):
    async with engine.connect() as holder:
        await _lock(holder)
        try:
            for attempt in range(repeats):
                async with engine.connect() as connection:
                    captured = {}
                    def configure(sync, proxy, trace):
                        view = _ConnectionView(sync, engine, None)
                        captured.update(view=view, trace=trace)
                        proxy.get_bind = lambda: view
                    started = asyncio.get_running_loop().time()
                    with pytest.raises(RuntimeError) as caught:
                        await _migrate(connection, "downgrade", configure=configure)
                    assert asyncio.get_running_loop().time() - started >= 29
                    assert str(caught.value) == "P3.3-S3 downgrade ACQUIRE_TIMEOUT"
                    assert caught.value.__cause__ is None and captured["trace"] == []
                    assert not any("FOR UPDATE" in sql or "RELEASE_LOCK" in sql for sql in captured["view"].sql)
                    assert not connection.closed and not connection.invalidated
                    await connection.rollback()
        finally:
            await _release(holder)
    assert (await _observe(engine))[1] == HEAD


async def test_s3_v31_d(s3db):
    await _timeout(s3db, 1)
    for mode in ("null", "invalid", "exception", "before", "preflight", "preflight-error", "pending", "after", "discard"):
        captured = {}
        async with s3db.connect() as connection:
            owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            await connection.rollback()
            def configure(sync, proxy, trace):
                view = _ConnectionView(sync, s3db, owner)
                proxy.get_bind = lambda: view
                captured.update(view=view, trace=trace)
                if mode in ("null", "invalid"):
                    view.result_override = ("GET_LOCK", None if mode == "null" else True)
                elif mode in ("exception", "pending"):
                    view.sql_fault = ("GET_LOCK", "exception" if mode == "exception" else "disconnect")
                elif mode == "preflight":
                    view.sql_fault = ("CONNECTION_ID", "disconnect")
                elif mode == "preflight-error":
                    view.sql_fault = ("CONNECTION_ID", "exception")
                elif mode == "before":
                    view.state_check = 1
                elif mode == "after":
                    view.state_check = 3
                elif mode == "discard":
                    view.result_override = ("GET_LOCK", None)
                    view.close_failure = True
            with pytest.raises(RuntimeError) as caught:
                await _migrate(connection, "downgrade", configure=configure)
            code = {
                "null": "NULL", "invalid": "INVALID_RESULT", "exception": "STATEMENT_FAILED",
                "before": "CONNECTION_LOST_BEFORE", "preflight": "CONNECTION_LOST_BEFORE",
                "pending": "CONNECTION_LOST_PENDING", "after": "CONNECTION_LOST_AFTER",
                "preflight-error": "STATEMENT_FAILED", "discard": "NULL",
            }[mode]
            assert str(caught.value) == "P3.3-S3 downgrade ACQUIRE_" + code
            assert caught.value.__cause__ is captured["view"].observed
            if mode == "discard":
                assert caught.value.close_error is captured["view"].close_error
            assert not captured["trace"]
            assert not any("FOR UPDATE" in sql or "RELEASE_LOCK" in sql for sql in captured["view"].sql)
            assert connection.closed or connection.invalidated
        signature, revision = await _observe(s3db, owner)
        assert signature is not None and revision == HEAD
    async with s3db.connect() as holder, s3db.connect() as connection:
        await _lock(holder)
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        started = asyncio.Event()
        captured = {}
        def configure(sync, proxy, trace):
            view = _ConnectionView(sync, s3db, owner)
            original = view.execute
            def execute(statement, *args, **kwargs):
                if "GET_LOCK" in str(statement):
                    started.set()
                return original(statement, *args, **kwargs)
            view.execute = execute
            proxy.get_bind = lambda: view
            captured.update(view=view, trace=trace)
        task = asyncio.create_task(_migrate(connection, "downgrade", configure=configure))
        try:
            await asyncio.wait_for(started.wait(), 5)
            await asyncio.sleep(0.25)
            assert not task.done()
            await _kill(s3db, owner)
            with pytest.raises(RuntimeError) as caught:
                await asyncio.wait_for(task, 5)
            assert str(caught.value) == "P3.3-S3 downgrade ACQUIRE_CONNECTION_LOST_PENDING"
            assert caught.value.__cause__ is captured["view"].observed
            assert not captured["trace"]
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await _release(holder)
    assert (await _observe(s3db, owner))[1] == HEAD


async def test_s3_v31_f(s3db):
    await _timeout(s3db, 2)


async def _writer_before(engine, *, old_snapshot, commit):
    async with _parents(engine) as run:
        async with engine.connect() as migration_connection, engine.connect() as writer_connection:
            migration_id = await migration_connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            writer_id = await writer_connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            assert migration_id != writer_id
            await migration_connection.rollback()
            await writer_connection.rollback()
            await migration_connection.execution_options(isolation_level="REPEATABLE READ")
            writer_flushed = asyncio.Event()
            allow_commit = asyncio.Event()
            snapshot_established = asyncio.Event()
            lock_started = asyncio.Event()
            captured = {}
            async def writer():
                async with AsyncSession(bind=writer_connection, join_transaction_mode="control_fully") as session:
                    await _lock(session)
                    try:
                        if old_snapshot:
                            await snapshot_established.wait()
                        await _add_native_binding_row(session, **_inputs(run), flush=True)
                        writer_flushed.set()
                        await allow_commit.wait()
                        if commit:
                            await session.commit()
                        else:
                            await session.rollback()
                    finally:
                        await _release(session)
                        await session.rollback()
            def configure(sync, proxy, trace):
                view = _ConnectionView(sync, engine, migration_id)
                original = view.execute
                def execute(statement, *args, **kwargs):
                    if "GET_LOCK" in str(statement):
                        lock_started.set()
                    return original(statement, *args, **kwargs)
                view.execute = execute
                proxy.get_bind = lambda: view
                captured.update(view=view, trace=trace)
            writer_task = asyncio.create_task(writer())
            migration_task = None
            try:
                if old_snapshot:
                    await migration_connection.begin()
                    assert (await migration_connection.execute(sa.text("SELECT 1 FROM run_protocol_bindings LIMIT 1"))).first() is None
                    snapshot_established.set()
                await asyncio.wait_for(writer_flushed.wait(), 5)
                migration_task = asyncio.create_task(_migrate(migration_connection, "downgrade", configure=configure))
                await asyncio.wait_for(lock_started.wait(), 5)
                await asyncio.sleep(0.25)
                assert not migration_task.done()
                assert captured["trace"] == []
                assert not any("FOR UPDATE" in sql for sql in captured["view"].sql)
                allow_commit.set()
                await asyncio.wait_for(writer_task, 10)
                if commit:
                    with pytest.raises(RuntimeError) as caught:
                        await asyncio.wait_for(migration_task, 10)
                    assert str(caught.value) == REFUSAL and caught.value.__cause__ is None
                    assert caught.value.cleanup_error is None and captured["trace"] == []
                    await migration_connection.rollback()
                else:
                    await asyncio.wait_for(migration_task, 10)
                    await migration_connection.commit()
                    assert captured["trace"] == ["drop_constraint", "drop_index", "drop_table"]
                assert captured["view"].sql.count("SELECT 1 FROM run_protocol_bindings LIMIT 1 FOR UPDATE") == 1
            finally:
                allow_commit.set()
                snapshot_established.set()
                for task in (writer_task, migration_task):
                    if task is not None and not task.done():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
        signature, revision = await _observe(engine)
        if commit:
            assert signature is not None and revision == HEAD
            assert len(signature["columns"]) == 19 and len(signature["checks"]) == 4
            assert signature["foreign_keys"] == {"fk_run_protocol_bindings_revision"}
            assert "ix_run_protocol_bindings_revision" in signature["indexes"]
            assert await _count(engine, run) == 1
            async with AsyncSession(engine) as session:
                row = (await session.execute(sa.select(orm.RunProtocolBindingRow))).scalar_one()
                assert {name: getattr(row, name) for name in _inputs(run)} == _inputs(run)
        else:
            assert signature is None and revision == BASE
    await _restore(engine)


async def test_s3_v31_b(s3db):
    for old_snapshot in (False, True):
        await _writer_before(s3db, old_snapshot=old_snapshot, commit=True)


async def test_s3_v31_c(s3db):
    await _writer_before(s3db, old_snapshot=False, commit=False)


async def _downgrade_before(engine, *, fail):
    async with _parents(engine) as run:
        protected = asyncio.Event()
        allow_ddl = asyncio.Event()
        writer_started = asyncio.Event()
        writer_acquired = asyncio.Event()
        transaction_closed = asyncio.Event()
        insert_started = asyncio.Event()
        primary = RuntimeError("first DDL sentinel")
        captured = {}
        async with engine.connect() as migration_connection, engine.connect() as writer_connection:
            migration_id = await migration_connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            writer_id = await writer_connection.scalar(sa.text("SELECT CONNECTION_ID()"))
            assert migration_id != writer_id
            await migration_connection.rollback()
            await writer_connection.rollback()
            def configure(sync, proxy, trace):
                from sqlalchemy.util import await_only
                original = proxy.drop_constraint
                def pause(*args, **kwargs):
                    protected.set()
                    await_only(allow_ddl.wait())
                    if fail:
                        raise primary
                    return original(*args, **kwargs)
                proxy.drop_constraint = pause
                captured["trace"] = trace
            async def downgrade():
                try:
                    await _migrate(migration_connection, "downgrade", configure=configure)
                    await migration_connection.commit()
                finally:
                    await migration_connection.rollback()
                    transaction_closed.set()
            async def writer():
                async with AsyncSession(bind=writer_connection, join_transaction_mode="control_fully") as session:
                    writer_started.set()
                    await _lock(session)
                    try:
                        writer_acquired.set()
                        await transaction_closed.wait()
                        insert_started.set()
                        if fail:
                            await _add_native_binding_row(session, **_inputs(run), flush=True)
                        else:
                            with pytest.raises(sa.exc.ProgrammingError) as caught:
                                await session.execute(sa.insert(orm.RunProtocolBindingRow).values(**_inputs(run)))
                            assert caught.value.orig.args[0] == 1146
                        await session.rollback()
                    finally:
                        await _release(session)
                        await session.rollback()
            migration_task = asyncio.create_task(downgrade())
            writer_task = None
            try:
                await asyncio.wait_for(protected.wait(), 5)
                writer_task = asyncio.create_task(writer())
                await asyncio.wait_for(writer_started.wait(), 5)
                # Observe the actual server-side GET_LOCK wait on a third
                # connection. The transaction-close barrier cannot prove it.
                async with engine.connect() as observer:
                    assert await observer.scalar(sa.text("SELECT CONNECTION_ID()")) not in (migration_id, writer_id)
                    async with asyncio.timeout(5):
                        while True:
                            process = (await observer.execute(sa.text(
                                "SELECT STATE, INFO FROM information_schema.PROCESSLIST WHERE ID = :id"
                            ), {"id": writer_id})).one()
                            owner = await observer.scalar(sa.text(f"SELECT IS_USED_LOCK('{LOCK}')"))
                            assert not writer_acquired.is_set() and owner != writer_id, "V32 writer acquired lock during protected interval"
                            if process.STATE == "User lock" and process.INFO == f"SELECT GET_LOCK('{LOCK}', 30)":
                                assert owner == migration_id
                                break
                            if writer_task.done():
                                await writer_task
                                pytest.fail("writer ended before observed lock wait")
                assert not insert_started.is_set()
                allow_ddl.set()
                if fail:
                    with pytest.raises(RuntimeError) as caught:
                        await asyncio.wait_for(migration_task, 10)
                    assert caught.value is primary and caught.value.cleanup_error is None
                else:
                    await asyncio.wait_for(migration_task, 10)
                await asyncio.wait_for(writer_task, 10)
                assert writer_acquired.is_set() and insert_started.is_set()
            finally:
                allow_ddl.set()
                tasks = [task for task in (migration_task, writer_task) if task is not None]
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 15)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        signature, revision = await _observe(engine)
        if fail:
            assert signature is not None and revision == HEAD and await _count(engine, run) == 0
        else:
            assert signature is None and revision == BASE
    await _restore(engine)


async def test_s3_v32_a(s3db):
    await _downgrade_before(s3db, fail=False)


async def test_s3_v32_b(s3db):
    await _downgrade_before(s3db, fail=True)
