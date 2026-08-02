from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.errors import (
    SnapshotContentVersionMismatchError,
    SnapshotSessionMismatchError,
)
from deviation_protocol.application.run_entry_service import (
    RunEntryCommand,
    RunEntryDecision,
    RunEntryDecisionCode,
    RunEntryIntegrityError,
    RunEntryResult,
    RunEntryService,
)
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.application.player_character_operations import (
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    build_mutation_success_receipt,
    mutation_fingerprint,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecision,
    RunReplayDecisionCode,
    StoredRunSuccessReceipt,
    activate_first_session_for_run,
    attach_session_fingerprint,
    attach_session_result,
    bind_player_character_fingerprint,
    bind_player_character_result,
    bind_player_character_to_run,
)
from deviation_protocol.application.run_service import (
    RunService,
    RunServiceDecision,
    RunServiceDecisionCode,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
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
    PlayerCharacterPolicyCode,
    PlayerCharacterPolicyDecision,
    PlayerConfirmation,
    RetirePlayerCharacterPolicy,
    TrustedFinalDeathEvidence,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSnapshotRow,
    GameSessionRow,
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
    RunCreationReceiptRow,
    RunCurrentRow,
    RunMutationReceiptRow,
    RunRevisionRow,
    RunSessionParticipationRow,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyGameSessionRepository,
    SqlAlchemyPlayerCharacterRepository,
    SqlAlchemyRunCreationReceiptRepository,
    SqlAlchemyRunMutationReceiptRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyRunSessionParticipationRepository,
)
from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunRepositoryError,
    RunStoredRecordIntegrityError,
    attach_operation_evidence_to_storage_bytes,
    binding_operation_evidence_to_storage_bytes,
    fingerprint_to_storage_bytes as run_fingerprint_to_storage_bytes,
    run_receipt_to_storage_bytes,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


NOW = datetime(2026, 7, 29, 15, 0, tzinfo=UTC)
RUN_SOURCE = RunAuthoritySourceRef(value="source.mysql-binding-run")
CHARACTER_SOURCE = AuthoritySourceRef(
    value="source.mysql-binding-character"
)
TIMEOUT = 10.0
LOCK_PROBE_TIMEOUT = 3.0
SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)


class _Resolver:
    def __init__(
        self,
        principal: RequestPrincipal,
        binding: ControllerBindingRef,
    ) -> None:
        self.principal = principal
        self.binding = binding

    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef:
        assert principal == self.principal
        return self.binding


class _Issuer:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.calls = 0

    def issue(self) -> Any:
        self.calls += 1
        return self.value


@dataclass(slots=True)
class _Scope:
    token: str
    run_ids: set[str] = field(default_factory=set)
    character_ids: set[str] = field(default_factory=set)
    bindings: set[str] = field(default_factory=set)
    session_ids: set[str] = field(default_factory=set)

    def run_id(self, suffix: str) -> RunId:
        value = f"run.bind-{self.token}-{suffix}"
        self.run_ids.add(value)
        return RunId(value=value)

    def line_id(self, suffix: str) -> ContinuousStoryLineId:
        return ContinuousStoryLineId(
            value=f"csl.bind-{self.token}-{suffix}"
        )

    def character_id(self, suffix: str) -> PlayerCharacterId:
        value = f"pc.bind-{self.token}-{suffix}"
        self.character_ids.add(value)
        return PlayerCharacterId(value=value)

    def binding(self, suffix: str) -> ControllerBindingRef:
        value = f"binding.bind-{self.token}-{suffix}"
        self.bindings.add(value)
        return ControllerBindingRef(value=value)

    def principal(self, suffix: str) -> RequestPrincipal:
        return RequestPrincipal(
            player_id=f"player.{self.token}-{suffix}",
            authentication_scheme="integration",
        )

    def session_id(self, suffix: str) -> str:
        value = f"session.{self.token}-{suffix}"
        self.session_ids.add(value)
        return value


@pytest.fixture
async def binding_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> Any:
    scope = _Scope(token=uuid4().hex)
    try:
        yield scope
    finally:
        async with mysql_session_factory.begin() as session:
            if scope.run_ids:
                await session.execute(
                    sa.delete(RunMutationReceiptRow).where(
                        RunMutationReceiptRow.run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    sa.delete(RunCreationReceiptRow).where(
                        RunCreationReceiptRow.result_run_id.in_(
                            scope.run_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(RunCurrentRow).where(
                        RunCurrentRow.run_id.in_(scope.run_ids)
                    )
                )
                await session.execute(
                    sa.delete(RunSessionParticipationRow).where(
                        RunSessionParticipationRow.run_id.in_(
                            scope.run_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(RunRevisionRow).where(
                        RunRevisionRow.run_id.in_(scope.run_ids)
                    )
                )
            if scope.session_ids:
                await session.execute(
                    sa.delete(GameSessionRow).where(
                        GameSessionRow.session_id.in_(scope.session_ids)
                    )
                )
            if scope.character_ids:
                await session.execute(
                    sa.delete(PlayerCharacterMutationReceiptRow).where(
                        PlayerCharacterMutationReceiptRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterCurrentRow).where(
                        PlayerCharacterCurrentRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterCreationReceiptRow).where(
                        PlayerCharacterCreationReceiptRow.result_player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterRevisionRow).where(
                        PlayerCharacterRevisionRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterIdAllocationRow).where(
                        PlayerCharacterIdAllocationRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
            if scope.bindings:
                await session.execute(
                    sa.delete(PlayerCharacterControllerBindingRow).where(
                        PlayerCharacterControllerBindingRow.controller_binding.in_(
                            scope.bindings
                        )
                    )
                )


@dataclass(frozen=True, slots=True)
class _Character:
    principal: RequestPrincipal
    binding: ControllerBindingRef
    record: CanonicalPlayerCharacter
    resolver: _Resolver
    service: PlayerCharacterService


def _character_service(
    factory: async_sessionmaker[AsyncSession],
    *,
    principal: RequestPrincipal,
    binding: ControllerBindingRef,
    player_character_id: PlayerCharacterId,
) -> tuple[PlayerCharacterService, _Resolver]:
    resolver = _Resolver(principal, binding)
    service = PlayerCharacterService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(factory),
        controller_binding_resolver=resolver,
        player_character_id_issuer=_Issuer(player_character_id),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=CHARACTER_SOURCE,
        clock=lambda: NOW,
        binding_integrity_guard_enabled=True,
    )
    return service, resolver


async def _create_character(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
    suffix: str,
) -> _Character:
    principal = scope.principal(suffix)
    binding = scope.binding(suffix)
    player_character_id = scope.character_id(suffix)
    service, resolver = _character_service(
        factory,
        principal=principal,
        binding=binding,
        player_character_id=player_character_id,
    )
    await service.create(
        principal,
        operation_id=PlayerCharacterOperationId(
            value=f"operation.{scope.token}.create-character-{suffix}"
        ),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    async with SqlAlchemyUnitOfWork(factory) as uow:
        record = await uow.player_characters.get(player_character_id)
    assert record is not None
    return _Character(
        principal=principal,
        binding=binding,
        record=record,
        resolver=resolver,
        service=service,
    )


async def _create_additional_owned_character(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
    suffix: str,
    owner: _Character,
) -> _Character:
    player_character_id = scope.character_id(suffix)
    service, resolver = _character_service(
        factory,
        principal=owner.principal,
        binding=owner.binding,
        player_character_id=player_character_id,
    )
    await service.create(
        owner.principal,
        operation_id=PlayerCharacterOperationId(
            value=f"operation.{scope.token}.create-character-{suffix}"
        ),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    async with SqlAlchemyUnitOfWork(factory) as uow:
        record = await uow.player_characters.get(player_character_id)
    assert record is not None
    return _Character(
        principal=owner.principal,
        binding=owner.binding,
        record=record,
        resolver=resolver,
        service=service,
    )


def _run_service(
    factory: async_sessionmaker[AsyncSession],
    *,
    run_id: RunId,
    line_id: ContinuousStoryLineId,
    character: _Character,
    uow_type: type[SqlAlchemyUnitOfWork] = SqlAlchemyUnitOfWork,
    evidence: Any | None = None,
    uow_factory: Any | None = None,
) -> RunService:
    return RunService(
        uow_factory=(
            uow_factory
            if uow_factory is not None
            else lambda: uow_type(factory)
        ),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RUN_SOURCE,
        clock=lambda: NOW,
        controller_binding_resolver=character.resolver,
        player_character_binding_evidence=(
            evidence if evidence is not None else character.service
        ),
    )


async def _create_run(
    service: RunService,
    scope: _Scope,
    suffix: str,
) -> None:
    await service.create_run(
        operation_id=RunOperationId(
            value=f"operation.{scope.token}.create-run-{suffix}"
        ),
        command=CreateRunCommand(source_reference=RUN_SOURCE),
    )


async def _add_session(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
    *,
    suffix: str,
    principal: RequestPrincipal,
) -> str:
    session_id = scope.session_id(suffix)
    async with factory.begin() as session:
        session.add(
            GameSessionRow(
                session_id=session_id,
                player_id=principal.player_id,
                scenario_id="binding-lock-order-scenario",
                scenario_version="1",
                phase="AWAITING_ACTION",
                turn_number=0,
                state_version=0,
                random_seed=42,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    return session_id


def _bind_command(
    *,
    run_id: RunId,
    line_id: ContinuousStoryLineId,
    character: _Character,
) -> BindPlayerCharacterCommand:
    return BindPlayerCharacterCommand(
        run_id=run_id,
        continuous_story_line_id=line_id,
        target_player_character_id=character.record.player_character_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=RUN_SOURCE,
    )


def _lifecycle_command(
    character: _Character,
    *,
    kind: PlayerCharacterMutationKind,
    suffix: str,
) -> tuple[PlayerCharacterOperationId, CharacterMutationCommand]:
    operation_id = PlayerCharacterOperationId(
        value=f"operation.lifecycle-{suffix}"
    )
    reference = ApplicableCharacterReference(
        player_character_id=character.record.player_character_id,
        contract_version=character.record.contract_version,
        record_revision=character.record.record_revision,
    )
    common: dict[str, Any] = {
        "contract_version": character.record.contract_version,
        "command_kind": kind,
        "target_player_character_id": (
            character.record.player_character_id
        ),
        "expected_revision": character.record.record_revision,
        "applicable_reference": reference,
    }
    if kind is PlayerCharacterMutationKind.RETIRE:
        common["confirmation"] = PlayerConfirmation(
            player_character_id=character.record.player_character_id,
            expected_revision=character.record.record_revision,
            operation_id=operation_id,
            mutation_kind=kind,
            source_reference=CHARACTER_SOURCE,
        )
    else:
        common["final_death_evidence"] = TrustedFinalDeathEvidence(
            player_character_id=character.record.player_character_id,
            expected_revision=character.record.record_revision,
            operation_id=operation_id,
            source_reference=CHARACTER_SOURCE,
        )
    return operation_id, CharacterMutationCommand(**common)


async def _run_family_counts(
    factory: async_sessionmaker[AsyncSession],
    run_id: RunId,
) -> tuple[int, int, int, int]:
    async with factory() as session:
        values = []
        for row_type in (
            RunRevisionRow,
            RunCurrentRow,
            RunCreationReceiptRow,
            RunMutationReceiptRow,
        ):
            column = (
                row_type.result_run_id
                if row_type is RunCreationReceiptRow
                else row_type.run_id
            )
            values.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count())
                        .select_from(row_type)
                        .where(column == run_id.value)
                    )
                    or 0
                )
            )
        return tuple(values)  # type: ignore[return-value]


@dataclass(slots=True)
class _LockOrderCoordination:
    player_character_locked: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    attach_run_requested: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    run_locked: asyncio.Event = field(default_factory=asyncio.Event)
    attach_run_locked: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    connection_ids: dict[str, int] = field(default_factory=dict)
    critical_events: list[str] = field(default_factory=list)

    def diagnostics(self) -> str:
        return (
            f"player_character_locked={self.player_character_locked.is_set()}, "
            "attach_run_requested="
            f"{self.attach_run_requested.is_set()}, "
            f"run_locked={self.run_locked.is_set()}, "
            f"attach_run_locked={self.attach_run_locked.is_set()}, "
            f"connection_ids={self.connection_ids}, "
            f"critical_events={self.critical_events}"
        )


class _AttachPlayerCharacterRepository(
    SqlAlchemyPlayerCharacterRepository
):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LockOrderCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ):
        raise AssertionError(
            "attachment must not read or lock player_character_current "
            "after taking the Run lock"
        )


class _AttachReconstructionRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LockOrderCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key,
    ):
        self._coordination.critical_events.append(
            "attach_run_requested"
        )
        self._coordination.attach_run_requested.set()
        await asyncio.wait_for(
            self._coordination.run_locked.wait(),
            timeout=TIMEOUT,
        )
        result = await super().get_session_attachment_lock_evidence(
            run_id,
            receipt_key=receipt_key,
        )
        self._coordination.critical_events.append("attach_run_locked")
        self._coordination.attach_run_locked.set()
        return result


class _ReplayRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LockOrderCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_for_update(self, run_id: RunId):
        result = await super().get_for_update(run_id)
        self._coordination.critical_events.append(
            "binding_replay_run_locked"
        )
        self._coordination.run_locked.set()
        return result


class _LifecycleGuardRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LockOrderCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_active_for_player_character_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ):
        self._coordination.critical_events.append(
            "lifecycle_player_character_locked"
        )
        self._coordination.player_character_locked.set()
        await asyncio.wait_for(
            self._coordination.attach_run_requested.wait(),
            timeout=TIMEOUT,
        )
        result = await super().get_active_for_player_character_for_update(
            player_character_id
        )
        self._coordination.critical_events.append("lifecycle_run_locked")
        self._coordination.run_locked.set()
        return result


class _CoordinatedUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        coordination: _LockOrderCoordination,
        role: str,
        run_repository_kind: str,
    ) -> None:
        super().__init__(factory)
        self._coordination = coordination
        self._role = role
        self._run_repository_kind = run_repository_kind

    async def __aenter__(self) -> "_CoordinatedUnitOfWork":
        await super().__aenter__()
        assert self._session is not None
        connection_id = await self._session.scalar(
            sa.text("SELECT CONNECTION_ID()")
        )
        assert connection_id is not None
        self._coordination.connection_ids[self._role] = int(connection_id)
        if self._run_repository_kind == "attach":
            self.player_characters = _AttachPlayerCharacterRepository(
                self._session,
                self._coordination,
            )
            self.runs = _AttachReconstructionRunRepository(
                self._session,
                self._coordination,
            )
        elif self._run_repository_kind == "lifecycle":
            self.runs = _LifecycleGuardRunRepository(
                self._session,
                self._coordination,
            )
        else:
            assert self._run_repository_kind == "record-only"
            self.runs = _ReplayRunRepository(
                self._session,
                self._coordination,
            )
        return self


class _CoordinatedBindingEvidence:
    def __init__(
        self,
        delegate: PlayerCharacterService,
        coordination: _LockOrderCoordination,
    ) -> None:
        self._delegate = delegate
        self._coordination = coordination

    async def lock_owned_for_binding(self, uow, **kwargs):
        evidence = await self._delegate.lock_owned_for_binding(
            uow,
            **kwargs,
        )
        self._coordination.critical_events.append(
            "binding_replay_player_character_locked"
        )
        self._coordination.player_character_locked.set()
        await asyncio.wait_for(
            self._coordination.attach_run_requested.wait(),
            timeout=TIMEOUT,
        )
        return evidence


async def _finish_concurrent_pair(
    *,
    label: str,
    coordination: _LockOrderCoordination,
    first: asyncio.Task[Any],
    second: asyncio.Task[Any],
) -> tuple[Any, Any]:
    tasks = (first, second)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=TIMEOUT,
        )
    except Exception as exc:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise AssertionError(
            f"{label} did not serialize cleanly; "
            f"{coordination.diagnostics()}; "
            f"failure={type(exc).__name__}: {exc}"
        ) from exc
    return results[0], results[1]


@dataclass(slots=True)
class _InverseForeignKeyDeadlockCoordination:
    attachment_session_locked: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    attachment_run_family_locked: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    attachment_before_revision_flush: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    allow_attachment_revision_flush: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    attachment_commit_returned: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    player_character_family_locked: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    player_character_run_lock_requested: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    player_character_run_lock_acquired: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    connection_ids: dict[str, int] = field(default_factory=dict)
    isolation_levels: dict[str, str] = field(default_factory=dict)
    mysql_versions: dict[str, str] = field(default_factory=dict)
    critical_events: list[str] = field(default_factory=list)
    lock_metadata_supported: bool | None = None
    lock_wait_observed: bool | None = None
    lock_metadata_errno: int | None = None
    player_character_current_lock_observed: bool = False
    player_character_revision_lock_sql: list[str] = field(
        default_factory=list
    )
    attachment_committed: bool = False
    attachment_rolled_back: bool = False
    player_character_rolled_back: bool = False

    def diagnostics(self) -> str:
        return (
            "attachment_session_locked="
            f"{self.attachment_session_locked.is_set()}, "
            "attachment_run_family_locked="
            f"{self.attachment_run_family_locked.is_set()}, "
            "attachment_before_revision_flush="
            f"{self.attachment_before_revision_flush.is_set()}, "
            "player_character_family_locked="
            f"{self.player_character_family_locked.is_set()}, "
            "player_character_run_lock_requested="
            f"{self.player_character_run_lock_requested.is_set()}, "
            "player_character_run_lock_acquired="
            f"{self.player_character_run_lock_acquired.is_set()}, "
            f"connection_ids={self.connection_ids}, "
            f"isolation_levels={self.isolation_levels}, "
            f"mysql_versions={self.mysql_versions}, "
            f"critical_events={self.critical_events}, "
            "lock_metadata_supported="
            f"{self.lock_metadata_supported}, "
            f"lock_wait_observed={self.lock_wait_observed}, "
            f"lock_metadata_errno={self.lock_metadata_errno}, "
            "player_character_current_lock_observed="
            f"{self.player_character_current_lock_observed}, "
            "player_character_revision_lock_sql="
            f"{self.player_character_revision_lock_sql}, "
            f"attachment_committed={self.attachment_committed}, "
            f"attachment_rolled_back={self.attachment_rolled_back}, "
            "player_character_rolled_back="
            f"{self.player_character_rolled_back}"
        )


class _InverseAttachmentSessionRepository(
    SqlAlchemyGameSessionRepository
):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _InverseForeignKeyDeadlockCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ):
        result = await super().get_owned_for_update(
            session_id,
            player_id,
        )
        assert result is not None
        self._coordination.critical_events.append(
            "attachment_session_locked"
        )
        self._coordination.attachment_session_locked.set()
        return result


class _InverseAttachmentRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _InverseForeignKeyDeadlockCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key,
    ):
        result = await super().get_session_attachment_lock_evidence(
            run_id,
            receipt_key=receipt_key,
        )
        assert result is not None
        self._coordination.critical_events.append(
            "attachment_run_family_locked"
        )
        self._coordination.attachment_run_family_locked.set()
        return result

    async def _flush_run_row(self, row: Any, **kwargs: Any) -> None:
        if (
            isinstance(row, RunRevisionRow)
            and row.mutation_kind == "ATTACH_SESSION"
        ):
            self._coordination.critical_events.append(
                "attachment_before_revision_flush"
            )
            self._coordination.attachment_before_revision_flush.set()
            await asyncio.wait_for(
                self._coordination.allow_attachment_revision_flush.wait(),
                timeout=TIMEOUT,
            )
            self._coordination.critical_events.append(
                "attachment_revision_flush_started"
            )
            await super()._flush_run_row(row, **kwargs)
            self._coordination.critical_events.append(
                "attachment_revision_flush_completed"
            )
            return
        await super()._flush_run_row(row, **kwargs)


class _InversePlayerCharacterRepository(
    SqlAlchemyPlayerCharacterRepository
):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _InverseForeignKeyDeadlockCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    @staticmethod
    def _sql(statement: Any) -> str:
        return str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()

    def _observe_lock_statement(self, statement: Any) -> None:
        sql = self._sql(statement)
        if (
            "from player_character_current" in sql
            and "for update" in sql
        ):
            self._coordination.player_character_current_lock_observed = True
        if "from player_character_revisions" in sql:
            self._coordination.player_character_revision_lock_sql.append(sql)

    async def _scalar(self, statement: Any) -> Any:
        self._observe_lock_statement(statement)
        return await super()._scalar(statement)

    async def _scalars(self, statement: Any) -> tuple[Any, ...]:
        self._observe_lock_statement(statement)
        return await super()._scalars(statement)

    async def get_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ):
        result = await super().get_for_update(player_character_id)
        assert result is not None
        self._coordination.critical_events.append(
            "player_character_family_locked"
        )
        self._coordination.player_character_family_locked.set()
        return result


class _InversePlayerCharacterRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _InverseForeignKeyDeadlockCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    @staticmethod
    def _sql(statement: Any) -> str:
        return str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()

    async def _run_scalar(self, statement: Any) -> Any:
        sql = self._sql(statement)
        observes_run_lock = (
            "from run_current" in sql
            and "for update" in sql
            and not self._coordination.player_character_run_lock_requested.is_set()
        )
        if observes_run_lock:
            self._coordination.critical_events.append(
                "player_character_run_lock_requested"
            )
            self._coordination.player_character_run_lock_requested.set()
        result = await super()._run_scalar(statement)
        if observes_run_lock:
            await asyncio.wait_for(
                self._coordination.attachment_commit_returned.wait(),
                timeout=TIMEOUT,
            )
            self._coordination.critical_events.append(
                "player_character_run_lock_acquired"
            )
            self._coordination.player_character_run_lock_acquired.set()
        return result


class _InverseForeignKeyDeadlockUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        coordination: _InverseForeignKeyDeadlockCoordination,
        role: str,
    ) -> None:
        super().__init__(factory)
        self._coordination = coordination
        self._role = role

    async def __aenter__(self) -> "_InverseForeignKeyDeadlockUnitOfWork":
        await super().__aenter__()
        assert self._session is not None
        connection_id = await self._session.scalar(
            sa.text("SELECT CONNECTION_ID()")
        )
        isolation_level = await self._session.scalar(
            sa.text("SELECT @@transaction_isolation")
        )
        mysql_version = await self._session.scalar(
            sa.text("SELECT VERSION()")
        )
        assert connection_id is not None
        assert isolation_level is not None
        assert mysql_version is not None
        self._coordination.connection_ids[self._role] = int(connection_id)
        self._coordination.isolation_levels[self._role] = str(
            isolation_level
        )
        self._coordination.mysql_versions[self._role] = str(mysql_version)
        if self._role == "attachment":
            self.sessions = _InverseAttachmentSessionRepository(
                self._session,
                self._coordination,
            )
            self.runs = _InverseAttachmentRunRepository(
                self._session,
                self._coordination,
            )
        else:
            assert self._role == "player-character"
            self.player_characters = _InversePlayerCharacterRepository(
                self._session,
                self._coordination,
            )
            self.runs = _InversePlayerCharacterRunRepository(
                self._session,
                self._coordination,
            )
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await super().__aexit__(exc_type, exc, traceback)
        if self._role == "attachment" and not self._committed:
            self._coordination.attachment_rolled_back = True
        if self._role == "player-character" and not self._committed:
            self._coordination.player_character_rolled_back = True

    async def commit(self) -> None:
        await super().commit()
        if self._role == "attachment":
            self._coordination.attachment_committed = True
            self._coordination.critical_events.append(
                "attachment_commit_returned"
            )
            self._coordination.attachment_commit_returned.set()


def _dbapi_errno(exc: DBAPIError) -> int | None:
    arguments = getattr(exc.orig, "args", ())
    return (
        arguments[0]
        if arguments and type(arguments[0]) is int
        else None
    )


async def _observe_mysql_run_lock_wait(
    factory: async_sessionmaker[AsyncSession],
    coordination: _InverseForeignKeyDeadlockCoordination,
) -> None:
    deadline = asyncio.get_running_loop().time() + LOCK_PROBE_TIMEOUT
    statement = sa.text(
        """
        SELECT COUNT(*)
        FROM performance_schema.data_lock_waits AS waits
        JOIN performance_schema.threads AS requesting
          ON requesting.THREAD_ID = waits.REQUESTING_THREAD_ID
        JOIN performance_schema.threads AS blocking
          ON blocking.THREAD_ID = waits.BLOCKING_THREAD_ID
        WHERE requesting.PROCESSLIST_ID = :requesting_id
          AND blocking.PROCESSLIST_ID = :blocking_id
        """
    )
    try:
        async with factory() as session:
            while True:
                count = await session.scalar(
                    statement,
                    {
                        "requesting_id": coordination.connection_ids[
                            "player-character"
                        ],
                        "blocking_id": coordination.connection_ids[
                            "attachment"
                        ],
                    },
                )
                coordination.lock_metadata_supported = True
                if int(count or 0) >= 1:
                    coordination.lock_wait_observed = True
                    coordination.critical_events.append(
                        "mysql_run_lock_wait_observed"
                    )
                    return
                if asyncio.get_running_loop().time() >= deadline:
                    coordination.lock_wait_observed = False
                    return
                await asyncio.sleep(0.01)
    except DBAPIError as exc:
        errno = _dbapi_errno(exc)
        if errno not in {1044, 1142, 1146, 1227}:
            raise
        coordination.lock_metadata_supported = False
        coordination.lock_wait_observed = None
        coordination.lock_metadata_errno = errno
        coordination.critical_events.append(
            "mysql_lock_metadata_unavailable"
        )


async def _finish_inverse_foreign_key_pair(
    *,
    label: str,
    coordination: _InverseForeignKeyDeadlockCoordination,
    attachment: asyncio.Task[Any],
    player_character: asyncio.Task[Any],
) -> tuple[Any, Any]:
    tasks = (attachment, player_character)
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=TIMEOUT,
        )
    except Exception as exc:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise AssertionError(
            f"{label} did not complete without a deadlock victim; "
            f"{coordination.diagnostics()}; "
            f"failure={type(exc).__name__}: {exc}"
        ) from exc
    return results[0], results[1]


@dataclass(slots=True)
class _LateBindingCoordination:
    session_locked: asyncio.Event = field(default_factory=asyncio.Event)
    run_lock_requested: asyncio.Event = field(default_factory=asyncio.Event)
    binding_committed: asyncio.Event = field(default_factory=asyncio.Event)
    run_locked: asyncio.Event = field(default_factory=asyncio.Event)
    immutable_revision_read: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    connection_ids: dict[str, int] = field(default_factory=dict)
    isolation_levels: dict[str, str] = field(default_factory=dict)
    critical_events: list[str] = field(default_factory=list)
    observed_current_version: int | None = None
    observed_creation_operation: str | None = None
    attachment_rolled_back: bool = False

    def diagnostics(self) -> str:
        return (
            f"session_locked={self.session_locked.is_set()}, "
            f"run_lock_requested={self.run_lock_requested.is_set()}, "
            f"binding_committed={self.binding_committed.is_set()}, "
            f"run_locked={self.run_locked.is_set()}, "
            "immutable_revision_read="
            f"{self.immutable_revision_read.is_set()}, "
            f"connection_ids={self.connection_ids}, "
            f"isolation_levels={self.isolation_levels}, "
            f"critical_events={self.critical_events}, "
            f"observed_current_version={self.observed_current_version}, "
            "observed_creation_operation="
            f"{self.observed_creation_operation}, "
            f"attachment_rolled_back={self.attachment_rolled_back}"
        )


class _LateBindingSessionRepository(SqlAlchemyGameSessionRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LateBindingCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ):
        result = await super().get_owned_for_update(
            session_id,
            player_id,
        )
        assert result is not None
        self._coordination.critical_events.append(
            "attachment_session_locked"
        )
        self._coordination.session_locked.set()
        return result


class _LateBindingAttachmentRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LateBindingCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination
        self._current_run_locked = False

    async def get(self, run_id: RunId):
        raise AssertionError(
            "attachment must not perform nonlocking Run discovery before "
            "the authoritative Run lock"
        )

    @staticmethod
    def _sql(statement: Any) -> str:
        return str(
            statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

    async def _run_scalar(self, statement: Any) -> Any:
        sql = self._sql(statement)
        lowered = sql.lower()
        if (
            "from run_current" in lowered
            and "for update" in lowered
            and not self._current_run_locked
        ):
            row = await super()._run_scalar(statement)
            assert row is not None
            self._current_run_locked = True
            self._coordination.observed_current_version = row.state_version
            self._coordination.observed_creation_operation = (
                row.creation_operation_id
            )
            self._coordination.critical_events.append(
                "attachment_run_locked"
            )
            self._coordination.run_locked.set()
            return row
        if not self._current_run_locked:
            raise AssertionError(
                "attachment issued a decision-controlling read before "
                "locking the current Run"
            )
        if "from player_character_revisions" in lowered:
            assert "for update" not in lowered
            self._coordination.critical_events.append(
                "attachment_exact_immutable_revision_read"
            )
            self._coordination.immutable_revision_read.set()
        return await super()._run_scalar(statement)

    async def _run_scalars(self, statement: Any) -> tuple[Any, ...]:
        if not self._current_run_locked:
            raise AssertionError(
                "attachment issued a family read before locking the "
                "current Run"
            )
        sql = self._sql(statement).lower()
        assert "for update" in sql
        return await super()._run_scalars(statement)

    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key,
    ):
        assert self._coordination.session_locked.is_set()
        self._coordination.critical_events.append(
            "attachment_run_lock_requested"
        )
        self._coordination.run_lock_requested.set()
        await asyncio.wait_for(
            self._coordination.binding_committed.wait(),
            timeout=TIMEOUT,
        )
        try:
            result = await super().get_session_attachment_lock_evidence(
                run_id,
                receipt_key=receipt_key,
            )
        except RunStoredRecordIntegrityError:
            self._coordination.critical_events.append(
                "attachment_canonical_family_rejected"
            )
            raise
        assert result is not None
        assert (
            result.canonical_run.player_character_binding is not None
        )
        self._coordination.observed_current_version = (
            result.canonical_run.state_version.value
        )
        self._coordination.observed_creation_operation = (
            result.canonical_run.creation_provenance.operation_id.value
        )
        self._coordination.critical_events.append(
            "attachment_canonical_family_validated"
        )
        return result

    async def get_for_update(self, run_id: RunId):
        raise AssertionError(
            "late bound evidence must not invoke full bound reconstruction"
        )


class _LateBindingAttachmentPlayerCharacterRepository(
    SqlAlchemyPlayerCharacterRepository
):
    async def get(
        self,
        player_character_id: PlayerCharacterId,
    ):
        raise AssertionError(
            "late-bound attachment must not read player_character_current"
        )

    async def get_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ):
        raise AssertionError(
            "late-bound attachment must not lock player_character_current"
        )


class _LateBindingAttachmentMutationReceiptRepository(
    SqlAlchemyRunMutationReceiptRepository
):
    async def get(self, key):
        raise AssertionError(
            "attachment must not read a receipt before the Run-family lock"
        )


class _LateBindingUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        coordination: _LateBindingCoordination,
        role: str,
        attachment: bool = False,
        corrupt_run_id: RunId | None = None,
        corrupt_state_version: int | None = None,
    ) -> None:
        super().__init__(factory)
        self._coordination = coordination
        self._role = role
        self._attachment = attachment
        self._corrupt_run_id = corrupt_run_id
        self._corrupt_state_version = corrupt_state_version

    async def __aenter__(self) -> "_LateBindingUnitOfWork":
        await super().__aenter__()
        assert self._session is not None
        connection_id = await self._session.scalar(
            sa.text("SELECT CONNECTION_ID()")
        )
        isolation_level = await self._session.scalar(
            sa.text("SELECT @@transaction_isolation")
        )
        assert connection_id is not None
        assert isolation_level is not None
        self._coordination.connection_ids[self._role] = int(
            connection_id
        )
        self._coordination.isolation_levels[self._role] = str(
            isolation_level
        )
        if self._attachment:
            self.sessions = _LateBindingSessionRepository(
                self._session,
                self._coordination,
            )
            self.runs = _LateBindingAttachmentRunRepository(
                self._session,
                self._coordination,
            )
            self.player_characters = (
                _LateBindingAttachmentPlayerCharacterRepository(
                    self._session
                )
            )
            self.run_mutation_receipts = (
                _LateBindingAttachmentMutationReceiptRepository(
                    self._session
                )
            )
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await super().__aexit__(exc_type, exc, traceback)
        if self._role == "attachment" and not self._committed:
            self._coordination.attachment_rolled_back = True

    async def commit(self) -> None:
        if self._corrupt_run_id is not None:
            assert self._session is not None
            assert self._corrupt_state_version is not None
            rewritten_operation = "operation.rewritten-create"
            rewritten_source = "source.rewritten-create"
            revision_result = await self._session.execute(
                sa.update(RunRevisionRow)
                .where(
                    RunRevisionRow.run_id
                    == self._corrupt_run_id.value,
                    RunRevisionRow.state_version
                    == self._corrupt_state_version,
                )
                .values(
                    creation_operation_id=rewritten_operation,
                    creation_source_reference=rewritten_source,
                )
            )
            current_result = await self._session.execute(
                sa.update(RunCurrentRow)
                .where(
                    RunCurrentRow.run_id
                    == self._corrupt_run_id.value,
                    RunCurrentRow.state_version
                    == self._corrupt_state_version,
                )
                .values(
                    creation_operation_id=rewritten_operation,
                    creation_source_reference=rewritten_source,
                )
            )
            assert revision_result.rowcount == 1
            assert current_result.rowcount == 1
            self._coordination.critical_events.append(
                "binding_suffix_creation_provenance_rewritten"
            )
        await super().commit()


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_outcome",
    ("conflict", "exact-replay", "corrupt-family"),
    ids=("conflict", "exact-replay", "corrupt-family"),
)
async def test_mysql_lock_first_late_binding_observes_committed_canonical_family(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    expected_outcome: str,
) -> None:
    suffix = {
        "conflict": "late-conflict",
        "exact-replay": "late-replay",
        "corrupt-family": "late-corrupt-family",
    }[expected_outcome]
    outcome_code = {
        "conflict": "conf",
        "exact-replay": "repl",
        "corrupt-family": "corr",
    }[expected_outcome]
    character_principal = binding_scope.principal(
        f"{outcome_code}-character"
    )
    binding = binding_scope.binding(suffix)
    player_character_id = binding_scope.character_id(suffix)
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    resolver = _Resolver(character_principal, binding)
    coordination = _LateBindingCoordination()
    character_service = PlayerCharacterService(
        uow_factory=lambda: _LateBindingUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="character-create",
        ),
        controller_binding_resolver=resolver,
        player_character_id_issuer=_Issuer(player_character_id),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=CHARACTER_SOURCE,
        clock=lambda: NOW,
        binding_integrity_guard_enabled=True,
    )
    setup_service = RunService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(
            mysql_session_factory
        ),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RUN_SOURCE,
        clock=lambda: NOW,
        controller_binding_resolver=resolver,
        player_character_binding_evidence=character_service,
    )
    await _create_run(setup_service, binding_scope, suffix)
    attachment_principal = (
        binding_scope.principal(f"{outcome_code}-loser")
        if expected_outcome == "conflict"
        else character_principal
    )
    session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=f"{outcome_code}-attachment",
        principal=attachment_principal,
    )
    attachment_operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.attach-{suffix}"
    )
    attachment_command = AttachSessionCommand(
        run_id=run_id,
        continuous_story_line_id=line_id,
        session_id=session_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=RUN_SOURCE,
    )
    original_principal = attachment_principal
    original_command = attachment_command
    if expected_outcome == "conflict":
        original_principal = binding_scope.principal(
            f"{outcome_code}-winner"
        )
        original_session_id = await _add_session(
            mysql_session_factory,
            binding_scope,
            suffix=f"{outcome_code}-winner",
            principal=original_principal,
        )
        original_command = attachment_command.model_copy(
            update={"session_id": original_session_id}
        )
    else:
        original_session_id = session_id
    original_attachment_result = await setup_service.attach_session(
        original_principal,
        operation_id=attachment_operation_id,
        command=original_command,
    )
    assert not isinstance(
        original_attachment_result,
        (RunServiceDecision, RunReplayDecision),
    )
    assert (
        original_attachment_result.resulting_state_version
        == RunStateVersion(value=2)
    )

    attachment_service = RunService(
        uow_factory=lambda: _LateBindingUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="attachment",
            attachment=True,
        ),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RUN_SOURCE,
        clock=lambda: NOW,
        controller_binding_resolver=resolver,
        player_character_binding_evidence=character_service,
    )
    attachment_task = asyncio.create_task(
        attachment_service.attach_session(
            attachment_principal,
            operation_id=attachment_operation_id,
            command=attachment_command,
        )
    )
    try:
        await asyncio.wait_for(
            coordination.run_lock_requested.wait(),
            timeout=TIMEOUT,
        )
        async with mysql_session_factory() as session:
            revision_count_before_binding = await session.scalar(
                sa.select(sa.func.count())
                .select_from(PlayerCharacterRevisionRow)
                .where(
                    PlayerCharacterRevisionRow.player_character_id
                    == player_character_id.value
                )
            )
        assert revision_count_before_binding == 0

        await character_service.create(
            character_principal,
            operation_id=PlayerCharacterOperationId(
                value=(
                    f"operation.{binding_scope.token}."
                    f"create-character-{suffix}"
                )
            ),
            command=CharacterCreationCommand(
                contract_version=PlayerCharacterContractVersion.V1,
                character_core=CharacterCore(),
                narration_preferences=NarrationPreferences(),
            ),
        )
        coordination.critical_events.append(
            "player_character_creation_committed"
        )
        async with SqlAlchemyUnitOfWork(
            mysql_session_factory
        ) as uow:
            record = await uow.player_characters.get(
                player_character_id
            )
        assert record is not None
        character = _Character(
            principal=character_principal,
            binding=binding,
            record=record,
            resolver=resolver,
            service=character_service,
        )
        binding_service = _run_service(
            mysql_session_factory,
            run_id=run_id,
            line_id=line_id,
            character=character,
            uow_factory=lambda: _LateBindingUnitOfWork(
                mysql_session_factory,
                coordination=coordination,
                role="binding",
                corrupt_run_id=(
                    run_id
                    if expected_outcome == "corrupt-family"
                    else None
                ),
                corrupt_state_version=(
                    3
                    if expected_outcome == "corrupt-family"
                    else None
                ),
            ),
        )
        binding_result = (
            await binding_service.bind_player_character_internal(
                character_principal,
                operation_id=RunOperationId(
                    value=(
                        f"operation.{binding_scope.token}.bind-{suffix}"
                    )
                ),
                command=BindPlayerCharacterCommand(
                    run_id=run_id,
                    continuous_story_line_id=line_id,
                    target_player_character_id=player_character_id,
                    expected_state_version=RunStateVersion(value=2),
                    source_reference=RUN_SOURCE,
                ),
            )
        )
        assert not isinstance(
            binding_result,
            (RunServiceDecision, RunReplayDecision),
        )
        coordination.critical_events.append("binding_committed")
        coordination.binding_committed.set()
        attachment_result = None
        attachment_failure = None
        try:
            attachment_result = await asyncio.wait_for(
                attachment_task,
                timeout=TIMEOUT,
            )
        except RunStoredRecordIntegrityError as exc:
            attachment_failure = exc
            if expected_outcome != "corrupt-family":
                raise AssertionError(
                    "valid late binding family failed integrity; "
                    f"{coordination.diagnostics()}; "
                    f"failure={type(exc).__name__}: {exc}"
                ) from exc
        except (RunRepositoryError, OperationalError) as exc:
            raise AssertionError(
                "late binding attachment escaped as infrastructure failure; "
                f"{coordination.diagnostics()}; "
                f"failure={type(exc).__name__}: {exc}"
            ) from exc
        except Exception as exc:
            raise AssertionError(
                "late binding attachment escaped as an unclassified failure; "
                f"{coordination.diagnostics()}; "
                f"failure={type(exc).__name__}: {exc}"
            ) from exc
    finally:
        coordination.binding_committed.set()
        if not attachment_task.done():
            attachment_task.cancel()
            await asyncio.gather(
                attachment_task,
                return_exceptions=True,
            )

    assert set(coordination.isolation_levels.values()) == {
        "REPEATABLE-READ"
    }
    assert coordination.connection_ids["attachment"] != (
        coordination.connection_ids["binding"]
    )
    expected_events = [
        "attachment_session_locked",
        "attachment_run_lock_requested",
        "player_character_creation_committed",
    ]
    if expected_outcome == "corrupt-family":
        expected_events.append(
            "binding_suffix_creation_provenance_rewritten"
        )
    expected_events.extend(
        [
            "binding_committed",
            "attachment_run_locked",
            "attachment_exact_immutable_revision_read",
            (
                "attachment_canonical_family_rejected"
                if expected_outcome == "corrupt-family"
                else "attachment_canonical_family_validated"
            ),
        ]
    )
    assert coordination.critical_events == expected_events
    assert coordination.run_locked.is_set()
    assert coordination.immutable_revision_read.is_set()
    assert coordination.critical_events.index(
        "binding_committed"
    ) < coordination.critical_events.index("attachment_run_locked")
    assert coordination.critical_events.index(
        "attachment_run_locked"
    ) < coordination.critical_events.index(
        "attachment_exact_immutable_revision_read"
    )
    if expected_outcome == "conflict":
        assert attachment_result == RunReplayDecision(
            code=RunReplayDecisionCode.CONFLICT
        )
    elif expected_outcome == "exact-replay":
        assert attachment_result == original_attachment_result
    else:
        assert expected_outcome == "corrupt-family"
        assert attachment_failure is not None
        assert attachment_result is None
        assert coordination.observed_current_version == 3
        assert (
            coordination.observed_creation_operation
            == "operation.rewritten-create"
        )
    assert coordination.attachment_rolled_back
    expected_version = 3
    expected_history = [
        (1, "CREATE"),
        (2, "ATTACH_SESSION"),
        (3, "BIND_PLAYER_CHARACTER"),
    ]
    expected_receipts = [
        (2, "run.attach-session/v1"),
        (3, "run.bind-player-character/v1"),
    ]
    expected_participation_count = 1

    async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
        final_character = await uow.player_characters.get(
            player_character_id
        )
        participation = (
            None
            if expected_outcome == "corrupt-family"
            else await uow.run_participations.get(
                original_session_id
            )
        )
        losing_participation = (
            None
            if (
                expected_outcome == "corrupt-family"
                or session_id == original_session_id
            )
            else await uow.run_participations.get(session_id)
        )
        final_run = (
            None
            if expected_outcome == "corrupt-family"
            else await uow.runs.get(run_id)
        )
    assert final_character is not None
    assert final_character.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert final_character.record_revision.value == 1
    if expected_outcome != "corrupt-family":
        assert final_run is not None
        assert final_run.state_version == RunStateVersion(
            value=expected_version
        )
        assert final_run.player_character_binding is not None
        assert (
            final_run.player_character_binding
            .applicable_character_reference
            == ApplicableCharacterReference(
                player_character_id=player_character_id,
                contract_version=PlayerCharacterContractVersion.V1,
                record_revision=final_character.record_revision,
            )
        )
    if expected_outcome != "corrupt-family":
        assert participation is not None
        assert losing_participation is None

    async with mysql_session_factory() as session:
        run_history = (
            await session.execute(
                sa.select(
                    RunRevisionRow.state_version,
                    RunRevisionRow.mutation_kind,
                )
                .where(RunRevisionRow.run_id == run_id.value)
                .order_by(RunRevisionRow.state_version)
            )
        ).all()
        run_receipts = (
            await session.execute(
                sa.select(
                    RunMutationReceiptRow.resulting_state_version,
                    RunMutationReceiptRow.operation_namespace,
                )
                .where(RunMutationReceiptRow.run_id == run_id.value)
                .order_by(
                    RunMutationReceiptRow.resulting_state_version
                )
            )
        ).all()
        participation_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(RunSessionParticipationRow)
            .where(
                RunSessionParticipationRow.run_id == run_id.value,
            )
        )
        character_revisions = (
            await session.execute(
                sa.select(
                    PlayerCharacterRevisionRow.record_revision,
                    PlayerCharacterRevisionRow.lifecycle,
                )
                .where(
                    PlayerCharacterRevisionRow.player_character_id
                    == player_character_id.value
                )
                .order_by(
                    PlayerCharacterRevisionRow.record_revision
                )
            )
        ).all()
        character_mutation_receipts = await session.scalar(
            sa.select(sa.func.count())
            .select_from(PlayerCharacterMutationReceiptRow)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == player_character_id.value
            )
        )
        current_row = (
            await session.execute(
                sa.select(
                    RunCurrentRow.state_version,
                    RunCurrentRow.creation_operation_id,
                    RunCurrentRow.creation_source_reference,
                    RunCurrentRow.binding_player_character_id,
                ).where(RunCurrentRow.run_id == run_id.value)
            )
        ).one()
        creation_provenance = (
            await session.execute(
                sa.select(
                    RunRevisionRow.state_version,
                    RunRevisionRow.creation_operation_id,
                    RunRevisionRow.creation_source_reference,
                )
                .where(RunRevisionRow.run_id == run_id.value)
                .order_by(RunRevisionRow.state_version)
            )
        ).all()

    assert run_history == expected_history
    assert run_receipts == expected_receipts
    assert participation_count == expected_participation_count
    assert character_revisions == [(1, "active")]
    assert character_mutation_receipts == 0
    assert current_row[0] == expected_version
    assert current_row[3] == player_character_id.value
    if expected_outcome == "corrupt-family":
        assert current_row[1:] == (
            "operation.rewritten-create",
            "source.rewritten-create",
            player_character_id.value,
        )
        assert creation_provenance == [
            (
                1,
                f"operation.{binding_scope.token}.create-run-{suffix}",
                RUN_SOURCE.value,
            ),
            (
                2,
                f"operation.{binding_scope.token}.create-run-{suffix}",
                RUN_SOURCE.value,
            ),
            (
                3,
                "operation.rewritten-create",
                "source.rewritten-create",
            ),
        ]


@dataclass(slots=True)
class _LateAttachmentReceiptCoordination:
    loser_run_lock_ready: asyncio.Event = field(
        default_factory=asyncio.Event
    )
    winner_committed: asyncio.Event = field(default_factory=asyncio.Event)
    connection_ids: dict[str, int] = field(default_factory=dict)
    isolation_levels: dict[str, str] = field(default_factory=dict)
    critical_events: list[str] = field(default_factory=list)
    loser_current_version: int | None = None
    loser_current_receipt_version: int | None = None
    loser_rolled_back: bool = False

    def diagnostics(self) -> str:
        return (
            "loser_run_lock_ready="
            f"{self.loser_run_lock_ready.is_set()}, "
            f"winner_committed={self.winner_committed.is_set()}, "
            f"connection_ids={self.connection_ids}, "
            f"isolation_levels={self.isolation_levels}, "
            f"critical_events={self.critical_events}, "
            f"loser_current_version={self.loser_current_version}, "
            "loser_current_receipt_version="
            f"{self.loser_current_receipt_version}, "
            f"loser_rolled_back={self.loser_rolled_back}"
        )


class _LateAttachmentReceiptSessionRepository(
    SqlAlchemyGameSessionRepository
):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LateAttachmentReceiptCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ):
        result = await super().get_owned_for_update(
            session_id,
            player_id,
        )
        assert result is not None
        self._coordination.critical_events.append(
            "loser_session_locked"
        )
        return result


class _LateAttachmentReceiptRepository(
    SqlAlchemyRunMutationReceiptRepository
):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LateAttachmentReceiptCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get(self, key):
        raise AssertionError(
            "attachment must not perform a pre-Run receipt read"
        )


class _LateAttachmentReceiptRunRepository(SqlAlchemyRunRepository):
    def __init__(
        self,
        session: AsyncSession,
        coordination: _LateAttachmentReceiptCoordination,
    ) -> None:
        super().__init__(session)
        self._coordination = coordination

    async def get(self, run_id: RunId):
        raise AssertionError(
            "attachment must not perform nonlocking Run discovery"
        )

    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key,
    ):
        self._coordination.critical_events.append(
            "loser_run_lock_ready"
        )
        self._coordination.loser_run_lock_ready.set()
        await asyncio.wait_for(
            self._coordination.winner_committed.wait(),
            timeout=TIMEOUT,
        )
        result = await super().get_session_attachment_lock_evidence(
            run_id,
            receipt_key=receipt_key,
        )
        assert result is not None
        assert result.canonical_run.player_character_binding is None
        assert result.attachment_receipt is not None
        self._coordination.loser_current_receipt_version = (
            result.attachment_receipt.result.resulting_state_version.value
        )
        self._coordination.critical_events.append(
            "loser_current_receipt_version_2"
        )
        self._coordination.loser_current_version = (
            result.canonical_run.state_version.value
        )
        self._coordination.critical_events.append(
            "loser_current_run_version_2"
        )
        return result

    async def get_for_update(self, run_id: RunId):
        raise AssertionError(
            "attachment carrier must own the only current Run lock"
        )


class _LateAttachmentReceiptUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        coordination: _LateAttachmentReceiptCoordination,
        role: str,
    ) -> None:
        super().__init__(factory)
        self._coordination = coordination
        self._role = role

    async def __aenter__(self) -> "_LateAttachmentReceiptUnitOfWork":
        await super().__aenter__()
        assert self._session is not None
        connection_id = await self._session.scalar(
            sa.text("SELECT CONNECTION_ID()")
        )
        isolation_level = await self._session.scalar(
            sa.text("SELECT @@transaction_isolation")
        )
        assert connection_id is not None
        assert isolation_level is not None
        self._coordination.connection_ids[self._role] = int(
            connection_id
        )
        self._coordination.isolation_levels[self._role] = str(
            isolation_level
        )
        if self._role == "loser":
            self.sessions = _LateAttachmentReceiptSessionRepository(
                self._session,
                self._coordination,
            )
            self.runs = _LateAttachmentReceiptRunRepository(
                self._session,
                self._coordination,
            )
            self.run_mutation_receipts = (
                _LateAttachmentReceiptRepository(
                    self._session,
                    self._coordination,
                )
            )
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await super().__aexit__(exc_type, exc, traceback)
        if self._role == "loser" and not self._committed:
            self._coordination.loser_rolled_back = True
            self._coordination.critical_events.append(
                "loser_rolled_back"
            )

    async def commit(self) -> None:
        await super().commit()
        if self._role == "winner":
            self._coordination.critical_events.append(
                "winner_committed"
            )
            self._coordination.winner_committed.set()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_late_conflicting_attachment_receipt_precedes_stale_version(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    suffix = "late-receipt"
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    setup_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(setup_service, binding_scope, suffix)
    loser_principal = binding_scope.principal(f"{suffix}-loser")
    winner_principal = binding_scope.principal(f"{suffix}-winner")
    loser_session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=f"{suffix}-loser",
        principal=loser_principal,
    )
    winner_session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=f"{suffix}-winner",
        principal=winner_principal,
    )
    operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.attach-{suffix}"
    )
    loser_command = AttachSessionCommand(
        run_id=run_id,
        continuous_story_line_id=line_id,
        session_id=loser_session_id,
        expected_state_version=RunStateVersion(value=1),
        source_reference=RUN_SOURCE,
    )
    winner_command = loser_command.model_copy(
        update={"session_id": winner_session_id}
    )
    _, loser_fingerprint = attach_session_fingerprint(
        loser_command,
        operation_id=operation_id,
    )
    _, winner_fingerprint = attach_session_fingerprint(
        winner_command,
        operation_id=operation_id,
    )
    assert loser_fingerprint != winner_fingerprint
    coordination = _LateAttachmentReceiptCoordination()
    loser_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _LateAttachmentReceiptUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="loser",
        ),
    )
    winner_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _LateAttachmentReceiptUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="winner",
        ),
    )
    loser_task = asyncio.create_task(
        loser_service.attach_session(
            loser_principal,
            operation_id=operation_id,
            command=loser_command,
        )
    )
    try:
        await asyncio.wait_for(
            coordination.loser_run_lock_ready.wait(),
            timeout=TIMEOUT,
        )
        try:
            winner_result = await asyncio.wait_for(
                winner_service.attach_session(
                    winner_principal,
                    operation_id=operation_id,
                    command=winner_command,
                ),
                timeout=TIMEOUT,
            )
        except (
            RunStoredRecordIntegrityError,
            RunRepositoryError,
            OperationalError,
        ) as exc:
            raise AssertionError(
                "winner escaped as an infrastructure failure; "
                f"{coordination.diagnostics()}; "
                f"failure={type(exc).__name__}: {exc}"
            ) from exc
        try:
            loser_result = await asyncio.wait_for(
                loser_task,
                timeout=TIMEOUT,
            )
        except (
            RunStoredRecordIntegrityError,
            RunRepositoryError,
            OperationalError,
        ) as exc:
            raise AssertionError(
                "late receipt loser escaped as an infrastructure failure; "
                f"{coordination.diagnostics()}; "
                f"failure={type(exc).__name__}: {exc}"
            ) from exc
    except TimeoutError as exc:
        raise AssertionError(
            "late attachment receipt race timed out; "
            f"{coordination.diagnostics()}"
        ) from exc
    finally:
        coordination.winner_committed.set()
        if not loser_task.done():
            loser_task.cancel()
            await asyncio.gather(loser_task, return_exceptions=True)

    assert not isinstance(winner_result, RunServiceDecision)
    assert not isinstance(winner_result, RunReplayDecision)
    assert winner_result.resulting_state_version == RunStateVersion(
        value=2
    )
    assert loser_result == RunReplayDecision(
        code=RunReplayDecisionCode.CONFLICT
    )
    assert loser_result.code is not RunReplayDecisionCode.REPLAY
    assert set(coordination.connection_ids) == {"loser", "winner"}
    assert len(set(coordination.connection_ids.values())) == 2
    assert set(coordination.isolation_levels.values()) == {
        "REPEATABLE-READ"
    }
    assert coordination.loser_current_version == 2
    assert coordination.loser_current_receipt_version == 2
    assert coordination.loser_rolled_back
    assert coordination.critical_events == [
        "loser_session_locked",
        "loser_run_lock_ready",
        "winner_committed",
        "loser_current_receipt_version_2",
        "loser_current_run_version_2",
        "loser_rolled_back",
    ]

    async with mysql_session_factory() as session:
        current = await session.scalar(
            sa.select(RunCurrentRow).where(
                RunCurrentRow.run_id == run_id.value
            )
        )
        history = (
            await session.execute(
                sa.select(
                    RunRevisionRow.state_version,
                    RunRevisionRow.mutation_kind,
                    RunRevisionRow.operation_id,
                )
                .where(RunRevisionRow.run_id == run_id.value)
                .order_by(RunRevisionRow.state_version)
            )
        ).all()
        receipts = (
            await session.execute(
                sa.select(
                    RunMutationReceiptRow.operation_id,
                    RunMutationReceiptRow.expected_state_version,
                    RunMutationReceiptRow.resulting_state_version,
                    RunMutationReceiptRow.participation_session_id,
                ).where(
                    RunMutationReceiptRow.run_id == run_id.value
                )
            )
        ).all()
        participations = (
            await session.execute(
                sa.select(
                    RunSessionParticipationRow.session_id,
                    RunSessionParticipationRow.joined_state_version,
                    RunSessionParticipationRow.operation_id,
                ).where(
                    RunSessionParticipationRow.run_id == run_id.value
                )
            )
        ).all()
        creation_receipt_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(RunCreationReceiptRow)
            .where(RunCreationReceiptRow.result_run_id == run_id.value)
        )

    assert current is not None
    assert current.state_version == 2
    assert current.binding_player_character_id is None
    assert current.active_player_character_id is None
    assert history == [
        (
            1,
            "CREATE",
            f"operation.{binding_scope.token}.create-run-{suffix}",
        ),
        (2, "ATTACH_SESSION", operation_id.value),
    ]
    assert receipts == [
        (operation_id.value, 1, 2, winner_session_id)
    ]
    assert participations == [
        (winner_session_id, 2, operation_id.value)
    ]
    assert all(row[0] != loser_session_id for row in participations)
    assert creation_receipt_count == 1
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)


async def _assert_attached_bound_state(
    factory: async_sessionmaker[AsyncSession],
    *,
    character: _Character,
    run_id: RunId,
    session_id: str,
) -> None:
    async with SqlAlchemyUnitOfWork(factory) as uow:
        current_character = await uow.player_characters.get(
            character.record.player_character_id
        )
        current_run = await uow.runs.get(run_id)
        participation = await uow.run_participations.get(session_id)
    assert current_character is not None
    assert current_character.lifecycle is PlayerCharacterLifecycle.ACTIVE
    assert current_character.record_revision == character.record.record_revision
    assert current_run is not None
    assert current_run.state_version == RunStateVersion(value=3)
    assert current_run.player_character_binding is not None
    assert (
        current_run.player_character_binding.applicable_character_reference
        == ApplicableCharacterReference(
            player_character_id=character.record.player_character_id,
            contract_version=character.record.contract_version,
            record_revision=character.record.record_revision,
        )
    )
    assert tuple(
        item.session_id
        for item in current_run.trusted_participation_references
    ) == (session_id,)
    assert participation == current_run.trusted_participation_references[0]
    assert await _run_family_counts(factory, run_id) == (3, 1, 1, 2)

    async with factory() as session:
        run_history = (
            await session.execute(
                sa.select(
                    RunRevisionRow.state_version,
                    RunRevisionRow.mutation_kind,
                )
                .where(RunRevisionRow.run_id == run_id.value)
                .order_by(RunRevisionRow.state_version)
            )
        ).all()
        run_receipts = (
            await session.execute(
                sa.select(
                    RunMutationReceiptRow.resulting_state_version,
                    RunMutationReceiptRow.operation_namespace,
                )
                .where(RunMutationReceiptRow.run_id == run_id.value)
                .order_by(
                    RunMutationReceiptRow.resulting_state_version
                )
            )
        ).all()
        player_character_counts = []
        for row_type in (
            PlayerCharacterRevisionRow,
            PlayerCharacterCurrentRow,
            PlayerCharacterCreationReceiptRow,
            PlayerCharacterMutationReceiptRow,
        ):
            column = (
                row_type.result_player_character_id
                if row_type is PlayerCharacterCreationReceiptRow
                else row_type.player_character_id
            )
            player_character_counts.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count())
                        .select_from(row_type)
                        .where(
                            column
                            == character.record.player_character_id.value
                        )
                    )
                    or 0
                )
            )
        session_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(GameSessionRow)
            .where(GameSessionRow.session_id == session_id)
        )
        participation_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(RunSessionParticipationRow)
            .where(
                RunSessionParticipationRow.session_id == session_id,
                RunSessionParticipationRow.run_id == run_id.value,
            )
        )

    assert run_history == [
        (1, "CREATE"),
        (2, "BIND_PLAYER_CHARACTER"),
        (3, "ATTACH_SESSION"),
    ]
    assert run_receipts == [
        (2, "run.bind-player-character/v1"),
        (3, "run.attach-session/v1"),
    ]
    assert player_character_counts == [1, 1, 1, 0]
    assert session_count == 1
    assert participation_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_binding_success_reload_exact_replay_conflict_and_fk(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        "round-trip",
    )
    run_id = binding_scope.run_id("round-trip")
    line_id = binding_scope.line_id("round-trip")
    service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(service, binding_scope, "round-trip")
    operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.bind-round-trip"
    )
    command = _bind_command(
        run_id=run_id,
        line_id=line_id,
        character=character,
    )

    result = await service.bind_player_character_internal(
        character.principal,
        operation_id=operation_id,
        command=command,
    )

    assert result.resulting_state_version == RunStateVersion(value=2)
    assert result.applicable_character_reference == (
        ApplicableCharacterReference(
            player_character_id=character.record.player_character_id,
            contract_version=character.record.contract_version,
            record_revision=character.record.record_revision,
        )
    )
    reloaded = await service.get_run(run_id=run_id)
    assert reloaded is not None
    assert reloaded.player_character_binding is not None
    assert (
        reloaded.player_character_binding.applicable_character_reference
        == result.applicable_character_reference
    )
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)

    replay = await service.bind_player_character_internal(
        character.principal,
        operation_id=operation_id,
        command=command,
    )
    assert replay == result
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)

    conflict = await service.bind_player_character_internal(
        character.principal,
        operation_id=operation_id,
        command=command.model_copy(
            update={"expected_state_version": RunStateVersion(value=2)}
        ),
    )
    assert isinstance(conflict, RunReplayDecision)
    assert conflict.code is RunReplayDecisionCode.CONFLICT
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)

    async with mysql_session_factory.begin() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                sa.delete(PlayerCharacterRevisionRow).where(
                    PlayerCharacterRevisionRow.player_character_id
                    == character.record.player_character_id.value,
                    PlayerCharacterRevisionRow.record_revision
                    == character.record.record_revision.value,
                )
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_bound_run_reconstruction_does_not_lock_referenced_player_character_revision(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        "revision-lock-probe",
    )
    run_id = binding_scope.run_id("revision-lock-probe")
    line_id = binding_scope.line_id("revision-lock-probe")
    service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(service, binding_scope, "revision-lock-probe")
    await service.bind_player_character_internal(
        character.principal,
        operation_id=RunOperationId(
            value=f"operation.{binding_scope.token}.bind-revision-lock-probe"
        ),
        command=_bind_command(
            run_id=run_id,
            line_id=line_id,
            character=character,
        ),
    )

    holder = mysql_session_factory()
    reader = mysql_session_factory()
    reader_task: asyncio.Task[Any] | None = None
    holder_connection_id: int | None = None
    reader_connection_id: int | None = None
    try:
        await holder.begin()
        await reader.begin()
        holder_connection_id = int(
            await holder.scalar(sa.text("SELECT CONNECTION_ID()"))
        )
        reader_connection_id = int(
            await reader.scalar(sa.text("SELECT CONNECTION_ID()"))
        )
        assert holder_connection_id != reader_connection_id
        locked_revision = await holder.scalar(
            sa.select(PlayerCharacterRevisionRow)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == character.record.player_character_id.value,
                PlayerCharacterRevisionRow.record_revision
                == character.record.record_revision.value,
            )
            .with_for_update()
        )
        assert locked_revision is not None
        assert holder.in_transaction()

        repository = SqlAlchemyRunRepository(reader)
        reader_task = asyncio.create_task(
            repository.get_for_update(run_id)
        )
        try:
            reconstructed = await asyncio.wait_for(
                reader_task,
                timeout=LOCK_PROBE_TIMEOUT,
            )
        except TimeoutError as exc:
            reader_task.cancel()
            await asyncio.gather(reader_task, return_exceptions=True)
            raise AssertionError(
                "bound Run reconstruction waited on the immutable "
                "Player Character revision lock after acquiring the Run lock; "
                f"holder_connection_id={holder_connection_id}, "
                f"reader_connection_id={reader_connection_id}, "
                f"run_id={run_id.value}"
            ) from exc

        assert reconstructed is not None
        assert reconstructed.player_character_binding is not None
        assert (
            reconstructed.player_character_binding
            .applicable_character_reference
            == ApplicableCharacterReference(
                player_character_id=character.record.player_character_id,
                contract_version=character.record.contract_version,
                record_revision=character.record.record_revision,
            )
        )
        assert holder.in_transaction()
    finally:
        if reader_task is not None and not reader_task.done():
            reader_task.cancel()
            await asyncio.gather(reader_task, return_exceptions=True)
        if reader.in_transaction():
            await reader.rollback()
        if holder.in_transaction():
            await holder.rollback()
        await reader.close()
        await holder.close()


class _RollbackProbeUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        rollbacks: list[bool],
    ) -> None:
        super().__init__(factory)
        self._rollbacks = rollbacks

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await super().__aexit__(exc_type, exc, traceback)
        self._rollbacks.append(not self._committed)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "corruption",
    ("malformed", "missing", "mismatched"),
    ids=(
        "malformed-actual-revision",
        "missing-actual-revision",
        "mismatched-actual-revision",
    ),
)
async def test_mysql_attachment_fails_closed_on_actual_referenced_revision_corruption(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    corruption: str,
) -> None:
    suffix = {
        "malformed": "actual-mal",
        "missing": "actual-mis",
        "mismatched": "actual-mat",
    }[corruption]
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    normal_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(normal_service, binding_scope, suffix)
    await normal_service.bind_player_character_internal(
        character.principal,
        operation_id=RunOperationId(
            value=f"operation.{binding_scope.token}.bind-{suffix}"
        ),
        command=_bind_command(
            run_id=run_id,
            line_id=line_id,
            character=character,
        ),
    )
    session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=suffix,
        principal=character.principal,
    )

    if corruption == "missing":
        async with mysql_session_factory() as session:
            await session.execute(
                sa.text("SET FOREIGN_KEY_CHECKS = 0")
            )
            try:
                result = await session.execute(
                    sa.delete(PlayerCharacterRevisionRow).where(
                        PlayerCharacterRevisionRow.player_character_id
                        == character.record.player_character_id.value,
                        PlayerCharacterRevisionRow.record_revision
                        == character.record.record_revision.value,
                    )
                )
                assert result.rowcount == 1
                await session.commit()
            finally:
                if session.in_transaction():
                    await session.rollback()
                await session.execute(
                    sa.text("SET FOREIGN_KEY_CHECKS = 1")
                )
                await session.commit()
    else:
        record_canonical = b"{"
        if corruption == "mismatched":
            other_record = CreatePlayerCharacterPolicy().create(
                player_character_id=PlayerCharacterId(
                    value=f"pc.mismatch-{binding_scope.token}"
                ),
                controller_binding=ControllerBindingRef(
                    value=f"binding.mismatch-{binding_scope.token}"
                ),
                character_core=CharacterCore(),
                narration_preferences=NarrationPreferences(),
                source_reference=AuthoritySourceRef(
                    value=f"source.mismatch-{binding_scope.token}"
                ),
            )
            record_canonical = (
                SqlAlchemyPlayerCharacterRepository._revision_row(
                    other_record,
                    created_at=NOW,
                ).record_canonical
            )
        async with mysql_session_factory.begin() as session:
            result = await session.execute(
                sa.update(PlayerCharacterRevisionRow)
                .where(
                    PlayerCharacterRevisionRow.player_character_id
                    == character.record.player_character_id.value,
                    PlayerCharacterRevisionRow.record_revision
                    == character.record.record_revision.value,
                )
                .values(record_canonical=record_canonical)
            )
            assert result.rowcount == 1

    rollbacks: list[bool] = []
    service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _RollbackProbeUnitOfWork(
            mysql_session_factory,
            rollbacks,
        ),
    )
    operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.attach-{suffix}"
    )

    with pytest.raises(RunStoredRecordIntegrityError):
        await service.attach_session(
            character.principal,
            operation_id=operation_id,
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=2),
                source_reference=RUN_SOURCE,
            ),
        )

    assert rollbacks == [True]
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)
    async with mysql_session_factory() as session:
        current_version = await session.scalar(
            sa.select(RunCurrentRow.state_version).where(
                RunCurrentRow.run_id == run_id.value
            )
        )
        participation_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(RunSessionParticipationRow)
            .where(
                RunSessionParticipationRow.session_id == session_id
            )
        )
        attachment_receipt_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(RunMutationReceiptRow)
            .where(
                RunMutationReceiptRow.run_id == run_id.value,
                RunMutationReceiptRow.operation_id
                == operation_id.value,
            )
        )

    assert current_version == 2
    assert participation_count == 0
    assert attachment_receipt_count == 0


class _PreCommitFailureUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("controlled binding pre-COMMIT failure")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_binding_commit_failure_rolls_back_and_does_not_guard_lifecycle(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        "rollback",
    )
    run_id = binding_scope.run_id("rollback")
    line_id = binding_scope.line_id("rollback")
    normal = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(normal, binding_scope, "rollback")
    failing = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_type=_PreCommitFailureUnitOfWork,
    )

    with pytest.raises(RuntimeError, match="pre-COMMIT"):
        await failing.bind_player_character_internal(
            character.principal,
            operation_id=RunOperationId(
                value=f"operation.{binding_scope.token}.bind-rollback"
            ),
            command=_bind_command(
                run_id=run_id,
                line_id=line_id,
                character=character,
            ),
        )

    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (1, 1, 1, 0)
    reloaded = await normal.get_run(run_id=run_id)
    assert reloaded is not None
    assert reloaded.player_character_binding is None

    operation_id, command = _lifecycle_command(
        character,
        kind=PlayerCharacterMutationKind.RETIRE,
        suffix=f"{binding_scope.token}-rollback",
    )
    retired = await character.service.mutate(
        character.principal,
        operation_id=operation_id,
        command=command,
    )
    assert not isinstance(retired, PlayerCharacterPolicyDecision)
    assert retired.resulting_lifecycle is PlayerCharacterLifecycle.RETIRED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_bound_character_guards_retire_and_final_death_without_writes(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        "guards",
    )
    run_id = binding_scope.run_id("guards")
    line_id = binding_scope.line_id("guards")
    service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(service, binding_scope, "guards")
    await service.bind_player_character_internal(
        character.principal,
        operation_id=RunOperationId(
            value=f"operation.{binding_scope.token}.bind-guards"
        ),
        command=_bind_command(
            run_id=run_id,
            line_id=line_id,
            character=character,
        ),
    )

    for kind in (
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.FINAL_DEATH,
    ):
        operation_id, command = _lifecycle_command(
            character,
            kind=kind,
            suffix=f"{binding_scope.token}-{kind.value}",
        )
        decision = await character.service.mutate(
            character.principal,
            operation_id=operation_id,
            command=command,
        )
        assert decision == PlayerCharacterPolicyDecision(
            code=(
                PlayerCharacterPolicyCode
                .ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
            )
        )

    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)
    async with mysql_session_factory() as session:
        character_revision_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(PlayerCharacterRevisionRow)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == character.record.player_character_id.value
            )
        )
        mutation_receipt_count = await session.scalar(
            sa.select(sa.func.count())
            .select_from(PlayerCharacterMutationReceiptRow)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == character.record.player_character_id.value
            )
        )
    assert character_revision_count == 1
    assert mutation_receipt_count == 0


class _HoldingBindingEvidence:
    def __init__(self, delegate: PlayerCharacterService) -> None:
        self.delegate = delegate
        self.locked = asyncio.Event()
        self.release = asyncio.Event()

    async def lock_owned_for_binding(self, uow, **kwargs):
        evidence = await self.delegate.lock_owned_for_binding(
            uow,
            **kwargs,
        )
        self.locked.set()
        await self.release.wait()
        return evidence


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    (
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.FINAL_DEATH,
    ),
)
async def test_mysql_bind_serializes_before_guarded_lifecycle_mutation(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    kind: PlayerCharacterMutationKind,
) -> None:
    suffix = f"race-{kind.value}"
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    holding = _HoldingBindingEvidence(character.service)
    service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        evidence=holding,
    )
    await _create_run(service, binding_scope, suffix)
    bind_task = asyncio.create_task(
        service.bind_player_character_internal(
            character.principal,
            operation_id=RunOperationId(
                value=f"operation.{binding_scope.token}.bind-{suffix}"
            ),
            command=_bind_command(
                run_id=run_id,
                line_id=line_id,
                character=character,
            ),
        )
    )
    await asyncio.wait_for(holding.locked.wait(), timeout=TIMEOUT)
    operation_id, command = _lifecycle_command(
        character,
        kind=kind,
        suffix=f"{binding_scope.token}-{suffix}",
    )
    lifecycle_task = asyncio.create_task(
        character.service.mutate(
            character.principal,
            operation_id=operation_id,
            command=command,
        )
    )
    holding.release.set()
    bound_result, lifecycle_result = await asyncio.wait_for(
        asyncio.gather(bind_task, lifecycle_task),
        timeout=TIMEOUT,
    )

    assert bound_result.resulting_state_version == RunStateVersion(value=2)
    assert lifecycle_result == PlayerCharacterPolicyDecision(
        code=(
            PlayerCharacterPolicyCode
            .ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
        )
    )
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    (
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.FINAL_DEATH,
    ),
)
async def test_mysql_attach_on_bound_run_serializes_with_guarded_lifecycle_mutation(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    kind: PlayerCharacterMutationKind,
) -> None:
    suffix = f"attach-vs-{kind.value}"
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    normal_run_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(normal_run_service, binding_scope, suffix)
    await normal_run_service.bind_player_character_internal(
        character.principal,
        operation_id=RunOperationId(
            value=f"operation.{binding_scope.token}.bind-{suffix}"
        ),
        command=_bind_command(
            run_id=run_id,
            line_id=line_id,
            character=character,
        ),
    )
    session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=suffix,
        principal=character.principal,
    )
    coordination = _LockOrderCoordination()
    lifecycle_service = PlayerCharacterService(
        uow_factory=lambda: _CoordinatedUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="lifecycle",
            run_repository_kind="lifecycle",
        ),
        controller_binding_resolver=character.resolver,
        player_character_id_issuer=_Issuer(
            character.record.player_character_id
        ),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=CHARACTER_SOURCE,
        clock=lambda: NOW,
        binding_integrity_guard_enabled=True,
    )
    attach_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _CoordinatedUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="attach",
            run_repository_kind="attach",
        ),
    )
    lifecycle_operation_id, lifecycle_command = _lifecycle_command(
        character,
        kind=kind,
        suffix=f"{binding_scope.token}-{suffix}",
    )
    lifecycle_task = asyncio.create_task(
        lifecycle_service.mutate(
            character.principal,
            operation_id=lifecycle_operation_id,
            command=lifecycle_command,
        )
    )
    await asyncio.wait_for(
        coordination.player_character_locked.wait(),
        timeout=TIMEOUT,
    )
    attach_task = asyncio.create_task(
        attach_service.attach_session(
            character.principal,
            operation_id=RunOperationId(
                value=f"operation.{binding_scope.token}.attach-{suffix}"
            ),
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=2),
                source_reference=RUN_SOURCE,
            ),
        )
    )

    lifecycle_result, attach_result = await _finish_concurrent_pair(
        label=f"attach versus {kind.value}",
        coordination=coordination,
        first=lifecycle_task,
        second=attach_task,
    )

    assert coordination.connection_ids.keys() == {
        "lifecycle",
        "attach",
    }
    assert len(set(coordination.connection_ids.values())) == 2
    assert coordination.critical_events == [
        "lifecycle_player_character_locked",
        "attach_run_requested",
        "lifecycle_run_locked",
        "attach_run_locked",
    ]
    assert lifecycle_result == PlayerCharacterPolicyDecision(
        code=(
            PlayerCharacterPolicyCode
            .ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
        )
    )
    assert not isinstance(attach_result, RunServiceDecision)
    assert not isinstance(attach_result, RunReplayDecision)
    assert attach_result.resulting_state_version == RunStateVersion(value=3)
    assert attach_result.participation_reference is not None
    assert attach_result.participation_reference.session_id == session_id
    await _assert_attached_bound_state(
        mysql_session_factory,
        character=character,
        run_id=run_id,
        session_id=session_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_identical_binding_replay_serializes_with_attach_on_bound_run(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    suffix = "replay-vs-attach"
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    normal_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(normal_service, binding_scope, suffix)
    binding_operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.bind-{suffix}"
    )
    binding_command = _bind_command(
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    original_binding_result = (
        await normal_service.bind_player_character_internal(
            character.principal,
            operation_id=binding_operation_id,
            command=binding_command,
        )
    )
    session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=suffix,
        principal=character.principal,
    )
    coordination = _LockOrderCoordination()
    replay_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        evidence=_CoordinatedBindingEvidence(
            character.service,
            coordination,
        ),
        uow_factory=lambda: _CoordinatedUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="binding-replay",
            run_repository_kind="record-only",
        ),
    )
    attach_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _CoordinatedUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="attach",
            run_repository_kind="attach",
        ),
    )
    replay_task = asyncio.create_task(
        replay_service.bind_player_character_internal(
            character.principal,
            operation_id=binding_operation_id,
            command=binding_command,
        )
    )
    await asyncio.wait_for(
        coordination.player_character_locked.wait(),
        timeout=TIMEOUT,
    )
    attach_task = asyncio.create_task(
        attach_service.attach_session(
            character.principal,
            operation_id=RunOperationId(
                value=f"operation.{binding_scope.token}.attach-{suffix}"
            ),
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=2),
                source_reference=RUN_SOURCE,
            ),
        )
    )

    replay_result, attach_result = await _finish_concurrent_pair(
        label="identical binding replay versus attach",
        coordination=coordination,
        first=replay_task,
        second=attach_task,
    )

    assert coordination.connection_ids.keys() == {
        "binding-replay",
        "attach",
    }
    assert len(set(coordination.connection_ids.values())) == 2
    assert coordination.critical_events == [
        "binding_replay_player_character_locked",
        "attach_run_requested",
        "binding_replay_run_locked",
        "attach_run_locked",
    ]
    assert replay_result == original_binding_result
    assert not isinstance(attach_result, RunServiceDecision)
    assert not isinstance(attach_result, RunReplayDecision)
    assert attach_result.resulting_state_version == RunStateVersion(value=3)
    assert attach_result.participation_reference is not None
    assert attach_result.participation_reference.session_id == session_id
    await _assert_attached_bound_state(
        mysql_session_factory,
        character=character,
        run_id=run_id,
        session_id=session_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "player_character_operation",
    (
        "binding-replay",
        PlayerCharacterMutationKind.RETIRE,
        PlayerCharacterMutationKind.FINAL_DEATH,
    ),
    ids=("binding-replay", "retire", "final-death"),
)
async def test_mysql_inverse_attachment_then_player_character_order_has_no_fk_deadlock(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    player_character_operation: str | PlayerCharacterMutationKind,
) -> None:
    operation_label = (
        player_character_operation.value.lower()
        if isinstance(
            player_character_operation,
            PlayerCharacterMutationKind,
        )
        else player_character_operation
    )
    operation_code = {
        "binding-replay": "replay",
        "retire": "retire",
        "final_death": "death",
    }[operation_label]
    suffix = f"inv-fk-{operation_code}"
    character = await _create_character(
        mysql_session_factory,
        binding_scope,
        suffix,
    )
    run_id = binding_scope.run_id(suffix)
    line_id = binding_scope.line_id(suffix)
    setup_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    await _create_run(setup_service, binding_scope, suffix)
    binding_operation_id = RunOperationId(
        value=f"operation.{binding_scope.token}.bind-{suffix}"
    )
    binding_command = _bind_command(
        run_id=run_id,
        line_id=line_id,
        character=character,
    )
    original_binding_result = (
        await setup_service.bind_player_character_internal(
            character.principal,
            operation_id=binding_operation_id,
            command=binding_command,
        )
    )
    assert not isinstance(
        original_binding_result,
        (RunServiceDecision, RunReplayDecision),
    )

    session_id = await _add_session(
        mysql_session_factory,
        binding_scope,
        suffix=suffix,
        principal=character.principal,
    )
    coordination = _InverseForeignKeyDeadlockCoordination()
    attachment_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=character,
        uow_factory=lambda: _InverseForeignKeyDeadlockUnitOfWork(
            mysql_session_factory,
            coordination=coordination,
            role="attachment",
        ),
    )
    attachment_task = asyncio.create_task(
        attachment_service.attach_session(
            character.principal,
            operation_id=RunOperationId(
                value=f"operation.{binding_scope.token}.attach-{suffix}"
            ),
            command=AttachSessionCommand(
                run_id=run_id,
                continuous_story_line_id=line_id,
                session_id=session_id,
                expected_state_version=RunStateVersion(value=2),
                source_reference=RUN_SOURCE,
            ),
        )
    )
    player_character_task: asyncio.Task[Any] | None = None
    try:
        await asyncio.wait_for(
            coordination.attachment_before_revision_flush.wait(),
            timeout=TIMEOUT,
        )
        assert coordination.attachment_session_locked.is_set()
        assert coordination.attachment_run_family_locked.is_set()

        player_character_uow_factory = (
            lambda: _InverseForeignKeyDeadlockUnitOfWork(
                mysql_session_factory,
                coordination=coordination,
                role="player-character",
            )
        )
        if player_character_operation == "binding-replay":
            player_character_service = _run_service(
                mysql_session_factory,
                run_id=run_id,
                line_id=line_id,
                character=character,
                uow_factory=player_character_uow_factory,
            )
            player_character_task = asyncio.create_task(
                player_character_service.bind_player_character_internal(
                    character.principal,
                    operation_id=binding_operation_id,
                    command=binding_command,
                )
            )
        else:
            assert isinstance(
                player_character_operation,
                PlayerCharacterMutationKind,
            )
            lifecycle_service = PlayerCharacterService(
                uow_factory=player_character_uow_factory,
                controller_binding_resolver=character.resolver,
                player_character_id_issuer=_Issuer(
                    character.record.player_character_id
                ),
                create_policy=CreatePlayerCharacterPolicy(),
                source_reference=CHARACTER_SOURCE,
                clock=lambda: NOW,
                binding_integrity_guard_enabled=True,
            )
            lifecycle_operation_id, lifecycle_command = _lifecycle_command(
                character,
                kind=player_character_operation,
                suffix=f"{binding_scope.token}-{suffix}",
            )
            player_character_task = asyncio.create_task(
                lifecycle_service.mutate(
                    character.principal,
                    operation_id=lifecycle_operation_id,
                    command=lifecycle_command,
                )
            )

        await asyncio.wait_for(
            coordination.player_character_family_locked.wait(),
            timeout=TIMEOUT,
        )
        await asyncio.wait_for(
            coordination.player_character_run_lock_requested.wait(),
            timeout=TIMEOUT,
        )
        assert set(coordination.connection_ids) == {
            "attachment",
            "player-character",
        }
        assert len(set(coordination.connection_ids.values())) == 2
        assert not coordination.player_character_run_lock_acquired.is_set()
        assert not player_character_task.done()
        await _observe_mysql_run_lock_wait(
            mysql_session_factory,
            coordination,
        )
        if coordination.lock_metadata_supported:
            assert coordination.lock_wait_observed

        coordination.allow_attachment_revision_flush.set()
        attachment_result, player_character_result = (
            await _finish_inverse_foreign_key_pair(
                label=(
                    "inverse attachment versus "
                    f"{operation_label}"
                ),
                coordination=coordination,
                attachment=attachment_task,
                player_character=player_character_task,
            )
        )
    finally:
        coordination.allow_attachment_revision_flush.set()
        tasks = tuple(
            task
            for task in (attachment_task, player_character_task)
            if task is not None
        )
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    assert set(coordination.isolation_levels.values()) == {
        "REPEATABLE-READ"
    }
    assert len(set(coordination.mysql_versions.values())) == 1
    assert coordination.attachment_committed
    assert not coordination.attachment_rolled_back
    assert coordination.player_character_rolled_back
    assert coordination.player_character_run_lock_acquired.is_set()
    assert coordination.player_character_current_lock_observed
    assert len(coordination.player_character_revision_lock_sql) == 2
    assert all(
        "lock in share mode" in sql and "for update" not in sql
        for sql in coordination.player_character_revision_lock_sql
    )
    assert "attachment_revision_flush_completed" in (
        coordination.critical_events
    )
    assert coordination.critical_events.index(
        "attachment_before_revision_flush"
    ) < coordination.critical_events.index(
        "player_character_family_locked"
    )
    assert coordination.critical_events.index(
        "player_character_run_lock_requested"
    ) < coordination.critical_events.index(
        "attachment_revision_flush_started"
    )
    assert coordination.critical_events.index(
        "attachment_commit_returned"
    ) < coordination.critical_events.index(
        "player_character_run_lock_acquired"
    )

    assert not isinstance(
        attachment_result,
        (RunServiceDecision, RunReplayDecision),
    )
    assert attachment_result.resulting_state_version == RunStateVersion(
        value=3
    )
    assert attachment_result.participation_reference is not None
    assert attachment_result.participation_reference.session_id == session_id
    if player_character_operation == "binding-replay":
        assert player_character_result == original_binding_result
    else:
        assert player_character_result == PlayerCharacterPolicyDecision(
            code=(
                PlayerCharacterPolicyCode
                .ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
            )
        )
    await _assert_attached_bound_state(
        mysql_session_factory,
        character=character,
        run_id=run_id,
        session_id=session_id,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_concurrent_bind_constraints_leave_one_complete_binding(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    first = await _create_character(
        mysql_session_factory,
        binding_scope,
        "same-run-first",
    )
    second = await _create_character(
        mysql_session_factory,
        binding_scope,
        "same-run-second",
    )
    run_id = binding_scope.run_id("same-run")
    line_id = binding_scope.line_id("same-run")
    first_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=first,
    )
    second_service = _run_service(
        mysql_session_factory,
        run_id=run_id,
        line_id=line_id,
        character=second,
    )
    await _create_run(first_service, binding_scope, "same-run")
    same_run_results = await asyncio.wait_for(
        asyncio.gather(
            first_service.bind_player_character_internal(
                first.principal,
                operation_id=RunOperationId(
                    value=f"operation.{binding_scope.token}.same-run-first"
                ),
                command=_bind_command(
                    run_id=run_id,
                    line_id=line_id,
                    character=first,
                ),
            ),
            second_service.bind_player_character_internal(
                second.principal,
                operation_id=RunOperationId(
                    value=f"operation.{binding_scope.token}.same-run-second"
                ),
                command=_bind_command(
                    run_id=run_id,
                    line_id=line_id,
                    character=second,
                ),
            ),
        ),
        timeout=TIMEOUT,
    )
    successes = [
        item
        for item in same_run_results
        if not isinstance(item, RunServiceDecision)
    ]
    losses = [
        item
        for item in same_run_results
        if isinstance(item, RunServiceDecision)
    ]
    assert len(successes) == len(losses) == 1
    assert losses[0].code in {
        RunServiceDecisionCode.STALE_VERSION,
        RunServiceDecisionCode.PLAYER_CHARACTER_BINDING_CONFLICT,
    }
    assert await _run_family_counts(
        mysql_session_factory,
        run_id,
    ) == (2, 1, 1, 1)

    shared = await _create_character(
        mysql_session_factory,
        binding_scope,
        "same-character",
    )
    run_a = binding_scope.run_id("same-character-a")
    line_a = binding_scope.line_id("same-character-a")
    run_b = binding_scope.run_id("same-character-b")
    line_b = binding_scope.line_id("same-character-b")
    service_a = _run_service(
        mysql_session_factory,
        run_id=run_a,
        line_id=line_a,
        character=shared,
    )
    service_b = _run_service(
        mysql_session_factory,
        run_id=run_b,
        line_id=line_b,
        character=shared,
    )
    await _create_run(service_a, binding_scope, "same-character-a")
    await _create_run(service_b, binding_scope, "same-character-b")
    same_character_results = await asyncio.wait_for(
        asyncio.gather(
            service_a.bind_player_character_internal(
                shared.principal,
                operation_id=RunOperationId(
                    value=f"operation.{binding_scope.token}.same-character-a"
                ),
                command=_bind_command(
                    run_id=run_a,
                    line_id=line_a,
                    character=shared,
                ),
            ),
            service_b.bind_player_character_internal(
                shared.principal,
                operation_id=RunOperationId(
                    value=f"operation.{binding_scope.token}.same-character-b"
                ),
                command=_bind_command(
                    run_id=run_b,
                    line_id=line_b,
                    character=shared,
                ),
            ),
        ),
        timeout=TIMEOUT,
    )
    assert sum(
        not isinstance(item, RunServiceDecision)
        for item in same_character_results
    ) == 1
    assert [
        item.code
        for item in same_character_results
        if isinstance(item, RunServiceDecision)
    ] == [RunServiceDecisionCode.PLAYER_CHARACTER_BINDING_CONFLICT]
    assert sorted(
        (
            await _run_family_counts(mysql_session_factory, run_a),
            await _run_family_counts(mysql_session_factory, run_b),
        )
    ) == [(1, 1, 1, 0), (2, 1, 1, 1)]


@dataclass(slots=True)
class _EntryUowCounts:
    units: int = 0
    commit_attempts: int = 0
    successful_commits: int = 0
    rollback_exits: int = 0
    closes: int = 0


@dataclass(slots=True)
class _TwoPartyEntryBarrier:
    labels: list[str] = field(default_factory=list)
    all_arrived: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)

    async def arrive(self, label: str) -> None:
        assert label not in self.labels
        self.labels.append(label)
        if len(self.labels) == 2:
            self.all_arrived.set()
        await asyncio.wait_for(self.release.wait(), timeout=TIMEOUT)


class _CountingEntryUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        counts: _EntryUowCounts,
    ) -> None:
        super().__init__(factory)
        self._entry_counts = counts

    async def __aenter__(self):
        self._entry_counts.units += 1
        return await super().__aenter__()

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None or not self._committed:
            self._entry_counts.rollback_exits += 1
        try:
            await super().__aexit__(exc_type, exc, traceback)
        finally:
            self._entry_counts.closes += 1

    async def commit(self) -> None:
        self._entry_counts.commit_attempts += 1
        await super().commit()
        self._entry_counts.successful_commits += 1


class _SynchronizedEntryUnitOfWork(_CountingEntryUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        counts: _EntryUowCounts,
        *,
        barrier: _TwoPartyEntryBarrier,
        label: str,
        point: str,
    ) -> None:
        super().__init__(factory, counts)
        self._barrier = barrier
        self._label = label
        self._point = point

    async def __aenter__(self):
        await super().__aenter__()
        targets = {
            "character-lock": (self.player_characters, "get_for_update"),
            "derived-key": (
                self.run_creation_receipts,
                "add_with_evidence",
            ),
            "run-identity": (self.runs, "add_initial"),
            "line-identity": (self.runs, "add_initial"),
            "session-identity": (self.sessions, "add_initial_session"),
        }
        repository, method_name = targets[self._point]
        original = getattr(repository, method_name)

        async def synchronize_then_call(*args, **kwargs):
            await self._barrier.arrive(self._label)
            return await original(*args, **kwargs)

        setattr(repository, method_name, synchronize_then_call)
        return self


class _DuplicateParticipationEntryUnitOfWork(_CountingEntryUnitOfWork):
    async def __aenter__(self):
        await super().__aenter__()
        assert self._session is not None
        original = SqlAlchemyRunSessionParticipationRepository(
            self._session
        )
        original_add = original.add

        async def add_twice(participation, *, joined_at):
            await original_add(participation, joined_at=joined_at)
            await original_add(participation, joined_at=joined_at)

        original.add = add_twice
        self.run_participations = original
        return self


class _PostCommitUncertaintyEntryUnitOfWork(_CountingEntryUnitOfWork):
    async def commit(self) -> None:
        self._entry_counts.commit_attempts += 1
        await SqlAlchemyUnitOfWork.commit(self)
        self._entry_counts.successful_commits += 1
        raise RuntimeError("controlled uncertain commit outcome")


class _BoundaryFailureEntryUnitOfWork(_CountingEntryUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        counts: _EntryUowCounts,
        *,
        boundary: str,
        failure_factory: Any,
    ) -> None:
        super().__init__(factory, counts)
        self._failure_boundary = boundary
        self._failure_factory = failure_factory

    async def __aenter__(self):
        await super().__aenter__()
        targets = {
            "run-1": (self.runs, "add_initial", 1),
            "creation-receipt": (
                self.run_creation_receipts,
                "add_with_evidence",
                1,
            ),
            "run-2": (self.runs, "append_revision", 1),
            "cas-1": (self.runs, "compare_and_swap_current", 1),
            "binding-receipt": (self.run_mutation_receipts, "add", 1),
            "session-row": (self.sessions, "add_initial_session", 1),
            "session-event": (self.sessions, "persist_events", 1),
            "session-snapshot": (self.sessions, "add_initial_snapshot", 1),
            "run-3": (self.runs, "append_revision", 2),
            "participation": (self.run_participations, "add", 1),
            "cas-2": (self.runs, "compare_and_swap_current", 2),
            "attachment-receipt": (self.run_mutation_receipts, "add", 2),
        }
        repository, method_name, target_call = targets[self._failure_boundary]
        original = getattr(repository, method_name)
        calls = 0

        async def fail_after_boundary(*args, **kwargs):
            nonlocal calls
            result = await original(*args, **kwargs)
            calls += 1
            if calls == target_call:
                raise self._failure_factory()
            return result

        setattr(repository, method_name, fail_after_boundary)
        return self


class _ReplayReceiptBarrierRepository(
    SqlAlchemyRunCreationReceiptRepository
):
    def __init__(
        self,
        session: AsyncSession,
        receipt_read: asyncio.Event,
        writer_done: asyncio.Event,
    ) -> None:
        super().__init__(session)
        self._receipt_read = receipt_read
        self._writer_done = writer_done

    async def get_with_evidence(self, key):
        stored = await super().get_with_evidence(key)
        self._receipt_read.set()
        await asyncio.wait_for(self._writer_done.wait(), timeout=TIMEOUT)
        return stored


class _ReplayBarrierUnitOfWork(_CountingEntryUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        counts: _EntryUowCounts,
        receipt_read: asyncio.Event,
        writer_done: asyncio.Event,
    ) -> None:
        super().__init__(factory, counts)
        self._receipt_read = receipt_read
        self._writer_done = writer_done

    async def __aenter__(self):
        await super().__aenter__()
        assert self._session is not None
        self.run_creation_receipts = _ReplayReceiptBarrierRepository(
            self._session, self._receipt_read, self._writer_done
        )
        return self


def _entry_service(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
    character: _Character,
    *,
    suffix: str,
    counts: _EntryUowCounts,
    content_version: str | None = None,
    uow_factory_override: Any | None = None,
    run_id: RunId | None = None,
    line_id: ContinuousStoryLineId | None = None,
    session_id: str | None = None,
) -> RunEntryService:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    if content_version is not None:
        content_catalog = scenario_catalog.content_catalog.model_copy(
            update={"content_version": content_version}
        )
        scenario_catalog = scenario_catalog.model_copy(
            update={
                "content_version": content_version,
                "content_catalog": content_catalog,
                "scenarios": tuple(
                    definition.model_copy(
                        update={"content_version": content_version}
                    )
                    for definition in scenario_catalog.scenarios
                ),
            }
        )
    session_id = session_id or scope.session_id(f"entry-{suffix}")

    def uow_factory() -> _CountingEntryUnitOfWork:
        if uow_factory_override is not None:
            return uow_factory_override()
        return _CountingEntryUnitOfWork(factory, counts)

    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
        event_id_generator=lambda: f"event.{scope.token}-{suffix}",
    )
    return RunEntryService(
        uow_factory=uow_factory,
        run_id_issuer=_Issuer(run_id or scope.run_id(f"entry-{suffix}")),
        continuous_story_line_id_issuer=_Issuer(
            line_id or scope.line_id(f"entry-{suffix}")
        ),
        source_reference=RUN_SOURCE,
        clock=lambda: NOW,
        controller_binding_resolver=character.resolver,
        player_character_binding_evidence=character.service,
        session_service=session_service,
    )


@dataclass(frozen=True, slots=True)
class _P8DurableFamilyCounts:
    revisions: int
    current: int
    creation_receipts: int
    mutation_receipts: int
    participations: int
    sessions: int
    events: int
    snapshots: int


async def _p8_durable_family_counts(
    factory: async_sessionmaker[AsyncSession],
    *,
    run_id: str,
    session_id: str,
) -> _P8DurableFamilyCounts:
    async with factory() as fresh:
        async def count(row_type: Any, predicate: Any) -> int:
            return int(
                await fresh.scalar(
                    sa.select(sa.func.count())
                    .select_from(row_type)
                    .where(predicate)
                )
                or 0
            )

        return _P8DurableFamilyCounts(
            revisions=await count(
                RunRevisionRow, RunRevisionRow.run_id == run_id
            ),
            current=await count(RunCurrentRow, RunCurrentRow.run_id == run_id),
            creation_receipts=await count(
                RunCreationReceiptRow,
                RunCreationReceiptRow.result_run_id == run_id,
            ),
            mutation_receipts=await count(
                RunMutationReceiptRow, RunMutationReceiptRow.run_id == run_id
            ),
            participations=await count(
                RunSessionParticipationRow,
                RunSessionParticipationRow.run_id == run_id,
            ),
            sessions=await count(
                GameSessionRow, GameSessionRow.session_id == session_id
            ),
            events=await count(
                DomainEventRow, DomainEventRow.session_id == session_id
            ),
            snapshots=await count(
                GameSnapshotRow, GameSnapshotRow.session_id == session_id
            ),
        )


async def _p8_scope_durable_totals(
    factory: async_sessionmaker[AsyncSession],
    scope: _Scope,
) -> _P8DurableFamilyCounts:
    async with factory() as fresh:
        async def count(row_type: Any, predicate: Any) -> int:
            return int(
                await fresh.scalar(
                    sa.select(sa.func.count())
                    .select_from(row_type)
                    .where(predicate)
                )
                or 0
            )

        return _P8DurableFamilyCounts(
            revisions=await count(
                RunRevisionRow, RunRevisionRow.run_id.in_(scope.run_ids)
            ),
            current=await count(
                RunCurrentRow, RunCurrentRow.run_id.in_(scope.run_ids)
            ),
            creation_receipts=await count(
                RunCreationReceiptRow,
                RunCreationReceiptRow.result_run_id.in_(scope.run_ids),
            ),
            mutation_receipts=await count(
                RunMutationReceiptRow,
                RunMutationReceiptRow.run_id.in_(scope.run_ids),
            ),
            participations=await count(
                RunSessionParticipationRow,
                RunSessionParticipationRow.run_id.in_(scope.run_ids),
            ),
            sessions=await count(
                GameSessionRow,
                GameSessionRow.session_id.in_(scope.session_ids),
            ),
            events=await count(
                DomainEventRow,
                DomainEventRow.session_id.in_(scope.session_ids),
            ),
            snapshots=await count(
                GameSnapshotRow,
                GameSnapshotRow.session_id.in_(scope.session_ids),
            ),
        )


async def _release_proven_entry_overlap(
    barrier: _TwoPartyEntryBarrier,
    first: asyncio.Task[Any],
    second: asyncio.Task[Any],
) -> tuple[Any, Any]:
    try:
        await asyncio.wait_for(barrier.all_arrived.wait(), timeout=TIMEOUT)
        assert sorted(barrier.labels) == ["first", "second"]
        assert not barrier.release.is_set()
        assert not first.done()
        assert not second.done()
        barrier.release.set()
        return await asyncio.wait_for(
            asyncio.gather(first, second),
            timeout=TIMEOUT,
        )
    except BaseException:
        barrier.release.set()
        for task in (first, second):
            if not task.done():
                task.cancel()
        await asyncio.gather(first, second, return_exceptions=True)
        raise


async def _insert_retired_immutable_revision(
    factory: async_sessionmaker[AsyncSession],
    character: _Character,
    *,
    suffix: str,
) -> ApplicableCharacterReference:
    operation_id, command = _lifecycle_command(
        character,
        kind=PlayerCharacterMutationKind.RETIRE,
        suffix=suffix,
    )
    decision = RetirePlayerCharacterPolicy().evaluate(
        character.record,
        target=command.target_player_character_id,
        expected_revision=command.expected_revision,
        operation_id=operation_id,
        confirmation=command.confirmation,
        applicable_reference=command.applicable_reference,
    )
    assert decision.code is PlayerCharacterPolicyCode.ACCEPTED
    assert decision.resulting_record is not None
    retired = decision.resulting_record
    _, fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=retired.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=retired.player_character_id,
            contract_version=retired.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=retired.record_revision,
            resulting_lifecycle=retired.lifecycle,
        ),
    )
    async with SqlAlchemyUnitOfWork(factory) as uow:
        await uow.player_characters.append_revision(retired, created_at=NOW)
        assert await uow.player_characters.compare_and_swap_current(
            retired,
            expected_revision=character.record.record_revision.value,
            created_at=NOW,
        )
        await uow.mutation_receipts.add(receipt, created_at=NOW)
        await uow.commit()
    return ApplicableCharacterReference(
        player_character_id=retired.player_character_id,
        contract_version=retired.contract_version,
        record_revision=retired.record_revision,
    )


async def _coherently_replace_p8_binding_family(
    factory: async_sessionmaker[AsyncSession],
    created: RunEntryResult,
    target: ApplicableCharacterReference,
) -> None:
    async with factory.begin() as session:
        repository = SqlAlchemyRunRepository(session)
        initial = await repository._run_at_revision(created.run_id, 1)
        mutation_rows = (
            await session.scalars(
                sa.select(RunMutationReceiptRow)
                .where(RunMutationReceiptRow.run_id == created.run_id.value)
                .order_by(RunMutationReceiptRow.resulting_state_version)
            )
        ).all()
        binding_row, attachment_row = mutation_rows
        binding_operation_id = RunOperationId(value=binding_row.operation_id)
        attachment_operation_id = RunOperationId(
            value=attachment_row.operation_id
        )
        binding_command = BindPlayerCharacterCommand(
            run_id=created.run_id,
            continuous_story_line_id=initial.continuous_story_line_id,
            target_player_character_id=target.player_character_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=RUN_SOURCE,
        )
        rebound = bind_player_character_to_run(
            initial,
            binding_command,
            applicable_character_reference=target,
            operation_id=binding_operation_id,
            occurred_at=NOW,
        )
        assert attachment_row.participation_session_id is not None
        reactivated = activate_first_session_for_run(
            rebound,
            AttachSessionCommand(
                run_id=created.run_id,
                continuous_story_line_id=initial.continuous_story_line_id,
                session_id=attachment_row.participation_session_id,
                expected_state_version=RunStateVersion(value=2),
                source_reference=RUN_SOURCE,
            ),
            operation_id=attachment_operation_id,
            occurred_at=NOW,
        )
        _, binding_fingerprint = (
            bind_player_character_fingerprint(
                binding_command,
                operation_id=binding_operation_id,
            )
        )
        binding_receipt = StoredRunSuccessReceipt(
            key=RunReceiptKey(
                run_id=created.run_id,
                operation_namespace=(
                    RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
                ),
                operation_id=binding_operation_id,
            ),
            fingerprint=binding_fingerprint,
            command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
            result=bind_player_character_result(rebound),
        )
        rebound_values = SqlAlchemyRunRepository._run_core_values(rebound)
        active_values = SqlAlchemyRunRepository._run_core_values(reactivated)
        await session.execute(
            sa.update(RunRevisionRow)
            .where(
                RunRevisionRow.run_id == created.run_id.value,
                RunRevisionRow.state_version == 2,
            )
            .values(**rebound_values)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            sa.update(RunRevisionRow)
            .where(
                RunRevisionRow.run_id == created.run_id.value,
                RunRevisionRow.state_version == 3,
            )
            .values(**active_values)
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            sa.update(RunCurrentRow)
            .where(RunCurrentRow.run_id == created.run_id.value)
            .values(
                **active_values,
                active_player_character_id=target.player_character_id.value,
            )
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            sa.update(RunMutationReceiptRow)
            .where(
                RunMutationReceiptRow.run_id == created.run_id.value,
                RunMutationReceiptRow.operation_namespace
                == RunOperationNamespace.BIND_PLAYER_CHARACTER_V1.value,
            )
            .values(
                fingerprint=run_fingerprint_to_storage_bytes(
                    binding_fingerprint
                ),
                result_player_character_id=target.player_character_id.value,
                result_character_contract_version=target.contract_version.value,
                result_character_record_revision=target.record_revision.value,
                receipt_canonical=run_receipt_to_storage_bytes(
                    binding_receipt
                ),
                operation_evidence_canonical=(
                    binding_operation_evidence_to_storage_bytes(
                        binding_command
                    )
                ),
            )
            .execution_options(synchronize_session=False)
        )


async def _coherently_replace_p8_participation_session(
    factory: async_sessionmaker[AsyncSession],
    created: RunEntryResult,
    replacement_session_id: str,
) -> None:
    async with factory.begin() as session:
        repository = SqlAlchemyRunRepository(session)
        bound = await repository._run_at_revision(created.run_id, 2)
        attachment_row = await session.scalar(
            sa.select(RunMutationReceiptRow).where(
                RunMutationReceiptRow.run_id == created.run_id.value,
                RunMutationReceiptRow.operation_namespace
                == RunOperationNamespace.ATTACH_SESSION_V1.value,
            )
        )
        assert attachment_row is not None
        operation_id = RunOperationId(value=attachment_row.operation_id)
        command = AttachSessionCommand(
            run_id=created.run_id,
            continuous_story_line_id=bound.continuous_story_line_id,
            session_id=replacement_session_id,
            expected_state_version=RunStateVersion(value=2),
            source_reference=RUN_SOURCE,
        )
        substituted = activate_first_session_for_run(
            bound,
            command,
            operation_id=operation_id,
            occurred_at=NOW,
        )
        _, fingerprint = attach_session_fingerprint(
            command,
            operation_id=operation_id,
        )
        receipt = StoredRunSuccessReceipt(
            key=RunReceiptKey(
                run_id=created.run_id,
                operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
                operation_id=operation_id,
            ),
            fingerprint=fingerprint,
            command_kind=RunMutationKind.ATTACH_SESSION,
            result=attach_session_result(substituted),
        )
        receipt_values = {
            column.name: getattr(attachment_row, column.name)
            for column in RunMutationReceiptRow.__table__.columns
        }
        receipt_values.update(
            {
                "fingerprint": run_fingerprint_to_storage_bytes(fingerprint),
                "participation_session_id": replacement_session_id,
                "receipt_canonical": run_receipt_to_storage_bytes(receipt),
                "operation_evidence_canonical": (
                    attach_operation_evidence_to_storage_bytes(command)
                ),
            }
        )
        await session.delete(attachment_row)
        await session.flush()
        changed = await session.execute(
            sa.update(RunSessionParticipationRow)
            .where(
                RunSessionParticipationRow.run_id == created.run_id.value
            )
            .values(session_id=replacement_session_id)
            .execution_options(synchronize_session=False)
        )
        assert changed.rowcount == 1
        session.add(RunMutationReceiptRow(**receipt_values))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_active_binding_query_returns_zero_then_one_canonical_match(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-active-query"
    )
    async with SqlAlchemyUnitOfWork(mysql_session_factory) as before:
        absent = await before.runs.get_active_for_player_character_for_update(
            character.record.player_character_id
        )
    assert absent is None

    counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="active-query",
        counts=counts,
    )
    created = await service.enter(
        character.principal,
        command=RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.active-query"
            ),
            player_character_id=character.record.player_character_id,
            expected_record_revision=character.record.record_revision,
            scenario_id="death_certificate",
        ),
    )
    assert isinstance(created, RunEntryResult)

    async with SqlAlchemyUnitOfWork(mysql_session_factory) as after:
        present = await after.runs.get_active_for_player_character_for_update(
            character.record.player_character_id
        )
    assert present is not None
    assert present.run_id == created.run_id
    assert present.player_character_binding is not None
    assert (
        present.player_character_binding.applicable_character_reference
        .player_character_id
        == character.record.player_character_id
    )
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=0,
        closes=1,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ("lifecycle", "ownership"))
async def test_mysql_p8_owned_character_query_rejects_corrupt_current_family(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    corruption: str,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, f"p8-owned-{corruption}"
    )
    other = await _create_character(
        mysql_session_factory, binding_scope, f"p8-owned-{corruption}-other"
    )
    async with mysql_session_factory.begin() as session:
        values = (
            {"lifecycle": PlayerCharacterLifecycle.RETIRED.value}
            if corruption == "lifecycle"
            else {"controller_binding": other.binding.value}
        )
        changed = await session.execute(
            sa.update(PlayerCharacterCurrentRow)
            .where(
                PlayerCharacterCurrentRow.player_character_id
                == character.record.player_character_id.value
            )
            .values(**values)
        )
        assert changed.rowcount == 1

    counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix=f"owned-{corruption}",
        counts=counts,
    )
    with pytest.raises(PlayerCharacterStoredRecordIntegrityError) as raised:
        await service.enter(
            character.principal,
            command=RunEntryCommand(
                public_operation_key=RunEntryPublicOperationKey(
                    value=f"entry.{binding_scope.token}.owned-{corruption}"
                ),
                player_character_id=character.record.player_character_id,
                expected_record_revision=character.record.record_revision,
                scenario_id="death_certificate",
            ),
        )

    assert character.record.player_character_id.value not in str(raised.value)
    assert other.binding.value not in str(raised.value)
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    async with mysql_session_factory() as session:
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(RunRevisionRow)
                .where(RunRevisionRow.run_id.in_(binding_scope.run_ids))
            )
            == 0
        )
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(GameSessionRow)
                .where(GameSessionRow.session_id.in_(binding_scope.session_ids))
            )
            == 0
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_active_binding_query_rejects_corrupt_surviving_family(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-corrupt-binding"
    )
    creation_counts = _EntryUowCounts()
    creator = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="cb-win",
        counts=creation_counts,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.corrupt-binding-winner"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )
    created = await creator.enter(character.principal, command=command)
    assert isinstance(created, RunEntryResult)

    async with mysql_session_factory.begin() as session:
        changed = await session.execute(
            sa.update(RunCurrentRow)
            .where(RunCurrentRow.run_id == created.run_id.value)
            .values(
                lifecycle_status="completed",
                binding_state="historical",
                inactivated_at=NOW,
                active_player_character_id=None,
            )
        )
        assert changed.rowcount == 1

    rejection_counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="cb-lose",
        counts=rejection_counts,
    )
    with pytest.raises(RunStoredRecordIntegrityError) as raised:
        await service.enter(
            character.principal,
            command=RunEntryCommand(
                public_operation_key=RunEntryPublicOperationKey(
                    value=f"entry.{binding_scope.token}.corrupt-binding-loser"
                ),
                player_character_id=character.record.player_character_id,
                expected_record_revision=character.record.record_revision,
                scenario_id="death_certificate",
            ),
        )

    assert created.run_id.value not in str(raised.value)
    assert rejection_counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    loser_run_id = next(
        run_id for run_id in binding_scope.run_ids if run_id != created.run_id.value
    )
    loser_session_id = next(
        session_id
        for session_id in binding_scope.session_ids
        if session_id != created.session_id
    )
    async with mysql_session_factory() as session:
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(RunRevisionRow)
                .where(RunRevisionRow.run_id == loser_run_id)
            )
            == 0
        )
        assert await session.get(GameSessionRow, loser_session_id) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_entry_enforces_32_character_scenario_version_before_writes(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    accepted_character = await _create_character(
        mysql_session_factory, binding_scope, "p8-width-32"
    )
    accepted_counts = _EntryUowCounts()
    accepted_service = _entry_service(
        mysql_session_factory,
        binding_scope,
        accepted_character,
        suffix="width-32",
        counts=accepted_counts,
        content_version="v" * 32,
    )
    accepted = await accepted_service.enter(
        accepted_character.principal,
        command=RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.width-32"
            ),
            player_character_id=accepted_character.record.player_character_id,
            expected_record_revision=accepted_character.record.record_revision,
            scenario_id="death_certificate",
        ),
    )
    assert isinstance(accepted, RunEntryResult)
    async with mysql_session_factory() as session:
        accepted_row = await session.get(GameSessionRow, accepted.session_id)
    assert accepted_row is not None
    assert accepted_row.scenario_version == "v" * 32

    rejected_character = await _create_character(
        mysql_session_factory, binding_scope, "p8-width-33"
    )
    rejected_counts = _EntryUowCounts()
    rejected_service = _entry_service(
        mysql_session_factory,
        binding_scope,
        rejected_character,
        suffix="width-33",
        counts=rejected_counts,
        content_version="v" * 33,
    )
    rejected = await rejected_service.enter(
        rejected_character.principal,
        command=RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.width-33"
            ),
            player_character_id=rejected_character.record.player_character_id,
            expected_record_revision=rejected_character.record.record_revision,
            scenario_id="death_certificate",
        ),
    )
    assert rejected == RunEntryDecision(
        code=RunEntryDecisionCode.INVALID_SCENARIO_DEFINITION
    )
    assert rejected_counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("substitution", "expected_error"),
    (
        ("binding", RunEntryIntegrityError),
        ("immutable-revision", RunStoredRecordIntegrityError),
        ("participation", RunEntryIntegrityError),
        ("session", SnapshotSessionMismatchError),
        ("initial-event", SnapshotSessionMismatchError),
    ),
)
async def test_mysql_p8_coherent_cross_family_substitutions_fail_closed(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    substitution: str,
    expected_error: type[Exception],
) -> None:
    short = {
        "binding": "xb",
        "immutable-revision": "xr",
        "participation": "xp",
        "session": "xs",
        "initial-event": "xe",
    }[substitution]
    character = await _create_character(
        mysql_session_factory, binding_scope, f"p8-{short}"
    )
    counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix=short,
        counts=counts,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.{short}"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )
    created = await service.enter(character.principal, command=command)
    assert isinstance(created, RunEntryResult)

    protected_value: str
    if substitution == "binding":
        replacement = await _create_additional_owned_character(
            mysql_session_factory,
            binding_scope,
            f"p8-{short}-alt",
            character,
        )
        target = ApplicableCharacterReference(
            player_character_id=replacement.record.player_character_id,
            contract_version=replacement.record.contract_version,
            record_revision=replacement.record.record_revision,
        )
        protected_value = target.player_character_id.value
        await _coherently_replace_p8_binding_family(
            mysql_session_factory, created, target
        )
    elif substitution == "immutable-revision":
        target = await _insert_retired_immutable_revision(
            mysql_session_factory,
            character,
            suffix=short,
        )
        protected_value = str(target.record_revision.value)
        await _coherently_replace_p8_binding_family(
            mysql_session_factory, created, target
        )
    elif substitution == "participation":
        replacement_session_id = await _add_session(
            mysql_session_factory,
            binding_scope,
            suffix=f"p8-{short}-alt",
            principal=character.principal,
        )
        protected_value = replacement_session_id
        await _coherently_replace_p8_participation_session(
            mysql_session_factory,
            created,
            replacement_session_id,
        )
    elif substitution == "session":
        protected_value = "binding-lock-order-scenario"
        async with mysql_session_factory.begin() as session:
            changed = await session.execute(
                sa.update(GameSessionRow)
                .where(GameSessionRow.session_id == created.session_id)
                .values(scenario_id=protected_value)
            )
            assert changed.rowcount == 1
    else:
        protected_value = "scenario.substituted"
        async with mysql_session_factory.begin() as session:
            changed = await session.execute(
                sa.update(DomainEventRow)
                .where(DomainEventRow.session_id == created.session_id)
                .values(
                    payload_json={
                        "scenario_id": protected_value,
                        "scenario_content_version": (
                            "death-certificate-1.1.0"
                        ),
                    }
                )
            )
            assert changed.rowcount == 1

    with pytest.raises(expected_error) as raised:
        await service.enter(character.principal, command=command)

    assert protected_value not in str(raised.value)
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )
    async with mysql_session_factory() as fresh:
        durable_counts = (
            await fresh.scalar(
                sa.select(sa.func.count()).select_from(RunRevisionRow).where(
                    RunRevisionRow.run_id == created.run_id.value
                )
            ),
            await fresh.scalar(
                sa.select(sa.func.count()).select_from(RunCurrentRow).where(
                    RunCurrentRow.run_id == created.run_id.value
                )
            ),
            await fresh.scalar(
                sa.select(sa.func.count())
                .select_from(RunCreationReceiptRow)
                .where(
                    RunCreationReceiptRow.result_run_id
                    == created.run_id.value
                )
            ),
            await fresh.scalar(
                sa.select(sa.func.count())
                .select_from(RunMutationReceiptRow)
                .where(RunMutationReceiptRow.run_id == created.run_id.value)
            ),
            await fresh.scalar(
                sa.select(sa.func.count())
                .select_from(RunSessionParticipationRow)
                .where(
                    RunSessionParticipationRow.run_id == created.run_id.value
                )
            ),
        )
    assert durable_counts == (3, 1, 1, 2, 1)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "boundary",
    (
        "run-1",
        "creation-receipt",
        "run-2",
        "cas-1",
        "binding-receipt",
        "session-row",
        "session-event",
        "session-snapshot",
        "run-3",
        "participation",
        "cas-2",
        "attachment-receipt",
    ),
)
async def test_mysql_p8_failure_after_each_write_boundary_rolls_back_everything(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    boundary: str,
) -> None:
    short_suffix = f"pf-{boundary[:4]}"
    character = await _create_character(
        mysql_session_factory, binding_scope, short_suffix
    )
    counts = _EntryUowCounts()

    def failing_uow() -> _BoundaryFailureEntryUnitOfWork:
        return _BoundaryFailureEntryUnitOfWork(
            mysql_session_factory,
            counts,
            boundary=boundary,
            failure_factory=lambda: RuntimeError(f"failure after {boundary}"),
        )

    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix=short_suffix,
        counts=counts,
        uow_factory_override=failing_uow,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.{boundary}"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )

    with pytest.raises(RuntimeError, match=f"failure after {boundary}"):
        await service.enter(character.principal, command=command)

    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    run_id = next(iter(binding_scope.run_ids))
    session_id = next(iter(binding_scope.session_ids))
    async with mysql_session_factory() as session:
        counts_after = (
            await session.scalar(
                sa.select(sa.func.count()).select_from(RunRevisionRow).where(
                    RunRevisionRow.run_id == run_id
                )
            ),
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(RunCreationReceiptRow)
                .where(RunCreationReceiptRow.result_run_id == run_id)
            ),
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(RunMutationReceiptRow)
                .where(RunMutationReceiptRow.run_id == run_id)
            ),
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(RunSessionParticipationRow)
                .where(RunSessionParticipationRow.run_id == run_id)
            ),
            await session.scalar(
                sa.select(sa.func.count()).select_from(GameSessionRow).where(
                    GameSessionRow.session_id == session_id
                )
            ),
        )
    assert counts_after == (0, 0, 0, 0, 0)

    async with SqlAlchemyUnitOfWork(mysql_session_factory) as following:
        locked = await following.player_characters.get_for_update(
            character.record.player_character_id
        )
    assert locked == character.record


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_cancellation_rolls_back_and_releases_all_locks(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-cancel"
    )
    counts = _EntryUowCounts()

    def cancelling_uow() -> _BoundaryFailureEntryUnitOfWork:
        return _BoundaryFailureEntryUnitOfWork(
            mysql_session_factory,
            counts,
            boundary="session-snapshot",
            failure_factory=asyncio.CancelledError,
        )

    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="cancel",
        counts=counts,
        uow_factory_override=cancelling_uow,
    )
    with pytest.raises(asyncio.CancelledError):
        await service.enter(
            character.principal,
            command=RunEntryCommand(
                public_operation_key=RunEntryPublicOperationKey(
                    value=f"entry.{binding_scope.token}.cancel"
                ),
                player_character_id=character.record.player_character_id,
                expected_record_revision=character.record.record_revision,
                scenario_id="death_certificate",
            ),
        )
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    async with SqlAlchemyUnitOfWork(mysql_session_factory) as following:
        locked = await asyncio.wait_for(
            following.player_characters.get_for_update(
                character.record.player_character_id
            ),
            timeout=TIMEOUT,
        )
    assert locked == character.record


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_entry_is_atomic_and_exact_replay_is_read_only(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-entry"
    )
    counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="atomic",
        counts=counts,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.atomic"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )

    created = await service.enter(character.principal, command=command)
    assert isinstance(created, RunEntryResult)
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=0,
        closes=1,
    )

    async with mysql_session_factory() as session:
        run_counts_list: list[int] = []
        for table in (
            RunRevisionRow,
            RunCurrentRow,
            RunMutationReceiptRow,
            RunSessionParticipationRow,
        ):
            run_counts_list.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count()).select_from(table).where(
                            table.run_id == created.run_id.value
                        )
                    )
                    or 0
                )
            )
        run_counts = tuple(run_counts_list)
        creation_row = await session.scalar(
            sa.select(RunCreationReceiptRow).where(
                RunCreationReceiptRow.result_run_id == created.run_id.value
            )
        )
        session_row = await session.get(GameSessionRow, created.session_id)
        snapshot_row = await session.get(GameSnapshotRow, created.session_id)
        event_rows = (
            await session.scalars(
                sa.select(DomainEventRow).where(
                    DomainEventRow.session_id == created.session_id
                )
            )
        ).all()
    assert run_counts == (3, 1, 2, 1)
    assert creation_row is not None
    assert 14 <= len(creation_row.operation_evidence_canonical) <= 4096
    assert creation_row.operation_evidence_canonical.startswith(
        b"\x89DP8S2CE\r\n\x1a\n\x01"
    )
    assert creation_row.fingerprint == hashlib.sha256(
        creation_row.operation_evidence_canonical
    ).digest()
    assert session_row is not None
    assert session_row.scenario_version == "death-certificate-1.1.0"
    assert snapshot_row is not None and snapshot_row.state_version == 0
    assert snapshot_row.state_json["schema_version"] == 3
    assert snapshot_row.state_json["player_memory"]["scenario_records"]
    assert len(event_rows) == 1
    assert event_rows[0].sequence_no == 1

    replayed = await service.enter(character.principal, command=command)
    assert replayed == created
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )

    async with mysql_session_factory() as session:
        assert (
            await session.scalar(
                sa.select(sa.func.count()).select_from(RunRevisionRow).where(
                    RunRevisionRow.run_id == created.run_id.value
                )
            )
            == 3
        )
        assert (
            await session.scalar(
                sa.select(sa.func.count()).select_from(DomainEventRow).where(
                    DomainEventRow.session_id == created.session_id
                )
            )
            == 1
        )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tamper",
    (
        "controller",
        "public-key",
        "player-character",
        "character-revision",
        "scenario",
        "content-version",
        "default-character",
        "source",
        "raw-fingerprint",
        "canonical-fingerprint",
        "canonical-result",
        "canonical-key",
    ),
)
async def test_mysql_p8_creation_evidence_and_receipt_tamper_fail_closed(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    tamper: str,
) -> None:
    short_suffix = f"pt-{tamper[:3]}"
    character = await _create_character(
        mysql_session_factory, binding_scope, short_suffix
    )
    counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix=short_suffix,
        counts=counts,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.{tamper}"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )
    created = await service.enter(character.principal, command=command)
    assert isinstance(created, RunEntryResult)

    async with mysql_session_factory.begin() as session:
        row = await session.scalar(
            sa.select(RunCreationReceiptRow).where(
                RunCreationReceiptRow.result_run_id == created.run_id.value
            )
        )
        assert row is not None
        if tamper in {
            "controller",
            "public-key",
            "player-character",
            "character-revision",
            "scenario",
            "content-version",
            "default-character",
            "source",
        }:
            payload = json.loads(row.operation_evidence_canonical[13:])
            if tamper == "controller":
                payload["controller_operation"]["controller_binding"][
                    "value"
                ] = "controller.tampered"
            elif tamper == "public-key":
                payload["controller_operation"][
                    "public_operation_key"
                ] = "entry.tampered"
            elif tamper == "player-character":
                payload["player_character"]["player_character_id"][
                    "value"
                ] = "pc.tampered"
            elif tamper == "character-revision":
                payload["player_character"][
                    "pre_entry_record_revision"
                ]["value"] = 2
            elif tamper == "scenario":
                payload["scenario"]["scenario_id"] = "scenario.tampered"
            elif tamper == "content-version":
                payload["scenario"]["content_version"] = "version.tampered"
            elif tamper == "default-character":
                payload["scenario"][
                    "default_character_definition_id"
                ] = "character.tampered"
            else:
                payload["trusted_run_source"]["source_reference"][
                    "value"
                ] = "source.tampered"
            row.operation_evidence_canonical = (
                b"\x89DP8S2CE\r\n\x1a\n\x01"
                + json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
        elif tamper == "raw-fingerprint":
            row.fingerprint = b"\x00" * 32
        else:
            receipt_payload = json.loads(row.receipt_canonical)
            if tamper == "canonical-fingerprint":
                receipt_payload["fingerprint"]["value"] = "0" * 64
            elif tamper == "canonical-result":
                receipt_payload["result"]["run_id"]["value"] = "run.tampered"
            else:
                receipt_payload["key"]["operation_id"][
                    "value"
                ] = "operation.tampered"
            row.receipt_canonical = json.dumps(
                receipt_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")

    with pytest.raises(RunStoredRecordIntegrityError):
        await service.enter(character.principal, command=command)
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("tamper", (False, True))
async def test_mysql_p8_replay_uses_current_session_and_snapshot_reads(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    tamper: bool,
) -> None:
    suffix = "p8-current-bad" if tamper else "p8-current-good"
    character = await _create_character(
        mysql_session_factory, binding_scope, suffix
    )
    creation_counts = _EntryUowCounts()
    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="current-bad" if tamper else "current-good",
        counts=creation_counts,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.current-{tamper}"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )
    created = await service.enter(character.principal, command=command)
    assert isinstance(created, RunEntryResult)

    receipt_read = asyncio.Event()
    writer_done = asyncio.Event()
    replay_counts = _EntryUowCounts()

    def replay_uow() -> _ReplayBarrierUnitOfWork:
        return _ReplayBarrierUnitOfWork(
            mysql_session_factory,
            replay_counts,
            receipt_read,
            writer_done,
        )

    service.uow_factory = replay_uow

    async def advance_current_state() -> None:
        await asyncio.wait_for(receipt_read.wait(), timeout=TIMEOUT)
        try:
            async with mysql_session_factory.begin() as writer:
                snapshot = await writer.get(GameSnapshotRow, created.session_id)
                assert snapshot is not None
                payload = deepcopy(snapshot.state_json)
                if tamper:
                    payload["content_version"] = "tampered-content"
                await writer.execute(
                    sa.update(GameSessionRow)
                    .where(GameSessionRow.session_id == created.session_id)
                    .values(state_version=1)
                )
                await writer.execute(
                    sa.update(GameSnapshotRow)
                    .where(GameSnapshotRow.session_id == created.session_id)
                    .values(state_version=1, state_json=payload)
                )
        finally:
            writer_done.set()

    replay_task = asyncio.create_task(
        service.enter(character.principal, command=command)
    )
    writer_task = asyncio.create_task(advance_current_state())
    if tamper:
        with pytest.raises(SnapshotContentVersionMismatchError):
            await asyncio.wait_for(
                asyncio.gather(replay_task, writer_task), timeout=TIMEOUT
            )
    else:
        replayed, _ = await asyncio.wait_for(
            asyncio.gather(replay_task, writer_task), timeout=TIMEOUT
        )
        assert replayed == created

    assert replay_counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, created.session_id)
        snapshot_row = await session.get(GameSnapshotRow, created.session_id)
    assert session_row is not None and session_row.state_version == 1
    assert snapshot_row is not None and snapshot_row.state_version == 1
    assert snapshot_row.state_json["content_version"] == (
        "tampered-content" if tamper else "death-certificate-1.1.0"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_same_character_same_key_has_one_commit_and_one_replay(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-entry-race"
    )
    counts = _EntryUowCounts()
    barrier = _TwoPartyEntryBarrier()
    labels = iter(("first", "second"))

    def synchronized_uow() -> _SynchronizedEntryUnitOfWork:
        return _SynchronizedEntryUnitOfWork(
            mysql_session_factory,
            counts,
            barrier=barrier,
            label=next(labels),
            point="character-lock",
        )

    first_service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="race-a",
        counts=counts,
        uow_factory_override=synchronized_uow,
    )
    second_service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="race-b",
        counts=counts,
        uow_factory_override=synchronized_uow,
    )
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(
            value=f"entry.{binding_scope.token}.race"
        ),
        player_character_id=character.record.player_character_id,
        expected_record_revision=character.record.record_revision,
        scenario_id="death_certificate",
    )

    first_task = asyncio.create_task(
        first_service.enter(character.principal, command=command)
    )
    second_task = asyncio.create_task(
        second_service.enter(character.principal, command=command)
    )
    first, second = await _release_proven_entry_overlap(
        barrier, first_task, second_task
    )

    assert isinstance(first, RunEntryResult)
    assert second == first
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )
    winning_counts = await _p8_durable_family_counts(
        mysql_session_factory,
        run_id=first.run_id.value,
        session_id=first.session_id,
    )
    assert winning_counts == _P8DurableFamilyCounts(3, 1, 1, 2, 1, 1, 1, 1)
    losing_run_id = next(
        value for value in binding_scope.run_ids if value != first.run_id.value
    )
    losing_session_id = next(
        value for value in binding_scope.session_ids if value != first.session_id
    )
    assert await _p8_durable_family_counts(
        mysql_session_factory,
        run_id=losing_run_id,
        session_id=losing_session_id,
    ) == _P8DurableFamilyCounts(0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_same_character_different_keys_has_one_durable_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-entry-different-key"
    )
    counts = _EntryUowCounts()
    barrier = _TwoPartyEntryBarrier()
    labels = iter(("first", "second"))

    def synchronized_uow() -> _SynchronizedEntryUnitOfWork:
        return _SynchronizedEntryUnitOfWork(
            mysql_session_factory,
            counts,
            barrier=barrier,
            label=next(labels),
            point="character-lock",
        )

    services = tuple(
        _entry_service(
            mysql_session_factory,
            binding_scope,
            character,
            suffix=f"different-{suffix}",
            counts=counts,
            uow_factory_override=synchronized_uow,
        )
        for suffix in ("a", "b")
    )
    commands = tuple(
        RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.different-{suffix}"
            ),
            player_character_id=character.record.player_character_id,
            expected_record_revision=character.record.record_revision,
            scenario_id="death_certificate",
        )
        for suffix in ("a", "b")
    )

    tasks = tuple(
        asyncio.create_task(
            service.enter(character.principal, command=command)
        )
        for service, command in zip(services, commands, strict=True)
    )
    results = await _release_proven_entry_overlap(
        barrier, tasks[0], tasks[1]
    )

    assert sum(isinstance(item, RunEntryResult) for item in results) == 1
    assert [
        item
        for item in results
        if isinstance(item, RunEntryDecision)
    ] == [
        RunEntryDecision(
            code=RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE
        )
    ]
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )
    winner = next(item for item in results if isinstance(item, RunEntryResult))
    assert await _p8_durable_family_counts(
        mysql_session_factory,
        run_id=winner.run_id.value,
        session_id=winner.session_id,
    ) == _P8DurableFamilyCounts(3, 1, 1, 2, 1, 1, 1, 1)
    losing_run_id = next(
        value for value in binding_scope.run_ids if value != winner.run_id.value
    )
    losing_session_id = next(
        value for value in binding_scope.session_ids if value != winner.session_id
    )
    assert await _p8_durable_family_counts(
        mysql_session_factory,
        run_id=losing_run_id,
        session_id=losing_session_id,
    ) == _P8DurableFamilyCounts(0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_same_derived_key_non_equivalent_race_has_one_family(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    first_character = await _create_character(
        mysql_session_factory, binding_scope, "p8-key-a"
    )
    second_character = await _create_additional_owned_character(
        mysql_session_factory,
        binding_scope,
        "p8-key-b",
        first_character,
    )
    counts = _EntryUowCounts()
    barrier = _TwoPartyEntryBarrier()
    labels = iter(("first", "second"))

    def synchronized_uow() -> _SynchronizedEntryUnitOfWork:
        return _SynchronizedEntryUnitOfWork(
            mysql_session_factory,
            counts,
            barrier=barrier,
            label=next(labels),
            point="character-lock",
        )

    services = tuple(
        _entry_service(
            mysql_session_factory,
            binding_scope,
            character,
            suffix=f"key-{suffix}",
            counts=counts,
            uow_factory_override=synchronized_uow,
        )
        for character, suffix in (
            (first_character, "a"),
            (second_character, "b"),
        )
    )
    commands = tuple(
        RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.same-derived-key"
            ),
            player_character_id=character.record.player_character_id,
            expected_record_revision=character.record.record_revision,
            scenario_id="death_certificate",
        )
        for character in (first_character, second_character)
    )
    tasks = tuple(
        asyncio.create_task(
            service.enter(first_character.principal, command=command)
        )
        for service, command in zip(services, commands, strict=True)
    )

    results = await _release_proven_entry_overlap(
        barrier, tasks[0], tasks[1]
    )

    assert sum(isinstance(item, RunEntryResult) for item in results) == 1
    assert [
        item for item in results if isinstance(item, RunEntryDecision)
    ] == [
        RunEntryDecision(code=RunEntryDecisionCode.IDEMPOTENCY_CONFLICT)
    ]
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )
    assert await _p8_scope_durable_totals(
        mysql_session_factory, binding_scope
    ) == _P8DurableFamilyCounts(3, 1, 1, 2, 1, 1, 1, 1)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("identity", "barrier_point"),
    (
        ("run", "run-identity"),
        ("line", "line-identity"),
        ("session", "session-identity"),
    ),
)
async def test_mysql_p8_identity_uniqueness_races_rollback_losing_family(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    identity: str,
    barrier_point: str,
) -> None:
    first_character = await _create_character(
        mysql_session_factory, binding_scope, f"p8-{identity}-a"
    )
    second_character = await _create_character(
        mysql_session_factory, binding_scope, f"p8-{identity}-b"
    )
    shared_run = (
        binding_scope.run_id("entry-shared-run")
        if identity == "run"
        else None
    )
    shared_line = (
        binding_scope.line_id("entry-shared-line")
        if identity == "line"
        else None
    )
    shared_session = (
        binding_scope.session_id("entry-shared-session")
        if identity == "session"
        else None
    )
    counts = _EntryUowCounts()
    barrier = _TwoPartyEntryBarrier()
    labels = iter(("first", "second"))

    def synchronized_uow() -> _SynchronizedEntryUnitOfWork:
        return _SynchronizedEntryUnitOfWork(
            mysql_session_factory,
            counts,
            barrier=barrier,
            label=next(labels),
            point=barrier_point,
        )

    services = tuple(
        _entry_service(
            mysql_session_factory,
            binding_scope,
            character,
            suffix=f"{identity}-{suffix}",
            counts=counts,
            uow_factory_override=synchronized_uow,
            run_id=shared_run,
            line_id=shared_line,
            session_id=shared_session,
        )
        for character, suffix in (
            (first_character, "a"),
            (second_character, "b"),
        )
    )
    commands = tuple(
        RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.{identity}-{suffix}"
            ),
            player_character_id=character.record.player_character_id,
            expected_record_revision=character.record.record_revision,
            scenario_id="death_certificate",
        )
        for character, suffix in (
            (first_character, "a"),
            (second_character, "b"),
        )
    )
    tasks = tuple(
        asyncio.create_task(
            service.enter(character.principal, command=command)
        )
        for service, command, character in zip(
            services,
            commands,
            (first_character, second_character),
            strict=True,
        )
    )

    results = await _release_proven_entry_overlap(
        barrier, tasks[0], tasks[1]
    )

    assert sum(isinstance(item, RunEntryResult) for item in results) == 1
    assert [
        item for item in results if isinstance(item, RunEntryDecision)
    ] == [RunEntryDecision(code=RunEntryDecisionCode.RUN_ENTRY_CONFLICT)]
    assert counts == _EntryUowCounts(
        units=2,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=2,
    )
    assert await _p8_scope_durable_totals(
        mysql_session_factory, binding_scope
    ) == _P8DurableFamilyCounts(3, 1, 1, 2, 1, 1, 1, 1)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_participation_uniqueness_loss_rolls_back_all_writes(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-participation-unique"
    )
    counts = _EntryUowCounts()

    def duplicate_participation_uow() -> (
        _DuplicateParticipationEntryUnitOfWork
    ):
        return _DuplicateParticipationEntryUnitOfWork(
            mysql_session_factory, counts
        )

    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="part-unique",
        counts=counts,
        uow_factory_override=duplicate_participation_uow,
    )
    result = await service.enter(
        character.principal,
        command=RunEntryCommand(
            public_operation_key=RunEntryPublicOperationKey(
                value=f"entry.{binding_scope.token}.part-unique"
            ),
            player_character_id=character.record.player_character_id,
            expected_record_revision=character.record.record_revision,
            scenario_id="death_certificate",
        ),
    )

    assert result == RunEntryDecision(
        code=RunEntryDecisionCode.RUN_ENTRY_CONFLICT
    )
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=0,
        successful_commits=0,
        rollback_exits=1,
        closes=1,
    )
    assert await _p8_scope_durable_totals(
        mysql_session_factory, binding_scope
    ) == _P8DurableFamilyCounts(0, 0, 0, 0, 0, 0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_p8_uncertain_commit_has_no_recovery_or_second_attempt(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    binding_scope: _Scope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = await _create_character(
        mysql_session_factory, binding_scope, "p8-uncertain"
    )
    counts = _EntryUowCounts()
    policy_calls: list[str] = []
    original_resolve = SessionService.resolve_run_entry_definition

    def counted_resolve(
        session_service: SessionService, scenario_id: str
    ):
        policy_calls.append(scenario_id)
        return original_resolve(session_service, scenario_id)

    monkeypatch.setattr(
        SessionService,
        "resolve_run_entry_definition",
        counted_resolve,
    )

    def uncertain_uow() -> _PostCommitUncertaintyEntryUnitOfWork:
        return _PostCommitUncertaintyEntryUnitOfWork(
            mysql_session_factory, counts
        )

    service = _entry_service(
        mysql_session_factory,
        binding_scope,
        character,
        suffix="uncertain",
        counts=counts,
        uow_factory_override=uncertain_uow,
    )
    with pytest.raises(
        RuntimeError, match="controlled uncertain commit outcome"
    ):
        await service.enter(
            character.principal,
            command=RunEntryCommand(
                public_operation_key=RunEntryPublicOperationKey(
                    value=f"entry.{binding_scope.token}.uncertain"
                ),
                player_character_id=character.record.player_character_id,
                expected_record_revision=(
                    character.record.record_revision
                ),
                scenario_id="death_certificate",
            ),
        )

    assert policy_calls == ["death_certificate"]
    assert service.run_id_issuer.calls == 1
    assert service.continuous_story_line_id_issuer.calls == 1
    assert counts == _EntryUowCounts(
        units=1,
        commit_attempts=1,
        successful_commits=1,
        rollback_exits=1,
        closes=1,
    )
    assert await _p8_scope_durable_totals(
        mysql_session_factory, binding_scope
    ) == _P8DurableFamilyCounts(3, 1, 1, 2, 1, 1, 1, 1)
