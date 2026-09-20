"""A12: independent processes execute public completion and replay the full store."""
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import pytest

ROOT=Path(__file__).parents[2]


def journey(seed,profile):
    env=os.environ.copy()
    for name in ("DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"):env.pop(name,None)
    env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",PYTHONUNBUFFERED="1",PYTHONHASHSEED=str(seed))
    child=subprocess.Popen([str(ROOT/".venv/Scripts/python.exe"),str(ROOT/"tests/e2e/support/native_world_continuation_child.py")],
        cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8")
    messages=queue.Queue()
    def reader():
        for line in child.stdout:messages.put(json.loads(line))
    threading.Thread(target=reader,daemon=True).start()
    trace=[]
    def send(method,path,body=None,key=None):
        request=dict(id=len(trace)+1,method=method,path=path,headers={"Content-Type":"application/json"})
        if body is not None:request["body"]=json.dumps(body,ensure_ascii=False)
        if key:request["headers"]["Idempotency-Key"]=key
        child.stdin.write(json.dumps(request,ensure_ascii=False)+"\n");child.stdin.flush()
        response=messages.get(timeout=30)
        assert response["id"]==request["id"] and response["status"]==200,response
        trace.append((request,response))
        return response["body"]
    try:
        ready=messages.get(timeout=30);assert ready["ready"]
        created=send("POST","/v1/player-characters",dict(contract_version="structured-player-character/v1",character_core={},narration_preferences={}),"e2e.character")
        request=dict(player_character_id=created["player_character_id"]["value"],expected_record_revision=1,
            profile_ref=dict(profile_id=profile,profile_version=1),entry_world=dict(entry_world_id="world.death_certificate",entry_world_version=1),
            overrides=[],presentation=dict(world_tone="balanced",reality_boundary="lawful",relationship_overlay="off"))
        entered=send("POST","/v1/runs/native",request,"e2e.entry");source=entered["session_id"]
        for index,step in enumerate(ready["actions"]):
            view=send("GET",f"/v1/sessions/{source}/view")
            if view["scenario_status"]=="ENDED":break
            action=dict(turn_id=f"e2e.turn.{index}",client_request_id=f"e2e.action.{index}",action_type=step["action_type"])
            if step["choice_id"]:action.update(choice_id=step["choice_id"],decision_id=view["narrative_frame"]["decision_id"])
            if step["description"]:action["description"]=step["description"]
            assert send("POST",f"/v1/sessions/{source}/actions",action)["state_changed"]
        ended=send("GET",f"/v1/sessions/{source}/view");assert ended["scenario_status"]=="ENDED"
        expected_class="RESOLVED" if profile=="difficulty.open-expedition" else "FAILED"
        assert ended["ending_status"]==expected_class
        command=dict(expected_run_state_version=3,expected_session_state_version=ended["metadata"]["state_version"])
        continued=send("POST",f"/v1/sessions/{source}/run-continuation",command,"e2e.continue");sid=continued["session_id"]
        assert continued["run_context"]==entered["run_context"]
        arrival=send("GET",f"/v1/sessions/{sid}/run-continuation")["arrival"]
        assert arrival["previous_ending_status"]==expected_class
        assert arrival["previous_ending_title"]==("规程已中断" if expected_class=="RESOLVED" else "记录成为现实")
        for index,action in enumerate((dict(action_type="OBSERVE",description="核对收件台"),dict(action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对发运排程"))):
            assert send("POST",f"/v1/sessions/{sid}/actions",dict(turn_id=f"e2e.destination.{index}",client_request_id=f"e2e.destination.{index}",**action))["state_changed"]
            assert send("GET",f"/v1/sessions/{sid}/run-continuation")["arrival"]==arrival
        status=send("GET",f"/v1/sessions/{sid}/run-continuation");assert status["predecessor"]["session_id"]==source
        assert send("GET",f"/v1/sessions/{source}/view")==ended
        view=send("GET",f"/v1/sessions/{sid}/view")
        assert send("POST",f"/v1/sessions/{sid}/actions",dict(turn_id="e2e.choice",client_request_id="e2e.choice",action_type="CHOOSE",
            decision_id=view["narrative_frame"]["decision_id"],choice_id="undelivered_receipt.action.hold"))["state_changed"]
        final=send("GET",f"/v1/sessions/{sid}/view");assert final["scenario_status"]=="ENDED"
        assert final["ending_status"]=="RESOLVED"
        offer=send("GET",f"/v1/sessions/{sid}/run-journey")
        assert offer["next_transition"]["kind"]=="regional_revisit"
        revisit_command=dict(expected_run_state_version=4,expected_session_state_version=final["metadata"]["state_version"])
        result=send("POST",f"/v1/sessions/{sid}/run-revisit",revisit_command,"e2e.revisit")
        archive=result["session_id"]
        assert send("POST",f"/v1/sessions/{archive}/actions",dict(action_type="OBSERVE",description="查看待核记录",
            turn_id="archive.observe",client_request_id="archive.observe"))["state_changed"]
        for path in (archive,sid,source,sid,archive):
            assert send("GET",f"/v1/sessions/{path}/run-journey")["current"]["session_id"]==archive
            send("GET",f"/v1/sessions/{path}/view")
        decision=send("GET",f"/v1/sessions/{archive}/view")
        assert send("POST",f"/v1/sessions/{archive}/actions",dict(action_type="CHOOSE",choice_id="receipt_archive.action.seal",
            decision_id=decision["narrative_frame"]["decision_id"],turn_id="archive.choose",client_request_id="archive.choose"))["state_changed"]
        final=send("GET",f"/v1/sessions/{archive}/view")
        assert final["ending_status"]=="RESOLVED"
        completion_command=dict(expected_run_state_version=5, expected_session_state_version=final["metadata"]["state_version"])
        assert send("GET",f"/v1/sessions/{archive}/run-completion")["can_complete"]
        completed=send("POST",f"/v1/sessions/{archive}/run-complete",completion_command,"e2e.complete")
        assert completed["resulting_run_state_version"]==6 and completed["lifecycle_status"]=="completed"
        for path in (archive,sid,source,sid,archive):
            assert send("GET",f"/v1/sessions/{path}/run-journey")["completion"]==completed["completion"]
            assert send("GET",f"/v1/sessions/{path}/run-completion")["completion"]==completed["completion"]
            send("GET",f"/v1/sessions/{path}/view")
        fresh=send("POST","/v1/runs/native",request,"e2e.fresh");assert fresh["run_context"]["run_id"]!=entered["run_context"]["run_id"]
        assert send("POST",f"/v1/sessions/{source}/run-continuation",command,"e2e.continue")==continued
        assert send("POST",f"/v1/sessions/{sid}/run-revisit",revisit_command,"e2e.revisit")==result
        assert send("POST",f'/v1/sessions/{fresh["session_id"]}/actions',dict(action_type="OBSERVE",description="查看环境",
            turn_id="fresh.observe",client_request_id="fresh.observe"))["state_changed"]
        assert send("POST",f"/v1/sessions/{archive}/run-complete",completion_command,"e2e.complete")==completed
        child.stdin.write(json.dumps(dict(id=9999,inspect=True))+"\n");child.stdin.flush()
        snapshot=messages.get(timeout=30)
        assert snapshot["id"]==9999
        assert snapshot["sha256"]==hashlib.sha256(json.dumps(snapshot["snapshot"],ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        child.stdin.close();assert child.wait(timeout=30)==0,child.stderr.read()
        return trace,snapshot
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)
        child.stdout.close();child.stderr.close()


@pytest.mark.parametrize("profile",["difficulty.open-expedition","difficulty.silent-hunting-ground"])
def test_a12_completion_has_complete_cross_process_identity(profile):
    first=journey(1,profile)
    second=journey(9173,profile)
    assert first==second
    if directory:=os.getenv("S7_COMPLETION_EVIDENCE_DIR"):
        # Optional external acceptance export; absent in ordinary test runs.
        output=Path(directory);output.mkdir(parents=True,exist_ok=True)
        for seed,value in ((1,first),(9173,second)):
            (output/f"{profile}.{seed}.json").write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")),encoding="utf-8")
