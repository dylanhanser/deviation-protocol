from copy import deepcopy
import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending

ARRIVAL_NOTICES = {
    "RESOLVED": "上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。",
    "FAILED": "上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。",
}


async def assert_public_arrival(client, sid, ended, expected_title):
    assert ended["presentation"]["ending"]["title"]==expected_title
    response=await client.get(f"/v1/sessions/{sid}/run-continuation")
    assert response.status_code==200,response.text
    expected=dict(previous_ending_status=ended["ending_status"],previous_ending_title=expected_title,
        entry_notice=ARRIVAL_NOTICES[ended["ending_status"]])
    assert response.json()["arrival"]==expected
    assert set(response.json())=={"schema_version","session_id","run_id","run_state_version","session_state_version",
        "lifecycle_status","can_continue","current_session_id","visit","predecessor","successor","arrival"}
    return expected


async def play_to_record_challenged(client,sid):
    from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS
    for index,step in enumerate(CANONICAL_ACTIONS):
        view=(await client.get(f"/v1/sessions/{sid}/view")).json()
        assert view["scenario_status"]!="ENDED",view
        action=dict(turn_id=f"challenge.{index}",client_request_id=f"challenge.{index}",action_type=step.action_type)
        if step.choice_id:
            action.update(decision_id=view["narrative_frame"]["decision_id"],choice_id=
                "death_certificate.action.final_disclose" if step.choice_id.endswith("final_suspend") else step.choice_id)
        if step.description:action["description"]=step.description
        response=await client.post(f"/v1/sessions/{sid}/actions",json=action)
        assert response.status_code==200 and response.json()["state_changed"],response.text
    view=(await client.get(f"/v1/sessions/{sid}/view")).json()
    assert view["scenario_status"]=="ENDED" and view["ending_status"]=="RESOLVED"
    return view


async def test_other_resolved_source_ending_is_publicly_playable_and_eligible():
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.open-expedition");sid=entered["session_id"]
        ended=await play_to_record_challenged(client,sid)
        assert runtime.store.snapshot().snapshots[sid].state["scenario_runtime"]["ending_id"]=="death_certificate.ending.record_challenged"
        assert (await client.get(f"/v1/sessions/{sid}/run-continuation")).json()["can_continue"]
        response=await client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"challenge.continue"})
        assert response.status_code==200,response.text
        assert runtime.store.snapshot().snapshots[response.json()["session_id"]].state["scenario_runtime"]["threat_clocks"]["dispatch_deadline"]["value"]==0
        sid=response.json()["session_id"]
        await assert_public_arrival(client,sid,ended,"记录已被质疑")
        action=await client.post(f"/v1/sessions/{sid}/actions",json=dict(action_type="OBSERVE",description="核对收件台",
            turn_id="arrival.challenge",client_request_id="arrival.challenge"))
        assert action.status_code==200 and action.json()["state_changed"]
        await assert_public_arrival(client,sid,ended,"记录已被质疑")


async def assert_foreign_continuation_is_opaque(client,app,principal,source,successor):
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    try:
        for foreign in (RequestPrincipal(player_id="foreign-player",authentication_scheme=principal.authentication_scheme),
                RequestPrincipal(player_id=principal.player_id,authentication_scheme="foreign-auth")):
            app.dependency_overrides[get_current_principal]=lambda:foreign
            for sid in (source,successor,"missing.session"):
                response=await client.get(f"/v1/sessions/{sid}/run-continuation")
                assert response.status_code==404,response.text
                assert set(response.json())=={"error"} and "predecessor" not in response.text
                response=await client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=3,
                    expected_session_state_version=0),headers={"Idempotency-Key":"foreign.continue"})
                assert response.status_code==404,response.text
    finally:app.dependency_overrides[get_current_principal]=lambda:principal


async def test_foreign_owner_controller_and_missing_session_reveal_no_edge():
    from deviation_protocol.api.dependencies import get_current_principal
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entered,_=await admit(client,"difficulty.silent-hunting-ground");sid=entered["session_id"]
        ended,_=await play_to_ending(client,sid)
        response=await client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"owner.continue"})
        assert response.status_code==200,response.text
        before=runtime.store.snapshot()
        await assert_foreign_continuation_is_opaque(client,app,get_current_principal(),sid,response.json()["session_id"])
        assert runtime.store.snapshot()==before


@pytest.mark.parametrize("profile",["difficulty.open-expedition","difficulty.fragile-alliance","difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("choice",["hold","release"])
async def test_public_continuation_action_history_exit_reentry(profile,choice):
    runtime=build_demo_runtime()
    app=create_app(services=runtime.services)
    app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        admitted,request=await admit(client,profile)
        sid=admitted["session_id"]
        status=await client.get(f"/v1/sessions/{sid}/run-continuation")
        assert status.status_code==200,status.text
        assert status.json()["predecessor"] is None and not status.json()["can_continue"]
        assert status.json()["arrival"] is None
        ended,actions=await play_to_ending(client,sid)
        old=runtime.store.snapshot()
        command=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        response=await client.post(f"/v1/sessions/{sid}/run-continuation",json=command,headers={"Idempotency-Key":"continue.one"})
        assert response.status_code==200,response.text
        continued=response.json()
        successor=continued["session_id"]
        assert successor!=sid and continued["run_context"]==admitted["run_context"]
        state=runtime.store.snapshot()
        assert state.snapshots[sid]==old.snapshots[sid] and state.sessions[sid]==old.sessions[sid]
        assert state.snapshots[successor].state["player"]==old.snapshots[sid].state["player"]
        assert state.player_character_current==old.player_character_current
        assert len(state.run_world_states)==2 and len(state.run_world_visits)==2 and len(state.run_world_positions)==1
        recovered=await client.get(f"/v1/sessions/{successor}/run-continuation")
        assert recovered.status_code==200,recovered.text
        assert recovered.json()["predecessor"]["session_id"]==sid
        title="规程已中断" if ended["ending_status"]=="RESOLVED" else "记录成为现实"
        await assert_public_arrival(client,successor,ended,title)
        assert (await client.get(f"/v1/sessions/{sid}/run-continuation")).json()["arrival"] is None
        assert (await client.get(f"/v1/sessions/{sid}/view")).json()==ended
        assert not (await client.get(f"/v1/sessions/{sid}/run-status")).json()["can_exit"]
        view=await client.get(f"/v1/sessions/{successor}/view")
        assert view.status_code==200,view.text
        assert view.json()["run_context"]==admitted["run_context"]
        for index,action in enumerate((dict(action_type="OBSERVE",description="核对收件台"),
            dict(action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对发运排程"))):
            response=await client.post(f"/v1/sessions/{successor}/actions",json=dict(turn_id=f"destination.{index}",client_request_id=f"destination.{index}",**action))
            assert response.status_code==200 and response.json()["state_changed"],response.text
            await assert_public_arrival(client,successor,ended,title)
        view=(await client.get(f"/v1/sessions/{successor}/view")).json()
        response=await client.post(f"/v1/sessions/{successor}/actions",json=dict(turn_id="destination.choice",client_request_id="destination.choice",
            action_type="CHOOSE",decision_id=view["narrative_frame"]["decision_id"],choice_id=f"undelivered_receipt.action.{choice}"))
        assert response.status_code==200 and response.json()["state_changed"],response.text
        final=(await client.get(f"/v1/sessions/{successor}/view")).json()
        assert final["scenario_status"]=="ENDED",final
        assert final["ending_status"]==("RESOLVED" if choice=="hold" else "FAILED")
        response=await client.post(f"/v1/sessions/{successor}/run-exit",json=dict(expected_run_state_version=4,
            expected_session_state_version=final["metadata"]["state_version"]),headers={"Idempotency-Key":"continued.exit"})
        assert response.status_code==200,response.text
        assert response.json()["run_state_version"]==5
        second=await client.post("/v1/runs/native",json=deepcopy(request),headers={"Idempotency-Key":"fresh.entry"})
        assert second.status_code==200,second.text
        assert second.json()["run_context"]["run_id"]!=admitted["run_context"]["run_id"]
        before=runtime.store.snapshot()
        assert (await client.post(f"/v1/sessions/{sid}/run-continuation",json=command,headers={"Idempotency-Key":"continue.one"})).json()==continued
        assert (await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"native.demo"})).json()==admitted
        for action,result in actions:
            assert (await client.post(f"/v1/sessions/{sid}/actions",json=action)).json()==result
        assert runtime.store.snapshot()==before
        await assert_public_arrival(client,successor,ended,title)


def test_arrival_is_required_nullable_closed_and_in_openapi():
    from deviation_protocol.api.schemas import NativeWorldArrivalResponse
    app=create_app(services=build_demo_runtime().services)
    schemas=app.openapi()["components"]["schemas"]
    assert "arrival" in schemas["NativeRunContinuationStatusResponse"]["required"]
    annotation=schemas["NativeWorldArrivalResponse"]
    assert set(annotation["properties"])=={"previous_ending_status","previous_ending_title","entry_notice"}
    assert annotation["additionalProperties"] is False
    for status,title in (("RESOLVED","规程已中断"),("RESOLVED","记录已被质疑"),("FAILED","记录成为现实")):
        value=dict(previous_ending_status=status,previous_ending_title=title,entry_notice=ARRIVAL_NOTICES[status])
        assert NativeWorldArrivalResponse.model_validate(value).model_dump()==value
        for key in value:
            missing=dict(value);missing.pop(key)
            with pytest.raises(ValueError):NativeWorldArrivalResponse.model_validate(missing)
        for change in ({"entry_notice":"模型生成说明"},{"previous_ending_status":"ACTIVE"},
                       {"previous_ending_title":"交叉结局"},{"seed":"private"}):
            with pytest.raises(ValueError):NativeWorldArrivalResponse.model_validate({**value,**change})
