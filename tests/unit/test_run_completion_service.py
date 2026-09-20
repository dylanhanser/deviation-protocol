"""Completion owns one atomic publication and no work on exact replay."""
import asyncio
from dataclasses import replace

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.application.run_completion_service import RunCompletionCommand
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
from tests.unit.test_run_completion_api import reach_archive


async def test_a07_every_demo_boundary_rollback_cancellation_and_replay(monkeypatch):
    from deviation_protocol.infrastructure import demo_persistence as d
    from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        _, regional, _, ended=await reach_archive(client,"difficulty.silent-hunting-ground")
        sid=regional["session_id"];before=runtime.store.snapshot()
        command=RunCompletionCommand(public_operation_key=RunEntryPublicOperationKey(value="fault.once"),expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"])
        service=runtime.services.run_completion_service
        for stage in ("revision","cas","receipt","reconstruction","trial"):
            for cancel in (False,True):
                sentinel=asyncio.CancelledError("completion cancellation") if cancel else RuntimeError("completion fault")
                with monkeypatch.context() as patch:
                    if stage in ("reconstruction","trial"):
                        original=d._classify_demo_run;calls=0
                        def fail(*args,**kwargs):
                            nonlocal calls
                            result=original(*args,**kwargs)
                            if result.canonical_run.lifecycle_status.value=="completed":
                                calls+=1
                                if calls==(2 if stage=="trial" else 1):raise sentinel
                            return result
                        patch.setattr(d,"_classify_demo_run",fail)
                    else:
                        owner,method={"revision":(d.DemoRunRepository,"append_revision"),
                            "cas":(d.DemoRunRepository,"compare_and_swap_current"),
                            "receipt":(d.DemoRunMutationReceiptRepository,"add")}[stage]
                        original=getattr(owner,method)
                        async def fail(*args,**kwargs):
                            await original(*args,**kwargs)
                            raise sentinel
                        patch.setattr(owner,method,fail)
                    expected=asyncio.CancelledError if cancel else NativeRunAdmissionOutcomeUnknownError if stage=="trial" else RuntimeError
                    with pytest.raises(expected):await service.complete(get_current_principal(),session_id=sid,command=command)
                assert runtime.store.snapshot()==before
                assert not runtime.store.active_uows and not runtime.store.any_session_lock_held
        import deviation_protocol.application.run_completion_service as completion
        project=completion.completion_result
        def outside_locks(family):
            assert not runtime.store.active_uows and not runtime.store.any_session_lock_held
            return project(family)
        with monkeypatch.context() as patch:
            patch.setattr(completion,"completion_result",outside_locks)
            result=await service.complete(get_current_principal(),session_id=sid,command=command)
        settled=runtime.store.snapshot()
        def forbidden(*args,**kwargs):raise AssertionError("replay consumed clock or commit")
        replay=replace(service,revisit=replace(service.revisit,continuation=replace(service.revisit.continuation,
            authority=replace(service.authority,clock=forbidden))))
        with monkeypatch.context() as patch:
            patch.setattr(d.DemoUnitOfWork,"commit",forbidden)
            patch.setattr(completion,"completion_result",outside_locks)
            assert await replay.complete(get_current_principal(),session_id=sid,command=command)==result
        assert runtime.store.snapshot()==settled


@pytest.mark.parametrize("raw",[b'{}',b'null',b'{"expected_run_state_version":true,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_run_state_version":3,"expected_session_state_version":0}',
    b'\xef\xbb\xbf{"expected_run_state_version":3,"expected_session_state_version":0}',
    b'{"expected_run_state_version":3,"expected_session_state_version":0,"destination":"x"}',b' '*1025])
async def test_a02_completion_closed_transport_before_lookup(raw):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    before=runtime.store.snapshot()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/sessions/missing/run-complete",content=raw,
            headers={"Content-Type":"application/json","Idempotency-Key":"invalid"})
        assert response.status_code==422,response.text
    assert runtime.store.snapshot()==before



