from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

import pytest

from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationFingerprint,
    CharacterOperationNamespace,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    Declaration,
    NarrationPreference,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
    PlayerDeclaredText,
    PlayerNarrationPreference,
    PlayerSubjectiveAuthority,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
    StoredControllerBindingRecord,
    StoredCreationReceiptRecord,
    StoredCurrentPlayerCharacterRecord,
    StoredMutationReceiptRecord,
    StoredPlayerCharacterIdAllocationRecord,
    StoredPlayerCharacterRevisionRecord,
    canonical_record_from_current_storage,
    canonical_record_from_revision_storage,
    canonical_record_to_storage_bytes,
    canonical_state_record_fingerprint,
    creation_operation_evidence_from_storage,
    creation_operation_evidence_to_storage_bytes,
    creation_receipt_from_storage,
    creation_receipt_to_storage_bytes,
    fingerprint_to_storage_bytes,
    mutation_operation_evidence_from_storage,
    mutation_operation_evidence_to_storage_bytes,
    mutation_receipt_from_storage,
    mutation_receipt_to_storage_bytes,
    validate_stored_player_character_record_set,
)


_CREATED_AT = datetime(2026, 7, 27, 12, 34, 56, 789012, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class _CreationAggregateFixture:
    command: CharacterCreationCommand
    operation_evidence_canonical: bytes
    operation_fingerprint: CharacterOperationFingerprint
    phase_one_receipt: StoredCreationSuccessReceipt
    canonical_record: CanonicalPlayerCharacter
    controller_binding_record: StoredControllerBindingRecord
    allocation_record: StoredPlayerCharacterIdAllocationRecord
    current_record: StoredCurrentPlayerCharacterRecord
    revision_one_record: StoredPlayerCharacterRevisionRecord
    creation_receipt_record: StoredCreationReceiptRecord


@dataclass(frozen=True, slots=True)
class _MutationAggregateFixture:
    creation: _CreationAggregateFixture
    operation_id: PlayerCharacterOperationId
    command: CharacterMutationCommand
    operation_evidence_canonical: bytes
    operation_fingerprint: CharacterOperationFingerprint
    phase_one_receipt: StoredMutationSuccessReceipt
    predecessor: CanonicalPlayerCharacter
    successor: CanonicalPlayerCharacter
    predecessor_revision_record: StoredPlayerCharacterRevisionRecord
    successor_revision_record: StoredPlayerCharacterRevisionRecord
    current_record: StoredCurrentPlayerCharacterRecord
    mutation_receipt_record: StoredMutationReceiptRecord


def _creation_command(label: str) -> CharacterCreationCommand:
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=Declaration[PlayerDeclaredText].declared(
                PlayerDeclaredText(
                    authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
                    text=f"Character {label}",
                )
            )
        ),
        narration_preferences=NarrationPreferences(
            internal_thoughts=Declaration[PlayerNarrationPreference].declared(
                PlayerNarrationPreference(
                    authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
                    value=NarrationPreference.HIGH_AGENCY,
                )
            )
        ),
    )


def _stored_current(
    record: CanonicalPlayerCharacter,
    canonical: bytes | None = None,
) -> StoredCurrentPlayerCharacterRecord:
    return StoredCurrentPlayerCharacterRecord(
        player_character_id=record.player_character_id,
        contract_version=record.contract_version.value,
        record_revision=record.record_revision.value,
        controller_binding=record.controller_binding,
        lifecycle=record.lifecycle.value,
        record_canonical=(
            canonical
            if canonical is not None
            else canonical_record_to_storage_bytes(record)
        ),
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
    )


def _stored_revision(
    record: CanonicalPlayerCharacter,
) -> StoredPlayerCharacterRevisionRecord:
    provenance = record.authority_provenance
    return StoredPlayerCharacterRevisionRecord(
        player_character_id=record.player_character_id,
        record_revision=record.record_revision.value,
        contract_version=record.contract_version.value,
        controller_binding=record.controller_binding,
        lifecycle=record.lifecycle.value,
        prior_revision=(
            provenance.prior_revision.value
            if provenance.prior_revision is not None
            else None
        ),
        mutation_kind=provenance.mutation_kind.value,
        authority_class=provenance.authority_class.value,
        source_reference=provenance.source_reference,
        record_canonical=canonical_record_to_storage_bytes(record),
        created_at=_CREATED_AT,
    )


def _stored_creation_receipt(
    *,
    receipt: StoredCreationSuccessReceipt,
    command: CharacterCreationCommand,
    source_reference: AuthoritySourceRef,
    result_record_fingerprint: bytes,
) -> StoredCreationReceiptRecord:
    result = receipt.result
    return StoredCreationReceiptRecord(
        controller_binding=receipt.key.controller_binding,
        operation_namespace=receipt.key.operation_namespace.value,
        operation_id=receipt.key.operation_id.value,
        fingerprint=fingerprint_to_storage_bytes(receipt.fingerprint),
        command_kind=receipt.command_kind,
        result_schema_version=receipt.result_schema_version,
        result_player_character_id=result.player_character_id,
        result_contract_version=result.contract_version.value,
        resulting_revision=result.resulting_revision.value,
        resulting_lifecycle=result.resulting_lifecycle.value,
        result_record_fingerprint=result_record_fingerprint,
        receipt_canonical=creation_receipt_to_storage_bytes(receipt),
        operation_evidence_canonical=(
            creation_operation_evidence_to_storage_bytes(
                command,
                source_reference=source_reference,
            )
        ),
        created_at=_CREATED_AT,
    )


def _stored_mutation_receipt(
    *,
    receipt: StoredMutationSuccessReceipt,
    command: CharacterMutationCommand,
    predecessor: CanonicalPlayerCharacter,
    successor: CanonicalPlayerCharacter,
) -> StoredMutationReceiptRecord:
    result = receipt.result
    return StoredMutationReceiptRecord(
        player_character_id=receipt.key.player_character_id,
        operation_namespace=receipt.key.operation_namespace.value,
        operation_id=receipt.key.operation_id.value,
        fingerprint=fingerprint_to_storage_bytes(receipt.fingerprint),
        command_kind=receipt.command_kind,
        result_schema_version=receipt.result_schema_version,
        expected_revision=command.expected_revision.value,
        result_player_character_id=result.player_character_id,
        result_contract_version=result.contract_version.value,
        result_command_kind=result.command_kind.value,
        command_result=result.command_result.value,
        resulting_revision=result.resulting_revision.value,
        resulting_lifecycle=result.resulting_lifecycle.value,
        before_record_fingerprint=canonical_state_record_fingerprint(
            predecessor
        ),
        after_record_fingerprint=canonical_state_record_fingerprint(successor),
        receipt_canonical=mutation_receipt_to_storage_bytes(receipt),
        operation_evidence_canonical=(
            mutation_operation_evidence_to_storage_bytes(command)
        ),
        created_at=_CREATED_AT,
    )


def _build_creation_aggregate(label: str) -> _CreationAggregateFixture:
    command = _creation_command(label)
    player_character_id = PlayerCharacterId(value=f"pc.creation-{label}")
    controller_binding = ControllerBindingRef(value=f"binding.creation-{label}")
    record = CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=AuthoritySourceRef(value=f"source.creation-{label}"),
    )
    operation_evidence_canonical = creation_operation_evidence_to_storage_bytes(
        command,
        source_reference=record.authority_provenance.source_reference,
    )
    _, operation_fingerprint = creation_fingerprint(command)
    receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=controller_binding,
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=PlayerCharacterOperationId(
                value=f"operation.creation-{label}"
            ),
        ),
        fingerprint=operation_fingerprint,
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=record.contract_version,
            resulting_revision=record.record_revision,
            resulting_lifecycle=record.lifecycle,
        ),
    )
    state_record_fingerprint = canonical_state_record_fingerprint(record)
    return _CreationAggregateFixture(
        command=command,
        operation_evidence_canonical=operation_evidence_canonical,
        operation_fingerprint=operation_fingerprint,
        phase_one_receipt=receipt,
        canonical_record=record,
        controller_binding_record=StoredControllerBindingRecord(
            controller_binding=controller_binding,
            created_at=_CREATED_AT,
        ),
        allocation_record=StoredPlayerCharacterIdAllocationRecord(
            player_character_id=player_character_id,
            created_at=_CREATED_AT,
        ),
        current_record=_stored_current(record),
        revision_one_record=_stored_revision(record),
        creation_receipt_record=_stored_creation_receipt(
            receipt=receipt,
            command=command,
            source_reference=record.authority_provenance.source_reference,
            result_record_fingerprint=state_record_fingerprint,
        ),
    )


def _mutation_command(
    creation: _CreationAggregateFixture,
    *,
    operation_id: PlayerCharacterOperationId,
    source_reference: AuthoritySourceRef,
    expected_revision: PlayerCharacterRevision | None = None,
) -> CharacterMutationCommand:
    revision = expected_revision or creation.canonical_record.record_revision
    player_character_id = creation.canonical_record.player_character_id
    return CharacterMutationCommand(
        contract_version=creation.canonical_record.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=player_character_id,
        expected_revision=revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=player_character_id,
            contract_version=creation.canonical_record.contract_version,
            record_revision=revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=player_character_id,
            expected_revision=revision,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=source_reference,
        ),
    )


def _mutation_receipt_for_command(
    aggregate: _MutationAggregateFixture,
    command: CharacterMutationCommand,
    *,
    operation_id: PlayerCharacterOperationId | None = None,
    result_record: CanonicalPlayerCharacter | None = None,
    resulting_revision: PlayerCharacterRevision | None = None,
) -> StoredMutationReceiptRecord:
    operation_id = operation_id or aggregate.operation_id
    result_record = result_record or aggregate.successor
    _, fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=command.target_player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=command.target_player_character_id,
            contract_version=command.contract_version,
            command_kind=command.command_kind,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=(
                resulting_revision or result_record.record_revision
            ),
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
    )
    return _stored_mutation_receipt(
        receipt=receipt,
        command=command,
        predecessor=aggregate.predecessor,
        successor=result_record,
    )


def _build_mutation_aggregate(label: str) -> _MutationAggregateFixture:
    creation = _build_creation_aggregate(label)
    operation_id = PlayerCharacterOperationId(
        value=f"Operation.Mutation-{label}"
    )
    command = _mutation_command(
        creation,
        operation_id=operation_id,
        source_reference=AuthoritySourceRef(
            value=f"Source.Confirmation-{label}"
        ),
    )
    operation_evidence_canonical = (
        mutation_operation_evidence_to_storage_bytes(command)
    )
    _, operation_fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    decision = evaluate_mutation_policy(
        creation.canonical_record,
        command=command,
        operation_id=operation_id,
    )
    assert decision.accepted
    assert decision.resulting_record is not None
    successor = decision.resulting_record
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=creation.canonical_record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=operation_fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=successor.player_character_id,
            contract_version=successor.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=successor.lifecycle,
        ),
    )
    return _MutationAggregateFixture(
        creation=creation,
        operation_id=operation_id,
        command=command,
        operation_evidence_canonical=operation_evidence_canonical,
        operation_fingerprint=operation_fingerprint,
        phase_one_receipt=receipt,
        predecessor=creation.canonical_record,
        successor=successor,
        predecessor_revision_record=creation.revision_one_record,
        successor_revision_record=_stored_revision(successor),
        current_record=_stored_current(successor),
        mutation_receipt_record=_stored_mutation_receipt(
            receipt=receipt,
            command=command,
            predecessor=creation.canonical_record,
            successor=successor,
        ),
    )


@pytest.fixture
def creation_aggregate() -> _CreationAggregateFixture:
    return _build_creation_aggregate("primary")


@pytest.fixture
def second_creation_aggregate() -> _CreationAggregateFixture:
    return _build_creation_aggregate("secondary")


@pytest.fixture
def mutation_aggregate() -> _MutationAggregateFixture:
    return _build_mutation_aggregate("Primary.MiXeD-K")


@pytest.fixture
def second_mutation_aggregate() -> _MutationAggregateFixture:
    return _build_mutation_aggregate("Secondary.MiXeD-K")


def _aggregate_validation_arguments(
    aggregate: _CreationAggregateFixture,
) -> dict[str, object]:
    return {
        "creation_receipt": aggregate.creation_receipt_record,
        "mutation_receipts": (),
        "revisions": (aggregate.revision_one_record,),
        "current": aggregate.current_record,
        "controller_binding": aggregate.controller_binding_record,
        "allocation": aggregate.allocation_record,
    }


def _validate_creation_aggregate(
    aggregate: _CreationAggregateFixture,
    **overrides: object,
) -> None:
    arguments = _aggregate_validation_arguments(aggregate)
    arguments.update(overrides)
    validate_stored_player_character_record_set(**arguments)


def _mutation_aggregate_validation_arguments(
    aggregate: _MutationAggregateFixture,
) -> dict[str, object]:
    return {
        "creation_receipt": aggregate.creation.creation_receipt_record,
        "mutation_receipts": (aggregate.mutation_receipt_record,),
        "revisions": (
            aggregate.predecessor_revision_record,
            aggregate.successor_revision_record,
        ),
        "current": aggregate.current_record,
        "controller_binding": aggregate.creation.controller_binding_record,
        "allocation": aggregate.creation.allocation_record,
    }


def _validate_mutation_aggregate(
    aggregate: _MutationAggregateFixture,
    **overrides: object,
) -> None:
    arguments = _mutation_aggregate_validation_arguments(aggregate)
    arguments.update(overrides)
    validate_stored_player_character_record_set(**arguments)


def _record_for_command(
    aggregate: _CreationAggregateFixture,
    command: CharacterCreationCommand,
    *,
    player_character_id: PlayerCharacterId | None = None,
    controller_binding: ControllerBindingRef | None = None,
) -> CanonicalPlayerCharacter:
    return CreatePlayerCharacterPolicy().create(
        player_character_id=(
            player_character_id or aggregate.canonical_record.player_character_id
        ),
        controller_binding=(
            controller_binding or aggregate.canonical_record.controller_binding
        ),
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=(
            aggregate.canonical_record.authority_provenance.source_reference
        ),
    )


def _consistent_creation_receipt_record(
    aggregate: _CreationAggregateFixture,
    *,
    command: CharacterCreationCommand | None = None,
    controller_binding: ControllerBindingRef | None = None,
    result_player_character_id: PlayerCharacterId | None = None,
) -> StoredCreationReceiptRecord:
    command = command or aggregate.command
    _, fingerprint = creation_fingerprint(command)
    receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=(
                controller_binding
                or aggregate.phase_one_receipt.key.controller_binding
            ),
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=aggregate.phase_one_receipt.key.operation_id,
        ),
        fingerprint=fingerprint,
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=(
                result_player_character_id
                or aggregate.phase_one_receipt.result.player_character_id
            ),
            contract_version=PlayerCharacterContractVersion.V1,
            resulting_revision=PlayerCharacterRevision(value=1),
            resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE,
        ),
    )
    return _stored_creation_receipt(
        receipt=receipt,
        command=command,
        source_reference=(
            aggregate.canonical_record.authority_provenance.source_reference
        ),
        result_record_fingerprint=(
            aggregate.creation_receipt_record.result_record_fingerprint
        ),
    )


def test_canonical_record_round_trip_is_deterministic_and_byte_exact(
    creation_aggregate: _CreationAggregateFixture,
):
    record = creation_aggregate.canonical_record
    encoded = canonical_record_to_storage_bytes(record)
    assert encoded == canonical_record_to_storage_bytes(record)
    assert canonical_record_from_current_storage(
        _stored_current(record, encoded)
    ) == record
    assert canonical_state_record_fingerprint(record) != encoded
    assert len(canonical_state_record_fingerprint(record)) == 32


def test_current_decoder_fails_closed_for_noncanonical_blob_and_column_substitution(
    creation_aggregate: _CreationAggregateFixture,
):
    record = creation_aggregate.canonical_record
    with pytest.raises(PlayerCharacterStoredRecordIntegrityError):
        canonical_record_from_current_storage(
            _stored_current(record, b'{"bad":true}')
        )
    stored = _stored_current(record)
    substituted = StoredCurrentPlayerCharacterRecord(
        player_character_id=PlayerCharacterId(value="pc.persistence-2"),
        contract_version=stored.contract_version,
        record_revision=stored.record_revision,
        controller_binding=stored.controller_binding,
        lifecycle=stored.lifecycle,
        record_canonical=stored.record_canonical,
        created_at=stored.created_at,
        updated_at=stored.updated_at,
    )
    with pytest.raises(PlayerCharacterStoredRecordIntegrityError):
        canonical_record_from_current_storage(substituted)


def test_creation_operation_evidence_is_lossless_canonical_and_fail_closed(
    creation_aggregate: _CreationAggregateFixture,
):
    command = creation_aggregate.command
    source_reference = (
        creation_aggregate.canonical_record.authority_provenance.source_reference
    )
    encoded = creation_operation_evidence_to_storage_bytes(
        command,
        source_reference=source_reference,
    )
    assert creation_operation_evidence_from_storage(encoded) == command
    assert (
        creation_operation_evidence_to_storage_bytes(
            command,
            source_reference=source_reference,
        )
        == encoded
    )
    with pytest.raises(PlayerCharacterStoredRecordIntegrityError):
        creation_operation_evidence_from_storage(b'{"unknown":true}')


def test_complete_valid_creation_aggregate_binds_all_authoritative_evidence(
    creation_aggregate: _CreationAggregateFixture,
):
    aggregate = creation_aggregate

    assert _validate_creation_aggregate(aggregate) is None

    decoded_command = creation_operation_evidence_from_storage(
        aggregate.creation_receipt_record.operation_evidence_canonical
    )
    fingerprint_payload, recomputed_operation_fingerprint = creation_fingerprint(
        decoded_command
    )
    decoded_receipt = creation_receipt_from_storage(
        aggregate.creation_receipt_record
    )
    decoded_history = canonical_record_from_revision_storage(
        aggregate.revision_one_record
    )
    decoded_current = canonical_record_from_current_storage(
        aggregate.current_record
    )
    recomputed_state_record_fingerprint = canonical_state_record_fingerprint(
        decoded_history
    )

    assert decoded_command == aggregate.command
    assert (
        aggregate.creation_receipt_record.operation_evidence_canonical
        == aggregate.operation_evidence_canonical
    )
    assert fingerprint_payload != aggregate.operation_evidence_canonical
    assert recomputed_operation_fingerprint == aggregate.operation_fingerprint
    assert decoded_receipt == aggregate.phase_one_receipt
    assert (
        fingerprint_to_storage_bytes(recomputed_operation_fingerprint)
        == aggregate.creation_receipt_record.fingerprint
    )
    assert (
        decoded_receipt.result.player_character_id
        == aggregate.canonical_record.player_character_id
        == aggregate.allocation_record.player_character_id
    )
    assert (
        decoded_receipt.key.controller_binding
        == aggregate.canonical_record.controller_binding
        == aggregate.controller_binding_record.controller_binding
    )
    assert (
        decoded_command.character_core
        == aggregate.canonical_record.character_core
    )
    assert (
        decoded_command.narration_preferences
        == aggregate.canonical_record.narration_preferences
    )
    assert (
        decoded_command.contract_version
        is aggregate.canonical_record.contract_version
        is PlayerCharacterContractVersion.V1
    )
    assert (
        aggregate.canonical_record.lifecycle
        is PlayerCharacterLifecycle.ACTIVE
    )
    assert aggregate.canonical_record.record_revision.value == 1
    assert (
        aggregate.canonical_record.authority_provenance.mutation_kind
        is PlayerCharacterMutationKind.CREATE
    )
    assert (
        aggregate.canonical_record.authority_provenance.authority_class
        is PlayerCharacterAuthorityClass.TRUSTED_CREATION
    )
    assert (
        aggregate.canonical_record.authority_provenance.prior_revision is None
    )
    assert decoded_history == aggregate.canonical_record
    assert decoded_current == decoded_history
    assert (
        recomputed_state_record_fingerprint
        == aggregate.creation_receipt_record.result_record_fingerprint
    )


@pytest.mark.parametrize(
    ("record_family", "missing_value", "expected_message"),
    (
        (
            "creation_receipt",
            None,
            "creation receipt record is required",
        ),
        (
            "revisions",
            (),
            "revision history record family is required",
        ),
        (
            "current",
            None,
            "current player-character record is required",
        ),
        (
            "controller_binding",
            None,
            "controller-binding record is required",
        ),
        (
            "allocation",
            None,
            "player-character allocation record is required",
        ),
    ),
    ids=(
        "creation-receipt",
        "revision-history",
        "current-record",
        "controller-binding",
        "permanent-id-allocation",
    ),
)
def test_creation_aggregate_rejects_each_missing_required_record_family(
    creation_aggregate: _CreationAggregateFixture,
    record_family: str,
    missing_value: object,
    expected_message: str,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            **{record_family: missing_value},
        )


@pytest.mark.parametrize(
    ("case", "expected_message"),
    (
        (
            "character-identity-mismatch",
            "creation receipt does not bind revision one",
        ),
        (
            "controller-mismatch",
            "creation receipt does not bind revision one",
        ),
        (
            "permanent-allocation-mismatch",
            "history substitution detected",
        ),
        (
            "declaration-mismatch",
            "creation operation evidence does not bind the initial record",
        ),
        (
            "immutable-contract-mismatch",
            "stored record columns do not match canonical record",
        ),
        (
            "provenance-mismatch",
            "stored revision provenance does not match canonical record",
        ),
        (
            "lifecycle-mismatch",
            "stored record columns do not match canonical record",
        ),
        (
            "wrong-creation-receipt-kind",
            "creation receipt columns do not match canonical receipt",
        ),
        (
            "creation-revision-other-than-one",
            "creation receipt columns do not match canonical receipt",
        ),
        (
            "current-not-revision-one-history",
            "current record does not equal latest history",
        ),
    ),
)
def test_creation_aggregate_rejects_identity_and_semantic_binding_mismatch(
    creation_aggregate: _CreationAggregateFixture,
    case: str,
    expected_message: str,
):
    aggregate = creation_aggregate
    overrides: dict[str, object]

    if case == "character-identity-mismatch":
        overrides = {
            "creation_receipt": _consistent_creation_receipt_record(
                aggregate,
                result_player_character_id=PlayerCharacterId(
                    value="pc.creation-other"
                ),
            )
        }
    elif case == "controller-mismatch":
        overrides = {
            "creation_receipt": _consistent_creation_receipt_record(
                aggregate,
                controller_binding=ControllerBindingRef(
                    value="binding.creation-other"
                ),
            )
        }
    elif case == "permanent-allocation-mismatch":
        overrides = {
            "allocation": replace(
                aggregate.allocation_record,
                player_character_id=PlayerCharacterId(
                    value="pc.creation-other"
                ),
            )
        }
    elif case == "declaration-mismatch":
        overrides = {
            "creation_receipt": _consistent_creation_receipt_record(
                aggregate,
                command=_creation_command("different-declarations"),
            )
        }
    elif case == "immutable-contract-mismatch":
        overrides = {
            "current": replace(
                aggregate.current_record,
                contract_version="structured-player-character/v2",
            )
        }
    elif case == "provenance-mismatch":
        overrides = {
            "revisions": (
                replace(
                    aggregate.revision_one_record,
                    source_reference=AuthoritySourceRef(
                        value="source.creation-other"
                    ),
                ),
            )
        }
    elif case == "lifecycle-mismatch":
        overrides = {
            "current": replace(
                aggregate.current_record,
                lifecycle=PlayerCharacterLifecycle.RETIRED.value,
            )
        }
    elif case == "wrong-creation-receipt-kind":
        overrides = {
            "creation_receipt": replace(
                aggregate.creation_receipt_record,
                command_kind=PlayerCharacterMutationKind.RETIRE.value,
            )
        }
    elif case == "creation-revision-other-than-one":
        overrides = {
            "creation_receipt": replace(
                aggregate.creation_receipt_record,
                resulting_revision=2,
            )
        }
    else:
        changed_command = _creation_command("different-current")
        changed_record = _record_for_command(aggregate, changed_command)
        overrides = {"current": _stored_current(changed_record)}

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_creation_aggregate(aggregate, **overrides)


def test_creation_aggregate_rejects_changed_evidence_with_old_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    changed_command = _creation_command("changed-evidence")
    _, changed_fingerprint = creation_fingerprint(changed_command)
    assert changed_fingerprint != creation_aggregate.operation_fingerprint
    corrupted = replace(
        creation_aggregate.creation_receipt_record,
        operation_evidence_canonical=(
            creation_operation_evidence_to_storage_bytes(
                changed_command,
                source_reference=(
                    creation_aggregate.canonical_record.authority_provenance.source_reference
                ),
            )
        ),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt columns do not match canonical receipt",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=corrupted,
        )


def test_creation_aggregate_rejects_changed_stored_operation_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    changed_fingerprint = b"\x00" * 32
    assert (
        changed_fingerprint
        != creation_aggregate.creation_receipt_record.fingerprint
    )
    corrupted = replace(
        creation_aggregate.creation_receipt_record,
        fingerprint=changed_fingerprint,
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt columns do not match canonical receipt",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=corrupted,
        )


def test_creation_aggregate_rejects_receipt_fingerprint_inconsistent_with_evidence(
    creation_aggregate: _CreationAggregateFixture,
):
    forged_fingerprint = CharacterOperationFingerprint(value="0" * 64)
    assert forged_fingerprint != creation_aggregate.operation_fingerprint
    forged_receipt = build_creation_success_receipt(
        key=creation_aggregate.phase_one_receipt.key,
        fingerprint=forged_fingerprint,
        result=creation_aggregate.phase_one_receipt.result,
    )
    corrupted = replace(
        creation_aggregate.creation_receipt_record,
        receipt_canonical=creation_receipt_to_storage_bytes(forged_receipt),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt columns do not match canonical receipt",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=corrupted,
        )


@pytest.mark.parametrize(
    ("substitution", "expected_message"),
    (
        (
            "operation-evidence",
            "creation receipt columns do not match canonical receipt",
        ),
        (
            "creation-receipt",
            "creation receipt does not bind revision one",
        ),
    ),
    ids=("operation-evidence", "creation-receipt"),
)
def test_creation_aggregate_rejects_second_creation_substitution(
    creation_aggregate: _CreationAggregateFixture,
    second_creation_aggregate: _CreationAggregateFixture,
    substitution: str,
    expected_message: str,
):
    if substitution == "operation-evidence":
        substituted = replace(
            creation_aggregate.creation_receipt_record,
            operation_evidence_canonical=(
                second_creation_aggregate.operation_evidence_canonical
            ),
        )
    else:
        substituted = second_creation_aggregate.creation_receipt_record

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=substituted,
        )


def test_creation_aggregate_recomputes_evidence_after_coordinated_fingerprint_corruption(
    creation_aggregate: _CreationAggregateFixture,
):
    forged_fingerprint = CharacterOperationFingerprint(value="f" * 64)
    assert forged_fingerprint != creation_aggregate.operation_fingerprint
    forged_receipt = build_creation_success_receipt(
        key=creation_aggregate.phase_one_receipt.key,
        fingerprint=forged_fingerprint,
        result=creation_aggregate.phase_one_receipt.result,
    )
    corrupted = replace(
        creation_aggregate.creation_receipt_record,
        fingerprint=fingerprint_to_storage_bytes(forged_fingerprint),
        receipt_canonical=creation_receipt_to_storage_bytes(forged_receipt),
    )
    assert corrupted.fingerprint == fingerprint_to_storage_bytes(
        forged_receipt.fingerprint
    )
    assert creation_fingerprint(creation_aggregate.command)[1] != forged_fingerprint

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt columns do not match canonical receipt",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=corrupted,
        )


def test_creation_aggregate_rejects_changed_canonical_content_with_stale_state_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    changed_command = _creation_command("changed-canonical-content")
    changed_record = _record_for_command(creation_aggregate, changed_command)
    assert (
        canonical_state_record_fingerprint(changed_record)
        != creation_aggregate.creation_receipt_record.result_record_fingerprint
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt does not bind revision one",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            revisions=(_stored_revision(changed_record),),
            current=_stored_current(changed_record),
        )


def test_creation_aggregate_rejects_changed_stored_state_record_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    changed_fingerprint = b"\xff" * 32
    assert (
        changed_fingerprint
        != creation_aggregate.creation_receipt_record.result_record_fingerprint
    )
    corrupted = replace(
        creation_aggregate.creation_receipt_record,
        result_record_fingerprint=changed_fingerprint,
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation receipt does not bind revision one",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=corrupted,
        )


def test_creation_aggregate_rejects_coordinated_provenance_substitution_against_unchanged_evidence(
    creation_aggregate: _CreationAggregateFixture,
):
    aggregate = creation_aggregate
    original = aggregate.canonical_record
    changed_source = AuthoritySourceRef(
        value="source.creation-coordinated-substitution"
    )
    substituted = original.detached_validated_copy(
        authority_provenance=AuthorityProvenance(
            target_player_character_id=original.player_character_id,
            prior_revision=None,
            resulting_revision=original.record_revision,
            mutation_kind=PlayerCharacterMutationKind.CREATE,
            authority_class=PlayerCharacterAuthorityClass.TRUSTED_CREATION,
            source_reference=changed_source,
        )
    )
    substituted_creation_receipt = replace(
        aggregate.creation_receipt_record,
        result_record_fingerprint=canonical_state_record_fingerprint(
            substituted
        ),
    )

    assert substituted.authority_provenance.source_reference == changed_source
    assert substituted.character_core == original.character_core
    assert substituted.narration_preferences == original.narration_preferences
    assert (
        substituted_creation_receipt.operation_evidence_canonical
        == aggregate.operation_evidence_canonical
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="creation operation evidence does not bind the initial record",
    ):
        _validate_creation_aggregate(
            aggregate,
            creation_receipt=substituted_creation_receipt,
            revisions=(_stored_revision(substituted),),
            current=_stored_current(substituted),
        )


def test_creation_aggregate_rejects_history_substituted_from_second_creation(
    creation_aggregate: _CreationAggregateFixture,
    second_creation_aggregate: _CreationAggregateFixture,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="history substitution detected",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            revisions=(second_creation_aggregate.revision_one_record,),
        )


def test_creation_aggregate_rejects_cross_character_current_substitution(
    creation_aggregate: _CreationAggregateFixture,
    second_creation_aggregate: _CreationAggregateFixture,
):
    substituted_record = _record_for_command(
        creation_aggregate,
        creation_aggregate.command,
        player_character_id=(
            second_creation_aggregate.canonical_record.player_character_id
        ),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="current record does not equal latest history",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            current=_stored_current(substituted_record),
        )


def test_creation_aggregate_rejects_cross_controller_current_substitution(
    creation_aggregate: _CreationAggregateFixture,
    second_creation_aggregate: _CreationAggregateFixture,
):
    substituted_record = _record_for_command(
        creation_aggregate,
        creation_aggregate.command,
        controller_binding=(
            second_creation_aggregate.canonical_record.controller_binding
        ),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="current record does not equal latest history",
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            current=_stored_current(substituted_record),
        )


def test_mutation_operation_evidence_encoding_is_deterministic(
    mutation_aggregate: _MutationAggregateFixture,
):
    command = mutation_aggregate.command
    encoded = mutation_operation_evidence_to_storage_bytes(command)

    assert encoded == mutation_aggregate.operation_evidence_canonical
    assert encoded == mutation_operation_evidence_to_storage_bytes(command)


def test_mutation_operation_evidence_round_trip_is_lossless(
    mutation_aggregate: _MutationAggregateFixture,
):
    encoded = mutation_aggregate.operation_evidence_canonical

    assert mutation_operation_evidence_from_storage(encoded) == (
        mutation_aggregate.command
    )
    assert (
        mutation_operation_evidence_to_storage_bytes(
            mutation_operation_evidence_from_storage(encoded)
        )
        == encoded
    )


def test_mutation_operation_evidence_preserves_exact_opaque_identifiers(
    mutation_aggregate: _MutationAggregateFixture,
):
    decoded = mutation_operation_evidence_from_storage(
        mutation_aggregate.operation_evidence_canonical
    )
    assert decoded.confirmation is not None

    assert decoded.target_player_character_id.value == (
        "pc.creation-Primary.MiXeD-K"
    )
    assert decoded.applicable_reference.player_character_id.value == (
        "pc.creation-Primary.MiXeD-K"
    )
    assert decoded.confirmation.player_character_id.value == (
        "pc.creation-Primary.MiXeD-K"
    )
    assert decoded.confirmation.operation_id.value == (
        "Operation.Mutation-Primary.MiXeD-K"
    )
    assert decoded.confirmation.source_reference.value == (
        "Source.Confirmation-Primary.MiXeD-K"
    )


def test_decoded_mutation_evidence_reconstructs_phase_one_command(
    mutation_aggregate: _MutationAggregateFixture,
):
    reconstructed = mutation_operation_evidence_from_storage(
        mutation_aggregate.operation_evidence_canonical
    )

    assert type(reconstructed) is CharacterMutationCommand
    assert reconstructed == mutation_aggregate.command


def test_reconstructed_mutation_evidence_produces_phase_one_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    reconstructed = mutation_operation_evidence_from_storage(
        mutation_aggregate.operation_evidence_canonical
    )
    _, fingerprint = mutation_fingerprint(
        reconstructed,
        operation_id=mutation_aggregate.operation_id,
    )

    assert fingerprint == mutation_aggregate.operation_fingerprint
    assert (
        fingerprint_to_storage_bytes(fingerprint)
        == mutation_aggregate.mutation_receipt_record.fingerprint
    )


def test_meaningful_mutation_command_change_changes_operation_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    changed = _mutation_command(
        mutation_aggregate.creation,
        operation_id=mutation_aggregate.operation_id,
        source_reference=AuthoritySourceRef(
            value="Source.Confirmation-MeaningfullyChanged"
        ),
    )
    _, changed_fingerprint = mutation_fingerprint(
        changed,
        operation_id=mutation_aggregate.operation_id,
    )

    assert changed != mutation_aggregate.command
    assert changed_fingerprint != mutation_aggregate.operation_fingerprint


def test_meaningful_successor_state_change_changes_state_record_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    changed = mutation_aggregate.successor.detached_validated_copy(
        character_core=_creation_command(
            "meaningfully-changed-successor"
        ).character_core
    )

    assert changed != mutation_aggregate.successor
    assert canonical_state_record_fingerprint(changed) != (
        canonical_state_record_fingerprint(mutation_aggregate.successor)
    )


def test_operation_and_state_record_fingerprint_types_remain_distinct(
    mutation_aggregate: _MutationAggregateFixture,
):
    operation_fingerprint = mutation_aggregate.operation_fingerprint
    state_record_fingerprint = canonical_state_record_fingerprint(
        mutation_aggregate.successor
    )

    assert type(operation_fingerprint) is CharacterOperationFingerprint
    assert type(state_record_fingerprint) is bytes
    assert operation_fingerprint != state_record_fingerprint


def test_complete_valid_mutation_aggregate_passes_validation(
    mutation_aggregate: _MutationAggregateFixture,
):
    assert _validate_mutation_aggregate(mutation_aggregate) is None


def test_mutation_aggregate_rejects_distinct_receipts_competing_for_one_successor_transition(
    mutation_aggregate: _MutationAggregateFixture,
):
    aggregate = mutation_aggregate
    competing_operation_id = PlayerCharacterOperationId(
        value="Operation.Mutation-Competing"
    )
    competing_command = _mutation_command(
        aggregate.creation,
        operation_id=competing_operation_id,
        source_reference=(
            aggregate.successor.authority_provenance.source_reference
        ),
    )
    competing_decision = evaluate_mutation_policy(
        aggregate.predecessor,
        command=competing_command,
        operation_id=competing_operation_id,
    )
    assert competing_decision.accepted
    assert competing_decision.resulting_record == aggregate.successor
    competing_receipt = _mutation_receipt_for_command(
        aggregate,
        competing_command,
        operation_id=competing_operation_id,
    )
    decoded_competing_receipt = mutation_receipt_from_storage(
        competing_receipt
    )

    assert (
        decoded_competing_receipt.key.operation_id
        == competing_operation_id
        != aggregate.phase_one_receipt.key.operation_id
    )
    assert (
        decoded_competing_receipt.fingerprint
        != aggregate.phase_one_receipt.fingerprint
    )
    assert (
        decoded_competing_receipt.result.resulting_revision
        == aggregate.phase_one_receipt.result.resulting_revision
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="multiple mutation receipts claim one successor transition",
    ):
        _validate_mutation_aggregate(
            aggregate,
            mutation_receipts=(
                aggregate.mutation_receipt_record,
                competing_receipt,
            ),
        )


def test_valid_mutation_aggregate_binds_every_authoritative_relationship(
    mutation_aggregate: _MutationAggregateFixture,
):
    aggregate = mutation_aggregate
    decoded_command = mutation_operation_evidence_from_storage(
        aggregate.mutation_receipt_record.operation_evidence_canonical
    )
    decoded_receipt = mutation_receipt_from_storage(
        aggregate.mutation_receipt_record
    )
    predecessor = canonical_record_from_revision_storage(
        aggregate.predecessor_revision_record
    )
    successor = canonical_record_from_revision_storage(
        aggregate.successor_revision_record
    )
    assert decoded_command.confirmation is not None

    assert decoded_command == aggregate.command
    assert decoded_receipt == aggregate.phase_one_receipt
    assert predecessor == aggregate.predecessor
    assert successor == aggregate.successor
    assert (
        canonical_record_from_current_storage(aggregate.current_record)
        == successor
    )
    assert (
        decoded_command.target_player_character_id
        == predecessor.player_character_id
        == successor.player_character_id
        == aggregate.creation.allocation_record.player_character_id
    )
    assert (
        predecessor.controller_binding
        == successor.controller_binding
        == aggregate.creation.controller_binding_record.controller_binding
    )
    assert decoded_command.expected_revision == predecessor.record_revision
    assert (
        decoded_command.applicable_reference.player_character_id
        == predecessor.player_character_id
    )
    assert (
        decoded_command.applicable_reference.contract_version
        == predecessor.contract_version
    )
    assert (
        decoded_command.applicable_reference.record_revision
        == predecessor.record_revision
    )
    assert successor.record_revision == predecessor.record_revision.successor()
    assert (
        decoded_receipt.result.resulting_revision
        == successor.record_revision
    )
    assert (
        successor.authority_provenance.prior_revision
        == predecessor.record_revision
    )
    assert (
        successor.authority_provenance.mutation_kind
        is PlayerCharacterMutationKind.RETIRE
    )
    assert (
        successor.authority_provenance.authority_class
        is PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
    )
    assert (
        decoded_command.confirmation.source_reference
        == successor.authority_provenance.source_reference
    )
    assert predecessor.character_core == successor.character_core
    assert predecessor.narration_preferences == successor.narration_preferences


@pytest.mark.parametrize(
    ("record_family", "missing_value", "expected_message"),
    (
        (
            "creation_receipt",
            None,
            "creation receipt record is required",
        ),
        (
            "mutation_receipts",
            (),
            "mutation receipts do not cover the complete successor history",
        ),
        (
            "revisions",
            (),
            "revision history record family is required",
        ),
        (
            "current",
            None,
            "current player-character record is required",
        ),
        (
            "controller_binding",
            None,
            "controller-binding record is required",
        ),
        (
            "allocation",
            None,
            "player-character allocation record is required",
        ),
    ),
    ids=(
        "creation-receipt",
        "mutation-receipt",
        "revision-history",
        "current-record",
        "controller-binding",
        "permanent-id-allocation",
    ),
)
def test_mutation_aggregate_rejects_each_missing_required_carrier_family(
    mutation_aggregate: _MutationAggregateFixture,
    record_family: str,
    missing_value: object,
    expected_message: str,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            **{record_family: missing_value},
        )


@pytest.mark.parametrize(
    ("case", "expected_message"),
    (
        (
            "character-identity-mismatch",
            "mutation receipt columns do not match canonical receipt",
        ),
        ("controller-mismatch", "history substitution detected"),
        ("permanent-allocation-mismatch", "history substitution detected"),
        (
            "immutable-declaration-mismatch",
            "mutation operation result does not equal successor history",
        ),
        (
            "immutable-contract-mismatch",
            "stored record columns do not match canonical record",
        ),
        (
            "applicable-reference-mismatch",
            "mutation operation evidence is invalid",
        ),
        (
            "required-confirmation-mismatch",
            "mutation operation result does not equal successor history",
        ),
        (
            "mutation-kind-mismatch",
            "stored revision provenance does not match canonical record",
        ),
        (
            "authority-class-mismatch",
            "stored revision provenance does not match canonical record",
        ),
        (
            "provenance-source-reference-mismatch",
            "stored revision provenance does not match canonical record",
        ),
    ),
)
def test_mutation_aggregate_rejects_identity_and_immutable_binding_mismatch(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
    case: str,
    expected_message: str,
):
    aggregate = mutation_aggregate
    overrides: dict[str, object]

    if case == "character-identity-mismatch":
        overrides = {
            "mutation_receipts": (
                replace(
                    aggregate.mutation_receipt_record,
                    player_character_id=(
                        second_mutation_aggregate.predecessor.player_character_id
                    ),
                ),
            )
        }
    elif case == "controller-mismatch":
        overrides = {
            "controller_binding": (
                second_mutation_aggregate.creation.controller_binding_record
            )
        }
    elif case == "permanent-allocation-mismatch":
        overrides = {
            "allocation": second_mutation_aggregate.creation.allocation_record
        }
    elif case == "immutable-declaration-mismatch":
        changed_successor = aggregate.successor.detached_validated_copy(
            character_core=_creation_command(
                "unauthorized-successor-declarations"
            ).character_core
        )
        overrides = {
            "mutation_receipts": (
                _stored_mutation_receipt(
                    receipt=aggregate.phase_one_receipt,
                    command=aggregate.command,
                    predecessor=aggregate.predecessor,
                    successor=changed_successor,
                ),
            ),
            "revisions": (
                aggregate.predecessor_revision_record,
                _stored_revision(changed_successor),
            ),
            "current": _stored_current(changed_successor),
        }
    elif case == "immutable-contract-mismatch":
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                replace(
                    aggregate.successor_revision_record,
                    contract_version="structured-player-character/v2",
                ),
            )
        }
    elif case == "applicable-reference-mismatch":
        corrupted_evidence = (
            aggregate.operation_evidence_canonical.replace(
                b'"record_revision":{"value":1}',
                b'"record_revision":{"value":2}',
                1,
            )
        )
        assert corrupted_evidence != aggregate.operation_evidence_canonical
        overrides = {
            "mutation_receipts": (
                replace(
                    aggregate.mutation_receipt_record,
                    operation_evidence_canonical=corrupted_evidence,
                ),
            )
        }
    elif case == "required-confirmation-mismatch":
        command = _mutation_command(
            aggregate.creation,
            operation_id=aggregate.operation_id,
            source_reference=AuthoritySourceRef(
                value="Source.Confirmation-DoesNotBindSuccessor"
            ),
        )
        overrides = {
            "mutation_receipts": (
                _mutation_receipt_for_command(aggregate, command),
            )
        }
    elif case == "mutation-kind-mismatch":
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                replace(
                    aggregate.successor_revision_record,
                    mutation_kind=PlayerCharacterMutationKind.FINAL_DEATH.value,
                ),
            )
        }
    elif case == "authority-class-mismatch":
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                replace(
                    aggregate.successor_revision_record,
                    authority_class=(
                        PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME.value
                    ),
                ),
            )
        }
    else:
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                replace(
                    aggregate.successor_revision_record,
                    source_reference=AuthoritySourceRef(
                        value="Source.Provenance-Substituted"
                    ),
                ),
            )
        }

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_mutation_aggregate(aggregate, **overrides)


@pytest.mark.parametrize(
    ("case", "expected_message"),
    (
        (
            "receipt-prior-does-not-match-predecessor",
            "mutation receipt prior revision does not match operation evidence",
        ),
        (
            "receipt-result-does-not-match-successor",
            "mutation receipt revision transition is inconsistent",
        ),
        (
            "identical-prior-and-resulting-revisions",
            "mutation receipt revision transition is inconsistent",
        ),
        (
            "skipped-revision",
            "revision history is missing or discontinuous",
        ),
        (
            "reversed-predecessor-and-successor",
            "revision history is missing or discontinuous",
        ),
        ("wrong-predecessor", "history substitution detected"),
        ("wrong-successor", "history substitution detected"),
        (
            "current-does-not-match-resulting-history",
            "current record does not equal latest history",
        ),
    ),
)
def test_mutation_aggregate_rejects_revision_and_history_relationship_corruption(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
    case: str,
    expected_message: str,
):
    aggregate = mutation_aggregate
    overrides: dict[str, object]

    if case == "receipt-prior-does-not-match-predecessor":
        overrides = {
            "mutation_receipts": (
                replace(
                    aggregate.mutation_receipt_record,
                    expected_revision=aggregate.successor.record_revision.value,
                ),
            )
        }
    elif case == "receipt-result-does-not-match-successor":
        overrides = {
            "mutation_receipts": (
                _mutation_receipt_for_command(
                    aggregate,
                    aggregate.command,
                    resulting_revision=PlayerCharacterRevision(value=3),
                ),
            )
        }
    elif case == "identical-prior-and-resulting-revisions":
        command = _mutation_command(
            aggregate.creation,
            operation_id=aggregate.operation_id,
            source_reference=(
                aggregate.successor.authority_provenance.source_reference
            ),
            expected_revision=aggregate.successor.record_revision,
        )
        overrides = {
            "mutation_receipts": (
                _mutation_receipt_for_command(aggregate, command),
            )
        }
    elif case == "skipped-revision":
        revision_three = PlayerCharacterRevision(value=3)
        skipped_successor = aggregate.successor.detached_validated_copy(
            record_revision=revision_three,
            authority_provenance=AuthorityProvenance(
                target_player_character_id=aggregate.successor.player_character_id,
                prior_revision=aggregate.successor.record_revision,
                resulting_revision=revision_three,
                mutation_kind=PlayerCharacterMutationKind.RETIRE,
                authority_class=(
                    PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
                ),
                source_reference=(
                    aggregate.successor.authority_provenance.source_reference
                ),
            ),
        )
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                _stored_revision(skipped_successor),
            )
        }
    elif case == "reversed-predecessor-and-successor":
        overrides = {
            "revisions": (
                aggregate.successor_revision_record,
                aggregate.predecessor_revision_record,
            )
        }
    elif case == "wrong-predecessor":
        overrides = {
            "revisions": (
                second_mutation_aggregate.predecessor_revision_record,
                aggregate.successor_revision_record,
            )
        }
    elif case == "wrong-successor":
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                second_mutation_aggregate.successor_revision_record,
            )
        }
    else:
        overrides = {"current": _stored_current(aggregate.predecessor)}

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_mutation_aggregate(aggregate, **overrides)


def test_mutation_aggregate_rejects_changed_evidence_with_old_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    changed = _mutation_command(
        mutation_aggregate.creation,
        operation_id=mutation_aggregate.operation_id,
        source_reference=AuthoritySourceRef(
            value="Source.ChangedEvidence-OldFingerprint"
        ),
    )
    corrupted = replace(
        mutation_aggregate.mutation_receipt_record,
        operation_evidence_canonical=(
            mutation_operation_evidence_to_storage_bytes(changed)
        ),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="mutation receipt columns do not match canonical receipt",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(corrupted,),
        )


def test_mutation_aggregate_rejects_changed_stored_operation_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    corrupted = replace(
        mutation_aggregate.mutation_receipt_record,
        fingerprint=b"\x00" * 32,
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="mutation receipt columns do not match canonical receipt",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(corrupted,),
        )


def test_mutation_aggregate_rejects_receipt_fingerprint_inconsistent_with_evidence(
    mutation_aggregate: _MutationAggregateFixture,
):
    forged_fingerprint = CharacterOperationFingerprint(value="0" * 64)
    forged_receipt = build_mutation_success_receipt(
        key=mutation_aggregate.phase_one_receipt.key,
        fingerprint=forged_fingerprint,
        result=mutation_aggregate.phase_one_receipt.result,
    )
    corrupted = replace(
        mutation_aggregate.mutation_receipt_record,
        fingerprint=fingerprint_to_storage_bytes(forged_fingerprint),
        receipt_canonical=mutation_receipt_to_storage_bytes(forged_receipt),
    )
    assert corrupted.fingerprint == fingerprint_to_storage_bytes(
        forged_receipt.fingerprint
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="mutation receipt columns do not match canonical receipt",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(corrupted,),
        )


@pytest.mark.parametrize(
    ("substitution", "expected_message"),
    (
        (
            "valid-operation-evidence",
            "mutation operation evidence does not bind receipt operation",
        ),
        ("valid-mutation-receipt", "mutation receipt substitution detected"),
    ),
)
def test_mutation_aggregate_rejects_second_valid_mutation_substitution(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
    substitution: str,
    expected_message: str,
):
    if substitution == "valid-operation-evidence":
        substituted = replace(
            mutation_aggregate.mutation_receipt_record,
            operation_evidence_canonical=(
                second_mutation_aggregate.operation_evidence_canonical
            ),
        )
    else:
        second = second_mutation_aggregate.mutation_receipt_record
        substituted = replace(
            second,
            before_record_fingerprint=(
                mutation_aggregate.mutation_receipt_record.before_record_fingerprint
            ),
            after_record_fingerprint=(
                mutation_aggregate.mutation_receipt_record.after_record_fingerprint
            ),
        )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(substituted,),
        )


def test_mutation_aggregate_rejects_coordinated_operation_and_fingerprint_corruption(
    mutation_aggregate: _MutationAggregateFixture,
):
    changed_command = _mutation_command(
        mutation_aggregate.creation,
        operation_id=mutation_aggregate.operation_id,
        source_reference=AuthoritySourceRef(
            value="Source.Coordinated-Operation-Corruption"
        ),
    )
    corrupted = _mutation_receipt_for_command(
        mutation_aggregate,
        changed_command,
    )
    decoded_receipt = mutation_receipt_from_storage(corrupted)
    decoded_command = mutation_operation_evidence_from_storage(
        corrupted.operation_evidence_canonical
    )
    _, recomputed = mutation_fingerprint(
        decoded_command,
        operation_id=decoded_receipt.key.operation_id,
    )
    assert decoded_receipt.fingerprint == recomputed
    assert corrupted.fingerprint == fingerprint_to_storage_bytes(recomputed)
    assert recomputed != mutation_aggregate.operation_fingerprint

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="mutation operation result does not equal successor history",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(corrupted,),
        )


@pytest.mark.parametrize(
    "state_record",
    ("predecessor", "successor"),
)
def test_mutation_aggregate_rejects_changed_canonical_content_with_stale_state_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
    state_record: str,
):
    aggregate = mutation_aggregate
    if state_record == "predecessor":
        changed_predecessor = _record_for_command(
            aggregate.creation,
            _creation_command("changed-predecessor-canonical-content"),
        )
        overrides = {
            "revisions": (
                _stored_revision(changed_predecessor),
                aggregate.successor_revision_record,
            )
        }
        expected_message = "creation receipt does not bind revision one"
    else:
        changed_successor = aggregate.successor.detached_validated_copy(
            character_core=_creation_command(
                "changed-successor-canonical-content"
            ).character_core
        )
        overrides = {
            "revisions": (
                aggregate.predecessor_revision_record,
                _stored_revision(changed_successor),
            ),
            "current": _stored_current(changed_successor),
        }
        expected_message = "mutation receipt does not bind adjacent history"

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=expected_message,
    ):
        _validate_mutation_aggregate(aggregate, **overrides)


@pytest.mark.parametrize(
    "state_record_fingerprint",
    ("before", "after"),
)
def test_mutation_aggregate_rejects_changed_stored_state_record_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
    state_record_fingerprint: str,
):
    field_name = f"{state_record_fingerprint}_record_fingerprint"
    corrupted = replace(
        mutation_aggregate.mutation_receipt_record,
        **{field_name: b"\xff" * 32},
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="mutation receipt does not bind adjacent history",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(corrupted,),
        )


@pytest.mark.parametrize(
    "history_record",
    ("predecessor", "successor"),
)
def test_mutation_aggregate_rejects_history_substituted_from_second_valid_mutation(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
    history_record: str,
):
    if history_record == "predecessor":
        revisions = (
            second_mutation_aggregate.predecessor_revision_record,
            mutation_aggregate.successor_revision_record,
        )
    else:
        revisions = (
            mutation_aggregate.predecessor_revision_record,
            second_mutation_aggregate.successor_revision_record,
        )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="history substitution detected",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            revisions=revisions,
        )


def test_mutation_aggregate_rejects_records_combined_from_two_valid_mutations(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
):
    second = second_mutation_aggregate

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="history substitution detected",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(second.mutation_receipt_record,),
            revisions=(
                second.predecessor_revision_record,
                second.successor_revision_record,
            ),
            current=second.current_record,
        )


def test_mutation_aggregate_rejects_cross_character_substitution(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="current record does not equal latest history",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            current=second_mutation_aggregate.current_record,
        )


def test_mutation_aggregate_rejects_cross_controller_substitution(
    mutation_aggregate: _MutationAggregateFixture,
    second_mutation_aggregate: _MutationAggregateFixture,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="history substitution detected",
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            controller_binding=(
                second_mutation_aggregate.creation.controller_binding_record
            ),
        )


@pytest.mark.parametrize(
    ("validation_path", "invalid_revision"),
    (
        ("current-record", True),
        ("current-record", False),
        ("revision-record", True),
        ("creation-receipt", True),
        ("mutation-expected-revision", True),
        ("mutation-resulting-revision", True),
    ),
)
def test_stored_revision_columns_require_exact_integers(
    creation_aggregate: _CreationAggregateFixture,
    mutation_aggregate: _MutationAggregateFixture,
    validation_path: str,
    invalid_revision: bool,
):
    if validation_path == "current-record":
        validate = lambda: canonical_record_from_current_storage(
            replace(
                creation_aggregate.current_record,
                record_revision=invalid_revision,
            )
        )
    elif validation_path == "revision-record":
        validate = lambda: canonical_record_from_revision_storage(
            replace(
                mutation_aggregate.successor_revision_record,
                prior_revision=invalid_revision,
            )
        )
    elif validation_path == "creation-receipt":
        validate = lambda: creation_receipt_from_storage(
            replace(
                creation_aggregate.creation_receipt_record,
                resulting_revision=invalid_revision,
            )
        )
    elif validation_path == "mutation-expected-revision":
        validate = lambda: mutation_receipt_from_storage(
            replace(
                mutation_aggregate.mutation_receipt_record,
                expected_revision=invalid_revision,
            )
        )
    else:
        validate = lambda: mutation_receipt_from_storage(
            replace(
                mutation_aggregate.mutation_receipt_record,
                resulting_revision=invalid_revision,
            )
        )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="must be an exact integer",
    ):
        validate()


def test_standalone_creation_receipt_rejects_mutable_operation_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match="fingerprint must contain exactly 32 immutable bytes",
    ):
        creation_receipt_from_storage(
            replace(
                creation_aggregate.creation_receipt_record,
                fingerprint=bytearray(
                    creation_aggregate.creation_receipt_record.fingerprint
                ),
            )
        )


def test_standalone_creation_receipt_rejects_mutable_state_record_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=(
            "result_record_fingerprint must contain exactly 32 immutable bytes"
        ),
    ):
        creation_receipt_from_storage(
            replace(
                creation_aggregate.creation_receipt_record,
                result_record_fingerprint=bytearray(
                    creation_aggregate.creation_receipt_record.result_record_fingerprint
                ),
            )
        )


def test_complete_aggregate_rejects_nested_mutable_state_record_fingerprint(
    mutation_aggregate: _MutationAggregateFixture,
):
    malformed = replace(
        mutation_aggregate.mutation_receipt_record,
        after_record_fingerprint=bytearray(
            mutation_aggregate.mutation_receipt_record.after_record_fingerprint
        ),
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=(
            "after_record_fingerprint must contain exactly 32 immutable bytes"
        ),
    ):
        _validate_mutation_aggregate(
            mutation_aggregate,
            mutation_receipts=(malformed,),
        )


@pytest.mark.parametrize(
    "fingerprint_column",
    (
        "creation-result",
        "mutation-before",
        "mutation-after",
    ),
)
def test_standalone_receipt_decoders_reject_empty_state_record_fingerprints(
    creation_aggregate: _CreationAggregateFixture,
    mutation_aggregate: _MutationAggregateFixture,
    fingerprint_column: str,
):
    if fingerprint_column == "creation-result":
        decode = lambda: creation_receipt_from_storage(
            replace(
                creation_aggregate.creation_receipt_record,
                result_record_fingerprint=b"",
            )
        )
        expected_field = "result_record_fingerprint"
    else:
        field_name = f"{fingerprint_column.removeprefix('mutation-')}_record_fingerprint"
        decode = lambda: mutation_receipt_from_storage(
            replace(
                mutation_aggregate.mutation_receipt_record,
                **{field_name: b""},
            )
        )
        expected_field = field_name

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=(
            f"{expected_field} must contain exactly 32 immutable bytes"
        ),
    ):
        decode()


def test_complete_aggregate_rejects_directly_constructed_empty_state_record_fingerprint(
    creation_aggregate: _CreationAggregateFixture,
):
    malformed = replace(
        creation_aggregate.creation_receipt_record,
        result_record_fingerprint=b"",
    )

    with pytest.raises(
        PlayerCharacterStoredRecordIntegrityError,
        match=(
            "result_record_fingerprint must contain exactly 32 immutable bytes"
        ),
    ):
        _validate_creation_aggregate(
            creation_aggregate,
            creation_receipt=malformed,
        )
