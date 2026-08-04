from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.narrative_jobs import (
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.application.ports import (
    MutationReceiptUniquenessConflictError,
    PersistedSnapshot,
    RunPlayerCharacterBindingUniquenessConflictError,
    RunReceiptUniquenessConflictError,
    RunSessionParticipationUniquenessConflictError,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunEntryCreationEvidence,
    RunOperationNamespace,
    RunReceiptKey,
    StoredRunSuccessReceipt,
    activate_first_session_for_run,
    attach_session_fingerprint,
    attach_session_result,
    bind_player_character_fingerprint,
    bind_player_character_result,
    bind_player_character_to_run,
    construct_created_run,
    creation_result as run_creation_result,
    run_entry_creation_fingerprint,
)
from deviation_protocol.application.run_service import (
    stage_run_entry_activation,
    stage_run_entry_binding,
    stage_run_entry_creation,
)
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.infrastructure.demo_generators import new_demo_generators
from deviation_protocol.infrastructure.demo_persistence import (
    DemoProcessStore,
    DemoStoreSnapshot,
    DemoUnitOfWork,
)
from deviation_protocol.infrastructure.errors import (
    OptimisticLockError,
    PlayerCharacterRepositoryConflictError,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunStoredRecordIntegrityError,
    creation_receipt_from_storage as run_creation_receipt_from_storage,
    mutation_receipt_from_storage as run_mutation_receipt_from_storage,
)


NOW = datetime(2000, 1, 1, tzinfo=timezone.utc)

_CREATION_BODY = {
    "contract_version": "structured-player-character/v1",
    "character_core": {},
    "narration_preferences": {},
}


def _character_family(
    label: str, *, controller_label: str | None = None
) -> SimpleNamespace:
    player_character_id = PlayerCharacterId(value=f"pc.demo-test-{label}")
    controller_binding = ControllerBindingRef(
        value=f"binding.demo-test-{controller_label or label}"
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
        source_reference=AuthoritySourceRef(value=f"source.demo-test-{label}"),
    )
    operation_id = PlayerCharacterOperationId(
        value=f"operation.demo-test-{label}"
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
    return SimpleNamespace(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        record=record,
        receipt=receipt,
    )


def _mutation_family(
    family: SimpleNamespace,
    label: str,
) -> SimpleNamespace:
    initial = family.record
    operation_id = PlayerCharacterOperationId(
        value=f"operation.demo-test-mutate-{label}"
    )
    command = CharacterMutationCommand(
        contract_version=initial.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=initial.player_character_id,
        expected_revision=initial.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=initial.player_character_id,
            contract_version=initial.contract_version,
            record_revision=initial.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=initial.player_character_id,
            expected_revision=initial.record_revision,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value=f"source.demo-test-mutate-{label}"
            ),
        ),
    )
    decision = evaluate_mutation_policy(
        initial,
        command=command,
        operation_id=operation_id,
    )
    assert decision.accepted
    successor = decision.resulting_record
    assert successor is not None
    _, fingerprint = mutation_fingerprint(command, operation_id=operation_id)
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=initial.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=successor.player_character_id,
            contract_version=successor.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
    )
    return SimpleNamespace(
        command=command,
        successor=successor,
        receipt=receipt,
    )


async def _commit_character_family(
    store: DemoProcessStore,
    family: SimpleNamespace,
    *,
    add_binding: bool = True,
) -> None:
    async with store.unit_of_work() as uow:
        if add_binding:
            await uow.controller_bindings.add(
                family.controller_binding, created_at=NOW
            )
        await uow.player_characters.add_allocation(
            family.player_character_id, created_at=NOW
        )
        await uow.player_characters.add_initial(
            family.record, created_at=NOW
        )
        await uow.creation_receipts.add(family.receipt, created_at=NOW)
        await uow.commit()


def _run_entry_family(
    label: str,
    *,
    character_family: SimpleNamespace,
    session_id: str,
    run_id: str,
    continuous_story_line_id: str,
) -> SimpleNamespace:
    source = RunAuthoritySourceRef(value=f"source.demo-test-run-{label}")
    typed_run_id = RunId(value=run_id)
    typed_line_id = ContinuousStoryLineId(value=continuous_story_line_id)
    create_operation_id = RunOperationId(
        value=f"operation.demo-test-run-create-{label}"
    )
    bind_operation_id = RunOperationId(
        value=f"operation.demo-test-run-bind-{label}"
    )
    attach_operation_id = RunOperationId(
        value=f"operation.demo-test-run-attach-{label}"
    )
    evidence = RunEntryCreationEvidence.model_validate(
        {
            "controller_operation": {
                "controller_binding": {
                    "value": character_family.controller_binding.value
                },
                "public_operation_key": f"entry.demo-test-{label}",
            },
            "player_character": {
                "player_character_id": {
                    "value": character_family.player_character_id.value
                },
                "pre_entry_record_revision": {"value": 1},
            },
            "scenario": {
                "scenario_id": "death_certificate",
                "content_version": "death-certificate-1.1.0",
                "default_character_definition_id": (
                    "character.death_certificate.investigator"
                ),
            },
            "trusted_run_source": {
                "source_reference": {"value": source.value}
            },
        }
    )
    initial = construct_created_run(
        CreateRunCommand(source_reference=source),
        run_id=typed_run_id,
        continuous_story_line_id=typed_line_id,
        operation_id=create_operation_id,
        occurred_at=NOW,
    )
    _, creation_fingerprint_value = run_entry_creation_fingerprint(evidence)
    creation_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=create_operation_id,
        ),
        fingerprint=creation_fingerprint_value,
        command_kind=RunMutationKind.CREATE,
        result=run_creation_result(initial),
    )
    reference = ApplicableCharacterReference(
        player_character_id=character_family.player_character_id,
        contract_version=character_family.record.contract_version,
        record_revision=character_family.record.record_revision,
    )
    bind_command = BindPlayerCharacterCommand(
        run_id=typed_run_id,
        continuous_story_line_id=typed_line_id,
        target_player_character_id=character_family.player_character_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=source,
    )
    bound = bind_player_character_to_run(
        initial,
        bind_command,
        applicable_character_reference=reference,
        operation_id=bind_operation_id,
        occurred_at=NOW,
    )
    _, binding_fingerprint = bind_player_character_fingerprint(
        bind_command, operation_id=bind_operation_id
    )
    binding_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=typed_run_id,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=bind_operation_id,
        ),
        fingerprint=binding_fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=bind_player_character_result(bound),
    )
    attach_command = AttachSessionCommand(
        run_id=typed_run_id,
        continuous_story_line_id=typed_line_id,
        session_id=session_id,
        expected_state_version=RunStateVersion(value=2),
        source_reference=source,
    )
    active = activate_first_session_for_run(
        bound,
        attach_command,
        operation_id=attach_operation_id,
        occurred_at=NOW,
    )
    _, attachment_fingerprint = attach_session_fingerprint(
        attach_command, operation_id=attach_operation_id
    )
    attachment_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=typed_run_id,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=attach_operation_id,
        ),
        fingerprint=attachment_fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(active),
    )
    return SimpleNamespace(
        initial=initial,
        creation_receipt=creation_receipt,
        evidence=evidence,
        bound=bound,
        binding_receipt=binding_receipt,
        active=active,
        attachment_receipt=attachment_receipt,
    )


async def _stage_run_entry_family(
    uow: DemoUnitOfWork,
    family: SimpleNamespace,
) -> None:
    await stage_run_entry_creation(
        uow,
        family.initial,
        family.creation_receipt,
        family.evidence,
        created_at=NOW,
    )
    assert await stage_run_entry_binding(
        uow,
        family.bound,
        family.binding_receipt,
        created_at=NOW,
    )
    assert await stage_run_entry_activation(
        uow,
        family.active,
        family.attachment_receipt,
        created_at=NOW,
    )


async def _commit_test_session(
    store: DemoProcessStore,
    label: str,
) -> str:
    session_id = f"session.demo-test-{label}"
    session = _session(
        session_id=session_id,
        player_id=f"player.demo-test-{label}",
    )
    async with store.unit_of_work() as uow:
        await uow.sessions.add_initial(
            session,
            character_definition_id="character.demo-test",
            creation_client_request_id=f"create.demo-test-{label}",
            state={"label": label},
            created_at=NOW,
        )
        await uow.sessions.persist_events(
            (
                _event(
                    event_id=f"event.demo-test-{label}",
                    session_id=session_id,
                ),
            ),
            state_version=0,
        )
        await uow.commit()
    return session_id


async def _seed_public_run(
    *,
    store: DemoProcessStore | None = None,
) -> tuple[DemoProcessStore, dict[str, object], dict[str, object]]:
    runtime = build_demo_runtime(store=store)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Persistence-1"},
                json=_CREATION_BODY,
            )
            assert created.status_code == 200, created.text
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Persistence-1"},
                json={
                    "player_character_id": created.json()[
                        "player_character_id"
                    ]["value"],
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )
            assert entered.status_code == 200, entered.text
    return runtime.store, created.json(), entered.json()


class _FailExpandedCommitUnitOfWork(DemoUnitOfWork):
    def _publish_atomically(self) -> None:
        if self._store.fail_expanded_commit:
            raise OptimisticLockError("controlled expanded authority conflict")
        super()._publish_atomically()


class _FailExpandedCommitStore(DemoProcessStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_expanded_commit = False

    def unit_of_work(self) -> DemoUnitOfWork:
        return _FailExpandedCommitUnitOfWork(self)


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


@pytest.mark.asyncio
async def test_player_character_repository_round_trips_complete_detached_family(
) -> None:
    store = DemoProcessStore()
    family = _character_family("round-trip")
    await _commit_character_family(store, family)

    async with store.unit_of_work() as uow:
        binding = await uow.controller_bindings.get(family.controller_binding)
        loaded = await uow.player_characters.get(family.player_character_id)
        receipt = await uow.creation_receipts.get(family.receipt.key)

    assert binding == family.controller_binding
    assert binding is not family.controller_binding
    assert loaded == family.record
    assert loaded is not family.record
    assert receipt == family.receipt
    assert receipt is not family.receipt

    assert loaded is not None
    object.__setattr__(
        loaded,
        "player_character_id",
        PlayerCharacterId(value="pc.demo-test-mutated-copy"),
    )
    object.__setattr__(
        receipt.result,
        "player_character_id",
        PlayerCharacterId(value="pc.demo-test-mutated-receipt-copy"),
    )
    async with store.unit_of_work() as uow:
        assert await uow.player_characters.get(
            family.player_character_id
        ) == family.record
        assert await uow.creation_receipts.get(
            family.receipt.key
        ) == family.receipt


@pytest.mark.asyncio
async def test_player_character_listing_is_owned_active_unbound_stable_and_bounded(
) -> None:
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created_ids: list[str] = []
            for ordinal in range(1, 6):
                response = await client.post(
                    "/v1/player-characters",
                    headers={
                        "Idempotency-Key": f"Create.Listing-{ordinal}"
                    },
                    json=_CREATION_BODY,
                )
                assert response.status_code == 200, response.text
                created_ids.append(
                    response.json()["player_character_id"]["value"]
                )
            retired = await client.post(
                f"/v1/player-characters/{created_ids[1]}/retirement",
                headers={"Idempotency-Key": "Retire.Listing-2"},
                json={
                    "contract_version": "structured-player-character/v1",
                    "expected_revision": {"value": 1},
                    "confirm_retirement": True,
                },
            )
            assert retired.status_code == 200, retired.text
            entered = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Listing-3"},
                json={
                    "player_character_id": created_ids[2],
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )
            assert entered.status_code == 200, entered.text

    foreign = _character_family("foreign")
    await _commit_character_family(runtime.store, foreign)
    async with runtime.store.unit_of_work() as uow:
        listed = await uow.player_characters.list_eligible_for_run_entry(
            ControllerBindingRef(value="binding.demo-player"), limit=2
        )

    assert [item.player_character_id.value for item in listed] == [
        created_ids[0],
        created_ids[3],
    ]
    assert all(
        item.controller_binding.value == "binding.demo-player"
        for item in listed
    )
    assert all(
        item.player_character_id != foreign.player_character_id
        for item in listed
    )


@pytest.mark.asyncio
async def test_player_character_lock_cas_and_receipt_conflicts_publish_no_partial_state(
) -> None:
    store = DemoProcessStore()
    family = _character_family("race")
    async with store.unit_of_work() as seed:
        await seed.controller_bindings.add(
            family.controller_binding, created_at=NOW
        )
        await seed.commit()

    first = store.unit_of_work()
    second = store.unit_of_work()
    await first.__aenter__()
    await second.__aenter__()
    try:
        for uow in (first, second):
            await uow.player_characters.add_allocation(
                family.player_character_id, created_at=NOW
            )
            await uow.player_characters.add_initial(
                family.record, created_at=NOW
            )
            await uow.creation_receipts.add(
                family.receipt, created_at=NOW
            )
        await first.commit()
        winner = store.snapshot()
        with pytest.raises(PlayerCharacterRepositoryConflictError):
            await second.commit()
        assert store.snapshot() == winner
    finally:
        if not first._closed:
            await first.__aexit__(None, None, None)
        if not second._closed:
            await second.__aexit__(None, None, None)

    snapshot = store.snapshot()
    assert len(snapshot.player_character_current) == 1
    assert len(snapshot.player_character_revisions) == 1
    assert len(snapshot.player_character_creation_receipts) == 1

    holder = store.unit_of_work()
    waiter = store.unit_of_work()
    await holder.__aenter__()
    await waiter.__aenter__()
    waiter_started = asyncio.Event()
    waiter_acquired = asyncio.Event()

    async def wait_for_character_lock():
        waiter_started.set()
        loaded = await waiter.player_characters.get_for_update(
            family.player_character_id
        )
        waiter_acquired.set()
        return loaded

    waiter_task = asyncio.create_task(wait_for_character_lock())
    try:
        locked = await holder.player_characters.get_for_update(
            family.player_character_id
        )
        assert locked == family.record
        assert locked is not family.record
        assert store._player_character_locks[
            family.player_character_id.value
        ].locked()
        await waiter_started.wait()
        await asyncio.sleep(0)
        assert not waiter_acquired.is_set()
        await holder.__aexit__(None, None, None)
        waited = await asyncio.wait_for(waiter_task, timeout=1)
        assert waited == family.record
        assert waited is not locked
        assert waiter_acquired.is_set()
        assert store._player_character_locks[
            family.player_character_id.value
        ].locked()
    finally:
        if not waiter_task.done():
            waiter_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter_task
        if not holder._closed:
            await holder.__aexit__(None, None, None)
        if not waiter._closed:
            await waiter.__aexit__(None, None, None)
    assert not store._player_character_locks[
        family.player_character_id.value
    ].locked()

    mutation = _mutation_family(family, "race")
    async with store.unit_of_work() as update:
        current = await update.player_characters.get_for_update(
            family.player_character_id
        )
        assert current == family.record
        await update.player_characters.append_revision(
            mutation.successor, created_at=NOW + timedelta(seconds=1)
        )
        assert await update.player_characters.compare_and_swap_current(
            mutation.successor,
            expected_revision=1,
            created_at=NOW + timedelta(seconds=1),
        )
        await update.mutation_receipts.add(
            mutation.receipt, created_at=NOW + timedelta(seconds=1)
        )
        await update.commit()

    mutated = store.snapshot()
    assert len(mutated.player_character_revisions) == 2
    assert len(mutated.player_character_current) == 1
    assert len(mutated.player_character_creation_receipts) == 1
    assert len(mutated.player_character_mutation_receipts) == 1
    assert next(iter(mutated.player_character_current.values())).record_revision == 2

    async with store.unit_of_work() as stale:
        current = await stale.player_characters.get_for_update(
            family.player_character_id
        )
        assert current == mutation.successor
        assert not await stale.player_characters.compare_and_swap_current(
            mutation.successor,
            expected_revision=1,
            created_at=NOW + timedelta(seconds=2),
        )
    assert store.snapshot() == mutated
    assert not store._player_character_locks[
        family.player_character_id.value
    ].locked()

    receipt_key, stored_receipt = next(
        iter(store._player_character_mutation_receipts.items())
    )
    partial_family = _character_family("unpublished-receipt-loser")
    contender = store.unit_of_work()
    await contender.__aenter__()
    try:
        loaded = await contender.player_characters.get_for_update(
            family.player_character_id
        )
        assert loaded == mutation.successor
        removed = store._player_character_mutation_receipts.pop(receipt_key)
        assert removed == stored_receipt
        try:
            await contender.mutation_receipts.add(
                mutation.receipt, created_at=NOW + timedelta(seconds=2)
            )
            await contender.controller_bindings.add(
                partial_family.controller_binding,
                created_at=NOW + timedelta(seconds=2),
            )
            await contender.player_characters.add_allocation(
                partial_family.player_character_id,
                created_at=NOW + timedelta(seconds=2),
            )
            await contender.player_characters.add_initial(
                partial_family.record,
                created_at=NOW + timedelta(seconds=2),
            )
            await contender.creation_receipts.add(
                partial_family.receipt,
                created_at=NOW + timedelta(seconds=2),
            )
        finally:
            store._player_character_mutation_receipts[receipt_key] = (
                stored_receipt
            )
        with pytest.raises(MutationReceiptUniquenessConflictError):
            await contender.commit()
    finally:
        if not contender._closed:
            await contender.__aexit__(None, None, None)

    assert store.snapshot() == mutated
    assert (
        partial_family.controller_binding.value
        not in store.snapshot().controller_bindings
    )
    assert (
        partial_family.player_character_id.value
        not in store.snapshot().player_character_id_allocations
    )
    assert (
        partial_family.player_character_id.value
        not in store.snapshot().player_character_current
    )
    assert not any(
        identity == partial_family.player_character_id.value
        for identity, _ in store.snapshot().player_character_revisions
    )
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

    async with store.unit_of_work() as recovered:
        recovered_record = await recovered.player_characters.get_for_update(
            family.player_character_id
        )
        recovered_receipt = await recovered.mutation_receipts.get(
            mutation.receipt.key
        )
        assert recovered_record == mutation.successor
        assert recovered_record is not mutation.successor
        assert recovered_receipt == mutation.receipt
        assert recovered_receipt is not mutation.receipt
    assert not store._player_character_locks[
        family.player_character_id.value
    ].locked()
    assert recovered_record is not None
    object.__setattr__(
        recovered_record,
        "player_character_id",
        PlayerCharacterId(value="pc.demo-test-detached-mutated"),
    )
    async with store.unit_of_work() as reread:
        assert await reread.player_characters.get(
            family.player_character_id
        ) == mutation.successor

    generators = new_demo_generators()
    assert generators.player_character_id() == "pc.demo-00000001"
    assert generators.run_id() == "run.demo-00000001"
    assert generators.continuous_story_line_id() == "csl.demo-00000001"


@pytest.mark.asyncio
async def test_run_repository_round_trips_revisions_binding_receipts_and_participation(
) -> None:
    store, created, entered = await _seed_public_run()
    snapshot = store.snapshot()
    run_id = RunId(value=str(entered["run_id"]))
    creation_receipt = run_creation_receipt_from_storage(
        next(iter(snapshot.run_creation_receipts.values()))
    )
    mutation_receipts = tuple(
        run_mutation_receipt_from_storage(item)
        for item in snapshot.run_mutation_receipts.values()
    )

    async with store.unit_of_work() as uow:
        run = await uow.runs.get(run_id)
        participation = await uow.run_participations.get(
            str(entered["session_id"])
        )
        loaded_creation = await uow.run_creation_receipts.get(
            creation_receipt.key
        )
        loaded_mutations = []
        for receipt in mutation_receipts:
            loaded_mutations.append(
                await uow.run_mutation_receipts.get(receipt.key)
            )

    assert run is not None
    assert run.state_version.value == 3
    assert run.lifecycle_status.value == "active"
    assert run.player_character_binding is not None
    reference = run.player_character_binding.applicable_character_reference
    assert reference.player_character_id.value == (
        created["player_character_id"]["value"]
    )
    assert participation in run.trusted_participation_references
    assert loaded_creation == creation_receipt
    assert tuple(loaded_mutations) == mutation_receipts
    assert len(snapshot.run_revisions) == 3


@pytest.mark.asyncio
async def test_run_active_binding_participation_and_receipt_uniqueness_are_atomic(
) -> None:
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Run-Race"},
                json=_CREATION_BODY,
            )
            character_id = created.json()["player_character_id"]["value"]
            body = {
                "player_character_id": character_id,
                "expected_record_revision": 1,
                "scenario_id": "death_certificate",
            }
            first, second = await asyncio.gather(
                client.post(
                    "/v1/runs",
                    headers={"Idempotency-Key": "Entry.Run-Race-A"},
                    json=body,
                ),
                client.post(
                    "/v1/runs",
                    headers={"Idempotency-Key": "Entry.Run-Race-B"},
                    json=body,
                ),
            )

    assert sorted((first.status_code, second.status_code)) == [200, 409]
    loser = first if first.status_code == 409 else second
    assert loser.json()["error"]["error_code"] == (
        "PLAYER_CHARACTER_NOT_ELIGIBLE"
    )
    snapshot = runtime.store.snapshot()
    assert len(snapshot.run_current) == 1
    assert len(snapshot.run_revisions) == 3
    assert len(snapshot.run_creation_receipts) == 1
    assert len(snapshot.run_mutation_receipts) == 2
    assert len(snapshot.run_participations) == 1
    assert len(snapshot.sessions) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "collision",
    ("participation", "mutation-receipt", "active-binding"),
)
async def test_run_direct_final_publication_uniqueness_collisions_are_atomic(
    collision: str,
) -> None:
    store = DemoProcessStore()
    generators = new_demo_generators()
    partial_binding = ControllerBindingRef(
        value=f"binding.demo-test-unpublished-run-{collision}"
    )

    if collision == "participation":
        winner_character = _character_family("participation-winner")
        loser_character = _character_family("participation-loser")
        recovery_character = _character_family("participation-recovery")
        for character in (
            winner_character,
            loser_character,
            recovery_character,
        ):
            await _commit_character_family(store, character)
        shared_session = await _commit_test_session(store, "participation-shared")
        recovery_session = await _commit_test_session(
            store, "participation-recovery"
        )
        winner_family = _run_entry_family(
            "participation-winner",
            character_family=winner_character,
            session_id=shared_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        loser_family = _run_entry_family(
            "participation-loser",
            character_family=loser_character,
            session_id=shared_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        first = store.unit_of_work()
        second = store.unit_of_work()
        await first.__aenter__()
        await second.__aenter__()
        try:
            owned = await second.sessions.get_owned_for_update(
                shared_session, "player.demo-test-participation-shared"
            )
            assert owned is not None
            await _stage_run_entry_family(first, winner_family)
            await _stage_run_entry_family(second, loser_family)
            assert shared_session in second._pending_run_participations
            await first.commit()
            winner_snapshot = store.snapshot()
            with pytest.raises(
                RunSessionParticipationUniquenessConflictError
            ):
                await second.commit()
        finally:
            if not first._closed:
                await first.__aexit__(None, None, None)
            if not second._closed:
                await second.__aexit__(None, None, None)
        recovery_family = _run_entry_family(
            "participation-recovery",
            character_family=recovery_character,
            session_id=recovery_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        expected_next_ordinal = 4
    elif collision == "active-binding":
        shared_character = _character_family("active-shared")
        recovery_character = _character_family("active-recovery")
        await _commit_character_family(store, shared_character)
        await _commit_character_family(store, recovery_character)
        winner_session = await _commit_test_session(store, "active-winner")
        loser_session = await _commit_test_session(store, "active-loser")
        recovery_session = await _commit_test_session(store, "active-recovery")
        winner_family = _run_entry_family(
            "active-winner",
            character_family=shared_character,
            session_id=winner_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        loser_family = _run_entry_family(
            "active-loser",
            character_family=shared_character,
            session_id=loser_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        first = store.unit_of_work()
        second = store.unit_of_work()
        await first.__aenter__()
        await second.__aenter__()
        try:
            assert (
                await second.runs.get_active_for_player_character_for_update(
                    shared_character.player_character_id
                )
                is None
            )
            await _stage_run_entry_family(first, winner_family)
            await _stage_run_entry_family(second, loser_family)
            assert (
                loser_family.active.run_id.value
                in second._pending_run_current
            )
            await first.commit()
            winner_snapshot = store.snapshot()
            with pytest.raises(
                RunPlayerCharacterBindingUniquenessConflictError
            ):
                await second.commit()
        finally:
            if not first._closed:
                await first.__aexit__(None, None, None)
            if not second._closed:
                await second.__aexit__(None, None, None)
        recovery_family = _run_entry_family(
            "active-recovery",
            character_family=recovery_character,
            session_id=recovery_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        expected_next_ordinal = 4
    else:
        baseline_character = _character_family("receipt-baseline")
        loser_character = _character_family("receipt-loser")
        recovery_character = _character_family("receipt-recovery")
        await _commit_character_family(store, baseline_character)
        await _commit_character_family(store, loser_character)
        await _commit_character_family(store, recovery_character)
        baseline_session = await _commit_test_session(store, "receipt-baseline")
        loser_session = await _commit_test_session(store, "receipt-loser")
        recovery_session = await _commit_test_session(store, "receipt-recovery")
        winner_family = _run_entry_family(
            "receipt-baseline",
            character_family=baseline_character,
            session_id=baseline_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        async with store.unit_of_work() as seed:
            await _stage_run_entry_family(seed, winner_family)
            await seed.commit()
        winner_snapshot = store.snapshot()
        loser_family = _run_entry_family(
            "receipt-loser",
            character_family=loser_character,
            session_id=loser_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        target_key, target_stored_receipt = next(
            (key, value)
            for key, value in store._run_mutation_receipts.items()
            if key[1] == RunOperationNamespace.ATTACH_SESSION_V1.value
        )
        contender = store.unit_of_work()
        await contender.__aenter__()
        try:
            locked = await contender.runs.get_for_update(
                winner_family.active.run_id
            )
            assert locked == winner_family.active
            await _stage_run_entry_family(contender, loser_family)
            removed = store._run_mutation_receipts.pop(target_key)
            assert removed == target_stored_receipt
            try:
                await contender.run_mutation_receipts.add(
                    winner_family.attachment_receipt,
                    created_at=NOW,
                )
                await contender.controller_bindings.add(
                    partial_binding, created_at=NOW
                )
            finally:
                store._run_mutation_receipts[target_key] = (
                    target_stored_receipt
                )
            assert target_key in contender._pending_run_mutation_receipts
            with pytest.raises(RunReceiptUniquenessConflictError):
                await contender.commit()
        finally:
            if not contender._closed:
                await contender.__aexit__(None, None, None)
        recovery_family = _run_entry_family(
            "receipt-recovery",
            character_family=recovery_character,
            session_id=recovery_session,
            run_id=generators.run_id(),
            continuous_story_line_id=generators.continuous_story_line_id(),
        )
        expected_next_ordinal = 4

    assert store.snapshot() == winner_snapshot
    assert partial_binding.value not in winner_snapshot.controller_bindings
    if loser_family is not None:
        assert loser_family.active.run_id.value not in winner_snapshot.run_current
        assert all(
            item.continuous_story_line_id
            != loser_family.active.continuous_story_line_id
            for item in winner_snapshot.run_current.values()
        )
    assert len(winner_snapshot.run_current) == 1
    assert len(winner_snapshot.run_revisions) == 3
    assert len(winner_snapshot.run_creation_receipts) == 1
    assert len(winner_snapshot.run_mutation_receipts) == 2
    assert len(winner_snapshot.run_participations) == 1
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

    async with store.unit_of_work() as recovery:
        await _stage_run_entry_family(recovery, recovery_family)
        await recovery.commit()
    recovered = store.snapshot()
    assert set(recovered.run_current) == {
        winner_family.active.run_id.value,
        recovery_family.active.run_id.value,
    }
    assert len(recovered.run_revisions) == 6
    assert len(recovered.run_creation_receipts) == 2
    assert len(recovered.run_mutation_receipts) == 4
    assert len(recovered.run_participations) == 2
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
    assert generators.run_id() == (
        f"run.demo-0000000{expected_next_ordinal}"
    )
    assert generators.continuous_story_line_id() == (
        f"csl.demo-0000000{expected_next_ordinal}"
    )
    assert generators.player_character_id() == "pc.demo-00000001"
    assert generators.clock().isoformat() == "2000-01-01T00:00:00+00:00"
    assert generators.session_id() == "demo-session-00000001"
    assert generators.seed() == 1
    assert generators.event_id() == "demo-event-00000001"


@pytest.mark.asyncio
async def test_run_entry_replay_lock_reads_return_complete_current_evidence() -> None:
    store, _, entered = await _seed_public_run()
    snapshot = store.snapshot()
    run_id = RunId(value=str(entered["run_id"]))
    attachment = next(
        run_mutation_receipt_from_storage(item)
        for item in snapshot.run_mutation_receipts.values()
        if item.operation_namespace == "run.attach-session/v1"
    )
    session_id = str(entered["session_id"])

    async with store.unit_of_work() as uow:
        run = await uow.runs.get_for_update(run_id)
        evidence = await uow.runs.get_session_attachment_lock_evidence(
            run_id, receipt_key=attachment.key
        )
        session = await uow.sessions.get_owned_for_update(
            session_id, "demo-player"
        )
        initialization_event = await uow.sessions.get_initialization_event(
            session_id
        )
        latest_snapshot = await uow.sessions.get_latest_snapshot_for_update(
            session_id
        )

        assert run is not None and run.state_version.value == 3
        assert evidence is not None
        assert evidence.canonical_run == run
        assert evidence.attachment_receipt == attachment
        assert session is not None and session.session.session_id == session_id
        assert initialization_event is not None
        assert latest_snapshot is not None
        assert latest_snapshot.state_version == 0


@pytest.mark.asyncio
async def test_expanded_uow_rolls_back_every_new_and_existing_family_together() -> None:
    store = _FailExpandedCommitStore()
    generators = new_demo_generators()
    runtime = build_demo_runtime(store=store, generators=generators)
    app = create_app(services=runtime.services)
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://demo.test"
        ) as client:
            created = await client.post(
                "/v1/player-characters",
                headers={"Idempotency-Key": "Create.Rollback-1"},
                json=_CREATION_BODY,
            )
            baseline = store.snapshot()
            store.fail_expanded_commit = True
            failed = await client.post(
                "/v1/runs",
                headers={"Idempotency-Key": "Entry.Rollback-1"},
                json={
                    "player_character_id": created.json()[
                        "player_character_id"
                    ]["value"],
                    "expected_record_revision": 1,
                    "scenario_id": "death_certificate",
                },
            )

    assert failed.status_code == 409
    assert failed.json()["error"]["error_code"] == "OPTIMISTIC_LOCK_CONFLICT"
    assert store.snapshot() == baseline
    assert generators.player_character_id() == "pc.demo-00000002"
    assert generators.run_id() == "run.demo-00000002"
    assert generators.continuous_story_line_id() == "csl.demo-00000002"
    assert generators.session_id() == "demo-session-00000002"
    assert generators.event_id() == "demo-event-00000002"
    assert generators.seed() == 2
    assert generators.job_id() == "demo-job-00000001"
    assert generators.lease_token() == "demo-lease-000000000000000000001"
    assert generators.worker_id() == "demo-worker-00000001"


@pytest.mark.asyncio
async def test_expanded_snapshot_is_complete_and_detached() -> None:
    store, _, _ = await _seed_public_run()
    expected_fields = (
        "sessions",
        "snapshots",
        "creation_keys",
        "turn_requests",
        "narrative_jobs",
        "events",
        "provider_progress",
        "controller_bindings",
        "player_character_id_allocations",
        "player_character_revisions",
        "player_character_current",
        "player_character_creation_receipts",
        "player_character_mutation_receipts",
        "run_revisions",
        "run_current",
        "run_participations",
        "run_creation_receipts",
        "run_mutation_receipts",
    )
    assert tuple(DemoStoreSnapshot.__dataclass_fields__) == expected_fields

    snapshot = store.snapshot()
    authoritative = deepcopy(snapshot)
    for field in expected_fields:
        value = getattr(snapshot, field)
        if isinstance(value, dict):
            value.clear()
    assert store.snapshot() == authoritative


@pytest.mark.asyncio
@pytest.mark.parametrize("family", ("player-character", "run"))
async def test_expanded_integrity_probes_reject_broken_relationships(
    family: str,
) -> None:
    store, created, entered = await _seed_public_run()
    if family == "player-character":
        identity = created["player_character_id"]["value"]
        store._player_character_revisions.pop((identity, 1))
        async with store.unit_of_work() as uow:
            with pytest.raises(PlayerCharacterStoredRecordIntegrityError):
                await uow.player_characters.get(
                    PlayerCharacterId(value=str(identity))
                )
    else:
        identity = str(entered["run_id"])
        store._run_revisions.pop((identity, 2))
        async with store.unit_of_work() as uow:
            with pytest.raises(RunStoredRecordIntegrityError):
                await uow.runs.get(RunId(value=identity))
