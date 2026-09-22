from copy import deepcopy
import httpx
import pytest

from deviation_protocol.api.main import create_app
from deviation_protocol.api.demo_composition import build_demo_runtime
from tests.unit.test_native_demo import admit
from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS


async def play_to_ending(client, sid):
    actions = []
    for index, step in enumerate(CANONICAL_ACTIONS):
        response = await client.get(f"/v1/sessions/{sid}/view")
        assert response.status_code == 200, response.text
        view = response.json()
        if view["scenario_status"] == "ENDED":
            return view, actions
        action = dict(turn_id=f"exit.turn.{index}", client_request_id=f"exit.action.{index}", action_type=step.action_type)
        if step.choice_id:
            action.update(choice_id=step.choice_id, decision_id=view["narrative_frame"]["decision_id"])
        if step.description:
            action["description"] = step.description
        response = await client.post(f"/v1/sessions/{sid}/actions", json=action)
        assert response.status_code == 200 and response.json()["state_changed"], response.text
        actions.append((action, response.json()))
    response = await client.get(f"/v1/sessions/{sid}/view")
    assert response.status_code == 200, response.text
    assert response.json()["scenario_status"] == "ENDED"
    return response.json(), actions


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.silent-hunting-ground"])
async def test_public_demo_exit_reentry_and_old_replays(profile):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        admitted, request = await admit(client, profile)
        sid = admitted["session_id"]
        initial = (await client.get(f"/v1/sessions/{sid}/run-status")).json()
        assert initial["can_exit"] is False and initial["run_state_version"] == 3
        ended, actions = await play_to_ending(client, sid)
        old = runtime.store.snapshot()
        status = await client.get(f"/v1/sessions/{sid}/run-status")
        assert status.status_code == 200 and status.json()["can_exit"], status.text
        exit_body = dict(expected_run_state_version=3, expected_session_state_version=ended["metadata"]["state_version"])
        response = await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "exit.one"})
        assert response.status_code == 200, response.text
        terminal = response.json()
        assert terminal["lifecycle_status"] == "terminated" and terminal["run_state_version"] == 4 and not terminal["can_exit"]
        exited = runtime.store.snapshot()
        from deviation_protocol.domain.run import RunId
        async with runtime.store.unit_of_work() as reader:
            family = await reader.run_protocol_bindings.get_classified(run_id=RunId(value=terminal["run_id"]))
            with pytest.raises(RuntimeError, match="native"):
                await reader.runs.append_revision(family.canonical_run,created_at=family.canonical_run.current_mutation_provenance.occurred_at)
        assert runtime.store.snapshot() == exited
        assert all(exited.run_revisions[k] == v for k, v in old.run_revisions.items())
        for name in ("player_character_current", "sessions", "snapshots", "run_protocol_bindings", "run_entry_world_bindings"):
            assert getattr(exited, name) == getattr(old, name)
        assert (await client.get(f"/v1/sessions/{sid}/view")).json() == ended
        discovery = await client.get("/v1/player-characters/eligible-for-run-entry")
        assert discovery.status_code == 200, discovery.text
        new_request = deepcopy(request)
        new_request["expected_record_revision"] = request["expected_record_revision"]
        response = await client.post("/v1/runs/native", json=new_request, headers={"Idempotency-Key": "entry.two"})
        assert response.status_code == 200, response.text
        second = response.json()
        assert second["session_id"] != sid and second["run_context"]["run_id"] != admitted["run_context"]["run_id"]
        settled = runtime.store.snapshot()
        assert (await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "exit.one"})).json() == terminal
        assert (await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": "native.demo"})).json() == admitted
        for action, result in actions:
            assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == result
        assert runtime.store.snapshot() == settled
        response = await client.post(f"/v1/sessions/{sid}/run-exit", json={**exit_body, "expected_session_state_version": 0}, headers={"Idempotency-Key": "exit.one"})
        assert response.status_code == 409 and response.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
        response = await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "exit.other"})
        assert response.status_code == 409 and response.json()["error"]["error_code"] == "RUN_EXIT_NOT_AVAILABLE"
        fresh = (await client.get(f"/v1/sessions/{second['session_id']}/view")).json()
        first_action = {**actions[0][0], "decision_id": fresh["narrative_frame"]["decision_id"]}
        response = await client.post(f"/v1/sessions/{second['session_id']}/actions", json=first_action)
        assert response.status_code == 200 and response.json()["state_changed"], response.text


@pytest.mark.parametrize("raw", [b'{}', b'null', b'{"expected_run_state_version":true,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_run_state_version":3,"expected_session_state_version":0}',
    b'\xef\xbb\xbf{"expected_run_state_version":3,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_session_state_version":0,"run_id":"x"}', b' ' * 1025])
async def test_exit_transport_is_closed_before_lookup(raw):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.post('/v1/sessions/missing/run-exit', content=raw,
            headers={"Idempotency-Key": "exit", "Content-Type": "application/json"})
        assert response.status_code == 422, response.text
        assert response.json()["error"]["error_code"] == "REQUEST_VALIDATION_FAILED"


@pytest.mark.parametrize("case,code", [("active","RUN_EXIT_NOT_AVAILABLE"),("stale","RUN_EXIT_STALE"),
    ("ending", "SNAPSHOT_INVALID"),("memory", "SNAPSHOT_INVALID"),("scenario","SNAPSHOT_INVALID"),
    ("content","SNAPSHOT_INVALID"),("controller","SESSION_NOT_FOUND"),("session","SESSION_NOT_FOUND")])
async def test_e02_invalid_exit_is_read_only(case, code):
    from dataclasses import replace
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        admitted, _ = await admit(client, "difficulty.silent-hunting-ground")
        sid = admitted["session_id"]
        if case != "active": await play_to_ending(client, sid)
        snapshot = runtime.store._snapshots[sid]
        data = deepcopy(snapshot.state)
        if case == "ending": data["scenario_runtime"]["ending_id"] = None
        if case == "memory": data["player_memory"]["scenario_records"] = []
        if case == "scenario": data["scenario_runtime"]["scenario_id"] = "unrelated"
        if case == "content": data["content_version"] = "wrong"
        runtime.store._snapshots[sid] = replace(snapshot, state=data)
        if case == "controller":
            app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="demo-player", authentication_scheme="forged")
        if case == "session": sid = "missing"
        before = runtime.store.snapshot()
        response = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"negative.exit"},
            json={"expected_run_state_version":3,"expected_session_state_version":0 if case == "stale" else snapshot.state_version})
        assert response.status_code == (404 if code == "SESSION_NOT_FOUND" else 409), response.text
        assert response.json()["error"]["error_code"] == code
        assert runtime.store.snapshot() == before


async def test_e09_openapi_projection_privacy_and_restarted_store():
    import json
    from deviation_protocol.api.demo_composition import build_dynamic_demo_runtime
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    schema = app.openapi()
    assert app.openapi() == schema
    assert schema["paths"]["/v1/sessions/{session_id}/run-status"]["get"]["operationId"] == "get_native_run_status"
    post = schema["paths"]["/v1/sessions/{session_id}/run-exit"]["post"]
    assert post["operationId"] == "exit_native_run"
    assert set(post["responses"]) == {"200","404","409","422","500","503"}
    assert len([p for p in post["parameters"] if p["name"] == "Idempotency-Key"]) == 1
    assert schema["components"]["schemas"]["NativeRunExitRequest"]["additionalProperties"] is False
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        admitted, _ = await admit(client, "difficulty.silent-hunting-ground")
        sid = admitted["session_id"]
        ended, _ = await play_to_ending(client, sid)
        response = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"private.exit.key"},
            json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert set(payload) == {"schema_version","session_id","run_id","run_state_version","session_state_version","lifecycle_status","can_exit"}
        text = json.dumps(payload)
        for marker in ("private.exit.key","controller", "fingerprint","snapshot", "operation_id", "continuous_story_line", "source_reference", "SELECT"):
            assert marker not in text
        assert (await client.get(f"/v1/sessions/{sid}/view")).json()["run_context"] == admitted["run_context"]
    for fresh, expected in ((build_demo_runtime(),404),(build_dynamic_demo_runtime(environ={}),503)):
        restarted = create_app(services=fresh.services)
        restarted.state.api_services = fresh.services
        async with httpx.AsyncClient(transport=httpx.ASGITransport(restarted), base_url="http://test") as client:
            response = await client.get(f"/v1/sessions/{sid}/run-status")
            assert response.status_code == expected, response.text


async def test_e02_non_hospital_catalog_valid_ended_fixture(monkeypatch, tmp_path):
    # E02 content boundary fixture; E01 independently plays real public actions.
    from dataclasses import replace
    from deviation_protocol.api import demo_composition
    from deviation_protocol.domain import entry_world
    from deviation_protocol.domain.scenario import ScenarioCatalog
    from deviation_protocol.domain.state import GameState
    from deviation_protocol.application.story_director import DeterministicStoryDirector
    from tests.unit.test_story_director import mini_catalog, VerifiedScenarioEvent
    payload = mini_catalog().model_dump(mode="json")
    payload["content_catalog"]["characters"][0]["resource_caps"] = [{"key":"composure","value":6}]
    definition = payload["scenarios"][0]
    definition["public_client"] = dict(title="Alpine signal", hook="Find the mountain signal",
        playable_characters=[dict(character_definition_id="character.alpine.scout",description="Scout")],
        default_character_definition_id="character.alpine.scout",
        scenes=[dict(phase_id=p["phase_id"],title=p["title"],summary="Mountain route") for p in definition["phases"]],
        endings=[dict(ending_id="alpine.ending.arrived",title="Arrived",summary="Reached the signal")],
        actions=[dict(action_type=a,label=a) for a in ("CUSTOM","EXPLORE","OBSERVE","MOVE","CONTINUE","CHOOSE")])
    definition["memory_rules"] = [dict(rule_id="alpine.start",rule_version="1.0.0",source_event_type="ScenarioStarted",operation="START_SCENARIO"),
        dict(rule_id="alpine.complete",rule_version="1.0.0",source_event_type="ScenarioRuntimeEventGenerated",
        operation="COMPLETE_SCENARIO",requires_scenario_completed=True,allowed_ending_ids=["alpine.ending.arrived"])]
    catalog = ScenarioCatalog.model_validate(payload)
    path = tmp_path / "alpine.json"
    path.write_text(catalog.model_dump_json(),encoding="utf-8")
    # Composition also registers the independently pinned sibling packs.
    for name in ("wind_gate_v1.json", "fog_station_v1.json"):
        (tmp_path / name).write_bytes(demo_composition.SCENARIO_PACK.with_name(name).read_bytes())
    monkeypatch.setattr(demo_composition,"SCENARIO_PACK",path)
    world = entry_world.AUTHORED_ENTRY_WORLDS_V1[0].model_copy(update={"scenario_id":definition["scenario_id"],
        "scenario_content_version":catalog.content_version,"default_character_definition_id":"character.alpine.scout"})
    monkeypatch.setattr(entry_world,"AUTHORED_ENTRY_WORLDS_V1",(world,))
    from deviation_protocol.application.native_turn_mechanics import NativeTurnMechanicsCoordinator
    from deviation_protocol.domain.run_protocol_mechanics import MECHANICS_CATALOGUE
    mechanics = replace(MECHANICS_CATALOGUE[0], scenario_id=world.scenario_id,
        content_version=world.scenario_content_version,character_id=world.default_character_definition_id)
    from deviation_protocol.application import native_turn_mechanics
    monkeypatch.setattr(native_turn_mechanics,"NativeTurnMechanicsCoordinator",lambda c,s:
        NativeTurnMechanicsCoordinator(c,s,catalogue=(mechanics,),worlds=(world,))
        if s.content_version == catalog.content_version else NativeTurnMechanicsCoordinator(c,s))
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        admitted, _ = await admit(client)
        sid = admitted["session_id"]
        snapshot = runtime.store._snapshots[sid]
        state = GameState.from_snapshot(snapshot.state,catalog=catalog.content_catalog,scenario_catalog=catalog)
        director = DeterministicStoryDirector()
        from deviation_protocol.domain.scenario_runtime import FactValueUpdate
        for event in (VerifiedScenarioEvent(event_id="signal",event_type="signal.verified",action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),deferred_bindings=(FactValueUpdate(fact_id="alpine.fact.route",value="north"),)),
            VerifiedScenarioEvent(event_id="route",event_type="route.chosen",action_type="move",new_location_id="alpine.ridge",
                decision_id="alpine.decision.route",resolves_current_decision=True)):
            state = director.advance_after_verified_result(state,catalog.scenarios[0],(event,)).candidate_state
        data = state.model_dump(mode="json")
        data["player_memory"]["scenario_records"] = [dict(scenario_id=definition["scenario_id"],scenario_content_version=catalog.content_version,
            status="COMPLETED",ending_id="alpine.ending.arrived",milestone_refs=["STARTED","COMPLETED","ENDING_CONFIRMED"],
            last_source_event_id="alpine.complete.event",last_source_sequence_no=2)]
        data["player_memory"]["last_applied_source_event_id"] = "alpine.complete.event"
        data["player_memory"]["last_applied_source_sequence_no"] = 2
        # The real snapshot loader must accept the complete authored runtime/memory.
        data = GameState.from_snapshot(data,catalog=catalog.content_catalog,scenario_catalog=catalog).to_snapshot()
        runtime.store._sessions[sid].session.state_version = 1
        runtime.store._snapshots[sid] = replace(snapshot,state=data,state_version=1)
        before = runtime.store.snapshot()
        response = await client.post(f"/v1/sessions/{sid}/run-exit",headers={"Idempotency-Key":"alpine.exit"},
            json={"expected_run_state_version":3,"expected_session_state_version":1})
        assert response.status_code == 200, response.text
        assert response.json()["lifecycle_status"] == "terminated"
        assert runtime.store.snapshot().snapshots == before.snapshots


async def test_e09_legacy_session_is_not_native_and_get_is_strict():
    from tests.integration.test_mysql_run_entry_playthrough import _entry
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        created = await client.post("/v1/player-characters",headers={"Idempotency-Key":"legacy.character"},
            json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
        entered = await _entry(client,key="legacy.entry",character_id=created.json()["player_character_id"]["value"])
        assert entered.status_code == 200,entered.text
        sid = entered.json()["session_id"]
        before = runtime.store.snapshot()
        response = await client.get(f"/v1/sessions/{sid}/run-status")
        assert response.status_code == 409 and response.json()["error"]["error_code"] == "NATIVE_RUN_REQUIRED"
        for kwargs in ({"content":b"x"},{"params":{"x":"1"}},{"headers":[("Content-Type","application/json"),("Content-Type","application/json")]}):
            assert (await client.request("GET",f"/v1/sessions/{sid}/run-status",**kwargs)).status_code == 422
        assert runtime.store.snapshot() == before
