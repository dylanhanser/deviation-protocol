from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


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
