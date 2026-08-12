from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import importlib
import inspect
import json
import sys

import httpx
import pytest

import deviation_protocol.api.demo_composition as demo_composition_module
from deviation_protocol.api.demo_composition import (
    CanonicalDemoNarrativeTurnOrchestrator,
    DemoRuntime,
    DynamicDemoConfigurationError,
    DynamicDemoShutdownError,
    build_demo_runtime,
    build_dynamic_demo_runtime,
)
from deviation_protocol.api.main import create_app
from deviation_protocol.application.narrative_models import NarrativeRequest
from deviation_protocol.application.dynamic_narrative_models import DynamicPromptBuilder
from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
)
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterOperationNamespace,
    CreationReceiptKey,
    CreationSuccessResult,
    build_creation_success_receipt,
    creation_fingerprint,
)
from deviation_protocol.domain.actions import ActionSubmission, ActionType
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
import deviation_protocol.infrastructure.demo_authority as demo_authority_module
from deviation_protocol.infrastructure.demo_authority import (
    CanonicalDemoProviderGuard,
)
from deviation_protocol.api.dependencies import get_demo_dev_principal
from deviation_protocol.infrastructure.demo_generators import (
    DemoGenerators,
    DemoStringSequence,
    new_demo_generators,
)
from deviation_protocol.infrastructure.demo_persistence import (
    DemoProcessStore,
    DemoSessionRepository,
    DemoStoreSnapshot,
    DemoTurnRequestRepository,
    DemoUnitOfWork,
)
from deviation_protocol.infrastructure.deterministic_narrative import (
    DeterministicDemoNarrativeProvider,
)
from deviation_protocol.infrastructure.deepseek_narrative import (
    DEFAULT_DEEPSEEK_MAX_TOKENS,
    DeepSeekNarrativeProvider,
)
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.run_persistence import (
    RunStoredRecordIntegrityError,
)


def test_demo_composition_registers_exact_player_character_and_run_routes() -> None:
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)

    assert {
        (route.path, frozenset(route.methods))
        for route in app.routes
        if route.path.startswith("/v1/player-characters")
        or route.path == "/v1/runs"
    } == {
        (
            "/v1/player-characters/eligible-for-run-entry",
            frozenset({"GET"}),
        ),
        ("/v1/player-characters", frozenset({"POST"})),
        (
            "/v1/player-characters/{player_character_id}",
            frozenset({"GET"}),
        ),
        (
            "/v1/player-characters/{player_character_id}/retirement",
            frozenset({"POST"}),
        ),
        ("/v1/runs", frozenset({"POST"})),
    }
    assert "PlayerCharacterRetirementRequest" in app.openapi()[
        "components"
    ]["schemas"]


class CountingProvider(DeterministicDemoNarrativeProvider):
    def __init__(self, events: list[str] | None = None) -> None:
        self.calls = 0
        self.requests: list[NarrativeRequest] = []
        self._events = events

    async def generate(self, request: NarrativeRequest):
        if self._events is not None:
            self._events.append("provider")
        self.calls += 1
        self.requests.append(request)
        return await super().generate(request)


class RejectingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: NarrativeRequest):
        del request
        self.calls += 1
        raise NarrativeProposalRejectedError()

    async def aclose(self) -> None:
        return None


class ConcurrentFirstCallProvider(DeterministicDemoNarrativeProvider):
    def __init__(self) -> None:
        self.calls = 0
        self._both_entered = asyncio.Event()

    async def generate(self, request: NarrativeRequest):
        self.calls += 1
        if self.calls == 2:
            self._both_entered.set()
        await asyncio.wait_for(self._both_entered.wait(), timeout=2)
        return await super().generate(request)


class RejectAfterProviderValidator:
    def validate(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise NarrativeProposalRejectedError()


class CancellingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.entered = asyncio.Event()

    async def generate(self, request: NarrativeRequest):
        del request
        self.calls += 1
        self.entered.set()
        await asyncio.Event().wait()

    async def aclose(self) -> None:
        return None


class ExplodingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: NarrativeRequest):
        del request
        self.calls += 1
        raise RuntimeError("controlled provider exception")

    async def aclose(self) -> None:
        return None


class FailOnceProvider(DeterministicDemoNarrativeProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: NarrativeRequest):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("controlled first Provider failure")
        return await super().generate(request)


class CancelOnceProvider(DeterministicDemoNarrativeProvider):
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: NarrativeRequest):
        self.calls += 1
        if self.calls == 1:
            raise asyncio.CancelledError()
        return await super().generate(request)


class ConcurrentAttemptProvider(DeterministicDemoNarrativeProvider):
    def __init__(self) -> None:
        self.calls = 0
        self.first_entered = asyncio.Event()
        self.release_first = asyncio.Event()

    async def generate(self, request: NarrativeRequest):
        self.calls += 1
        if self.calls == 1:
            self.first_entered.set()
            await self.release_first.wait()
        return await super().generate(request)


class FailProviderGameplayCommitUnitOfWork(DemoUnitOfWork):
    def _publish_atomically(self) -> None:
        if (
            self._store.fail_provider_gameplay_commit
            and self._pending_provider_progress is not None
        ):
            raise OptimisticLockError("controlled Demo Provider gameplay commit failure")
        super()._publish_atomically()


class FailProviderGameplayCommitStore(DemoProcessStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_provider_gameplay_commit = True

    def unit_of_work(self) -> DemoUnitOfWork:
        return FailProviderGameplayCommitUnitOfWork(self)


_LATE_INTEGRITY_PRIVATE_TEXT = (
    "private late integrity authority binding.demo-player Entry.Integrity-1"
)


class LateIntegrityFailureUnitOfWork(DemoUnitOfWork):
    def _publish_atomically(self) -> None:
        if not self._store.fail_late_integrity:
            super()._publish_atomically()
            return
        if len(self._pending_run_participations) != 1:
            raise AssertionError("late integrity injection requires one participation")
        session_id, stored = next(iter(self._pending_run_participations.items()))
        del self._pending_run_participations[session_id]
        self._pending_run_participations["private-late-integrity-session"] = stored
        self._store.late_integrity_injections += 1
        try:
            super()._publish_atomically()
        except RunStoredRecordIntegrityError as exc:
            raise RunStoredRecordIntegrityError(
                _LATE_INTEGRITY_PRIVATE_TEXT
            ) from exc
        raise AssertionError("late integrity injection did not fail closed")


class LateIntegrityFailureStore(DemoProcessStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_late_integrity = False
        self.late_integrity_injections = 0

    def unit_of_work(self) -> DemoUnitOfWork:
        return LateIntegrityFailureUnitOfWork(self)


@dataclass(frozen=True, slots=True)
class AuthorizationOrderingCounts:
    sequence_lock_calls: int
    sequence_lock_acquire_wait_calls: int
    sequence_lock_acquisitions: int
    has_committed_request_calls: int
    uow_factory_calls: int
    uow_constructions: int
    uow_entry_calls: int
    durable_lock_calls: int
    durable_lock_lookup_calls: int
    durable_lock_acquire_wait_calls: int
    durable_lock_acquisitions: int
    durable_committed_request_lookup_calls: int
    durable_committed_request_reads: int
    uow_snapshot_retrieval_calls: int
    durable_snapshot_reads: int
    checkpoint_calls: int
    checkpoint_state_loads: int
    checkpoint_validations: int
    store_snapshot_calls: int
    authorization_creations: int
    context_sets: int
    context_resets: int


class AuthorizationOrderingProbe:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.sequence_lock_calls = 0
        self.sequence_lock_acquire_wait_calls = 0
        self.sequence_lock_acquisitions = 0
        self.has_committed_request_calls = 0
        self.uow_factory_calls = 0
        self.uow_constructions = 0
        self.uow_entry_calls = 0
        self.durable_lock_calls = 0
        self.durable_lock_lookup_calls = 0
        self.durable_lock_acquire_wait_calls = 0
        self.durable_lock_acquisitions = 0
        self.durable_committed_request_lookup_calls = 0
        self.durable_committed_request_reads = 0
        self.uow_snapshot_retrieval_calls = 0
        self.durable_snapshot_reads = 0
        self.checkpoint_calls = 0
        self.checkpoint_state_loads = 0
        self.checkpoint_validations = 0
        self.authorization_creations = 0
        self.context_sets = 0
        self.context_resets = 0

    def counts(self, store: CountingSnapshotStore) -> AuthorizationOrderingCounts:
        return AuthorizationOrderingCounts(
            sequence_lock_calls=self.sequence_lock_calls,
            sequence_lock_acquire_wait_calls=self.sequence_lock_acquire_wait_calls,
            sequence_lock_acquisitions=self.sequence_lock_acquisitions,
            has_committed_request_calls=self.has_committed_request_calls,
            uow_factory_calls=self.uow_factory_calls,
            uow_constructions=self.uow_constructions,
            uow_entry_calls=self.uow_entry_calls,
            durable_lock_calls=self.durable_lock_calls,
            durable_lock_lookup_calls=self.durable_lock_lookup_calls,
            durable_lock_acquire_wait_calls=self.durable_lock_acquire_wait_calls,
            durable_lock_acquisitions=self.durable_lock_acquisitions,
            durable_committed_request_lookup_calls=(
                self.durable_committed_request_lookup_calls
            ),
            durable_committed_request_reads=self.durable_committed_request_reads,
            uow_snapshot_retrieval_calls=self.uow_snapshot_retrieval_calls,
            durable_snapshot_reads=self.durable_snapshot_reads,
            checkpoint_calls=self.checkpoint_calls,
            checkpoint_state_loads=self.checkpoint_state_loads,
            checkpoint_validations=self.checkpoint_validations,
            store_snapshot_calls=store.snapshot_calls,
            authorization_creations=self.authorization_creations,
            context_sets=self.context_sets,
            context_resets=self.context_resets,
        )


class ProbedSequenceLock:
    """Thin test-only recorder around the real per-session sequence lock."""

    def __init__(
        self,
        delegate: asyncio.Lock,
        probe: AuthorizationOrderingProbe,
    ) -> None:
        self._delegate = delegate
        self._probe = probe

    async def acquire(self) -> bool:
        self._probe.sequence_lock_acquire_wait_calls += 1
        self._probe.events.append("sequence_lock_acquire_wait")
        acquired = await self._delegate.acquire()
        self._probe.sequence_lock_acquisitions += 1
        self._probe.events.append("sequence_lock_acquired")
        return acquired

    def release(self) -> None:
        self._delegate.release()

    def locked(self) -> bool:
        return self._delegate.locked()

    async def __aenter__(self) -> ProbedSequenceLock:
        await self.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        del exc_type, exc, traceback
        self.release()


class ProbedDurableSessionLock:
    """Thin test-only recorder around the real Demo repository lock."""

    def __init__(
        self,
        delegate: asyncio.Lock,
        probe: AuthorizationOrderingProbe,
    ) -> None:
        self._delegate = delegate
        self._probe = probe

    async def acquire(self) -> bool:
        self._probe.durable_lock_acquire_wait_calls += 1
        self._probe.events.append("durable_lock_acquire_wait")
        acquired = await self._delegate.acquire()
        self._probe.durable_lock_acquisitions += 1
        self._probe.events.append("durable_lock_acquired")
        return acquired

    def release(self) -> None:
        self._delegate.release()

    def locked(self) -> bool:
        return self._delegate.locked()


class ProbedSessionLockRegistry(dict[str, ProbedDurableSessionLock]):
    """Record the exact `_session_locks.setdefault` production lookup."""

    def __init__(self, probe: AuthorizationOrderingProbe) -> None:
        super().__init__()
        self._probe = probe

    def setdefault(
        self,
        key: str,
        default: asyncio.Lock | None = None,
    ) -> ProbedDurableSessionLock:
        self._probe.durable_lock_lookup_calls += 1
        self._probe.events.append("durable_lock_lookup")
        if key not in self:
            if default is None:
                raise AssertionError("Demo lock lookup must supply a real lock")
            self[key] = ProbedDurableSessionLock(default, self._probe)
        return self[key]


class ProbedDurableReadMap(dict[object, object]):
    """Record a direct `.get()` against a real Demo durable-state mapping."""

    def __init__(
        self,
        values: dict[object, object],
        *,
        probe: AuthorizationOrderingProbe,
        counter_name: str,
        event_name: str,
    ) -> None:
        super().__init__(values)
        self._probe = probe
        self._counter_name = counter_name
        self._event_name = event_name

    def get(self, key: object, default: object = None) -> object:
        setattr(
            self._probe,
            self._counter_name,
            getattr(self._probe, self._counter_name) + 1,
        )
        self._probe.events.append(self._event_name)
        return super().get(key, default)

    def __deepcopy__(self, memo: dict[int, object]) -> dict[object, object]:
        return deepcopy(dict(self), memo)


class ProbedDemoSessionRepository(DemoSessionRepository):
    def __init__(
        self,
        store: DemoProcessStore,
        uow: DemoUnitOfWork,
        probe: AuthorizationOrderingProbe,
    ) -> None:
        super().__init__(store, uow)
        self._probe = probe

    async def lock_for_turn(self, session_id: str) -> bool:
        self._probe.durable_lock_calls += 1
        self._probe.events.append("durable_lock_for_turn")
        return await super().lock_for_turn(session_id)

    async def get_latest_snapshot(self, session_id: str):
        self._probe.uow_snapshot_retrieval_calls += 1
        self._probe.events.append("uow_snapshot_retrieval")
        return await super().get_latest_snapshot(session_id)


class ProbedDemoTurnRequestRepository(DemoTurnRequestRepository):
    def __init__(
        self,
        store: DemoProcessStore,
        uow: DemoUnitOfWork,
        probe: AuthorizationOrderingProbe,
    ) -> None:
        super().__init__(store, uow)
        self._probe = probe

    async def get_by_client_request_id(
        self,
        session_id: str,
        client_request_id: str,
    ):
        self._probe.durable_committed_request_lookup_calls += 1
        self._probe.events.append("durable_committed_request_lookup")
        return await super().get_by_client_request_id(
            session_id,
            client_request_id,
        )


class ProbedDemoUnitOfWork(DemoUnitOfWork):
    def __init__(
        self,
        store: DemoProcessStore,
        probe: AuthorizationOrderingProbe,
    ) -> None:
        super().__init__(store)
        self._probe = probe
        self._probe.uow_constructions += 1
        self._probe.events.append("uow_construction")
        self.sessions = ProbedDemoSessionRepository(store, self, probe)
        self.turn_requests = ProbedDemoTurnRequestRepository(store, self, probe)

    async def __aenter__(self) -> ProbedDemoUnitOfWork:
        self._probe.uow_entry_calls += 1
        self._probe.events.append("uow_entry")
        await super().__aenter__()
        return self

    def _publish_atomically(self) -> None:
        super()._publish_atomically()
        self._store._snapshots = ProbedDurableReadMap(
            dict(self._store._snapshots),
            probe=self._probe,
            counter_name="durable_snapshot_reads",
            event_name="durable_snapshot_read",
        )
        self._store._turn_requests = ProbedDurableReadMap(
            dict(self._store._turn_requests),
            probe=self._probe,
            counter_name="durable_committed_request_reads",
            event_name="durable_committed_request_read",
        )


class CountingSnapshotStore(DemoProcessStore):
    def __init__(self, probe: AuthorizationOrderingProbe) -> None:
        super().__init__()
        self._probe = probe
        self.snapshot_calls = 0
        self._session_locks = ProbedSessionLockRegistry(probe)
        self._snapshots = ProbedDurableReadMap(
            {},
            probe=probe,
            counter_name="durable_snapshot_reads",
            event_name="durable_snapshot_read",
        )
        self._turn_requests = ProbedDurableReadMap(
            {},
            probe=probe,
            counter_name="durable_committed_request_reads",
            event_name="durable_committed_request_read",
        )

    def unit_of_work(self) -> DemoUnitOfWork:
        self._probe.uow_factory_calls += 1
        self._probe.events.append("uow_factory")
        return ProbedDemoUnitOfWork(self, self._probe)

    def snapshot(self) -> DemoStoreSnapshot:
        self.snapshot_calls += 1
        return super().snapshot()


class ProbedAuthorizationContext:
    def __init__(self, delegate: object, probe: AuthorizationOrderingProbe) -> None:
        self._delegate = delegate
        self._probe = probe

    def get(self):
        return self._delegate.get()  # type: ignore[attr-defined]

    def set(self, value: object):
        self._probe.context_sets += 1
        self._probe.events.append("context_set")
        return self._delegate.set(value)  # type: ignore[attr-defined]

    def reset(self, token: object) -> None:
        self._probe.context_resets += 1
        self._probe.events.append("context_reset")
        self._delegate.reset(token)  # type: ignore[attr-defined]


def _install_authorization_ordering_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> AuthorizationOrderingProbe:
    probe = AuthorizationOrderingProbe()
    original_checkpoint = (
        CanonicalDemoNarrativeTurnOrchestrator._provider_checkpoint
    )
    original_load_state = CanonicalDemoNarrativeTurnOrchestrator._load_state
    original_sequence_lock = CanonicalDemoProviderGuard.sequence_lock
    original_has_committed_request = (
        CanonicalDemoProviderGuard.has_committed_request
    )
    original_validate_checkpoint = CanonicalDemoProviderGuard._validate_checkpoint
    original_authorization = demo_authority_module._DemoProviderAuthorization
    original_context = demo_authority_module._CURRENT_AUTHORIZATION
    original_stage_provider_progress = DemoUnitOfWork.stage_provider_progress
    original_commit = DemoUnitOfWork.commit

    def sequence_lock(
        guard: CanonicalDemoProviderGuard,
        session_id: str,
    ) -> ProbedSequenceLock:
        probe.sequence_lock_calls += 1
        probe.events.append("sequence_lock")
        return ProbedSequenceLock(
            original_sequence_lock(guard, session_id),
            probe,
        )

    def has_committed_request(
        guard: CanonicalDemoProviderGuard,
        submission: ActionSubmission,
    ) -> bool:
        probe.has_committed_request_calls += 1
        probe.events.append("has_committed_request")
        return original_has_committed_request(guard, submission)

    def checkpoint(
        orchestrator: CanonicalDemoNarrativeTurnOrchestrator,
        session_id: str,
    ):
        probe.checkpoint_calls += 1
        probe.events.append("checkpoint_factory")
        return original_checkpoint(orchestrator, session_id)

    def load_state(
        orchestrator: CanonicalDemoNarrativeTurnOrchestrator,
        payload: object,
        session_id: str,
    ):
        probe.checkpoint_state_loads += 1
        probe.events.append("state_load")
        return original_load_state(orchestrator, payload, session_id)

    def validate_checkpoint(*args: object, **kwargs: object) -> None:
        probe.checkpoint_validations += 1
        probe.events.append("checkpoint_validation")
        original_validate_checkpoint(*args, **kwargs)

    def authorization(*args: object, **kwargs: object):
        probe.authorization_creations += 1
        probe.events.append("authorization_construction")
        return original_authorization(*args, **kwargs)

    def stage_provider_progress(
        uow: DemoUnitOfWork,
        session_id: str,
        *,
        expected_progress: int,
        next_progress: int,
    ) -> None:
        probe.events.append("stage_provider_progress")
        original_stage_provider_progress(
            uow,
            session_id,
            expected_progress=expected_progress,
            next_progress=next_progress,
        )

    async def commit(uow: DemoUnitOfWork) -> None:
        if uow._pending_provider_progress is not None:
            probe.events.append("provider_progress_commit")
        await original_commit(uow)

    monkeypatch.setattr(
        CanonicalDemoProviderGuard,
        "sequence_lock",
        sequence_lock,
    )
    monkeypatch.setattr(
        CanonicalDemoProviderGuard,
        "has_committed_request",
        has_committed_request,
    )

    monkeypatch.setattr(
        CanonicalDemoNarrativeTurnOrchestrator,
        "_provider_checkpoint",
        checkpoint,
    )
    monkeypatch.setattr(
        CanonicalDemoNarrativeTurnOrchestrator,
        "_load_state",
        load_state,
    )
    monkeypatch.setattr(
        CanonicalDemoProviderGuard,
        "_validate_checkpoint",
        staticmethod(validate_checkpoint),
    )
    monkeypatch.setattr(
        demo_authority_module,
        "_DemoProviderAuthorization",
        authorization,
    )
    monkeypatch.setattr(
        demo_authority_module,
        "_CURRENT_AUTHORIZATION",
        ProbedAuthorizationContext(original_context, probe),
    )
    monkeypatch.setattr(
        DemoUnitOfWork,
        "stage_provider_progress",
        stage_provider_progress,
    )
    monkeypatch.setattr(DemoUnitOfWork, "commit", commit)
    return probe


_CANONICAL_HTTP_STEPS = (
    ("CHOOSE", "death_certificate.action.move_fingers_rhythmically"),
    ("CUSTOM", "请协调员复核我的连续回应和生命体征"),
    ("CONTINUE", None),
    ("CONTINUE", None),
    ("CHOOSE", "death_certificate.action.prove_vitals"),
    ("CONTINUE", None),
    ("CONTINUE", None),
    ("CONTINUE", None),
    ("CHOOSE", "death_certificate.action.inspect_archive"),
    ("EXPLORE", "沿记录与档案审计路径核对签发时间"),
    ("EXPLORE", "核对日志时间顺序以及规程反馈"),
    ("CHOOSE", "death_certificate.action.open_observation"),
    ("OBSERVE", "复核地下患者的生命体征与连续监测历史"),
    ("CONTINUE", None),
    ("CONTINUE", None),
    ("CHOOSE", "death_certificate.action.pause_protocol"),
    ("CHOOSE", "death_certificate.action.ask_coordinator"),
    ("CHOOSE", "death_certificate.action.public_override"),
    ("CHOOSE", "death_certificate.action.final_suspend"),
)


async def _create_default_demo_session(
    client: httpx.AsyncClient, *, identity: str
) -> str:
    created = await client.post(
        "/v1/sessions",
        json={
            "client_request_id": f"{identity}-create",
            "character_definition_id": (
                "character.death_certificate.investigator"
            ),
            "scenario_id": "death_certificate",
        },
    )
    assert created.status_code == 201
    return created.json()["session_id"]


def _fresh_default_demo_app():
    sys.modules.pop("deviation_protocol.api.demo", None)
    module = importlib.import_module("deviation_protocol.api.demo")
    return module._runtime, module.app


async def _submit_canonical_step(
    client: httpx.AsyncClient,
    session_id: str,
    *,
    ordinal: int,
    identity: str,
) -> httpx.Response:
    action_type, value = _CANONICAL_HTTP_STEPS[ordinal - 1]
    view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
    body: dict[str, object] = {
        "turn_id": f"{identity}-turn-{ordinal}",
        "client_request_id": f"{identity}-request-{ordinal}",
        "action_type": action_type,
    }
    if action_type == "CHOOSE":
        assert value in {
            choice["choice_id"]
            for choice in view["action_affordances"]["choices"]
        }
        body["decision_id"] = view["action_affordances"]["decision_id"]
        body["choice_id"] = value
    elif value is not None:
        body["description"] = value
    response = await client.post(
        f"/v1/sessions/{session_id}/actions", json=body
    )
    assert response.status_code == 200, response.text
    assert response.json()["resulting_state_version"] == ordinal
    return response


async def _run_canonical_steps(
    client: httpx.AsyncClient,
    session_id: str,
    *,
    first: int,
    last: int,
    identity: str,
) -> None:
    for ordinal in range(first, last + 1):
        await _submit_canonical_step(
            client,
            session_id,
            ordinal=ordinal,
            identity=identity,
        )


async def _assert_http_rejection_is_atomic(
    client: httpx.AsyncClient,
    runtime: object,
    *,
    session_id: str,
    request_id: str,
    body: dict[str, object],
) -> None:
    store = runtime.store  # type: ignore[attr-defined]
    before = store.snapshot()
    response = await client.post(
        f"/v1/sessions/{session_id}/actions", json=body
    )
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "error_code": "NARRATIVE_PROPOSAL_REJECTED",
            "message": "Narrative processing failed",
        }
    }
    assert store.snapshot() == before
    status = await client.get(
        f"/v1/sessions/{session_id}/requests/{request_id}"
    )
    assert status.status_code == 404
    assert status.json()["error"]["error_code"] == (
        "NARRATIVE_REQUEST_NOT_FOUND"
    )


def _assert_only_jobs_changed(before: object, after: object) -> None:
    assert replace(
        after,  # type: ignore[arg-type]
        narrative_jobs=before.narrative_jobs,  # type: ignore[attr-defined]
    ) == before


def _runtime_guard(runtime: DemoRuntime) -> CanonicalDemoProviderGuard:
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    return orchestrator._guard()


def _provider_submission(session_id: str, *, identity: str) -> ActionSubmission:
    return ActionSubmission(
        session_id=session_id,
        turn_id=f"{identity}-authorized-turn",
        client_request_id=f"{identity}-authorized-request",
        action_type=ActionType.CUSTOM,
        description="请协调员复核我的连续回应和生命体征",
    )


def _uncounted_snapshot(store: CountingSnapshotStore) -> DemoStoreSnapshot:
    return DemoProcessStore.snapshot(store)


def _assert_instrumented_uow_factory_is_composed(
    orchestrator: CanonicalDemoNarrativeTurnOrchestrator,
    store: CountingSnapshotStore,
) -> None:
    factory = orchestrator.uow_factory
    assert getattr(factory, "__self__", None) is store
    assert getattr(factory, "__func__", None) is CountingSnapshotStore.unit_of_work


def _assert_rejected_handle_did_no_work(
    *,
    before: AuthorizationOrderingCounts,
    after: AuthorizationOrderingCounts,
    store_before: DemoStoreSnapshot,
    store_after: DemoStoreSnapshot,
    provider_calls_before: int,
    provider_calls_after: int,
) -> None:
    # Every operation below has its own recorder at the real execution boundary.
    # Store equality remains an atomicity assertion, not evidence for zero calls.
    assert after.sequence_lock_calls == before.sequence_lock_calls
    assert (
        after.sequence_lock_acquire_wait_calls
        == before.sequence_lock_acquire_wait_calls
    )
    assert after.sequence_lock_acquisitions == before.sequence_lock_acquisitions
    assert (
        after.has_committed_request_calls
        == before.has_committed_request_calls
    )
    assert after.uow_factory_calls == before.uow_factory_calls
    assert after.uow_constructions == before.uow_constructions
    assert after.uow_entry_calls == before.uow_entry_calls
    assert after.durable_lock_calls == before.durable_lock_calls
    assert after.durable_lock_lookup_calls == before.durable_lock_lookup_calls
    assert (
        after.durable_lock_acquire_wait_calls
        == before.durable_lock_acquire_wait_calls
    )
    assert after.durable_lock_acquisitions == before.durable_lock_acquisitions
    assert (
        after.durable_committed_request_lookup_calls
        == before.durable_committed_request_lookup_calls
    )
    assert (
        after.durable_committed_request_reads
        == before.durable_committed_request_reads
    )
    assert (
        after.uow_snapshot_retrieval_calls
        == before.uow_snapshot_retrieval_calls
    )
    assert after.durable_snapshot_reads == before.durable_snapshot_reads
    assert after.checkpoint_calls == before.checkpoint_calls
    assert after.checkpoint_state_loads == before.checkpoint_state_loads
    assert after.checkpoint_validations == before.checkpoint_validations
    assert after.store_snapshot_calls == before.store_snapshot_calls
    assert after.authorization_creations == before.authorization_creations
    assert after.context_sets == before.context_sets
    assert after.context_resets == before.context_resets
    assert store_after == store_before
    assert provider_calls_after == provider_calls_before


def _assert_ordered_subsequence(events: list[str], expected: tuple[str, ...]) -> None:
    cursor = 0
    for event in events:
        if event == expected[cursor]:
            cursor += 1
            if cursor == len(expected):
                return
    raise AssertionError(f"missing ordered event subsequence: {expected!r} in {events!r}")


@asynccontextmanager
async def _authorized_provider_transaction(
    client: httpx.AsyncClient,
    runtime: DemoRuntime,
    *,
    identity: str,
) -> AsyncIterator[
    tuple[
        CanonicalDemoProviderGuard,
        NarrativeRequest,
        str,
        DemoStoreSnapshot,
    ]
]:
    session_id = await _create_default_demo_session(client, identity=identity)
    await _submit_canonical_step(
        client,
        session_id,
        ordinal=1,
        identity=identity,
    )
    submission = _provider_submission(session_id, identity=identity)
    orchestrator = runtime.services.turn_orchestrator
    guard = _runtime_guard(runtime)
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    async with guard.sequence_lock(session_id):
        prepared = await orchestrator._prepare_or_execute(submission)
        job = getattr(prepared, "job", None)
        assert job is not None
        request = NarrativeRequest.model_validate(
            job.narrative_request, strict=False
        )
        token = guard.authorize_submission(
            orchestrator._capability(),
            submission,
            checkpoint_factory=lambda: orchestrator._provider_checkpoint(
                session_id
            ),
        )
        before = runtime.store.snapshot()
        try:
            yield guard, request, session_id, before
        finally:
            guard.reset_authorization(token)


async def _attempt_reentrant_provider_use(
    runtime: DemoRuntime,
    guard: CanonicalDemoProviderGuard,
    request: NarrativeRequest,
    *,
    session_id: str,
    identity: str,
) -> object:
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    submission = ActionSubmission(
        session_id=session_id,
        turn_id=f"{identity}-authorized-turn",
        client_request_id=f"{identity}-authorized-request",
        action_type=ActionType.CUSTOM,
        description="请协调员复核我的连续回应和生命体征",
    )
    try:
        token = guard.authorize_submission(
            orchestrator._capability(),
            submission,
            checkpoint_factory=lambda: orchestrator._provider_checkpoint(
                session_id
            ),
        )
    except NarrativeProposalRejectedError as exc:
        return exc
    try:
        return await guard.generate(request)
    finally:
        guard.reset_authorization(token)


def _assert_wrapped_provider_is_not_publicly_reachable(
    guard: CanonicalDemoProviderGuard,
    implementation: object,
) -> None:
    public_names = tuple(name for name in dir(guard) if not name.startswith("_"))
    assert "delegate" not in public_names
    assert "provider" not in public_names
    assert all(getattr(guard, name) is not implementation for name in public_names)


def test_generator_families_are_exact_and_independent() -> None:
    generators = new_demo_generators()

    assert generators.clock().isoformat() == "2000-01-01T00:00:00+00:00"
    assert generators.clock().isoformat() == "2000-01-01T00:00:01+00:00"
    assert generators.player_character_id() == "pc.demo-00000001"
    assert generators.player_character_id() == "pc.demo-00000002"
    assert generators.run_id() == "run.demo-00000001"
    assert generators.run_id() == "run.demo-00000002"
    assert generators.continuous_story_line_id() == "csl.demo-00000001"
    assert generators.continuous_story_line_id() == "csl.demo-00000002"
    assert generators.session_id() == "demo-session-00000001"
    assert generators.session_id() == "demo-session-00000002"
    assert generators.event_id() == "demo-event-00000001"
    assert generators.job_id() == "demo-job-00000001"
    assert generators.lease_token() == "demo-lease-000000000000000000001"
    assert len("demo-lease-000000000000000000001") == 32
    assert generators.worker_id() == "demo-worker-00000001"
    assert generators.seed() == 1
    assert generators.seed() == 2

    independent = new_demo_generators()
    independent.player_character_id()
    independent.run_id()
    assert independent.continuous_story_line_id() == "csl.demo-00000001"
    assert independent.session_id() == "demo-session-00000001"


@pytest.mark.parametrize(
    ("target", "final_value"),
    (
        ("player_character_id", "pc.demo-99999999"),
        ("run_id", "run.demo-99999999"),
        ("continuous_story_line_id", "csl.demo-99999999"),
    ),
)
def test_new_demo_identity_sequences_exhaust_at_exactly_eight_digits_without_consumption(
    target: str,
    final_value: str,
) -> None:
    generators = new_demo_generators()
    sequence = getattr(generators, target)
    assert isinstance(sequence, DemoStringSequence)
    sequence._next_value = 99_999_999

    assert sequence() == final_value
    assert sequence._next_value == 100_000_000
    for _ in range(2):
        with pytest.raises(
            RuntimeError,
            match="^Demo string sequence exhausted its fixed-width boundary$",
        ):
            sequence()
        assert sequence._next_value == 100_000_000

    independent_first_values = {
        name: getattr(generators, name)()
        for name in (
            "player_character_id",
            "run_id",
            "continuous_story_line_id",
        )
        if name != target
    }
    assert independent_first_values == {
        name: {
            "player_character_id": "pc.demo-00000001",
            "run_id": "run.demo-00000001",
            "continuous_story_line_id": "csl.demo-00000001",
        }[name]
        for name in independent_first_values
    }


def _recording_generators() -> tuple[
    DemoGenerators, dict[str, list[object]]
]:
    base = new_demo_generators()
    emitted = {
        name: [] for name in DemoGenerators.__dataclass_fields__
    }

    def record(name: str, generator):
        def invoke():
            value = generator()
            emitted[name].append(value)
            return value

        return invoke

    return (
        DemoGenerators(
            **{
                name: record(name, getattr(base, name))
                for name in DemoGenerators.__dataclass_fields__
            }
        ),
        emitted,
    )


async def _seed_foreign_player_character(store: DemoProcessStore) -> str:
    player_character_id = PlayerCharacterId(value="pc.demo-foreign-owned")
    controller_binding = ControllerBindingRef(value="binding.demo-foreign")
    source_reference = AuthoritySourceRef(value="source.demo-foreign")
    operation_id = PlayerCharacterOperationId(
        value="operation.demo-foreign-create"
    )
    command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    record = CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=source_reference,
    )
    _, fingerprint = creation_fingerprint(command)
    receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=controller_binding,
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=record.contract_version,
            resulting_revision=record.record_revision,
            resulting_lifecycle=record.lifecycle,
        ),
    )
    occurred_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    async with store.unit_of_work() as uow:
        await uow.controller_bindings.add(
            controller_binding, created_at=occurred_at
        )
        await uow.player_characters.add_allocation(
            player_character_id, created_at=occurred_at
        )
        await uow.player_characters.add_initial(
            record, created_at=occurred_at
        )
        await uow.creation_receipts.add(receipt, created_at=occurred_at)
        await uow.commit()
    return player_character_id.value


@pytest.mark.asyncio
async def test_demo_services_share_store_clock_catalog_session_and_fixed_authority(
) -> None:
    runtime = build_demo_runtime()
    player_character_service = runtime.services.player_character_service
    run_service = runtime.services.run_service
    entry_service = runtime.services.run_entry_service

    assert player_character_service is not None
    assert run_service is not None
    assert entry_service is not None
    assert player_character_service.uow_factory == runtime.store.unit_of_work
    assert run_service.uow_factory == runtime.store.unit_of_work
    assert entry_service.uow_factory == runtime.store.unit_of_work
    assert player_character_service.clock is runtime.generators.clock
    assert run_service.clock is runtime.generators.clock
    assert entry_service.clock is runtime.generators.clock
    assert entry_service.session_service is runtime.services.session_service
    assert run_service.player_character_binding_evidence is (
        player_character_service
    )
    assert await player_character_service.controller_binding_resolver.resolve(
        get_demo_dev_principal()
    ) == await run_service.controller_binding_resolver.resolve(
        get_demo_dev_principal()
    )
    assert (
        await run_service.controller_binding_resolver.resolve(
            get_demo_dev_principal()
        )
    ).value == "binding.demo-player"


@pytest.mark.asyncio
async def test_demo_public_create_discover_enter_view_action_and_replay_are_atomic(
) -> None:
    generators, emitted = _recording_generators()
    runtime = build_demo_runtime(generators=generators)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)
    creation_body = {
        "contract_version": "structured-player-character/v1",
        "character_core": {},
        "narration_preferences": {},
    }

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Demo-1"},
                json=creation_body,
            )
            assert created.status_code == 200, created.text
            assert created.json()["player_character_id"] == {
                "value": "pc.demo-00000001"
            }
            assert emitted["clock"][0].isoformat() == (
                "2000-01-01T00:00:00+00:00"
            )
            assert {
                name: len(values) for name, values in emitted.items()
            } == {
                "clock": 1,
                "player_character_id": 1,
                "run_id": 0,
                "continuous_story_line_id": 0,
                "session_id": 0,
                "event_id": 0,
                "job_id": 0,
                "lease_token": 0,
                "worker_id": 0,
                "seed": 0,
            }
            before_create_replay = runtime.store.snapshot()
            emitted_before_create_replay = deepcopy(emitted)
            create_replay = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Demo-1"},
                json=creation_body,
            )
            assert create_replay.json() == created.json()
            assert runtime.store.snapshot() == before_create_replay
            assert emitted == emitted_before_create_replay
            create_mismatch = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Demo-1"},
                json={
                    **creation_body,
                    "character_core": {
                        "name_or_code_name": {
                            "state": "declared",
                            "value": {
                                "authority": "player-expression",
                                "text": "Changed",
                            },
                        }
                    },
                },
            )
            assert create_mismatch.status_code == 409
            assert create_mismatch.json()["error"]["error_code"] == (
                "IDEMPOTENCY_CONFLICT"
            )
            assert runtime.store.snapshot() == before_create_replay
            assert emitted == emitted_before_create_replay

            eligible = await client.get(
                "/v1/player-characters/eligible-for-run-entry"
            )
            assert eligible.status_code == 200
            assert eligible.json()["eligible_player_characters"] == [
                created.json()
            ]
            entry_body = {
                "player_character_id": "pc.demo-00000001",
                "expected_record_revision": 1,
                "scenario_id": "death_certificate",
            }
            pre_entry_snapshot = runtime.store.snapshot()
            pre_entry_emitted = deepcopy(emitted)
            missing = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Missing-1"},
                json={**entry_body, "player_character_id": "pc.demo-missing"},
            )
            stale = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Stale-1"},
                json={**entry_body, "expected_record_revision": 2},
            )
            assert missing.status_code == 404
            assert missing.json()["error"]["error_code"] == (
                "PLAYER_CHARACTER_NOT_FOUND"
            )
            assert stale.status_code == 409
            assert stale.json()["error"]["error_code"] == (
                "PLAYER_CHARACTER_STALE"
            )
            assert runtime.store.snapshot() == pre_entry_snapshot
            assert emitted == pre_entry_emitted
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Demo-1"},
                json=entry_body,
            )
            assert entered.status_code == 200, entered.text
            assert entered.json()["run_id"] == "run.demo-00000001"
            assert entered.json()["session_id"] == "demo-session-00000001"
            committed = runtime.store.snapshot()
            assert len(committed.run_revisions) == 3
            assert next(iter(committed.run_current.values())).state_version == 3
            assert len(committed.run_participations) == 1
            assert len(committed.sessions) == 1
            assert len(committed.events) == 1
            assert {
                name: len(values) for name, values in emitted.items()
            } == {
                "clock": 2,
                "player_character_id": 1,
                "run_id": 1,
                "continuous_story_line_id": 1,
                "session_id": 1,
                "event_id": 1,
                "job_id": 0,
                "lease_token": 0,
                "worker_id": 0,
                "seed": 1,
            }

            emitted_before_entry_replay = deepcopy(emitted)
            entry_replay = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Demo-1"},
                json=entry_body,
            )
            assert entry_replay.json() == entered.json()
            assert runtime.store.snapshot() == committed
            assert emitted == emitted_before_entry_replay

            incompatible = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Demo-1"},
                json={**entry_body, "scenario_id": "other-scenario"},
            )
            assert incompatible.status_code == 409
            assert incompatible.json()["error"]["error_code"] == (
                "IDEMPOTENCY_CONFLICT"
            )
            occupied = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Demo-2"},
                json=entry_body,
            )
            assert occupied.status_code == 409
            assert occupied.json()["error"]["error_code"] == (
                "PLAYER_CHARACTER_NOT_ELIGIBLE"
            )
            assert "run.demo-00000001" not in occupied.text
            assert runtime.store.snapshot() == committed
            assert emitted == emitted_before_entry_replay

            view = await client.get(
                "/v1/sessions/demo-session-00000001/view"
            )
            assert view.status_code == 200
            action = await _submit_canonical_step(
                client,
                "demo-session-00000001",
                ordinal=1,
                identity="run-entry",
            )
            assert action.json()["resulting_state_version"] == 1


@pytest.mark.asyncio
async def test_demo_public_run_entry_hides_foreign_owned_player_character_without_issuance(
) -> None:
    store = DemoProcessStore()
    foreign_id = await _seed_foreign_player_character(store)
    generators, emitted = _recording_generators()
    runtime = build_demo_runtime(store=store, generators=generators)
    baseline = store.snapshot()
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            response = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Foreign-1"},
                json={
                    "player_character_id": foreign_id,
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "error_code": "PLAYER_CHARACTER_NOT_FOUND",
            "message": "Player character was not found",
        }
    }
    public_text = response.text.casefold()
    for private_value in (
        foreign_id,
        "binding.demo-foreign",
        "source.demo-foreign",
        "operation.demo-foreign-create",
        "entry.foreign-1",
        "receipt",
        "run_id",
        "session_id",
    ):
        assert private_value.casefold() not in public_text
    assert store.snapshot() == baseline
    assert not baseline.run_revisions
    assert not baseline.run_current
    assert not baseline.run_participations
    assert not baseline.run_creation_receipts
    assert not baseline.run_mutation_receipts
    assert not baseline.sessions
    assert not baseline.snapshots
    assert not baseline.events
    assert {name: len(values) for name, values in emitted.items()} == {
        name: 0 for name in emitted
    }
    assert store.active_uows == 0
    assert not any(
        lock.locked()
        for registry in (
            store._controller_locks,
            store._player_character_locks,
            store._run_locks,
            store._session_locks,
        )
        for lock in registry.values()
    )


@pytest.mark.asyncio
async def test_demo_public_late_uow_integrity_failure_rolls_back_all_entry_families(
) -> None:
    store = LateIntegrityFailureStore()
    generators, emitted = _recording_generators()
    runtime = build_demo_runtime(store=store, generators=generators)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Integrity-1"},
                json={
                    "contract_version": "structured-player-character/v1",
                    "character_core": {},
                    "narration_preferences": {},
                },
            )
            assert created.status_code == 200, created.text
            baseline = store.snapshot()
            store.fail_late_integrity = True
            failed = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Integrity-1"},
                json={
                    "player_character_id": "pc.demo-00000001",
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )

    assert store.late_integrity_injections == 1
    assert failed.status_code == 500
    assert failed.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    public_text = failed.text.casefold()
    for private_value in (
        _LATE_INTEGRITY_PRIVATE_TEXT,
        "private-late-integrity-session",
        "binding.demo-player",
        "source.demo-run",
        "entry.integrity-1",
        "pc.demo-00000001",
        "run.demo-00000001",
        "csl.demo-00000001",
        "demo-session-00000001",
        "receipt",
    ):
        assert private_value.casefold() not in public_text

    after = store.snapshot()
    assert after == baseline
    assert len(after.controller_bindings) == 1
    assert len(after.player_character_id_allocations) == 1
    assert len(after.player_character_revisions) == 1
    assert len(after.player_character_current) == 1
    assert len(after.player_character_creation_receipts) == 1
    assert not after.player_character_mutation_receipts
    assert not after.run_revisions
    assert not after.run_current
    assert not after.run_participations
    assert not after.run_creation_receipts
    assert not after.run_mutation_receipts
    assert not after.sessions
    assert not after.snapshots
    assert not after.creation_keys
    assert not after.events
    assert {name: len(values) for name, values in emitted.items()} == {
        "clock": 2,
        "player_character_id": 1,
        "run_id": 1,
        "continuous_story_line_id": 1,
        "session_id": 1,
        "event_id": 1,
        "job_id": 0,
        "lease_token": 0,
        "worker_id": 0,
        "seed": 1,
    }
    assert store.active_uows == 0
    assert not any(
        lock.locked()
        for registry in (
            store._controller_locks,
            store._player_character_locks,
            store._run_locks,
            store._session_locks,
        )
        for lock in registry.values()
    )
    assert generators.clock().isoformat() == "2000-01-01T00:00:02+00:00"
    assert generators.player_character_id() == "pc.demo-00000002"
    assert generators.run_id() == "run.demo-00000002"
    assert generators.continuous_story_line_id() == "csl.demo-00000002"
    assert generators.session_id() == "demo-session-00000002"
    assert generators.seed() == 2
    assert generators.event_id() == "demo-event-00000002"
    assert generators.job_id() == "demo-job-00000001"
    assert generators.lease_token() == "demo-lease-000000000000000000001"
    assert generators.worker_id() == "demo-worker-00000001"


def _generators_failing_after_emission(
    target: str,
    mode: str,
    *,
    fail_on_call: int,
) -> tuple[DemoGenerators, dict[str, list[object]]]:
    generators, emitted = _recording_generators()
    original = getattr(generators, target)
    calls = 0

    def invoke():
        nonlocal calls
        value = original()
        calls += 1
        if calls == fail_on_call:
            if mode == "exception":
                raise RuntimeError(f"controlled {target} post-emission failure")
            if mode == "cancellation":
                raise asyncio.CancelledError()
            if mode == "validation":
                return " invalid "
            if mode == "conflict":
                raise OptimisticLockError(
                    f"controlled {target} post-emission conflict"
                )
            raise AssertionError(f"unknown failure mode: {mode}")
        return value

    return replace(generators, **{target: invoke}), emitted


_ISSUANCE_BOUNDARIES = (
    ("character-create", "clock"),
    ("character-create", "player_character_id"),
    ("run-entry", "clock"),
    ("run-entry", "run_id"),
    ("run-entry", "continuous_story_line_id"),
    ("run-entry", "session_id"),
    ("run-entry", "seed"),
    ("run-entry", "event_id"),
)
_POST_EMISSION_CASES = (
    *(
        (operation, target, mode)
        for operation, target in _ISSUANCE_BOUNDARIES
        for mode in ("exception", "conflict", "cancellation")
    ),
    ("character-create", "player_character_id", "validation"),
    ("run-entry", "run_id", "validation"),
    ("run-entry", "continuous_story_line_id", "validation"),
)
_EXPECTED_RECORDED_PREFIXES = {
    "clock": (
        datetime(2000, 1, 1, tzinfo=timezone.utc),
        datetime(2000, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
        datetime(2000, 1, 1, 0, 0, 2, tzinfo=timezone.utc),
    ),
    "player_character_id": (
        "pc.demo-00000001",
        "pc.demo-00000002",
    ),
    "run_id": ("run.demo-00000001", "run.demo-00000002"),
    "continuous_story_line_id": (
        "csl.demo-00000001",
        "csl.demo-00000002",
    ),
    "session_id": (
        "demo-session-00000001",
        "demo-session-00000002",
    ),
    "seed": (1, 2),
    "event_id": ("demo-event-00000001", "demo-event-00000002"),
    "job_id": (),
    "lease_token": (),
    "worker_id": (),
}


def _assert_recorded_generator_prefixes(
    emitted: dict[str, list[object]],
) -> None:
    for name, values in emitted.items():
        expected = _EXPECTED_RECORDED_PREFIXES[name]
        assert values == list(expected[: len(values)])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "target", "mode"), _POST_EMISSION_CASES
)
async def test_demo_generator_values_never_rewind_after_post_emission_failure(
    operation: str,
    target: str,
    mode: str,
) -> None:
    fail_on_call = 2 if operation == "run-entry" and target == "clock" else 1
    generators, emitted = _generators_failing_after_emission(
        target, mode, fail_on_call=fail_on_call
    )
    runtime = build_demo_runtime(generators=generators)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    entry_target = operation == "run-entry"
    creation_body = {
        "contract_version": "structured-player-character/v1",
        "character_core": {},
        "narration_preferences": {},
    }
    entry_body = {
        "player_character_id": "pc.demo-00000001",
        "expected_record_revision": 1,
        "scenario_id": "death_certificate",
    }

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            if entry_target:
                created = await client.post(
                    "/v1/player-characters",
                    headers={"Idempotency-Key": "Create.Boundary-1"},
                    json=creation_body,
                )
                assert created.status_code == 200, created.text
                baseline = runtime.store.snapshot()
                request = client.post(
                    "/v1/runs",
                    headers={"Idempotency-Key": "Entry.Boundary-1"},
                    json=entry_body,
                )
            else:
                baseline = runtime.store.snapshot()
                request = client.post(
                    "/v1/player-characters",
                    headers={"Idempotency-Key": "Create.Boundary-1"},
                    json=creation_body,
                )

            if mode == "cancellation":
                with pytest.raises(asyncio.CancelledError):
                    await request
            else:
                response = await request
                if mode == "conflict":
                    assert response.status_code == 409
                    assert response.json() == {
                        "error": {
                            "error_code": "OPTIMISTIC_LOCK_CONFLICT",
                            "message": "State changed concurrently",
                        }
                    }
                else:
                    assert response.status_code == 500
                    assert response.json() == {
                        "error": {
                            "error_code": "INTERNAL_SERVER_ERROR",
                            "message": "Internal server error",
                        }
                    }

            assert runtime.store.snapshot() == baseline
            assert runtime.store.active_uows == 0
            assert not any(
                lock.locked()
                for registry in (
                    runtime.store._controller_locks,
                    runtime.store._player_character_locks,
                    runtime.store._run_locks,
                    runtime.store._session_locks,
                )
                for lock in registry.values()
            )
            operation_order = (
                (
                    "clock",
                    "run_id",
                    "continuous_story_line_id",
                    "session_id",
                    "seed",
                    "event_id",
                )
                if entry_target
                else ("clock", "player_character_id")
            )
            boundary = operation_order.index(target)
            expected_counts = {name: 0 for name in emitted}
            if entry_target:
                expected_counts.update({"clock": 1, "player_character_id": 1})
            for name in operation_order[: boundary + 1]:
                expected_counts[name] += 1
            assert {name: len(values) for name, values in emitted.items()} == (
                expected_counts
            )
            _assert_recorded_generator_prefixes(emitted)

            if mode == "conflict":
                if entry_target:
                    recovered = await client.post(
                        "/v1/runs",
                        headers={"Idempotency-Key": "Entry.Boundary-1"},
                        json=entry_body,
                    )
                else:
                    recovered = await client.post(
                        "/v1/player-characters",
                        headers={"Idempotency-Key": "Create.Boundary-1"},
                        json=creation_body,
                    )
                assert recovered.status_code == 200, recovered.text
                recovered_counts = dict(expected_counts)
                for name in operation_order:
                    recovered_counts[name] += 1
                assert {
                    name: len(values) for name, values in emitted.items()
                } == recovered_counts
                _assert_recorded_generator_prefixes(emitted)

                committed = runtime.store.snapshot()
                if entry_target:
                    expected_run_ordinal = 2 if boundary >= 1 else 1
                    expected_line_ordinal = 2 if boundary >= 2 else 1
                    expected_session_ordinal = 2 if boundary >= 3 else 1
                    expected_run_id = (
                        f"run.demo-0000000{expected_run_ordinal}"
                    )
                    expected_line_id = (
                        f"csl.demo-0000000{expected_line_ordinal}"
                    )
                    expected_session_id = (
                        f"demo-session-0000000{expected_session_ordinal}"
                    )
                    assert recovered.json()["run_id"] == expected_run_id
                    assert recovered.json()["session_id"] == expected_session_id
                    assert tuple(committed.run_current) == (expected_run_id,)
                    current = committed.run_current[expected_run_id]
                    assert current.continuous_story_line_id.value == (
                        expected_line_id
                    )
                    assert tuple(committed.sessions) == (expected_session_id,)
                    assert len(committed.run_revisions) == 3
                    assert len(committed.run_participations) == 1
                    assert len(committed.run_creation_receipts) == 1
                    assert len(committed.run_mutation_receipts) == 2
                    assert len(committed.snapshots) == 1
                    assert len(committed.events) == 1
                    assert recovered_counts["player_character_id"] == 1
                else:
                    expected_character_ordinal = (
                        2 if target == "player_character_id" else 1
                    )
                    expected_character_id = (
                        f"pc.demo-0000000{expected_character_ordinal}"
                    )
                    assert recovered.json()["player_character_id"] == {
                        "value": expected_character_id
                    }
                    assert tuple(committed.player_character_current) == (
                        expected_character_id,
                    )
                    assert len(committed.player_character_revisions) == 1
                    assert len(committed.player_character_creation_receipts) == 1
                    assert not committed.run_current
                    assert recovered_counts["run_id"] == 0
                    assert recovered_counts["continuous_story_line_id"] == 0
                assert runtime.store.active_uows == 0
                assert not any(
                    lock.locked()
                    for registry in (
                        runtime.store._controller_locks,
                        runtime.store._player_character_locks,
                        runtime.store._run_locks,
                        runtime.store._session_locks,
                    )
                    for lock in registry.values()
                )

    if mode != "conflict":
        next_value = getattr(generators, target)()
        expected_next = {
            "clock": (
                "2000-01-01T00:00:02+00:00"
                if entry_target
                else "2000-01-01T00:00:01+00:00"
            ),
            "player_character_id": "pc.demo-00000002",
            "run_id": "run.demo-00000002",
            "continuous_story_line_id": "csl.demo-00000002",
            "session_id": "demo-session-00000002",
            "seed": 2,
            "event_id": "demo-event-00000002",
        }[target]
        if target == "clock":
            next_value = next_value.isoformat()
        assert next_value == expected_next


@pytest.mark.asyncio
async def test_view_failure_after_run_entry_preserves_committed_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    service_type = type(runtime.services.session_service)
    original = service_type.get_view
    calls = 0

    async def fail_first_view(self, principal, session_id):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("controlled first View failure")
        return await original(self, principal, session_id)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.View-Failure"},
                json={
                    "contract_version": "structured-player-character/v1",
                    "character_core": {},
                    "narration_preferences": {},
                },
            )
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.View-Failure"},
                json={
                    "player_character_id": created.json()[
                        "player_character_id"
                    ]["value"],
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )
            assert entered.status_code == 200, entered.text
            committed = runtime.store.snapshot()
            monkeypatch.setattr(service_type, "get_view", fail_first_view)
            path = f"/v1/sessions/{entered.json()['session_id']}/view"
            failed = await client.get(path)
            recovered = await client.get(path)

    assert failed.status_code == 500
    assert failed.json()["error"]["error_code"] == "INTERNAL_SERVER_ERROR"
    assert recovered.status_code == 200
    assert recovered.json()["metadata"]["state_version"] == 0
    assert runtime.store.snapshot() == committed


def test_demo_composition_has_no_engine_or_external_provider_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("production constructor must not be called")

    monkeypatch.setattr("deviation_protocol.api.main.create_engine", forbidden)
    monkeypatch.setattr(
        "deviation_protocol.api.main.DeepSeekNarrativeProvider", forbidden
    )

    implementation = DeterministicDemoNarrativeProvider()
    runtime = build_demo_runtime(provider=implementation)

    assert runtime.services.engine is None
    assert runtime.services.narrative_provider is runtime.provider
    assert not isinstance(runtime.provider, CanonicalDemoProviderGuard)
    _assert_wrapped_provider_is_not_publicly_reachable(
        _runtime_guard(runtime), implementation
    )
    assert isinstance(
        runtime.services.turn_orchestrator,
        CanonicalDemoNarrativeTurnOrchestrator,
    )
    assert runtime.store.snapshot().sessions == {}


def test_dedicated_demo_asgi_entrypoint_is_explicit_and_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import deviation_protocol.api.main as normal_main

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("normal runtime constructor must not be called")

    monkeypatch.setattr(normal_main, "build_default_services", forbidden)
    monkeypatch.setattr(normal_main, "create_engine", forbidden)
    monkeypatch.setattr(normal_main, "DeepSeekNarrativeProvider", forbidden)
    sys.modules.pop("deviation_protocol.api.demo", None)

    demo_module = importlib.import_module("deviation_protocol.api.demo")

    assert demo_module.app is not normal_main.app
    assert demo_module._runtime.services.engine is None
    assert not isinstance(
        demo_module._runtime.provider, CanonicalDemoProviderGuard
    )
    assert not hasattr(demo_module._runtime.provider, "delegate")
    assert not hasattr(demo_module._runtime.provider, "provider")
    assert all(
        "trace" not in path.casefold() and "debug" not in path.casefold()
        for path in demo_module.app.openapi()["paths"]
    )


def test_production_composition_public_surface_exposes_no_authority_path() -> None:
    implementation = DeterministicDemoNarrativeProvider()
    runtime = build_demo_runtime(provider=implementation)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)

    assert not hasattr(orchestrator, "canonical_provider_guard")
    assert not hasattr(orchestrator, "demo_authority_capability")

    owners = (
        runtime,
        runtime.services,
        orchestrator,
        runtime.provider,
        runtime.services.narrative_provider,
    )
    forbidden_name_parts = (
        "authority",
        "authorize",
        "authorization",
        "capability",
        "delegate",
        "guard",
    )
    for owner in owners:
        public_members = tuple(
            (name, member)
            for name, member in inspect.getmembers_static(owner)
            if not name.startswith("_")
        )
        assert all(
            not isinstance(member, CanonicalDemoProviderGuard)
            for _, member in public_members
        )
        assert all(member is not implementation for _, member in public_members)
        assert all(
            not any(part in name.casefold() for part in forbidden_name_parts)
            for name, _ in public_members
        )


@pytest.mark.asyncio
async def test_historical_public_authority_bypass_fails_then_request_calls_provider_once() -> None:
    implementation = CountingProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            identity = "public-authority-bypass"
            session_id = await _create_default_demo_session(
                client, identity=identity
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity=identity,
            )
            submission = _provider_submission(session_id, identity=identity)
            orchestrator = runtime.services.turn_orchestrator
            assert isinstance(
                orchestrator, CanonicalDemoNarrativeTurnOrchestrator
            )

            bypass_error: BaseException | None = None
            try:
                public_guard = getattr(
                    orchestrator, "canonical_provider_guard"
                )
                public_capability = getattr(
                    orchestrator, "demo_authority_capability"
                )
                assert isinstance(public_guard, CanonicalDemoProviderGuard)
                async with public_guard.sequence_lock(session_id):
                    prepared = await orchestrator._prepare_or_execute(
                        submission
                    )
                    job = getattr(prepared, "job", None)
                    assert job is not None
                    request = NarrativeRequest.model_validate(
                        job.narrative_request, strict=False
                    )
                    token = public_guard.authorize_submission(
                        public_capability,
                        submission,
                        checkpoint_factory=lambda: orchestrator._provider_checkpoint(
                            session_id
                        ),
                    )
                    try:
                        await public_guard.generate(request)
                    finally:
                        public_guard.reset_authorization(token)
            except AttributeError as exc:
                bypass_error = exc

            calls_after_bypass = implementation.calls
            response = await orchestrator.handle(submission)
            repeated = await orchestrator.handle(submission)

            with pytest.raises(NarrativeProposalRejectedError):
                await runtime.provider.generate(implementation.requests[-1])

    assert (calls_after_bypass, implementation.calls) == (0, 1)
    assert type(bypass_error) is AttributeError
    assert response == repeated
    assert response.resulting_state_version == 2
    assert _runtime_guard(runtime).completed_calls(session_id) == 1


@pytest.mark.asyncio
async def test_originating_task_can_use_authorized_provider_allowance_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider(events=probe.events)
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="single-use"
            ) as (guard, request, session_id, before):
                authorized_counts = probe.counts(store)
                proposal = await guard.generate(request)
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)

                assert authorized_counts.checkpoint_calls == 1
                assert authorized_counts.checkpoint_state_loads >= 1
                assert authorized_counts.checkpoint_validations == 1
                assert authorized_counts.store_snapshot_calls >= 2
                assert authorized_counts.authorization_creations == 1
                assert authorized_counts.context_sets == 1
                assert authorized_counts.context_resets == 0
                assert proposal.provider_metadata.provider == "deterministic-demo"
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0

            assert probe.context_resets == 1


@pytest.mark.asyncio
async def test_public_non_nested_authorization_runs_checkpoint_validation_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider(events=probe.events)
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="public-non-nested"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="public-non-nested",
            )
            before = probe.counts(store)
            events_before = len(probe.events)

            await _submit_canonical_step(
                client,
                session_id,
                ordinal=2,
                identity="public-non-nested",
            )

            after = probe.counts(store)
            operation_events = probe.events[events_before:]

    assert after.sequence_lock_calls - before.sequence_lock_calls == 2
    assert (
        after.sequence_lock_acquire_wait_calls
        - before.sequence_lock_acquire_wait_calls
        == 1
    )
    assert (
        after.sequence_lock_acquisitions
        - before.sequence_lock_acquisitions
        == 1
    )
    assert (
        after.has_committed_request_calls
        - before.has_committed_request_calls
        == 1
    )
    assert after.uow_factory_calls - before.uow_factory_calls > 0
    assert (
        after.uow_constructions - before.uow_constructions
        == after.uow_factory_calls - before.uow_factory_calls
    )
    assert (
        after.uow_entry_calls - before.uow_entry_calls
        == after.uow_factory_calls - before.uow_factory_calls
    )
    assert after.durable_lock_calls - before.durable_lock_calls > 0
    assert (
        after.durable_lock_lookup_calls - before.durable_lock_lookup_calls
        == after.durable_lock_calls - before.durable_lock_calls
    )
    assert (
        after.durable_lock_acquire_wait_calls
        - before.durable_lock_acquire_wait_calls
        == after.durable_lock_calls - before.durable_lock_calls
    )
    assert (
        after.durable_lock_acquisitions - before.durable_lock_acquisitions
        == after.durable_lock_calls - before.durable_lock_calls
    )
    assert (
        after.durable_committed_request_lookup_calls
        - before.durable_committed_request_lookup_calls
        > 0
    )
    assert (
        after.durable_committed_request_reads
        - before.durable_committed_request_reads
        > 0
    )
    assert (
        after.uow_snapshot_retrieval_calls
        - before.uow_snapshot_retrieval_calls
        > 0
    )
    assert after.durable_snapshot_reads - before.durable_snapshot_reads > 0
    assert after.checkpoint_calls - before.checkpoint_calls == 1
    assert after.checkpoint_validations - before.checkpoint_validations == 1
    assert after.store_snapshot_calls - before.store_snapshot_calls == 4
    assert after.authorization_creations - before.authorization_creations == 1
    assert after.context_sets - before.context_sets == 1
    assert after.context_resets - before.context_resets == 1
    assert implementation.calls == 1
    assert _runtime_guard(runtime).completed_calls(session_id) == 1
    _assert_ordered_subsequence(
        operation_events,
        (
            "sequence_lock",
            "has_committed_request",
            "checkpoint_factory",
            "state_load",
            "checkpoint_validation",
            "authorization_construction",
            "context_set",
            "sequence_lock",
            "provider",
            "stage_provider_progress",
            "provider_progress_commit",
            "context_reset",
        ),
    )


@pytest.mark.asyncio
async def test_same_session_handle_reentry_rejects_before_lock_and_preserves_outer_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="same-session-handle-reentry"
            ) as (guard, request, session_id, _):
                owner_task = asyncio.current_task()
                before = probe.counts(store)
                store_before = _uncounted_snapshot(store)
                provider_calls_before = implementation.calls

                with pytest.raises(NarrativeProposalRejectedError):
                    async with asyncio.timeout(0.5):
                        await orchestrator.handle(
                            _provider_submission(
                                session_id,
                                identity="same-session-handle-reentry",
                            )
                        )

                after = probe.counts(store)
                assert asyncio.current_task() is owner_task
                _assert_rejected_handle_did_no_work(
                    before=before,
                    after=after,
                    store_before=store_before,
                    store_after=_uncounted_snapshot(store),
                    provider_calls_before=provider_calls_before,
                    provider_calls_after=implementation.calls,
                )
                proposal = await guard.generate(request)
                assert proposal.provider_metadata.provider == "deterministic-demo"
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)
                assert implementation.calls == 1

            resets_after_outer_cleanup = probe.context_resets
            with pytest.raises(NarrativeProposalRejectedError):
                await runtime.provider.generate(request)
            assert probe.context_resets == resets_after_outer_cleanup == 1

            later_session_id = await _create_default_demo_session(
                client, identity="same-task-later-independent"
            )
            await _submit_canonical_step(
                client,
                later_session_id,
                ordinal=1,
                identity="same-task-later-independent",
            )
            await _submit_canonical_step(
                client,
                later_session_id,
                ordinal=2,
                identity="same-task-later-independent",
            )

    assert implementation.calls == 2
    assert _runtime_guard(runtime).completed_calls(later_session_id) == 1


@pytest.mark.asyncio
async def test_cross_session_handle_reentry_rejects_before_snapshot_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            nested_identity = "cross-session-nested"
            nested_session_id = await _create_default_demo_session(
                client, identity=nested_identity
            )
            await _submit_canonical_step(
                client,
                nested_session_id,
                ordinal=1,
                identity=nested_identity,
            )
            async with _authorized_provider_transaction(
                client, runtime, identity="cross-session-outer"
            ) as (guard, request, _, _):
                before = probe.counts(store)
                store_before = _uncounted_snapshot(store)
                provider_calls_before = implementation.calls

                with pytest.raises(NarrativeProposalRejectedError):
                    await orchestrator.handle(
                        _provider_submission(
                            nested_session_id,
                            identity=nested_identity,
                        )
                    )

                after = probe.counts(store)
                _assert_rejected_handle_did_no_work(
                    before=before,
                    after=after,
                    store_before=store_before,
                    store_after=_uncounted_snapshot(store),
                    provider_calls_before=provider_calls_before,
                    provider_calls_after=implementation.calls,
                )
                await guard.generate(request)
                assert implementation.calls == 1


@pytest.mark.asyncio
async def test_consumed_outer_handle_reentry_rejects_without_restoring_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            nested_identity = "consumed-outer-nested"
            nested_session_id = await _create_default_demo_session(
                client, identity=nested_identity
            )
            await _submit_canonical_step(
                client,
                nested_session_id,
                ordinal=1,
                identity=nested_identity,
            )
            async with _authorized_provider_transaction(
                client, runtime, identity="consumed-outer"
            ) as (guard, request, _, _):
                await guard.generate(request)
                before = probe.counts(store)
                store_before = _uncounted_snapshot(store)
                provider_calls_before = implementation.calls

                with pytest.raises(NarrativeProposalRejectedError):
                    await orchestrator.handle(
                        _provider_submission(
                            nested_session_id,
                            identity=nested_identity,
                        )
                    )

                after = probe.counts(store)
                _assert_rejected_handle_did_no_work(
                    before=before,
                    after=after,
                    store_before=store_before,
                    store_after=_uncounted_snapshot(store),
                    provider_calls_before=provider_calls_before,
                    provider_calls_after=implementation.calls,
                )
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)
                assert implementation.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("attempt_count", (1, 8))
async def test_inherited_child_handle_attempts_reject_before_all_nested_work(
    monkeypatch: pytest.MonkeyPatch,
    attempt_count: int,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    _assert_instrumented_uow_factory_is_composed(orchestrator, store)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            nested_identity = f"child-handle-{attempt_count}"
            nested_session_id = await _create_default_demo_session(
                client, identity=nested_identity
            )
            await _submit_canonical_step(
                client,
                nested_session_id,
                ordinal=1,
                identity=nested_identity,
            )
            submission = _provider_submission(
                nested_session_id,
                identity=nested_identity,
            )
            async with _authorized_provider_transaction(
                client,
                runtime,
                identity=f"child-handle-outer-{attempt_count}",
            ) as (guard, request, _, _):
                before = probe.counts(store)
                store_before = _uncounted_snapshot(store)
                provider_calls_before = implementation.calls

                results = await asyncio.gather(
                    *(
                        asyncio.create_task(orchestrator.handle(submission))
                        for _ in range(attempt_count)
                    ),
                    return_exceptions=True,
                )

                after = probe.counts(store)
                assert len(results) == attempt_count
                assert all(
                    type(result) is NarrativeProposalRejectedError
                    for result in results
                )
                _assert_rejected_handle_did_no_work(
                    before=before,
                    after=after,
                    store_before=store_before,
                    store_after=_uncounted_snapshot(store),
                    provider_calls_before=provider_calls_before,
                    provider_calls_after=implementation.calls,
                )
                await guard.generate(request)
                assert implementation.calls == 1


@pytest.mark.asyncio
async def test_checkpoint_factory_exception_precedes_context_install_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CheckpointFactoryError(RuntimeError):
        pass

    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)
    orchestrator = runtime.services.turn_orchestrator
    guard = _runtime_guard(runtime)
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            identity = "checkpoint-factory-error"
            session_id = await _create_default_demo_session(
                client, identity=identity
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity=identity,
            )
            submission = _provider_submission(session_id, identity=identity)
            factory_calls = 0

            def fail_checkpoint_factory():
                nonlocal factory_calls
                factory_calls += 1
                raise CheckpointFactoryError("controlled checkpoint failure")

            before = probe.counts(store)
            store_before = _uncounted_snapshot(store)
            assert demo_authority_module._CURRENT_AUTHORIZATION.get() is None

            with pytest.raises(
                CheckpointFactoryError, match="controlled checkpoint failure"
            ):
                guard.authorize_submission(
                    orchestrator._capability(),
                    submission,
                    checkpoint_factory=fail_checkpoint_factory,
                )

            after = probe.counts(store)
            assert factory_calls == 1
            assert demo_authority_module._CURRENT_AUTHORIZATION.get() is None
            _assert_rejected_handle_did_no_work(
                before=before,
                after=after,
                store_before=store_before,
                store_after=_uncounted_snapshot(store),
                provider_calls_before=0,
                provider_calls_after=implementation.calls,
            )

            await _submit_canonical_step(
                client,
                session_id,
                ordinal=2,
                identity=identity,
            )

    assert implementation.calls == 1
    assert demo_authority_module._CURRENT_AUTHORIZATION.get() is None
    assert _runtime_guard(runtime).completed_calls(session_id) == 1


@pytest.mark.asyncio
async def test_child_task_inheriting_context_cannot_use_provider_allowance() -> None:
    implementation = CountingProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="child-task"
            ) as (guard, request, session_id, before):
                child_result = (
                    await asyncio.gather(
                        asyncio.create_task(guard.generate(request)),
                        return_exceptions=True,
                    )
                )[0]
                proposal = await guard.generate(request)

                assert type(child_result) is NarrativeProposalRejectedError
                assert proposal.provider_metadata.provider == "deterministic-demo"
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_same_task_reentrant_authorization_cannot_restore_unused_outer_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            owner_task = asyncio.current_task()
            async with _authorized_provider_transaction(
                client, runtime, identity="reentrant-unused"
            ) as (guard, request, session_id, before):
                counts_before_nested = probe.counts(store)
                nested_result = await _attempt_reentrant_provider_use(
                    runtime,
                    guard,
                    request,
                    session_id=session_id,
                    identity="reentrant-unused",
                )
                counts_after_nested = probe.counts(store)
                calls_after_nested_attempt = implementation.calls
                outer_proposal = await guard.generate(request)

                assert asyncio.current_task() is owner_task
                assert type(nested_result) is NarrativeProposalRejectedError
                assert counts_after_nested == counts_before_nested
                assert calls_after_nested_attempt == 0
                assert outer_proposal.provider_metadata.provider == (
                    "deterministic-demo"
                )
                assert implementation.calls == 1
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0

            assert probe.context_sets == 1
            assert probe.context_resets == 1
            counts_before_outside_use = probe.counts(store)
            with pytest.raises(NarrativeProposalRejectedError):
                await guard.generate(request)
            assert probe.counts(store) == counts_before_outside_use

            async with _authorized_provider_transaction(
                client, runtime, identity="reentrant-cleanup"
            ) as (next_guard, next_request, next_session_id, next_before):
                next_proposal = await next_guard.generate(next_request)

                assert next_proposal.provider_metadata.provider == (
                    "deterministic-demo"
                )
                assert implementation.calls == 2
                assert runtime.store.snapshot() == next_before
                assert next_guard.completed_calls(next_session_id) == 0

            assert probe.context_sets == 2
            assert probe.context_resets == 2


@pytest.mark.asyncio
async def test_reentrant_authorization_cannot_replace_consumed_outer_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="reentrant-consumed"
            ) as (guard, request, session_id, before):
                outer_proposal = await guard.generate(request)
                counts_before_nested = probe.counts(store)
                nested_result = await _attempt_reentrant_provider_use(
                    runtime,
                    guard,
                    request,
                    session_id=session_id,
                    identity="reentrant-consumed",
                )
                counts_after_nested = probe.counts(store)

                assert outer_proposal.provider_metadata.provider == (
                    "deterministic-demo"
                )
                assert type(nested_result) is NarrativeProposalRejectedError
                assert counts_after_nested == counts_before_nested
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_inherited_child_task_cannot_install_fresh_provider_allowance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="child-reauthorize"
            ) as (guard, request, session_id, before):
                counts_before_child = probe.counts(store)
                nested_result = await asyncio.create_task(
                    _attempt_reentrant_provider_use(
                        runtime,
                        guard,
                        request,
                        session_id=session_id,
                        identity="child-reauthorize",
                    )
                )
                counts_after_child = probe.counts(store)
                calls_after_child_attempt = implementation.calls
                outer_proposal = await guard.generate(request)

                assert type(nested_result) is NarrativeProposalRejectedError
                assert counts_after_child == counts_before_child
                assert calls_after_child_attempt == 0
                assert outer_proposal.provider_metadata.provider == (
                    "deterministic-demo"
                )
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_concurrent_inherited_authorizations_do_no_checkpoint_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = _install_authorization_ordering_probe(monkeypatch)
    implementation = CountingProvider()
    store = CountingSnapshotStore(probe)
    runtime = build_demo_runtime(store=store, provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="concurrent-reauthorize"
            ) as (guard, request, session_id, before):
                counts_before_children = probe.counts(store)
                nested_results = await asyncio.gather(
                    *(
                        asyncio.create_task(
                            _attempt_reentrant_provider_use(
                                runtime,
                                guard,
                                request,
                                session_id=session_id,
                                identity="concurrent-reauthorize",
                            )
                        )
                        for _ in range(8)
                    )
                )
                counts_after_children = probe.counts(store)
                outer_proposal = await guard.generate(request)

                assert len(nested_results) == 8
                assert all(
                    type(result) is NarrativeProposalRejectedError
                    for result in nested_results
                )
                assert counts_after_children == counts_before_children
                assert outer_proposal.provider_metadata.provider == (
                    "deterministic-demo"
                )
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_concurrent_attempts_cannot_multiply_underlying_provider_execution() -> None:
    implementation = ConcurrentAttemptProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="concurrent-use"
            ) as (guard, request, session_id, before):
                async def concurrent_attempts() -> list[object]:
                    await implementation.first_entered.wait()
                    results = await asyncio.gather(
                        *(guard.generate(request) for _ in range(8)),
                        return_exceptions=True,
                    )
                    implementation.release_first.set()
                    return list(results)

                attempts = asyncio.create_task(concurrent_attempts())
                proposal = await guard.generate(request)
                results = await attempts

                assert proposal.provider_metadata.provider == "deterministic-demo"
                assert len(results) == 8
                assert all(
                    type(result) is NarrativeProposalRejectedError
                    for result in results
                )
                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_gate_validation_failure_consumes_allowance_without_provider_call() -> None:
    implementation = CountingProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="validation-use"
            ) as (guard, request, session_id, before):
                invalid_request = request.model_copy(
                    update={
                        "player_intent": request.player_intent.model_copy(
                            update={"description": "非授权的替代输入"}
                        )
                    }
                )
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(invalid_request)
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)

                assert implementation.calls == 0
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_provider_failure_does_not_restore_consumed_allowance() -> None:
    implementation = FailOnceProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="failed-use"
            ) as (guard, request, session_id, before):
                with pytest.raises(RuntimeError, match="first Provider failure"):
                    await guard.generate(request)
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)

                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_provider_cancellation_does_not_restore_consumed_allowance() -> None:
    implementation = CancelOnceProvider()
    runtime = build_demo_runtime(provider=implementation)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            async with _authorized_provider_transaction(
                client, runtime, identity="cancelled-use"
            ) as (guard, request, session_id, before):
                with pytest.raises(asyncio.CancelledError):
                    await guard.generate(request)
                with pytest.raises(NarrativeProposalRejectedError):
                    await guard.generate(request)

                assert implementation.calls == 1
                assert runtime.store.snapshot() == before
                assert guard.completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_real_public_app_opens_with_bound_choose_without_provider_or_trace_surface() -> None:
    provider = CountingProvider()
    runtime = build_demo_runtime(provider=provider)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            scenarios = await client.get("/v1/scenarios")
            assert scenarios.status_code == 200
            created = await client.post(
                "/v1/sessions",
                json={
                    "client_request_id": "create-request-1",
                    "character_definition_id": (
                        "character.death_certificate.investigator"
                    ),
                    "scenario_id": "death_certificate",
                },
            )
            assert created.status_code == 201
            assert created.json()["session_id"] == "demo-session-00000001"
            view = await client.get("/v1/sessions/demo-session-00000001/view")
            assert view.status_code == 200
            opening = view.json()
            assert opening["action_affordances"]["mode"] == "DECISION"
            assert opening["action_affordances"]["actions"] == []
            choice = opening["action_affordances"]["choices"][0]
            assert choice["choice_id"] == (
                "death_certificate.action.move_fingers_rhythmically"
            )
            response = await client.post(
                "/v1/sessions/demo-session-00000001/actions",
                json={
                    "turn_id": "turn-1",
                    "client_request_id": "request-1",
                    "action_type": "CHOOSE",
                    "decision_id": opening["action_affordances"]["decision_id"],
                    "choice_id": choice["choice_id"],
                },
            )
            assert response.status_code == 200
            assert provider.calls == 0

    serialized = json.dumps(
        (scenarios.json(), created.json(), opening, response.json()),
        ensure_ascii=False,
    ).casefold()
    for private_marker in (
        "deviation-demo-generator-trace",
        "security_alert",
        "underground_patient_stability",
        "demo-job-",
        "demo-lease-",
        "demo-worker-",
        "deterministic-demo-v1",
    ):
        assert private_marker not in serialized
    assert all(
        "trace" not in path.casefold() and "debug" not in path.casefold()
        for path in app.openapi()["paths"]
    )
    snapshot = runtime.store.snapshot()
    assert len(snapshot.events) == 2
    assert snapshot.narrative_jobs == {}


@pytest.mark.asyncio
async def test_default_demo_rejects_clinical_provider_action_before_opening_choose_atomically() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="pre-opening"
            )
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id="pre-opening-clinical-request",
                body={
                    "turn_id": "pre-opening-clinical-turn",
                    "client_request_id": "pre-opening-clinical-request",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )

    assert _runtime_guard(runtime).completed_calls(session_id) == 0
    assert runtime.store.snapshot().narrative_jobs == {}


@pytest.mark.asyncio
async def test_two_default_demo_sessions_progress_independently_through_complete_scripts() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_a = await _create_default_demo_session(client, identity="session-a")
            session_b = await _create_default_demo_session(client, identity="session-b")
            for ordinal in range(1, len(_CANONICAL_HTTP_STEPS) + 1):
                await _submit_canonical_step(
                    client,
                    session_a,
                    ordinal=ordinal,
                    identity="session-a",
                )
                await _submit_canonical_step(
                    client,
                    session_b,
                    ordinal=ordinal,
                    identity="session-b",
                )
            view_a = (await client.get(f"/v1/sessions/{session_a}/view")).json()
            view_b = (await client.get(f"/v1/sessions/{session_b}/view")).json()

    snapshot = runtime.store.snapshot()
    assert _runtime_guard(runtime).completed_calls(session_a) == 4
    assert _runtime_guard(runtime).completed_calls(session_b) == 4
    assert snapshot.provider_progress == {session_a: 4, session_b: 4}
    assert snapshot.sessions[session_a].session.state_version == 19
    assert snapshot.sessions[session_b].session.state_version == 19
    assert sum(event.session_id == session_a for event in snapshot.events) == 27
    assert sum(event.session_id == session_b for event in snapshot.events) == 27
    assert sum(job.session_id == session_a for job in snapshot.narrative_jobs.values()) == 5
    assert sum(job.session_id == session_b for job in snapshot.narrative_jobs.values()) == 5
    assert view_a["scenario_status"] == view_b["scenario_status"] == "ENDED"


@pytest.mark.asyncio
async def test_concurrent_first_provider_actions_in_two_sessions_do_not_share_a_lock() -> None:
    provider = ConcurrentFirstCallProvider()
    runtime = build_demo_runtime(provider=provider)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_a = await _create_default_demo_session(
                client, identity="concurrent-a"
            )
            session_b = await _create_default_demo_session(
                client, identity="concurrent-b"
            )
            await _submit_canonical_step(
                client, session_a, ordinal=1, identity="concurrent-a"
            )
            await _submit_canonical_step(
                client, session_b, ordinal=1, identity="concurrent-b"
            )
            responses = await asyncio.gather(
                _submit_canonical_step(
                    client, session_a, ordinal=2, identity="concurrent-a"
                ),
                _submit_canonical_step(
                    client, session_b, ordinal=2, identity="concurrent-b"
                ),
            )

    assert [response.status_code for response in responses] == [200, 200]
    assert provider.calls == 2
    assert _runtime_guard(runtime).completed_calls(session_a) == 1
    assert _runtime_guard(runtime).completed_calls(session_b) == 1


@pytest.mark.asyncio
async def test_repeated_and_reordered_calls_in_one_session_do_not_affect_another() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_a = await _create_default_demo_session(client, identity="isolated-a")
            session_b = await _create_default_demo_session(client, identity="isolated-b")
            await _submit_canonical_step(
                client, session_a, ordinal=1, identity="isolated-a"
            )
            await _submit_canonical_step(
                client, session_b, ordinal=1, identity="isolated-b"
            )
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_a,
                request_id="isolated-a-reordered",
                body={
                    "turn_id": "isolated-a-reordered-turn",
                    "client_request_id": "isolated-a-reordered",
                    "action_type": "EXPLORE",
                    "description": "沿记录与档案审计路径核对签发时间",
                },
            )
            await _submit_canonical_step(
                client, session_b, ordinal=2, identity="isolated-b"
            )
            await _submit_canonical_step(
                client, session_a, ordinal=2, identity="isolated-a"
            )
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_a,
                request_id="isolated-a-repeat",
                body={
                    "turn_id": "isolated-a-repeat-turn",
                    "client_request_id": "isolated-a-repeat",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_a,
                request_id="isolated-a-too-early-records",
                body={
                    "turn_id": "isolated-a-too-early-records-turn",
                    "client_request_id": "isolated-a-too-early-records",
                    "action_type": "EXPLORE",
                    "description": "沿记录与档案审计路径核对签发时间",
                },
            )

    assert _runtime_guard(runtime).completed_calls(session_a) == 1
    assert _runtime_guard(runtime).completed_calls(session_b) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_type", "description", "request_id"),
    (
        (
            "EXPLORE",
            "沿记录与档案审计路径核对签发时间",
            "reordered-request",
        ),
        (
            "CUSTOM",
            "这不是冻结的临床复核输入",
            "mismatched-request",
        ),
    ),
    ids=("reordered", "mismatched-input"),
)
async def test_default_demo_provider_guard_rejects_reordered_or_mismatched_call_before_mutation(
    action_type: str,
    description: str,
    request_id: str,
) -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity=request_id
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity=request_id,
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 0
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id=request_id,
                body={
                    "turn_id": f"{request_id}-turn",
                    "client_request_id": request_id,
                    "action_type": action_type,
                    "description": description,
                },
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 0


@pytest.mark.asyncio
async def test_default_demo_provider_guard_rejects_repeated_call_before_mutation() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="repeat"
            )
            await _run_canonical_steps(
                client,
                session_id,
                first=1,
                last=2,
                identity="repeat",
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 1
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id="repeat-invalid-request",
                body={
                    "turn_id": "repeat-invalid-turn",
                    "client_request_id": "repeat-invalid-request",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 1


@pytest.mark.asyncio
async def test_default_demo_exact_provider_request_retry_remains_idempotent() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="idempotent"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="idempotent",
            )
            first = await _submit_canonical_step(
                client,
                session_id,
                ordinal=2,
                identity="idempotent",
            )
            before = runtime.store.snapshot()
            retry = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json={
                    "turn_id": "idempotent-turn-2",
                    "client_request_id": "idempotent-request-2",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )

    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert runtime.store.snapshot() == before
    assert _runtime_guard(runtime).completed_calls(session_id) == 1


@pytest.mark.asyncio
async def test_default_demo_provider_guard_accepts_canonical_order_and_rejects_extra_call() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="canonical"
            )
            await _run_canonical_steps(
                client,
                session_id,
                first=1,
                last=13,
                identity="canonical",
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 4
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id="extra-request",
                body={
                    "turn_id": "extra-turn",
                    "client_request_id": "extra-request",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 4
            await _run_canonical_steps(
                client,
                session_id,
                first=14,
                last=19,
                identity="canonical",
            )
            final_view = (
                await client.get(f"/v1/sessions/{session_id}/view")
            ).json()

    assert final_view["metadata"]["state_version"] == 19
    assert final_view["scenario_status"] == "ENDED"
    assert final_view["ending_status"] == "RESOLVED"
    assert len(runtime.store.snapshot().events) == 27
    assert len(runtime.store.snapshot().narrative_jobs) == 5


@pytest.mark.asyncio
async def test_default_demo_completion_rejects_missing_provider_call_before_mutation() -> None:
    runtime, app = _fresh_default_demo_app()
    assert isinstance(_runtime_guard(runtime), CanonicalDemoProviderGuard)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="missing"
            )
            await _run_canonical_steps(
                client,
                session_id,
                first=1,
                last=18,
                identity="missing",
            )
            assert _runtime_guard(runtime).completed_calls(session_id) == 4
            runtime.store._provider_progress[session_id] = 3
            view = (
                await client.get(f"/v1/sessions/{session_id}/view")
            ).json()
            final_choice = "death_certificate.action.final_suspend"
            assert final_choice in {
                choice["choice_id"]
                for choice in view["action_affordances"]["choices"]
            }
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id="missing-final-request",
                body={
                    "turn_id": "missing-final-turn",
                    "client_request_id": "missing-final-request",
                    "action_type": "CHOOSE",
                    "decision_id": view["action_affordances"]["decision_id"],
                    "choice_id": final_choice,
                },
            )

    snapshot = runtime.store.snapshot()
    assert snapshot.sessions[session_id].session.state_version == 18
    assert len(snapshot.events) == 26
    assert len(snapshot.narrative_jobs) == 4


@pytest.mark.asyncio
async def test_post_provider_proposal_validation_failure_preserves_progress_and_gameplay() -> None:
    provider = CountingProvider()
    runtime = build_demo_runtime(provider=provider)
    orchestrator = runtime.services.turn_orchestrator
    assert isinstance(orchestrator, CanonicalDemoNarrativeTurnOrchestrator)
    orchestrator.proposal_validator = RejectAfterProviderValidator()  # type: ignore[assignment]
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="proposal-rejection"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="proposal-rejection",
            )
            before = runtime.store.snapshot()
            body = {
                "turn_id": "proposal-rejection-turn-2",
                "client_request_id": "proposal-rejection-request-2",
                "action_type": "CUSTOM",
                "description": "请协调员复核我的连续回应和生命体征",
            }
            failed = await client.post(
                f"/v1/sessions/{session_id}/actions", json=body
            )
            after = runtime.store.snapshot()
            before_exact_retry = runtime.store.snapshot()
            exact_retry = await client.post(
                f"/v1/sessions/{session_id}/actions", json=body
            )
            assert runtime.store.snapshot() == before_exact_retry
            await _assert_http_rejection_is_atomic(
                client,
                runtime,
                session_id=session_id,
                request_id="proposal-rejection-new-request",
                body={
                    **body,
                    "turn_id": "proposal-rejection-new-turn",
                    "client_request_id": "proposal-rejection-new-request",
                },
            )

    assert failed.status_code == exact_retry.status_code == 503
    assert provider.calls == 1
    _assert_only_jobs_changed(before, after)
    assert _runtime_guard(runtime).completed_calls(session_id) == 0
    assert len(after.narrative_jobs) == 1
    failed_job = next(iter(after.narrative_jobs.values()))
    assert failed_job.status is NarrativeJobStatus.FAILED_TERMINAL
    assert failed_job.error_code == "NARRATIVE_PROPOSAL_REJECTED"


def test_dynamic_composition_defaults_to_fake_without_credential_selection() -> None:
    runtime = build_dynamic_demo_runtime(
        environ={"DEEPSEEK_API_KEY": "unused-test-value"}
    )
    assert runtime.provider.__class__.__name__ == "_DynamicFakeProvider"
    assert runtime.provider.invocation_count == 0


@pytest.mark.asyncio
async def test_dynamic_fake_observation_resets_and_never_constructs_live(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class CredentialSentinel(dict[str, str]):
        def get(self, key: str, default=None):
            if key.startswith("DEEPSEEK_"):
                raise AssertionError("Fake selection must not inspect credentials")
            return super().get(key, default)

    source = CredentialSentinel(
        {
            "DEVIATION_DEMO_DYNAMIC_PROVIDER": "fake",
            "DEVIATION_DEMO_DYNAMIC_FAKE_FAILURE_AT_ACTION": "5",
            "DEEPSEEK_API_KEY": "inherited-sentinel-must-not-be-read",
        }
    )
    live_calls: list[str] = []

    def forbidden_settings(*args, **kwargs):
        del args, kwargs
        live_calls.append("settings")
        raise AssertionError("Fake selection must not read Live settings")

    def forbidden_live_provider(*args, **kwargs):
        del args, kwargs
        live_calls.append("provider")
        raise AssertionError("Fake selection must not construct a Live Provider")

    with monkeypatch.context() as trapped:
        trapped.setattr(
            demo_composition_module.DeepSeekSettings,
            "from_environment",
            forbidden_settings,
        )
        trapped.setattr(
            demo_composition_module,
            "DeepSeekNarrativeProvider",
            forbidden_live_provider,
        )
        first = build_dynamic_demo_runtime(environ=source)
        second = build_dynamic_demo_runtime(environ=source)
        try:
            assert first.provider.__class__.__name__ == "_DynamicFakeProvider"
            assert second.provider.__class__.__name__ == "_DynamicFakeProvider"
            assert first.provider.invocation_count == second.provider.invocation_count == 0
            assert first._owned_resources == (first.provider,)
            assert second._owned_resources == (second.provider,)
            assert live_calls == []
        finally:
            await first.aclose()
            await second.aclose()

    assert capsys.readouterr().out.splitlines() == [
        "DNVS_FAKE_EVIDENCE event=reset cumulative_invocations=0",
        "DNVS_FAKE_EVIDENCE event=reset cumulative_invocations=0",
    ]
def test_dynamic_composition_invalid_selector_fails_closed() -> None:
    with pytest.raises(DynamicDemoConfigurationError):
        build_dynamic_demo_runtime(
            environ={"DEVIATION_DEMO_DYNAMIC_PROVIDER": ""}
        )


@pytest.mark.asyncio
async def test_dynamic_runtime_closes_owned_provider_exactly_once() -> None:
    class ClosableProvider:
        def __init__(self) -> None:
            self.closes = 0

        async def generate_dynamic(self, request):  # pragma: no cover - no call
            raise AssertionError("shutdown test must not invoke the Provider")

        async def aclose(self) -> None:
            self.closes += 1

    provider = ClosableProvider()
    runtime = build_dynamic_demo_runtime(
        provider=provider,
        own_injected_provider=True,
        environ={},
    )
    await asyncio.gather(runtime.aclose(), runtime.aclose(), runtime.aclose())
    assert provider.closes == 1


@pytest.mark.asyncio
async def test_dynamic_runtime_leaves_injected_caller_owned_provider_open() -> None:
    class CallerOwnedProvider:
        def __init__(self) -> None:
            self.closes = 0

        async def generate_dynamic(self, request):  # pragma: no cover - no call
            raise AssertionError("shutdown ownership test must not call Provider")

        async def aclose(self) -> None:
            self.closes += 1

    provider = CallerOwnedProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    await runtime.aclose()
    assert provider.closes == 0


def test_dynamic_live_selection_with_missing_or_retrying_settings_fails_closed() -> None:
    with pytest.raises(DynamicDemoConfigurationError):
        build_dynamic_demo_runtime(
            environ={"DEVIATION_DEMO_DYNAMIC_PROVIDER": "live"}
        )
    with pytest.raises(DynamicDemoConfigurationError):
        build_dynamic_demo_runtime(
            environ={
                "DEVIATION_DEMO_DYNAMIC_PROVIDER": "live",
                "DEEPSEEK_API_KEY": "unit-test-sentinel",
                "DEEPSEEK_MAX_RETRIES": "1",
            }
        )


@pytest.mark.asyncio
async def test_dynamic_live_selection_is_exact_explicit_opt_in_with_zero_retries(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime = build_dynamic_demo_runtime(
        environ={
            "DEVIATION_DEMO_DYNAMIC_PROVIDER": "live",
            "DEEPSEEK_API_KEY": "unit-test-sentinel",
            "DEEPSEEK_MAX_RETRIES": "0",
        }
    )
    try:
        assert isinstance(
            runtime.provider, demo_composition_module._DynamicLiveEvidenceProvider
        )
        assert runtime.provider.wrapper_attempt_count == 0
        assert isinstance(runtime.provider._provider, DeepSeekNarrativeProvider)
        assert runtime.services.turn_orchestrator.provider_name == "deepseek"
        assert runtime.services.turn_orchestrator.live_provider_references
        assert runtime.provider._provider._settings.max_retries == 0
        assert (
            runtime.provider._provider._settings.max_tokens
            == DEFAULT_DEEPSEEK_MAX_TOKENS
            == 4_096
        )
        assert capsys.readouterr().out == ""
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_dynamic_rejection_console_reporter_is_live_selection_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class InjectedProvider:
        async def generate_dynamic(self, request):  # pragma: no cover - no call
            del request
            raise AssertionError("diagnostic isolation must not invoke Provider")

        async def aclose(self) -> None:
            return None

    class LocalLiveProvider(demo_composition_module._DynamicFakeProvider):
        def __init__(self, _settings) -> None:
            super().__init__()
            self.provider_body = (
                "INERT_PROVIDER_BODY_SENTINEL INERT_BASE_URL_SENTINEL "
                "INERT_FULL_RUNTIME_IDENTIFIER_SENTINEL"
            )
            self.base_url = _settings.base_url
            self.runtime_identifier = _settings.model
            self.captured_prompt = ""

        async def generate_dynamic(self, request):
            self.captured_prompt = DynamicPromptBuilder().build(request).user
            generated = await super().generate_dynamic(request)
            payload = generated.candidate
            fact = payload.proposed_public_facts[0].model_copy(
                update={"value": "INERT_PROTECTED_HIDDEN_VALUE_SENTINEL"}
            )
            return generated.model_copy(
                update={
                    "candidate": payload.model_copy(
                        update={
                            "narrative_text": "INERT_CANDIDATE_NARRATIVE_SENTINEL" + "界" * 350,
                            "proposed_consequences": ("INERT_INTERNAL_MARKER_SENTINEL",),
                            "proposed_public_facts": (fact,),
                            "next_scene": payload.next_scene.model_copy(
                                update={"title": "INERT_INTERNAL_IDENTIFIER_SENTINEL"}
                            ),
                            "suggested_actions": (
                                "隐秘建议哨兵。",
                                "比较另一项公开线索。",
                                "谨慎等待新的变化。",
                            ),
                        }
                    ),
                    "provider_metadata": generated.provider_metadata.model_copy(
                        update={"request_id": self.provider_body}
                    ),
                }
            )

    fake = build_dynamic_demo_runtime(environ={})
    injected = build_dynamic_demo_runtime(provider=InjectedProvider(), environ={})
    local_live: LocalLiveProvider | None = None

    def local_factory(settings, _prompt_builder):
        nonlocal local_live
        local_live = LocalLiveProvider(settings)
        return local_live

    monkeypatch.setattr(
        demo_composition_module, "DeepSeekNarrativeProvider", local_factory
    )
    live = build_dynamic_demo_runtime(
        environ={
            "DEVIATION_DEMO_DYNAMIC_PROVIDER": "live",
            "DEEPSEEK_API_KEY": "INERT_CREDENTIAL_SHAPED_SENTINEL",
            "DEEPSEEK_MAX_RETRIES": "0",
        }
    )
    try:
        from deviation_protocol.application.dynamic_narrative_orchestrator import (
            DynamicNarrativeRejectionDiagnostic,
        )

        for runtime in (fake, injected):
            runtime.services.turn_orchestrator._report_rejection(
                DynamicNarrativeRejectionDiagnostic.PRE_LENGTH
            )
        assert capsys.readouterr().out == ""
        app = create_app(services=live.services)
        app.state.api_services = live.services
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://inert.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Inert.Diagnostics.Create"},
                json={
                    "contract_version": "structured-player-character/v1",
                    "character_core": {},
                    "narration_preferences": {},
                },
            )
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Inert.Diagnostics.Entry"},
                json={
                    "player_character_id": created.json()["player_character_id"]["value"],
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )
            assert created.status_code == entered.status_code == 200
            session_id = entered.json()["session_id"]
            import deviation_protocol.application.dynamic_narrative_orchestrator as orchestrator_module

            original_index = orchestrator_module._hidden_reference_index
            monkeypatch.setattr(
                orchestrator_module,
                "_hidden_reference_index",
                lambda *args, **kwargs: (
                    (_ for _ in ()).throw(
                        ValueError("INERT_ORIGINAL_REJECTION_EXCEPTION_SENTINEL")
                    )
                    if local_live is not None and local_live.invocation_count
                    else original_index(*args, **kwargs)
                ),
            )
            rejected = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json={
                    "turn_id": "INERT_INTERNAL_IDENTIFIER_SENTINEL",
                    "client_request_id": "INERT_RUNTIME_IDENTIFIER_SENTINEL",
                    "action_type": "CUSTOM",
                    "description": "INERT_SUBMITTED_ACTION_SENTINEL INERT_PROMPT_FRAGMENT_SENTINEL",
                },
            )
            assert rejected.status_code == 503
            assert rejected.json() == {
                "error": {
                    "error_code": "NARRATIVE_PROPOSAL_REJECTED",
                    "message": "Narrative processing failed",
                }
            }
            assert "DNVS_LIVE_DIAG_PRE_REFERENCE_INDEX" not in rejected.text
        captured = capsys.readouterr()
        assert captured.out == (
            "DNVS_LIVE_EVIDENCE event=wrapper_attempt ordinal=1 "
            "cumulative_wrapper_attempts=1\n"
            "DNVS_LIVE_DIAG_PRE_REFERENCE_INDEX\n"
        )
        assert captured.err == ""
        output = captured.out + captured.err
        assert "event=wrapper_attempt" in output
        assert "cumulative_wrapper_attempts=1" in output
        assert "event=provider_generation" not in output
        assert "cumulative_generations" not in output
        for sentinel in (
            "INERT_SUBMITTED_ACTION_SENTINEL",
            "INERT_CANDIDATE_NARRATIVE_SENTINEL",
            "隐秘建议哨兵。",
            "INERT_PROMPT_FRAGMENT_SENTINEL",
            "INERT_PROTECTED_HIDDEN_VALUE_SENTINEL",
            "INERT_INTERNAL_MARKER_SENTINEL",
            "INERT_INTERNAL_IDENTIFIER_SENTINEL",
            "INERT_PROVIDER_BODY_SENTINEL",
            "INERT_BASE_URL_SENTINEL",
            "INERT_CREDENTIAL_SHAPED_SENTINEL",
            "INERT_FULL_RUNTIME_IDENTIFIER_SENTINEL",
            "INERT_ORIGINAL_REJECTION_EXCEPTION_SENTINEL",
            "ValueError",
            "Traceback",
        ):
            assert sentinel not in output
        assert isinstance(
            live.provider, demo_composition_module._DynamicLiveEvidenceProvider
        )
        assert live.provider.wrapper_attempt_count == 1
        assert local_live is not None and local_live.invocation_count == 1
        assert "INERT_PROMPT_FRAGMENT_SENTINEL" in local_live.captured_prompt
        assert local_live.base_url
        assert local_live.runtime_identifier
    finally:
        await fake.aclose()
        await injected.aclose()
        await live.aclose()


@pytest.mark.asyncio
async def test_deterministic_demo_rejection_remains_console_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider = RejectingProvider()
    runtime = build_demo_runtime(provider=provider)
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://inert.test"
        ) as client:
            session_id = await _create_default_demo_session(client, identity="silent-demo")
            response = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json={
                    "turn_id": "silent-demo-turn",
                    "client_request_id": "silent-demo-request",
                    "action_type": "CONTINUE",
                },
            )
        assert response.status_code == 200
        assert provider.calls == 0
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
        assert "DNVS_LIVE_DIAG_" not in captured.out + captured.err
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_ordinary_dynamic_fake_rejection_remains_console_silent(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class OrdinaryProvider(demo_composition_module._DynamicFakeProvider):
        async def generate_dynamic(self, request):
            generated = await super().generate_dynamic(request)
            return generated.model_copy(
                update={
                    "candidate": generated.candidate.model_copy(
                        update={"narrative_text": "state_version" + "界" * 350}
                    )
                }
            )

    provider = OrdinaryProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://inert.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "ordinary-silent-create"},
                json={"contract_version": "structured-player-character/v1", "character_core": {}, "narration_preferences": {}},
            )
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "ordinary-silent-entry"},
                json={"player_character_id": created.json()["player_character_id"]["value"], "expected_record_revision": 1, "scenario_id": "death_certificate"},
            )
            response = await client.post(
                f"/v1/sessions/{entered.json()['session_id']}/actions",
                json={"turn_id": "ordinary-silent-turn", "client_request_id": "ordinary-silent-request", "action_type": "CUSTOM", "description": "ordinary inert action"},
            )
        assert response.status_code == 503
        assert provider.invocation_count == 1
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
        assert "DNVS_LIVE_DIAG_" not in captured.out + captured.err
        assert "DNVS_LIVE_DIAG_" not in response.text
    finally:
        await runtime.aclose()


def test_injected_provider_with_live_selector_fails_closed_without_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class InjectedProvider:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_dynamic(self, request):  # pragma: no cover - configuration rejects first
            del request
            self.calls += 1
            raise AssertionError("injected Provider must not run")

    provider = InjectedProvider()
    factory_calls: list[str] = []
    monkeypatch.setattr(
        demo_composition_module,
        "DeepSeekNarrativeProvider",
        lambda *_args, **_kwargs: factory_calls.append("factory"),
    )
    with pytest.raises(DynamicDemoConfigurationError):
        build_dynamic_demo_runtime(
            provider=provider,
            environ={
                "DEVIATION_DEMO_DYNAMIC_PROVIDER": "live",
                "DEEPSEEK_API_KEY": "INERT_CREDENTIAL_SHAPED_SENTINEL",
                "DEEPSEEK_MAX_RETRIES": "0",
            },
        )
    captured = capsys.readouterr()
    assert factory_calls == []
    assert provider.calls == 0
    assert captured.out == captured.err == ""


@pytest.mark.asyncio
async def test_dynamic_runtime_closes_all_resources_and_sanitizes_close_failure() -> None:
    class Resource:
        def __init__(self, *, fail: bool = False) -> None:
            self.fail = fail
            self.closes = 0

        async def aclose(self) -> None:
            self.closes += 1
            if self.fail:
                raise RuntimeError("private close detail")

    base = build_dynamic_demo_runtime(environ={})
    first = Resource(fail=True)
    second = Resource()
    runtime = DemoRuntime(
        services=base.services,
        store=base.store,
        generators=base.generators,
        provider=base.provider,
        _owned_resources=(first, second),
    )
    try:
        with pytest.raises(DynamicDemoShutdownError) as captured:
            await runtime.aclose()
        assert str(captured.value) == "DYNAMIC_DEMO_SHUTDOWN_FAILED"
        assert first.closes == second.closes == 1
        with pytest.raises(DynamicDemoShutdownError):
            await runtime.aclose()
        assert first.closes == second.closes == 1
    finally:
        await base.aclose()


@pytest.mark.asyncio
async def test_dynamic_runtime_shutdown_survives_repeated_owner_cancellation() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    class SlowResource:
        def __init__(self) -> None:
            self.closes = 0

        async def aclose(self) -> None:
            self.closes += 1
            entered.set()
            await release.wait()

    base = build_dynamic_demo_runtime(environ={})
    resource = SlowResource()
    runtime = DemoRuntime(
        services=base.services,
        store=base.store,
        generators=base.generators,
        provider=base.provider,
        _owned_resources=(resource,),
    )
    try:
        closing = asyncio.create_task(runtime.aclose())
        await entered.wait()
        closing.cancel()
        closing.cancel()
        closing.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await closing
        assert resource.closes == 1
        await runtime.aclose()
        assert resource.closes == 1
    finally:
        release.set()
        await base.aclose()


@pytest.mark.asyncio
async def test_direct_or_alternate_provider_caller_cannot_bypass_demo_authority() -> None:
    provider = CountingProvider()
    runtime = build_demo_runtime(provider=provider)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="direct-guard"
            )
            await _run_canonical_steps(
                client,
                session_id,
                first=1,
                last=2,
                identity="direct-guard",
            )
            before = runtime.store.snapshot()
            with pytest.raises(NarrativeProposalRejectedError):
                await runtime.provider.generate(provider.requests[0])

    assert runtime.store.snapshot() == before
    assert provider.calls == 1
    assert _runtime_guard(runtime).completed_calls(session_id) == 1


@pytest.mark.asyncio
async def test_provider_cancellation_rolls_back_progress_and_gameplay_atomically() -> None:
    provider = CancellingProvider()
    generators, emitted = _recording_generators()
    runtime = build_demo_runtime(provider=provider, generators=generators)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="provider-cancel"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="provider-cancel",
            )
            before = runtime.store.snapshot()
            emitted_before = deepcopy(emitted)
            request = asyncio.create_task(
                client.post(
                    f"/v1/sessions/{session_id}/actions",
                    json={
                        "turn_id": "provider-cancel-turn-2",
                        "client_request_id": "provider-cancel-request-2",
                        "action_type": "CUSTOM",
                        "description": "请协调员复核我的连续回应和生命体征",
                    },
                )
            )
            await asyncio.wait_for(provider.entered.wait(), timeout=2)
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            after = runtime.store.snapshot()

    _assert_only_jobs_changed(before, after)
    assert provider.calls == 1
    assert _runtime_guard(runtime).completed_calls(session_id) == 0
    assert len(after.narrative_jobs) == 1
    cancelled_job = next(iter(after.narrative_jobs.values()))
    assert cancelled_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
    assert cancelled_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
    for stream in ("job_id", "lease_token", "worker_id"):
        assert len(emitted[stream]) == len(emitted_before[stream]) + 1
    assert runtime.generators.job_id() == "demo-job-00000002"
    assert runtime.generators.lease_token() == (
        "demo-lease-000000000000000000002"
    )
    assert runtime.generators.worker_id() == "demo-worker-00000002"
    assert not runtime.store.any_session_lock_held
    assert runtime.store.active_uows == 0


@pytest.mark.asyncio
async def test_provider_exception_rolls_back_progress_and_gameplay_atomically() -> None:
    provider = ExplodingProvider()
    generators, emitted = _recording_generators()
    runtime = build_demo_runtime(provider=provider, generators=generators)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="provider-exception"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="provider-exception",
            )
            before = runtime.store.snapshot()
            emitted_before = deepcopy(emitted)
            failed = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json={
                    "turn_id": "provider-exception-turn-2",
                    "client_request_id": "provider-exception-request-2",
                    "action_type": "CUSTOM",
                    "description": "请协调员复核我的连续回应和生命体征",
                },
            )
            after = runtime.store.snapshot()

    assert failed.status_code == 503
    assert failed.json()["error"]["error_code"] == "NARRATIVE_PROVIDER_UNAVAILABLE"
    _assert_only_jobs_changed(before, after)
    assert provider.calls == 1
    assert _runtime_guard(runtime).completed_calls(session_id) == 0
    assert next(iter(after.narrative_jobs.values())).status is (
        NarrativeJobStatus.OUTCOME_UNKNOWN
    )
    for stream in ("job_id", "lease_token", "worker_id"):
        assert len(emitted[stream]) == len(emitted_before[stream]) + 1
    assert runtime.generators.job_id() == "demo-job-00000002"
    assert runtime.generators.lease_token() == (
        "demo-lease-000000000000000000002"
    )
    assert runtime.generators.worker_id() == "demo-worker-00000002"


@pytest.mark.asyncio
async def test_gameplay_commit_failure_after_provider_return_is_atomic_and_releases_lock() -> None:
    provider = CountingProvider()
    store = FailProviderGameplayCommitStore()
    runtime = build_demo_runtime(store=store, provider=provider)
    app = create_app(services=runtime.services)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://demo.test",
        ) as client:
            session_id = await _create_default_demo_session(
                client, identity="commit-failure"
            )
            await _submit_canonical_step(
                client,
                session_id,
                ordinal=1,
                identity="commit-failure",
            )
            before = runtime.store.snapshot()
            body = {
                "turn_id": "commit-failure-turn-2",
                "client_request_id": "commit-failure-request-2",
                "action_type": "CUSTOM",
                "description": "请协调员复核我的连续回应和生命体征",
            }
            failed = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json=body,
            )
            after = runtime.store.snapshot()
            pending_retry = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json=body,
            )
            after_pending_retry = runtime.store.snapshot()
            for _ in range(121):
                runtime.generators.clock()
            store.fail_provider_gameplay_commit = False
            resumed = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json=body,
            )
            after_resumed = runtime.store.snapshot()

    assert failed.status_code == 409
    assert pending_retry.status_code == 202
    assert after_pending_retry == after
    assert resumed.status_code == 200
    assert resumed.json()["resulting_state_version"] == 2
    assert provider.calls == 1
    _assert_only_jobs_changed(before, after)
    assert _runtime_guard(runtime).completed_calls(session_id) == 1
    assert after.sessions[session_id].session.state_version == 1
    assert after.snapshots[session_id].state_version == 1
    assert len(after.events) == 2
    assert len(after.turn_requests) == 1
    assert len(after.narrative_jobs) == 1
    pending_job = next(iter(after.narrative_jobs.values()))
    assert pending_job.status is NarrativeJobStatus.PROPOSAL_VALIDATED
    resumed_job = next(iter(after_resumed.narrative_jobs.values()))
    assert resumed_job.status is NarrativeJobStatus.COMMITTED
    assert after_resumed.sessions[session_id].session.state_version == 2
    assert after_resumed.snapshots[session_id].state_version == 2
    assert len(after_resumed.events) == 4
    assert len(after_resumed.turn_requests) == 2
    assert not store.any_session_lock_held
    assert store.active_uows == 0


@pytest.mark.asyncio
async def test_provider_failure_is_terminal_idempotent_and_preserves_last_view() -> None:
    provider = RejectingProvider()
    runtime = build_demo_runtime(provider=provider)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/sessions",
                json={
                    "client_request_id": "failure-create",
                    "character_definition_id": (
                        "character.death_certificate.investigator"
                    ),
                    "scenario_id": "death_certificate",
                },
            )
            session_id = created.json()["session_id"]
            view_path = f"/v1/sessions/{session_id}/view"
            action_path = f"/v1/sessions/{session_id}/actions"
            opening = (await client.get(view_path)).json()
            opening_choice = next(
                choice
                for choice in opening["action_affordances"]["choices"]
                if choice["choice_id"]
                == "death_certificate.action.move_fingers_rhythmically"
            )
            opening_response = await client.post(
                action_path,
                json={
                    "turn_id": "failure-opening-turn",
                    "client_request_id": "failure-opening-request",
                    "action_type": "CHOOSE",
                    "decision_id": opening["action_affordances"]["decision_id"],
                    "choice_id": opening_choice["choice_id"],
                },
            )
            assert opening_response.status_code == 200
            last_committed_view = (await client.get(view_path)).json()
            failing_body = {
                "turn_id": "failure-provider-turn",
                "client_request_id": "failure-provider-request",
                "action_type": "CUSTOM",
                "description": "请协调员复核我的连续回应和生命体征",
            }

            first_failure = await client.post(action_path, json=failing_body)
            repeated_failure = await client.post(action_path, json=failing_body)
            request_status = await client.get(
                f"/v1/sessions/{session_id}/requests/failure-provider-request"
            )
            unchanged_view = (await client.get(view_path)).json()

    assert first_failure.status_code == repeated_failure.status_code == 503
    assert first_failure.json() == repeated_failure.json() == {
        "error": {
            "error_code": "NARRATIVE_PROPOSAL_REJECTED",
            "message": "Narrative processing failed",
        }
    }
    assert provider.calls == 1
    assert request_status.status_code == 200
    assert request_status.json() == {
        "session_id": session_id,
        "client_request_id": "failure-provider-request",
        "status": "FAILED",
        "client_action": "DO_NOT_RETRY",
        "error_code": "NARRATIVE_REQUEST_FAILED",
        "retry_after_seconds": None,
        "response": None,
    }
    assert unchanged_view == last_committed_view
    assert unchanged_view["metadata"]["state_version"] == 1
    snapshot = runtime.store.snapshot()
    assert len(snapshot.events) == 2
    assert len(snapshot.turn_requests) == 1
    assert len(snapshot.narrative_jobs) == 1
    failed_job = next(iter(snapshot.narrative_jobs.values()))
    assert failed_job.status is NarrativeJobStatus.FAILED_TERMINAL
    assert failed_job.error_code == "NARRATIVE_PROPOSAL_REJECTED"
