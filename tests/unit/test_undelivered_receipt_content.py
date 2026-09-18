from pathlib import Path
from copy import deepcopy
import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending

PACK=Path(__file__).parents[2]/"config/scenarios/undelivered_receipt_v1.json"


@pytest.mark.parametrize("clock,events,held,expected",[
    (39,("dispatch.held",),True,"receipt_held"),
    (39,("dispatch.released",),False,"dispatch_closed"),
    (39,("dispatch.held","dispatch.released"),True,"receipt_held"),
    (40,("dispatch.held",),True,"deadline_reached"),
    (40,("dispatch.released",),False,"deadline_reached"),
    (40,("dispatch.held","dispatch.released"),True,"deadline_reached"),
])
def test_independent_ending_priority_boundaries(clock,events,held,expected):
    definition=JsonScenarioCatalogLoader(PACK).load().scenarios[0]
    assert [(e.ending_id,e.priority) for e in definition.endings]==[
        ("undelivered_receipt.ending.deadline_reached",10),
        ("undelivered_receipt.ending.receipt_held",20),
        ("undelivered_receipt.ending.dispatch_closed",30)]
    runtime=ScenarioRuntimeState(scenario_id=definition.scenario_id,scenario_content_version=definition.content_version,
        current_phase_id=definition.phases[0].phase_id,current_location_id=definition.locations[0].location_id,
        threat_clocks={"dispatch_deadline":{"clock_id":"dispatch_deadline","value":clock}},
        mutable_fact_values={"undelivered_receipt.fact.dispatch_held":held})
    # Synthetic selector proof only: independently start from the same runtime
    # for each definition order; these simultaneous events are not public play.
    for endings in (definition.endings,tuple(reversed(definition.endings))):
        candidate=runtime.model_copy(deep=True)
        ordered=definition.model_copy(update={"endings":endings})
        DeterministicStoryDirector()._apply_ending(candidate,ordered,events)
        assert candidate.ending_id==f"undelivered_receipt.ending.{expected}"
        assert candidate.ending_status.value==("RESOLVED" if expected=="receipt_held" else "FAILED")


@pytest.mark.parametrize("profile",["difficulty.open-expedition","difficulty.fragile-alliance","difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("zero",[False,True])
async def test_public_zero_composure_carryover_and_actual_destination_deadline(profile,zero):
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        entry,request=await admit(client,profile)
        source=entry["session_id"]
        if zero:
            # Resource-only fixture; both endings are reached by real public play.
            runtime.store._snapshots[source].state["player"]["resources"]["composure"]["current"]=0
        ended,_=await play_to_ending(client,source)
        source_state=runtime.store.snapshot().snapshots[source].state
        result=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"deadline.continue"})
        assert result.status_code==200,result.text
        sid=result.json()["session_id"]
        initial=runtime.store.snapshot().snapshots[sid].state
        assert initial["player"]==source_state["player"]
        assert initial["scenario_runtime"]["threat_clocks"]["dispatch_deadline"]["value"]==(4 if ended["ending_status"]=="FAILED" else 0)
        objectives=entry["run_context"]["objectives"]
        expected_player=deepcopy(source_state["player"])
        expected_clock=initial["scenario_runtime"]["threat_clocks"]["dispatch_deadline"]["value"]
        for index in range(41):
            view=(await client.get(f"/v1/sessions/{sid}/view")).json()
            if view["scenario_status"]=="ENDED":break
            response=await client.post(f"/v1/sessions/{sid}/actions",json=dict(action_type="CUSTOM",description="在大厅等候，不改动回执与排程",
                turn_id=f"deadline.{index}",client_request_id=f"deadline.{index}"))
            assert response.status_code==200 and response.json()["state_changed"],response.text
            expected_clock=min(40,expected_clock+1+objectives["consequence_severity"]//50+objectives["conflict_intensity"]//50)
            resource=expected_player["resources"]["composure"]
            resource["current"]=max(0,resource["current"]-objectives["resource_pressure"]//50)
            actual=runtime.store.snapshot().snapshots[sid].state
            assert actual["scenario_runtime"]["threat_clocks"]["dispatch_deadline"]["value"]==expected_clock
            assert actual["player"]==expected_player
        assert view["scenario_status"]=="ENDED" and view["ending_status"]=="FAILED"
        state=runtime.store.snapshot().snapshots[sid].state
        assert state["scenario_runtime"]["ending_id"]=="undelivered_receipt.ending.deadline_reached"
        assert state["player_memory"]["scenario_records"][0]["status"]=="COMPLETED"
        assert (await client.get(f"/v1/sessions/{sid}/run-continuation")).json()["can_continue"] is False
        before=runtime.store.snapshot()
        unavailable=await client.post(f"/v1/sessions/{sid}/run-continuation",json=dict(expected_run_state_version=4,
            expected_session_state_version=view["metadata"]["state_version"]),headers={"Idempotency-Key":"no.third"})
        assert unavailable.status_code==409 and runtime.store.snapshot()==before
        exited=await client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=4,
            expected_session_state_version=view["metadata"]["state_version"]),headers={"Idempotency-Key":"deadline.exit"})
        assert exited.status_code==200 and exited.json()["run_state_version"]==5,exited.text
        fresh=await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"deadline.fresh"})
        assert fresh.status_code==200 and fresh.json()["run_context"]["run_id"]!=entry["run_context"]["run_id"],fresh.text


@pytest.mark.parametrize("profile",["difficulty.open-expedition","difficulty.fragile-alliance","difficulty.silent-hunting-ground"])
@pytest.mark.parametrize("boundary",["default","beneficial","adverse"])
@pytest.mark.parametrize("zero",[False,True])
async def test_public_permitted_objective_boundaries_complete_hold_and_exit(profile,boundary,zero):
    from tests.unit.test_native_run_entry_api import body
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        created=await client.post("/v1/player-characters",json=dict(contract_version="structured-player-character/v1",character_core={},narration_preferences={}),headers={"Idempotency-Key":"extreme.character"})
        options=(await client.get("/v1/run-entry-options")).json()
        selected=next(p for p in options["profiles"] if p["profile_ref"]["profile_id"]==profile)
        request=body(created.json()["player_character_id"]["value"])
        request["profile_ref"]=selected["profile_ref"]
        request["overrides"]=[] if boundary=="default" else [dict(parameter=r["parameter"],
            value=r["maximum" if (boundary=="adverse")!=(r["parameter"]=="social_trust") else "minimum"])
            for r in selected["override_rules"]]
        admitted=await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"extreme.admit"})
        assert admitted.status_code==200,admitted.text
        source=admitted.json()["session_id"]
        if zero:
            # Resource fixture only. No ending/runtime/visit evidence is injected.
            runtime.store._snapshots[source].state["player"]["resources"]["composure"]["current"]=0
        ended,_=await play_to_ending(client,source)
        source_store=runtime.store.snapshot()
        source_player=source_store.snapshots[source].state["player"]
        response=await client.post(f"/v1/sessions/{source}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"extreme.continue"})
        assert response.status_code==200,response.text
        sid=response.json()["session_id"]
        assert runtime.store.snapshot().snapshots[sid].state["player"]==source_player
        assert runtime.store.snapshot().player_character_current==source_store.player_character_current
        objectives=admitted.json()["run_context"]["objectives"]
        def clock():return runtime.store.snapshot().snapshots[sid].state["scenario_runtime"]["threat_clocks"]["dispatch_deadline"]["value"]
        before=clock()
        assert before==(0 if ended["ending_status"]=="RESOLVED" else 4)
        expected_player=deepcopy(source_player)
        for index,(action,bound) in enumerate(((dict(action_type="OBSERVE",description="核对收件台"),5),
            (dict(action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对发运排程"),7))):
            result=await client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id=f"extreme.{index}",client_request_id=f"extreme.{index}",**action))
            assert result.status_code==200 and result.json()["state_changed"],result.text
            assert 1<=clock()-before<=bound
            # Independent arithmetic, not the production policy under test.
            assert clock()-before==1+objectives["information_opacity"]//50+objectives["conflict_intensity"]//50+(
                (100-objectives["social_trust"])//50 if index==1 else 0)
            resource=expected_player["resources"]["composure"]
            resource["current"]=max(0,resource["current"]-objectives["resource_pressure"]//50)
            actual=runtime.store.snapshot().snapshots[sid].state
            assert actual["player"]==expected_player
            assert actual["scenario_runtime"]["current_location_id"]=="undelivered_receipt.dispatch_counter"
            assert "undelivered_receipt.clue.receipt_gap" in actual["scenario_runtime"]["discovered_clue_ids"]
            if index==1:assert "undelivered_receipt.clue.dispatch_schedule" in actual["scenario_runtime"]["discovered_clue_ids"]
            before=clock()
        view=(await client.get(f"/v1/sessions/{sid}/view")).json()
        assert view["scenario_status"]=="ACTIVE" and view["narrative_frame"]["decision_id"]
        held=await client.post(f"/v1/sessions/{sid}/actions",json=dict(turn_id="extreme.hold",client_request_id="extreme.hold",
            action_type="CHOOSE",decision_id=view["narrative_frame"]["decision_id"],choice_id="undelivered_receipt.action.hold"))
        assert held.status_code==200 and held.json()["state_changed"],held.text
        final=(await client.get(f"/v1/sessions/{sid}/view")).json()
        assert final["scenario_status"]=="ENDED" and final["ending_status"]=="RESOLVED"
        state=runtime.store.snapshot().snapshots[sid].state
        assert state["scenario_runtime"]["ending_id"]=="undelivered_receipt.ending.receipt_held"
        assert state["scenario_runtime"]["mutable_fact_values"]["undelivered_receipt.fact.dispatch_held"] is True
        assert state["player_memory"]["scenario_records"][0]["status"]=="COMPLETED"
        assert state["player"]==expected_player and clock()==before
        assert runtime.store.snapshot().snapshots[source]==source_store.snapshots[source]
        assert runtime.store.snapshot().player_character_current==source_store.player_character_current
        assert not (await client.get(f"/v1/sessions/{sid}/run-continuation")).json()["can_continue"]
        exited=await client.post(f"/v1/sessions/{sid}/run-exit",json=dict(expected_run_state_version=4,
            expected_session_state_version=final["metadata"]["state_version"]),headers={"Idempotency-Key":"extreme.exit"})
        assert exited.status_code==200 and exited.json()["run_state_version"]==5,exited.text
        fresh=await client.post("/v1/runs/native",json=request,headers={"Idempotency-Key":"extreme.fresh"})
        assert fresh.status_code==200 and fresh.json()["run_context"]["run_id"]!=admitted.json()["run_context"]["run_id"],fresh.text
