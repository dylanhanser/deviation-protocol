"""Strict Session-scoped native lifecycle intent and safe status projections."""
from copy import deepcopy
import json

from fastapi import Depends, Request

from deviation_protocol.api.dependencies import get_api_services, get_current_principal
from deviation_protocol.api.errors import error_response
from deviation_protocol.api.schemas import NativeRunExitRequest, NativeRunStatusResponse
from deviation_protocol.application.run_exit_service import RunExitCommand, RunExitError
from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError, NativeRunAdmissionLockError, RunWriteConflictError
from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
from deviation_protocol.infrastructure.run_persistence import RunStoredRecordIntegrityError
from deviation_protocol.application.errors import (SnapshotInvalidError, SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError, SnapshotStateVersionMismatchError,
    SnapshotSessionMismatchError, SnapshotContentVersionMismatchError)


def install_run_exit_routes(app):
    from deviation_protocol.api.main import (
        SessionPathId, _public_error_responses, _validate_run_entry_transport,
        _request_validation_failure, _reject_duplicate_json_members,
    )

    async def invoke(service, principal, session_id, command=None):
        if service is None:
            return error_response(503, "RUN_EXIT_NOT_AVAILABLE", "Run exit is not available")
        try:
            result = (await service.status(principal, session_id=session_id) if command is None
                else await service.exit(principal, session_id=session_id, command=command))
            return NativeRunStatusResponse.model_validate(result)
        except RunExitError as error:
            return error_response(409, error.code, "Run exit cannot be performed")
        except NativeRunAdmissionOutcomeUnknownError:
            return error_response(503, "RUN_EXIT_OUTCOME_UNKNOWN", "Run exit outcome is unknown")
        except (NativeRunAdmissionLockError, RunWriteConflictError):
            return error_response(409, "RUN_EXIT_CONFLICT", "Run exit conflicts with current state")
        except (RunProtocolBindingStoredIntegrityError, RunStoredRecordIntegrityError,
                SnapshotInvalidError, SnapshotNotFoundError, SnapshotSchemaVersionMismatchError,
                SnapshotStateVersionMismatchError, SnapshotSessionMismatchError, SnapshotContentVersionMismatchError):
            return error_response(409, "SNAPSHOT_INVALID", "Session state is unavailable or incompatible")

    @app.get("/v1/sessions/{session_id}/run-status", operation_id="get_native_run_status",
        response_model=NativeRunStatusResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
    async def status(session_id: SessionPathId, request: Request,
                     principal=Depends(get_current_principal), services=Depends(get_api_services)):
        names = [name.lower() for name, _ in request.scope["headers"]]
        if any(names.count(name) > 1 for name in (b"content-type", b"content-length", b"transfer-encoding", b"idempotency-key")):
            _request_validation_failure()
        if request.scope["query_string"] or await request.body():
            _request_validation_failure()
        return await invoke(services.run_exit_service, principal, session_id)

    @app.post("/v1/sessions/{session_id}/run-exit", operation_id="exit_native_run",
        response_model=NativeRunStatusResponse, responses=_public_error_responses(404, 409, 422, 500, 503), tags=["runs"])
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
            body = NativeRunExitRequest.model_validate(value, strict=True)
        except (ValueError, UnicodeDecodeError):
            _request_validation_failure()
        command = RunExitCommand(public_operation_key=key, **body.model_dump())
        return await invoke(services.run_exit_service, principal, session_id, command)

    default_openapi = app.openapi

    def openapi():
        schema = deepcopy(default_openapi())
        schema["components"]["schemas"]["NativeRunExitRequest"] = NativeRunExitRequest.model_json_schema()
        route = schema["paths"]["/v1/sessions/{session_id}/run-exit"]["post"]
        route["requestBody"] = {"required": True, "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/NativeRunExitRequest"}}}}
        route["parameters"] = [p for p in route.get("parameters", []) if p.get("in") != "header"]
        route["parameters"].append({"name": "Idempotency-Key", "in": "header", "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"}})
        app.openapi_schema = schema
        return schema

    app.openapi = openapi
