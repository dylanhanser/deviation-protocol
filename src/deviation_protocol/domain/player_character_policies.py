from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ContinuityMetadata,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
    canonical_player_declaration_bytes,
    revalidate_player_character_model,
    validate_applicable_character_reference,
    validate_canonical_player_character,
)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class PlayerCharacterPolicyCode(StrEnum):
    ACCEPTED = "ACCEPTED"
    TARGET_MISMATCH = "TARGET_MISMATCH"
    STALE_REVISION = "STALE_REVISION"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_MISMATCH = "CONFIRMATION_MISMATCH"
    TRUSTED_DEATH_EVIDENCE_REQUIRED = "TRUSTED_DEATH_EVIDENCE_REQUIRED"
    TRUSTED_DEATH_EVIDENCE_MISMATCH = "TRUSTED_DEATH_EVIDENCE_MISMATCH"
    REACTIVATION_AUTHORITY_UNAVAILABLE = "REACTIVATION_AUTHORITY_UNAVAILABLE"
    CONTINUITY_RETURN_POLICY_UNAVAILABLE = "CONTINUITY_RETURN_POLICY_UNAVAILABLE"
    APPLICABLE_REFERENCE_MISMATCH = "APPLICABLE_REFERENCE_MISMATCH"
    REVISION_EXHAUSTED = "REVISION_EXHAUSTED"


class ContinuityEffect(StrEnum):
    NONE = "NONE"
    END_CURRENT_LINE_IF_PRESENT = "END_CURRENT_LINE_IF_PRESENT"


class PlayerConfirmation(_StrictFrozenModel):
    player_character_id: PlayerCharacterId
    expected_revision: PlayerCharacterRevision
    operation_id: PlayerCharacterOperationId
    mutation_kind: PlayerCharacterMutationKind
    source_reference: AuthoritySourceRef


class TrustedFinalDeathEvidence(_StrictFrozenModel):
    player_character_id: PlayerCharacterId
    expected_revision: PlayerCharacterRevision
    operation_id: PlayerCharacterOperationId
    source_reference: AuthoritySourceRef


@dataclass(frozen=True, slots=True)
class PlayerCharacterPolicyDecision:
    code: PlayerCharacterPolicyCode
    resulting_record: CanonicalPlayerCharacter | None = None
    applicable_reference: ApplicableCharacterReference | None = None
    continuity_effect: ContinuityEffect = ContinuityEffect.NONE

    @property
    def accepted(self) -> bool:
        return self.code is PlayerCharacterPolicyCode.ACCEPTED


def _rejected(code: PlayerCharacterPolicyCode) -> PlayerCharacterPolicyDecision:
    return PlayerCharacterPolicyDecision(code=code)


def _revalidate_common_inputs(
    record: CanonicalPlayerCharacter,
    *,
    target: PlayerCharacterId,
    expected_revision: PlayerCharacterRevision,
    applicable_reference: ApplicableCharacterReference,
) -> tuple[
    CanonicalPlayerCharacter,
    PlayerCharacterId,
    PlayerCharacterRevision,
    ApplicableCharacterReference,
]:
    return (
        validate_canonical_player_character(record),
        revalidate_player_character_model(target, PlayerCharacterId),
        revalidate_player_character_model(
            expected_revision,
            PlayerCharacterRevision,
        ),
        validate_applicable_character_reference(applicable_reference),
    )


def _validate_common(
    record: CanonicalPlayerCharacter,
    *,
    target: PlayerCharacterId,
    expected_revision: PlayerCharacterRevision,
    applicable_reference: ApplicableCharacterReference,
) -> PlayerCharacterPolicyCode | None:
    if record.player_character_id != target:
        return PlayerCharacterPolicyCode.TARGET_MISMATCH
    if record.record_revision != expected_revision:
        return PlayerCharacterPolicyCode.STALE_REVISION
    if (
        applicable_reference.player_character_id != record.player_character_id
        or applicable_reference.contract_version != record.contract_version
        or applicable_reference.record_revision != record.record_revision
    ):
        return PlayerCharacterPolicyCode.APPLICABLE_REFERENCE_MISMATCH
    if not record.record_revision.has_successor:
        return PlayerCharacterPolicyCode.REVISION_EXHAUSTED
    return None


def _validate_confirmation(
    confirmation: PlayerConfirmation | None,
    *,
    record: CanonicalPlayerCharacter,
    operation_id: PlayerCharacterOperationId,
    mutation_kind: PlayerCharacterMutationKind,
) -> PlayerCharacterPolicyCode | None:
    if confirmation is None:
        return PlayerCharacterPolicyCode.CONFIRMATION_REQUIRED
    confirmation = revalidate_player_character_model(
        confirmation,
        PlayerConfirmation,
    )
    if (
        confirmation.player_character_id != record.player_character_id
        or confirmation.expected_revision != record.record_revision
        or confirmation.operation_id != operation_id
        or confirmation.mutation_kind is not mutation_kind
    ):
        return PlayerCharacterPolicyCode.CONFIRMATION_MISMATCH
    return None


def _mutated_record(
    record: CanonicalPlayerCharacter,
    *,
    lifecycle: PlayerCharacterLifecycle,
    mutation_kind: PlayerCharacterMutationKind,
    authority_class: PlayerCharacterAuthorityClass,
    source_reference: AuthoritySourceRef,
) -> CanonicalPlayerCharacter:
    next_revision = record.record_revision.successor()
    provenance = AuthorityProvenance(
        target_player_character_id=record.player_character_id,
        prior_revision=record.record_revision,
        resulting_revision=next_revision,
        mutation_kind=mutation_kind,
        authority_class=authority_class,
        source_reference=source_reference,
    )
    return record.detached_validated_copy(
        record_revision=next_revision,
        lifecycle=lifecycle,
        controller_binding=record.controller_binding,
        character_core=record.character_core,
        narration_preferences=record.narration_preferences,
        character_development=record.character_development,
        continuity_metadata=ContinuityMetadata(),
        authority_provenance=provenance,
    )


class CreatePlayerCharacterPolicy:
    def create(
        self,
        *,
        player_character_id: PlayerCharacterId,
        controller_binding: ControllerBindingRef,
        character_core: CharacterCore,
        narration_preferences: NarrationPreferences,
        source_reference: AuthoritySourceRef,
    ) -> CanonicalPlayerCharacter:
        player_character_id = revalidate_player_character_model(
            player_character_id,
            PlayerCharacterId,
        )
        controller_binding = revalidate_player_character_model(
            controller_binding,
            ControllerBindingRef,
        )
        character_core = revalidate_player_character_model(
            character_core,
            CharacterCore,
        )
        narration_preferences = revalidate_player_character_model(
            narration_preferences,
            NarrationPreferences,
        )
        canonical_player_declaration_bytes(
            character_core=character_core,
            narration_preferences=narration_preferences,
        )
        source_reference = revalidate_player_character_model(
            source_reference,
            AuthoritySourceRef,
        )
        revision = PlayerCharacterRevision(value=1)
        return CanonicalPlayerCharacter(
            contract_version=PlayerCharacterContractVersion.V1,
            player_character_id=player_character_id,
            record_revision=revision,
            controller_binding=controller_binding,
            lifecycle=PlayerCharacterLifecycle.ACTIVE,
            character_core=character_core,
            narration_preferences=narration_preferences,
            character_development=(),
            continuity_metadata=ContinuityMetadata(),
            authority_provenance=AuthorityProvenance(
                target_player_character_id=player_character_id,
                prior_revision=None,
                resulting_revision=revision,
                mutation_kind=PlayerCharacterMutationKind.CREATE,
                authority_class=PlayerCharacterAuthorityClass.TRUSTED_CREATION,
                source_reference=source_reference,
            ),
        )


class RetirePlayerCharacterPolicy:
    def evaluate(
        self,
        record: CanonicalPlayerCharacter,
        *,
        target: PlayerCharacterId,
        expected_revision: PlayerCharacterRevision,
        operation_id: PlayerCharacterOperationId,
        confirmation: PlayerConfirmation | None,
        applicable_reference: ApplicableCharacterReference,
    ) -> PlayerCharacterPolicyDecision:
        record, target, expected_revision, applicable_reference = (
            _revalidate_common_inputs(
                record,
                target=target,
                expected_revision=expected_revision,
                applicable_reference=applicable_reference,
            )
        )
        operation_id = revalidate_player_character_model(
            operation_id,
            PlayerCharacterOperationId,
        )
        failure = _validate_common(
            record,
            target=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
        )
        if failure is not None:
            return _rejected(failure)
        if record.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
            return _rejected(PlayerCharacterPolicyCode.INVALID_TRANSITION)
        failure = _validate_confirmation(
            confirmation,
            record=record,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
        )
        if failure is not None:
            return _rejected(failure)
        assert confirmation is not None
        candidate = _mutated_record(
            record,
            lifecycle=PlayerCharacterLifecycle.RETIRED,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            authority_class=PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER,
            source_reference=confirmation.source_reference,
        )
        return PlayerCharacterPolicyDecision(
            code=PlayerCharacterPolicyCode.ACCEPTED,
            resulting_record=candidate,
            applicable_reference=applicable_reference,
            continuity_effect=ContinuityEffect.END_CURRENT_LINE_IF_PRESENT,
        )


class ReactivatePlayerCharacterPolicy:
    """Phase 1 fails closed because no approved Run/active-line evidence issuer exists."""

    def evaluate(
        self,
        record: CanonicalPlayerCharacter,
        *,
        target: PlayerCharacterId,
        expected_revision: PlayerCharacterRevision,
        operation_id: PlayerCharacterOperationId,
        confirmation: PlayerConfirmation | None,
        applicable_reference: ApplicableCharacterReference,
    ) -> PlayerCharacterPolicyDecision:
        record, target, expected_revision, applicable_reference = (
            _revalidate_common_inputs(
                record,
                target=target,
                expected_revision=expected_revision,
                applicable_reference=applicable_reference,
            )
        )
        operation_id = revalidate_player_character_model(
            operation_id,
            PlayerCharacterOperationId,
        )
        failure = _validate_common(
            record,
            target=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
        )
        if failure is not None:
            return _rejected(failure)
        if record.lifecycle is not PlayerCharacterLifecycle.RETIRED:
            return _rejected(PlayerCharacterPolicyCode.INVALID_TRANSITION)
        failure = _validate_confirmation(
            confirmation,
            record=record,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.REACTIVATE,
        )
        if failure is not None:
            return _rejected(failure)
        return _rejected(
            PlayerCharacterPolicyCode.REACTIVATION_AUTHORITY_UNAVAILABLE
        )


class FinalDeathPlayerCharacterPolicy:
    def evaluate(
        self,
        record: CanonicalPlayerCharacter,
        *,
        target: PlayerCharacterId,
        expected_revision: PlayerCharacterRevision,
        operation_id: PlayerCharacterOperationId,
        evidence: TrustedFinalDeathEvidence | None,
        applicable_reference: ApplicableCharacterReference,
    ) -> PlayerCharacterPolicyDecision:
        record, target, expected_revision, applicable_reference = (
            _revalidate_common_inputs(
                record,
                target=target,
                expected_revision=expected_revision,
                applicable_reference=applicable_reference,
            )
        )
        operation_id = revalidate_player_character_model(
            operation_id,
            PlayerCharacterOperationId,
        )
        failure = _validate_common(
            record,
            target=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
        )
        if failure is not None:
            return _rejected(failure)
        if record.lifecycle not in {
            PlayerCharacterLifecycle.ACTIVE,
            PlayerCharacterLifecycle.RETIRED,
        }:
            return _rejected(PlayerCharacterPolicyCode.INVALID_TRANSITION)
        if evidence is None:
            return _rejected(
                PlayerCharacterPolicyCode.TRUSTED_DEATH_EVIDENCE_REQUIRED
            )
        evidence = revalidate_player_character_model(
            evidence,
            TrustedFinalDeathEvidence,
        )
        if (
            evidence.player_character_id != record.player_character_id
            or evidence.expected_revision != record.record_revision
            or evidence.operation_id != operation_id
        ):
            return _rejected(
                PlayerCharacterPolicyCode.TRUSTED_DEATH_EVIDENCE_MISMATCH
            )
        candidate = _mutated_record(
            record,
            lifecycle=PlayerCharacterLifecycle.DECEASED,
            mutation_kind=PlayerCharacterMutationKind.FINAL_DEATH,
            authority_class=PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME,
            source_reference=evidence.source_reference,
        )
        return PlayerCharacterPolicyDecision(
            code=PlayerCharacterPolicyCode.ACCEPTED,
            resulting_record=candidate,
            applicable_reference=applicable_reference,
            continuity_effect=(
                ContinuityEffect.END_CURRENT_LINE_IF_PRESENT
                if record.lifecycle is PlayerCharacterLifecycle.ACTIVE
                else ContinuityEffect.NONE
            ),
        )


class AuthorizedContinuityReturnPolicy:
    """No adjudication authority exists in the first slice."""

    def evaluate(
        self,
        record: CanonicalPlayerCharacter,
        *,
        target: PlayerCharacterId,
        expected_revision: PlayerCharacterRevision,
        applicable_reference: ApplicableCharacterReference,
    ) -> PlayerCharacterPolicyDecision:
        record, target, expected_revision, applicable_reference = (
            _revalidate_common_inputs(
                record,
                target=target,
                expected_revision=expected_revision,
                applicable_reference=applicable_reference,
            )
        )
        failure = _validate_common(
            record,
            target=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
        )
        if failure is not None:
            return _rejected(failure)
        if record.lifecycle is not PlayerCharacterLifecycle.DECEASED:
            return _rejected(PlayerCharacterPolicyCode.INVALID_TRANSITION)
        return _rejected(
            PlayerCharacterPolicyCode.CONTINUITY_RETURN_POLICY_UNAVAILABLE
        )
