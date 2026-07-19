from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json

from deviation_protocol.domain.decision_cadence import DecisionCadencePolicy
from deviation_protocol.domain.facts import (
    FactKind,
    FactVisibility,
    StoryFact,
    StoryMutation,
    StoryMutationError,
    StoryMutationValidator,
)
from deviation_protocol.domain.narrative import (
    AllowedCustomActionConstraints,
    NarrativeFrame,
    NpcKnowledgeFrame,
    RenderableFact,
    SuggestedAction,
    VerifiedEventFrame,
    VisibleClock,
)
from deviation_protocol.domain.scenario import (
    DecisionWindowDefinition,
    EndingStatus,
    FrameMode,
    ScenarioDefinition,
    TransitionDefinition,
    TransitionTrigger,
)
from deviation_protocol.domain.scenario_rules import DeclarativeConditionEvaluator
from deviation_protocol.domain.scenario_runtime import (
    MAX_APPLIED_SCENARIO_EVENTS,
    MAX_DECISIONS_MADE,
    ScenarioRuntimeState,
    VerifiedScenarioEvent,
)
from deviation_protocol.domain.state import GameState


class StoryDirectorError(ValueError):
    """A verified result or scenario state cannot be advanced safely."""


@dataclass(frozen=True, slots=True)
class _GeneratedScenarioEvent:
    event_id: str
    event_type: str
    expose_in_frame: bool

    def as_frame(self) -> VerifiedEventFrame:
        return VerifiedEventFrame(event_id=self.event_id, event_type=self.event_type)


@dataclass(frozen=True, slots=True)
class StoryDirectorResult:
    candidate_state: GameState
    frame: NarrativeFrame
    generated_events: tuple[VerifiedEventFrame, ...] = ()


class DeterministicStoryDirector:
    def __init__(
        self,
        *,
        condition_evaluator: DeclarativeConditionEvaluator | None = None,
        cadence_policy: DecisionCadencePolicy | None = None,
    ) -> None:
        self._conditions = condition_evaluator or DeclarativeConditionEvaluator()
        self._cadence = cadence_policy or DecisionCadencePolicy(self._conditions)

    def start_scenario(
        self,
        state: GameState,
        definition: ScenarioDefinition,
        *,
        profession_tags: Iterable[str] = (),
    ) -> StoryDirectorResult:
        if state.scenario_runtime is not None:
            raise StoryDirectorError("game state already has an active scenario runtime")
        if state.content_version != definition.content_version:
            raise StoryDirectorError("game state and scenario content versions do not match")
        tags = self._profession_tags(definition, profession_tags)
        candidate = deepcopy(state)
        candidate.schema_version = 2
        candidate.scenario_runtime = ScenarioRuntimeState.from_definition(definition)
        candidate.scenario_runtime.validate_against(definition)
        self._open_decision(candidate.scenario_runtime, definition, ())
        frame = self._build_frame(candidate, definition, (), tags)
        return StoryDirectorResult(candidate, frame)

    def plan_initial_frame(
        self,
        state: GameState,
        definition: ScenarioDefinition,
        *,
        profession_tags: Iterable[str] = (),
    ) -> NarrativeFrame:
        tags = self._profession_tags(definition, profession_tags)
        runtime = self._runtime(state, definition)
        if (
            runtime.current_phase_id != definition.initial_phase_id
            or runtime.phase_beat_index != 0
            or runtime.decisions_made
        ):
            raise StoryDirectorError("initial frame can only be planned at scenario start")
        self._reject_unrecorded_decision(runtime, definition)
        return self._build_frame(state, definition, (), tags)

    def plan_frame(
        self,
        state: GameState,
        definition: ScenarioDefinition,
        *,
        profession_tags: Iterable[str] = (),
    ) -> NarrativeFrame:
        tags = self._profession_tags(definition, profession_tags)
        runtime = self._runtime(state, definition)
        self._reject_unrecorded_decision(runtime, definition)
        return self._build_frame(state, definition, (), tags)

    def advance_after_verified_result(
        self,
        state: GameState,
        definition: ScenarioDefinition,
        verified_events: Sequence[VerifiedScenarioEvent] = (),
        *,
        profession_tags: Iterable[str] = (),
    ) -> StoryDirectorResult:
        events = tuple(verified_events)
        if len(events) > 64:
            raise StoryDirectorError("one advancement exceeds the verified event limit")
        if any(
            not isinstance(event, VerifiedScenarioEvent) or not event.is_authentic()
            for event in events
        ):
            raise StoryDirectorError(
                "scenario events must come from the server verification boundary"
            )
        original_runtime = self._runtime(state, definition)
        if original_runtime.ending_status is not EndingStatus.ACTIVE:
            raise StoryDirectorError("ended scenario cannot advance")
        self._reject_duplicate_event_ids(events)
        replayed_ids = sorted(
            {event.event_id for event in events}
            & set(original_runtime.applied_event_ids)
        )
        if replayed_ids:
            raise StoryDirectorError(
                f"verified scenario event was already applied: {', '.join(replayed_ids)}"
            )
        if (
            len(original_runtime.applied_event_ids) + len(events)
            > MAX_APPLIED_SCENARIO_EVENTS
        ):
            raise StoryDirectorError("verified scenario event history limit reached")
        tags = self._profession_tags(definition, profession_tags)

        if events and all(event.local_query for event in events):
            frame = self._build_frame(state, definition, events, tags)
            return StoryDirectorResult(deepcopy(state), frame)
        if any(event.local_query for event in events):
            raise StoryDirectorError("local query events cannot be mixed with state changes")
        if original_runtime.current_decision_id is not None and not any(
            event.resolves_current_decision for event in events
        ):
            raise StoryDirectorError("an open decision requires a verified player response")

        candidate = deepcopy(state)
        runtime = self._runtime(candidate, definition)
        phase = definition.phase(runtime.current_phase_id)
        action_events = [event for event in events if event.action_type is not None]
        if len(action_events) > 1:
            raise StoryDirectorError("one advancement can contain at most one timed action")

        resolved_decision = False
        generated: list[_GeneratedScenarioEvent] = []
        for event in events:
            resolved_decision |= self._apply_verified_event(
                runtime, definition, event, tags
            )
        runtime.applied_event_ids = (
            *runtime.applied_event_ids,
            *(event.event_id for event in events),
        )
        runtime.phase_beat_index += 1
        if action_events:
            action_type = action_events[0].action_type
            assert action_type is not None
            if action_type not in phase.allowed_action_types:
                raise StoryDirectorError(f"action type {action_type!r} is not allowed in phase")
            cost = next(
                (item for item in phase.action_time_costs if item.action_type == action_type), None
            )
            if cost is not None:
                generated.extend(self._advance_clocks(runtime, definition, cost.clock_advances))
        elif not events:
            generated.extend(
                self._advance_clocks(runtime, definition, phase.auto_beat_clock_advances)
            )

        generated.extend(self._complete_clue_groups(runtime, definition))
        event_types = tuple(event.event_type for event in events) + tuple(
            event.event_type for event in generated
        )
        self._apply_transition(runtime, definition, event_types, resolved_decision)
        self._apply_ending(runtime, definition, event_types)
        self._open_decision(runtime, definition, event_types)
        phase = definition.phase(runtime.current_phase_id)
        if (
            runtime.ending_status is EndingStatus.ACTIVE
            and runtime.current_decision_id is None
            and runtime.phase_beat_index >= phase.max_auto_beats
            and not self._eligible_transition(runtime, definition, event_types, resolved_decision)
        ):
            raise StoryDirectorError("phase reached max_auto_beats without a decision or transition")
        if runtime.ending_status is EndingStatus.ACTIVE and phase.terminal:
            raise StoryDirectorError("terminal phase was reached without a matching ending")
        try:
            runtime.validate_against(definition)
        except (TypeError, ValueError) as exc:
            raise StoryDirectorError("candidate scenario runtime is invalid") from exc

        visible_frame_events = tuple(
            [
                VerifiedEventFrame(event_id=item.event_id, event_type=item.event_type)
                for item in events
                if item.expose_in_frame
            ]
            + [item.as_frame() for item in generated if item.expose_in_frame]
        )
        if len(visible_frame_events) > 128:
            raise StoryDirectorError("visible scenario event projection exceeds its limit")
        frame = self._build_frame(candidate, definition, visible_frame_events, tags)
        return StoryDirectorResult(
            candidate,
            frame,
            tuple(item.as_frame() for item in generated),
        )

    def _open_decision(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
        event_types: Iterable[str],
    ) -> None:
        if runtime.ending_status is not EndingStatus.ACTIVE or runtime.current_decision_id is not None:
            return
        window = self._cadence.select_window(
            definition=definition, runtime=runtime, event_types=event_types
        )
        if window is not None:
            runtime.current_decision_id = window.decision_id

    def _reject_unrecorded_decision(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
    ) -> None:
        if (
            runtime.ending_status is EndingStatus.ACTIVE
            and runtime.current_decision_id is None
            and self._cadence.select_window(
                definition=definition,
                runtime=runtime,
                event_types=(),
            )
            is not None
        ):
            raise StoryDirectorError(
                "eligible decision is missing from scenario runtime state"
            )

    @staticmethod
    def _runtime(state: GameState, definition: ScenarioDefinition) -> ScenarioRuntimeState:
        if state.scenario_runtime is None:
            raise StoryDirectorError("game state has no scenario runtime")
        if state.content_version != definition.content_version:
            raise StoryDirectorError("game state and scenario content versions do not match")
        try:
            state.scenario_runtime.validate_against(definition)
        except (TypeError, ValueError) as exc:
            raise StoryDirectorError("scenario runtime is invalid for its definition") from exc
        return state.scenario_runtime

    @staticmethod
    def _profession_tags(
        definition: ScenarioDefinition, profession_tags: Iterable[str]
    ) -> frozenset[str]:
        tags = frozenset(profession_tags)
        unknown_tags = tags - set(definition.available_profession_tags)
        if unknown_tags:
            raise StoryDirectorError(
                f"unknown profession tags: {', '.join(sorted(unknown_tags))}"
            )
        return tags

    @staticmethod
    def _reject_duplicate_event_ids(events: Sequence[VerifiedScenarioEvent]) -> None:
        counts = Counter(event.event_id for event in events)
        duplicates = sorted(event_id for event_id, count in counts.items() if count > 1)
        if duplicates:
            raise StoryDirectorError(f"duplicate verified event ID: {', '.join(duplicates)}")
        if any(
            event.event_id.startswith(("clock.", "cluegroup."))
            for event in events
        ):
            raise StoryDirectorError(
                "verified event ID uses a StoryDirector-reserved namespace"
            )

    def _apply_verified_event(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
        event: VerifiedScenarioEvent,
        profession_tags: frozenset[str],
    ) -> bool:
        phase = definition.phase(runtime.current_phase_id)
        validator = StoryMutationValidator(
            dynamic_fact_limit=definition.dynamic_fact_limit,
            dynamic_key_max_length=definition.dynamic_fact_key_max_length,
            dynamic_value_max_length=definition.dynamic_fact_value_max_length,
        )
        known_clue_ids = {item.clue_id for item in definition.clues}
        for clue_id in event.discovered_clue_ids:
            if clue_id not in known_clue_ids:
                raise StoryDirectorError(f"clue {clue_id!r} is not discoverable in this phase")
            clue = definition.clue(clue_id)
            if clue_id not in phase.allowed_clue_ids or phase.phase_id not in clue.allowed_phase_ids:
                raise StoryDirectorError(f"clue {clue_id!r} is not discoverable in this phase")
            if event.event_type not in clue.source_event_types:
                raise StoryDirectorError(f"event cannot discover clue {clue_id!r}")
            if clue.required_any_profession_tags and not (
                profession_tags & set(clue.required_any_profession_tags)
            ):
                raise StoryDirectorError(f"profession tag required for clue {clue_id!r}")
            runtime.discovered_clue_ids = runtime.discovered_clue_ids | {clue_id}

        for binding in event.deferred_bindings:
            try:
                fact = definition.fact(binding.fact_id)
            except StopIteration as exc:
                raise StoryDirectorError("verified event references an unknown fact") from exc
            current = StoryFact(
                binding.fact_id,
                FactKind.DEFERRED,
                runtime.bound_deferred_facts.get(binding.fact_id),
                visibility=fact.visibility,
            )
            try:
                validated = validator.validate_deferred_binding(
                    current,
                    StoryMutation(
                        binding.fact_id,
                        binding.value,
                        causal_event_id=event.event_id,
                    ),
                    allowed_candidates=fact.deferred_candidates,
                )
            except StoryMutationError as exc:
                raise StoryDirectorError(str(exc)) from exc
            runtime.bound_deferred_facts[binding.fact_id] = validated.value

        for update in event.mutable_fact_updates:
            try:
                fact = definition.fact(update.fact_id)
            except StopIteration as exc:
                raise StoryDirectorError("verified event references an unknown fact") from exc
            current_value = runtime.mutable_fact_values.get(update.fact_id)
            current = StoryFact(
                update.fact_id,
                fact.kind,
                current_value,
                visibility=fact.visibility,
            )
            try:
                validated = validator.validate_mutable_transition(
                    current,
                    StoryMutation(
                        update.fact_id,
                        update.value,
                        causal_event_id=event.event_id,
                    ),
                    causal_event_type=event.event_type,
                    allowed_transitions=(
                        (
                            transition.from_value,
                            transition.to_value,
                            transition.event_type,
                        )
                        for transition in fact.mutable_transitions
                    ),
                )
            except StoryMutationError as exc:
                raise StoryDirectorError(str(exc)) from exc
            runtime.mutable_fact_values[update.fact_id] = validated.value

        declared_ids = {fact.fact_id for fact in definition.facts}
        for update in event.dynamic_fact_updates:
            current = {
                key: StoryFact(key, FactKind.DYNAMIC, value, visibility=FactVisibility.PLAYER_KNOWN)
                for key, value in runtime.dynamic_facts.items()
            }
            validated = validator.validate_dynamic_collection(
                current,
                StoryMutation(
                    update.fact_id,
                    update.value,
                    kind=FactKind.DYNAMIC,
                    causal_event_id=event.event_id,
                ),
                reserved_fact_ids=declared_ids,
            )
            runtime.dynamic_facts[validated.key] = validated.value

        location_ids = {location.location_id for location in definition.locations}
        for location_id in event.opened_location_ids:
            if location_id not in location_ids:
                raise StoryDirectorError("verified event opens unknown location")
            runtime.opened_location_ids = runtime.opened_location_ids | {location_id}
        if event.new_location_id is not None:
            if event.new_location_id not in runtime.opened_location_ids:
                raise StoryDirectorError("cannot move to a location that is not open")
            if event.new_location_id not in phase.visible_location_ids:
                raise StoryDirectorError("cannot move to a location outside the current phase")
            runtime.current_location_id = event.new_location_id

        if event.resolves_current_decision:
            if runtime.current_decision_id is None:
                raise StoryDirectorError("verified result cannot resolve a missing decision")
            if event.decision_id != runtime.current_decision_id:
                raise StoryDirectorError(
                    "verified result cannot resolve a different decision"
                )
            if len(runtime.decisions_made) >= MAX_DECISIONS_MADE:
                raise StoryDirectorError("completed decision history limit reached")
            runtime.decisions_made = (*runtime.decisions_made, runtime.current_decision_id)
            runtime.current_decision_id = None
            return True
        return False

    @staticmethod
    def _advance_clocks(
        runtime, definition, advances
    ) -> list[_GeneratedScenarioEvent]:
        generated: list[_GeneratedScenarioEvent] = []
        for advance in advances:
            clock_definition = definition.clock(advance.clock_id)
            clock = runtime.threat_clocks[advance.clock_id]
            old = clock.value
            clock.value = min(clock_definition.maximum, old + advance.amount)
            for threshold in sorted(
                clock_definition.thresholds, key=lambda item: item.threshold
            ):
                if old < threshold.threshold <= clock.value and threshold.threshold not in clock.triggered_thresholds:
                    clock.triggered_thresholds = clock.triggered_thresholds | {threshold.threshold}
                    generated.append(
                        _GeneratedScenarioEvent(
                            event_id=f"clock.{clock.clock_id}.{threshold.threshold}",
                            event_type=threshold.event_type,
                            expose_in_frame=clock_definition.player_visible,
                        )
                    )
        return generated

    @staticmethod
    def _complete_clue_groups(
        runtime, definition
    ) -> list[_GeneratedScenarioEvent]:
        generated: list[_GeneratedScenarioEvent] = []
        for group in definition.clue_groups:
            if group.clue_group_id in runtime.completed_clue_group_ids:
                continue
            count = len(set(group.clue_ids) & runtime.discovered_clue_ids)
            if count >= group.required_count:
                runtime.completed_clue_group_ids = runtime.completed_clue_group_ids | {
                    group.clue_group_id
                }
                generated.append(
                    _GeneratedScenarioEvent(
                        event_id=f"cluegroup.{group.clue_group_id}",
                        event_type=group.completion_event_type,
                        expose_in_frame=True,
                    )
                )
        return generated

    def _eligible_transition(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
        event_types: Iterable[str],
        resolved_decision: bool,
    ) -> TransitionDefinition | None:
        phase = definition.phase(runtime.current_phase_id)
        candidates: list[tuple[int, str, TransitionDefinition]] = []
        for transition in phase.transitions:
            if transition.max_uses is not None and runtime.transition_use_counts.get(
                transition.transition_id, 0
            ) >= transition.max_uses:
                continue
            if transition.trigger is TransitionTrigger.VERIFIED_EVENT and not tuple(event_types):
                continue
            if transition.trigger is TransitionTrigger.DECISION and not resolved_decision:
                continue
            if transition.trigger is TransitionTrigger.AUTOMATIC and runtime.phase_beat_index < phase.min_auto_beats:
                continue
            if self._conditions.all_match(
                transition.conditions,
                definition=definition,
                runtime=runtime,
                event_types=event_types,
            ):
                target = definition.phase(transition.target_phase_id)
                if self._conditions.all_match(
                    target.entry_conditions,
                    definition=definition,
                    runtime=runtime,
                    event_types=event_types,
                ):
                    candidates.append(
                        (transition.priority, transition.transition_id, transition)
                    )
        return min(candidates, default=(0, "", None))[2]

    def _apply_transition(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
        event_types: Iterable[str],
        resolved_decision: bool,
    ) -> None:
        transition = self._eligible_transition(runtime, definition, event_types, resolved_decision)
        if transition is None:
            return
        runtime.transition_use_counts[transition.transition_id] = (
            runtime.transition_use_counts.get(transition.transition_id, 0) + 1
        )
        runtime.current_phase_id = transition.target_phase_id
        runtime.phase_beat_index = 0
        runtime.current_decision_id = None
        visits = runtime.phase_visit_counts.get(transition.target_phase_id, 0) + 1
        target = definition.phase(transition.target_phase_id)
        if target.max_visits is not None and visits > target.max_visits:
            raise StoryDirectorError("phase visit limit exceeded")
        runtime.phase_visit_counts[transition.target_phase_id] = visits
        runtime.rapid_decision_mode = target.rapid_decision_allowed
        if runtime.current_location_id not in target.visible_location_ids:
            opened = [
                item for item in target.visible_location_ids if item in runtime.opened_location_ids
            ]
            if not opened:
                raise StoryDirectorError("target phase has no open visible location")
            runtime.current_location_id = opened[0]

    def _apply_ending(
        self,
        runtime: ScenarioRuntimeState,
        definition: ScenarioDefinition,
        event_types: Iterable[str],
    ) -> None:
        for ending in sorted(
            definition.endings, key=lambda item: (item.priority, item.ending_id)
        ):
            if self._conditions.all_match(
                ending.conditions,
                definition=definition,
                runtime=runtime,
                event_types=event_types,
            ):
                runtime.ending_status = ending.status
                runtime.ending_id = ending.ending_id
                runtime.current_decision_id = None
                return

    def _build_frame(
        self,
        state: GameState,
        definition: ScenarioDefinition,
        recent_events: Sequence[VerifiedScenarioEvent | VerifiedEventFrame],
        profession_tags: frozenset[str],
    ) -> NarrativeFrame:
        runtime = self._runtime(state, definition)
        phase = definition.phase(runtime.current_phase_id)
        visible_recent_events = tuple(
            event
            for event in recent_events
            if isinstance(event, VerifiedEventFrame) or event.expose_in_frame
        )
        event_types = tuple(event.event_type for event in visible_recent_events)
        window = (
            definition.decision_window(runtime.current_decision_id)
            if runtime.current_decision_id is not None
            else None
        )
        known_fact_ids = {
            fact.fact_id
            for fact in definition.facts
            if fact.visibility is FactVisibility.PLAYER_KNOWN
        }
        for clue_id in runtime.discovered_clue_ids:
            known_fact_ids.update(definition.clue(clue_id).supports_fact_ids)
        rendered = {
            fact_id: RenderableFact(
                fact_id=fact_id,
                value=self._conditions.fact_value(fact_id, definition, runtime),
            )
            for fact_id in sorted(known_fact_ids)
            if self._conditions.fact_value(fact_id, definition, runtime) is not None
        }
        must_ids = tuple(fact_id for fact_id in phase.must_render_fact_ids if fact_id in rendered)
        must = tuple(rendered[fact_id] for fact_id in must_ids)
        may = tuple(rendered[fact_id] for fact_id in sorted(set(rendered) - set(must_ids)))
        dynamic = tuple(
            RenderableFact(fact_id=key, value=value)
            for key, value in sorted(runtime.dynamic_facts.items())
        )

        location = next(item for item in definition.locations if item.location_id == runtime.current_location_id)
        visible_definition_ids = set(location.visible_entity_ids)
        visible_npcs = tuple(
            (npc_id, npc.definition_id)
            for npc_id, npc in sorted(state.npcs.items())
            if npc.definition_id in visible_definition_ids
        )
        visible_entities = tuple(npc_id for npc_id, _ in visible_npcs)
        references = {
            reference.npc_definition_id: reference
            for reference in definition.npc_references
        }
        npc_frames = []
        for npc_id, npc_definition_id in visible_npcs:
            reference = references[npc_definition_id]
            facts = tuple(
                RenderableFact(
                    fact_id=fact_id,
                    value=self._conditions.fact_value(fact_id, definition, runtime),
                )
                for fact_id in sorted(set(reference.known_fact_ids) & known_fact_ids)
                if self._conditions.fact_value(fact_id, definition, runtime) is not None
            )
            npc_frames.append(
                NpcKnowledgeFrame(
                    npc_id=npc_id,
                    npc_definition_id=npc_definition_id,
                    known_facts=facts,
                )
            )

        npc_runtime_ids: dict[str, tuple[str, ...]] = {}
        for npc_id, npc_definition_id in visible_npcs:
            npc_runtime_ids[npc_definition_id] = (
                *npc_runtime_ids.get(npc_definition_id, ()),
                npc_id,
            )
        decision_payload = self._decision_payload(
            window,
            profession_tags,
            npc_runtime_ids=npc_runtime_ids,
            npc_definition_ids=frozenset(references),
        )
        ended = runtime.ending_status is not EndingStatus.ACTIVE
        mode = (
            FrameMode.SETTLEMENT
            if ended
            else FrameMode.RAPID_DECISION
            if window is not None and runtime.rapid_decision_mode
            else FrameMode.DECISION
            if window is not None
            else FrameMode.FLOW
        )
        event_frames = tuple(
            item
            if isinstance(item, VerifiedEventFrame)
            else VerifiedEventFrame(event_id=item.event_id, event_type=item.event_type)
            for item in visible_recent_events
        )
        required_visible_events = tuple(
            event_type
            for event_type in phase.required_event_types
            if event_type in set(event_types)
        )
        draft = NarrativeFrame(
            frame_id="frame.pending",
            scenario_id=definition.scenario_id,
            phase_id=phase.phase_id,
            mode=mode,
            current_location_id=runtime.current_location_id,
            must_render_facts=must,
            may_render_facts=(*may, *dynamic),
            visible_entities=visible_entities,
            visible_clues=tuple(sorted(runtime.discovered_clue_ids & set(phase.allowed_clue_ids))),
            must_render_event_types=required_visible_events,
            recent_verified_events=event_frames,
            npc_knowledge=tuple(npc_frames),
            tone_hints=phase.tone_hints,
            target_length=definition.narrative_length.target,
            min_length=definition.narrative_length.minimum,
            max_length=definition.narrative_length.maximum,
            decision_required=window is not None,
            decision_id=window.decision_id if window is not None else None,
            decision_reason=window.reason if window is not None else None,
            suggested_actions=decision_payload[0],
            allowed_custom_action_constraints=decision_payload[1],
            stop_condition="SCENARIO_ENDED" if ended else "AWAIT_PLAYER" if window else "CONTINUE",
            player_visible_clocks=tuple(
                VisibleClock(
                    clock_id=clock.clock_id,
                    value=runtime.threat_clocks[clock.clock_id].value,
                    maximum=clock.maximum,
                )
                for clock in definition.threat_clocks
                if clock.player_visible
            ),
        )
        frame_seed = draft.model_dump(mode="json", exclude={"frame_id"})
        digest = sha256(
            json.dumps(
                frame_seed,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()[:24]
        return draft.model_copy(update={"frame_id": f"frame.{digest}"})

    @staticmethod
    def _decision_payload(
        window: DecisionWindowDefinition | None,
        profession_tags: frozenset[str],
        *,
        npc_runtime_ids: dict[str, tuple[str, ...]],
        npc_definition_ids: frozenset[str],
    ) -> tuple[tuple[SuggestedAction, ...], AllowedCustomActionConstraints | None]:
        if window is None:
            return (), None
        actions: list[SuggestedAction] = []
        for action in window.suggested_actions:
            if action.required_any_profession_tags and not (
                profession_tags & set(action.required_any_profession_tags)
            ):
                continue
            targets: list[str] = []
            unavailable_npc_target = False
            for target_id in action.target_ids:
                if target_id not in npc_definition_ids:
                    targets.append(target_id)
                    continue
                runtime_ids = npc_runtime_ids.get(target_id, ())
                if not runtime_ids:
                    unavailable_npc_target = True
                    break
                targets.extend(runtime_ids)
            if unavailable_npc_target:
                continue
            actions.append(
                SuggestedAction(
                    action_id=action.action_id,
                    action_type=action.action_type,
                    label_hint=action.label_hint,
                    target_ids=tuple(targets),
                )
            )
        if not actions:
            raise StoryDirectorError("decision has no action available to this character")
        constraints = window.custom_action_constraints
        return tuple(actions), AllowedCustomActionConstraints(
            allowed_action_types=constraints.allowed_action_types,
            max_description_length=constraints.max_description_length,
            must_target_visible_entity=constraints.must_target_visible_entity,
        )
