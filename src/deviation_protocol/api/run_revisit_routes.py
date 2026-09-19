"""Strict Session-scoped native lifecycle intent and safe status projections."""
from copy import deepcopy
import json

from fastapi import Depends, Request

from deviation_protocol.api.dependencies import get_api_services, get_current_principal
from deviation_protocol.api.errors import error_response
from deviation_protocol.api.schemas import NativeRunRevisitRequest, NativeRunJourneyResponse, NativeRunRevisitResultResponse
from deviation_protocol.application.run_revisit_service import RunRevisitCommand, RunRevisitError
from deviation_protocol.application.ports import (NativeRunAdmissionOutcomeUnknownError,
    NativeRunAdmissionLockError, NativeRunAdmissionWriteConflictError, RunWriteConflictError,
    RunReceiptUniquenessConflictError, RunSessionParticipationUniquenessConflictError)
from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
from deviation_protocol.infrastructure.run_persistence import RunStoredRecordIntegrityError
from deviation_protocol.application.errors import (SnapshotInvalidError, SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError, SnapshotStateVersionMismatchError,
    SnapshotSessionMismatchError, SnapshotContentVersionMismatchError)


def install_run_revisit_routes(app):
    from deviation_protocol.api.main import (
        SessionPathId, _public_error_responses, _validate_run_entry_transport,
        _request_validation_failure, _reject_duplicate_json_members,
    )

    async def invoke(service, principal, session_id, command=None):
        if service is None:
            return error_response(503, "RUN_REVISIT_NOT_AVAILABLE", "Run regional revisit is not available")
        try:
            result = (await service.journey(principal, session_id=session_id) if command is None
                else await service.revisit(principal, session_id=session_id, command=command))
            return (NativeRunJourneyResponse if command is None else NativeRunRevisitResultResponse).model_validate(result)
        except RunRevisitError as error:
            return error_response(409, error.code, "Run regional revisit cannot be performed")
        except NativeRunAdmissionOutcomeUnknownError:
            return error_response(503, "RUN_REVISIT_OUTCOME_UNKNOWN", "Run regional revisit outcome is unknown")
        except (NativeRunAdmissionLockError, NativeRunAdmissionWriteConflictError, RunWriteConflictError,
                RunReceiptUniquenessConflictError, RunSessionParticipationUniquenessConflictError):
            return error_response(409, "RUN_REVISIT_CONFLICT", "Run regional revisit conflicts with current state")
        except (RunProtocolBindingStoredIntegrityError, RunStoredRecordIntegrityError,
                SnapshotInvalidError, SnapshotNotFoundError, SnapshotSchemaVersionMismatchError,
                SnapshotStateVersionMismatchError, SnapshotSessionMismatchError, SnapshotContentVersionMismatchError):
            return error_response(409, "SNAPSHOT_INVALID", "Session state is unavailable or incompatible")

    @app.get("/v1/sessions/{session_id}/run-journey", operation_id="get_native_run_journey",
        response_model=NativeRunJourneyResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def status(session_id: SessionPathId, request: Request,
                     principal=Depends(get_current_principal), services=Depends(get_api_services)):
        names = [name.lower() for name, _ in request.scope["headers"]]
        if any(names.count(name) > 1 for name in (b"content-type", b"content-length", b"transfer-encoding", b"idempotency-key")):
            _request_validation_failure()
        if request.scope["query_string"] or await request.body():
            _request_validation_failure()
        return await invoke(services.run_revisit_service, principal, session_id)

    @app.post("/v1/sessions/{session_id}/run-revisit", operation_id="revisit_native_region",
        response_model=NativeRunRevisitResultResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def exit_run(session_id: SessionPathId, request: Request,
                       principal=Depends(get_current_principal), services=Depends(get_api_services)):
        if request.scope["query_string"]:
            _request_validation_failure()
        key = _validate_run_entry_transport(request, request.headers.get("idempotency-key", ""))
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024:
                _request_validation_failure()
        try:
            decoded = bytes(raw).decode("utf-8")
            value = json.loads(decoded, object_pairs_hook=_reject_duplicate_json_members)
            body = NativeRunRevisitRequest.model_validate(value, strict=True)
        except (ValueError, UnicodeDecodeError):
            _request_validation_failure()
        command = RunRevisitCommand(public_operation_key=key, **body.model_dump())
        return await invoke(services.run_revisit_service, principal, session_id, command)

    default_openapi = app.openapi

    def openapi():
        schema = deepcopy(default_openapi())
        schema["components"]["schemas"]["NativeRunRevisitRequest"] = NativeRunRevisitRequest.model_json_schema()
        route = schema["paths"]["/v1/sessions/{session_id}/run-revisit"]["post"]
        route["requestBody"] = {"required": True, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/NativeRunRevisitRequest"}}}}
        route["parameters"] = [p for p in route.get("parameters", []) if p.get("in") != "header"]
        route["parameters"].append({"name": "Idempotency-Key", "in": "header", "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"}})
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
