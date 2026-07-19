from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any

from deviation_protocol.domain.json_values import freeze_json_object


_EVENT_TYPE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: str
    session_id: str
    turn_id: str
    sequence_no: int
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class DomainEventDraft:
    """Deterministic event content awaiting a persistence envelope.

    The application orchestrator supplies event_id, sequence_no and occurred_at when
    converting a draft into a persisted DomainEvent inside its transaction.
    """

    event_type: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if not _EVENT_TYPE_PATTERN.fullmatch(self.event_type):
            raise ValueError("event_type must be a stable non-empty identifier")
        object.__setattr__(
            self,
            "payload",
            freeze_json_object(self.payload, path="event payload"),
        )
