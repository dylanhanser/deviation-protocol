import httpx
import pytest
import asyncio
from dataclasses import replace

from deviation_protocol.api.main import create_app
from deviation_protocol.api.demo_composition import build_demo_runtime
from tests.unit.test_native_run_entry_api import body
from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS


async def admit(client, profile="difficulty.open-expedition", key="native.demo"):
    created = await client.post("/v1/player-characters", headers={"Idempotency-Key": key + ".character"},
        json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
    assert created.status_code == 200, created.text
    request = body(created.json()["player_character_id"]["value"])
    request["profile_ref"]["profile_id"] = profile
    response = await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    return response.json(), request


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.fragile-alliance", "difficulty.silent-hunting-ground"])
async def test_native_demo_public_play_and_replay(profile):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        admitted, request = await admit(client, profile)
        sid = admitted["session_id"]
        original = runtime.store.snapshot()
        for index, step in enumerate(CANONICAL_ACTIONS):
            result = await client.get(f"/v1/sessions/{sid}/view")
            assert result.status_code == 200, result.text
            view = result.json()
            assert view["run_context"] == admitted["run_context"]
            if view["scenario_status"] == "ENDED": break
            action = dict(turn_id=f"native.turn.{index}", client_request_id=f"native.request.{index}", action_type=step.action_type)
            if step.choice_id: action.update(choice_id=step.choice_id, decision_id=view["narrative_frame"]["decision_id"])
            if step.description: action["description"] = step.description
            result = await client.post(f"/v1/sessions/{sid}/actions", json=action)
            assert result.status_code == 200, result.text
            assert result.json()["state_changed"], (index, result.text)
            before_replay = runtime.store.snapshot()
            assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == result.json()
            assert runtime.store.snapshot() == before_replay
        final = await client.get(f"/v1/sessions/{sid}/view")
        assert final.json()["scenario_status"] == "ENDED"
        assert final.json()["ending_status"] in {"RESOLVED", "FAILED"}
        assert (await client.post("/v1/runs/native", json=request, headers={"Idempotency-Key": "native.demo"})).json() == admitted
        after = runtime.store.snapshot()
        assert after.run_current == original.run_current
        assert after.run_protocol_bindings == original.run_protocol_bindings
        assert after.run_entry_world_bindings == original.run_entry_world_bindings
        assert after.player_character_current == original.player_character_current
        assert after.provider_progress == original.provider_progress
        assert not runtime.store.active_uows and not runtime.store.any_session_lock_held


async def test_native_accepts_non_script_action_and_corruption_is_not_legacy():
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        admitted, _ = await admit(client)
        sid = admitted["session_id"]
        response = await client.post(f"/v1/sessions/{sid}/actions", json={"turn_id":"ordinary", "client_request_id":"ordinary",
            "action_type":"CUSTOM", "description":"我缓缓抬起手，示意自己还能听见。"})
        assert response.status_code == 200 and response.json()["state_changed"], response.text
        runtime.store._run_protocol_bindings.clear()
        corrupt = runtime.store.snapshot()
        response = await client.get(f"/v1/sessions/{sid}/view")
        assert response.status_code == 409
        assert response.json()["error"]["error_code"] == "SNAPSHOT_INVALID"
        assert runtime.store.snapshot() == corrupt


@pytest.mark.parametrize("stage", ["protocol", "world", "commit"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_native_admission_failure_discards_every_staged_map(monkeypatch, stage, cancel):
    from deviation_protocol.infrastructure.demo_persistence import DemoRunProtocolBindingRepository, DemoRunEntryWorldBindingRepository, DemoUnitOfWork
    runtime=build_demo_runtime(); app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        created=await client.post("/v1/player-characters",headers={"Idempotency-Key":"atomic.character"},json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
        baseline=runtime.store.snapshot()
        owner,method={"protocol":(DemoRunProtocolBindingRepository,"add_native"),"world":(DemoRunEntryWorldBindingRepository,"add_native"),"commit":(DemoUnitOfWork,"commit")}[stage]
        original=getattr(owner,method)
        async def fail(*args,**kwargs):
            if stage != "commit": await original(*args,**kwargs)
            raise asyncio.CancelledError() if cancel else RuntimeError("injected atomic failure")
        with monkeypatch.context() as patch:
            patch.setattr(owner,method,fail)
            request=body(created.json()["player_character_id"]["value"])
            if cancel:
                with pytest.raises(asyncio.CancelledError): await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"atomic.entry"})
            else:
                assert (await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"atomic.entry"})).status_code==500
        assert runtime.store.snapshot()==baseline
        assert runtime.store.active_uows==0 and not runtime.store.any_session_lock_held
        assert (await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"atomic.entry"})).status_code==200


@pytest.mark.parametrize("kind", ["world", "fingerprint", "input", "receipt", "reverse", "character", "snapshot"])
async def test_native_corruption_is_read_only_safe_failure(kind):
    runtime=build_demo_runtime(); app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        response,_=await admit(client)
        sid=response["session_id"]; rid=response["run_context"]["run_id"]; store=runtime.store
        if kind=="world": store._run_entry_world_bindings.clear()
        if kind=="fingerprint": store._run_protocol_bindings[rid]=replace(store._run_protocol_bindings[rid],resolution_fingerprint=b"\x00"*32)
        if kind=="input": store._run_protocol_bindings[rid]=replace(store._run_protocol_bindings[rid],resolution_input_canonical=b"{}")
        if kind=="receipt":
            key=next(iter(store._run_creation_receipts)); store._run_creation_receipts[key]=replace(store._run_creation_receipts[key],operation_evidence_canonical=b"\x8aBAD")
        if kind=="reverse": store._run_participations.clear()
        if kind=="character": store._player_character_revisions.clear()
        if kind=="snapshot": store._snapshots[sid].state["schema_version"]=True
        before=store.snapshot()
        view=await client.get(f"/v1/sessions/{sid}/view")
        assert view.status_code==409,view.text
        assert view.json()=={"error":{"error_code":"SNAPSHOT_INVALID","message":"Session state is unavailable or incompatible"}}
        assert store.snapshot()==before


async def test_native_renderer_nested_and_inherited_calls_do_zero_protected_work(monkeypatch):
    from deviation_protocol.infrastructure.deterministic_narrative import DeterministicDemoNarrativeProvider
    from deviation_protocol.application.narrative_models import NarrativeProposalRejectedError
    from deviation_protocol.domain.actions import ActionSubmission,ActionType
    from deviation_protocol.infrastructure.demo_persistence import DemoProcessStore
    calls=[]
    original=DemoProcessStore.unit_of_work
    def counted(self): calls.append("uow"); return original(self)
    monkeypatch.setattr(DemoProcessStore,"unit_of_work",counted)
    class Provider(DeterministicDemoNarrativeProvider):
        async def generate(self,request):
            before=list(calls)
            async def denied(identity):
                with pytest.raises(NarrativeProposalRejectedError):
                    await runtime.services.turn_orchestrator.handle(ActionSubmission(session_id=identity,turn_id="nested",client_request_id="nested",action_type=ActionType.CUSTOM,description="普通行动"))
            await denied(sid)
            await denied("other-session")
            await asyncio.gather(*(denied(sid) for _ in range(8)))
            assert calls==before
            assert runtime.store.active_uows==0 and not runtime.store.any_session_lock_held
            return await super().generate(request)
    runtime=build_demo_runtime(provider=Provider()); app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response,_=await admit(client); sid=response["session_id"]
        for i in range(2):
            result=await client.post(f"/v1/sessions/{sid}/actions",json={"turn_id":f"ordinary.{i}","client_request_id":f"ordinary.{i}","action_type":"CUSTOM","description":"我举起手向现场人员示意。"})
            assert result.status_code==200,result.text


async def test_native_inserts_require_explicit_admission_uow():
    runtime=build_demo_runtime()
    async with runtime.store.unit_of_work() as uow:
        for repository,method,args in [(uow.run_protocol_bindings,"add_native",(None,)),(uow.run_entry_world_bindings,"add_native",(None,)),(uow.run_creation_receipts,"add_native_with_evidence",(None,None))]:
            with pytest.raises(RuntimeError,match="admission UoW"):
                await getattr(repository,method)(*args,created_at=None)
    assert not runtime.store.snapshot().run_protocol_bindings


@pytest.mark.parametrize("cancel", [False, True])
async def test_native_render_allowance_consumed_on_failure_and_later_transaction_works(monkeypatch,cancel):
    from deviation_protocol.infrastructure.deterministic_narrative import DeterministicDemoNarrativeProvider
    from deviation_protocol.application.narrative_models import NarrativeProposalRejectedError
    class Provider(DeterministicDemoNarrativeProvider):
        calls=0
        async def generate(self,request):
            self.calls+=1
            if self.calls==1:
                raise asyncio.CancelledError() if cancel else RuntimeError("injected renderer failure")
            return await super().generate(request)
    provider=Provider(); runtime=build_demo_runtime(provider=provider)
    native=runtime.services.turn_orchestrator._DemoNarrativeDispatcher__native
    renderer=native.narrative_provider; generate=renderer.generate
    with pytest.raises(NarrativeProposalRejectedError): await generate(None)
    async def checked(request):
        try: return await generate(request)
        except (RuntimeError,asyncio.CancelledError):
            before=runtime.store.snapshot()
            with pytest.raises(NarrativeProposalRejectedError): await generate(request)
            with pytest.raises(NarrativeProposalRejectedError): await asyncio.create_task(generate(request))
            assert runtime.store.snapshot()==before and provider.calls==1
            raise
    monkeypatch.setattr(renderer,"generate",checked)
    app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        first,_=await admit(client,key="guard.first")
        payload={"turn_id":"guard.turn","client_request_id":"guard.request","action_type":"CUSTOM","description":"我举手示意。"}
        if cancel:
            with pytest.raises(asyncio.CancelledError): await client.post(f"/v1/sessions/{first['session_id']}/actions",json=payload)
        else: await client.post(f"/v1/sessions/{first['session_id']}/actions",json=payload)
        assert runtime.store.active_uows==0 and not runtime.store.any_session_lock_held
        second,_=await admit(client,key="guard.second")
        result=await client.post(f"/v1/sessions/{second['session_id']}/actions",json=payload)
        assert result.status_code==200 and result.json()["state_changed"],result.text
        assert provider.calls==2


async def test_native_validated_resume_and_committed_replay_do_not_render_twice(monkeypatch):
    from deviation_protocol.infrastructure.deterministic_narrative import DeterministicDemoNarrativeProvider
    class Provider(DeterministicDemoNarrativeProvider):
        calls=0
        async def generate(self,request):
            self.calls+=1; return await super().generate(request)
    provider=Provider(); runtime=build_demo_runtime(provider=provider)
    native=runtime.services.turn_orchestrator._DemoNarrativeDispatcher__native
    finalize=native._finalize
    async def fail(*args): raise RuntimeError("after validated proposal")
    app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        entry,_=await admit(client)
        url=f"/v1/sessions/{entry['session_id']}/actions"
        payload={"turn_id":"resume.turn","client_request_id":"resume.request","action_type":"CUSTOM","description":"我举手示意。"}
        monkeypatch.setattr(native,"_finalize",fail)
        assert (await client.post(url,json=payload)).status_code==500
        monkeypatch.setattr(native,"_finalize",finalize)
        for key,job in runtime.store._narrative_jobs.items():
            runtime.store._narrative_jobs[key]=job.model_copy(update={"lease_expires_at":job.created_at})
        response=await client.post(url,json=payload)
        assert response.status_code==200 and response.json()["state_changed"],response.text
        before=runtime.store.snapshot()
        assert (await client.post(url,json=payload)).json()==response.json()
        assert runtime.store.snapshot()==before and provider.calls==1


async def test_native_duplicate_concurrency_and_commit_acknowledgement_replay(monkeypatch):
    from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork
    runtime=build_demo_runtime(); app=create_app(services=runtime.services); app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
        entry,request=await admit(client)
        before=runtime.store.snapshot()
        replies=await asyncio.gather(*(client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"native.demo"}) for _ in range(4)))
        assert all(r.status_code==200 and r.json()==entry for r in replies)
        assert runtime.store.snapshot()==before
        created=await client.post("/v1/player-characters",headers={"Idempotency-Key":"ack.character"},json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
        request=body(created.json()["player_character_id"]["value"])
        original=DemoUnitOfWork.commit
        async def lost(self):
            await original(self)
            raise RuntimeError("acknowledgement lost")
        with monkeypatch.context() as patch:
            patch.setattr(DemoUnitOfWork,"commit",lost)
            assert (await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"ack.entry"})).status_code==500
        committed=runtime.store.snapshot()
        recovered=await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"ack.entry"})
        assert recovered.status_code==200 and runtime.store.snapshot()==committed
        assert len(committed.run_protocol_bindings)==2 and len(committed.run_entry_world_bindings)==2
