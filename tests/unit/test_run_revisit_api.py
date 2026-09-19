"""Production Demo composition journeys; no injected endings or transition evidence."""
from copy import deepcopy

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending


async def view(client, sid):
    response = await client.get(f"/v1/sessions/{sid}/view")
    assert response.status_code == 200, response.text
    return response.json()


async def action(client, sid, key, **fields):
    response = await client.post(f"/v1/sessions/{sid}/actions",
        json=dict(turn_id=key, client_request_id=key, **fields))
    assert response.status_code == 200 and response.json()["state_changed"], response.text
    return response.json()


async def reach_hold(client, profile, *, runtime=None, boundary="default", zero_fixture=False):
    if boundary == "default":
        entry, request = await admit(client, profile)
    else:
        from tests.unit.test_native_run_entry_api import body as admission_body
        created = await client.post("/v1/player-characters", headers={"Idempotency-Key": "boundary.character"},
            json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
        assert created.status_code == 200, created.text
        request = admission_body(created.json()["player_character_id"]["value"])
        request["profile_ref"]["profile_id"] = profile
        options = (await client.get("/v1/run-entry-options")).json()
        selected = next(p for p in options["profiles"] if p["profile_ref"]["profile_id"] == profile)
        request["overrides"] = [dict(parameter=r["parameter"], value=r[
            "maximum" if (r["parameter"] == "social_trust") == (boundary == "beneficial") else "minimum"])
            for r in selected["override_rules"]]
        response = await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": "boundary.admit"})
        assert response.status_code == 200, response.text
        entry = response.json()
    first = entry["session_id"]
    ending, _ = await play_to_ending(client, first)
    if zero_fixture:
        assert runtime is not None and entry["run_context"]["objectives"]["resource_pressure"] // 50 == 0
        # Explicit resource-only fixture before either immutable world root exists.
        runtime.store._snapshots[first].state["player"]["resources"]["composure"]["current"] = 0
        ending = await view(client, first)
    body = dict(expected_run_state_version=3, expected_session_state_version=ending["metadata"]["state_version"])
    continued = await client.post(f"/v1/sessions/{first}/run-continuation", json=body,
                                  headers={"Idempotency-Key": "journey.continue"})
    assert continued.status_code == 200, continued.text
    second = continued.json()["session_id"]
    q = entry["run_context"]["objectives"]["resource_pressure"] // 50
    if runtime is not None:
        resource = runtime.store._snapshots[second].state["player"]["resources"]["composure"]
        if zero_fixture:
            assert q == 0, "resource-only zero fixture is reserved for public depletion being impossible"
            assert resource["current"] == 0
        elif q:
            from math import ceil
            for index in range(max(0, ceil(resource["current"] / q) - 2)):
                previous = runtime.store.snapshot().snapshots[second].state["player"]["resources"]["composure"]["current"]
                await action(client, second, f"dispatch.deplete.{index}", action_type="CUSTOM", description="静候核验")
                current = runtime.store.snapshot().snapshots[second].state["player"]["resources"]["composure"]["current"]
                assert current == max(0, previous-q)
    await action(client, second, "dispatch.observe", action_type="OBSERVE", description="核对收件台")
    await action(client, second, "dispatch.talk", action_type="TALK", target_ids=["scenario-npc-1"], dialogue="核对排程")
    decision = await view(client, second)
    await action(client, second, "dispatch.hold", action_type="CHOOSE",
        decision_id=decision["narrative_frame"]["decision_id"], choice_id="undelivered_receipt.action.hold")
    held = await view(client, second)
    assert held["ending_status"] == "RESOLVED"
    if runtime is not None and (q or zero_fixture):
        assert runtime.store.snapshot().snapshots[second].state["player"]["resources"]["composure"]["current"] == 0
    return entry, request, ending, continued.json(), body, held


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r01_r02_full_public_three_visit_journey_both_endings_exit_and_fresh_action(profile, choice, *, boundary="default", zero_fixture=False):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        entry, admission, first_end, continued, old_body, held = await reach_hold(client, profile, runtime=runtime, boundary=boundary, zero_fixture=zero_fixture)
        first, second = entry["session_id"], continued["session_id"]
        if boundary == "default" and profile != "difficulty.fragile-alliance":
            assert first_end["ending_status"] == ("RESOLVED" if profile == "difficulty.open-expedition" else "FAILED")
        before = runtime.store.snapshot()
        offered = await client.get(f"/v1/sessions/{second}/run-journey")
        assert offered.status_code == 200, offered.text
        assert offered.json()["next_transition"]["kind"] == "regional_revisit"
        assert runtime.store.snapshot() == before
        body = dict(expected_run_state_version=4, expected_session_state_version=held["metadata"]["state_version"])
        response = await client.post(f"/v1/sessions/{second}/run-revisit", json=body,
                                     headers={"Idempotency-Key": "journey.revisit"})
        assert response.status_code == 200, response.text
        result = response.json()
        third = result["session_id"]
        arrived = runtime.store.snapshot()
        assert arrived.snapshots[third].state["player"] == before.snapshots[second].state["player"]
        assert arrived.player_character_current == before.player_character_current
        assert arrived.run_world_states == before.run_world_states
        for sid in (first, second):
            assert arrived.snapshots[sid] == before.snapshots[sid]
        assert len(arrived.run_world_visit_entries) == 1 and len(arrived.run_world_visits) == 3
        start = await view(client, third)
        assert start["scenario_status"] == "ACTIVE" and not start["public_clocks"]
        await action(client, third, "archive.observe", action_type="OBSERVE", description="查看待核记录")
        expected_player = deepcopy(arrived.snapshots[third].state["player"])
        q = entry["run_context"]["objectives"]["resource_pressure"] // 50
        expected_player["resources"]["composure"]["current"] = max(0, expected_player["resources"]["composure"]["current"] - q)
        assert runtime.store.snapshot().snapshots[third].state["player"] == expected_player
        progressed = await view(client, third)
        assert progressed["metadata"]["state_version"] == 1
        assert not progressed["public_clocks"]
        history_before = runtime.store.snapshot()
        for sid in (third, second, first, second, third):
            journey = await client.get(f"/v1/sessions/{sid}/run-journey")
            assert journey.status_code == 200, journey.text
            assert journey.json()["current"]["session_id"] == third
            assert journey.json()["next_transition"] is None
            await view(client, sid)
        assert runtime.store.snapshot() == history_before
        old_get = await client.get(f"/v1/sessions/{first}/run-continuation")
        assert old_get.status_code == 409 and old_get.json()["error"]["error_code"] == "RUN_CONTINUATION_NOT_AVAILABLE"
        await action(client, third, "archive.choose", action_type="CHOOSE",
            decision_id=progressed["narrative_frame"]["decision_id"], choice_id="receipt_archive.action." + choice)
        expected_player["resources"]["composure"]["current"] = max(0, expected_player["resources"]["composure"]["current"] - q)
        assert runtime.store.snapshot().snapshots[third].state["player"] == expected_player
        ended = await view(client, third)
        assert ended["ending_status"] == ("RESOLVED" if choice == "seal" else "FAILED")
        exited = await client.post(f"/v1/sessions/{third}/run-exit",
            json=dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"]),
            headers={"Idempotency-Key": "journey.exit"})
        assert exited.status_code == 200 and exited.json()["run_state_version"] == 6, exited.text
        fresh = await client.post("/v1/runs/native", json=admission, headers={"Idempotency-Key": "journey.fresh"})
        assert fresh.status_code == 200, fresh.text
        await action(client, fresh.json()["session_id"], "fresh.observe", action_type="OBSERVE", description="查看环境")
        replay = await client.post(f"/v1/sessions/{second}/run-revisit", json=body,
                                  headers={"Idempotency-Key": "journey.revisit"})
        assert replay.status_code == 200 and replay.json() == result, replay.text
        old_replay = await client.post(f"/v1/sessions/{first}/run-continuation", json=old_body,
                                      headers={"Idempotency-Key": "journey.continue"})
        assert old_replay.status_code == 200 and old_replay.json() == continued, old_replay.text
        settled = runtime.store.snapshot()
        original_key = "native.demo" if boundary == "default" else "boundary.admit"
        replay_admission = await client.post("/v1/runs/native", json=admission, headers={"Idempotency-Key":original_key})
        assert replay_admission.status_code == 200 and replay_admission.json() == entry, replay_admission.text
        replay_exit = await client.post(f"/v1/sessions/{third}/run-exit", json=dict(expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"]), headers={"Idempotency-Key":"journey.exit"})
        assert replay_exit.status_code == 200 and replay_exit.json() == exited.json(), replay_exit.text
        assert runtime.store.snapshot() == settled



@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.fragile-alliance", "difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("boundary", ["beneficial", "adverse"])
@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r02_public_objective_boundaries(profile, boundary, choice):
    await test_r01_r02_full_public_three_visit_journey_both_endings_exit_and_fresh_action(profile, choice, boundary=boundary)


@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r02_fragile_default_public_completion(choice):
    await test_r01_r02_full_public_three_visit_journey_both_endings_exit_and_fresh_action("difficulty.fragile-alliance", choice)


@pytest.mark.parametrize("boundary", ["default", "beneficial", "adverse"])
@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r02_resource_only_zero_fixture_not_public_depletion(boundary, choice):
    await test_r01_r02_full_public_three_visit_journey_both_endings_exit_and_fresh_action(
        "difficulty.open-expedition", choice, boundary=boundary, zero_fixture=True)


@pytest.mark.parametrize("choice", ["seal", "defer"])
async def test_r02_fragile_beneficial_resource_only_zero_fixture(choice):
    await test_r01_r02_full_public_three_visit_journey_both_endings_exit_and_fresh_action(
        "difficulty.fragile-alliance", choice, boundary="beneficial", zero_fixture=True)
