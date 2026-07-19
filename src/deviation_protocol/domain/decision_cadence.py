from __future__ import annotations

from collections.abc import Iterable

from deviation_protocol.domain.scenario import DecisionWindowDefinition, ScenarioDefinition
from deviation_protocol.domain.scenario_rules import DeclarativeConditionEvaluator
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState


class DecisionCadencePolicy:
    """Select sparse, content-configured decision windows without inventing choices."""

    def __init__(self, evaluator: DeclarativeConditionEvaluator | None = None) -> None:
        self._evaluator = evaluator or DeclarativeConditionEvaluator()

    def select_window(
        self,
        *,
        definition: ScenarioDefinition,
        runtime: ScenarioRuntimeState,
        event_types: Iterable[str] = (),
    ) -> DecisionWindowDefinition | None:
        phase = definition.phase(runtime.current_phase_id)
        if runtime.current_decision_id is not None:
            return definition.decision_window(runtime.current_decision_id)
        if runtime.phase_beat_index < phase.min_auto_beats:
            return None
        for decision_id in phase.decision_window_ids:
            window = definition.decision_window(decision_id)
            if window.once and decision_id in runtime.decisions_made:
                continue
            if not window.earliest_beat <= runtime.phase_beat_index <= window.latest_beat:
                continue
            if self._evaluator.all_match(
                window.conditions,
                definition=definition,
                runtime=runtime,
                event_types=event_types,
            ):
                return window
        return None
