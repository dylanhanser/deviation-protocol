from __future__ import annotations

from enum import StrEnum
import json
import re
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_serializer,
    model_validator,
)

from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.json_values import (
    canonical_json_key,
    freeze_bounded_json_value,
    json_values_equal,
)
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.scenario import (
    EndingStatus,
    MAX_SCENARIO_COUNTER,
    ScenarioDefinition,
)


StrictBool = Annotated[bool, Field(strict=True)]
_VERIFIED_SCENARIO_EVENT_ISSUER = object()
_DYNAMIC_FACT_KEY = re.compile(r"^dynamic\.[A-Za-z0-9][A-Za-z0-9_.:-]*$")
MAX_APPLIED_SCENARIO_EVENTS = 1_024
MAX_NARRATIVE_OUTCOME_EVIDENCE = 1_024
MAX_DECISIONS_MADE = 1_024


class ScenarioRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ThreatClockState(ScenarioRuntimeModel):
    clock_id: DefinitionId
    value: Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)]
    triggered_thresholds: frozenset[
        Annotated[int, Field(strict=True, ge=0, le=MAX_SCENARIO_COUNTER)]
    ] = frozenset()

    @field_serializer("triggered_thresholds")
    def serialize_thresholds(self, value: frozenset[int]) -> list[int]:
        return sorted(value)


class NarrativeOutcomeEvidence(ScenarioRuntimeModel):
    """Private authoritative proof of one accepted narrative outcome shape."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_rule_id: DefinitionId
    outcome_result: NarrativeOutcomeResult
    scenario_event_type: DefinitionId
    npc_definition_ids: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_targets(self) -> NarrativeOutcomeEvidence:
        targets = tuple(sorted(self.npc_definition_ids))
        if len(targets) != len(set(targets)):
            raise ValueError("narrative outcome evidence repeats an NPC target")
        object.__setattr__(self, "npc_definition_ids", targets)
        return self

    def stable_key(self) -> tuple[str, str, str, tuple[str, ...]]:
        return (
            self.outcome_rule_id,
            self.outcome_result.value,
            self.scenario_event_type,
            self.npc_definition_ids,
        )


class ScenarioRuntimeState(ScenarioRuntimeModel):
    scenario_id: DefinitionId
    scenario_content_version: DefinitionId
    current_phase_id: DefinitionId
    phase_beat_index: Annotated[int, Field(strict=True, ge=0)] = 0
    current_location_id: DefinitionId
    discovered_clue_ids: frozenset[DefinitionId] = frozenset()
    completed_clue_group_ids: frozenset[DefinitionId] = frozenset()
    bound_deferred_facts: dict[DefinitionId, Any] = Field(default_factory=dict)
    mutable_fact_values: dict[DefinitionId, Any] = Field(default_factory=dict)
    dynamic_facts: dict[DefinitionId, Any] = Field(default_factory=dict)
    threat_clocks: dict[DefinitionId, ThreatClockState] = Field(default_factory=dict)
    opened_location_ids: frozenset[DefinitionId] = frozenset()
    current_decision_id: DefinitionId | None = None
    decisions_made: tuple[DefinitionId, ...] = ()
    rapid_decision_mode: StrictBool = False
    ending_status: EndingStatus = EndingStatus.ACTIVE
    ending_id: DefinitionId | None = None
    phase_visit_counts: dict[
        DefinitionId,
        Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)],
    ] = Field(default_factory=dict)
    transition_use_counts: dict[
        DefinitionId,
        Annotated[int, Field(strict=True, ge=1, le=MAX_SCENARIO_COUNTER)],
    ] = Field(default_factory=dict)
    applied_event_ids: tuple[DefinitionId, ...] = ()
    narrative_outcome_evidence: tuple[NarrativeOutcomeEvidence, ...] = ()

    @field_serializer(
        "discovered_clue_ids", "completed_clue_group_ids", "opened_location_ids"
    )
    def serialize_sets(self, value: frozenset[str]) -> list[str]:
        return sorted(value)

    @model_validator(mode="after")
    def validate_runtime_maps(self) -> ScenarioRuntimeState:
        for clock_id, clock in self.threat_clocks.items():
            if clock_id != clock.clock_id:
                raise ValueError("threat clock key must match clock_id")
        for name, values in (
            ("bound deferred fact", self.bound_deferred_facts),
            ("mutable fact", self.mutable_fact_values),
            ("dynamic fact", self.dynamic_facts),
        ):
            for key, value in values.items():
                values[key] = freeze_bounded_json_value(value, path=f"{name} {key!r}")
        return self

    @classmethod
    def from_definition(cls, definition: ScenarioDefinition) -> ScenarioRuntimeState:
        return cls(
            scenario_id=definition.scenario_id,
            scenario_content_version=definition.content_version,
            current_phase_id=definition.initial_phase_id,
            current_location_id=definition.initial_location_id,
            mutable_fact_values={
                fact.fact_id: fact.value
                for fact in definition.facts
                if fact.kind.value == "MUTABLE"
            },
            threat_clocks={
                clock.clock_id: ThreatClockState(
                    clock_id=clock.clock_id,
                    value=clock.initial,
                    triggered_thresholds=frozenset(
                        threshold.threshold
                        for threshold in clock.thresholds
                        if threshold.threshold <= clock.initial
                    ),
                )
                for clock in definition.threat_clocks
            },
            opened_location_ids=frozenset(
                location.location_id for location in definition.locations if location.initially_open
            )
            | frozenset((definition.initial_location_id,)),
            phase_visit_counts={definition.initial_phase_id: 1},
            rapid_decision_mode=definition.phase(
                definition.initial_phase_id
            ).rapid_decision_allowed,
        )

    def validate_against(self, definition: ScenarioDefinition) -> None:
        if self.ending_status is EndingStatus.ACTIVE and self.ending_id is not None:
            raise ValueError("active scenario cannot have an ending_id")
        if self.ending_status is not EndingStatus.ACTIVE and self.ending_id is None:
            raise ValueError("ended scenario requires ending_id")
        if self.scenario_id != definition.scenario_id:
            raise ValueError("runtime scenario_id does not match definition")
        if self.scenario_content_version != definition.content_version:
            raise ValueError("runtime scenario content version does not match definition")
        phase_ids = {item.phase_id for item in definition.phases}
        location_ids = {item.location_id for item in definition.locations}
        clue_ids = {item.clue_id for item in definition.clues}
        group_ids = {item.clue_group_id for item in definition.clue_groups}
        if self.current_phase_id not in phase_ids:
            raise ValueError("runtime current phase does not exist")
        phase = definition.phase(self.current_phase_id)
        if self.phase_beat_index > phase.max_auto_beats:
            raise ValueError("runtime phase beat exceeds the phase maximum")
        if self.current_location_id not in location_ids:
            raise ValueError("runtime current location does not exist")
        if not self.opened_location_ids <= location_ids:
            raise ValueError("runtime references unknown opened location")
        if not self.discovered_clue_ids <= clue_ids:
            raise ValueError("runtime references unknown clue")
        if not self.completed_clue_group_ids <= group_ids:
            raise ValueError("runtime references unknown clue group")
        expected_completed_groups = {
            group.clue_group_id
            for group in definition.clue_groups
            if len(set(group.clue_ids) & self.discovered_clue_ids)
            >= group.required_count
        }
        if self.completed_clue_group_ids != expected_completed_groups:
            raise ValueError("runtime completed clue groups do not match discovered clues")
        deferred_ids = {item.fact_id for item in definition.facts if item.kind.value == "DEFERRED"}
        mutable_ids = {item.fact_id for item in definition.facts if item.kind.value == "MUTABLE"}
        if not set(self.bound_deferred_facts) <= deferred_ids:
            raise ValueError("runtime contains undeclared deferred fact")
        for fact_id, value in self.bound_deferred_facts.items():
            fact = definition.fact(fact_id)
            if not any(
                json_values_equal(value, candidate)
                for candidate in fact.deferred_candidates
            ):
                raise ValueError("runtime deferred fact uses a disallowed candidate")
        if set(self.mutable_fact_values) != mutable_ids:
            raise ValueError("runtime mutable fact set does not match definition")
        for fact_id, value in self.mutable_fact_values.items():
            fact = definition.fact(fact_id)
            reachable = {canonical_json_key(fact.value)}
            changed = True
            while changed:
                changed = False
                for transition in fact.mutable_transitions:
                    if (
                        canonical_json_key(transition.from_value) in reachable
                        and canonical_json_key(transition.to_value) not in reachable
                    ):
                        reachable.add(canonical_json_key(transition.to_value))
                        changed = True
            if canonical_json_key(value) not in reachable:
                raise ValueError("runtime mutable fact value is unreachable")
        if any(not _DYNAMIC_FACT_KEY.fullmatch(key) for key in self.dynamic_facts):
            raise ValueError("runtime dynamic fact is outside dynamic.* namespace")
        if len(self.dynamic_facts) > definition.dynamic_fact_limit:
            raise ValueError("runtime dynamic fact count exceeds definition limit")
        declared_fact_ids = {item.fact_id for item in definition.facts}
        for key, value in self.dynamic_facts.items():
            if key in declared_fact_ids:
                raise ValueError("runtime dynamic fact overwrites a declared fact")
            if len(key) > definition.dynamic_fact_key_max_length:
                raise ValueError("runtime dynamic fact key exceeds definition limit")
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            if len(encoded) > definition.dynamic_fact_value_max_length:
                raise ValueError("runtime dynamic fact value exceeds definition limit")
        clocks = {item.clock_id: item for item in definition.threat_clocks}
        if set(self.threat_clocks) != set(clocks):
            raise ValueError("runtime threat clock set does not match definition")
        for clock_id, state in self.threat_clocks.items():
            clock = clocks[clock_id]
            if not clock.minimum <= state.value <= clock.maximum:
                raise ValueError("runtime threat clock value is outside bounds")
            known_thresholds = {item.threshold for item in clock.thresholds}
            if not state.triggered_thresholds <= known_thresholds:
                raise ValueError("runtime contains unknown triggered threshold")
            expected_thresholds = {
                item.threshold for item in clock.thresholds if item.threshold <= state.value
            }
            if state.triggered_thresholds != expected_thresholds:
                raise ValueError("runtime triggered thresholds do not match clock value")
        if not set(self.phase_visit_counts) <= phase_ids:
            raise ValueError("runtime phase visits reference unknown phase")
        if self.phase_visit_counts.get(self.current_phase_id, 0) < 1:
            raise ValueError("runtime current phase has no recorded visit")
        for phase_id, count in self.phase_visit_counts.items():
            maximum = definition.phase(phase_id).max_visits
            if maximum is not None and count > maximum:
                raise ValueError("runtime phase visit count exceeds definition limit")
        transition_ids = {
            item.transition_id for phase in definition.phases for item in phase.transitions
        }
        if not set(self.transition_use_counts) <= transition_ids:
            raise ValueError("runtime transition uses reference unknown transition")
        transitions = {
            item.transition_id: item
            for phase_definition in definition.phases
            for item in phase_definition.transitions
        }
        for transition_id, count in self.transition_use_counts.items():
            maximum = transitions[transition_id].max_uses
            if maximum is not None and count > maximum:
                raise ValueError("runtime transition use count exceeds definition limit")
        decision_ids = {item.decision_id for item in definition.decision_windows}
        if self.current_decision_id is not None:
            if self.current_decision_id not in decision_ids:
                raise ValueError("runtime current decision does not exist")
            if self.current_decision_id not in phase.decision_window_ids:
                raise ValueError("runtime current decision is not available in its phase")
        if not set(self.decisions_made) <= decision_ids:
            raise ValueError("runtime completed decisions reference unknown decisions")
        if len(self.decisions_made) > MAX_DECISIONS_MADE:
            raise ValueError("runtime completed decision history exceeds its limit")
        for decision_id in set(self.decisions_made):
            if (
                self.decisions_made.count(decision_id) > 1
                and definition.decision_window(decision_id).once
            ):
                raise ValueError("runtime repeated a one-time decision")
        if self.current_decision_id in self.decisions_made:
            window = definition.decision_window(self.current_decision_id)
            if window.once:
                raise ValueError("runtime reopened a one-time decision")
        if len(self.applied_event_ids) > MAX_APPLIED_SCENARIO_EVENTS:
            raise ValueError("runtime applied event history exceeds its limit")
        if len(self.applied_event_ids) != len(set(self.applied_event_ids)):
            raise ValueError("runtime applied event history contains duplicates")
        evidence_keys = tuple(
            item.stable_key() for item in self.narrative_outcome_evidence
        )
        if len(evidence_keys) > MAX_NARRATIVE_OUTCOME_EVIDENCE:
            raise ValueError("runtime narrative outcome evidence exceeds its limit")
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError("runtime narrative outcome evidence contains duplicates")
        if evidence_keys != tuple(sorted(evidence_keys)):
            raise ValueError("runtime narrative outcome evidence is not stably sorted")
        outcome_rules = {
            item.rule_id: item for item in definition.narrative_outcome_rules
        }
        for evidence in self.narrative_outcome_evidence:
            outcome_rule = outcome_rules.get(evidence.outcome_rule_id)
            if outcome_rule is None:
                raise ValueError("runtime narrative outcome evidence references an unknown rule")
            try:
                effect = outcome_rule.effect(evidence.outcome_result)
            except StopIteration as exc:
                raise ValueError(
                    "runtime narrative outcome evidence references an unknown result"
                ) from exc
            if effect.event_type != evidence.scenario_event_type:
                raise ValueError(
                    "runtime narrative outcome evidence has a mismatched event type"
                )
            if not set(evidence.npc_definition_ids) <= set(
                outcome_rule.required_visible_npc_definition_ids
            ):
                raise ValueError(
                    "runtime narrative outcome evidence has an unauthorized NPC target"
                )
        if self.rapid_decision_mode and not phase.rapid_decision_allowed:
            raise ValueError("runtime rapid decision mode is not allowed in this phase")
        if self.current_location_id not in self.opened_location_ids:
            raise ValueError("runtime current location is not open")
        if self.current_location_id not in phase.visible_location_ids:
            raise ValueError("runtime current location is not visible in its phase")
        endings = {item.ending_id: item for item in definition.endings}
        if self.ending_id is not None:
            ending = endings.get(self.ending_id)
            if ending is None or ending.status is not self.ending_status:
                raise ValueError("runtime ending does not match its definition")
        if self.ending_status is EndingStatus.ACTIVE and phase.terminal:
            raise ValueError("terminal phase cannot remain active")


class FactValueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fact_id: DefinitionId
    value: Any

    @field_serializer("value")
    def serialize_value(self, value: Any) -> Any:
        return value

    @model_validator(mode="after")
    def freeze_value(self) -> FactValueUpdate:
        object.__setattr__(
            self,
            "value",
            freeze_bounded_json_value(
                self.value, path=f"fact update {self.fact_id!r}"
            ),
        )
        return self


class VerifiedScenarioEvent(BaseModel):
    """Structured event shape that is trusted only after server-side sealing."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    event_id: DefinitionId
    event_type: DefinitionId
    source: DefinitionId | None = None
    decision_id: DefinitionId | None = None
    action_type: DefinitionId | None = None
    local_query: StrictBool = False
    discovered_clue_ids: tuple[DefinitionId, ...] = ()
    deferred_bindings: tuple[FactValueUpdate, ...] = ()
    mutable_fact_updates: tuple[FactValueUpdate, ...] = ()
    dynamic_fact_updates: tuple[FactValueUpdate, ...] = ()
    opened_location_ids: tuple[DefinitionId, ...] = ()
    new_location_id: DefinitionId | None = None
    resolves_current_decision: StrictBool = False
    expose_in_frame: StrictBool = False
    narrative_outcome_rule_id: DefinitionId | None = None
    narrative_outcome_result: NarrativeOutcomeResult | None = None
    narrative_outcome_npc_definition_ids: tuple[DefinitionId, ...] = ()
    _issuer: object | None = PrivateAttr(default=None)
    _sealed_payload: str | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def validate_query_is_read_only(self) -> VerifiedScenarioEvent:
        if self.resolves_current_decision and self.decision_id is None:
            raise ValueError("decision-resolving event requires decision_id")
        if not self.resolves_current_decision and self.decision_id is not None:
            raise ValueError("non-decision event cannot carry decision_id")
        has_mutation = any(
            (
                self.discovered_clue_ids,
                self.deferred_bindings,
                self.mutable_fact_updates,
                self.dynamic_fact_updates,
                self.opened_location_ids,
                self.new_location_id is not None,
                self.resolves_current_decision,
            )
        )
        if self.local_query and has_mutation:
            raise ValueError("local query cannot carry scenario mutations")
        update_count = sum(
            len(items)
            for items in (
                self.discovered_clue_ids,
                self.deferred_bindings,
                self.mutable_fact_updates,
                self.dynamic_fact_updates,
                self.opened_location_ids,
            )
        )
        if update_count > 64:
            raise ValueError("verified scenario event exceeds the mutation limit")
        for label, updates in (
            ("deferred", self.deferred_bindings),
            ("mutable", self.mutable_fact_updates),
            ("dynamic", self.dynamic_fact_updates),
        ):
            ids = tuple(item.fact_id for item in updates)
            if len(ids) != len(set(ids)):
                raise ValueError(f"verified scenario event repeats a {label} fact update")
        outcome_fields_present = (
            self.narrative_outcome_rule_id is not None,
            self.narrative_outcome_result is not None,
        )
        if any(outcome_fields_present) != all(outcome_fields_present):
            raise ValueError("narrative outcome event evidence is incomplete")
        if len(self.narrative_outcome_npc_definition_ids) != len(
            set(self.narrative_outcome_npc_definition_ids)
        ):
            raise ValueError("narrative outcome event repeats an NPC target")
        if self.narrative_outcome_npc_definition_ids != tuple(
            sorted(self.narrative_outcome_npc_definition_ids)
        ):
            raise ValueError("narrative outcome event NPC targets are not sorted")
        has_outcome_evidence = all(outcome_fields_present)
        if has_outcome_evidence != (self.source == "VALIDATED_NARRATIVE_OUTCOME"):
            raise ValueError(
                "validated narrative outcome source and exact evidence must agree"
            )
        if self.narrative_outcome_npc_definition_ids and not has_outcome_evidence:
            raise ValueError("narrative outcome NPC targets require exact evidence")
        return self

    def is_authentic(self) -> bool:
        return (
            self._issuer is _VERIFIED_SCENARIO_EVENT_ISSUER
            and self._sealed_payload == _event_payload_signature(self)
        )


def _seal_verified_scenario_event(
    event: VerifiedScenarioEvent,
) -> VerifiedScenarioEvent:
    """Server-internal handoff used only after a trusted resolver verifies a result."""

    sealed = VerifiedScenarioEvent.model_validate(event.model_dump(mode="json"))
    sealed.__pydantic_private__["_issuer"] = _VERIFIED_SCENARIO_EVENT_ISSUER
    sealed.__pydantic_private__["_sealed_payload"] = _event_payload_signature(sealed)
    return sealed


def _issue_verified_scenario_event(**payload: Any) -> VerifiedScenarioEvent:
    """Test/future server adapter helper; deliberately excluded from public exports."""

    return _seal_verified_scenario_event(VerifiedScenarioEvent.model_validate(payload))


def _event_payload_signature(event: VerifiedScenarioEvent) -> str:
    return json.dumps(
        event.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
