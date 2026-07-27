from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, StrEnum
import json
import re
from typing import Annotated, Any, Generic, Literal, TypeVar
import unicodedata

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


STRUCTURED_PLAYER_CHARACTER_CONTRACT_VERSION = "structured-player-character/v1"
MAX_PLAYER_DECLARATION_CANONICAL_BYTES = 65_536
MAX_CANONICAL_INTEGER = 2**63 - 1
MIN_CANONICAL_INTEGER = -(2**63)

_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_T = TypeVar("_T")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _normalize_exact_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if not normalized or "\x00" in normalized:
        raise ValueError("declared text must be non-empty and contain no NUL")
    try:
        normalized.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("declared text must be valid Unicode") from None
    return normalized


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


def revalidate_player_character_model(
    value: _ModelT,
    model_type: type[_ModelT],
) -> _ModelT:
    """Validate the complete actual instance state at a trust boundary."""

    if type(value) is not model_type:
        raise TypeError(f"expected {model_type.__name__}")
    _validate_actual_pydantic_state(
        value,
        path=model_type.__name__,
        visited=set(),
    )
    validated = model_type.model_validate(value)
    if validated != value:
        raise ValueError(
            f"{model_type.__name__} source state is not already canonical"
        )
    return value


def _validate_actual_pydantic_state(
    value: BaseModel,
    *,
    path: str,
    visited: set[int],
) -> None:
    identity = id(value)
    if identity in visited:
        return
    visited.add(identity)

    model_type = type(value)
    fields = set(model_type.model_fields)
    state = value.__dict__
    state_fields = set(state)
    missing = fields - state_fields
    unknown = state_fields - fields
    if missing:
        raise ValueError(
            f"{path} is missing required instance state: {sorted(missing)!r}"
        )
    if unknown:
        raise ValueError(
            f"{path} contains unknown instance state: {sorted(unknown)!r}"
        )

    extra_state = getattr(value, "__pydantic_extra__", None)
    if extra_state is not None:
        if not isinstance(extra_state, Mapping):
            raise ValueError(f"{path} has malformed Pydantic extra state")
        if extra_state:
            raise ValueError(
                f"{path} contains unauthorized Pydantic extra state: "
                f"{sorted(extra_state)!r}"
            )

    private_state = getattr(value, "__pydantic_private__", None)
    declared_private = set(getattr(model_type, "__private_attributes__", {}))
    if private_state is not None:
        if not isinstance(private_state, Mapping):
            raise ValueError(f"{path} has malformed Pydantic private state")
        unauthorized_private = set(private_state) - declared_private
        if unauthorized_private:
            raise ValueError(
                f"{path} contains unauthorized Pydantic private state: "
                f"{sorted(unauthorized_private)!r}"
            )

    fields_set = getattr(value, "__pydantic_fields_set__", None)
    if type(fields_set) is not set or not fields_set <= fields:
        raise ValueError(f"{path} contains invalid Pydantic fields-set state")

    for field_name in fields:
        _validate_nested_pydantic_state(
            state[field_name],
            path=f"{path}.{field_name}",
            visited=visited,
        )


def _validate_nested_pydantic_state(
    value: Any,
    *,
    path: str,
    visited: set[int],
) -> None:
    if isinstance(value, BaseModel):
        _validate_actual_pydantic_state(value, path=path, visited=visited)
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _validate_nested_pydantic_state(
                key,
                path=f"{path}.<key>",
                visited=visited,
            )
            _validate_nested_pydantic_state(
                nested,
                path=f"{path}[{key!r}]",
                visited=visited,
            )
        return
    if isinstance(value, (list, tuple, set, frozenset)):
        for index, nested in enumerate(value):
            _validate_nested_pydantic_state(
                nested,
                path=f"{path}[{index}]",
                visited=visited,
            )


def canonical_character_operation_bytes(value: Any) -> bytes:
    """Serialize the Phase 1 value algebra deterministically."""

    normalized = _canonical_value(value, path="$")
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_value(value: Any, *, path: str) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not MIN_CANONICAL_INTEGER <= value <= MAX_CANONICAL_INTEGER:
            raise ValueError(f"{path} integer is outside the signed 64-bit range")
        return value
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        try:
            normalized.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError(f"{path} contains invalid Unicode") from None
        return normalized
    if isinstance(value, Enum):
        return _canonical_value(value.value, path=path)
    if isinstance(value, BaseModel):
        validated = revalidate_player_character_model(value, type(value))
        return _canonical_value(
            validated.model_dump(mode="python", warnings="none"),
            path=path,
        )
    if isinstance(value, Mapping):
        normalized_items: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            try:
                normalized_key.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError(f"{path} contains an invalid Unicode key") from None
            if normalized_key in normalized_items:
                raise ValueError(f"{path} contains object keys that collide after NFC normalization")
            normalized_items[normalized_key] = _canonical_value(nested, path=f"{path}.{normalized_key}")
        return {key: normalized_items[key] for key in sorted(normalized_items)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    raise TypeError(f"{path} contains unsupported canonical value {type(value).__name__}")


class _OpaqueReference(_StrictFrozenModel):
    value: str = Field(strict=True, min_length=1, max_length=128)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        if not _OPAQUE_REF.fullmatch(normalized):
            raise ValueError("reference must be a bounded opaque identifier")
        return normalized

    def __str__(self) -> str:
        return self.value


class PlayerCharacterId(_OpaqueReference):
    """Permanent identity in the player-character domain."""


class ControllerBindingRef(_OpaqueReference):
    """Private authority reference, distinct from a principal or character ID."""


class PlayerCharacterOperationId(_OpaqueReference):
    """Opaque idempotency key; never an identity, authority, or capability."""


class AuthoritySourceRef(_OpaqueReference):
    """Opaque trusted provenance/evidence reference."""


class PlayerCharacterContractVersion(StrEnum):
    V1 = STRUCTURED_PLAYER_CHARACTER_CONTRACT_VERSION


class PlayerCharacterRevision(_StrictFrozenModel):
    value: int = Field(strict=True, ge=1, le=MAX_CANONICAL_INTEGER)

    @property
    def has_successor(self) -> bool:
        return self.value < MAX_CANONICAL_INTEGER

    def successor(self) -> PlayerCharacterRevision:
        if not self.has_successor:
            raise ValueError(
                "player-character revision has no signed 64-bit successor"
            )
        return PlayerCharacterRevision(value=self.value + 1)


class PlayerCharacterLifecycle(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"
    DECEASED = "deceased"


class DeclarationState(StrEnum):
    OMITTED = "omitted"
    EXPLICITLY_ABSENT = "explicitly-absent"
    DECLARED = "declared"
    INTENTIONALLY_UNDECIDED = "intentionally-undecided"


class Declaration(_StrictFrozenModel, Generic[_T]):
    """Lossless logical state for one approved optional declaration slot."""

    state: DeclarationState
    value: _T | None = None

    @model_validator(mode="after")
    def validate_state(self) -> Declaration[_T]:
        if self.state is DeclarationState.DECLARED:
            if self.value is None:
                raise ValueError("a declared slot requires a value")
        elif self.value is not None:
            raise ValueError("only a declared slot may carry a value")
        return self

    @classmethod
    def omitted(cls) -> Declaration[_T]:
        return cls(state=DeclarationState.OMITTED)

    @classmethod
    def explicitly_absent(cls) -> Declaration[_T]:
        return cls(state=DeclarationState.EXPLICITLY_ABSENT)

    @classmethod
    def declared(cls, value: _T) -> Declaration[_T]:
        return cls(state=DeclarationState.DECLARED, value=value)

    @classmethod
    def intentionally_undecided(cls) -> Declaration[_T]:
        return cls(state=DeclarationState.INTENTIONALLY_UNDECIDED)


class PlayerSubjectiveAuthority(StrEnum):
    PLAYER_EXPRESSION = "player-expression"
    PLAYER_CONFIRMATION = "player-confirmation"


class ExternalFactAuthority(StrEnum):
    TRUSTED_SERVER_RULE = "trusted-server-rule"
    AUTHORITATIVE_EVENT = "authoritative-event"
    SCENARIO_ADJUDICATION = "scenario-adjudication"


class PlayerDeclaredText(_StrictFrozenModel):
    """Player-authored value; server/Provider inference is not an admitted source."""

    authority: PlayerSubjectiveAuthority
    text: str = Field(strict=True, min_length=1)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalize_exact_text(value)


class ExternalFact(_StrictFrozenModel):
    """Externally grounded fact, deliberately incompatible with player declarations."""

    authority: ExternalFactAuthority
    fact: str = Field(strict=True, min_length=1)

    @field_validator("fact")
    @classmethod
    def normalize_fact(cls, value: str) -> str:
        return _normalize_exact_text(value)


class AdultAgePresentation(_StrictFrozenModel):
    """Vocabulary-neutral presentation whose only admitted meaning is adult."""

    adult_only: Literal[True]


class DistinguishingFeatures(_StrictFrozenModel):
    features: tuple[PlayerDeclaredText, ...]

    @model_validator(mode="after")
    def reject_duplicates(self) -> DistinguishingFeatures:
        canonical = tuple(
            (item.authority.value, item.text) for item in self.features
        )
        if len(canonical) != len(set(canonical)):
            raise ValueError("distinguishing features must not contain duplicates")
        return self


class CustomValueEntry(_StrictFrozenModel):
    key: str = Field(strict=True, min_length=1)
    declaration: Declaration[PlayerDeclaredText]

    @field_validator("key")
    @classmethod
    def normalize_key(cls, value: str) -> str:
        return _normalize_exact_text(value)


class CustomValues(_StrictFrozenModel):
    entries: tuple[CustomValueEntry, ...]

    @model_validator(mode="after")
    def reject_duplicate_keys(self) -> CustomValues:
        keys = tuple(item.key for item in self.entries)
        if len(keys) != len(set(keys)):
            raise ValueError("custom value keys must be unique")
        return self


class NarrationPreference(StrEnum):
    HIGH_IMMERSION = "high-immersion"
    BALANCED = "balanced"
    HIGH_AGENCY = "high-agency"


class PlayerNarrationPreference(_StrictFrozenModel):
    authority: PlayerSubjectiveAuthority
    value: NarrationPreference


class CharacterCore(_StrictFrozenModel):
    name_or_code_name: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    preferred_form_of_address: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    adult_identity_and_gender_expression: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    broad_adult_age_presentation: Declaration[AdultAgePresentation] = Field(
        default_factory=Declaration[AdultAgePresentation].omitted
    )
    broad_appearance_direction: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    distinguishing_features: Declaration[DistinguishingFeatures] = Field(
        default_factory=Declaration[DistinguishingFeatures].omitted
    )
    outward_presentation: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    inward_tendency: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    reality_anchor: Declaration[PlayerDeclaredText] = Field(
        default_factory=Declaration[PlayerDeclaredText].omitted
    )
    custom_values: Declaration[CustomValues] = Field(
        default_factory=Declaration[CustomValues].omitted
    )


class NarrationPreferences(_StrictFrozenModel):
    internal_thoughts: Declaration[PlayerNarrationPreference] = Field(
        default_factory=Declaration[PlayerNarrationPreference].omitted
    )


class ContinuityMetadata(_StrictFrozenModel):
    """Phase 1 represents no unowned Run/story-line binding."""

    current_story_line_reference: None = None


class PlayerCharacterMutationKind(StrEnum):
    CREATE = "CREATE"
    RETIRE = "RETIRE"
    REACTIVATE = "REACTIVATE"
    FINAL_DEATH = "FINAL_DEATH"
    AUTHORIZED_CONTINUITY_RETURN = "AUTHORIZED_CONTINUITY_RETURN"


class PlayerCharacterAuthorityClass(StrEnum):
    TRUSTED_CREATION = "trusted-creation"
    AUTHENTICATED_CONTROLLER = "authenticated-controller"
    TRUSTED_SERVER_OUTCOME = "trusted-server-outcome"
    TRUSTED_CONTINUITY_ADJUDICATION = "trusted-continuity-adjudication"


class AuthorityProvenance(_StrictFrozenModel):
    target_player_character_id: PlayerCharacterId
    prior_revision: PlayerCharacterRevision | None
    resulting_revision: PlayerCharacterRevision
    mutation_kind: PlayerCharacterMutationKind
    authority_class: PlayerCharacterAuthorityClass
    source_reference: AuthoritySourceRef

    @model_validator(mode="after")
    def validate_revision_transition(self) -> AuthorityProvenance:
        if self.mutation_kind is PlayerCharacterMutationKind.CREATE:
            if self.prior_revision is not None or self.resulting_revision.value != 1:
                raise ValueError("creation provenance must establish revision one")
        elif (
            self.prior_revision is None
            or self.resulting_revision.value != self.prior_revision.value + 1
        ):
            raise ValueError("mutation provenance must advance exactly one revision")
        return self


class ApplicableCharacterReference(_StrictFrozenModel):
    player_character_id: PlayerCharacterId
    contract_version: PlayerCharacterContractVersion
    record_revision: PlayerCharacterRevision


class CanonicalPlayerCharacter(_StrictFrozenModel):
    contract_version: PlayerCharacterContractVersion
    player_character_id: PlayerCharacterId
    record_revision: PlayerCharacterRevision
    controller_binding: ControllerBindingRef
    lifecycle: PlayerCharacterLifecycle
    character_core: CharacterCore
    narration_preferences: NarrationPreferences
    character_development: tuple[()] = ()
    continuity_metadata: ContinuityMetadata
    authority_provenance: AuthorityProvenance

    @model_validator(mode="after")
    def validate_complete_record(self) -> CanonicalPlayerCharacter:
        provenance = self.authority_provenance
        if (
            provenance.target_player_character_id != self.player_character_id
            or provenance.resulting_revision != self.record_revision
        ):
            raise ValueError("authority provenance must bind the current record")
        _validate_declaration_envelope(
            character_core=self.character_core,
            narration_preferences=self.narration_preferences,
        )
        expected = {
            PlayerCharacterMutationKind.CREATE: (
                1,
                None,
                PlayerCharacterLifecycle.ACTIVE,
                PlayerCharacterAuthorityClass.TRUSTED_CREATION,
            ),
            PlayerCharacterMutationKind.RETIRE: (
                None,
                "advance",
                PlayerCharacterLifecycle.RETIRED,
                PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER,
            ),
            PlayerCharacterMutationKind.FINAL_DEATH: (
                None,
                "advance",
                PlayerCharacterLifecycle.DECEASED,
                PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME,
            ),
        }.get(provenance.mutation_kind)
        if expected is None:
            raise ValueError("unavailable mutation kind cannot describe a canonical record")
        revision, prior, lifecycle, authority = expected
        if (
            self.lifecycle is not lifecycle
            or provenance.authority_class is not authority
            or (revision is not None and self.record_revision.value != revision)
            or (prior == "advance" and provenance.prior_revision is None)
        ):
            raise ValueError("authority provenance does not match canonical lifecycle")
        return self

    def detached_validated_copy(self, **updates: Any) -> CanonicalPlayerCharacter:
        source = revalidate_player_character_model(
            self,
            CanonicalPlayerCharacter,
        )
        payload = source.model_dump(mode="python")
        payload.update(updates)
        return CanonicalPlayerCharacter.model_validate(payload)


def validate_canonical_player_character(
    value: CanonicalPlayerCharacter,
) -> CanonicalPlayerCharacter:
    return revalidate_player_character_model(value, CanonicalPlayerCharacter)


def canonical_player_declaration_bytes(
    *,
    character_core: CharacterCore,
    narration_preferences: NarrationPreferences,
) -> bytes:
    validated_core = revalidate_player_character_model(character_core, CharacterCore)
    validated_preferences = revalidate_player_character_model(
        narration_preferences,
        NarrationPreferences,
    )
    encoded = canonical_character_operation_bytes(
        {
            "character_core": validated_core,
            "narration_preferences": validated_preferences,
        }
    )
    if len(encoded) > MAX_PLAYER_DECLARATION_CANONICAL_BYTES:
        raise ValueError(
            "canonical player declaration exceeds the Phase 1 byte envelope"
        )
    return encoded


def _validate_declaration_envelope(
    *,
    character_core: CharacterCore,
    narration_preferences: NarrationPreferences,
) -> None:
    canonical_player_declaration_bytes(
        character_core=character_core,
        narration_preferences=narration_preferences,
    )


def validate_applicable_character_reference(
    value: ApplicableCharacterReference,
) -> ApplicableCharacterReference:
    return revalidate_player_character_model(value, ApplicableCharacterReference)


class PlayerCharacterSubjectRef(_StrictFrozenModel):
    player_character_id: PlayerCharacterId
    applicable_reference: ApplicableCharacterReference | None = None

    @model_validator(mode="after")
    def validate_reference_identity(self) -> PlayerCharacterSubjectRef:
        if (
            self.applicable_reference is not None
            and self.applicable_reference.player_character_id
            != self.player_character_id
        ):
            raise ValueError("subject and applicable reference identities must match")
        return self
