from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.api.dependencies import ApiServices, get_current_principal
from deviation_protocol.api.main import create_app
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    NarrativeJobRow,
    TurnRequestRow,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyGameSessionRepository,
    SqlAlchemyNarrativeJobRepository,
)
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.test_mysql_phase_2_4a_api import (
    NOW,
    ScriptedOpeningProvider,
    _asgi_request,
)


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
BUSINESS_ROWS = (
    GameSessionRow,
    GameSnapshotRow,
    DomainEventRow,
    TurnRequestRow,
    NarrativeJobRow,
)


def _build_app(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    *,
    player_id: str,
    session_id: str,
) -> tuple[FastAPI, ScriptedOpeningProvider]:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    provider = ScriptedOpeningProvider()
    clock_value = [NOW]
    principal = RequestPrincipal(
        player_id=player_id, authentication_scheme="integration"
    )
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    service = SessionService(
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: clock_value[0],
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        narrative_provider=provider,
        provider_name="scripted",
        model_name="offline-script",
        clock=lambda: clock_value[0],
        lease_duration=timedelta(minutes=2),
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    services = ApiServices(
        session_service=service,
        turn_orchestrator=orchestrator,
        narrative_provider=provider,
    )
    app = create_app(services=services)
    app.state.api_services = services
    app.state.test_clock = clock_value
    app.dependency_overrides[get_current_principal] = lambda: principal
    return app, provider


async def _create(app: FastAPI, session_id: str, prefix: str) -> dict[str, Any]:
    status, created = await _asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": f"{prefix}-create",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert status == 201
    assert created["session_id"] == session_id
    return created


async def _action(
    app: FastAPI,
    session_id: str,
    request_id: str,
    action_type: str,
    **payload: Any,
) -> dict[str, Any]:
    status, response = await _asgi_request(
        app,
        "POST",
        f"/v1/sessions/{session_id}/actions",
        {
            "turn_id": f"turn-{request_id}",
            "client_request_id": request_id,
            "action_type": action_type,
            **payload,
        },
    )
    assert status == 200, response
    return response


async def _choose(
    app: FastAPI,
    session_id: str,
    request_id: str,
    frame: dict[str, Any],
) -> dict[str, Any]:
    return await _action(
        app,
        session_id,
        request_id,
        "CHOOSE",
        decision_id=frame["decision_id"],
        choice_id=frame["suggested_actions"][0]["action_id"],
    )


def _deadline(response: dict[str, Any]) -> int:
    return next(
        item["value"]
        for item in response["narrative_frame"]["player_visible_clocks"]
        if item["clock_id"] == "predicted_death_deadline"
    )


async def _cleanup_and_assert_empty(
    mysql_session_factory: async_sessionmaker[AsyncSession], player_id: str
) -> None:
    async with mysql_session_factory.begin() as database:
        await database.execute(
            delete(GameSessionRow).where(GameSessionRow.player_id == player_id)
        )
    async with mysql_session_factory() as database:
        counts = [
            await database.scalar(select(func.count()).select_from(row_type))
            for row_type in BUSINESS_ROWS
        ]
    assert counts == [0, 0, 0, 0, 0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_public_api_complete_happy_path_commits_ending_and_memory(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    player_id = f"phase-2-4b-happy-player-{uuid4().hex}"
    session_id = f"phase-2-4b-happy-{uuid4().hex}"
    app, provider = _build_app(
        mysql_session_factory, player_id=player_id, session_id=session_id
    )
    try:
        await _create(app, session_id, "happy")
        current = await _action(
            app,
            session_id,
            "happy-opening",
            "CUSTOM",
            description="我有规律地移动手指，发出可复核的生命信号",
        )
        current = await _action(
            app,
            session_id,
            "happy-recheck",
            "TALK",
            dialogue="请协调员复核我的连续回应和生命体征",
        )
        current = await _action(app, session_id, "happy-life-1", "CONTINUE")
        current = await _action(app, session_id, "happy-life-2", "CONTINUE")
        current = await _choose(app, session_id, "happy-early", current["narrative_frame"])
        current = await _action(app, session_id, "happy-escape-1", "CONTINUE")
        current = await _action(app, session_id, "happy-escape-2", "CONTINUE")
        current = await _action(app, session_id, "happy-investigation-1", "CONTINUE")
        current = await _choose(
            app, session_id, "happy-investigation-choice", current["narrative_frame"]
        )
        current = await _action(
            app,
            session_id,
            "happy-records",
            "EXPLORE",
            description="沿记录与档案审计路径核对签发时间",
        )
        records_replay = await _action(
            app,
            session_id,
            "happy-records",
            "EXPLORE",
            description="沿记录与档案审计路径核对签发时间",
        )
        assert records_replay == current
        assert provider.calls == 3
        current = await _action(
            app,
            session_id,
            "happy-audit",
            "EXPLORE",
            description="核对日志时间顺序以及规程反馈",
        )
        current = await _choose(
            app, session_id, "happy-investigation-choice-2", current["narrative_frame"]
        )
        current = await _action(
            app,
            session_id,
            "happy-patient",
            "OBSERVE",
            description="复核地下患者的生命体征与连续监测历史",
        )
        current = await _action(app, session_id, "happy-truth-1", "CONTINUE")
        current = await _action(app, session_id, "happy-truth-2", "CONTINUE")
        for index in range(1, 4):
            current = await _choose(
                app,
                session_id,
                f"happy-core-{index}",
                current["narrative_frame"],
            )
        version_before_ending = current["resulting_state_version"]
        async with mysql_session_factory() as database:
            events_before_ending = await database.scalar(
                select(func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.session_id == session_id)
            )
        original_job_add = SqlAlchemyNarrativeJobRepository.add

        async def fail_after_local_job_staging(
            repository: SqlAlchemyNarrativeJobRepository,
            job: Any,
        ) -> None:
            await original_job_add(repository, job)
            if job.prompt_schema_version == "local-server-template-v1":
                raise RuntimeError("injected rollback after local settlement job")

        monkeypatch.setattr(
            SqlAlchemyNarrativeJobRepository,
            "add",
            fail_after_local_job_staging,
        )
        final_frame = current["narrative_frame"]
        with pytest.raises(
            RuntimeError, match="injected rollback after local settlement job"
        ):
            await _asgi_request(
                app,
                "POST",
                f"/v1/sessions/{session_id}/actions",
                {
                    "turn_id": "turn-happy-core-4",
                    "client_request_id": "happy-core-4",
                    "action_type": "CHOOSE",
                    "decision_id": final_frame["decision_id"],
                    "choice_id": final_frame["suggested_actions"][0]["action_id"],
                },
            )
        async with mysql_session_factory() as database:
            rolled_session = await database.get(GameSessionRow, session_id)
            rolled_snapshot = await database.get(GameSnapshotRow, session_id)
            rolled_events = await database.scalar(
                select(func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.session_id == session_id)
            )
            rolled_job = await database.scalar(
                select(NarrativeJobRow).where(
                    NarrativeJobRow.session_id == session_id,
                    NarrativeJobRow.client_request_id == "happy-core-4",
                )
            )
        assert rolled_session is not None
        assert rolled_session.state_version == version_before_ending
        assert rolled_snapshot is not None
        assert rolled_snapshot.state_version == version_before_ending
        assert rolled_snapshot.state_json["player_memory"]["scenario_records"][0][
            "status"
        ] == "STARTED"
        assert rolled_events == events_before_ending
        assert rolled_job is None
        monkeypatch.setattr(
            SqlAlchemyNarrativeJobRepository,
            "add",
            original_job_add,
        )
        current = await _choose(
            app, session_id, "happy-core-4", final_frame
        )
        assert current["narrative_frame"]["stop_condition"] == "SCENARIO_ENDED"
        assert _deadline(current) < 13
        assert provider.calls == 5

        view_status, view = await _asgi_request(
            app, "GET", f"/v1/sessions/{session_id}/view"
        )
        assert view_status == 200
        assert view["ending_id"] == "death_certificate.ending.protocol_broken"
        assert view["player_memory"]["scenarios"][0]["status"] == "COMPLETED"

        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            snapshot_row = await database.get(GameSnapshotRow, session_id)
            event_types = (
                await database.scalars(
                    select(DomainEventRow.event_type)
                    .where(DomainEventRow.session_id == session_id)
                    .order_by(DomainEventRow.sequence_no)
                )
            ).all()
            settlement_job = await database.scalar(
                select(NarrativeJobRow).where(
                    NarrativeJobRow.session_id == session_id,
                    NarrativeJobRow.client_request_id == "happy-core-4",
                )
            )
        assert session_row is not None and snapshot_row is not None
        assert session_row.state_version == snapshot_row.state_version
        assert snapshot_row.state_json["scenario_runtime"]["ending_status"] == "RESOLVED"
        assert "ScenarioDecisionSelected" in event_types
        assert settlement_job is not None
        assert settlement_job.status == "COMMITTED"
        assert settlement_job.prompt_schema_version == "local-server-template-v1"
        assert settlement_job.attempt_count == 0
        assert settlement_job.accepted_narrative_text == current["narrative_text"]
    finally:
        await _cleanup_and_assert_empty(mysql_session_factory, player_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_deadline_path_rolls_back_then_deduplicates_and_completes(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    player_id = f"phase-2-4b-deadline-player-{uuid4().hex}"
    session_id = f"phase-2-4b-deadline-{uuid4().hex}"
    app, provider = _build_app(
        mysql_session_factory, player_id=player_id, session_id=session_id
    )
    original_save = SqlAlchemyGameSessionRepository.save_snapshot_and_events
    try:
        await _create(app, session_id, "deadline")
        current = await _action(
            app,
            session_id,
            "deadline-opening",
            "CUSTOM",
            description="我有规律地移动手指，发出可复核的生命信号",
        )

        async def fail_after_staging(
            repository: SqlAlchemyGameSessionRepository,
            session: Any,
            state: Any,
            events: Any,
            expected_state_version: int,
        ) -> None:
            await original_save(
                repository, session, state, events, expected_state_version
            )
            raise RuntimeError("injected rollback after staging")

        current = await _action(app, session_id, "deadline-life-1", "CONTINUE")
        duplicate = await _action(app, session_id, "deadline-life-1", "CONTINUE")
        assert duplicate == current
        current = await _action(app, session_id, "deadline-life-2", "CONTINUE")
        current = await _action(app, session_id, "deadline-life-3", "CONTINUE")
        current = await _choose(
            app, session_id, "deadline-early", current["narrative_frame"]
        )
        current = await _action(app, session_id, "deadline-escape-1", "CONTINUE")
        current = await _action(app, session_id, "deadline-escape-2", "CONTINUE")
        no_effect = 0
        while _deadline(current) < 12:
            if current["narrative_frame"]["decision_required"]:
                current = await _choose(
                    app,
                    session_id,
                    f"deadline-choice-{no_effect}",
                    current["narrative_frame"],
                )
            else:
                no_effect += 1
                current = await _action(
                    app,
                    session_id,
                    f"deadline-no-effect-{no_effect}",
                    "CUSTOM",
                    description="等待并重复与线索无关的动作",
                )
        assert _deadline(current) == 12
        version_before_ending = current["resulting_state_version"]
        async with mysql_session_factory() as database:
            events_before_ending = await database.scalar(
                select(func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.session_id == session_id)
            )

        monkeypatch.setattr(
            SqlAlchemyGameSessionRepository,
            "save_snapshot_and_events",
            fail_after_staging,
        )
        with pytest.raises(RuntimeError, match="injected rollback after staging"):
            await _asgi_request(
                app,
                "POST",
                f"/v1/sessions/{session_id}/actions",
                {
                    "turn_id": "turn-deadline-final-no-effect",
                    "client_request_id": "deadline-final-no-effect",
                    "action_type": "CUSTOM",
                    "description": "等待并重复与线索无关的动作",
                },
            )
        async with mysql_session_factory() as database:
            rolled_session = await database.get(GameSessionRow, session_id)
            rolled_snapshot = await database.get(GameSnapshotRow, session_id)
            rolled_events = await database.scalar(
                select(func.count())
                .select_from(DomainEventRow)
                .where(DomainEventRow.session_id == session_id)
            )
        assert rolled_session is not None
        assert rolled_session.state_version == version_before_ending
        assert rolled_snapshot is not None
        assert rolled_snapshot.state_version == version_before_ending
        assert rolled_snapshot.state_json["scenario_runtime"]["threat_clocks"][
            "predicted_death_deadline"
        ]["value"] == 12
        assert rolled_snapshot.state_json["player_memory"]["scenario_records"][0][
            "status"
        ] == "STARTED"
        assert rolled_events == events_before_ending

        monkeypatch.setattr(
            SqlAlchemyGameSessionRepository,
            "save_snapshot_and_events",
            original_save,
        )
        app.state.test_clock[0] += timedelta(minutes=3)
        current = await _action(
            app,
            session_id,
            "deadline-final-no-effect",
            "CUSTOM",
            description="等待并重复与线索无关的动作",
        )
        duplicate = await _action(
            app,
            session_id,
            "deadline-final-no-effect",
            "CUSTOM",
            description="等待并重复与线索无关的动作",
        )
        assert duplicate == current
        assert _deadline(current) == 13
        assert current["narrative_frame"]["stop_condition"] == "SCENARIO_ENDED"
        view_status, view = await _asgi_request(
            app, "GET", f"/v1/sessions/{session_id}/view"
        )
        assert view_status == 200
        assert view["ending_id"] == "death_certificate.ending.deadline_reached"
        assert view["player_memory"]["scenarios"][0]["status"] == "COMPLETED"
        assert provider.calls == 7
    finally:
        monkeypatch.setattr(
            SqlAlchemyGameSessionRepository,
            "save_snapshot_and_events",
            original_save,
        )
        await _cleanup_and_assert_empty(mysql_session_factory, player_id)
