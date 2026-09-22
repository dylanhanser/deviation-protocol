"""Actual-head migration, admission rollback/concurrency and exact initial restoration."""
import asyncio
from contextlib import asynccontextmanager

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker

from deviation_protocol.api import main
from deviation_protocol.application.opening_preparation import OpeningPreparationService
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.opening_preparation_persistence import SqlOpeningPreparationRepository
from tests.integration.test_mysql_world_continuation_migration import schema_state, migrate_to
from tests.integration.test_mysql_run_entry_playthrough import _Scope, _build_runtime, _delete_scope
from tests.integration.test_mysql_run_protocol_binding import SCRIPT
from tests.unit.test_native_run_admission import command

pytestmark = pytest.mark.integration


@asynccontextmanager
async def opening_runtime(engine):
    initial = await schema_state(engine)
    original = initial[0]["alembic_version"][1][0][0]
    head = SCRIPT.get_current_head()
    assert head == "20260921_0012"
    # This test restores schema too, so require an empty dedicated test database.
    assert not any(rows for name, (_, rows) in initial[0].items() if name != "alembic_version")
    await migrate_to(engine, head)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    scope = _Scope()
    try:
        runtime = await _build_runtime(factory, scope, character_count=2, block_first_provider_call=False)
        admission = main.build_native_run_admission_service(engine=engine, run_service=runtime.services.run_service,
            session_service=runtime.services.session_service)
        yield OpeningPreparationService(admission), runtime, factory, scope
    finally:
        async with factory.begin() as session:
            scope.run_ids.update(value for value in (await session.scalars(sa.select(orm.OpeningPreparationRow.run_id).where(
                orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))).all() if value is not None)
            await session.execute(sa.delete(orm.OpeningPreparationRow).where(orm.OpeningPreparationRow.character_id.in_(scope.player_character_ids)))
            for model in (orm.RunEntryWorldBindingRow, orm.RunProtocolBindingRow):
                await session.execute(sa.delete(model).where(model.run_id.in_(scope.run_ids)))
        await _delete_scope(factory, scope)
        await migrate_to(engine, original)
        assert await schema_state(engine) == initial


async def test_mysql_prepare_confirm_concurrency_replay_and_migration_refusal(mysql_engine):
    async with opening_runtime(mysql_engine) as (service, runtime, factory, scope):
        intent = command(runtime.character_ids[0])
        records = await asyncio.gather(*(service.prepare(runtime.principal, intent) for _ in range(4)))
        assert all(record == records[0] for record in records)
        record = records[0]
        assert (await service.get(runtime.principal, record.character_id)) == record
        # Downgrade must refuse even an unconfirmed persisted offer, preserving all bytes.
        before = await schema_state(mysql_engine)
        with pytest.raises(RuntimeError, match="Opening preparations exist"):
            await migrate_to(mysql_engine, "20260920_0011")
        assert await schema_state(mysql_engine) == before
        async def confirm():
            return await service.confirm(runtime.principal, record.preparation_id, record.character_id,
                record.catalog_version, record.candidates[:2])
        confirmed = await asyncio.gather(*(confirm() for _ in range(4)))
        assert all(value == confirmed[0] for value in confirmed)
        scope.run_ids.add(confirmed[0].run_id)
        from deviation_protocol.application.opening_preparation import decode_command, decode_result
        result = decode_result(confirmed[0].result_json, decode_command(confirmed[0].command_json))
        scope.session_ids.add(result.session_id)
        assert (await confirm()) == confirmed[0]
        async with factory() as session:
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.OpeningPreparationRow)) == 1
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.RunCurrentRow)) == 1
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.GameSessionRow)) == 1
        # Matching ORM metadata, including FK types, unique keys and CHECK constraints.
        from alembic.autogenerate import compare_metadata
        from alembic.runtime.migration import MigrationContext
        async with mysql_engine.connect() as connection:
            differences = await connection.run_sync(lambda c: compare_metadata(MigrationContext.configure(c), orm.Base.metadata))
        assert differences == []


async def test_mysql_confirmation_failure_keeps_preparation_and_no_partial_run(mysql_engine, monkeypatch):
    async with opening_runtime(mysql_engine) as (service, runtime, factory, scope):
        record = await service.prepare(runtime.principal, command(runtime.character_ids[0]))
        before = await schema_state(mysql_engine)
        original = SqlOpeningPreparationRepository.save
        async def fail(repository, value):
            await original(repository, value)
            if value.state == "CONFIRMED":
                raise RuntimeError("injected after opening finalization")
        with monkeypatch.context() as patch:
            patch.setattr(SqlOpeningPreparationRepository, "save", fail)
            with pytest.raises(RuntimeError, match="injected after opening finalization"):
                await service.confirm(runtime.principal, record.preparation_id, record.character_id,
                    record.catalog_version, record.candidates[:2])
        assert await schema_state(mysql_engine) == before
        assert await service.get(runtime.principal, record.character_id) == record


@pytest.mark.parametrize("first", ["prepare", "legacy", "confirm"])
async def test_mysql_legacy_admission_serializes_with_preparation_and_confirmation(mysql_engine, monkeypatch, first):
    from deviation_protocol.application.run_entry_service import RunEntryCommand, RunEntryResult, RunEntryDecision
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    from deviation_protocol.application.opening_preparation import OpeningPreparation, PreparationRejected, decode_command, decode_result
    async with opening_runtime(mysql_engine) as (service, runtime, factory, scope):
        intent = command(runtime.character_ids[0])
        legacy = runtime.services.run_entry_service
        request = RunEntryCommand(public_operation_key=RunEntryPublicOperationKey(value="race.legacy"),
            player_character_id=intent.player_character_id, expected_record_revision=intent.expected_record_revision,
            scenario_id="death_certificate")
        held, release, entered = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_save = SqlOpeningPreparationRepository.save
        original_guard = legacy._has_pending_opening
        record = await service.prepare(runtime.principal, intent) if first == "confirm" else None

        async def pause_save(repository, value):
            await original_save(repository, value)
            if (first == "prepare" and value.state == "PENDING") or (first == "confirm" and value.state == "CONFIRMED"):
                held.set()
                await asyncio.wait_for(release.wait(), 10)

        async def pause_guard(uow, character_id):
            held.set()
            await asyncio.wait_for(release.wait(), 10)
            return await original_guard(uow, character_id)

        async def opening_operation():
            if record is None:
                return await service.prepare(runtime.principal, intent)
            return await service.confirm(runtime.principal, record.preparation_id, record.character_id,
                record.catalog_version, record.candidates[:2])

        with monkeypatch.context() as patch:
            patch.setattr(SqlOpeningPreparationRepository, "save", pause_save)
            if first == "legacy":
                patch.setattr(type(legacy), "_has_pending_opening", staticmethod(pause_guard))
            leader = asyncio.create_task(legacy.enter(runtime.principal, command=request) if first == "legacy" else opening_operation())
            await asyncio.wait_for(held.wait(), 10)
            async def follower_call():
                entered.set()
                try:
                    return await (opening_operation() if first == "legacy" else legacy.enter(runtime.principal, command=request))
                except PreparationRejected as error:
                    return error
            follower = asyncio.create_task(follower_call())
            try:
                await entered.wait()
                await asyncio.sleep(0.05)
                assert not follower.done(), "competing admission escaped the character transaction lock"
            finally:
                release.set()
            first_result, second_result = await asyncio.wait_for(asyncio.gather(leader, follower), 15)

        if first == "legacy":
            assert isinstance(first_result, RunEntryResult)
            assert isinstance(second_result, PreparationRejected)
            assert second_result.code == "PLAYER_CHARACTER_NOT_ELIGIBLE"
            scope.run_ids.add(first_result.run_id.value)
            scope.session_ids.add(first_result.session_id)
            assert await service.get(runtime.principal, intent.player_character_id.value) is None
            before = await schema_state(mysql_engine)
            assert await legacy.enter(runtime.principal, command=request) == first_result
            assert await schema_state(mysql_engine) == before
        else:
            assert isinstance(first_result, OpeningPreparation)
            assert isinstance(second_result, RunEntryDecision)
            assert second_result.code.value == "PLAYER_CHARACTER_NOT_ELIGIBLE"
            if first == "prepare":
                assert await service.get(runtime.principal, first_result.character_id) == first_result
                async with factory() as session:
                    assert await session.scalar(sa.select(sa.func.count()).select_from(orm.RunCurrentRow)) == 0
                    assert await session.scalar(sa.select(sa.func.count()).select_from(orm.GameSessionRow)) == 0
                first_result = await service.confirm(runtime.principal, first_result.preparation_id,
                    first_result.character_id, first_result.catalog_version, first_result.candidates[:2])
            result = decode_result(first_result.result_json, decode_command(first_result.command_json))
            scope.run_ids.add(first_result.run_id)
            scope.session_ids.add(result.session_id)
        async with factory() as session:
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.RunCurrentRow)) == 1
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.GameSessionRow)) == 1


async def test_normal_public_sql_composition_restart_and_action_replay(mysql_engine, monkeypatch):
    import httpx
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
    from tests.integration.test_mysql_native_turn_mechanics import Renderer
    from tests.unit.test_native_run_entry_api import body
    async with opening_runtime(mysql_engine) as (_, original, factory, scope):
        monkeypatch.setattr(main, "create_engine", lambda: mysql_engine)
        def build_services():
            services = main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
                authentication_scheme=original.principal.authentication_scheme, player_id=original.principal.player_id,
                controller_id=original.resolver.binding.value),))
            services.turn_orchestrator.narrative_provider = Renderer()
            return services
        services = build_services()
        app = main.create_app(services=services)
        app.state.api_services = services
        app.dependency_overrides[get_current_principal] = lambda: original.principal
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            prepared = await client.post("/v1/opening-preparations", json=body(original.character_ids[0].value),
                headers={"Idempotency-Key":"sql.opening"})
            assert prepared.status_code == 200, prepared.text
            record = prepared.json()
            # Rebuild normal services; recovery uses only committed SQL authority.
            app.state.api_services = build_services()
            read = await client.get(f'/v1/player-characters/{record["character_id"]}/opening-preparation')
            assert read.json() == record
            confirmation = {"character_id":record["character_id"],"catalog_version":record["catalog_version"],
                "selected_ids":[t["id"] for t in record["candidates"][:2]]}
            route = f'/v1/opening-preparations/{record["preparation_id"]}/confirm'
            confirmed = await client.post(route, json=confirmation, headers={"Idempotency-Key":"sql.confirm"})
            assert confirmed.status_code == 200, confirmed.text
            result = confirmed.json()["result"]
            sid = result["session_id"]
            scope.run_ids.add(result["run_context"]["run_id"])
            scope.session_ids.add(sid)
            app.state.api_services = build_services()
            assert (await client.post(route, json=confirmation, headers={"Idempotency-Key":"sql.confirm"})).json() == confirmed.json()
            action = {"action_type":"OBSERVE","description":"查看环境","turn_id":"sql.observe","client_request_id":"sql.observe"}
            response = await client.post(f"/v1/sessions/{sid}/actions", json=action)
            assert response.status_code == 200 and response.json()["state_changed"], response.text
            before_replay = await schema_state(mysql_engine)
            assert (await client.post(f"/v1/sessions/{sid}/actions", json=action)).json() == response.json()
            assert await schema_state(mysql_engine) == before_replay
            assert len((await client.get(f"/v1/sessions/{sid}/opening-talents")).json()) == 2
