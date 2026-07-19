from __future__ import annotations

import re
from typing import Annotated, Literal, Protocol, TypeAlias
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative import NarrativeFrame


PROMPT_SCHEMA_VERSION = "narrative-prompt-v1"
PROPOSAL_SCHEMA_VERSION = "narrative-proposal-v1"
MAX_NARRATIVE_TEXT_CHARACTERS = 10_000
MAX_NARRATIVE_USAGE_TOKENS = 2_000_000

_PUBLIC_CONTEXT_INTERNAL_ID_PATTERN = re.compile(
    r"\b(?:frame|scenario|phase|decision|fact|clue|event|seal|capability|npc|"
    r"location|item|skill|clock|resource|currency|attribute|choice)\."
    r"[A-Za-z0-9_.:-]+",
    re.IGNORECASE,
)
_PUBLIC_CONTEXT_INTERNAL_MARKERS = (
    "action_signature",
    "client_request_id",
    "policy_trace",
    "state_version",
    "trustedscenarioeventissuer",
    "trusted_scenario_event_issuer",
    "verifiedscenarioevent",
    "verified_scenario_event",
    "domaineventdraft",
    "domain_event_draft",
    "capability",
    "event_seal",
    "anomaly_evaluation_required",
)

StableNarrativeId: TypeAlias = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
BoundedText: TypeAlias = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=MAX_NARRATIVE_TEXT_CHARACTERS),
]


class NarrativeBoundaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class NarrativePlayerIntent(NarrativeBoundaryModel):
    """Player-authored intent with request, transaction, and authority data removed."""

    action_type: ActionType
    target_ids: Annotated[tuple[StableNarrativeId, ...], Field(max_length=32)] = ()
    tool_ids: Annotated[tuple[StableNarrativeId, ...], Field(max_length=32)] = ()
    description: Annotated[str, Field(strict=True, min_length=1, max_length=150)] | None = None
    dialogue: Annotated[str, Field(strict=True, min_length=1, max_length=200)] | None = None
    selected_choice_id: StableNarrativeId | None = None
    item_instance_id: StableNarrativeId | None = None
    equipment_slot_id: StableNarrativeId | None = None
    skill_definition_id: StableNarrativeId | None = None

    @field_validator("description", "dialogue", mode="before")
    @classmethod
    def normalize_player_text(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()

    @model_validator(mode="after")
    def canonicalize_reference_order(self) -> NarrativePlayerIntent:
        for field_name in ("target_ids", "tool_ids"):
            values = getattr(self, field_name)
            if len(values) != len(set(values)):
                raise ValueError(f"narrative player intent repeats {field_name}")
            object.__setattr__(self, field_name, tuple(sorted(values)))
        return self

    @classmethod
    def from_submission(cls, submission: ActionSubmission) -> NarrativePlayerIntent:
        """Copy only normalized, player-visible semantic fields."""

        return cls(
            action_type=submission.action_type,
            target_ids=tuple(submission.target_ids),
            tool_ids=tuple(submission.tool_ids),
            description=submission.description,
            dialogue=submission.dialogue,
            selected_choice_id=submission.choice_id,
            item_instance_id=submission.item_instance_id,
            equipment_slot_id=submission.equipment_slot_id,
            skill_definition_id=submission.skill_definition_id,
        )


class NarrativeRequest(NarrativeBoundaryModel):
    """Vendor-neutral, player-safe, bounded input to a narrative provider."""

    frame: NarrativeFrame
    player_intent: NarrativePlayerIntent
    player_visible_character_tags: Annotated[
        tuple[StableNarrativeId, ...], Field(max_length=32)
    ] = ()
    recent_narrative_fragments: Annotated[
        tuple[Annotated[str, Field(strict=True, min_length=1, max_length=1_000)], ...],
        Field(max_length=6),
    ] = ()
    public_story_summary: Annotated[
        str, Field(strict=True, max_length=2_000)
    ] = ""
    language: Literal["zh-CN"] = "zh-CN"
    style_profile_id: StableNarrativeId
    prompt_schema_version: Literal["narrative-prompt-v1"] = PROMPT_SCHEMA_VERSION

    @field_validator("frame", mode="before")
    @classmethod
    def detach_frame(cls, value: object) -> object:
        if isinstance(value, NarrativeFrame):
            return NarrativeFrame.model_validate_json(value.model_dump_json())
        return value

    @field_validator("player_intent", mode="before")
    @classmethod
    def detach_player_intent(cls, value: object) -> object:
        if isinstance(value, NarrativePlayerIntent):
            return NarrativePlayerIntent.model_validate_json(value.model_dump_json())
        return value

    @model_validator(mode="after")
    def validate_safe_bounds(self) -> NarrativeRequest:
        frame_json = self.frame.model_dump_json()
        if len(frame_json) > 24_000:
            raise ValueError("narrative frame exceeds the provider serialization limit")
        if self.frame.max_length > MAX_NARRATIVE_TEXT_CHARACTERS:
            raise ValueError("narrative frame exceeds the proposal text limit")
        knowledge_npc_ids = tuple(item.npc_id for item in self.frame.npc_knowledge)
        if len(knowledge_npc_ids) != len(set(knowledge_npc_ids)) or not set(
            knowledge_npc_ids
        ) <= set(self.frame.visible_entities):
            raise ValueError("narrative frame contains non-visible NPC knowledge")
        if len(set(self.player_visible_character_tags)) != len(
            self.player_visible_character_tags
        ):
            raise ValueError("narrative request repeats a character tag")
        object.__setattr__(
            self,
            "player_visible_character_tags",
            tuple(sorted(self.player_visible_character_tags)),
        )
        public_context = (
            *self.recent_narrative_fragments,
            self.public_story_summary,
        )
        for value in public_context:
            folded = value.casefold()
            if _PUBLIC_CONTEXT_INTERNAL_ID_PATTERN.search(value) or any(
                marker in folded for marker in _PUBLIC_CONTEXT_INTERNAL_MARKERS
            ):
                raise ValueError("public narrative context contains an internal reference")
        return self


class NarrativeUsage(NarrativeBoundaryModel):
    input_tokens: Annotated[
        int, Field(strict=True, ge=0, le=MAX_NARRATIVE_USAGE_TOKENS)
    ] | None = None
    output_tokens: Annotated[
        int, Field(strict=True, ge=0, le=MAX_NARRATIVE_USAGE_TOKENS)
    ] | None = None
    total_tokens: Annotated[
        int, Field(strict=True, ge=0, le=MAX_NARRATIVE_USAGE_TOKENS)
    ] | None = None
    cache_hit_input_tokens: Annotated[
        int, Field(strict=True, ge=0, le=MAX_NARRATIVE_USAGE_TOKENS)
    ] | None = None
    cache_miss_input_tokens: Annotated[
        int, Field(strict=True, ge=0, le=MAX_NARRATIVE_USAGE_TOKENS)
    ] | None = None


class NarrativeProviderMetadata(NarrativeBoundaryModel):
    provider: StableNarrativeId
    model: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    request_id: Annotated[str, Field(strict=True, min_length=1, max_length=256)] | None = None
    finish_reason: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    attempts: Annotated[int, Field(strict=True, ge=1, le=8)]
    latency_ms: Annotated[int, Field(strict=True, ge=0, le=3_600_000)]


class NpcUtterance(NarrativeBoundaryModel):
    speaker_entity_id: StableNarrativeId
    text: Annotated[str, Field(strict=True, min_length=1, max_length=500)]


class PerceptibleOutcomeProposal(NarrativeBoundaryModel):
    proposal_type: Literal["PERCEPTIBLE_CHANGE"]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=400)]
    referenced_entity_ids: Annotated[
        tuple[StableNarrativeId, ...], Field(max_length=16)
    ] = ()


class NpcReactionProposal(NarrativeBoundaryModel):
    proposal_type: Literal["NPC_REACTION"]
    npc_entity_id: StableNarrativeId
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=400)]


class ActionAttemptProposal(NarrativeBoundaryModel):
    proposal_type: Literal["ACTION_ATTEMPT_NOTED"]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=400)]


UntrustedOutcomeProposal: TypeAlias = Annotated[
    PerceptibleOutcomeProposal | NpcReactionProposal | ActionAttemptProposal,
    Field(discriminator="proposal_type"),
]


class NarrativeProposalPayload(NarrativeBoundaryModel):
    """Strict model-authored JSON. It has shape, but never authority."""

    schema_version: Literal["narrative-proposal-v1"]
    narrative_text: BoundedText
    referenced_entity_ids: Annotated[
        tuple[StableNarrativeId, ...], Field(max_length=128)
    ] = ()
    npc_utterances: Annotated[tuple[NpcUtterance, ...], Field(max_length=16)] = ()
    untrusted_outcome_proposals: Annotated[
        tuple[UntrustedOutcomeProposal, ...], Field(max_length=16)
    ] = ()
    continuity_notes: Annotated[
        tuple[Annotated[str, Field(strict=True, min_length=1, max_length=240)], ...],
        Field(max_length=8),
    ] = ()

    @model_validator(mode="after")
    def reject_duplicate_references(self) -> NarrativeProposalPayload:
        if len(set(self.referenced_entity_ids)) != len(self.referenced_entity_ids):
            raise ValueError("narrative proposal repeats an entity reference")
        speakers = tuple(item.speaker_entity_id for item in self.npc_utterances)
        if len(set(speakers)) != len(speakers):
            raise ValueError("narrative proposal repeats an NPC speaker")
        return self


class UntrustedNarrativeProposal(NarrativeBoundaryModel):
    proposal: NarrativeProposalPayload
    provider_metadata: NarrativeProviderMetadata
    usage: NarrativeUsage = NarrativeUsage()


class ValidatedNarrativeProposal(NarrativeBoundaryModel):
    """Structurally and contextually safe prose candidate, not a scenario event."""

    proposal: NarrativeProposalPayload
    provider_metadata: NarrativeProviderMetadata
    usage: NarrativeUsage = NarrativeUsage()


class NarrativeProvider(Protocol):
    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal: ...

    async def aclose(self) -> None: ...


class NarrativeBoundaryError(RuntimeError):
    """Stable failure whose string representation never includes untrusted details."""

    code = "NARRATIVE_BOUNDARY_ERROR"
    public_message = "Narrative processing failed."

    def __init__(self) -> None:
        super().__init__(self.code)


class NarrativeRequestRejectedError(NarrativeBoundaryError):
    code = "NARRATIVE_REQUEST_REJECTED"
    public_message = "Narrative request was rejected."


class NarrativeProviderRequestError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_REQUEST_INVALID"


class NarrativeProviderAuthenticationError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_AUTHENTICATION_FAILED"


class NarrativeProviderBalanceError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_BALANCE_INSUFFICIENT"


class NarrativeProviderRateLimitError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_RATE_LIMITED"


class NarrativeProviderUnavailableError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_UNAVAILABLE"


class NarrativeProviderResponseError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_RESPONSE_INVALID"


class NarrativeProviderTruncatedError(NarrativeBoundaryError):
    code = "NARRATIVE_PROVIDER_RESPONSE_TRUNCATED"


class NarrativeProposalRejectedError(NarrativeBoundaryError):
    code = "NARRATIVE_PROPOSAL_REJECTED"


class NarrativePublicReferences(NarrativeBoundaryModel):
    """Authoritative allowlists and known-sensitive identifiers for validation."""

    allowed_public_entity_ids: Annotated[
        frozenset[StableNarrativeId], Field(max_length=256)
    ] = frozenset()
    visible_runtime_npc_ids: Annotated[
        frozenset[StableNarrativeId], Field(max_length=128)
    ] = frozenset()
    player_owned_item_ids: Annotated[
        frozenset[StableNarrativeId], Field(max_length=256)
    ] = frozenset()
    forbidden_identifiers: Annotated[
        frozenset[StableNarrativeId], Field(max_length=512)
    ] = frozenset()

    @model_validator(mode="after")
    def validate_reference_sets(self) -> NarrativePublicReferences:
        if not self.visible_runtime_npc_ids <= self.allowed_public_entity_ids:
            raise ValueError("visible NPC references must be public entities")
        if not self.player_owned_item_ids <= self.allowed_public_entity_ids:
            raise ValueError("owned item references must be public entities")
        if self.allowed_public_entity_ids & self.forbidden_identifiers:
            raise ValueError("public and forbidden reference sets overlap")
        return self
