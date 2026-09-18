from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import hashlib
import json
import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending


@pytest.mark.parametrize("corruption",["root_missing","visit_missing","position_missing","root_digest","root_bytes","visit_order",
    "position_session","crossed_root","crossed_visit","source_snapshot","source_memory","destination_memory","content_version","receipt",
    "coherent_initial_memory","active_source_job"])
async def test_owned_continuation_corruption_never_becomes_null_predecessor(corruption):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground")
        source=entered["session_id"]
        ended,_=await play_to_ending(client,source)
        response=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"corrupt.continue"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"];store=runtime.store;rid=entered["run_context"]["run_id"]
        root_key=next(k for k,v in store._run_world_states.items() if v.world_id=="world.undelivered_receipt")
        visit_key=next(k for k,v in store._run_world_visits.items() if v.visit_ordinal==2)
        if corruption=="root_missing":del store._run_world_states[root_key]
        elif corruption=="visit_missing":del store._run_world_visits[visit_key]
        elif corruption=="position_missing":store._run_world_positions.clear()
        elif corruption=="root_digest":store._run_world_states[root_key].state_sha256=b"\0"*32
        elif corruption=="root_bytes":store._run_world_states[root_key].state_canonical=b"{}"
        elif corruption=="visit_order":store._run_world_visits[visit_key].visit_ordinal=True
        elif corruption=="position_session":store._run_world_positions[rid].session_id=source
        elif corruption in ("crossed_root","crossed_visit"):
            mapping,key=(store._run_world_states,root_key) if corruption=="crossed_root" else (store._run_world_visits,visit_key)
            mapping[("foreign.run",key[1])]=SimpleNamespace(**{**vars(deepcopy(mapping[key])),"run_id":"foreign.run"})
        elif corruption=="source_snapshot":store._snapshots[source].state["player"]["resources"]["composure"]["current"]+=1
        elif corruption=="source_memory":store._snapshots[source].state["player_memory"]["scenario_records"]=[]
        elif corruption=="destination_memory":store._snapshots[sid].state["player_memory"]=deepcopy(store._snapshots[source].state["player_memory"])
        elif corruption=="content_version":store._sessions[sid]=replace(store._sessions[sid],session=replace(store._sessions[sid].session,scenario_version="foreign.1"))
        elif corruption=="receipt":
            key=next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version==4)
            store._run_mutation_receipts[key]=replace(store._run_mutation_receipts[key],operation_evidence_canonical=b"{}")
        elif corruption=="active_source_job":
            from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
            key=next(k for k,v in store._narrative_jobs.items() if v.session_id==source and v.attempt_count==1)
            store._narrative_jobs[key]=store._narrative_jobs[key].model_copy(update={"status":NarrativeJobStatus.PREPARED,
                "validated_proposal":None,"validated_proposal_digest":None,"outcome_rule_id":None,
                "accepted_narrative_text":None,"attempt_count":0})
        elif corruption=="coherent_initial_memory":
            from deviation_protocol.domain.world_continuation import snapshot_canonical_bytes,decode_world_state_root
            from deviation_protocol.domain.run import canonical_run_operation_bytes
            row=store._run_world_states[root_key];root=json.loads(row.state_canonical)
            memory=root["snapshot"]["player_memory"]
            removed=memory["known_public_facts"].pop()["fact_ref"]
            memory["scenario_records"][0]["known_public_fact_refs"].remove(removed)
            root["snapshot_sha256"]=hashlib.sha256(snapshot_canonical_bytes(root["snapshot"])).hexdigest()
            row.state_canonical=snapshot_canonical_bytes(root);row.state_sha256=hashlib.sha256(row.state_canonical).digest()
            # This is valid local memory and all digests/associations agree; only
            # independent sealed-initialization reconstruction can reject it.
            runtime.services.content_registry.validate_root(decode_world_state_root(row.state_canonical))
            store._snapshots[sid].state["player_memory"]=deepcopy(memory)
            key=next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version==4)
            evidence=json.loads(store._run_mutation_receipts[key].operation_evidence_canonical)
            evidence["destination_world_state_sha256"]=row.state_sha256.hex()
            store._run_mutation_receipts[key]=replace(store._run_mutation_receipts[key],operation_evidence_canonical=canonical_run_operation_bytes(evidence))
        before=store.snapshot()
        for target in (source,sid):
            for route in ("view","run-continuation","run-status"):
                reply=await client.get(f"/v1/sessions/{target}/{route}")
                assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",(corruption,route,reply.text)
        assert store.snapshot()==before


async def test_every_new_root_receipt_and_row_field_rejects_independent_corruption():
    """One actual public journey, then isolated single-field damage and rollback."""
    from deviation_protocol.domain.world_continuation import snapshot_canonical_bytes
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground")
        source=entered["session_id"];ended,_=await play_to_ending(client,source)
        response=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"matrix.continue"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"];store=runtime.store;cases=0
        async def rejected(label):
            nonlocal cases
            before=store.snapshot()
            for target in (source,sid):
                reply=await client.get(f"/v1/sessions/{target}/run-continuation")
                assert reply.status_code==409 and reply.json()["error"]["error_code"]=="SNAPSHOT_INVALID",(label,reply.text)
            assert store.snapshot()==before
            cases+=1
        # Every canonical key, including nested request, selection and snapshot
        # keys, is independently removed. Root digests are recomputed so the
        # decoder/association must reject the malformed evidence itself.
        def paths(value,prefix=()):
            if isinstance(value,dict):
                for key,item in value.items():
                    yield prefix+(key,)
                    yield from paths(item,prefix+(key,))
        for key,original in list(store._run_world_states.items()):
            payload=json.loads(original.state_canonical)
            for path in paths(payload):
                damaged=deepcopy(payload);parent=damaged
                for part in path[:-1]:parent=parent[part]
                del parent[path[-1]]
                row=deepcopy(original);row.state_canonical=snapshot_canonical_bytes(damaged)
                row.state_sha256=hashlib.sha256(row.state_canonical).digest()
                store._run_world_states[key]=row
                try:await rejected(("root",path))
                finally:store._run_world_states[key]=original
        receipt_key=next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version==4)
        receipt=store._run_mutation_receipts[receipt_key];payload=json.loads(receipt.operation_evidence_canonical)
        for path in paths(payload):
            damaged=deepcopy(payload);parent=damaged
            for part in path[:-1]:parent=parent[part]
            del parent[path[-1]]
            store._run_mutation_receipts[receipt_key]=replace(receipt,operation_evidence_canonical=snapshot_canonical_bytes(damaged))
            try:await rejected(("receipt",path))
            finally:store._run_mutation_receipts[receipt_key]=receipt
        for mapping in (store._run_world_states,store._run_world_visits,store._run_world_positions):
            for key,original in list(mapping.items()):
                for field in vars(original):
                    row=deepcopy(original);setattr(row,field,None);mapping[key]=row
                    try:await rejected(("column",field))
                    finally:mapping[key]=original
        assert cases>200
        assert (await client.get(f"/v1/sessions/{sid}/run-continuation")).status_code==200
