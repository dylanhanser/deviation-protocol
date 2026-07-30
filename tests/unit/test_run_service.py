from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_service import (
    PlayerCharacterBindingEligibilityEvidence,
)
from deviation_protocol.application.ports import (
    RunPlayerCharacterBindingUniquenessConflictError,
    RunSessionAttachmentLockEvidence,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    ReservedBindPlayerCharacterCommand,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecision,
    RunReplayDecisionCode,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
    bind_player_character_fingerprint,
    bind_player_character_result,
    bind_player_character_to_run,
    construct_created_run,
    create_run_fingerprint,
    creation_result,
)
from deviation_protocol.application.run_service import (
    RunService,
    RunServiceDecision,
    RunServiceDecisionCode,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    ControllerBindingRef,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunStoredRecordIntegrityError,
)


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
SOURCE = RunAuthoritySourceRef(value="source.run-service")
RUN_ID = RunId(value="run.service")
LINE_ID = ContinuousStoryLineId(value="csl.service")
PLAYER_CHARACTER_ID = PlayerCharacterId(value="pc.service")
CONTROLLER_BINDING = ControllerBindingRef(value="controller.service")
CHARACTER_REFERENCE = ApplicableCharacterReference(
    player_character_id=PLAYER_CHARACTER_ID,
    contract_version=PlayerCharacterContractVersion.V1,
    record_revision=PlayerCharacterRevision(value=1),
)
PRINCIPAL = RequestPrincipal(
    player_id="player.service",
    authentication_scheme="test",
)


class _Issuer:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def issue(self):
        self.calls += 1
        return self.value


class _Uow:
    def __init__(self) -> None:
        self.current_attachment_receipt = None
        self.sessions = SimpleNamespace(
            get_owned_for_update=AsyncMock(return_value=None)
        )
        self.player_characters = SimpleNamespace(
            get_for_update=AsyncMock(return_value=None)
        )
        self.runs = SimpleNamespace(
            get=AsyncMock(return_value=None),
            get_for_update=AsyncMock(return_value=None),
            get_session_attachment_lock_evidence=AsyncMock(),
            get_active_for_player_character=AsyncMock(return_value=None),
            add_initial=AsyncMock(),
            append_revision=AsyncMock(),
            compare_and_swap_current=AsyncMock(return_value=True),
        )

        async def attachment_lock_evidence(
            _run_id,
            *,
            receipt_key,
        ):
            current = self.runs.get_for_update.return_value
            if current is None:
                return None
            return RunSessionAttachmentLockEvidence(
                canonical_run=current,
                attachment_receipt=self.current_attachment_receipt,
            )

        self.runs.get_session_attachment_lock_evidence.side_effect = (
            attachment_lock_evidence
        )
        self.run_participations = SimpleNamespace(
            get=AsyncMock(return_value=None),
            add=AsyncMock(),
        )
        self.run_creation_receipts = SimpleNamespace(
            get=AsyncMock(return_value=None),
            add=AsyncMock(),
        )
        self.run_mutation_receipts = SimpleNamespace(
            get=AsyncMock(return_value=None),
            add=AsyncMock(),
        )
        self.commit = AsyncMock()
        self.rollback_calls = 0
        self.close_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None or self.commit.await_count == 0:
            self.rollback_calls += 1
        self.close_calls += 1


class _Factory:
    def __init__(self, *units: _Uow) -> None:
        self.units = list(units)
        self.calls = 0

    def __call__(self) -> _Uow:
        unit = self.units[self.calls]
        self.calls += 1
        return unit


def _service(
    uow: _Uow,
    *,
    resolver: object | None = None,
    evidence: object | None = None,
    clock=None,
) -> tuple[RunService, _Issuer, _Issuer]:
    run_issuer = _Issuer(RUN_ID)
    line_issuer = _Issuer(LINE_ID)
    resolver = resolver or SimpleNamespace(
        resolve=AsyncMock(return_value=CONTROLLER_BINDING)
    )
    evidence = evidence or SimpleNamespace(
        lock_owned_for_binding=AsyncMock(
            return_value=PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=CHARACTER_REFERENCE,
                lifecycle=PlayerCharacterLifecycle.ACTIVE,
            )
        )
    )
    return (
        RunService(
            uow_factory=_Factory(uow),
            run_id_issuer=run_issuer,
            continuous_story_line_id_issuer=line_issuer,
            source_reference=SOURCE,
            clock=clock or (lambda: NOW),
            controller_binding_resolver=resolver,  # type: ignore[arg-type]
            player_character_binding_evidence=evidence,  # type: ignore[arg-type]
        ),
        run_issuer,
        line_issuer,
    )


def _created():
    return construct_created_run(
        CreateRunCommand(source_reference=SOURCE),
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.create"),
        occurred_at=NOW,
    )


def _attach_command(
    *,
    expected_state_version: int = 1,
) -> AttachSessionCommand:
    return AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id="session.service",
        expected_state_version=RunStateVersion(
            value=expected_state_version
        ),
        source_reference=SOURCE,
    )


def _bind_command(
    *,
    expected_state_version: int = 1,
    line_id: ContinuousStoryLineId = LINE_ID,
) -> BindPlayerCharacterCommand:
    return BindPlayerCharacterCommand(
        run_id=RUN_ID,
        continuous_story_line_id=line_id,
        target_player_character_id=PLAYER_CHARACTER_ID,
        expected_state_version=RunStateVersion(
            value=expected_state_version
        ),
        source_reference=SOURCE,
    )


def _bound(
    *,
    operation_id: RunOperationId | None = None,
):
    return bind_player_character_to_run(
        _created(),
        _bind_command(),
        applicable_character_reference=CHARACTER_REFERENCE,
        operation_id=operation_id
        or RunOperationId(value="operation.bind.internal"),
        occurred_at=NOW,
    )


def _bound_after(
    current,
    *,
    operation_id: RunOperationId,
):
    return bind_player_character_to_run(
        current,
        BindPlayerCharacterCommand(
            run_id=current.run_id,
            continuous_story_line_id=(
                current.continuous_story_line_id
            ),
            target_player_character_id=PLAYER_CHARACTER_ID,
            expected_state_version=current.state_version,
            source_reference=SOURCE,
        ),
        applicable_character_reference=CHARACTER_REFERENCE,
        operation_id=operation_id,
        occurred_at=NOW + timedelta(seconds=1),
    )


def _attachment_lock_evidence(
    run,
    *,
    receipt: StoredRunSuccessReceipt | None = None,
) -> RunSessionAttachmentLockEvidence:
    return RunSessionAttachmentLockEvidence(
        canonical_run=run,
        attachment_receipt=receipt,
    )


def _owned_session() -> object:
    return SimpleNamespace(
        session=GameSession(
            session_id="session.service",
            player_id="player.service",
            scenario_id="scenario.service",
            scenario_version="1",
            phase="AWAITING_ACTION",
            turn_number=0,
            state_version=0,
            random_seed=1,
        )
    )


@pytest.mark.asyncio
async def test_create_run_writes_revision_current_receipt_and_commits_once() -> None:
    uow = _Uow()
    service, run_issuer, line_issuer = _service(uow)

    result = await service.create_run(
        operation_id=RunOperationId(value="operation.create"),
        command=CreateRunCommand(source_reference=SOURCE),
    )

    assert result == creation_result(_created())
    assert run_issuer.calls == line_issuer.calls == 1
    uow.runs.add_initial.assert_awaited_once()
    uow.run_creation_receipts.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    assert uow.rollback_calls == 0
    assert uow.close_calls == 1


@pytest.mark.asyncio
async def test_creation_replay_returns_original_without_issuance_or_commit() -> None:
    uow = _Uow()
    service, run_issuer, line_issuer = _service(uow)
    command = CreateRunCommand(source_reference=SOURCE)
    operation_id = RunOperationId(value="operation.create")
    _, fingerprint = create_run_fingerprint(command)
    uow.run_creation_receipts.get.return_value = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.CREATE,
        result=creation_result(_created()),
    )

    result = await service.create_run(
        operation_id=operation_id,
        command=command,
    )

    assert result == creation_result(_created())
    assert run_issuer.calls == line_issuer.calls == 0
    uow.runs.add_initial.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.parametrize(
    "clock_value",
    (
        datetime(2026, 7, 29, 12, 0),
        datetime(
            2026,
            7,
            29,
            12,
            0,
            tzinfo=timezone(timedelta(hours=1)),
        ),
    ),
)
@pytest.mark.asyncio
async def test_creation_rejects_non_utc_clock_without_persistence(
    clock_value: datetime,
) -> None:
    uow = _Uow()
    service, _, _ = _service(uow)
    service.clock = lambda: clock_value

    with pytest.raises(ValueError, match="exact UTC"):
        await service.create_run(
            operation_id=RunOperationId(value="operation.invalid-clock"),
            command=CreateRunCommand(source_reference=SOURCE),
        )

    uow.runs.add_initial.assert_not_awaited()
    uow.run_creation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_attachment_checks_session_ownership_before_run_or_receipt() -> None:
    uow = _Uow()
    service, _, _ = _service(uow)

    result = await service.attach_session(
        RequestPrincipal(
            player_id="other.player",
            authentication_scheme="test",
        ),
        operation_id=RunOperationId(value="operation.attach"),
        command=_attach_command(),
    )

    assert result == RunServiceDecision(
        code=RunServiceDecisionCode.AUTHORIZATION_FAILED
    )
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.runs.get_session_attachment_lock_evidence.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_attachment_commits_revision_participation_cas_and_receipt() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    uow.runs.get_for_update.return_value = _created()
    service, _, _ = _service(uow)
    command = _attach_command()

    result = await service.attach_session(
        RequestPrincipal(
            player_id="player.service",
            authentication_scheme="test",
        ),
        operation_id=RunOperationId(value="operation.attach"),
        command=command,
    )

    expected = attach_session_result(
        attach_session_to_run(
            _created(),
            command,
            operation_id=RunOperationId(value="operation.attach"),
            occurred_at=NOW,
        )
    )
    assert result == expected
    uow.runs.append_revision.assert_awaited_once()
    uow.run_participations.add.assert_awaited_once()
    uow.runs.compare_and_swap_current.assert_awaited_once()
    uow.run_mutation_receipts.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_bound_attachment_locks_complete_run_family_directly() -> None:
    events: list[str] = []
    uow = _Uow()
    bound = _bound()
    command = _attach_command(expected_state_version=2)
    operation_id = RunOperationId(value="operation.attach-bound")

    async def lock_session(session_id, player_id):
        events.append("session_current_lock")
        return _owned_session()

    async def lock_run_carrier(run_id, *, receipt_key):
        events.append("run_current_and_complete_family")
        return _attachment_lock_evidence(bound)

    async def append_revision(*args, **kwargs):
        events.append("bound_run_revision_insert")

    uow.sessions.get_owned_for_update.side_effect = lock_session
    uow.runs.get_session_attachment_lock_evidence.side_effect = (
        lock_run_carrier
    )
    uow.runs.append_revision.side_effect = append_revision
    service, _, _ = _service(uow)

    result = await service.attach_session(
        PRINCIPAL,
        operation_id=operation_id,
        command=command,
    )

    successor = attach_session_to_run(
        bound,
        command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    assert result == attach_session_result(successor)
    assert events == [
        "session_current_lock",
        "run_current_and_complete_family",
        "bound_run_revision_insert",
    ]
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.runs.get_session_attachment_lock_evidence.assert_awaited_once_with(
        RUN_ID,
        receipt_key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=operation_id,
        ),
    )
    uow.runs.append_revision.assert_awaited_once_with(
        successor,
        created_at=NOW,
    )
    uow.runs.compare_and_swap_current.assert_awaited_once_with(
        successor,
        expected_state_version=2,
        updated_at=NOW,
    )
    uow.run_participations.add.assert_awaited_once()
    uow.run_mutation_receipts.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    assert uow.rollback_calls == 0


@pytest.mark.asyncio
async def test_attachment_uses_late_bound_locked_family_without_prelock_read() -> None:
    events: list[str] = []
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    bound = _bound()

    async def lock_current_carrier(_run_id, *, receipt_key):
        events.append("run_current_carrier_lock")
        return _attachment_lock_evidence(bound)

    uow.runs.get_session_attachment_lock_evidence.side_effect = (
        lock_current_carrier
    )
    service, _, _ = _service(uow)
    operation_id = RunOperationId(value="operation.attach-raced-bind")
    command = _attach_command(expected_state_version=2)

    result = await service.attach_session(
        PRINCIPAL,
        operation_id=operation_id,
        command=command,
    )

    successor = attach_session_to_run(
        bound,
        command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    assert result == attach_session_result(successor)
    assert events == ["run_current_carrier_lock"]
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.runs.get.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.runs.append_revision.assert_awaited_once()
    uow.run_participations.add.assert_awaited_once()
    uow.runs.compare_and_swap_current.assert_awaited_once()
    uow.run_mutation_receipts.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    assert uow.rollback_calls == 0


@pytest.mark.asyncio
async def test_attachment_noncanonical_locked_family_rolls_back_without_write() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    uow.runs.get_session_attachment_lock_evidence.side_effect = (
        RunStoredRecordIntegrityError(
            "Run creation provenance changed across history"
        )
    )
    service, _, _ = _service(uow)

    with pytest.raises(
        RunStoredRecordIntegrityError,
        match="creation provenance",
    ):
        await service.attach_session(
            PRINCIPAL,
            operation_id=RunOperationId(
                value="operation.attach-malformed-family"
            ),
            command=_attach_command(),
        )

    uow.player_characters.get_for_update.assert_not_awaited()
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("conflicting_reuse", (False, True))
async def test_attachment_locked_family_preserves_receipt_decision(
    conflicting_reuse: bool,
) -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    operation_id = RunOperationId(value="operation.attach-before-bind")
    accepted_command = _attach_command()
    attached = attach_session_to_run(
        _created(),
        accepted_command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    later_bound = _bound_after(
        attached,
        operation_id=RunOperationId(value="operation.bind-after-attach"),
    )
    _, fingerprint = attach_session_fingerprint(
        accepted_command,
        operation_id=operation_id,
    )
    original_result = attach_session_result(attached)
    current_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=original_result,
    )
    uow.runs.get_session_attachment_lock_evidence.side_effect = None
    uow.runs.get_session_attachment_lock_evidence.return_value = (
        _attachment_lock_evidence(
            later_bound,
            receipt=current_receipt,
        )
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        PRINCIPAL,
        operation_id=operation_id,
        command=(
            _attach_command(expected_state_version=2)
            if conflicting_reuse
            else accepted_command
        ),
    )

    if conflicting_reuse:
        assert result == RunReplayDecision(
            code=RunReplayDecisionCode.CONFLICT
        )
    else:
        assert result == original_result
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_attachment_exact_replay_precedes_stale_version_rejection() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    attached = attach_session_to_run(
        _created(),
        _attach_command(),
        operation_id=RunOperationId(value="operation.attach"),
        occurred_at=NOW,
    )
    uow.runs.get_for_update.return_value = attached
    command = _attach_command()
    operation_id = RunOperationId(value="operation.attach")
    _, fingerprint = attach_session_fingerprint(
        command,
        operation_id=operation_id,
    )
    uow.current_attachment_receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(attached),
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        RequestPrincipal(
            player_id="player.service",
            authentication_scheme="test",
        ),
        operation_id=operation_id,
        command=command,
    )

    assert result == attach_session_result(attached)
    uow.runs.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.run_participations.get.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_attachment_current_conflicting_receipt_precedes_stale_version() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    operation_id = RunOperationId(value="operation.attach-current-conflict")
    winner_command = _attach_command().model_copy(
        update={"session_id": "session.concurrent-winner"}
    )
    winner = attach_session_to_run(
        _created(),
        winner_command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    uow.runs.get_for_update.return_value = winner
    _, winner_fingerprint = attach_session_fingerprint(
        winner_command,
        operation_id=operation_id,
    )
    receipt_key = RunReceiptKey(
        run_id=RUN_ID,
        operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
        operation_id=operation_id,
    )
    uow.current_attachment_receipt = StoredRunSuccessReceipt(
        key=receipt_key,
        fingerprint=winner_fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(winner),
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        PRINCIPAL,
        operation_id=operation_id,
        command=_attach_command(),
    )

    assert result == RunReplayDecision(
        code=RunReplayDecisionCode.CONFLICT
    )
    uow.runs.get.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.runs.get_session_attachment_lock_evidence.assert_awaited_once_with(
        RUN_ID,
        receipt_key=receipt_key,
    )
    uow.runs.get_for_update.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_bound_attachment_uses_current_receipt_before_stale_version() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    bound = _bound()
    operation_id = RunOperationId(
        value="operation.attach-bound-current-conflict"
    )
    winner_command = _attach_command(
        expected_state_version=2
    ).model_copy(update={"session_id": "session.bound-winner"})
    winner = attach_session_to_run(
        bound,
        winner_command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    uow.runs.get_for_update.return_value = winner
    _, winner_fingerprint = attach_session_fingerprint(
        winner_command,
        operation_id=operation_id,
    )
    receipt_key = RunReceiptKey(
        run_id=RUN_ID,
        operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
        operation_id=operation_id,
    )
    uow.current_attachment_receipt = StoredRunSuccessReceipt(
        key=receipt_key,
        fingerprint=winner_fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(winner),
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        PRINCIPAL,
        operation_id=operation_id,
        command=_attach_command(expected_state_version=2),
    )

    assert result == RunReplayDecision(
        code=RunReplayDecisionCode.CONFLICT
    )
    uow.runs.get.assert_not_awaited()
    uow.player_characters.get_for_update.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.get_for_update.assert_not_awaited()
    uow.runs.get_session_attachment_lock_evidence.assert_awaited_once_with(
        RUN_ID,
        receipt_key=receipt_key,
    )
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_same_key_changed_line_evaluates_receipt_and_conflicts_without_write() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    created = _created()
    uow.runs.get_for_update.return_value = created
    original_command = _attach_command()
    operation_id = RunOperationId(value="operation.attach")
    attached = attach_session_to_run(
        created,
        original_command,
        operation_id=operation_id,
        occurred_at=NOW,
    )
    _, original_fingerprint = attach_session_fingerprint(
        original_command,
        operation_id=operation_id,
    )
    receipt_key = RunReceiptKey(
        run_id=RUN_ID,
        operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
        operation_id=operation_id,
    )
    uow.current_attachment_receipt = StoredRunSuccessReceipt(
        key=receipt_key,
        fingerprint=original_fingerprint,
        command_kind=RunMutationKind.ATTACH_SESSION,
        result=attach_session_result(attached),
    )
    changed_line_command = original_command.model_copy(
        update={
            "continuous_story_line_id": ContinuousStoryLineId(
                value="csl.changed-line"
            )
        }
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        RequestPrincipal(
            player_id="player.service",
            authentication_scheme="test",
        ),
        operation_id=operation_id,
        command=changed_line_command,
    )

    assert result.code is RunReplayDecisionCode.CONFLICT
    uow.runs.get.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert created.state_version == RunStateVersion(value=1)
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_new_changed_line_checks_absent_receipt_before_target_mismatch() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    created = _created()
    uow.runs.get_for_update.return_value = created
    operation_id = RunOperationId(value="operation.new-target-mismatch")
    receipt_key = RunReceiptKey(
        run_id=RUN_ID,
        operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
        operation_id=operation_id,
    )
    command = _attach_command().model_copy(
        update={
            "continuous_story_line_id": ContinuousStoryLineId(
                value="csl.new-target-mismatch"
            )
        }
    )
    service, _, _ = _service(uow)

    result = await service.attach_session(
        RequestPrincipal(
            player_id="player.service",
            authentication_scheme="test",
        ),
        operation_id=operation_id,
        command=command,
    )

    assert result == RunServiceDecision(
        code=RunServiceDecisionCode.TARGET_MISMATCH
    )
    uow.runs.get.assert_not_awaited()
    uow.run_mutation_receipts.get.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_participations.add.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert created.state_version == RunStateVersion(value=1)
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_cas_loss_rolls_back_and_returns_typed_conflict() -> None:
    uow = _Uow()
    uow.sessions.get_owned_for_update.return_value = _owned_session()
    uow.runs.get_for_update.return_value = _created()
    uow.runs.compare_and_swap_current.return_value = False
    service, _, _ = _service(uow)

    result = await service.attach_session(
        RequestPrincipal(
            player_id="player.service",
            authentication_scheme="test",
        ),
        operation_id=RunOperationId(value="operation.attach"),
        command=_attach_command(),
    )

    assert result == RunServiceDecision(
        code=RunServiceDecisionCode.CONCURRENT_STATE_CONFLICT
    )
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_cancellation_uses_exceptional_cleanup_and_propagates() -> None:
    uow = _Uow()
    uow.run_creation_receipts.get.side_effect = asyncio.CancelledError
    service, _, _ = _service(uow)

    with pytest.raises(asyncio.CancelledError):
        await service.create_run(
            operation_id=RunOperationId(value="operation.cancel"),
            command=CreateRunCommand(source_reference=SOURCE),
        )

    assert uow.rollback_calls == 1
    assert uow.close_calls == 1
    uow.commit.assert_not_awaited()


def test_binding_namespace_remains_reserved_without_unit_of_work() -> None:
    uow = _Uow()
    service, _, _ = _service(uow)

    result = service.bind_player_character(
        operation_id=RunOperationId(value="operation.bind"),
        command=ReservedBindPlayerCharacterCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            expected_state_version=RunStateVersion(value=1),
            source_reference=SOURCE,
        ),
    )

    assert result.code is RunReplayDecisionCode.RESERVED_OPERATION_REJECTED


@pytest.mark.asyncio
async def test_internal_binding_locks_character_then_run_and_commits_once() -> None:
    events: list[str] = []
    uow = _Uow()

    async def lock_character(*args, **kwargs):
        events.append("player_character_current")
        return PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=CHARACTER_REFERENCE,
            lifecycle=PlayerCharacterLifecycle.ACTIVE,
        )

    async def lock_run(run_id):
        events.append("run_current")
        return _created()

    evidence = SimpleNamespace(
        lock_owned_for_binding=AsyncMock(side_effect=lock_character)
    )
    uow.runs.get_for_update.side_effect = lock_run
    service, _, _ = _service(uow, evidence=evidence)
    operation_id = RunOperationId(value="operation.bind.internal")

    result = await service.bind_player_character_internal(
        PRINCIPAL,
        operation_id=operation_id,
        command=_bind_command(),
    )

    successor = _bound(operation_id=operation_id)
    assert result == bind_player_character_result(successor)
    assert events == ["player_character_current", "run_current"]
    evidence.lock_owned_for_binding.assert_awaited_once_with(
        uow,
        trusted_controller_binding=CONTROLLER_BINDING,
        target_player_character_id=PLAYER_CHARACTER_ID,
    )
    uow.runs.get_active_for_player_character.assert_awaited_once_with(
        PLAYER_CHARACTER_ID
    )
    uow.runs.append_revision.assert_awaited_once_with(
        successor,
        created_at=NOW,
    )
    uow.runs.compare_and_swap_current.assert_awaited_once_with(
        successor,
        expected_state_version=1,
        updated_at=NOW,
    )
    uow.run_mutation_receipts.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
    assert uow.rollback_calls == 0


@pytest.mark.asyncio
async def test_internal_binding_exact_replay_uses_original_result_without_write_or_clock() -> None:
    uow = _Uow()
    operation_id = RunOperationId(value="operation.bind.replay")
    accepted_command = _bind_command()
    accepted_run = _bound(operation_id=operation_id)
    later_run = attach_session_to_run(
        accepted_run,
        AttachSessionCommand(
            run_id=RUN_ID,
            continuous_story_line_id=LINE_ID,
            session_id="session.later",
            expected_state_version=RunStateVersion(value=2),
            source_reference=SOURCE,
        ),
        operation_id=RunOperationId(value="operation.attach.later"),
        occurred_at=NOW + timedelta(seconds=1),
    )
    _, fingerprint = bind_player_character_fingerprint(
        accepted_command,
        operation_id=operation_id,
    )
    original_result = bind_player_character_result(accepted_run)
    uow.runs.get_for_update.return_value = later_run
    uow.run_mutation_receipts.get.return_value = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=original_result,
    )
    evidence = SimpleNamespace(
        lock_owned_for_binding=AsyncMock(
            return_value=PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=(
                    ApplicableCharacterReference(
                        player_character_id=PLAYER_CHARACTER_ID,
                        contract_version=(
                            PlayerCharacterContractVersion.V1
                        ),
                        record_revision=PlayerCharacterRevision(value=2),
                    )
                ),
                lifecycle=PlayerCharacterLifecycle.RETIRED,
            )
        )
    )

    def forbidden_clock() -> datetime:
        raise AssertionError("exact replay must not use the clock")

    service, _, _ = _service(
        uow,
        evidence=evidence,
        clock=forbidden_clock,
    )

    result = await service.bind_player_character_internal(
        PRINCIPAL,
        operation_id=operation_id,
        command=accepted_command,
    )

    assert result == original_result
    uow.runs.get_active_for_player_character.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
async def test_internal_binding_changed_request_identity_reuse_conflicts_without_write() -> None:
    uow = _Uow()
    uow.runs.get_for_update.return_value = _created()
    operation_id = RunOperationId(value="operation.bind.conflict")
    accepted_command = _bind_command()
    accepted_run = _bound(operation_id=operation_id)
    _, fingerprint = bind_player_character_fingerprint(
        accepted_command,
        operation_id=operation_id,
    )
    uow.run_mutation_receipts.get.return_value = StoredRunSuccessReceipt(
        key=RunReceiptKey(
            run_id=RUN_ID,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        result=bind_player_character_result(accepted_run),
    )
    service, _, _ = _service(uow)

    result = await service.bind_player_character_internal(
        PRINCIPAL,
        operation_id=operation_id,
        command=_bind_command(expected_state_version=2),
    )

    assert result.code is RunReplayDecisionCode.CONFLICT
    uow.runs.get_active_for_player_character.assert_not_awaited()
    uow.runs.append_revision.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("character_evidence", "current", "occupied", "expected_code"),
    (
        (
            None,
            None,
            None,
            RunServiceDecisionCode.AUTHORIZATION_FAILED,
        ),
        (
            PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=CHARACTER_REFERENCE,
                lifecycle=PlayerCharacterLifecycle.RETIRED,
            ),
            _created(),
            None,
            RunServiceDecisionCode.PLAYER_CHARACTER_INELIGIBLE,
        ),
        (
            PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=CHARACTER_REFERENCE,
                lifecycle=PlayerCharacterLifecycle.ACTIVE,
            ),
            _bound(),
            None,
            RunServiceDecisionCode.PLAYER_CHARACTER_BINDING_CONFLICT,
        ),
        (
            PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=CHARACTER_REFERENCE,
                lifecycle=PlayerCharacterLifecycle.ACTIVE,
            ),
            _created(),
            _bound(),
            RunServiceDecisionCode.PLAYER_CHARACTER_BINDING_CONFLICT,
        ),
    ),
)
async def test_internal_binding_rejections_leave_no_partial_mutation(
    character_evidence,
    current,
    occupied,
    expected_code,
) -> None:
    uow = _Uow()
    uow.runs.get_for_update.return_value = current
    uow.runs.get_active_for_player_character.return_value = occupied
    evidence = SimpleNamespace(
        lock_owned_for_binding=AsyncMock(return_value=character_evidence)
    )
    service, _, _ = _service(uow, evidence=evidence)

    result = await service.bind_player_character_internal(
        PRINCIPAL,
        operation_id=RunOperationId(value="operation.bind.rejected"),
        command=_bind_command(
            expected_state_version=(
                current.state_version.value if current is not None else 1
            )
        ),
    )

    assert result == RunServiceDecision(code=expected_code)
    uow.runs.append_revision.assert_not_awaited()
    uow.runs.compare_and_swap_current.assert_not_awaited()
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cas_effect", "expected_code"),
    (
        (
            False,
            RunServiceDecisionCode.CONCURRENT_STATE_CONFLICT,
        ),
        (
            RunPlayerCharacterBindingUniquenessConflictError(
                "duplicate binding"
            ),
            RunServiceDecisionCode.PLAYER_CHARACTER_BINDING_CONFLICT,
        ),
    ),
)
async def test_internal_binding_cas_failures_roll_back(
    cas_effect,
    expected_code,
) -> None:
    uow = _Uow()
    uow.runs.get_for_update.return_value = _created()
    if isinstance(cas_effect, BaseException):
        uow.runs.compare_and_swap_current.side_effect = cas_effect
    else:
        uow.runs.compare_and_swap_current.return_value = cas_effect
    service, _, _ = _service(uow)

    result = await service.bind_player_character_internal(
        PRINCIPAL,
        operation_id=RunOperationId(value="operation.bind.cas"),
        command=_bind_command(),
    )

    assert result == RunServiceDecision(code=expected_code)
    uow.run_mutation_receipts.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
    assert uow.rollback_calls == 1
