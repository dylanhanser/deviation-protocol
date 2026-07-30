from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    RunReplayDecision,
    RunReplayDecisionCode,
)
from deviation_protocol.application.run_service import (
    RunService,
    RunServiceDecision,
    RunServiceDecisionCode,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.infrastructure.orm_models import (
    Base,
    GameSessionRow,
    RunCreationReceiptRow,
    RunCurrentRow,
    RunMutationReceiptRow,
    RunRevisionRow,
    RunSessionParticipationRow,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "alembic"
    / "versions"
    / "20260729_0005_minimum_run_core.py"
)
RUN_TABLES = (
    "run_revisions",
    "run_current",
    "run_session_participations",
    "run_creation_receipts",
    "run_mutation_receipts",
)
NOW = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
SOURCE = RunAuthoritySourceRef(value="source.mysql-run")


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"minimum_run_core_{uuid4().hex}",
        MIGRATION,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _MigrationRecorder:
    def __init__(self) -> None:
        self.metadata = sa.MetaData()
        sa.Table(
            "game_sessions",
            self.metadata,
            sa.Column(
                "session_id",
                mysql.VARCHAR(
                    64,
                    charset="utf8mb4",
                    collation="utf8mb4_0900_ai_ci",
                ),
                primary_key=True,
            ),
        )
        sa.Table(
            "player_character_revisions",
            self.metadata,
            sa.Column(
                "player_character_id",
                mysql.VARCHAR(128, charset="ascii", collation="ascii_bin"),
                primary_key=True,
            ),
            sa.Column("record_revision", sa.BigInteger(), primary_key=True),
        )
        self.events: list[tuple[str, ...]] = []

    def create_table(self, name: str, *elements: Any, **options: Any) -> None:
        self.events.append(("create_table", name))
        sa.Table(name, self.metadata, *elements, **options)

    def create_index(
        self,
        name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        unique: bool = False,
        **_: Any,
    ) -> None:
        self.events.append(("create_index", name, table_name))
        table = self.metadata.tables[table_name]
        sa.Index(
            name,
            *(table.c[column] for column in columns),
            unique=unique,
        )

    def create_foreign_key(
        self,
        name: str,
        source: str,
        target: str,
        local: tuple[str, ...],
        remote: tuple[str, ...],
        **options: Any,
    ) -> None:
        self.events.append(("create_foreign_key", name, source))
        self.metadata.tables[source].append_constraint(
            sa.ForeignKeyConstraint(
                local,
                tuple(f"{target}.{column}" for column in remote),
                name=name,
                ondelete=options.get("ondelete"),
                onupdate=options.get("onupdate"),
            )
        )


def _table_signature(table: sa.Table) -> tuple[Any, ...]:
    dialect = mysql.dialect()
    columns = tuple(
        (
            column.name,
            column.type.compile(dialect=dialect).upper(),
            column.nullable,
            column.primary_key,
        )
        for column in table.columns
    )
    uniques = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
        and constraint.name is not None
    }
    checks = {
        constraint.name: " ".join(str(constraint.sqltext).split())
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
        and constraint.name is not None
    }
    indexes = {
        index.name: tuple(column.name for column in index.columns)
        for index in table.indexes
    }
    foreign_keys = {
        constraint.name: (
            tuple(column.name for column in constraint.columns),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
            constraint.ondelete,
            constraint.onupdate,
        )
        for constraint in table.foreign_key_constraints
    }
    return columns, uniques, checks, indexes, foreign_keys


def test_run_migration_matches_shared_metadata_and_is_linear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    recorder = _MigrationRecorder()
    monkeypatch.setattr(migration.op, "create_table", recorder.create_table)
    monkeypatch.setattr(migration.op, "create_index", recorder.create_index)
    monkeypatch.setattr(
        migration.op,
        "create_foreign_key",
        recorder.create_foreign_key,
    )
    migration.upgrade()

    assert tuple(
        name for name in recorder.metadata.tables if name in RUN_TABLES
    ) == RUN_TABLES
    for table_name in RUN_TABLES:
        assert _table_signature(recorder.metadata.tables[table_name]) == (
            _table_signature(Base.metadata.tables[table_name])
        )
    first_foreign_key = next(
        index
        for index, event in enumerate(recorder.events)
        if event[0] == "create_foreign_key"
    )
    assert all(
        event[0] != "create_index"
        for event in recorder.events[first_foreign_key:]
    )

    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["20260729_0005"]
    revision = scripts.get_revision("20260729_0005")
    assert revision is not None
    assert revision.down_revision == "20260728_0004"


class _DowngradeResult:
    def __init__(self, value: int | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> int | None:
        return self.value


class _DowngradeConnection:
    def __init__(self, populated: str | None) -> None:
        self.populated = populated
        self.probed: list[str] = []

    def execute(self, statement: Any) -> _DowngradeResult:
        sql = str(statement)
        table_name = next(name for name in RUN_TABLES if name in sql)
        self.probed.append(table_name)
        return _DowngradeResult(
            1 if table_name == self.populated else None
        )


def test_run_migration_downgrade_refuses_data_before_destructive_ddl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    connection = _DowngradeConnection("run_current")
    destructive: list[str] = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda *args, **kwargs: destructive.append("constraint"),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_index",
        lambda *args, **kwargs: destructive.append("index"),
    )
    monkeypatch.setattr(
        migration.op,
        "drop_table",
        lambda *args, **kwargs: destructive.append("table"),
    )

    with pytest.raises(RuntimeError, match="recovery must be forward-only"):
        migration.downgrade()

    assert connection.probed == list(RUN_TABLES)
    assert destructive == []


def _safe_database_url() -> str:
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("TEST_DATABASE_URL is not configured; no SQLite fallback is used")
    parsed = make_url(value)
    if (
        parsed.drivername != "mysql+asyncmy"
        or parsed.database != "deviation_protocol_test"
    ):
        pytest.fail("Run integration tests require the designated async MySQL test database")
    return value


@pytest.mark.integration
def test_mysql_run_migration_upgrades_only_the_designated_test_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", _safe_database_url())
    command.upgrade(Config(str(ROOT / "alembic.ini")), "20260729_0005")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_run_schema_is_exact_and_binding_seam_is_nullable(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with mysql_session_factory() as session:
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        tables = set(
            (
                await session.execute(
                    text(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME LIKE 'run_%'"
                    )
                )
            ).scalars()
        )
        nullable_binding_columns = set(
            (
                await session.execute(
                    text(
                        "SELECT TABLE_NAME, COLUMN_NAME "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME IN ('run_current', 'run_revisions') "
                        "AND COLUMN_NAME LIKE 'binding_%' "
                        "AND IS_NULLABLE = 'YES'"
                    )
                )
            ).all()
        )
        game_session_run_columns = set(
            (
                await session.execute(
                    text(
                        "SELECT COLUMN_NAME "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME = 'game_sessions' "
                        "AND COLUMN_NAME IN "
                        "('run_id', 'continuous_story_line_id', "
                        "'player_character_id', 'active_player_character_id')"
                    )
                )
            ).scalars()
        )

    assert revision == "20260729_0005"
    assert tables == set(RUN_TABLES)
    assert game_session_run_columns == set()
    expected_binding_columns = {
        "binding_player_character_id",
        "binding_contract_version",
        "binding_record_revision",
        "binding_state",
        "binding_operation_id",
        "binding_authority_source_ref",
    }
    assert nullable_binding_columns == {
        (table, column)
        for table in ("run_current", "run_revisions")
        for column in expected_binding_columns
    }


class _Issuer:
    def __init__(self, value: RunId | ContinuousStoryLineId) -> None:
        self.value = value
        self.calls = 0

    def issue(self):
        self.calls += 1
        return self.value


def _service(
    factory: async_sessionmaker[AsyncSession],
    *,
    run_id: RunId,
    line_id: ContinuousStoryLineId,
    uow_type: type[SqlAlchemyUnitOfWork] = SqlAlchemyUnitOfWork,
) -> RunService:
    return RunService(
        uow_factory=lambda: uow_type(factory),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=SOURCE,
        clock=lambda: NOW,
        controller_binding_resolver=object(),  # type: ignore[arg-type]
        player_character_binding_evidence=object(),  # type: ignore[arg-type]
    )


@dataclass(slots=True)
class _RunScope:
    token: str
    run_ids: list[str] = field(default_factory=list)
    session_ids: list[str] = field(default_factory=list)

    def run_id(self, suffix: str) -> RunId:
        value = f"run.it-{self.token}-{suffix}"
        self.run_ids.append(value)
        return RunId(value=value)

    def line_id(self, suffix: str) -> ContinuousStoryLineId:
        return ContinuousStoryLineId(value=f"csl.it-{self.token}-{suffix}")

    def session_id(self, suffix: str) -> str:
        value = f"it-run-{self.token}-{suffix}"
        self.session_ids.append(value)
        return value


@pytest.fixture
async def run_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> Any:
    scope = _RunScope(token=uuid4().hex)
    try:
        yield scope
    finally:
        async with mysql_session_factory.begin() as session:
            if scope.run_ids:
                await session.execute(
                    delete(RunMutationReceiptRow).where(
                        RunMutationReceiptRow.run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    delete(RunCreationReceiptRow).where(
                        RunCreationReceiptRow.result_run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    delete(RunCurrentRow).where(
                        RunCurrentRow.run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    delete(RunSessionParticipationRow).where(
                        RunSessionParticipationRow.run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    delete(RunRevisionRow).where(
                        RunRevisionRow.run_id.in_(scope.run_ids)
                    )
                )
            if scope.session_ids:
                await session.execute(
                    delete(GameSessionRow).where(
                        GameSessionRow.session_id.in_(scope.session_ids)
                    )
                )


async def _add_session(
    factory: async_sessionmaker[AsyncSession],
    session_id: str,
) -> None:
    async with factory.begin() as session:
        session.add(
            GameSessionRow(
                session_id=session_id,
                player_id="run-integration-player",
                scenario_id="run-integration-scenario",
                scenario_version="1",
                phase="AWAITING_ACTION",
                turn_number=0,
                state_version=0,
                random_seed=42,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def _principal() -> RequestPrincipal:
    return RequestPrincipal(
        player_id="run-integration-player",
        authentication_scheme="integration",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_run_create_attach_reload_replay_and_conflict_are_atomic(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    run_scope: _RunScope,
) -> None:
    run_id = run_scope.run_id("round-trip")
    line_id = run_scope.line_id("round-trip")
    session_id = run_scope.session_id("round-trip")
    await _add_session(mysql_session_factory, session_id)
    service = _service(mysql_session_factory, run_id=run_id, line_id=line_id)
    create_operation = RunOperationId(value=f"operation.{run_scope.token}.create")
    create_command = CreateRunCommand(source_reference=SOURCE)

    created = await service.create_run(
        operation_id=create_operation,
        command=create_command,
    )
    replayed = await service.create_run(
        operation_id=create_operation,
        command=create_command,
    )
    assert replayed == created

    attach_operation = RunOperationId(value=f"operation.{run_scope.token}.attach")
    attach_command = AttachSessionCommand(
        run_id=run_id,
        continuous_story_line_id=line_id,
        session_id=session_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    attached = await service.attach_session(
        _principal(),
        operation_id=attach_operation,
        command=attach_command,
    )
    assert attached.resulting_state_version == RunStateVersion(value=2)
    assert (
        await service.attach_session(
            _principal(),
            operation_id=attach_operation,
            command=attach_command,
        )
        == attached
    )
    conflict = await service.attach_session(
        _principal(),
        operation_id=attach_operation,
        command=attach_command.model_copy(
            update={"expected_state_version": RunStateVersion(value=2)}
        ),
    )
    assert isinstance(conflict, RunReplayDecision)
    assert conflict.code is RunReplayDecisionCode.CONFLICT

    reloaded = await service.get_run(run_id=run_id)
    assert reloaded is not None
    assert reloaded.state_version == RunStateVersion(value=2)
    assert reloaded.player_character_binding is None
    assert tuple(
        item.session_id for item in reloaded.trusted_participation_references
    ) == (session_id,)


class _PreCommitFailureUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("controlled pre-COMMIT failure")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_run_pre_commit_failure_rolls_back_all_families(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    run_scope: _RunScope,
) -> None:
    run_id = run_scope.run_id("rollback")
    service = _service(
        mysql_session_factory,
        run_id=run_id,
        line_id=run_scope.line_id("rollback"),
        uow_type=_PreCommitFailureUnitOfWork,
    )

    with pytest.raises(RuntimeError, match="pre-COMMIT"):
        await service.create_run(
            operation_id=RunOperationId(
                value=f"operation.{run_scope.token}.rollback"
            ),
            command=CreateRunCommand(source_reference=SOURCE),
        )

    async with mysql_session_factory() as session:
        counts_list = []
        for row_type in (
            RunRevisionRow,
            RunCurrentRow,
            RunCreationReceiptRow,
        ):
            counts_list.append(
                await session.scalar(
                    select(func.count()).select_from(row_type).where(
                        (
                            row_type.result_run_id
                            if row_type is RunCreationReceiptRow
                            else row_type.run_id
                    )
                        == run_id.value
                    )
                )
            )
    assert tuple(counts_list) == (0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_same_run_concurrency_has_one_version_two_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    run_scope: _RunScope,
) -> None:
    run_id = run_scope.run_id("race")
    line_id = run_scope.line_id("race")
    first_session = run_scope.session_id("race-a")
    second_session = run_scope.session_id("race-b")
    await _add_session(mysql_session_factory, first_session)
    await _add_session(mysql_session_factory, second_session)
    service = _service(mysql_session_factory, run_id=run_id, line_id=line_id)
    await service.create_run(
        operation_id=RunOperationId(value=f"operation.{run_scope.token}.race-create"),
        command=CreateRunCommand(source_reference=SOURCE),
    )

    async def attach(label: str, session_id: str) -> object:
        return await service.attach_session(
            _principal(),
            operation_id=RunOperationId(
                value=f"operation.{run_scope.token}.race-{label}"
            ),
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=1),
                source_reference=SOURCE,
            ),
        )

    results = await asyncio.gather(
        attach("a", first_session),
        attach("b", second_session),
    )
    successes = [
        item
        for item in results
        if not isinstance(item, RunServiceDecision)
    ]
    conflicts = [
        item
        for item in results
        if isinstance(item, RunServiceDecision)
        and item.code is RunServiceDecisionCode.STALE_VERSION
    ]
    assert len(successes) == len(conflicts) == 1
    reloaded = await service.get_run(run_id=run_id)
    assert reloaded is not None
    assert reloaded.state_version == RunStateVersion(value=2)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_cross_run_session_claim_has_one_atomic_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    run_scope: _RunScope,
) -> None:
    first_run_id = run_scope.run_id("cross-a")
    second_run_id = run_scope.run_id("cross-b")
    first_line_id = run_scope.line_id("cross-a")
    second_line_id = run_scope.line_id("cross-b")
    session_id = run_scope.session_id("cross")
    await _add_session(mysql_session_factory, session_id)
    first_service = _service(
        mysql_session_factory,
        run_id=first_run_id,
        line_id=first_line_id,
    )
    second_service = _service(
        mysql_session_factory,
        run_id=second_run_id,
        line_id=second_line_id,
    )
    await first_service.create_run(
        operation_id=RunOperationId(
            value=f"operation.{run_scope.token}.cross-create-a"
        ),
        command=CreateRunCommand(source_reference=SOURCE),
    )
    await second_service.create_run(
        operation_id=RunOperationId(
            value=f"operation.{run_scope.token}.cross-create-b"
        ),
        command=CreateRunCommand(source_reference=SOURCE),
    )

    async def attach(
        service: RunService,
        run_id: RunId,
        line_id: ContinuousStoryLineId,
        suffix: str,
    ) -> object:
        return await service.attach_session(
            _principal(),
            operation_id=RunOperationId(
                value=f"operation.{run_scope.token}.cross-{suffix}"
            ),
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=1),
                source_reference=SOURCE,
            ),
        )

    results = await asyncio.gather(
        attach(first_service, first_run_id, first_line_id, "a"),
        attach(second_service, second_run_id, second_line_id, "b"),
    )
    conflicts = [
        item
        for item in results
        if isinstance(item, RunServiceDecision)
        and item.code
        is RunServiceDecisionCode.SESSION_PARTICIPATION_CONFLICT
    ]
    assert len(conflicts) == 1
    versions = (
        (await first_service.get_run(run_id=first_run_id)).state_version,
        (await second_service.get_run(run_id=second_run_id)).state_version,
    )
    assert sorted(version.value for version in versions) == [1, 2]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_run_reconstruction_rejects_cross_row_corruption(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    run_scope: _RunScope,
) -> None:
    run_id = run_scope.run_id("corrupt")
    line_id = run_scope.line_id("corrupt")
    service = _service(mysql_session_factory, run_id=run_id, line_id=line_id)
    await service.create_run(
        operation_id=RunOperationId(value=f"operation.{run_scope.token}.corrupt"),
        command=CreateRunCommand(source_reference=SOURCE),
    )
    async with mysql_session_factory.begin() as session:
        await session.execute(
            update(RunCurrentRow)
            .where(RunCurrentRow.run_id == run_id.value)
            .values(
                creation_source_reference="source.corrupted",
                source_reference="source.corrupted",
            )
        )
    try:
        with pytest.raises(
            RunStoredRecordIntegrityError,
            match="latest immutable revision",
        ):
            await service.get_run(run_id=run_id)
    finally:
        async with mysql_session_factory.begin() as session:
            await session.execute(
                update(RunCurrentRow)
                .where(RunCurrentRow.run_id == run_id.value)
                .values(
                    creation_source_reference=SOURCE.value,
                    source_reference=SOURCE.value,
                )
            )
