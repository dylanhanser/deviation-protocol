"""Stored-candidate corruption and independent canonical-byte checks."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import httpx

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_run_revisit_api import reach_hold, action, view


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


async def test_r04_r05_entry_canonical_goldens_and_all_fields_fail_closed_from_every_visit():
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        entered, _, _, continued, _, held = await reach_hold(client, "difficulty.silent-hunting-ground")
        source = held["metadata"]["session_id"]
        before = runtime.store.snapshot()
        response = await client.post(f"/v1/sessions/{source}/run-revisit", headers={"Idempotency-Key": "golden"},
            json=dict(expected_run_state_version=4, expected_session_state_version=held["metadata"]["state_version"]))
        assert response.status_code == 200, response.text
        result = response.json()
        third = result["session_id"]
        key, original = next(iter(runtime.store._run_world_visit_entries.items()))
        obj = json.loads(original.entry_canonical)
        assert original.entry_canonical == canonical(dict(reversed(list(obj.items()))))
        assert original.entry_sha256 == hashlib.sha256(canonical(obj)).digest()
        assert obj["snapshot"] == runtime.store.snapshot().snapshots[third].state
        assert obj["snapshot_sha256"] == hashlib.sha256(canonical(obj["snapshot"])).hexdigest()
        assert obj["base_snapshot_sha256"] == hashlib.sha256(canonical(before.snapshots[source].state)).hexdigest()
        expected_id = canonical(dict(schema="run.world-visit-id/v2", run_id=result["run_id"],
            continuous_story_line_id=obj["continuous_story_line_id"], session_id=third, joined_state_version=5))
        assert obj["visit_id"] == hashlib.sha256(expected_id).hexdigest()
        receipt = next(row for row in runtime.store.snapshot().run_mutation_receipts.values() if row.resulting_state_version == 5)
        evidence = json.loads(receipt.operation_evidence_canonical)
        assert receipt.operation_evidence_canonical == canonical(evidence)
        assert evidence["selection_seed"] == hashlib.sha256(b"deviation-protocol:regional-revisit-selection:v1\0" + canonical(evidence["selection_inputs"])).hexdigest()
        assert evidence["destination_entry_sha256"] == original.entry_sha256.hex()
        # Build the complete expected records from the public command, prior
        # committed inputs and separately issued Session/event identities. Do
        # not obtain the expected member inventory from the record under test.
        after = runtime.store.snapshot()
        common = dict(run_id=entered["run_context"]["run_id"],
            continuous_story_line_id=before.run_current[result["run_id"]].continuous_story_line_id.value)
        digest = lambda value: hashlib.sha256(canonical(value)).hexdigest()
        base_digest = digest(before.snapshots[source].state)
        world = dict(world_id="world.undelivered_receipt", world_version=1)
        region = dict(region_id="region.undelivered_receipt.verification_archive", region_version=1)
        content = "fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39"
        visits = []
        for ordinal, sid, wid, rid in (
            (1, entered["session_id"], "world.death_certificate", "region.death_certificate.facility"),
            (2, source, "world.undelivered_receipt", "region.undelivered_receipt.dispatch_hall")):
            visits.append(dict(visit_id=digest(dict(schema="run.world-visit-id/v1", **common,
                session_id=sid, joined_state_version=ordinal+2)), visit_ordinal=ordinal,
                session_id=sid, world=dict(world_id=wid, world_version=1), region=dict(region_id=rid, region_version=1)))
        expected_entry = dict(schema="run-regional-entry/v1", **common,
            visit_id=hashlib.sha256(expected_id).hexdigest(), session_id=third, world=world, region=region,
            scenario_id="receipt_archive", scenario_content_version="receipt-archive-1.0.0", content_sha256=content,
            base_visit_id=visits[1]["visit_id"], base_session_id=source,
            base_session_state_version=held["metadata"]["state_version"], base_snapshot_sha256=base_digest,
            unlock_ending_id="undelivered_receipt.ending.receipt_held", snapshot_state_version=0,
            snapshot=after.snapshots[third].state, snapshot_sha256=digest(after.snapshots[third].state))
        assert original.entry_canonical == canonical(expected_entry)
        selection = dict(selector_version="regional-revisit/v1", **common, source_session_id=source,
            source_session_state_version=held["metadata"]["state_version"], source_snapshot_sha256=base_digest,
            resolution_fingerprint=before.run_protocol_bindings[result["run_id"]].resolution_fingerprint.hex(),
            visits=visits, eligible_pool=[dict(world=world, region=region, scenario_id="receipt_archive",
                scenario_content_version="receipt-archive-1.0.0", content_sha256=content,
                required_priority=0, weight=1, cooldown_completed_visits=0)])
        request = dict(schema="run.revisit-native-region-request/v1", **common,
            controller_binding="binding.demo-player", player_id="demo-player", public_operation_key="golden",
            source_session_id=source, expected_run_state_version=4,
            expected_session_state_version=held["metadata"]["state_version"], source_reference="source.demo-run")
        expected_evidence = dict(schema="run.revisit-native-region-evidence/v1", request=request,
            source_ending=dict(scenario_id="undelivered_receipt", scenario_content_version="undelivered-receipt-1.0.0",
                ending_id="undelivered_receipt.ending.receipt_held", ending_status="RESOLVED",
                session_state_version=held["metadata"]["state_version"], snapshot_sha256=base_digest),
            selection_inputs=selection,
            selection_seed=hashlib.sha256(b"deviation-protocol:regional-revisit-selection:v1\0"+canonical(selection)).hexdigest(),
            source_visit_id=visits[1]["visit_id"], destination_visit_id=expected_entry["visit_id"], destination_session_id=third,
            destination_creation_request_id=digest(dict(schema="run.regional-session-create/v1",
                controller_binding="binding.demo-player", public_operation_key="golden", run_id=result["run_id"])),
            destination_initial_event_id=next(e.event_id for e in after.events if e.session_id==third and e.sequence_no==1),
            destination_random_seed=after.sessions[third].session.random_seed, world_base_snapshot_sha256=base_digest,
            destination_entry_sha256=digest(expected_entry), carryover_rule="carry-player-state/v1",
            occurred_at=after.sessions[third].created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
        assert receipt.operation_evidence_canonical == canonical(expected_evidence)
        paths = (entered["session_id"], continued["session_id"], third)

        async def rejected():
            corrupt = runtime.store.snapshot()
            for sid in paths:
                for endpoint in ("view", "run-journey"):
                    reply = await client.get(f"/v1/sessions/{sid}/{endpoint}")
                    assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
            reply = await client.post(f"/v1/sessions/{third}/actions", json=dict(turn_id="corrupt.action", client_request_id="corrupt.action", action_type="OBSERVE", description="查看待核记录"))
            assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
            assert runtime.store.snapshot() == corrupt

        try:
            # Rehashing cannot authorize a missing/coerced/extra canonical member.
            for field in obj:
                changed = deepcopy(obj)
                del changed[field]
                row = deepcopy(original)
                row.entry_canonical = canonical(changed)
                row.entry_sha256 = hashlib.sha256(row.entry_canonical).digest()
                runtime.store._run_world_visit_entries[key] = row
                await rejected()
            for field, value in (("unexpected", True), ("snapshot_state_version", False),
                ("base_session_id", "foreign.session"), ("base_snapshot_sha256", "a" * 64),
                ("base_visit_id", "foreign.visit"), ("content_sha256", "a" * 64),
                ("run_id", "foreign.run"), ("continuous_story_line_id", "foreign.line")):
                changed = deepcopy(obj)
                changed[field] = value
                row = deepcopy(original)
                row.entry_canonical = canonical(changed)
                row.entry_sha256 = hashlib.sha256(row.entry_canonical).digest()
                runtime.store._run_world_visit_entries[key] = row
                await rejected()
            runtime.store._run_world_visit_entries[key] = deepcopy(original)
            for name in ("_run_world_visit_entries", "_run_world_visits", "_run_world_positions", "_run_mutation_receipts"):
                saved = deepcopy(getattr(runtime.store, name))
                try:
                    getattr(runtime.store, name).clear()
                    await rejected()
                    reply = await client.get("/v1/sessions/foreign.session/run-journey")
                    assert reply.status_code == 404
                finally:
                    setattr(runtime.store, name, saved)
            saved_events = deepcopy(runtime.store._events)
            saved_snapshot = deepcopy(runtime.store._snapshots[third])
            try:
                runtime.store._events = [e for e in saved_events if not (e.session_id == third and e.sequence_no == 1)]
                await rejected()
                runtime.store._events = [replace(e, payload={"scenario_id": "foreign"})
                    if e.session_id == third and e.sequence_no == 1 else e for e in saved_events]
                await rejected()
                runtime.store._events = saved_events
                state = deepcopy(saved_snapshot.state)
                state["player_memory"] = {}
                runtime.store._snapshots[third] = replace(saved_snapshot, state=state)
                await rejected()
                # Ownership remains first even with two corrupt owned-family records.
                runtime.store._run_world_visit_entries.clear()
                reply = await client.get("/v1/sessions/foreign.session/run-journey")
                assert reply.status_code == 404
                await rejected()
            finally:
                runtime.store._events = saved_events
                runtime.store._snapshots[third] = saved_snapshot
        finally:
            runtime.store._run_world_visit_entries[key] = original
        # Legitimate progressed evidence remains readable after the negative cases.
        await action(client, third, "valid.observe", action_type="OBSERVE", description="查看待核记录")
        assert (await view(client, third))["metadata"]["state_version"] == 1
        for sid in paths:
            assert (await client.get(f"/v1/sessions/{sid}/run-journey")).status_code == 200
