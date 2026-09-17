import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from tests.e2e.support.native_demo_replay_child import drive


@pytest.mark.parametrize("profile,variation", [("difficulty.open-expedition",False),("difficulty.fragile-alliance",False),
    ("difficulty.silent-hunting-ground",False),("difficulty.open-expedition",True)])
async def test_native_cross_process_exact_public_and_complete_store(profile,variation):
    expected=await drive(profile,variation)
    root=Path(__file__).resolve().parents[2]
    for seed in ("1","937"):
        environment=os.environ.copy()
        for key in ("DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"):
            environment.pop(key,None)
        environment["PYTHONHASHSEED"]=seed
        environment["PYTHONIOENCODING"]="utf-8"
        command=[sys.executable,str(root/"tests/e2e/support/native_demo_replay_child.py"),profile]
        if variation: command.append("variation")
        child=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=90)
        assert child.returncode==0,child.stderr.decode("utf-8")
        assert json.loads(child.stdout)==expected


async def drive_exit():
    import httpx
    from unittest.mock import patch
    from deviation_protocol.api.main import create_app
    from deviation_protocol.api.demo_composition import build_demo_runtime
    from tests.unit.test_native_demo import admit
    from tests.unit.test_run_exit_api import play_to_ending
    from tests.e2e.support.native_demo_replay_child import detached
    def denied(*args, **kwargs): raise AssertionError("external I/O is forbidden")
    with patch("socket.socket.connect",denied), patch("deviation_protocol.api.main.create_engine",denied), patch("deviation_protocol.api.main.DeepSeekNarrativeProvider",denied):
        runtime = build_demo_runtime()
        app = create_app(services=runtime.services)
        app.state.api_services = runtime.services
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
            first, request = await admit(client,"difficulty.silent-hunting-ground")
            sid = first["session_id"]
            ended, actions = await play_to_ending(client,sid)
            app.state.api_services = build_demo_runtime(store=runtime.store,generators=runtime.generators).services
            terminal = await client.post(f"/v1/sessions/{sid}/run-exit",headers={"Idempotency-Key":"deterministic.exit"},
                json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
            assert terminal.status_code == 200, terminal.text
            second = await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"deterministic.second"})
            assert second.status_code == 200, second.text
            fresh = (await client.get(f"/v1/sessions/{second.json()['session_id']}/view")).json()
            action = {**actions[0][0],"decision_id":fresh["narrative_frame"]["decision_id"]}
            played = await client.post(f"/v1/sessions/{second.json()['session_id']}/actions",json=action)
            assert played.status_code == 200 and played.json()["state_changed"]
            assert (await client.get(f"/v1/sessions/{sid}/view")).json() == ended
            return {"first":first,"ending":ended,"exit":terminal.json(),"second":second.json(),"action":played.json(),"store":detached(runtime.store.snapshot())}


async def test_e09_terminal_store_and_repeat_journey_are_cross_process_deterministic():
    expected = await drive_exit()
    environment = os.environ.copy()
    for key in ("DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"):
        environment.pop(key,None)
    environment.update(PYTHONHASHSEED="713",PYTHONIOENCODING="utf-8")
    child = subprocess.run([sys.executable,"-c","import asyncio,json; from tests.e2e.test_native_demo_playthrough import drive_exit; print(json.dumps(asyncio.run(drive_exit()),ensure_ascii=False))"],
        cwd=Path(__file__).resolve().parents[2],env=environment,capture_output=True,timeout=90)
    assert child.returncode == 0,child.stderr.decode("utf-8")
    assert json.loads(child.stdout) == expected
