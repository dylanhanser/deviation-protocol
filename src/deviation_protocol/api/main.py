from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path as FilePath
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Path, Response, status

from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
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
from deviation_protocol.application.identity import RequestPrincipal
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
from deviation_protocol.domain.player_character import AuthoritySourceRef
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
    )


def build_run_service(*, uow_factory: UnitOfWorkFactory) -> RunService:
    return RunService(
        uow_factory=uow_factory,
        run_id_issuer=Uuid4RunIdIssuer(),
        continuous_story_line_id_issuer=Uuid4ContinuousStoryLineIdIssuer(),
        source_reference=RunAuthoritySourceRef(value="source.production-run"),
        clock=_run_clock,
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
    return ApiServices(
        session_service=SessionService(
            uow_factory=uow_factory,
            catalog=catalog,
            scenario_catalog=scenario_catalog,
        ),
        turn_orchestrator=orchestrator,
        player_character_service=build_player_character_service(
            uow_factory=uow_factory,
            controller_binding_resolver=controller_binding_resolver,
        ),
        run_service=build_run_service(uow_factory=uow_factory),
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
