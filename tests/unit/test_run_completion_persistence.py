"""Synthetic corruptions of a public-play family; independent evidence oracle."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import httpx

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_run_completion_api import reach_archive


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


async def test_a03_complete_evidence_golden_and_every_association_rejects_on_owned_paths():
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        history,regional,_,ended=await reach_archive(client,"difficulty.silent-hunting-ground")
        paths=(history[0]["session_id"],history[3]["session_id"],regional["session_id"])
        body=dict(expected_run_state_version=5,expected_session_state_version=ended["metadata"]["state_version"])
        before=runtime.store.snapshot()
        response=await client.post(f"/v1/sessions/{paths[2]}/run-complete",json=body,headers={"Idempotency-Key":"golden"})
        assert response.status_code==200,response.text
        after=runtime.store.snapshot()
        key,row=next((k,v) for k,v in after.run_mutation_receipts.items() if v.resulting_state_version==6)
        request=dict(schema="run.complete-revisited-native-request/v1",controller_binding="binding.demo-player",player_id="demo-player",
            public_operation_key="golden",run_id=regional["run_id"],continuous_story_line_id=before.run_current[regional["run_id"]].continuous_story_line_id.value,
            source_session_id=paths[2],source_reference="source.demo-run",**body)
        digest=lambda value:hashlib.sha256(canonical(value)).hexdigest()
        operation=digest(dict(schema="run.complete-revisited-native-operation/v1",controller_binding="binding.demo-player",public_operation_key="golden",run_id=regional["run_id"]))
        identifier=digest(dict(schema="run.completion-id/v1",run_id=regional["run_id"],continuous_story_line_id=request["continuous_story_line_id"],operation_id=operation))
        sources=[]
        packs=("7cb4b45d527c96a7d7477b14053a3d85acf532d41f50dd7499656a6e53ab1ec0",
               "74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c",
               "fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39")
        for ordinal,sid in enumerate(paths,1):
            state=before.snapshots[sid].state;game=before.sessions[sid].session
            visit_id=digest(dict(schema="run.world-visit-id/v2" if ordinal==3 else "run.world-visit-id/v1",
                run_id=regional["run_id"],continuous_story_line_id=request["continuous_story_line_id"],session_id=sid,joined_state_version=ordinal+2))
            sources.append(dict(visit_id=visit_id,visit_ordinal=ordinal,session_id=sid,session_state_version=game.state_version,
                world=dict(world_id="world.death_certificate" if ordinal==1 else "world.undelivered_receipt",world_version=1),
                region=dict(region_id=("region.death_certificate.facility","region.undelivered_receipt.dispatch_hall","region.undelivered_receipt.verification_archive")[ordinal-1],region_version=1),
                scenario_id=game.scenario_id,scenario_content_version=game.scenario_version,content_sha256=packs[ordinal-1],snapshot_sha256=digest(state),
                ending_id=state["scenario_runtime"]["ending_id"],ending_status=state["scenario_runtime"]["ending_status"]))
        def event(sid,inner):
            e=next(e for e in before.events if e.session_id==sid and e.payload.get("scenario_event_type")==inner)
            return dict(session_id=sid,event_id=e.event_id,sequence_no=e.sequence_no,
                scenario_event_id=e.payload["scenario_event_id"],decision_id=e.payload["decision_id"],selected_action_id=e.payload["selected_action_id"])
        expected=dict(schema="run.complete-revisited-native-evidence/v1",request=request,completion_id=identifier,
            rule_version="receipt-archive-closure/v1",sources=sources,held_event=event(paths[1],"dispatch.held"),sealed_event=event(paths[2],"receipt_archive.record.sealed"),
            transition=dict(schema="run.canon-transition/v1",kind="close_unresolved_verification/v1",world=dict(world_id="world.undelivered_receipt",world_version=1),
                from_disposition="open_unresolved",to_disposition="closed_unresolved",preserved_facts=dict(dispatch_held=True,delivery_unproven=True,unresolved_sealed=True)),
            occurred_at=row.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
        assert row.operation_evidence_canonical==canonical(expected)
        assert row.fingerprint.hex()==digest(request)
        assert response.json()["completion"]["completion_id"]==identifier
        # Every top-level member plus every source/event association has an
        # independently corrupted record. These are deliberately synthetic.
        variants=[]
        for member in expected:
            changed=deepcopy(expected);del changed[member];variants.append(canonical(changed))
        for i,source in enumerate(sources):
            for member in source:
                changed=deepcopy(expected);value=changed["sources"][i][member]
                changed["sources"][i][member]=(value+1 if type(value) is int else {**value,next(iter(value)):"wrong"} if type(value) is dict else "b"*64 if member.endswith("sha256") else "wrong")
                variants.append(canonical(changed))
        for carrier in ("held_event","sealed_event"):
            for member in expected[carrier]:
                changed=deepcopy(expected);changed[carrier][member]=99 if member=="sequence_no" else "wrong";variants.append(canonical(changed))
        variants.extend((row.operation_evidence_canonical+b" ",b"\xef\xbb\xbf"+row.operation_evidence_canonical,b"{}",b"x"*16385))
        try:
            for payload in variants:
                runtime.store._run_mutation_receipts[key]=replace(row,operation_evidence_canonical=payload)
                corrupted=runtime.store.snapshot()
                for sid in paths:
                    for endpoint in ("view","run-journey","run-status","run-completion"):
                        reply=await client.get(f"/v1/sessions/{sid}/{endpoint}")
                        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",reply.text
                replay=await client.post(f"/v1/sessions/{paths[2]}/run-complete",json=body,headers={"Idempotency-Key":"golden"})
                assert replay.status_code==409 and replay.json()["error"]["error_code"]=="SNAPSHOT_INVALID",replay.text
                assert runtime.store.snapshot()==corrupted
        finally:runtime.store._run_mutation_receipts[key]=row
        assert runtime.store.snapshot()==after
        assert (await client.get(f"/v1/sessions/{paths[2]}/run-completion")).status_code==200


async def test_a03_actual_seal_event_memory_and_fact_provenance_before_eligibility():
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        history,regional,_,ended=await reach_archive(client,"difficulty.silent-hunting-ground")
        sid=regional["session_id"];paths=(history[0]["session_id"],history[3]["session_id"],sid)
        original_events=deepcopy(runtime.store._events);original_snapshot=deepcopy(runtime.store._snapshots[sid])
        mutations=[]
        for field in ("scenario_event_type","scenario_event_id","decision_id","selected_action_id"):
            events=deepcopy(original_events)
            index=next(i for i,e in enumerate(events) if e.session_id==sid and e.payload.get("scenario_event_type")=="receipt_archive.record.sealed")
            events[index]=replace(events[index],payload={**events[index].payload,field:"wrong"})
            mutations.append((events,original_snapshot))
        events=[e for e in original_events if not (e.session_id==sid and e.payload.get("scenario_event_type")=="receipt_archive.record.sealed")]
        mutations.append((events,original_snapshot))
        for field,value in (("last_source_event_id","wrong"),("last_source_sequence_no",999),("ending_id","wrong")):
            snapshot=deepcopy(original_snapshot);snapshot.state["player_memory"]["scenario_records"][0][field]=value
            mutations.append((original_events,snapshot))
        snapshot=deepcopy(original_snapshot)
        snapshot.state["scenario_runtime"]["mutable_fact_values"]["receipt_archive.fact.unresolved_sealed"]=False
        mutations.append((original_events,snapshot))
        try:
            for events,snapshot in mutations:
                runtime.store._events=deepcopy(events);runtime.store._snapshots[sid]=deepcopy(snapshot)
                before=runtime.store.snapshot()
                for path in paths:
                    for route in ("view","run-journey","run-status","run-completion"):
                        reply=await client.get(f"/v1/sessions/{path}/{route}")
                        assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",reply.text
                reply=await client.post(f"/v1/sessions/{sid}/run-complete",json=dict(expected_run_state_version=5,
                    expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"corrupted"})
                assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",reply.text
                assert runtime.store.snapshot()==before
        finally:runtime.store._events=original_events;runtime.store._snapshots[sid]=original_snapshot
