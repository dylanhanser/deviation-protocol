from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from deviation_protocol.application.run_operations import (
    ATTACH_SESSION_RESULT_SCHEMA_VERSION,
    BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION,
    CREATE_RUN_RESULT_SCHEMA_VERSION,
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    ReservedBindPlayerCharacterCommand,
    RunOperationFingerprint,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecisionCode,
    RunSafeResult,
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
    evaluate_receipt,
    reject_reserved_bind_player_character,
)
from pydantic import ValidationError
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunLifecycleStatus,
    RunMutationKind,
    RunMutationProvenance,
    RunOperationId,
    RunSessionParticipationReference,
    RunStateVersion,
)


RUN_ID = RunId(value="run.123e4567e89b42d3a456426614174000")
LINE_ID = ContinuousStoryLineId(value="csl.123e4567e89b42d3a456426614174001")
SOURCE = RunAuthoritySourceRef(value="source.run")
PLAYER_CHARACTER_ID = PlayerCharacterId(value="pc.bound")
CHARACTER_REFERENCE = ApplicableCharacterReference(
    player_character_id=PLAYER_CHARACTER_ID,
    contract_version=PlayerCharacterContractVersion.V1,
    record_revision=PlayerCharacterRevision(value=7),
)


def record(*, attached: bool = False) -> CanonicalRun:
    create = RunMutationProvenance(
        target_run_id=RUN_ID,
        target_continuous_story_line_id=LINE_ID,
        prior_state_version=None,
        resulting_state_version=RunStateVersion(value=1),
        mutation_kind=RunMutationKind.CREATE,
        operation_id=RunOperationId(value="operation.create"),
        source_reference=SOURCE,
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    if not attached:
        return CanonicalRun(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            lifecycle_status=RunLifecycleStatus.PRE_FIRST_TURN,
            state_version=RunStateVersion(value=1),
            creation_provenance=create,
            current_mutation_provenance=create,
        )
    participation = RunSessionParticipationReference(
        session_id="session.1",
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        joined_state_version=RunStateVersion(value=2),
        operation_id=RunOperationId(value="operation.attach"),
        source_reference=SOURCE,
    )
    return CanonicalRun(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        lifecycle_status=RunLifecycleStatus.PRE_FIRST_TURN,
        state_version=RunStateVersion(value=2),
        creation_provenance=create,
        current_mutation_provenance=RunMutationProvenance(
            target_run_id=RUN_ID,
            target_continuous_story_line_id=LINE_ID,
            prior_state_version=RunStateVersion(value=1),
            resulting_state_version=RunStateVersion(value=2),
            mutation_kind=RunMutationKind.ATTACH_SESSION,
            operation_id=participation.operation_id,
            source_reference=SOURCE,
            occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        ),
        trusted_participation_references=(participation,),
    )


def test_fingerprints_are_deterministic_and_bind_every_admitted_input() -> None:
    create_bytes, create_hash = create_run_fingerprint(CreateRunCommand(source_reference=SOURCE))
    assert create_hash.value == "6ee16df58e55f922954f522ea2f4e727266713124d959b3595d9a54ab0104506"
    assert create_bytes
    command = AttachSessionCommand(run_id=RUN_ID, continuous_story_line_id=LINE_ID, session_id="session.1", expected_state_version=RunStateVersion(value=1), source_reference=SOURCE)
    first = attach_session_fingerprint(command, operation_id=RunOperationId(value="operation.a"))
    second = attach_session_fingerprint(command, operation_id=RunOperationId(value="operation.a"))
    changed = attach_session_fingerprint(command, operation_id=RunOperationId(value="operation.b"))
    assert first == second
    assert first != changed

    bind_command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    bound = bind_player_character_fingerprint(
        bind_command,
        operation_id=RunOperationId(value="operation.bind"),
    )
    assert bound == bind_player_character_fingerprint(
        bind_command,
        operation_id=RunOperationId(value="operation.bind"),
    )
    changed_commands = (
        bind_command.model_copy(
            update={"run_id": RunId(value="run.changed")}
        ),
        bind_command.model_copy(
            update={
                "continuous_story_line_id": ContinuousStoryLineId(
                    value="csl.changed"
                )
            }
        ),
        bind_command.model_copy(
            update={
                "target_player_character_id": PlayerCharacterId(
                    value="pc.changed"
                )
            }
        ),
        bind_command.model_copy(
            update={"expected_state_version": RunStateVersion(value=2)}
        ),
        bind_command.model_copy(
            update={
                "source_reference": RunAuthoritySourceRef(
                    value="source.changed"
                )
            }
        ),
    )
    for changed_command in changed_commands:
        assert bind_player_character_fingerprint(
            changed_command,
            operation_id=RunOperationId(value="operation.bind"),
        ) != bound
    assert bind_player_character_fingerprint(
        bind_command,
        operation_id=RunOperationId(value="operation.changed"),
    ) != bound


def test_pure_creation_and_participation_commands_build_exact_successors() -> None:
    created = construct_created_run(
        CreateRunCommand(source_reference=SOURCE),
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.create"),
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    attached = attach_session_to_run(
        created,
        AttachSessionCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            session_id="session.1",
            expected_state_version=RunStateVersion(value=1),
            source_reference=SOURCE,
        ),
        operation_id=RunOperationId(value="operation.attach"),
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    assert attached.state_version == RunStateVersion(value=2)
    assert attached.player_character_binding is None
    with pytest.raises(ValueError, match="already participates"):
        attach_session_to_run(
            attached,
            AttachSessionCommand(
                run_id=RUN_ID,
                continuous_story_line_id=LINE_ID,
                session_id="session.1",
                expected_state_version=RunStateVersion(value=2),
                source_reference=SOURCE,
            ),
            operation_id=RunOperationId(value="operation.duplicate"),
            occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        )


def test_pure_binding_command_builds_exact_successor_without_character_mutation() -> None:
    created = record()
    command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=created.state_version,
        source_reference=SOURCE,
    )
    operation_id = RunOperationId(value="operation.bind")
    occurred_at = datetime(2026, 7, 29, tzinfo=UTC)

    bound = bind_player_character_to_run(
        created,
        command,
        applicable_character_reference=CHARACTER_REFERENCE,
        operation_id=operation_id,
        occurred_at=occurred_at,
    )

    assert created.player_character_binding is None
    assert bound.state_version == RunStateVersion(value=2)
    assert bound.creation_provenance == created.creation_provenance
    assert bound.trusted_participation_references == ()
    assert bound.current_mutation_provenance.mutation_kind is (
        RunMutationKind.BIND_PLAYER_CHARACTER
    )
    assert bound.current_mutation_provenance.operation_id == operation_id
    assert bound.current_mutation_provenance.source_reference == SOURCE
    assert bound.current_mutation_provenance.occurred_at == occurred_at
    binding = bound.player_character_binding
    assert binding is not None
    assert binding.run_id == RUN_ID
    assert binding.continuous_story_line_id == LINE_ID
    assert binding.applicable_character_reference == CHARACTER_REFERENCE
    assert binding.binding_state == "active"
    assert binding.inactivated_at is None
    assert binding.binding_operation_id == operation_id
    assert binding.binding_authority_source_ref == SOURCE
    assert binding.bound_at == occurred_at

    attached = attach_session_to_run(
        bound,
        AttachSessionCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            session_id="session.after-binding",
            expected_state_version=bound.state_version,
            source_reference=SOURCE,
        ),
        operation_id=RunOperationId(value="operation.attach-after-binding"),
        occurred_at=occurred_at,
    )
    assert attached.player_character_binding == binding
    assert attached.state_version == RunStateVersion(value=3)


@pytest.mark.parametrize(
    ("change", "message"),
    (
        (
            {"run_id": RunId(value="run.changed")},
            "does not bind the current Run",
        ),
        (
            {
                "continuous_story_line_id": ContinuousStoryLineId(
                    value="csl.changed"
                )
            },
            "does not bind the current Run",
        ),
        (
            {"expected_state_version": RunStateVersion(value=2)},
            "does not bind the current Run",
        ),
        (
            {
                "target_player_character_id": PlayerCharacterId(
                    value="pc.changed"
                )
            },
            "does not bind the command target",
        ),
    ),
)
def test_pure_binding_rejects_stale_or_contradictory_evidence(
    change: dict[str, object],
    message: str,
) -> None:
    command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    ).model_copy(update=change)

    with pytest.raises(ValueError, match=message):
        bind_player_character_to_run(
            record(),
            command,
            applicable_character_reference=CHARACTER_REFERENCE,
            operation_id=RunOperationId(value="operation.bind"),
            occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
        )


def test_safe_results_and_receipt_replay_conflict_are_exact() -> None:
    created = creation_result(record())
    assert created.result_schema_version == CREATE_RUN_RESULT_SCHEMA_VERSION
    attached = attach_session_result(record(attached=True))
    assert attached.result_schema_version == ATTACH_SESSION_RESULT_SCHEMA_VERSION
    key = RunReceiptKey(operation_namespace=RunOperationNamespace.CREATE_V1, operation_id=RunOperationId(value="operation.create"))
    _, fingerprint = create_run_fingerprint(CreateRunCommand(source_reference=SOURCE))
    receipt = StoredRunSuccessReceipt(key=key, fingerprint=fingerprint, command_kind=RunMutationKind.CREATE, result=created)
    assert evaluate_receipt(receipt, key=key, fingerprint=fingerprint, command_kind=RunMutationKind.CREATE).code is RunReplayDecisionCode.REPLAY
    assert evaluate_receipt(receipt, key=key, fingerprint=RunOperationFingerprint(value="0" * 64), command_kind=RunMutationKind.CREATE).code is RunReplayDecisionCode.CONFLICT
    assert evaluate_receipt(None, key=key, fingerprint=fingerprint, command_kind=RunMutationKind.CREATE).code is RunReplayDecisionCode.ABSENT


def test_binding_safe_result_and_receipt_replay_are_exact() -> None:
    command = BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
    )
    operation_id = RunOperationId(value="operation.bind")
    bound = bind_player_character_to_run(
        record(),
        command,
        applicable_character_reference=CHARACTER_REFERENCE,
        operation_id=operation_id,
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    result = bind_player_character_result(bound)
    key = RunReceiptKey(
        operation_namespace=RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
        operation_id=operation_id,
        run_id=RUN_ID,
    )
    _, fingerprint = bind_player_character_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = StoredRunSuccessReceipt(
        key=key,
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=result,
    )

    assert (
        result.result_schema_version
        == BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION
    )
    assert result.participation_reference is None
    assert result.applicable_character_reference == CHARACTER_REFERENCE
    assert evaluate_receipt(
        receipt,
        key=key,
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
    ).stored_success_result == result


def test_legacy_safe_result_bytes_do_not_gain_binding_fields() -> None:
    created = creation_result(record())
    attached = attach_session_result(record(attached=True))

    assert "applicable_character_reference" not in (
        created.model_dump(mode="python")
    )
    assert "applicable_character_reference" not in (
        attached.model_dump(mode="python")
    )
    assert "applicable_character_reference" in (
        bind_player_character_result(
            bind_player_character_to_run(
                record(),
                BindPlayerCharacterCommand(
                    run_id=RUN_ID,
                    continuous_story_line_id=LINE_ID,
                    target_player_character_id=PLAYER_CHARACTER_ID,
                    expected_state_version=RunStateVersion(value=1),
                    source_reference=SOURCE,
                ),
                applicable_character_reference=CHARACTER_REFERENCE,
                operation_id=RunOperationId(value="operation.bind"),
                occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
            )
        ).model_dump(mode="python")
    )


@pytest.mark.parametrize(
    "lifecycle_status",
    (
        RunLifecycleStatus.ACTIVE,
        RunLifecycleStatus.COMPLETED,
        RunLifecycleStatus.TERMINATED,
    ),
)
def test_creation_safe_result_rejects_every_non_creation_lifecycle(
    lifecycle_status: RunLifecycleStatus,
) -> None:
    with pytest.raises(ValidationError, match="initial unjoined state"):
        RunSafeResult(
            result_schema_version=CREATE_RUN_RESULT_SCHEMA_VERSION,
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            lifecycle_status=lifecycle_status,
            resulting_state_version=RunStateVersion(value=1),
        )


@pytest.mark.parametrize(
    "lifecycle_status",
    (
        RunLifecycleStatus.COMPLETED,
        RunLifecycleStatus.TERMINATED,
    ),
)
def test_attachment_safe_result_rejects_non_active_line_lifecycle(
    lifecycle_status: RunLifecycleStatus,
) -> None:
    attached = attach_session_result(record(attached=True))
    with pytest.raises(ValidationError, match="participation result"):
        RunSafeResult(
            result_schema_version=ATTACH_SESSION_RESULT_SCHEMA_VERSION,
            run_id=attached.run_id,
            continuous_story_line_id=attached.continuous_story_line_id,
            lifecycle_status=lifecycle_status,
            resulting_state_version=attached.resulting_state_version,
            participation_reference=attached.participation_reference,
        )


def test_safe_results_accept_exact_valid_lifecycles_and_replay_revalidates() -> None:
    created = creation_result(record())
    attached = attach_session_result(record(attached=True))
    active_attachment = RunSafeResult(
        result_schema_version=ATTACH_SESSION_RESULT_SCHEMA_VERSION,
        run_id=attached.run_id,
        continuous_story_line_id=attached.continuous_story_line_id,
        lifecycle_status=RunLifecycleStatus.ACTIVE,
        resulting_state_version=attached.resulting_state_version,
        participation_reference=attached.participation_reference,
    )
    assert created.lifecycle_status is RunLifecycleStatus.PRE_FIRST_TURN
    assert attached.lifecycle_status is RunLifecycleStatus.PRE_FIRST_TURN
    assert active_attachment.lifecycle_status is RunLifecycleStatus.ACTIVE

    key = RunReceiptKey(
        operation_namespace=RunOperationNamespace.CREATE_V1,
        operation_id=RunOperationId(value="operation.create"),
    )
    _, fingerprint = create_run_fingerprint(
        CreateRunCommand(source_reference=SOURCE)
    )
    receipt = StoredRunSuccessReceipt(
        key=key,
        fingerprint=fingerprint,
        command_kind=RunMutationKind.CREATE,
        result=created,
    )
    corrupted_receipt = receipt.model_copy(
        update={
            "result": created.model_copy(
                update={"lifecycle_status": RunLifecycleStatus.ACTIVE}
            )
        }
    )
    with pytest.raises(ValidationError, match="initial unjoined state"):
        evaluate_receipt(
            corrupted_receipt,
            key=key,
            fingerprint=fingerprint,
            command_kind=RunMutationKind.CREATE,
        )


def test_reserved_player_character_binding_namespace_is_rejected() -> None:
    decision = reject_reserved_bind_player_character(
        ReservedBindPlayerCharacterCommand(run_id=RUN_ID, continuous_story_line_id=LINE_ID, expected_state_version=RunStateVersion(value=1), source_reference=SOURCE),
        operation_id=RunOperationId(value="operation.bind"),
    )
    assert decision.code is RunReplayDecisionCode.RESERVED_OPERATION_REJECTED


def test_internal_binding_command_rejects_untrusted_or_injected_fields() -> None:
    payload = {
        "run_id": RUN_ID,
        "continuous_story_line_id": LINE_ID,
        "target_player_character_id": PLAYER_CHARACTER_ID,
        "expected_state_version": RunStateVersion(value=1),
        "source_reference": SOURCE,
    }
    for injected_field in (
        "controller_binding",
        "request_principal",
        "session_id",
        "applicable_character_reference",
        "operation_id",
    ):
        with pytest.raises(ValidationError, match="Extra inputs"):
            BindPlayerCharacterCommand.model_validate(
                {**payload, injected_field: "injected"},
            )


def test_p4_s1a_keeps_binding_persistence_service_and_public_api_inactive() -> None:
    source_root = Path(__file__).parents[2] / "src" / "deviation_protocol"
    repository_source = (
        source_root / "infrastructure" / "repositories.py"
    ).read_text(encoding="utf-8")
    run_service_source = (
        source_root / "application" / "run_service.py"
    ).read_text(encoding="utf-8")
    api_source = (source_root / "api" / "main.py").read_text(
        encoding="utf-8"
    )

    assert (
        "minimum Run persistence rejects populated binding state"
        in repository_source
    )
    assert (
        "command: ReservedBindPlayerCharacterCommand"
        in run_service_source
    )
    assert "bind_player_character_to_run" not in run_service_source
    assert "binding_integrity_guard_enabled=True" not in api_source
    assert "run.bind-player-character/v1" not in api_source


def test_operation_models_reject_malformed_session_and_receipt_bindings() -> None:
    with pytest.raises(ValidationError, match="opaque non-whitespace"):
        AttachSessionCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            session_id="session with space",
            expected_state_version=RunStateVersion(value=1),
            source_reference=SOURCE,
        )
    key = RunReceiptKey(
        operation_namespace=RunOperationNamespace.CREATE_V1,
        operation_id=RunOperationId(value="operation.create"),
    )
    _, fingerprint = create_run_fingerprint(CreateRunCommand(source_reference=SOURCE))
    with pytest.raises(ValidationError, match="command bindings"):
        StoredRunSuccessReceipt(
            key=key,
            fingerprint=fingerprint,
            command_kind=RunMutationKind.ATTACH_SESSION,
            result=creation_result(record()),
        )
