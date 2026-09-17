"""Sanitized in-process ASGI native journey, usable in independent child processes."""
import asyncio
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import httpx
from pydantic import BaseModel
from deviation_protocol.api.main import create_app
from deviation_protocol.api.demo_composition import build_demo_runtime
from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS
from tests.unit.test_native_run_entry_api import body


def detached(value):
    if isinstance(value, BaseModel): return detached(value.model_dump(mode="python"))
    if is_dataclass(value): return {f.name:detached(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict): return [[detached(k),detached(v)] for k,v in sorted(value.items(), key=lambda item:repr(item[0]))]
    if isinstance(value, (list,tuple)): return [detached(v) for v in value]
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, bytes): return value.hex()
    if isinstance(value, Enum): return value.value
    return value


async def drive(profile, variation=False):
    calls=[]
    def denied(*args, **kwargs):
        calls.append(True)
        raise AssertionError("external operation forbidden")
    with patch("deviation_protocol.api.main.create_engine", denied), patch("deviation_protocol.api.main.DeepSeekNarrativeProvider", denied), patch("socket.socket.connect", denied):
        runtime = build_demo_runtime()
        app=create_app(services=runtime.services)
        app.state.api_services=runtime.services
        trace=[]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://native.test") as client:
            options=await client.get("/v1/run-entry-options"); assert options.status_code==200
            trace.append(options.json())
            created=await client.post("/v1/player-characters",headers={"Idempotency-Key":"native.character"},json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
            assert created.status_code==200
            trace.append(created.json())
            request=body(created.json()["player_character_id"]["value"])
            request["profile_ref"]["profile_id"]=profile
            if variation:
                request["overrides"]=[{"parameter":"resource_pressure","value":30}]
                request["presentation"]={"world_tone":"heroic","reality_boundary":"chaotic","relationship_overlay":"charged"}
            admitted=await client.post("/v1/runs/native",headers={"Idempotency-Key":"native.entry"},json=request)
            assert admitted.status_code==200,admitted.text
            trace.append(admitted.json()); sid=admitted.json()["session_id"]
            for i,step in enumerate(CANONICAL_ACTIONS):
                # A fresh composition reconstructs context and gameplay from detached storage.
                fresh=build_demo_runtime(store=runtime.store,generators=runtime.generators)
                app.state.api_services=fresh.services
                view=await client.get(f"/v1/sessions/{sid}/view"); assert view.status_code==200,view.text
                trace.append(view.json())
                assert view.json()["run_context"]==admitted.json()["run_context"]
                if view.json()["scenario_status"]=="ENDED": break
                action=dict(turn_id=f"native.{i}",client_request_id=f"native.{i}",action_type=step.action_type)
                if step.choice_id: action.update(choice_id=step.choice_id,decision_id=view.json()["narrative_frame"]["decision_id"])
                if step.description: action["description"]=step.description
                response=await client.post(f"/v1/sessions/{sid}/actions",json=action)
                assert response.status_code==200 and response.json()["state_changed"],response.text
                trace.append(response.json())
                status=await client.get(f"/v1/sessions/{sid}/requests/{action['client_request_id']}")
                assert status.status_code==200 and status.json()["status"]=="COMMITTED",status.text
                trace.append(status.json())
                before=runtime.store.snapshot()
                assert (await client.post(f"/v1/sessions/{sid}/actions",json=action)).json()==response.json()
                assert runtime.store.snapshot()==before
            final=await client.get(f"/v1/sessions/{sid}/view"); assert final.status_code==200
            assert final.json()["scenario_status"]=="ENDED"
            trace.append(final.json())
            public_bytes=json.dumps(trace,ensure_ascii=False)
            for private_marker in ('"controller_binding"','"resolution_fingerprint"','"binding_digest"','"resolution_input"','"run_protocol_context"','"narrative_request"','"continuous_story_line_id"'):
                assert private_marker not in public_bytes
            assert (await client.post("/v1/runs/native",headers={"Idempotency-Key":"native.entry"},json=request)).json()==admitted.json()
            result=detached(runtime.store.snapshot())
            app.state.api_services=build_demo_runtime().services
            assert (await client.get(f"/v1/sessions/{sid}/view")).status_code==404
            assert calls==[]
            return {"trace":trace,"store":result,"external_calls":0,"restart_status":404}


if __name__=="__main__":
    assert not any(name in os.environ for name in ("DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"))
    print(json.dumps(asyncio.run(drive(sys.argv[1],len(sys.argv)>2)),ensure_ascii=False,sort_keys=True,separators=(",",":")))
