from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable


class DemoLogicalClock:
    def __init__(self) -> None:
        self._next_offset = 0

    def __call__(self) -> datetime:
        value = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(
            seconds=self._next_offset
        )
        self._next_offset += 1
        return value


class DemoStringSequence:
    def __init__(self, prefix: str, *, width: int) -> None:
        self._prefix = prefix
        self._width = width
        self._next_value = 1

    def __call__(self) -> str:
        value = f"{self._prefix}{self._next_value:0{self._width}d}"
        self._next_value += 1
        return value


class DemoSeedSequence:
    def __init__(self) -> None:
        self._next_value = 1

    def __call__(self) -> int:
        if self._next_value >= 2**63:
            raise RuntimeError("Demo seed sequence exhausted the 63-bit boundary")
        value = self._next_value
        self._next_value += 1
        return value


@dataclass(frozen=True, slots=True)
class DemoGenerators:
    clock: Callable[[], datetime]
    session_id: Callable[[], str]
    event_id: Callable[[], str]
    job_id: Callable[[], str]
    lease_token: Callable[[], str]
    worker_id: Callable[[], str]
    seed: Callable[[], int]


def new_demo_generators() -> DemoGenerators:
    return DemoGenerators(
        clock=DemoLogicalClock(),
        session_id=DemoStringSequence("demo-session-", width=8),
        event_id=DemoStringSequence("demo-event-", width=8),
        job_id=DemoStringSequence("demo-job-", width=8),
        lease_token=DemoStringSequence("demo-lease-", width=21),
        worker_id=DemoStringSequence("demo-worker-", width=8),
        seed=DemoSeedSequence(),
    )
