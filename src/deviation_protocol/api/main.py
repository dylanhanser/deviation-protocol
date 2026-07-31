from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path as FilePath
import re
from typing import Annotated, Any, NoReturn

from fastapi import Depends, FastAPI, Header, Path, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
    get_player_character_service,
    get_session_service,
    get_turn_orchestrator,
)
from deviation_protocol.api.errors import install_exception_handlers
from deviation_protocol.api.schemas import (
    ActionRequest,
    ActionResponse,
    CreateSessionRequest,
    ErrorResponse,
    NarrativeRequestStatusResponse,
)
from deviation_protocol.application.errors import (
    IdempotencyConflictError,
    PlayerCharacterNotFoundError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CharacterCreationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationSuccessResult,
)
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.ports import (
    ControllerBindingResolver,
    TurnOrchestrator,
    UnitOfWorkFactory,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.run_service import RunService
from deviation_protocol.application.session_service import (
    PlayerVisibleStateProjection,
    PlayerSessionView,
    PublicScenarioCatalog,
    PublicNarrativeRequestStatus,
    SessionCreationResult,
    SessionMetadata,
    SessionService,
)
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.narrative_prompt import (
    PromptBuilder,
    default_style_profile,
)
from deviation_protocol.infrastructure.deepseek_narrative import (
    DeepSeekNarrativeProvider,
    DeepSeekSettings,
)
from deviation_protocol.infrastructure.database import create_engine, create_session_factory
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    PlayerCharacterId,
    PlayerCharacterOperationId,
)
from deviation_protocol.domain.run import RunAuthoritySourceRef
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.infrastructure.player_character_authority import (
    ConfiguredControllerBinding,
    ConfiguredControllerBindingResolver,
    Uuid4PlayerCharacterIdIssuer,
)
from deviation_protocol.infrastructure.run_authority import (
    Uuid4ContinuousStoryLineIdIssuer,
    Uuid4RunIdIssuer,
)
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCENARIO_PACK = (
    FilePath(__file__).parents[3]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
SessionPathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
RequestPathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
PlayerCharacterPathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
_PLAYER_CHARACTER_IDEMPOTENCY_KEY_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
)
PlayerCharacterIdempotencyKeyHeader = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
        pattern=_PLAYER_CHARACTER_IDEMPOTENCY_KEY_PATTERN.pattern,
    ),
]
_PLAYER_CHARACTER_CREATION_OPENAPI_EXTRA: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/CharacterCreationCommand",
                }
            }
        },
    }
}

_PUBLIC_ERROR_DESCRIPTIONS = {
    400: "Domain rule violation",
    404: "Public resource not found",
    409: "Request or session state conflict",
    422: "Request validation failed",
    500: "Internal server error",
    503: "Narrative service unavailable",
}


def _public_error_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    return {
        status_code: {
            "model": ErrorResponse,
            "description": _PUBLIC_ERROR_DESCRIPTIONS[status_code],
        }
        for status_code in status_codes
    }


def _raw_header_values(request: Request, raw_name: bytes) -> tuple[bytes, ...]:
    return tuple(
        raw_value
        for header_name, raw_value in request.scope.get("headers", ())
        if header_name.lower() == raw_name
    )


def _request_validation_failure() -> NoReturn:
    raise RequestValidationError([])


def _validate_player_character_creation_transport(
    request: Request,
    idempotency_key: str,
) -> PlayerCharacterOperationId:
    raw_content_types = _raw_header_values(request, b"content-type")
    if len(raw_content_types) != 1:
        _request_validation_failure()
    try:
        content_type = raw_content_types[0].decode("ascii")
    except UnicodeDecodeError:
        _request_validation_failure()
    media_type = content_type.split(";", 1)[0].strip(" \t").lower()
    if media_type != "application/json":
        _request_validation_failure()

    raw_idempotency_keys = _raw_header_values(request, b"idempotency-key")
    if len(raw_idempotency_keys) != 1:
        _request_validation_failure()
    raw_idempotency_key = raw_idempotency_keys[0]
    try:
        raw_value = raw_idempotency_key.decode("ascii")
    except UnicodeDecodeError:
        _request_validation_failure()
    if (
        not 1 <= len(raw_idempotency_key) <= 128
        or _PLAYER_CHARACTER_IDEMPOTENCY_KEY_PATTERN.fullmatch(raw_value) is None
        or raw_value != idempotency_key
    ):
        _request_validation_failure()
    try:
        return PlayerCharacterOperationId(value=raw_value)
    except ValueError:
        _request_validation_failure()


def _parse_player_character_creation_command(
    raw_body: bytes,
) -> CharacterCreationCommand:
    try:
        return CharacterCreationCommand.model_validate_json(raw_body)
    except ValidationError:
        _request_validation_failure()


def _install_player_character_creation_openapi_schema(
    app: FastAPI,
) -> None:
    default_openapi = app.openapi
    installed_schema: dict[str, Any] | None = None

    def _openapi() -> dict[str, Any]:
        nonlocal installed_schema
        if installed_schema is not None:
            return installed_schema

        original_openapi_schema = app.openapi_schema
        published = False
        try:
            base_schema = default_openapi()
            command_schema = CharacterCreationCommand.model_json_schema(
                mode="validation",
                ref_template="#/components/schemas/{model}",
            )
            definitions = command_schema.pop("$defs", {})
            generated_components = {
                "CharacterCreationCommand": command_schema,
                **definitions,
            }

            if not isinstance(base_schema, dict) or not isinstance(
                definitions,
                dict,
            ):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )
            if any(
                not isinstance(name, str) or not isinstance(definition, dict)
                for name, definition in generated_components.items()
            ):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )

            base_components = base_schema.get("components", {})
            if not isinstance(base_components, dict):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )
            base_schemas = base_components.get("schemas", {})
            if not isinstance(base_schemas, dict):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )
            for name, definition in generated_components.items():
                if name in base_schemas and base_schemas[name] != definition:
                    raise RuntimeError(
                        "Player Character OpenAPI component collision"
                    )

            candidate_schema = deepcopy(base_schema)
            candidate_components = candidate_schema.setdefault(
                "components",
                {},
            )
            if not isinstance(candidate_components, dict):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )
            candidate_schemas = candidate_components.setdefault("schemas", {})
            if not isinstance(candidate_schemas, dict):
                raise RuntimeError(
                    "Player Character OpenAPI schema integrity failure"
                )
            for name, definition in generated_components.items():
                if name not in candidate_schemas:
                    candidate_schemas[name] = deepcopy(definition)

            for name, definition in generated_components.items():
                if candidate_schemas.get(name) != definition:
                    raise RuntimeError(
                        "Player Character OpenAPI schema integrity failure"
                    )

            pending: list[Any] = [candidate_schema]
            while pending:
                current = pending.pop()
                if isinstance(current, dict):
                    for key, value in current.items():
                        if key != "$ref":
                            pending.append(value)
                            continue
                        if not isinstance(value, str) or not value.startswith("#/"):
                            raise RuntimeError(
                                "Player Character OpenAPI reference integrity "
                                "failure"
                            )
                        target: Any = candidate_schema
                        for encoded_part in value[2:].split("/"):
                            part = encoded_part.replace("~1", "/").replace(
                                "~0",
                                "~",
                            )
                            if isinstance(target, dict) and part in target:
                                target = target[part]
                            elif (
                                isinstance(target, list)
                                and part.isdigit()
                                and int(part) < len(target)
                            ):
                                target = target[int(part)]
                            else:
                                raise RuntimeError(
                                    "Player Character OpenAPI reference integrity "
                                    "failure"
                                )
                elif isinstance(current, list):
                    pending.extend(current)

            app.openapi_schema = candidate_schema
            installed_schema = candidate_schema
            published = True
            return candidate_schema
        finally:
            if not published:
                app.openapi_schema = original_openapi_schema

    app.openapi = _openapi


def _project_creation_success(
    result: CreationSuccessResult,
) -> PlayerCharacterSelfProjection:
    return PlayerCharacterSelfProjection(
        player_character_id=result.player_character_id,
        contract_version=result.contract_version,
        record_revision=result.resulting_revision,
        lifecycle=result.resulting_lifecycle,
    )


def _translate_creation_decision(
    decision: CharacterOperationProtocolDecision,
) -> NoReturn:
    if (
        decision.operation_namespace is CharacterOperationNamespace.CREATE_V1
        and decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    ):
        raise PlayerCharacterNotFoundError("player-character.create")
    if (
        decision.operation_namespace is CharacterOperationNamespace.CREATE_V1
        and decision.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    ):
        raise IdempotencyConflictError("player-character.create")
    raise RuntimeError("unexpected Player Character creation decision")


def _player_character_clock() -> datetime:
    return datetime.now(timezone.utc)


def _run_clock() -> datetime:
    return datetime.now(timezone.utc)


def build_player_character_service(
    *,
    uow_factory: UnitOfWorkFactory,
    controller_binding_resolver: ControllerBindingResolver,
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=uow_factory,
        controller_binding_resolver=controller_binding_resolver,
        player_character_id_issuer=Uuid4PlayerCharacterIdIssuer(),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(
            value="source.production-player-character"
        ),
        clock=_player_character_clock,
        binding_integrity_guard_enabled=True,
    )


def build_run_service(
    *,
    uow_factory: UnitOfWorkFactory,
    controller_binding_resolver: ControllerBindingResolver,
    player_character_binding_evidence: PlayerCharacterService,
) -> RunService:
    return RunService(
        uow_factory=uow_factory,
        run_id_issuer=Uuid4RunIdIssuer(),
        continuous_story_line_id_issuer=Uuid4ContinuousStoryLineIdIssuer(),
        source_reference=RunAuthoritySourceRef(value="source.production-run"),
        clock=_run_clock,
        controller_binding_resolver=controller_binding_resolver,
        player_character_binding_evidence=(
            player_character_binding_evidence
        ),
    )


def build_default_services(
    *,
    player_character_controller_bindings: (
        Sequence[ConfiguredControllerBinding] | None
    ) = None,
) -> ApiServices:
    """Build runtime dependencies without opening a connection or running migrations."""
    controller_binding_resolver = (
        ConfiguredControllerBindingResolver.from_environment()
        if player_character_controller_bindings is None
        else ConfiguredControllerBindingResolver(
            player_character_controller_bindings
        )
    )
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    catalog = scenario_catalog.content_catalog
    engine = create_engine()
    session_factory = create_session_factory(engine)
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    try:
        deepseek_settings = DeepSeekSettings.from_environment()
    except ValueError:
        deepseek_settings = None
    provider = (
        DeepSeekNarrativeProvider(
            deepseek_settings,
            PromptBuilder(profiles=(default_style_profile(),)),
        )
        if deepseek_settings is not None
        else None
    )
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        narrative_provider=provider,
        provider_name="deepseek",
        model_name=(
            deepseek_settings.model
            if deepseek_settings is not None
            else "deepseek-v4-flash"
        ),
    )
    player_character_service = build_player_character_service(
        uow_factory=uow_factory,
        controller_binding_resolver=controller_binding_resolver,
    )
    return ApiServices(
        session_service=SessionService(
            uow_factory=uow_factory,
            catalog=catalog,
            scenario_catalog=scenario_catalog,
        ),
        turn_orchestrator=orchestrator,
        player_character_service=player_character_service,
        run_service=build_run_service(
            uow_factory=uow_factory,
            controller_binding_resolver=controller_binding_resolver,
            player_character_binding_evidence=player_character_service,
        ),
        engine=engine,
        narrative_provider=provider,
    )


def create_app(*, services: ApiServices | None = None) -> FastAPI:
    owns_services = services is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime = services or build_default_services()
        app.state.api_services = runtime
        try:
            yield
        finally:
            if owns_services and runtime.engine is not None:
                await runtime.engine.dispose()
            if owns_services and runtime.narrative_provider is not None:
                await runtime.narrative_provider.aclose()

    app = FastAPI(
        title="Deviation Protocol",
        version="0.3.0",
        lifespan=lifespan,
    )
    install_exception_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "phase": "3.0"}

    if services is None or services.player_character_service is not None:

        @app.post(
            "/v1/player-characters",
            status_code=status.HTTP_200_OK,
            response_model=PlayerCharacterSelfProjection,
            response_description="Player Character created or exactly replayed.",
            operation_id="create_player_character",
            summary="Create or replay a Player Character",
            description=(
                "Controller identity is derived only from the trusted server-side "
                "principal. Idempotency-Key is required and is not authorization. "
                "First success and exact replay share HTTP 200 and the same body "
                "semantics. Replay returns the original creation result; clients use "
                "the owned GET for current state. No controller binding, receipt, "
                "fingerprint, provenance, Run, persistence, transaction, or recovery "
                "data is public. The fixed development principal is not production "
                "authentication; production authentication and Internet deployment "
                "are unsupported."
            ),
            tags=["player-characters"],
            responses=_public_error_responses(404, 409, 422, 500),
            openapi_extra=_PLAYER_CHARACTER_CREATION_OPENAPI_EXTRA,
        )
        async def create_player_character(
            http_request: Request,
            idempotency_key: PlayerCharacterIdempotencyKeyHeader,
            principal: RequestPrincipal = Depends(get_current_principal),
            service: PlayerCharacterService = Depends(get_player_character_service),
        ) -> PlayerCharacterSelfProjection:
            operation_id = _validate_player_character_creation_transport(
                http_request,
                idempotency_key,
            )
            raw_body = await http_request.body()
            command = _parse_player_character_creation_command(raw_body)
            result = await service.create(
                principal,
                operation_id=operation_id,
                command=command,
            )
            if isinstance(result, CreationSuccessResult):
                return _project_creation_success(result)
            _translate_creation_decision(result)

        @app.get(
            "/v1/player-characters/{player_character_id}",
            response_model=PlayerCharacterSelfProjection,
            responses=_public_error_responses(404, 422, 500),
            tags=["player-characters"],
        )
        async def get_owned_player_character(
            player_character_id: PlayerCharacterPathId,
            principal: RequestPrincipal = Depends(get_current_principal),
            service: PlayerCharacterService = Depends(get_player_character_service),
        ) -> PlayerCharacterSelfProjection:
            projection = await service.get_owned(
                principal,
                player_character_id=PlayerCharacterId(value=player_character_id),
            )
            if projection is None:
                raise PlayerCharacterNotFoundError(player_character_id)
            return projection

        _install_player_character_creation_openapi_schema(app)

    @app.get(
        "/v1/scenarios",
        response_model=PublicScenarioCatalog,
        responses=_public_error_responses(500),
        tags=["scenarios"],
    )
    async def list_scenarios(
        service: SessionService = Depends(get_session_service),
    ) -> PublicScenarioCatalog:
        return service.list_public_scenarios()

    @app.post(
        "/v1/sessions",
        response_model=SessionCreationResult,
        status_code=status.HTTP_201_CREATED,
        responses=_public_error_responses(409, 422, 500),
        tags=["sessions"],
    )
    async def create_session(
        request: CreateSessionRequest,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> SessionCreationResult:
        result = await service.create(
            principal,
            client_request_id=request.client_request_id,
            character_definition_id=request.character_definition_id,
            scenario_id=request.scenario_id,
        )
        if not isinstance(result, SessionCreationResult):  # pragma: no cover
            raise RuntimeError("scenario creation did not return its initial frame")
        return result

    @app.get(
        "/v1/sessions/{session_id}",
        response_model=SessionMetadata,
        tags=["sessions"],
    )
    async def get_session(
        session_id: SessionPathId,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> SessionMetadata:
        return await service.get_metadata(principal, session_id)

    @app.get(
        "/v1/sessions/{session_id}/state",
        response_model=PlayerVisibleStateProjection,
        tags=["sessions"],
    )
    async def get_session_state(
        session_id: SessionPathId,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> PlayerVisibleStateProjection:
        return await service.get_visible_state(principal, session_id)

    @app.get(
        "/v1/sessions/{session_id}/view",
        response_model=PlayerSessionView,
        response_model_exclude_none=True,
        responses=_public_error_responses(404, 409, 422, 500),
        tags=["sessions"],
    )
    async def get_session_view(
        session_id: SessionPathId,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> PlayerSessionView:
        return await service.get_view(principal, session_id)

    @app.get(
        "/v1/sessions/{session_id}/requests/{client_request_id}",
        response_model=NarrativeRequestStatusResponse,
        responses=_public_error_responses(404, 409, 422, 500),
        tags=["actions"],
    )
    async def get_narrative_request_status(
        session_id: SessionPathId,
        client_request_id: RequestPathId,
        http_response: Response,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> NarrativeRequestStatusResponse:
        result = await service.get_narrative_request_status(
            principal, session_id, client_request_id
        )
        if result.status is PublicNarrativeRequestStatus.PENDING:
            assert result.retry_after_seconds is not None
            http_response.headers["Retry-After"] = str(result.retry_after_seconds)
        return NarrativeRequestStatusResponse.from_application_result(result)

    @app.post(
        "/v1/sessions/{session_id}/actions",
        response_model=ActionResponse,
        responses={
            status.HTTP_202_ACCEPTED: {
                "model": ActionResponse,
                "description": "Narrative processing pending",
            },
            **_public_error_responses(400, 404, 409, 422, 500, 503),
        },
        tags=["actions"],
    )
    async def submit_action(
        session_id: SessionPathId,
        request: ActionRequest,
        http_response: Response,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
        orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
    ) -> ActionResponse:
        await service.require_owner(principal, session_id)
        response = await orchestrator.handle(request.to_submission(session_id))
        if response.narrative_pending:
            http_response.status_code = status.HTTP_202_ACCEPTED
        return ActionResponse.from_turn_response(response)

    return app


app = create_app()
