"""Real S4 admission and S5 turns through normal production composition."""
from contextlib import asynccontextmanager
import json
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa

from deviation_protocol.api import main
from deviation_protocol.application.native_run_admission import NativeRunAdmissionResult
from deviation_protocol.application.narrative_models import (
    UntrustedNarrativeProposal, NarrativeProposalPayload, NarrativeProviderMetadata,
    SelectedNarrativeOutcome,
)
from deviation_protocol.application.narrative_prompt import PromptBuilder, default_style_profile
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain import run_protocol as s1, run_protocol_resolution as s2
from deviation_protocol.domain.state import GameState
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure.player_character_authority import ConfiguredControllerBinding
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.test_mysql_native_run_admission import native_runtime, family_bytes

pytestmark = pytest.mark.integration
PROFILES = ("difficulty.open-expedition", "difficulty.fragile-alliance", "difficulty.silent-hunting-ground")


class Renderer:
    def __init__(self):
        self.calls = 0
        self.prompts = []

    async def generate(self, request):
        self.calls += 1
        self.prompts.append(PromptBuilder(profiles=(default_style_profile(),)).build(request))
        from tests.integration.test_mysql_phase_2_4a_api import ScriptedOpeningProvider
        return await ScriptedOpeningProvider().generate(request)


@asynccontextmanager
async def production_case(engine, monkeypatch, profile="difficulty.fragile-alliance", overrides=None):
    async with native_runtime(engine) as case:
        monkeypatch.setattr(main, "create_engine", lambda: engine)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        services = main.build_default_services(player_character_controller_bindings=(ConfiguredControllerBinding(
            authentication_scheme=case.runtime.principal.authentication_scheme,
            player_id=case.runtime.principal.player_id, controller_id=case.runtime.resolver.binding.value),))
        protocol = case.command.protocol.model_copy(update={"profile_ref": s1.RunProtocolProfileRefV1(
            profile_id=s1.RunProtocolProfileId(value=profile), profile_version=s1.RunProtocolProfileVersion(value=1))})
        command = case.command.model_copy(update={"protocol": protocol,
            "overrides": s2.RunProtocolOverrideProposalV1(profile_ref=protocol.profile_ref, entries=tuple(
                s2.RunProtocolObjectiveOverrideV1(parameter=s2.ObjectiveParameterName(name), value=s2.ObjectiveParameterValue(value=value))
                for name, value in (overrides or {}).items()))})
        result = await services.native_run_admission_service.enter(case.runtime.principal, command=command)
        assert type(result) is NativeRunAdmissionResult
        case.scope.run_ids.add(result.run_id.value)
        case.scope.session_ids.add(result.session_id)
        case.services, case.result = services, result
        case.renderer = Renderer()
        services.turn_orchestrator.narrative_provider = case.renderer
        yield case


def opening(case):
    return ActionSubmission(session_id=case.result.session_id, turn_id="s5.turn.1",
        client_request_id="s5.request.1", action_type=ActionType.CUSTOM,
        description="我尝试有规律地移动手指发出生命信号")


async def snapshot(case):
    async with SqlAlchemyUnitOfWork(case.factory) as unit:
        return await unit.sessions.get_latest_snapshot(case.result.session_id)


@pytest.mark.parametrize("profile,current,charge,actual", [
    (PROFILES[0], 6, 0, 0), (PROFILES[1], 0, 1, 0), (PROFILES[1], 6, 1, 1)])
async def test_resource_controls_reload_and_exact_replay(mysql_engine, monkeypatch, profile, current, charge, actual):
    async with production_case(mysql_engine, monkeypatch, profile) as case:
        if current == 0:
            async with case.factory.begin() as session:
                row = await session.scalar(sa.select(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id == case.result.session_id))
                data = json.loads(json.dumps(row.state_json))
                data["player"]["resources"]["composure"]["current"] = 0
                row.state_json = data
        before = (await snapshot(case)).state
        calls = []
        consume = GameState.consume_resource
        def recorded(self, resource, amount):
            calls.append((resource, amount))
            return consume(self, resource, amount)
        monkeypatch.setattr(GameState, "consume_resource", recorded)
        action = opening(case)
        response = await case.services.turn_orchestrator.handle(action)
        assert response.state_changed
        after = (await snapshot(case)).state
        assert after["player"]["resources"]["composure"]["current"] == current - actual
        assert after["scenario_runtime"] != before["scenario_runtime"]
        assert after["scenario_runtime"]["narrative_outcome_evidence"]
        assert calls == ([("composure", actual)] if actual else [])
        async with case.factory() as session:
            events = (await session.scalars(sa.select(orm.DomainEventRow).where(orm.DomainEventRow.session_id == case.result.session_id))).all()
            spend = [e for e in events if e.event_type == "RunProtocolResourceSpent"]
            audits = [e for e in events if e.event_type == "RunProtocolMechanicsApplied"]
            assert len(spend) == bool(actual) and len(audits) == 1
            assert audits[0].payload_json["resource"]["requested"] == charge
            assert audits[0].payload_json["resource"]["actual"] == actual
            if actual:
                assert spend[0].payload_json == dict(resource_id="composure", requested=1, actual=1, before=6, after=5)
        committed = await family_bytes(case)
        async def no_fresh_load(*a, **kw):
            pytest.fail("committed replay reloaded mechanics")
        monkeypatch.setattr(case.services.turn_orchestrator.native_coordinator, "load", no_fresh_load)
        assert await case.services.turn_orchestrator.handle(action) == response
        assert await family_bytes(case) == committed
        assert len(calls) == bool(actual) and case.renderer.calls == 1
        assert '"run_protocol_context"' in case.renderer.prompts[0].user


@pytest.mark.parametrize("profile", PROFILES)
async def test_profile_playthrough_to_authored_ending(mysql_engine, monkeypatch, profile):
    from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS
    async with production_case(mysql_engine, monkeypatch, profile) as case:
        before = await family_bytes(case)
        for index, step in enumerate(CANONICAL_ACTIONS):
            view = await case.services.session_service.get_view(case.runtime.principal, case.result.session_id)
            data = (await snapshot(case)).state
            if data["scenario_runtime"]["ending_status"] != "ACTIVE":
                break
            orch = case.services.turn_orchestrator
            state = orch._load_state(data, case.result.session_id)
            definition = orch.scenario_catalog.scenarios[0]
            from deviation_protocol.application.scenario_event_bridge import bind_public_decision_frame
            frame = bind_public_decision_frame(orch.story_director.plan_frame(state, definition,
                profession_tags=frozenset(orch.catalog.character(state.player.character_definition_id).tags) & set(definition.available_profession_tags)),
                session_id=case.result.session_id, state_version=(await snapshot(case)).state_version,
                scenario_content_version=definition.content_version)
            args = dict(session_id=case.result.session_id, turn_id=f"play.{index}", client_request_id=f"play.{index}",
                        action_type=ActionType(step.action_type))
            if step.choice_id:
                args.update(decision_id=frame.decision_id, choice_id=step.choice_id)
            if step.description:
                args.update(description=step.description)
            response = await orch.handle(ActionSubmission(**args))
            assert response.state_changed, (index, response)
        data = (await snapshot(case)).state
        assert data["scenario_runtime"]["ending_status"] != "ACTIVE"
        assert data["scenario_runtime"]["ending_id"]
        after = await family_bytes(case)
        for table in before:
            if table.startswith("run_") or table.startswith("player_character"):
                assert after[table] == before[table]


async def test_compile_prompt_and_provider_have_no_sessions_or_mysql_locks(mysql_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from deviation_protocol.application import run_protocol_prompt_context as compiler
    from deviation_protocol.infrastructure.unit_of_work import NATIVE_ADMISSION_LOCK
    async with production_case(mysql_engine, monkeypatch) as case:
        active, unclosed, observed = set(), set(), []
        class Session(AsyncSession):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)
                unclosed.add(id(self))
            async def close(self):
                await super().close()
                unclosed.remove(id(self))
        factory = async_sessionmaker(mysql_engine, class_=Session, expire_on_commit=False)
        class Unit(SqlAlchemyUnitOfWork):
            async def __aenter__(self):
                await super().__aenter__()
                active.add(id(self))
                return self
            async def __aexit__(self, *args):
                try:
                    await super().__aexit__(*args)
                finally:
                    active.remove(id(self))
        case.services.turn_orchestrator.uow_factory = lambda: Unit(factory)
        async def independent_lock():
            engine = create_async_engine(mysql_engine.url, poolclass=NullPool)
            try:
                async with engine.connect() as connection:
                    assert await connection.scalar(sa.text("SELECT DATABASE()")) == "deviation_protocol_test"
                    await connection.execute(sa.text("SET SESSION innodb_lock_wait_timeout=1"))
                    assert await connection.scalar(sa.select(orm.GameSessionRow.session_id).where(
                        orm.GameSessionRow.session_id == case.result.session_id).with_for_update(nowait=True)) == case.result.session_id
                    assert await connection.scalar(sa.text("SELECT IS_FREE_LOCK(:name)"), {"name": NATIVE_ADMISSION_LOCK}) == 1
                    await connection.rollback()
            finally:
                await engine.dispose()
        def check(stage):
            assert not active and not unclosed
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(lambda: asyncio.run(independent_lock())).result(timeout=10)
            observed.append(stage)
        compile_original = compiler.compile_run_protocol_context
        def compile_checked(*a):
            check("compiler")
            return compile_original(*a)
        monkeypatch.setattr(compiler, "compile_run_protocol_context", compile_checked)
        build_original = PromptBuilder.build
        def build_checked(self, request):
            check("prompt")
            return build_original(self, request)
        monkeypatch.setattr(PromptBuilder, "build", build_checked)
        generate = case.renderer.generate
        async def checked(request):
            check("provider")
            return await generate(request)
        case.renderer.generate = checked
        await case.services.turn_orchestrator.handle(opening(case))
        assert observed == ["compiler", "provider", "prompt"]
        assert not active and not unclosed


@pytest.mark.parametrize("stage", ["before_events", "after_events", "snapshot", "response", "job", "commit"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_native_finalize_failure_rolls_back_all_gameplay(mysql_engine, monkeypatch, stage, cancel):
    from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
    async with production_case(mysql_engine, monkeypatch) as case:
        before = await family_bytes(case)
        primary = asyncio.CancelledError() if cancel else RuntimeError("injected finalize failure")
        class Unit(SqlAlchemyUnitOfWork):
            async def __aenter__(self):
                await super().__aenter__()
                self.finalizing = False
                persist = self.sessions.persist_events
                async def events(*a, **kw):
                    self.finalizing = True
                    if stage == "before_events":
                        raise primary
                    result = await persist(*a, **kw)
                    if stage == "after_events":
                        raise primary
                    return result
                self.sessions.persist_events = events
                port, name = {"snapshot": (self.sessions, "save_snapshot_and_events"),
                    "response": (self.turn_requests, "add"), "job": (self.narrative_jobs, "replace"),
                    "commit": (self, "commit")}.get(stage, (None, None))
                if port is not None:
                    original = getattr(port, name)
                    async def fail(*a, **kw):
                        if self.finalizing:
                            raise primary
                        return await original(*a, **kw)
                    setattr(port, name, fail)
                return self
        case.services.turn_orchestrator.uow_factory = lambda: Unit(case.factory)
        with pytest.raises(type(primary)):
            await case.services.turn_orchestrator.handle(opening(case))
        after = await family_bytes(case)
        for table in before:
            if table != "narrative_jobs":
                assert after[table] == before[table], table


async def test_validated_proposal_resume_does_not_recall_or_compile(mysql_engine, monkeypatch):
    from deviation_protocol.application import run_protocol_prompt_context as compiler
    async with production_case(mysql_engine, monkeypatch) as case:
        orch = case.services.turn_orchestrator
        finalize = type(orch)._finalize
        async def crash(*args):
            raise RuntimeError("crash after validated proposal")
        monkeypatch.setattr(type(orch), "_finalize", crash)
        with pytest.raises(RuntimeError):
            await orch.handle(opening(case))
        monkeypatch.setattr(type(orch), "_finalize", finalize)
        async with case.factory.begin() as session:
            await session.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.session_id == case.result.session_id)
                .values(lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5)))
        monkeypatch.setattr(compiler, "compile_run_protocol_context", lambda *a: pytest.fail("resume compiled"))
        response = await orch.handle(opening(case))
        assert response.state_changed and case.renderer.calls == 1
        assert await orch.handle(opening(case)) == response
        assert (await snapshot(case)).state["player"]["resources"]["composure"]["current"] == 5


async def test_stale_finalize_cannot_spend(mysql_engine, monkeypatch):
    from deviation_protocol.application.errors import NarrativeJobStaleError
    async with production_case(mysql_engine, monkeypatch) as case:
        generate = case.renderer.generate
        async def change_after_detach(request):
            proposal = await generate(request)
            async with case.factory.begin() as session:
                row = await session.scalar(sa.select(orm.GameSnapshotRow).where(orm.GameSnapshotRow.session_id == case.result.session_id))
                data = json.loads(json.dumps(row.state_json))
                data["player"]["resources"]["composure"]["current"] = 4
                row.state_json = data
            return proposal
        case.renderer.generate = change_after_detach
        with pytest.raises(NarrativeJobStaleError):
            await case.services.turn_orchestrator.handle(opening(case))
        assert (await snapshot(case)).state["player"]["resources"]["composure"]["current"] == 4
        async with case.factory() as session:
            assert await session.scalar(sa.select(sa.func.count()).select_from(orm.DomainEventRow).where(
                orm.DomainEventRow.session_id == case.result.session_id, orm.DomainEventRow.event_type == "RunProtocolResourceSpent")) == 0


@pytest.mark.parametrize("overrides,expected", [
    ({"resource_pressure":75,"social_trust":30,"consequence_severity":80,"information_opacity":75,"conflict_intensity":75}, (1,0,1,1,4)),
    ({"social_trust":55,"information_opacity":45,"conflict_intensity":45}, (0,0,0,0,1)),
])
async def test_combined_talk_discovery_clock_components(mysql_engine, monkeypatch, overrides, expected):
    async with production_case(mysql_engine, monkeypatch, overrides=overrides) as case:
        orch = case.services.turn_orchestrator
        first = await orch.handle(opening(case))
        action = ActionSubmission(session_id=case.result.session_id, turn_id="talk", client_request_id="talk",
            action_type=ActionType.TALK, dialogue="请协调员复核我的连续回应和生命体征")
        response = await orch.handle(action)
        assert response.state_changed, response
        async with case.factory() as session:
            audit = await session.scalar(sa.select(orm.DomainEventRow).where(
                orm.DomainEventRow.session_id == case.result.session_id, orm.DomainEventRow.turn_id == "talk",
                orm.DomainEventRow.event_type == "RunProtocolMechanicsApplied"))
            rows = audit.payload_json["clocks"]
            assert rows
            for row in rows:
                assert (row["social"], row["severity"], row["opacity"], row["conflict"],
                    row["base"] + sum(row[k] for k in ("social","severity","opacity","conflict"))) == expected
        data = (await snapshot(case)).state
        assert "death_certificate.clue.coherent_response" in data["scenario_runtime"]["discovered_clue_ids"]


@pytest.mark.parametrize("attack", ["result", "token", "grants", "relationships", "death", "world", "canon"])
async def test_adversarial_model_cannot_mutate_gameplay(mysql_engine, monkeypatch, attack):
    from deviation_protocol.application.narrative_models import NarrativeBoundaryError
    async with production_case(mysql_engine, monkeypatch) as case:
        before = await family_bytes(case)
        original = case.renderer.generate
        async def adversary(request):
            proposal = await original(request)
            if attack in {"result", "token"}:
                selected = proposal.proposal.selected_outcome
                from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
                key, value = ("result", NarrativeOutcomeResult.FAILURE) if attack == "result" else ("outcome_token", "outcome." + "b" * 48)
                object.__setattr__(selected, key, value)
            else:
                proposal.proposal.__dict__[attack] = {"unauthorized": True}
            return proposal
        case.renderer.generate = adversary
        with pytest.raises(NarrativeBoundaryError):
            await case.services.turn_orchestrator.handle(opening(case))
        after = await family_bytes(case)
        for table in before:
            if table != "narrative_jobs":
                assert after[table] == before[table]


async def test_concurrent_native_request_has_one_winner(mysql_engine, monkeypatch):
    async with production_case(mysql_engine, monkeypatch) as case:
        action = opening(case)
        results = await asyncio.gather(*(case.services.turn_orchestrator.handle(action) for _ in range(2)))
        replay = await case.services.turn_orchestrator.handle(action)
        assert replay.state_changed and any(r == replay for r in results)
        assert case.renderer.calls == 1
        assert (await snapshot(case)).state["player"]["resources"]["composure"]["current"] == 5


@pytest.mark.parametrize("missing", ["participation", "protocol", "world"])
async def test_missing_native_evidence_never_becomes_standalone(mysql_engine, monkeypatch, missing):
    async with production_case(mysql_engine, monkeypatch) as case:
        model = {"participation": orm.RunSessionParticipationRow, "protocol": orm.RunProtocolBindingRow,
                 "world": orm.RunEntryWorldBindingRow}[missing]
        if missing == "participation":
            # MySQL prevents physically orphaning the receipt. Also inject a lost
            # forward read and retain the real reverse indexed query as a guard.
            with pytest.raises(sa.exc.IntegrityError):
                async with case.factory.begin() as session:
                    await session.execute(sa.delete(model).where(model.run_id == case.result.run_id.value))
            from deviation_protocol.infrastructure.repositories import SqlAlchemyRunSessionParticipationRepository
            async def absent(*args):
                return None
            monkeypatch.setattr(SqlAlchemyRunSessionParticipationRepository, "get", absent)
        else:
            async with case.factory.begin() as session:
                if missing == "protocol":
                    await session.execute(sa.delete(orm.RunEntryWorldBindingRow).where(orm.RunEntryWorldBindingRow.run_id == case.result.run_id.value))
                await session.execute(sa.delete(model).where(model.run_id == case.result.run_id.value))
        before = await family_bytes(case)
        from deviation_protocol.application.native_turn_mechanics import NativeTurnBindingError
        from deviation_protocol.infrastructure.run_protocol_binding_persistence import RunProtocolBindingStoredIntegrityError
        with pytest.raises((NativeTurnBindingError, RunProtocolBindingStoredIntegrityError)):
            await case.services.turn_orchestrator.handle(opening(case))
        assert await family_bytes(case) == before and case.renderer.calls == 0


@pytest.mark.parametrize("severity,conflict,expected", [(45,45,1),(80,75,3)])
async def test_adverse_result_keeps_authored_floor(mysql_engine, monkeypatch, severity, conflict, expected):
    async with production_case(mysql_engine, monkeypatch, overrides={"consequence_severity":severity,"conflict_intensity":conflict}) as case:
        action = opening(case).model_copy(update={"action_type":ActionType.OBSERVE,"description":"我静静观察周围"})
        response = await case.services.turn_orchestrator.handle(action)
        assert response.state_changed
        async with case.factory() as session:
            audit = await session.scalar(sa.select(orm.DomainEventRow).where(orm.DomainEventRow.session_id == case.result.session_id,
                orm.DomainEventRow.event_type == "RunProtocolMechanicsApplied"))
            assert audit.payload_json["selected_result"] == "AMBIGUOUS"
            for row in audit.payload_json["clocks"]:
                assert row["base"] == 1 and row["social"] == row["opacity"] == 0
                assert row["base"] + row["severity"] + row["conflict"] == expected


async def test_acknowledgement_loss_after_commit_recovers_without_second_spend(mysql_engine, monkeypatch):
    async with production_case(mysql_engine, monkeypatch) as case:
        class Unit(SqlAlchemyUnitOfWork):
            async def commit(self):
                changed = bool(self.sessions._pending_session_versions)
                await super().commit()
                if changed:
                    raise ConnectionError("lost acknowledgement")
        orch = case.services.turn_orchestrator
        orch.uow_factory = lambda: Unit(case.factory)
        with pytest.raises(ConnectionError):
            await orch.handle(opening(case))
        orch.uow_factory = lambda: SqlAlchemyUnitOfWork(case.factory)
        before = await family_bytes(case)
        assert (await orch.handle(opening(case))).state_changed
        assert await family_bytes(case) == before and case.renderer.calls == 1


@pytest.mark.parametrize("validated", [False, True])
async def test_pre_s5_native_jobs_become_stale_without_recall(mysql_engine, monkeypatch, validated):
    from deviation_protocol.application.errors import NarrativeJobStaleError
    from deviation_protocol.application.native_turn_mechanics import digest
    async with production_case(mysql_engine, monkeypatch) as case:
        orch, action = case.services.turn_orchestrator, opening(case)
        prepared = await orch._prepare_or_execute(action)
        job = prepared.job
        if validated:
            job = await orch._claim(job.job_id)
            request = await orch._detach_request(job, action)
            proposal = await case.renderer.generate(request)
            proposal = orch.proposal_validator.validate(proposal, request=request, public_references=orch._public_references(request))
            job = await orch._store_validated_proposal(job, proposal)
        calls = case.renderer.calls
        async with case.factory.begin() as session:
            await session.execute(sa.update(orm.NarrativeJobRow).where(orm.NarrativeJobRow.job_id == job.job_id)
                .values(narrative_request_json=job.narrative_request["request"],
                    request_fingerprint=digest(job.narrative_request["request"]),
                    lease_expires_at=(datetime.now(timezone.utc)-timedelta(minutes=5)) if validated else None))
        before = (await snapshot(case)).state
        with pytest.raises(NarrativeJobStaleError):
            await orch.handle(action)
        assert (await snapshot(case)).state == before and case.renderer.calls == calls


async def test_native_provider_cancellation_has_no_gameplay_effect(mysql_engine, monkeypatch):
    async with production_case(mysql_engine, monkeypatch) as case:
        before = await family_bytes(case)
        async def cancelled(request):
            raise asyncio.CancelledError()
        case.renderer.generate = cancelled
        with pytest.raises(asyncio.CancelledError):
            await case.services.turn_orchestrator.handle(opening(case))
        after = await family_bytes(case)
        for table in before:
            if table != "narrative_jobs":
                assert before[table] == after[table]
