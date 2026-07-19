from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FactKind(StrEnum):
    FIXED = "FIXED"
    DEFERRED = "DEFERRED"
    MUTABLE = "MUTABLE"


@dataclass(frozen=True, slots=True)
class StoryFact:
    key: str
    kind: FactKind
    value: Any = None
    causal_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class StoryMutation:
    key: str
    value: Any
    kind: FactKind | None = None
    causal_event_id: str | None = None


class StoryMutationError(ValueError):
    """A mutation would violate the scenario truth boundary."""


class StoryMutationValidator:
    """Freezes scenario truth without freezing how a player reaches it."""

    DYNAMIC_PREFIX = "dynamic."

    def validate(self, current: StoryFact | None, mutation: StoryMutation) -> StoryFact:
        if current is not None and current.key != mutation.key:
            raise StoryMutationError("current fact key does not match mutation key")

        if mutation.key.startswith(self.DYNAMIC_PREFIX):
            return self._validate_dynamic(current, mutation)

        if current is None:
            if mutation.kind is None:
                raise StoryMutationError("new facts must declare a fact kind")
            if mutation.kind is FactKind.MUTABLE and not mutation.causal_event_id:
                raise StoryMutationError("MUTABLE facts require causal_event_id")
            return StoryFact(
                key=mutation.key,
                kind=mutation.kind,
                value=mutation.value,
                causal_event_id=mutation.causal_event_id,
            )

        if current.kind is FactKind.FIXED:
            raise StoryMutationError("FIXED facts cannot be modified")

        if current.kind is FactKind.DEFERRED:
            if current.value is not None:
                raise StoryMutationError("DEFERRED facts can only be bound once")
            return StoryFact(current.key, current.kind, mutation.value, mutation.causal_event_id)

        if current.kind is FactKind.MUTABLE:
            if not mutation.causal_event_id:
                raise StoryMutationError("MUTABLE facts require causal_event_id")
            return StoryFact(current.key, current.kind, mutation.value, mutation.causal_event_id)

        raise StoryMutationError(f"unsupported fact kind: {current.kind}")

    def _validate_dynamic(
        self, current: StoryFact | None, mutation: StoryMutation
    ) -> StoryFact:
        if not mutation.causal_event_id:
            raise StoryMutationError("dynamic facts require causal_event_id")
        if current is not None and current.kind is FactKind.FIXED:
            raise StoryMutationError("dynamic facts cannot overwrite FIXED facts")
        if mutation.kind not in (None, FactKind.MUTABLE):
            raise StoryMutationError("dynamic facts must be MUTABLE")
        return StoryFact(
            key=mutation.key,
            kind=FactKind.MUTABLE,
            value=mutation.value,
            causal_event_id=mutation.causal_event_id,
        )
