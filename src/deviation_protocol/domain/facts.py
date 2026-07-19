from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

from deviation_protocol.domain.json_values import (
    freeze_bounded_json_value,
    freeze_json_value,
    json_values_equal,
)


class FactKind(StrEnum):
    FIXED = "FIXED"
    DEFERRED = "DEFERRED"
    MUTABLE = "MUTABLE"
    DYNAMIC = "DYNAMIC"


class FactVisibility(StrEnum):
    HIDDEN = "HIDDEN"
    DISCOVERABLE = "DISCOVERABLE"
    PLAYER_KNOWN = "PLAYER_KNOWN"
    NPC_KNOWN = "NPC_KNOWN"


class NarrativeFactKind(StrEnum):
    VALIDATED_INTENT = "VALIDATED_INTENT"
    AUTHORITATIVE_CONTEXT = "AUTHORITATIVE_CONTEXT"
    RESOLVED_STATE = "RESOLVED_STATE"
    QUERY_RESULT = "QUERY_RESULT"


@dataclass(frozen=True, slots=True)
class StoryFact:
    key: str
    kind: FactKind
    value: Any = None
    causal_event_id: str | None = None
    visibility: FactVisibility = FactVisibility.HIDDEN


@dataclass(frozen=True, slots=True)
class NarrativeFact:
    """An immutable fact a later narrative renderer must preserve.

    Unlike StoryFact this is not a mutation of scenario truth. It describes an
    already validated intent or an already committed candidate-state change.
    """

    key: str
    value: Any
    kind: NarrativeFactKind = NarrativeFactKind.RESOLVED_STATE

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,255}", self.key):
            raise ValueError("narrative fact key must be a stable non-empty identifier")
        object.__setattr__(
            self,
            "value",
            freeze_json_value(self.value, path=f"narrative fact {self.key!r}"),
        )


@dataclass(frozen=True, slots=True)
class StoryMutation:
    key: str
    value: Any
    kind: FactKind | None = None
    causal_event_id: str | None = None
    visibility: FactVisibility | None = None


class StoryMutationError(ValueError):
    """A mutation would violate the scenario truth boundary."""


class StoryMutationValidator:
    """Freezes scenario truth without freezing how a player reaches it."""

    DYNAMIC_PREFIX = "dynamic."
    DYNAMIC_KEY_PATTERN = re.compile(
        r"^dynamic\.[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )

    def __init__(
        self,
        *,
        dynamic_fact_limit: int = 20,
        dynamic_key_max_length: int = 96,
        dynamic_value_max_length: int = 500,
    ) -> None:
        if (
            type(dynamic_fact_limit) is not int
            or type(dynamic_key_max_length) is not int
            or type(dynamic_value_max_length) is not int
            or dynamic_fact_limit < 1
            or dynamic_key_max_length < len(self.DYNAMIC_PREFIX)
            or dynamic_value_max_length < 1
        ):
            raise ValueError("dynamic fact limits must be positive")
        self._dynamic_fact_limit = dynamic_fact_limit
        self._dynamic_key_max_length = dynamic_key_max_length
        self._dynamic_value_max_length = dynamic_value_max_length

    def validate(self, current: StoryFact | None, mutation: StoryMutation) -> StoryFact:
        if current is not None and current.key != mutation.key:
            raise StoryMutationError("current fact key does not match mutation key")

        if mutation.key.startswith(self.DYNAMIC_PREFIX):
            return self._validate_dynamic(current, mutation)
        if mutation.kind is FactKind.DYNAMIC:
            raise StoryMutationError("DYNAMIC facts must use the dynamic.* namespace")

        if current is None:
            if mutation.kind is None:
                raise StoryMutationError("new facts must declare a fact kind")
            if mutation.kind is FactKind.MUTABLE and not mutation.causal_event_id:
                raise StoryMutationError("MUTABLE facts require causal_event_id")
            return StoryFact(
                key=mutation.key,
                kind=mutation.kind,
                value=freeze_bounded_json_value(
                    mutation.value, path=f"story fact {mutation.key!r}"
                ),
                causal_event_id=mutation.causal_event_id,
                visibility=mutation.visibility or FactVisibility.HIDDEN,
            )

        if current.kind is FactKind.FIXED:
            raise StoryMutationError("FIXED facts cannot be modified")

        if current.kind is FactKind.DEFERRED:
            if current.value is not None:
                raise StoryMutationError("DEFERRED facts can only be bound once")
            return StoryFact(
                current.key,
                current.kind,
                freeze_bounded_json_value(
                    mutation.value, path=f"story fact {mutation.key!r}"
                ),
                mutation.causal_event_id,
                mutation.visibility or current.visibility,
            )

        if current.kind is FactKind.MUTABLE:
            if not mutation.causal_event_id:
                raise StoryMutationError("MUTABLE facts require causal_event_id")
            return StoryFact(
                current.key,
                current.kind,
                freeze_bounded_json_value(
                    mutation.value, path=f"story fact {mutation.key!r}"
                ),
                mutation.causal_event_id,
                mutation.visibility or current.visibility,
            )

        raise StoryMutationError(f"unsupported fact kind: {current.kind}")

    def validate_deferred_binding(
        self,
        current: StoryFact,
        mutation: StoryMutation,
        *,
        allowed_candidates: Iterable[Any],
    ) -> StoryFact:
        if current.kind is not FactKind.DEFERRED:
            raise StoryMutationError("only DEFERRED facts can be bound")
        if not any(
            json_values_equal(mutation.value, candidate)
            for candidate in allowed_candidates
        ):
            raise StoryMutationError("DEFERRED fact value is not an allowed candidate")
        return self.validate(current, mutation)

    def validate_mutable_transition(
        self,
        current: StoryFact,
        mutation: StoryMutation,
        *,
        causal_event_type: str,
        allowed_transitions: Iterable[tuple[Any, Any, str]],
    ) -> StoryFact:
        if current.kind is not FactKind.MUTABLE:
            raise StoryMutationError("only MUTABLE facts can use mutable updates")
        if not mutation.causal_event_id:
            raise StoryMutationError("MUTABLE facts require causal_event_id")
        allowed = any(
            json_values_equal(from_value, current.value)
            and json_values_equal(to_value, mutation.value)
            and event_type == causal_event_type
            for from_value, to_value, event_type in allowed_transitions
        )
        if not allowed:
            raise StoryMutationError(
                "MUTABLE fact update lacks an allowed causal transition"
            )
        return self.validate(current, mutation)

    def _validate_dynamic(
        self, current: StoryFact | None, mutation: StoryMutation
    ) -> StoryFact:
        if not mutation.causal_event_id:
            raise StoryMutationError("dynamic facts require causal_event_id")
        if current is not None and current.kind is FactKind.FIXED:
            raise StoryMutationError("dynamic facts cannot overwrite FIXED facts")
        if mutation.kind not in (None, FactKind.DYNAMIC):
            raise StoryMutationError("dynamic facts must be DYNAMIC")
        if not self.DYNAMIC_KEY_PATTERN.fullmatch(mutation.key):
            raise StoryMutationError("dynamic fact key must have a stable non-empty suffix")
        if len(mutation.key) > self._dynamic_key_max_length:
            raise StoryMutationError("dynamic fact key exceeds configured length limit")
        value = freeze_bounded_json_value(
            mutation.value,
            path=f"dynamic fact {mutation.key!r}",
        )
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(encoded) > self._dynamic_value_max_length:
            raise StoryMutationError("dynamic fact value exceeds configured length limit")
        return StoryFact(
            key=mutation.key,
            kind=FactKind.DYNAMIC,
            value=value,
            causal_event_id=mutation.causal_event_id,
            visibility=mutation.visibility or (
                current.visibility if current is not None else FactVisibility.PLAYER_KNOWN
            ),
        )

    def validate_dynamic_collection(
        self,
        current: Mapping[str, StoryFact],
        mutation: StoryMutation,
        *,
        reserved_fact_ids: Iterable[str] = (),
    ) -> StoryFact:
        if not mutation.key.startswith(self.DYNAMIC_PREFIX):
            raise StoryMutationError("dynamic fact keys must use the dynamic.* namespace")
        if mutation.key in set(reserved_fact_ids):
            raise StoryMutationError("dynamic facts cannot overwrite declared facts")
        existing = current.get(mutation.key)
        if existing is None and len(current) >= self._dynamic_fact_limit:
            raise StoryMutationError("dynamic fact count exceeds configured limit")
        return self.validate(existing, mutation)
