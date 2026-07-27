from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json

from pydantic import ValidationError
import pytest

from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    CREATION_TRANSACTION_ORDER,
    FIRST_SLICE_RETENTION_BOUNDARY,
    LATER_PERSISTENCE_ATOMICITY_REQUIREMENTS,
    MUTATION_RESULT_SCHEMA_VERSION,
    MUTATION_TRANSACTION_ORDER,
    UNIQUE_RACE_RECOVERY_ORDER,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    canonical_character_operation_bytes,
    creation_fingerprint,
    evaluate_creation_receipt_protocol,
    evaluate_mutation_policy,
    evaluate_mutation_receipt_protocol,
    mutation_fingerprint,
    recover_creation_unique_race_winner,
    recover_mutation_unique_race_winner,
    validate_stored_creation_success_receipt,
    validate_stored_mutation_success_receipt,
)
from deviation_protocol.domain.player_character import (
    AdultAgePresentation,
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    canonical_player_declaration_bytes,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    CustomValueEntry,
    CustomValues,
    Declaration,
    DistinguishingFeatures,
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
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
    TrustedFinalDeathEvidence,
)


def player_text(text: str) -> PlayerDeclaredText:
    return PlayerDeclaredText(
        authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
        text=text,
    )


def creation_command(
    *,
    name_state: str = "declared",
    name: str = "Cafe\u0301",
) -> CharacterCreationCommand:
    if name_state == "declared":
        name_declaration = Declaration[PlayerDeclaredText].declared(
            player_text(name)
        )
    elif name_state == "absent":
        name_declaration = Declaration[PlayerDeclaredText].explicitly_absent()
    elif name_state == "undecided":
        name_declaration = Declaration[
            PlayerDeclaredText
        ].intentionally_undecided()
    else:
        name_declaration = Declaration[PlayerDeclaredText].omitted()
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=name_declaration,
            preferred_form_of_address=Declaration[
                PlayerDeclaredText
            ].explicitly_absent(),
            adult_identity_and_gender_expression=Declaration[
                PlayerDeclaredText
            ].intentionally_undecided(),
            broad_adult_age_presentation=Declaration[
                AdultAgePresentation
            ].declared(
                AdultAgePresentation(
                    adult_only=True,
                )
            ),
            broad_appearance_direction=Declaration[
                PlayerDeclaredText
            ].declared(player_text("weathered")),
            distinguishing_features=Declaration[
                DistinguishingFeatures
            ].declared(
                DistinguishingFeatures(
                    features=(
                        player_text("silver glasses"),
                        player_text("scar"),
                    )
                )
            ),
            outward_presentation=Declaration[PlayerDeclaredText].omitted(),
            inward_tendency=Declaration[PlayerDeclaredText].declared(
                player_text("cautious")
            ),
            reality_anchor=Declaration[PlayerDeclaredText].declared(
                player_text("a chosen promise")
            ),
            custom_values=Declaration[CustomValues].declared(
                CustomValues(
                    entries=(
                        CustomValueEntry(
                            key="loyalty",
                            declaration=Declaration[
                                PlayerDeclaredText
                            ].declared(player_text("deliberate")),
                        ),
                        CustomValueEntry(
                            key="future",
                            declaration=Declaration[
                                PlayerDeclaredText
                            ].intentionally_undecided(),
                        ),
                    )
                )
            ),
        ),
        narration_preferences=NarrationPreferences(
            internal_thoughts=Declaration[
                PlayerNarrationPreference
            ].intentionally_undecided()
        ),
    )


def boundary_creation_command(text: str) -> CharacterCreationCommand:
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=Declaration[PlayerDeclaredText].declared(
                player_text(text)
            )
        ),
        narration_preferences=NarrationPreferences(),
    )


def fixed_65_feature_creation_command() -> CharacterCreationCommand:
    features = tuple(
        player_text(f"fixed-feature-{index:02d}") for index in range(65)
    )
    assert len(features) == 65
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            distinguishing_features=Declaration[
                DistinguishingFeatures
            ].declared(DistinguishingFeatures(features=features))
        ),
        narration_preferences=NarrationPreferences(),
    )


def operation_id(value: str = "operation.golden-1") -> PlayerCharacterOperationId:
    return PlayerCharacterOperationId(value=value)


def character_id(value: str = "pc.golden-1") -> PlayerCharacterId:
    return PlayerCharacterId(value=value)


def mutation_command(
    kind: PlayerCharacterMutationKind,
    *,
    revision: int = 7,
    op_id: PlayerCharacterOperationId | None = None,
) -> CharacterMutationCommand:
    op_id = op_id or operation_id()
    target = character_id()
    expected_revision = PlayerCharacterRevision(value=revision)
    applicable_reference = ApplicableCharacterReference(
        player_character_id=target,
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=expected_revision,
    )
    if kind in {
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.REACTIVATE,
    }:
        return CharacterMutationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            command_kind=kind,
            target_player_character_id=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
            confirmation=PlayerConfirmation(
                player_character_id=target,
                expected_revision=expected_revision,
                operation_id=op_id,
                mutation_kind=kind,
                source_reference=AuthoritySourceRef(
                    value="confirmation.golden-1"
                ),
            ),
        )
    if kind is PlayerCharacterMutationKind.FINAL_DEATH:
        return CharacterMutationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            command_kind=kind,
            target_player_character_id=target,
            expected_revision=expected_revision,
            applicable_reference=applicable_reference,
            final_death_evidence=TrustedFinalDeathEvidence(
                player_character_id=target,
                expected_revision=expected_revision,
                operation_id=op_id,
                source_reference=AuthoritySourceRef(value="event.death-1"),
            ),
        )
    return CharacterMutationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=kind,
        target_player_character_id=target,
        expected_revision=expected_revision,
        applicable_reference=applicable_reference,
    )


GOLDEN_VECTORS = {
    "creation": {
        "canonical_json": (
            '{"command_kind":"CREATE","contract_version":"structured-player-character/v1",'
            '"declarations":{"character_core":{"adult_identity_and_gender_expression":'
            '{"state":"intentionally-undecided","value":null},'
            '"broad_adult_age_presentation":{"state":"declared","value":'
            '{"adult_only":true}},"broad_appearance_direction":{"state":"declared",'
            '"value":{"authority":"player-expression","text":"weathered"}},'
            '"custom_values":{"state":"declared","value":{"entries":['
            '{"declaration":{"state":"declared","value":{"authority":'
            '"player-expression","text":"deliberate"}},"key":"loyalty"},'
            '{"declaration":{"state":"intentionally-undecided","value":null},'
            '"key":"future"}]}},"distinguishing_features":{"state":"declared",'
            '"value":{"features":[{"authority":"player-expression","text":'
            '"silver glasses"},{"authority":"player-expression","text":"scar"}]}},'
            '"inward_tendency":{"state":"declared","value":{"authority":'
            '"player-expression","text":"cautious"}},"name_or_code_name":'
            '{"state":"declared","value":{"authority":"player-expression",'
            '"text":"Café"}},"outward_presentation":{"state":"omitted","value":null},'
            '"preferred_form_of_address":{"state":"explicitly-absent","value":null},'
            '"reality_anchor":{"state":"declared","value":{"authority":'
            '"player-expression","text":"a chosen promise"}}},'
            '"narration_preferences":{"internal_thoughts":{"state":'
            '"intentionally-undecided","value":null}}},'
            '"operation_namespace":"player-character.create/v1"}'
        ),
        "fingerprint": (
            "b3599c01cfa309b7b6e32f25212c94775f1da98b46ac232b25fa2368f6f3030e"
        ),
    },
    "retire": {
        "canonical_json": (
            '{"applicable_reference":{"contract_version":'
            '"structured-player-character/v1","player_character_id":'
            '{"value":"pc.golden-1"},"record_revision":{"value":7}},'
            '"command_kind":"RETIRE","contract_version":'
            '"structured-player-character/v1","expected_revision":7,'
            '"mutation_body":{"confirmation":{"expected_revision":7,'
            '"mutation_kind":"RETIRE","operation_id":{"value":"operation.golden-1"},'
            '"player_character_id":{"value":"pc.golden-1"},"source_reference":'
            '{"value":"confirmation.golden-1"}}},"operation_namespace":'
            '"player-character.mutate/v1","target_player_character_id":'
            '{"value":"pc.golden-1"}}'
        ),
        "fingerprint": (
            "8e577a14945c2dd5d3f30ed72e8ef928bd974c1567803b9b662ac8f05e41769f"
        ),
    },
    "reactivate": {
        "canonical_json": (
            '{"applicable_reference":{"contract_version":'
            '"structured-player-character/v1","player_character_id":'
            '{"value":"pc.golden-1"},"record_revision":{"value":7}},'
            '"command_kind":"REACTIVATE","contract_version":'
            '"structured-player-character/v1","expected_revision":7,'
            '"mutation_body":{"confirmation":{"expected_revision":7,'
            '"mutation_kind":"REACTIVATE","operation_id":'
            '{"value":"operation.golden-1"},"player_character_id":'
            '{"value":"pc.golden-1"},"source_reference":'
            '{"value":"confirmation.golden-1"}}},"operation_namespace":'
            '"player-character.mutate/v1","target_player_character_id":'
            '{"value":"pc.golden-1"}}'
        ),
        "fingerprint": (
            "9712c00cb54de15261ebeebb558302c157b66fb990838cedb8cbf5f3f6b997d7"
        ),
    },
    "final_death": {
        "canonical_json": (
            '{"applicable_reference":{"contract_version":'
            '"structured-player-character/v1","player_character_id":'
            '{"value":"pc.golden-1"},"record_revision":{"value":7}},'
            '"command_kind":"FINAL_DEATH","contract_version":'
            '"structured-player-character/v1","expected_revision":7,'
            '"mutation_body":{"trusted_final_death_evidence":'
            '{"expected_revision":7,"operation_id":{"value":"operation.golden-1"},'
            '"player_character_id":{"value":"pc.golden-1"},"source_reference":'
            '{"value":"event.death-1"}}},"operation_namespace":'
            '"player-character.mutate/v1","target_player_character_id":'
            '{"value":"pc.golden-1"}}'
        ),
        "fingerprint": (
            "779b7f8b4db4d25da7ecc98b7cab1bed7d507a0ae56e38645092c9f8dc1ba666"
        ),
    },
    "authorized_continuity_return_unavailable": {
        "canonical_json": (
            '{"applicable_reference":{"contract_version":'
            '"structured-player-character/v1","player_character_id":'
            '{"value":"pc.golden-1"},"record_revision":{"value":7}},'
            '"command_kind":"AUTHORIZED_CONTINUITY_RETURN","contract_version":'
            '"structured-player-character/v1","expected_revision":7,'
            '"mutation_body":{"policy_state":"unavailable-in-phase-1"},'
            '"operation_namespace":"player-character.mutate/v1",'
            '"target_player_character_id":{"value":"pc.golden-1"}}'
        ),
        "fingerprint": (
            "26ba3471670b2202f48bbc401b98dc66dbdbd17c89a4154a44c6c593a17be8b0"
        ),
    },
}

MUTATION_GOLDEN_VECTOR_LENGTHS = {
    "retire": 583,
    "reactivate": 591,
    "final_death": 571,
    "authorized_continuity_return_unavailable": 436,
}


def current_record(*, revision: int = 1):
    record = CreatePlayerCharacterPolicy().create(
        player_character_id=character_id(),
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(value="source.create"),
    )
    if revision == 1:
        return record
    resulting_revision = PlayerCharacterRevision(value=revision)
    return record.detached_validated_copy(
        record_revision=resulting_revision,
        lifecycle=PlayerCharacterLifecycle.RETIRED,
        authority_provenance=AuthorityProvenance(
            target_player_character_id=record.player_character_id,
            prior_revision=PlayerCharacterRevision(value=revision - 1),
            resulting_revision=resulting_revision,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            authority_class=PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER,
            source_reference=AuthoritySourceRef(value="source.prior-mutation"),
        ),
    )


def deceased_record(*, revision: int = 7) -> CanonicalPlayerCharacter:
    record = current_record()
    resulting_revision = PlayerCharacterRevision(value=revision)
    return record.detached_validated_copy(
        record_revision=resulting_revision,
        lifecycle=PlayerCharacterLifecycle.DECEASED,
        authority_provenance=AuthorityProvenance(
            target_player_character_id=record.player_character_id,
            prior_revision=PlayerCharacterRevision(value=revision - 1),
            resulting_revision=resulting_revision,
            mutation_kind=PlayerCharacterMutationKind.FINAL_DEATH,
            authority_class=PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME,
            source_reference=AuthoritySourceRef(value="source.prior-death"),
        ),
    )


def creation_result() -> CreationSuccessResult:
    return CreationSuccessResult(
        result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
        player_character_id=character_id(),
        contract_version=PlayerCharacterContractVersion.V1,
        resulting_revision=PlayerCharacterRevision(value=1),
        resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE,
    )


def mutation_result(
    kind: PlayerCharacterMutationKind = PlayerCharacterMutationKind.RETIRE,
    *,
    resulting_revision: int = 8,
) -> MutationSuccessResult:
    result, lifecycle = {
        PlayerCharacterMutationKind.RETIRE: (
            MutationCommandResult.RETIRED,
            PlayerCharacterLifecycle.RETIRED,
        ),
        PlayerCharacterMutationKind.REACTIVATE: (
            MutationCommandResult.REACTIVATED,
            PlayerCharacterLifecycle.ACTIVE,
        ),
        PlayerCharacterMutationKind.FINAL_DEATH: (
            MutationCommandResult.DECEASED,
            PlayerCharacterLifecycle.DECEASED,
        ),
        PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN: (
            MutationCommandResult.CONTINUITY_RETURNED,
            PlayerCharacterLifecycle.ACTIVE,
        ),
    }[kind]
    return MutationSuccessResult(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=character_id(),
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=kind,
        command_result=result,
        resulting_revision=PlayerCharacterRevision(value=resulting_revision),
        resulting_lifecycle=lifecycle,
    )


def stored_creation_receipt_payload() -> dict[str, object]:
    receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=ControllerBindingRef(
                value="Binding.MiXeD-K",
            ),
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=operation_id("Operation.MiXeD-K"),
        ),
        fingerprint=creation_fingerprint(creation_command())[1],
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=character_id("Pc.MiXeD-K"),
            contract_version=PlayerCharacterContractVersion.V1,
            resulting_revision=PlayerCharacterRevision(value=1),
            resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE,
        ),
    )
    return receipt.model_dump(mode="json")


def stored_mutation_receipt_payload() -> dict[str, object]:
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=character_id("Pc.MiXeD-K"),
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id("Operation.MiXeD-K"),
        ),
        fingerprint=mutation_fingerprint(
            mutation_command(PlayerCharacterMutationKind.RETIRE),
            operation_id=operation_id(),
        )[1],
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=character_id("Pc.MiXeD-K"),
            contract_version=PlayerCharacterContractVersion.V1,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=PlayerCharacterRevision(value=8),
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
    )
    return receipt.model_dump(mode="json")


def nested_value(value, path: tuple[str, ...]):
    current = value
    for field_name in path:
        if isinstance(current, dict):
            current = current[field_name]
        else:
            current = getattr(current, field_name)
    return current


def replace_nested_value(
    value: dict[str, object],
    path: tuple[str, ...],
    replacement: str,
) -> None:
    current = value
    for field_name in path[:-1]:
        current = current[field_name]  # type: ignore[assignment,index]
    current[path[-1]] = replacement  # type: ignore[index]


class SplitViewReceiptMapping(Mapping[str, object]):
    """Exposes one view through ``get`` and another through ``items``."""

    def __init__(
        self,
        *,
        prevalidation_view: dict[str, object],
        canonicalization_view: dict[str, object],
    ) -> None:
        self._prevalidation_view = prevalidation_view
        self._canonicalization_view = canonicalization_view

    def __getitem__(self, key: str) -> object:
        return self._canonicalization_view[key]

    def __iter__(self):
        return iter(self._canonicalization_view)

    def __len__(self) -> int:
        return len(self._canonicalization_view)

    def get(self, key: str, default: object = None) -> object:
        return self._prevalidation_view.get(key, default)

    def items(self):
        return self._canonicalization_view.items()


class SingleObservationReceiptMapping(Mapping[str, object]):
    """Rejects reads other than one top-level ``items`` materialization."""

    def __init__(self, value: dict[str, object]) -> None:
        self._value = value
        self.items_calls = 0

    def __getitem__(self, key: str) -> object:
        raise AssertionError("receipt reconstruction must not read __getitem__")

    def __iter__(self):
        raise AssertionError("receipt reconstruction must not iterate the source mapping")

    def __len__(self) -> int:
        raise AssertionError("receipt reconstruction must not measure the source mapping")

    def get(self, key: str, default: object = None) -> object:
        raise AssertionError("receipt reconstruction must not read get")

    def items(self):
        self.items_calls += 1
        if self.items_calls > 1:
            raise AssertionError("receipt reconstruction must materialize once")
        return self._value.items()


def test_canonical_serializer_defines_all_supported_scalar_sequence_and_object_behavior() -> None:
    first = canonical_character_operation_bytes(
        {
            "z": None,
            "a": [True, False, 0, -2, "Cafe\u0301"],
            "enum": NarrationPreference.HIGH_AGENCY,
            "object": {"β": 2, "a": 1},
        }
    )
    second = canonical_character_operation_bytes(
        {
            "object": {"a": 1, "β": 2},
            "enum": NarrationPreference.HIGH_AGENCY,
            "a": (True, False, 0, -2, "Café"),
            "z": None,
        }
    )
    assert first == second
    assert first == (
        '{"a":[true,false,0,-2,"Café"],"enum":"high-agency",'
        '"object":{"a":1,"β":2},"z":null}'
    ).encode()


@pytest.mark.parametrize(
    "unsupported",
    (
        1.0,
        float("nan"),
        b"bytes",
        {"unordered"},
        frozenset({"unordered"}),
        range(3),
        {1: "non-string-key"},
        2**63,
        -(2**63) - 1,
    ),
)
def test_canonical_serializer_rejects_unsupported_or_ambiguous_values(
    unsupported,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_character_operation_bytes(unsupported)


def test_canonical_serializer_rejects_nfc_colliding_object_keys() -> None:
    with pytest.raises(ValueError, match="collide"):
        canonical_character_operation_bytes({"Café": 1, "Cafe\u0301": 2})


def test_canonical_serializer_preserves_omitted_key_versus_explicit_null() -> None:
    assert canonical_character_operation_bytes({}) != (
        canonical_character_operation_bytes({"value": None})
    )


def test_creation_and_every_mutation_kind_match_fixed_golden_vectors() -> None:
    create_bytes, create_digest = creation_fingerprint(creation_command())
    assert create_bytes == GOLDEN_VECTORS["creation"]["canonical_json"].encode()
    assert create_digest.value == GOLDEN_VECTORS["creation"]["fingerprint"]
    for vector_name, kind in (
        ("retire", PlayerCharacterMutationKind.RETIRE),
        ("reactivate", PlayerCharacterMutationKind.REACTIVATE),
        ("final_death", PlayerCharacterMutationKind.FINAL_DEATH),
        (
            "authorized_continuity_return_unavailable",
            PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN,
        ),
    ):
        expected_literal = GOLDEN_VECTORS[vector_name]["canonical_json"].encode()
        assert (
            len(expected_literal)
            == MUTATION_GOLDEN_VECTOR_LENGTHS[vector_name]
        )
        encoded, digest = mutation_fingerprint(
            mutation_command(kind), operation_id=operation_id()
        )
        assert encoded == expected_literal
        assert digest.value == GOLDEN_VECTORS[vector_name]["fingerprint"]


def test_namespace_command_expected_revision_and_operation_binding_separate_fingerprints() -> None:
    create_bytes, create_digest = creation_fingerprint(creation_command())
    retire_bytes, retire_digest = mutation_fingerprint(
        mutation_command(PlayerCharacterMutationKind.RETIRE),
        operation_id=operation_id(),
    )
    later_bytes, later_digest = mutation_fingerprint(
        mutation_command(PlayerCharacterMutationKind.RETIRE, revision=8),
        operation_id=operation_id(),
    )
    other_operation = operation_id("operation.golden-2")
    other_operation_bytes, other_operation_digest = mutation_fingerprint(
        mutation_command(
            PlayerCharacterMutationKind.RETIRE,
            op_id=other_operation,
        ),
        operation_id=other_operation,
    )
    assert create_bytes != retire_bytes
    assert len(
        {
            create_digest.value,
            retire_digest.value,
            later_digest.value,
            other_operation_digest.value,
        }
    ) == 4
    assert later_bytes != retire_bytes
    assert other_operation_bytes != retire_bytes


def test_declaration_state_tags_are_not_replay_equivalent() -> None:
    vectors = {
        state: creation_fingerprint(creation_command(name_state=state))[1].value
        for state in ("omitted", "absent", "undecided", "declared")
    }
    assert len(set(vectors.values())) == 4


def test_unicode_equivalence_is_nfc_only_and_preserves_meaningful_text() -> None:
    composed = creation_fingerprint(creation_command(name="Café"))
    decomposed = creation_fingerprint(creation_command(name="Cafe\u0301"))
    case_changed = creation_fingerprint(creation_command(name="CAFÉ"))
    spaced = creation_fingerprint(creation_command(name=" Café "))
    assert composed == decomposed
    assert composed[1] != case_changed[1]
    assert composed[1] != spaced[1]


def test_fingerprints_have_no_session_run_request_action_provider_or_display_identity_dependency() -> None:
    encoded, _ = creation_fingerprint(creation_command())
    serialized = encoded.decode()
    for forbidden in (
        "session_id",
        "run_id",
        "client_request_id",
        "action_signature",
        "provider",
        "display_name",
        "controller_binding",
        "provenance",
        "player_character_id",
    ):
        assert forbidden not in serialized


def test_receipt_key_namespaces_and_owners_are_non_interchangeable() -> None:
    create_key = CreationReceiptKey(
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    mutate_key = MutationReceiptKey(
        player_character_id=character_id(),
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    assert type(create_key) is not type(mutate_key)
    with pytest.raises(ValidationError):
        CreationReceiptKey(
            controller_binding=ControllerBindingRef(value="binding.golden-1"),
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        )


def test_creation_authentication_and_trusted_binding_precede_lookup_and_allocation() -> None:
    looked_up = []

    def lookup(key):
        looked_up.append(key)
        return None

    for authenticated, binding in (
        (False, None),
        (False, ControllerBindingRef(value="binding.golden-1")),
        (True, None),
    ):
        decision = evaluate_creation_receipt_protocol(
            authentication_succeeded=authenticated,
            trusted_controller_binding=binding,
            operation_id=operation_id(),
            command=creation_command(),
            lookup_receipt=lookup,
        )
        assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        assert not decision.may_allocate_permanent_id
        assert decision.stored_success_result is None
    assert looked_up == []
    authorized = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=ControllerBindingRef(
            value="binding.golden-1"
        ),
        operation_id=operation_id(),
        command=creation_command(),
        lookup_receipt=lookup,
    )
    assert authorized.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    assert (
        authorized.operation_namespace
        is CharacterOperationNamespace.CREATE_V1
    )
    assert authorized.may_allocate_permanent_id
    assert not authorized.may_apply_mutation
    assert authorized.requires_atomic_success_receipt_on_commit
    assert len(looked_up) == 1


def test_exact_creation_replay_returns_stored_original_result_and_never_allocates() -> None:
    command = creation_command()
    _, fingerprint = creation_fingerprint(command)
    key = CreationReceiptKey(
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    stored = build_creation_success_receipt(
        key=key,
        fingerprint=fingerprint,
        result=creation_result(),
    )
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=key.controller_binding,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: stored,
    )
    assert decision.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert decision.stored_success_result == stored.result
    assert not decision.may_allocate_permanent_id
    assert not decision.requires_atomic_success_receipt_on_commit


def test_creation_mismatched_reuse_discloses_no_prior_result_and_changes_nothing() -> None:
    command = creation_command()
    _, fingerprint = creation_fingerprint(command)
    key = CreationReceiptKey(
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    stored = build_creation_success_receipt(
        key=key,
        fingerprint=fingerprint,
        result=creation_result(),
    )
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=key.controller_binding,
        operation_id=operation_id(),
        command=creation_command(name_state="absent"),
        lookup_receipt=lambda _: stored,
    )
    assert decision.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    assert decision.stored_success_result is None
    assert not decision.may_allocate_permanent_id


def test_mutation_authorizes_current_binding_before_receipt_or_character_disclosure() -> None:
    record = current_record()
    command = mutation_command(
        PlayerCharacterMutationKind.RETIRE,
        revision=record.record_revision.value,
    )
    lookups = []
    for authenticated, binding, current in (
        (False, record.controller_binding, record),
        (True, ControllerBindingRef(value="binding.other"), record),
        (True, record.controller_binding, None),
    ):
        decision = evaluate_mutation_receipt_protocol(
            authentication_succeeded=authenticated,
            trusted_controller_binding=binding,
            current_record=current,
            operation_id=operation_id(),
            command=command,
            lookup_receipt=lambda key: lookups.append(key),
        )
        assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        assert decision.stored_success_result is None
    assert lookups == []
    authorized = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: None,
    )
    assert authorized.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    assert (
        authorized.operation_namespace
        is CharacterOperationNamespace.MUTATE_V1
    )
    assert authorized.may_apply_mutation
    assert not authorized.may_allocate_permanent_id
    assert authorized.requires_atomic_success_receipt_on_commit


def test_exact_mutation_replay_precedes_revision_check_and_returns_original_result() -> None:
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=7)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    key = MutationReceiptKey(
        player_character_id=character_id(),
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    stored = build_mutation_success_receipt(
        key=key,
        fingerprint=fingerprint,
        result=mutation_result(),
    )
    later_record = current_record(revision=12)
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=later_record.controller_binding,
        current_record=later_record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: stored,
    )
    assert decision.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert decision.stored_success_result == mutation_result()
    assert not decision.may_apply_mutation


@pytest.mark.parametrize(
    "kind",
    (
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.FINAL_DEATH,
    ),
)
def test_successful_mutation_replay_validates_exact_resulting_record_bindings(
    kind: PlayerCharacterMutationKind,
) -> None:
    prior_record = current_record()
    command = mutation_command(kind, revision=1)
    policy = evaluate_mutation_policy(
        prior_record,
        command=command,
        operation_id=operation_id(),
    )
    assert policy.resulting_record is not None
    resulting_record = policy.resulting_record
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    stored = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=prior_record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        result=mutation_result(kind, resulting_revision=2),
    )

    replay = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=resulting_record.controller_binding,
        current_record=resulting_record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: stored,
    )
    assert replay.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert replay.stored_success_result == stored.result


def test_stale_new_mutation_never_applies_or_writes_a_success_receipt() -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=7)
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: None,
    )
    assert decision.code is CharacterOperationProtocolCode.STALE_REVISION
    assert not decision.may_apply_mutation
    assert not decision.requires_atomic_success_receipt_on_commit


@pytest.mark.parametrize(
    ("mismatch", "expected_code"),
    (
        ("fingerprint", CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT),
        ("command", CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE),
        ("target", CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE),
        ("schema", CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE),
        ("resulting_revision", CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT),
    ),
)
def test_mutation_mismatched_reuse_is_deterministic_and_discloses_no_result(
    mismatch: str,
    expected_code: CharacterOperationProtocolCode,
) -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    key = MutationReceiptKey(
        player_character_id=character_id(),
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    stored = build_mutation_success_receipt(
        key=key,
        fingerprint=fingerprint,
        result=mutation_result(),
    )
    if mismatch == "fingerprint":
        _, other_fingerprint = mutation_fingerprint(
            mutation_command(PlayerCharacterMutationKind.RETIRE, revision=8),
            operation_id=operation_id(),
        )
        stored = stored.model_copy(update={"fingerprint": other_fingerprint})
    elif mismatch == "command":
        stored = stored.model_copy(
            update={"command_kind": PlayerCharacterMutationKind.REACTIVATE.value}
        )
    elif mismatch == "target":
        stored = stored.model_copy(
            update={
                "result": stored.result.model_copy(
                    update={"player_character_id": PlayerCharacterId(value="pc.other")}
                )
            }
        )
    elif mismatch == "schema":
        stored = stored.model_copy(
            update={"result_schema_version": "player-character.mutate-result/v2"}
        )
    else:
        stored = stored.model_copy(
            update={
                "result": stored.result.model_copy(
                    update={
                        "resulting_revision": PlayerCharacterRevision(value=9)
                    }
                )
            }
        )
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: stored,
    )
    assert decision.code is expected_code
    assert decision.stored_success_result is None
    assert not decision.may_apply_mutation


def test_malformed_stored_receipt_is_integrity_failure_not_reconstructed_success() -> None:
    command = creation_command()
    _, fingerprint = creation_fingerprint(command)
    key = CreationReceiptKey(
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    class MalformedStoredReceipt:
        def model_dump(self, *, mode: str):
            assert mode == "python"
            return {
                "key": key,
                "fingerprint": fingerprint,
                "command_kind": PlayerCharacterMutationKind.CREATE.value,
                "result_schema_version": CREATION_RESULT_SCHEMA_VERSION,
                "result": {"private_record": "must not be reconstructed"},
            }

    malformed = MalformedStoredReceipt()
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=key.controller_binding,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: malformed,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None
    assert not decision.may_allocate_permanent_id


def test_invalid_current_record_fails_privately_before_mutation_receipt_lookup() -> None:
    record = current_record()
    invalid = record.model_copy(update={"controller_binding": None})
    lookups = []
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=invalid,
        operation_id=operation_id(),
        command=mutation_command(
            PlayerCharacterMutationKind.RETIRE,
            revision=record.record_revision.value,
        ),
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


def test_privacy_safe_success_results_and_receipts_exclude_private_authority_data() -> None:
    creation = creation_result()
    mutation = mutation_result()
    serialized = canonical_character_operation_bytes(
        {
            "creation": creation,
            "mutation": mutation,
        }
    ).decode()
    for forbidden in (
        "controller",
        "principal",
        "provenance",
        "confirmation",
        "provider",
        "private",
        "source_reference",
    ):
        assert forbidden not in serialized


def test_stored_success_receipts_round_trip_strict_json_and_reject_unknown_fields() -> None:
    command = creation_command()
    _, creation_digest = creation_fingerprint(command)
    creation_key = CreationReceiptKey(
        controller_binding=ControllerBindingRef(value="binding.golden-1"),
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    creation_receipt = build_creation_success_receipt(
        key=creation_key,
        fingerprint=creation_digest,
        result=creation_result(),
    )
    creation_payload = creation_receipt.model_dump(mode="json")
    assert (
        validate_stored_creation_success_receipt(creation_payload)
        == creation_receipt
    )
    with pytest.raises(ValidationError):
        validate_stored_creation_success_receipt(
            {**creation_payload, "private_record": {}}
        )

    mutation = mutation_command(PlayerCharacterMutationKind.RETIRE)
    _, mutation_digest = mutation_fingerprint(
        mutation, operation_id=operation_id()
    )
    mutation_receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=character_id(),
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=mutation_digest,
        result=mutation_result(),
    )
    assert validate_stored_mutation_success_receipt(
        mutation_receipt.model_dump(mode="json")
    ) == mutation_receipt
    serialized = canonical_character_operation_bytes(creation_payload).decode()
    with pytest.raises(ValueError, match="duplicate"):
        validate_stored_creation_success_receipt(
            serialized.replace(
                '{"command_kind":"CREATE",',
                '{"command_kind":"CREATE","command_kind":"CREATE",',
                1,
            )
        )
    with pytest.raises(ValueError, match="float"):
        validate_stored_creation_success_receipt(
            serialized.replace('"command_kind":"CREATE"', '"unexpected":1.5', 1)
        )
    for invalid_constant in ("NaN", "Infinity", "-Infinity"):
        with pytest.raises(ValueError, match="constant"):
            validate_stored_creation_success_receipt(
                serialized.replace(
                    '"command_kind":"CREATE"',
                    f'"unexpected":{invalid_constant}',
                    1,
                )
            )
    with pytest.raises(ValueError, match="valid strict JSON"):
        validate_stored_creation_success_receipt(
            serialized.encode("utf-8") + b"\xff"
        )
    with pytest.raises(ValueError, match="byte bound"):
        validate_stored_creation_success_receipt(
            b'{"padding":"' + (b"x" * 65_536) + b'"}'
        )
    missing_key = dict(creation_payload)
    missing_key.pop("key")
    with pytest.raises(ValidationError):
        validate_stored_creation_success_receipt(missing_key)
    with pytest.raises(ValidationError, match="bindings are inconsistent"):
        validate_stored_creation_success_receipt(
            {**creation_payload, "command_kind": "RETIRE"}
        )


@pytest.mark.parametrize(
    "entry_point",
    ("mapping", "strict-json-bytes"),
    ids=("mapping", "strict-json-bytes"),
)
@pytest.mark.parametrize(
    ("receipt_payload", "validator", "identifier_path"),
    (
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("key", "controller_binding", "value"),
            id="creation-key-controller-binding-controller-binding-ref",
        ),
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("key", "operation_id", "value"),
            id="creation-key-operation-id-player-character-operation-id",
        ),
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("result", "player_character_id", "value"),
            id="creation-result-player-character-id-player-character-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("key", "player_character_id", "value"),
            id="mutation-key-player-character-id-player-character-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("key", "operation_id", "value"),
            id="mutation-key-operation-id-player-character-operation-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("result", "player_character_id", "value"),
            id="mutation-result-player-character-id-player-character-id",
        ),
    ),
)
def test_stored_receipt_identifiers_validate_original_input_before_normalization(
    receipt_payload,
    validator,
    identifier_path: tuple[str, ...],
    entry_point: str,
) -> None:
    invalid_payload = receipt_payload()
    exact_ascii = nested_value(invalid_payload, identifier_path)
    assert isinstance(exact_ascii, str)
    assert exact_ascii.endswith("K")
    invalid_original = f"{exact_ascii[:-1]}\u212a"
    replace_nested_value(
        invalid_payload,
        identifier_path,
        invalid_original,
    )
    invalid_input = (
        invalid_payload
        if entry_point == "mapping"
        else json.dumps(
            invalid_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    if isinstance(invalid_input, bytes):
        assert invalid_original.encode("utf-8") in invalid_input
        assert invalid_original.encode("utf-8") != exact_ascii.encode("utf-8")
    else:
        assert nested_value(invalid_input, identifier_path) == invalid_original

    with pytest.raises(ValidationError, match="bounded opaque identifier"):
        validator(invalid_input)

    accepted_payload = receipt_payload()
    accepted_original = nested_value(accepted_payload, identifier_path)
    accepted_input = (
        accepted_payload
        if entry_point == "mapping"
        else json.dumps(
            accepted_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    reconstructed = validator(accepted_input)
    exposed = nested_value(reconstructed, identifier_path)
    assert exposed == accepted_original
    assert exposed.encode("utf-8") == accepted_original.encode("utf-8")


@pytest.mark.parametrize(
    ("receipt_payload", "validator", "identifier_path"),
    (
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("key", "controller_binding", "value"),
            id="creation-controller-binding",
        ),
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("key", "operation_id", "value"),
            id="creation-operation-id",
        ),
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("result", "player_character_id", "value"),
            id="creation-result-player-character-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("key", "player_character_id", "value"),
            id="mutation-key-player-character-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("key", "operation_id", "value"),
            id="mutation-operation-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("result", "player_character_id", "value"),
            id="mutation-result-player-character-id",
        ),
    ),
)
def test_stored_receipt_mapping_snapshot_rejects_split_view_identifiers(
    receipt_payload,
    validator,
    identifier_path: tuple[str, ...],
) -> None:
    prevalidation_view = receipt_payload()
    canonicalization_view = deepcopy(prevalidation_view)
    exact_ascii = nested_value(prevalidation_view, identifier_path)
    assert isinstance(exact_ascii, str)
    invalid_original = f"{exact_ascii[:-1]}\u212a"
    replace_nested_value(
        canonicalization_view,
        identifier_path,
        invalid_original,
    )
    split_view = SplitViewReceiptMapping(
        prevalidation_view=prevalidation_view,
        canonicalization_view=canonicalization_view,
    )

    with pytest.raises(ValidationError, match="bounded opaque identifier"):
        validator(split_view)


def test_stored_receipt_mapping_snapshot_recursively_materializes_nested_mappings() -> None:
    prevalidation_view = stored_creation_receipt_payload()
    canonicalization_view = deepcopy(prevalidation_view)
    replace_nested_value(
        canonicalization_view,
        ("key", "operation_id", "value"),
        "Operation.MiXeD-\u212a",
    )
    nested_split_view = SplitViewReceiptMapping(
        prevalidation_view=prevalidation_view["key"],  # type: ignore[arg-type]
        canonicalization_view=canonicalization_view["key"],  # type: ignore[arg-type]
    )
    payload = dict(prevalidation_view)
    payload["key"] = nested_split_view

    with pytest.raises(ValidationError, match="bounded opaque identifier"):
        validate_stored_creation_success_receipt(payload)


@pytest.mark.parametrize(
    ("receipt_payload", "validator", "identifier_path"),
    (
        pytest.param(
            stored_creation_receipt_payload,
            validate_stored_creation_success_receipt,
            ("key", "operation_id", "value"),
            id="creation-operation-id",
        ),
        pytest.param(
            stored_mutation_receipt_payload,
            validate_stored_mutation_success_receipt,
            ("key", "player_character_id", "value"),
            id="mutation-player-character-id",
        ),
    ),
)
def test_stored_receipt_mapping_is_materialized_once_and_preserves_ascii_values(
    receipt_payload,
    validator,
    identifier_path: tuple[str, ...],
) -> None:
    source = SingleObservationReceiptMapping(receipt_payload())

    reconstructed = validator(source)

    exposed = nested_value(reconstructed, identifier_path)
    assert isinstance(exposed, str)
    assert exposed.endswith("MiXeD-K")
    assert exposed.encode("utf-8") == exposed.encode("ascii")
    assert source.items_calls == 1


def test_unique_race_recovery_requires_rollback_and_never_repeats_creation() -> None:
    command = creation_command()
    _, fingerprint = creation_fingerprint(command)
    binding = ControllerBindingRef(value="binding.golden-1")
    key = CreationReceiptKey(
        controller_binding=binding,
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id(),
    )
    winner = build_creation_success_receipt(
        key=key,
        fingerprint=fingerprint,
        result=creation_result(),
    )
    rereads = []
    with pytest.raises(RuntimeError, match="roll back"):
        recover_creation_unique_race_winner(
            losing_transaction_rolled_back=False,
            authentication_succeeded=True,
            trusted_controller_binding=binding,
            operation_id=operation_id(),
            command=command,
            reread_receipt_in_fresh_transaction=lambda value: rereads.append(
                value
            ),
        )
    assert rereads == []
    replay = recover_creation_unique_race_winner(
        losing_transaction_rolled_back=True,
        authentication_succeeded=True,
        trusted_controller_binding=binding,
        operation_id=operation_id(),
        command=command,
        reread_receipt_in_fresh_transaction=lambda value: winner,
    )
    assert replay.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert not replay.may_allocate_permanent_id
    missing_winner = recover_creation_unique_race_winner(
        losing_transaction_rolled_back=True,
        authentication_succeeded=True,
        trusted_controller_binding=binding,
        operation_id=operation_id(),
        command=command,
        reread_receipt_in_fresh_transaction=lambda value: None,
    )
    assert (
        missing_winner.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert not missing_winner.may_allocate_permanent_id


def test_mutation_unique_race_recovery_never_reapplies_without_durable_winner() -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    decision = recover_mutation_unique_race_winner(
        losing_transaction_rolled_back=True,
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        reread_receipt_in_fresh_transaction=lambda value: None,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert not decision.may_apply_mutation


def test_transaction_orders_encode_authorization_replay_atomicity_and_fresh_reread() -> None:
    assert CREATION_TRANSACTION_ORDER.index(
        type(CREATION_TRANSACTION_ORDER[0]).LOOK_UP_CREATION_RECEIPT
    ) < CREATION_TRANSACTION_ORDER.index(
        type(CREATION_TRANSACTION_ORDER[0]).ALLOCATE_PERMANENT_ID
    )
    assert MUTATION_TRANSACTION_ORDER.index(
        type(
            MUTATION_TRANSACTION_ORDER[0]
        ).VALIDATE_TYPED_OPERATION_AND_REVISION_DOMAIN
    ) < MUTATION_TRANSACTION_ORDER.index(
        type(MUTATION_TRANSACTION_ORDER[0]).LOOK_UP_MUTATION_RECEIPT
    )
    assert MUTATION_TRANSACTION_ORDER.index(
        type(MUTATION_TRANSACTION_ORDER[0]).RESOLVE_REPLAY_OR_CONFLICT
    ) < MUTATION_TRANSACTION_ORDER.index(
        type(
            MUTATION_TRANSACTION_ORDER[0]
        ).VALIDATE_CONTEXT_REFERENCE_AND_EXPECTED_REVISION
    )
    assert [step.value for step in UNIQUE_RACE_RECOVERY_ORDER][:2] == [
        "roll-back-losing-transaction",
        "open-fresh-transaction",
    ]
    requirements = LATER_PERSISTENCE_ATOMICITY_REQUIREMENTS
    assert requirements.allocation_ledger_is_append_only
    assert requirements.issued_ids_are_never_reusable
    assert requirements.losing_attempt_leaves_no_reusable_orphan_id
    assert requirements.equivalent_concurrent_creation_has_at_most_one_committed_winner
    assert not requirements.repository_methods_commit_independently
    assert not requirements.response_may_report_success_before_commit


def test_first_slice_retention_is_bounded_omission_not_permanent_policy() -> None:
    boundary = FIRST_SLICE_RETENTION_BOUNDARY
    assert boundary.successful_receipts_only
    assert not boundary.pending_state_supported
    assert not boundary.rejected_receipts_supported
    assert not boundary.cleanup_supported
    assert not boundary.deletion_supported
    assert not boundary.archival_supported
    assert not boundary.permanent_retention_policy_selected
    assert not boundary.production_rollout_supported


def test_applicable_reference_is_fingerprinted_and_cannot_bypass_replay_or_policy() -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    encoded, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    assert b'"applicable_reference"' in encoded
    key = MutationReceiptKey(
        player_character_id=character_id(),
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    stored = build_mutation_success_receipt(
        key=key, fingerprint=fingerprint, result=mutation_result()
    )
    changed = command.model_copy(
        update={
            "applicable_reference": command.applicable_reference.model_copy(
                update={"record_revision": PlayerCharacterRevision(value=2)}
            ),
            "expected_revision": PlayerCharacterRevision(value=2),
        }
    )
    changed = changed.model_copy(
        update={
            "confirmation": changed.confirmation.model_copy(
                update={"expected_revision": PlayerCharacterRevision(value=2)}
            )
        }
    )
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=changed,
        lookup_receipt=lambda _: stored,
    )
    assert decision.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    policy = evaluate_mutation_policy(record, command=command, operation_id=operation_id())
    assert policy.applicable_reference is command.applicable_reference


@pytest.mark.parametrize(
    ("text", "declaration_bytes"),
    (
        ("x" * 64_819, 65_535),
        ("x" * 64_820, 65_536),
        (chr(0xE9) * 32_410, 65_536),
        (("e" + chr(0x301)) * 32_410, 65_536),
    ),
    ids=("below", "exact-ascii", "exact-multibyte", "exact-nfc"),
)
def test_fixed_declaration_boundary_can_participate_in_creation(
    text: str,
    declaration_bytes: int,
) -> None:
    command = boundary_creation_command(text)
    assert len(
        canonical_player_declaration_bytes(
            character_core=command.character_core,
            narration_preferences=command.narration_preferences,
        )
    ) == declaration_bytes

    encoded, fingerprint = creation_fingerprint(command)
    assert len(encoded) > declaration_bytes
    assert b'"command_kind":"CREATE"' in encoded
    assert b'"contract_version":"structured-player-character/v1"' in encoded
    assert b'"operation_namespace":"player-character.create/v1"' in encoded
    assert len(fingerprint.value) == 64

    created = CreatePlayerCharacterPolicy().create(
        player_character_id=PlayerCharacterId(value="pc.boundary-create"),
        controller_binding=ControllerBindingRef(
            value="binding.boundary-create"
        ),
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=AuthoritySourceRef(value="source.boundary-create"),
    )
    assert validate_canonical_player_character(created) == created

    lookups = []
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=created.controller_binding,
        operation_id=operation_id("operation.boundary-create"),
        command=command,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    assert len(lookups) == 1


def test_fixed_65_features_validate_through_the_complete_creation_boundary() -> None:
    command = fixed_65_feature_creation_command()
    declaration = command.character_core.distinguishing_features
    assert declaration.value is not None
    assert len(declaration.value.features) == 65

    declaration_bytes = canonical_player_declaration_bytes(
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
    )
    assert len(declaration_bytes) < 65_536
    assert CharacterCreationCommand.model_validate(command) == command

    record = current_record().detached_validated_copy(
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
    )
    assert validate_canonical_player_character(record) == record

    fingerprint_bytes, fingerprint = creation_fingerprint(command)
    assert fingerprint_bytes
    assert len(fingerprint.value) == 64

    created = CreatePlayerCharacterPolicy().create(
        player_character_id=PlayerCharacterId(value="pc.fixed-65-features"),
        controller_binding=ControllerBindingRef(
            value="binding.fixed-65-features"
        ),
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=AuthoritySourceRef(
            value="source.fixed-65-features"
        ),
    )
    assert created.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert validate_canonical_player_character(created) == created

    lookups = []
    protocol = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=created.controller_binding,
        operation_id=operation_id("operation.fixed-65-features"),
        command=command,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert protocol.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    assert len(lookups) == 1


def test_fixed_65_537_byte_declaration_fails_before_creation_receipt_lookup() -> None:
    core = CharacterCore(
        name_or_code_name=Declaration[PlayerDeclaredText].declared(
            player_text("x" * 64_821)
        )
    )
    with pytest.raises(ValidationError, match="declaration"):
        CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=core,
            narration_preferences=NarrationPreferences(),
        )

    bypassed = CharacterCreationCommand.model_construct(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=core,
        narration_preferences=NarrationPreferences(),
    )
    lookups = []
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=ControllerBindingRef(
            value="binding.over-boundary"
        ),
        operation_id=operation_id("operation.over-boundary"),
        command=bypassed,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


def test_creation_boundaries_reject_bypassed_nested_declaration_before_lookup() -> None:
    valid_text = player_text("valid before bypass")
    corrupted_text = valid_text.model_copy(update={"text": None})
    declaration = Declaration[PlayerDeclaredText].declared(valid_text)
    corrupted_core = CharacterCore().model_copy(
        update={
            "name_or_code_name": declaration.model_copy(
                update={"value": corrupted_text}
            )
        }
    )
    bypassed = CharacterCreationCommand.model_construct(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=corrupted_core,
        narration_preferences=NarrationPreferences(),
    )

    with pytest.raises(ValidationError, match="character_core"):
        creation_fingerprint(bypassed)
    lookups = []
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=ControllerBindingRef(
            value="binding.corrupted-declaration"
        ),
        operation_id=operation_id("operation.corrupted-declaration"),
        command=bypassed,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


def test_unknown_creation_command_state_rejects_before_fingerprint_and_lookup() -> None:
    command = creation_command()
    corrupted = command.model_copy(
        update={"unknown_command_state": "caller-injected"}
    )

    with pytest.raises(ValueError, match="unknown instance state"):
        creation_fingerprint(corrupted)

    lookups = []
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=ControllerBindingRef(
            value="binding.unknown-command"
        ),
        operation_id=operation_id("operation.unknown-command"),
        command=corrupted,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


@pytest.mark.parametrize("trusted_value", ("controller", "operation"))
def test_creation_protocol_revalidates_trusted_identity_values_before_lookup(
    trusted_value: str,
) -> None:
    binding = ControllerBindingRef(value="binding.creation-trust-boundary")
    op_id = operation_id("operation.creation-trust-boundary")
    if trusted_value == "controller":
        binding = binding.model_copy(update={"value": None})
    else:
        op_id = op_id.model_construct(value=None)
    lookups = []
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=binding,
        operation_id=op_id,
        command=creation_command(),
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


@pytest.mark.parametrize(
    "corruption",
    (
        "missing_reference",
        "missing_nested_revision",
        "invalid_contract_version",
        "malformed_nested_identity",
        "unknown_nested_attribute",
    ),
)
def test_corrupted_applicable_reference_fails_at_every_mutation_boundary(
    corruption: str,
) -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    reference = command.applicable_reference
    if corruption == "missing_reference":
        corrupted_reference = None
    elif corruption == "missing_nested_revision":
        corrupted_reference = reference.model_copy(
            update={
                "record_revision": reference.record_revision.model_construct(
                    value=None
                )
            }
        )
    elif corruption == "invalid_contract_version":
        corrupted_reference = reference.model_copy(
            update={"contract_version": "structured-player-character/v999"}
        )
    elif corruption == "malformed_nested_identity":
        corrupted_reference = reference.model_copy(
            update={
                "player_character_id": reference.player_character_id.model_copy(
                    update={"value": None}
                )
            }
        )
    else:
        corrupted_reference = reference.model_copy(
            update={
                "record_revision": reference.record_revision.model_copy(
                    update={"unknown_reference_state": "caller-injected"}
                )
            }
        )
    corrupted_command = command.model_copy(
        update={"applicable_reference": corrupted_reference}
    )
    expected_error = (
        ValueError
        if corruption == "unknown_nested_attribute"
        else (ValidationError, TypeError)
    )
    expected_match = (
        "unknown instance state"
        if corruption == "unknown_nested_attribute"
        else None
    )

    with pytest.raises(expected_error, match=expected_match):
        mutation_fingerprint(corrupted_command, operation_id=operation_id())
    with pytest.raises(expected_error, match=expected_match):
        evaluate_mutation_policy(
            record,
            command=corrupted_command,
            operation_id=operation_id(),
        )

    lookups = []
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=corrupted_command,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


@pytest.mark.parametrize(
    "corruption",
    (
        "nested_declaration",
        "provenance_authority",
        "unavailable_active_provenance",
        "unknown_top_level",
    ),
)
def test_corrupted_current_record_blocks_matching_receipt_lookup_and_disclosure(
    corruption: str,
) -> None:
    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    stored = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        result=mutation_result(resulting_revision=2),
    )
    if corruption == "nested_declaration":
        declaration = Declaration[PlayerDeclaredText].declared(
            player_text("valid")
        )
        corrupted_text = declaration.value.model_copy(update={"text": None})
        corrupted = record.model_copy(
            update={
                "character_core": record.character_core.model_copy(
                    update={
                        "name_or_code_name": declaration.model_copy(
                            update={"value": corrupted_text}
                        )
                    }
                )
            }
        )
    elif corruption == "provenance_authority":
        corrupted = record.model_copy(
            update={
                "authority_provenance": record.authority_provenance.model_copy(
                    update={
                        "authority_class": (
                            PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME
                        )
                    }
                )
            }
        )
    elif corruption == "unavailable_active_provenance":
        resulting_revision = PlayerCharacterRevision(value=2)
        corrupted = record.model_copy(
            update={
                "record_revision": resulting_revision,
                "lifecycle": PlayerCharacterLifecycle.ACTIVE,
                "authority_provenance": AuthorityProvenance.model_construct(
                    target_player_character_id=record.player_character_id,
                    prior_revision=record.record_revision,
                    resulting_revision=resulting_revision,
                    mutation_kind=PlayerCharacterMutationKind.REACTIVATE,
                    authority_class=(
                        PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER
                    ),
                    source_reference=AuthoritySourceRef(
                        value="source.forged-reactivation"
                    ),
                ),
            }
        )
    else:
        corrupted = record.model_copy(
            update={"unknown_record_state": "caller-injected"}
        )

    lookups = []
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=corrupted,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda key: lookups.append(key) or stored,
    )
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert decision.stored_success_result is None
    assert lookups == []


@pytest.mark.parametrize(
    "corruption",
    ("receipt", "key", "result"),
)
def test_unknown_stored_receipt_state_is_rejected_before_success_disclosure(
    corruption: str,
) -> None:
    prior_record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    resulting_record = evaluate_mutation_policy(
        prior_record,
        command=command,
        operation_id=operation_id(),
    ).resulting_record
    assert resulting_record is not None
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=prior_record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        result=mutation_result(resulting_revision=2),
    )
    if corruption == "receipt":
        corrupted = receipt.model_copy(
            update={"unknown_receipt_state": "caller-injected"}
        )
    elif corruption == "key":
        corrupted = receipt.model_copy(
            update={
                "key": receipt.key.model_copy(
                    update={"unknown_key_state": "caller-injected"}
                )
            }
        )
    else:
        corrupted = receipt.model_copy(
            update={
                "result": receipt.result.model_copy(
                    update={"unknown_result_state": "caller-injected"}
                )
            }
        )

    with pytest.raises(ValueError, match="unknown instance state"):
        validate_stored_mutation_success_receipt(corrupted)
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=resulting_record.controller_binding,
        current_record=resulting_record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: corrupted,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None
    assert not decision.may_apply_mutation


def test_corrupted_stored_receipt_fails_before_touching_success_result() -> None:
    class StoredSuccessDisclosureSentinel:
        def __init__(self) -> None:
            object.__setattr__(self, "accessed", False)

        def __getattribute__(self, name: str):
            if name in {"accessed", "__dict__", "__class__"}:
                return object.__getattribute__(self, name)
            object.__setattr__(self, "accessed", True)
            raise AssertionError("stored success result was touched")

    record = current_record()
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        result=mutation_result(resulting_revision=2),
    )
    sentinel = StoredSuccessDisclosureSentinel()
    corrupted = receipt.model_copy(
        update={
            "result": sentinel,
            "unknown_receipt_state": "caller-injected",
        }
    )

    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: corrupted,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None
    assert not sentinel.accessed


@pytest.mark.parametrize(
    ("kind", "record_factory", "command_result"),
    (
        (
            PlayerCharacterMutationKind.REACTIVATE,
            lambda: current_record(revision=7),
            MutationCommandResult.REACTIVATED,
        ),
        (
            PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN,
            lambda: deceased_record(revision=7),
            MutationCommandResult.CONTINUITY_RETURNED,
        ),
    ),
)
def test_unavailable_mutation_cannot_replay_forged_matching_success(
    kind: PlayerCharacterMutationKind,
    record_factory,
    command_result: MutationCommandResult,
) -> None:
    record = record_factory()
    command = mutation_command(kind, revision=7)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    key = MutationReceiptKey(
        player_character_id=record.player_character_id,
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    forged_result = MutationSuccessResult.model_construct(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=record.player_character_id,
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=kind,
        command_result=command_result,
        resulting_revision=PlayerCharacterRevision(value=8),
        resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE,
    )
    forged_receipt = StoredMutationSuccessReceipt.model_construct(
        key=key,
        fingerprint=fingerprint,
        command_kind=kind.value,
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        result=forged_result,
    )

    with pytest.raises(ValidationError, match="unavailable"):
        validate_stored_mutation_success_receipt(forged_receipt)
    with pytest.raises(ValidationError, match="unavailable"):
        build_mutation_success_receipt(
            key=key,
            fingerprint=fingerprint,
            result=forged_result,
        )

    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: forged_receipt,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None
    assert not decision.may_apply_mutation


@pytest.mark.parametrize("forgery", ("active_result", "wrong_result_category"))
def test_semantically_impossible_stored_success_is_integrity_failure(
    forgery: str,
) -> None:
    record = current_record(revision=7)
    command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=7)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    key = MutationReceiptKey(
        player_character_id=record.player_character_id,
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id(),
    )
    if forgery == "active_result":
        result = mutation_result().model_copy(
            update={"resulting_lifecycle": PlayerCharacterLifecycle.ACTIVE}
        )
    else:
        result = creation_result()
    forged = StoredMutationSuccessReceipt.model_construct(
        key=key,
        fingerprint=fingerprint,
        command_kind=PlayerCharacterMutationKind.RETIRE.value,
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        result=result,
    )

    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: forged,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None


def test_stored_success_rejects_conflicting_exact_revision_provenance() -> None:
    prior_record = current_record()
    retire_command = mutation_command(PlayerCharacterMutationKind.RETIRE, revision=1)
    death_operation = operation_id("operation.actual-final-death")
    death_command = mutation_command(
        PlayerCharacterMutationKind.FINAL_DEATH,
        revision=1,
        op_id=death_operation,
    )
    actual_record = evaluate_mutation_policy(
        prior_record,
        command=death_command,
        operation_id=death_operation,
    ).resulting_record
    assert actual_record is not None

    _, retire_fingerprint = mutation_fingerprint(
        retire_command,
        operation_id=operation_id(),
    )
    forged_retire_receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=prior_record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=retire_fingerprint,
        result=mutation_result(
            PlayerCharacterMutationKind.RETIRE,
            resulting_revision=2,
        ),
    )
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=actual_record.controller_binding,
        current_record=actual_record,
        operation_id=operation_id(),
        command=retire_command,
        lookup_receipt=lambda _: forged_retire_receipt,
    )
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert decision.stored_success_result is None


def test_application_boundary_rejects_revision_overflow_before_receipt_lookup() -> None:
    record = current_record(revision=9223372036854775807)
    command = mutation_command(
        PlayerCharacterMutationKind.FINAL_DEATH,
        revision=9223372036854775807,
    )
    with pytest.raises(ValueError, match="no representable signed 64-bit successor"):
        mutation_fingerprint(command, operation_id=operation_id())

    def lookup_must_not_run(_):
        raise AssertionError("revision-exhausted operation reached receipt lookup")

    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lookup_must_not_run,
    )
    assert decision.code is CharacterOperationProtocolCode.REVISION_EXHAUSTED
    assert decision.stored_success_result is None
    assert not decision.may_apply_mutation
    assert not decision.requires_atomic_success_receipt_on_commit


def test_forged_out_of_range_prior_and_result_reject_before_lookup_or_receipt_bytes() -> None:
    record = current_record(revision=9223372036854775807)
    valid_command = mutation_command(
        PlayerCharacterMutationKind.FINAL_DEATH,
        revision=9223372036854775807,
    )
    invalid_revision = PlayerCharacterRevision.model_construct(
        value=9223372036854775808
    )
    invalid_reference = ApplicableCharacterReference.model_construct(
        player_character_id=valid_command.target_player_character_id,
        contract_version=valid_command.contract_version,
        record_revision=invalid_revision,
    )
    assert valid_command.final_death_evidence is not None
    invalid_evidence = valid_command.final_death_evidence.model_copy(
        update={"expected_revision": invalid_revision}
    )
    invalid_prior_command = CharacterMutationCommand.model_construct(
        contract_version=valid_command.contract_version,
        command_kind=valid_command.command_kind,
        target_player_character_id=valid_command.target_player_character_id,
        expected_revision=invalid_revision,
        applicable_reference=invalid_reference,
        confirmation=None,
        final_death_evidence=invalid_evidence,
    )
    lookups = []
    prior_decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=record.controller_binding,
        current_record=record,
        operation_id=operation_id(),
        command=invalid_prior_command,
        lookup_receipt=lambda key: lookups.append(key),
    )
    assert (
        prior_decision.code
        is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    )
    assert prior_decision.stored_success_result is None
    assert lookups == []

    fingerprintable_command = mutation_command(
        PlayerCharacterMutationKind.FINAL_DEATH,
        revision=9223372036854775806,
    )
    _, fingerprint = mutation_fingerprint(
        fingerprintable_command,
        operation_id=operation_id(),
    )
    forged_result = MutationSuccessResult.model_construct(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=record.player_character_id,
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=PlayerCharacterMutationKind.FINAL_DEATH,
        command_result=MutationCommandResult.DECEASED,
        resulting_revision=invalid_revision,
        resulting_lifecycle=PlayerCharacterLifecycle.DECEASED,
    )
    forged_receipt = StoredMutationSuccessReceipt.model_construct(
        key=MutationReceiptKey(
            player_character_id=record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        command_kind=PlayerCharacterMutationKind.FINAL_DEATH.value,
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        result=forged_result,
    )
    with pytest.raises(ValidationError, match="less than or equal"):
        canonical_character_operation_bytes(forged_result)
    with pytest.raises(ValidationError, match="less than or equal"):
        build_mutation_success_receipt(
            key=forged_receipt.key,
            fingerprint=fingerprint,
            result=forged_result,
        )
    with pytest.raises(ValidationError, match="less than or equal"):
        validate_stored_mutation_success_receipt(forged_receipt)


def test_last_representable_success_exact_replay_and_changed_conflict_remain_supported() -> None:
    command = mutation_command(
        PlayerCharacterMutationKind.FINAL_DEATH,
        revision=9223372036854775806,
    )
    current = deceased_record(revision=9223372036854775807)
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id())
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=current.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id(),
        ),
        fingerprint=fingerprint,
        result=mutation_result(
            PlayerCharacterMutationKind.FINAL_DEATH,
            resulting_revision=9223372036854775807,
        ),
    )

    exact = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=current.controller_binding,
        current_record=current,
        operation_id=operation_id(),
        command=command,
        lookup_receipt=lambda _: receipt,
    )
    assert exact.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert exact.stored_success_result == receipt.result

    assert command.final_death_evidence is not None
    changed = command.model_copy(
        update={
            "final_death_evidence": command.final_death_evidence.model_copy(
                update={
                    "source_reference": AuthoritySourceRef(
                        value="event.changed-at-high-revision"
                    )
                }
            )
        }
    )
    conflict = evaluate_mutation_receipt_protocol(
        authentication_succeeded=True,
        trusted_controller_binding=current.controller_binding,
        current_record=current,
        operation_id=operation_id(),
        command=changed,
        lookup_receipt=lambda _: receipt,
    )
    assert conflict.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    assert conflict.stored_success_result is None
