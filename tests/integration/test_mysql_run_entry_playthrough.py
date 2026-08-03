from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import uuid4

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import ApiServices, get_current_principal
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_models import (
    NarrativeProvider,
    NarrativeRequest,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.player_character_operations import (
    CharacterCreationCommand,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.run_service import RunService
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterOperationId,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
)
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    NarrativeJobRow,
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
    RunCreationReceiptRow,
    RunCurrentRow,
    RunMutationReceiptRow,
    RunRevisionRow,
    RunSessionParticipationRow,
    TurnRequestRow,
)
from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.e2e.test_demo_cross_process_replay import (
    ACTION_EVENT_COUNTS,
    CANONICAL_ACTIONS,
    PROVIDER_ACTIONS,
)
from tests.integration.test_mysql_phase_2_4a_api import ScriptedOpeningProvider


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
TIMEOUT = 10.0


class _Resolver:
    def __init__(
        self,
        principal: RequestPrincipal,
        binding: ControllerBindingRef,
    ) -> None:
        self.principal = principal
        self.binding = binding
        self.calls: list[RequestPrincipal] = []

    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef | None:
        self.calls.append(principal)
        if principal != self.principal:
            return None
        return self.binding


class _SequenceIssuer:
    def __init__(self, values: list[Any]) -> None:
        self.values = list(values)
        self.calls = 0

    def issue(self) -> Any:
        if self.calls >= len(self.values):
            raise AssertionError("deterministic issuer was called too many times")
        value = self.values[self.calls]
        self.calls += 1
        return value


class _SequenceGenerator:
    def __init__(self, values: list[Any]) -> None:
        self.values = list(values)
        self.calls = 0

    def __call__(self) -> Any:
        if self.calls >= len(self.values):
            raise AssertionError("deterministic generator was called too many times")
        value = self.values[self.calls]
        self.calls += 1
        return value


class _CounterGenerator:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        return f"{self.prefix}{self.calls:04d}"


class _BlockingScriptedProvider(NarrativeProvider):
    def __init__(self, *, block_first: bool) -> None:
        self.delegate = ScriptedOpeningProvider()
        self.block_first = block_first
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def generate(
        self,
        request: NarrativeRequest,
    ) -> UntrustedNarrativeProposal:
        self.calls += 1
        if self.block_first and self.calls == 1:
            self.entered.set()
            await self.release.wait()
        return await self.delegate.generate(request)

    async def aclose(self) -> None:
        await self.delegate.aclose()


@dataclass(slots=True)
class _Scope:
    token: str = field(default_factory=lambda: uuid4().hex)
    run_ids: set[str] = field(default_factory=set)
    session_ids: set[str] = field(default_factory=set)
    player_character_ids: set[str] = field(default_factory=set)
    controller_bindings: set[str] = field(default_factory=set)

    def principal(self, suffix: str = "owner") -> RequestPrincipal:
        return RequestPrincipal(
            player_id=f"player.it-{self.token[:24]}-{suffix}",
            authentication_scheme="integration",
        )

    def binding(self, suffix: str = "owner") -> ControllerBindingRef:
        value = f"binding.it-{self.token}-{suffix}"
        self.controller_bindings.add(value)
        return ControllerBindingRef(value=value)

    def player_character_id(self, suffix: str) -> PlayerCharacterId:
        value = f"pc.it-{self.token}-{suffix}"
        self.player_character_ids.add(value)
        return PlayerCharacterId(value=value)

    def run_id(self) -> RunId:
        value = f"run.it-{self.token}"
        self.run_ids.add(value)
        return RunId(value=value)

    def line_id(self) -> ContinuousStoryLineId:
        return ContinuousStoryLineId(value=f"csl.it-{self.token}")

    def session_id(self) -> str:
        value = f"session.it-{self.token}"
        self.session_ids.add(value)
        return value


def _scoped_family_predicates(scope: _Scope) -> tuple[tuple[Any, Any], ...]:
    return (
        (NarrativeJobRow, NarrativeJobRow.session_id.in_(scope.session_ids)),
        (TurnRequestRow, TurnRequestRow.session_id.in_(scope.session_ids)),
        (DomainEventRow, DomainEventRow.session_id.in_(scope.session_ids)),
        (GameSnapshotRow, GameSnapshotRow.session_id.in_(scope.session_ids)),
        (RunMutationReceiptRow, RunMutationReceiptRow.run_id.in_(scope.run_ids)),
        (
            RunCreationReceiptRow,
            RunCreationReceiptRow.result_run_id.in_(scope.run_ids),
        ),
        (RunCurrentRow, RunCurrentRow.run_id.in_(scope.run_ids)),
        (
            RunSessionParticipationRow,
            RunSessionParticipationRow.run_id.in_(scope.run_ids),
        ),
        (RunRevisionRow, RunRevisionRow.run_id.in_(scope.run_ids)),
        (GameSessionRow, GameSessionRow.session_id.in_(scope.session_ids)),
        (
            PlayerCharacterMutationReceiptRow,
            PlayerCharacterMutationReceiptRow.player_character_id.in_(
                scope.player_character_ids
            ),
        ),
        (
            PlayerCharacterCurrentRow,
            PlayerCharacterCurrentRow.player_character_id.in_(
                scope.player_character_ids
            ),
        ),
        (
            PlayerCharacterCreationReceiptRow,
            PlayerCharacterCreationReceiptRow.result_player_character_id.in_(
                scope.player_character_ids
            ),
        ),
        (
            PlayerCharacterRevisionRow,
            PlayerCharacterRevisionRow.player_character_id.in_(
                scope.player_character_ids
            ),
        ),
        (
            PlayerCharacterIdAllocationRow,
            PlayerCharacterIdAllocationRow.player_character_id.in_(
                scope.player_character_ids
            ),
        ),
        (
            PlayerCharacterControllerBindingRow,
            PlayerCharacterControllerBindingRow.controller_binding.in_(
                scope.controller_bindings
            ),
        ),
    )


async def _delete_scope(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
) -> None:
    async with factory.begin() as session:
        if scope.session_ids:
            for row_type in (
                NarrativeJobRow,
                TurnRequestRow,
                DomainEventRow,
                GameSnapshotRow,
            ):
                await session.execute(
                    sa.delete(row_type).where(
                        row_type.session_id.in_(scope.session_ids)
                    )
                )
        if scope.run_ids:
            await session.execute(
                sa.delete(RunMutationReceiptRow).where(
                    RunMutationReceiptRow.run_id.in_(scope.run_ids)
                )
            )
            await session.execute(
                sa.delete(RunCreationReceiptRow).where(
                    RunCreationReceiptRow.result_run_id.in_(scope.run_ids)
                )
            )
            await session.execute(
                sa.delete(RunCurrentRow).where(
                    RunCurrentRow.run_id.in_(scope.run_ids)
                )
            )
            await session.execute(
                sa.delete(RunSessionParticipationRow).where(
                    RunSessionParticipationRow.run_id.in_(scope.run_ids)
                )
            )
            await session.execute(
                sa.delete(RunRevisionRow).where(
                    RunRevisionRow.run_id.in_(scope.run_ids)
                )
            )
        if scope.session_ids:
            await session.execute(
                sa.delete(GameSessionRow).where(
                    GameSessionRow.session_id.in_(scope.session_ids)
                )
            )
        if scope.player_character_ids:
            await session.execute(
                sa.delete(PlayerCharacterMutationReceiptRow).where(
                    PlayerCharacterMutationReceiptRow.player_character_id.in_(
                        scope.player_character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterCurrentRow).where(
                    PlayerCharacterCurrentRow.player_character_id.in_(
                        scope.player_character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterCreationReceiptRow).where(
                    PlayerCharacterCreationReceiptRow.result_player_character_id.in_(
                        scope.player_character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterRevisionRow).where(
                    PlayerCharacterRevisionRow.player_character_id.in_(
                        scope.player_character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterIdAllocationRow).where(
                    PlayerCharacterIdAllocationRow.player_character_id.in_(
                        scope.player_character_ids
                    )
                )
            )
        if scope.controller_bindings:
            await session.execute(
                sa.delete(PlayerCharacterControllerBindingRow).where(
                    PlayerCharacterControllerBindingRow.controller_binding.in_(
                        scope.controller_bindings
                    )
                )
            )

    predicates = _scoped_family_predicates(scope)
    async with factory() as session:
        residual = [
            int(
                await session.scalar(
                    sa.select(sa.func.count()).select_from(row_type).where(predicate)
                )
                or 0
            )
            for row_type, predicate in predicates
        ]
    assert residual == [0] * len(predicates)


@asynccontextmanager
async def _scoped(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[_Scope]:
    scope = _Scope()
    try:
        yield scope
    finally:
        await _delete_scope(factory, scope)


@dataclass(slots=True)
class _Runtime:
    app: Any
    services: ApiServices
    principal: RequestPrincipal
    resolver: _Resolver
    character_ids: tuple[PlayerCharacterId, ...]
    run_id: RunId
    line_id: ContinuousStoryLineId
    session_id: str
    run_issuer: _SequenceIssuer
    line_issuer: _SequenceIssuer
    session_generator: _SequenceGenerator
    provider: _BlockingScriptedProvider
    scenario_catalog: Any


async def _build_runtime(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
    *,
    character_count: int,
    block_first_provider_call: bool,
) -> _Runtime:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    principal = scope.principal()
    binding = scope.binding()
    resolver = _Resolver(principal, binding)
    character_ids = tuple(
        scope.player_character_id(f"owned-{index}")
        for index in range(1, character_count + 1)
    )
    character_issuer = _SequenceIssuer(list(character_ids))
    uow_factory = lambda: SqlAlchemyUnitOfWork(factory)
    character_service = PlayerCharacterService(
        uow_factory=uow_factory,
        controller_binding_resolver=resolver,
        player_character_id_issuer=character_issuer,
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.it-player-character"),
        clock=lambda: NOW,
        binding_integrity_guard_enabled=True,
    )
    for index, character_id in enumerate(character_ids, start=1):
        result = await character_service.create(
            principal,
            operation_id=PlayerCharacterOperationId(
                value=f"operation.{scope.token}.create-{index}"
            ),
            command=CharacterCreationCommand(
                contract_version=PlayerCharacterContractVersion.V1,
                character_core=CharacterCore(),
                narration_preferences=NarrationPreferences(),
            ),
        )
        assert result.player_character_id == character_id
        assert result.resulting_revision.value == 1
        assert result.resulting_lifecycle.value == "active"
    assert character_issuer.calls == character_count

    run_id = scope.run_id()
    line_id = scope.line_id()
    session_id = scope.session_id()
    run_issuer = _SequenceIssuer([run_id])
    line_issuer = _SequenceIssuer([line_id])
    session_generator = _SequenceGenerator([session_id])
    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: NOW,
        session_id_generator=session_generator,
        seed_generator=_SequenceGenerator([42]),
        event_id_generator=_CounterGenerator(f"event.{scope.token[:16]}-"),
    )
    run_service = RunService(
        uow_factory=uow_factory,
        run_id_issuer=run_issuer,
        continuous_story_line_id_issuer=line_issuer,
        source_reference=RunAuthoritySourceRef(value="source.it-run"),
        clock=lambda: NOW,
        controller_binding_resolver=resolver,
        player_character_binding_evidence=character_service,
    )
    run_entry_service = main.build_run_entry_service(
        run_service=run_service,
        session_service=session_service,
    )
    provider = _BlockingScriptedProvider(
        block_first=block_first_provider_call
    )
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        narrative_provider=provider,
        provider_name="scripted",
        model_name="offline-script",
        clock=lambda: NOW,
        lease_duration=timedelta(minutes=2),
        job_id_generator=_CounterGenerator(f"job.{scope.token[:16]}-"),
        lease_token_generator=_CounterGenerator(
            f"lease.token.{scope.token[:24]}-"
        ),
        worker_id_generator=_CounterGenerator(f"worker.{scope.token[:16]}-"),
        event_id_generator=_CounterGenerator(f"event.action.{scope.token[:12]}-"),
    )
    services = ApiServices(
        session_service=session_service,
        turn_orchestrator=orchestrator,
        player_character_service=character_service,
        run_service=run_service,
        run_entry_service=run_entry_service,
        narrative_provider=provider,
    )
    app = main.create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: principal

    assert run_entry_service.uow_factory is run_service.uow_factory
    assert run_entry_service.uow_factory is character_service.uow_factory
    assert run_entry_service.uow_factory is session_service.uow_factory
    assert run_entry_service.uow_factory is orchestrator.uow_factory
    assert run_entry_service.run_id_issuer is run_service.run_id_issuer
    assert (
        run_entry_service.continuous_story_line_id_issuer
        is run_service.continuous_story_line_id_issuer
    )
    assert run_entry_service.session_service is session_service
    return _Runtime(
        app=app,
        services=services,
        principal=principal,
        resolver=resolver,
        character_ids=character_ids,
        run_id=run_id,
        line_id=line_id,
        session_id=session_id,
        run_issuer=run_issuer,
        line_issuer=line_issuer,
        session_generator=session_generator,
        provider=provider,
        scenario_catalog=scenario_catalog,
    )


async def _entry(
    client: httpx.AsyncClient,
    *,
    key: str,
    character_id: str,
    revision: int = 1,
    scenario_id: str = "death_certificate",
) -> httpx.Response:
    return await client.post(
        "/v1/runs",
        headers={"Idempotency-Key": key, "Content-Type": "application/json"},
        json={
            "player_character_id": character_id,
            "expected_record_revision": revision,
            "scenario_id": scenario_id,
        },
    )


async def _family_counts(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
) -> tuple[int, ...]:
    predicates = (
        (RunRevisionRow, RunRevisionRow.run_id.in_(scope.run_ids)),
        (RunCurrentRow, RunCurrentRow.run_id.in_(scope.run_ids)),
        (
            RunCreationReceiptRow,
            RunCreationReceiptRow.result_run_id.in_(scope.run_ids),
        ),
        (RunMutationReceiptRow, RunMutationReceiptRow.run_id.in_(scope.run_ids)),
        (
            RunSessionParticipationRow,
            RunSessionParticipationRow.run_id.in_(scope.run_ids),
        ),
        (GameSessionRow, GameSessionRow.session_id.in_(scope.session_ids)),
        (GameSnapshotRow, GameSnapshotRow.session_id.in_(scope.session_ids)),
        (DomainEventRow, DomainEventRow.session_id.in_(scope.session_ids)),
        (TurnRequestRow, TurnRequestRow.session_id.in_(scope.session_ids)),
        (NarrativeJobRow, NarrativeJobRow.session_id.in_(scope.session_ids)),
    )
    async with factory() as session:
        counts: list[int] = []
        for row_type, predicate in predicates:
            counts.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count())
                        .select_from(row_type)
                        .where(predicate)
                    )
                    or 0
                )
            )
        return tuple(counts)


async def _create_foreign_character(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
) -> PlayerCharacterId:
    principal = scope.principal("foreign")
    binding = scope.binding("foreign")
    character_id = scope.player_character_id("foreign")
    service = PlayerCharacterService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(factory),
        controller_binding_resolver=_Resolver(principal, binding),
        player_character_id_issuer=_SequenceIssuer([character_id]),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.it-foreign-character"),
        clock=lambda: NOW,
        binding_integrity_guard_enabled=True,
    )
    result = await service.create(
        principal,
        operation_id=PlayerCharacterOperationId(
            value=f"operation.{scope.token}.create-foreign"
        ),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    assert result.player_character_id == character_id
    return character_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_public_run_entry_replay_decisions_and_no_write_boundaries(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with _scoped(mysql_session_factory) as scope:
        runtime = await _build_runtime(
            mysql_session_factory,
            scope,
            character_count=3,
            block_first_provider_call=False,
        )
        foreign_id = await _create_foreign_character(mysql_session_factory, scope)
        transport = httpx.ASGITransport(app=runtime.app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            first = await _entry(
                client,
                key="entry.boundary",
                character_id=runtime.character_ids[0].value,
            )
            assert first.status_code == 200
            assert first.json() == {
                "run_id": runtime.run_id.value,
                "session_id": runtime.session_id,
                "scenario_id": "death_certificate",
                "player_character": {
                    "player_character_id": {
                        "value": runtime.character_ids[0].value
                    },
                    "contract_version": "structured-player-character/v1",
                    "record_revision": {"value": 1},
                    "lifecycle": "active",
                },
            }
            admitted_counts = await _family_counts(mysql_session_factory, scope)
            assert admitted_counts == (3, 1, 1, 2, 1, 1, 1, 1, 0, 0)
            replay = await _entry(
                client,
                key="entry.boundary",
                character_id=runtime.character_ids[0].value,
            )
            assert replay.status_code == 200
            assert replay.content == first.content
            assert await _family_counts(mysql_session_factory, scope) == admitted_counts
            assert runtime.run_issuer.calls == 1
            assert runtime.line_issuer.calls == 1
            assert runtime.session_generator.calls == 1
            assert runtime.provider.calls == 0

            conflict = await _entry(
                client,
                key="entry.boundary",
                character_id=runtime.character_ids[0].value,
                revision=2,
            )
            assert conflict.status_code == 409
            assert conflict.json() == {
                "error": {
                    "error_code": "IDEMPOTENCY_CONFLICT",
                    "message": "Idempotency key was reused",
                }
            }

            not_found_bodies = []
            for suffix, character_id in (
                ("missing", f"pc.missing-{scope.token}"),
                ("foreign", foreign_id.value),
            ):
                response = await _entry(
                    client,
                    key=f"entry.{suffix}",
                    character_id=character_id,
                )
                assert response.status_code == 404
                not_found_bodies.append(response.content)
            unavailable_principal = RequestPrincipal(
                player_id=f"player.unavailable-{scope.token[:24]}",
                authentication_scheme="integration",
            )
            runtime.app.dependency_overrides[get_current_principal] = (
                lambda: unavailable_principal
            )
            unavailable = await _entry(
                client,
                key="entry.unavailable-controller",
                character_id=runtime.character_ids[0].value,
            )
            runtime.app.dependency_overrides[get_current_principal] = (
                lambda: runtime.principal
            )
            assert unavailable.status_code == 404
            not_found_bodies.append(unavailable.content)
            assert len(set(not_found_bodies)) == 1
            assert not_found_bodies[0] == (
                b'{"error":{"error_code":"PLAYER_CHARACTER_NOT_FOUND",'
                b'"message":"Player character was not found"}}'
            )

            stale = await _entry(
                client,
                key="entry.stale",
                character_id=runtime.character_ids[1].value,
                revision=2,
            )
            assert stale.status_code == 409
            assert stale.json() == {
                "error": {
                    "error_code": "PLAYER_CHARACTER_STALE",
                    "message": "Player character revision is stale",
                }
            }
            ineligible = await _entry(
                client,
                key="entry.bound-character",
                character_id=runtime.character_ids[0].value,
            )
            assert ineligible.status_code == 409
            assert ineligible.json() == {
                "error": {
                    "error_code": "PLAYER_CHARACTER_NOT_ELIGIBLE",
                    "message": "Player character is not eligible for Run entry",
                }
            }
            invalid_scenario = await _entry(
                client,
                key="entry.invalid-scenario",
                character_id=runtime.character_ids[2].value,
                scenario_id="scenario.unavailable",
            )
            assert invalid_scenario.status_code == 422
            assert invalid_scenario.json() == {
                "error": {
                    "error_code": "INVALID_SCENARIO_DEFINITION",
                    "message": "Scenario definition is not available",
                }
            }
            assert await _family_counts(mysql_session_factory, scope) == admitted_counts
            assert runtime.run_issuer.calls == 1
            assert runtime.line_issuer.calls == 1
            assert runtime.session_generator.calls == 1
            assert runtime.provider.calls == runtime.provider.delegate.calls == 0


async def _pending_read_fingerprint(
    factory: async_sessionmaker[AsyncSession],
    *,
    session_id: str,
    run_id: str,
) -> tuple[Any, ...]:
    async with factory() as session:
        game_session = await session.scalar(
            sa.select(GameSessionRow).where(GameSessionRow.session_id == session_id)
        )
        snapshot = await session.scalar(
            sa.select(GameSnapshotRow).where(GameSnapshotRow.session_id == session_id)
        )
        jobs = tuple(
            (
                row.job_id,
                row.status,
                row.attempt_count,
                row.client_request_id,
                row.validated_proposal_digest,
                row.accepted_narrative_text,
            )
            for row in (
                await session.scalars(
                    sa.select(NarrativeJobRow)
                    .where(NarrativeJobRow.session_id == session_id)
                    .order_by(NarrativeJobRow.job_id)
                )
            ).all()
        )
        run = await session.scalar(
            sa.select(RunCurrentRow).where(RunCurrentRow.run_id == run_id)
        )
        assert game_session is not None and snapshot is not None and run is not None
        return (
            game_session.phase,
            game_session.turn_number,
            game_session.state_version,
            snapshot.state_version,
            snapshot.state_json,
            jobs,
            run.state_version,
            run.lifecycle_status,
        )


def _action_body(
    *,
    token: str,
    ordinal: int,
    view: dict[str, Any],
) -> dict[str, Any]:
    step = CANONICAL_ACTIONS[ordinal - 1]
    affordances = view["action_affordances"]
    body: dict[str, Any] = {
        "turn_id": f"turn.{token[:16]}.{ordinal:02d}",
        "client_request_id": f"action.{token[:16]}.{ordinal:02d}",
        "action_type": step.action_type,
    }
    if step.action_type == "CHOOSE":
        assert affordances["mode"] == "DECISION"
        displayed = {
            choice["choice_id"]: choice for choice in affordances["choices"]
        }
        assert step.choice_id in displayed
        assert displayed[step.choice_id]["action_type"] == "CHOOSE"
        body["decision_id"] = affordances["decision_id"]
        body["choice_id"] = step.choice_id
    else:
        assert affordances["mode"] == "FREE_ACTIONS"
        advertised = next(
            action
            for action in affordances["actions"]
            if action["action_type"] == step.action_type
        )
        assert advertised["target_required"] is False
        if step.description is None:
            assert step.action_type == "CONTINUE"
            assert advertised["input_kind"] == "NONE"
            assert "max_input_length" not in advertised
        else:
            assert advertised["input_kind"] == "DESCRIPTION"
            assert advertised["max_input_length"] == 150
            body["description"] = step.description
    return body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_production_asgi_run_entry_reaches_canonical_terminal_view(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with _scoped(mysql_session_factory) as scope:
        runtime = await _build_runtime(
            mysql_session_factory,
            scope,
            character_count=1,
            block_first_provider_call=True,
        )
        transport = httpx.ASGITransport(app=runtime.app, raise_app_exceptions=True)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            timeout=TIMEOUT,
        ) as client:
            entry_key = "entry.canonical-playthrough"
            admitted = await _entry(
                client,
                key=entry_key,
                character_id=runtime.character_ids[0].value,
            )
            assert admitted.status_code == 200
            admission_body = admitted.json()
            assert admission_body == {
                "run_id": runtime.run_id.value,
                "session_id": runtime.session_id,
                "scenario_id": "death_certificate",
                "player_character": {
                    "player_character_id": {
                        "value": runtime.character_ids[0].value
                    },
                    "contract_version": "structured-player-character/v1",
                    "record_revision": {"value": 1},
                    "lifecycle": "active",
                },
            }
            assert set(admission_body) == {
                "run_id",
                "session_id",
                "scenario_id",
                "player_character",
            }
            assert runtime.run_issuer.calls == 1
            assert runtime.line_issuer.calls == 1
            assert runtime.session_generator.calls == 1
            assert runtime.provider.calls == 0

            admission_counts = await _family_counts(mysql_session_factory, scope)
            assert admission_counts == (3, 1, 1, 2, 1, 1, 1, 1, 0, 0)
            replay = await _entry(
                client,
                key=entry_key,
                character_id=runtime.character_ids[0].value,
            )
            assert replay.status_code == 200
            assert replay.content == admitted.content
            assert await _family_counts(mysql_session_factory, scope) == admission_counts
            assert runtime.run_issuer.calls == 1
            assert runtime.line_issuer.calls == 1
            assert runtime.session_generator.calls == 1
            assert runtime.provider.calls == 0

            async with mysql_session_factory() as database:
                run_revisions = list(
                    (
                        await database.scalars(
                            sa.select(RunRevisionRow)
                            .where(RunRevisionRow.run_id == runtime.run_id.value)
                            .order_by(RunRevisionRow.state_version)
                        )
                    ).all()
                )
                run_current = await database.scalar(
                    sa.select(RunCurrentRow).where(
                        RunCurrentRow.run_id == runtime.run_id.value
                    )
                )
                creation_receipts = list(
                    (
                        await database.scalars(
                            sa.select(RunCreationReceiptRow).where(
                                RunCreationReceiptRow.result_run_id
                                == runtime.run_id.value
                            )
                        )
                    ).all()
                )
                mutation_receipts = list(
                    (
                        await database.scalars(
                            sa.select(RunMutationReceiptRow)
                            .where(
                                RunMutationReceiptRow.run_id
                                == runtime.run_id.value
                            )
                            .order_by(RunMutationReceiptRow.resulting_state_version)
                        )
                    ).all()
                )
                participations = list(
                    (
                        await database.scalars(
                            sa.select(RunSessionParticipationRow).where(
                                RunSessionParticipationRow.run_id
                                == runtime.run_id.value
                            )
                        )
                    ).all()
                )
                game_session = await database.scalar(
                    sa.select(GameSessionRow).where(
                        GameSessionRow.session_id == runtime.session_id
                    )
                )
                initial_snapshot = await database.scalar(
                    sa.select(GameSnapshotRow).where(
                        GameSnapshotRow.session_id == runtime.session_id
                    )
                )
                initial_events = list(
                    (
                        await database.scalars(
                            sa.select(DomainEventRow).where(
                                DomainEventRow.session_id == runtime.session_id
                            )
                        )
                    ).all()
                )
                character_current = await database.scalar(
                    sa.select(PlayerCharacterCurrentRow).where(
                        PlayerCharacterCurrentRow.player_character_id
                        == runtime.character_ids[0].value
                    )
                )
            assert [row.state_version for row in run_revisions] == [1, 2, 3]
            assert [row.mutation_kind for row in run_revisions] == [
                "CREATE",
                "BIND_PLAYER_CHARACTER",
                "ATTACH_SESSION",
            ]
            assert run_current is not None
            assert run_current.state_version == 3
            assert run_current.lifecycle_status == "active"
            assert run_current.continuous_story_line_id == runtime.line_id.value
            assert run_current.binding_player_character_id == (
                runtime.character_ids[0].value
            )
            assert run_current.binding_record_revision == 1
            assert run_current.binding_state == "active"
            assert run_current.active_player_character_id == (
                runtime.character_ids[0].value
            )
            assert len(creation_receipts) == 1
            assert [row.command_kind for row in mutation_receipts] == [
                "BIND_PLAYER_CHARACTER",
                "ATTACH_SESSION",
            ]
            assert len(participations) == 1
            assert participations[0].session_id == runtime.session_id
            assert participations[0].joined_state_version == 3
            assert game_session is not None
            assert game_session.player_id == runtime.principal.player_id
            assert game_session.scenario_id == "death_certificate"
            definition = runtime.scenario_catalog.scenario("death_certificate")
            assert definition is not None and definition.public_client is not None
            assert game_session.scenario_version == definition.content_version
            assert game_session.character_definition_id == (
                definition.public_client.default_character_definition_id
            )
            assert game_session.state_version == 0
            assert initial_snapshot is not None
            assert initial_snapshot.state_version == 0
            assert len(initial_events) == 1
            assert initial_events[0].sequence_no == 1
            assert initial_events[0].event_type == "ScenarioStarted"
            assert character_current is not None
            assert character_current.record_revision == 1
            assert character_current.lifecycle == "active"

            view_path = f"/v1/sessions/{runtime.session_id}/view"
            action_path = f"/v1/sessions/{runtime.session_id}/actions"
            initial_view_response = await client.get(view_path)
            assert initial_view_response.status_code == 200
            initial_view = initial_view_response.json()
            assert initial_view["metadata"]["session_id"] == runtime.session_id
            assert initial_view["metadata"]["state_version"] == 0
            assert initial_view["scenario_status"] == "ACTIVE"
            assert initial_view["action_affordances"]["mode"] == "DECISION"
            assert initial_view["action_affordances"]["decision_id"] == (
                initial_view["narrative_frame"]["decision_id"]
            )
            assert "death_certificate.action.move_fingers_rhythmically" in {
                choice["choice_id"]
                for choice in initial_view["action_affordances"]["choices"]
            }
            assert initial_view["action_affordances"]["actions"] == []
            assert all(
                choice["action_type"] == "CHOOSE"
                for choice in initial_view["action_affordances"]["choices"]
            )
            assert not any(
                action.get("action_type") == "CUSTOM"
                for action in initial_view["action_affordances"]["actions"]
            )

            observed_action_kinds: list[str] = []
            observed_provider_ordinals: list[int] = []
            submitted_actions: dict[int, dict[str, Any]] = {}
            committed_responses: dict[int, dict[str, Any]] = {}
            provider_calls_after_action: dict[int, int] = {}
            previous_provider_calls = 0
            for ordinal, step in enumerate(CANONICAL_ACTIONS, start=1):
                before_response = await client.get(view_path)
                assert before_response.status_code == 200
                before = before_response.json()
                assert before["metadata"]["session_id"] == runtime.session_id
                assert before["metadata"]["state_version"] == ordinal - 1
                body = _action_body(
                    token=scope.token,
                    ordinal=ordinal,
                    view=before,
                )
                submitted_actions[ordinal] = body
                observed_action_kinds.append(body["action_type"])

                if ordinal == 2:
                    original_task = asyncio.create_task(
                        client.post(action_path, json=body)
                    )
                    try:
                        await asyncio.wait_for(
                            runtime.provider.entered.wait(), timeout=TIMEOUT
                        )
                        assert not original_task.done()
                        assert runtime.provider.calls == 1
                        assert runtime.provider.delegate.calls == 0
                        duplicate = await asyncio.wait_for(
                            client.post(action_path, json=body), timeout=TIMEOUT
                        )
                        assert duplicate.status_code == 202
                        duplicate_body = duplicate.json()
                        assert duplicate_body["client_request_id"] == (
                            body["client_request_id"]
                        )
                        assert duplicate_body["narrative_pending"] is True
                        assert duplicate_body["narrative_status"] == "PENDING"
                        assert duplicate_body["resulting_state_version"] == 1
                        assert runtime.provider.calls == 1

                        status_path = (
                            f"/v1/sessions/{runtime.session_id}/requests/"
                            f"{body['client_request_id']}"
                        )
                        pending_status = await client.get(status_path)
                        assert pending_status.status_code == 200
                        assert pending_status.json()["status"] == "PENDING"
                        assert pending_status.json()["client_action"] == (
                            "POLL_SAME_REQUEST"
                        )
                        assert pending_status.headers["Retry-After"] == "2"
                        before_pending_read = await _pending_read_fingerprint(
                            mysql_session_factory,
                            session_id=runtime.session_id,
                            run_id=runtime.run_id.value,
                        )
                        pending_view_response = await client.get(view_path)
                        assert pending_view_response.status_code == 200
                        pending_view = pending_view_response.json()
                        assert pending_view["metadata"]["state_version"] == 1
                        assert pending_view["recent_narrative_texts"] == []
                        after_pending_read = await _pending_read_fingerprint(
                            mysql_session_factory,
                            session_id=runtime.session_id,
                            run_id=runtime.run_id.value,
                        )
                        assert after_pending_read == before_pending_read
                    finally:
                        runtime.provider.release.set()
                    action_response = await asyncio.wait_for(
                        original_task, timeout=TIMEOUT
                    )
                    assert action_response.status_code == 200
                    action_result = action_response.json()
                    assert action_result["narrative_status"] == "COMMITTED"
                    assert runtime.provider.calls == 1
                    assert runtime.provider.delegate.calls == 1
                    committed_status = await client.get(status_path)
                    assert committed_status.status_code == 200
                    committed_status_body = committed_status.json()
                    assert committed_status_body["status"] == "COMMITTED"
                    assert committed_status_body["client_action"] == (
                        "RESPONSE_AVAILABLE"
                    )
                    assert committed_status_body["response"] == action_result
                    assert "Retry-After" not in committed_status.headers
                else:
                    action_response = await client.post(action_path, json=body)
                    assert action_response.status_code == 200
                    action_result = action_response.json()

                assert action_result["client_request_id"] == (
                    body["client_request_id"]
                )
                assert action_result["resulting_state_version"] == ordinal
                committed_responses[ordinal] = action_result
                if runtime.provider.calls > previous_provider_calls:
                    observed_provider_ordinals.append(ordinal)
                previous_provider_calls = runtime.provider.calls
                provider_calls_after_action[ordinal] = runtime.provider.calls
                assert runtime.provider.calls == len(
                    [item for item in PROVIDER_ACTIONS if item <= ordinal]
                )

                if ordinal == 1:
                    assert runtime.provider.calls == 0
                    assert action_result["narrative_required"] is False
                    async with mysql_session_factory() as database:
                        jobs_after_action_one = int(
                            await database.scalar(
                                sa.select(sa.func.count())
                                .select_from(NarrativeJobRow)
                                .where(
                                    NarrativeJobRow.session_id
                                    == runtime.session_id
                                )
                            )
                            or 0
                        )
                    assert jobs_after_action_one == 0

                after_response = await client.get(view_path)
                assert after_response.status_code == 200
                after = after_response.json()
                assert after["metadata"]["session_id"] == runtime.session_id
                assert after["metadata"]["state_version"] == ordinal
                if action_result["narrative_frame"] is not None:
                    for frame_field in ("phase_id", "mode", "stop_condition"):
                        assert after["narrative_frame"][frame_field] == (
                            action_result["narrative_frame"][frame_field]
                        )
                if ordinal == 1:
                    assert after["action_affordances"]["mode"] == "FREE_ACTIONS"
                    custom = next(
                        action
                        for action in after["action_affordances"]["actions"]
                        if action["action_type"] == "CUSTOM"
                    )
                    assert custom["input_kind"] == "DESCRIPTION"
                    assert custom["target_required"] is False
                    assert custom["max_input_length"] == 150

            assert observed_action_kinds == [
                "CHOOSE",
                "CUSTOM",
                "CONTINUE",
                "CONTINUE",
                "CHOOSE",
                "CONTINUE",
                "CONTINUE",
                "CONTINUE",
                "CHOOSE",
                "EXPLORE",
                "EXPLORE",
                "CHOOSE",
                "OBSERVE",
                "CONTINUE",
                "CONTINUE",
                "CHOOSE",
                "CHOOSE",
                "CHOOSE",
                "CHOOSE",
            ]
            assert observed_provider_ordinals == [2, 10, 11, 13]
            assert runtime.provider.calls == runtime.provider.delegate.calls == 4
            assert set(submitted_actions) == set(committed_responses) == set(
                range(1, 20)
            )
            terminal_submission = submitted_actions[19]
            terminal_action_response = committed_responses[19]
            assert terminal_submission["action_type"] == "CHOOSE"
            assert terminal_submission["choice_id"] == (
                "death_certificate.action.final_suspend"
            )
            assert terminal_action_response["resulting_state_version"] == 19
            assert terminal_action_response["narrative_frame"]["mode"] == (
                "SETTLEMENT"
            )
            assert terminal_action_response["narrative_frame"][
                "stop_condition"
            ] == "SCENARIO_ENDED"
            assert provider_calls_after_action[18] == 4
            assert provider_calls_after_action[19] == 4

            terminal_response = await client.get(view_path)
            assert terminal_response.status_code == 200
            terminal_view = terminal_response.json()
            assert terminal_view["metadata"]["session_id"] == runtime.session_id
            assert terminal_view["metadata"]["state_version"] == 19
            assert terminal_view["scenario_status"] == "ENDED"
            assert terminal_view["ending_status"] == "RESOLVED"
            assert terminal_view["ending_id"] == (
                "death_certificate.ending.protocol_broken"
            )
            assert terminal_view["narrative_frame"]["mode"] == "SETTLEMENT"
            assert terminal_view["narrative_frame"]["stop_condition"] == (
                "SCENARIO_ENDED"
            )
            assert terminal_view["action_affordances"] == {
                "mode": "ENDED",
                "actions": [],
                "choices": [],
            }
            assert terminal_view["presentation"]["ending"]["title"]
            assert terminal_view["presentation"]["ending"]["summary"]
            assert terminal_view["player_memory"]["scenarios"][0]["status"] == (
                "COMPLETED"
            )
            assert len(terminal_view["recent_narrative_texts"]) == 5

            async with mysql_session_factory() as database:
                terminal_session = await database.scalar(
                    sa.select(GameSessionRow).where(
                        GameSessionRow.session_id == runtime.session_id
                    )
                )
                terminal_snapshot = await database.scalar(
                    sa.select(GameSnapshotRow).where(
                        GameSnapshotRow.session_id == runtime.session_id
                    )
                )
                events = list(
                    (
                        await database.scalars(
                            sa.select(DomainEventRow)
                            .where(DomainEventRow.session_id == runtime.session_id)
                            .order_by(DomainEventRow.sequence_no)
                        )
                    ).all()
                )
                requests = list(
                    (
                        await database.scalars(
                            sa.select(TurnRequestRow)
                            .join(
                                RunSessionParticipationRow,
                                RunSessionParticipationRow.session_id
                                == TurnRequestRow.session_id,
                            )
                            .where(
                                RunSessionParticipationRow.run_id
                                == runtime.run_id.value
                            )
                        )
                    ).all()
                )
                jobs = list(
                    (
                        await database.scalars(
                            sa.select(NarrativeJobRow)
                            .join(
                                RunSessionParticipationRow,
                                RunSessionParticipationRow.session_id
                                == NarrativeJobRow.session_id,
                            )
                            .where(
                                RunSessionParticipationRow.run_id
                                == runtime.run_id.value
                            )
                        )
                    ).all()
                )
                final_run = await database.scalar(
                    sa.select(RunCurrentRow).where(
                        RunCurrentRow.run_id == runtime.run_id.value
                    )
                )
                final_run_revision_count = int(
                    await database.scalar(
                        sa.select(sa.func.count())
                        .select_from(RunRevisionRow)
                        .where(RunRevisionRow.run_id == runtime.run_id.value)
                    )
                    or 0
                )
                final_creation_receipt_count = int(
                    await database.scalar(
                        sa.select(sa.func.count())
                        .select_from(RunCreationReceiptRow)
                        .where(
                            RunCreationReceiptRow.result_run_id
                            == runtime.run_id.value
                        )
                    )
                    or 0
                )
                final_mutation_receipt_count = int(
                    await database.scalar(
                        sa.select(sa.func.count())
                        .select_from(RunMutationReceiptRow)
                        .where(
                            RunMutationReceiptRow.run_id == runtime.run_id.value
                        )
                    )
                    or 0
                )
                final_participation_count = int(
                    await database.scalar(
                        sa.select(sa.func.count())
                        .select_from(RunSessionParticipationRow)
                        .where(
                            RunSessionParticipationRow.run_id
                            == runtime.run_id.value
                        )
                    )
                    or 0
                )
                final_character = await database.scalar(
                    sa.select(PlayerCharacterCurrentRow).where(
                        PlayerCharacterCurrentRow.player_character_id
                        == runtime.character_ids[0].value
                    )
                )
            assert terminal_session is not None
            assert terminal_session.state_version == 19
            assert terminal_snapshot is not None
            assert terminal_snapshot.state_version == 19
            assert terminal_snapshot.state_json["scenario_runtime"][
                "ending_status"
            ] == "RESOLVED"
            assert terminal_snapshot.state_json["scenario_runtime"]["ending_id"] == (
                terminal_view["ending_id"]
            )
            assert terminal_snapshot.state_json["player_memory"][
                "scenario_records"
            ][0]["status"] == "COMPLETED"
            assert len(events) == 1 + sum(ACTION_EVENT_COUNTS)
            assert [row.sequence_no for row in events] == list(
                range(1, len(events) + 1)
            )
            assert [row.event_type for row in events].count("ScenarioStarted") == 1
            assert [row.event_type for row in events].count(
                "NarrativeOutcomeAccepted"
            ) == 4
            assert "ScenarioDecisionSelected" in {
                row.event_type for row in events
            }
            assert len(requests) == 19
            assert len({row.client_request_id for row in requests}) == 19
            assert all(
                row.response_json is not None and row.error_text is None
                for row in requests
            )
            requests_by_client_id = {
                row.client_request_id: row for row in requests
            }
            assert set(requests_by_client_id) == {
                body["client_request_id"] for body in submitted_actions.values()
            }
            assert len(jobs) == 5
            assert all(row.status == "COMMITTED" for row in jobs)
            for job in jobs:
                request = requests_by_client_id[job.client_request_id]
                assert job.session_id == request.session_id == runtime.session_id
                assert job.turn_id == request.turn_id
                assert job.action_signature == request.action_signature
            local_jobs = [
                row
                for row in jobs
                if row.prompt_schema_version == "local-server-template-v1"
            ]
            provider_jobs = [
                row
                for row in jobs
                if row.prompt_schema_version != "local-server-template-v1"
            ]
            assert len(local_jobs) == 1
            local_job = local_jobs[0]
            terminal_request = requests_by_client_id[
                terminal_submission["client_request_id"]
            ]
            assert local_job.attempt_count == 0
            assert local_job.client_request_id == terminal_request.client_request_id
            assert local_job.turn_id == terminal_request.turn_id == (
                terminal_submission["turn_id"]
            )
            assert local_job.action_signature == terminal_request.action_signature
            assert local_job.prepared_state_version == 18
            assert terminal_request.request_json["action_type"] == "CHOOSE"
            assert terminal_request.request_json["choice_id"] == (
                "death_certificate.action.final_suspend"
            )
            assert terminal_request.response_json is not None
            assert terminal_request.response_json["resulting_state_version"] == 19
            assert terminal_request.response_json["narrative_frame"]["mode"] == (
                "SETTLEMENT"
            )
            assert terminal_request.response_json["narrative_frame"][
                "stop_condition"
            ] == "SCENARIO_ENDED"
            assert len(provider_jobs) == 4
            assert all(row.attempt_count == 1 for row in provider_jobs)
            assert {
                row.client_request_id for row in provider_jobs
            } == {
                submitted_actions[ordinal]["client_request_id"]
                for ordinal in PROVIDER_ACTIONS
            }
            assert final_run is not None
            assert final_run.state_version == 3
            assert final_run.lifecycle_status == "active"
            assert final_run.binding_state == "active"
            assert final_run.active_player_character_id == (
                runtime.character_ids[0].value
            )
            assert final_run_revision_count == 3
            assert final_creation_receipt_count == 1
            assert final_mutation_receipt_count == 2
            assert final_participation_count == 1
            assert final_character is not None
            assert final_character.record_revision == 1
            assert final_character.lifecycle == "active"

            before_terminal_replay = await _family_counts(
                mysql_session_factory, scope
            )
            calls_before_terminal_replay = runtime.provider.calls
            terminal_replay = await _entry(
                client,
                key=entry_key,
                character_id=runtime.character_ids[0].value,
            )
            assert terminal_replay.status_code == 200
            assert terminal_replay.content == admitted.content
            assert await _family_counts(
                mysql_session_factory, scope
            ) == before_terminal_replay
            assert runtime.run_issuer.calls == 1
            assert runtime.line_issuer.calls == 1
            assert runtime.session_generator.calls == 1
            assert runtime.provider.calls == calls_before_terminal_replay == 4
