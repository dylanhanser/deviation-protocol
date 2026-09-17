import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from deviation_protocol.api.main import create_app
from deviation_protocol.api.dependencies import get_current_principal
from deviation_protocol.application.native_turn_mechanics import NativeTurnMechanicsCoordinator
from tests.unit.test_native_run_admission import native_service_fixture


def body(character="character.golden"):
    return dict(player_character_id=character, expected_record_revision=1,
        profile_ref=dict(profile_id="difficulty.fragile-alliance", profile_version=1),
        entry_world=dict(entry_world_id="world.death_certificate", entry_world_version=1),
        overrides=[], presentation=dict(world_tone="balanced", reality_boundary="lawful", relationship_overlay="off"))


@pytest.fixture
def runtime():
    events = []
    service, unit, factory, legacy = native_service_fixture(events)
    session = service.session_service
    session.native_view_coordinator = NativeTurnMechanicsCoordinator(session.catalog, session.scenario_catalog)
    service = SimpleNamespace(enter=AsyncMock(wraps=service.enter))
    services = SimpleNamespace(session_service=session, native_run_admission_service=service,
        run_entry_service=None, player_character_service=None)
    app = create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: legacy.PRINCIPAL
    return app, service, unit, legacy, events


async def test_real_admission_once_and_public_cross_binding(runtime):
    app, service, unit, legacy, events = runtime
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        options = await client.get("/v1/run-entry-options")
        assert options.status_code == 200
        assert len(options.json()["profiles"]) == 3
        response = await client.post("/v1/runs/native", json=body(legacy.REFERENCE.player_character_id.value), headers={"Idempotency-Key": "native.test"})
        assert response.status_code == 200, response.text
        data = response.json()
        assert set(data) == {"session_id", "scenario_id", "scenario_content_version", "run_context"}
        assert data["run_context"]["objectives"] == dict(resource_pressure=60, social_trust=45, consequence_severity=65, information_opacity=60, conflict_intensity=60)
        assert data["run_context"]["resource_pressure_label"] == "Fluid"
        service.enter.assert_awaited_once()
        unit.commit.assert_awaited_once()


@pytest.mark.parametrize("kind", ["extra", "null", "bool", "float", "duplicate", "nested-duplicate", "large", "bom", "nan", "duplicate-key-header", "duplicate-content", "query", "off-step"])
async def test_transport_rejects_before_application(runtime, kind):
    app, service, *_ = runtime
    data = body()
    headers = [("Content-Type", "application/json"), ("Idempotency-Key", "native.test")]
    url = "/v1/runs/native"
    if kind == "extra": data["run_id"] = "forged"
    if kind in {"null", "bool", "float"}: data["expected_record_revision"] = {"null": None, "bool": True, "float": 1.0}[kind]
    if kind == "off-step": data["overrides"] = [{"parameter": "resource_pressure", "value": 61}]
    raw = json.dumps(data).encode()
    if kind == "duplicate": raw = b'{"overrides":[],' + raw[1:]
    if kind == "nested-duplicate": raw = raw.replace(b'"world_tone":', b'"world_tone":"grim","world_tone":')
    if kind == "large": raw += b" " * (4097 - len(raw))
    if kind == "bom": raw = b"\xef\xbb\xbf" + raw
    if kind == "nan": raw = raw.replace(b'"expected_record_revision": 1', b'"expected_record_revision": NaN')
    if kind == "duplicate-key-header": headers.append(("Idempotency-Key", "native.test"))
    if kind == "duplicate-content": headers.append(("Content-Type", "application/json"))
    if kind == "query": url += "?x=1"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        response = await client.post(url, content=raw, headers=headers)
    assert response.status_code == 422
    assert response.json() == {"error": {"error_code": "REQUEST_VALIDATION_FAILED", "message": "Request validation failed"}}
    service.enter.assert_not_awaited()


def test_openapi_has_exact_native_statuses(runtime):
    schema = runtime[0].openapi()
    native = schema["paths"]["/v1/runs/native"]["post"]
    assert native["operationId"] == "enter_native_run"
    assert set(native["responses"]) == {"200", "404", "409", "422", "500", "503"}
    assert native["requestBody"]["required"] is True
    assert "NativeRunAdmissionResult" not in schema["components"]["schemas"]


async def test_inclusive_transport_limit_and_discovery_rejection(runtime):
    app,service,_,legacy,_=runtime
    raw=json.dumps(body(legacy.REFERENCE.player_character_id.value)).encode()
    raw+=b" "*(4096-len(raw))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/runs/native",content=raw,headers={"Content-Type":"application/json; charset=utf-8","Idempotency-Key":"limit"})
        assert response.status_code==200,response.text
        for url,data in [("/v1/run-entry-options?x=1",b""),("/v1/run-entry-options",b"{}")]:
            assert (await client.request("GET",url,content=data)).status_code==422
    service.enter.assert_awaited_once()


@pytest.mark.parametrize("code,status",[("AUTHORIZATION_FAILED",404),("IDEMPOTENCY_CONFLICT",409),("PLAYER_CHARACTER_STALE",409),
    ("PLAYER_CHARACTER_NOT_ELIGIBLE",409),("INVALID_PROTOCOL",422),("INVALID_ENTRY_WORLD",422),("INVALID_SCENARIO_DEFINITION",422),("RUN_ENTRY_CONFLICT",409)])
async def test_exact_decision_mapping(runtime,code,status):
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionDecision,NativeRunAdmissionDecisionCode
    from deviation_protocol.api.run_protocol_routes import _DECISIONS
    app,service,*_=runtime
    service.enter=AsyncMock(return_value=NativeRunAdmissionDecision(code=NativeRunAdmissionDecisionCode(code)))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        response=await client.post("/v1/runs/native",json=body(),headers={"Idempotency-Key":"decision"})
    assert response.status_code==status
    assert response.json()=={"error":{"error_code":_DECISIONS[code][1],"message":_DECISIONS[code][2]}}


async def test_absent_service_still_validates_transport(runtime):
    app,*_=runtime
    app.state.api_services.native_run_admission_service=None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app),base_url="http://test") as client:
        assert (await client.post("/v1/runs/native",json={})).status_code==422
        response=await client.post("/v1/runs/native",json=body(),headers={"Idempotency-Key":"absent"})
        assert response.status_code==503
        options=(await client.get("/v1/run-entry-options")).json()
        assert options["native_entry_available"] is False and options["profiles"]==options["entry_worlds"]==[]
