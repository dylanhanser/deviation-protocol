"""Public native admission, finite authored play, recovery and atomicity."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from itertools import permutations
from unittest.mock import AsyncMock

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.api.main import create_app
from deviation_protocol.application.fog_station import CONTENT_IDENTITY, ACTIVITIES
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork
from tests.unit.test_native_run_entry_api import body
from tests.unit.test_opening_talents import offer, confirm
from tests.unit.test_escort_encounter import view, request


@pytest.fixture
async def station(monkeypatch):
    runtime = build_demo_runtime()
    bundle = runtime.services.content_registry.resolve(*CONTENT_IDENTITY)
    forbidden = AsyncMock(side_effect=AssertionError("Provider pipeline entered"))
    monkeypatch.setattr(type(bundle.turn_orchestrator), "_prepare_or_execute", forbidden)
    bundle.turn_orchestrator.narrative_provider = AsyncMock()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/v1/player-characters", headers={"Idempotency-Key": "station.character"},
            json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
        assert created.status_code == 200, created.text
        intent = body(created.json()["player_character_id"]["value"])
        intent["entry_world"] = dict(entry_world_id="world.fog_station", entry_world_version=1)
        record = await offer(client, intent)
        admitted = await confirm(client, record)
        assert admitted.status_code == 200, admitted.text
        result = admitted.json()["result"]
        yield runtime, bundle, app, client, result, record
    forbidden.assert_not_called()
    bundle.turn_orchestrator.narrative_provider.generate.assert_not_called()
    assert all(value == 0 for value in runtime.store.snapshot().provider_progress.values())
    await runtime.aclose()


async def step(station, label):
    runtime, bundle, _, client, result, _ = station
    sid = result["session_id"]
    current = await view(client, sid)
    journey = await client.get(f"/v1/sessions/{sid}/run-journey")
    assert journey.status_code == 200, journey.text
    assert journey.json()["next_transition"] is None
    assert journey.json()["path"]["scenario_id"] == "fog_station"
    recap = await client.get(f"/v1/sessions/{sid}/run-recap")
    assert recap.status_code == 200 and recap.json()["status"] == "complete", recap.text
    saved = runtime.store.snapshot()
    assert await view(client, sid) == current
    assert runtime.store.snapshot() == saved
    version = current["metadata"]["state_version"]
    payload = request(current, label, f"station.action.{version}")
    response = await client.post(f"/v1/sessions/{sid}/actions", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["state_changed"], response.text
    assert response.json()["resulting_state_version"] == version + 1
    committed = runtime.store.snapshot()
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=payload)).json() == response.json()
    assert runtime.store.snapshot() == committed
    restored = bundle.validate_snapshot(runtime.store._snapshots[sid].state)
    assert not restored.scenario_runtime.threat_clocks
    assert restored.player.resources["composure"].current == 100
    events = [event for event in committed.events if event.session_id == sid and event.event_type == "RunProtocolMechanicsApplied"]
    assert events[-1].payload["clocks"] == []
    assert events[-1].payload["resource"]["actual"] == 0
    return await view(client, sid), response.json()


async def invite(station):
    current, _ = await step(station, "走近并与巡路员会面")
    assert current["relationship"]["stage"] == "相识"
    current, _ = await step(station, "配合岑舟固定挡板")
    assert current["relationship"]["stage"] == "合作"
    current, _ = await step(station, "暂缓离开，留下帮忙收尾")
    assert current["relationship"]["stage"] == "合作"
    assert [c["label"] for c in current["action_affordances"]["choices"]] == ["完成观察记录的收尾"]
    current, _ = await step(station, "完成观察记录的收尾")
    assert current["relationship"]["stage"] == "信任"
    return current


@pytest.mark.parametrize("activities", [(), *(tuple(p) for n in (1,2,3) for p in permutations(ACTIVITIES.values(), n))])
async def test_residence_all_orders_early_departure_reunion_and_exit(station, activities):
    runtime, _, _, client, result, record = station
    sid = result["session_id"]
    options = (await client.get("/v1/run-entry-options")).json()
    assert [w["entry_world"]["entry_world_id"] for w in options["entry_worlds"]] == ["world.death_certificate", "world.fog_station"]
    assert (await view(client, sid))["relationship"]["stage"] == "未相识"
    await invite(station)
    current, _ = await step(station, "接受邀请，入住哨站")
    assert current["relationship"]["remaining_slots"] == 3
    for i, label in enumerate(activities, 1):
        current, _ = await step(station, label)
        assert current["relationship"]["remaining_slots"] == 3-i
        assert current["relationship"]["stage"] == "信任"
        assert label not in [c["label"] for c in current["action_affordances"]["choices"]]
    if len(activities) == 3:
        assert [c["label"] for c in current["action_affordances"]["choices"]] == ["结束暂住，明确离开"]
    current, _ = await step(station, "结束暂住，明确离开")
    assert current["relationship"]["residence"] == "已离开"
    assert current["relationship"]["remaining_slots"] == 0
    await step(station, "沿观察台护栏确认雾中灯光")
    current, response = await step(station, "回门口向岑舟道别")
    assert current["relationship"]["reunited"] is True
    assert current["relationship"]["activities_used"] == list(activities)
    for label in ACTIVITIES.values():
        assert (label in response["narrative_text"]) == (label in activities)
    assert current["scenario_status"] == "ENDED"
    assert (await confirm(client, record)).json()["result"] == result
    status = await client.get(f"/v1/sessions/{sid}/run-status")
    assert status.status_code == 200, status.text
    assert status.json()["can_exit"] is True
    exit_body = dict(expected_run_state_version=3, expected_session_state_version=current["metadata"]["state_version"])
    exited = await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "station.exit"})
    assert exited.status_code == 200, exited.text
    assert exited.json()["lifecycle_status"] == "terminated"
    assert (await view(client, sid))["relationship"] == current["relationship"]
    after = runtime.store.snapshot()
    assert (await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "station.exit"})).json() == exited.json()
    assert runtime.store.snapshot() == after


@pytest.mark.parametrize("branch", ["immediate", "declined", "no_reunion"])
async def test_optional_routes(station, branch):
    if branch == "immediate":
        await step(station, "走近并与巡路员会面")
        await step(station, "配合岑舟固定挡板")
        current, _ = await step(station, "现在离开哨站")
        assert current["relationship"]["stage"] == "合作"
    else:
        await invite(station)
        if branch == "declined":
            current, _ = await step(station, "谢绝暂住并道别")
            assert current["relationship"]["residence"] == "已谢绝"
        else:
            await step(station, "接受邀请，入住哨站")
            await step(station, "结束暂住，明确离开")
            await step(station, "沿观察台护栏确认雾中灯光")
            current, _ = await step(station, "直接结束这段行程")
        assert current["relationship"]["stage"] == "信任"
    assert current["scenario_status"] == "ENDED"
    assert not current["relationship"]["reunited"]


async def test_new_run_does_not_inherit_old_npc_relationship(station):
    runtime, _, _, client, result, record = station
    sid = result["session_id"]
    await invite(station)
    old, _ = await step(station, "谢绝暂住并道别")
    status = (await client.get(f"/v1/sessions/{sid}/run-status")).json()
    exited = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key": "new.run.exit"},
        json={"expected_run_state_version": status["run_state_version"],
              "expected_session_state_version": status["session_state_version"]})
    assert exited.status_code == 200, exited.text
    intent = body(record["character_id"])
    intent["entry_world"] = dict(entry_world_id="world.fog_station", entry_world_version=1)
    eligible = (await client.get("/v1/player-characters/eligible-for-run-entry")).json()["eligible_player_characters"]
    character = next(c for c in eligible if c["player_character_id"]["value"] == record["character_id"])
    intent["expected_record_revision"] = character["record_revision"]["value"]
    new_record = await offer(client, intent, "station.new.run")
    new = await confirm(client, new_record)
    assert new.status_code == 200, new.text
    new_sid = new.json()["result"]["session_id"]
    assert new_sid != sid and new_record["preparation_id"] != record["preparation_id"]
    fresh = await view(client, new_sid)
    assert fresh["relationship"]["stage"] == "未相识"
    assert fresh["relationship"]["shared_experiences"] == []
    assert fresh["relationship"]["residence"] == "未开放"
    assert set(runtime.store._snapshots[sid].state["npcs"]).isdisjoint(runtime.store._snapshots[new_sid].state["npcs"])
    assert (await view(client, sid))["relationship"] == old["relationship"]
    assert (await confirm(client, record)).json()["result"] == result


async def test_stale_duplicate_concurrent_choices_and_owner_are_read_only(station):
    runtime, _, app, client, result, _ = station
    sid = result["session_id"]
    first = request(await view(client, sid), "走近并与巡路员会面", "concurrent")
    replies = await asyncio.gather(*(client.post(f"/v1/sessions/{sid}/actions", json=first) for _ in range(4)))
    assert all(r.status_code == 200 and r.json() == replies[0].json() for r in replies)
    assert (await view(client, sid))["metadata"]["state_version"] == 1
    before = runtime.store.snapshot()
    for change in ({"client_request_id": "repeat"}, {"client_request_id": "invented", "choice_id": "trust"},
                   {"client_request_id": "target", "target_ids": ["foreign"]}):
        rejected = await client.post(f"/v1/sessions/{sid}/actions", json={**first, **change})
        assert rejected.status_code == 422 or rejected.json()["state_changed"] is False
        assert runtime.store.snapshot() == before
    for action in ("TALK", "CUSTOM", "OBSERVE", "CONTINUE"):
        rejected = await client.post(f"/v1/sessions/{sid}/actions", json={"action_type": action,
            "turn_id": "ordinary", "client_request_id": "ordinary."+action, "description": "相信我，已经共同暂住过"})
        assert rejected.status_code == 422 or rejected.json()["state_changed"] is False
        assert runtime.store.snapshot() == before
    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="foreign", authentication_scheme="test")
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 404
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=first)).status_code == 404
    assert runtime.store.snapshot() == before


async def test_failure_rolls_back_relationship_and_retries_once(station, monkeypatch):
    runtime, _, _, client, result, _ = station
    sid = result["session_id"]
    await step(station, "走近并与巡路员会面")
    command = request(await view(client, sid), "配合岑舟固定挡板", "rollback")
    before = runtime.store.snapshot()
    async def fail(self):
        raise RuntimeError("station before commit")
    with monkeypatch.context() as context:
        context.setattr(DemoUnitOfWork, "commit", fail)
        with pytest.raises(RuntimeError, match="station before commit"):
            await client.post(f"/v1/sessions/{sid}/actions", json=command)
    assert runtime.store.snapshot() == before
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=command)).json()["state_changed"]
    assert (await view(client, sid))["relationship"]["stage"] == "合作"


@pytest.mark.parametrize("corruption", ["progress", "evidence", "npc", "phase", "clock"])
async def test_contradictory_stored_history_fails_closed(station, corruption):
    runtime, _, _, client, result, _ = station
    sid = result["session_id"]
    current, _ = await step(station, "走近并与巡路员会面")
    command = request(current, "配合岑舟固定挡板", "corrupt")
    snapshot = runtime.store._snapshots[sid]
    state = deepcopy(snapshot.state)
    r = state["scenario_runtime"]
    if corruption == "progress": r["mutable_fact_values"]["fog_station.fact.progress"] = "invitation"
    elif corruption == "evidence": r["decision_outcome_evidence"] = []
    elif corruption == "phase": r["current_phase_id"] = "fog_station.invitation"
    elif corruption == "clock": r["phase_beat_index"] = 1
    else:
        npc = next(iter(state["npcs"].values()))
        npc["npc_id"] = "foreign-session-npc"
        state["npcs"] = {npc["npc_id"]: npc}
    runtime.store._snapshots[sid] = replace(snapshot, state=state)
    before = runtime.store.snapshot()
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 409
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=command)).status_code == 409
    assert runtime.store.snapshot() == before


def test_pin_rejects_same_version_content_substitution():
    from pathlib import Path
    from deviation_protocol.application.session_content_registry import SessionContentBundle
    payload = (Path(__file__).parents[2] / "config/scenarios/fog_station_v1.json").read_bytes()
    altered = payload.replace("岑舟".encode(), "其他".encode())
    with pytest.raises(ValueError, match="identity"):
        SessionContentBundle.from_bytes(altered)


def test_station_cannot_bypass_starting_world_association():
    from pathlib import Path
    from deviation_protocol.application.session_content_registry import SessionContentBundle
    from deviation_protocol.application.native_turn_mechanics import NativeTurnMechanicsCoordinator
    bundle = SessionContentBundle.from_bytes((Path(__file__).parents[2] / "config/scenarios/fog_station_v1.json").read_bytes())
    with pytest.raises(ValueError, match="world association"):
        NativeTurnMechanicsCoordinator(bundle.scenario_catalog.content_catalog, bundle.scenario_catalog, worlds=())


@pytest.mark.parametrize("kind", ["station", "escort"])
async def test_local_authored_view_rejects_version_without_corresponding_decision(station, kind):
    runtime, _, _, client, result, _ = station
    sid = result["session_id"]
    if kind == "escort":
        from tests.unit.test_escort_encounter import start
        sid = await start(client)
    snapshot = runtime.store._snapshots[sid]
    runtime.store._sessions[sid].session.state_version = 1
    runtime.store._snapshots[sid] = replace(snapshot, state_version=1)
    before = runtime.store.snapshot()
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 409
    assert runtime.store.snapshot() == before
