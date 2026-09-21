"""Bounded public Session proof on the established test-only MySQL harness.

No DDL or server lifecycle operations. Only rows belonging to the generated
Session IDs are created and deleted; the fixture validates the test DB name.
"""
from copy import deepcopy
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select, func

from deviation_protocol.api import main
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.application.escort_encounter import CONTENT_IDENTITY
from deviation_protocol.infrastructure.orm_models import (
    GameSessionRow, GameSnapshotRow, DomainEventRow, TurnRequestRow, NarrativeJobRow,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.mark.parametrize("route", ["steady", "recover", "rush", "withdraw"])
async def test_public_escort_sql_atomic_reload_and_replay(mysql_engine, mysql_session_factory, monkeypatch, route):
    monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
    def no_settings():
        raise ValueError("real Provider disabled for this test")
    monkeypatch.setattr(main.DeepSeekSettings, "from_environment", no_settings)
    services = main.build_default_services(player_character_controller_bindings=[ConfiguredControllerBinding(authentication_scheme="demo-dev-only", player_id="demo-player", controller_id="controller.escort-test")])
    bundle = services.content_registry.resolve(*CONTENT_IDENTITY)
    provider = AsyncMock()
    bundle.turn_orchestrator.narrative_provider = provider
    sid = None
    app = main.create_app(services=services)
    async def stored():
        async with mysql_session_factory() as db:
            version = await db.scalar(select(GameSessionRow.state_version).where(GameSessionRow.session_id == sid))
            snapshot = await db.scalar(select(GameSnapshotRow.state_json).where(GameSnapshotRow.session_id == sid))
            counts = tuple([await db.scalar(select(func.count()).select_from(t).where(t.session_id == sid))
                            for t in (DomainEventRow, TurnRequestRow, NarrativeJobRow)])
            return version, deepcopy(snapshot), counts
    try:
        async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/v1/sessions", json={"client_request_id": "it-escort-" + uuid4().hex,
                "scenario_id": "wind_gate", "character_definition_id": "character.wind_gate.traveler"})
            assert created.status_code == 201, created.text
            sid = created.json()["session_id"]
            labels = {"steady": ["先扶稳同行者", "沿扶手护送到出口", "结伴进入候船室"],
                      "recover": ["立即带向通道", "停步抓牢扶手，扶稳对方", "结伴进入候船室"],
                      "rush": ["立即带向通道", "继续抢行"], "withdraw": ["一起撤入避风间"]}[route]
            first_body = first_response = None
            for step, label in enumerate(labels, 1):
                before = await stored()
                current_response = await client.get(f"/v1/sessions/{sid}/view")
                assert current_response.status_code == 200, current_response.text
                current = current_response.json()
                assert await stored() == before
                choices = current["action_affordances"]
                choice = next(c for c in choices["choices"] if c["label"] == label)
                body = {"action_type": "CHOOSE", "decision_id": choices["decision_id"],
                        "choice_id": choice["choice_id"], "turn_id": f"step-{step}", "client_request_id": f"request-{step}"}
                if step == 1:
                    # Fail after events and snapshot have been flushed, immediately
                    # before transaction commit; fresh connections must see no delta.
                    async def fail_commit(self):
                        raise RuntimeError("escort-injected-before-commit")
                    with monkeypatch.context() as m:
                        m.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
                        with pytest.raises(RuntimeError, match="escort-injected-before-commit"):
                            await client.post(f"/v1/sessions/{sid}/actions", json=body)
                    assert await stored() == before
                response = await client.post(f"/v1/sessions/{sid}/actions", json=body)
                assert response.status_code == 200, response.text
                assert response.json()["resulting_state_version"] == step
                assert response.json()["state_changed"]
                if step == 1:
                    first_body, first_response = body, response.json()
                saved = await stored()
                assert saved[0] == step and saved[2][1:] == (step, step)
                assert (await client.post(f"/v1/sessions/{sid}/actions", json=body)).json() == response.json()
                assert await stored() == saved
                # Rebuild the normal production service graph between actions.
                # This proves fresh-service/connection snapshot reload, not a DB restart.
                app.state.api_services = main.build_default_services(player_character_controller_bindings=[ConfiguredControllerBinding(authentication_scheme="demo-dev-only", player_id="demo-player", controller_id="controller.escort-test")])
            ended = (await client.get(f"/v1/sessions/{sid}/view")).json()
            assert ended["encounter"]["condition"] is None
            assert ended["encounter"]["outcome"] == ("SUCCESS" if route in ("steady", "recover") else "SAFE_WITHDRAWAL")
            saved = await stored()
            assert (await client.post(f"/v1/sessions/{sid}/actions", json=first_body)).json() == first_response
            assert await stored() == saved
            assert not ended.get("run_context")
            provider.generate.assert_not_called()
    finally:
        if sid is not None:
            async with mysql_session_factory.begin() as db:
                await db.execute(delete(GameSessionRow).where(GameSessionRow.session_id == sid))
            async with mysql_session_factory() as db:
                for table in (GameSessionRow, GameSnapshotRow, DomainEventRow, TurnRequestRow, NarrativeJobRow):
                    assert await db.scalar(select(func.count()).select_from(table).where(table.session_id == sid)) == 0
