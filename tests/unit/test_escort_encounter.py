from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.api.main import create_app
from deviation_protocol.application.escort_encounter import CONTENT_IDENTITY, FACT, EscortEncounterPolicy
from deviation_protocol.application.escort_encounter_services import build_escort_bundle
from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.domain.state import GameState
from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork


@pytest.fixture
async def game(monkeypatch):
    runtime = build_demo_runtime()
    bundle = runtime.services.content_registry.resolve(*CONTENT_IDENTITY)
    provider = AsyncMock()
    bundle.turn_orchestrator.narrative_provider = provider
    forbidden = AsyncMock(side_effect=AssertionError("Provider pipeline entered"))
    monkeypatch.setattr(type(bundle.turn_orchestrator), "_prepare_or_execute", forbidden)
    app = create_app(services=runtime.services)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield runtime, bundle, app, client
    provider.generate.assert_not_called()
    forbidden.assert_not_called()
    assert all(value == 0 for value in runtime.store.snapshot().provider_progress.values())
    await runtime.aclose()


async def start(client, key="new-escort"):
    response = await client.post("/v1/sessions", json={"client_request_id": key,
        "scenario_id": "wind_gate", "character_definition_id": "character.wind_gate.traveler"})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


async def view(client, sid):
    response = await client.get(f"/v1/sessions/{sid}/view")
    assert response.status_code == 200, response.text
    return response.json()


def request(current, label, key):
    affordance = current["action_affordances"]
    choice = next(item for item in affordance["choices"] if item["label"] == label)
    return {"action_type": "CHOOSE", "turn_id": key, "client_request_id": key,
        "decision_id": affordance["decision_id"], "choice_id": choice["choice_id"]}


ROUTES = [
    (["先扶稳同行者", "沿扶手护送到出口", "结伴进入候船室"], ["扶稳", "扶稳", None], "SUCCESS"),
    (["立即带向通道", "停步抓牢扶手，扶稳对方", "结伴进入候船室"], ["失衡", "扶稳", None], "SUCCESS"),
    (["立即带向通道", "继续抢行"], ["失衡", None], "SAFE_WITHDRAWAL"),
    (["一起撤入避风间"], [None], "SAFE_WITHDRAWAL"),
    (["先扶稳同行者", "一起撤入避风间"], ["扶稳", None], "SAFE_WITHDRAWAL"),
    (["立即带向通道", "一起撤入避风间"], ["失衡", None], "SAFE_WITHDRAWAL"),
    (["先扶稳同行者", "沿扶手护送到出口", "一起撤入避风间"], ["扶稳", "扶稳", None], "SAFE_WITHDRAWAL"),
    (["立即带向通道", "停步抓牢扶手，扶稳对方", "一起撤入避风间"], ["失衡", "扶稳", None], "SAFE_WITHDRAWAL"),
]


@pytest.mark.parametrize("labels,conditions,outcome", ROUTES)
async def test_public_routes_snapshot_replay_and_no_provider(game, labels, conditions, outcome):
    runtime, bundle, _, client = game
    catalog = (await client.get("/v1/scenarios")).json()
    story = next(item for item in catalog["scenarios"] if item["scenario_id"] == "wind_gate")
    assert story["entry_mode"] == "SESSION"
    sid = await start(client)
    current = await view(client, sid)
    assert current["encounter"]["condition"] == "慌乱"
    original_player = deepcopy(runtime.store._snapshots[sid].state["player"])
    other = await start(client, "other-session")
    other_snapshot = deepcopy(runtime.store._snapshots[other])
    for index, (label, condition) in enumerate(zip(labels, conditions), 1):
        before = runtime.store.snapshot()
        assert await view(client, sid) == current
        assert runtime.store.snapshot() == before
        body = request(current, label, f"action-{index}")
        response = await client.post(f"/v1/sessions/{sid}/actions", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["state_changed"] is True, response.text
        assert response.json()["resulting_state_version"] == index
        assert response.json()["narrative_text"]
        saved = runtime.store.snapshot()
        replay = await client.post(f"/v1/sessions/{sid}/actions", json=body)
        assert replay.json() == response.json()
        assert runtime.store.snapshot() == saved
        conflict = await client.post(f"/v1/sessions/{sid}/actions", json={**body, "choice_id": "different"})
        assert conflict.status_code == 409
        assert runtime.store.snapshot() == saved
        current = await view(client, sid)
        assert current["encounter"]["condition"] == condition
        payload = runtime.store._snapshots[sid].state
        restored = GameState.from_snapshot(payload, catalog=bundle.scenario_catalog.content_catalog, scenario_catalog=bundle.scenario_catalog)
        bundle.session_service.encounter_policy.validate(restored, sid, bundle.scenario_catalog.scenarios[0])
        assert restored.to_snapshot() == payload
        assert payload["player"] == original_player
        assert runtime.store._snapshots[other] == other_snapshot
    assert current["encounter"]["outcome"] == outcome
    assert current["action_affordances"]["mode"] == "ENDED"
    assert current["ending_status"] == ("RESOLVED" if outcome == "SUCCESS" else "FAILED")
    before = runtime.store.snapshot()
    rejected = await client.post(f"/v1/sessions/{sid}/actions", json={**body, "client_request_id": "after-end"})
    assert rejected.json()["state_changed"] is False
    assert runtime.store.snapshot() == before
    assert not before.run_current and not before.run_participations
    assert all(job.attempt_count == 0 and job.provider_name == "local-server" for job in before.narrative_jobs.values())


async def test_stale_unavailable_wrong_target_and_owner_rejected_without_writes(game):
    runtime, _, app, client = game
    sid = await start(client)
    current = await view(client, sid)
    body = request(current, "先扶稳同行者", "first")
    await client.post(f"/v1/sessions/{sid}/actions", json=body)
    before = runtime.store.snapshot()
    for update in [{"client_request_id": "stale"}, {"choice_id": "unavailable", "client_request_id": "unknown"}, {"target_ids": ["foreign-npc"], "client_request_id": "target"}]:
        response = await client.post(f"/v1/sessions/{sid}/actions", json={**body, **update})
        assert response.status_code == 422 or response.json()["state_changed"] is False
        assert runtime.store.snapshot() == before
    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="stranger", authentication_scheme="test")
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 404
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=body)).status_code == 404
    assert runtime.store.snapshot() == before


@pytest.mark.parametrize("corruption", ["phase", "location", "condition", "missing", "duplicate", "cross-session", "decision"])
async def test_corrupt_state_rejects_reads_and_writes(game, corruption):
    runtime, _, _, client = game
    sid = await start(client)
    body = request(await view(client, sid), "先扶稳同行者", "bad-state")
    snapshot = runtime.store._snapshots[sid]
    payload = deepcopy(snapshot.state)
    r = payload["scenario_runtime"]
    if corruption == "phase": r["current_phase_id"] = "wind_gate.transfer"
    elif corruption == "location": r["current_location_id"] = "wind_gate.midpoint"
    elif corruption == "condition": r["mutable_fact_values"][FACT] = "steady"
    elif corruption == "decision": r["current_decision_id"] = "wind_gate.decision.unsteady"
    elif corruption == "missing": payload["npcs"] = {}
    else:
        npc = deepcopy(next(iter(payload["npcs"].values())))
        npc["npc_id"] = EscortEncounterPolicy.companion_id("other-session")
        if corruption == "cross-session": payload["npcs"] = {}
        payload["npcs"][npc["npc_id"]] = npc
    runtime.store._snapshots[sid] = replace(snapshot, state=payload)
    before = runtime.store.snapshot()
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 409
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=body)).status_code == 409
    assert runtime.store.snapshot() == before


async def test_invisible_companion_policy_and_content_pin(game, tmp_path):
    runtime, bundle, _, client = game
    sid = await start(client)
    definition = bundle.scenario_catalog.scenarios[0]
    state = bundle.validate_snapshot(runtime.store._snapshots[sid].state)
    invisible = definition.model_copy(update={"locations": tuple(item.model_copy(update={"visible_entity_ids": ()}) for item in definition.locations)})
    with pytest.raises(SnapshotInvalidError):
        bundle.session_service.encounter_policy.validate(state, sid, invisible)
    changed = tmp_path / "altered.json"
    pack = Path(__file__).parents[2] / "config/scenarios/wind_gate_v1.json"
    changed.write_bytes(pack.read_bytes().replace("阵风".encode(), "强风".encode()))
    with pytest.raises(ValueError, match="identity"):
        build_escort_bundle(changed, uow_factory=runtime.store.unit_of_work)


async def test_failure_before_commit_rolls_back_everything(game, monkeypatch):
    runtime, _, _, client = game
    sid = await start(client)
    body = request(await view(client, sid), "先扶稳同行者", "atomic")
    before = runtime.store.snapshot()
    async def fail(self):
        raise RuntimeError("injected-before-commit")
    with monkeypatch.context() as context:
        context.setattr(DemoUnitOfWork, "commit", fail)
        with pytest.raises(RuntimeError, match="injected-before-commit"):
            await client.post(f"/v1/sessions/{sid}/actions", json=body)
    assert runtime.store.snapshot() == before
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=body)).json()["state_changed"] is True


async def test_current_choice_contract_cross_session_token_and_create_replay(game):
    runtime, _, _, client = game
    sid = await start(client)
    before = runtime.store.snapshot()
    assert await start(client) == sid
    assert runtime.store.snapshot() == before
    other = await start(client, "another")
    current = await view(client, sid)
    body = request(current, "先扶稳同行者", "unavailable")
    foreign = await view(client, other)
    for update in [
        {"choice_id": "wind_gate.choice.door_success"},
        {"decision_id": foreign["action_affordances"]["decision_id"]},
    ]:
        before = runtime.store.snapshot()
        response = await client.post(f"/v1/sessions/{sid}/actions", json={**body, **update})
        assert response.status_code == 200
        assert response.json()["resolution_kind"] == "REJECTED_LOCAL"
        assert runtime.store.snapshot() == before
    before = runtime.store.snapshot()
    response = await client.post(f"/v1/sessions/{sid}/actions", json={
        "action_type": "CUSTOM", "description": "自行决定同行者状态", "turn_id": "free", "client_request_id": "free"})
    assert response.json()["resolution_kind"] == "REJECTED_LOCAL"
    assert runtime.store.snapshot() == before
    from deviation_protocol.application.errors import InvalidScenarioDefinitionError
    with pytest.raises(InvalidScenarioDefinitionError):
        runtime.services.session_service.resolve_run_entry_definition("wind_gate")
