import asyncio
from dataclasses import replace
from copy import deepcopy

import httpx
import pytest

from deviation_protocol.api.main import create_app
from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.domain.opening_talents import load_catalog, roll_candidates, validate_selection, OpeningTalentClockPolicy, CATALOG_VERSION
from tests.unit.test_native_run_entry_api import body


def test_catalog_and_deterministic_active_pool():
    entries = load_catalog()
    assert len(entries) == len({e.id for e in entries}) == len({e.name for e in entries}) == 100
    assert [sum(e.tier == t for e in entries) for t in ("TOP", "TRADEOFF", "ORDINARY", "WEAK")] == [5, 20, 35, 40]
    assert sum(e.status == "CURRENT" for e in entries) == 12
    active = {e.id for e in entries if e.status == "CURRENT"}
    rolls = [roll_candidates(f"{i:064x}") for i in range(100)]
    assert len(set(rolls)) > 1
    for i, roll in enumerate(rolls):
        assert roll == roll_candidates(f"{i:064x}")
        assert len(set(roll)) == 5 and set(roll) <= active
        assert len(set(roll) & {f"T{i:03}" for i in range(1, 6)}) <= 1


@pytest.mark.parametrize("selections", [(), ("T001",), ("T001", "T001"), ("T001", "T026", "T027"), ("T002", "T026"), ("T061", "T026")])
def test_invalid_selection(selections):
    with pytest.raises(ValueError):
        validate_selection(("T001", "T006", "T026", "T027", "T028"), selections)


@pytest.mark.parametrize("identity,expected", [
    ("T001", (0, 0, -1, -1)), ("T006", (0, -1, 1, 0)),
    ("T007", (-1, 1, 0, 0)), ("T008", (1, 0, 0, -1)),
    ("T026", (0, -1, 0, 0)), ("T027", (-1, 0, 0, 0)),
    ("T028", (0, 0, -1, 0)), ("T029", (0, 0, 0, -1)),
    ("T061", (0, 1, 0, 0)), ("T062", (1, 0, 0, 0)),
    ("T063", (0, 0, 1, 0)), ("T064", (0, 0, 0, 1)),
])
def test_all_approved_effects(identity, expected):
    policy = OpeningTalentClockPolicy()
    for action, modifier in zip(("OBSERVE", "TALK", "EXPLORE", "CUSTOM"), expected, strict=True):
        neutral = next(t for t, affected in (("T026", "TALK"), ("T027", "OBSERVE"), ("T028", "EXPLORE"))
            if affected != action and t != identity)
        assert policy.modifier(CATALOG_VERSION, (identity, neutral), action) == modifier


def test_composition_floor_and_explicit_legacy():
    policy = OpeningTalentClockPolicy()
    assert policy.modifier(None, (), "TALK") == 0
    assert policy.modifier(CATALOG_VERSION, ("T006", "T026"), "TALK") == -2
    assert policy.modifier(CATALOG_VERSION, ("T006", "T063"), "EXPLORE") == 2
    assert 1 + policy.additional(1, -2) == 1
    assert 1 + policy.additional(0, 2) == 3
    with pytest.raises(ValueError):
        policy.modifier(CATALOG_VERSION, ("T002", "T026"), "TALK")


@pytest.mark.parametrize("selected,delta", [(("T007", "T027"), -2), (("T008", "T062"), 2)])
def test_effect_changes_only_additional_clock_in_real_mechanics(selected, delta):
    from tests.unit.test_native_turn_mechanics import fixture_inputs
    f = fixture_inputs(quiet=True)
    bound = fixture_inputs(quiet=True, opening_talents={"catalog_version": CATALOG_VERSION, "selected_ids": list(selected)})
    result = bound.coordinator.decide(bound.inputs, bound.state, bound.definition, bound.submission, selected=bound.selected)
    assert result.resource == f.decision.resource
    assert bound.state.to_snapshot() == f.state.to_snapshot()
    assert result.selected_rule == f.decision.selected_rule and result.selected_result == f.decision.selected_result
    assert result.clocks
    for original, changed in zip(f.decision.clocks, result.clocks, strict=True):
        assert original.base == changed.base
        assert changed.amount == original.base + max(0, original.amount - original.base + delta)
        assert changed.amount >= original.base


async def test_public_action_replay_with_confirmed_talents(opening):
    runtime, client, request = opening
    record = await offer(client, request)
    response = await confirm(client, record)
    assert response.status_code == 200, response.text
    sid = response.json()["result"]["session_id"]
    action = {"turn_id": "opening.observe", "client_request_id": "opening.observe", "action_type": "OBSERVE", "description": "查看环境"}
    result = await client.post(f"/v1/sessions/{sid}/actions", json=action)
    assert result.status_code == 200, result.text
    assert result.json()["state_changed"]
    before = runtime.store.snapshot()
    assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == result.json()
    assert runtime.store.snapshot() == before
    assert (await client.get(f"/v1/sessions/{sid}/view")).json()["metadata"]["state_version"] == 1


async def test_missing_confirmed_binding_cannot_become_legacy(opening):
    runtime, client, request = opening
    record = await offer(client, request)
    response = await confirm(client, record)
    sid = response.json()["result"]["session_id"]
    stored = runtime.store._opening_preparations.pop(record["preparation_id"])
    try:
        from deviation_protocol.application.native_run_admission import NativeRunAdmissionIntegrityError
        with pytest.raises(NativeRunAdmissionIntegrityError, match="missing confirmed"):
            await client.get(f"/v1/sessions/{sid}/opening-talents")
        with pytest.raises(NativeRunAdmissionIntegrityError, match="missing confirmed"):
            await client.post(f"/v1/sessions/{sid}/actions", json={"action_type":"OBSERVE", "description":"查看环境",
                "turn_id":"missing.talent", "client_request_id":"missing.talent"})
    finally:
        runtime.store._opening_preparations[record["preparation_id"]] = stored


async def test_openapi_declares_new_transport_and_no_private_metadata(opening):
    _, client, _ = opening
    schema = (await client.get("/openapi.json")).json()
    for path in ("/v1/opening-preparations", "/v1/opening-preparations/{preparation_id}/confirm"):
        post = schema["paths"][path]["post"]
        assert post["requestBody"]["required"]
        assert any(p["name"] == "Idempotency-Key" and p["required"] for p in post["parameters"])
    assert set(schema["components"]["schemas"]["TalentCard"]["properties"]) == {"id", "name", "tier", "description"}


@pytest.mark.parametrize("kind", ["profile", "world", "duplicate", "query", "oversize"])
async def test_invalid_preparation_transport_and_catalog_leave_no_offer(opening, kind):
    import json
    runtime, client, request = opening
    if kind == "profile": request["profile_ref"]["profile_id"] = "difficulty.unknown"
    if kind == "world": request["entry_world"]["entry_world_id"] = "world.unknown"
    raw = json.dumps(request)
    if kind == "duplicate": raw = '{"overrides":[],' + raw[1:]
    if kind == "oversize": raw += " " * 4097
    response = await client.post("/v1/opening-preparations" + ("?hidden=1" if kind == "query" else ""),
        content=raw, headers={"Content-Type":"application/json","Idempotency-Key":"invalid.prepare"})
    assert response.status_code == 422, response.text
    assert not runtime.store._opening_preparations and not runtime.store._sessions


async def test_old_admission_cannot_bypass_pending_choices_or_claim_confirmation_key(opening):
    runtime, client, request = opening
    record = await offer(client, request)
    for key in ("old.direct.entry", "opening." + record["preparation_id"]):
        response = await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key":key})
        assert response.status_code == 409, response.text
        assert not runtime.store._sessions
        assert (await client.get(f'/v1/player-characters/{record["character_id"]}/opening-preparation')).json() == record
    assert (await confirm(client, record)).status_code == 200


async def test_legacy_pending_rejection_is_atomic_and_confirmation_still_usable(opening):
    runtime, client, request = opening
    record = await offer(client, request)
    before = runtime.store.snapshot()
    response = await client.post("/v1/runs", headers={"Idempotency-Key":"legacy.pending"}, json={
        "player_character_id":record["character_id"], "expected_record_revision":request["expected_record_revision"],
        "scenario_id":"death_certificate"})
    assert response.status_code == 409
    assert response.json()["error"]["error_code"] == "PLAYER_CHARACTER_NOT_ELIGIBLE"
    assert runtime.store.snapshot() == before
    assert (await confirm(client, record)).status_code == 200


async def test_legacy_exact_replay_precedes_later_pending_guard(opening, monkeypatch):
    runtime, client, request = opening
    body = {"player_character_id":request["player_character_id"],
        "expected_record_revision":request["expected_record_revision"], "scenario_id":"death_certificate"}
    headers = {"Idempotency-Key":"legacy.original"}
    first = await client.post("/v1/runs", headers=headers, json=body)
    assert first.status_code == 200, first.text
    before = runtime.store.snapshot()
    # A replay must not consult *any* current admission gate, even a later pending offer.
    from deviation_protocol.infrastructure.opening_preparation_persistence import DemoOpeningPreparationRepository
    async def forbidden(*args, **kwargs):
        raise AssertionError("historical replay consulted current preparation")
    monkeypatch.setattr(DemoOpeningPreparationRepository, "latest", forbidden)
    assert (await client.post("/v1/runs", headers=headers, json=body)).json() == first.json()
    assert runtime.store.snapshot() == before


async def test_new_run_after_exit_keeps_old_confirmed_talents_and_request_replay(opening):
    _, client, request = opening
    request["profile_ref"]["profile_id"] = "difficulty.open-expedition"
    record = await offer(client, request)
    committed = (await confirm(client, record)).json()
    sid = committed["result"]["session_id"]
    from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS
    for index, step in enumerate(CANONICAL_ACTIONS):
        view = (await client.get(f"/v1/sessions/{sid}/view")).json()
        if view["scenario_status"] == "ENDED":
            break
        action = {"turn_id": f"opening.end.{index}", "client_request_id": f"opening.end.{index}", "action_type": step.action_type}
        if step.choice_id:
            action.update(choice_id=step.choice_id, decision_id=view["narrative_frame"]["decision_id"])
        if step.description:
            action["description"] = step.description
        response = await client.post(f"/v1/sessions/{sid}/actions", json=action)
        assert response.status_code == 200, response.text
    status = (await client.get(f"/v1/sessions/{sid}/run-status")).json()
    assert status["can_exit"], status
    exited = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"opening.exit"},
        json={"expected_run_state_version":status["run_state_version"], "expected_session_state_version":status["session_state_version"]})
    assert exited.status_code == 200, exited.text
    eligible = (await client.get("/v1/player-characters/eligible-for-run-entry")).json()["eligible_player_characters"]
    current = next(c for c in eligible if c["player_character_id"]["value"] == record["character_id"])
    request["expected_record_revision"] = current["record_revision"]["value"]
    fresh = await offer(client, request, "opening.next.run")
    assert fresh["preparation_id"] != record["preparation_id"] and fresh["state"] == "PENDING"
    assert (await confirm(client, record)).json() == committed
    assert await offer(client, request, "opening.prepare") == committed
    old_cards = (await client.get(f"/v1/sessions/{sid}/opening-talents")).json()
    assert {t["id"] for t in old_cards} == set(committed["selected_ids"])


async def test_ownership_and_stale_character_reject_without_consuming(opening):
    runtime, client, request = opening
    record = await offer(client, request)
    from deviation_protocol.application.opening_preparation import OpeningPreparationService, PreparationRejected, decode_command
    from deviation_protocol.application.identity import RequestPrincipal
    service = OpeningPreparationService(runtime.services.native_run_admission_service)
    with pytest.raises(PreparationRejected, match="PLAYER_CHARACTER_NOT_FOUND"):
        await service.confirm(RequestPrincipal(player_id="other.player", authentication_scheme="demo"), record["preparation_id"], record["character_id"],
            record["catalog_version"], tuple(t["id"] for t in record["candidates"][:2]))
    # Frozen preparation cannot silently adopt a changed character revision.
    from deviation_protocol.infrastructure.opening_preparation_persistence import decode, encode
    from deviation_protocol.application.opening_preparation import encode_command
    from deviation_protocol.domain.player_character import PlayerCharacterRevision
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionCommand
    original = runtime.store._opening_preparations[record["preparation_id"]]
    stored = decode(original)
    command = decode_command(stored.command_json)
    stale = NativeRunAdmissionCommand(**{**{name:getattr(command,name) for name in type(command).model_fields},
        "expected_record_revision":PlayerCharacterRevision(value=command.expected_record_revision.value+1)})
    runtime.store._opening_preparations[record["preparation_id"]] = encode(replace(stored,command_json=encode_command(stale)))
    response = await confirm(client, record)
    assert response.status_code == 409 and response.json()["error"]["error_code"] == "PLAYER_CHARACTER_STALE"
    assert not runtime.store._sessions
    runtime.store._opening_preparations[record["preparation_id"]] = original


@pytest.fixture
async def opening():
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        created = await client.post("/v1/player-characters", headers={"Idempotency-Key": "opening.character"},
            json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
        assert created.status_code == 200, created.text
        request = body(created.json()["player_character_id"]["value"])
        yield runtime, client, request


async def offer(client, request, key="opening.prepare"):
    response = await client.post("/v1/opening-preparations", json=request, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return response.json()


async def confirm(client, record, selected=None):
    return await client.post(f'/v1/opening-preparations/{record["preparation_id"]}/confirm',
        headers={"Idempotency-Key": "confirm." + record["preparation_id"]},
        json={"character_id": record["character_id"], "catalog_version": record["catalog_version"],
              "selected_ids": selected if selected is not None else [t["id"] for t in record["candidates"][:2]]})


async def test_refresh_concurrency_frozen_parameters_confirmation_replay(opening):
    runtime, client, request = opening
    records = await asyncio.gather(*(offer(client, request, f"prep.{i}") for i in range(5)))
    record = records[0]
    assert all(r == record for r in records)
    assert record["state"] == "PENDING" and record["result"] is None
    assert len(runtime.store._sessions) == 0
    changed = deepcopy(request)
    changed["profile_ref"]["profile_id"] = "difficulty.open-expedition"
    assert await offer(client, changed, "changed.parameters") == record
    restored = await client.get(f'/v1/player-characters/{record["character_id"]}/opening-preparation')
    assert restored.json() == record
    responses = await asyncio.gather(*(confirm(client, record) for _ in range(4)))
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    assert all(r.json() == responses[0].json() for r in responses)
    committed = responses[0].json()
    assert len(runtime.store._sessions) == 1 and len(runtime.store._opening_preparations) == 1
    immutable = runtime.store.snapshot()
    assert (await confirm(client, record, [t["id"] for t in record["candidates"][2:4]])).status_code == 409
    assert runtime.store.snapshot() == immutable
    sid = committed["result"]["session_id"]
    talents = await client.get(f"/v1/sessions/{sid}/opening-talents")
    assert talents.status_code == 200, talents.text
    assert {t["id"] for t in talents.json()} == set(committed["selected_ids"])
    assert (await client.get(f"/v1/sessions/{sid}/view")).status_code == 200
    for secret in ("seed", "effect_and_dependencies", "command_json", "owner"):
        assert secret not in str(committed)


@pytest.mark.parametrize("kind", ["empty", "one", "three", "duplicate", "future", "outside", "version", "character", "identity"])
async def test_invalid_public_confirmation_keeps_offer(opening, kind):
    runtime, client, request = opening
    record = await offer(client, request)
    selected = [t["id"] for t in record["candidates"][:2]]
    if kind == "empty": selected = []
    if kind == "one": selected = selected[:1]
    if kind == "three": selected += [record["candidates"][2]["id"]]
    if kind == "duplicate": selected = selected[:1] * 2
    if kind == "future": selected[0] = "T002"
    if kind == "outside": selected[0] = next(t.id for t in load_catalog() if t.status == "CURRENT" and t.id not in {c["id"] for c in record["candidates"]})
    altered = dict(record)
    if kind == "version": altered["catalog_version"] = "opening-talents/v2"
    if kind == "character": altered["character_id"] = "other.character"
    if kind == "identity": altered["preparation_id"] = "0" * 32
    before = dict(runtime.store._opening_preparations)
    response = await confirm(client, altered, selected)
    assert response.status_code in (404, 409, 422), response.text
    assert runtime.store._opening_preparations == before and not runtime.store._sessions


@pytest.mark.parametrize("stage", ["session", "world", "preparation", "commit"])
async def test_failure_rolls_back_admission_and_selection(opening, monkeypatch, stage):
    runtime, client, request = opening
    record = await offer(client, request)
    from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork, DemoRunEntryWorldBindingRepository
    from deviation_protocol.infrastructure.opening_preparation_persistence import DemoOpeningPreparationRepository
    from deviation_protocol.application.session_service import SessionService
    owner, method = {"session": (SessionService, "stage_run_entry_initialization"),
        "world": (DemoRunEntryWorldBindingRepository, "add_native"),
        "preparation": (DemoOpeningPreparationRepository, "save"), "commit": (DemoUnitOfWork, "commit")}[stage]
    before, offers = runtime.store.snapshot(), dict(runtime.store._opening_preparations)
    original = getattr(owner, method)
    async def fail(*args, **kwargs):
        if stage != "commit":
            await original(*args, **kwargs)
        raise RuntimeError("opening injected failure")
    with monkeypatch.context() as patch:
        patch.setattr(owner, method, fail)
        with pytest.raises(RuntimeError, match="opening injected failure"):
            await confirm(client, record)
    assert runtime.store.snapshot() == before and runtime.store._opening_preparations == offers
    assert (await confirm(client, record)).status_code == 200


@pytest.mark.parametrize("stage", ["prepare", "confirm"])
async def test_lost_commit_acknowledgement_replays_original_record(opening, monkeypatch, stage):
    runtime, client, request = opening
    from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork
    from deviation_protocol.infrastructure.opening_preparation_persistence import decode
    record = await offer(client, request) if stage == "confirm" else None
    original = DemoUnitOfWork.commit
    async def lose_ack(unit):
        await original(unit)
        raise RuntimeError("opening commit acknowledgement lost")
    with monkeypatch.context() as patch:
        patch.setattr(DemoUnitOfWork, "commit", lose_ack)
        with pytest.raises(RuntimeError, match="opening commit acknowledgement lost"):
            if stage == "prepare":
                await offer(client, request)
            else:
                await confirm(client, record)
    assert len(runtime.store._opening_preparations) == 1
    stored = decode(next(iter(runtime.store._opening_preparations.values())))
    recovered = await offer(client, request)
    assert recovered["preparation_id"] == stored.preparation_id
    assert tuple(t["id"] for t in recovered["candidates"]) == stored.candidates
    if stage == "confirm":
        assert (await confirm(client, record)).json() == recovered
        assert len(runtime.store._sessions) == 1
    else:
        assert not runtime.store._sessions
