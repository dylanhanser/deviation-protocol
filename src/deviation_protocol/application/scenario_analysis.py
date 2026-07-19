from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
import json
from math import ceil
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.application.scenario_event_bridge import bind_public_decision_frame
from deviation_protocol.application.scenario_initialization import initialize_scenario_state
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.facts import FactKind, FactVisibility
from deviation_protocol.domain.json_values import (
    freeze_bounded_json_value,
    json_values_equal,
)
from deviation_protocol.domain.narrative import NarrativeFrame, RenderableFact, SuggestedAction, VisibleClock
from deviation_protocol.domain.scenario import (
    AlwaysCondition,
    ClueGroupCompleteCondition,
    ClockAtLeastCondition,
    ClockAtMostCondition,
    DecisionsAtLeastCondition,
    EventOccurredCondition,
    FactEqualsCondition,
    LocationOpenedCondition,
    PhaseBeatAtLeastCondition,
    PhaseVisitAtLeastCondition,
    ScenarioDefinition,
    ScenePhaseDefinition,
    TransitionTrigger,
)
from deviation_protocol.domain.state import GameState, PlayerState


MAX_DIAGNOSTICS = 256
CADENCE_SPARSE_BEATS_PER_WINDOW = 3
CADENCE_LONG_GAP_HEURISTIC_BEATS = 4
CADENCE_DENSE_WINDOWS_NUMERATOR = 1
CADENCE_DENSE_WINDOWS_DENOMINATOR = 2
PREVIEW_PLAYER_ID = "scenario-workbench-player"
PREVIEW_SESSION_ID = "scenario-workbench-preview"


class AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProofState(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class ScenarioDiagnostic(AnalysisModel):
    severity: DiagnosticSeverity
    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
    message: Annotated[str, Field(min_length=1, max_length=240)]
    subject_type: Annotated[str, Field(min_length=1, max_length=40)]
    subject_id: Annotated[str, Field(min_length=1, max_length=256)]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def freeze_metadata(self) -> ScenarioDiagnostic:
        object.__setattr__(
            self,
            "metadata",
            freeze_bounded_json_value(
                self.metadata,
                path="scenario diagnostic metadata",
                max_depth=4,
                max_collection_items=32,
                max_string_length=256,
            ),
        )
        return self


class DiagnosticCounts(AnalysisModel):
    error: int = 0
    warning: int = 0
    info: int = 0


class ScenarioCounts(AnalysisModel):
    phases: int
    transitions: int
    facts: int
    clues: int
    clue_groups: int
    clocks: int
    decisions: int
    endings: int
    outcome_rules: int


class ValidationSummary(AnalysisModel):
    scenario_id: str
    schema_version: int
    content_version: str
    counts: ScenarioCounts
    initial_phase_id: str
    initial_location_id: str
    diagnostics: tuple[ScenarioDiagnostic, ...]
    diagnostic_counts: DiagnosticCounts


class TransitionAnalysis(AnalysisModel):
    traversal_index: int
    source_phase_id: str
    transition_id: str
    target_phase_id: str
    trigger: str
    priority: int
    conditions_present: bool
    source_phase_reachable: bool
    condition_satisfiable_unknown: ProofState
    guaranteed_traversable: ProofState


class CycleAnalysis(AnalysisModel):
    phase_ids: tuple[str, ...]
    transition_ids: tuple[str, ...]
    automatic_only: bool
    bounded: bool


class EndingAnalysis(AnalysisModel):
    ending_id: str
    structurally_referenced: bool
    source_phase_reachable: ProofState
    condition_satisfiable_unknown: ProofState
    guaranteed_reachable: ProofState


class GraphAnalysis(AnalysisModel):
    reachable_phase_ids: tuple[str, ...]
    unreachable_phase_ids: tuple[str, ...]
    illegal_dead_end_phase_ids: tuple[str, ...]
    transitions: tuple[TransitionAnalysis, ...]
    cycles: tuple[CycleAnalysis, ...]
    endings: tuple[EndingAnalysis, ...]
    potentially_reachable_ending_ids: tuple[str, ...]
    unreachable_ending_ids: tuple[str, ...]
    ending_reachability_unknown_ids: tuple[str, ...]


class DecisionCadenceAnalysis(AnalysisModel):
    phase_id: str
    window_count: int
    cadence_type: str
    rapid_decision_allowed: bool
    min_auto_beats: int
    max_auto_beats: int
    repeatable_window_count: int
    long_without_choice: ProofState
    dense_non_rapid_choices: ProofState
    rapid_has_high_choice_density: ProofState
    signals_are_heuristic: Literal[True] = True


class ClueAnalysis(AnalysisModel):
    clue_id: str
    visibility_class: str
    has_declared_source: bool
    source_structurally_reachable: bool
    source_condition_satisfiable_unknown: ProofState
    guaranteed_discoverable: ProofState
    producer_types: tuple[str, ...]


class ClueGroupAnalysis(AnalysisModel):
    clue_group_id: str
    declared_clue_count: int
    structurally_sourceable_count: int
    required_count: int


class FactAnalysis(AnalysisModel):
    counts_by_kind: dict[str, int]
    unbindable_deferred_fact_ids: tuple[str, ...]
    unchangeable_mutable_fact_ids: tuple[str, ...]


class ClockAnalysis(AnalysisModel):
    clock_id: str
    minimum: int
    maximum: int
    initial: int
    thresholds: tuple[int, ...]
    player_visible: bool
    minimum_declared_action_cost: int | None
    maximum_declared_action_cost: int | None
    minimum_declared_auto_advance: int | None
    maximum_declared_auto_advance: int | None
    has_declared_progression_source: bool
    source_structurally_reachable: bool
    progression_condition_satisfiable_unknown: ProofState
    guaranteed_to_progress: ProofState
    unreachable_thresholds: tuple[int, ...]


class FrameBudget(AnalysisModel):
    label: str
    json_characters: int
    utf8_bytes: int
    list_count: int
    list_item_count: int
    narrative_fact_count: int
    visible_npc_count: int
    clue_count: int
    clock_count: int
    suggested_action_count: int
    heuristic_token_estimate: int
    token_estimate_kind: Literal["heuristic_utf8_bytes_divided_by_4"] = (
        "heuristic_utf8_bytes_divided_by_4"
    )


class ScenarioAnalysisReport(AnalysisModel):
    scenario_id: str
    schema_version: int
    content_version: str
    counts: ScenarioCounts
    graph: GraphAnalysis
    decision_cadence: tuple[DecisionCadenceAnalysis, ...]
    clues: tuple[ClueAnalysis, ...]
    clue_visibility_counts: dict[str, int]
    clue_groups: tuple[ClueGroupAnalysis, ...]
    facts: FactAnalysis
    clocks: tuple[ClockAnalysis, ...]
    frame_budgets: tuple[FrameBudget, ...]
    diagnostics: tuple[ScenarioDiagnostic, ...]
    diagnostic_counts: DiagnosticCounts


class ActiveDecisionPreview(AnalysisModel):
    decision_id: str
    reason: str
    suggested_actions: tuple[SuggestedAction, ...]


class ScenarioPreviewReport(AnalysisModel):
    scenario_id: str
    content_version: str
    character_definition_id: str
    phase_id: str
    public_location_id: str
    player_known_facts: tuple[RenderableFact, ...]
    visible_npc_ids: tuple[str, ...]
    public_clue_ids: tuple[str, ...]
    public_clocks: tuple[VisibleClock, ...]
    active_decision: ActiveDecisionPreview | None
    frame_id: str
    budget: FrameBudget
    preview_identity_kind: Literal["LOCAL_SYNTHETIC_PREVIEW"] = (
        "LOCAL_SYNTHETIC_PREVIEW"
    )
    decision_binding_scope: Literal["LOCAL_PREVIEW_ONLY"] = "LOCAL_PREVIEW_ONLY"
    production_api_credential: Literal[False] = False


@dataclass(frozen=True, slots=True)
class ScenarioPreviewBuild:
    report: ScenarioPreviewReport
    candidate_state: GameState
    frame: NarrativeFrame


def scenario_counts(definition: ScenarioDefinition) -> ScenarioCounts:
    return ScenarioCounts(
        phases=len(definition.phases),
        transitions=sum(len(phase.transitions) for phase in definition.phases),
        facts=len(definition.facts),
        clues=len(definition.clues),
        clue_groups=len(definition.clue_groups),
        clocks=len(definition.threat_clocks),
        decisions=len(definition.decision_windows),
        endings=len(definition.endings),
        outcome_rules=len(definition.narrative_outcome_rules),
    )


def validation_summary(
    definition: ScenarioDefinition,
    *,
    blocking_diagnostics: tuple[ScenarioDiagnostic, ...] = (),
) -> ValidationSummary:
    diagnostics = _finalize_diagnostics([
        ScenarioDiagnostic(
            severity=DiagnosticSeverity.INFO,
            code="SCENARIO_CATALOG_VALID",
            message="The scenario passed the authoritative catalog validation boundary.",
            subject_type="scenario",
            subject_id=definition.scenario_id,
        ),
        *(
            item
            for item in blocking_diagnostics
            if item.severity is DiagnosticSeverity.ERROR
        ),
    ])
    return ValidationSummary(
        scenario_id=definition.scenario_id,
        schema_version=definition.schema_version,
        content_version=definition.content_version,
        counts=scenario_counts(definition),
        initial_phase_id=definition.initial_phase_id,
        initial_location_id=definition.initial_location_id,
        diagnostics=diagnostics,
        diagnostic_counts=_diagnostic_counts(diagnostics),
    )


def build_initial_preview(
    catalog: ContentCatalog,
    definition: ScenarioDefinition,
    *,
    character_definition_id: str,
    story_director: DeterministicStoryDirector | None = None,
) -> ScenarioPreviewBuild:
    character = catalog.character(character_definition_id)
    if character is None or "npc" in character.tags or "player" not in character.tags:
        raise ValueError("character selection is not a playable catalog character")
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition(PREVIEW_PLAYER_ID, character),
    )
    director = story_director or DeterministicStoryDirector()
    started = initialize_scenario_state(
        state,
        catalog,
        definition,
        character_tags=character.tags,
        story_director=director,
    )
    candidate = started.candidate_state
    candidate.validate_against(catalog)
    frame = bind_public_decision_frame(
        started.frame,
        session_id=PREVIEW_SESSION_ID,
        state_version=0,
        scenario_content_version=definition.content_version,
    )
    public_facts = tuple(
        sorted(
            (*frame.must_render_facts, *frame.may_render_facts),
            key=lambda item: item.fact_id,
        )
    )
    active_decision = (
        ActiveDecisionPreview(
            decision_id=frame.decision_id or "",
            reason=(frame.decision_reason.value if frame.decision_reason is not None else ""),
            suggested_actions=frame.suggested_actions,
        )
        if frame.decision_required
        else None
    )
    report = ScenarioPreviewReport(
        scenario_id=frame.scenario_id,
        content_version=definition.content_version,
        character_definition_id=character.definition_id,
        phase_id=frame.phase_id,
        public_location_id=frame.current_location_id,
        player_known_facts=public_facts,
        visible_npc_ids=frame.visible_entities,
        public_clue_ids=frame.visible_clues,
        public_clocks=frame.player_visible_clocks,
        active_decision=active_decision,
        frame_id=frame.frame_id,
        budget=frame_budget(frame, label="initial_public_frame"),
    )
    return ScenarioPreviewBuild(report=report, candidate_state=candidate, frame=frame)


def frame_budget(frame: NarrativeFrame, *, label: str) -> FrameBudget:
    payload = frame.model_dump(mode="json")
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    list_count, list_item_count = _list_metrics(payload)
    utf8_bytes = len(encoded.encode("utf-8"))
    return FrameBudget(
        label=label,
        json_characters=len(encoded),
        utf8_bytes=utf8_bytes,
        list_count=list_count,
        list_item_count=list_item_count,
        narrative_fact_count=len(frame.must_render_facts) + len(frame.may_render_facts),
        visible_npc_count=len(frame.visible_entities),
        clue_count=len(frame.visible_clues),
        clock_count=len(frame.player_visible_clocks),
        suggested_action_count=len(frame.suggested_actions),
        heuristic_token_estimate=ceil(utf8_bytes / 4),
    )


class ScenarioAnalyzer:
    """Bounded structural analysis over an already validated scenario definition."""

    def analyze(
        self,
        definition: ScenarioDefinition,
        *,
        initial_public_frame: NarrativeFrame | None = None,
    ) -> ScenarioAnalysisReport:
        diagnostics: list[ScenarioDiagnostic] = []
        graph, reachable = self._graph(definition, diagnostics)
        cadence = self._cadence(definition, diagnostics)
        clues = self._clues(definition, reachable, diagnostics)
        facts = self._facts(definition, diagnostics)
        clocks = self._clocks(definition, reachable, diagnostics)
        budgets = (
            (frame_budget(initial_public_frame, label="initial_public_frame"),)
            if initial_public_frame is not None
            else ()
        )
        if initial_public_frame is None:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.INFO,
                    "INITIAL_FRAME_BUDGET_UNKNOWN",
                    "Initial public Frame budget requires an explicit playable character.",
                    "scenario",
                    definition.scenario_id,
                )
            )
        diagnostics.append(
            _diagnostic(
                DiagnosticSeverity.INFO,
                "STATE_SPACE_NOT_EXHAUSTIVE",
                "Condition-dependent reachability remains unknown; no full state-space proof was attempted.",
                "scenario",
                definition.scenario_id,
            )
        )
        finalized = _finalize_diagnostics(diagnostics)
        clue_results = {item.clue_id: item for item in clues}
        return ScenarioAnalysisReport(
            scenario_id=definition.scenario_id,
            schema_version=definition.schema_version,
            content_version=definition.content_version,
            counts=scenario_counts(definition),
            graph=graph,
            decision_cadence=cadence,
            clues=clues,
            clue_visibility_counts={
                visibility: sum(
                    item.visibility_class == visibility for item in clues
                )
                for visibility in ("discoverable", "hidden", "public")
            },
            clue_groups=tuple(
                ClueGroupAnalysis(
                    clue_group_id=group.clue_group_id,
                    declared_clue_count=len(group.clue_ids),
                    structurally_sourceable_count=sum(
                        clue_results[clue_id].source_structurally_reachable
                        for clue_id in group.clue_ids
                    ),
                    required_count=group.required_count,
                )
                for group in sorted(definition.clue_groups, key=lambda item: item.clue_group_id)
            ),
            facts=facts,
            clocks=clocks,
            frame_budgets=budgets,
            diagnostics=finalized,
            diagnostic_counts=_diagnostic_counts(finalized),
        )

    def _graph(
        self,
        definition: ScenarioDefinition,
        diagnostics: list[ScenarioDiagnostic],
    ) -> tuple[GraphAnalysis, frozenset[str]]:
        phase_map = {phase.phase_id: phase for phase in definition.phases}
        reachable = {definition.initial_phase_id}
        frontier = [definition.initial_phase_id]
        while frontier and len(reachable) <= len(phase_map):
            source = frontier.pop(0)
            for transition in sorted(
                phase_map[source].transitions,
                key=lambda item: (item.priority, item.transition_id),
            ):
                if transition.target_phase_id not in reachable:
                    reachable.add(transition.target_phase_id)
                    frontier.append(transition.target_phase_id)
        unreachable = tuple(sorted(set(phase_map) - reachable))
        for phase_id in unreachable:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.ERROR,
                    "PHASE_UNREACHABLE",
                    "The phase is not structurally reachable from the initial phase.",
                    "phase",
                    phase_id,
                )
            )
        dead_ends = tuple(
            sorted(
                phase.phase_id
                for phase in definition.phases
                if not phase.terminal and not phase.transitions
            )
        )
        for phase_id in dead_ends:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.ERROR,
                    "PHASE_ILLEGAL_DEAD_END",
                    "A non-terminal phase has no outgoing transition.",
                    "phase",
                    phase_id,
                )
            )

        transitions: list[TransitionAnalysis] = []
        index = 0
        clock_sources = self._clock_sources(
            definition,
            reachable=frozenset(reachable),
        )
        for phase in definition.phases:
            for transition in sorted(
                phase.transitions, key=lambda item: (item.priority, item.transition_id)
            ):
                target = phase_map[transition.target_phase_id]
                combined_conditions = (
                    *transition.conditions,
                    *target.entry_conditions,
                )
                condition_proof = self._condition_satisfiability(
                    definition,
                    combined_conditions,
                    reachable=frozenset(reachable),
                    clock_sources=clock_sources,
                    source_phase=phase,
                )
                transitions.append(
                    TransitionAnalysis(
                        traversal_index=index,
                        source_phase_id=phase.phase_id,
                        transition_id=transition.transition_id,
                        target_phase_id=transition.target_phase_id,
                        trigger=transition.trigger.value,
                        priority=transition.priority,
                        conditions_present=bool(combined_conditions),
                        source_phase_reachable=phase.phase_id in reachable,
                        condition_satisfiable_unknown=condition_proof,
                        guaranteed_traversable=(
                            ProofState.NO
                            if phase.phase_id not in reachable
                            or condition_proof is ProofState.NO
                            else ProofState.UNKNOWN
                        ),
                    )
                )
                index += 1

        cycles = self._cycles(definition)
        for cycle in cycles:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.WARNING,
                    "AUTOMATIC_CYCLE_BOUNDED" if cycle.automatic_only else "PHASE_CYCLE_PRESENT",
                    "A bounded automatic cycle is present."
                    if cycle.automatic_only
                    else "A structural phase cycle is present; condition-dependent behavior is unknown.",
                    "phase_cycle",
                    cycle.phase_ids[0],
                    {"phase_count": len(cycle.phase_ids), "bounded": cycle.bounded},
                )
            )

        unreachable_endings: list[str] = []
        possible_endings: list[str] = []
        unknown_endings: list[str] = []
        ending_results: list[EndingAnalysis] = []
        for ending in sorted(definition.endings, key=lambda item: (item.priority, item.ending_id)):
            source_proof = self._ending_source_phase_reachability(
                definition,
                ending.conditions,
                reachable=frozenset(reachable),
            )
            condition_proof = self._condition_satisfiability(
                definition,
                ending.conditions,
                reachable=frozenset(reachable),
                clock_sources=clock_sources,
            )
            guaranteed = (
                ProofState.NO
                if source_proof is ProofState.NO
                or condition_proof is ProofState.NO
                else ProofState.UNKNOWN
            )
            ending_results.append(
                EndingAnalysis(
                    ending_id=ending.ending_id,
                    structurally_referenced=True,
                    source_phase_reachable=source_proof,
                    condition_satisfiable_unknown=condition_proof,
                    guaranteed_reachable=guaranteed,
                )
            )
            if guaranteed is ProofState.NO:
                unreachable_endings.append(ending.ending_id)
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.ERROR,
                        "ENDING_STRUCTURALLY_UNREACHABLE",
                        "The ending has no structurally reachable trigger path.",
                        "ending",
                        ending.ending_id,
                    )
                )
            else:
                possible_endings.append(ending.ending_id)
                if (
                    source_proof is ProofState.UNKNOWN
                    or condition_proof is ProofState.UNKNOWN
                    or guaranteed is ProofState.UNKNOWN
                ):
                    unknown_endings.append(ending.ending_id)

        return (
            GraphAnalysis(
                reachable_phase_ids=tuple(sorted(reachable)),
                unreachable_phase_ids=unreachable,
                illegal_dead_end_phase_ids=dead_ends,
                transitions=tuple(transitions),
                cycles=cycles,
                endings=tuple(ending_results),
                potentially_reachable_ending_ids=tuple(possible_endings),
                unreachable_ending_ids=tuple(unreachable_endings),
                ending_reachability_unknown_ids=tuple(unknown_endings),
            ),
            frozenset(reachable),
        )

    def _condition_satisfiability(
        self,
        definition: ScenarioDefinition,
        conditions: tuple[Any, ...],
        *,
        reachable: frozenset[str],
        clock_sources: dict[str, list[int]],
        source_phase: ScenePhaseDefinition | None = None,
    ) -> ProofState:
        proofs: list[ProofState] = []
        for condition in conditions:
            if isinstance(condition, AlwaysCondition):
                proof = ProofState.YES
            elif isinstance(condition, PhaseBeatAtLeastCondition):
                phases = (
                    (source_phase,)
                    if source_phase is not None
                    else tuple(
                        phase
                        for phase in definition.phases
                        if phase.phase_id in reachable
                    )
                )
                if not any(
                    phase is not None
                    and condition.value <= phase.max_auto_beats
                    for phase in phases
                ):
                    proof = ProofState.NO
                elif condition.value == 0:
                    proof = ProofState.YES
                else:
                    proof = ProofState.UNKNOWN
            elif isinstance(condition, FactEqualsCondition):
                fact = definition.fact(condition.fact_id)
                if fact.kind is FactKind.FIXED:
                    proof = (
                        ProofState.YES
                        if json_values_equal(fact.value, condition.value)
                        else ProofState.NO
                    )
                elif fact.kind is FactKind.DEFERRED:
                    proof = (
                        ProofState.UNKNOWN
                        if any(
                            json_values_equal(candidate, condition.value)
                            for candidate in fact.deferred_candidates
                        )
                        else ProofState.NO
                    )
                else:
                    proof = (
                        ProofState.YES
                        if json_values_equal(fact.value, condition.value)
                        else ProofState.UNKNOWN
                    )
            elif isinstance(condition, ClueGroupCompleteCondition):
                group = definition.clue_group(condition.clue_group_id)
                structurally_available = sum(
                    bool(
                        self._clue_declared_source_phases(definition, clue_id)
                        & set(reachable)
                    )
                    for clue_id in group.clue_ids
                )
                proof = (
                    ProofState.UNKNOWN
                    if structurally_available >= group.required_count
                    else ProofState.NO
                )
            elif isinstance(condition, ClockAtLeastCondition):
                clock = definition.clock(condition.clock_id)
                proof = (
                    ProofState.YES
                    if clock.initial >= condition.value
                    else ProofState.UNKNOWN
                    if clock_sources[condition.clock_id]
                    else ProofState.NO
                )
            elif isinstance(condition, ClockAtMostCondition):
                clock = definition.clock(condition.clock_id)
                proof = (
                    ProofState.YES
                    if clock.initial <= condition.value
                    else ProofState.NO
                )
            elif isinstance(condition, LocationOpenedCondition):
                location = next(
                    item
                    for item in definition.locations
                    if item.location_id == condition.location_id
                )
                proof = (
                    ProofState.YES
                    if location.initially_open
                    or condition.location_id == definition.initial_location_id
                    else ProofState.UNKNOWN
                )
            elif isinstance(condition, DecisionsAtLeastCondition):
                reachable_windows = {
                    decision_id
                    for phase in definition.phases
                    if phase.phase_id in reachable
                    for decision_id in phase.decision_window_ids
                }
                proof = (
                    ProofState.YES
                    if condition.value == 0
                    else ProofState.UNKNOWN
                    if reachable_windows
                    else ProofState.NO
                )
            elif isinstance(condition, EventOccurredCondition):
                proof = ProofState.UNKNOWN
            elif isinstance(condition, PhaseVisitAtLeastCondition):
                proof = (
                    ProofState.NO
                    if condition.phase_id not in reachable
                    else ProofState.YES
                    if condition.phase_id == definition.initial_phase_id
                    and condition.value == 1
                    else ProofState.UNKNOWN
                )
            else:  # pragma: no cover - closed schema union
                proof = ProofState.UNKNOWN
            proofs.append(proof)
        if any(item is ProofState.NO for item in proofs):
            return ProofState.NO
        if any(item is ProofState.UNKNOWN for item in proofs):
            return ProofState.UNKNOWN
        return ProofState.YES

    def _ending_source_phase_reachability(
        self,
        definition: ScenarioDefinition,
        conditions: tuple[Any, ...],
        *,
        reachable: frozenset[str],
    ) -> ProofState:
        proofs: list[ProofState] = []
        for condition in conditions:
            if isinstance(condition, PhaseVisitAtLeastCondition):
                proof = (
                    ProofState.YES
                    if condition.phase_id in reachable
                    else ProofState.NO
                )
            elif isinstance(condition, PhaseBeatAtLeastCondition):
                proof = (
                    ProofState.YES
                    if any(
                        phase.phase_id in reachable
                        and phase.max_auto_beats >= condition.value
                        for phase in definition.phases
                    )
                    else ProofState.NO
                )
            elif isinstance(condition, ClueGroupCompleteCondition):
                group = definition.clue_group(condition.clue_group_id)
                available = sum(
                    bool(
                        self._clue_declared_source_phases(definition, clue_id)
                        & set(reachable)
                    )
                    for clue_id in group.clue_ids
                )
                proof = (
                    ProofState.YES
                    if available >= group.required_count
                    else ProofState.NO
                )
            elif isinstance(condition, (ClockAtLeastCondition, ClockAtMostCondition)):
                clock = definition.clock(condition.clock_id)
                initially_satisfied = (
                    clock.initial >= condition.value
                    if isinstance(condition, ClockAtLeastCondition)
                    else clock.initial <= condition.value
                )
                source_phase_ids = {
                    phase.phase_id
                    for phase in definition.phases
                    if any(
                        advance.clock_id == condition.clock_id
                        for advance in phase.auto_beat_clock_advances
                    )
                    or any(
                        advance.clock_id == condition.clock_id
                        for cost in phase.action_time_costs
                        for advance in cost.clock_advances
                    )
                }
                proof = (
                    ProofState.YES
                    if initially_satisfied
                    or bool(source_phase_ids & set(reachable))
                    else ProofState.NO
                )
            elif isinstance(condition, DecisionsAtLeastCondition):
                has_reachable_window = any(
                    phase.phase_id in reachable and phase.decision_window_ids
                    for phase in definition.phases
                )
                proof = (
                    ProofState.YES
                    if condition.value == 0
                    else ProofState.YES
                    if has_reachable_window
                    else ProofState.NO
                )
            elif isinstance(condition, EventOccurredCondition):
                # Event conditions do not declare a source phase in the schema.
                proof = ProofState.UNKNOWN
            elif isinstance(condition, LocationOpenedCondition):
                location = next(
                    item
                    for item in definition.locations
                    if item.location_id == condition.location_id
                )
                proof = (
                    ProofState.YES
                    if location.initially_open
                    or condition.location_id == definition.initial_location_id
                    else ProofState.UNKNOWN
                )
            else:
                proof = ProofState.YES
            proofs.append(proof)
        if any(item is ProofState.NO for item in proofs):
            return ProofState.NO
        if any(item is ProofState.UNKNOWN for item in proofs):
            return ProofState.UNKNOWN
        return ProofState.YES

    def _cycles(self, definition: ScenarioDefinition) -> tuple[CycleAnalysis, ...]:
        phase_map = {phase.phase_id: phase for phase in definition.phases}
        adjacency = {
            phase.phase_id: tuple(transition.target_phase_id for transition in phase.transitions)
            for phase in definition.phases
        }
        index = 0
        indexes: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        components: list[tuple[str, ...]] = []

        def visit(node: str) -> None:
            nonlocal index
            indexes[node] = lowlinks[node] = index
            index += 1
            stack.append(node)
            on_stack.add(node)
            for target in sorted(adjacency[node]):
                if target not in indexes:
                    visit(target)
                    lowlinks[node] = min(lowlinks[node], lowlinks[target])
                elif target in on_stack:
                    lowlinks[node] = min(lowlinks[node], indexes[target])
            if lowlinks[node] == indexes[node]:
                component: list[str] = []
                while stack:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.append(member)
                    if member == node:
                        break
                members = tuple(sorted(component))
                if len(members) > 1 or node in adjacency[node]:
                    components.append(members)

        for phase_id in sorted(phase_map):
            if phase_id not in indexes:
                visit(phase_id)

        results: list[CycleAnalysis] = []
        for members in sorted(components):
            member_set = set(members)
            edges = [
                transition
                for phase_id in members
                for transition in phase_map[phase_id].transitions
                if transition.target_phase_id in member_set
            ]
            automatic_only = bool(edges) and all(
                edge.trigger is TransitionTrigger.AUTOMATIC for edge in edges
            )
            bounded = any(phase_map[item].max_visits is not None for item in members) or any(
                edge.max_uses is not None for edge in edges
            )
            results.append(
                CycleAnalysis(
                    phase_ids=members,
                    transition_ids=tuple(sorted(edge.transition_id for edge in edges)),
                    automatic_only=automatic_only,
                    bounded=bounded,
                )
            )
        return tuple(results)

    def _cadence(
        self,
        definition: ScenarioDefinition,
        diagnostics: list[ScenarioDiagnostic],
    ) -> tuple[DecisionCadenceAnalysis, ...]:
        windows = {item.decision_id: item for item in definition.decision_windows}
        results: list[DecisionCadenceAnalysis] = []
        for phase in definition.phases:
            phase_windows = [windows[item] for item in phase.decision_window_ids]
            conditional = any(window.conditions for window in phase_windows)
            repeatable = sum(not window.once for window in phase_windows)
            if phase.terminal:
                cadence_type = "terminal"
            elif phase.rapid_decision_allowed:
                cadence_type = "rapid"
            elif not phase_windows:
                cadence_type = "no_declared_windows"
            elif all(window.earliest_beat == window.latest_beat == 0 for window in phase_windows):
                cadence_type = "immediate"
            elif (
                phase.max_auto_beats + 1
                >= CADENCE_SPARSE_BEATS_PER_WINDOW * len(phase_windows)
            ):
                cadence_type = "sparse"
            else:
                cadence_type = "bounded"

            beats = sorted(window.earliest_beat for window in phase_windows)
            max_gap = (
                max(
                    [
                        max(0, beats[0]),
                        max(0, phase.max_auto_beats - beats[-1]),
                        *(
                            max(0, right - left - 1)
                            for left, right in zip(
                                beats, beats[1:], strict=False
                            )
                        ),
                    ]
                )
                if beats
                else phase.max_auto_beats + 1
            )
            long_without = (
                ProofState.UNKNOWN
                if conditional
                else ProofState.YES
                if max_gap >= CADENCE_LONG_GAP_HEURISTIC_BEATS
                else ProofState.NO
            )
            cadence_span = max(
                1, phase.max_auto_beats + 1
            )
            dense_enough = (
                len(phase_windows) * CADENCE_DENSE_WINDOWS_DENOMINATOR
                >= cadence_span * CADENCE_DENSE_WINDOWS_NUMERATOR
            )
            dense_non_rapid = (
                ProofState.UNKNOWN
                if conditional
                else ProofState.YES
                if not phase.rapid_decision_allowed
                and len(phase_windows) > 1
                and dense_enough
                else ProofState.NO
            )
            rapid_density = (
                ProofState.NO
                if not phase.rapid_decision_allowed
                else ProofState.UNKNOWN
                if conditional
                else ProofState.YES
                if dense_enough
                else ProofState.NO
            )
            if long_without is ProofState.YES:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "DECISION_GAP_LONG_HEURISTIC",
                        "Heuristic: the declared cadence can leave a long interval without a choice.",
                        "phase",
                        phase.phase_id,
                        {
                            "heuristic": True,
                            "gap_beats": max_gap,
                            "threshold_beats": CADENCE_LONG_GAP_HEURISTIC_BEATS,
                        },
                    )
                )
            if dense_non_rapid is ProofState.YES:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "DECISION_DENSITY_HIGH_NON_RAPID_HEURISTIC",
                        "Heuristic: a non-rapid phase declares tightly spaced choices.",
                        "phase",
                        phase.phase_id,
                        {
                            "heuristic": True,
                            "density_numerator": CADENCE_DENSE_WINDOWS_NUMERATOR,
                            "density_denominator": CADENCE_DENSE_WINDOWS_DENOMINATOR,
                        },
                    )
                )
            if phase.rapid_decision_allowed and rapid_density is ProofState.NO:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "RAPID_DECISION_DENSITY_LOW_HEURISTIC",
                        "Heuristic: a rapid phase does not declare a high choice density.",
                        "phase",
                        phase.phase_id,
                        {
                            "heuristic": True,
                            "density_numerator": CADENCE_DENSE_WINDOWS_NUMERATOR,
                            "density_denominator": CADENCE_DENSE_WINDOWS_DENOMINATOR,
                        },
                    )
                )
            results.append(
                DecisionCadenceAnalysis(
                    phase_id=phase.phase_id,
                    window_count=len(phase_windows),
                    cadence_type=cadence_type,
                    rapid_decision_allowed=phase.rapid_decision_allowed,
                    min_auto_beats=phase.min_auto_beats,
                    max_auto_beats=phase.max_auto_beats,
                    repeatable_window_count=repeatable,
                    long_without_choice=long_without,
                    dense_non_rapid_choices=dense_non_rapid,
                    rapid_has_high_choice_density=rapid_density,
                )
            )
        return tuple(results)

    def _clues(
        self,
        definition: ScenarioDefinition,
        reachable: frozenset[str],
        diagnostics: list[ScenarioDiagnostic],
    ) -> tuple[ClueAnalysis, ...]:
        producers: dict[str, list[Any]] = defaultdict(list)
        for rule in definition.narrative_outcome_rules:
            for effect in rule.effects:
                for clue_id in effect.discovered_clue_ids:
                    clue = definition.clue(clue_id)
                    if effect.event_type in clue.source_event_types:
                        producers[clue_id].append(rule)
        facts = {fact.fact_id: fact for fact in definition.facts}
        results: list[ClueAnalysis] = []
        for clue in sorted(definition.clues, key=lambda item: item.clue_id):
            visibilities = {facts[item].visibility for item in clue.supports_fact_ids}
            visibility_class = (
                "public"
                if FactVisibility.PLAYER_KNOWN in visibilities
                else "discoverable"
                if FactVisibility.DISCOVERABLE in visibilities
                else "hidden"
            )
            source_rules = producers.get(clue.clue_id, [])
            source_phases = {
                phase_id
                for rule in source_rules
                for phase_id in rule.allowed_phase_ids
            }
            has_source = bool(source_rules)
            structurally_reachable = bool(
                source_phases & set(clue.allowed_phase_ids) & set(reachable)
            )
            condition_proof = (
                self._clue_source_condition_satisfiability(
                    definition,
                    clue_id=clue.clue_id,
                    source_rules=source_rules,
                    reachable=reachable,
                )
                if structurally_reachable
                else ProofState.NO
            )
            guaranteed = (
                ProofState.UNKNOWN
                if structurally_reachable
                and condition_proof is not ProofState.NO
                else ProofState.NO
            )
            if not has_source:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLUE_NO_DECLARED_DISCOVERY_PRODUCER",
                        "No outcome template declares a matching discovery producer for this clue.",
                        "clue",
                        clue.clue_id,
                    )
                )
            elif not structurally_reachable:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLUE_SOURCE_UNREACHABLE",
                        "Declared discovery producers do not overlap a structurally reachable allowed phase.",
                        "clue",
                        clue.clue_id,
                    )
                )
            results.append(
                ClueAnalysis(
                    clue_id=clue.clue_id,
                    visibility_class=visibility_class,
                    has_declared_source=has_source,
                    source_structurally_reachable=structurally_reachable,
                    source_condition_satisfiable_unknown=condition_proof,
                    guaranteed_discoverable=guaranteed,
                    producer_types=(
                        ("narrative_outcome_rule",) if has_source else ()
                    ),
                )
            )
        return tuple(results)

    def _clue_source_condition_satisfiability(
        self,
        definition: ScenarioDefinition,
        *,
        clue_id: str,
        source_rules: list[Any],
        reachable: frozenset[str],
    ) -> ProofState:
        clue = definition.clue(clue_id)
        phase_map = {phase.phase_id: phase for phase in definition.phases}
        locations = {
            location.location_id: location for location in definition.locations
        }
        for rule in source_rules:
            candidate_phases = (
                set(rule.allowed_phase_ids)
                & set(clue.allowed_phase_ids)
                & set(reachable)
            )
            if not candidate_phases:
                continue
            if rule.required_current_decision_ids and not any(
                set(rule.required_current_decision_ids)
                & set(phase_map[phase_id].decision_window_ids)
                for phase_id in candidate_phases
            ):
                continue
            if any(
                not (
                    self._clue_declared_source_phases(
                        definition,
                        required_clue_id,
                    )
                    & set(reachable)
                )
                for required_clue_id in rule.required_clue_ids
            ):
                continue
            if rule.required_visible_npc_definition_ids and not any(
                set(rule.required_visible_npc_definition_ids)
                <= {
                    entity_id
                    for location_id in phase_map[phase_id].visible_location_ids
                    for entity_id in locations[location_id].visible_entity_ids
                }
                for phase_id in candidate_phases
            ):
                continue
            fact_impossible = False
            for requirement in rule.required_fact_values:
                fact = definition.fact(requirement.fact_id)
                if fact.kind is FactKind.FIXED and not json_values_equal(
                    fact.value, requirement.value
                ):
                    fact_impossible = True
                    break
            if fact_impossible:
                continue
            # Player intent, model-selected outcome, prerequisite clues, and
            # non-fixed fact state cannot be proven from the static catalog.
            return ProofState.UNKNOWN
        return ProofState.NO

    def _facts(
        self,
        definition: ScenarioDefinition,
        diagnostics: list[ScenarioDiagnostic],
    ) -> FactAnalysis:
        counts = {kind.value: 0 for kind in FactKind}
        for fact in definition.facts:
            counts[fact.kind.value] += 1
        deferred_sources = {
            update.fact_id
            for rule in definition.narrative_outcome_rules
            for effect in rule.effects
            for update in effect.deferred_bindings
        }
        mutable_sources = {
            update.fact_id
            for rule in definition.narrative_outcome_rules
            for effect in rule.effects
            for update in effect.mutable_fact_updates
        }
        unbindable = tuple(
            sorted(
                fact.fact_id
                for fact in definition.facts
                if fact.kind is FactKind.DEFERRED and fact.fact_id not in deferred_sources
            )
        )
        unchangeable = tuple(
            sorted(
                fact.fact_id
                for fact in definition.facts
                if fact.kind is FactKind.MUTABLE and fact.fact_id not in mutable_sources
            )
        )
        for fact_id in unbindable:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.WARNING,
                    "DEFERRED_FACT_NO_DECLARED_BINDING",
                    "No outcome template declares a legal binding for this DEFERRED fact.",
                    "fact",
                    fact_id,
                )
            )
        for fact_id in unchangeable:
            diagnostics.append(
                _diagnostic(
                    DiagnosticSeverity.WARNING,
                    "MUTABLE_FACT_NO_DECLARED_UPDATE",
                    "No outcome template declares a legal update for this MUTABLE fact.",
                    "fact",
                    fact_id,
                )
            )
        return FactAnalysis(
            counts_by_kind={key: counts[key] for key in sorted(counts)},
            unbindable_deferred_fact_ids=unbindable,
            unchangeable_mutable_fact_ids=unchangeable,
        )

    @staticmethod
    def _clue_declared_source_phases(
        definition: ScenarioDefinition,
        clue_id: str,
    ) -> set[str]:
        clue = definition.clue(clue_id)
        return {
            phase_id
            for rule in definition.narrative_outcome_rules
            if any(
                clue_id in effect.discovered_clue_ids
                and effect.event_type in clue.source_event_types
                for effect in rule.effects
            )
            for phase_id in rule.allowed_phase_ids
            if phase_id in clue.allowed_phase_ids
        }

    def _clock_sources(
        self,
        definition: ScenarioDefinition,
        *,
        reachable: frozenset[str] | None = None,
    ) -> dict[str, list[int]]:
        sources: dict[str, list[int]] = {clock.clock_id: [] for clock in definition.threat_clocks}
        for phase in definition.phases:
            if reachable is not None and phase.phase_id not in reachable:
                continue
            for advance in phase.auto_beat_clock_advances:
                sources[advance.clock_id].append(advance.amount)
            for cost in phase.action_time_costs:
                for advance in cost.clock_advances:
                    sources[advance.clock_id].append(advance.amount)
        return sources

    def _clocks(
        self,
        definition: ScenarioDefinition,
        reachable: frozenset[str],
        diagnostics: list[ScenarioDiagnostic],
    ) -> tuple[ClockAnalysis, ...]:
        results: list[ClockAnalysis] = []
        signatures: dict[tuple[Any, ...], list[str]] = defaultdict(list)
        for clock in sorted(definition.threat_clocks, key=lambda item: item.clock_id):
            action_amounts = [
                advance.amount
                for phase in definition.phases
                for cost in phase.action_time_costs
                for advance in cost.clock_advances
                if advance.clock_id == clock.clock_id
            ]
            auto_amounts = [
                advance.amount
                for phase in definition.phases
                for advance in phase.auto_beat_clock_advances
                if advance.clock_id == clock.clock_id
            ]
            source_amounts = [*action_amounts, *auto_amounts]
            reachable_source_amounts = [
                advance.amount
                for phase in definition.phases
                if phase.phase_id in reachable
                for advance in phase.auto_beat_clock_advances
                if advance.clock_id == clock.clock_id
            ] + [
                advance.amount
                for phase in definition.phases
                if phase.phase_id in reachable
                for cost in phase.action_time_costs
                for advance in cost.clock_advances
                if advance.clock_id == clock.clock_id
            ]
            unreachable_thresholds = tuple(
                threshold.threshold
                for threshold in clock.thresholds
                if threshold.threshold > clock.initial
                and not reachable_source_amounts
            )
            if not source_amounts:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLOCK_NO_PROGRESSION_SOURCE",
                        "The clock has no declared action-cost or automatic progression source.",
                        "clock",
                        clock.clock_id,
                    )
                )
            elif not reachable_source_amounts:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLOCK_SOURCE_STRUCTURALLY_UNREACHABLE",
                        "Declared clock progression sources occur only in structurally unreachable phases.",
                        "clock",
                        clock.clock_id,
                    )
                )
            for threshold in unreachable_thresholds:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLOCK_THRESHOLD_UNREACHABLE",
                        "The threshold is above the initial value but the clock has no structurally reachable progression source.",
                        "clock",
                        clock.clock_id,
                        {"threshold": threshold},
                    )
                )
            signature = (
                clock.minimum,
                clock.maximum,
                clock.initial,
                tuple(sorted(action_amounts)),
                tuple(sorted(auto_amounts)),
            )
            signatures[signature].append(clock.clock_id)
            results.append(
                ClockAnalysis(
                    clock_id=clock.clock_id,
                    minimum=clock.minimum,
                    maximum=clock.maximum,
                    initial=clock.initial,
                    thresholds=tuple(item.threshold for item in clock.thresholds),
                    player_visible=clock.player_visible,
                    minimum_declared_action_cost=min(action_amounts, default=None),
                    maximum_declared_action_cost=max(action_amounts, default=None),
                    minimum_declared_auto_advance=min(auto_amounts, default=None),
                    maximum_declared_auto_advance=max(auto_amounts, default=None),
                    has_declared_progression_source=bool(source_amounts),
                    source_structurally_reachable=bool(reachable_source_amounts),
                    progression_condition_satisfiable_unknown=(
                        ProofState.UNKNOWN
                        if reachable_source_amounts
                        else ProofState.NO
                    ),
                    guaranteed_to_progress=(
                        ProofState.UNKNOWN
                        if reachable_source_amounts
                        else ProofState.NO
                    ),
                    unreachable_thresholds=unreachable_thresholds,
                )
            )
        for clock_ids in sorted(signatures.values()):
            if len(clock_ids) > 1:
                diagnostics.append(
                    _diagnostic(
                        DiagnosticSeverity.WARNING,
                        "CLOCK_BUDGETS_POSSIBLY_DUPLICATED",
                        "Multiple clocks share the same bounds and declared advance amounts; semantic duplication is unknown.",
                        "clock_group",
                        clock_ids[0],
                        {"clock_count": len(clock_ids)},
                    )
                )
        return tuple(results)


def _diagnostic(
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    subject_type: str,
    subject_id: str,
    metadata: dict[str, Any] | None = None,
) -> ScenarioDiagnostic:
    return ScenarioDiagnostic(
        severity=severity,
        code=code,
        message=message,
        subject_type=subject_type,
        subject_id=subject_id,
        metadata=metadata or {},
    )


def _finalize_diagnostics(
    diagnostics: list[ScenarioDiagnostic],
) -> tuple[ScenarioDiagnostic, ...]:
    order = {
        DiagnosticSeverity.ERROR: 0,
        DiagnosticSeverity.WARNING: 1,
        DiagnosticSeverity.INFO: 2,
    }
    sorted_diagnostics = sorted(
        diagnostics,
        key=lambda item: (
            order[item.severity],
            item.code,
            item.subject_type,
            item.subject_id,
        ),
    )
    if len(sorted_diagnostics) <= MAX_DIAGNOSTICS:
        return tuple(sorted_diagnostics)
    limited = sorted_diagnostics[: MAX_DIAGNOSTICS - 1]
    limited.append(
        _diagnostic(
            DiagnosticSeverity.WARNING,
            "DIAGNOSTIC_LIMIT_REACHED",
            "Additional diagnostics were omitted because the output limit was reached.",
            "scenario",
            "diagnostic-limit",
            {"limit": MAX_DIAGNOSTICS},
        )
    )
    return tuple(limited)


def _diagnostic_counts(
    diagnostics: tuple[ScenarioDiagnostic, ...],
) -> DiagnosticCounts:
    return DiagnosticCounts(
        error=sum(item.severity is DiagnosticSeverity.ERROR for item in diagnostics),
        warning=sum(item.severity is DiagnosticSeverity.WARNING for item in diagnostics),
        info=sum(item.severity is DiagnosticSeverity.INFO for item in diagnostics),
    )


def _list_metrics(value: Any) -> tuple[int, int]:
    list_count = 0
    item_count = 0
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            list_count += 1
            item_count += len(current)
            stack.extend(current)
        elif isinstance(current, dict):
            stack.extend(current.values())
    return list_count, item_count
