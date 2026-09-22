"""Public same-Run patrol continuation, evidence, recovery and atomicity."""
from copy import deepcopy
import asyncio

import pytest

from tests.unit.test_fog_station import station, step, invite
from tests.unit.test_escort_encounter import view, request


async def original_admission_replay_lifecycle(client, app, intent, entry_kind, scope,
        read_state, *, rebuild=None, invalid_association=None):
    """Exercise the same public replay contract against Demo and real SQL stores."""
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    from deviation_protocol.domain.run import RunId
    from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1
    from deviation_protocol.domain.fog_patrol import FogContinuedV1, FogTerminatedV1
    from tests.unit.test_opening_talents import offer, confirm

    if entry_kind == "talent":
        preparation = await offer(client, intent, "r1.prepare")
        async def replay(changed=False):
            selected = [c["id"] for c in preparation["candidates"][2:4]] if changed else None
            return await confirm(client, preparation, selected)
    else:
        async def replay(changed=False):
            proposed = deepcopy(intent)
            if changed:
                proposed["entry_world"] = {"entry_world_id": "world.death_certificate", "entry_world_version": 1}
            return await client.post("/v1/runs/native", json=proposed,
                headers={"Idempotency-Key": "r1.native"})
    original = await replay()
    assert original.status_code == 200, original.text
    admitted = original.json()["result"] if entry_kind == "talent" else original.json()
    source = admitted["session_id"]
    run_id = admitted["run_context"]["run_id"]
    scope.session_ids.add(source)
    scope.run_ids.add(run_id)

    async def checkpoint(family_type):
        if rebuild is not None:
            app.state.api_services = rebuild()
        before = await read_state()
        service = app.state.api_services.native_run_admission_service
        async with service.uow_factory() as uow:
            family = await uow.run_protocol_bindings.get_classified_for_update(run_id=RunId(value=run_id))
            assert type(family) is family_type
            historical = family if family_type is NativeRunAdmissionV1 else family.admission
            assert historical.canonical_run.trusted_participation_references[0].session_id == source
        response = await replay()
        # Includes the complete original frozen selection, content and Run/Session
        # projection, not a response constructed from the current patrol Session.
        assert response.status_code == 200 and response.content == original.content, response.text
        assert await read_state() == before
        changed = await replay(changed=True)
        assert changed.status_code == 409
        assert changed.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
        assert await read_state() == before
        overrides = dict(app.dependency_overrides)
        try:
            app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(
                player_id="r1.foreign", authentication_scheme="demo-dev-only")
            assert (await replay()).status_code == 404
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(overrides)
        assert await read_state() == before
        if invalid_association is not None and family_type is not NativeRunAdmissionV1:
            await invalid_association(replay)
            assert await read_state() == before
        print(f"R1 {entry_kind}: {family_type.__name__}: exact original 200; state/counts unchanged")

    await checkpoint(NativeRunAdmissionV1)
    for i, label in enumerate(("走近并与巡路员会面", "配合岑舟固定挡板", "现在离开哨站")):
        response = await client.post(f"/v1/sessions/{source}/actions",
            json=request(await view(client, source), label, f"r1.source.{i}"))
        assert response.status_code == 200 and response.json()["state_changed"], response.text
    continued = await client.post(f"/v1/sessions/{source}/run-continuation",
        json={"expected_run_state_version": 3, "expected_session_state_version": 3},
        headers={"Idempotency-Key": "r1.continue"})
    assert continued.status_code == 200, continued.text
    sid = continued.json()["session_id"]
    scope.session_ids.add(sid)
    assert sid != source and continued.json()["run_id"] == run_id
    await checkpoint(FogContinuedV1)
    for i, label in enumerate(("走近岑舟，打个招呼", "沿背风小径安全绕行", "向岑舟道别，继续走远")):
        response = await client.post(f"/v1/sessions/{sid}/actions",
            json=request(await view(client, sid), label, f"r1.patrol.{i}"))
        assert response.status_code == 200 and response.json()["state_changed"], response.text
    exited = await client.post(f"/v1/sessions/{sid}/run-exit",
        json={"expected_run_state_version": 4, "expected_session_state_version": 3},
        headers={"Idempotency-Key": "r1.exit"})
    assert exited.status_code == 200 and exited.json()["lifecycle_status"] == "terminated", exited.text
    eligible = (await client.get("/v1/player-characters/eligible-for-run-entry")).json()
    assert any(c["player_character_id"]["value"] == intent["player_character_id"]
        for c in eligible["eligible_player_characters"])
    await checkpoint(FogTerminatedV1)


@pytest.mark.parametrize("entry_kind", ["talent", "native"])
async def test_original_admission_replay_across_fog_lifecycle(station, entry_kind):
    from types import SimpleNamespace
    from tests.unit.test_native_run_entry_api import body
    runtime, _, app, client, _, _ = station
    created = await client.post("/v1/player-characters", headers={"Idempotency-Key": "r1.character"},
        json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
    assert created.status_code == 200, created.text
    intent = body(created.json()["player_character_id"]["value"])
    intent["entry_world"] = {"entry_world_id": "world.fog_station", "entry_world_version": 1}
    async def read_state():
        return runtime.store.snapshot()
    async def invalid_association(replay):
        # Keep the original receipt, but remove its required continuation entry.
        # Both public replay routes must still run the authoritative classifier.
        key, entry = next(iter(runtime.store._run_world_visit_entries.items()))
        del runtime.store._run_world_visit_entries[key]
        try:
            before = runtime.store.snapshot()
            response = await replay()
            assert response.status_code == 409, response.text
            assert response.json()["error"]["error_code"] == "SNAPSHOT_INVALID"
            assert runtime.store.snapshot() == before
        finally:
            runtime.store._run_world_visit_entries[key] = entry
    await original_admission_replay_lifecycle(client, app, intent, entry_kind,
        SimpleNamespace(session_ids=set(), run_ids=set()), read_state,
        invalid_association=invalid_association)


async def ending(station, branch="immediate", activities=()):
    if branch == "immediate":
        await step(station, "走近并与巡路员会面")
        await step(station, "配合岑舟固定挡板")
        await step(station, "现在离开哨站")
    else:
        await invite(station)
        if branch == "declined":
            await step(station, "谢绝暂住并道别")
        else:
            await step(station, "接受邀请，入住哨站")
            for label in activities:
                await step(station, label)
            await step(station, "结束暂住，明确离开")
            await step(station, "沿观察台护栏确认雾中灯光")
            await step(station, "回门口向岑舟道别" if branch == "reunited" else "直接结束这段行程")


async def continue_visit(station, key="patrol.continue"):
    runtime, _, _, client, admitted, _ = station
    sid = admitted["session_id"]
    before = runtime.store.snapshot()
    journey = await client.get(f"/v1/sessions/{sid}/run-journey")
    assert journey.status_code == 200, journey.text
    assert journey.json()["next_transition"]["kind"] == "fog_patrol"
    assert journey.json()["run_state_version"] == 3
    assert runtime.store.snapshot() == before
    current = await view(client, sid)
    body = dict(expected_run_state_version=3, expected_session_state_version=current["metadata"]["state_version"])
    response = await client.post(f"/v1/sessions/{sid}/run-continuation", json=body, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return response.json(), body


@pytest.mark.parametrize("branch,activities", [
    ("immediate", ()), ("declined", ()), ("finished", ()),
    ("reunited", ("复盘脱险",)),
    ("reunited", ("听一段已公开的巡路往事", "一起整理观察记录", "复盘脱险")),
])
@pytest.mark.parametrize("helping", [True, False])
async def test_public_reunion_recovery_and_explicit_exit(station, branch, activities, helping):
    runtime, _, _, client, admitted, preparation = station
    source_id = admitted["session_id"]
    await ending(station, branch, activities)
    original = deepcopy(runtime.store._snapshots[source_id].state)
    source_ending_title = (await view(client, source_id))["presentation"]["ending"]["title"]
    frozen_talents = deepcopy(runtime.store.snapshot().opening_preparations)
    result, body = await continue_visit(station)
    sid = result["session_id"]
    assert sid != source_id and result["visit"]["world_id"] == "world.fog_station"
    assert result["visit"]["visit_ordinal"] == 2
    initial = deepcopy(runtime.store._snapshots[sid].state)
    assert initial["player"] == original["player"]
    assert set(initial["npcs"]).isdisjoint(original["npcs"])
    assert initial["player_memory"] != original["player_memory"]
    assert len(runtime.store.snapshot().run_world_states) == 1
    for label in ("走近岑舟，打个招呼", "在护栏内拉稳绳索，协助拆灯" if helping else "沿背风小径安全绕行",
                  "向岑舟道别，离开风口" if helping else "向岑舟道别，继续走远"):
        before = runtime.store.snapshot()
        current = await view(client, sid)
        assert current.get("relationship") is None
        journey = await client.get(f"/v1/sessions/{sid}/run-journey")
        assert journey.status_code == 200, journey.text
        assert journey.json()["predecessor"]["session_id"] == source_id
        assert journey.json()["arrival"]["previous_ending_title"] == source_ending_title
        assert journey.json()["next_transition"] is None
        assert (await client.get(f"/v1/sessions/{sid}/run-recap")).json()["status"] == "complete"
        assert await view(client, sid) == current
        assert runtime.store.snapshot() == before
        payload = request(current, label, "patrol.action." + str(current["metadata"]["state_version"]))
        response = await client.post(f"/v1/sessions/{sid}/actions", json=payload)
        assert response.status_code == 200 and response.json()["state_changed"], response.text
        if label == "走近岑舟，打个招呼":
            text = response.json()["narrative_text"]
            assert "上次访问的回响" in text
            assert ("短暂的合作" in text) == (branch == "immediate")
            assert ("谢绝了暂住" in text) == (branch == "declined")
            assert ("没有一起做过暂住活动" in text) == (branch in ("finished", "reunited") and not activities)
            if activities:
                expected = {"复盘脱险":"复盘脱险的那一刻", "听一段已公开的巡路往事":"讲过的那段巡路往事", "一起整理观察记录":"一起整理观察记录的情景"}[activities[0]]
                assert expected in text
        after = runtime.store.snapshot()
        assert (await client.post(f"/v1/sessions/{sid}/actions", json=payload)).json() == response.json()
        assert runtime.store.snapshot() == after
    ended = await view(client, sid)
    assert ended["scenario_status"] == "ENDED"
    assert "暂时没有可继续的内容" in ended["presentation"]["ending"]["summary"]
    if not helping:
        assert "协助拆灯" not in "".join(ended["recent_narrative_texts"])
    before = runtime.store.snapshot()
    replay = await client.post(f"/v1/sessions/{source_id}/run-continuation", json=body, headers={"Idempotency-Key": "patrol.continue"})
    assert replay.status_code == 200 and replay.json() == result, replay.text
    assert runtime.store.snapshot() == before
    status = (await client.get(f"/v1/sessions/{sid}/run-status")).json()
    assert status["lifecycle_status"] == "active" and status["can_exit"] is True
    exit_body = dict(expected_run_state_version=4, expected_session_state_version=3)
    no_third = await client.post(f"/v1/sessions/{sid}/run-continuation", json=exit_body,
        headers={"Idempotency-Key": "no.third.visit"})
    assert no_third.status_code == 409, no_third.text
    assert runtime.store.snapshot() == before
    exited = await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body, headers={"Idempotency-Key": "patrol.exit"})
    assert exited.status_code == 200 and exited.json()["lifecycle_status"] == "terminated", exited.text
    terminal = runtime.store.snapshot()
    assert (await client.post(f"/v1/sessions/{source_id}/run-continuation", json=body,
        headers={"Idempotency-Key": "patrol.continue"})).json() == result
    assert (await client.post(f"/v1/sessions/{sid}/run-exit", json=exit_body,
        headers={"Idempotency-Key": "patrol.exit"})).json() == exited.json()
    assert runtime.store.snapshot() == terminal
    eligible = (await client.get("/v1/player-characters/eligible-for-run-entry")).json()["eligible_player_characters"]
    assert any(row["player_character_id"]["value"] == preparation["character_id"] for row in eligible)
    assert (await view(client, sid))["scenario_status"] == "ENDED"
    assert runtime.store._snapshots[source_id].state == original
    assert runtime.store._snapshots[sid].state["player"] == original["player"]
    assert runtime.store.snapshot().opening_preparations == frozen_talents
    for event in runtime.store.snapshot().events:
        if event.session_id == sid and event.event_type == "RunProtocolMechanicsApplied":
            assert event.payload["clocks"] == [] and event.payload["resource"]["actual"] == 0


@pytest.mark.parametrize("fault", ["missing_event", "event_session", "event_choice", "event_type", "npc", "content", "ending"])
async def test_source_evidence_fails_closed_without_writes(station, fault):
    runtime, _, _, client, result, _ = station
    await ending(station)
    sid = result["session_id"]
    if fault.startswith("event") or fault == "missing_event":
        events = runtime.store._events
        index = next(i for i,e in enumerate(events) if e.session_id == sid and e.event_type == "ScenarioDecisionSelected")
        if fault == "missing_event":
            del events[index]
        else:
            from dataclasses import replace
            event = events[index]
            events[index] = replace(event, **({"session_id": "wrong.session"} if fault == "event_session" else {
                "payload": {**event.payload, "selected_action_id" if fault == "event_choice" else "scenario_event_type": "invented"}}))
    else:
        snapshot = runtime.store._snapshots[sid].state
        if fault == "npc":
            next(iter(snapshot["npcs"].values()))["definition_id"] = "npc.wrong.cen_zhou"
        elif fault == "content":
            snapshot["content_version"] = "fog-station-9.0.0"
        else:
            snapshot["scenario_runtime"]["ending_id"] = "fog_station.ending.reunited"
    before = runtime.store.snapshot()
    for method, path, kwargs in (("get", "run-journey", {}), ("post", "run-continuation", {
            "json": {"expected_run_state_version":3,"expected_session_state_version":3},
            "headers":{"Idempotency-Key":"invalid.evidence"}})):
        response = await getattr(client, method)(f"/v1/sessions/{sid}/{path}", **kwargs)
        assert response.status_code == 409 and response.json()["error"]["error_code"] == "SNAPSHOT_INVALID", response.text
        assert runtime.store.snapshot() == before


@pytest.mark.parametrize("race", ["duplicate", "competing", "exit"])
async def test_continuation_serializes_once_and_never_resurrects(station, race):
    runtime, _, _, client, result, _ = station
    await ending(station)
    sid = result["session_id"]
    body = {"expected_run_state_version":3,"expected_session_state_version":3}
    async def post(path, key):
        return await client.post(f"/v1/sessions/{sid}/{path}", json=body, headers={"Idempotency-Key":key})
    replies = await asyncio.gather(post("run-continuation","race.1"),
        post("run-exit" if race == "exit" else "run-continuation", "race.1" if race == "duplicate" else "race.2"))
    assert sorted(r.status_code for r in replies) == ([200,200] if race == "duplicate" else [200,409]), [r.text for r in replies]
    if race == "duplicate":
        assert replies[0].json() == replies[1].json()
    assert len(runtime.store.snapshot().run_world_visits) in (0,2)
    before = runtime.store.snapshot()
    rejected = await post("run-continuation", "race.extra")
    assert rejected.status_code == 409
    assert runtime.store.snapshot() == before


async def test_rollback_after_staged_family_and_wrong_owner(station, monkeypatch):
    from deviation_protocol.infrastructure.demo_persistence import DemoRunWorldContinuationRepository
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    runtime, _, app, client, result, _ = station
    await ending(station)
    sid = result["session_id"]
    body = {"expected_run_state_version":3,"expected_session_state_version":3}
    before = runtime.store.snapshot()
    original = DemoRunWorldContinuationRepository.add
    async def fail(self, family):
        await original(self, family)
        raise RuntimeError("patrol staged rollback")
    with monkeypatch.context() as patch:
        patch.setattr(DemoRunWorldContinuationRepository, "add", fail)
        with pytest.raises(RuntimeError, match="patrol staged rollback"):
            await client.post(f"/v1/sessions/{sid}/run-continuation", json=body, headers={"Idempotency-Key":"rollback"})
    assert runtime.store.snapshot() == before
    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="foreign", authentication_scheme="test")
    assert (await client.post(f"/v1/sessions/{sid}/run-continuation", json=body, headers={"Idempotency-Key":"other.owner"})).status_code == 404
    assert runtime.store.snapshot() == before
    app.dependency_overrides.clear()
    await continue_visit(station, "rollback")


async def test_sealed_associations_fail_closed_and_old_recap_keeps_cutoff(station):
    import hashlib
    import json
    from types import SimpleNamespace
    runtime, _, _, client, admitted, _ = station
    await ending(station)
    source = admitted["session_id"]
    old_recap = (await client.get(f"/v1/sessions/{source}/run-recap")).json()
    result, body = await continue_visit(station)
    sid = result["session_id"]
    assert (await client.get(f"/v1/sessions/{source}/run-recap")).json()["text"] == old_recap["text"]
    key, original = next(iter(runtime.store._run_world_visit_entries.items()))
    for field, value in (("run_id", "other.run"), ("source_session_id", "other.session"),
            ("scenario_content_version", "fog-patrol-9.0.0"), ("content_sha256", "0" * 64),
            ("logical_npc", "authored-person.someone-else/v1"), ("source_npc", "npc.wrong"),
            ("destination_npc", "npc.wrong")):
        payload = json.loads(original.entry_canonical)
        payload[field] = value
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        runtime.store._run_world_visit_entries[key] = SimpleNamespace(**{**vars(original),
            "entry_canonical": raw, "entry_sha256": hashlib.sha256(raw).digest()})
        before = runtime.store.snapshot()
        for path in ("view", "run-journey"):
            response = await client.get(f"/v1/sessions/{sid}/{path}")
            assert response.status_code == 409, response.text
            assert response.json()["error"]["error_code"] == "SNAPSHOT_INVALID"
        replay = await client.post(f"/v1/sessions/{source}/run-continuation", json=body,
            headers={"Idempotency-Key": "patrol.continue"})
        assert replay.status_code == 409, replay.text
        assert runtime.store.snapshot() == before
        runtime.store._run_world_visit_entries[key] = original
    assert (await client.get(f"/v1/sessions/{sid}/run-journey")).status_code == 200


async def test_terminated_source_and_second_visit_have_no_third_transition(station):
    runtime, _, _, client, admitted, _ = station
    await ending(station)
    sid = admitted["session_id"]
    body = {"expected_run_state_version": 3, "expected_session_state_version": 3}
    response = await client.post(f"/v1/sessions/{sid}/run-exit", json=body, headers={"Idempotency-Key": "exit.first"})
    assert response.status_code == 200, response.text
    before = runtime.store.snapshot()
    assert (await client.get(f"/v1/sessions/{sid}/run-journey")).json()["next_transition"] is None
    response = await client.post(f"/v1/sessions/{sid}/run-continuation", json=body, headers={"Idempotency-Key": "too.late"})
    assert response.status_code == 409
    assert runtime.store.snapshot() == before


def test_patrol_pack_is_exact_version_and_cannot_substitute_bytes():
    from pathlib import Path
    from deviation_protocol.application.session_content_registry import SessionContentBundle
    raw = (Path(__file__).parents[2] / "config/scenarios/fog_patrol_v1.json").read_bytes()
    bundle = SessionContentBundle.from_bytes(raw)
    assert not bundle.standalone
    for changed in (raw + b" ", raw.replace(b"fog-patrol-1.0.0", b"fog-patrol-1.0.1")):
        with pytest.raises(ValueError, match="patrol content identity mismatch"):
            SessionContentBundle.from_bytes(changed)
