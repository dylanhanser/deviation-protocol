"""Separate native entry transport; S4 owns admission and exact replay."""
from __future__ import annotations

from copy import deepcopy
import json

from fastapi import Depends, Request

from deviation_protocol.api.dependencies import get_api_services, get_current_principal
from deviation_protocol.api.errors import error_response
from deviation_protocol.api.schemas import NativeRunEntryRequest, NativeRunEntryResponse
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.public_run_protocol import (
    RunEntryOptionsResponse, project_entry_options, project_native_context,
)


def native_command(request, key):
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionCommand
    from deviation_protocol.domain import run_protocol as s1, run_protocol_resolution as s2
    from deviation_protocol.domain.entry_world import EntryWorldRefV1, EntryWorldId, EntryWorldVersion
    from deviation_protocol.domain.player_character import PlayerCharacterId, PlayerCharacterRevision
    ref = s1.RunProtocolProfileRefV1(profile_id=s1.RunProtocolProfileId(value=request.profile_ref.profile_id),
        profile_version=s1.RunProtocolProfileVersion(value=request.profile_ref.profile_version))
    return NativeRunAdmissionCommand(public_operation_key=key,
        player_character_id=PlayerCharacterId(value=request.player_character_id),
        expected_record_revision=PlayerCharacterRevision(value=request.expected_record_revision),
        protocol=s1.RunProtocolEnvelopeV1(schema_version="run-protocol-envelope/v1", profile_ref=ref,
            world_tone=s1.RunProtocolWorldTone(request.presentation.world_tone),
            reality_boundary=s1.RunProtocolRealityBoundary(request.presentation.reality_boundary),
            relationship_overlay=s1.RunProtocolRelationshipOverlay(request.presentation.relationship_overlay)),
        overrides=s2.RunProtocolOverrideProposalV1(profile_ref=ref, entries=tuple(s2.RunProtocolObjectiveOverrideV1(
            parameter=s2.ObjectiveParameterName(o.parameter), value=s2.ObjectiveParameterValue(value=o.value)) for o in request.overrides)),
        entry_world=EntryWorldRefV1(entry_world_id=EntryWorldId(value=request.entry_world.entry_world_id),
            entry_world_version=EntryWorldVersion(value=request.entry_world.entry_world_version)))


def project_success(result, command):
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionResult
    from deviation_protocol.domain.run import revalidate_run_model
    revalidate_run_model(result, NativeRunAdmissionResult)
    envelope = result.resolved_protocol.resolution_input.envelope
    if (result.applicable_character_reference.player_character_id != command.player_character_id
            or result.applicable_character_reference.record_revision != command.expected_record_revision
            or result.entry_world != command.entry_world or envelope != command.protocol
            or result.resolved_protocol.resolution_input.authorized_overrides.entries != tuple(sorted(
                command.overrides.entries, key=lambda e: list(type(e.parameter)).index(e.parameter)))):
        raise ValueError("inconsistent native admission response")
    return NativeRunEntryResponse(session_id=result.session_id, scenario_id=result.scenario_id,
        scenario_content_version=result.scenario_content_version, run_context=project_native_context(result))


_DECISIONS = {
    "AUTHORIZATION_FAILED": (404, "PLAYER_CHARACTER_NOT_FOUND", "Player character was not found"),
    "IDEMPOTENCY_CONFLICT": (409, "IDEMPOTENCY_CONFLICT", "Idempotency key was reused"),
    "PLAYER_CHARACTER_STALE": (409, "PLAYER_CHARACTER_STALE", "Player character revision is stale"),
    "PLAYER_CHARACTER_NOT_ELIGIBLE": (409, "PLAYER_CHARACTER_NOT_ELIGIBLE", "Player character is not eligible for Run entry"),
    "INVALID_PROTOCOL": (422, "INVALID_RUN_PROTOCOL", "Run settings are not available"),
    "INVALID_ENTRY_WORLD": (422, "INVALID_ENTRY_WORLD", "Entry world is not available"),
    "INVALID_SCENARIO_DEFINITION": (422, "INVALID_SCENARIO_DEFINITION", "Scenario definition is not available"),
    "RUN_ENTRY_CONFLICT": (409, "RUN_ENTRY_CONFLICT", "Run entry conflicts with current state"),
}


def install_run_protocol_routes(app):
    from deviation_protocol.api.opening_talent_routes import install_opening_talent_routes
    install_opening_talent_routes(app)
    from deviation_protocol.api.main import (
        _public_error_responses, _validate_run_entry_transport,
        _request_validation_failure, _reject_duplicate_json_members, _openapi_schema_values_match,
    )

    @app.get("/v1/run-entry-options", operation_id="get_run_entry_options",
        response_model=RunEntryOptionsResponse, responses=_public_error_responses(422, 500), tags=["runs"])
    async def options(http_request: Request, services=Depends(get_api_services)):
        if http_request.scope["query_string"] or await http_request.body():
            _request_validation_failure()
        return project_entry_options(services.session_service, services.session_service.native_view_coordinator
            if services.native_run_admission_service is not None else None)

    @app.post("/v1/runs/native", operation_id="enter_native_run", response_model=NativeRunEntryResponse,
        responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def enter(http_request: Request, principal: RequestPrincipal = Depends(get_current_principal),
                    services=Depends(get_api_services)):
        if http_request.scope["query_string"]:
            _request_validation_failure()
        key = _validate_run_entry_transport(http_request, http_request.headers.get("idempotency-key", ""))
        raw = bytearray()
        async for chunk in http_request.stream():
            raw.extend(chunk)
            if len(raw) > 4096:
                _request_validation_failure()
        try:
            decoded = bytes(raw).decode("utf-8")
            json.loads(decoded, object_pairs_hook=_reject_duplicate_json_members)
            request = NativeRunEntryRequest.model_validate_json(decoded)
        except (ValueError, UnicodeDecodeError):
            _request_validation_failure()
        service = services.native_run_admission_service
        if service is None:
            return error_response(503, "NATIVE_RUN_ENTRY_NOT_AVAILABLE", "Native Run entry is not available")
        from deviation_protocol.application.native_run_admission import NativeRunAdmissionResult, NativeRunAdmissionDecision
        from deviation_protocol.domain.run import revalidate_run_model
        command = native_command(request, key)
        result = await service.enter(principal, command=command)
        if type(result) is NativeRunAdmissionResult:
            return project_success(result, command)
        if type(result) is NativeRunAdmissionDecision:
            revalidate_run_model(result, NativeRunAdmissionDecision)
            return error_response(*_DECISIONS[result.code.value])
        raise RuntimeError("unexpected native admission result")

    default_openapi = app.openapi

    def openapi():
        schema = deepcopy(default_openapi())
        request = NativeRunEntryRequest.model_json_schema(ref_template="#/components/schemas/{model}")
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for name, value in request.pop("$defs", {}).items():
            if name in components and not _openapi_schema_values_match(components[name], value):
                raise ValueError("native OpenAPI component conflict")
            components[name] = value
        components["NativeRunEntryRequest"] = request
        route = schema["paths"]["/v1/runs/native"]["post"]
        route["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/NativeRunEntryRequest"}}}}
        route["parameters"] = [{"name": "Idempotency-Key", "in": "header", "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"}}]
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
