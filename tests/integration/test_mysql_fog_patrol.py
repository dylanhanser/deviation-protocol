"""Dedicated MySQL proof with exact initial schema/data restoration."""
import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from deviation_protocol.api import main
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.infrastructure.repositories import SqlAlchemyRunWorldContinuationRepository
from tests.integration.test_mysql_world_continuation_migration import migrate_to, schema_state
from tests.integration.test_mysql_run_entry_playthrough import _Scope, _delete_scope
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.unit.test_native_run_entry_api import body
from tests.unit.test_opening_talents import offer, confirm
from tests.unit.test_escort_encounter import view, request

pytestmark = pytest.mark.integration
HEAD = "20260922_0013"


@asynccontextmanager
async def deployed(engine):
    initial = await schema_state(engine)
    original = initial[0]["alembic_version"][1][0][0]
    try:
        await migrate_to(engine, HEAD)
        yield
    finally:
        await migrate_to(engine, original)
        assert await schema_state(engine) == initial


@pytest.mark.parametrize("entry_kind", ["talent", "native"])
async def test_original_admission_receipt_replay_across_fog_lifecycle(
        mysql_engine, mysql_session_factory, monkeypatch, entry_kind):
    from tests.unit.test_fog_patrol import original_admission_replay_lifecycle
    async with deployed(mysql_engine):
        token = uuid4().hex
        scope = _Scope(token=token)
        monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
        def no_provider():
            raise ValueError("Provider disabled")
        monkeypatch.setattr(main.DeepSeekSettings, "from_environment", no_provider)
        bindings = [ConfiguredControllerBinding(authentication_scheme="demo-dev-only",
            player_id="demo-player", controller_id="r1." + token)]
        def services():
            return main.build_default_services(player_character_controller_bindings=bindings)
        app = main.create_app(services=services())
        app.state.api_services = services()
        async def read_state():
            # Includes every persisted row/count, receipts, participations, events,
            # character/Run state, snapshots and CHECK enforcement; lock is free.
            return await schema_state(mysql_engine)
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                created = await client.post("/v1/player-characters",
                    headers={"Idempotency-Key": "r1.character." + token},
                    json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}})
                assert created.status_code == 200, created.text
                cid = created.json()["player_character_id"]["value"]
                scope.player_character_ids.add(cid)
                async with mysql_session_factory() as db:
                    scope.controller_bindings.add((await db.get(orm.PlayerCharacterCurrentRow, cid)).controller_binding)
                intent = body(cid)
                intent["entry_world"] = {"entry_world_id": "world.fog_station", "entry_world_version": 1}
                await original_admission_replay_lifecycle(client, app, intent, entry_kind,
                    scope, read_state, rebuild=services)
        finally:
            async with mysql_session_factory.begin() as db:
                # Include any committed admission/continuation whose response was
                # lost, restricted to this test's character, before FK-order cleanup.
                scope.run_ids.update((await db.scalars(sa.select(orm.RunCurrentRow.run_id)
                    .where(orm.RunCurrentRow.binding_player_character_id.in_(scope.player_character_ids)))).all())
                scope.session_ids.update((await db.scalars(sa.select(orm.RunSessionParticipationRow.session_id)
                    .where(orm.RunSessionParticipationRow.run_id.in_(scope.run_ids)))).all())
                await db.execute(sa.delete(orm.OpeningPreparationRow)
                    .where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))
                for model in (orm.RunWorldPositionRow, orm.RunWorldVisitEntryRow, orm.RunWorldVisitRow,
                        orm.RunWorldStateRow, orm.RunEntryWorldBindingRow, orm.RunProtocolBindingRow):
                    await db.execute(sa.delete(model).where(model.run_id.in_(scope.run_ids)))
            await _delete_scope(mysql_session_factory, scope)


async def test_migration_only_extends_three_checks_and_recovers_interrupted_ddl(mysql_engine, monkeypatch):
    initial = await schema_state(mysql_engine)
    original = initial[0]["alembic_version"][1][0][0]
    try:
        await migrate_to(mysql_engine, "20260921_0012")
        before = await schema_state(mysql_engine)
        module = SCRIPT.get_revision(HEAD).module
        alter = module._alter
        def fail(connection, table, checks):
            if table == "run_world_visit_entries" and checks == module.NEW[table]:
                raise RuntimeError("injected second patrol ALTER")
            return alter(connection, table, checks)
        with monkeypatch.context() as patch:
            patch.setattr(module, "_alter", fail)
            with pytest.raises(RuntimeError, match="injected second patrol ALTER"):
                await migrate_to(mysql_engine, HEAD)
        assert await schema_state(mysql_engine) == before
        await migrate_to(mysql_engine, HEAD)
        after = await schema_state(mysql_engine)
        assert set(before[0]) == set(after[0])
        for name, (ddl, rows) in before[0].items():
            if name != "alembic_version":
                assert after[0][name][1] == rows
            if name not in ("run_world_states", "run_world_visit_entries", "alembic_version"):
                assert after[0][name][0] == ddl
        assert before[1] == after[1]  # Names, keys, CHECK enforcement unchanged.
        async with mysql_engine.connect() as connection:
            assert await connection.run_sync(lambda c: compare_metadata(MigrationContext.configure(c), orm.Base.metadata)) == []
        await migrate_to(mysql_engine, "20260921_0012")
        assert await schema_state(mysql_engine) == before
    finally:
        await migrate_to(mysql_engine, original)
    assert await schema_state(mysql_engine) == initial


@pytest.mark.parametrize("branch,helping,race", [("immediate", True, "duplicate"), ("declined", False, "duplicate"),
    ("finished", False, "duplicate"), ("reunited", True, "duplicate"),
    ("immediate", True, "competing"), ("immediate", False, "exit")])
async def test_production_patrol_atomic_play_recovery_replay(mysql_engine, mysql_session_factory, monkeypatch, branch, helping, race):
    async with deployed(mysql_engine):
        token = uuid4().hex
        scope = _Scope(token=token)
        monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
        def no_provider():
            raise ValueError("Provider disabled")
        monkeypatch.setattr(main.DeepSeekSettings, "from_environment", no_provider)
        bindings = [ConfiguredControllerBinding(authentication_scheme="demo-dev-only", player_id="demo-player", controller_id="patrol."+token)]
        def services():
            return main.build_default_services(player_character_controller_bindings=bindings)
        app = main.create_app(services=services())
        app.state.api_services = services()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                created = await client.post("/v1/player-characters", headers={"Idempotency-Key":"patrol."+token},
                    json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
                assert created.status_code == 200, created.text
                cid = created.json()["player_character_id"]["value"]
                scope.player_character_ids.add(cid)
                async with mysql_session_factory() as db:
                    scope.controller_bindings.add((await db.get(orm.PlayerCharacterCurrentRow, cid)).controller_binding)
                intent = body(cid)
                intent["entry_world"] = {"entry_world_id":"world.fog_station","entry_world_version":1}
                prep = await offer(client, intent, "prepare."+token)
                admitted = await confirm(client, prep)
                assert admitted.status_code == 200, admitted.text
                source = admitted.json()["result"]["session_id"]
                scope.session_ids.add(source)
                scope.run_ids.add(admitted.json()["result"]["run_context"]["run_id"])
                labels = ["走近并与巡路员会面","配合岑舟固定挡板"]
                if branch == "immediate":
                    labels += ["现在离开哨站"]
                else:
                    labels += ["暂缓离开，留下帮忙收尾","完成观察记录的收尾"]
                    if branch == "declined":
                        labels += ["谢绝暂住并道别"]
                    else:
                        labels += ["接受邀请，入住哨站"]
                        if branch == "reunited":
                            labels += ["复盘脱险","听一段已公开的巡路往事","一起整理观察记录"]
                        labels += ["结束暂住，明确离开","沿观察台护栏确认雾中灯光", "回门口向岑舟道别" if branch == "reunited" else "直接结束这段行程"]
                for i,label in enumerate(labels):
                    response = await client.post(f"/v1/sessions/{source}/actions", json=request(await view(client, source),label,f"source.{i}"))
                    assert response.status_code == 200 and response.json()["state_changed"], response.text
                source_view = await view(client, source)
                before = await schema_state(mysql_engine)
                command = dict(expected_run_state_version=3,expected_session_state_version=len(labels))
                async def continue_run(key="continue"):
                    return await client.post(f"/v1/sessions/{source}/run-continuation",json=command,headers={"Idempotency-Key":key+token})
                original_add = SqlAlchemyRunWorldContinuationRepository.add
                async def fail(self,family):
                    await original_add(self,family)
                    raise RuntimeError("patrol SQL rollback")
                with monkeypatch.context() as patch:
                    patch.setattr(SqlAlchemyRunWorldContinuationRepository,"add",fail)
                    with pytest.raises(RuntimeError,match="patrol SQL rollback"):
                        await continue_run()
                assert await schema_state(mysql_engine) == before
                rival = (client.post(f"/v1/sessions/{source}/run-exit", json=command,
                    headers={"Idempotency-Key":"rival.exit"+token}) if race == "exit" else continue_run("rival" if race == "competing" else "continue"))
                replies = await asyncio.gather(continue_run(), rival)
                assert sorted(r.status_code for r in replies) == ([200,200] if race == "duplicate" else [200,409]), [r.text for r in replies]
                if race == "duplicate":
                    assert replies[0].json() == replies[1].json()
                if race == "exit" and replies[1].status_code == 200:
                    before = await schema_state(mysql_engine)
                    assert (await continue_run("after.exit")).status_code == 409
                    assert await schema_state(mysql_engine) == before
                    return
                if race == "competing" and replies[1].status_code == 200:
                    # Restore the winner's exact key for later receipt replay.
                    original_continue = continue_run
                    async def continue_run(key="rival"):
                        return await original_continue(key)
                    replies.reverse()
                result = replies[0].json()
                sid = result["session_id"]
                scope.session_ids.add(sid)
                stored = await schema_state(mysql_engine)
                assert (await continue_run("competing")).status_code == 409
                assert await schema_state(mysql_engine) == stored
                with pytest.raises(RuntimeError,match="Patrol evidence exists"):
                    await migrate_to(mysql_engine,"20260921_0012")
                assert await schema_state(mysql_engine) == stored
                async with mysql_session_factory.begin() as db:
                    # The new entry must never accept the old joined revision.
                    from sqlalchemy.exc import OperationalError
                    with pytest.raises(OperationalError,match="ck_run_world_visit_entries_version"):
                        await db.execute(sa.update(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.session_id==sid).values(joined_state_version=5))
                    await db.rollback()
                assert await schema_state(mysql_engine) == stored
                for i,label in enumerate(("走近岑舟，打个招呼", "在护栏内拉稳绳索，协助拆灯" if helping else "沿背风小径安全绕行",
                        "向岑舟道别，离开风口" if helping else "向岑舟道别，继续走远")):
                    app.state.api_services = services()
                    before = await schema_state(mysql_engine)
                    current = await view(client,sid)
                    assert current["metadata"]["state_version"] == i
                    assert (await client.get(f"/v1/sessions/{sid}/run-journey")).status_code == 200
                    assert (await client.get(f"/v1/sessions/{sid}/run-recap")).json()["status"] == "complete"
                    assert await schema_state(mysql_engine) == before
                    action = request(current,label,f"destination.{i}")
                    reply = await client.post(f"/v1/sessions/{sid}/actions",json=action)
                    assert reply.status_code == 200 and reply.json()["state_changed"],reply.text
                    app.state.api_services = services()
                    assert (await client.post(f"/v1/sessions/{sid}/actions",json=action)).json()==reply.json()
                assert (await view(client,sid))["scenario_status"] == "ENDED"
                assert await view(client,source) == source_view
                assert (await continue_run()).json() == result
                exited = await client.post(f"/v1/sessions/{sid}/run-exit",json={"expected_run_state_version":4,"expected_session_state_version":3},headers={"Idempotency-Key":"exit."+token})
                assert exited.status_code == 200 and exited.json()["lifecycle_status"]=="terminated",exited.text
                app.state.api_services=services()
                assert (await view(client,sid))["scenario_status"] == "ENDED"
                assert (await client.get("/v1/player-characters/eligible-for-run-entry")).status_code==200
        finally:
            # Discover any committed lost response by this test's character only.
            async with mysql_session_factory.begin() as db:
                rows=(await db.scalars(sa.select(orm.OpeningPreparationRow).where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))).all()
                scope.run_ids.update(r.run_id for r in rows if r.run_id)
                scope.session_ids.update((await db.scalars(sa.select(orm.RunSessionParticipationRow.session_id).where(orm.RunSessionParticipationRow.run_id.in_(scope.run_ids)))).all())
                await db.execute(sa.delete(orm.OpeningPreparationRow).where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))
                for model in (orm.RunWorldPositionRow,orm.RunWorldVisitEntryRow,orm.RunWorldVisitRow,orm.RunWorldStateRow,orm.RunEntryWorldBindingRow,orm.RunProtocolBindingRow):
                    await db.execute(sa.delete(model).where(model.run_id.in_(scope.run_ids)))
            await _delete_scope(mysql_session_factory,scope)


@pytest.mark.parametrize("phase", ["GET_LOCK", "RELEASE_LOCK"])
async def test_migration_failed_lock_result_discards_owner_and_preserves_primary(mysql_engine, monkeypatch, phase):
    from tests.integration.test_mysql_native_run_migration import _ConnectionView, observe
    initial = await schema_state(mysql_engine)
    module = SCRIPT.get_revision(HEAD).module
    sentinel = RuntimeError("patrol body sentinel")
    async with mysql_engine.connect() as connection:
        owner = await connection.scalar(sa.text("SELECT CONNECTION_ID()"))
        await connection.rollback()
        def run(sync):
            proxy = _ConnectionView(sync, mysql_engine, owner, result_override=(phase, None))
            with monkeypatch.context() as patch:
                patch.setattr(module.op, "get_bind", lambda: proxy)
                with module._locked():
                    raise sentinel
        with pytest.raises(RuntimeError) as caught:
            await connection.run_sync(run)
        if phase == "RELEASE_LOCK":
            assert caught.value is sentinel and isinstance(sentinel.cleanup_error, RuntimeError)
        else:
            assert "Could not lock" in str(caught.value)
    await observe(mysql_engine, owner)
    assert await schema_state(mysql_engine) == initial


async def test_migration_preserves_nonempty_old_roots_entries_and_exact_replay(mysql_engine, monkeypatch):
    from tests.integration.test_mysql_world_continuation import continuation_case
    from tests.integration.test_mysql_world_revisit import held_source, revisit
    # This fixture's supported original-schema precondition is checked by the
    # fixture itself. Never combine it with an independently deployed schema.
    async with continuation_case(mysql_engine, monkeypatch, head="20260921_0012") as case:
        try:
            entered, _, _, old_body, continued, held = await held_source(case)
            response = await revisit(case, held)
            assert response.status_code == 200, response.text
            result = response.json()
            case.scope.session_ids.add(result["session_id"])
            old = await schema_state(mysql_engine)
            assert old[0]["run_world_states"][1] and old[0]["run_world_visit_entries"][1]
            await migrate_to(mysql_engine, HEAD)
            upgraded = await schema_state(mysql_engine)
            for name, (_, rows) in old[0].items():
                if name != "alembic_version":
                    assert upgraded[0][name][1] == rows
            assert (await revisit(case, held)).json() == result
            replay = await case.client.post(f'/v1/sessions/{entered["session_id"]}/run-continuation',
                json=old_body, headers={"Idempotency-Key":"s7.2.continue"})
            assert replay.status_code == 200 and replay.json() == continued, replay.text
            assert (await case.client.get(f'/v1/sessions/{result["session_id"]}/view')).status_code == 200
            assert await schema_state(mysql_engine) == upgraded
            await migrate_to(mysql_engine, "20260921_0012")
            assert await schema_state(mysql_engine) == old
        finally:
            await migrate_to(mysql_engine, "20260921_0012")
            # Older fixture only knows its 010/011 entry cleanup gate.
            async with case.factory.begin() as db:
                await db.execute(sa.delete(orm.RunWorldVisitEntryRow).where(orm.RunWorldVisitEntryRow.run_id.in_(case.scope.run_ids)))
