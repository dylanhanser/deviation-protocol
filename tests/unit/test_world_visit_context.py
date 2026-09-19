from copy import copy
import json
import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.application import world_visit_context as context
from deviation_protocol.application.run_protocol_prompt_context import RunPromptContextError
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending


async def test_visit_attachment_is_bounded_private_authentic_and_compiled_outside_uow(monkeypatch):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    captured=[]
    original=context.compile_world_visit_context
    def compile(evidence,inputs,decision):
        assert runtime.store.active_uows==0 and not runtime.store.any_session_lock_held
        result=original(evidence,inputs,decision)
        captured.append((evidence,inputs,decision,result))
        return result
    monkeypatch.setattr(context,"compile_world_visit_context",compile)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground")
        source=entered["session_id"]
        ended,_=await play_to_ending(client,source)
        response=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"context.continue"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"]
        action=dict(turn_id="context.turn",client_request_id="context.action",action_type="OBSERVE",description="核对收件台")
        response=await client.post(f"/v1/sessions/{sid}/actions",json=action)
        assert response.status_code==200 and response.json()["state_changed"],response.text
        assert len(captured)==1
        evidence,inputs,decision,compiled=captured[0]
        assert compiled.validated_object()=={
            "schema":"world-visit-prompt-context/v1","world_title":"未送达的回执","region_title":"发运大厅","visit_ordinal":2,
            "previous_ending_status":"FAILED","previous_ending_title":"记录成为现实",
            "entry_notice":"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。"}
        assert len(compiled.data)<=2048
        literal='{"entry_notice":"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。","previous_ending_status":"FAILED","previous_ending_title":"记录成为现实","region_title":"发运大厅","schema":"world-visit-prompt-context/v1","visit_ordinal":2,"world_title":"未送达的回执"}'
        assert compiled.data==literal.encode("utf-8")
        jobs=[j for j in runtime.store.snapshot().narrative_jobs.values() if j.session_id==sid]
        assert len(jobs)==1 and jobs[0].narrative_request["schema"]=="native-visit-turn-request/v1"
        assert b"world-visit-prompt-context" not in json.dumps(jobs[0].narrative_request,ensure_ascii=False).encode()
        binding=json.loads(inputs.binding_bytes)
        assert binding["run_revision"]==4 and binding["visit_ordinal"]==2
        assert binding["world"]=={"world_id":"world.undelivered_receipt","world_version":1}
        assert binding["region"]=={"region_id":"region.undelivered_receipt.dispatch_hall","region_version":1}
        assert binding["entry_world"]=={"entry_world_id":{"value":"world.death_certificate"},"entry_world_version":{"value":1}}
        assert binding["scenario_id"]=="undelivered_receipt" and binding["scenario_content_version"]=="undelivered-receipt-1.0.0"
        from deviation_protocol.application.native_turn_mechanics import parse_job_request
        payload=jobs[0].narrative_request
        assert parse_job_request(payload)[1]==payload
        for field,value in (("run_revision",3),("run_revision",5),("visit_ordinal",True),("visit_id","crossed"),
                ("world",{"world_id":"world.undelivered_receipt","world_version":2}),
                ("region",{"region_id":"region.foreign","region_version":1}),("continuation_fingerprint",None)):
            bad=json.loads(json.dumps(payload));bad["binding"][field]=value
            with pytest.raises(ValueError):parse_job_request(bad)
        for version in ("native-turn-request/v1","native-visit-turn-request/v2"):
            with pytest.raises(ValueError):parse_job_request({**payload,"schema":version})
        for bad in ({},object(),object.__new__(context.DetachedWorldVisitEvidence)):
            with pytest.raises(RunPromptContextError):original(bad,inputs,decision)
        for field,value in (("binding",b"{}"),("snapshot",b"{}"),("ending_status","RESOLVED"),("ending_id","foreign")):
            changed=copy(evidence);object.__setattr__(changed,field,value)
            with pytest.raises(RunPromptContextError):original(changed,inputs,decision)
        changed=copy(compiled);object.__setattr__(changed,"data",b"{}")
        with pytest.raises(RunPromptContextError):changed.validated_object()
        before=runtime.store.snapshot()
        assert (await client.post(f"/v1/sessions/{sid}/actions",json=action)).json()==response.json()
        assert len(captured)==1 and runtime.store.snapshot()==before


async def test_regional_attachment_is_bounded_private_authentic_and_compiled_outside_uow(monkeypatch):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    captured=[]
    original=context.compile_regional_visit_context
    def compile(evidence,inputs,decision):
        assert runtime.store.active_uows==0 and not runtime.store.any_session_lock_held
        result=original(evidence,inputs,decision)
        captured.append((evidence,inputs,decision,result))
        return result
    monkeypatch.setattr(context,"compile_regional_visit_context",compile)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        from tests.unit.test_run_revisit_api import reach_hold
        *_,ended=await reach_hold(client,"difficulty.silent-hunting-ground")
        captured.clear()
        source=ended["metadata"]["session_id"]
        response=await client.post(f"/v1/sessions/{source}/run-revisit",json=dict(expected_run_state_version=4,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"context.revisit"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"]
        action=dict(turn_id="context.turn",client_request_id="context.action",action_type="OBSERVE",description="查看待核记录")
        response=await client.post(f"/v1/sessions/{sid}/actions",json=action)
        assert response.status_code==200 and response.json()["state_changed"],response.text
        assert len(captured)==1
        evidence,inputs,decision,compiled=captured[0]
        assert compiled.validated_object()=={
            "schema":"world-regional-prompt-context/v1","world_title":"未送达的回执","region_title":"核验档案室","visit_ordinal":3,
            "previous_ending_status":"RESOLVED","previous_ending_title":"回执待核，发运暂缓",
            "entry_notice":"会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。"}
        assert len(compiled.data)<=2048
        literal='{"entry_notice":"会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。","previous_ending_status":"RESOLVED","previous_ending_title":"回执待核，发运暂缓","region_title":"核验档案室","schema":"world-regional-prompt-context/v1","visit_ordinal":3,"world_title":"未送达的回执"}'
        assert compiled.data==literal.encode("utf-8")
        jobs=[j for j in runtime.store.snapshot().narrative_jobs.values() if j.session_id==sid]
        assert len(jobs)==1 and jobs[0].narrative_request["schema"]=="native-regional-turn-request/v1"
        assert b"world-regional-prompt-context" not in json.dumps(jobs[0].narrative_request,ensure_ascii=False).encode()
        binding=json.loads(inputs.binding_bytes)
        assert binding["run_revision"]==5 and binding["visit_ordinal"]==3
        assert binding["world"]=={"world_id":"world.undelivered_receipt","world_version":1}
        assert binding["region"]=={"region_id":"region.undelivered_receipt.verification_archive","region_version":1}
        assert binding["entry_world"]=={"entry_world_id":{"value":"world.death_certificate"},"entry_world_version":{"value":1}}
        assert binding["scenario_id"]=="receipt_archive" and binding["scenario_content_version"]=="receipt-archive-1.0.0"
        from deviation_protocol.application.native_turn_mechanics import parse_job_request
        payload=jobs[0].narrative_request
        assert parse_job_request(payload)[1]==payload
        for field,value in (("run_revision",3),("run_revision",4),("visit_ordinal",True),("visit_id","crossed"),
                ("world",{"world_id":"world.undelivered_receipt","world_version":2}),
                ("region",{"region_id":"region.foreign","region_version":1}),("regional_entry_fingerprint",None)):
            bad=json.loads(json.dumps(payload));bad["binding"][field]=value
            with pytest.raises(ValueError):parse_job_request(bad)
        for version in ("native-turn-request/v1","native-visit-turn-request/v2"):
            with pytest.raises(ValueError):parse_job_request({**payload,"schema":version})
        for bad in ({},object(),object.__new__(context.DetachedRegionalVisitEvidence)):
            with pytest.raises(RunPromptContextError):original(bad,inputs,decision)
        for field,value in (("binding",b"{}"),("snapshot",b"{}"),("ending_status","FAILED"),("ending_id","foreign"),("base_snapshot_sha256","a"*64),("entry_sha256","a"*64),("receipt_evidence_sha256","a"*64)):
            changed=copy(evidence);object.__setattr__(changed,field,value)
            with pytest.raises(RunPromptContextError):original(changed,inputs,decision)
        changed=copy(compiled);object.__setattr__(changed,"data",b"{}")
        with pytest.raises(RunPromptContextError):changed.validated_object()
        before=runtime.store.snapshot()
        assert (await client.post(f"/v1/sessions/{sid}/actions",json=action)).json()==response.json()
        assert len(captured)==1 and runtime.store.snapshot()==before
