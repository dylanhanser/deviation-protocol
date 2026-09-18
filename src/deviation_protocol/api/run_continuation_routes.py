"""Strict Session-scoped native lifecycle intent and safe status projections."""
from copy import deepcopy
import json

from fastapi import Depends, Request

from deviation_protocol.api.dependencies import get_api_services, get_current_principal
from deviation_protocol.api.errors import error_response
from deviation_protocol.api.schemas import NativeRunContinuationRequest, NativeRunContinuationStatusResponse, NativeRunContinuationResultResponse
from deviation_protocol.application.run_continuation_service import RunContinuationCommand, RunContinuationError
from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError, NativeRunAdmissionLockError, RunWriteConflictError
from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
from deviation_protocol.infrastructure.run_persistence import RunStoredRecordIntegrityError
from deviation_protocol.application.errors import (SnapshotInvalidError, SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError, SnapshotStateVersionMismatchError,
    SnapshotSessionMismatchError, SnapshotContentVersionMismatchError)


def install_run_continuation_routes(app):
    from deviation_protocol.api.main import (
        SessionPathId, _public_error_responses, _validate_run_entry_transport,
        _request_validation_failure, _reject_duplicate_json_members,
    )

    async def invoke(service, principal, session_id, command=None):
        if service is None:
            return error_response(503, "RUN_CONTINUATION_NOT_AVAILABLE", "Run continuation is not available")
        try:
            result = (await service.status(principal, session_id=session_id) if command is None
                else await service.continue_run(principal, session_id=session_id, command=command))
            return (NativeRunContinuationStatusResponse if command is None else NativeRunContinuationResultResponse).model_validate(result)
        except RunContinuationError as error:
            return error_response(409, error.code, "Run continuation cannot be performed")
        except NativeRunAdmissionOutcomeUnknownError:
            return error_response(503, "RUN_CONTINUATION_OUTCOME_UNKNOWN", "Run continuation outcome is unknown")
        except (NativeRunAdmissionLockError, RunWriteConflictError):
            return error_response(409, "RUN_CONTINUATION_CONFLICT", "Run continuation conflicts with current state")
        except (RunProtocolBindingStoredIntegrityError, RunStoredRecordIntegrityError,
                SnapshotInvalidError, SnapshotNotFoundError, SnapshotSchemaVersionMismatchError,
                SnapshotStateVersionMismatchError, SnapshotSessionMismatchError, SnapshotContentVersionMismatchError):
            return error_response(409, "SNAPSHOT_INVALID", "Session state is unavailable or incompatible")

    @app.get("/v1/sessions/{session_id}/run-continuation", operation_id="get_native_run_continuation",
        response_model=NativeRunContinuationStatusResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def status(session_id: SessionPathId, request: Request,
                     principal=Depends(get_current_principal), services=Depends(get_api_services)):
        names = [name.lower() for name, _ in request.scope["headers"]]
        if any(names.count(name) > 1 for name in (b"content-type", b"content-length", b"transfer-encoding", b"idempotency-key")):
            _request_validation_failure()
        if request.scope["query_string"] or await request.body():
            _request_validation_failure()
        return await invoke(services.run_continuation_service, principal, session_id)

    @app.post("/v1/sessions/{session_id}/run-continuation", operation_id="continue_native_run",
        response_model=NativeRunContinuationResultResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
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
            body = NativeRunContinuationRequest.model_validate(value, strict=True)
        except (ValueError, UnicodeDecodeError):
            _request_validation_failure()
        command = RunContinuationCommand(public_operation_key=key, **body.model_dump())
        return await invoke(services.run_continuation_service, principal, session_id, command)

    default_openapi = app.openapi

    def openapi():
        schema = deepcopy(default_openapi())
        schema["components"]["schemas"]["NativeRunContinuationRequest"] = NativeRunContinuationRequest.model_json_schema()
        route = schema["paths"]["/v1/sessions/{session_id}/run-continuation"]["post"]
        route["requestBody"] = {"required": True, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/NativeRunContinuationRequest"}}}}
        route["parameters"] = [p for p in route.get("parameters", []) if p.get("in") != "header"]
        route["parameters"].append({"name": "Idempotency-Key", "in": "header", "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"}})
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
