"""Public native admission, View recovery and authored endings on real MySQL."""
import httpx
import pytest
import json
import sqlalchemy as sa
from types import SimpleNamespace
from unittest.mock import AsyncMock
from dataclasses import replace

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from tests.integration.test_mysql_native_run_admission import native_runtime, family_bytes
from tests.integration.test_mysql_native_turn_mechanics import Renderer, PROFILES, production_case, snapshot
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.domain.state import GameState
from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS
from tests.unit.test_native_run_entry_api import body

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("profile", PROFILES)
async def test_public_native_profile_journey(mysql_engine, monkeypatch, profile):
    async with native_runtime(mysql_engine) as case:
        monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        def services():
            result = main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
                authentication_scheme=case.runtime.principal.authentication_scheme,
                player_id=case.runtime.principal.player_id, controller_id=case.runtime.resolver.binding.value),))
            result.turn_orchestrator.narrative_provider = Renderer()
            return result
        runtime = services()
        app = main.create_app(services=runtime)
        app.state.api_services = runtime
        app.dependency_overrides[get_current_principal] = lambda: case.runtime.principal
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            options = await client.get("/v1/run-entry-options")
            assert options.status_code == 200
            assert options.json()["native_entry_available"] is True
            eligible = await client.get("/v1/player-characters/eligible-for-run-entry")
            assert eligible.status_code == 200, eligible.text
            assert case.runtime.character_ids[0].value in [p["player_character_id"]["value"] for p in eligible.json()["eligible_player_characters"]]
            request = body(case.runtime.character_ids[0].value)
            request["profile_ref"]["profile_id"] = profile
            headers = {"Idempotency-Key": "s6.public.entry"}
            admitted = await client.post("/v1/runs/native", json=request, headers=headers)
            assert admitted.status_code == 200, admitted.text
            data = admitted.json()
            session_id = data["session_id"]
            case.scope.run_ids.add(data["run_context"]["run_id"])
            case.scope.session_ids.add(session_id)
            before = await family_bytes(case)
            for index, step in enumerate(CANONICAL_ACTIONS):
                view_response = await client.get(f"/v1/sessions/{session_id}/view")
                assert view_response.status_code == 200, view_response.text
                view = view_response.json()
                assert view["run_context"] == data["run_context"]
                if view["scenario_status"] == "ENDED":
                    break
                action = dict(turn_id=f"s6.turn.{index}", client_request_id=f"s6.request.{index}", action_type=step.action_type)
                if step.choice_id:
                    action.update(decision_id=view["narrative_frame"]["decision_id"], choice_id=step.choice_id)
                if step.description:
                    action["description"] = step.description
                response = await client.post(f"/v1/sessions/{session_id}/actions", json=action)
                assert response.status_code == 200, response.text
                assert response.json()["state_changed"], (index, response.text)
                assert (await client.post(f"/v1/sessions/{session_id}/actions", json=action)).json() == response.json()
                app.state.api_services = services()
            final = await client.get(f"/v1/sessions/{session_id}/view")
            assert final.status_code == 200, final.text
            assert final.json()["scenario_status"] == "ENDED"
            assert final.json()["ending_status"] in {"RESOLVED", "FAILED"}
            assert final.json()["run_context"] == data["run_context"]
            async with case.factory() as session:
                stored = await session.scalar(sa.select(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id == session_id))
                assert stored.state_json["player_memory"]["scenario_records"]
                assert await session.scalar(sa.select(sa.func.count()).select_from(orm.DomainEventRow).where(orm.DomainEventRow.session_id == session_id)) > 1
            replay = await client.post("/v1/runs/native", json=request, headers=headers)
            assert replay.status_code == 200 and replay.json() == data
            after = await family_bytes(case)
            for table in before:
                if table.startswith(("run_", "player_character")):
                    assert before[table] == after[table]


@pytest.mark.parametrize("profile,current,charge,actual", [(PROFILES[0],6,0,0),(PROFILES[1],0,1,0),(PROFILES[1],6,1,1)])
async def test_public_resource_zero_and_positive_depletion(mysql_engine,monkeypatch,profile,current,charge,actual):
    async with production_case(mysql_engine,monkeypatch,profile) as case:
        sid=case.result.session_id
        if current == 0:
            async with case.factory.begin() as session:
                row=await session.scalar(sa.select(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id==sid))
                state=json.loads(json.dumps(row.state_json)); state["player"]["resources"]["composure"]["current"]=0; row.state_json=state
        before=(await snapshot(case)).state
        calls=[]; original=GameState.consume_resource
        def consume(self,resource,amount):
            calls.append((resource,amount)); return original(self,resource,amount)
        monkeypatch.setattr(GameState,"consume_resource",consume)
        app=main.create_app(services=case.services); app.state.api_services=case.services
        app.dependency_overrides[get_current_principal]=lambda:case.runtime.principal
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
            response=await client.post(f"/v1/sessions/{sid}/actions",json={"turn_id":"s6.resource","client_request_id":"s6.resource","action_type":"CUSTOM","description":"我尝试有规律地移动手指发出生命信号"})
            assert response.status_code==200 and response.json()["state_changed"],response.text
            assert (await client.get(f"/v1/sessions/{sid}/view")).status_code==200
        after=(await snapshot(case)).state
        assert after["player"]["resources"]["composure"]["current"]==current-actual
        assert after["scenario_runtime"]!=before["scenario_runtime"]
        assert calls==([("composure",actual)] if actual else [])
        async with case.factory() as session:
            events=(await session.scalars(sa.select(orm.DomainEventRow).where(orm.DomainEventRow.session_id==sid))).all()
            assert len([e for e in events if e.event_type=="RunProtocolResourceSpent"])==bool(actual)
            audit=next(e for e in events if e.event_type=="RunProtocolMechanicsApplied")
            assert audit.payload_json["resource"]["requested"]==charge
            assert audit.payload_json["resource"]["actual"]==actual


async def test_public_view_ownership_and_corruption_never_repairs(mysql_engine,monkeypatch):
    async with production_case(mysql_engine,monkeypatch) as case:
        app=main.create_app(services=case.services); app.state.api_services=case.services
        app.dependency_overrides[get_current_principal]=lambda:case.runtime.principal
        sid=case.result.session_id
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app,raise_app_exceptions=False),base_url="http://test") as client:
            before=await family_bytes(case)
            original=case.services.session_service.native_controller_resolver
            case.services.session_service.native_controller_resolver=SimpleNamespace(resolve=AsyncMock(return_value=None))
            denied=await client.get(f"/v1/sessions/{sid}/view")
            assert denied.status_code==404 and denied.json()["error"]["error_code"]=="SESSION_NOT_FOUND"
            case.services.session_service.native_controller_resolver=original
            app.dependency_overrides[get_current_principal]=lambda:case.scope.principal("foreign")
            assert (await client.get(f"/v1/sessions/{sid}/view")).json()==denied.json()
            assert await family_bytes(case)==before
            app.dependency_overrides[get_current_principal]=lambda:case.runtime.principal
            async with case.factory.begin() as session:
                row=await session.scalar(sa.select(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id==case.result.run_id.value))
                original_fingerprint=row.resolution_fingerprint; row.resolution_fingerprint=b"\x00"*32
            corrupt=await family_bytes(case)
            response=await client.get(f"/v1/sessions/{sid}/view")
            assert response.status_code==409 and response.json()["error"]["error_code"]=="SNAPSHOT_INVALID"
            assert await family_bytes(case)==corrupt
            async with case.factory.begin() as session:
                await session.execute(sa.update(orm.RunProtocolBindingRow).where(orm.RunProtocolBindingRow.run_id==case.result.run_id.value).values(resolution_fingerprint=original_fingerprint))
            assert await family_bytes(case)==before


@pytest.mark.parametrize("profile",PROFILES)
async def test_demo_and_production_native_semantic_delta_parity(mysql_engine,monkeypatch,profile):
    from deviation_protocol.api.demo_composition import build_demo_runtime
    from deviation_protocol.infrastructure.demo_generators import new_demo_generators
    from tests.unit.test_native_demo import admit
    async with production_case(mysql_engine,monkeypatch,profile) as case:
        async with case.factory() as session:
            row=await session.get(orm.GameSessionRow,case.result.session_id)
            seed=row.random_seed
        demo=build_demo_runtime(generators=replace(new_demo_generators(),seed=lambda:seed,session_id=lambda:case.result.session_id))
        demo_app=main.create_app(services=demo.services); demo_app.state.api_services=demo.services
        prod_app=main.create_app(services=case.services); prod_app.state.api_services=case.services
        prod_app.dependency_overrides[get_current_principal]=lambda:case.runtime.principal
        async with httpx.AsyncClient(transport=httpx.ASGITransport(demo_app),base_url="http://demo") as dc, httpx.AsyncClient(transport=httpx.ASGITransport(prod_app),base_url="http://production-test") as pc:
            entry,_=await admit(dc,profile)
            sid=entry["session_id"]
            payload={"turn_id":"parity.turn","client_request_id":"parity.request","action_type":"CUSTOM","description":"我举手示意。"}
            results=[await client.post(f"/v1/sessions/{sid}/actions",json=payload) for client in (dc,pc)]
            assert all(r.status_code==200 and r.json()["state_changed"] for r in results)
            demo_state=demo.store.snapshot().snapshots[sid].state
            prod_state=(await snapshot(case)).state
            assert demo_state["player"]["resources"]==prod_state["player"]["resources"]
            # Run/character/controller IDs and event issuers are adapter-specific.
            # Compare every gameplay runtime field; evidence identities remain local.
            evidence_fields={"applied_event_ids","narrative_outcome_evidence","decision_outcome_evidence"}
            assert {k:v for k,v in demo_state["scenario_runtime"].items() if k not in evidence_fields}=={k:v for k,v in prod_state["scenario_runtime"].items() if k not in evidence_fields}
            demo_audit=next(e.payload for e in demo.store.snapshot().events if e.event_type=="RunProtocolMechanicsApplied")
            async with case.factory() as session:
                prod_audit=await session.scalar(sa.select(orm.DomainEventRow).where(orm.DomainEventRow.session_id==sid,orm.DomainEventRow.event_type=="RunProtocolMechanicsApplied"))
                demo_payload=dict(demo_audit); prod_payload=dict(prod_audit.payload_json)
                assert demo_payload.pop("binding_digest")!=prod_payload.pop("binding_digest")
                assert demo_payload==prod_payload
