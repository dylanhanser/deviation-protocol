from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    ReservedBindPlayerCharacterCommand,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecisionCode,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
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
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
)


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
SOURCE = RunAuthoritySourceRef(value="source.run-service")
RUN_ID = RunId(value="run.service")
LINE_ID = ContinuousStoryLineId(value="csl.service")


class _Issuer:
    def __init__(self, value: object) -> None:
        self.value = value
        self.calls = 0

    def issue(self):
        self.calls += 1
        return self.value


class _Uow:
    def __init__(self) -> None:
        self.sessions = SimpleNamespace(
            get_owned_for_update=AsyncMock(return_value=None)
        )
        self.runs = SimpleNamespace(
            get=AsyncMock(return_value=None),
            get_for_update=AsyncMock(return_value=None),
            add_initial=AsyncMock(),
            append_revision=AsyncMock(),
            compare_and_swap_current=AsyncMock(return_value=True),
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


def _service(uow: _Uow) -> tuple[RunService, _Issuer, _Issuer]:
    run_issuer = _Issuer(RUN_ID)
    line_issuer = _Issuer(LINE_ID)
    return (
        RunService(
            uow_factory=_Factory(uow),
            run_id_issuer=run_issuer,
            continuous_story_line_id_issuer=line_issuer,
            source_reference=SOURCE,
            clock=lambda: NOW,
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


def _attach_command() -> AttachSessionCommand:
    return AttachSessionCommand(
        run_id=RUN_ID,
        continuous_story_line_id=LINE_ID,
        session_id="session.service",
        expected_state_version=RunStateVersion(value=1),
        source_reference=SOURCE,
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
    uow.runs.get_for_update.assert_not_awaited()
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
    uow.run_mutation_receipts.get.return_value = StoredRunSuccessReceipt(
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
    uow.run_participations.get.assert_not_awaited()
    uow.commit.assert_not_awaited()


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
    uow.run_mutation_receipts.get.return_value = StoredRunSuccessReceipt(
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
    uow.run_mutation_receipts.get.assert_awaited_once_with(receipt_key)
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
    uow.run_mutation_receipts.get.assert_awaited_once_with(receipt_key)
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
