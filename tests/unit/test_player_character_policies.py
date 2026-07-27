from __future__ import annotations

from pydantic import ValidationError
import pytest

from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    Declaration,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
    PlayerDeclaredText,
    PlayerSubjectiveAuthority,
)
from deviation_protocol.domain.player_character_policies import (
    AuthorizedContinuityReturnPolicy,
    ContinuityEffect,
    CreatePlayerCharacterPolicy,
    FinalDeathPlayerCharacterPolicy,
    PlayerCharacterPolicyCode,
    PlayerConfirmation,
    ReactivatePlayerCharacterPolicy,
    RetirePlayerCharacterPolicy,
    TrustedFinalDeathEvidence,
)


def created_record():
    return CreatePlayerCharacterPolicy().create(
        player_character_id=PlayerCharacterId(value="pc.policy-1"),
        controller_binding=ControllerBindingRef(value="binding.policy-1"),
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(value="source.policy-create"),
    )


def operation_id(value: str = "operation.policy-1") -> PlayerCharacterOperationId:
    return PlayerCharacterOperationId(value=value)


def confirmation(record, kind, *, op_id=None):
    return PlayerConfirmation(
        player_character_id=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id or operation_id(),
        mutation_kind=kind,
        source_reference=AuthoritySourceRef(value="source.player-confirmation"),
    )


def applicable_reference(record):
    return ApplicableCharacterReference(
        player_character_id=record.player_character_id,
        contract_version=record.contract_version,
        record_revision=record.record_revision,
    )


def retire(record=None):
    record = record or created_record()
    return RetirePlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=operation_id(),
        confirmation=confirmation(record, PlayerCharacterMutationKind.RETIRE),
        applicable_reference=applicable_reference(record),
    )


def test_creation_builds_complete_active_revision_one_record() -> None:
    record = created_record()
    assert record.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert record.record_revision == PlayerCharacterRevision(value=1)
    assert record.controller_binding == ControllerBindingRef(
        value="binding.policy-1"
    )
    assert record.character_development == ()


def test_retirement_is_detached_advances_once_and_preserves_identity_binding_and_reference() -> None:
    record = created_record()
    reference = applicable_reference(record)
    decision = retire(record)
    assert decision.accepted
    assert decision.resulting_record is not None
    assert decision.resulting_record is not record
    assert decision.resulting_record.lifecycle is PlayerCharacterLifecycle.RETIRED
    assert decision.resulting_record.record_revision.value == 2
    assert (
        decision.resulting_record.player_character_id
        == record.player_character_id
    )
    assert decision.resulting_record.controller_binding == record.controller_binding
    assert decision.applicable_reference == reference
    assert (
        decision.continuity_effect
        is ContinuityEffect.END_CURRENT_LINE_IF_PRESENT
    )
    assert record.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert record.record_revision.value == 1


@pytest.mark.parametrize(
    "confirmation_value,expected_code",
    (
        (None, PlayerCharacterPolicyCode.CONFIRMATION_REQUIRED),
        ("mismatch", PlayerCharacterPolicyCode.CONFIRMATION_MISMATCH),
    ),
)
def test_retirement_requires_exact_bound_confirmation(
    confirmation_value,
    expected_code,
) -> None:
    record = created_record()
    bound = (
        None
        if confirmation_value is None
        else confirmation(
            record,
            PlayerCharacterMutationKind.RETIRE,
            op_id=operation_id("operation.other"),
        )
    )
    decision = RetirePlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=operation_id(),
        confirmation=bound,
        applicable_reference=applicable_reference(record),
    )
    assert decision.code is expected_code
    assert decision.resulting_record is None
    assert record.record_revision.value == 1


def test_stale_or_wrong_target_retirement_never_advances_state() -> None:
    record = created_record()
    for target, revision, expected in (
        (
            PlayerCharacterId(value="pc.other"),
            record.record_revision,
            PlayerCharacterPolicyCode.TARGET_MISMATCH,
        ),
        (
            record.player_character_id,
            PlayerCharacterRevision(value=2),
            PlayerCharacterPolicyCode.STALE_REVISION,
        ),
    ):
        decision = RetirePlayerCharacterPolicy().evaluate(
            record,
            target=target,
            expected_revision=revision,
            operation_id=operation_id(),
            confirmation=confirmation(
                record, PlayerCharacterMutationKind.RETIRE
            ),
            applicable_reference=applicable_reference(record),
        )
        assert decision.code is expected
        assert decision.resulting_record is None
    assert record.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert record.record_revision.value == 1


def test_reactivation_fails_closed_without_run_owned_active_line_evidence() -> None:
    retired = retire().resulting_record
    assert retired is not None
    decision = ReactivatePlayerCharacterPolicy().evaluate(
        retired,
        target=retired.player_character_id,
        expected_revision=retired.record_revision,
        operation_id=operation_id("operation.reactivate"),
        confirmation=confirmation(
            retired,
            PlayerCharacterMutationKind.REACTIVATE,
            op_id=operation_id("operation.reactivate"),
        ),
        applicable_reference=applicable_reference(retired),
    )
    assert (
        decision.code
        is PlayerCharacterPolicyCode.REACTIVATION_AUTHORITY_UNAVAILABLE
    )
    assert decision.resulting_record is None
    assert retired.lifecycle is PlayerCharacterLifecycle.RETIRED


@pytest.mark.parametrize(
    "starting_state",
    (PlayerCharacterLifecycle.ACTIVE, PlayerCharacterLifecycle.RETIRED),
)
def test_final_death_requires_trusted_bound_evidence_and_preserves_binding(
    starting_state: PlayerCharacterLifecycle,
) -> None:
    record = created_record()
    if starting_state is PlayerCharacterLifecycle.RETIRED:
        record = retire(record).resulting_record
        assert record is not None
    op_id = operation_id("operation.final-death")
    missing = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=None,
        applicable_reference=applicable_reference(record),
    )
    assert missing.code is PlayerCharacterPolicyCode.TRUSTED_DEATH_EVIDENCE_REQUIRED
    evidence = TrustedFinalDeathEvidence(
        player_character_id=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        source_reference=AuthoritySourceRef(value="event.final-death"),
    )
    accepted = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=evidence,
        applicable_reference=applicable_reference(record),
    )
    assert accepted.accepted
    assert accepted.resulting_record is not None
    assert accepted.resulting_record.lifecycle is PlayerCharacterLifecycle.DECEASED
    assert accepted.resulting_record.controller_binding == record.controller_binding
    assert accepted.resulting_record.record_revision.value == (
        record.record_revision.value + 1
    )


def test_deceased_character_cannot_use_ordinary_reactivation_or_final_death() -> None:
    record = created_record()
    op_id = operation_id("operation.final-death")
    deceased = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=TrustedFinalDeathEvidence(
            player_character_id=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            source_reference=AuthoritySourceRef(value="event.final-death"),
        ),
        applicable_reference=applicable_reference(record),
    ).resulting_record
    assert deceased is not None
    reactivation = ReactivatePlayerCharacterPolicy().evaluate(
        deceased,
        target=deceased.player_character_id,
        expected_revision=deceased.record_revision,
        operation_id=operation_id("operation.reactivate"),
        confirmation=confirmation(
            deceased,
            PlayerCharacterMutationKind.REACTIVATE,
            op_id=operation_id("operation.reactivate"),
        ),
        applicable_reference=applicable_reference(deceased),
    )
    assert reactivation.code is PlayerCharacterPolicyCode.INVALID_TRANSITION


def test_authorized_continuity_return_is_deterministically_unavailable() -> None:
    record = created_record()
    op_id = operation_id("operation.final-death")
    deceased = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=TrustedFinalDeathEvidence(
            player_character_id=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            source_reference=AuthoritySourceRef(value="event.final-death"),
        ),
        applicable_reference=applicable_reference(record),
    ).resulting_record
    assert deceased is not None
    decision = AuthorizedContinuityReturnPolicy().evaluate(
        deceased,
        target=deceased.player_character_id,
        expected_revision=deceased.record_revision,
        applicable_reference=applicable_reference(deceased),
    )
    assert (
        decision.code
        is PlayerCharacterPolicyCode.CONTINUITY_RETURN_POLICY_UNAVAILABLE
    )
    assert decision.resulting_record is None


def test_applicable_reference_mismatch_rejects_without_switching_or_following() -> None:
    record = created_record()
    mismatched = ApplicableCharacterReference(
        player_character_id=PlayerCharacterId(value="pc.other"),
        contract_version=record.contract_version,
        record_revision=record.record_revision,
    )
    decision = RetirePlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=operation_id(),
        confirmation=confirmation(record, PlayerCharacterMutationKind.RETIRE),
        applicable_reference=mismatched,
    )
    assert decision.code is PlayerCharacterPolicyCode.APPLICABLE_REFERENCE_MISMATCH
    assert decision.resulting_record is None
    assert record.record_revision.value == 1


@pytest.mark.parametrize(
    "starting_state,policy_name",
    (
        (PlayerCharacterLifecycle.RETIRED, "retire"),
        (PlayerCharacterLifecycle.DECEASED, "retire"),
        (PlayerCharacterLifecycle.ACTIVE, "reactivate"),
        (PlayerCharacterLifecycle.DECEASED, "reactivate"),
        (PlayerCharacterLifecycle.DECEASED, "final_death"),
        (PlayerCharacterLifecycle.ACTIVE, "continuity_return"),
        (PlayerCharacterLifecycle.RETIRED, "continuity_return"),
    ),
)
def test_every_unlisted_or_same_state_lifecycle_edge_rejects_without_mutation(
    starting_state: PlayerCharacterLifecycle,
    policy_name: str,
) -> None:
    record = created_record()
    if starting_state is PlayerCharacterLifecycle.RETIRED:
        record = retire(record).resulting_record
        assert record is not None
    elif starting_state is PlayerCharacterLifecycle.DECEASED:
        op_id = operation_id("operation.prepare-death")
        record = FinalDeathPlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            evidence=TrustedFinalDeathEvidence(
                player_character_id=record.player_character_id,
                expected_revision=record.record_revision,
                operation_id=op_id,
                source_reference=AuthoritySourceRef(value="event.prepare-death"),
            ),
                applicable_reference=applicable_reference(record),
        ).resulting_record
        assert record is not None
    before = record
    op_id = operation_id("operation.forbidden-edge")
    if policy_name == "retire":
        decision = RetirePlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.RETIRE,
                op_id=op_id,
            ),
            applicable_reference=applicable_reference(record),
        )
    elif policy_name == "reactivate":
        decision = ReactivatePlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.REACTIVATE,
                op_id=op_id,
            ),
            applicable_reference=applicable_reference(record),
        )
    elif policy_name == "final_death":
        decision = FinalDeathPlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            evidence=TrustedFinalDeathEvidence(
                player_character_id=record.player_character_id,
                expected_revision=record.record_revision,
                operation_id=op_id,
                source_reference=AuthoritySourceRef(value="event.forbidden-edge"),
            ),
            applicable_reference=applicable_reference(record),
        )
    else:
        decision = AuthorizedContinuityReturnPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            applicable_reference=applicable_reference(record),
        )
    assert decision.code is PlayerCharacterPolicyCode.INVALID_TRANSITION
    assert decision.resulting_record is None
    assert record == before


def test_creation_policy_revalidates_corrupted_nested_declaration_values() -> None:
    declaration = Declaration[PlayerDeclaredText].declared(
        PlayerDeclaredText(
            authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
            text="valid before bypass",
        )
    )
    corrupted_text = declaration.value.model_copy(update={"text": None})
    corrupted_core = CharacterCore().model_copy(
        update={
            "name_or_code_name": declaration.model_copy(
                update={"value": corrupted_text}
            )
        }
    )

    with pytest.raises(ValidationError, match="text"):
        CreatePlayerCharacterPolicy().create(
            player_character_id=PlayerCharacterId(value="pc.corrupted-create"),
            controller_binding=ControllerBindingRef(
                value="binding.corrupted-create"
            ),
            character_core=corrupted_core,
            narration_preferences=NarrationPreferences(),
            source_reference=AuthoritySourceRef(value="source.corrupted-create"),
        )


def test_creation_policy_rejects_unknown_nested_declaration_state() -> None:
    valid_text = PlayerDeclaredText(
        authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
        text="valid before unknown-state bypass",
    )
    corrupted_text = valid_text.model_copy(
        update={"unknown_nested_state": "caller-injected"}
    )
    corrupted_core = CharacterCore().model_copy(
        update={
            "name_or_code_name": Declaration[PlayerDeclaredText].declared(
                valid_text
            ).model_copy(update={"value": corrupted_text})
        }
    )

    with pytest.raises(ValueError, match="unknown instance state"):
        CreatePlayerCharacterPolicy().create(
            player_character_id=PlayerCharacterId(
                value="pc.unknown-corrupted-create"
            ),
            controller_binding=ControllerBindingRef(
                value="binding.unknown-corrupted-create"
            ),
            character_core=corrupted_core,
            narration_preferences=NarrationPreferences(),
            source_reference=AuthoritySourceRef(
                value="source.unknown-corrupted-create"
            ),
        )


@pytest.mark.parametrize("corrupted_field", ("identity", "controller"))
def test_creation_policy_revalidates_corrupted_identity_and_controller_values(
    corrupted_field: str,
) -> None:
    player_character_id = PlayerCharacterId(value="pc.create-boundary")
    controller_binding = ControllerBindingRef(value="binding.create-boundary")
    if corrupted_field == "identity":
        player_character_id = player_character_id.model_copy(
            update={"value": None}
        )
    else:
        controller_binding = controller_binding.model_construct(value=None)

    with pytest.raises(ValidationError):
        CreatePlayerCharacterPolicy().create(
            player_character_id=player_character_id,
            controller_binding=controller_binding,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
            source_reference=AuthoritySourceRef(value="source.create-boundary"),
        )


def test_direct_lifecycle_policy_revalidates_corrupted_complete_record() -> None:
    record = created_record()
    corrupted = record.model_copy(
        update={
            "controller_binding": record.controller_binding.model_copy(
                update={"value": None}
            )
        }
    )

    with pytest.raises(ValidationError, match="controller_binding"):
        RetirePlayerCharacterPolicy().evaluate(
            corrupted,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id(),
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.RETIRE,
            ),
            applicable_reference=applicable_reference(record),
        )


def test_direct_lifecycle_policy_rejects_unknown_record_and_nested_reference_state() -> None:
    record = created_record()
    unknown_record = record.model_copy(
        update={"unknown_record_state": "caller-injected"}
    )
    with pytest.raises(ValueError, match="unknown instance state"):
        RetirePlayerCharacterPolicy().evaluate(
            unknown_record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id(),
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.RETIRE,
            ),
            applicable_reference=applicable_reference(record),
        )

    reference = applicable_reference(record)
    unknown_nested_reference = reference.model_copy(
        update={
            "record_revision": reference.record_revision.model_copy(
                update={"unknown_reference_state": "caller-injected"}
            )
        }
    )
    with pytest.raises(ValueError, match="unknown instance state"):
        RetirePlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id(),
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.RETIRE,
            ),
            applicable_reference=unknown_nested_reference,
        )


def test_direct_lifecycle_policy_revalidates_corrupted_applicable_reference() -> None:
    record = created_record()
    reference = applicable_reference(record)
    corrupted = reference.model_copy(
        update={
            "record_revision": reference.record_revision.model_construct(
                value=None
            )
        }
    )

    with pytest.raises(ValidationError, match="record_revision"):
        RetirePlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id(),
            confirmation=confirmation(
                record,
                PlayerCharacterMutationKind.RETIRE,
            ),
            applicable_reference=corrupted,
        )


def test_direct_lifecycle_policy_revalidates_corrupted_confirmation() -> None:
    record = created_record()
    bound = confirmation(record, PlayerCharacterMutationKind.RETIRE)
    corrupted = bound.model_copy(
        update={
            "source_reference": bound.source_reference.model_construct(
                value=None
            )
        }
    )

    with pytest.raises(ValidationError, match="source_reference"):
        RetirePlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id(),
            confirmation=corrupted,
            applicable_reference=applicable_reference(record),
        )


def test_direct_lifecycle_policy_revalidates_corrupted_death_evidence() -> None:
    record = created_record()
    op_id = operation_id("operation.corrupted-evidence")
    evidence = TrustedFinalDeathEvidence(
        player_character_id=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        source_reference=AuthoritySourceRef(value="event.corrupted-evidence"),
    )
    corrupted = evidence.model_copy(
        update={
            "player_character_id": evidence.player_character_id.model_copy(
                update={"value": None}
            )
        }
    )

    with pytest.raises(ValidationError, match="player_character_id"):
        FinalDeathPlayerCharacterPolicy().evaluate(
            record,
            target=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            evidence=corrupted,
            applicable_reference=applicable_reference(record),
        )


def retired_record_at_revision(revision_value: int):
    record = created_record()
    revision = PlayerCharacterRevision(value=revision_value)
    return record.detached_validated_copy(
        record_revision=revision,
        lifecycle=PlayerCharacterLifecycle.RETIRED,
        authority_provenance=AuthorityProvenance(
            target_player_character_id=record.player_character_id,
            prior_revision=PlayerCharacterRevision(value=revision_value - 1),
            resulting_revision=revision,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            authority_class=(
                PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
            ),
            source_reference=AuthoritySourceRef(value="source.high-revision"),
        ),
    )


def test_direct_policy_accepts_the_last_representable_revision_successor() -> None:
    record = retired_record_at_revision(9223372036854775806)
    op_id = operation_id("operation.last-representable-successor")
    decision = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=TrustedFinalDeathEvidence(
            player_character_id=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            source_reference=AuthoritySourceRef(
                value="event.last-representable-successor"
            ),
        ),
        applicable_reference=applicable_reference(record),
    )

    assert decision.code is PlayerCharacterPolicyCode.ACCEPTED
    assert decision.resulting_record is not None
    assert (
        decision.resulting_record.record_revision.value
        == 9223372036854775807
    )


def test_direct_policy_rejects_revision_overflow_before_success() -> None:
    record = retired_record_at_revision(9223372036854775807)
    op_id = operation_id("operation.revision-overflow")
    decision = FinalDeathPlayerCharacterPolicy().evaluate(
        record,
        target=record.player_character_id,
        expected_revision=record.record_revision,
        operation_id=op_id,
        evidence=TrustedFinalDeathEvidence(
            player_character_id=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=op_id,
            source_reference=AuthoritySourceRef(value="event.revision-overflow"),
        ),
        applicable_reference=applicable_reference(record),
    )

    assert decision.code is PlayerCharacterPolicyCode.REVISION_EXHAUSTED
    assert decision.resulting_record is None
    assert record.record_revision.value == 9223372036854775807
