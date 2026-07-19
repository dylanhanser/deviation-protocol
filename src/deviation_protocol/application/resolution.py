from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any

from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.facts import NarrativeFact
from deviation_protocol.domain.json_values import freeze_json_object
from deviation_protocol.domain.state import GameState


class ResolutionStatus(StrEnum):
    RESOLVED_LOCAL = "RESOLVED_LOCAL"
    REJECTED_LOCAL = "REJECTED_LOCAL"
    NARRATIVE_REQUIRED = "NARRATIVE_REQUIRED"
    ANOMALY_EVALUATION_REQUIRED = "ANOMALY_EVALUATION_REQUIRED"


@dataclass(frozen=True, slots=True)
class PlayerFeedback:
    code: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.code):
            raise ValueError("feedback code must be a stable uppercase identifier")
        object.__setattr__(
            self,
            "parameters",
            freeze_json_object(self.parameters, path="feedback parameters"),
        )


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    status: ResolutionStatus
    success: bool
    result_code: str
    updated_state: GameState | None = None
    state_changed: bool = False
    events: tuple[DomainEventDraft, ...] = ()
    facts: tuple[NarrativeFact, ...] = ()
    feedback: PlayerFeedback = field(
        default_factory=lambda: PlayerFeedback("NO_FEEDBACK")
    )

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.result_code):
            raise ValueError("result_code must be a stable uppercase identifier")
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "facts", tuple(self.facts))
        if self.state_changed != (self.updated_state is not None):
            raise ValueError("state_changed must match the presence of updated_state")
        if self.success != (self.status is ResolutionStatus.RESOLVED_LOCAL):
            raise ValueError("only RESOLVED_LOCAL results may be successful")
        if self.status is ResolutionStatus.REJECTED_LOCAL:
            if self.updated_state is not None or self.events or self.facts:
                raise ValueError("REJECTED_LOCAL cannot contain state, events, or facts")
        elif self.status in {
            ResolutionStatus.NARRATIVE_REQUIRED,
            ResolutionStatus.ANOMALY_EVALUATION_REQUIRED,
        }:
            if self.updated_state is not None or self.events:
                raise ValueError("narrative routing cannot contain state or event drafts")
        elif self.status is ResolutionStatus.RESOLVED_LOCAL:
            if self.events and self.updated_state is None:
                raise ValueError("event drafts require a resolved candidate state")
            if self.updated_state is not None and not self.events:
                raise ValueError("resolved candidate state requires at least one event draft")
