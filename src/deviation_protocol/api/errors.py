from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from deviation_protocol.application.errors import (
    CandidateStateInvalidError,
    IdempotencyConflictError,
    InvalidCharacterDefinitionError,
    InvalidScenarioDefinitionError,
    PlayerCharacterNotFoundError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
    SnapshotInvalidError,
    SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
    StoredTurnResponseInvalidError,
    UnsupportedResolutionError,
    NarrativeJobActiveError,
    NarrativeJobStaleError,
    NarrativeOutcomeUnknownError,
    NarrativeOutcomeUnavailableError,
    NarrativeProviderNotConfiguredError,
    NarrativeRequestNotFoundError,
)
from deviation_protocol.application.narrative_models import NarrativeBoundaryError
from deviation_protocol.domain.state import DomainRuleViolation
from deviation_protocol.infrastructure.errors import OptimisticLockError


logger = logging.getLogger(__name__)


def error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"error_code": error_code, "message": message}},
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _: Request, __: RequestValidationError
    ) -> JSONResponse:
        return error_response(422, "REQUEST_VALIDATION_FAILED", "Request validation failed")

    @app.exception_handler(SessionNotFoundError)
    async def not_found_handler(_: Request, __: SessionNotFoundError) -> JSONResponse:
        return error_response(404, "SESSION_NOT_FOUND", "Session was not found")

    @app.exception_handler(PlayerCharacterNotFoundError)
    async def player_character_not_found_handler(
        _: Request, __: PlayerCharacterNotFoundError
    ) -> JSONResponse:
        return error_response(
            404,
            "PLAYER_CHARACTER_NOT_FOUND",
            "Player character was not found",
        )

    @app.exception_handler(NarrativeRequestNotFoundError)
    async def narrative_request_not_found_handler(
        _: Request, __: NarrativeRequestNotFoundError
    ) -> JSONResponse:
        return error_response(
            404,
            "NARRATIVE_REQUEST_NOT_FOUND",
            "Narrative request was not found",
        )

    @app.exception_handler(InvalidCharacterDefinitionError)
    async def invalid_character_handler(
        _: Request, __: InvalidCharacterDefinitionError
    ) -> JSONResponse:
        return error_response(
            422,
            "INVALID_CHARACTER_DEFINITION",
            "Character definition is not available",
        )

    @app.exception_handler(InvalidScenarioDefinitionError)
    async def invalid_scenario_handler(
        _: Request, __: InvalidScenarioDefinitionError
    ) -> JSONResponse:
        return error_response(
            422,
            "INVALID_SCENARIO_DEFINITION",
            "Scenario definition is not available",
        )

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_handler(_: Request, __: IdempotencyConflictError) -> JSONResponse:
        return error_response(409, "IDEMPOTENCY_CONFLICT", "Idempotency key was reused")

    @app.exception_handler(OptimisticLockError)
    async def optimistic_lock_handler(_: Request, __: OptimisticLockError) -> JSONResponse:
        return error_response(409, "OPTIMISTIC_LOCK_CONFLICT", "State changed concurrently")

    @app.exception_handler(NarrativeJobActiveError)
    async def narrative_active_handler(
        _: Request, __: NarrativeJobActiveError
    ) -> JSONResponse:
        return error_response(409, "NARRATIVE_JOB_ACTIVE", "A narrative turn is active")

    narrative_conflicts = (
        NarrativeJobStaleError,
        NarrativeOutcomeUnknownError,
        NarrativeOutcomeUnavailableError,
    )

    async def narrative_conflict_handler(_: Request, exc: Exception) -> JSONResponse:
        return error_response(
            409,
            getattr(exc, "code", "NARRATIVE_CONFLICT"),
            "Narrative turn cannot be committed",
        )

    for error_type in narrative_conflicts:
        app.add_exception_handler(error_type, narrative_conflict_handler)

    @app.exception_handler(NarrativeProviderNotConfiguredError)
    async def provider_not_configured_handler(
        _: Request, __: NarrativeProviderNotConfiguredError
    ) -> JSONResponse:
        return error_response(
            503,
            "NARRATIVE_PROVIDER_NOT_CONFIGURED",
            "Narrative provider is not configured",
        )

    @app.exception_handler(NarrativeBoundaryError)
    async def narrative_boundary_handler(
        _: Request, exc: NarrativeBoundaryError
    ) -> JSONResponse:
        return error_response(503, exc.code, "Narrative processing failed")

    incompatible_errors = (
        SnapshotContentVersionMismatchError,
        SnapshotSchemaVersionMismatchError,
        SnapshotStateVersionMismatchError,
        SnapshotInvalidError,
        SnapshotNotFoundError,
        SnapshotSessionMismatchError,
        CandidateStateInvalidError,
        StoredTurnResponseInvalidError,
        UnsupportedResolutionError,
    )

    async def incompatible_handler(request: Request, exc: Exception) -> JSONResponse:
        del request
        code = getattr(exc, "code", "SESSION_STATE_INCOMPATIBLE")
        return error_response(409, code, "Session state is unavailable or incompatible")

    for error_type in incompatible_errors:
        app.add_exception_handler(error_type, incompatible_handler)

    @app.exception_handler(DomainRuleViolation)
    async def domain_handler(_: Request, exc: DomainRuleViolation) -> JSONResponse:
        return error_response(400, exc.code.value.upper(), "Action violates a domain rule")

    @app.exception_handler(Exception)
    async def unknown_handler(request: Request, exc: Exception) -> JSONResponse:
        del request
        # Never copy exception text or a traceback into logs at this public edge;
        # database URLs, SQL parameters and local paths can be present there.
        logger.error("Unhandled API error type=%s", type(exc).__name__)
        return error_response(500, "INTERNAL_SERVER_ERROR", "Internal server error")
