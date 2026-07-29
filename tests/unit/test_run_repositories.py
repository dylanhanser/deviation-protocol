from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
import inspect
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError, OperationalError

from deviation_protocol.application.ports import (
    RunCreationReceiptRepository,
    RunMutationReceiptRepository,
    RunRepository,
    RunSessionParticipationRepository,
    RunSessionParticipationUniquenessConflictError,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    RunOperationNamespace,
    RunReceiptKey,
    attach_session_to_run,
    construct_created_run,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunSessionParticipationReference,
    RunStateVersion,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunRepositoryError,
    RunStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyRunCreationReceiptRepository,
    SqlAlchemyRunMutationReceiptRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyRunSessionParticipationRepository,
)
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
SOURCE = RunAuthoritySourceRef(value="source.run-repository")
RUN_ID = RunId(value="run.repository")
LINE_ID = ContinuousStoryLineId(value="csl.repository")


def _created():
    return construct_created_run(
        CreateRunCommand(source_reference=SOURCE),
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.create"),
        occurred_at=NOW,
    )


class _SessionProbe:
    def __init__(self) -> None:
        self.no_autoflush = nullcontext()
        self.scalar_results: list[Any] = []
        self.scalars_results: list[list[Any]] = []
        self.scalar_statements: list[Any] = []
        self.execute_result: Any = SimpleNamespace(rowcount=1)
        self.execute_statements: list[Any] = []
        self.added: list[Any] = []
        self.flush_calls: list[tuple[Any, ...]] = []
        self.scalar_error: BaseException | None = None
        self.flush_error: BaseException | None = None

    async def scalar(self, statement: Any) -> Any:
        self.scalar_statements.append(statement)
        if self.scalar_error is not None:
            raise self.scalar_error
        return self.scalar_results.pop(0) if self.scalar_results else None

    async def scalars(self, statement: Any) -> Any:
        self.scalar_statements.append(statement)
        rows = self.scalars_results.pop(0) if self.scalars_results else []
        return SimpleNamespace(all=lambda: rows)

    async def execute(self, statement: Any) -> Any:
        self.execute_statements.append(statement)
        return self.execute_result

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def flush(self, rows: tuple[Any, ...]) -> None:
        self.flush_calls.append(rows)
        if self.flush_error is not None:
            raise self.flush_error


@pytest.mark.parametrize(
    ("adapter", "port"),
    (
        (SqlAlchemyRunRepository, RunRepository),
        (
            SqlAlchemyRunSessionParticipationRepository,
            RunSessionParticipationRepository,
        ),
        (
            SqlAlchemyRunCreationReceiptRepository,
            RunCreationReceiptRepository,
        ),
        (
            SqlAlchemyRunMutationReceiptRepository,
            RunMutationReceiptRepository,
        ),
    ),
)
def test_run_repository_adapters_match_exact_port_signatures(
    adapter: type[Any],
    port: type[Any],
) -> None:
    assert issubclass(adapter, port)
    for method_name in port.__abstractmethods__:
        assert inspect.signature(getattr(adapter, method_name)) == (
            inspect.signature(getattr(port, method_name))
        )


@pytest.mark.asyncio
async def test_add_initial_flushes_revision_then_current_without_commit() -> None:
    session = _SessionProbe()
    repository = SqlAlchemyRunRepository(session)

    await repository.add_initial(_created(), created_at=NOW)

    assert len(session.added) == 2
    assert session.added[0].__tablename__ == "run_revisions"
    assert session.added[1].__tablename__ == "run_current"
    assert session.flush_calls == [
        (session.added[0],),
        (session.added[1],),
    ]
    assert session.added[1].active_player_character_id is None


@pytest.mark.asyncio
async def test_get_for_update_targets_exact_run_and_missing_is_exact_none() -> None:
    session = _SessionProbe()
    repository = SqlAlchemyRunRepository(session)

    assert await repository.get_for_update(RUN_ID) is None

    compiled = str(
        session.scalar_statements[0].compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "FOR UPDATE" in compiled
    assert f"= '{RUN_ID.value}'" in compiled
    assert len(session.scalar_statements) == 5


@pytest.mark.asyncio
async def test_missing_current_with_revision_evidence_is_corruption() -> None:
    session = _SessionProbe()
    session.scalar_results.extend((None, RUN_ID.value))
    repository = SqlAlchemyRunRepository(session)

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="current Run row is missing",
    ):
        await repository.get(RUN_ID)


@pytest.mark.asyncio
async def test_participation_duplicate_is_narrow_typed_conflict() -> None:
    session = _SessionProbe()
    participation = RunSessionParticipationReference(
        session_id="session.repository",
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        joined_state_version=RunStateVersion(value=2),
        operation_id=RunOperationId(value="operation.attach"),
        source_reference=SOURCE,
    )
    attached = attach_session_to_run(
        _created(),
        AttachSessionCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            session_id=participation.session_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=SOURCE,
        ),
        operation_id=participation.operation_id,
        occurred_at=NOW,
    )
    revision = SqlAlchemyRunRepository._run_revision_row(
        attached,
        created_at=NOW,
    )
    session.scalar_results.append(revision)
    session.flush_error = IntegrityError(
        "INSERT",
        {},
        Exception(1062, "opaque duplicate"),
    )
    repository = SqlAlchemyRunSessionParticipationRepository(session)
    with pytest.raises(RunSessionParticipationUniquenessConflictError):
        await repository.add(participation, joined_at=NOW)


@pytest.mark.asyncio
async def test_run_repository_read_failure_is_sanitized_and_chained() -> None:
    session = _SessionProbe()
    session.scalar_error = OperationalError(
        "SELECT",
        {},
        Exception(2013, "secret server diagnostic"),
    )
    repository = SqlAlchemyRunRepository(session)

    with pytest.raises(RunRepositoryError) as exc_info:
        await repository.get(RUN_ID)

    assert exc_info.value.__cause__ is session.scalar_error
    assert "secret server diagnostic" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_mutation_receipt_repository_rejects_reserved_namespace() -> None:
    repository = SqlAlchemyRunMutationReceiptRepository(_SessionProbe())
    key = RunReceiptKey(
        run_id=RunId(value="run.reserved"),
        operation_namespace=RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
        operation_id=RunOperationId(value="operation.reserved"),
    )

    with pytest.raises(ValueError, match="rejects namespace"):
        await repository.get(key)
