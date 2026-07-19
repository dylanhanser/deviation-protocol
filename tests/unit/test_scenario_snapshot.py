from __future__ import annotations

from copy import deepcopy
import json

import pytest

from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.scenario import ScenarioCatalog
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    _issue_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState, PlayerState, migrate_snapshot_payload
from tests.unit.test_story_director import mini_catalog, state_for


def test_v1_snapshot_migrates_purely_to_v2() -> None:
    catalog = mini_catalog()
    character = catalog.content_catalog.character("character.alpine.scout")
    assert character is not None
    old = {
        "schema_version": 1,
        "content_version": catalog.content_version,
        "player": PlayerState.from_definition("player-1", character).model_dump(mode="json"),
        "npcs": {},
    }
    untouched = deepcopy(old)
    migrated = migrate_snapshot_payload(old)
    assert old == untouched
    assert migrated["schema_version"] == 2
    assert migrated["scenario_runtime"] is None
    restored = GameState.from_snapshot(old, catalog=catalog.content_catalog)
    assert restored.schema_version == 2
    assert restored.scenario_runtime is None


def test_v2_scenario_snapshot_round_trips_with_separate_content_version() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    started = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    payload = started.candidate_state.to_snapshot()
    encoded = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    restored = GameState.from_snapshot(
        encoded,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    assert restored == started.candidate_state
    assert restored.schema_version == 2
    assert restored.scenario_runtime is not None
    assert restored.scenario_runtime.scenario_content_version == definition.content_version


def test_scenario_snapshot_requires_matching_scenario_catalog() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    started = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    with pytest.raises(ValueError, match="scenario catalog is required"):
        GameState.from_snapshot(
            started.candidate_state.to_snapshot(),
            catalog=catalog.content_catalog,
        )


def test_v2_scenario_snapshot_rejects_mismatched_catalog_versions_and_content() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    started = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    payload = catalog.model_dump(mode="json")
    payload["content_catalog"]["characters"][0]["display_name"] = "不同定义"
    different_content = ScenarioCatalog.model_validate(payload)
    with pytest.raises(ValueError, match="catalogs do not match"):
        GameState.from_snapshot(
            started.candidate_state.to_snapshot(),
            catalog=catalog.content_catalog,
            scenario_catalog=different_content,
        )

    different_version_payload = catalog.model_dump(mode="json")
    different_version_payload["content_version"] = "alpine-signal-2"
    different_version_payload["content_catalog"]["content_version"] = "alpine-signal-2"
    different_version_payload["scenarios"][0]["content_version"] = "alpine-signal-2"
    different_version = ScenarioCatalog.model_validate(different_version_payload)
    with pytest.raises(ValueError, match="content version"):
        GameState.from_snapshot(
            started.candidate_state.to_snapshot(),
            scenario_catalog=different_version,
        )


def test_v2_normal_game_state_remains_compatible_without_scenario_catalog() -> None:
    catalog = mini_catalog()
    state = state_for(catalog)
    restored = GameState.from_snapshot(
        state.to_snapshot(), catalog=catalog.content_catalog
    )
    assert restored == state
    assert restored.scenario_runtime is None


def test_all_scenario_runtime_mutations_round_trip_through_snapshot() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    investigated = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            _issue_verified_scenario_event(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
                deferred_bindings=(
                    FactValueUpdate(fact_id="alpine.fact.route", value="north"),
                ),
                dynamic_fact_updates=(
                    FactValueUpdate(fact_id="dynamic.shelter", value="camp"),
                ),
                opened_location_ids=("alpine.ridge",),
                new_location_id="alpine.ridge",
            ),
            _issue_verified_scenario_event(
                event_id="event.beacon",
                event_type="beacon.disabled",
                mutable_fact_updates=(
                    FactValueUpdate(fact_id="alpine.fact.beacon_active", value=False),
                ),
            ),
        ),
    )
    ended = director.advance_after_verified_result(
        investigated.candidate_state,
        definition,
        (
            _issue_verified_scenario_event(
                event_id="event.route",
                event_type="route.chosen",
                action_type="move",
                resolves_current_decision=True,
            ),
        ),
    )
    restored = GameState.from_snapshot(
        ended.candidate_state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    assert restored == ended.candidate_state
    runtime = restored.scenario_runtime
    assert runtime is not None
    assert runtime.discovered_clue_ids
    assert runtime.completed_clue_group_ids
    assert runtime.bound_deferred_facts
    assert runtime.mutable_fact_values["alpine.fact.beacon_active"] is False
    assert runtime.dynamic_facts
    assert runtime.threat_clocks["alpine_storm"].triggered_thresholds == {2}
    assert runtime.decisions_made
    assert runtime.transition_use_counts
    assert runtime.ending_id == "alpine.ending.arrived"


def test_snapshot_rejects_v1_scenario_state_and_float_runtime_values() -> None:
    catalog = mini_catalog()
    state = state_for(catalog)
    v1 = state.to_snapshot()
    v1["schema_version"] = 1
    v1["scenario_runtime"] = None
    with pytest.raises(ValueError, match="v1 snapshot cannot contain"):
        migrate_snapshot_payload(v1)

    started = DeterministicStoryDirector().start_scenario(
        state_for(catalog), catalog.scenarios[0]
    )
    runtime = started.candidate_state.scenario_runtime
    assert runtime is not None
    runtime.dynamic_facts["dynamic.float"] = 1.5
    with pytest.raises((TypeError, ValueError), match="float"):
        started.candidate_state.to_snapshot()
