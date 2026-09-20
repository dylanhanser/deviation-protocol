"""Public gameplay completion; no injected ending or disconnected completion store."""
from copy import deepcopy

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.unit.test_run_revisit_api import reach_hold, action, view


async def reach_archive(client, profile="difficulty.open-expedition", choice="seal", *, runtime=None, zero_fixture=False):
    history = await reach_hold(client, profile, runtime=runtime, zero_fixture=zero_fixture)
    held = history[-1]
    second = held["metadata"]["session_id"]
    body = dict(expected_run_state_version=4, expected_session_state_version=held["metadata"]["state_version"])
    response = await client.post(f"/v1/sessions/{second}/run-revisit", json=body,
                                headers={"Idempotency-Key": "completion.revisit"})
    assert response.status_code == 200, response.text
    revisit = response.json()
    third = revisit["session_id"]
    await action(client, third, "archive.observe", action_type="OBSERVE", description="核验封存记录")
    current = await view(client, third)
    if choice is not None:
        await action(client, third, "archive.choose", action_type="CHOOSE",
            decision_id=current["narrative_frame"]["decision_id"], choice_id="receipt_archive.action." + choice)
    return history, revisit, body, await view(client, third)


def prepared_job(job):
    """Strict valid job carrier; attaching it to an ended source is corruption."""
    from deviation_protocol.application.narrative_jobs import NarrativeJob, NarrativeJobStatus
    values = {name: getattr(job, name) for name in type(job).model_fields}
    values.update(status=NarrativeJobStatus.PREPARED, attempt_count=0, lease_token=None,
        lease_owner=None, lease_expires_at=None, validated_proposal=None,
        validated_proposal_digest=None, outcome_rule_id=None, accepted_narrative_text=None, error_code=None)
    return NarrativeJob.model_validate(values, strict=True)


@pytest.mark.parametrize("completed", [False, True])
async def test_r1_ended_live_jobs_reject_every_owned_reader_and_replay(completed):
    from deviation_protocol.application.narrative_jobs import LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION
    from deviation_protocol.domain.run import RunId
    from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    runtime = build_demo_runtime(); app = create_app(services=runtime.services); app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        history, regional, revisit_body, ended = await reach_archive(client, "difficulty.silent-hunting-ground")
        paths = (history[0]["session_id"], history[3]["session_id"], regional["session_id"])
        body = dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"])
        replays = [("/v1/runs/native", history[1], "native.demo"),
            (f"/v1/sessions/{paths[0]}/run-continuation", history[4], "journey.continue"),
            (f"/v1/sessions/{paths[1]}/run-revisit", revisit_body, "completion.revisit")]
        if completed:
            reply = await client.post(f"/v1/sessions/{paths[2]}/run-complete", json=body, headers={"Idempotency-Key": "r1.complete"})
            assert reply.status_code == 200, reply.text
        replays.append((f"/v1/sessions/{paths[2]}/run-complete", body, "r1.complete"))
        readers = [(sid, route) for sid in paths for route in ("view", "run-journey", "run-status", "run-completion", "run-continuation")]
        clean = runtime.store.snapshot()
        for sid, route in readers:
            reply = await client.get(f"/v1/sessions/{sid}/{route}")
            if route == "run-continuation":
                assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "RUN_CONTINUATION_NOT_AVAILABLE", reply.text
            else: assert reply.status_code == 200, (sid, route, reply.text)
        assert runtime.store.snapshot() == clean
        for source in paths:
            job = next(j for j in runtime.store._narrative_jobs.values() if j.session_id == source and j.prompt_schema_version != LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION)
            try:
                runtime.store._narrative_jobs[job.job_id] = prepared_job(job)
                before = runtime.store.snapshot()
                for sid, route in readers:
                    reply = await client.get(f"/v1/sessions/{sid}/{route}")
                    assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", (source, sid, route, reply.text)
                for route, request, key in replays:
                    reply = await client.post(route, json=request, headers={"Idempotency-Key": key})
                    assert reply.status_code == 409 and reply.json()["error"]["error_code"] == "SNAPSHOT_INVALID", reply.text
                async with runtime.services.run_completion_service.authority.session_service.uow_factory() as unit:
                    with pytest.raises(RunProtocolBindingStoredIntegrityError):
                        await unit.run_protocol_bindings.get_classified(run_id=RunId(value=regional["run_id"]))
                app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="unrelated", authentication_scheme="demo")
                for sid, route in readers:
                    reply = await client.get(f"/v1/sessions/{sid}/{route}")
                    assert reply.status_code == 404, reply.text
                app.dependency_overrides.clear()
                assert runtime.store.snapshot() == before
            finally:
                app.dependency_overrides.clear()
                runtime.store._narrative_jobs[job.job_id] = job
        assert runtime.store.snapshot() == clean


async def test_r1_active_archive_permits_valid_live_job():
    from deviation_protocol.application.narrative_jobs import LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION
    runtime = build_demo_runtime(); app = create_app(services=runtime.services); app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        history, regional, _, current = await reach_archive(client, "difficulty.silent-hunting-ground", choice=None)
        assert current["scenario_status"] == "ACTIVE"
        sid = regional["session_id"]
        job = next(j for j in runtime.store._narrative_jobs.values() if j.session_id == sid and j.prompt_schema_version != LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION)
        runtime.store._narrative_jobs[job.job_id] = prepared_job(job)
        before = runtime.store.snapshot()
        try:
            for path in (history[0]["session_id"], history[3]["session_id"], sid):
                for route in ("view", "run-journey", "run-status", "run-completion"):
                    reply = await client.get(f"/v1/sessions/{path}/{route}")
                    assert reply.status_code == 200, reply.text
            assert runtime.store.snapshot() == before
        finally: runtime.store._narrative_jobs[job.job_id] = job


@pytest.mark.parametrize("profile", ["difficulty.open-expedition", "difficulty.silent-hunting-ground", "difficulty.fragile-alliance"])
async def test_a01_a04_public_completion_and_immutable_history(profile):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        history, revisit, revisit_body, ended = await reach_archive(client, profile)
        first, second, third = history[0]["session_id"], history[3]["session_id"], revisit["session_id"]
        before = runtime.store.snapshot()
        views = [await view(client, sid) for sid in (first, second, third)]
        status = await client.get(f"/v1/sessions/{third}/run-completion")
        assert status.status_code == 200, status.text
        assert status.json()["can_complete"] is True
        assert status.json()["completion"] is None
        assert runtime.store.snapshot() == before

        body = dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"])
        result = await client.post(f"/v1/sessions/{third}/run-complete", json=body,
                                  headers={"Idempotency-Key": "complete.once"})
        assert result.status_code == 200, result.text
        assert result.json()["lifecycle_status"] == "completed"
        after = runtime.store.snapshot()
        assert after.sessions == before.sessions
        assert after.snapshots == before.snapshots
        assert after.events == before.events
        for sid, original in zip((first, second, third), views):
            assert await view(client, sid) == original
            status = await client.get(f"/v1/sessions/{sid}/run-status")
            assert status.status_code == 200, status.text
            assert status.json()["schema_version"] == "native-run-status/v2"
            assert status.json()["can_exit"] is False
            journey = await client.get(f"/v1/sessions/{sid}/run-journey")
            assert journey.status_code == 200, journey.text
            assert journey.json()["schema_version"] == "native-run-journey/v2"
            completion = await client.get(f"/v1/sessions/{sid}/run-completion")
            assert completion.status_code == 200, completion.text
            assert completion.json()["completion"] == result.json()["completion"]
        replay = await client.post(f"/v1/sessions/{third}/run-complete", json=body,
                                  headers={"Idempotency-Key": "complete.once"})
        assert replay.json() == result.json()
        for path, old_body, key, expected in (
            (f"{first}/run-continuation", history[4], "journey.continue", history[3]),
            (f"{second}/run-revisit", revisit_body, "completion.revisit", revisit),
        ):
            replay = await client.post("/v1/sessions/" + path, json=old_body, headers={"Idempotency-Key": key})
            assert replay.status_code == 200, replay.text
            assert replay.json() == expected
        assert runtime.store.snapshot() == after


async def test_a05_a06_old_receipts_after_later_admission_and_retirement():
    import json
    from tests.unit.test_run_exit_api import play_to_ending
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    actions=[];recording=True
    async def capture(response):
        if recording and response.request.url.path.endswith("/actions") and response.status_code==200:
            await response.aread();actions.append((response.request.url.path,json.loads(response.request.content),response.json()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test",event_hooks={"response":[capture]}) as client:
        history,regional,revisit_body,ended=await reach_archive(client,"difficulty.silent-hunting-ground")
        sid=regional["session_id"];body=dict(expected_run_state_version=5,expected_session_state_version=ended["metadata"]["state_version"])
        prefix=runtime.store.snapshot()
        completed=await client.post(f"/v1/sessions/{sid}/run-complete",json=body,headers={"Idempotency-Key":"replay.complete"})
        assert completed.status_code==200,completed.text
        recording=False
        async def replay_all():
            before=runtime.store.snapshot()
            for route,request,result in actions:
                reply=await client.post(route,json=request);assert reply.json()==result,reply.text
            for route,request,key,result in (
                ("/v1/runs/native",history[1],"native.demo",history[0]),
                (f'/v1/sessions/{history[0]["session_id"]}/run-continuation',history[4],"journey.continue",history[3]),
                (f'/v1/sessions/{history[3]["session_id"]}/run-revisit',revisit_body,"completion.revisit",regional),
                (f"/v1/sessions/{sid}/run-complete",body,"replay.complete",completed.json()),
            ):
                reply=await client.post(route,json=request,headers={"Idempotency-Key":key});assert reply.json()==result,reply.text
            assert runtime.store.snapshot()==before
        await replay_all()
        fresh=await client.post("/v1/runs/native",json=history[1],headers={"Idempotency-Key":"replay.fresh"})
        assert fresh.status_code==200,fresh.text
        fresh_id=fresh.json()["session_id"]
        await replay_all()
        ending,fresh_actions=await play_to_ending(client,fresh_id)
        assert fresh_actions and fresh_actions[0][1]["state_changed"]
        exit_body=dict(expected_run_state_version=3,expected_session_state_version=ending["metadata"]["state_version"])
        exited=await client.post(f"/v1/sessions/{fresh_id}/run-exit",json=exit_body,headers={"Idempotency-Key":"fresh.exit"})
        assert exited.status_code==200,exited.text
        retired=await client.post(f'/v1/player-characters/{history[1]["player_character_id"]}/retirement',
            json=dict(contract_version="structured-player-character/v1",expected_revision={"value":1},confirm_retirement=True),headers={"Idempotency-Key":"later.retire"})
        assert retired.status_code==200,retired.text
        await replay_all()
        assert (await client.post(f"/v1/sessions/{fresh_id}/run-exit",json=exit_body,headers={"Idempotency-Key":"fresh.exit"})).json()==exited.json()
        conflict=await client.post(f"/v1/sessions/{sid}/run-complete",json={**body,"expected_run_state_version":6},headers={"Idempotency-Key":"replay.complete"})
        assert conflict.status_code==409 and conflict.json()["error"]["error_code"]=="IDEMPOTENCY_CONFLICT",conflict.text

        # Synthetic retired-character/active-Run corruption, never a reachable
        # public lifecycle: restore only the old qualified prefix after the
        # real retirement above. Every completion entry must reject it.
        rid=regional["run_id"]
        runtime.store._run_current[rid]=prefix.run_current[rid]
        del runtime.store._run_revisions[(rid,6)]
        key=next(k for k,row in runtime.store._run_mutation_receipts.items() if row.run_id.value==rid and row.resulting_state_version==6)
        del runtime.store._run_mutation_receipts[key]
        corrupted=runtime.store.snapshot()
        for method,kwargs in (("GET",{}),("POST",dict(json=body,headers={"Idempotency-Key":"retired.new"}))):
            route="run-completion" if method=="GET" else "run-complete"
            response=await client.request(method,f"/v1/sessions/{sid}/{route}",**kwargs)
            if method=="GET":
                assert response.status_code==200 and response.json()["reason"]=="character_ineligible" and not response.json()["can_complete"],response.text
            else:
                assert response.status_code==409 and response.json()["error"]["error_code"]=="RUN_COMPLETION_NOT_AVAILABLE",response.text
        assert runtime.store.snapshot()==corrupted


async def test_a05_synthetic_zero_composure_has_no_completion_refill():
    from dataclasses import fields
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        _,regional,_,ended=await reach_archive(client,runtime=runtime,zero_fixture=True)
        sid=regional["session_id"]
        bundle=runtime.services.content_registry.resolve("receipt_archive","receipt-archive-1.0.0")
        fixture=bundle.validate_snapshot(runtime.store._snapshots[sid].state)
        fixture.grant_item(bundle.scenario_catalog.content_catalog,"item.death_certificate.audit_token",instance_id="synthetic.carry.token")
        fixture.credit_currency("credits",17)
        # The frozen packs declare no skills: only the empty skill/cooldown map
        # is supported. Do not invent a skill to claim production reachability.
        assert not bundle.scenario_catalog.content_catalog.skills and fixture.player.skills=={}
        runtime.store._snapshots[sid].state.clear();runtime.store._snapshots[sid].state.update(fixture.to_snapshot())
        before=runtime.store.snapshot()
        assert before.snapshots[sid].state["player"]["resources"]["composure"]["current"]==0
        reply=await client.post(f"/v1/sessions/{sid}/run-complete",json=dict(expected_run_state_version=5,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"zero.complete"})
        assert reply.status_code==200,reply.text
        after=runtime.store.snapshot()
        for field in fields(before):
            if field.name not in ("run_current","run_revisions","run_mutation_receipts"):
                assert getattr(before,field.name)==getattr(after,field.name),field.name


async def test_a02_defer_is_not_completion():
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        _, revisit, _, ended = await reach_archive(client, choice="defer")
        sid = revisit["session_id"]
        before = runtime.store.snapshot()
        status = await client.get(f"/v1/sessions/{sid}/run-completion")
        assert status.status_code == 200, status.text
        assert status.json()["reason"] == "ending_not_eligible"
        result = await client.post(f"/v1/sessions/{sid}/run-complete",
            json=dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"]),
            headers={"Idempotency-Key": "ineligible"})
        assert result.status_code == 409, result.text
        assert result.json()["error"]["error_code"] == "RUN_COMPLETION_NOT_AVAILABLE"
        assert runtime.store.snapshot() == before


@pytest.mark.parametrize("branch", ["hold", "release", "deadline"])
async def test_a02_public_ineligible_stages_leave_every_map_unchanged(branch):
    from tests.unit.test_native_demo import admit
    from tests.unit.test_run_exit_api import play_to_ending
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        async def unavailable(sid):
            before=runtime.store.snapshot()
            status=await client.get(f"/v1/sessions/{sid}/run-completion")
            assert status.status_code==200,status.text
            value=status.json();assert not value["can_complete"] and value["offer"] is None
            result=await client.post(f"/v1/sessions/{sid}/run-complete",json=dict(expected_run_state_version=value["run_state_version"],
                expected_session_state_version=value["path"]["session_state_version"]),headers={"Idempotency-Key":"unavailable."+sid})
            assert result.status_code==409 and result.json()["error"]["error_code"]=="RUN_COMPLETION_NOT_AVAILABLE",result.text
            assert runtime.store.snapshot()==before
        admitted,_=await admit(client,"difficulty.silent-hunting-ground" if branch=="deadline" else "difficulty.open-expedition")
        first=admitted["session_id"];await unavailable(first)
        ended,_=await play_to_ending(client,first);await unavailable(first)
        response=await client.post(f"/v1/sessions/{first}/run-continuation",json=dict(expected_run_state_version=3,
            expected_session_state_version=ended["metadata"]["state_version"]),headers={"Idempotency-Key":"negative.continue"})
        assert response.status_code==200,response.text
        second=response.json()["session_id"];await unavailable(first);await unavailable(second)
        if branch=="deadline":
            for index in range(20):
                current=await view(client,second)
                if current["scenario_status"]=="ENDED":break
                await action(client,second,f"deadline.{index}",action_type="CUSTOM",description="等待核验")
            assert (await view(client,second))["scenario_status"]=="ENDED"
        else:
            await action(client,second,"negative.observe",action_type="OBSERVE",description="核对收件台")
            await action(client,second,"negative.talk",action_type="TALK",target_ids=["scenario-npc-1"],dialogue="核对排程")
            current=await view(client,second)
            await action(client,second,"negative.choice",action_type="CHOOSE",decision_id=current["narrative_frame"]["decision_id"],choice_id="undelivered_receipt.action."+branch)
        await unavailable(second)
        if branch=="hold":
            current=await view(client,second)
            response=await client.post(f"/v1/sessions/{second}/run-revisit",json=dict(expected_run_state_version=4,
                expected_session_state_version=current["metadata"]["state_version"]),headers={"Idempotency-Key":"negative.revisit"})
            assert response.status_code==200,response.text
            third=response.json()["session_id"];await unavailable(third);await unavailable(second)


def test_a02_completion_openapi_and_closed_projection_inventory():
    app=create_app();schema=app.openapi()
    for path,verb,dto in (("run-completion","get","NativeRunCompletionStatusResponse"),("run-complete","post","NativeRunCompletionResultResponse")):
        route=schema["paths"]["/v1/sessions/{session_id}/"+path][verb]
        assert set(route["responses"])=={"200","404","409","422","500","503"}
        assert route["responses"]["200"]["content"]["application/json"]["schema"]=={"$ref":"#/components/schemas/"+dto}
        assert route["responses"]["422"]["content"]["application/json"]["schema"]=={"$ref":"#/components/schemas/ErrorResponse"}
        assert schema["components"]["schemas"][dto]["additionalProperties"] is False
    from deviation_protocol.api.schemas import NativeRunCompletionResultResponse, NativeRunCompletionStatusResponse
    assert set(NativeRunCompletionResultResponse.model_fields)=={"schema_version","source_session_id","source_session_state_version","run_id","resulting_run_state_version","lifecycle_status","run_context","visit","completion"}
    assert set(NativeRunCompletionStatusResponse.model_fields)=={"schema_version","session_id","run_id","run_state_version","lifecycle_status","run_context","path","current","can_complete","reason","offer","completion"}


async def test_a02_legacy_standalone_missing_and_strict_get_are_read_only():
    from tests.integration.test_mysql_run_entry_playthrough import _entry
    from tests.unit.test_demo_composition import _create_default_demo_session
    runtime=build_demo_runtime();app=create_app(services=runtime.services);app.state.api_services=runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        created=await client.post("/v1/player-characters",headers={"Idempotency-Key":"completion.legacy.character"},
            json=dict(contract_version="structured-player-character/v1",character_core={},narration_preferences={}))
        assert created.status_code==200,created.text
        entered=await _entry(client,key="completion.legacy",character_id=created.json()["player_character_id"]["value"])
        assert entered.status_code==200,entered.text
        standalone=await _create_default_demo_session(client,identity="completion.standalone")
        before=runtime.store.snapshot()
        for sid in (entered.json()["session_id"],standalone):
            for method,endpoint in (("GET","run-completion"),("POST","run-complete")):
                response=await client.request(method,f"/v1/sessions/{sid}/{endpoint}",**({} if method=="GET" else
                    dict(json=dict(expected_run_state_version=5,expected_session_state_version=0),headers={"Idempotency-Key":"completion.ineligible"})))
                assert response.status_code==409 and response.json()["error"]["error_code"]=="NATIVE_RUN_REQUIRED",response.text
            for kwargs in (dict(content=b"x"),dict(params={"x":"1"}),dict(headers=[("Content-Type","application/json"),("Content-Type","application/json")])):
                response=await client.request("GET",f"/v1/sessions/{sid}/run-completion",**kwargs)
                assert response.status_code==422,response.text
        assert (await client.get("/v1/sessions/missing/run-completion")).status_code==404
        assert runtime.store.snapshot()==before
