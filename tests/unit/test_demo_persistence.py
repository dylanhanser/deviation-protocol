from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.narrative_jobs import (
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.ports import PersistedSnapshot
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.demo_persistence import DemoProcessStore
from deviation_protocol.infrastructure.errors import OptimisticLockError


NOW = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _session(*, session_id: str = "session-1", player_id: str = "player-1") -> GameSession:
    return GameSession(
        session_id=session_id,
        player_id=player_id,
        scenario_id="scenario-1",
        scenario_version="1.0.0",
        phase="phase-1",
        turn_number=0,
        state_version=0,
        random_seed=1,
    )


def _event(
    sequence_no: int = 1,
    *,
    event_id: str | None = None,
    session_id: str = "session-1",
) -> DomainEvent:
    return DomainEvent(
        event_id=event_id or f"event-{sequence_no}",
        session_id=session_id,
        turn_id="turn-1",
        sequence_no=sequence_no,
        event_type="demo.changed",
        payload={"sequence": sequence_no},
        occurred_at=NOW + timedelta(seconds=sequence_no),
    )


def _submission(*, request_id: str = "request-1") -> ActionSubmission:
    return ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id=request_id,
        action_type=ActionType.CONTINUE,
    )


def _job(
    *,
    job_id: str = "job-1",
    request_id: str = "request-1",
) -> NarrativeJob:
    return NarrativeJob(
        job_id=job_id,
        session_id="session-1",
        turn_id="turn-1",
        client_request_id=request_id,
        action_signature="a" * 64,
        prepared_state_version=0,
        state_fingerprint="b" * 64,
        scenario_id="scenario-1",
        scenario_content_version="1.0.0",
        request_fingerprint="c" * 64,
        narrative_request={},
        prompt_schema_version="narrative-prompt-v2",
        style_profile_version="1.0.0",
        provider_name="deterministic-demo",
        model_name="deterministic-demo-v1",
        created_at=NOW,
        updated_at=NOW,
    )


def _transition(job: NarrativeJob, **updates: object) -> NarrativeJob:
    values = job.model_dump(mode="python")
    values.update(updates)
    return NarrativeJob.model_validate(values)


def _claimed_job(
    job: NarrativeJob,
    *,
    lease_token: str = "lease-token-00000000000000000001",
    lease_owner: str = "worker-1",
) -> NarrativeJob:
    return _transition(
        job,
        status=NarrativeJobStatus.IN_PROGRESS,
        attempt_count=1,
        lease_token=lease_token,
        lease_owner=lease_owner,
        lease_expires_at=NOW + timedelta(minutes=2),
        updated_at=NOW + timedelta(seconds=1),
    )


def _validated_job(job: NarrativeJob) -> NarrativeJob:
    return _transition(
        job,
        status=NarrativeJobStatus.PROPOSAL_VALIDATED,
        validated_proposal={"proposal": "safe"},
        validated_proposal_digest="e" * 64,
        updated_at=NOW + timedelta(seconds=2),
    )


def _committed_job(
    job: NarrativeJob, *, text: str = "deterministic accepted text"
) -> NarrativeJob:
    return _transition(
        job,
        status=NarrativeJobStatus.COMMITTED,
        lease_token=None,
        lease_owner=None,
        lease_expires_at=None,
        outcome_rule_id="outcome-rule-1",
        accepted_narrative_text=text,
        updated_at=NOW + timedelta(seconds=3),
    )


async def _add_initial(store: DemoProcessStore) -> GameSession:
    session = _session()
    async with store.unit_of_work() as uow:
        await uow.sessions.add_initial(
            session,
            character_definition_id="character-1",
            creation_client_request_id="create-1",
            state={"value": 0},
            created_at=NOW,
        )
        await uow.sessions.persist_events((_event(),), state_version=0)
        await uow.commit()
    return session


@pytest.mark.asyncio
async def test_initial_session_snapshot_event_and_ownership_commit_as_detached_copies() -> None:
    store = DemoProcessStore()
    session = await _add_initial(store)
    session.phase = "mutated-outside"

    async with store.unit_of_work() as uow:
        owned = await uow.sessions.get_owned("session-1", "player-1")
        assert owned is not None
        assert owned.session.phase == "phase-1"
        assert await uow.sessions.get_owned("session-1", "other") is None
        replay = await uow.sessions.get_by_creation_request("player-1", "create-1")
        assert replay == owned
        snapshot = await uow.sessions.get_latest_snapshot("session-1")
        assert snapshot is not None
        assert snapshot.state == {"value": 0}
        assert await uow.sessions.next_event_sequence_no("session-1") == 2

    committed = store.snapshot()
    assert tuple(item.event_id for item in committed.events) == ("event-1",)
    assert store.active_uows == 0


@pytest.mark.asyncio
async def test_uncommitted_and_explicitly_rolled_back_mutations_publish_nothing() -> None:
    store = DemoProcessStore()
    session = _session()

    async with store.unit_of_work() as uow:
        await uow.sessions.add_initial(
            session,
            character_definition_id="character-1",
            creation_client_request_id="create-1",
            state={"value": 0},
            created_at=NOW,
        )
    assert store.snapshot().sessions == {}

    async with store.unit_of_work() as uow:
        await uow.sessions.add_initial(
            session,
            character_definition_id="character-1",
            creation_client_request_id="create-1",
            state={"value": 0},
            created_at=NOW,
        )
        await uow.rollback()
    assert store.snapshot().sessions == {}


@pytest.mark.asyncio
async def test_snapshot_event_turn_commit_and_rollback_restore_session_version() -> None:
    store = DemoProcessStore()
    await _add_initial(store)

    async with store.unit_of_work() as uow:
        assert await uow.sessions.lock_for_turn("session-1")
        loaded = await uow.sessions.get("session-1")
        assert loaded is not None
        receipts = await uow.sessions.persist_events((_event(2),), state_version=1)
        assert receipts[0].is_authentic()
        await uow.sessions.save_snapshot_and_events(
            loaded,
            {"value": 1},
            (),
            expected_state_version=0,
        )
        assert loaded.state_version == 1
        await uow.turn_requests.add(
            _submission(),
            "d" * 64,
            ActionRoute.RESOLVE_LOCAL,
            {"result": "committed"},
        )
        await uow.commit()
    assert loaded.state_version == 1

    committed = store.snapshot()
    assert committed.sessions["session-1"].session.state_version == 1
    assert committed.snapshots["session-1"].state == {"value": 1}
    assert len(committed.events) == 2
    assert committed.turn_requests[("session-1", "request-1")].response == {
        "result": "committed"
    }

    async with store.unit_of_work() as uow:
        assert await uow.sessions.lock_for_turn("session-1")
        rolled_back = await uow.sessions.get("session-1")
        assert rolled_back is not None
        await uow.sessions.persist_events((_event(3),), state_version=2)
        await uow.sessions.save_snapshot_and_events(
            rolled_back,
            {"value": 2},
            (),
            expected_state_version=1,
        )
        assert rolled_back.state_version == 2
        await uow.rollback()
        assert rolled_back.state_version == 1
    assert len(store.snapshot().events) == 2
    assert store.snapshot().snapshots["session-1"].state == {"value": 1}


@pytest.mark.asyncio
async def test_save_snapshot_and_events_rejects_unknown_session_at_method_entry() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    baseline = store.snapshot()
    unknown = _session(session_id="unknown-session")

    async with store.unit_of_work() as uow:
        with pytest.raises(OptimisticLockError, match="state_version changed"):
            await uow.sessions.save_snapshot_and_events(
                unknown,
                {"must_not_publish": True},
                (_event(2, session_id="unknown-session"),),
                expected_state_version=0,
            )

    assert unknown.state_version == 0
    assert store.snapshot() == baseline


@pytest.mark.asyncio
async def test_session_lock_serializes_owners_and_is_released_after_cleanup() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    first_has_lock = asyncio.Event()
    release_first = asyncio.Event()
    second_has_lock = asyncio.Event()

    async def first_owner() -> None:
        async with store.unit_of_work() as uow:
            assert await uow.sessions.lock_for_turn("session-1")
            first_has_lock.set()
            await release_first.wait()

    async def second_owner() -> None:
        await first_has_lock.wait()
        async with store.unit_of_work() as uow:
            assert await uow.sessions.lock_for_turn("session-1")
            second_has_lock.set()

    first = asyncio.create_task(first_owner())
    second = asyncio.create_task(second_owner())
    await first_has_lock.wait()
    await asyncio.sleep(0)
    assert not second_has_lock.is_set()
    release_first.set()
    await asyncio.gather(first, second)
    assert second_has_lock.is_set()
    assert not store.any_session_lock_held

    async with store.unit_of_work() as uow:
        assert not await uow.sessions.lock_for_turn("missing-session")
    assert not store.any_session_lock_held


@pytest.mark.asyncio
async def test_turn_lock_is_released_by_exception_and_explicit_rollback_cleanup() -> None:
    store = DemoProcessStore()
    await _add_initial(store)

    with pytest.raises(RuntimeError, match="forced lock exception"):
        async with store.unit_of_work() as uow:
            assert await uow.sessions.lock_for_turn("session-1")
            assert store.any_session_lock_held
            raise RuntimeError("forced lock exception")
    assert not store.any_session_lock_held

    async with store.unit_of_work() as uow:
        assert await uow.sessions.lock_for_turn("session-1")
        assert store.any_session_lock_held
        await uow.rollback()
        assert not store.any_session_lock_held
    assert not store.any_session_lock_held


@pytest.mark.asyncio
async def test_event_batch_rejects_duplicate_ids_sequences_and_nonpositive_sequence() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    baseline = store.snapshot()
    batches = (
        (
            _event(2, event_id="batch-duplicate"),
            _event(3, event_id="batch-duplicate"),
        ),
        (
            _event(2, event_id="batch-a"),
            _event(2, event_id="batch-b"),
        ),
        (_event(0, event_id="batch-zero"),),
    )
    for batch in batches:
        async with store.unit_of_work() as uow:
            with pytest.raises(OptimisticLockError):
                await uow.sessions.persist_events(batch, state_version=1)
        assert store.snapshot() == baseline


@pytest.mark.asyncio
async def test_unknown_session_writes_fail_without_publication() -> None:
    store = DemoProcessStore()
    baseline = store.snapshot()

    with pytest.raises(ValueError, match="initial snapshot"):
        async with store.unit_of_work() as uow:
            await uow.sessions.add_initial_snapshot(
                _session(session_id="missing"),
                state={"value": 0},
                created_at=NOW,
            )
            await uow.commit()
    assert store.snapshot() == baseline

    with pytest.raises(ValueError, match="turn request"):
        async with store.unit_of_work() as uow:
            await uow.turn_requests.add(
                _submission(),
                "d" * 64,
                ActionRoute.RESOLVE_LOCAL,
                {"result": "unknown"},
            )
            await uow.commit()
    assert store.snapshot() == baseline

    with pytest.raises(ValueError, match="narrative job"):
        async with store.unit_of_work() as uow:
            await uow.narrative_jobs.add(_job())
            await uow.commit()
    assert store.snapshot() == baseline

    async with store.unit_of_work() as uow:
        with pytest.raises(ValueError, match="event"):
            await uow.sessions.persist_events((_event(),), state_version=0)
    assert store.snapshot() == baseline


@pytest.mark.asyncio
async def test_uow_lifecycle_multiple_lock_and_multiple_state_update_are_fail_closed() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    async with store.unit_of_work() as uow:
        await uow.sessions.add_initial(
            _session(session_id="session-2", player_id="player-2"),
            character_definition_id="character-2",
            creation_client_request_id="create-2",
            state={"value": 0},
            created_at=NOW,
        )
        await uow.commit()

    inactive = store.unit_of_work()
    with pytest.raises(RuntimeError, match="not active"):
        await inactive.commit()

    uow = store.unit_of_work()
    await uow.__aenter__()
    try:
        with pytest.raises(RuntimeError, match="re-entered"):
            await uow.__aenter__()
        assert await uow.sessions.lock_for_turn("session-1")
        with pytest.raises(RuntimeError, match="multiple sessions"):
            await uow.sessions.lock_for_turn("session-2")
        loaded = await uow.sessions.get("session-1")
        assert loaded is not None
        await uow.sessions.save_snapshot_and_events(
            loaded,
            {"value": 1},
            (),
            expected_state_version=0,
        )
        with pytest.raises(RuntimeError, match="multiple snapshot updates"):
            await uow.sessions.save_snapshot_and_events(
                loaded,
                {"value": 2},
                (),
                expected_state_version=0,
            )
        await uow.rollback()
        assert loaded.state_version == 0
        await uow.commit()
        with pytest.raises(RuntimeError, match="already committed"):
            await uow.commit()
        with pytest.raises(RuntimeError, match="already committed"):
            await uow.sessions.get("session-1")
        await uow.__aexit__(None, None, None)
    finally:
        if not uow._closed:
            await uow.__aexit__(None, None, None)
    with pytest.raises(RuntimeError, match="not active"):
        await uow.rollback()


@pytest.mark.asyncio
async def test_uniqueness_and_optimistic_failures_are_fail_closed() -> None:
    store = DemoProcessStore()
    await _add_initial(store)

    with pytest.raises(ConcurrentSessionCreateError):
        async with store.unit_of_work() as uow:
            await uow.sessions.add_initial(
                _session(session_id="session-other"),
                character_definition_id="character-1",
                creation_client_request_id="create-1",
                state={"value": 0},
                created_at=NOW,
            )
            await uow.commit()

    async with store.unit_of_work() as uow:
        staged = _session(session_id="staged-session")
        await uow.sessions.add_initial(
            staged,
            character_definition_id="character-1",
            creation_client_request_id="staged-create",
            state={"value": 0},
            created_at=NOW,
        )
        with pytest.raises(ConcurrentSessionCreateError):
            await uow.sessions.add_initial_session(
                staged,
                character_definition_id="character-1",
                creation_client_request_id="staged-create-2",
                created_at=NOW,
            )
        with pytest.raises(OptimisticLockError):
            await uow.sessions.add_initial_snapshot(
                staged, state={"value": 1}, created_at=NOW
            )

    async with store.unit_of_work() as uow:
        loaded = await uow.sessions.get("session-1")
        assert loaded is not None
        with pytest.raises(OptimisticLockError):
            await uow.sessions.save_snapshot_and_events(
                loaded,
                {"value": 99},
                (),
                expected_state_version=9,
            )

    async with store.unit_of_work() as uow:
        await uow.turn_requests.add(
            _submission(), "d" * 64, ActionRoute.RESOLVE_LOCAL, {"result": 1}
        )
        with pytest.raises(ConcurrentTurnRequestError):
            await uow.turn_requests.add(
                _submission(), "d" * 64, ActionRoute.RESOLVE_LOCAL, {"result": 2}
            )

    async with store.unit_of_work() as uow:
        with pytest.raises(OptimisticLockError):
            await uow.sessions.persist_events(
                (_event(2, event_id="event-1"),), state_version=1
            )


@pytest.mark.asyncio
async def test_initial_session_and_snapshot_commit_validation_rejections_are_atomic() -> None:
    empty = DemoProcessStore()
    with pytest.raises(ValueError, match="creation request ID"):
        async with empty.unit_of_work() as uow:
            await uow.sessions.add_initial_session(
                _session(),
                character_definition_id="character-1",
                creation_client_request_id=None,  # type: ignore[arg-type]
                created_at=NOW,
            )
            await uow.commit()
    assert empty.snapshot().sessions == {}

    store = DemoProcessStore()
    await _add_initial(store)
    baseline = store.snapshot()
    with pytest.raises(OptimisticLockError, match="already exists"):
        async with store.unit_of_work() as uow:
            await uow.sessions.add_initial_snapshot(
                _session(), state={"value": 9}, created_at=NOW
            )
            await uow.commit()
    assert store.snapshot() == baseline


@pytest.mark.asyncio
@pytest.mark.parametrize("collision", ("session-id", "creation-key"))
async def test_initial_session_commit_uniqueness_races_publish_only_the_winner(
    collision: str,
) -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    baseline = store.snapshot()
    staged_session = (
        _session(session_id="session-1", player_id="other-player")
        if collision == "session-id"
        else _session(session_id="session-other")
    )
    staged_creation = "other-create" if collision == "session-id" else "create-1"

    with pytest.raises(ConcurrentSessionCreateError):
        async with store.unit_of_work() as uow:
            await uow.sessions.add_initial(
                staged_session,
                character_definition_id="character-1",
                creation_client_request_id=staged_creation,
                state={"value": 99},
                created_at=NOW,
            )
            await uow.commit()
    assert store.snapshot() == baseline


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "external_change",
    ("missing-session", "session-version", "missing-snapshot", "snapshot-version"),
)
async def test_state_update_commit_validation_rejects_each_external_change_atomically(
    external_change: str,
) -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    uow = store.unit_of_work()
    await uow.__aenter__()
    assert await uow.sessions.lock_for_turn("session-1")
    assert store.session_lock_held("session-1")
    loaded = await uow.sessions.get("session-1")
    assert loaded is not None
    await uow.sessions.save_snapshot_and_events(
        loaded,
        {"value": 1},
        (_event(2),),
        expected_state_version=0,
    )
    await uow.turn_requests.add(
        _submission(request_id="state-update-request"),
        "d" * 64,
        ActionRoute.RESOLVE_LOCAL,
        {"must_not_publish": True},
    )
    if external_change == "missing-session":
        del store._sessions["session-1"]
    elif external_change == "session-version":
        store._sessions["session-1"].session.state_version = 9
    elif external_change == "missing-snapshot":
        del store._snapshots["session-1"]
    else:
        store._snapshots["session-1"] = PersistedSnapshot(
            state_version=9,
            state={"value": "external"},
        )
    external_state = store.snapshot()
    try:
        with pytest.raises(OptimisticLockError) as raised:
            await uow.commit()
        await uow.__aexit__(type(raised.value), raised.value, None)
    finally:
        if not uow._closed:
            await uow.__aexit__(None, None, None)
    assert store.snapshot() == external_state
    assert not store.session_lock_held("session-1")
    assert not store.any_session_lock_held


@pytest.mark.asyncio
async def test_provider_progress_commit_rollback_exception_and_validation_are_atomic() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    baseline = store.snapshot()
    assert baseline.provider_progress == {"session-1": 0}

    async with store.unit_of_work() as uow:
        assert await uow.sessions.lock_for_turn("session-1")
        uow.stage_provider_progress(
            "session-1", expected_progress=0, next_progress=1
        )
        await uow.rollback()
    assert store.snapshot() == baseline
    assert not store.any_session_lock_held

    with pytest.raises(RuntimeError, match="progress exception rollback"):
        async with store.unit_of_work() as uow:
            assert await uow.sessions.lock_for_turn("session-1")
            uow.stage_provider_progress(
                "session-1", expected_progress=0, next_progress=1
            )
            raise RuntimeError("progress exception rollback")
    assert store.snapshot() == baseline
    assert not store.any_session_lock_held

    async with store.unit_of_work() as uow:
        uow.stage_provider_progress(
            "session-1", expected_progress=0, next_progress=1
        )
        with pytest.raises(RuntimeError, match="multiple Provider advances"):
            uow.stage_provider_progress(
                "session-1", expected_progress=0, next_progress=1
            )
    assert store.snapshot() == baseline

    for expected_progress, next_progress in ((-1, 0), (0, 0), (0, 2)):
        async with store.unit_of_work() as uow:
            with pytest.raises(ValueError, match="invalid Demo Provider progress"):
                uow.stage_provider_progress(
                    "session-1",
                    expected_progress=expected_progress,
                    next_progress=next_progress,
                )
    async with store.unit_of_work() as uow:
        with pytest.raises(OptimisticLockError, match="changed concurrently"):
            uow.stage_provider_progress(
                "session-1", expected_progress=1, next_progress=2
            )
    assert store.snapshot() == baseline


@pytest.mark.asyncio
@pytest.mark.parametrize("external_change", ("missing-session", "progress"))
async def test_provider_progress_commit_validation_releases_lock_without_publication(
    external_change: str,
) -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    uow = store.unit_of_work()
    await uow.__aenter__()
    assert await uow.sessions.lock_for_turn("session-1")
    if external_change == "progress":
        loaded = await uow.sessions.get("session-1")
        assert loaded is not None
        await uow.sessions.save_snapshot_and_events(
            loaded,
            {"must_not_publish": True},
            (_event(2),),
            expected_state_version=0,
        )
        await uow.turn_requests.add(
            _submission(request_id="progress-validation-request"),
            "d" * 64,
            ActionRoute.NARRATIVE_NORMAL,
            {"must_not_publish": True},
        )
    uow.stage_provider_progress("session-1", expected_progress=0, next_progress=1)
    if external_change == "missing-session":
        del store._sessions["session-1"]
    else:
        store._provider_progress["session-1"] = 2
    external_state = store.snapshot()
    try:
        expected_error = ValueError if external_change == "missing-session" else OptimisticLockError
        with pytest.raises(expected_error) as raised:
            await uow.commit()
        await uow.__aexit__(type(raised.value), raised.value, None)
    finally:
        if not uow._closed:
            await uow.__aexit__(None, None, None)

    assert store.snapshot() == external_state
    assert ("session-1", "progress-validation-request") not in (
        store.snapshot().turn_requests
    )
    assert not store.any_session_lock_held


@pytest.mark.asyncio
async def test_commit_rejects_an_event_whose_pending_session_disappeared() -> None:
    store = DemoProcessStore()
    with pytest.raises(ValueError, match="event refers"):
        async with store.unit_of_work() as uow:
            await uow.sessions.add_initial_session(
                _session(),
                character_definition_id="character-1",
                creation_client_request_id="create-1",
                created_at=NOW,
            )
            await uow.sessions.persist_events((_event(),), state_version=0)
            uow._pending_session = None
            await uow.commit()
    assert store.snapshot().events == ()


@pytest.mark.asyncio
async def test_job_add_claim_fencing_release_terminal_and_recent_text_semantics() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()

    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()

    claimed = _transition(
        prepared,
        status=NarrativeJobStatus.IN_PROGRESS,
        attempt_count=1,
        lease_token="lease-token-00000000000000000001",
        lease_owner="worker-1",
        lease_expires_at=NOW + timedelta(minutes=2),
        updated_at=NOW + timedelta(seconds=1),
    )
    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.get_active_for_session("session-1") == prepared
        assert not await uow.narrative_jobs.replace(
            claimed,
            expected_status=NarrativeJobStatus.PREPARED,
            expected_lease_owner="wrong-owner",
        )
        assert await uow.narrative_jobs.replace(
            claimed, expected_status=NarrativeJobStatus.PREPARED
        )
        await uow.commit()

    terminal = _transition(
        claimed,
        status=NarrativeJobStatus.COMMITTED,
        lease_token=None,
        lease_owner=None,
        lease_expires_at=None,
        validated_proposal={"proposal": "safe"},
        validated_proposal_digest="e" * 64,
        outcome_rule_id="outcome-rule-1",
        accepted_narrative_text="deterministic accepted text",
        updated_at=NOW + timedelta(seconds=2),
    )
    async with store.unit_of_work() as uow:
        assert not await uow.narrative_jobs.replace(
            terminal,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token="wrong-token",
            expected_lease_owner="worker-1",
        )
        assert await uow.narrative_jobs.replace(
            terminal,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token="lease-token-00000000000000000001",
            expected_lease_owner="worker-1",
        )
        await uow.commit()

    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.get_active_for_session("session-1") is None
        assert await uow.narrative_jobs.recent_committed_texts(
            "session-1", limit=5
        ) == ("deterministic accepted text",)


@pytest.mark.asyncio
async def test_two_sequential_job_cas_transitions_commit_in_order_in_one_uow() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()

    claimed = _claimed_job(prepared)
    validated = _validated_job(claimed)
    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.replace(
            claimed,
            expected_status=NarrativeJobStatus.PREPARED,
        )
        assert await uow.narrative_jobs.get("job-1") == claimed
        assert await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner=claimed.lease_owner,
        )
        assert store.snapshot().narrative_jobs["job-1"] == prepared
        await uow.commit()

    assert store.snapshot().narrative_jobs["job-1"] == validated


@pytest.mark.asyncio
async def test_complete_provider_job_lifecycle_can_commit_atomically_in_one_uow() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    claimed = _claimed_job(prepared)
    validated = _validated_job(claimed)
    committed = _committed_job(validated)

    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        assert await uow.narrative_jobs.replace(
            claimed,
            expected_status=NarrativeJobStatus.PREPARED,
        )
        assert await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner=claimed.lease_owner,
        )
        assert await uow.narrative_jobs.replace(
            committed,
            expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
            expected_lease_token=validated.lease_token,
            expected_lease_owner=validated.lease_owner,
        )
        assert store.snapshot().narrative_jobs == {}
        await uow.commit()

    assert store.snapshot().narrative_jobs == {"job-1": committed}


@pytest.mark.asyncio
async def test_staged_sequential_job_transitions_roll_back_explicitly_and_on_exception() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()
    claimed = _claimed_job(prepared)
    validated = _validated_job(claimed)

    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.replace(
            claimed, expected_status=NarrativeJobStatus.PREPARED
        )
        assert await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner=claimed.lease_owner,
        )
        await uow.rollback()
    assert store.snapshot().narrative_jobs["job-1"] == prepared

    with pytest.raises(RuntimeError, match="force exception rollback"):
        async with store.unit_of_work() as uow:
            assert await uow.narrative_jobs.replace(
                claimed, expected_status=NarrativeJobStatus.PREPARED
            )
            assert await uow.narrative_jobs.replace(
                validated,
                expected_status=NarrativeJobStatus.IN_PROGRESS,
                expected_lease_token=claimed.lease_token,
                expected_lease_owner=claimed.lease_owner,
            )
            raise RuntimeError("force exception rollback")
    assert store.snapshot().narrative_jobs["job-1"] == prepared
    assert not store.any_session_lock_held


@pytest.mark.asyncio
async def test_invalid_intermediate_job_cas_and_fencing_mismatch_do_not_stage() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()
    claimed = _claimed_job(prepared)
    validated = _validated_job(claimed)
    committed = _committed_job(validated)

    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.replace(
            claimed, expected_status=NarrativeJobStatus.PREPARED
        )
        assert not await uow.narrative_jobs.replace(
            committed,
            expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner=claimed.lease_owner,
        )
        assert not await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token="wrong-lease-token-0000000000000000",
            expected_lease_owner=claimed.lease_owner,
        )
        assert not await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner="wrong-worker",
        )
    assert store.snapshot().narrative_jobs["job-1"] == prepared


@pytest.mark.asyncio
async def test_external_job_mutation_before_chain_commit_rejects_the_whole_chain() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()

    claimed = _claimed_job(prepared)
    validated = _validated_job(claimed)
    external_claim = _claimed_job(
        prepared,
        lease_token="lease-token-00000000000000000002",
        lease_owner="worker-2",
    )
    staged = store.unit_of_work()
    await staged.__aenter__()
    try:
        assert await staged.narrative_jobs.replace(
            claimed, expected_status=NarrativeJobStatus.PREPARED
        )
        assert await staged.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token=claimed.lease_token,
            expected_lease_owner=claimed.lease_owner,
        )
        await staged.turn_requests.add(
            _submission(request_id="chain-request"),
            "d" * 64,
            ActionRoute.NARRATIVE_NORMAL,
            {"must_not_publish": True},
        )
        async with store.unit_of_work() as external:
            assert await external.narrative_jobs.replace(
                external_claim,
                expected_status=NarrativeJobStatus.PREPARED,
            )
            await external.commit()

        with pytest.raises(OptimisticLockError) as raised:
            await staged.commit()
        await staged.__aexit__(type(raised.value), raised.value, None)
    finally:
        if not staged._closed:
            await staged.__aexit__(None, None, None)

    snapshot = store.snapshot()
    assert snapshot.narrative_jobs["job-1"] == external_claim
    assert ("session-1", "chain-request") not in snapshot.turn_requests


@pytest.mark.asyncio
async def test_recent_committed_text_zero_and_positive_boundaries_match_sql() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    expected = ("first", "second", "third")
    async with store.unit_of_work() as uow:
        for ordinal, text in enumerate(expected, start=1):
            prepared = _job(
                job_id=f"job-{ordinal}", request_id=f"request-{ordinal}"
            )
            claimed = _claimed_job(
                prepared,
                lease_token=f"lease-token-{ordinal:024d}",
                lease_owner=f"worker-{ordinal}",
            )
            validated = _validated_job(claimed)
            committed = _transition(
                _committed_job(validated, text=text),
                created_at=NOW + timedelta(seconds=ordinal),
                updated_at=NOW + timedelta(seconds=ordinal),
            )
            await uow.narrative_jobs.add(committed)
        await uow.commit()

    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.recent_committed_texts(
            "session-1", limit=0
        ) == ()
        assert await uow.narrative_jobs.recent_committed_texts(
            "session-1", limit=1
        ) == ("third",)
        assert await uow.narrative_jobs.recent_committed_texts(
            "session-1", limit=10
        ) == expected


@pytest.mark.asyncio
async def test_duplicate_job_identity_and_rollback_do_not_publish() -> None:
    store = DemoProcessStore()
    await _add_initial(store)

    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(_job())
    assert store.snapshot().narrative_jobs == {}

    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(_job())
        with pytest.raises(ConcurrentTurnRequestError):
            await uow.narrative_jobs.add(_job(job_id="job-2"))

    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(_job())
        with pytest.raises(ConcurrentTurnRequestError):
            await uow.narrative_jobs.add(
                _job(job_id="job-1", request_id="request-other")
            )


@pytest.mark.asyncio
async def test_atomic_commit_conflict_publishes_only_the_winner() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    first = store.unit_of_work()
    second = store.unit_of_work()
    await first.__aenter__()
    await second.__aenter__()
    try:
        await first.turn_requests.add(
            _submission(), "d" * 64, ActionRoute.RESOLVE_LOCAL, {"winner": 1}
        )
        await second.turn_requests.add(
            _submission(), "d" * 64, ActionRoute.RESOLVE_LOCAL, {"winner": 2}
        )
        await second.narrative_jobs.add(_job(job_id="loser-job", request_id="loser"))
        await first.commit()
        with pytest.raises(ConcurrentTurnRequestError) as raised:
            await second.commit()
        await second.__aexit__(type(raised.value), raised.value, None)
        await first.__aexit__(None, None, None)
    finally:
        if store.active_uows:
            if not first._closed:
                await first.__aexit__(None, None, None)
            if not second._closed:
                await second.__aexit__(None, None, None)

    snapshot = store.snapshot()
    assert snapshot.turn_requests[("session-1", "request-1")].response == {
        "winner": 1
    }
    assert "loser-job" not in snapshot.narrative_jobs


@pytest.mark.asyncio
@pytest.mark.parametrize("collision", ("job-id", "request-id"))
async def test_job_add_commit_uniqueness_races_publish_only_the_winner(
    collision: str,
) -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    staged = store.unit_of_work()
    await staged.__aenter__()
    staged_job = _job()
    await staged.narrative_jobs.add(staged_job)
    await staged.turn_requests.add(
        _submission(request_id="staged-turn-request"),
        "d" * 64,
        ActionRoute.NARRATIVE_NORMAL,
        {"must_not_publish": True},
    )
    winner = (
        _job(job_id="job-1", request_id="winner-request")
        if collision == "job-id"
        else _job(job_id="winner-job", request_id="request-1")
    )
    async with store.unit_of_work() as external:
        await external.narrative_jobs.add(winner)
        await external.commit()
    winner_state = store.snapshot()
    try:
        with pytest.raises(ConcurrentTurnRequestError) as raised:
            await staged.commit()
        await staged.__aexit__(type(raised.value), raised.value, None)
    finally:
        if not staged._closed:
            await staged.__aexit__(None, None, None)
    assert store.snapshot() == winner_state


@pytest.mark.asyncio
@pytest.mark.parametrize("collision", ("event-id", "sequence"))
async def test_event_commit_races_reject_the_loser_without_partial_publication(
    collision: str,
) -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    staged = store.unit_of_work()
    await staged.__aenter__()
    staged_event = (
        _event(3, event_id="shared-event")
        if collision == "event-id"
        else _event(2, event_id="staged-event")
    )
    await staged.sessions.persist_events((staged_event,), state_version=1)
    await staged.turn_requests.add(
        _submission(request_id="event-race-request"),
        "d" * 64,
        ActionRoute.RESOLVE_LOCAL,
        {"must_not_publish": True},
    )
    winner_event = (
        _event(2, event_id="shared-event")
        if collision == "event-id"
        else _event(2, event_id="winner-event")
    )
    async with store.unit_of_work() as external:
        await external.sessions.persist_events(
            (winner_event,), state_version=1
        )
        await external.commit()
    winner_state = store.snapshot()
    try:
        with pytest.raises(OptimisticLockError) as raised:
            await staged.commit()
        await staged.__aexit__(type(raised.value), raised.value, None)
    finally:
        if not staged._closed:
            await staged.__aexit__(None, None, None)
    assert store.snapshot() == winner_state


@pytest.mark.asyncio
async def test_job_cas_race_and_expired_validated_reclaim_preserve_fencing() -> None:
    store = DemoProcessStore()
    await _add_initial(store)
    prepared = _job()
    async with store.unit_of_work() as uow:
        await uow.narrative_jobs.add(prepared)
        await uow.commit()

    first_claim = _transition(
        prepared,
        status=NarrativeJobStatus.IN_PROGRESS,
        attempt_count=1,
        lease_token="lease-token-00000000000000000001",
        lease_owner="worker-1",
        lease_expires_at=NOW + timedelta(seconds=1),
        updated_at=NOW + timedelta(seconds=1),
    )
    second_claim = _transition(
        prepared,
        status=NarrativeJobStatus.IN_PROGRESS,
        attempt_count=1,
        lease_token="lease-token-00000000000000000002",
        lease_owner="worker-2",
        lease_expires_at=NOW + timedelta(seconds=1),
        updated_at=NOW + timedelta(seconds=1),
    )
    first = store.unit_of_work()
    second = store.unit_of_work()
    await first.__aenter__()
    await second.__aenter__()
    try:
        assert await first.narrative_jobs.replace(
            first_claim, expected_status=NarrativeJobStatus.PREPARED
        )
        assert await second.narrative_jobs.replace(
            second_claim, expected_status=NarrativeJobStatus.PREPARED
        )
        await first.commit()
        with pytest.raises(OptimisticLockError) as raised:
            await second.commit()
        await second.__aexit__(type(raised.value), raised.value, None)
        await first.__aexit__(None, None, None)
    finally:
        if store.active_uows:
            if not first._closed:
                await first.__aexit__(None, None, None)
            if not second._closed:
                await second.__aexit__(None, None, None)

    validated = _transition(
        first_claim,
        status=NarrativeJobStatus.PROPOSAL_VALIDATED,
        validated_proposal={"proposal": "safe"},
        validated_proposal_digest="e" * 64,
        updated_at=NOW + timedelta(seconds=2),
    )
    async with store.unit_of_work() as uow:
        assert await uow.narrative_jobs.replace(
            validated,
            expected_status=NarrativeJobStatus.IN_PROGRESS,
            expected_lease_token="lease-token-00000000000000000001",
            expected_lease_owner="worker-1",
        )
        await uow.commit()

    reclaimed = _transition(
        validated,
        lease_token="lease-token-00000000000000000003",
        lease_owner="worker-3",
        lease_expires_at=NOW + timedelta(minutes=2),
        updated_at=NOW + timedelta(seconds=3),
    )
    async with store.unit_of_work() as uow:
        assert not await uow.narrative_jobs.replace(
            reclaimed,
            expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
            expected_lease_token=validated.lease_token,
            expected_lease_owner="wrong-worker",
        )
        assert await uow.narrative_jobs.replace(
            reclaimed,
            expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
            expected_lease_token=validated.lease_token,
            expected_lease_owner=validated.lease_owner,
        )
        await uow.commit()

    winner = store.snapshot().narrative_jobs["job-1"]
    assert winner.lease_token == "lease-token-00000000000000000003"
    assert winner.lease_owner == "worker-3"
