from __future__ import annotations

import pytest

from deviation_protocol.domain.facts import (
    FactKind,
    StoryFact,
    StoryMutation,
    StoryMutationError,
    StoryMutationValidator,
)


@pytest.fixture
def validator() -> StoryMutationValidator:
    return StoryMutationValidator()


def test_fixed_fact_cannot_be_modified(validator: StoryMutationValidator) -> None:
    current = StoryFact("truth.culprit", FactKind.FIXED, "npc-1")
    with pytest.raises(StoryMutationError, match="FIXED"):
        validator.validate(current, StoryMutation("truth.culprit", "npc-2"))


def test_deferred_fact_can_be_bound_once(validator: StoryMutationValidator) -> None:
    initial = StoryFact("truth.safe_code", FactKind.DEFERRED)
    bound = validator.validate(initial, StoryMutation("truth.safe_code", "7319"))
    assert bound.value == "7319"
    assert bound.kind is FactKind.DEFERRED
    with pytest.raises(StoryMutationError, match="only be bound once"):
        validator.validate(bound, StoryMutation("truth.safe_code", "0000"))


def test_mutable_fact_requires_causal_event(validator: StoryMutationValidator) -> None:
    current = StoryFact("world.power", FactKind.MUTABLE, "on", "event-1")
    with pytest.raises(StoryMutationError, match="causal_event_id"):
        validator.validate(current, StoryMutation("world.power", "off"))


def test_mutable_fact_changes_with_causal_event(validator: StoryMutationValidator) -> None:
    current = StoryFact("world.power", FactKind.MUTABLE, "on", "event-1")
    changed = validator.validate(
        current, StoryMutation("world.power", "off", causal_event_id="event-2")
    )
    assert changed.value == "off"
    assert changed.causal_event_id == "event-2"


def test_dynamic_fact_can_be_created_with_cause(validator: StoryMutationValidator) -> None:
    created = validator.validate(
        None,
        StoryMutation(
            "dynamic.player_built_radio",
            {"frequency_khz": 101_700},
            causal_event_id="event-build-radio",
        ),
    )
    assert created.kind is FactKind.DYNAMIC
    assert created.key.startswith("dynamic.")


def test_scenario_fact_values_reject_floats(
    validator: StoryMutationValidator,
) -> None:
    with pytest.raises(TypeError, match="requires integers"):
        validator.validate(
            None,
            StoryMutation(
                "dynamic.player_built_radio",
                {"frequency": 101.7},
                causal_event_id="event-build-radio",
            ),
        )


def test_dynamic_fact_without_cause_is_rejected(validator: StoryMutationValidator) -> None:
    with pytest.raises(StoryMutationError, match="causal_event_id"):
        validator.validate(None, StoryMutation("dynamic.shortcut", True))


@pytest.mark.parametrize("key", ["dynamic.", "dynamic..empty", "dynamic.-bad"])
def test_dynamic_fact_requires_stable_non_empty_suffix(
    validator: StoryMutationValidator, key: str
) -> None:
    with pytest.raises(StoryMutationError, match="stable non-empty suffix"):
        validator.validate(
            None,
            StoryMutation(key, True, causal_event_id="event-create"),
        )


def test_dynamic_namespace_cannot_overwrite_fixed_fact(
    validator: StoryMutationValidator,
) -> None:
    fixed = StoryFact("dynamic.reserved_truth", FactKind.FIXED, "sealed")
    with pytest.raises(StoryMutationError, match="FIXED"):
        validator.validate(
            fixed,
            StoryMutation("dynamic.reserved_truth", "open", causal_event_id="event-9"),
        )
