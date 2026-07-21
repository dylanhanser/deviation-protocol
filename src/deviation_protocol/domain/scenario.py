from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.content import (
    ContentCatalog,
    ContentDefinitionError,
    DefinitionId,
)
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.facts import FactKind, FactVisibility
from deviation_protocol.domain.json_values import (
    canonical_json_key,
    freeze_bounded_json_value,
    json_values_equal,
)
from deviation_protocol.domain.narrative_outcome import (
    NarrativeFactEffect,
    NarrativeOutcomeRuleDefinition,
)
from deviation_protocol.domain.memory_rules import (
    MemoryRuleDefinition,
    MemoryRuleOperation,
    MemoryRuleSourceEventType,
)
from deviation_protocol.domain.player_memory import SignificantExperienceCategory


MAX_SCENARIOS_PER_CATALOG = 32
MAX_PHASES_PER_SCENARIO = 64
MAX_LOCATIONS_PER_SCENARIO = 128
MAX_NPCS_PER_SCENARIO = 128
MAX_FACTS_PER_SCENARIO = 256
MAX_CLUES_PER_SCENARIO = 512
MAX_CLUE_GROUPS_PER_SCENARIO = 128
MAX_CLOCKS_PER_SCENARIO = 32
MAX_DECISIONS_PER_SCENARIO = 256
MAX_ENDINGS_PER_SCENARIO = 64
MAX_SCENARIO_PAYLOAD_DEPTH = 32
MAX_SCENARIO_PAYLOAD_NODES = 50_000
MAX_SCENARIO_COLLECTION_ITEMS = 512
MAX_SCENARIO_STRING_LENGTH = 4_000
MAX_SCENARIO_COUNTER = 1_000_000
MAX_AUTO_BEATS = 10_000
MAX_NARRATIVE_LENGTH = 10_000
SUPPORTED_SCENARIO_SCHEMA_VERSION = 1
StrictBool = Annotated[bool, Field(strict=True)]


class ScenarioDefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TransitionTrigger(StrEnum):
    AUTOMATIC = "AUTOMATIC"
    VERIFIED_EVENT = "VERIFIED_EVENT"
    DECISION = "DECISION"


class DecisionReason(StrEnum):
    IRREVERSIBLE_CONSEQUENCE = "IRREVERSIBLE_CONSEQUENCE"
    RESOURCE_COMMITMENT = "RESOURCE_COMMITMENT"
    ROUTE_DIVERGENCE = "ROUTE_DIVERGENCE"
    NPC_COMMITMENT = "NPC_COMMITMENT"
    CORE_REVELATION = "CORE_REVELATION"
    TIME_CRITICAL = "TIME_CRITICAL"
    MORAL_CONFLICT = "MORAL_CONFLICT"
    PLAYER_DIRECT_RESPONSE = "PLAYER_DIRECT_RESPONSE"


class FrameMode(StrEnum):
    FLOW = "FLOW"
    DECISION = "DECISION"
    RAPID_DECISION = "RAPID_DECISION"
    SETTLEMENT = "SETTLEMENT"


class EndingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class AlwaysCondition(ScenarioDefinitionModel):
    rule_type: Literal["ALWAYS"]


class PhaseBeatAtLeastCondition(ScenarioDefinitionModel):
    rule_type: Literal["PHASE_BEAT_AT_LEAST"]
    value: Annotated[int, Field(strict=True, ge=0, le=MAX_AUTO_BEATS)]


class FactEqualsCondition(ScenarioDefinitionModel):
    rule_type: Literal["FACT_EQUALS"]
    fact_id: DefinitionId
    value: Any

    @field_validator("value")
    @classmethod
    def validate_json_value(cls, value: Any) -> Any:
        return freeze_bounded_json_value(value, path="fact condition value")


class ClueGroupCompleteCondition(ScenarioDefinitionModel):
    rule_type: Literal["CLUE_GROUP_COMPLETE"]
    clue_group_id: DefinitionId


class ClockAtLeastCondition(ScenarioDefinitionModel):
    rule_type: Literal["CLOCK_AT_LEAST"]
    clock_id: DefinitionId
    value: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)]


class ClockAtMostCondition(ScenarioDefinitionModel):
    rule_type: Literal["CLOCK_AT_MOST"]
    clock_id: DefinitionId
    value: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)]


class LocationOpenedCondition(ScenarioDefinitionModel):
    rule_type: Literal["LOCATION_OPENED"]
    location_id: DefinitionId


class DecisionsAtLeastCondition(ScenarioDefinitionModel):
    rule_type: Literal["DECISIONS_AT_LEAST"]
    value: Annotated[int, Field(strict=True, ge=0, le=MAX_DECISIONS_PER_SCENARIO)]


class EventOccurredCondition(ScenarioDefinitionModel):
    rule_type: Literal["EVENT_OCCURRED"]
    event_type: DefinitionId


class PhaseVisitAtLeastCondition(ScenarioDefinitionModel):
    rule_type: Literal["PHASE_VISIT_AT_LEAST"]
    phase_id: DefinitionId
    value: Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)]


class NpcAliveAcknowledgedCondition(ScenarioDefinitionModel):
    rule_type: Literal["NPC_ALIVE_ACKNOWLEDGED"]
    minimum_count: Annotated[int, Field(strict=True, ge=1, le=MAX_NPCS_PER_SCENARIO)] = 1


ConditionDefinition: TypeAlias = Annotated[
    AlwaysCondition
    | PhaseBeatAtLeastCondition
    | FactEqualsCondition
    | ClueGroupCompleteCondition
    | ClockAtLeastCondition
    | ClockAtMostCondition
    | LocationOpenedCondition
    | DecisionsAtLeastCondition
    | EventOccurredCondition
    | PhaseVisitAtLeastCondition
    | NpcAliveAcknowledgedCondition,
    Field(discriminator="rule_type"),
]


class MutableFactTransition(ScenarioDefinitionModel):
    from_value: Any
    to_value: Any
    event_type: DefinitionId

    @field_validator("from_value", "to_value")
    @classmethod
    def validate_json_values(cls, value: Any) -> Any:
        return freeze_bounded_json_value(value, path="mutable fact transition")


class FactDefinition(ScenarioDefinitionModel):
    fact_id: DefinitionId
    kind: FactKind
    visibility: FactVisibility = FactVisibility.HIDDEN
    value: Any = None
    deferred_candidates: tuple[Any, ...] = ()
    mutable_transitions: tuple[MutableFactTransition, ...] = ()

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Any) -> Any:
        return freeze_bounded_json_value(value, path="fact value")

    @field_validator("deferred_candidates")
    @classmethod
    def validate_candidates(cls, values: tuple[Any, ...]) -> tuple[Any, ...]:
        return tuple(
            freeze_bounded_json_value(value, path="deferred candidate") for value in values
        )

    @model_validator(mode="after")
    def validate_kind_shape(self) -> FactDefinition:
        if self.kind is FactKind.FIXED:
            if self.value is None or self.deferred_candidates or self.mutable_transitions:
                raise ValueError("FIXED fact requires value and cannot declare candidates/transitions")
        elif self.kind is FactKind.DEFERRED:
            if self.value is not None or not self.deferred_candidates or self.mutable_transitions:
                raise ValueError("DEFERRED fact requires candidates and no initial value")
            frozen = tuple(canonical_json_key(item) for item in self.deferred_candidates)
            _reject_duplicates(frozen, f"fact {self.fact_id!r} deferred candidate")
        elif self.kind is FactKind.MUTABLE:
            if self.value is None or self.deferred_candidates or not self.mutable_transitions:
                raise ValueError("MUTABLE fact requires initial value and transitions")
            _reject_duplicates(
                (
                    canonical_json_key(
                        [item.from_value, item.to_value, item.event_type]
                    )
                    for item in self.mutable_transitions
                ),
                f"fact {self.fact_id!r} mutable transition",
            )
        elif self.kind is FactKind.DYNAMIC:
            raise ValueError("DYNAMIC facts are runtime-only and cannot be predeclared")
        return self


class LocationDefinition(ScenarioDefinitionModel):
    location_id: DefinitionId
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=300)]
    initially_open: StrictBool = False
    visible_entity_ids: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_entities(self) -> LocationDefinition:
        _reject_duplicates(
            self.visible_entity_ids, f"location {self.location_id!r} entity"
        )
        return self


class ScenarioNpcReference(ScenarioDefinitionModel):
    npc_definition_id: DefinitionId
    known_fact_ids: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_known_facts(self) -> ScenarioNpcReference:
        _reject_duplicates(
            self.known_fact_ids,
            f"NPC {self.npc_definition_id!r} known fact",
        )
        return self


class ClueDefinition(ScenarioDefinitionModel):
    clue_id: DefinitionId
    supports_fact_ids: tuple[DefinitionId, ...]
    source_event_types: tuple[DefinitionId, ...]
    allowed_phase_ids: tuple[DefinitionId, ...]
    required_any_profession_tags: tuple[DefinitionId, ...] = ()
    visible_summary: Annotated[str, Field(strict=True, min_length=1, max_length=240)]

    @model_validator(mode="after")
    def validate_non_empty(self) -> ClueDefinition:
        if not self.supports_fact_ids or not self.source_event_types or not self.allowed_phase_ids:
            raise ValueError("clue fact, event, and phase references cannot be empty")
        for label, values in (
            ("fact", self.supports_fact_ids),
            ("source event", self.source_event_types),
            ("phase", self.allowed_phase_ids),
            ("profession tag", self.required_any_profession_tags),
        ):
            _reject_duplicates(values, f"clue {self.clue_id!r} {label}")
        return self


class ClueGroupDefinition(ScenarioDefinitionModel):
    clue_group_id: DefinitionId
    clue_ids: tuple[DefinitionId, ...]
    required_count: Annotated[int, Field(strict=True, ge=1)]
    completion_event_type: DefinitionId

    @model_validator(mode="after")
    def validate_threshold(self) -> ClueGroupDefinition:
        _reject_duplicates(self.clue_ids, f"clue group {self.clue_group_id!r} clue")
        if self.required_count > len(self.clue_ids):
            raise ValueError("clue group threshold exceeds available clues")
        return self


class ClockThresholdDefinition(ScenarioDefinitionModel):
    threshold: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)]
    event_type: DefinitionId


class ThreatClockDefinition(ScenarioDefinitionModel):
    clock_id: DefinitionId
    minimum: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)] = 0
    maximum: Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)]
    initial: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)] = 0
    player_visible: StrictBool = False
    thresholds: tuple[ClockThresholdDefinition, ...] = ()

    @model_validator(mode="after")
    def validate_bounds(self) -> ThreatClockDefinition:
        if self.minimum >= self.maximum:
            raise ValueError("clock minimum must be less than maximum")
        if not self.minimum <= self.initial <= self.maximum:
            raise ValueError("clock initial value is outside its bounds")
        values = tuple(item.threshold for item in self.thresholds)
        if len(values) > 64:
            raise ValueError("clock threshold count exceeds limit 64")
        _reject_duplicates((str(value) for value in values), f"clock {self.clock_id!r} threshold")
        if any(value < self.minimum or value > self.maximum for value in values):
            raise ValueError("clock threshold is outside its bounds")
        return self


class ClockAdvanceDefinition(ScenarioDefinitionModel):
    clock_id: DefinitionId
    amount: Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)]


class ActionTimeCostDefinition(ScenarioDefinitionModel):
    action_type: DefinitionId
    clock_advances: tuple[ClockAdvanceDefinition, ...] = ()


class SuggestedActionDefinition(ScenarioDefinitionModel):
    action_id: DefinitionId
    action_type: DefinitionId
    label_hint: Annotated[str, Field(strict=True, min_length=1, max_length=160)]
    target_ids: tuple[DefinitionId, ...] = ()
    required_any_profession_tags: tuple[DefinitionId, ...] = ()
    server_event_type: DefinitionId | None = None
    mutable_fact_updates: tuple[NarrativeFactEffect, ...] = ()
    opened_location_ids: tuple[DefinitionId, ...] = ()
    new_location_id: DefinitionId | None = None
    server_narrative_text: Annotated[
        str, Field(strict=True, min_length=1, max_length=1000)
    ] | None = None

    @model_validator(mode="after")
    def validate_server_effect(self) -> SuggestedActionDefinition:
        fact_ids = tuple(item.fact_id for item in self.mutable_fact_updates)
        _reject_duplicates(fact_ids, f"action {self.action_id!r} mutable fact")
        _reject_duplicates(
            self.opened_location_ids, f"action {self.action_id!r} opened location"
        )
        if (
            self.mutable_fact_updates
            or self.opened_location_ids
            or self.new_location_id is not None
        ) and self.server_event_type is None:
            raise ValueError("decision world updates require a server event type")
        if self.server_narrative_text is not None and self.server_event_type is None:
            raise ValueError("decision server narrative requires a server event type")
        return self


class CustomActionConstraints(ScenarioDefinitionModel):
    allowed_action_types: tuple[DefinitionId, ...]
    max_description_length: Annotated[int, Field(strict=True, ge=1, le=2000)] = 500
    must_target_visible_entity: StrictBool = True

    @model_validator(mode="after")
    def validate_action_types(self) -> CustomActionConstraints:
        if not self.allowed_action_types:
            raise ValueError("custom action constraints require an allowed action type")
        _reject_duplicates(self.allowed_action_types, "custom action type")
        return self


class DecisionWindowDefinition(ScenarioDefinitionModel):
    decision_id: DefinitionId
    reason: DecisionReason
    earliest_beat: Annotated[int, Field(strict=True, ge=0, le=MAX_AUTO_BEATS)]
    latest_beat: Annotated[int, Field(strict=True, ge=0, le=MAX_AUTO_BEATS)]
    conditions: tuple[ConditionDefinition, ...] = ()
    suggested_actions: tuple[SuggestedActionDefinition, ...]
    custom_action_constraints: CustomActionConstraints
    once: StrictBool = True

    @model_validator(mode="after")
    def validate_window(self) -> DecisionWindowDefinition:
        if self.latest_beat < self.earliest_beat:
            raise ValueError("decision latest_beat cannot precede earliest_beat")
        if not self.suggested_actions:
            raise ValueError("decision window requires at least one suggested action")
        if len(self.suggested_actions) > 32:
            raise ValueError("decision window suggested action count exceeds limit 32")
        if not any(
            not action.required_any_profession_tags
            for action in self.suggested_actions
        ):
            raise ValueError("decision window requires a profession-independent action")
        _reject_duplicates(
            (item.action_id for item in self.suggested_actions),
            f"decision {self.decision_id!r} action",
        )
        for action in self.suggested_actions:
            _reject_duplicates(
                action.target_ids,
                f"action {action.action_id!r} target",
            )
        return self


class TransitionDefinition(ScenarioDefinitionModel):
    transition_id: DefinitionId
    target_phase_id: DefinitionId
    trigger: TransitionTrigger
    conditions: tuple[ConditionDefinition, ...] = ()
    priority: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)] = 100
    max_uses: Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)] | None = None


class ScenePhaseDefinition(ScenarioDefinitionModel):
    phase_id: DefinitionId
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    entry_conditions: tuple[ConditionDefinition, ...] = ()
    must_render_fact_ids: tuple[DefinitionId, ...] = ()
    required_event_types: tuple[DefinitionId, ...] = ()
    allowed_clue_ids: tuple[DefinitionId, ...] = ()
    visible_location_ids: tuple[DefinitionId, ...]
    objective_ids: tuple[DefinitionId, ...] = ()
    allowed_action_types: tuple[DefinitionId, ...]
    min_auto_beats: Annotated[int, Field(strict=True, ge=0, le=MAX_AUTO_BEATS)]
    max_auto_beats: Annotated[int, Field(strict=True, ge=0, le=MAX_AUTO_BEATS)]
    decision_window_ids: tuple[DefinitionId, ...] = ()
    transitions: tuple[TransitionDefinition, ...] = ()
    action_time_costs: tuple[ActionTimeCostDefinition, ...] = ()
    auto_beat_clock_advances: tuple[ClockAdvanceDefinition, ...] = ()
    rapid_decision_allowed: StrictBool = False
    terminal: StrictBool = False
    required: StrictBool = True
    max_visits: Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)] | None = None
    tone_hints: tuple[Annotated[str, Field(strict=True, min_length=1, max_length=80)], ...] = ()

    @model_validator(mode="after")
    def validate_phase_shape(self) -> ScenePhaseDefinition:
        if self.max_auto_beats < self.min_auto_beats:
            raise ValueError("phase max_auto_beats cannot be less than min_auto_beats")
        if self.terminal and self.transitions:
            raise ValueError("terminal phase cannot declare transitions")
        if self.terminal and any(
            (
                self.decision_window_ids,
                self.action_time_costs,
                self.auto_beat_clock_advances,
                self.rapid_decision_allowed,
                self.max_auto_beats != 0,
            )
        ):
            raise ValueError("terminal phase cannot advance clocks or open decisions")
        if not self.terminal and not self.transitions:
            raise ValueError("non-terminal phase must declare at least one transition")
        if not self.visible_location_ids:
            raise ValueError("phase must expose at least one visible location")
        if not self.allowed_action_types:
            raise ValueError("phase must allow at least one action type")
        if len(self.tone_hints) > 16:
            raise ValueError("phase tone hint count exceeds limit 16")
        _reject_duplicates(
            (item.transition_id for item in self.transitions),
            f"phase {self.phase_id!r} transition",
        )
        for label, values in (
            ("visible location", self.visible_location_ids),
            ("clue", self.allowed_clue_ids),
            ("must-render fact", self.must_render_fact_ids),
            ("decision", self.decision_window_ids),
            ("action type", self.allowed_action_types),
            ("objective", self.objective_ids),
            ("tone hint", self.tone_hints),
            ("required event", self.required_event_types),
        ):
            _reject_duplicates(values, f"phase {self.phase_id!r} {label}")
        _reject_duplicates(
            (item.action_type for item in self.action_time_costs),
            f"phase {self.phase_id!r} action time cost",
        )
        return self


class EndingRuleDefinition(ScenarioDefinitionModel):
    ending_id: DefinitionId
    status: EndingStatus
    conditions: tuple[ConditionDefinition, ...]
    priority: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)] = 100

    @model_validator(mode="after")
    def validate_ending(self) -> EndingRuleDefinition:
        if self.status is EndingStatus.ACTIVE:
            raise ValueError("ending rules must resolve or fail the scenario")
        if not self.conditions:
            raise ValueError("ending rules require at least one condition")
        return self


class PublicPlayableCharacterDefinition(ScenarioDefinitionModel):
    character_definition_id: DefinitionId
    description: Annotated[str, Field(strict=True, min_length=1, max_length=300)]


class PublicScenePresentationDefinition(ScenarioDefinitionModel):
    phase_id: DefinitionId
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=300)]


class PublicEndingPresentationDefinition(ScenarioDefinitionModel):
    ending_id: DefinitionId
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=500)]


class PublicActionPresentationDefinition(ScenarioDefinitionModel):
    action_type: ActionType
    label: Annotated[str, Field(strict=True, min_length=1, max_length=80)]


class PublicClientScenarioDefinition(ScenarioDefinitionModel):
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    hook: Annotated[str, Field(strict=True, min_length=1, max_length=300)]
    playable_characters: tuple[PublicPlayableCharacterDefinition, ...]
    default_character_definition_id: DefinitionId
    scenes: tuple[PublicScenePresentationDefinition, ...]
    endings: tuple[PublicEndingPresentationDefinition, ...]
    actions: tuple[PublicActionPresentationDefinition, ...]

    @model_validator(mode="after")
    def validate_public_client_shape(self) -> PublicClientScenarioDefinition:
        for label, values, maximum in (
            (
                "playable character",
                tuple(item.character_definition_id for item in self.playable_characters),
                16,
            ),
            ("scene", tuple(item.phase_id for item in self.scenes), 64),
            ("ending", tuple(item.ending_id for item in self.endings), 64),
            ("action", tuple(item.action_type.value for item in self.actions), 16),
        ):
            if not values:
                raise ValueError(f"public client {label} collection cannot be empty")
            if len(values) > maximum:
                raise ValueError(
                    f"public client {label} count exceeds limit {maximum}"
                )
            _reject_duplicates(values, f"public client {label}")
        if self.default_character_definition_id not in {
            item.character_definition_id for item in self.playable_characters
        }:
            raise ValueError("default public character is not playable")
        return self


class NarrativeLengthDefinition(ScenarioDefinitionModel):
    target: Annotated[int, Field(strict=True, ge=1, le=MAX_NARRATIVE_LENGTH)]
    minimum: Annotated[int, Field(strict=True, ge=1, le=MAX_NARRATIVE_LENGTH)]
    maximum: Annotated[int, Field(strict=True, ge=1, le=MAX_NARRATIVE_LENGTH)]

    @model_validator(mode="after")
    def validate_order(self) -> NarrativeLengthDefinition:
        if not self.minimum <= self.target <= self.maximum:
            raise ValueError("narrative length must satisfy minimum <= target <= maximum")
        return self


class ScenarioDefinition(ScenarioDefinitionModel):
    scenario_id: DefinitionId
    schema_version: Annotated[int, Field(strict=True)]
    content_version: DefinitionId
    title: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    summary: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    initial_phase_id: DefinitionId
    initial_location_id: DefinitionId
    phases: tuple[ScenePhaseDefinition, ...]
    locations: tuple[LocationDefinition, ...]
    npc_references: tuple[ScenarioNpcReference, ...] = ()
    facts: tuple[FactDefinition, ...]
    clues: tuple[ClueDefinition, ...]
    clue_groups: tuple[ClueGroupDefinition, ...]
    threat_clocks: tuple[ThreatClockDefinition, ...]
    decision_windows: tuple[DecisionWindowDefinition, ...]
    endings: tuple[EndingRuleDefinition, ...]
    available_profession_tags: tuple[DefinitionId, ...] = ()
    story_item_definition_ids: tuple[DefinitionId, ...] = ()
    dynamic_fact_limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 20
    dynamic_fact_key_max_length: Annotated[int, Field(strict=True, ge=9, le=128)] = 96
    dynamic_fact_value_max_length: Annotated[int, Field(strict=True, ge=1, le=4000)] = 500
    narrative_length: NarrativeLengthDefinition
    narrative_outcome_rules: tuple[NarrativeOutcomeRuleDefinition, ...] = ()
    memory_rules: tuple[MemoryRuleDefinition, ...] = ()
    public_client: PublicClientScenarioDefinition | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_payload_complexity(cls, value: Any) -> Any:
        _validate_payload_complexity(value)
        return value

    @field_validator("schema_version")
    @classmethod
    def supported_schema(cls, value: int) -> int:
        if value != SUPPORTED_SCENARIO_SCHEMA_VERSION:
            raise ValueError(
                "unsupported scenario schema_version; expected "
                f"{SUPPORTED_SCENARIO_SCHEMA_VERSION}"
            )
        return value

    @model_validator(mode="after")
    def validate_graph_and_references(self) -> ScenarioDefinition:
        self._validate_collection_limits()
        if sum(len(clock.thresholds) for clock in self.threat_clocks) > 128:
            raise ContentDefinitionError(
                "scenario clock threshold count exceeds limit 128"
            )
        phases = _unique_map(self.phases, "phase_id", "phase")
        locations = _unique_map(self.locations, "location_id", "location")
        facts = _unique_map(self.facts, "fact_id", "fact")
        clues = _unique_map(self.clues, "clue_id", "clue")
        groups = _unique_map(self.clue_groups, "clue_group_id", "clue group")
        clocks = _unique_map(self.threat_clocks, "clock_id", "clock")
        windows = _unique_map(self.decision_windows, "decision_id", "decision")
        _unique_map(self.endings, "ending_id", "ending")
        outcome_rules = _unique_map(
            self.narrative_outcome_rules, "rule_id", "narrative outcome rule"
        )
        memory_rules = _unique_map(self.memory_rules, "rule_id", "memory rule")
        _reject_duplicates(
            (item.npc_definition_id for item in self.npc_references), "scenario NPC reference"
        )
        _reject_duplicates(self.available_profession_tags, "scenario profession tag")
        _reject_duplicates(self.story_item_definition_ids, "scenario story item")
        if self.public_client is not None:
            public = self.public_client
            if {item.phase_id for item in public.scenes} != set(phases):
                raise ContentDefinitionError(
                    "public client scenes must exactly cover scenario phases"
                )
            ending_ids = {item.ending_id for item in self.endings}
            if {item.ending_id for item in public.endings} != ending_ids:
                raise ContentDefinitionError(
                    "public client endings must exactly cover scenario endings"
                )
            required_action_types = {
                ActionType.CONTINUE,
                *(
                    action_type
                    for rule in self.narrative_outcome_rules
                    for action_type in rule.intent.action_types
                ),
            }
            public_progression_types = {
                ActionType.CONTINUE,
                ActionType.TALK,
                ActionType.CUSTOM,
                ActionType.EXPLORE,
                ActionType.OBSERVE,
                ActionType.MOVE,
            }
            if not required_action_types <= public_progression_types:
                raise ContentDefinitionError(
                    "public client scenario uses an unsupported progression action"
                )
            if not required_action_types <= {
                item.action_type for item in public.actions
            }:
                raise ContentDefinitionError(
                    "public client action labels do not cover scenario actions"
                )
        if self.initial_phase_id not in phases:
            raise ContentDefinitionError("initial phase does not exist")
        if self.initial_location_id not in locations:
            raise ContentDefinitionError("initial location does not exist")

        owned_ids = [
            *phases,
            *locations,
            *facts,
            *clues,
            *groups,
            *clocks,
            *windows,
            *(item.ending_id for item in self.endings),
            *outcome_rules,
            *memory_rules,
            *(
                transition.transition_id
                for phase in self.phases
                for transition in phase.transitions
            ),
            *(
                action.action_id
                for window in self.decision_windows
                for action in window.suggested_actions
            ),
        ]
        _reject_duplicates(owned_ids, "scenario-owned ID")

        all_transitions: list[tuple[str, TransitionDefinition]] = []
        for phase in self.phases:
            _require_all(phase.visible_location_ids, locations, f"phase {phase.phase_id!r} location")
            _require_all(phase.allowed_clue_ids, clues, f"phase {phase.phase_id!r} clue")
            _require_all(phase.must_render_fact_ids, facts, f"phase {phase.phase_id!r} fact")
            _require_all(phase.decision_window_ids, windows, f"phase {phase.phase_id!r} decision")
            for transition in phase.transitions:
                if transition.target_phase_id not in phases:
                    raise ContentDefinitionError(
                        f"transition {transition.transition_id!r} references missing phase"
                    )
                self._validate_conditions(transition.conditions, phases, facts, groups, clocks, locations)
                all_transitions.append((phase.phase_id, transition))
            for cost in (*phase.action_time_costs,):
                if cost.action_type not in phase.allowed_action_types:
                    raise ContentDefinitionError(
                        f"phase {phase.phase_id!r} time cost uses a disallowed action type"
                    )
                self._validate_clock_advances(cost.clock_advances, clocks)
            self._validate_clock_advances(phase.auto_beat_clock_advances, clocks)
            self._validate_conditions(phase.entry_conditions, phases, facts, groups, clocks, locations)

        _reject_duplicates(
            (transition.transition_id for _, transition in all_transitions), "scenario transition"
        )
        mutable_transition_event_types = {
            transition.event_type
            for fact in self.facts
            for transition in fact.mutable_transitions
        }
        for clue in self.clues:
            _require_all(clue.supports_fact_ids, facts, f"clue {clue.clue_id!r} fact")
            _require_all(clue.allowed_phase_ids, phases, f"clue {clue.clue_id!r} phase")
            _require_all(
                clue.required_any_profession_tags,
                set(self.available_profession_tags),
                f"clue {clue.clue_id!r} profession tag",
            )
        for group in self.clue_groups:
            _require_all(group.clue_ids, clues, f"clue group {group.clue_group_id!r} clue")
            tag_free = sum(not clues[clue_id].required_any_profession_tags for clue_id in group.clue_ids)
            if tag_free < group.required_count:
                raise ContentDefinitionError(
                    f"clue group {group.clue_group_id!r} requires a profession tag"
                )
        for npc in self.npc_references:
            _require_all(npc.known_fact_ids, facts, f"NPC {npc.npc_definition_id!r} fact")
        for window in self.decision_windows:
            self._validate_conditions(window.conditions, phases, facts, groups, clocks, locations)
            if all(item.once for item in self.decision_windows):
                for condition in window.conditions:
                    if (
                        isinstance(condition, DecisionsAtLeastCondition)
                        and condition.value > len(self.decision_windows)
                    ):
                        raise ContentDefinitionError(
                            f"decision {window.decision_id!r} can never satisfy its decision count"
                        )
            for action in window.suggested_actions:
                if (
                    action.mutable_fact_updates
                    and action.server_event_type is not None
                    and action.server_event_type not in mutable_transition_event_types
                ):
                    raise ContentDefinitionError(
                        "decision effect event is not declared by a scenario transition"
                    )
                _require_all(
                    action.required_any_profession_tags,
                    set(self.available_profession_tags),
                    f"action {action.action_id!r} profession tag",
                )
                _require_all(
                    action.target_ids,
                    set(locations)
                    | {item.npc_definition_id for item in self.npc_references}
                    | set(self.story_item_definition_ids),
                    f"action {action.action_id!r} target",
                )
                for update in action.mutable_fact_updates:
                    fact = facts.get(update.fact_id)
                    if fact is None or fact.kind is not FactKind.MUTABLE:
                        raise ContentDefinitionError(
                            "decision effect references an invalid mutable fact"
                        )
                    if not any(
                        transition.event_type == action.server_event_type
                        and json_values_equal(transition.to_value, update.value)
                        for transition in fact.mutable_transitions
                    ):
                        raise ContentDefinitionError(
                            "decision effect is not an allowed mutable transition"
                        )
        for phase in self.phases:
            for decision_id in phase.decision_window_ids:
                window = windows[decision_id]
                if phase.rapid_decision_allowed and not window.once:
                    raise ContentDefinitionError(
                        f"rapid phase {phase.phase_id!r} cannot repeat decision {decision_id!r}"
                    )
                if (
                    window.latest_beat < phase.min_auto_beats
                    or window.earliest_beat > phase.max_auto_beats
                    or any(
                        isinstance(condition, PhaseBeatAtLeastCondition)
                        and condition.value > window.latest_beat
                        for condition in window.conditions
                    )
                ):
                    raise ContentDefinitionError(
                        f"decision {decision_id!r} can never open in phase {phase.phase_id!r}"
                    )
                for action in window.suggested_actions:
                    if action.action_type not in phase.allowed_action_types:
                        raise ContentDefinitionError(
                            f"decision {decision_id!r} uses an action disallowed by phase"
                        )
                    _require_all(
                        action.opened_location_ids,
                        locations,
                        f"decision action {action.action_id!r} opened location",
                    )
                    if action.new_location_id is not None:
                        _require_all(
                            (action.new_location_id,),
                            locations,
                            f"decision action {action.action_id!r} destination",
                        )
                        if action.new_location_id not in phase.visible_location_ids:
                            raise ContentDefinitionError(
                                f"decision action {action.action_id!r} destination is not visible"
                            )
                _require_all(
                    window.custom_action_constraints.allowed_action_types,
                    set(phase.allowed_action_types),
                    f"decision {decision_id!r} custom action type",
                )
        for ending in self.endings:
            self._validate_conditions(ending.conditions, phases, facts, groups, clocks, locations)

        npc_definition_ids = {item.npc_definition_id for item in self.npc_references}
        decision_phase_ids = {
            decision_id: {
                phase.phase_id
                for phase in self.phases
                if decision_id in phase.decision_window_ids
            }
            for decision_id in windows
        }
        mutex_priorities: set[tuple[str, int]] = set()
        for rule in self.narrative_outcome_rules:
            _require_all(rule.allowed_phase_ids, phases, f"outcome rule {rule.rule_id!r} phase")
            _require_all(
                rule.required_visible_npc_definition_ids,
                npc_definition_ids,
                f"outcome rule {rule.rule_id!r} NPC",
            )
            _require_all(rule.required_clue_ids, clues, f"outcome rule {rule.rule_id!r} clue")
            _require_all(
                rule.required_current_decision_ids,
                windows,
                f"outcome rule {rule.rule_id!r} decision",
            )
            _require_all(
                rule.required_current_location_ids,
                locations,
                f"outcome rule {rule.rule_id!r} current location",
            )
            for location_id in rule.required_current_location_ids:
                if not all(
                    location_id in phases[phase_id].visible_location_ids
                    for phase_id in rule.allowed_phase_ids
                ):
                    raise ContentDefinitionError(
                        f"outcome rule {rule.rule_id!r} current location is not visible"
                    )
            for decision_id in rule.required_current_decision_ids:
                if not set(rule.allowed_phase_ids) & decision_phase_ids[decision_id]:
                    raise ContentDefinitionError(
                        f"outcome rule {rule.rule_id!r} decision is unreachable"
                    )
            for requirement in rule.required_fact_values:
                _require_all((requirement.fact_id,), facts, f"outcome rule {rule.rule_id!r} fact")
            for effect in rule.effects:
                _require_all(
                    effect.player_alive_acknowledgement_npc_definition_ids,
                    set(rule.required_visible_npc_definition_ids),
                    f"outcome rule {rule.rule_id!r} acknowledging NPC",
                )
                _require_all(
                    effect.discovered_clue_ids,
                    clues,
                    f"outcome rule {rule.rule_id!r} effect clue",
                )
                _require_all(
                    effect.opened_location_ids,
                    locations,
                    f"outcome rule {rule.rule_id!r} effect location",
                )
                if effect.new_location_id is not None:
                    _require_all(
                        (effect.new_location_id,),
                        locations,
                        f"outcome rule {rule.rule_id!r} destination",
                    )
                    if not all(
                        effect.new_location_id in phases[phase_id].visible_location_ids
                        for phase_id in rule.allowed_phase_ids
                    ):
                        raise ContentDefinitionError(
                            "narrative outcome destination is not visible in every allowed phase"
                        )
                for fact_update in effect.deferred_bindings:
                    fact = facts.get(fact_update.fact_id)
                    if fact is None or fact.kind is not FactKind.DEFERRED:
                        raise ContentDefinitionError("narrative deferred effect references invalid fact")
                    if not any(
                        json_values_equal(fact_update.value, candidate)
                        for candidate in fact.deferred_candidates
                    ):
                        raise ContentDefinitionError("narrative deferred effect uses invalid value")
                for fact_update in effect.mutable_fact_updates:
                    fact = facts.get(fact_update.fact_id)
                    if fact is None or fact.kind is not FactKind.MUTABLE:
                        raise ContentDefinitionError("narrative mutable effect references invalid fact")
                    allowed = {canonical_json_key(item.to_value) for item in fact.mutable_transitions}
                    if canonical_json_key(fact_update.value) not in allowed:
                        raise ContentDefinitionError("narrative mutable effect uses invalid value")
                for phase_id in rule.allowed_phase_ids:
                    phase = phases[phase_id]
                    if effect.action_type not in phase.allowed_action_types:
                        raise ContentDefinitionError(
                            f"outcome rule {rule.rule_id!r} uses disallowed action cost"
                        )
            key = (rule.mutex_group, rule.priority)
            if key in mutex_priorities:
                raise ContentDefinitionError(
                    "narrative outcome mutex group has ambiguous equal priorities"
                )
            mutex_priorities.add(key)

        ending_ids = {item.ending_id for item in self.endings}
        all_outcome_event_types = {
            effect.event_type
            for outcome_rule in self.narrative_outcome_rules
            for effect in outcome_rule.effects
        }
        all_runtime_event_types = {
            *all_outcome_event_types,
            *(
                transition.event_type
                for fact in self.facts
                for transition in fact.mutable_transitions
            ),
            *(group.completion_event_type for group in self.clue_groups),
            *(
                threshold.event_type
                for clock in self.threat_clocks
                for threshold in clock.thresholds
            ),
        }
        for rule in self.memory_rules:
            _require_all(
                rule.required_narrative_outcome_rule_ids,
                outcome_rules,
                f"memory rule {rule.rule_id!r} narrative outcome rule",
            )
            _require_all(
                rule.allowed_ending_ids,
                ending_ids,
                f"memory rule {rule.rule_id!r} ending",
            )
            if rule.npc_definition_id is not None:
                _require_all(
                    (rule.npc_definition_id,),
                    npc_definition_ids,
                    f"memory rule {rule.rule_id!r} NPC",
                )
            if rule.public_fact_id is not None:
                fact = facts.get(rule.public_fact_id)
                if fact is None or fact.visibility is FactVisibility.HIDDEN:
                    raise ContentDefinitionError(
                        f"memory rule {rule.rule_id!r} references a non-public fact"
                    )
            if rule.source_event_type is MemoryRuleSourceEventType.SCENARIO_STARTED:
                if rule.required_narrative_outcome_rule_ids:
                    raise ContentDefinitionError(
                        "scenario-started memory rule cannot require a narrative outcome"
                    )
            if rule.required_scenario_event_types:
                permitted_event_types = all_runtime_event_types
                if (
                    rule.source_event_type
                    is MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED
                ):
                    permitted_event_types = all_outcome_event_types
                if rule.required_narrative_outcome_rule_ids:
                    permitted_event_types = {
                        effect.event_type
                        for rule_id in rule.required_narrative_outcome_rule_ids
                        for effect in outcome_rules[rule_id].effects
                    }
                _require_all(
                    rule.required_scenario_event_types,
                    permitted_event_types,
                    f"memory rule {rule.rule_id!r} scenario event",
                )
            if rule.required_outcome_results:
                permitted_results = {
                    effect.result
                    for rule_id in (
                        rule.required_narrative_outcome_rule_ids
                        or tuple(outcome_rules)
                    )
                    for effect in outcome_rules[rule_id].effects
                }
                _require_all(
                    rule.required_outcome_results,
                    permitted_results,
                    f"memory rule {rule.rule_id!r} outcome result",
                )
            if (
                rule.operation
                is MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE
            ):
                category = rule.significant_experience_category
                if category in {
                    SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
                    SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
                } and rule.npc_definition_id is None:
                    raise ContentDefinitionError(
                        "NPC significant memory rule requires an NPC reference"
                    )
                if (
                    category
                    is SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY
                    and rule.public_fact_id is None
                ):
                    raise ContentDefinitionError(
                        "public-discovery memory rule requires a fact reference"
                    )

        reachable = {self.initial_phase_id}
        changed = True
        while changed:
            changed = False
            for source, transition in all_transitions:
                if source in reachable and transition.target_phase_id not in reachable:
                    reachable.add(transition.target_phase_id)
                    changed = True
        unreachable = sorted(
            phase.phase_id for phase in self.phases if phase.required and phase.phase_id not in reachable
        )
        if unreachable:
            raise ContentDefinitionError(f"required phase is unreachable: {', '.join(unreachable)}")
        self._reject_unbounded_automatic_cycles(phases)
        return self

    def _validate_collection_limits(self) -> None:
        limits = (
            ("phase", len(self.phases), MAX_PHASES_PER_SCENARIO),
            ("location", len(self.locations), MAX_LOCATIONS_PER_SCENARIO),
            ("NPC", len(self.npc_references), MAX_NPCS_PER_SCENARIO),
            ("fact", len(self.facts), MAX_FACTS_PER_SCENARIO),
            ("clue", len(self.clues), MAX_CLUES_PER_SCENARIO),
            ("clue group", len(self.clue_groups), MAX_CLUE_GROUPS_PER_SCENARIO),
            ("clock", len(self.threat_clocks), MAX_CLOCKS_PER_SCENARIO),
            ("decision", len(self.decision_windows), MAX_DECISIONS_PER_SCENARIO),
            ("ending", len(self.endings), MAX_ENDINGS_PER_SCENARIO),
            ("narrative outcome rule", len(self.narrative_outcome_rules), 128),
            ("memory rule", len(self.memory_rules), 256),
        )
        for label, count, maximum in limits:
            if count > maximum:
                raise ContentDefinitionError(
                    f"scenario {label} count exceeds limit {maximum}"
                )

    @staticmethod
    def _validate_clock_advances(
        advances: tuple[ClockAdvanceDefinition, ...], clocks: Mapping[str, object]
    ) -> None:
        _reject_duplicates((item.clock_id for item in advances), "clock advance")
        _require_all((item.clock_id for item in advances), clocks, "clock advance")

    @staticmethod
    def _validate_conditions(
        conditions: tuple[ConditionDefinition, ...],
        phases: Mapping[str, object],
        facts: Mapping[str, object],
        groups: Mapping[str, object],
        clocks: Mapping[str, ThreatClockDefinition],
        locations: Mapping[str, object],
    ) -> None:
        for condition in conditions:
            if isinstance(condition, FactEqualsCondition):
                _require_all((condition.fact_id,), facts, "condition fact")
                fact = facts[condition.fact_id]
                assert isinstance(fact, FactDefinition)
                possible_values = (
                    (fact.value,)
                    if fact.kind is FactKind.FIXED
                    else fact.deferred_candidates
                    if fact.kind is FactKind.DEFERRED
                    else (fact.value, *(item.to_value for item in fact.mutable_transitions))
                )
                if not any(
                    json_values_equal(condition.value, value) for value in possible_values
                ):
                    raise ContentDefinitionError(
                        f"condition fact {condition.fact_id!r} can never equal its value"
                    )
            elif isinstance(condition, ClueGroupCompleteCondition):
                _require_all((condition.clue_group_id,), groups, "condition clue group")
            elif isinstance(condition, (ClockAtLeastCondition, ClockAtMostCondition)):
                clock = clocks.get(condition.clock_id)
                if clock is None:
                    raise ContentDefinitionError(
                        f"condition clock references missing ID {condition.clock_id!r}"
                    )
                if not clock.minimum <= condition.value <= clock.maximum:
                    raise ContentDefinitionError("condition clock value is outside bounds")
            elif isinstance(condition, LocationOpenedCondition):
                _require_all((condition.location_id,), locations, "condition location")
            elif isinstance(condition, PhaseVisitAtLeastCondition):
                _require_all((condition.phase_id,), phases, "condition phase")
                phase = phases[condition.phase_id]
                assert isinstance(phase, ScenePhaseDefinition)
                if phase.max_visits is not None and condition.value > phase.max_visits:
                    raise ContentDefinitionError(
                        f"condition phase {condition.phase_id!r} cannot reach its visit count"
                    )

    def _reject_unbounded_automatic_cycles(
        self, phases: Mapping[str, ScenePhaseDefinition]
    ) -> None:
        # A cycle is unbounded exactly when every phase in it lacks max_visits and
        # every automatic edge in it lacks max_uses.  Remove all bounded phases and
        # edges, then use Kahn's algorithm to detect a remaining cycle in O(V + E).
        # The former simple-path enumeration was exponential on dense acyclic input.
        unbounded_phase_ids = {
            phase_id
            for phase_id, phase in phases.items()
            if phase.max_visits is None
        }
        adjacency: dict[str, list[str]] = {
            phase_id: [] for phase_id in unbounded_phase_ids
        }
        indegree = {phase_id: 0 for phase_id in unbounded_phase_ids}
        for phase_id in sorted(unbounded_phase_ids):
            for transition in phases[phase_id].transitions:
                if (
                    transition.trigger is TransitionTrigger.AUTOMATIC
                    and transition.max_uses is None
                    and transition.target_phase_id in unbounded_phase_ids
                ):
                    adjacency[phase_id].append(transition.target_phase_id)
                    indegree[transition.target_phase_id] += 1

        frontier = [
            phase_id for phase_id, degree in indegree.items() if degree == 0
        ]
        visited = 0
        while frontier:
            phase_id = frontier.pop()
            visited += 1
            for target in adjacency[phase_id]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    frontier.append(target)
        if visited != len(unbounded_phase_ids):
            raise ContentDefinitionError("unbounded automatic transition cycle")

    def phase(self, phase_id: str) -> ScenePhaseDefinition:
        return next(item for item in self.phases if item.phase_id == phase_id)

    def fact(self, fact_id: str) -> FactDefinition:
        return next(item for item in self.facts if item.fact_id == fact_id)

    def clue(self, clue_id: str) -> ClueDefinition:
        return next(item for item in self.clues if item.clue_id == clue_id)

    def clue_group(self, group_id: str) -> ClueGroupDefinition:
        return next(item for item in self.clue_groups if item.clue_group_id == group_id)

    def clock(self, clock_id: str) -> ThreatClockDefinition:
        return next(item for item in self.threat_clocks if item.clock_id == clock_id)

    def decision_window(self, decision_id: str) -> DecisionWindowDefinition:
        return next(item for item in self.decision_windows if item.decision_id == decision_id)


class ScenarioCatalog(ScenarioDefinitionModel):
    schema_version: Annotated[int, Field(strict=True)]
    content_version: DefinitionId
    content_catalog: ContentCatalog
    scenarios: tuple[ScenarioDefinition, ...]

    @model_validator(mode="before")
    @classmethod
    def validate_payload_complexity(cls, value: Any) -> Any:
        _validate_payload_complexity(value)
        return value

    @field_validator("schema_version")
    @classmethod
    def supported_schema(cls, value: int) -> int:
        if value != SUPPORTED_SCENARIO_SCHEMA_VERSION:
            raise ValueError(
                "unsupported scenario catalog schema_version; expected "
                f"{SUPPORTED_SCENARIO_SCHEMA_VERSION}"
            )
        return value

    @model_validator(mode="after")
    def validate_catalog(self) -> ScenarioCatalog:
        if len(self.scenarios) > MAX_SCENARIOS_PER_CATALOG:
            raise ContentDefinitionError(
                f"scenario count exceeds limit {MAX_SCENARIOS_PER_CATALOG}"
            )
        if self.content_catalog.content_version != self.content_version:
            raise ContentDefinitionError("scenario and content catalog versions must match")
        scenarios = _unique_map(self.scenarios, "scenario_id", "scenario")
        available_character_tags = {
            tag for character in self.content_catalog.characters for tag in character.tags
        }
        for scenario in scenarios.values():
            if scenario.content_version != self.content_version:
                raise ContentDefinitionError("scenario content_version does not match catalog")
            _require_all(
                (item.npc_definition_id for item in scenario.npc_references),
                {item.definition_id for item in self.content_catalog.npcs},
                f"scenario {scenario.scenario_id!r} NPC",
            )
            _require_all(
                scenario.story_item_definition_ids,
                {item.definition_id for item in self.content_catalog.items},
                f"scenario {scenario.scenario_id!r} story item",
            )
            _require_all(
                scenario.available_profession_tags,
                available_character_tags,
                f"scenario {scenario.scenario_id!r} profession tag",
            )
            if scenario.public_client is not None:
                characters = {
                    item.definition_id: item
                    for item in self.content_catalog.characters
                }
                _require_all(
                    (
                        item.character_definition_id
                        for item in scenario.public_client.playable_characters
                    ),
                    characters,
                    f"scenario {scenario.scenario_id!r} public character",
                )
                if any(
                    "npc" in characters[item.character_definition_id].tags
                    for item in scenario.public_client.playable_characters
                ):
                    raise ContentDefinitionError(
                        "public playable character cannot be an NPC"
                    )
            entity_ids = {item.npc_definition_id for item in scenario.npc_references}
            for location in scenario.locations:
                _require_all(
                    location.visible_entity_ids,
                    entity_ids,
                    f"location {location.location_id!r} entity",
                )
            outcome_rules = {
                item.rule_id: item for item in scenario.narrative_outcome_rules
            }
            for memory_rule in scenario.memory_rules:
                npc_definition_id = memory_rule.npc_definition_id
                if npc_definition_id is None:
                    continue
                candidate_outcomes = tuple(
                    outcome_rules[rule_id]
                    for rule_id in (
                        memory_rule.required_narrative_outcome_rule_ids
                        or tuple(outcome_rules)
                    )
                )
                if not any(
                    npc_definition_id
                    in outcome.required_visible_npc_definition_ids
                    and any(
                        (
                            not memory_rule.required_outcome_results
                            or effect.result
                            in memory_rule.required_outcome_results
                        )
                        and (
                            not memory_rule.required_scenario_event_types
                            or effect.event_type
                            in memory_rule.required_scenario_event_types
                        )
                        for effect in outcome.effects
                    )
                    for outcome in candidate_outcomes
                ):
                    raise ContentDefinitionError(
                        f"memory rule {memory_rule.rule_id!r} NPC is not an "
                        "authoritative narrative outcome subject"
                    )
        return self

    def scenario(self, scenario_id: str) -> ScenarioDefinition | None:
        return next((item for item in self.scenarios if item.scenario_id == scenario_id), None)


def _reject_duplicates(values: Iterable[str], label: str) -> None:
    sequence = tuple(values)
    duplicates = sorted(value for value, count in Counter(sequence).items() if count > 1)
    if duplicates:
        raise ContentDefinitionError(f"duplicate {label}: {', '.join(duplicates)}")


def _unique_map(items: Iterable[Any], attribute: str, label: str) -> dict[str, Any]:
    sequence = tuple(items)
    _reject_duplicates((getattr(item, attribute) for item in sequence), label)
    return {getattr(item, attribute): item for item in sequence}


def _require_all(values: Iterable[str], known: Mapping[str, object] | set[str], label: str) -> None:
    for value in values:
        if value not in known:
            raise ContentDefinitionError(f"{label} references missing ID {value!r}")


def _validate_payload_complexity(value: Any) -> None:
    nodes = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_SCENARIO_PAYLOAD_NODES:
            raise ContentDefinitionError("scenario payload exceeds node limit")
        if depth > MAX_SCENARIO_PAYLOAD_DEPTH:
            raise ContentDefinitionError("scenario payload exceeds nesting depth limit")
        if isinstance(item, str):
            if len(item) > MAX_SCENARIO_STRING_LENGTH:
                raise ContentDefinitionError("scenario payload contains an oversized string")
            return
        if isinstance(item, Mapping):
            if len(item) > MAX_SCENARIO_COLLECTION_ITEMS:
                raise ContentDefinitionError("scenario payload object exceeds size limit")
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise ContentDefinitionError("scenario payload object keys must be strings")
                visit(key, depth + 1)
                visit(nested, depth + 1)
            return
        if isinstance(item, (list, tuple)):
            if len(item) > MAX_SCENARIO_COLLECTION_ITEMS:
                raise ContentDefinitionError("scenario payload array exceeds size limit")
            for nested in item:
                visit(nested, depth + 1)

    visit(value, 0)
