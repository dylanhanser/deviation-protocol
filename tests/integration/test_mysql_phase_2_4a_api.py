from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    NarrativeProviderMetadata,
    NarrativeRequest,
    NpcUtterance,
    SelectedNarrativeOutcome,
    UntrustedNarrativeProposal,
)
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
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


class ScriptedOpeningProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        candidate = request.outcome_candidates[0]
        description = candidate.safe_description
        speaker = (
            candidate.allowed_entity_ids[0]
            if candidate.allowed_entity_ids
            and (
                "临床复核" in description
                or "生命信号" in description
            )
            else None
        )
        if "记录链" in description:
            scene = "你查阅记录与档案，逐项核对签发时间和记录顺序。"
        elif "审计顺序" in description:
            scene = "你检查审计日志与规程顺序，追踪处置反馈的时间链。"
        elif "地下观察对象" in description:
            scene = "你观察地下患者的生命体征，并复核连续监测记录。"
        elif "临床复核" in description:
            scene = "设备记录了可重复反应，现场开始复核生命体征。"
        elif candidate.allowed_results[0].value == "NO_EFFECT":
            scene = "这次尝试没有形成可验证的新结果，现场状态保持不变。"
        else:
            scene = "你让仍能控制的手指反复敲出节奏，设备显示了可复核的生命信号。"
        return UntrustedNarrativeProposal(
            proposal=NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text=scene * 20,
                referenced_entity_ids=((speaker,) if speaker is not None else ()),
                npc_utterances=((
                    NpcUtterance(
                        speaker_entity_id=speaker,
                        text="我拒绝承认任何结论，只记录设备变化。",
                    ),
                ) if speaker is not None else ()),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=candidate.allowed_results[0],
                    referenced_entity_ids=((speaker,) if speaker is not None else ()),
                ),
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="scripted",
                model="offline-script",
                finish_reason="stop",
                attempts=1,
                latency_ms=0,
            ),
        )

    async def aclose(self) -> None:
        return None


async def _asgi_request(
    app: FastAPI,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    sent = False
    status_code = 500
    response_parts: list[bytes] = []

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_parts.append(message.get("body", b""))

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )
    return status_code, json.loads(b"".join(response_parts))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_play_001_public_api_reaches_early_strategy_after_three_continues(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    player_id = f"phase-2-4a-player-{uuid4().hex}"
    session_id = f"phase-2-4a-{uuid4().hex}"
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    provider = ScriptedOpeningProvider()
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    service = SessionService(
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
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
    app.dependency_overrides[get_current_principal] = lambda: principal

    try:
        created_status, created = await _asgi_request(
            app,
            "POST",
            "/v1/sessions",
            {
                "client_request_id": "create-phase-2-4a",
                "character_definition_id": "character.death_certificate.investigator",
                "scenario_id": "death_certificate",
            },
        )
        assert created_status == 201
        opening_status, opening = await _asgi_request(
            app,
            "POST",
            f"/v1/sessions/{created['session_id']}/actions",
            {
                "turn_id": "opening-turn",
                "client_request_id": "opening-narrative",
                "action_type": "CUSTOM",
                "description": "我尝试有规律地移动手指发出生命信号",
            },
        )
        assert opening_status == 200
        assert opening["narrative_status"] == "COMMITTED"
        assert opening["narrative_frame"]["phase_id"] == (
            "death_certificate.life_disputed"
        )
        assert opening["narrative_frame"]["stop_condition"] == "CONTINUE"

        assert provider.calls == 1
        continue_responses: list[dict[str, Any]] = []
        for index in range(1, 4):
            continue_status, continued = await _asgi_request(
                app,
                "POST",
                f"/v1/sessions/{created['session_id']}/actions",
                {
                    "turn_id": f"continue-turn-{index}",
                    "client_request_id": f"continue-request-{index}",
                    "action_type": "CONTINUE",
                },
            )
            assert continue_status == 200
            assert continued["result_code"] == "SCENARIO_AUTO_BEAT_ADVANCED"
            assert continued["resulting_state_version"] == index + 1
            assert continued["state_changed"] is True
            assert provider.calls == 1
            continue_responses.append(continued)

            async with mysql_session_factory() as database:
                step_session = await database.get(GameSessionRow, session_id)
                step_snapshot = await database.get(GameSnapshotRow, session_id)
            assert step_session is not None
            assert step_snapshot is not None
            assert step_session.state_version == step_snapshot.state_version == index + 1
            assert step_snapshot.state_json["scenario_runtime"][
                "phase_beat_index"
            ] == index

        assert [
            response["narrative_frame"]["stop_condition"]
            for response in continue_responses
        ] == ["CONTINUE", "CONTINUE", "AWAIT_PLAYER"]
        final = continue_responses[-1]
        assert final["narrative_frame"]["phase_id"] == (
            "death_certificate.life_disputed"
        )
        assert final["narrative_frame"]["decision_required"] is True

        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            snapshot_row = await database.get(GameSnapshotRow, session_id)
            events = (
                await database.scalars(
                    select(DomainEventRow)
                    .where(DomainEventRow.session_id == session_id)
                    .order_by(DomainEventRow.sequence_no)
                )
            ).all()
            turn_requests = (
                await database.scalars(
                    select(TurnRequestRow)
                    .where(TurnRequestRow.session_id == session_id)
                    .order_by(TurnRequestRow.client_request_id)
                )
            ).all()
            narrative_jobs = (
                await database.scalars(
                    select(NarrativeJobRow).where(
                        NarrativeJobRow.session_id == session_id
                    )
                )
            ).all()
        assert session_row is not None and session_row.state_version == 4
        assert snapshot_row is not None and snapshot_row.state_version == 4
        runtime = snapshot_row.state_json["scenario_runtime"]
        assert runtime["current_phase_id"] == "death_certificate.life_disputed"
        assert runtime["phase_beat_index"] == 3
        assert runtime["current_decision_id"] == (
            "death_certificate.decision.early_strategy"
        )
        assert runtime["threat_clocks"]["disposal_protocol"] == {
            "clock_id": "disposal_protocol",
            "triggered_thresholds": [3],
            "value": 3,
        }
        assert len(events) == 6
        assert [event.event_type for event in events] == [
            "ScenarioStarted",
            "NarrativeOutcomeAccepted",
            "ScenarioAutoBeatAdvanced",
            "ScenarioAutoBeatAdvanced",
            "ScenarioAutoBeatAdvanced",
            "ScenarioRuntimeEventGenerated",
        ]
        continue_events = [
            event for event in events if event.event_type == "ScenarioAutoBeatAdvanced"
        ]
        assert len(continue_events) == 3
        assert all(
            event.payload_json["source"] == "SERVER_AUTO_ADVANCE"
            for event in continue_events
        )
        assert len(turn_requests) == 4
        persisted_final = next(
            request
            for request in turn_requests
            if request.client_request_id == "continue-request-3"
        )
        assert set(persisted_final.response_json) == {
            *final,
            "action_signature",
        }
        assert all(
            persisted_final.response_json[field] == value
            for field, value in final.items()
        )
        assert len(narrative_jobs) == 1
        assert narrative_jobs[0].status == "COMMITTED"
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.player_id == player_id)
            )

    assert provider.calls == 1
    async with mysql_session_factory() as database:
        residual = []
        for row_type in (
            GameSessionRow,
            GameSnapshotRow,
            DomainEventRow,
            TurnRequestRow,
            NarrativeJobRow,
        ):
            residual.append(
                await database.scalar(
                    select(func.count())
                    .select_from(row_type)
                )
            )
    assert residual == [0, 0, 0, 0, 0]
