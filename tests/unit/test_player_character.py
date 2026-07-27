from __future__ import annotations

from pydantic import ValidationError
import pytest

from deviation_protocol.domain.player_character import (
    AdultAgePresentation,
    ApplicableCharacterReference,
    AuthorityProvenance,
    AuthoritySourceRef,
    canonical_player_declaration_bytes,
    CanonicalPlayerCharacter,
    CharacterCore,
    ContinuityMetadata,
    ControllerBindingRef,
    CustomValueEntry,
    CustomValues,
    Declaration,
    DeclarationState,
    DistinguishingFeatures,
    ExternalFact,
    ExternalFactAuthority,
    NarrationPreference,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
    PlayerCharacterSubjectRef,
    PlayerDeclaredText,
    PlayerNarrationPreference,
    PlayerSubjectiveAuthority,
    revalidate_player_character_model,
    validate_applicable_character_reference,
    validate_canonical_player_character,
)


def player_text(text: str = "exact player declaration") -> PlayerDeclaredText:
    return PlayerDeclaredText(
        authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
        text=text,
    )


def declared_values() -> dict[str, object]:
    return {
        "name_or_code_name": player_text("Aster"),
        "preferred_form_of_address": player_text("Captain"),
        "adult_identity_and_gender_expression": player_text("ambiguous adult"),
        "broad_adult_age_presentation": AdultAgePresentation(
            adult_only=True,
        ),
        "broad_appearance_direction": player_text("weathered"),
        "distinguishing_features": DistinguishingFeatures(
            features=(player_text("silver glasses"),)
        ),
        "outward_presentation": player_text("calm"),
        "inward_tendency": player_text("cautious"),
        "reality_anchor": player_text("the promise I chose"),
        "custom_values": CustomValues(
            entries=(
                CustomValueEntry(
                    key="loyalty",
                    declaration=Declaration[PlayerDeclaredText].declared(
                        player_text("chosen, not inferred")
                    ),
                ),
                CustomValueEntry(
                    key="future",
                    declaration=Declaration[PlayerDeclaredText].intentionally_undecided(),
                ),
            )
        ),
    }


def canonical_record() -> CanonicalPlayerCharacter:
    character_id = PlayerCharacterId(value="pc.test-1")
    revision = PlayerCharacterRevision(value=1)
    return CanonicalPlayerCharacter(
        contract_version=PlayerCharacterContractVersion.V1,
        player_character_id=character_id,
        record_revision=revision,
        controller_binding=ControllerBindingRef(value="binding.test-1"),
        lifecycle=PlayerCharacterLifecycle.ACTIVE,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        continuity_metadata=ContinuityMetadata(),
        authority_provenance=AuthorityProvenance(
            target_player_character_id=character_id,
            prior_revision=None,
            resulting_revision=revision,
            mutation_kind=PlayerCharacterMutationKind.CREATE,
            authority_class=PlayerCharacterAuthorityClass.TRUSTED_CREATION,
            source_reference=AuthoritySourceRef(value="source.create-1"),
        ),
    )


def test_supported_character_core_slot_inventory_is_exact() -> None:
    assert tuple(CharacterCore.model_fields) == (
        "name_or_code_name",
        "preferred_form_of_address",
        "adult_identity_and_gender_expression",
        "broad_adult_age_presentation",
        "broad_appearance_direction",
        "distinguishing_features",
        "outward_presentation",
        "inward_tendency",
        "reality_anchor",
        "custom_values",
    )
    with pytest.raises(ValidationError):
        CharacterCore.model_validate({"biography": {"state": "omitted"}})


@pytest.mark.parametrize("slot_name", tuple(CharacterCore.model_fields))
@pytest.mark.parametrize(
    "state",
    (
        DeclarationState.OMITTED,
        DeclarationState.EXPLICITLY_ABSENT,
        DeclarationState.INTENTIONALLY_UNDECIDED,
    ),
)
def test_every_character_core_slot_preserves_each_valueless_declaration_state(
    slot_name: str,
    state: DeclarationState,
) -> None:
    core = CharacterCore.model_validate(
        {slot_name: Declaration[object](state=state)}
    )
    declaration = getattr(core, slot_name)
    assert declaration.state is state
    assert declaration.value is None


@pytest.mark.parametrize("slot_name,value", tuple(declared_values().items()))
def test_every_character_core_slot_accepts_only_its_typed_declared_value(
    slot_name: str,
    value: object,
) -> None:
    core = CharacterCore.model_validate(
        {slot_name: Declaration[object].declared(value)}
    )
    declaration = getattr(core, slot_name)
    assert declaration.state is DeclarationState.DECLARED
    assert declaration.value == value


def test_declaration_states_are_pairwise_distinct_and_value_rules_are_strict() -> None:
    declarations = (
        Declaration[PlayerDeclaredText].omitted(),
        Declaration[PlayerDeclaredText].explicitly_absent(),
        Declaration[PlayerDeclaredText].intentionally_undecided(),
        Declaration[PlayerDeclaredText].declared(player_text()),
    )
    assert len(set(declarations)) == 4
    with pytest.raises(ValidationError):
        Declaration[PlayerDeclaredText](
            state=DeclarationState.DECLARED,
            value=None,
        )
    with pytest.raises(ValidationError):
        Declaration[PlayerDeclaredText](
            state=DeclarationState.EXPLICITLY_ABSENT,
            value=player_text(),
        )


def test_adult_age_presentation_requires_explicit_adult_only_proof() -> None:
    with pytest.raises(ValidationError):
        AdultAgePresentation.model_validate(
            {
                "adult_only": False,
            }
        )
    with pytest.raises(ValidationError):
        AdultAgePresentation.model_validate(
            {}
        )
    with pytest.raises(ValidationError):
        AdultAgePresentation.model_validate(
            {
                "adult_only": True,
                "declaration": player_text("minor or unproved presentation"),
            }
        )


def test_narration_preference_has_no_selected_default_and_preserves_undecided() -> None:
    omitted = NarrationPreferences()
    undecided = NarrationPreferences(
        internal_thoughts=Declaration[
            PlayerNarrationPreference
        ].intentionally_undecided()
    )
    balanced = NarrationPreferences(
        internal_thoughts=Declaration[PlayerNarrationPreference].declared(
            PlayerNarrationPreference(
                authority=PlayerSubjectiveAuthority.PLAYER_CONFIRMATION,
                value=NarrationPreference.BALANCED,
            )
        )
    )
    assert omitted.internal_thoughts.state is DeclarationState.OMITTED
    assert omitted.internal_thoughts.value is None
    assert (
        undecided.internal_thoughts.state
        is DeclarationState.INTENTIONALLY_UNDECIDED
    )
    assert undecided != omitted != balanced


def test_subjective_state_accepts_only_player_expression_or_confirmation() -> None:
    for invalid_authority in (
        "server-inference",
        "provider-inference",
        "narration-inference",
        "npc-output",
        "summary",
        "event",
        "consequence",
    ):
        with pytest.raises(ValidationError):
            PlayerDeclaredText.model_validate(
                {"authority": invalid_authority, "text": "settled inner state"}
            )


def test_player_declaration_and_external_fact_authorities_are_not_interchangeable() -> None:
    external = ExternalFact(
        authority=ExternalFactAuthority.AUTHORITATIVE_EVENT,
        fact="the bridge collapsed",
    )
    with pytest.raises(ValidationError):
        Declaration[PlayerDeclaredText].declared(external)
    with pytest.raises(ValidationError):
        ExternalFact.model_validate(player_text("I believe it collapsed"))


def test_player_text_uses_nfc_without_case_or_whitespace_equivalence() -> None:
    composed = player_text("Café")
    decomposed = player_text("Cafe\u0301")
    spaced = player_text("  Café  ")
    assert composed == decomposed
    assert spaced.text == "  Café  "
    assert spaced != composed


def test_identity_domains_remain_distinct_even_for_equal_storage_text() -> None:
    character_id = PlayerCharacterId(value="same.value")
    controller_binding = ControllerBindingRef(value="same.value")
    source = AuthoritySourceRef(value="same.value")
    assert character_id != controller_binding
    assert character_id != source
    assert controller_binding != source


@pytest.mark.parametrize(
    ("reference_type", "prefix"),
    (
        pytest.param(PlayerCharacterId, "Pc", id="player-character-id"),
        pytest.param(ControllerBindingRef, "Binding", id="controller-binding"),
        pytest.param(
            PlayerCharacterOperationId,
            "Operation",
            id="player-character-operation-id",
        ),
        pytest.param(AuthoritySourceRef, "Source", id="authority-source"),
    ),
)
def test_opaque_identifier_types_validate_and_preserve_exact_input(
    reference_type: type[
        PlayerCharacterId
        | ControllerBindingRef
        | PlayerCharacterOperationId
        | AuthoritySourceRef
    ],
    prefix: str,
) -> None:
    with pytest.raises(ValidationError, match="bounded opaque identifier"):
        reference_type(value=f"{prefix}.MiXeD-\u212a")

    exact_identifier = f"{prefix}.MiXeD-K"
    accepted = reference_type(value=exact_identifier)
    assert accepted.value == exact_identifier
    assert accepted.value.encode("utf-8") == exact_identifier.encode("utf-8")

    maximum_identifier = f"K{'a' * 126}Z"
    assert reference_type(value=maximum_identifier).value == maximum_identifier
    for invalid in (
        "",
        f"K{'a' * 127}Z",
        f"{prefix} whitespace",
        f"{prefix}.control\x00",
    ):
        with pytest.raises(ValidationError):
            reference_type(value=invalid)
    with pytest.raises(ValidationError):
        reference_type(value=1)


def test_complete_record_requires_binding_empty_development_and_matching_provenance() -> None:
    record = canonical_record()
    assert record.controller_binding == ControllerBindingRef(value="binding.test-1")
    with pytest.raises(ValidationError):
        CanonicalPlayerCharacter.model_validate(
            {
                **record.model_dump(mode="python"),
                "character_development": ("provider summary",),
            }
        )
    with pytest.raises(ValidationError):
        CanonicalPlayerCharacter.model_validate(
            {
                **record.model_dump(mode="python"),
                "authority_provenance": record.authority_provenance.model_copy(
                    update={
                        "target_player_character_id": PlayerCharacterId(
                            value="pc.other"
                        )
                    }
                ),
            }
        )
    payload = record.model_dump(mode="python")
    payload.pop("controller_binding")
    with pytest.raises(ValidationError):
        CanonicalPlayerCharacter.model_validate(payload)


def test_applicable_reference_and_subject_require_exact_character_identity() -> None:
    record = canonical_record()
    reference = ApplicableCharacterReference(
        player_character_id=record.player_character_id,
        contract_version=record.contract_version,
        record_revision=record.record_revision,
    )
    assert PlayerCharacterSubjectRef(
        player_character_id=record.player_character_id,
        applicable_reference=reference,
    )
    with pytest.raises(ValidationError):
        PlayerCharacterSubjectRef(
            player_character_id=PlayerCharacterId(value="pc.other"),
            applicable_reference=reference,
        )


@pytest.mark.parametrize(
    ("kind", "lifecycle", "authority"),
    (
        (PlayerCharacterMutationKind.RETIRE, PlayerCharacterLifecycle.ACTIVE, PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER),
        (PlayerCharacterMutationKind.RETIRE, PlayerCharacterLifecycle.RETIRED, PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME),
        (PlayerCharacterMutationKind.FINAL_DEATH, PlayerCharacterLifecycle.ACTIVE, PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME),
        (PlayerCharacterMutationKind.FINAL_DEATH, PlayerCharacterLifecycle.DECEASED, PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER),
        (PlayerCharacterMutationKind.REACTIVATE, PlayerCharacterLifecycle.ACTIVE, PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER),
        (PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN, PlayerCharacterLifecycle.ACTIVE, PlayerCharacterAuthorityClass.TRUSTED_CONTINUITY_ADJUDICATION),
    ),
)
def test_complete_record_rejects_impossible_mutation_provenance_matrix(
    kind: PlayerCharacterMutationKind,
    lifecycle: PlayerCharacterLifecycle,
    authority: PlayerCharacterAuthorityClass,
) -> None:
    record = canonical_record()
    revision = PlayerCharacterRevision(value=2)
    with pytest.raises(ValidationError, match="canonical lifecycle|unavailable"):
        record.detached_validated_copy(
            record_revision=revision,
            lifecycle=lifecycle,
            authority_provenance=AuthorityProvenance(
                target_player_character_id=record.player_character_id,
                prior_revision=record.record_revision,
                resulting_revision=revision,
                mutation_kind=kind,
                authority_class=authority,
                source_reference=AuthoritySourceRef(value="source.matrix"),
            ),
        )


def boundary_character_core(text: str) -> CharacterCore:
    return CharacterCore(
        name_or_code_name=Declaration[PlayerDeclaredText].declared(
            player_text(text)
        )
    )


@pytest.mark.parametrize(
    ("text", "expected_canonical_bytes"),
    (
        ("x" * 64_819, 65_535),
        ("x" * 64_820, 65_536),
        (chr(0xE9) * 32_410, 65_536),
        (("e" + chr(0x301)) * 32_410, 65_536),
    ),
    ids=("below", "exact-ascii", "exact-multibyte", "exact-nfc"),
)
def test_fixed_declaration_envelope_boundaries_validate_directly_and_on_reload(
    text: str,
    expected_canonical_bytes: int,
) -> None:
    core = boundary_character_core(text)
    encoded = canonical_player_declaration_bytes(
        character_core=core,
        narration_preferences=NarrationPreferences(),
    )
    assert len(encoded) == expected_canonical_bytes

    record = canonical_record().detached_validated_copy(character_core=core)
    assert validate_canonical_player_character(record) == record
    assert (
        CanonicalPlayerCharacter.model_validate_json(record.model_dump_json())
        == record
    )


def test_declaration_envelope_rejects_fixed_65_537_byte_payload_everywhere() -> None:
    core = boundary_character_core("x" * 64_821)
    with pytest.raises(ValueError, match="declaration"):
        canonical_player_declaration_bytes(
            character_core=core,
            narration_preferences=NarrationPreferences(),
        )
    with pytest.raises(ValidationError, match="declaration"):
        canonical_record().detached_validated_copy(character_core=core)


def test_direct_record_validation_rejects_bypassed_nested_declaration_corruption() -> None:
    record = canonical_record()
    declaration = Declaration[PlayerDeclaredText].declared(player_text("valid"))
    corrupted_text = declaration.value.model_copy(update={"text": None})
    corrupted_core = record.character_core.model_copy(
        update={
            "name_or_code_name": declaration.model_copy(
                update={"value": corrupted_text}
            )
        }
    )
    corrupted_record = record.model_copy(
        update={"character_core": corrupted_core}
    )

    with pytest.raises(ValidationError, match="character_core"):
        CanonicalPlayerCharacter.model_validate(corrupted_record)
    with pytest.raises(ValidationError, match="character_core"):
        validate_canonical_player_character(corrupted_record)


def test_shared_revalidation_inspects_complete_actual_pydantic_state() -> None:
    valid = PlayerCharacterId(value="pc.actual-state")
    assert revalidate_player_character_model(valid, PlayerCharacterId) is valid

    copied_unknown = valid.model_copy(
        update={"unknown_top_level": "caller-injected"}
    )
    with pytest.raises(ValueError, match="unknown instance state"):
        revalidate_player_character_model(copied_unknown, PlayerCharacterId)

    direct_unknown = PlayerCharacterId(value="pc.direct-state")
    object.__setattr__(
        direct_unknown,
        "unknown_direct_attribute",
        "caller-injected",
    )
    with pytest.raises(ValueError, match="unknown instance state"):
        revalidate_player_character_model(direct_unknown, PlayerCharacterId)

    private_unknown = PlayerCharacterId(value="pc.private-state")
    object.__setattr__(
        private_unknown,
        "__pydantic_private__",
        {"caller_private": "caller-injected"},
    )
    with pytest.raises(ValueError, match="unauthorized Pydantic private"):
        revalidate_player_character_model(private_unknown, PlayerCharacterId)

    bookkeeping_unknown = PlayerCharacterId(value="pc.bookkeeping-state")
    object.__setattr__(
        bookkeeping_unknown,
        "__pydantic_fields_set__",
        {"value", "caller_bookkeeping"},
    )
    with pytest.raises(ValueError, match="fields-set"):
        revalidate_player_character_model(
            bookkeeping_unknown,
            PlayerCharacterId,
        )


def test_shared_revalidation_rejects_nested_unknown_and_constructed_malformed_state() -> None:
    reference = ApplicableCharacterReference(
        player_character_id=PlayerCharacterId(value="pc.nested-state"),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=7),
    )
    corrupted_reference = reference.model_copy(
        update={
            "record_revision": reference.record_revision.model_copy(
                update={"unknown_nested": "caller-injected"}
            )
        }
    )
    with pytest.raises(ValueError, match="unknown instance state"):
        validate_applicable_character_reference(corrupted_reference)

    malformed_constructed = PlayerCharacterRevision.model_construct(
        value="not-an-integer",
        unknown_construct_input="ignored-by-pydantic-extra-forbid",
    )
    assert "unknown_construct_input" not in malformed_constructed.__dict__
    with pytest.raises(ValidationError, match="value"):
        revalidate_player_character_model(
            malformed_constructed,
            PlayerCharacterRevision,
        )


def test_player_character_revision_uses_the_complete_signed_64_bit_domain() -> None:
    immediately_below_maximum = PlayerCharacterRevision(
        value=9223372036854775806
    )
    assert immediately_below_maximum.successor() == PlayerCharacterRevision(
        value=9223372036854775807
    )

    maximum = PlayerCharacterRevision(value=9223372036854775807)
    assert not maximum.has_successor
    with pytest.raises(ValueError, match="no signed 64-bit successor"):
        maximum.successor()
    with pytest.raises(ValidationError, match="less than or equal"):
        PlayerCharacterRevision(value=9223372036854775808)
