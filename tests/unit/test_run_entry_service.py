from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from deviation_protocol.api import dependencies as api_dependencies
from deviation_protocol.api import main as api_main
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_service import (
    PlayerCharacterBindingEligibilityEvidence,
)
from deviation_protocol.application.ports import (
    PersistedSession,
    PersistedSnapshot,
    RunReceiptUniquenessConflictError,
    StoredRunCreationEvidence,
)
from deviation_protocol.application.run_entry_service import (
    RunEntryCommand,
    RunEntryDecision,
    RunEntryDecisionCode,
    RunEntryIntegrityError,
    RunEntryResult,
    RunEntryService,
)
from deviation_protocol.application.run_operations import (
    CreateRunCommand,
    RunEntryPublicOperationKey,
    create_run_fingerprint,
    run_entry_evidence_bytes,
)
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import (
    _issue_persisted_event_receipt,
)
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
)
from deviation_protocol.infrastructure.content_loader import (
    JsonContentCatalogLoader,
)
from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
)


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
NOW = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
PRINCIPAL = RequestPrincipal(
    player_id="player.entry", authentication_scheme="test"
)
CONTROLLER = ControllerBindingRef(value="controller.entry")
REFERENCE = ApplicableCharacterReference(
    player_character_id=PlayerCharacterId(value="pc.entry"),
    contract_version=PlayerCharacterContractVersion.V1,
    record_revision=PlayerCharacterRevision(value=1),
)


class _Issuer:
    def __init__(self, value: object, events: list[str], name: str) -> None:
        self.value = value
        self.events = events
        self.name = name
        self.calls = 0

    def issue(self):
        self.calls += 1
        self.events.append(self.name)
        return self.value


class _Uow:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.successfully_committed = False
        self.rollback_calls = 0
        self.close_calls = 0

        def logged(name: str, result=None):
            async def call(*args, **kwargs):
                self.events.append(name)
                return result

            return AsyncMock(side_effect=call)

        async def persist(events, *, state_version):
            self.events.append("session.event")
            return tuple(
                _issue_persisted_event_receipt(
                    event, state_version=state_version
                )
                for event in events
            )

        self.runs = SimpleNamespace(
            get_active_for_player_character_for_update=logged(
                "run.active-lock", None
            ),
            get_for_update=logged("run.lock", None),
            add_initial=logged("run.revision-1"),
            append_revision=logged("run.revision"),
            compare_and_swap_current=logged("run.cas", True),
        )
        self.run_creation_receipts = SimpleNamespace(
            get_with_evidence=logged("creation-receipt.read", None),
            add_with_evidence=logged("creation-receipt.write"),
        )
        self.run_mutation_receipts = SimpleNamespace(
            add=logged("mutation-receipt.write")
        )
        self.run_participations = SimpleNamespace(
            add=logged("participation.write")
        )
        self.sessions = SimpleNamespace(
            get_by_creation_request=logged("session.creation-read", None),
            add_initial_session=logged("session.row"),
            next_event_sequence_no=logged("session.sequence", 1),
            persist_events=AsyncMock(side_effect=persist),
            add_initial_snapshot=logged("session.snapshot"),
            get_owned_for_update=logged("session.lock", None),
            get_initialization_event=logged("session.initial-event", None),
            get_latest_snapshot_for_update=logged("session.snapshot-lock", None),
        )
        self.commit = AsyncMock(side_effect=self._commit)

    async def _commit(self) -> None:
        self.events.append("commit")
        self.successfully_committed = True

    async def __aenter__(self):
        self.events.append("uow.enter")
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if not self.successfully_committed:
            self.rollback_calls += 1
            self.events.append("uow.rollback")
        self.close_calls += 1
        self.events.append("uow.close")


class _Factory:
    def __init__(self, *units: _Uow) -> None:
        self.units = units
        self.calls = 0

    def __call__(self) -> _Uow:
        unit = self.units[self.calls]
        self.calls += 1
        return unit


def _command(**changes: object) -> RunEntryCommand:
    values: dict[str, object] = {
        "public_operation_key": RunEntryPublicOperationKey(
            value="entry.example"
        ),
        "player_character_id": REFERENCE.player_character_id,
        "expected_record_revision": REFERENCE.record_revision,
        "scenario_id": "death_certificate",
    }
    values.update(changes)
    return RunEntryCommand(**values)


def _service(
    factory: _Factory,
    events: list[str],
) -> tuple[RunEntryService, _Issuer, _Issuer, object]:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_service = SessionService(
        uow_factory=factory,  # never used by P8's helper seams
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: "session.entry",
        seed_generator=lambda: 42,
        event_id_generator=lambda: "event.entry-started",
    )
    def resolve(principal):
        events.append("controller.resolve")
        return CONTROLLER

    async def lock_owned(*args, **kwargs):
        events.append("pc.lock")
        return PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=REFERENCE,
            lifecycle=PlayerCharacterLifecycle.ACTIVE,
        )

    resolver = SimpleNamespace(resolve=AsyncMock(side_effect=resolve))
    evidence = SimpleNamespace(
        lock_owned_for_binding=AsyncMock(side_effect=lock_owned)
    )
    run_issuer = _Issuer(RunId(value="run.entry"), events, "run.issue")
    line_issuer = _Issuer(
        ContinuousStoryLineId(value="csl.entry"), events, "line.issue"
    )
    service = RunEntryService(
        uow_factory=factory,
        run_id_issuer=run_issuer,
        continuous_story_line_id_issuer=line_issuer,
        source_reference=RunAuthoritySourceRef(value="source.production-run"),
        clock=lambda: (events.append("clock") or NOW),
        controller_binding_resolver=resolver,
        player_character_binding_evidence=evidence,
        session_service=session_service,
    )
    return service, run_issuer, line_issuer, evidence


def _stored_creation(uow: _Uow) -> StoredRunCreationEvidence:
    receipt, evidence = (
        uow.run_creation_receipts.add_with_evidence.await_args.args
    )
    return StoredRunCreationEvidence(
        receipt=receipt,
        evidence=evidence,
        evidence_canonical=run_entry_evidence_bytes(evidence),
    )


def test_run_entry_command_is_strict_and_binds_the_frozen_public_inputs() -> None:
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(value="entry.example"),
        player_character_id=PlayerCharacterId(value="pc.example"),
        expected_record_revision=PlayerCharacterRevision(value=1),
        scenario_id="death_certificate",
    )
    assert command.public_operation_key.value == "entry.example"
    with pytest.raises(ValidationError):
        RunEntryCommand.model_validate({**command.model_dump(mode="python"), "unknown": "x"})


@pytest.mark.asyncio
async def test_fresh_entry_stages_the_complete_family_once_in_exact_order() -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, run_issuer, line_issuer, _ = _service(factory, events)

    result = await service.enter(PRINCIPAL, command=_command())

    assert isinstance(result, RunEntryResult)
    assert result.model_dump(mode="json") == {
        "run_id": {"value": "run.entry"},
        "session_id": "session.entry",
        "scenario_id": "death_certificate",
        "player_character": {
            "player_character_id": {"value": "pc.entry"},
            "contract_version": "structured-player-character/v1",
            "record_revision": {"value": 1},
            "lifecycle": "active",
        },
    }
    assert factory.calls == run_issuer.calls == line_issuer.calls == 1
    assert uow.commit.await_count == 1
    assert uow.rollback_calls == 0
    assert uow.close_calls == 1
    assert events == [
        "controller.resolve",
        "uow.enter",
        "pc.lock",
        "creation-receipt.read",
        "run.active-lock",
        "session.creation-read",
        "clock",
        "run.issue",
        "line.issue",
        "run.revision-1",
        "creation-receipt.write",
        "run.revision",
        "run.cas",
        "mutation-receipt.write",
        "session.row",
        "session.sequence",
        "session.event",
        "session.snapshot",
        "run.revision",
        "participation.write",
        "run.cas",
        "mutation-receipt.write",
        "commit",
        "uow.close",
    ]


@pytest.mark.asyncio
async def test_exact_replay_uses_one_uow_zero_mutation_and_zero_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    fresh = _Uow(events)
    replay = _Uow(events)
    factory = _Factory(fresh, replay)
    service, run_issuer, line_issuer, evidence_reader = _service(
        factory, events
    )
    command = _command()

    first = await service.enter(PRINCIPAL, command=command)
    assert isinstance(first, RunEntryResult)
    creation_args = fresh.run_creation_receipts.add_with_evidence.await_args.args
    receipt, evidence = creation_args
    stored = StoredRunCreationEvidence(
        receipt=receipt,
        evidence=evidence,
        evidence_canonical=run_entry_evidence_bytes(evidence),
    )
    active = fresh.runs.append_revision.await_args_list[1].args[0]
    session_call = fresh.sessions.add_initial_session.await_args
    session = session_call.args[0]
    persisted = PersistedSession(
        session=session,
        character_definition_id=session_call.kwargs["character_definition_id"],
        creation_client_request_id=session_call.kwargs[
            "creation_client_request_id"
        ],
        created_at=NOW,
        updated_at=NOW,
    )
    event = fresh.sessions.persist_events.await_args.args[0][0]
    snapshot = PersistedSnapshot(
        state_version=0,
        state=deepcopy(fresh.sessions.add_initial_snapshot.await_args.kwargs["state"]),
    )
    def load(name: str, value):
        async def call(*args, **kwargs):
            events.append(name)
            return value

        return call

    for method, name, value in (
        (
            replay.run_creation_receipts.get_with_evidence,
            "creation-receipt.read",
            stored,
        ),
        (replay.runs.get_for_update, "run.lock", active),
        (replay.sessions.get_owned_for_update, "session.lock", persisted),
        (
            replay.sessions.get_initialization_event,
            "session.initial-event",
            event,
        ),
        (
            replay.sessions.get_latest_snapshot_for_update,
            "session.snapshot-lock",
            snapshot,
        ),
    ):
        method.side_effect = load(name, value)

    async def lock_retired_successor(*args, **kwargs):
        events.append("pc.lock")
        return PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=REFERENCE.model_copy(
                update={
                    "record_revision": PlayerCharacterRevision(value=2)
                }
            ),
            lifecycle=PlayerCharacterLifecycle.RETIRED,
        )

    evidence_reader.lock_owned_for_binding.side_effect = lock_retired_successor
    definition_policy = Mock(side_effect=AssertionError("replay used fresh policy"))
    monkeypatch.setattr(
        SessionService,
        "resolve_run_entry_definition",
        definition_policy,
    )

    before_issuers = (run_issuer.calls, line_issuer.calls)
    replay_start = len(events)
    replayed = await service.enter(PRINCIPAL, command=command)

    assert replayed == first
    assert factory.calls == 2
    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert replay.commit.await_count == 0
    assert replay.rollback_calls == replay.close_calls == 1
    assert events[replay_start:] == [
        "controller.resolve",
        "uow.enter",
        "pc.lock",
        "creation-receipt.read",
        "run.lock",
        "session.lock",
        "session.initial-event",
        "session.snapshot-lock",
        "uow.rollback",
        "uow.close",
    ]
    replay.runs.get_active_for_player_character_for_update.assert_not_awaited()
    replay.sessions.get_by_creation_request.assert_not_awaited()
    replay.runs.add_initial.assert_not_awaited()
    replay.runs.append_revision.assert_not_awaited()
    replay.runs.compare_and_swap_current.assert_not_awaited()
    replay.run_creation_receipts.add_with_evidence.assert_not_awaited()
    replay.run_mutation_receipts.add.assert_not_awaited()
    replay.run_participations.add.assert_not_awaited()
    replay.sessions.add_initial_session.assert_not_awaited()
    replay.sessions.persist_events.assert_not_awaited()
    replay.sessions.add_initial_snapshot.assert_not_awaited()
    definition_policy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("resolved", (None, object()))
async def test_authorization_failure_before_uow_touches_no_transaction_or_issuer(
    resolved: object | None,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    resolver = service.controller_binding_resolver.resolve
    resolver.side_effect = None
    resolver.return_value = resolved

    result = await service.enter(PRINCIPAL, command=_command())

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.AUTHORIZATION_FAILED
    )
    assert factory.calls == run_issuer.calls == line_issuer.calls == 0
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 0


@pytest.mark.asyncio
async def test_other_controller_receipt_fails_authorization_before_disclosure() -> None:
    events: list[str] = []
    fresh = _Uow(events)
    replay = _Uow(events)
    factory = _Factory(fresh, replay)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    command = _command()
    created = await service.enter(PRINCIPAL, command=command)
    assert isinstance(created, RunEntryResult)
    replay.run_creation_receipts.get_with_evidence.side_effect = None
    replay.run_creation_receipts.get_with_evidence.return_value = _stored_creation(
        fresh
    )
    resolver = service.controller_binding_resolver.resolve
    resolver.side_effect = None
    resolver.return_value = ControllerBindingRef(value="controller.other")
    before_issuers = (run_issuer.calls, line_issuer.calls)

    result = await service.enter(PRINCIPAL, command=command)

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.AUTHORIZATION_FAILED
    )
    assert set(result.model_dump(mode="json")) == {"code"}
    assert factory.calls == 2
    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert replay.commit.await_count == 0
    assert replay.rollback_calls == replay.close_calls == 1
    replay.runs.get_for_update.assert_not_awaited()
    replay.sessions.get_owned_for_update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field",
    ("public-operation-key", "player-character", "revision", "scenario"),
)
async def test_each_typed_public_replay_mismatch_is_idempotency_conflict(
    field: str,
) -> None:
    events: list[str] = []
    fresh = _Uow(events)
    replay = _Uow(events)
    factory = _Factory(fresh, replay)
    service, run_issuer, line_issuer, evidence_reader = _service(
        factory, events
    )
    original = _command()
    created = await service.enter(PRINCIPAL, command=original)
    assert isinstance(created, RunEntryResult)
    replay.run_creation_receipts.get_with_evidence.side_effect = None
    replay.run_creation_receipts.get_with_evidence.return_value = _stored_creation(
        fresh
    )
    changes: dict[str, object]
    if field == "public-operation-key":
        changes = {
            "public_operation_key": RunEntryPublicOperationKey(
                value="entry.changed"
            )
        }
    elif field == "player-character":
        changed_id = PlayerCharacterId(value="pc.changed")
        changes = {"player_character_id": changed_id}
        evidence_reader.lock_owned_for_binding.side_effect = None
        evidence_reader.lock_owned_for_binding.return_value = (
            PlayerCharacterBindingEligibilityEvidence(
                applicable_character_reference=REFERENCE.model_copy(
                    update={"player_character_id": changed_id}
                ),
                lifecycle=PlayerCharacterLifecycle.ACTIVE,
            )
        )
    elif field == "revision":
        changes = {
            "expected_record_revision": PlayerCharacterRevision(value=2)
        }
    else:
        changes = {"scenario_id": "scenario.changed"}
    before_issuers = (run_issuer.calls, line_issuer.calls)

    result = await service.enter(PRINCIPAL, command=_command(**changes))

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.IDEMPOTENCY_CONFLICT
    )
    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert replay.commit.await_count == 0
    assert replay.rollback_calls == replay.close_calls == 1
    replay.runs.get_for_update.assert_not_awaited()
    replay.runs.get_active_for_player_character_for_update.assert_not_awaited()
    replay.sessions.get_by_creation_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_historical_receipt_is_conflict_without_rewrite_or_recovery() -> None:
    events: list[str] = []
    fresh = _Uow(events)
    replay = _Uow(events)
    factory = _Factory(fresh, replay)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    command = _command()
    created = await service.enter(PRINCIPAL, command=command)
    assert isinstance(created, RunEntryResult)
    stored = _stored_creation(fresh)
    historical = CreateRunCommand(
        source_reference=RunAuthoritySourceRef(value="source.production-run")
    )
    historical_bytes, historical_fingerprint = create_run_fingerprint(
        historical
    )
    replay.run_creation_receipts.get_with_evidence.side_effect = None
    replay.run_creation_receipts.get_with_evidence.return_value = (
        StoredRunCreationEvidence(
            receipt=stored.receipt.model_copy(
                update={"fingerprint": historical_fingerprint}
            ),
            evidence=historical,
            evidence_canonical=historical_bytes,
        )
    )
    before_issuers = (run_issuer.calls, line_issuer.calls)

    result = await service.enter(PRINCIPAL, command=command)

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.IDEMPOTENCY_CONFLICT
    )
    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert replay.commit.await_count == 0
    assert replay.rollback_calls == replay.close_calls == 1
    replay.runs.get_for_update.assert_not_awaited()
    replay.run_creation_receipts.add_with_evidence.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("eligibility", ("inactive", "version-exhausted"))
async def test_fresh_ineligible_character_stops_before_binding_and_scenario_checks(
    eligibility: str,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, run_issuer, line_issuer, evidence_reader = _service(factory, events)
    reference = REFERENCE
    lifecycle = PlayerCharacterLifecycle.RETIRED
    command = _command()
    if eligibility == "version-exhausted":
        reference = REFERENCE.model_copy(
            update={
                "record_revision": PlayerCharacterRevision(value=2**63 - 1)
            }
        )
        lifecycle = PlayerCharacterLifecycle.ACTIVE
        command = _command(expected_record_revision=reference.record_revision)
    evidence_reader.lock_owned_for_binding.side_effect = None
    evidence_reader.lock_owned_for_binding.return_value = (
        PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=reference,
            lifecycle=lifecycle,
        )
    )

    result = await service.enter(PRINCIPAL, command=command)

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE
    )
    assert factory.calls == 1
    assert run_issuer.calls == line_issuer.calls == 0
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 1
    uow.runs.get_active_for_player_character_for_update.assert_not_awaited()
    uow.sessions.get_by_creation_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_existing_active_binding_is_ineligible_before_scenario_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    fresh = _Uow(events)
    occupied = _Uow(events)
    factory = _Factory(fresh, occupied)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    first = await service.enter(PRINCIPAL, command=_command())
    assert isinstance(first, RunEntryResult)
    active = fresh.runs.append_revision.await_args_list[1].args[0]
    occupied.runs.get_active_for_player_character_for_update.side_effect = None
    occupied.runs.get_active_for_player_character_for_update.return_value = active
    policy = Mock(side_effect=AssertionError("bound character reached policy"))
    monkeypatch.setattr(
        SessionService,
        "resolve_run_entry_definition",
        policy,
    )
    before_issuers = (run_issuer.calls, line_issuer.calls)

    result = await service.enter(
        PRINCIPAL,
        command=_command(
            public_operation_key=RunEntryPublicOperationKey(
                value="entry.bound-other-key"
            )
        ),
    )

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE
    )
    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert occupied.commit.await_count == 0
    assert occupied.rollback_calls == occupied.close_calls == 1
    policy.assert_not_called()
    occupied.sessions.get_by_creation_request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("unavailable", ("scenario", "default"))
async def test_unavailable_scenario_or_default_is_exact_invalid_definition_decision(
    unavailable: str,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    command = _command(scenario_id="scenario.missing")
    if unavailable == "default":
        command = _command()
        service.session_service.catalog = (
            service.session_service.catalog.model_copy(
                update={"characters": ()}
            )
        )

    result = await service.enter(PRINCIPAL, command=command)

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.INVALID_SCENARIO_DEFINITION
    )
    assert factory.calls == 1
    assert run_issuer.calls == line_issuer.calls == 0
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 1
    uow.runs.get_active_for_player_character_for_update.assert_awaited_once_with(
        REFERENCE.player_character_id
    )
    uow.sessions.get_by_creation_request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("loss", "expected"),
    (
        (
            "creation-receipt",
            RunEntryDecisionCode.IDEMPOTENCY_CONFLICT,
        ),
        ("binding-receipt", RunEntryDecisionCode.RUN_ENTRY_CONFLICT),
        ("cas", RunEntryDecisionCode.RUN_ENTRY_CONFLICT),
        ("session-identity", RunEntryDecisionCode.RUN_ENTRY_CONFLICT),
    ),
)
async def test_each_fresh_conflict_boundary_has_exact_decision_and_cleanup(
    loss: str,
    expected: RunEntryDecisionCode,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, _, _, _ = _service(factory, events)
    if loss == "creation-receipt":
        uow.run_creation_receipts.add_with_evidence.side_effect = (
            RunReceiptUniquenessConflictError("creation collision")
        )
    elif loss == "binding-receipt":
        uow.run_mutation_receipts.add.side_effect = (
            RunReceiptUniquenessConflictError("binding collision")
        )
    elif loss == "cas":
        async def lose_cas(*args, **kwargs):
            events.append("run.cas")
            return False

        uow.runs.compare_and_swap_current.side_effect = lose_cas
    else:
        uow.sessions.get_by_creation_request.side_effect = None
        uow.sessions.get_by_creation_request.return_value = object()

    result = await service.enter(PRINCIPAL, command=_command())

    assert result == RunEntryDecision(code=expected)
    assert factory.calls == 1
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 1
    if loss == "creation-receipt":
        uow.runs.append_revision.assert_not_awaited()
    if loss == "binding-receipt":
        assert uow.run_mutation_receipts.add.await_count == 1
        uow.sessions.add_initial_session.assert_not_awaited()
    if loss == "cas":
        assert uow.runs.compare_and_swap_current.await_count == 1
        uow.run_mutation_receipts.add.assert_not_awaited()
    if loss == "session-identity":
        uow.runs.add_initial.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_replay_run_is_integrity_failure_not_success_or_decision() -> None:
    events: list[str] = []
    fresh = _Uow(events)
    replay = _Uow(events)
    factory = _Factory(fresh, replay)
    service, run_issuer, line_issuer, _ = _service(factory, events)
    command = _command()
    created = await service.enter(PRINCIPAL, command=command)
    assert isinstance(created, RunEntryResult)
    replay.run_creation_receipts.get_with_evidence.side_effect = None
    replay.run_creation_receipts.get_with_evidence.return_value = _stored_creation(
        fresh
    )
    before_issuers = (run_issuer.calls, line_issuer.calls)

    with pytest.raises(RunEntryIntegrityError, match="family is missing"):
        await service.enter(PRINCIPAL, command=command)

    assert (run_issuer.calls, line_issuer.calls) == before_issuers
    assert replay.commit.await_count == 0
    assert replay.rollback_calls == replay.close_calls == 1
    replay.sessions.get_owned_for_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejections_preserve_one_uow_zero_commit_and_precedence() -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, run_issuer, line_issuer, evidence_reader = _service(factory, events)
    evidence_reader.lock_owned_for_binding.return_value = (
        PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=REFERENCE,
            lifecycle=PlayerCharacterLifecycle.ACTIVE,
        )
    )

    result = await service.enter(
        PRINCIPAL,
        command=_command(
            expected_record_revision=PlayerCharacterRevision(value=2)
        ),
    )

    assert result == RunEntryDecision(code=RunEntryDecisionCode.PLAYER_CHARACTER_STALE)
    assert factory.calls == 1
    assert run_issuer.calls == line_issuer.calls == 0
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 1
    uow.runs.get_active_for_player_character_for_update.assert_not_awaited()
    uow.sessions.get_by_creation_request.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("pre-commit failure"),
        asyncio.CancelledError(),
    ),
)
async def test_precommit_failures_and_cancellation_propagate_without_recovery(
    failure: BaseException,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, _, _, _ = _service(factory, events)
    uow.sessions.persist_events.side_effect = failure

    with pytest.raises(type(failure)):
        await service.enter(PRINCIPAL, command=_command())

    assert factory.calls == 1
    assert uow.commit.await_count == 0
    assert uow.rollback_calls == uow.close_calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    (
        RuntimeError("uncertain commit"),
        asyncio.CancelledError(),
    ),
)
async def test_commit_failure_or_cancellation_has_one_attempt_and_no_success(
    failure: BaseException,
) -> None:
    events: list[str] = []
    uow = _Uow(events)
    factory = _Factory(uow)
    service, _, _, _ = _service(factory, events)
    uow.commit.side_effect = failure

    with pytest.raises(type(failure)):
        await service.enter(PRINCIPAL, command=_command())

    assert factory.calls == 1
    assert uow.commit.await_count == 1
    assert uow.rollback_calls == uow.close_calls == 1


def test_p8_s3_exposes_the_canonical_run_entry_service_at_the_public_route() -> None:
    events: list[str] = []
    service, _, _, _ = _service(_Factory(_Uow(events)), events)
    services = api_dependencies.ApiServices(
        session_service=service.session_service,
        turn_orchestrator=object(),  # type: ignore[arg-type]
        run_entry_service=service,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(api_services=services))
    )
    app = api_main.create_app(services=services)
    route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/v1/runs"
    )
    result_fields = set(RunEntryResult.model_fields)

    assert not hasattr(api_dependencies, "RunEntryCoordinator")
    assert not hasattr(api_main, "RunEntryCoordinator")
    assert get_type_hints(api_dependencies.ApiServices)["run_entry_service"] == (
        RunEntryService | None
    )
    assert (
        get_type_hints(api_dependencies.get_run_entry_service)["return"]
        is RunEntryService
    )
    assert api_dependencies.get_run_entry_service(request) is service
    assert get_type_hints(route.endpoint)["service"] is RunEntryService
    assert api_dependencies.get_run_entry_service in {
        dependency.call for dependency in route.dependant.dependencies
    }
    assert route.methods == {"POST"}
    assert route.operation_id == "enter_run"
    assert result_fields == {
        "run_id",
        "session_id",
        "scenario_id",
        "player_character",
    }
    assert not {
        "snapshot",
        "receipt",
        "operation_id",
        "continuous_story_line_id",
        "source_reference",
        "random_seed",
    } & result_fields
