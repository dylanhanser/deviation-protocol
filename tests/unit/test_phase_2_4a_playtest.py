from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest
from fastapi import FastAPI

from deviation_protocol.api.dependencies import ApiServices, get_current_principal
from deviation_protocol.api.main import create_app
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import ConcurrentTurnRequestError
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
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
from deviation_protocol.application.ports import (
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_service import (
    MAX_VIEW_RECENT_NARRATIVES,
    MAX_VIEW_RECENT_NARRATIVE_CHARACTERS,
    MAX_VIEW_RECENT_NARRATIVE_UTF8_BYTES,
    SessionService,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
# This private issuer is confined to the in-memory Repository contract adapter.
# PLAY-001 production reachability is proved by the real-MySQL public API test.
from deviation_protocol.domain.persisted_events import _issue_persisted_event_receipt
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
ACTION_RESPONSE_ALLOWLIST = {
    "session_id",
    "client_request_id",
    "resolution_kind",
    "result_code",
    "feedback_code",
    "feedback_parameters",
    "resulting_state_version",
    "state_changed",
    "narrative_required",
    "narrative_pending",
    "narrative_frame",
    "narrative_text",
    "narrative_status",
    "local_query_result",
}
REQUEST_STATUS_ALLOWLIST = {
    "session_id",
    "client_request_id",
    "status",
    "client_action",
    "error_code",
    "retry_after_seconds",
    "response",
}


def clone_job(job: NarrativeJob) -> NarrativeJob:
    return NarrativeJob.model_validate(job.model_dump(mode="python"))


class MemoryStore:
    def __init__(self) -> None:
        self.sessions: dict[str, PersistedSession] = {}
        self.snapshots: dict[str, PersistedSnapshot] = {}
        self.creation_keys: dict[tuple[str, str], str] = {}
        self.turn_requests: dict[tuple[str, str], PersistedTurnRequest] = {}
        self.jobs: dict[str, NarrativeJob] = {}
        self.events: list[DomainEvent] = []
        self.session_locks: dict[str, asyncio.Lock] = {}
        self.commit_lock = asyncio.Lock()


class MemorySessionRepository:
    def __init__(self, store: MemoryStore, uow: MemoryUnitOfWork) -> None:
        self.store = store
        self.uow = uow

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        self.uow.pending_session = PersistedSession(
            session=replace(session),
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
            updated_at=created_at,
        )

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        del created_at
        self.uow.pending_snapshot = PersistedSnapshot(
            session.state_version, deepcopy(dict(state))
        )

    async def add_initial(self, session: GameSession, **kwargs: Any) -> None:
        await self.add_initial_session(
            session,
            character_definition_id=kwargs["character_definition_id"],
            creation_client_request_id=kwargs["creation_client_request_id"],
            created_at=kwargs["created_at"],
        )
        await self.add_initial_snapshot(
            session,
            state=kwargs["state"],
            created_at=kwargs["created_at"],
        )

    async def get_owned(
        self, session_id: str, player_id: str
    ) -> PersistedSession | None:
        value = self.store.sessions.get(session_id)
        if value is None or value.session.player_id != player_id:
            return None
        return deepcopy(value)

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        session_id = self.store.creation_keys.get((player_id, client_request_id))
        return deepcopy(self.store.sessions.get(session_id)) if session_id else None

    async def lock_for_turn(self, session_id: str) -> bool:
        lock = self.store.session_locks.setdefault(session_id, asyncio.Lock())
        await lock.acquire()
        self.uow.lock = lock
        return session_id in self.store.sessions

    async def get(self, session_id: str) -> GameSession | None:
        value = self.store.sessions.get(session_id)
        return replace(value.session) if value is not None else None

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        return deepcopy(self.store.snapshots.get(session_id))

    async def next_event_sequence_no(self, session_id: str) -> int:
        return max(
            (
                event.sequence_no
                for event in (*self.store.events, *self.uow.pending_events)
                if event.session_id == session_id
            ),
            default=0,
        ) + 1

    async def persist_events(
        self, events: Sequence[DomainEvent], *, state_version: int
    ) -> tuple[Any, ...]:
        self.uow.pending_events = (*self.uow.pending_events, *deepcopy(tuple(events)))
        return tuple(
            _issue_persisted_event_receipt(event, state_version=state_version)
            for event in events
        )

    async def save_snapshot_and_events(
        self,
        session: GameSession,
        state: Mapping[str, Any],
        events: Sequence[DomainEvent],
        expected_state_version: int,
    ) -> None:
        current = self.store.sessions.get(session.session_id)
        if current is None or current.session.state_version != expected_state_version:
            raise OptimisticLockError("state changed concurrently")
        self.uow.pending_state = (
            session.session_id,
            expected_state_version + 1,
            deepcopy(dict(state)),
        )
        if events:
            self.uow.pending_events = (*self.uow.pending_events, *deepcopy(tuple(events)))


class MemoryTurnRequestRepository:
    def __init__(self, store: MemoryStore, uow: MemoryUnitOfWork) -> None:
        self.store = store
        self.uow = uow

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        return deepcopy(self.store.turn_requests.get((session_id, client_request_id)))

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        del route
        self.uow.pending_turn = (
            (submission.session_id, submission.client_request_id),
            PersistedTurnRequest(
                turn_id=submission.turn_id,
                action_signature=action_signature,
                response=deepcopy(dict(response)),
            ),
        )


class MemoryNarrativeJobRepository:
    def __init__(self, store: MemoryStore, uow: MemoryUnitOfWork) -> None:
        self.store = store
        self.uow = uow

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        del for_update
        return next(
            (
                clone_job(job)
                for job in self.store.jobs.values()
                if job.session_id == session_id
                and job.client_request_id == client_request_id
            ),
            None,
        )

    async def get(self, job_id: str, *, for_update: bool = False) -> NarrativeJob | None:
        del for_update
        job = self.store.jobs.get(job_id)
        return clone_job(job) if job is not None else None

    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        jobs = sorted(
            (
                job
                for job in self.store.jobs.values()
                if job.session_id == session_id
                and job.status in ACTIVE_NARRATIVE_JOB_STATUSES
            ),
            key=lambda job: (job.created_at, job.job_id),
        )
        return clone_job(jobs[0]) if jobs else None

    async def add(self, job: NarrativeJob) -> None:
        self.uow.pending_job_add = clone_job(job)

    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        current = self.store.jobs.get(job.job_id)
        if (
            current is None
            or current.status is not expected_status
            or current.lease_token != expected_lease_token
            or current.lease_owner != expected_lease_owner
        ):
            return False
        self.uow.pending_job_replace = clone_job(job)
        return True

    async def recent_committed_texts(
        self, session_id: str, *, limit: int
    ) -> tuple[str, ...]:
        jobs = sorted(
            (
                job
                for job in self.store.jobs.values()
                if job.session_id == session_id
                and job.status is NarrativeJobStatus.COMMITTED
                and job.accepted_narrative_text is not None
            ),
            key=lambda job: (job.updated_at, job.job_id),
        )[-limit:]
        return tuple(job.accepted_narrative_text for job in jobs if job.accepted_narrative_text)


class MemoryUnitOfWork:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.sessions = MemorySessionRepository(store, self)
        self.turn_requests = MemoryTurnRequestRepository(store, self)
        self.narrative_jobs = MemoryNarrativeJobRepository(store, self)
        self.pending_session: PersistedSession | None = None
        self.pending_snapshot: PersistedSnapshot | None = None
        self.pending_state: tuple[str, int, dict[str, Any]] | None = None
        self.pending_events: tuple[DomainEvent, ...] = ()
        self.pending_turn: tuple[tuple[str, str], PersistedTurnRequest] | None = None
        self.pending_job_add: NarrativeJob | None = None
        self.pending_job_replace: NarrativeJob | None = None
        self.lock: asyncio.Lock | None = None
        self.committed = False

    async def __aenter__(self) -> MemoryUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        if self.lock is not None:
            self.lock.release()

    async def commit(self) -> None:
        async with self.store.commit_lock:
            if (
                self.pending_turn is not None
                and self.pending_turn[0] in self.store.turn_requests
            ):
                raise ConcurrentTurnRequestError
            if self.pending_session is not None:
                persisted = deepcopy(self.pending_session)
                key = (
                    persisted.session.player_id,
                    persisted.creation_client_request_id,
                )
                assert key[1] is not None
                self.store.sessions[persisted.session.session_id] = persisted
                self.store.creation_keys[(key[0], key[1])] = persisted.session.session_id
            if self.pending_snapshot is not None:
                assert self.pending_session is not None
                self.store.snapshots[self.pending_session.session.session_id] = deepcopy(
                    self.pending_snapshot
                )
            if self.pending_state is not None:
                session_id, version, state = self.pending_state
                persisted = self.store.sessions[session_id]
                updated_session = replace(persisted.session)
                updated_session.state_version = version
                self.store.sessions[session_id] = replace(
                    persisted,
                    session=updated_session,
                    updated_at=NOW,
                )
                self.store.snapshots[session_id] = PersistedSnapshot(version, deepcopy(state))
            if self.pending_turn is not None:
                key, request = self.pending_turn
                self.store.turn_requests[key] = deepcopy(request)
            if self.pending_job_add is not None:
                self.store.jobs[self.pending_job_add.job_id] = clone_job(
                    self.pending_job_add
                )
            if self.pending_job_replace is not None:
                self.store.jobs[self.pending_job_replace.job_id] = clone_job(
                    self.pending_job_replace
                )
            self.store.events.extend(deepcopy(self.pending_events))
        self.committed = True

    async def rollback(self) -> None:
        return None


class BlockingScriptedProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        candidate = request.outcome_candidates[0]
        speaker = candidate.allowed_entity_ids[0]
        return UntrustedNarrativeProposal(
            proposal=NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text=(
                    "你让仍能控制的手指反复敲出节奏，设备的变化让分诊协调员停下处置并重新核对。"
                    * 12
                ),
                referenced_entity_ids=(speaker,),
                npc_utterances=(
                    NpcUtterance(
                        speaker_entity_id=speaker,
                        text="我看到你的反应了，你有意识。",
                    ),
                ),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=NarrativeOutcomeResult.SUCCESS,
                    referenced_entity_ids=(speaker,),
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


async def asgi_request(
    app: FastAPI,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    sent = False
    status_code = 500
    response_parts: list[bytes] = []
    response_headers: dict[str, str] = {}

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
            response_headers.update(
                (key.decode("latin-1").lower(), value.decode("latin-1"))
                for key, value in message.get("headers", ())
            )
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
    return status_code, json.loads(b"".join(response_parts)), response_headers


def build_playtest() -> tuple[FastAPI, MemoryStore, BlockingScriptedProvider]:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    store = MemoryStore()
    provider = BlockingScriptedProvider()
    uow_factory = lambda: MemoryUnitOfWork(store)
    service = SessionService(
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: "playtest-session",
        seed_generator=lambda: 42,
        event_id_generator=lambda: "playtest-start-event",
    )
    event_number = iter(range(1, 30))
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
        job_id_generator=lambda: "playtest-job",
        lease_token_generator=lambda: "a" * 32,
        worker_id_generator=lambda: "playtest-worker",
        event_id_generator=lambda: f"playtest-event-{next(event_number)}",
    )
    services = ApiServices(
        session_service=service,
        turn_orchestrator=orchestrator,
        narrative_provider=provider,
    )
    app = create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(
        player_id="playtest-player", authentication_scheme="offline-test"
    )
    return app, store, provider


def assert_no_internal_fields(payload: Any) -> None:
    forbidden = {
        "action_signature",
        "state_fingerprint",
        "rule_id",
        "job_id",
        "lease_token",
        "lease_owner",
        "outcome_token",
        "validated_proposal",
        "candidate_text",
        "sequence_no",
        "receipt",
        "issuer",
        "seal",
        "source_event_id",
        "source_sequence_no",
        "deferred_count",
        "provider_name",
        "model_name",
        "usage",
    }
    if isinstance(payload, dict):
        assert forbidden.isdisjoint(payload)
        for value in payload.values():
            assert_no_internal_fields(value)
    elif isinstance(payload, list):
        for value in payload:
            assert_no_internal_fields(value)


@pytest.mark.asyncio
async def test_memory_repository_contract_reaches_first_followup_decision() -> None:
    app, store, provider = build_playtest()
    status, created, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": "create-playtest",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert status == 201
    initial_status, initial_view, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )
    assert initial_status == 200
    assert initial_view["metadata"]["state_version"] == 0
    assert initial_view["narrative_frame"]["stop_condition"] == "AWAIT_PLAYER"

    opening_task = asyncio.create_task(
        asgi_request(
            app,
            "POST",
            "/v1/sessions/playtest-session/actions",
            {
                "turn_id": "opening-turn",
                "client_request_id": "opening-request",
                "action_type": "CUSTOM",
                "description": "我尝试有规律地移动手指发出生命信号",
            },
        )
    )
    await asyncio.sleep(0.05)
    assert not opening_task.done(), opening_task.result()
    await asyncio.wait_for(provider.entered.wait(), timeout=2)
    pending_status, pending, pending_headers = await asgi_request(
        app,
        "GET",
        "/v1/sessions/playtest-session/requests/opening-request",
    )
    assert pending_status == 200
    assert pending["status"] == "PENDING"
    assert pending["client_action"] == "POLL_SAME_REQUEST"
    assert pending_headers["retry-after"] == "2"
    pending_job_before_reads = clone_job(store.jobs["playtest-job"])
    pending_view_status, pending_view, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )
    assert pending_view_status == 200
    assert pending_view["metadata"]["state_version"] == 0
    assert pending_view["recent_narrative_texts"] == []
    assert store.jobs["playtest-job"] == pending_job_before_reads

    provider.release.set()
    opening_status, opening, _ = await opening_task
    assert opening_status == 200
    assert opening["narrative_status"] == "COMMITTED"
    assert opening["narrative_frame"]["phase_id"] == "death_certificate.life_disputed"
    assert opening["narrative_frame"]["stop_condition"] == "CONTINUE"
    committed_status, committed, _ = await asgi_request(
        app,
        "GET",
        "/v1/sessions/playtest-session/requests/opening-request",
    )
    assert committed_status == 200
    assert committed["status"] == "COMMITTED"
    assert set(opening) == ACTION_RESPONSE_ALLOWLIST
    assert set(committed) == REQUEST_STATUS_ALLOWLIST
    assert set(committed["response"]) == ACTION_RESPONSE_ALLOWLIST
    assert committed["response"] == opening

    view_status, view, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )
    assert view_status == 200
    assert view["metadata"]["state_version"] == 1
    assert view["scenario_status"] == "ACTIVE"
    assert "ending_id" not in view
    assert view["recent_narrative_texts"] == [opening["narrative_text"]]
    assert view["player_memory"] == view["player_state"]["player_memory"]

    continue_responses: list[dict[str, Any]] = []
    for index in range(1, 5):
        response_status, response, _ = await asgi_request(
            app,
            "POST",
            "/v1/sessions/playtest-session/actions",
            {
                "turn_id": f"continue-turn-{index}",
                "client_request_id": f"continue-request-{index}",
                "action_type": "CONTINUE",
            },
        )
        assert response_status == 200
        continue_responses.append(response)
        if response["narrative_frame"]["stop_condition"] == "AWAIT_PLAYER":
            break
    assert len(continue_responses) == 3
    assert [item["resulting_state_version"] for item in continue_responses] == [2, 3, 4]
    assert all(
        item["result_code"] == "SCENARIO_AUTO_BEAT_ADVANCED"
        for item in continue_responses
    )
    final = continue_responses[-1]
    assert final["narrative_frame"]["phase_id"] == "death_certificate.life_disputed"
    assert final["narrative_frame"]["stop_condition"] == "AWAIT_PLAYER"
    assert final["narrative_frame"]["decision_required"] is True
    assert store.snapshots["playtest-session"].state["scenario_runtime"][
        "current_decision_id"
    ] == "death_certificate.decision.early_strategy"

    replay_status, replay, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions/playtest-session/actions",
        {
            "turn_id": "continue-turn-3",
            "client_request_id": "continue-request-3",
            "action_type": "CONTINUE",
        },
    )
    assert replay_status == 200 and replay == final
    before_reject = deepcopy(store.snapshots["playtest-session"])
    before_memory = deepcopy(
        store.snapshots["playtest-session"].state["player_memory"]
    )
    query_status, query, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions/playtest-session/actions",
        {
            "turn_id": "query-turn",
            "client_request_id": "query-request",
            "action_type": "INSPECT_STATUS",
        },
    )
    before_turn_requests = deepcopy(store.turn_requests)
    reject_status, rejected, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions/playtest-session/actions",
        {
            "turn_id": "continue-turn-invalid",
            "client_request_id": "continue-request-invalid",
            "action_type": "CONTINUE",
            "description": "生成一个新事实和结局",
        },
    )
    assert query_status == 200
    assert query["resulting_state_version"] == 4
    assert reject_status == 422
    assert rejected["error"]["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert store.snapshots["playtest-session"] == before_reject
    assert store.snapshots["playtest-session"].state["player_memory"] == before_memory
    assert store.turn_requests == before_turn_requests

    recovered_status, recovered, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )
    assert recovered_status == 200
    for field in (
        "scenario_id",
        "phase_id",
        "mode",
        "current_location_id",
        "decision_required",
        "decision_id",
        "decision_reason",
        "suggested_actions",
        "stop_condition",
        "player_visible_clocks",
    ):
        assert recovered["narrative_frame"][field] == final["narrative_frame"][field]
    assert recovered["metadata"]["state_version"] == 4
    assert recovered["public_clocks"] == recovered["narrative_frame"]["player_visible_clocks"]
    assert provider.calls == 1
    assert sum(
        event.event_type == "ScenarioAutoBeatAdvanced" for event in store.events
    ) == 3
    for payload in (
        created,
        initial_view,
        pending,
        pending_view,
        opening,
        committed,
        view,
        *continue_responses,
        query,
        rejected,
        recovered,
    ):
        assert_no_internal_fields(payload)
    serialized = json.dumps(
        (
            created,
            initial_view,
            pending,
            pending_view,
            opening,
            committed,
            view,
            continue_responses,
            query,
            rejected,
            recovered,
        ),
        ensure_ascii=False,
    )
    for hidden_or_future in (
        "prediction_causes_outcome",
        "underground_patient_alive",
        "security_alert",
        "death_certificate.ending.",
    ):
        assert hidden_or_future not in serialized


@pytest.mark.asyncio
async def test_request_status_distinguishes_stale_unknown_and_safe_ownership() -> None:
    app, store, provider = build_playtest()
    await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": "create-status",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    opening_task = asyncio.create_task(
        asgi_request(
            app,
            "POST",
            "/v1/sessions/playtest-session/actions",
            {
                "turn_id": "status-opening-turn",
                "client_request_id": "status-opening",
                "action_type": "CUSTOM",
                "description": "我尝试有规律地移动手指发出生命信号",
            },
        )
    )
    await asyncio.sleep(0.05)
    assert not opening_task.done(), opening_task.result()
    await asyncio.wait_for(provider.entered.wait(), timeout=2)
    provider.release.set()
    await opening_task
    template = store.jobs["playtest-job"].model_dump(mode="python")
    for request_id, status, error_code in (
        ("stale-request", NarrativeJobStatus.STALE, "NARRATIVE_JOB_STALE"),
        (
            "unknown-request",
            NarrativeJobStatus.OUTCOME_UNKNOWN,
            "NARRATIVE_OUTCOME_UNKNOWN",
        ),
        (
            "legacy-retryable-request",
            NarrativeJobStatus.FAILED_RETRYABLE,
            "LEGACY_RETRYABLE_FAILURE",
        ),
    ):
        template.update(
            {
                "job_id": f"job-{request_id}",
                "turn_id": f"turn-{request_id}",
                "client_request_id": request_id,
                "status": status,
                "lease_token": None,
                "lease_owner": None,
                "lease_expires_at": None,
                "validated_proposal": None,
                "validated_proposal_digest": None,
                "outcome_rule_id": None,
                "accepted_narrative_text": None,
                "error_code": error_code,
            }
        )
        store.jobs[template["job_id"]] = NarrativeJob.model_validate(template)

    proposal_template = store.jobs["playtest-job"].model_dump(mode="python")
    proposal_template.update(
        {
            "job_id": "job-proposal-request",
            "turn_id": "turn-proposal-request",
            "client_request_id": "proposal-request",
            "status": NarrativeJobStatus.PROPOSAL_VALIDATED,
            "lease_token": "b" * 32,
            "lease_owner": "proposal-worker",
            "lease_expires_at": NOW + timedelta(minutes=1),
            "outcome_rule_id": None,
            "accepted_narrative_text": None,
            "error_code": None,
        }
    )
    store.jobs["job-proposal-request"] = NarrativeJob.model_validate(
        proposal_template
    )

    stale_status, stale, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/requests/stale-request"
    )
    unknown_status, unknown, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/requests/unknown-request"
    )
    proposal_status, proposal, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/requests/proposal-request"
    )
    legacy_status, legacy, _ = await asgi_request(
        app,
        "GET",
        "/v1/sessions/playtest-session/requests/legacy-retryable-request",
    )
    assert stale_status == unknown_status == proposal_status == legacy_status == 200
    assert (stale["status"], stale["error_code"], stale["client_action"]) == (
        "STALE",
        "NARRATIVE_REQUEST_STALE",
        "REFRESH_VIEW",
    )
    assert (
        unknown["status"],
        unknown["error_code"],
        unknown["client_action"],
    ) == ("OUTCOME_UNKNOWN", "NARRATIVE_OUTCOME_UNKNOWN", "DO_NOT_RETRY")
    assert (legacy["status"], legacy["error_code"], legacy["client_action"]) == (
        "FAILED",
        "NARRATIVE_REQUEST_FAILED",
        "DO_NOT_RETRY",
    )
    assert stale["response"] is unknown["response"] is legacy["response"] is None
    assert proposal == {
        "session_id": "playtest-session",
        "client_request_id": "proposal-request",
        "status": "PENDING",
        "client_action": "POLL_SAME_REQUEST",
        "error_code": None,
        "retry_after_seconds": 2,
        "response": None,
    }
    assert provider.calls == 1
    assert_no_internal_fields(stale)
    assert_no_internal_fields(unknown)
    assert_no_internal_fields(legacy)
    assert_no_internal_fields(proposal)

    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(
        player_id="other-player", authentication_scheme="offline-test"
    )
    hidden_status, hidden, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/requests/stale-request"
    )
    hidden_view_status, hidden_view, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )
    assert hidden_status == hidden_view_status == 404
    assert hidden == {
        "error": {
            "error_code": "SESSION_NOT_FOUND",
            "message": "Session was not found",
        }
    }
    assert hidden_view == hidden


def test_view_recent_narrative_budget_is_bounded_and_prefers_newer_texts() -> None:
    texts = tuple(f"片段-{index}-" + ("界" * 3_000) for index in range(10))
    selected = SessionService._bounded_recent_texts(texts)

    assert len(selected) <= MAX_VIEW_RECENT_NARRATIVES
    assert sum(map(len, selected)) <= MAX_VIEW_RECENT_NARRATIVE_CHARACTERS
    assert sum(len(text.encode("utf-8")) for text in selected) <= (
        MAX_VIEW_RECENT_NARRATIVE_UTF8_BYTES
    )
    assert selected
    assert selected[-1].startswith("片段-9-")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "damage",
    ["missing", "version", "schema", "content", "player", "scenario"],
)
async def test_view_unifies_known_snapshot_integrity_failures(damage: str) -> None:
    app, store, _ = build_playtest()
    created_status, _, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": f"create-damaged-{damage}",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert created_status == 201
    original = store.snapshots["playtest-session"]
    payload = deepcopy(dict(original.state))
    if damage == "missing":
        del store.snapshots["playtest-session"]
    elif damage == "version":
        store.snapshots["playtest-session"] = PersistedSnapshot(1, payload)
    elif damage == "schema":
        payload["schema_version"] = 999
        store.snapshots["playtest-session"] = PersistedSnapshot(0, payload)
    elif damage == "content":
        payload["content_version"] = "other-content"
        store.snapshots["playtest-session"] = PersistedSnapshot(0, payload)
    elif damage == "player":
        payload["player"]["player_id"] = "other-player"
        store.snapshots["playtest-session"] = PersistedSnapshot(0, payload)
    else:
        payload["scenario_runtime"]["scenario_content_version"] = "other-scenario"
        store.snapshots["playtest-session"] = PersistedSnapshot(0, payload)

    status_code, response, _ = await asgi_request(
        app, "GET", "/v1/sessions/playtest-session/view"
    )

    assert status_code == 409
    assert response == {
        "error": {
            "error_code": "SNAPSHOT_INVALID",
            "message": "Session state is unavailable or incompatible",
        }
    }


@pytest.mark.asyncio
async def test_view_does_not_mask_unknown_snapshot_repository_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, _, _ = build_playtest()
    created_status, _, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": "create-repository-failure",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert created_status == 201

    async def fail_snapshot_read(
        self: MemorySessionRepository, session_id: str
    ) -> PersistedSnapshot | None:
        del self, session_id
        raise RuntimeError("unknown repository failure")

    monkeypatch.setattr(
        MemorySessionRepository, "get_latest_snapshot", fail_snapshot_read
    )
    with pytest.raises(RuntimeError, match="unknown repository failure"):
        await asgi_request(app, "GET", "/v1/sessions/playtest-session/view")
