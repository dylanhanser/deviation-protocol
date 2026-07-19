from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorError,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.facts import FactKind, StoryFact, StoryMutation, StoryMutationError, StoryMutationValidator
from deviation_protocol.domain.scenario import FrameMode, ScenarioCatalog
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    VerifiedScenarioEvent as UntrustedVerifiedScenarioEvent,
    _issue_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState, PlayerState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader


DEATH_PACK = Path(__file__).parents[2] / "config" / "scenarios" / "death_certificate_v1.json"
VerifiedScenarioEvent = _issue_verified_scenario_event


def mini_catalog() -> ScenarioCatalog:
    return ScenarioCatalog.model_validate(
        {
            "schema_version": 1,
            "content_version": "alpine-signal-1",
            "content_catalog": {
                "schema_version": 1,
                "content_version": "alpine-signal-1",
                "characters": [
                    {
                        "definition_id": "character.alpine.scout",
                        "display_name": "山地巡查员",
                        "base_attributes": [],
                        "resource_caps": [],
                        "equipment_slots": [],
                        "tags": ["player"],
                    },
                    {
                        "definition_id": "character.alpine.ranger",
                        "display_name": "护林员模板",
                        "base_attributes": [],
                        "resource_caps": [],
                        "equipment_slots": [],
                        "tags": ["npc"],
                    },
                ],
                "npcs": [
                    {
                        "definition_id": "npc.alpine.ranger",
                        "character_definition_id": "character.alpine.ranger",
                        "display_name": "护林员",
                        "persona_summary": "只使用自己核实过的山地信号信息。",
                        "tags": ["ranger"],
                    }
                ],
                "items": [],
                "equipment": [],
                "skills": [],
                "effects": [],
            },
            "scenarios": [
                {
                    "scenario_id": "alpine_signal",
                    "schema_version": 1,
                    "content_version": "alpine-signal-1",
                    "title": "山脊信号",
                    "summary": "巡查员在风暴抵达前核验山脊信号。",
                    "initial_phase_id": "alpine.search",
                    "initial_location_id": "alpine.camp",
                    "locations": [
                        {
                            "location_id": "alpine.camp",
                            "title": "营地",
                            "summary": "山脊下的临时营地。",
                            "initially_open": True,
                            "visible_entity_ids": ["npc.alpine.ranger"],
                        },
                        {
                            "location_id": "alpine.ridge",
                            "title": "山脊",
                            "summary": "信号来源所在的高地。",
                            "initially_open": True,
                            "visible_entity_ids": [],
                        },
                    ],
                    "npc_references": [
                        {
                            "npc_definition_id": "npc.alpine.ranger",
                            "known_fact_ids": ["alpine.fact.weather"],
                        }
                    ],
                    "facts": [
                        {
                            "fact_id": "alpine.fact.weather",
                            "kind": "FIXED",
                            "visibility": "PLAYER_KNOWN",
                            "value": "storm_approaching",
                        },
                        {
                            "fact_id": "alpine.fact.signal_origin",
                            "kind": "FIXED",
                            "visibility": "DISCOVERABLE",
                            "value": "ridge_beacon",
                        },
                        {
                            "fact_id": "alpine.fact.route",
                            "kind": "DEFERRED",
                            "visibility": "DISCOVERABLE",
                            "deferred_candidates": ["north", "south"],
                        },
                        {
                            "fact_id": "alpine.fact.beacon_active",
                            "kind": "MUTABLE",
                            "visibility": "PLAYER_KNOWN",
                            "value": True,
                            "mutable_transitions": [
                                {
                                    "from_value": True,
                                    "to_value": False,
                                    "event_type": "beacon.disabled",
                                }
                            ],
                        },
                    ],
                    "clues": [
                        {
                            "clue_id": "alpine.clue.signal_trace",
                            "supports_fact_ids": ["alpine.fact.signal_origin"],
                            "source_event_types": ["signal.verified"],
                            "allowed_phase_ids": ["alpine.search"],
                            "visible_summary": "信号轨迹指向山脊信标。",
                        }
                    ],
                    "clue_groups": [
                        {
                            "clue_group_id": "alpine_signal_located",
                            "clue_ids": ["alpine.clue.signal_trace"],
                            "required_count": 1,
                            "completion_event_type": "signal.group.completed",
                        }
                    ],
                    "threat_clocks": [
                        {
                            "clock_id": "alpine_storm",
                            "minimum": 0,
                            "maximum": 3,
                            "initial": 0,
                            "player_visible": True,
                            "thresholds": [
                                {"threshold": 2, "event_type": "storm.warning"}
                            ],
                        }
                    ],
                    "decision_windows": [
                        {
                            "decision_id": "alpine.decision.route",
                            "reason": "ROUTE_DIVERGENCE",
                            "earliest_beat": 1,
                            "latest_beat": 1,
                            "conditions": [
                                {
                                    "rule_type": "CLUE_GROUP_COMPLETE",
                                    "clue_group_id": "alpine_signal_located",
                                }
                            ],
                            "suggested_actions": [
                                {
                                    "action_id": "alpine.action.ridge",
                                    "action_type": "move",
                                    "label_hint": "沿山脊接近信标",
                                },
                                {
                                    "action_id": "alpine.action.shelter",
                                    "action_type": "commit",
                                    "label_hint": "先固定避风路线",
                                },
                            ],
                            "custom_action_constraints": {
                                "allowed_action_types": ["move", "commit"],
                                "max_description_length": 300,
                                "must_target_visible_entity": False,
                            },
                        }
                    ],
                    "phases": [
                        {
                            "phase_id": "alpine.search",
                            "title": "搜索",
                            "must_render_fact_ids": ["alpine.fact.weather"],
                            "allowed_clue_ids": ["alpine.clue.signal_trace"],
                            "visible_location_ids": ["alpine.camp", "alpine.ridge"],
                            "allowed_action_types": ["investigate", "move", "commit", "observe"],
                            "min_auto_beats": 1,
                            "max_auto_beats": 2,
                            "decision_window_ids": ["alpine.decision.route"],
                            "transitions": [
                                {
                                    "transition_id": "alpine.transition.to_ridge",
                                    "target_phase_id": "alpine.summit",
                                    "trigger": "DECISION",
                                    "conditions": [
                                        {
                                            "rule_type": "CLUE_GROUP_COMPLETE",
                                            "clue_group_id": "alpine_signal_located",
                                        }
                                    ],
                                }
                            ],
                            "action_time_costs": [
                                {
                                    "action_type": "investigate",
                                    "clock_advances": [
                                        {"clock_id": "alpine_storm", "amount": 2}
                                    ],
                                }
                            ],
                            "rapid_decision_allowed": False,
                        },
                        {
                            "phase_id": "alpine.summit",
                            "title": "抵达",
                            "must_render_fact_ids": ["alpine.fact.signal_origin"],
                            "allowed_clue_ids": [],
                            "visible_location_ids": ["alpine.ridge"],
                            "allowed_action_types": ["observe"],
                            "min_auto_beats": 0,
                            "max_auto_beats": 0,
                            "terminal": True,
                        },
                    ],
                    "endings": [
                        {
                            "ending_id": "alpine.ending.arrived",
                            "status": "RESOLVED",
                            "conditions": [
                                {"rule_type": "EVENT_OCCURRED", "event_type": "route.chosen"}
                            ],
                        }
                    ],
                    "available_profession_tags": [],
                    "story_item_definition_ids": [],
                    "dynamic_fact_limit": 1,
                    "dynamic_fact_key_max_length": 40,
                    "dynamic_fact_value_max_length": 40,
                    "narrative_length": {"target": 200, "minimum": 100, "maximum": 300},
                }
            ],
        }
    )


def state_for(catalog: ScenarioCatalog) -> GameState:
    character = catalog.content_catalog.character("character.alpine.scout")
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    state.spawn_npc(
        catalog.content_catalog,
        "npc.alpine.ranger",
        "alpine-ranger-runtime",
    )
    return state


def test_non_hospital_scenario_uses_same_loader_catalog_and_director_end_to_end(
    tmp_path: Path,
) -> None:
    path = tmp_path / "alpine_signal_v1.json"
    path.write_text(
        mini_catalog().model_dump_json(),
        encoding="utf-8",
    )
    catalog = JsonScenarioCatalogLoader(path).load()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    assert started.frame.mode is FrameMode.FLOW
    assert started.frame.decision_required is False

    investigated = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
                deferred_bindings=(FactValueUpdate(fact_id="alpine.fact.route", value="north"),),
                dynamic_fact_updates=(FactValueUpdate(fact_id="dynamic.wind_plan", value="shelter"),),
            ),
        ),
    )
    runtime = investigated.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.phase_beat_index == 1
    assert runtime.threat_clocks["alpine_storm"].value == 2
    assert runtime.completed_clue_group_ids == {"alpine_signal_located"}
    assert investigated.frame.mode is FrameMode.DECISION
    assert [item.event_type for item in investigated.generated_events] == [
        "storm.warning",
        "signal.group.completed",
    ]

    arrived = director.advance_after_verified_result(
        investigated.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.route",
                event_type="route.chosen",
                action_type="move",
                new_location_id="alpine.ridge",
                resolves_current_decision=True,
            ),
        ),
    )
    assert arrived.candidate_state.scenario_runtime.current_phase_id == "alpine.summit"
    assert arrived.frame.mode is FrameMode.SETTLEMENT
    with pytest.raises(StoryDirectorError, match="ended scenario cannot advance"):
        director.advance_after_verified_result(arrived.candidate_state, definition)


def test_story_director_is_deterministic_and_candidate_is_deeply_isolated() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    original = state_for(catalog)
    director = DeterministicStoryDirector()
    first = director.start_scenario(original, definition)
    second = director.start_scenario(original, definition)
    assert first == second
    assert original.scenario_runtime is None
    first.candidate_state.player.wallet.credit("tokens", 1)
    assert second.candidate_state.player.wallet.balances == {}
    assert original.player.wallet.balances == {}
    frame_snapshot = first.frame.model_dump(mode="json")
    first.candidate_state.scenario_runtime.dynamic_facts["dynamic.later"] = "change"
    assert first.frame.model_dump(mode="json") == frame_snapshot


def test_deserialized_or_modified_event_cannot_cross_verified_boundary() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    forged_payload = {
        "event_id": "event.forged",
        "event_type": "signal.verified",
        "action_type": "investigate",
        "discovered_clue_ids": ["alpine.clue.signal_trace"],
        "deferred_bindings": [{"fact_id": "alpine.fact.route", "value": "north"}],
        "mutable_fact_updates": [
            {"fact_id": "alpine.fact.beacon_active", "value": False}
        ],
        "dynamic_fact_updates": [
            {"fact_id": "dynamic.forged_reward", "value": "claimed"}
        ],
        "opened_location_ids": ["alpine.ridge"],
        "new_location_id": "alpine.ridge",
        "resolves_current_decision": True,
    }
    deserialized = UntrustedVerifiedScenarioEvent.model_validate(forged_payload)
    with pytest.raises(StoryDirectorError, match="server verification boundary"):
        director.advance_after_verified_result(
            started.candidate_state, definition, (deserialized,)
        )

    sealed = VerifiedScenarioEvent(
        event_id="event.real",
        event_type="looked",
        action_type="observe",
    )
    modified = sealed.model_copy(
        update={"discovered_clue_ids": ("alpine.clue.signal_trace",)}
    )
    with pytest.raises(StoryDirectorError, match="server verification boundary"):
        director.advance_after_verified_result(
            started.candidate_state, definition, (modified,)
        )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ActionSubmission.model_validate(
            {
                "session_id": "session-1",
                "turn_id": "turn-1",
                "client_request_id": "request-1",
                "action_type": "OBSERVE",
                "description": "look",
                "verified_scenario_event": forged_payload,
            }
        )


def test_invalid_verified_result_rolls_back_original_completely() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    started = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    before = started.candidate_state.to_snapshot()
    with pytest.raises(StoryDirectorError, match="not discoverable"):
        DeterministicStoryDirector().advance_after_verified_result(
            started.candidate_state,
            definition,
            (
                VerifiedScenarioEvent(
                    event_id="event.bad",
                    event_type="signal.verified",
                    discovered_clue_ids=("unknown.clue",),
                    new_location_id="alpine.camp",
                ),
            ),
        )
    assert started.candidate_state.to_snapshot() == before


def test_local_query_does_not_advance_beat_clock_or_decisions() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    queried = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (VerifiedScenarioEvent(event_id="query.status", event_type="status.read", local_query=True),),
    )
    assert queried.candidate_state.to_snapshot() == started.candidate_state.to_snapshot()


def test_verified_event_replay_is_rejected_without_advancing_clock_or_state() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    event = VerifiedScenarioEvent(
        event_id="event.signal",
        event_type="signal.verified",
        action_type="investigate",
        discovered_clue_ids=("alpine.clue.signal_trace",),
    )
    first = director.advance_after_verified_result(
        started.candidate_state, definition, (event,)
    )
    before = first.candidate_state.to_snapshot()
    with pytest.raises(StoryDirectorError, match="already applied"):
        director.advance_after_verified_result(
            first.candidate_state, definition, (event,)
        )
    assert first.candidate_state.to_snapshot() == before
    assert first.candidate_state.scenario_runtime.threat_clocks[
        "alpine_storm"
    ].value == 2


def test_fixed_deferred_mutable_and_dynamic_boundaries() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    before = started.candidate_state.to_snapshot()
    with pytest.raises(StoryDirectorError, match="only MUTABLE"):
        director.advance_after_verified_result(
            started.candidate_state,
            definition,
            (
                VerifiedScenarioEvent(
                    event_id="event.fixed",
                    event_type="beacon.disabled",
                    mutable_fact_updates=(FactValueUpdate(fact_id="alpine.fact.weather", value="clear"),),
                ),
            ),
        )
    assert started.candidate_state.to_snapshot() == before

    validator = StoryMutationValidator(dynamic_fact_limit=1, dynamic_key_max_length=30, dynamic_value_max_length=10)
    fixed = StoryFact("dynamic.reserved", FactKind.FIXED, True)
    with pytest.raises(StoryMutationError, match="FIXED"):
        validator.validate(fixed, StoryMutation("dynamic.reserved", False, causal_event_id="event"))
    with pytest.raises(StoryMutationError, match="count"):
        validator.validate_dynamic_collection(
            {"dynamic.one": StoryFact("dynamic.one", FactKind.DYNAMIC, 1)},
            StoryMutation("dynamic.two", 2, kind=FactKind.DYNAMIC, causal_event_id="event"),
        )
    with pytest.raises(StoryMutationError, match="length"):
        validator.validate_dynamic_collection(
            {},
            StoryMutation("dynamic.one", "value-is-too-long", kind=FactKind.DYNAMIC, causal_event_id="event"),
        )


def test_hidden_truth_and_unowned_npc_knowledge_do_not_leak_into_frame() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    started = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    all_player_fact_ids = {
        item.fact_id for item in (*started.frame.must_render_facts, *started.frame.may_render_facts)
    }
    assert "alpine.fact.signal_origin" not in all_player_fact_ids
    assert started.frame.npc_knowledge[0].known_facts[0].fact_id == "alpine.fact.weather"
    assert all(
        fact.fact_id != "alpine.fact.signal_origin"
        for npc in started.frame.npc_knowledge
        for fact in npc.known_facts
    )
    with pytest.raises(ValidationError):
        started.frame.npc_knowledge[0].known_facts = ()
    serialized = json.dumps(
        started.frame.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
    )
    assert "alpine.fact.signal_origin" not in serialized
    assert "ridge_beacon" not in serialized
    assert "alpine.ending.arrived" not in serialized


def test_serialized_frame_excludes_visible_npc_secrets_hidden_events_and_endings() -> None:
    catalog = JsonScenarioCatalogLoader(DEATH_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character("character.death_certificate.investigator")
    assert character is not None
    director = DeterministicStoryDirector()
    started = director.start_scenario(
        GameState(
            content_version=catalog.content_version,
            player=PlayerState.from_definition("player-1", character),
        ),
        definition,
    )
    candidate = deepcopy(started.candidate_state)
    candidate.spawn_npc(
        catalog.content_catalog,
        "npc.death_certificate.records_custodian",
        "records-custodian-runtime",
    )
    runtime = candidate.scenario_runtime
    assert runtime is not None
    runtime.current_phase_id = "death_certificate.investigation"
    runtime.current_location_id = "death_certificate.records_room"
    runtime.opened_location_ids = runtime.opened_location_ids | {
        "death_certificate.records_room"
    }
    runtime.current_decision_id = None
    runtime.phase_beat_index = 0
    runtime.phase_visit_counts["death_certificate.investigation"] = 1

    frame = director.plan_frame(candidate, definition)
    assert frame.visible_entities == ("records-custodian-runtime",)
    assert frame.npc_knowledge[0].known_facts == ()
    serialized = json.dumps(
        frame.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    for forbidden in (
        "death_certificate.fact.record_predates_diagnosis",
        "death_certificate.fact.record_signature_valid",
        "death_certificate.fact.prediction_causes_outcome",
        "security.alert.high",
        "death_certificate.ending.deadline_reached",
        "death_certificate.ending.protocol_broken",
    ):
        assert forbidden not in serialized


def test_hidden_clock_threshold_event_is_internal_but_not_in_serialized_frame() -> None:
    payload = mini_catalog().model_dump(mode="json")
    payload["scenarios"][0]["threat_clocks"][0]["player_visible"] = False
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    result = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
                expose_in_frame=True,
            ),
        ),
    )
    assert "storm.warning" in {
        item.event_type for item in result.generated_events
    }
    serialized = json.dumps(result.frame.model_dump(mode="json"), sort_keys=True)
    assert "storm.warning" not in serialized
    assert "alpine_storm" not in serialized
    assert "signal.verified" in serialized


def test_open_decision_requires_response_and_each_frame_has_single_decision_payload() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    decision = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    assert decision.frame.decision_required
    assert decision.frame.decision_reason is not None
    with pytest.raises(StoryDirectorError, match="requires a verified player response"):
        director.advance_after_verified_result(decision.candidate_state, definition)

    damaged = deepcopy(decision.candidate_state)
    assert damaged.scenario_runtime is not None
    damaged.scenario_runtime.current_decision_id = None
    with pytest.raises(StoryDirectorError, match="eligible decision is missing"):
        director.plan_frame(damaged, definition)


def test_trivial_action_does_not_create_a_decision_without_an_eligible_window() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    result = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.looked",
                event_type="door.opened",
                action_type="observe",
            ),
        ),
    )
    assert result.frame.mode is FrameMode.FLOW
    assert result.frame.decision_required is False


def test_phase_with_zero_windows_can_auto_advance_without_inventing_choice() -> None:
    catalog = JsonScenarioCatalogLoader(DEATH_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character("character.death_certificate.investigator")
    assert character is not None
    director = DeterministicStoryDirector()
    started = director.start_scenario(
        GameState(
            content_version=catalog.content_version,
            player=PlayerState.from_definition("player-1", character),
        ),
        definition,
    )
    state = deepcopy(started.candidate_state)
    runtime = state.scenario_runtime
    assert runtime is not None
    runtime.current_phase_id = "death_certificate.disposal_escape"
    runtime.current_location_id = "death_certificate.service_corridor"
    runtime.current_decision_id = None
    runtime.phase_beat_index = 0
    runtime.phase_visit_counts["death_certificate.disposal_escape"] = 1
    first = director.advance_after_verified_result(state, definition)
    assert first.frame.mode is FrameMode.FLOW
    assert first.candidate_state.scenario_runtime.current_phase_id == (
        "death_certificate.disposal_escape"
    )
    second = director.advance_after_verified_result(first.candidate_state, definition)
    assert second.candidate_state.scenario_runtime.current_phase_id == (
        "death_certificate.investigation"
    )
    assert second.frame.decision_required is False


def test_phase_progress_cannot_continue_forever_past_configured_maximum() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    first = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (VerifiedScenarioEvent(event_id="event.one", event_type="looked", action_type="observe"),),
    )
    before = first.candidate_state.to_snapshot()
    with pytest.raises(StoryDirectorError, match="max_auto_beats"):
        director.advance_after_verified_result(
            first.candidate_state,
            definition,
            (VerifiedScenarioEvent(event_id="event.two", event_type="waited", action_type="observe"),),
        )
    assert first.candidate_state.to_snapshot() == before


def test_multiple_eligible_transitions_use_explicit_priority_not_list_order() -> None:
    payload = mini_catalog().model_dump(mode="json")
    phase = payload["scenarios"][0]["phases"][0]
    original = phase["transitions"][0]
    original["priority"] = 50
    preferred = deepcopy(original)
    preferred["transition_id"] = "alpine.transition.preferred"
    preferred["priority"] = 10
    phase["transitions"] = [original, preferred]
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    decision = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    arrived = director.advance_after_verified_result(
        decision.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.route",
                event_type="route.chosen",
                action_type="move",
                new_location_id="alpine.ridge",
                resolves_current_decision=True,
            ),
        ),
    )
    runtime = arrived.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.transition_use_counts == {"alpine.transition.preferred": 1}


def test_multiple_matching_endings_use_explicit_priority_not_list_order() -> None:
    payload = mini_catalog().model_dump(mode="json")
    preferred = deepcopy(payload["scenarios"][0]["endings"][0])
    preferred["ending_id"] = "alpine.ending.priority_failure"
    preferred["status"] = "FAILED"
    preferred["priority"] = 5
    payload["scenarios"][0]["endings"][0]["priority"] = 50
    payload["scenarios"][0]["endings"].append(preferred)
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    decision = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    ended = director.advance_after_verified_result(
        decision.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.route",
                event_type="route.chosen",
                action_type="move",
                new_location_id="alpine.ridge",
                resolves_current_decision=True,
            ),
        ),
    )
    runtime = ended.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.ending_id == "alpine.ending.priority_failure"


def test_multiple_simultaneous_windows_choose_declared_phase_order_once() -> None:
    payload = mini_catalog().model_dump(mode="json")
    scenario_payload = payload["scenarios"][0]
    alternate = deepcopy(scenario_payload["decision_windows"][0])
    alternate["decision_id"] = "alpine.decision.alternate"
    for index, action in enumerate(alternate["suggested_actions"]):
        action["action_id"] = f"alpine.action.alternate_{index}"
    scenario_payload["decision_windows"].append(alternate)
    scenario_payload["phases"][0]["decision_window_ids"] = [
        "alpine.decision.alternate",
        "alpine.decision.route",
    ]
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    result = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    runtime = result.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.current_decision_id == "alpine.decision.alternate"
    assert result.frame.decision_required


def test_resolved_one_time_window_does_not_reopen_in_same_phase() -> None:
    payload = mini_catalog().model_dump(mode="json")
    phase = payload["scenarios"][0]["phases"][0]
    phase["max_auto_beats"] = 3
    phase["transitions"][0]["conditions"] = [
        {"rule_type": "DECISIONS_AT_LEAST", "value": 99}
    ]
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    decision = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    resolved = director.advance_after_verified_result(
        decision.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.route.response",
                event_type="route.responded",
                action_type="move",
                resolves_current_decision=True,
            ),
        ),
    )
    runtime = resolved.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.current_decision_id is None
    assert runtime.decisions_made == ("alpine.decision.route",)
    assert resolved.frame.mode is FrameMode.FLOW


def test_multi_clock_failure_leaves_original_state_completely_unchanged() -> None:
    payload = mini_catalog().model_dump(mode="json")
    scenario_payload = payload["scenarios"][0]
    scenario_payload["locations"][1]["initially_open"] = False
    scenario_payload["threat_clocks"].append(
        {
            "clock_id": "alpine_visibility",
            "minimum": 0,
            "maximum": 3,
            "initial": 0,
            "player_visible": False,
            "thresholds": [],
        }
    )
    cost = scenario_payload["phases"][0]["action_time_costs"][0]
    cost["clock_advances"].append(
        {"clock_id": "alpine_visibility", "amount": 1}
    )
    transition = scenario_payload["phases"][0]["transitions"][0]
    transition["trigger"] = "VERIFIED_EVENT"
    catalog = ScenarioCatalog.model_validate(payload)
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    before = started.candidate_state.to_snapshot()
    with pytest.raises(StoryDirectorError, match="no open visible location"):
        director.advance_after_verified_result(
            started.candidate_state,
            definition,
            (
                VerifiedScenarioEvent(
                    event_id="event.signal",
                    event_type="signal.verified",
                    action_type="investigate",
                    discovered_clue_ids=("alpine.clue.signal_trace",),
                ),
            ),
        )
    assert started.candidate_state.to_snapshot() == before


def test_deferred_fact_binds_once_and_clue_discovery_is_idempotent() -> None:
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    first = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace", "alpine.clue.signal_trace"),
                deferred_bindings=(FactValueUpdate(fact_id="alpine.fact.route", value="north"),),
            ),
        ),
    )
    runtime = first.candidate_state.scenario_runtime
    assert runtime is not None
    assert runtime.discovered_clue_ids == {"alpine.clue.signal_trace"}
    assert len(runtime.completed_clue_group_ids) == 1
    with pytest.raises(StoryDirectorError, match="only be bound once"):
        director.advance_after_verified_result(
            first.candidate_state,
            definition,
            (
                VerifiedScenarioEvent(
                    event_id="event.rebind",
                    event_type="route.chosen",
                    resolves_current_decision=True,
                    deferred_bindings=(FactValueUpdate(fact_id="alpine.fact.route", value="south"),),
                ),
            ),
        )


def test_director_never_generates_anomaly_candidate() -> None:
    source = Path("src/deviation_protocol/application/story_director.py").read_text(encoding="utf-8")
    assert "ANOMALY_EVALUATION_REQUIRED" not in source


def test_death_scenario_opens_once_then_uses_sparse_and_rapid_cadence() -> None:
    catalog = JsonScenarioCatalogLoader(DEATH_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character("character.death_certificate.investigator")
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    director = DeterministicStoryDirector()
    opened = director.start_scenario(state, definition)
    assert opened.frame.mode is FrameMode.DECISION
    assert opened.candidate_state.scenario_runtime.current_decision_id == (
        "death_certificate.decision.immediate_survival"
    )

    disputed = director.advance_after_verified_result(
        opened.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.survived",
                event_type="survival.response.verified",
                action_type="respond",
                resolves_current_decision=True,
            ),
        ),
    )
    assert disputed.frame.mode is FrameMode.FLOW
    current = disputed
    for _ in range(2):
        current = director.advance_after_verified_result(current.candidate_state, definition)
        assert current.frame.mode is FrameMode.FLOW
    current = director.advance_after_verified_result(current.candidate_state, definition)
    assert current.frame.mode is FrameMode.DECISION
    assert current.candidate_state.scenario_runtime.current_decision_id == (
        "death_certificate.decision.early_strategy"
    )

    rapid_state = deepcopy(current.candidate_state)
    runtime = rapid_state.scenario_runtime
    assert runtime is not None
    runtime.current_phase_id = "death_certificate.core_conflict"
    runtime.current_location_id = "death_certificate.control_room"
    runtime.opened_location_ids = runtime.opened_location_ids | {
        "death_certificate.control_room"
    }
    runtime.phase_beat_index = 0
    runtime.current_decision_id = "death_certificate.decision.core_one"
    runtime.rapid_decision_mode = True
    runtime.phase_visit_counts["death_certificate.core_conflict"] = 1
    rapid = director.plan_frame(rapid_state, definition)
    assert rapid.mode is FrameMode.RAPID_DECISION
    assert rapid.decision_required is True


def test_death_initial_frame_projects_opening_hook_without_hidden_truths() -> None:
    catalog = JsonScenarioCatalogLoader(DEATH_PACK).load()
    definition = catalog.scenario("death_certificate")
    assert definition is not None
    character = catalog.content_catalog.character(
        "character.death_certificate.investigator"
    )
    assert character is not None
    opened = DeterministicStoryDirector().start_scenario(
        GameState(
            content_version=catalog.content_version,
            player=PlayerState.from_definition("player-1", character),
        ),
        definition,
    )

    must_render = {item.fact_id: item.value for item in opened.frame.must_render_facts}
    body_bag = must_render["death_certificate.fact.opening_body_bag_state"]
    assert body_bag == {
        "container_type": "BODY_BAG",
        "player_position": "INSIDE",
        "zipper_motion": "CLOSING",
    }
    time_conflict = must_render["death_certificate.fact.opening_time_conflict"]
    assert time_conflict["awareness_time"]["hour"] == 2
    assert time_conflict["awareness_time"]["minute"] == 18
    assert time_conflict["recorded_death_time"]["hour"] == 2
    assert time_conflict["recorded_death_time"]["minute"] == 31
    assert time_conflict["difference_minutes"] == 13
    assert time_conflict["deadline_clock_id"] == "predicted_death_deadline"
    assert must_render["death_certificate.fact.death_certificate_issued"] is True
    assert must_render[
        "death_certificate.fact.comfort_disposition_imminent"
    ]["status"] == "IMMINENT"

    objective = must_render[
        "death_certificate.fact.initial_survival_objective"
    ]
    assert objective["objective_type"] == "NPC_ACKNOWLEDGES_PLAYER_ALIVE"
    assert objective["acknowledgement_mode"] == "EXPLICIT"
    assert objective["minimum_acknowledging_npcs"] == 1
    assert objective["npc_scope"] == "RUNTIME_NPC"
    assert objective["deadline_relation"] == "BEFORE"
    assert objective["deadline_time"] == {
        "hour": 2,
        "minute": 31,
        "minutes_after_midnight": 151,
    }

    assert opened.frame.mode is FrameMode.DECISION
    assert opened.frame.decision_required is True
    initial_phase = definition.phase(definition.initial_phase_id)
    assert initial_phase is not None
    assert initial_phase.decision_window_ids == (
        "death_certificate.decision.immediate_survival",
    )
    assert [item.action_id for item in opened.frame.suggested_actions] == [
        "death_certificate.action.move_fingers_rhythmically",
        "death_certificate.action.interfere_pulse_oximeter",
        "death_certificate.action.adjust_breathing_signal",
        "death_certificate.action.observe_quietly",
    ]
    assert [item.label_hint for item in opened.frame.suggested_actions] == [
        "有规律地移动仍可控制的手指",
        "干扰指夹式血氧传感器",
        "调整呼吸制造可识别生命信号",
        "保持安静并获取现场信息",
    ]
    assert opened.frame.allowed_custom_action_constraints is not None
    assert opened.frame.allowed_custom_action_constraints.allowed_action_types == (
        "respond",
        "physical_response",
        "observe",
    )
    deadline = next(
        item
        for item in opened.frame.player_visible_clocks
        if item.clock_id == "predicted_death_deadline"
    )
    assert (deadline.value, deadline.maximum) == (0, 13)

    serialized = opened.frame.model_dump_json()
    for hidden_token in (
        "prediction_causes_outcome",
        "underground_patient",
        "self_fulfilling_truth",
        "death_certificate.ending.",
    ):
        assert hidden_token not in serialized


def test_death_scenario_all_seven_phases_are_reachable_through_generic_runtime() -> None:
    catalog = JsonScenarioCatalogLoader(DEATH_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character("character.death_certificate.investigator")
    assert character is not None
    director = DeterministicStoryDirector()
    current = director.start_scenario(
        GameState(
            content_version=catalog.content_version,
            player=PlayerState.from_definition("player-1", character),
        ),
        definition,
    )
    visited = [current.candidate_state.scenario_runtime.current_phase_id]

    current = director.advance_after_verified_result(
        current.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.survival",
                event_type="survival.response.verified",
                action_type="respond",
                resolves_current_decision=True,
            ),
        ),
    )
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)
    for _ in range(3):
        current = director.advance_after_verified_result(
            current.candidate_state, definition
        )
    current = director.advance_after_verified_result(
        current.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.early-route",
                event_type="route.selected",
                action_type="move",
                resolves_current_decision=True,
            ),
        ),
    )
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)
    current = director.advance_after_verified_result(current.candidate_state, definition)
    current = director.advance_after_verified_result(current.candidate_state, definition)
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)

    clue_batches = (
        (
            VerifiedScenarioEvent(
                event_id="event.record-time",
                event_type="record.timestamp_verified",
                action_type="investigate",
                discovered_clue_ids=("death_certificate.clue.record_timestamp",),
            ),
            VerifiedScenarioEvent(
                event_id="event.record-audit",
                event_type="record.audit_verified",
                discovered_clue_ids=("death_certificate.clue.audit_sequence",),
            ),
        ),
        (
            VerifiedScenarioEvent(
                event_id="event.protocol-feedback",
                event_type="protocol.feedback_verified",
                action_type="investigate",
                discovered_clue_ids=("death_certificate.clue.protocol_feedback",),
            ),
            VerifiedScenarioEvent(
                event_id="event.case-comparison",
                event_type="case.compared",
                discovered_clue_ids=("death_certificate.clue.comparison_case",),
            ),
        ),
        (
            VerifiedScenarioEvent(
                event_id="event.patient-vitals",
                event_type="patient.vitals_verified",
                action_type="investigate",
                discovered_clue_ids=("death_certificate.clue.patient_vitals",),
                opened_location_ids=("death_certificate.observation_level",),
                new_location_id="death_certificate.observation_level",
                resolves_current_decision=True,
            ),
            VerifiedScenarioEvent(
                event_id="event.patient-history",
                event_type="patient.history_verified",
                discovered_clue_ids=("death_certificate.clue.monitor_history",),
            ),
        ),
    )
    for batch in clue_batches:
        current = director.advance_after_verified_result(
            current.candidate_state, definition, batch
        )
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)

    current = director.advance_after_verified_result(current.candidate_state, definition)
    current = director.advance_after_verified_result(
        current.candidate_state,
        definition,
        (
            VerifiedScenarioEvent(
                event_id="event.control-opened",
                event_type="control.route.opened",
                action_type="observe",
                opened_location_ids=("death_certificate.control_room",),
            ),
        ),
    )
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)

    for index, (event_type, action_type) in enumerate(
        (
            ("core.step.one", "commit"),
            ("core.step.two", "talk"),
            ("core.step.three", "commit"),
            ("core.conflict.resolved", "commit"),
        ),
        start=1,
    ):
        current = director.advance_after_verified_result(
            current.candidate_state,
            definition,
            (
                VerifiedScenarioEvent(
                    event_id=f"event.core.{index}",
                    event_type=event_type,
                    action_type=action_type,
                    resolves_current_decision=True,
                ),
            ),
        )
    visited.append(current.candidate_state.scenario_runtime.current_phase_id)

    assert visited == [
        "death_certificate.arrival_locked",
        "death_certificate.life_disputed",
        "death_certificate.disposal_escape",
        "death_certificate.investigation",
        "death_certificate.self_fulfilling_truth",
        "death_certificate.core_conflict",
        "death_certificate.resolution",
    ]
    assert current.frame.mode is FrameMode.SETTLEMENT
    assert current.candidate_state.scenario_runtime.ending_id == (
        "death_certificate.ending.record_challenged"
    )


def test_generic_runtime_modules_contain_no_first_scenario_identifiers_or_special_fields() -> None:
    paths = (
        Path("src/deviation_protocol/domain/scenario.py"),
        Path("src/deviation_protocol/domain/scenario_runtime.py"),
        Path("src/deviation_protocol/domain/scenario_rules.py"),
        Path("src/deviation_protocol/domain/decision_cadence.py"),
        Path("src/deviation_protocol/domain/narrative.py"),
        Path("src/deviation_protocol/application/story_director.py"),
        Path("src/deviation_protocol/infrastructure/scenario_loader.py"),
    )
    forbidden = (
        "death_certificate",
        "arrival_locked",
        "triage_coordinator",
        "underground_patient",
        "hospital",
        "nurse",
    )
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
    assert not any(term in combined for term in forbidden)
