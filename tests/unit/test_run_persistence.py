from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunOperationNamespace,
    RunReceiptKey,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
    bind_player_character_fingerprint,
    bind_player_character_result,
    bind_player_character_to_run,
    construct_created_run,
    create_run_fingerprint,
    creation_result,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunStoredRecordIntegrityError,
    StoredCurrentRunRecord,
    StoredRunCreationReceiptRecord,
    StoredRunMutationReceiptRecord,
    StoredRunRevisionRecord,
    StoredRunSessionParticipationRecord,
    attach_operation_evidence_to_storage_bytes,
    binding_operation_evidence_to_storage_bytes,
    creation_operation_evidence_to_storage_bytes,
    fingerprint_to_storage_bytes,
    run_receipt_to_storage_bytes,
    validate_stored_run_record_set,
)


RUN_ID = RunId(value="run.persistence")
LINE_ID = ContinuousStoryLineId(value="csl.persistence")
SOURCE = RunAuthoritySourceRef(value="source.persistence")
CREATED_AT = datetime(2026, 7, 29, 10, 0, tzinfo=UTC)
JOINED_AT = datetime(2026, 7, 29, 10, 1, tzinfo=UTC)
BINDING_AT = datetime(2026, 7, 29, 10, 2, tzinfo=UTC)
AFTER_BINDING_AT = datetime(2026, 7, 29, 10, 3, tzinfo=UTC)
PLAYER_CHARACTER_ID = PlayerCharacterId(value="pc.persistence")


def _core(
    run: CanonicalRun,
    *,
    current_row: bool = False,
) -> dict[str, object]:
    creation = run.creation_provenance
    current = run.current_mutation_provenance
    binding = run.player_character_binding
    return {
        "run_id": run.run_id,
        "continuous_story_line_id": run.continuous_story_line_id,
        "lifecycle_status": run.lifecycle_status.value,
        "state_version": run.state_version.value,
        "creation_operation_id": creation.operation_id,
        "creation_source_reference": creation.source_reference,
        "creation_occurred_at": creation.occurred_at,
        "prior_state_version": (
            current.prior_state_version.value
            if current.prior_state_version is not None
            else None
        ),
        "mutation_kind": current.mutation_kind.value,
        "operation_id": current.operation_id,
        "source_reference": current.source_reference,
        "occurred_at": current.occurred_at,
        "binding_player_character_id": (
            binding.applicable_character_reference.player_character_id.value
            if binding is not None
            else None
        ),
        "binding_contract_version": (
            binding.applicable_character_reference.contract_version.value
            if binding is not None
            else None
        ),
        "binding_record_revision": (
            binding.applicable_character_reference.record_revision.value
            if binding is not None
            else None
        ),
        "binding_state": (
            binding.binding_state if binding is not None else None
        ),
        "binding_operation_id": (
            binding.binding_operation_id.value
            if binding is not None
            else None
        ),
        "binding_authority_source_ref": (
            binding.binding_authority_source_ref.value
            if binding is not None
            else None
        ),
        "bound_at": binding.bound_at if binding is not None else None,
        "inactivated_at": (
            binding.inactivated_at if binding is not None else None
        ),
        "active_player_character_id": (
            binding.applicable_character_reference.player_character_id.value
            if current_row and binding is not None
            else None
        ),
    }


def _records() -> tuple[
    CanonicalRun,
    StoredCurrentRunRecord,
    tuple[StoredRunRevisionRecord, ...],
    tuple[StoredRunSessionParticipationRecord, ...],
    StoredRunCreationReceiptRecord,
    tuple[StoredRunMutationReceiptRecord, ...],
]:
    create_command = CreateRunCommand(source_reference=SOURCE)
    create_operation = RunOperationId(value="operation.create")
    created = construct_created_run(
        create_command,
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=create_operation,
        occurred_at=CREATED_AT,
    )
    attach_command = AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id="session.persistence",
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    attach_operation = RunOperationId(value="operation.attach")
    attached = attach_session_to_run(
        created,
        attach_command,
        operation_id=attach_operation,
        occurred_at=JOINED_AT,
    )
    revisions = (
        StoredRunRevisionRecord(**_core(created), created_at=CREATED_AT),
        StoredRunRevisionRecord(**_core(attached), created_at=JOINED_AT),
    )
    current = StoredCurrentRunRecord(
        **_core(attached),
        created_at=CREATED_AT,
        updated_at=JOINED_AT,
    )
    participation = attached.trusted_participation_references[-1]
    participations = (
        StoredRunSessionParticipationRecord(
            session_id=participation.session_id,
            run_id=participation.run_id,
            continuous_story_line_id=participation.continuous_story_line_id,
            joined_state_version=participation.joined_state_version.value,
            operation_id=participation.operation_id,
            source_reference=participation.source_reference,
            joined_at=JOINED_AT,
        ),
    )
    _, creation_fingerprint = create_run_fingerprint(create_command)
    creation_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=create_operation,
        ),
        fingerprint=creation_fingerprint,
        command_kind=RunMutationKind.CREATE,
        result=creation_result(created),
    )
    stored_creation = StoredRunCreationReceiptRecord(
        operation_namespace=creation_receipt.key.operation_namespace.value,
        operation_id=creation_receipt.key.operation_id,
        fingerprint=fingerprint_to_storage_bytes(creation_receipt.fingerprint),
        command_kind=creation_receipt.command_kind.value,
        result_schema_version=creation_receipt.result.result_schema_version,
        result_run_id=RUN_ID,
        result_continuous_story_line_id=LINE_ID,
        resulting_lifecycle_status=created.lifecycle_status.value,
        resulting_state_version=1,
        receipt_canonical=run_receipt_to_storage_bytes(creation_receipt),
        operation_evidence_canonical=(
            creation_operation_evidence_to_storage_bytes(create_command)
        ),
        created_at=CREATED_AT,
    )
    _, mutation_fingerprint = attach_session_fingerprint(
        attach_command,
        operation_id=attach_operation,
    )
    mutation_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=attach_operation,
        ),
        fingerprint=mutation_fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(attached),
    )
    stored_mutation = StoredRunMutationReceiptRecord(
        run_id=RUN_ID,
        operation_namespace=mutation_receipt.key.operation_namespace.value,
        operation_id=mutation_receipt.key.operation_id,
        fingerprint=fingerprint_to_storage_bytes(mutation_receipt.fingerprint),
        command_kind=mutation_receipt.command_kind.value,
        result_schema_version=mutation_receipt.result.result_schema_version,
        expected_state_version=1,
        result_run_id=RUN_ID,
        result_continuous_story_line_id=LINE_ID,
        resulting_lifecycle_status=attached.lifecycle_status.value,
        resulting_state_version=2,
        participation_session_id=participation.session_id,
        participation_operation_id=participation.operation_id.value,
        participation_source_reference=participation.source_reference.value,
        result_player_character_id=None,
        result_character_contract_version=None,
        result_character_record_revision=None,
        receipt_canonical=run_receipt_to_storage_bytes(mutation_receipt),
        operation_evidence_canonical=(
            attach_operation_evidence_to_storage_bytes(attach_command)
        ),
        created_at=JOINED_AT,
    )
    return (
        attached,
        current,
        revisions,
        participations,
        stored_creation,
        (stored_mutation,),
    )


def _bound_records() -> tuple[
    CanonicalRun,
    StoredCurrentRunRecord,
    tuple[StoredRunRevisionRecord, ...],
    StoredRunCreationReceiptRecord,
    tuple[StoredRunMutationReceiptRecord, ...],
    CanonicalPlayerCharacter,
]:
    _, _, legacy_revisions, _, creation_receipt, _ = _records()
    create_command = CreateRunCommand(source_reference=SOURCE)
    created = construct_created_run(
        create_command,
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.create"),
        occurred_at=CREATED_AT,
    )
    referenced_character = CreatePlayerCharacterPolicy().create(
        player_character_id=PLAYER_CHARACTER_ID,
        controller_binding=ControllerBindingRef(
            value="binding.persistence"
        ),
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(
            value="source.character-persistence"
        ),
    )
    bind_command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    bind_operation = RunOperationId(value="operation.bind")
    bound = bind_player_character_to_run(
        created,
        bind_command,
        applicable_character_reference=ApplicableCharacterReference(
            player_character_id=referenced_character.player_character_id,
            contract_version=referenced_character.contract_version,
            record_revision=referenced_character.record_revision,
        ),
        operation_id=bind_operation,
        occurred_at=BINDING_AT,
    )
    revisions = (
        legacy_revisions[0],
        StoredRunRevisionRecord(
            **_core(bound),
            created_at=BINDING_AT,
        ),
    )
    current = StoredCurrentRunRecord(
        **_core(bound, current_row=True),
        created_at=CREATED_AT,
        updated_at=BINDING_AT,
    )
    _, fingerprint = bind_player_character_fingerprint(
        bind_command,
        operation_id=bind_operation,
    )
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=bind_operation,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=bind_player_character_result(bound),
    )
    stored_mutation = StoredRunMutationReceiptRecord(
        run_id=RUN_ID,
        operation_namespace=receipt.key.operation_namespace.value,
        operation_id=bind_operation,
        fingerprint=fingerprint_to_storage_bytes(fingerprint),
        command_kind=receipt.command_kind.value,
        result_schema_version=receipt.result.result_schema_version,
        expected_state_version=1,
        result_run_id=RUN_ID,
        result_continuous_story_line_id=LINE_ID,
        resulting_lifecycle_status=bound.lifecycle_status.value,
        resulting_state_version=2,
        participation_session_id=None,
        participation_operation_id=None,
        participation_source_reference=None,
        result_player_character_id=PLAYER_CHARACTER_ID.value,
        result_character_contract_version=(
            PlayerCharacterContractVersion.V1.value
        ),
        result_character_record_revision=1,
        receipt_canonical=run_receipt_to_storage_bytes(receipt),
        operation_evidence_canonical=(
            binding_operation_evidence_to_storage_bytes(bind_command)
        ),
        created_at=BINDING_AT,
    )
    return (
        bound,
        current,
        revisions,
        creation_receipt,
        (stored_mutation,),
        referenced_character,
    )


def _bound_then_attached_records() -> tuple[
    CanonicalRun,
    StoredCurrentRunRecord,
    tuple[StoredRunRevisionRecord, ...],
    tuple[StoredRunSessionParticipationRecord, ...],
    StoredRunCreationReceiptRecord,
    tuple[StoredRunMutationReceiptRecord, ...],
    CanonicalPlayerCharacter,
]:
    (
        bound,
        _,
        revisions,
        creation,
        binding_mutations,
        referenced_character,
    ) = _bound_records()
    command = AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id="session.after-binding",
        expected_state_version=RunStateVersion(value=2),
        source_reference=SOURCE,
    )
    operation_id = RunOperationId(value="operation.attach-after-binding")
    attached = attach_session_to_run(
        bound,
        command,
        operation_id=operation_id,
        occurred_at=AFTER_BINDING_AT,
    )
    participation = attached.trusted_participation_references[-1]
    stored_participation = StoredRunSessionParticipationRecord(
        session_id=participation.session_id,
        run_id=participation.run_id,
        continuous_story_line_id=participation.continuous_story_line_id,
        joined_state_version=participation.joined_state_version.value,
        operation_id=participation.operation_id,
        source_reference=participation.source_reference,
        joined_at=AFTER_BINDING_AT,
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
        result=attach_session_result(attached),
    )
    stored_receipt = StoredRunMutationReceiptRecord(
        run_id=RUN_ID,
        operation_namespace=receipt.key.operation_namespace.value,
        operation_id=operation_id,
        fingerprint=fingerprint_to_storage_bytes(fingerprint),
        command_kind=receipt.command_kind.value,
        result_schema_version=receipt.result.result_schema_version,
        expected_state_version=2,
        result_run_id=RUN_ID,
        result_continuous_story_line_id=LINE_ID,
        resulting_lifecycle_status=attached.lifecycle_status.value,
        resulting_state_version=3,
        participation_session_id=participation.session_id,
        participation_operation_id=participation.operation_id.value,
        participation_source_reference=(
            participation.source_reference.value
        ),
        result_player_character_id=None,
        result_character_contract_version=None,
        result_character_record_revision=None,
        receipt_canonical=run_receipt_to_storage_bytes(receipt),
        operation_evidence_canonical=(
            attach_operation_evidence_to_storage_bytes(command)
        ),
        created_at=AFTER_BINDING_AT,
    )
    return (
        attached,
        StoredCurrentRunRecord(
            **_core(attached, current_row=True),
            created_at=CREATED_AT,
            updated_at=AFTER_BINDING_AT,
        ),
        (
            *revisions,
            StoredRunRevisionRecord(
                **_core(attached),
                created_at=AFTER_BINDING_AT,
            ),
        ),
        (stored_participation,),
        creation,
        (*binding_mutations, stored_receipt),
        referenced_character,
    )


def test_complete_run_storage_strictly_reconstructs_current_history() -> None:
    run, current, revisions, participations, creation, mutations = _records()

    reconstructed = validate_stored_run_record_set(
        creation_receipt=creation,
        mutation_receipts=mutations,
        revisions=revisions,
        current=current,
        participations=participations,
    )

    assert reconstructed == run
    assert reconstructed.player_character_binding is None


def test_complete_binding_storage_reconstructs_exact_cross_aggregate_evidence() -> None:
    (
        run,
        current,
        revisions,
        creation,
        mutations,
        referenced_character,
    ) = _bound_records()

    reconstructed = validate_stored_run_record_set(
        creation_receipt=creation,
        mutation_receipts=mutations,
        revisions=revisions,
        current=current,
        participations=(),
        referenced_player_character_revision=referenced_character,
    )

    assert reconstructed == run
    binding = reconstructed.player_character_binding
    assert binding is not None
    assert binding.applicable_character_reference.player_character_id == (
        referenced_character.player_character_id
    )
    assert binding.applicable_character_reference.contract_version == (
        referenced_character.contract_version
    )
    assert binding.applicable_character_reference.record_revision == (
        referenced_character.record_revision
    )
    assert current.active_player_character_id == PLAYER_CHARACTER_ID.value


def test_later_attachment_preserves_the_exact_binding_evidence() -> None:
    (
        run,
        current,
        revisions,
        participations,
        creation,
        mutations,
        referenced_character,
    ) = _bound_then_attached_records()

    reconstructed = validate_stored_run_record_set(
        creation_receipt=creation,
        mutation_receipts=mutations,
        revisions=revisions,
        current=current,
        participations=participations,
        referenced_player_character_revision=referenced_character,
    )

    assert reconstructed == run
    assert reconstructed.state_version == RunStateVersion(value=3)
    assert reconstructed.player_character_binding is not None
    assert (
        reconstructed.player_character_binding.binding_operation_id.value
        == "operation.bind"
    )
    assert (
        reconstructed.current_mutation_provenance.mutation_kind
        is RunMutationKind.ATTACH_SESSION
    )


def test_binding_storage_requires_surviving_immutable_character_evidence() -> None:
    _, current, revisions, creation, mutations, _ = _bound_records()

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="referenced immutable player-character revision is missing",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=revisions,
            current=current,
            participations=(),
        )


def test_binding_storage_rejects_a_foreign_character_revision() -> None:
    _, current, revisions, creation, mutations, _ = _bound_records()
    foreign_character = CreatePlayerCharacterPolicy().create(
        player_character_id=PlayerCharacterId(value="pc.foreign"),
        controller_binding=ControllerBindingRef(value="binding.foreign"),
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(value="source.foreign"),
    )

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="binding reference does not match",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=revisions,
            current=current,
            participations=(),
            referenced_player_character_revision=foreign_character,
        )


@pytest.mark.parametrize(
    ("revision_change", "current_change", "message"),
    (
        (
            {"binding_operation_id": None},
            {"binding_operation_id": None},
            "binding evidence is partial",
        ),
        (
            {"bound_at": datetime(2026, 7, 29, 10, 2)},
            {"bound_at": datetime(2026, 7, 29, 10, 2)},
            "bound_at must be an exact UTC",
        ),
    ),
)
def test_binding_storage_rejects_partial_or_malformed_envelopes(
    revision_change: dict[str, object],
    current_change: dict[str, object],
    message: str,
) -> None:
    (
        _,
        current,
        revisions,
        creation,
        mutations,
        referenced_character,
    ) = _bound_records()
    corrupted_revisions = (
        revisions[0],
        replace(revisions[1], **revision_change),
    )

    with pytest.raises(RunStoredRecordIntegrityError, match=message):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=corrupted_revisions,
            current=replace(current, **current_change),
            participations=(),
            referenced_player_character_revision=referenced_character,
        )


def test_binding_storage_rejects_contradictory_current_backstop() -> None:
    (
        _,
        current,
        revisions,
        creation,
        mutations,
        referenced_character,
    ) = _bound_records()

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="does not match the current-row backstop",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=revisions,
            current=replace(
                current,
                active_player_character_id="pc.contradictory",
            ),
            participations=(),
            referenced_player_character_revision=referenced_character,
        )


def test_binding_storage_requires_exact_receipt_and_continuous_history() -> None:
    (
        _,
        current,
        revisions,
        creation,
        mutations,
        referenced_character,
    ) = _bound_records()

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="do not cover successor history",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=(),
            revisions=revisions,
            current=current,
            participations=(),
            referenced_player_character_revision=referenced_character,
        )
    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="receipt columns are inconsistent",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=(
                replace(
                    mutations[0],
                    result_character_record_revision=2,
                ),
            ),
            revisions=revisions,
            current=current,
            participations=(),
            referenced_player_character_revision=referenced_character,
        )
    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="missing or discontinuous",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=(revisions[1],),
            current=current,
            participations=(),
            referenced_player_character_revision=referenced_character,
        )


@pytest.mark.parametrize(
    ("revision_change", "current_change"),
    (
        (
            {
                "creation_operation_id": RunOperationId(
                    value="operation.corrupted-creation"
                )
            },
            {
                "creation_operation_id": RunOperationId(
                    value="operation.corrupted-creation"
                )
            },
        ),
        (
            {
                "creation_source_reference": RunAuthoritySourceRef(
                    value="source.corrupted-creation"
                )
            },
            {
                "creation_source_reference": RunAuthoritySourceRef(
                    value="source.corrupted-creation"
                )
            },
        ),
        (
            {
                "creation_occurred_at": datetime(
                    2026,
                    7,
                    29,
                    10,
                    0,
                    1,
                    tzinfo=UTC,
                )
            },
            {
                "creation_occurred_at": datetime(
                    2026,
                    7,
                    29,
                    10,
                    0,
                    1,
                    tzinfo=UTC,
                ),
                "created_at": datetime(
                    2026,
                    7,
                    29,
                    10,
                    0,
                    1,
                    tzinfo=UTC,
                ),
            },
        ),
    ),
)
def test_successor_and_current_cannot_rewrite_creation_provenance_together(
    revision_change: dict[str, object],
    current_change: dict[str, object],
) -> None:
    _, current, revisions, participations, creation, mutations = _records()
    corrupted_revisions = (
        revisions[0],
        replace(revisions[1], **revision_change),
    )

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="rewrote immutable creation provenance",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=corrupted_revisions,
            current=replace(current, **current_change),
            participations=participations,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ({"state_version": 1}, "latest immutable revision"),
        (
            {"binding_player_character_id": "pc.forbidden"},
            "latest immutable revision",
        ),
    ),
)
def test_current_run_corruption_is_rejected_without_repair(
    change: dict[str, object],
    message: str,
) -> None:
    _, current, revisions, participations, creation, mutations = _records()

    with pytest.raises(RunStoredRecordIntegrityError, match=message):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=revisions,
            current=replace(current, **change),
            participations=participations,
        )


def test_missing_participation_or_receipt_evidence_fails_closed() -> None:
    _, current, revisions, participations, creation, mutations = _records()

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="stored canonical Run state is invalid",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=revisions,
            current=current,
            participations=(),
        )
    with pytest.raises(RunStoredRecordIntegrityError, match="do not cover"):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=(),
            revisions=revisions,
            current=current,
            participations=participations,
        )


def test_attachment_receipt_rejects_character_binding_columns() -> None:
    _, current, revisions, participations, creation, mutations = _records()
    corrupted = replace(
        mutations[0],
        result_player_character_id="pc.forbidden",
    )

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="populated binding result fields",
    ):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=(corrupted,),
            revisions=revisions,
            current=current,
            participations=participations,
        )
