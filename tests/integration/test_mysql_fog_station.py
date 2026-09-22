"""Dedicated-test-DB public native slice; no DDL, only task-owned row cleanup."""
import asyncio
from copy import deepcopy
from uuid import uuid4

import httpx
import pytest
import sqlalchemy as sa

from deviation_protocol.api import main
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.test_mysql_run_entry_playthrough import _Scope, _delete_scope
from tests.unit.test_native_run_entry_api import body
from tests.unit.test_opening_talents import offer, confirm
from tests.unit.test_escort_encounter import view, request

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("branch", ["all_activities", "early_departure", "decline"])
async def test_production_native_station_atomic_recovery_and_exit(mysql_engine, mysql_session_factory, monkeypatch, branch):
    # mysql_engine validates driver and exact dedicated database before connecting.
    async with mysql_session_factory() as db:
        initial_head = await db.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert initial_head == "20260921_0012", "deploy actual migration head separately; this test never changes schema"
    token = uuid4().hex
    scope = _Scope(token=token)
    monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
    def no_provider():
        raise ValueError("Provider disabled")
    monkeypatch.setattr(main.DeepSeekSettings, "from_environment", no_provider)
    bindings = [ConfiguredControllerBinding(authentication_scheme="demo-dev-only", player_id="demo-player", controller_id="station."+token)]
    def services():
        return main.build_default_services(player_character_controller_bindings=bindings)
    app = main.create_app(services=services())
    app.state.api_services = services()
    sid = None
    async def stored():
        async with mysql_session_factory() as db:
            current = await db.get(orm.GameSessionRow, sid)
            snap = await db.scalar(sa.select(orm.GameSnapshotRow.state_json).where(orm.GameSnapshotRow.session_id == sid))
            counts = tuple([await db.scalar(sa.select(sa.func.count()).select_from(model).where(model.session_id == sid))
                            for model in (orm.DomainEventRow, orm.NarrativeJobRow, orm.TurnRequestRow)])
            return current.state_version, deepcopy(snap), counts
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/v1/player-characters", headers={"Idempotency-Key": "station."+token},
                json={"contract_version":"structured-player-character/v1", "character_core":{}, "narration_preferences":{}})
            assert created.status_code == 200, created.text
            cid = created.json()["player_character_id"]["value"]
            scope.player_character_ids.add(cid)
            async with mysql_session_factory() as db:
                character = await db.get(orm.PlayerCharacterCurrentRow, cid)
                scope.controller_bindings.add(character.controller_binding)
            intent = body(cid)
            intent["entry_world"] = {"entry_world_id":"world.fog_station", "entry_world_version":1}
            record = await offer(client, intent, "station.prepare."+token)
            results = await asyncio.gather(*(confirm(client, record) for _ in range(3)))
            assert all(r.status_code == 200 and r.json() == results[0].json() for r in results), [r.text for r in results]
            admitted = results[0].json()["result"]
            sid = admitted["session_id"]
            scope.session_ids.add(sid)
            scope.run_ids.add(admitted["run_context"]["run_id"])
            labels = ["走近并与巡路员会面", "配合岑舟固定挡板", "暂缓离开，留下帮忙收尾", "完成观察记录的收尾"]
            if branch == "decline":
                labels += ["谢绝暂住并道别"]
            else:
                labels += ["接受邀请，入住哨站"]
                if branch == "all_activities":
                    labels += ["复盘脱险", "听一段已公开的巡路往事", "一起整理观察记录"]
                labels += ["结束暂住，明确离开", "沿观察台护栏确认雾中灯光", "回门口向岑舟道别"]
            for number, label in enumerate(labels):
                before = await stored()
                current = await view(client, sid)
                assert await stored() == before
                action = request(current, label, f"station.{number}")
                if number == 1:
                    async def fail_commit(self):
                        raise RuntimeError("station rollback")
                    with monkeypatch.context() as patch:
                        patch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
                        with pytest.raises(RuntimeError, match="station rollback"):
                            await client.post(f"/v1/sessions/{sid}/actions", json=action)
                    assert await stored() == before
                responses = await asyncio.gather(*(client.post(f"/v1/sessions/{sid}/actions", json=action) for _ in range(2)))
                assert all(r.status_code == 200 and r.json() == responses[0].json() for r in responses)
                assert responses[0].json()["state_changed"]
                saved = await stored()
                assert saved[0] == number+1 and saved[2][1:] == (number+1, number+1)
                # New production graph, repositories and DB connection for recovery.
                app.state.api_services = services()
                assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == responses[0].json()
                assert await stored() == saved
            current = await view(client, sid)
            assert current["scenario_status"] == "ENDED"
            assert current["relationship"]["stage"] == "信任"
            assert (await confirm(client, record)).json()["result"] == admitted
            exited = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"station.exit."+token},
                json={"expected_run_state_version":3,"expected_session_state_version":len(labels)})
            assert exited.status_code == 200, exited.text
            assert (await view(client, sid))["relationship"] == current["relationship"]
    finally:
        # Identify only this test's admission rows, including a successful lost response.
        async with mysql_session_factory.begin() as db:
            rows = (await db.scalars(sa.select(orm.OpeningPreparationRow).where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))).all()
            scope.run_ids.update(r.run_id for r in rows if r.run_id)
            if scope.run_ids:
                scope.session_ids.update((await db.scalars(sa.select(orm.RunSessionParticipationRow.session_id).where(orm.RunSessionParticipationRow.run_id.in_(scope.run_ids)))).all())
            await db.execute(sa.delete(orm.OpeningPreparationRow).where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))
            for model in (orm.RunEntryWorldBindingRow, orm.RunProtocolBindingRow):
                await db.execute(sa.delete(model).where(model.run_id.in_(scope.run_ids)))
        await _delete_scope(mysql_session_factory, scope)
        async with mysql_session_factory() as db:
            assert await db.scalar(sa.text("SELECT version_num FROM alembic_version")) == initial_head
