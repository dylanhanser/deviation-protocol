"""Public-play replay authority and strict transport on the real Demo store."""
from dataclasses import replace
import hashlib
import json
import asyncio
import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.api.schemas import NativeRunContinuationStatusResponse
from deviation_protocol.application.run_continuation_service import RunContinuationCommand
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending


@pytest.mark.parametrize("raw",[b'{}',b'null',b'{"expected_run_state_version":true,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_run_state_version":3,"expected_session_state_version":0}',
    b'\xef\xbb\xbf{"expected_run_state_version":3,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_session_state_version":0,"destination":"x"}',b' '*1025])
async def test_continuation_closed_transport_before_lookup(raw):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    before=runtime.store.snapshot()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/sessions/missing/run-continuation",content=raw,
            headers={"Content-Type":"application/json","Idempotency-Key":"invalid"})
        assert response.status_code==422,response.text
    assert runtime.store.snapshot()==before


async def test_replay_uses_no_clock_identity_preparation_or_commit(monkeypatch):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground");sid=entered["session_id"]
        ended,_=await play_to_ending(client,sid)
        body=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        reply=await client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"replay.once"})
        assert reply.status_code==200,reply.text
        result=reply.json();before=runtime.store.snapshot()
        def forbidden(*args,**kwargs):raise AssertionError("replay consumed an identity/clock/preparation")
        service=runtime.services.run_continuation_service
        service=replace(service,authority=replace(service.authority,clock=forbidden))
        from deviation_protocol.application.session_service import SessionService
        monkeypatch.setattr(SessionService,"prepare_world_continuation_initialization",forbidden)
        command=RunContinuationCommand(public_operation_key=RunEntryPublicOperationKey(value="replay.once"),**body)
        async with runtime.store.unit_of_work() as unit:
            unit_type=type(unit)
        monkeypatch.setattr(unit_type,"commit",forbidden)
        # Use the exact public Demo principal, independently supplied by its resolver.
        from deviation_protocol.api.dependencies import get_current_principal
        principal=get_current_principal()
        from deviation_protocol.api.schemas import NativeRunContinuationResultResponse
        replay=await service.continue_run(principal,session_id=sid,command=command)
        assert NativeRunContinuationResultResponse.model_validate(replay).model_dump(mode="json")==result
        changed=await client.post(f"/v1/sessions/{sid}/run-continuation",json={**body,"expected_session_state_version":0},headers={"Idempotency-Key":"replay.once"})
        assert changed.status_code==409 and changed.json()["error"]["error_code"]=="IDEMPOTENCY_CONFLICT"
        fresh=await client.post(f"/v1/sessions/{sid}/run-continuation",json=body,headers={"Idempotency-Key":"replay.other"})
        assert fresh.status_code==409 and fresh.json()["error"]["error_code"]=="RUN_CONTINUATION_NOT_AVAILABLE"
        assert runtime.store.snapshot()==before
        status=(await client.get(f"/v1/sessions/{result['session_id']}/run-continuation")).json()
        for change in ({"predecessor":None},{"run_state_version":3},{"lifecycle_status":"terminated"}):
            with pytest.raises(ValueError):NativeRunContinuationStatusResponse.model_validate({**status,**change})
        missing=dict(status);missing.pop("predecessor")
        with pytest.raises(ValueError):NativeRunContinuationStatusResponse.model_validate(missing)


async def test_world_root_bytes_match_independent_snapshot_convention():
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground");source=entered["session_id"]
        ended,_=await play_to_ending(client,source)
        response=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"golden"})
        assert response.status_code==200,response.text
        for row in runtime.store.snapshot().run_world_states.values():
            obj=json.loads(row.state_canonical)
            snapshot=runtime.store.snapshot().snapshots[obj["session_id"]].state
            canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
            assert obj["snapshot"]==snapshot
            assert obj["snapshot_sha256"]==hashlib.sha256(canonical(snapshot)).hexdigest()
            assert row.state_canonical==canonical(dict(reversed(list(obj.items()))))
            assert row.state_sha256==hashlib.sha256(canonical(obj)).digest()


@pytest.mark.parametrize("trial",[False,True])
@pytest.mark.parametrize("cancel",[False,True])
async def test_demo_continuation_staging_and_trial_failure_publish_nothing(monkeypatch,trial,cancel):
    from deviation_protocol.infrastructure import demo_persistence
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground");sid=entered["session_id"]
        ended,_=await play_to_ending(client,sid);before=runtime.store.snapshot()
        original=demo_persistence._classify_demo_run;calls=0
        sentinel=asyncio.CancelledError("trial cancelled") if cancel else RuntimeError("trial failed")
        def fail(*args,**kwargs):
            nonlocal calls
            result=original(*args,**kwargs)
            if result.canonical_run.state_version.value==4:
                calls+=1
                if calls==(2 if trial else 1):raise sentinel
            return result
        command=RunContinuationCommand(public_operation_key=RunEntryPublicOperationKey(value="trial.once"),expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"])
        service=runtime.services.run_continuation_service
        with monkeypatch.context() as patch:
            patch.setattr(demo_persistence,"_classify_demo_run",fail)
            expected=asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError if trial else RuntimeError
            with pytest.raises(expected):await service.continue_run(get_current_principal(),session_id=sid,command=command)
        assert runtime.store.snapshot()==before
        result=await service.continue_run(get_current_principal(),session_id=sid,command=command)
        assert result["session_id"]!=sid
