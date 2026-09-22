"""Versioned, allowlisted opening preparation transport."""
import json
from typing import Literal

from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from deviation_protocol.api.dependencies import get_api_services, get_current_principal
from deviation_protocol.api.errors import error_response
from deviation_protocol.api.schemas import NativeRunEntryRequest, NativeRunEntryResponse
from deviation_protocol.api.run_protocol_routes import native_command, project_success
from deviation_protocol.application.opening_preparation import OpeningPreparationService, PreparationRejected, decode_command, decode_result
from deviation_protocol.application.native_run_admission import NativeRunAdmissionCommand, NativeRunAdmissionResult
from deviation_protocol.domain.opening_talents import load_catalog


class TalentCard(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    name: str
    tier: Literal["TOP", "TRADEOFF", "ORDINARY", "WEAK"]
    description: str


class OpeningPreparationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["opening-preparation/v1"] = "opening-preparation/v1"
    preparation_id: str
    character_id: str
    catalog_version: str
    state: Literal["PENDING", "CONFIRMED"]
    admission: NativeRunEntryRequest
    candidates: list[TalentCard]
    selected_ids: list[str]
    result: NativeRunEntryResponse | None


class OpeningConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    character_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    catalog_version: Literal["opening-talents/v1"]
    selected_ids: list[str] = Field(min_length=2, max_length=2)


def projection(record):
    command = decode_command(record.command_json)
    catalog = {t.id: t for t in load_catalog(record.catalog_version)}
    def card(identity):
        t = catalog[identity]
        return TalentCard(id=t.id, name=t.name, tier=t.tier, description=t.description)
    envelope = command.protocol
    return OpeningPreparationResponse(preparation_id=record.preparation_id,
        character_id=record.character_id, catalog_version=record.catalog_version, state=record.state,
        admission=NativeRunEntryRequest.model_validate_json(json.dumps({
            "player_character_id": record.character_id,
            "expected_record_revision": command.expected_record_revision.value,
            "profile_ref": {"profile_id": envelope.profile_ref.profile_id.value,
                "profile_version": envelope.profile_ref.profile_version.value},
            "entry_world": {"entry_world_id": command.entry_world.entry_world_id.value,
                "entry_world_version": command.entry_world.entry_world_version.value},
            "presentation": {"world_tone": envelope.world_tone.value, "reality_boundary": envelope.reality_boundary.value,
                "relationship_overlay": envelope.relationship_overlay.value},
            "overrides": [{"parameter": e.parameter.value, "value": e.value.value} for e in command.overrides.entries]})),
        candidates=[card(t) for t in record.candidates], selected_ids=list(record.selections),
        result=None if record.result_json is None else project_success(
            decode_result(record.result_json, command), command))


def install_opening_talent_routes(app):
    from deviation_protocol.api.main import (
        _public_error_responses, _validate_run_entry_transport, _request_validation_failure,
        _reject_duplicate_json_members, SessionPathId, PlayerCharacterPathId, RequestPathId,
    )

    def service(services):
        if services.native_run_admission_service is None:
            raise PreparationRejected("NATIVE_RUN_ENTRY_NOT_AVAILABLE")
        return OpeningPreparationService(services.native_run_admission_service)

    async def body(request, model):
        if request.scope["query_string"]:
            _request_validation_failure()
        _validate_run_entry_transport(request, request.headers.get("idempotency-key", ""))
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 4096:
                _request_validation_failure()
        try:
            json.loads(raw, object_pairs_hook=_reject_duplicate_json_members)
            return model.model_validate_json(bytes(raw))
        except (ValueError, UnicodeDecodeError):
            _request_validation_failure()

    def rejected(error):
        code = error.code
        status = 404 if code == "PLAYER_CHARACTER_NOT_FOUND" else 422 if code.startswith("INVALID_") else 503 if code == "NATIVE_RUN_ENTRY_NOT_AVAILABLE" else 409
        return error_response(status, code, "Opening preparation is not available for this request")

    @app.post("/v1/opening-preparations", response_model=OpeningPreparationResponse,
        responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def prepare(http_request: Request, principal=Depends(get_current_principal), services=Depends(get_api_services)):
        request = await body(http_request, NativeRunEntryRequest)
        key = _validate_run_entry_transport(http_request, http_request.headers.get("idempotency-key", ""))
        try:
            return projection(await service(services).prepare(principal, native_command(request, key)))
        except PreparationRejected as error:
            return rejected(error)

    @app.get("/v1/player-characters/{character_id}/opening-preparation", response_model=OpeningPreparationResponse | None,
        responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def current(character_id: PlayerCharacterPathId, http_request: Request, principal=Depends(get_current_principal), services=Depends(get_api_services)):
        if http_request.scope["query_string"] or await http_request.body():
            _request_validation_failure()
        try:
            record = await service(services).get(principal, character_id)
            return None if record is None else projection(record)
        except PreparationRejected as error:
            return rejected(error)

    @app.post("/v1/opening-preparations/{preparation_id}/confirm", response_model=OpeningPreparationResponse,
        responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def confirm(preparation_id: RequestPathId, http_request: Request, principal=Depends(get_current_principal), services=Depends(get_api_services)):
        request = await body(http_request, OpeningConfirmationRequest)
        try:
            return projection(await service(services).confirm(principal, preparation_id, request.character_id,
                request.catalog_version, tuple(request.selected_ids)))
        except PreparationRejected as error:
            return rejected(error)

    @app.get("/v1/sessions/{session_id}/opening-talents", response_model=list[TalentCard],
        responses=_public_error_responses(404, 422, 500, 503), tags=["runs"])
    async def talents(session_id: SessionPathId, http_request: Request, principal=Depends(get_current_principal), services=Depends(get_api_services)):
        if http_request.scope["query_string"] or await http_request.body():
            _request_validation_failure()
        admission = services.native_run_admission_service
        if admission is None:
            return error_response(503, "NATIVE_RUN_ENTRY_NOT_AVAILABLE", "Native Run entry is not available")
        async with admission.uow_factory() as uow:
            session = await uow.sessions.get_owned_for_update(session_id, principal.player_id)
            if session is None:
                return error_response(404, "SESSION_NOT_FOUND", "Session was not found")
            participation = await uow.run_participations.get(session_id)
            if participation is None:
                return []
            from deviation_protocol.application.opening_preparation import load_run_talents
            family = await uow.run_protocol_bindings.get_classified(run_id=participation.run_id)
            record = await load_run_talents(uow, family, principal.player_id)
            if record is None:
                return []
            return [card for card in projection(record).candidates if card.id in record.selections]

    default_openapi = app.openapi

    def openapi():
        from copy import deepcopy
        from deviation_protocol.api.main import _openapi_schema_values_match
        schema = deepcopy(default_openapi())
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        for path, model in (("/v1/opening-preparations", NativeRunEntryRequest),
                            ("/v1/opening-preparations/{preparation_id}/confirm", OpeningConfirmationRequest)):
            definition = model.model_json_schema(ref_template="#/components/schemas/{model}")
            for name, value in definition.pop("$defs", {}).items():
                if name in components and not _openapi_schema_values_match(components[name], value):
                    raise ValueError("opening OpenAPI component conflict")
                components[name] = value
            components[model.__name__] = definition
            route = schema["paths"][path]["post"]
            route["requestBody"] = {"required": True, "content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/" + model.__name__}}}}
            route.setdefault("parameters", []).append({"name": "Idempotency-Key", "in": "header", "required": True,
                "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"}})
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
