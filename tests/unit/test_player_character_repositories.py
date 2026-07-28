from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
import inspect
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError, OperationalError

from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.application.ports import (
    ControllerBindingRegistryRepository,
    PlayerCharacterCreationReceiptRepository,
    PlayerCharacterMutationReceiptRepository,
    PlayerCharacterRepository,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    MAX_CANONICAL_INTEGER,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
)
from deviation_protocol.infrastructure.errors import (
    PlayerCharacterRepositoryConflictError,
    PlayerCharacterRepositoryError,
)
from deviation_protocol.infrastructure.orm_models import (
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
    canonical_record_from_revision_storage,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyPlayerCharacterCreationReceiptRepository,
    SqlAlchemyPlayerCharacterMutationReceiptRepository,
    SqlAlchemyPlayerCharacterRepository,
)


_NOW = datetime(2026, 7, 28, 10, 11, 12, 345678, tzinfo=UTC)


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
        self.commit_calls = 0
        self.rollback_calls = 0

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

    async def commit(self) -> None:
        self.commit_calls += 1
        raise AssertionError("repository must not commit")

    async def rollback(self) -> None:
        self.rollback_calls += 1
        raise AssertionError("repository must not roll back")


def _character_fixture(label: str = "unit") -> Any:
    player_character_id = PlayerCharacterId(value=f"pc.repository-{label}")
    controller_binding = ControllerBindingRef(
        value=f"binding.repository-{label}"
    )
    creation_command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    initial = CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        character_core=creation_command.character_core,
        narration_preferences=creation_command.narration_preferences,
        source_reference=AuthoritySourceRef(
            value=f"source.repository-{label}"
        ),
    )
    creation_operation_id = PlayerCharacterOperationId(
        value=f"operation.create-{label}"
    )
    _, creation_operation_fingerprint = creation_fingerprint(creation_command)
    creation_receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=controller_binding,
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=creation_operation_id,
        ),
        fingerprint=creation_operation_fingerprint,
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=initial.contract_version,
            resulting_revision=initial.record_revision,
            resulting_lifecycle=initial.lifecycle,
        ),
    )
    mutation_operation_id = PlayerCharacterOperationId(
        value=f"operation.mutate-{label}"
    )
    mutation_command = CharacterMutationCommand(
        contract_version=initial.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=player_character_id,
        expected_revision=initial.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=player_character_id,
            contract_version=initial.contract_version,
            record_revision=initial.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=player_character_id,
            expected_revision=initial.record_revision,
            operation_id=mutation_operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value=f"source.retire-{label}"
            ),
        ),
    )
    decision = evaluate_mutation_policy(
        initial,
        command=mutation_command,
        operation_id=mutation_operation_id,
    )
    assert decision.accepted
    assert decision.resulting_record is not None
    successor = decision.resulting_record
    _, mutation_operation_fingerprint = mutation_fingerprint(
        mutation_command,
        operation_id=mutation_operation_id,
    )
    mutation_receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=mutation_operation_id,
        ),
        fingerprint=mutation_operation_fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=successor.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
    )
    return SimpleNamespace(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        initial=initial,
        successor=successor,
        creation_receipt=creation_receipt,
        mutation_receipt=mutation_receipt,
    )


def _corrupt_stored_row(
    record_family: str,
    fixture: Any,
) -> Any:
    if record_family == "controller-binding":
        return PlayerCharacterControllerBindingRow(
            controller_binding=" invalid ",
            created_at=_NOW,
        )
    if record_family == "allocation":
        return PlayerCharacterIdAllocationRow(
            player_character_id=" invalid ",
            created_at=_NOW,
        )
    if record_family == "current":
        row = SqlAlchemyPlayerCharacterRepository._current_row(
            fixture.initial,
            created_at=_NOW,
        )
        row.created_at = "not-a-datetime"
        return row
    if record_family == "revision":
        row = SqlAlchemyPlayerCharacterRepository._revision_row(
            fixture.initial,
            created_at=_NOW,
        )
        row.source_reference = " invalid "
        return row
    if record_family == "creation-receipt":
        receipt = fixture.creation_receipt
        result = receipt.result
        return PlayerCharacterCreationReceiptRow(
            controller_binding=receipt.key.controller_binding.value,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id.value,
            fingerprint=b"\0" * 32,
            command_kind=receipt.command_kind,
            result_schema_version=receipt.result_schema_version,
            result_player_character_id=" invalid ",
            result_contract_version=result.contract_version.value,
            resulting_revision=result.resulting_revision.value,
            resulting_lifecycle=result.resulting_lifecycle.value,
            result_record_fingerprint=b"\0" * 32,
            receipt_canonical=b"{}",
            operation_evidence_canonical=b"{}",
            created_at=_NOW,
        )
    if record_family == "mutation-receipt":
        receipt = fixture.mutation_receipt
        result = receipt.result
        return PlayerCharacterMutationReceiptRow(
            player_character_id=receipt.key.player_character_id.value,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id.value,
            fingerprint=b"\0" * 32,
            command_kind=receipt.command_kind,
            result_schema_version=receipt.result_schema_version,
            expected_revision=result.resulting_revision.value - 1,
            result_player_character_id=" invalid ",
            result_contract_version=result.contract_version.value,
            result_command_kind=result.command_kind.value,
            command_result=result.command_result.value,
            resulting_revision=result.resulting_revision.value,
            resulting_lifecycle=result.resulting_lifecycle.value,
            before_record_fingerprint=b"\0" * 32,
            after_record_fingerprint=b"\0" * 32,
            receipt_canonical=b"{}",
            operation_evidence_canonical=b"{}",
            created_at=_NOW,
        )
    raise AssertionError(f"unknown record family: {record_family}")


@pytest.mark.parametrize(
    ("adapter", "port"),
    (
        (
            SqlAlchemyControllerBindingRegistryRepository,
            ControllerBindingRegistryRepository,
        ),
        (SqlAlchemyPlayerCharacterRepository, PlayerCharacterRepository),
        (
            SqlAlchemyPlayerCharacterCreationReceiptRepository,
            PlayerCharacterCreationReceiptRepository,
        ),
        (
            SqlAlchemyPlayerCharacterMutationReceiptRepository,
            PlayerCharacterMutationReceiptRepository,
        ),
    ),
)
def test_repository_adapters_implement_exact_port_signatures(
    adapter: type[Any],
    port: type[Any],
) -> None:
    assert issubclass(adapter, port)
    for method_name in port.__abstractmethods__:
        assert inspect.signature(getattr(adapter, method_name)) == (
            inspect.signature(getattr(port, method_name))
        )


@pytest.mark.asyncio
async def test_registry_add_flushes_without_transaction_ownership() -> None:
    session = _SessionProbe()
    repository = SqlAlchemyControllerBindingRegistryRepository(session)
    binding = ControllerBindingRef(value="binding.repository-unit")

    await repository.add(binding, created_at=_NOW)

    assert len(session.added) == 1
    assert session.added[0].controller_binding == binding.value
    assert session.flush_calls == [(session.added[0],)]
    assert session.commit_calls == 0
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_registry_lock_targets_exact_row_for_update() -> None:
    binding = ControllerBindingRef(value="binding.repository-lock")
    session = _SessionProbe()
    session.scalar_results.append(
        PlayerCharacterControllerBindingRow(
            controller_binding=binding.value,
            created_at=_NOW,
        )
    )
    repository = SqlAlchemyControllerBindingRegistryRepository(session)

    assert await repository.lock(binding) == binding

    compiled = str(
        session.scalar_statements[0].compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "FOR UPDATE" in compiled
    assert f"= '{binding.value}'" in compiled


@pytest.mark.asyncio
async def test_character_locked_get_targets_exact_current_row() -> None:
    character_id = PlayerCharacterId(value="pc.repository-lock")
    session = _SessionProbe()
    repository = SqlAlchemyPlayerCharacterRepository(session)

    assert await repository.get_for_update(character_id) is None

    compiled = str(
        session.scalar_statements[0].compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "FOR UPDATE" in compiled
    assert f"= '{character_id.value}'" in compiled


@pytest.mark.asyncio
async def test_duplicate_insert_is_a_chained_repository_conflict() -> None:
    original = Exception(1062, "duplicate")
    session = _SessionProbe()
    session.flush_error = IntegrityError("INSERT", {}, original)
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(
        PlayerCharacterRepositoryConflictError
    ) as exc_info:
        await repository.add_allocation(
            PlayerCharacterId(value="pc.repository-conflict"),
            created_at=_NOW,
        )

    assert exc_info.value.__cause__ is session.flush_error
    assert session.commit_calls == 0
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_operational_write_failure_is_sanitized_and_chained() -> None:
    original = Exception(2006, "connection lost")
    session = _SessionProbe()
    session.flush_error = OperationalError("INSERT", {}, original)
    repository = SqlAlchemyControllerBindingRegistryRepository(session)

    with pytest.raises(PlayerCharacterRepositoryError) as exc_info:
        await repository.add(
            ControllerBindingRef(value="binding.repository-operational"),
            created_at=_NOW,
        )

    assert type(exc_info.value) is PlayerCharacterRepositoryError
    assert exc_info.value.__cause__ is session.flush_error
    assert "connection lost" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_unrecognized_integrity_failure_is_not_a_false_conflict() -> None:
    original = Exception(1452, "foreign key failure")
    session = _SessionProbe()
    session.flush_error = IntegrityError("INSERT", {}, original)
    repository = SqlAlchemyControllerBindingRegistryRepository(session)

    with pytest.raises(PlayerCharacterRepositoryError) as exc_info:
        await repository.add(
            ControllerBindingRef(value="binding.repository-integrity"),
            created_at=_NOW,
        )

    assert type(exc_info.value) is PlayerCharacterRepositoryError
    assert exc_info.value.__cause__ is session.flush_error


@pytest.mark.asyncio
async def test_operational_read_failure_is_sanitized_and_chained() -> None:
    original = Exception(2013, "server unavailable")
    session = _SessionProbe()
    session.scalar_error = OperationalError("SELECT", {}, original)
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(PlayerCharacterRepositoryError) as exc_info:
        await repository.get(
            PlayerCharacterId(value="pc.repository-read-failure")
        )

    assert exc_info.value.__cause__ is session.scalar_error
    assert "server unavailable" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_stored_binding_fails_closed_with_chaining() -> None:
    session = _SessionProbe()
    session.scalar_results.append(
        PlayerCharacterControllerBindingRow(
            controller_binding=" invalid ",
            created_at=_NOW,
        )
    )
    repository = SqlAlchemyControllerBindingRegistryRepository(session)

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError
    ) as exc_info:
        await repository.get(
            ControllerBindingRef(value="binding.repository-valid")
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("record_family", "converter_name", "expected_message", "cause_type"),
    (
        (
            "controller-binding",
            "_controller_binding_record",
            "stored controller-binding row is invalid",
            ValueError,
        ),
        (
            "allocation",
            "_allocation_record",
            "stored player-character allocation row is invalid",
            ValueError,
        ),
        (
            "current",
            "_current_record",
            "stored current player-character row is invalid",
            AttributeError,
        ),
        (
            "revision",
            "_revision_record",
            "stored player-character revision row is invalid",
            ValueError,
        ),
        (
            "creation-receipt",
            "_creation_receipt_record",
            "stored creation receipt row is invalid",
            ValueError,
        ),
        (
            "mutation-receipt",
            "_mutation_receipt_record",
            "stored mutation receipt row is invalid",
            ValueError,
        ),
    ),
    ids=(
        "controller-binding",
        "allocation",
        "current",
        "revision",
        "creation-receipt",
        "mutation-receipt",
    ),
)
def test_each_stored_row_family_fails_closed_with_its_chained_cause(
    record_family: str,
    converter_name: str,
    expected_message: str,
    cause_type: type[BaseException],
) -> None:
    fixture = _character_fixture(f"corrupt-{record_family}")
    converter = getattr(
        SqlAlchemyPlayerCharacterRepository,
        converter_name,
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ) as exc_info:
        converter(_corrupt_stored_row(record_family, fixture))

    assert isinstance(exc_info.value.__cause__, cause_type)
    assert "not-a-datetime" not in str(exc_info.value)
    assert " invalid " not in str(exc_info.value)


@pytest.mark.parametrize(
    "reference_type",
    (
        PlayerCharacterId,
        ControllerBindingRef,
        PlayerCharacterOperationId,
        AuthoritySourceRef,
    ),
)
def test_repository_opaque_references_accept_128_and_reject_129_characters(
    reference_type: type[Any],
) -> None:
    exact = "A" * 128

    assert reference_type(value=exact).value == exact
    with pytest.raises(ValueError):
        reference_type(value=exact + "A")


@pytest.mark.asyncio
async def test_current_reconstruction_rejects_dangling_exact_revision_without_fallback() -> None:
    fixture = _character_fixture("dangling-revision")
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            SqlAlchemyPlayerCharacterRepository._current_row(
                fixture.initial,
                created_at=_NOW,
            ),
            None,
        )
    )
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="revision reference is dangling",
    ):
        await repository.get(fixture.player_character_id)

    assert len(session.scalar_statements) == 2
    exact_revision_sql = str(
        session.scalar_statements[1].compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert fixture.player_character_id.value in exact_revision_sql
    assert "record_revision = 1" in exact_revision_sql
    assert "ORDER BY" not in exact_revision_sql


@pytest.mark.asyncio
async def test_current_reconstruction_rejects_cross_row_character_identity() -> None:
    requested = _character_fixture("requested-identity")
    substituted = _character_fixture("substituted-identity")
    session = _SessionProbe()
    session.scalar_results.append(
        SqlAlchemyPlayerCharacterRepository._current_row(
            substituted.initial,
            created_at=_NOW,
        )
    )
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="lookup identity is mismatched",
    ):
        await repository.get(requested.player_character_id)

    assert len(session.scalar_statements) == 1


@pytest.mark.asyncio
async def test_current_reconstruction_rejects_cross_row_revision_identity() -> None:
    requested = _character_fixture("requested-revision")
    substituted = _character_fixture("substituted-revision")
    session = _SessionProbe()
    session.scalar_results.extend(
        (
            SqlAlchemyPlayerCharacterRepository._current_row(
                requested.initial,
                created_at=_NOW,
            ),
            SqlAlchemyPlayerCharacterRepository._revision_row(
                substituted.initial,
                created_at=_NOW,
            ),
        )
    )
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="current player-character row does not match its revision",
    ):
        await repository.get(requested.player_character_id)

    assert len(session.scalar_statements) == 2


@pytest.mark.asyncio
async def test_maximum_revision_reconstructs_but_increment_overflow_executes_no_sql() -> None:
    fixture = _character_fixture("maximum-revision")
    maximum_revision = PlayerCharacterRevision(
        value=MAX_CANONICAL_INTEGER
    )
    maximum_record = fixture.initial.detached_validated_copy(
        record_revision=maximum_revision,
        lifecycle=PlayerCharacterLifecycle.RETIRED,
        authority_provenance=AuthorityProvenance(
            target_player_character_id=fixture.player_character_id,
            prior_revision=PlayerCharacterRevision(
                value=MAX_CANONICAL_INTEGER - 1
            ),
            resulting_revision=maximum_revision,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            authority_class=(
                PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
            ),
            source_reference=AuthoritySourceRef(
                value="source.maximum-revision"
            ),
        ),
    )
    revision_row = SqlAlchemyPlayerCharacterRepository._revision_row(
        maximum_record,
        created_at=_NOW,
    )

    assert canonical_record_from_revision_storage(
        SqlAlchemyPlayerCharacterRepository._revision_record(revision_row)
    ) == maximum_record
    assert not maximum_record.record_revision.has_successor

    final_successor_session = _SessionProbe()
    final_successor_session.scalar_results.append(revision_row)
    final_successor_repository = SqlAlchemyPlayerCharacterRepository(
        final_successor_session
    )
    assert await final_successor_repository.compare_and_swap_current(
        maximum_record,
        expected_revision=MAX_CANONICAL_INTEGER - 1,
        created_at=_NOW,
    )
    assert len(final_successor_session.scalar_statements) == 1
    assert len(final_successor_session.execute_statements) == 1

    session = _SessionProbe()
    repository = SqlAlchemyPlayerCharacterRepository(session)
    with pytest.raises(
        ValueError,
        match="expected revision does not match successor record",
    ):
        await repository.compare_and_swap_current(
            maximum_record,
            expected_revision=MAX_CANONICAL_INTEGER,
            created_at=_NOW,
        )

    assert session.scalar_statements == []
    assert session.execute_statements == []
    assert session.flush_calls == []


@pytest.mark.asyncio
async def test_current_compare_and_swap_uses_identity_revision_and_binding() -> None:
    fixture = _character_fixture("cas")
    session = _SessionProbe()
    session.scalar_results.append(
        SqlAlchemyPlayerCharacterRepository._revision_row(
            fixture.successor,
            created_at=_NOW,
        )
    )
    repository = SqlAlchemyPlayerCharacterRepository(session)

    assert await repository.compare_and_swap_current(
        fixture.successor,
        expected_revision=fixture.initial.record_revision.value,
        created_at=_NOW,
    )

    compiled = str(
        session.execute_statements[0].compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert fixture.player_character_id.value in compiled
    assert fixture.controller_binding.value in compiled
    assert "record_revision = 1" in compiled
    assert "record_revision=2" in compiled.replace(" ", "")
    assert session.flush_calls == []
    assert session.commit_calls == 0
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_current_compare_and_swap_reports_stale_zero_row_result() -> None:
    fixture = _character_fixture("stale")
    session = _SessionProbe()
    session.scalar_results.append(
        SqlAlchemyPlayerCharacterRepository._revision_row(
            fixture.successor,
            created_at=_NOW,
        )
    )
    session.execute_result = SimpleNamespace(rowcount=0)
    repository = SqlAlchemyPlayerCharacterRepository(session)

    assert not await repository.compare_and_swap_current(
        fixture.successor,
        expected_revision=1,
        created_at=_NOW,
    )


@pytest.mark.asyncio
async def test_missing_repository_rows_return_none_without_retry() -> None:
    session = _SessionProbe()
    fixture = _character_fixture("missing")

    assert (
        await SqlAlchemyControllerBindingRegistryRepository(session).get(
            fixture.controller_binding
        )
        is None
    )
    assert (
        await SqlAlchemyPlayerCharacterRepository(session).get(
            fixture.player_character_id
        )
        is None
    )
    assert (
        await SqlAlchemyPlayerCharacterCreationReceiptRepository(session).get(
            fixture.creation_receipt.key
        )
        is None
    )
    assert (
        await SqlAlchemyPlayerCharacterMutationReceiptRepository(session).get(
            fixture.mutation_receipt.key
        )
        is None
    )
    assert len(session.scalar_statements) == 8
    assert session.commit_calls == 0
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_missing_current_with_allocation_evidence_is_corruption() -> None:
    character_id = PlayerCharacterId(value="pc.repository-orphaned")
    session = _SessionProbe()
    session.scalar_results.extend((None, character_id.value))
    repository = SqlAlchemyPlayerCharacterRepository(session)

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="current row is missing",
    ):
        await repository.get(character_id)
