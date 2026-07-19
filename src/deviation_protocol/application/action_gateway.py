from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable

from deviation_protocol.domain.actions import ActionContext
from deviation_protocol.domain.policies import (
    ActionPolicy,
    PolicyDecision,
    PolicyOutcome,
    build_policy_chain,
)


class ActionRoute(StrEnum):
    REJECT_LOCAL = "REJECT_LOCAL"
    RESOLVE_LOCAL = "RESOLVE_LOCAL"
    NARRATIVE_NORMAL = "NARRATIVE_NORMAL"
    NARRATIVE_ANOMALY_CANDIDATE = "NARRATIVE_ANOMALY_CANDIDATE"


@dataclass(frozen=True, slots=True)
class GatewayResult:
    route: ActionRoute
    action_signature: str
    policy_trace: tuple[PolicyDecision, ...]


class ActionGateway:
    def __init__(self, policies: Iterable[ActionPolicy]) -> None:
        self._policies = tuple(policies)
        if not self._policies:
            raise ValueError("ActionGateway requires at least one policy")

    @classmethod
    def from_config(cls, path: str | Path | None = None) -> "ActionGateway":
        config_path = Path(path) if path else Path(__file__).parents[3] / "config" / "action_policies.json"
        with config_path.open(encoding="utf-8") as stream:
            config = json.load(stream)
        return cls(build_policy_chain(config))

    def evaluate(self, context: ActionContext) -> GatewayResult:
        trace: list[PolicyDecision] = []
        route = ActionRoute.NARRATIVE_NORMAL
        for policy in self._policies:
            decision = policy.evaluate(context)
            trace.append(decision)
            if decision.outcome is PolicyOutcome.REJECT:
                route = ActionRoute.REJECT_LOCAL
                break
            if decision.outcome is PolicyOutcome.RESOLVE_LOCAL:
                route = ActionRoute.RESOLVE_LOCAL
                break

        # Anomaly promotion is intentionally not guessed here. A later independent
        # AnomalyEvaluator may promote an already-valid NARRATIVE_NORMAL action.
        return GatewayResult(
            route=route,
            action_signature=context.submission.action_signature(),
            policy_trace=tuple(trace),
        )
