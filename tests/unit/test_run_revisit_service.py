"""Exact replay, transport, rollback and trial-publication contracts on real Demo families."""
import asyncio
from dataclasses import replace
import httpx
import pytest
from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.application.run_revisit_service import RunRevisitCommand
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
from tests.unit.test_run_revisit_api import reach_hold
from tests.unit.test_run_revisit_api import action, view
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending

@pytest.mark.parametrize("raw",[b'{}',b'null',b'{"expected_run_state_version":true,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_run_state_version":3,"expected_session_state_version":0}',
    b'\xef\xbb\xbf{"expected_run_state_version":3,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_session_state_version":0,"destination":"x"}',b' '*1025])
async def test_revisit_closed_transport_before_lookup(raw):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    before=runtime.store.snapshot()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/sessions/missing/run-revisit",content=raw,
            headers={"Content-Type":"application/json","Idempotency-Key":"invalid"})
        assert response.status_code==422,response.text
    assert runtime.store.snapshot()==before



@pytest.mark.parametrize("stage", ["session", "event", "snapshot", "revision", "participation", "cas", "receipt", "entry", "reconstruction", "trial"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_r07_demo_each_staging_boundary_and_trial_are_atomic(monkeypatch, stage, cancel):
    from deviation_protocol.infrastructure import demo_persistence as d
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        *_,held=await reach_hold(client,"difficulty.silent-hunting-ground")
        sid=held["metadata"]["session_id"];before=runtime.store.snapshot()
        command=RunRevisitCommand(public_operation_key=RunEntryPublicOperationKey(value="fault.once"),expected_run_state_version=4,
            expected_session_state_version=held["metadata"]["state_version"])
        service=runtime.services.run_revisit_service
        sentinel=asyncio.CancelledError("injected regional cancellation") if cancel else RuntimeError("injected regional fault")
        with monkeypatch.context() as patch:
            if stage in ("reconstruction","trial"):
                original=d._classify_demo_run;calls=0
                def fail(*args,**kwargs):
                    nonlocal calls
                    result=original(*args,**kwargs)
                    if result.canonical_run.state_version.value==5:
                        calls+=1
                        if calls==(2 if stage=="trial" else 1):raise sentinel
                    return result
                patch.setattr(d,"_classify_demo_run",fail)
            else:
                owner,method={"session":(d.DemoSessionRepository,"add_initial_session"),
                    "event":(d.DemoSessionRepository,"persist_events"),"snapshot":(d.DemoSessionRepository,"add_initial_snapshot"),
                    "revision":(d.DemoRunRepository,"append_revision"),"participation":(d.DemoRunSessionParticipationRepository,"add"),
                    "cas":(d.DemoRunRepository,"compare_and_swap_current"),"receipt":(d.DemoRunMutationReceiptRepository,"add"),
                    "entry":(d.DemoRunWorldRevisitRepository,"add")}[stage]
                original=getattr(owner,method)
                async def fail(*args,**kwargs):
                    await original(*args,**kwargs)
                    raise sentinel
                patch.setattr(owner,method,fail)
            expected=asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError if stage=="trial" else RuntimeError
            with pytest.raises(expected):await service.revisit(get_current_principal(),session_id=sid,command=command)
        assert runtime.store.snapshot()==before
        assert not runtime.store.active_uows and not runtime.store.any_session_lock_held
        result=await service.revisit(get_current_principal(),session_id=sid,command=command)
        settled=runtime.store.snapshot()
        def forbidden(*args,**kwargs):raise AssertionError("replay consumed preparation/time/commit")
        from deviation_protocol.application.session_service import SessionService
        with monkeypatch.context() as patch:
            patch.setattr(SessionService,"prepare_regional_revisit_initialization",forbidden)
            patch.setattr(d.DemoUnitOfWork,"commit",forbidden)
            replay=replace(service,continuation=replace(service.continuation,authority=replace(service.authority,clock=forbidden)))
            assert await replay.revisit(get_current_principal(),session_id=sid,command=command)==result
        assert runtime.store.snapshot()==settled


@pytest.mark.parametrize("ending", ["active", "release", "deadline", "hold"])
async def test_r03_actual_unlock_and_one_use_no_farming(ending):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground")
        first,_=await play_to_ending(client,entered["session_id"])
        response=await client.post(f'/v1/sessions/{entered["session_id"]}/run-continuation',
            json=dict(expected_run_state_version=3,expected_session_state_version=first["metadata"]["state_version"]),
            headers={"Idempotency-Key":"eligibility.continue"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"]
        if ending=="deadline":
            for n in range(40):
                current=await view(client,sid)
                if current["scenario_status"]=="ENDED":break
                await action(client,sid,f"wait.{n}",action_type="CUSTOM",description="静候核验")
            assert (await view(client,sid))["ending_id"]=="undelivered_receipt.ending.deadline_reached"
        elif ending in ("release","hold"):
            await action(client,sid,"observe",action_type="OBSERVE",description="核对收件台")
            await action(client,sid,"talk",action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对排程")
            decision=await view(client,sid)
            await action(client,sid,"choose",action_type="CHOOSE",decision_id=decision["narrative_frame"]["decision_id"],
                choice_id="undelivered_receipt.action."+ending)
        current=await view(client,sid)
        command=dict(expected_run_state_version=4,expected_session_state_version=current["metadata"]["state_version"])
        before=runtime.store.snapshot()
        offer=await client.get(f"/v1/sessions/{sid}/run-journey")
        assert offer.status_code==200,offer.text
        assert (offer.json()["next_transition"] is not None)==(ending=="hold")
        assert runtime.store.snapshot()==before
        for extra in (dict(destination="receipt_archive"),dict(unlocked=True)):
            invalid=await client.post(f"/v1/sessions/{sid}/run-revisit",json={**command,**extra},headers={"Idempotency-Key":"invalid"})
            assert invalid.status_code==422
            assert runtime.store.snapshot()==before
        reply=await client.post(f"/v1/sessions/{sid}/run-revisit",json=command,headers={"Idempotency-Key":"once"})
        if ending!="hold":
            assert reply.status_code==409 and reply.json()["error"]["error_code"]=="RUN_REVISIT_NOT_AVAILABLE"
            assert runtime.store.snapshot()==before
            return
        assert reply.status_code==200,reply.text
        third=reply.json()["session_id"]
        before=runtime.store.snapshot()
        for path in (entered["session_id"],sid,third):
            assert (await client.get(f"/v1/sessions/{path}/run-journey")).json()["next_transition"] is None
            rejected=await client.post(f"/v1/sessions/{path}/run-revisit",json=command,headers={"Idempotency-Key":"fresh.key"})
            assert rejected.status_code==409 and rejected.json()["error"]["error_code"]=="RUN_REVISIT_NOT_AVAILABLE"
        conflict=await client.post(f"/v1/sessions/{sid}/run-revisit",json={**command,"expected_session_state_version":0},headers={"Idempotency-Key":"once"})
        assert conflict.status_code==409 and conflict.json()["error"]["error_code"]=="IDEMPOTENCY_CONFLICT"
        assert runtime.store.snapshot()==before
