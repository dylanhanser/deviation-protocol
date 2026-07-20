from __future__ import annotations

from copy import deepcopy
import json

import pytest

from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.scenario import ScenarioCatalog
from deviation_protocol.domain.player_memory import (
    SignificantExperienceCategory,
    stable_significant_experience_id,
)
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    _issue_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState, PlayerState, migrate_snapshot_payload
from tests.unit.test_story_director import mini_catalog, state_for


def test_v1_snapshot_migrates_purely_through_v2_to_v3() -> None:
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
    assert migrated["schema_version"] == 3
    assert migrated["scenario_runtime"] is None
    assert migrated["player_memory"] == {
        "known_public_facts": [],
        "last_applied_source_sequence_no": 0,
        "last_applied_source_event_id": None,
        "memory_model_version": 2,
        "sync_status": "CURRENT",
        "first_deferred_source_sequence_no": None,
        "last_deferred_source_sequence_no": None,
        "deferred_event_count": 0,
        "npc_records": [],
        "scenario_records": [],
        "significant_experiences": [],
    }
    restored = GameState.from_snapshot(old, catalog=catalog.content_catalog)
    assert restored.schema_version == 3
    assert restored.scenario_runtime is None
    assert restored.player_memory.scenario_records == ()


def test_v2_snapshot_migrates_purely_to_v3_empty_memory() -> None:
    catalog = mini_catalog()
    v2 = state_for(catalog).to_snapshot()
    v2["schema_version"] = 2
    v2.pop("player_memory")
    untouched = deepcopy(v2)
    migrated = migrate_snapshot_payload(v2)
    assert v2 == untouched
    assert migrated["schema_version"] == 3
    assert migrated["scenario_runtime"] is None
    assert migrated["player_memory"]["memory_model_version"] == 2
    assert all(
        migrated["player_memory"][key] == []
        for key in (
            "scenario_records",
            "npc_records",
            "significant_experiences",
            "known_public_facts",
        )
    )


def test_v1_and_v2_snapshots_cannot_smuggle_v3_player_memory() -> None:
    catalog = mini_catalog()
    for version in (1, 2):
        payload = state_for(catalog).to_snapshot()
        payload["schema_version"] = version
        if version == 1:
            payload.pop("scenario_runtime")
        untouched = deepcopy(payload)
        with pytest.raises(ValueError, match="cannot contain player_memory"):
            migrate_snapshot_payload(payload)
        assert payload == untouched


def test_v3_empty_memory_round_trip_is_byte_semantic_stable() -> None:
    catalog = mini_catalog()
    state = state_for(catalog)
    first = json.dumps(
        state.to_snapshot(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    restored = GameState.from_snapshot(json.loads(first), catalog=catalog.content_catalog)
    second = json.dumps(
        restored.to_snapshot(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert first == second


@pytest.mark.parametrize("version", [True, 3.0, "3"])
def test_v3_schema_version_requires_strict_integer(version: object) -> None:
    payload = state_for(mini_catalog()).to_snapshot()
    payload["schema_version"] = version
    with pytest.raises((TypeError, ValueError)):
        GameState.from_snapshot(payload)


def test_v3_rejects_extra_duplicate_invalid_and_non_json_memory_values() -> None:
    payload = state_for(mini_catalog()).to_snapshot()
    payload["player_memory"]["unexpected"] = "no"
    with pytest.raises(ValueError, match="unexpected"):
        GameState.from_snapshot(payload)

    payload = state_for(mini_catalog()).to_snapshot()
    record = {
        "scenario_id": "alpine_signal",
        "scenario_content_version": "alpine-signal-1",
        "status": "STARTED",
        "ending_id": None,
        "milestone_refs": ["STARTED"],
        "known_public_fact_refs": [],
        "last_source_event_id": "event.1",
        "last_source_sequence_no": 1,
    }
    payload["player_memory"]["scenario_records"] = [record, deepcopy(record)]
    with pytest.raises(ValueError, match="repeats a scenario"):
        GameState.from_snapshot(payload)

    payload = state_for(mini_catalog()).to_snapshot()
    invalid = deepcopy(record)
    invalid["scenario_id"] = "invalid id with spaces"
    payload["player_memory"]["scenario_records"] = [invalid]
    with pytest.raises(ValueError, match="scenario_id"):
        GameState.from_snapshot(payload)

    for illegal in (1.5, {"not-json"}, RuntimeError("not-json"), PlayerState):
        payload = state_for(mini_catalog()).to_snapshot()
        payload["player_memory"]["known_public_facts"] = [illegal]
        with pytest.raises((TypeError, ValueError), match="non-JSON|float"):
            GameState.from_snapshot(payload)


def test_v3_rejects_over_capacity_memory_collection() -> None:
    payload = state_for(mini_catalog()).to_snapshot()
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": f"scenario-{index}",
            "scenario_content_version": "content-1",
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": f"event-{index}",
            "last_source_sequence_no": index + 1,
        }
        for index in range(65)
    ]
    with pytest.raises(ValueError, match="64 items"):
        GameState.from_snapshot(payload)


def test_v3_rejects_experience_id_not_bound_to_all_content() -> None:
    payload = state_for(mini_catalog()).to_snapshot()
    category = SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY
    valid_id = stable_significant_experience_id(
        source_event_id="event.discovery",
        scenario_id="alpine_signal",
        category=category,
        subject_refs=(),
        public_fact_refs=("alpine.fact.weather",),
    )
    payload["player_memory"]["significant_experiences"] = [
        {
            "entry_id": valid_id,
            "scenario_id": "alpine_signal",
            "category": category.value,
            "summary": "CRITICAL_PUBLIC_FACT_LEARNED",
            "subject_refs": [],
            "public_fact_refs": ["alpine.fact.beacon_active"],
            "source_event_id": "event.discovery",
            "source_sequence_no": 1,
        }
    ]
    payload["player_memory"]["last_applied_source_sequence_no"] = 1
    with pytest.raises(ValueError, match="ID does not match"):
        GameState.from_snapshot(payload)


def test_v3_rejects_inconsistent_memory_ordering_and_orphan_indexes() -> None:
    payload = state_for(mini_catalog()).to_snapshot()
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": "alpine_signal",
            "scenario_content_version": "alpine-signal-1",
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": "event.start",
            "last_source_sequence_no": 2,
        }
    ]
    with pytest.raises(ValueError, match="ordering marker"):
        GameState.from_snapshot(payload)

    payload = state_for(mini_catalog()).to_snapshot()
    payload["player_memory"]["known_public_facts"] = [
        {
            "fact_ref": "alpine.fact.weather",
            "scenario_id": "missing-scenario",
            "source_event_id": "event.fact",
            "source_sequence_no": 1,
        }
    ]
    payload["player_memory"]["last_applied_source_sequence_no"] = 1
    with pytest.raises(ValueError, match="orphan scenario"):
        GameState.from_snapshot(payload)


def test_v3_scenario_snapshot_round_trips_with_separate_content_version() -> None:
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
    assert restored.schema_version == 3
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
                decision_id="alpine.decision.route",
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
    v1.pop("player_memory")
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
