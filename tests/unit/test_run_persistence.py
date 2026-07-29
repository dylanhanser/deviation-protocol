from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    RunOperationNamespace,
    RunReceiptKey,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
    construct_created_run,
    create_run_fingerprint,
    creation_result,
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


def _core(run: CanonicalRun) -> dict[str, object]:
    creation = run.creation_provenance
    current = run.current_mutation_provenance
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
        "binding_player_character_id": None,
        "binding_contract_version": None,
        "binding_record_revision": None,
        "binding_state": None,
        "binding_operation_id": None,
        "binding_authority_source_ref": None,
        "bound_at": None,
        "inactivated_at": None,
        "active_player_character_id": None,
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
            "binding seam",
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

    with pytest.raises(RunStoredRecordIntegrityError, match="participation history"):
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


def test_mutation_receipt_rejects_reserved_character_binding_columns() -> None:
    _, current, revisions, participations, creation, mutations = _records()
    corrupted = replace(
        mutations[0],
        result_player_character_id="pc.forbidden",
    )

    with pytest.raises(RunStoredRecordIntegrityError, match="reserved binding"):
        validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=(corrupted,),
            revisions=revisions,
            current=current,
            participations=participations,
        )
