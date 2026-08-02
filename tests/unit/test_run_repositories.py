from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
import inspect
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError, OperationalError

from deviation_protocol.application.ports import (
    GameSessionRepository,
    RunCreationReceiptRepository,
    RunMutationReceiptRepository,
    RunRepository,
    RunSessionParticipationRepository,
    RunSessionParticipationUniquenessConflictError,
    RunPlayerCharacterBindingUniquenessConflictError,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunEntryCreationEvidence,
    RunOperationNamespace,
    RunReceiptKey,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
    bind_player_character_fingerprint,
    bind_player_character_result,
    bind_player_character_to_run,
    construct_created_run,
    create_run_fingerprint,
    creation_result,
    run_entry_creation_fingerprint,
    run_entry_evidence_bytes,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunMutationKind,
    RunSessionParticipationReference,
    RunStateVersion,
)
from deviation_protocol.application.run_operations import StoredRunSuccessReceipt
from deviation_protocol.infrastructure.run_persistence import (
    RunRepositoryError,
    RunStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyGameSessionRepository,
    SqlAlchemyPlayerCharacterRepository,
    SqlAlchemyRunCreationReceiptRepository,
    SqlAlchemyRunMutationReceiptRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyRunSessionParticipationRepository,
)
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
SOURCE = RunAuthoritySourceRef(value="source.run-repository")
RUN_ID = RunId(value="run.repository")
LINE_ID = ContinuousStoryLineId(value="csl.repository")
PLAYER_CHARACTER_ID = PlayerCharacterId(value="pc.repository")
CONTROLLER_BINDING = ControllerBindingRef(value="binding.repository")
CHARACTER_SOURCE = AuthoritySourceRef(value="source.character-repository")
CHARACTER_REFERENCE = ApplicableCharacterReference(
    player_character_id=PLAYER_CHARACTER_ID,
    contract_version=PlayerCharacterContractVersion.V1,
    record_revision=PlayerCharacterRevision(value=1),
)


def _active_character():
    return CreatePlayerCharacterPolicy().create(
        player_character_id=PLAYER_CHARACTER_ID,
        controller_binding=CONTROLLER_BINDING,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=CHARACTER_SOURCE,
    )


def _referenced_revision_row(record=None):
    return SqlAlchemyPlayerCharacterRepository._revision_row(
        record or _active_character(),
        created_at=NOW,
    )


def _retired_character():
    active = _active_character()
    return active.detached_validated_copy(
        record_revision=PlayerCharacterRevision(value=2),
        lifecycle=PlayerCharacterLifecycle.RETIRED,
        authority_provenance=AuthorityProvenance(
            target_player_character_id=PLAYER_CHARACTER_ID,
            prior_revision=PlayerCharacterRevision(value=1),
            resulting_revision=PlayerCharacterRevision(value=2),
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            authority_class=(
                PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
            ),
            source_reference=CHARACTER_SOURCE,
        ),
    )


def _created():
    return construct_created_run(
        CreateRunCommand(source_reference=SOURCE),
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.create"),
        occurred_at=NOW,
    )


def _bound():
    return bind_player_character_to_run(
        _created(),
        BindPlayerCharacterCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            target_player_character_id=PLAYER_CHARACTER_ID,
            expected_state_version=RunStateVersion(value=1),
            source_reference=SOURCE,
        ),
        applicable_character_reference=CHARACTER_REFERENCE,
        operation_id=RunOperationId(value="operation.bind"),
        occurred_at=NOW,
    )


async def _stored_creation_receipt_row() -> Any:
    created = _created()
    command = CreateRunCommand(source_reference=SOURCE)
    _, fingerprint = create_run_fingerprint(command)
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=RunOperationId(value="operation.create"),
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.CREATE,
        result=creation_result(created),
    )
    session = _SessionProbe()
    repository = SqlAlchemyRunCreationReceiptRepository(session)
    repository._run_at_revision = AsyncMock(  # type: ignore[method-assign]
        return_value=created
    )
    repository._validate_complete_run = AsyncMock(  # type: ignore[method-assign]
        return_value=created
    )
    await repository.add(receipt, created_at=NOW)
    return session.added[0]


async def _stored_attachment_evidence(
    *,
    session_id: str = "session.repository",
    operation_id: RunOperationId | None = None,
) -> tuple[Any, Any, Any, Any]:
    operation_id = operation_id or RunOperationId(
        value="operation.attach"
    )
    before = _created()
    command = AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id=session_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    after = attach_session_to_run(
        before,
        command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    _, fingerprint = attach_session_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(after),
    )
    receipt_session = _SessionProbe()
    receipt_repository = SqlAlchemyRunMutationReceiptRepository(
        receipt_session
    )
    receipt_repository._run_at_revision = AsyncMock(  # type: ignore[method-assign]
        side_effect=(before, after)
    )
    receipt_repository._validate_complete_run = AsyncMock(  # type: ignore[method-assign]
        return_value=after
    )
    await receipt_repository.add(receipt, created_at=NOW)
    participation = after.trusted_participation_references[-1]
    participation_row = SimpleNamespace(
        session_id=participation.session_id,
        run_id=participation.run_id.value,
        continuous_story_line_id=(
            participation.continuous_story_line_id.value
        ),
        joined_state_version=participation.joined_state_version.value,
        operation_id=participation.operation_id.value,
        source_reference=participation.source_reference.value,
        joined_at=NOW,
    )
    return before, after, participation_row, receipt_session.added[0]


async def _stored_mutation_receipt_row(
    before: Any,
    after: Any,
    command: AttachSessionCommand | BindPlayerCharacterCommand,
    *,
    operation_id: RunOperationId,
) -> Any:
    if isinstance(command, AttachSessionCommand):
        _, fingerprint = attach_session_fingerprint(
            command,
            operation_id=operation_id,
        )
        namespace = RunOperationNamespace.ATTACH_SESSION_V1
        kind = RunMutationKind.ATTACH_SESSION
        result = attach_session_result(after)
    else:
        _, fingerprint = bind_player_character_fingerprint(
            command,
            operation_id=operation_id,
        )
        namespace = RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
        kind = RunMutationKind.BIND_PLAYER_CHARACTER
        result = bind_player_character_result(after)
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=namespace,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=kind,
        result=result,
    )
    session = _SessionProbe()
    repository = SqlAlchemyRunMutationReceiptRepository(session)
    repository._run_at_revision = AsyncMock(  # type: ignore[method-assign]
        side_effect=(before, after)
    )
    repository._validate_complete_run = AsyncMock(  # type: ignore[method-assign]
        return_value=after
    )
    await repository.add(
        receipt,
        created_at=after.current_mutation_provenance.occurred_at,
    )
    return session.added[0]


async def _stored_bound_then_attached_family(
    *,
    reference: ApplicableCharacterReference = CHARACTER_REFERENCE,
    referenced_record=None,
) -> dict[str, Any]:
    created = _created()
    bind_operation = RunOperationId(value="operation.bind")
    bind_command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=created.state_version,
        source_reference=SOURCE,
    )
    bound = bind_player_character_to_run(
        created,
        bind_command,
        applicable_character_reference=reference,
        operation_id=bind_operation,
        occurred_at=NOW + timedelta(seconds=1),
    )
    attach_operation = RunOperationId(value="operation.attach-after-bind")
    attach_command = AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id="session.repository-after-bind",
        expected_state_version=bound.state_version,
        source_reference=SOURCE,
    )
    attached = attach_session_to_run(
        bound,
        attach_command,
        operation_id=attach_operation,
        occurred_at=NOW + timedelta(seconds=2),
    )
    participation = attached.trusted_participation_references[-1]
    current_row = SqlAlchemyRunRepository._current_run_row(
        attached,
        created_at=NOW,
    )
    current_row.updated_at = NOW + timedelta(seconds=2)
    return {
        "created": created,
        "bound": bound,
        "attached": attached,
        "current": current_row,
        "revisions": [
            SqlAlchemyRunRepository._run_revision_row(
                created,
                created_at=NOW,
            ),
            SqlAlchemyRunRepository._run_revision_row(
                bound,
                created_at=NOW + timedelta(seconds=1),
            ),
            SqlAlchemyRunRepository._run_revision_row(
                attached,
                created_at=NOW + timedelta(seconds=2),
            ),
        ],
        "participations": [
            SimpleNamespace(
                session_id=participation.session_id,
                run_id=participation.run_id.value,
                continuous_story_line_id=(
                    participation.continuous_story_line_id.value
                ),
                joined_state_version=(
                    participation.joined_state_version.value
                ),
                operation_id=participation.operation_id.value,
                source_reference=participation.source_reference.value,
                joined_at=NOW + timedelta(seconds=2),
            )
        ],
        "creation_receipt": await _stored_creation_receipt_row(),
        "mutation_receipts": [
            await _stored_mutation_receipt_row(
                created,
                bound,
                bind_command,
                operation_id=bind_operation,
            ),
            await _stored_mutation_receipt_row(
                bound,
                attached,
                attach_command,
                operation_id=attach_operation,
            ),
        ],
        "receipt_key": RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=attach_operation,
        ),
        "referenced_revision": _referenced_revision_row(
            referenced_record
        ),
    }


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
        self.execute_error: BaseException | None = None

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
        if self.execute_error is not None:
            raise self.execute_error
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
async def test_current_snapshot_port_fails_closed_and_sql_is_a_current_locking_read() -> None:
    with pytest.raises(NotImplementedError):
        await GameSessionRepository.get_latest_snapshot_for_update(
            object(), "session.entry"
        )

    row = SimpleNamespace(state_version=7, state_json={"schema_version": 3})
    session = _SessionProbe()
    session.scalar_results.append(row)
    result = await SqlAlchemyGameSessionRepository(
        session
    ).get_latest_snapshot_for_update("session.entry")

    assert result is not None
    assert result.state_version == 7
    statement = session.scalar_statements[0]
    compiled = str(
        statement.compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "game_snapshots.session_id = 'session.entry'" in compiled
    assert "FOR UPDATE" in compiled
    assert statement.get_execution_options()["populate_existing"] is True


@pytest.mark.asyncio
async def test_composite_creation_receipt_is_written_and_reloaded_exactly() -> None:
    created = _created()
    evidence = RunEntryCreationEvidence.model_validate(
        {
            "controller_operation": {
                "controller_binding": {"value": "controller.example"},
                "public_operation_key": "entry.example",
            },
            "player_character": {
                "player_character_id": {"value": "pc.example"},
                "pre_entry_record_revision": {"value": 1},
            },
            "scenario": {
                "scenario_id": "death_certificate",
                "content_version": "death-certificate-1.1.0",
                "default_character_definition_id": (
                    "character.death_certificate.investigator"
                ),
            },
            "trusted_run_source": {
                "source_reference": {"value": SOURCE.value}
            },
        }
    )
    _, fingerprint = run_entry_creation_fingerprint(evidence)
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=created.creation_provenance.operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.CREATE,
        result=creation_result(created),
    )
    write_session = _SessionProbe()
    repository = SqlAlchemyRunCreationReceiptRepository(write_session)
    repository._run_at_revision = AsyncMock(return_value=created)  # type: ignore[method-assign]
    repository._validate_complete_run = AsyncMock(return_value=created)  # type: ignore[method-assign]
    await repository.add_with_evidence(receipt, evidence, created_at=NOW)

    row = write_session.added[0]
    assert row.operation_evidence_canonical == run_entry_evidence_bytes(evidence)
    assert len(row.operation_evidence_canonical) <= 4096
    assert write_session.flush_calls == [(row,)]

    read_session = _SessionProbe()
    read_session.scalar_results.append(row)
    reader = SqlAlchemyRunCreationReceiptRepository(read_session)
    reader._run_at_revision = AsyncMock(return_value=created)  # type: ignore[method-assign]
    reader._validate_complete_run = AsyncMock(return_value=created)  # type: ignore[method-assign]
    stored = await reader.get_with_evidence(receipt.key)

    assert stored is not None
    assert stored.receipt == receipt
    assert stored.evidence == evidence
    assert stored.evidence_canonical == run_entry_evidence_bytes(evidence)


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
async def test_mutation_receipt_repository_admits_internal_binding_namespace() -> None:
    session = _SessionProbe()
    repository = SqlAlchemyRunMutationReceiptRepository(session)
    key = RunReceiptKey(
        run_id=RunId(value="run.reserved"),
        operation_namespace=RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
        operation_id=RunOperationId(value="operation.reserved"),
    )

    assert await repository.get(key) is None
    assert len(session.scalar_statements) == 1


def test_binding_revision_and_current_rows_preserve_exact_active_reference() -> None:
    bound = _bound()

    revision = SqlAlchemyRunRepository._run_revision_row(
        bound,
        created_at=NOW,
    )
    current = SqlAlchemyRunRepository._current_run_row(
        bound,
        created_at=NOW,
    )

    assert revision.binding_player_character_id == PLAYER_CHARACTER_ID.value
    assert (
        revision.binding_contract_version
        == PlayerCharacterContractVersion.V1.value
    )
    assert revision.binding_record_revision == 1
    assert current.binding_player_character_id == PLAYER_CHARACTER_ID.value
    assert current.active_player_character_id == PLAYER_CHARACTER_ID.value


@pytest.mark.asyncio
async def test_binding_current_duplicate_is_narrow_typed_conflict() -> None:
    session = _SessionProbe()
    bound = _bound()
    session.scalar_results.append(
        SqlAlchemyRunRepository._run_revision_row(
            bound,
            created_at=NOW,
        )
    )
    session.execute_error = IntegrityError(
        "UPDATE",
        {},
        Exception(1062, "opaque duplicate"),
    )
    repository = SqlAlchemyRunRepository(session)

    with pytest.raises(
        RunPlayerCharacterBindingUniquenessConflictError
    ):
        await repository.compare_and_swap_current(
            bound,
            expected_state_version=1,
            updated_at=NOW,
        )


@pytest.mark.asyncio
async def test_binding_receipt_maps_exact_reference_and_operation_evidence() -> None:
    session = _SessionProbe()
    repository = SqlAlchemyRunMutationReceiptRepository(session)
    before = _created()
    after = _bound()
    operation_id = RunOperationId(value="operation.bind")
    command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    _, fingerprint = bind_player_character_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=bind_player_character_result(after),
    )
    repository._run_at_revision = AsyncMock(  # type: ignore[method-assign]
        side_effect=(before, after)
    )
    repository._validate_complete_run = AsyncMock(  # type: ignore[method-assign]
        return_value=after
    )

    await repository.add(receipt, created_at=NOW)

    assert len(session.added) == 1
    row = session.added[0]
    assert row.result_player_character_id == PLAYER_CHARACTER_ID.value
    assert (
        row.result_character_contract_version
        == PlayerCharacterContractVersion.V1.value
    )
    assert row.result_character_record_revision == 1
    assert row.participation_session_id is None
    assert row.operation_evidence_canonical


@pytest.mark.asyncio
async def test_attachment_lock_evidence_reads_exact_immutable_character_after_run_locks() -> None:
    before = _created()
    after = _bound()
    operation_id = RunOperationId(value="operation.bind")
    command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    _, fingerprint = bind_player_character_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=bind_player_character_result(after),
    )
    receipt_session = _SessionProbe()
    receipt_repository = SqlAlchemyRunMutationReceiptRepository(
        receipt_session
    )
    receipt_repository._run_at_revision = AsyncMock(  # type: ignore[method-assign]
        side_effect=(before, after)
    )
    receipt_repository._validate_complete_run = AsyncMock(  # type: ignore[method-assign]
        return_value=after
    )
    await receipt_repository.add(receipt, created_at=NOW)
    receipt_row = receipt_session.added[0]
    creation_row = await _stored_creation_receipt_row()
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            SqlAlchemyRunRepository._current_run_row(
                after,
                created_at=NOW,
            ),
            creation_row,
            _referenced_revision_row(),
        )
    )
    session.scalars_results.extend(
        (
            [
                SqlAlchemyRunRepository._run_revision_row(
                    before,
                    created_at=NOW,
                ),
                SqlAlchemyRunRepository._run_revision_row(
                    after,
                    created_at=NOW,
                ),
            ],
            [],
            [receipt_row],
        )
    )
    repository = SqlAlchemyRunRepository(session)

    evidence = await repository.get_session_attachment_lock_evidence(
        RUN_ID,
        receipt_key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=RunOperationId(
                value="operation.absent-attachment"
            ),
        ),
    )

    assert evidence is not None
    assert evidence.canonical_run == after
    assert evidence.attachment_receipt is None
    compiled = tuple(
        str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.scalar_statements
    )
    run_family_statements = tuple(
        statement
        for statement in compiled
        if "player_character_revisions" not in statement
    )
    character_statements = tuple(
        statement
        for statement in compiled
        if "player_character_revisions" in statement
    )
    assert all("FOR UPDATE" in statement for statement in run_family_statements)
    assert len(character_statements) == 1
    assert "FOR UPDATE" not in character_statements[0]
    assert (
        f"player_character_revisions.player_character_id = "
        f"'{PLAYER_CHARACTER_ID.value}'"
    ) in character_statements[0]
    assert "player_character_revisions.record_revision = 1" in (
        character_statements[0]
    )


@pytest.mark.asyncio
async def test_attachment_lock_evidence_returns_current_receipt_validated_against_locked_history() -> None:
    before, after, participation_row, receipt_row = (
        await _stored_attachment_evidence()
    )
    creation_row = await _stored_creation_receipt_row()
    receipt_key = RunReceiptKey(
        run_id=RUN_ID,
        operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
        operation_id=RunOperationId(value="operation.attach"),
    )
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            SqlAlchemyRunRepository._current_run_row(
                after,
                created_at=NOW,
            ),
            creation_row,
        )
    )
    session.scalars_results.extend(
        (
            [
                SqlAlchemyRunRepository._run_revision_row(
                    before,
                    created_at=NOW,
                ),
                SqlAlchemyRunRepository._run_revision_row(
                    after,
                    created_at=NOW,
                ),
            ],
            [participation_row],
            [receipt_row],
        )
    )
    repository = SqlAlchemyRunRepository(session)

    evidence = await repository.get_session_attachment_lock_evidence(
        RUN_ID,
        receipt_key=receipt_key,
    )

    assert evidence is not None
    assert evidence.canonical_run == after
    assert evidence.attachment_receipt is not None
    assert evidence.attachment_receipt.key == receipt_key
    assert evidence.attachment_receipt.result == attach_session_result(
        after
    )
    compiled = tuple(
        str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.scalar_statements
    )
    assert all("FOR UPDATE" in statement for statement in compiled)
    assert all(
        "player_character_revisions" not in statement
        for statement in compiled
    )
    mutation_statement = next(
        statement
        for statement in compiled
        if "FROM run_mutation_receipts" in statement
    )
    assert "run_mutation_receipts.operation_id =" not in mutation_statement


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corruption",
    (
        "malformed-receipt",
        "result-version",
        "participation",
        "revision",
        "duplicate",
    ),
)
async def test_attachment_lock_evidence_fails_closed_on_inconsistent_current_receipt(
    corruption: str,
) -> None:
    before, after, participation_row, receipt_row = (
        await _stored_attachment_evidence()
    )
    creation_row = await _stored_creation_receipt_row()
    if corruption == "malformed-receipt":
        receipt_row.receipt_canonical = b"{"
    elif corruption == "result-version":
        receipt_row.resulting_state_version = 3
    elif corruption == "participation":
        participation_row.joined_at = NOW + timedelta(seconds=1)
    elif corruption == "revision":
        receipt_row.created_at = NOW + timedelta(seconds=1)
    receipt_rows = (
        [receipt_row, receipt_row]
        if corruption == "duplicate"
        else [receipt_row]
    )
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            SqlAlchemyRunRepository._current_run_row(
                after,
                created_at=NOW,
            ),
            creation_row,
        )
    )
    session.scalars_results.extend(
        (
            [
                SqlAlchemyRunRepository._run_revision_row(
                    before,
                    created_at=NOW,
                ),
                SqlAlchemyRunRepository._run_revision_row(
                    after,
                    created_at=NOW,
                ),
            ],
            [participation_row],
            receipt_rows,
        )
    )
    repository = SqlAlchemyRunRepository(session)

    with pytest.raises(RunStoredRecordIntegrityError):
        await repository.get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=RunReceiptKey(
                run_id=RUN_ID,
                operation_namespace=(
                    RunOperationNamespace.ATTACH_SESSION_V1
                ),
                operation_id=RunOperationId(
                    value="operation.attach"
                ),
            ),
        )

    assert all(
        "player_character_revisions"
        not in str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.scalar_statements
    )


def _family_session(family: dict[str, Any]) -> _SessionProbe:
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            family["current"],
            family["creation_receipt"],
            family["referenced_revision"],
        )
    )
    session.scalars_results.extend(
        (
            family["revisions"],
            family["participations"],
            family["mutation_receipts"],
        )
    )
    return session


@pytest.mark.asyncio
async def test_attachment_lock_evidence_accepts_complete_bound_attachment_family() -> None:
    family = await _stored_bound_then_attached_family()
    repository = SqlAlchemyRunRepository(_family_session(family))

    evidence = await repository.get_session_attachment_lock_evidence(
        RUN_ID,
        receipt_key=family["receipt_key"],
    )

    assert evidence is not None
    assert evidence.canonical_run == family["attached"]
    assert evidence.attachment_receipt is not None
    assert evidence.attachment_receipt.key == family["receipt_key"]


@pytest.mark.asyncio
async def test_valid_stored_binding_contract_version_converts_to_strict_enum() -> None:
    family = await _stored_bound_then_attached_family()
    assert (
        family["current"].binding_contract_version
        == PlayerCharacterContractVersion.V1.value
    )

    evidence = await SqlAlchemyRunRepository(
        _family_session(family)
    ).get_session_attachment_lock_evidence(
        RUN_ID,
        receipt_key=family["receipt_key"],
    )

    assert evidence is not None
    binding = evidence.canonical_run.player_character_binding
    assert binding is not None
    assert (
        binding.applicable_character_reference.contract_version
        is PlayerCharacterContractVersion.V1
    )


@pytest.mark.asyncio
async def test_invalid_stored_binding_contract_version_is_classified_corruption() -> None:
    family = await _stored_bound_then_attached_family()
    family["current"].binding_contract_version = (
        "structured-player-character/v2"
    )

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="stored Run binding reference is invalid",
    ) as error:
        await SqlAlchemyRunRepository(
            _family_session(family)
        ).get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=family["receipt_key"],
        )

    assert isinstance(error.value.__cause__, ValueError)


def test_applicable_character_reference_keeps_strict_contract_boundary() -> None:
    with pytest.raises(ValidationError):
        ApplicableCharacterReference(
            player_character_id=PLAYER_CHARACTER_ID,
            contract_version=PlayerCharacterContractVersion.V1.value,
            record_revision=PlayerCharacterRevision(value=1),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corruption",
    (
        "malformed",
        "missing",
        "stored-column-mismatch",
        "run-reference-mismatch",
    ),
)
async def test_attachment_lock_evidence_fails_closed_on_actual_character_revision(
    corruption: str,
) -> None:
    family = await _stored_bound_then_attached_family()
    if corruption == "malformed":
        family["referenced_revision"].record_canonical = b"{"
    elif corruption == "missing":
        family["referenced_revision"] = None
    else:
        other = CreatePlayerCharacterPolicy().create(
            player_character_id=PlayerCharacterId(value="pc.repository-other"),
            controller_binding=ControllerBindingRef(
                value="binding.repository-other"
            ),
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
            source_reference=AuthoritySourceRef(
                value="source.character-repository-other"
            ),
        )
        other_row = _referenced_revision_row(other)
        if corruption == "stored-column-mismatch":
            family["referenced_revision"].record_canonical = (
                other_row.record_canonical
            )
        else:
            family["referenced_revision"] = other_row

    with pytest.raises(RunStoredRecordIntegrityError) as error:
        await SqlAlchemyRunRepository(
            _family_session(family)
        ).get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=family["receipt_key"],
        )

    if corruption in {"malformed", "stored-column-mismatch"}:
        assert isinstance(
            error.value.__cause__,
            PlayerCharacterStoredRecordIntegrityError,
        )
    else:
        assert error.value.__cause__ is None


@pytest.mark.asyncio
async def test_non_revision_one_reference_loads_its_actual_canonical_revision() -> None:
    reference = ApplicableCharacterReference(
        player_character_id=PLAYER_CHARACTER_ID,
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=2),
    )
    family = await _stored_bound_then_attached_family(
        reference=reference,
        referenced_record=_retired_character(),
    )
    session = _family_session(family)

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="binding reference does not match its immutable",
    ):
        await SqlAlchemyRunRepository(
            session
        ).get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=family["receipt_key"],
        )

    character_statement = next(
        str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        for statement in session.scalar_statements
        if "player_character_revisions" in str(statement)
    )
    assert "player_character_revisions.record_revision = 2" in (
        character_statement
    )
    assert "FOR UPDATE" not in character_statement


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corruption",
    (
        "rewritten-creation-provenance",
        "missing-creation-receipt",
        "contradictory-creation-receipt",
        "missing-nonrequest-receipt",
        "duplicate-nonrequest-receipt",
        "unrelated-historical-transition",
        "referenced-character-contract",
        "binding-continuity",
        "binding-receipt-agreement",
    ),
)
async def test_attachment_lock_evidence_rejects_noncanonical_complete_family(
    corruption: str,
) -> None:
    family = await _stored_bound_then_attached_family()
    if corruption == "rewritten-creation-provenance":
        rewritten_creation = (
            family["bound"].creation_provenance.model_copy(
                update={
                    "operation_id": RunOperationId(
                        value="operation.rewritten-create"
                    ),
                    "source_reference": RunAuthoritySourceRef(
                        value="source.rewritten-create"
                    ),
                }
            )
        )
        rewritten_bound = family["bound"].model_copy(
            update={"creation_provenance": rewritten_creation}
        )
        rewritten_attached = family["attached"].model_copy(
            update={"creation_provenance": rewritten_creation}
        )
        family["revisions"][1] = (
            SqlAlchemyRunRepository._run_revision_row(
                rewritten_bound,
                created_at=NOW + timedelta(seconds=1),
            )
        )
        family["revisions"][2] = (
            SqlAlchemyRunRepository._run_revision_row(
                rewritten_attached,
                created_at=NOW + timedelta(seconds=2),
            )
        )
        family["current"] = SqlAlchemyRunRepository._current_run_row(
            rewritten_attached,
            created_at=NOW,
        )
        family["current"].updated_at = NOW + timedelta(seconds=2)
    elif corruption == "missing-creation-receipt":
        family["creation_receipt"] = None
    elif corruption == "contradictory-creation-receipt":
        family["creation_receipt"].resulting_state_version = 2
    elif corruption == "missing-nonrequest-receipt":
        family["mutation_receipts"] = [
            family["mutation_receipts"][1]
        ]
    elif corruption == "duplicate-nonrequest-receipt":
        family["mutation_receipts"] = [
            family["mutation_receipts"][0],
            family["mutation_receipts"][0],
            family["mutation_receipts"][1],
        ]
    elif corruption == "unrelated-historical-transition":
        replacement_operation = RunOperationId(
            value="operation.rewritten-bind"
        )
        replacement_provenance = (
            family["bound"].current_mutation_provenance.model_copy(
                update={"operation_id": replacement_operation}
            )
        )
        replacement_binding = (
            family["bound"].player_character_binding.model_copy(
                update={"binding_operation_id": replacement_operation}
            )
        )
        rewritten_bound = family["bound"].model_copy(
            update={
                "current_mutation_provenance": replacement_provenance,
                "player_character_binding": replacement_binding,
            }
        )
        rewritten_attached = family["attached"].model_copy(
            update={"player_character_binding": replacement_binding}
        )
        family["revisions"][1] = (
            SqlAlchemyRunRepository._run_revision_row(
                rewritten_bound,
                created_at=NOW + timedelta(seconds=1),
            )
        )
        family["revisions"][2] = (
            SqlAlchemyRunRepository._run_revision_row(
                rewritten_attached,
                created_at=NOW + timedelta(seconds=2),
            )
        )
        family["current"] = SqlAlchemyRunRepository._current_run_row(
            rewritten_attached,
            created_at=NOW,
        )
        family["current"].updated_at = NOW + timedelta(seconds=2)
    elif corruption == "referenced-character-contract":
        family["mutation_receipts"][
            0
        ].result_character_contract_version = (
            "player-character-contract/v2"
        )
    elif corruption == "binding-continuity":
        replacement_binding = (
            family["attached"].player_character_binding.model_copy(
                update={
                    "binding_operation_id": RunOperationId(
                        value="operation.discontinuous-bind"
                    )
                }
            )
        )
        rewritten_attached = family["attached"].model_copy(
            update={"player_character_binding": replacement_binding}
        )
        family["revisions"][2] = (
            SqlAlchemyRunRepository._run_revision_row(
                rewritten_attached,
                created_at=NOW + timedelta(seconds=2),
            )
        )
        family["current"] = SqlAlchemyRunRepository._current_run_row(
            rewritten_attached,
            created_at=NOW,
        )
        family["current"].updated_at = NOW + timedelta(seconds=2)
    elif corruption == "binding-receipt-agreement":
        family["mutation_receipts"][0].expected_state_version = 2

    repository = SqlAlchemyRunRepository(_family_session(family))

    with pytest.raises(RunStoredRecordIntegrityError):
        await repository.get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=family["receipt_key"],
        )


@pytest.mark.asyncio
async def test_attachment_lock_evidence_rejects_partial_binding_carrier() -> None:
    family = await _stored_bound_then_attached_family()
    assert family["creation_receipt"] is not None
    assert family["current"].state_version == (
        family["revisions"][-1].state_version
    )
    family["current"].binding_contract_version = None
    family["revisions"][-1].binding_contract_version = None
    session = _family_session(family)
    repository = SqlAlchemyRunRepository(session)

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="binding evidence is partial",
    ):
        await repository.get_session_attachment_lock_evidence(
            RUN_ID,
            receipt_key=RunReceiptKey(
                run_id=RUN_ID,
                operation_namespace=(
                    RunOperationNamespace.ATTACH_SESSION_V1
                ),
                operation_id=RunOperationId(
                    value="operation.absent-attachment"
                ),
            ),
        )

    assert all(
        "player_character_revisions" not in str(statement)
        for statement in session.scalar_statements
    )
