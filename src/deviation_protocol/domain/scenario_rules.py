from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from deviation_protocol.domain.json_values import json_values_equal
from deviation_protocol.domain.scenario import (
    AlwaysCondition,
    ClockAtLeastCondition,
    ClockAtMostCondition,
    ClueGroupCompleteCondition,
    ConditionDefinition,
    DecisionsAtLeastCondition,
    EventOccurredCondition,
    FactEqualsCondition,
    LocationOpenedCondition,
    NpcAliveAcknowledgedCondition,
    PhaseBeatAtLeastCondition,
    PhaseVisitAtLeastCondition,
    ScenarioDefinition,
)
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState


class DeclarativeConditionEvaluator:
    """Evaluate the closed, non-executable scenario rule vocabulary."""

    def all_match(
        self,
        conditions: Iterable[ConditionDefinition],
        *,
        definition: ScenarioDefinition,
        runtime: ScenarioRuntimeState,
        event_types: Iterable[str] = (),
    ) -> bool:
        occurred = frozenset(event_types)
        return all(
            self.matches(
                condition,
                definition=definition,
                runtime=runtime,
                event_types=occurred,
            )
            for condition in conditions
        )

    def matches(
        self,
        condition: ConditionDefinition,
        *,
        definition: ScenarioDefinition,
        runtime: ScenarioRuntimeState,
        event_types: frozenset[str],
    ) -> bool:
        if isinstance(condition, AlwaysCondition):
            return True
        if isinstance(condition, PhaseBeatAtLeastCondition):
            return runtime.phase_beat_index >= condition.value
        if isinstance(condition, FactEqualsCondition):
            return self.values_equal(
                self.fact_value(condition.fact_id, definition, runtime),
                condition.value,
            )
        if isinstance(condition, ClueGroupCompleteCondition):
            return condition.clue_group_id in runtime.completed_clue_group_ids
        if isinstance(condition, ClockAtLeastCondition):
            return runtime.threat_clocks[condition.clock_id].value >= condition.value
        if isinstance(condition, ClockAtMostCondition):
            return runtime.threat_clocks[condition.clock_id].value <= condition.value
        if isinstance(condition, LocationOpenedCondition):
            return condition.location_id in runtime.opened_location_ids
        if isinstance(condition, DecisionsAtLeastCondition):
            return len(runtime.decisions_made) >= condition.value
        if isinstance(condition, EventOccurredCondition):
            return condition.event_type in event_types
        if isinstance(condition, PhaseVisitAtLeastCondition):
            return runtime.phase_visit_counts.get(condition.phase_id, 0) >= condition.value
        if isinstance(condition, NpcAliveAcknowledgedCondition):
            acknowledged = {
                npc_id
                for evidence in runtime.narrative_outcome_evidence
                for npc_id in (
                    evidence.player_alive_acknowledgement_npc_ids
                )
            }
            return len(acknowledged) >= condition.minimum_count
        raise TypeError(f"unsupported condition definition: {type(condition).__name__}")

    @staticmethod
    def values_equal(left: Any, right: Any) -> bool:
        return json_values_equal(left, right)

    @staticmethod
    def fact_value(
        fact_id: str, definition: ScenarioDefinition, runtime: ScenarioRuntimeState
    ) -> Any:
        fact = definition.fact(fact_id)
        if fact.kind.value == "FIXED":
            return fact.value
        if fact.kind.value == "DEFERRED":
            return runtime.bound_deferred_facts.get(fact_id)
        if fact.kind.value == "MUTABLE":
            return runtime.mutable_fact_values[fact_id]
        raise TypeError("declared scenario facts cannot be DYNAMIC")
