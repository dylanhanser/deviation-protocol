from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from types import TracebackType
from typing import Any, Mapping, Sequence

from deviation_protocol.application import ports as application_ports
from deviation_protocol.application import run_operations as run_operations_module
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.player_character_operations import (
    CharacterCreationCommand,
    CharacterMutationCommand,
    CreationReceiptKey,
    MutationReceiptKey,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
)
from deviation_protocol.application.ports import (
    ControllerBindingRegistryRepository,
    ControllerBindingUniquenessConflictError,
    GameSessionRepository,
    MutationReceiptUniquenessConflictError,
    NarrativeJobRepository,
    PlayerCharacterCreationReceiptRepository,
    PlayerCharacterMutationReceiptRepository,
    PlayerCharacterRepository,
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
    RunCreationReceiptRepository,
    RunMutationReceiptRepository,
    RunReceiptUniquenessConflictError,
    RunRepository,
    RunSessionAttachmentLockEvidence,
    RunSessionParticipationRepository,
    RunSessionParticipationUniquenessConflictError,
    StoredRunCreationEvidence,
    TurnRequestRepository,
    UnitOfWork,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    RunEntryCreationEvidence,
    RunOperationNamespace,
    RunReceiptKey,
    StoredRunSuccessReceipt,
    run_entry_creation_fingerprint,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    CanonicalPlayerCharacter,
    ControllerBindingRef,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterRevision,
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    PlayerConfirmation,
    TrustedFinalDeathEvidence,
)
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    RunId,
    RunMutationKind,
    RunSessionParticipationReference,
    validate_canonical_run,
)
from deviation_protocol.infrastructure.errors import (
    OptimisticLockError,
    PlayerCharacterRepositoryConflictError,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
    StoredControllerBindingRecord,
    StoredCreationReceiptRecord,
    StoredCurrentPlayerCharacterRecord,
    StoredMutationReceiptRecord,
    StoredPlayerCharacterIdAllocationRecord,
    StoredPlayerCharacterRevisionRecord,
    canonical_record_from_current_storage,
    canonical_record_from_revision_storage,
    canonical_record_to_storage_bytes,
    canonical_state_record_fingerprint,
    creation_operation_evidence_to_storage_bytes,
    creation_receipt_from_storage,
    creation_receipt_to_storage_bytes,
    fingerprint_to_storage_bytes,
    mutation_operation_evidence_to_storage_bytes,
    mutation_receipt_from_storage,
    mutation_receipt_to_storage_bytes,
    validate_stored_player_character_record_set,
)
from deviation_protocol.infrastructure.run_persistence import (
    RunRepositoryConflictError,
    RunStoredRecordIntegrityError,
    StoredCurrentRunRecord,
    StoredRunCreationReceiptRecord,
    StoredRunMutationReceiptRecord,
    StoredRunRevisionRecord,
    StoredRunSessionParticipationRecord,
    attach_operation_evidence_to_storage_bytes,
    binding_operation_evidence_to_storage_bytes,
    canonical_run_from_current_storage,
    canonical_run_from_revision_storage,
    creation_evidence_from_storage,
    creation_operation_evidence_to_storage_bytes as run_creation_evidence_bytes,
    creation_receipt_from_storage as run_creation_receipt_from_storage,
    fingerprint_to_storage_bytes as run_fingerprint_to_storage_bytes,
    mutation_receipt_from_storage as run_mutation_receipt_from_storage,
    participation_from_storage,
    run_receipt_to_storage_bytes,
    validate_stored_run_record_set,
)


_RunActiveBindingUniquenessConflictError = getattr(
    application_ports,
    "RunPlayer" "CharacterBindingUniquenessConflictError",
)
_RunBindCommand = getattr(
    run_operations_module,
    "BindPlayer" "CharacterCommand",
)


def _clone_job(job: NarrativeJob) -> NarrativeJob:
    return NarrativeJob.model_validate(job.model_dump(mode="python"))


def _clone_session(session: GameSession) -> GameSession:
    return replace(session)


@dataclass(frozen=True, slots=True)
class DemoStoreSnapshot:
    sessions: dict[str, PersistedSession]
    snapshots: dict[str, PersistedSnapshot]
    creation_keys: dict[tuple[str, str], str]
    turn_requests: dict[tuple[str, str], PersistedTurnRequest]
    narrative_jobs: dict[str, NarrativeJob]
    events: tuple[DomainEvent, ...]
    provider_progress: dict[str, int]
    controller_bindings: dict[str, StoredControllerBindingRecord]
    player_character_id_allocations: dict[
        str, StoredPlayerCharacterIdAllocationRecord
    ]
    player_character_revisions: dict[
        tuple[str, int], StoredPlayerCharacterRevisionRecord
    ]
    player_character_current: dict[str, StoredCurrentPlayerCharacterRecord]
    player_character_creation_receipts: dict[
        tuple[str, str, str], StoredCreationReceiptRecord
    ]
    player_character_mutation_receipts: dict[
        tuple[str, str, str], StoredMutationReceiptRecord
    ]
    run_revisions: dict[tuple[str, int], StoredRunRevisionRecord]
    run_current: dict[str, StoredCurrentRunRecord]
    run_participations: dict[str, StoredRunSessionParticipationRecord]
    run_creation_receipts: dict[
        tuple[str, str], StoredRunCreationReceiptRecord
    ]
    run_mutation_receipts: dict[
        tuple[str, str, str], StoredRunMutationReceiptRecord
    ]


class DemoProcessStore:
    """Process-lifetime storage used only by the explicit Demo composition root."""

    def __init__(self) -> None:
        self._sessions: dict[str, PersistedSession] = {}
        self._snapshots: dict[str, PersistedSnapshot] = {}
        self._creation_keys: dict[tuple[str, str], str] = {}
        self._turn_requests: dict[tuple[str, str], PersistedTurnRequest] = {}
        self._narrative_jobs: dict[str, NarrativeJob] = {}
        self._events: list[DomainEvent] = []
        self._provider_progress: dict[str, int] = {}
        self._controller_bindings: dict[str, StoredControllerBindingRecord] = {}
        self._player_character_id_allocations: dict[
            str, StoredPlayerCharacterIdAllocationRecord
        ] = {}
        self._player_character_revisions: dict[
            tuple[str, int], StoredPlayerCharacterRevisionRecord
        ] = {}
        self._player_character_current: dict[
            str, StoredCurrentPlayerCharacterRecord
        ] = {}
        self._player_character_creation_receipts: dict[
            tuple[str, str, str], StoredCreationReceiptRecord
        ] = {}
        self._player_character_mutation_receipts: dict[
            tuple[str, str, str], StoredMutationReceiptRecord
        ] = {}
        self._run_revisions: dict[
            tuple[str, int], StoredRunRevisionRecord
        ] = {}
        self._run_current: dict[str, StoredCurrentRunRecord] = {}
        self._run_participations: dict[
            str, StoredRunSessionParticipationRecord
        ] = {}
        self._run_creation_receipts: dict[
            tuple[str, str], StoredRunCreationReceiptRecord
        ] = {}
        self._run_mutation_receipts: dict[
            tuple[str, str, str], StoredRunMutationReceiptRecord
        ] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._controller_locks: dict[str, asyncio.Lock] = {}
        self._player_character_locks: dict[str, asyncio.Lock] = {}
        self._run_locks: dict[str, asyncio.Lock] = {}
        self._commit_lock = asyncio.Lock()
        self._active_uows = 0

    def unit_of_work(self) -> DemoUnitOfWork:
        return DemoUnitOfWork(self)

    @property
    def active_uows(self) -> int:
        return self._active_uows

    @property
    def any_session_lock_held(self) -> bool:
        return any(lock.locked() for lock in self._session_locks.values())

    def session_lock_held(self, session_id: str) -> bool:
        lock = self._session_locks.get(session_id)
        return lock is not None and lock.locked()

    def snapshot(self) -> DemoStoreSnapshot:
        return DemoStoreSnapshot(
            sessions=deepcopy(self._sessions),
            snapshots=deepcopy(self._snapshots),
            creation_keys=deepcopy(self._creation_keys),
            turn_requests=deepcopy(self._turn_requests),
            narrative_jobs={
                key: _clone_job(value) for key, value in self._narrative_jobs.items()
            },
            events=deepcopy(tuple(self._events)),
            provider_progress=dict(self._provider_progress),
            controller_bindings=deepcopy(self._controller_bindings),
            player_character_id_allocations=deepcopy(
                self._player_character_id_allocations
            ),
            player_character_revisions=deepcopy(
                self._player_character_revisions
            ),
            player_character_current=deepcopy(self._player_character_current),
            player_character_creation_receipts=deepcopy(
                self._player_character_creation_receipts
            ),
            player_character_mutation_receipts=deepcopy(
                self._player_character_mutation_receipts
            ),
            run_revisions=deepcopy(self._run_revisions),
            run_current=deepcopy(self._run_current),
            run_participations=deepcopy(self._run_participations),
            run_creation_receipts=deepcopy(self._run_creation_receipts),
            run_mutation_receipts=deepcopy(self._run_mutation_receipts),
        )


@dataclass(slots=True)
class _StateUpdate:
    session: GameSession
    expected_version: int
    next_version: int
    state: dict[str, Any]


@dataclass(slots=True)
class _JobReplacement:
    job: NarrativeJob
    expected_status: NarrativeJobStatus
    expected_lease_token: str | None
    expected_lease_owner: str | None


@dataclass(frozen=True, slots=True)
class _ProviderProgressUpdate:
    session_id: str
    expected_progress: int
    next_progress: int


@dataclass(slots=True)
class _AuthorityMaps:
    controller_bindings: dict[str, StoredControllerBindingRecord]
    player_character_id_allocations: dict[
        str, StoredPlayerCharacterIdAllocationRecord
    ]
    player_character_revisions: dict[
        tuple[str, int], StoredPlayerCharacterRevisionRecord
    ]
    player_character_current: dict[str, StoredCurrentPlayerCharacterRecord]
    player_character_creation_receipts: dict[
        tuple[str, str, str], StoredCreationReceiptRecord
    ]
    player_character_mutation_receipts: dict[
        tuple[str, str, str], StoredMutationReceiptRecord
    ]
    run_revisions: dict[tuple[str, int], StoredRunRevisionRecord]
    run_current: dict[str, StoredCurrentRunRecord]
    run_participations: dict[str, StoredRunSessionParticipationRecord]
    run_creation_receipts: dict[
        tuple[str, str], StoredRunCreationReceiptRecord
    ]
    run_mutation_receipts: dict[
        tuple[str, str, str], StoredRunMutationReceiptRecord
    ]


def _character_creation_key(key: CreationReceiptKey) -> tuple[str, str, str]:
    return (
        key.controller_binding.value,
        key.operation_namespace.value,
        key.operation_id.value,
    )


def _character_mutation_key(key: MutationReceiptKey) -> tuple[str, str, str]:
    return (
        key.player_character_id.value,
        key.operation_namespace.value,
        key.operation_id.value,
    )


def _run_creation_key(key: RunReceiptKey) -> tuple[str, str]:
    return key.operation_namespace.value, key.operation_id.value


def _run_mutation_key(key: RunReceiptKey) -> tuple[str, str, str]:
    if key.run_id is None:
        raise ValueError("Run mutation receipt requires a Run identity")
    return key.run_id.value, key.operation_namespace.value, key.operation_id.value


def _stored_character_revision(
    record: CanonicalPlayerCharacter,
    *,
    created_at: datetime,
) -> StoredPlayerCharacterRevisionRecord:
    record = validate_canonical_player_character(record)
    provenance = record.authority_provenance
    return StoredPlayerCharacterRevisionRecord(
        player_character_id=record.player_character_id,
        record_revision=record.record_revision.value,
        contract_version=record.contract_version.value,
        controller_binding=record.controller_binding,
        lifecycle=record.lifecycle.value,
        prior_revision=(
            provenance.prior_revision.value
            if provenance.prior_revision is not None
            else None
        ),
        mutation_kind=provenance.mutation_kind.value,
        authority_class=provenance.authority_class.value,
        source_reference=provenance.source_reference,
        record_canonical=canonical_record_to_storage_bytes(record),
        created_at=created_at,
    )


def _stored_character_current(
    record: CanonicalPlayerCharacter,
    *,
    created_at: datetime,
    updated_at: datetime | None = None,
) -> StoredCurrentPlayerCharacterRecord:
    record = validate_canonical_player_character(record)
    return StoredCurrentPlayerCharacterRecord(
        player_character_id=record.player_character_id,
        contract_version=record.contract_version.value,
        record_revision=record.record_revision.value,
        controller_binding=record.controller_binding,
        lifecycle=record.lifecycle.value,
        record_canonical=canonical_record_to_storage_bytes(record),
        created_at=created_at,
        updated_at=updated_at or created_at,
    )


def _run_core_values(run: CanonicalRun) -> dict[str, Any]:
    run = validate_canonical_run(run)
    creation = run.creation_provenance
    current = run.current_mutation_provenance
    binding = run.player_character_binding
    return {
        "run_id": run.run_id,
        "continuous_story_line_id": run.continuous_story_line_id,
        "lifecycle_status": run.lifecycle_status.value,
        "state_version": run.state_version.value,
        "creation_operation_id": creation.operation_id,
        "creation_source_reference": creation.source_reference,
        "creation_occurred_at": creation.occurred_at,
        "prior_state_version": (
            current.prior_state_version.value
            if current.prior_state_version is not None
            else None
        ),
        "mutation_kind": current.mutation_kind.value,
        "operation_id": current.operation_id,
        "source_reference": current.source_reference,
        "occurred_at": current.occurred_at,
        "binding_player_character_id": (
            binding.applicable_character_reference.player_character_id.value
            if binding is not None
            else None
        ),
        "binding_contract_version": (
            binding.applicable_character_reference.contract_version.value
            if binding is not None
            else None
        ),
        "binding_record_revision": (
            binding.applicable_character_reference.record_revision.value
            if binding is not None
            else None
        ),
        "binding_state": binding.binding_state if binding is not None else None,
        "binding_operation_id": (
            binding.binding_operation_id.value if binding is not None else None
        ),
        "binding_authority_source_ref": (
            binding.binding_authority_source_ref.value
            if binding is not None
            else None
        ),
        "bound_at": binding.bound_at if binding is not None else None,
        "inactivated_at": binding.inactivated_at if binding is not None else None,
    }


def _stored_run_revision(
    run: CanonicalRun,
    *,
    created_at: datetime,
) -> StoredRunRevisionRecord:
    return StoredRunRevisionRecord(
        **_run_core_values(run),
        active_player_character_id=None,
        created_at=created_at,
    )


def _stored_run_current(
    run: CanonicalRun,
    *,
    created_at: datetime,
    updated_at: datetime | None = None,
) -> StoredCurrentRunRecord:
    binding = run.player_character_binding
    return StoredCurrentRunRecord(
        **_run_core_values(run),
        active_player_character_id=(
            binding.applicable_character_reference.player_character_id.value
            if binding is not None
            else None
        ),
        created_at=created_at,
        updated_at=updated_at or created_at,
    )


def _participations_for_run(
    maps: _AuthorityMaps,
    run_id: RunId,
    *,
    through_version: int | None = None,
) -> tuple[RunSessionParticipationReference, ...]:
    stored = tuple(
        value
        for value in maps.run_participations.values()
        if value.run_id == run_id
        and (
            through_version is None
            or value.joined_state_version <= through_version
        )
    )
    return tuple(
        participation_from_storage(value)
        for value in sorted(
            stored,
            key=lambda item: (item.joined_state_version, item.session_id),
        )
    )


def _character_from_maps(
    maps: _AuthorityMaps,
    player_character_id: PlayerCharacterId,
) -> CanonicalPlayerCharacter | None:
    identity = player_character_id.value
    current = maps.player_character_current.get(identity)
    has_evidence = (
        identity in maps.player_character_id_allocations
        or any(key[0] == identity for key in maps.player_character_revisions)
        or any(
            item.result_player_character_id == player_character_id
            for item in maps.player_character_creation_receipts.values()
        )
        or any(key[0] == identity for key in maps.player_character_mutation_receipts)
    )
    if current is None:
        if has_evidence:
            raise PlayerCharacterStoredRecordIntegrityError(
                "player-character current record is missing"
            )
        return None
    if current.player_character_id != player_character_id:
        raise PlayerCharacterStoredRecordIntegrityError(
            "current player-character lookup identity is mismatched"
        )
    creation_receipts = tuple(
        item
        for item in maps.player_character_creation_receipts.values()
        if item.result_player_character_id == player_character_id
    )
    if len(creation_receipts) > 1:
        raise PlayerCharacterStoredRecordIntegrityError(
            "player-character has duplicate creation receipt evidence"
        )
    revisions = tuple(
        item
        for (stored_id, _), item in sorted(
            maps.player_character_revisions.items(),
            key=lambda pair: pair[0],
        )
        if stored_id == identity
    )
    mutation_receipts = tuple(
        item
        for (stored_id, _, _), item in sorted(
            maps.player_character_mutation_receipts.items(),
            key=lambda pair: (pair[1].resulting_revision, pair[0]),
        )
        if stored_id == identity
    )
    validate_stored_player_character_record_set(
        creation_receipt=(creation_receipts[0] if creation_receipts else None),
        mutation_receipts=mutation_receipts,
        revisions=revisions,
        current=current,
        controller_binding=maps.controller_bindings.get(
            current.controller_binding.value
        ),
        allocation=maps.player_character_id_allocations.get(identity),
    )
    return canonical_record_from_current_storage(current)


def _run_at_revision(
    maps: _AuthorityMaps,
    run_id: RunId,
    state_version: int,
) -> CanonicalRun:
    stored = maps.run_revisions.get((run_id.value, state_version))
    if stored is None:
        raise RunStoredRecordIntegrityError("referenced Run revision is missing")
    return canonical_run_from_revision_storage(
        stored,
        participations=_participations_for_run(
            maps,
            run_id,
            through_version=state_version,
        ),
    )


def _run_from_maps(
    maps: _AuthorityMaps,
    run_id: RunId,
) -> CanonicalRun | None:
    identity = run_id.value
    current = maps.run_current.get(identity)
    has_evidence = (
        any(key[0] == identity for key in maps.run_revisions)
        or any(item.run_id == run_id for item in maps.run_participations.values())
        or any(
            item.result_run_id == run_id
            for item in maps.run_creation_receipts.values()
        )
        or any(key[0] == identity for key in maps.run_mutation_receipts)
    )
    if current is None:
        if has_evidence:
            raise RunStoredRecordIntegrityError("current Run record is missing")
        return None
    if current.run_id != run_id:
        raise RunStoredRecordIntegrityError(
            "current Run lookup identity is mismatched"
        )
    creations = tuple(
        item
        for item in maps.run_creation_receipts.values()
        if item.result_run_id == run_id
    )
    if len(creations) > 1:
        raise RunStoredRecordIntegrityError(
            "Run has duplicate creation receipt evidence"
        )
    revisions = tuple(
        item
        for (stored_id, _), item in sorted(
            maps.run_revisions.items(), key=lambda pair: pair[0]
        )
        if stored_id == identity
    )
    mutation_receipts = tuple(
        item
        for (stored_id, _, _), item in sorted(
            maps.run_mutation_receipts.items(),
            key=lambda pair: (pair[1].resulting_state_version, pair[0]),
        )
        if stored_id == identity
    )
    participation_records = tuple(
        item
        for item in maps.run_participations.values()
        if item.run_id == run_id
    )
    referenced_character = None
    if (
        current.binding_player_character_id is not None
        and current.binding_record_revision is not None
    ):
        stored_character = maps.player_character_revisions.get(
            (
                current.binding_player_character_id,
                current.binding_record_revision,
            )
        )
        if stored_character is not None:
            try:
                referenced_character = canonical_record_from_revision_storage(
                    stored_character
                )
            except PlayerCharacterStoredRecordIntegrityError as exc:
                raise RunStoredRecordIntegrityError(
                    "referenced immutable player-character revision is invalid"
                ) from exc
    return validate_stored_run_record_set(
        creation_receipt=(creations[0] if creations else None),
        mutation_receipts=mutation_receipts,
        revisions=revisions,
        current=current,
        participations=tuple(
            sorted(
                participation_records,
                key=lambda item: (
                    item.joined_state_version,
                    item.session_id,
                ),
            )
        ),
        referenced_player_character_revision=referenced_character,
    )


def _active_run_for_character(
    maps: _AuthorityMaps,
    player_character_id: PlayerCharacterId,
) -> CanonicalRun | None:
    identity = player_character_id.value
    run_ids = {
        item.run_id.value
        for item in maps.run_current.values()
        if item.active_player_character_id == identity
        or item.binding_player_character_id == identity
    }
    run_ids.update(
        item.run_id.value
        for item in maps.run_revisions.values()
        if item.binding_player_character_id == identity
    )
    run_ids.update(
        item.run_id.value
        for item in maps.run_mutation_receipts.values()
        if item.result_player_character_id == identity
    )
    if not run_ids:
        return None
    if len(run_ids) != 1:
        raise RunStoredRecordIntegrityError(
            "player character has contradictory surviving binding evidence"
        )
    run = _run_from_maps(maps, RunId(value=next(iter(run_ids))))
    if run is None:
        raise RunStoredRecordIntegrityError(
            "active binding has no canonical Run"
        )
    binding = run.player_character_binding
    if (
        not run.lifecycle_status.is_active_line
        or binding is None
        or binding.binding_state != "active"
        or binding.inactivated_at is not None
        or binding.applicable_character_reference.player_character_id
        != player_character_id
    ):
        raise RunStoredRecordIntegrityError(
            "surviving binding evidence is not one canonical active binding"
        )
    return run


def _character_mutation_evidence(
    receipt: StoredMutationSuccessReceipt,
    *,
    before: CanonicalPlayerCharacter,
    after: CanonicalPlayerCharacter,
) -> bytes:
    result = receipt.result
    provenance = after.authority_provenance
    operation_id = receipt.key.operation_id
    applicable_reference = ApplicableCharacterReference(
        player_character_id=before.player_character_id,
        contract_version=before.contract_version,
        record_revision=before.record_revision,
    )
    confirmation = None
    final_death_evidence = None
    if result.command_kind is PlayerCharacterMutationKind.RETIRE:
        confirmation = PlayerConfirmation(
            player_character_id=before.player_character_id,
            expected_revision=before.record_revision,
            operation_id=operation_id,
            mutation_kind=result.command_kind,
            source_reference=provenance.source_reference,
        )
    elif result.command_kind is PlayerCharacterMutationKind.FINAL_DEATH:
        final_death_evidence = TrustedFinalDeathEvidence(
            player_character_id=before.player_character_id,
            expected_revision=before.record_revision,
            operation_id=operation_id,
            source_reference=provenance.source_reference,
        )
    else:
        raise PlayerCharacterStoredRecordIntegrityError(
            "mutation receipt has an unavailable command kind"
        )
    try:
        command = CharacterMutationCommand(
            contract_version=before.contract_version,
            command_kind=result.command_kind,
            target_player_character_id=before.player_character_id,
            expected_revision=before.record_revision,
            applicable_reference=applicable_reference,
            confirmation=confirmation,
            final_death_evidence=final_death_evidence,
        )
        return mutation_operation_evidence_to_storage_bytes(command)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PlayerCharacterStoredRecordIntegrityError(
            "mutation receipt operation evidence is inconsistent"
        ) from exc


class DemoControllerBindingRegistryRepository(
    ControllerBindingRegistryRepository
):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, controller_binding: ControllerBindingRef
    ) -> ControllerBindingRef | None:
        self._uow._ensure_open()
        stored = self._uow._visible_authority_maps().controller_bindings.get(
            controller_binding.value
        )
        if stored is None:
            return None
        if stored.controller_binding != controller_binding:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored controller-binding lookup identity is mismatched"
            )
        return ControllerBindingRef(value=stored.controller_binding.value)

    async def add(
        self,
        controller_binding: ControllerBindingRef,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        key = controller_binding.value
        maps = self._uow._visible_authority_maps()
        if key in maps.controller_bindings:
            raise ControllerBindingUniquenessConflictError(
                "controller-binding insertion conflict"
            )
        self._uow._pending_controller_bindings[key] = (
            StoredControllerBindingRecord(
                controller_binding=controller_binding,
                created_at=created_at,
            )
        )

    async def lock(
        self, controller_binding: ControllerBindingRef
    ) -> ControllerBindingRef | None:
        self._uow._ensure_open()
        await self._uow._acquire_controller_lock(controller_binding.value)
        return await self.get(controller_binding)


class DemoPlayerCharacterRepository(PlayerCharacterRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def allocation_exists(
        self, player_character_id: PlayerCharacterId
    ) -> bool:
        self._uow._ensure_open()
        return (
            player_character_id.value
            in self._uow._visible_authority_maps().player_character_id_allocations
        )

    async def add_allocation(
        self,
        player_character_id: PlayerCharacterId,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        key = player_character_id.value
        maps = self._uow._visible_authority_maps()
        if key in maps.player_character_id_allocations:
            raise PlayerCharacterRepositoryConflictError(
                "player-character allocation conflict"
            )
        self._uow._pending_player_character_id_allocations[key] = (
            StoredPlayerCharacterIdAllocationRecord(
                player_character_id=player_character_id,
                created_at=created_at,
            )
        )

    async def get(
        self, player_character_id: PlayerCharacterId
    ) -> CanonicalPlayerCharacter | None:
        self._uow._ensure_open()
        return _character_from_maps(
            self._uow._visible_authority_maps(), player_character_id
        )

    async def get_for_update(
        self, player_character_id: PlayerCharacterId
    ) -> CanonicalPlayerCharacter | None:
        self._uow._ensure_open()
        await self._uow._acquire_player_character_lock(
            player_character_id.value
        )
        return await self.get(player_character_id)

    async def list_eligible_for_run_entry(
        self,
        controller_binding: ControllerBindingRef,
        *,
        limit: int,
    ) -> tuple[CanonicalPlayerCharacter, ...]:
        self._uow._ensure_open()
        if type(limit) is not int or limit < 1 or limit > 33:
            raise ValueError(
                "eligible-character discovery limit is outside its bound"
            )
        maps = self._uow._visible_authority_maps()
        records: list[CanonicalPlayerCharacter] = []
        for identity, stored in sorted(maps.player_character_current.items()):
            if stored.controller_binding != controller_binding:
                continue
            record = _character_from_maps(maps, PlayerCharacterId(value=identity))
            if record is None:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery current record is missing"
                )
            if record.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
                continue
            try:
                occupied = _active_run_for_character(
                    maps, record.player_character_id
                )
            except RunStoredRecordIntegrityError as exc:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery active binding evidence is invalid"
                ) from exc
            if occupied is None:
                records.append(record)
            if len(records) == limit:
                break
        return tuple(records)

    async def add_initial(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        record = validate_canonical_player_character(record)
        if record.record_revision.value != 1:
            raise PlayerCharacterStoredRecordIntegrityError(
                "initial player-character record is inconsistent"
            )
        maps = self._uow._visible_authority_maps()
        identity = record.player_character_id.value
        revision_key = (identity, 1)
        if (
            revision_key in maps.player_character_revisions
            or identity in maps.player_character_current
        ):
            raise PlayerCharacterRepositoryConflictError(
                "initial player-character record conflict"
            )
        if (
            record.controller_binding.value not in maps.controller_bindings
            or identity not in maps.player_character_id_allocations
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "initial player-character companions are missing"
            )
        revision = _stored_character_revision(record, created_at=created_at)
        current = _stored_character_current(record, created_at=created_at)
        if (
            canonical_record_from_revision_storage(revision) != record
            or canonical_record_from_current_storage(current) != record
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "initial player-character storage mapping is inconsistent"
            )
        self._uow._pending_player_character_revisions[revision_key] = revision
        self._uow._pending_player_character_current[identity] = current
        self._uow._pending_player_character_current_expected[identity] = None

    async def append_revision(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        record = validate_canonical_player_character(record)
        prior = record.authority_provenance.prior_revision
        if prior is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor player-character revision has no predecessor"
            )
        current = await self.get(record.player_character_id)
        if current is None:
            raise PlayerCharacterRepositoryConflictError(
                "successor player-character has no current record"
            )
        if (
            current.record_revision != prior
            or current.controller_binding != record.controller_binding
            or current.contract_version != record.contract_version
            or record.record_revision.value != prior.value + 1
        ):
            raise PlayerCharacterRepositoryConflictError(
                "successor player-character revision is stale"
            )
        key = (record.player_character_id.value, record.record_revision.value)
        if key in self._uow._visible_authority_maps().player_character_revisions:
            raise PlayerCharacterRepositoryConflictError(
                "player-character revision insertion conflict"
            )
        stored = _stored_character_revision(record, created_at=created_at)
        if canonical_record_from_revision_storage(stored) != record:
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor player-character storage mapping is inconsistent"
            )
        self._uow._pending_player_character_revisions[key] = stored

    async def compare_and_swap_current(
        self,
        record: CanonicalPlayerCharacter,
        *,
        expected_revision: int,
        created_at: datetime,
    ) -> bool:
        self._uow._ensure_open()
        record = validate_canonical_player_character(record)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("expected revision is outside its domain")
        expected = PlayerCharacterRevision(value=expected_revision)
        if (
            record.record_revision.value != expected_revision + 1
            or record.authority_provenance.prior_revision != expected
        ):
            raise ValueError(
                "expected revision does not match successor record"
            )
        maps = self._uow._visible_authority_maps()
        identity = record.player_character_id.value
        current = maps.player_character_current.get(identity)
        if current is None or current.record_revision != expected_revision:
            return False
        revision = maps.player_character_revisions.get(
            (identity, record.record_revision.value)
        )
        if (
            revision is None
            or canonical_record_from_revision_storage(revision) != record
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor revision does not match current candidate"
            )
        if identity not in self._uow._pending_player_character_current_expected:
            self._uow._pending_player_character_current_expected[identity] = (
                expected_revision
            )
        self._uow._pending_player_character_current[identity] = (
            _stored_character_current(
                record,
                created_at=current.created_at,
                updated_at=created_at,
            )
        )
        return True


class DemoPlayerCharacterCreationReceiptRepository(
    PlayerCharacterCreationReceiptRepository
):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, key: CreationReceiptKey
    ) -> StoredCreationSuccessReceipt | None:
        self._uow._ensure_open()
        stored = (
            self._uow._visible_authority_maps()
            .player_character_creation_receipts.get(
                _character_creation_key(key)
            )
        )
        if stored is None:
            return None
        receipt = creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt lookup identity is mismatched"
            )
        if (
            _character_from_maps(
                self._uow._visible_authority_maps(),
                receipt.result.player_character_id,
            )
            is None
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt result family is missing"
            )
        return receipt

    async def add(
        self,
        receipt: StoredCreationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        maps = self._uow._visible_authority_maps()
        key = _character_creation_key(receipt.key)
        result = receipt.result
        if key in maps.player_character_creation_receipts or any(
            item.result_player_character_id == result.player_character_id
            and item.resulting_revision == result.resulting_revision.value
            for item in maps.player_character_creation_receipts.values()
        ):
            raise PlayerCharacterRepositoryConflictError(
                "creation receipt unique-race conflict"
            )
        revision = maps.player_character_revisions.get(
            (result.player_character_id.value, result.resulting_revision.value)
        )
        if revision is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt result revision is missing"
            )
        record = canonical_record_from_revision_storage(revision)
        command = CharacterCreationCommand(
            contract_version=record.contract_version,
            character_core=record.character_core,
            narration_preferences=record.narration_preferences,
        )
        stored = StoredCreationReceiptRecord(
            controller_binding=receipt.key.controller_binding,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id.value,
            fingerprint=fingerprint_to_storage_bytes(receipt.fingerprint),
            command_kind=receipt.command_kind,
            result_schema_version=receipt.result_schema_version,
            result_player_character_id=result.player_character_id,
            result_contract_version=result.contract_version.value,
            resulting_revision=result.resulting_revision.value,
            resulting_lifecycle=result.resulting_lifecycle.value,
            result_record_fingerprint=canonical_state_record_fingerprint(record),
            receipt_canonical=creation_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=(
                creation_operation_evidence_to_storage_bytes(
                    command,
                    source_reference=record.authority_provenance.source_reference,
                )
            ),
            created_at=created_at,
        )
        if creation_receipt_from_storage(stored) != receipt:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt storage mapping is inconsistent"
            )
        trial = self._uow._visible_authority_maps()
        trial.player_character_creation_receipts[key] = stored
        _character_from_maps(trial, result.player_character_id)
        self._uow._pending_player_character_creation_receipts[key] = stored


class DemoPlayerCharacterMutationReceiptRepository(
    PlayerCharacterMutationReceiptRepository
):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, key: MutationReceiptKey
    ) -> StoredMutationSuccessReceipt | None:
        self._uow._ensure_open()
        stored = (
            self._uow._visible_authority_maps()
            .player_character_mutation_receipts.get(
                _character_mutation_key(key)
            )
        )
        if stored is None:
            return None
        receipt = mutation_receipt_from_storage(stored)
        if receipt.key != key:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt lookup identity is mismatched"
            )
        if _character_from_maps(
            self._uow._visible_authority_maps(), key.player_character_id
        ) is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt character family is missing"
            )
        return receipt

    async def add(
        self,
        receipt: StoredMutationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        maps = self._uow._visible_authority_maps()
        key = _character_mutation_key(receipt.key)
        result = receipt.result
        if key in maps.player_character_mutation_receipts or any(
            item.player_character_id == receipt.key.player_character_id
            and item.resulting_revision == result.resulting_revision.value
            for item in maps.player_character_mutation_receipts.values()
        ):
            raise MutationReceiptUniquenessConflictError(
                "mutation receipt unique-race conflict"
            )
        expected_revision = result.resulting_revision.value - 1
        before_stored = maps.player_character_revisions.get(
            (receipt.key.player_character_id.value, expected_revision)
        )
        after_stored = maps.player_character_revisions.get(
            (
                receipt.key.player_character_id.value,
                result.resulting_revision.value,
            )
        )
        if before_stored is None or after_stored is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt revision evidence is missing"
            )
        before = canonical_record_from_revision_storage(before_stored)
        after = canonical_record_from_revision_storage(after_stored)
        stored = StoredMutationReceiptRecord(
            player_character_id=receipt.key.player_character_id,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id.value,
            fingerprint=fingerprint_to_storage_bytes(receipt.fingerprint),
            command_kind=receipt.command_kind,
            result_schema_version=receipt.result_schema_version,
            expected_revision=expected_revision,
            result_player_character_id=result.player_character_id,
            result_contract_version=result.contract_version.value,
            result_command_kind=result.command_kind.value,
            command_result=result.command_result.value,
            resulting_revision=result.resulting_revision.value,
            resulting_lifecycle=result.resulting_lifecycle.value,
            before_record_fingerprint=canonical_state_record_fingerprint(before),
            after_record_fingerprint=canonical_state_record_fingerprint(after),
            receipt_canonical=mutation_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=_character_mutation_evidence(
                receipt,
                before=before,
                after=after,
            ),
            created_at=created_at,
        )
        if mutation_receipt_from_storage(stored) != receipt:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt storage mapping is inconsistent"
            )
        trial = self._uow._visible_authority_maps()
        trial.player_character_mutation_receipts[key] = stored
        _character_from_maps(trial, receipt.key.player_character_id)
        self._uow._pending_player_character_mutation_receipts[key] = stored


class DemoRunRepository(RunRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(self, run_id: RunId) -> CanonicalRun | None:
        self._uow._ensure_open()
        return _run_from_maps(self._uow._visible_authority_maps(), run_id)

    async def get_for_update(self, run_id: RunId) -> CanonicalRun | None:
        self._uow._ensure_open()
        await self._uow._acquire_run_lock(run_id.value)
        return await self.get(run_id)

    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key: RunReceiptKey,
    ) -> RunSessionAttachmentLockEvidence | None:
        if (
            receipt_key.run_id != run_id
            or receipt_key.operation_namespace
            is not RunOperationNamespace.ATTACH_SESSION_V1
        ):
            raise ValueError(
                "Run attachment lock rejects mismatched receipt scope"
            )
        current = await self.get_for_update(run_id)
        if current is None:
            return None
        maps = self._uow._visible_authority_maps()
        stored = maps.run_mutation_receipts.get(_run_mutation_key(receipt_key))
        attachment_receipt = None
        if stored is not None:
            attachment_receipt = run_mutation_receipt_from_storage(stored)
            if attachment_receipt.key != receipt_key:
                raise RunStoredRecordIntegrityError(
                    "Run attachment receipt lookup identity is mismatched"
                )
        return RunSessionAttachmentLockEvidence(
            canonical_run=current,
            attachment_receipt=attachment_receipt,
        )

    async def get_active_for_player_character(
        self, player_character_id: PlayerCharacterId
    ) -> CanonicalRun | None:
        self._uow._ensure_open()
        return _active_run_for_character(
            self._uow._visible_authority_maps(), player_character_id
        )

    async def get_active_for_player_character_for_update(
        self, player_character_id: PlayerCharacterId
    ) -> CanonicalRun | None:
        self._uow._ensure_open()
        await self._uow._acquire_player_character_lock(
            player_character_id.value
        )
        run = await self.get_active_for_player_character(player_character_id)
        if run is None:
            return None
        await self._uow._acquire_run_lock(run.run_id.value)
        return await self.get_active_for_player_character(player_character_id)

    async def add_initial(
        self,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        run = validate_canonical_run(run)
        if (
            run.state_version.value != 1
            or run.current_mutation_provenance.mutation_kind
            is not RunMutationKind.CREATE
            or run.trusted_participation_references
            or run.player_character_binding is not None
        ):
            raise RunStoredRecordIntegrityError(
                "initial Run state is inconsistent"
            )
        maps = self._uow._visible_authority_maps()
        identity = run.run_id.value
        revision_key = (identity, 1)
        if revision_key in maps.run_revisions or identity in maps.run_current:
            raise RunRepositoryConflictError("initial Run record conflict")
        if any(
            item.continuous_story_line_id == run.continuous_story_line_id
            for item in maps.run_current.values()
        ):
            raise RunRepositoryConflictError(
                "continuous-story-line identity conflict"
            )
        revision = _stored_run_revision(run, created_at=created_at)
        current = _stored_run_current(run, created_at=created_at)
        if (
            canonical_run_from_revision_storage(
                revision, participations=()
            )
            != run
            or canonical_run_from_current_storage(current, participations=())
            != run
        ):
            raise RunStoredRecordIntegrityError(
                "initial Run storage mapping is inconsistent"
            )
        self._uow._pending_run_revisions[revision_key] = revision
        self._uow._pending_run_current[identity] = current
        self._uow._pending_run_current_expected[identity] = None

    async def append_revision(
        self,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        run = validate_canonical_run(run)
        prior = run.current_mutation_provenance.prior_state_version
        if (
            prior is None
            or run.current_mutation_provenance.mutation_kind
            not in {
                RunMutationKind.ATTACH_SESSION,
                RunMutationKind.BIND_PLAYER_CHARACTER,
            }
        ):
            raise RunStoredRecordIntegrityError(
                "successor Run revision is not an admitted mutation"
            )
        current = await self.get(run.run_id)
        if current is None:
            raise RunRepositoryConflictError(
                "successor Run has no current record"
            )
        if (
            current.state_version != prior
            or current.continuous_story_line_id
            != run.continuous_story_line_id
            or run.state_version.value != current.state_version.value + 1
        ):
            raise RunRepositoryConflictError("successor Run revision is stale")
        key = (run.run_id.value, run.state_version.value)
        if key in self._uow._visible_authority_maps().run_revisions:
            raise RunRepositoryConflictError(
                "Run revision insertion conflict"
            )
        stored = _stored_run_revision(run, created_at=created_at)
        if (
            canonical_run_from_revision_storage(
                stored,
                participations=run.trusted_participation_references,
            )
            != run
        ):
            raise RunStoredRecordIntegrityError(
                "successor Run storage mapping is inconsistent"
            )
        self._uow._pending_run_revisions[key] = stored

    async def compare_and_swap_current(
        self,
        run: CanonicalRun,
        *,
        expected_state_version: int,
        updated_at: datetime,
    ) -> bool:
        self._uow._ensure_open()
        run = validate_canonical_run(run)
        if (
            type(expected_state_version) is not int
            or expected_state_version < 1
            or run.state_version.value != expected_state_version + 1
            or run.current_mutation_provenance.prior_state_version is None
            or run.current_mutation_provenance.prior_state_version.value
            != expected_state_version
        ):
            raise ValueError(
                "expected Run version does not match successor state"
            )
        maps = self._uow._visible_authority_maps()
        identity = run.run_id.value
        current = maps.run_current.get(identity)
        if current is None or current.state_version != expected_state_version:
            return False
        if _run_at_revision(maps, run.run_id, run.state_version.value) != run:
            raise RunStoredRecordIntegrityError(
                "successor Run revision does not match current candidate"
            )
        binding = run.player_character_binding
        if binding is not None:
            character_id = (
                binding.applicable_character_reference.player_character_id.value
            )
            if any(
                other_id != identity
                and item.active_player_character_id == character_id
                for other_id, item in maps.run_current.items()
            ):
                raise _RunActiveBindingUniquenessConflictError(
                    "active player-character binding conflict"
                )
        if identity not in self._uow._pending_run_current_expected:
            self._uow._pending_run_current_expected[identity] = (
                expected_state_version
            )
        self._uow._pending_run_current[identity] = _stored_run_current(
            run,
            created_at=current.created_at,
            updated_at=updated_at,
        )
        return True


class DemoRunSessionParticipationRepository(
    RunSessionParticipationRepository
):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, session_id: str
    ) -> RunSessionParticipationReference | None:
        self._uow._ensure_open()
        maps = self._uow._visible_authority_maps()
        stored = maps.run_participations.get(session_id)
        if stored is None:
            return None
        participation = participation_from_storage(stored)
        if participation.session_id != session_id:
            raise RunStoredRecordIntegrityError(
                "Run participation lookup identity is mismatched"
            )
        run = _run_from_maps(maps, participation.run_id)
        if (
            run is None
            or participation not in run.trusted_participation_references
        ):
            raise RunStoredRecordIntegrityError(
                "Run participation is not bound to canonical state"
            )
        return participation

    async def add(
        self,
        participation: RunSessionParticipationReference,
        *,
        joined_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        maps = self._uow._visible_authority_maps()
        if participation.session_id in maps.run_participations:
            raise RunSessionParticipationUniquenessConflictError(
                "Run Session participation conflict"
            )
        stored = StoredRunSessionParticipationRecord(
            session_id=participation.session_id,
            run_id=participation.run_id,
            continuous_story_line_id=participation.continuous_story_line_id,
            joined_state_version=participation.joined_state_version.value,
            operation_id=participation.operation_id,
            source_reference=participation.source_reference,
            joined_at=joined_at,
        )
        if participation_from_storage(stored) != participation:
            raise RunStoredRecordIntegrityError(
                "Run participation storage mapping is inconsistent"
            )
        revision = maps.run_revisions.get(
            (
                participation.run_id.value,
                participation.joined_state_version.value,
            )
        )
        if (
            revision is None
            or revision.continuous_story_line_id
            != participation.continuous_story_line_id
            or revision.mutation_kind
            != RunMutationKind.ATTACH_SESSION.value
            or revision.operation_id != participation.operation_id
            or revision.source_reference != participation.source_reference
            or revision.occurred_at != joined_at
        ):
            raise RunStoredRecordIntegrityError(
                "Run participation does not bind its revision"
            )
        self._uow._pending_run_participations[participation.session_id] = stored


class DemoRunCreationReceiptRepository(RunCreationReceiptRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, key: RunReceiptKey
    ) -> StoredRunSuccessReceipt | None:
        stored = await self._get_stored(key)
        if stored is None:
            return None
        receipt = run_creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt lookup identity is mismatched"
            )
        if _run_from_maps(
            self._uow._visible_authority_maps(), receipt.result.run_id
        ) is None:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt family is missing"
            )
        return receipt

    async def get_with_evidence(
        self, key: RunReceiptKey
    ) -> StoredRunCreationEvidence | None:
        stored = await self._get_stored(key)
        if stored is None:
            return None
        receipt = run_creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt lookup identity is mismatched"
            )
        evidence = creation_evidence_from_storage(
            stored.operation_evidence_canonical
        )
        if _run_from_maps(
            self._uow._visible_authority_maps(), receipt.result.run_id
        ) is None:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt family is missing"
            )
        return StoredRunCreationEvidence(
            receipt=receipt,
            evidence=evidence,
            evidence_canonical=stored.operation_evidence_canonical,
        )

    async def add_with_evidence(
        self,
        receipt: StoredRunSuccessReceipt,
        evidence: RunEntryCreationEvidence,
        *,
        created_at: datetime,
    ) -> None:
        evidence_bytes, fingerprint = run_entry_creation_fingerprint(evidence)
        if receipt.fingerprint != fingerprint:
            raise RunStoredRecordIntegrityError(
                "P8 receipt fingerprint does not bind composite evidence"
            )
        await self._add_stored(
            receipt,
            operation_evidence_canonical=evidence_bytes,
            created_at=created_at,
        )

    async def add(
        self,
        receipt: StoredRunSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        maps = self._uow._visible_authority_maps()
        revision = _run_at_revision(
            maps,
            receipt.result.run_id,
            receipt.result.resulting_state_version.value,
        )
        await self._add_stored(
            receipt,
            operation_evidence_canonical=run_creation_evidence_bytes(
                CreateRunCommand(
                    source_reference=revision.creation_provenance.source_reference
                )
            ),
            created_at=created_at,
        )

    async def _get_stored(
        self, key: RunReceiptKey
    ) -> StoredRunCreationReceiptRecord | None:
        self._uow._ensure_open()
        if key.operation_namespace is not RunOperationNamespace.CREATE_V1:
            raise ValueError("Run creation receipt repository rejects namespace")
        return self._uow._visible_authority_maps().run_creation_receipts.get(
            _run_creation_key(key)
        )

    async def _add_stored(
        self,
        receipt: StoredRunSuccessReceipt,
        *,
        operation_evidence_canonical: bytes,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        if (
            receipt.key.operation_namespace
            is not RunOperationNamespace.CREATE_V1
            or receipt.command_kind is not RunMutationKind.CREATE
        ):
            raise ValueError("Run creation receipt repository rejects command")
        maps = self._uow._visible_authority_maps()
        key = _run_creation_key(receipt.key)
        if key in maps.run_creation_receipts or any(
            item.result_run_id == receipt.result.run_id
            for item in maps.run_creation_receipts.values()
        ):
            raise RunReceiptUniquenessConflictError(
                "Run creation receipt conflict"
            )
        result = receipt.result
        revision = _run_at_revision(
            maps, result.run_id, result.resulting_state_version.value
        )
        stored = StoredRunCreationReceiptRecord(
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id,
            fingerprint=run_fingerprint_to_storage_bytes(receipt.fingerprint),
            command_kind=receipt.command_kind.value,
            result_schema_version=result.result_schema_version,
            result_run_id=result.run_id,
            result_continuous_story_line_id=result.continuous_story_line_id,
            resulting_lifecycle_status=result.lifecycle_status.value,
            resulting_state_version=result.resulting_state_version.value,
            receipt_canonical=run_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=operation_evidence_canonical,
            created_at=created_at,
        )
        if (
            run_creation_receipt_from_storage(stored) != receipt
            or revision.creation_provenance.operation_id
            != receipt.key.operation_id
            or revision.creation_provenance.occurred_at != created_at
        ):
            raise RunStoredRecordIntegrityError(
                "Run creation receipt storage mapping is inconsistent"
            )
        trial = self._uow._visible_authority_maps()
        trial.run_creation_receipts[key] = stored
        _run_from_maps(trial, result.run_id)
        self._uow._pending_run_creation_receipts[key] = stored


class DemoRunMutationReceiptRepository(RunMutationReceiptRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get(
        self, key: RunReceiptKey
    ) -> StoredRunSuccessReceipt | None:
        self._uow._ensure_open()
        if key.operation_namespace not in {
            RunOperationNamespace.ATTACH_SESSION_V1,
            RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
        }:
            raise ValueError("minimum Run mutation repository rejects namespace")
        stored = self._uow._visible_authority_maps().run_mutation_receipts.get(
            _run_mutation_key(key)
        )
        if stored is None:
            return None
        receipt = run_mutation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run mutation receipt lookup identity is mismatched"
            )
        if key.run_id is None or _run_from_maps(
            self._uow._visible_authority_maps(), key.run_id
        ) is None:
            raise RunStoredRecordIntegrityError(
                "Run mutation receipt family is missing"
            )
        return receipt

    async def add(
        self,
        receipt: StoredRunSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        if (
            (
                receipt.key.operation_namespace,
                receipt.command_kind,
            )
            not in {
                (
                    RunOperationNamespace.ATTACH_SESSION_V1,
                    RunMutationKind.ATTACH_SESSION,
                ),
                (
                    RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
                    RunMutationKind.BIND_PLAYER_CHARACTER,
                ),
            }
            or receipt.key.run_id is None
        ):
            raise ValueError("minimum Run mutation repository rejects command")
        maps = self._uow._visible_authority_maps()
        key = _run_mutation_key(receipt.key)
        result = receipt.result
        if key in maps.run_mutation_receipts or any(
            item.run_id == receipt.key.run_id
            and item.resulting_state_version == result.resulting_state_version.value
            for item in maps.run_mutation_receipts.values()
        ):
            raise RunReceiptUniquenessConflictError(
                "Run mutation receipt conflict"
            )
        expected_version = result.resulting_state_version.value - 1
        before = _run_at_revision(maps, receipt.key.run_id, expected_version)
        after = _run_at_revision(
            maps,
            receipt.key.run_id,
            result.resulting_state_version.value,
        )
        participation = result.participation_reference
        character_reference = result.applicable_character_reference
        if receipt.command_kind is RunMutationKind.ATTACH_SESSION:
            if participation is None or character_reference is not None:
                raise RunStoredRecordIntegrityError(
                    "Run attachment receipt result shape is invalid"
                )
            command = (
                AttachSessionCommand(
                    run_id=after.run_id,
                    continuous_story_line_id=after.continuous_story_line_id,
                    session_id=participation.session_id,
                    expected_state_version=before.state_version,
                    source_reference=(
                        after.current_mutation_provenance.source_reference
                    ),
                )
            )
            operation_evidence = attach_operation_evidence_to_storage_bytes(
                command
            )
        else:
            if participation is not None or character_reference is None:
                raise RunStoredRecordIntegrityError(
                    "Run binding receipt result shape is invalid"
                )
            command = _RunBindCommand(
                run_id=after.run_id,
                continuous_story_line_id=after.continuous_story_line_id,
                target_player_character_id=character_reference.player_character_id,
                expected_state_version=before.state_version,
                source_reference=(
                    after.current_mutation_provenance.source_reference
                ),
            )
            operation_evidence = binding_operation_evidence_to_storage_bytes(
                command
            )
        stored = StoredRunMutationReceiptRecord(
            run_id=receipt.key.run_id,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id,
            fingerprint=run_fingerprint_to_storage_bytes(receipt.fingerprint),
            command_kind=receipt.command_kind.value,
            result_schema_version=result.result_schema_version,
            expected_state_version=expected_version,
            result_run_id=result.run_id,
            result_continuous_story_line_id=result.continuous_story_line_id,
            resulting_lifecycle_status=result.lifecycle_status.value,
            resulting_state_version=result.resulting_state_version.value,
            participation_session_id=(
                participation.session_id if participation is not None else None
            ),
            participation_operation_id=(
                participation.operation_id.value
                if participation is not None
                else None
            ),
            participation_source_reference=(
                participation.source_reference.value
                if participation is not None
                else None
            ),
            result_player_character_id=(
                character_reference.player_character_id.value
                if character_reference is not None
                else None
            ),
            result_character_contract_version=(
                character_reference.contract_version.value
                if character_reference is not None
                else None
            ),
            result_character_record_revision=(
                character_reference.record_revision.value
                if character_reference is not None
                else None
            ),
            receipt_canonical=run_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=operation_evidence,
            created_at=created_at,
        )
        if run_mutation_receipt_from_storage(stored) != receipt:
            raise RunStoredRecordIntegrityError(
                "Run mutation receipt storage mapping is inconsistent"
            )
        trial = self._uow._visible_authority_maps()
        trial.run_mutation_receipts[key] = stored
        _run_from_maps(trial, receipt.key.run_id)
        self._uow._pending_run_mutation_receipts[key] = stored


class DemoSessionRepository(GameSessionRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        if self._uow._pending_session is not None:
            raise ConcurrentSessionCreateError()
        persisted = PersistedSession(
            session=_clone_session(session),
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
            updated_at=created_at,
        )
        self._uow._pending_session = deepcopy(persisted)

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        del created_at
        self._uow._ensure_open()
        if self._uow._pending_snapshot is not None:
            raise OptimisticLockError("Demo initial snapshot is already staged")
        self._uow._pending_snapshot = (
            session.session_id,
            PersistedSnapshot(
                state_version=session.state_version,
                state=deepcopy(dict(state)),
            ),
        )

    async def add_initial(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        await self.add_initial_session(
            session,
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
        )
        await self.add_initial_snapshot(session, state=state, created_at=created_at)

    async def get_owned(
        self, session_id: str, player_id: str
    ) -> PersistedSession | None:
        self._uow._ensure_open()
        value = self._visible_session(session_id)
        if value is None or value.session.player_id != player_id:
            return None
        return deepcopy(value)

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ) -> PersistedSession | None:
        self._uow._ensure_open()
        await self._uow._acquire_session_lock(session_id)
        return await self.get_owned(session_id, player_id)

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        self._uow._ensure_open()
        pending = self._uow._pending_session
        if (
            pending is not None
            and pending.session.player_id == player_id
            and pending.creation_client_request_id == client_request_id
        ):
            return deepcopy(pending)
        session_id = self._store._creation_keys.get((player_id, client_request_id))
        value = self._store._sessions.get(session_id) if session_id else None
        return deepcopy(value) if value is not None else None

    async def lock_for_turn(self, session_id: str) -> bool:
        self._uow._ensure_open()
        await self._uow._acquire_session_lock(session_id)
        return self._visible_session(session_id) is not None

    async def get(self, session_id: str) -> GameSession | None:
        self._uow._ensure_open()
        value = self._visible_session(session_id)
        return _clone_session(value.session) if value is not None else None

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        self._uow._ensure_open()
        pending = self._uow._pending_snapshot
        if pending is not None and pending[0] == session_id:
            return deepcopy(pending[1])
        update = self._uow._pending_state_update
        if update is not None and update.session.session_id == session_id:
            return PersistedSnapshot(
                state_version=update.next_version,
                state=deepcopy(update.state),
            )
        value = self._store._snapshots.get(session_id)
        return deepcopy(value) if value is not None else None

    async def get_latest_snapshot_for_update(
        self, session_id: str,
    ) -> PersistedSnapshot | None:
        self._uow._ensure_open()
        await self._uow._acquire_session_lock(session_id)
        return await self.get_latest_snapshot(session_id)

    async def get_initialization_event(
        self, session_id: str
    ) -> DomainEvent | None:
        self._uow._ensure_open()
        matches = tuple(
            event
            for event in (*self._store._events, *self._uow._pending_events)
            if event.session_id == session_id and event.sequence_no == 1
        )
        if len(matches) > 1:
            raise ValueError("Demo Session has duplicate initialization events")
        return deepcopy(matches[0]) if matches else None

    async def next_event_sequence_no(self, session_id: str) -> int:
        self._uow._ensure_open()
        return (
            max(
                (
                    event.sequence_no
                    for event in (*self._store._events, *self._uow._pending_events)
                    if event.session_id == session_id
                ),
                default=0,
            )
            + 1
        )

    async def persist_events(
        self, events: Sequence[DomainEvent], *, state_version: int
    ) -> tuple[PersistedEventReceipt, ...]:
        self._uow._ensure_open()
        detached = deepcopy(tuple(events))
        existing_ids = {
            item.event_id for item in (*self._store._events, *self._uow._pending_events)
        }
        existing_sequences = {
            (item.session_id, item.sequence_no)
            for item in (*self._store._events, *self._uow._pending_events)
        }
        batch_ids: set[str] = set()
        batch_sequences: set[tuple[str, int]] = set()
        for event in detached:
            sequence_key = (event.session_id, event.sequence_no)
            if (
                event.event_id in existing_ids
                or event.event_id in batch_ids
                or sequence_key in existing_sequences
                or sequence_key in batch_sequences
                or event.sequence_no < 1
            ):
                raise OptimisticLockError("Demo event identity or sequence conflict")
            if self._visible_session(event.session_id) is None:
                raise ValueError("Demo event refers to an unknown session")
            batch_ids.add(event.event_id)
            batch_sequences.add(sequence_key)
        self._uow._pending_events = (*self._uow._pending_events, *detached)
        return tuple(
            _issue_persisted_event_receipt(event, state_version=state_version)
            for event in detached
        )

    async def save_snapshot_and_events(
        self,
        session: GameSession,
        state: Mapping[str, Any],
        events: Sequence[DomainEvent],
        expected_state_version: int,
    ) -> None:
        self._uow._ensure_open()
        current = self._visible_session(session.session_id)
        if current is None or current.session.state_version != expected_state_version:
            raise OptimisticLockError(
                f"session {session.session_id!r} state_version changed concurrently"
            )
        if self._uow._pending_state_update is not None:
            raise RuntimeError("one Demo UoW cannot stage multiple snapshot updates")
        if events:
            await self.persist_events(events, state_version=expected_state_version + 1)
        original_version = session.state_version
        next_version = expected_state_version + 1
        session.state_version = next_version
        self._uow._pending_session_versions.append((session, original_version))
        self._uow._pending_state_update = _StateUpdate(
            session=_clone_session(session),
            expected_version=expected_state_version,
            next_version=next_version,
            state=deepcopy(dict(state)),
        )

    def _visible_session(self, session_id: str) -> PersistedSession | None:
        pending = self._uow._pending_session
        if pending is not None and pending.session.session_id == session_id:
            return pending
        return self._store._sessions.get(session_id)


class DemoTurnRequestRepository(TurnRequestRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        self._uow._ensure_open()
        key = (session_id, client_request_id)
        pending = self._uow._pending_turn_requests.get(key)
        value = pending if pending is not None else self._store._turn_requests.get(key)
        return deepcopy(value) if value is not None else None

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        del route
        self._uow._ensure_open()
        key = (submission.session_id, submission.client_request_id)
        if key in self._store._turn_requests or key in self._uow._pending_turn_requests:
            raise ConcurrentTurnRequestError()
        self._uow._pending_turn_requests[key] = PersistedTurnRequest(
            turn_id=submission.turn_id,
            action_signature=action_signature,
            response=deepcopy(dict(response)),
        )


class DemoNarrativeJobRepository(NarrativeJobRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get_by_client_request_id(
        self,
        session_id: str,
        client_request_id: str,
        *,
        for_update: bool = False,
    ) -> NarrativeJob | None:
        del for_update
        self._uow._ensure_open()
        return next(
            (
                _clone_job(job)
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.client_request_id == client_request_id
            ),
            None,
        )

    async def get(
        self, job_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        del for_update
        self._uow._ensure_open()
        job = self._visible_jobs().get(job_id)
        return _clone_job(job) if job is not None else None

    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        self._uow._ensure_open()
        jobs = sorted(
            (
                job
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.status in ACTIVE_NARRATIVE_JOB_STATUSES
            ),
            key=lambda item: (item.created_at, item.job_id),
        )
        return _clone_job(jobs[0]) if jobs else None

    async def add(self, job: NarrativeJob) -> None:
        self._uow._ensure_open()
        visible = self._visible_jobs()
        if job.job_id in visible or any(
            item.session_id == job.session_id
            and item.client_request_id == job.client_request_id
            for item in visible.values()
        ):
            raise ConcurrentTurnRequestError()
        self._uow._pending_job_adds[job.job_id] = _clone_job(job)

    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        self._uow._ensure_open()
        current = self._visible_jobs().get(job.job_id)
        if not _job_matches(
            current,
            expected_status=expected_status,
            expected_lease_token=expected_lease_token,
            expected_lease_owner=expected_lease_owner,
        ):
            return False
        self._uow._pending_job_replacements.setdefault(job.job_id, []).append(
            _JobReplacement(
                job=_clone_job(job),
                expected_status=expected_status,
                expected_lease_token=expected_lease_token,
                expected_lease_owner=expected_lease_owner,
            )
        )
        return True

    async def recent_committed_texts(
        self, session_id: str, *, limit: int
    ) -> tuple[str, ...]:
        self._uow._ensure_open()
        if limit == 0:
            return ()
        jobs = sorted(
            (
                job
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.status is NarrativeJobStatus.COMMITTED
                and job.accepted_narrative_text is not None
            ),
            key=lambda item: (item.updated_at, item.job_id),
        )[-limit:]
        return tuple(
            job.accepted_narrative_text
            for job in jobs
            if job.accepted_narrative_text is not None
        )

    def _visible_jobs(self) -> dict[str, NarrativeJob]:
        visible = dict(self._store._narrative_jobs)
        visible.update(self._uow._pending_job_adds)
        visible.update(
            {
                key: replacements[-1].job
                for key, replacements in self._uow._pending_job_replacements.items()
            }
        )
        return visible


class DemoUnitOfWork(UnitOfWork):
    def __init__(self, store: DemoProcessStore) -> None:
        self._store = store
        self.sessions = DemoSessionRepository(store, self)
        self.turn_requests = DemoTurnRequestRepository(store, self)
        self.narrative_jobs = DemoNarrativeJobRepository(store, self)
        self.controller_bindings = DemoControllerBindingRegistryRepository(
            store, self
        )
        self.player_characters = DemoPlayerCharacterRepository(store, self)
        self.creation_receipts = (
            DemoPlayerCharacterCreationReceiptRepository(store, self)
        )
        self.mutation_receipts = (
            DemoPlayerCharacterMutationReceiptRepository(store, self)
        )
        self.runs = DemoRunRepository(store, self)
        self.run_participations = DemoRunSessionParticipationRepository(
            store, self
        )
        self.run_creation_receipts = DemoRunCreationReceiptRepository(
            store, self
        )
        self.run_mutation_receipts = DemoRunMutationReceiptRepository(
            store, self
        )
        self._pending_session: PersistedSession | None = None
        self._pending_snapshot: tuple[str, PersistedSnapshot] | None = None
        self._pending_state_update: _StateUpdate | None = None
        self._pending_events: tuple[DomainEvent, ...] = ()
        self._pending_turn_requests: dict[
            tuple[str, str], PersistedTurnRequest
        ] = {}
        self._pending_job_adds: dict[str, NarrativeJob] = {}
        self._pending_job_replacements: dict[
            str, list[_JobReplacement]
        ] = {}
        self._pending_session_versions: list[tuple[GameSession, int]] = []
        self._pending_provider_progress: _ProviderProgressUpdate | None = None
        self._pending_controller_bindings: dict[
            str, StoredControllerBindingRecord
        ] = {}
        self._pending_player_character_id_allocations: dict[
            str, StoredPlayerCharacterIdAllocationRecord
        ] = {}
        self._pending_player_character_revisions: dict[
            tuple[str, int], StoredPlayerCharacterRevisionRecord
        ] = {}
        self._pending_player_character_current: dict[
            str, StoredCurrentPlayerCharacterRecord
        ] = {}
        self._pending_player_character_current_expected: dict[
            str, int | None
        ] = {}
        self._pending_player_character_creation_receipts: dict[
            tuple[str, str, str], StoredCreationReceiptRecord
        ] = {}
        self._pending_player_character_mutation_receipts: dict[
            tuple[str, str, str], StoredMutationReceiptRecord
        ] = {}
        self._pending_run_revisions: dict[
            tuple[str, int], StoredRunRevisionRecord
        ] = {}
        self._pending_run_current: dict[str, StoredCurrentRunRecord] = {}
        self._pending_run_current_expected: dict[str, int | None] = {}
        self._pending_run_participations: dict[
            str, StoredRunSessionParticipationRecord
        ] = {}
        self._pending_run_creation_receipts: dict[
            tuple[str, str], StoredRunCreationReceiptRecord
        ] = {}
        self._pending_run_mutation_receipts: dict[
            tuple[str, str, str], StoredRunMutationReceiptRecord
        ] = {}
        self._held_session_lock: asyncio.Lock | None = None
        self._held_session_id: str | None = None
        self._held_controller_locks: dict[str, asyncio.Lock] = {}
        self._held_player_character_locks: dict[str, asyncio.Lock] = {}
        self._held_run_locks: dict[str, asyncio.Lock] = {}
        self._entered = False
        self._closed = False
        self._committed = False

    async def __aenter__(self) -> DemoUnitOfWork:
        if self._entered or self._closed:
            raise RuntimeError("Demo UnitOfWork cannot be re-entered")
        self._entered = True
        self._store._active_uows += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            self._release_all_locks()
            self._closed = True
            self._store._active_uows -= 1

    async def commit(self) -> None:
        self._ensure_open()
        if self._committed:
            raise RuntimeError("Demo UnitOfWork has already committed")
        try:
            async with self._store._commit_lock:
                self._publish_atomically()
        except BaseException:
            await self.rollback()
            raise
        self._pending_session_versions.clear()
        self._committed = True
        self._release_all_locks()

    async def rollback(self) -> None:
        self._ensure_open(allow_committed=True)
        for session, previous_version in reversed(self._pending_session_versions):
            session.state_version = previous_version
        self._pending_session_versions.clear()
        self._clear_staged()
        self._release_all_locks()
        self._committed = False

    async def _acquire_session_lock(self, session_id: str) -> None:
        self._ensure_open()
        if self._held_session_lock is not None:
            if self._held_session_id != session_id:
                raise RuntimeError("one Demo UoW cannot lock multiple sessions")
            return
        lock = self._store._session_locks.setdefault(session_id, asyncio.Lock())
        await lock.acquire()
        self._held_session_lock = lock
        self._held_session_id = session_id

    async def _acquire_controller_lock(self, controller_id: str) -> None:
        await self._acquire_authority_lock(
            self._store._controller_locks,
            self._held_controller_locks,
            controller_id,
        )

    async def _acquire_player_character_lock(
        self, player_character_id: str
    ) -> None:
        await self._acquire_authority_lock(
            self._store._player_character_locks,
            self._held_player_character_locks,
            player_character_id,
        )

    async def _acquire_run_lock(self, run_id: str) -> None:
        await self._acquire_authority_lock(
            self._store._run_locks,
            self._held_run_locks,
            run_id,
        )

    async def _acquire_authority_lock(
        self,
        registry: dict[str, asyncio.Lock],
        held: dict[str, asyncio.Lock],
        identity: str,
    ) -> None:
        self._ensure_open()
        if identity in held:
            return
        lock = registry.setdefault(identity, asyncio.Lock())
        await lock.acquire()
        held[identity] = lock

    def _release_all_locks(self) -> None:
        if self._held_session_lock is not None:
            self._held_session_lock.release()
            self._held_session_lock = None
            self._held_session_id = None
        for held in (
            self._held_run_locks,
            self._held_player_character_locks,
            self._held_controller_locks,
        ):
            for lock in reversed(tuple(held.values())):
                lock.release()
            held.clear()

    def _visible_authority_maps(self) -> _AuthorityMaps:
        maps = _AuthorityMaps(
            controller_bindings=dict(self._store._controller_bindings),
            player_character_id_allocations=dict(
                self._store._player_character_id_allocations
            ),
            player_character_revisions=dict(
                self._store._player_character_revisions
            ),
            player_character_current=dict(self._store._player_character_current),
            player_character_creation_receipts=dict(
                self._store._player_character_creation_receipts
            ),
            player_character_mutation_receipts=dict(
                self._store._player_character_mutation_receipts
            ),
            run_revisions=dict(self._store._run_revisions),
            run_current=dict(self._store._run_current),
            run_participations=dict(self._store._run_participations),
            run_creation_receipts=dict(self._store._run_creation_receipts),
            run_mutation_receipts=dict(self._store._run_mutation_receipts),
        )
        maps.controller_bindings.update(self._pending_controller_bindings)
        maps.player_character_id_allocations.update(
            self._pending_player_character_id_allocations
        )
        maps.player_character_revisions.update(
            self._pending_player_character_revisions
        )
        maps.player_character_current.update(
            self._pending_player_character_current
        )
        maps.player_character_creation_receipts.update(
            self._pending_player_character_creation_receipts
        )
        maps.player_character_mutation_receipts.update(
            self._pending_player_character_mutation_receipts
        )
        maps.run_revisions.update(self._pending_run_revisions)
        maps.run_current.update(self._pending_run_current)
        maps.run_participations.update(self._pending_run_participations)
        maps.run_creation_receipts.update(self._pending_run_creation_receipts)
        maps.run_mutation_receipts.update(self._pending_run_mutation_receipts)
        return maps

    def stage_provider_progress(
        self,
        session_id: str,
        *,
        expected_progress: int,
        next_progress: int,
    ) -> None:
        """Stage Demo-only Provider authority in the gameplay transaction."""

        self._ensure_open()
        if self._pending_provider_progress is not None:
            raise RuntimeError("one Demo UoW cannot stage multiple Provider advances")
        if (
            type(expected_progress) is not int
            or type(next_progress) is not int
            or expected_progress < 0
            or next_progress != expected_progress + 1
        ):
            raise ValueError("invalid Demo Provider progress transition")
        if self._store._provider_progress.get(session_id) != expected_progress:
            raise OptimisticLockError("Demo Provider progress changed concurrently")
        self._pending_provider_progress = _ProviderProgressUpdate(
            session_id=session_id,
            expected_progress=expected_progress,
            next_progress=next_progress,
        )

    def _publish_atomically(self) -> None:
        sessions = deepcopy(self._store._sessions)
        snapshots = deepcopy(self._store._snapshots)
        creation_keys = dict(self._store._creation_keys)
        turn_requests = deepcopy(self._store._turn_requests)
        jobs = {
            key: _clone_job(value) for key, value in self._store._narrative_jobs.items()
        }
        events = deepcopy(self._store._events)
        provider_progress = dict(self._store._provider_progress)
        authority = _AuthorityMaps(
            controller_bindings=deepcopy(self._store._controller_bindings),
            player_character_id_allocations=deepcopy(
                self._store._player_character_id_allocations
            ),
            player_character_revisions=deepcopy(
                self._store._player_character_revisions
            ),
            player_character_current=deepcopy(
                self._store._player_character_current
            ),
            player_character_creation_receipts=deepcopy(
                self._store._player_character_creation_receipts
            ),
            player_character_mutation_receipts=deepcopy(
                self._store._player_character_mutation_receipts
            ),
            run_revisions=deepcopy(self._store._run_revisions),
            run_current=deepcopy(self._store._run_current),
            run_participations=deepcopy(self._store._run_participations),
            run_creation_receipts=deepcopy(
                self._store._run_creation_receipts
            ),
            run_mutation_receipts=deepcopy(
                self._store._run_mutation_receipts
            ),
        )

        pending_session = self._pending_session
        if pending_session is not None:
            session_id = pending_session.session.session_id
            creation_id = pending_session.creation_client_request_id
            if creation_id is None:
                raise ValueError("Demo initial session requires a creation request ID")
            creation_key = (pending_session.session.player_id, creation_id)
            if session_id in sessions or creation_key in creation_keys:
                raise ConcurrentSessionCreateError()
            sessions[session_id] = deepcopy(pending_session)
            creation_keys[creation_key] = session_id
            provider_progress[session_id] = 0

        if self._pending_snapshot is not None:
            session_id, snapshot = self._pending_snapshot
            if session_id not in sessions:
                raise ValueError("Demo initial snapshot refers to an unknown session")
            if session_id in snapshots:
                raise OptimisticLockError("Demo initial snapshot already exists")
            snapshots[session_id] = deepcopy(snapshot)

        update = self._pending_state_update
        if update is not None:
            session_id = update.session.session_id
            current = sessions.get(session_id)
            current_snapshot = snapshots.get(session_id)
            if (
                current is None
                or current.session.state_version != update.expected_version
                or current_snapshot is None
                or current_snapshot.state_version != update.expected_version
            ):
                raise OptimisticLockError(
                    f"session {session_id!r} state changed before Demo commit"
                )
            updated_at = max(
                (
                    event.occurred_at
                    for event in self._pending_events
                    if event.session_id == session_id
                ),
                default=current.updated_at,
            )
            sessions[session_id] = replace(
                current,
                session=_clone_session(update.session),
                updated_at=updated_at,
            )
            snapshots[session_id] = PersistedSnapshot(
                state_version=update.next_version,
                state=deepcopy(update.state),
            )

        for key, value in self._pending_turn_requests.items():
            if key in turn_requests:
                raise ConcurrentTurnRequestError()
            if key[0] not in sessions:
                raise ValueError("Demo turn request refers to an unknown session")
            turn_requests[key] = deepcopy(value)

        for job_id, job in self._pending_job_adds.items():
            if job_id in jobs or any(
                item.session_id == job.session_id
                and item.client_request_id == job.client_request_id
                for item in jobs.values()
            ):
                raise ConcurrentTurnRequestError()
            if job.session_id not in sessions:
                raise ValueError("Demo narrative job refers to an unknown session")
            jobs[job_id] = _clone_job(job)

        for job_id, replacements in self._pending_job_replacements.items():
            current = jobs.get(job_id)
            for replacement in replacements:
                if not _job_matches(
                    current,
                    expected_status=replacement.expected_status,
                    expected_lease_token=replacement.expected_lease_token,
                    expected_lease_owner=replacement.expected_lease_owner,
                ):
                    raise OptimisticLockError(
                        "Demo narrative job fencing check failed"
                    )
                current = replacement.job
            assert current is not None
            jobs[job_id] = _clone_job(current)

        event_ids = {event.event_id for event in events}
        event_sequences = {(event.session_id, event.sequence_no) for event in events}
        for event in self._pending_events:
            key = (event.session_id, event.sequence_no)
            if event.event_id in event_ids or key in event_sequences:
                raise OptimisticLockError("Demo event identity or sequence conflict")
            if event.session_id not in sessions:
                raise ValueError("Demo event refers to an unknown session")
            event_ids.add(event.event_id)
            event_sequences.add(key)
            events.append(deepcopy(event))

        progress_update = self._pending_provider_progress
        if progress_update is not None:
            if progress_update.session_id not in sessions:
                raise ValueError("Demo Provider progress refers to an unknown session")
            if (
                provider_progress.get(progress_update.session_id)
                != progress_update.expected_progress
            ):
                raise OptimisticLockError("Demo Provider progress changed before commit")
            provider_progress[progress_update.session_id] = progress_update.next_progress

        if set(self._pending_controller_bindings) & set(
            authority.controller_bindings
        ):
            raise ControllerBindingUniquenessConflictError(
                "controller-binding insertion conflict"
            )
        if set(self._pending_player_character_id_allocations) & set(
            authority.player_character_id_allocations
        ):
            raise PlayerCharacterRepositoryConflictError(
                "player-character allocation conflict"
            )
        if set(self._pending_player_character_revisions) & set(
            authority.player_character_revisions
        ):
            raise PlayerCharacterRepositoryConflictError(
                "player-character revision insertion conflict"
            )
        if set(self._pending_player_character_creation_receipts) & set(
            authority.player_character_creation_receipts
        ) or any(
            pending.result_player_character_id
            == existing.result_player_character_id
            and pending.resulting_revision == existing.resulting_revision
            for pending in self._pending_player_character_creation_receipts.values()
            for existing in authority.player_character_creation_receipts.values()
        ):
            raise PlayerCharacterRepositoryConflictError(
                "creation receipt unique-race conflict"
            )
        if set(self._pending_player_character_mutation_receipts) & set(
            authority.player_character_mutation_receipts
        ) or any(
            pending.player_character_id == existing.player_character_id
            and pending.resulting_revision == existing.resulting_revision
            for pending in self._pending_player_character_mutation_receipts.values()
            for existing in authority.player_character_mutation_receipts.values()
        ):
            raise MutationReceiptUniquenessConflictError(
                "mutation receipt unique-race conflict"
            )
        for identity, expected in (
            self._pending_player_character_current_expected.items()
        ):
            current = authority.player_character_current.get(identity)
            if expected is None:
                if current is not None:
                    raise PlayerCharacterRepositoryConflictError(
                        "initial current player-character conflict"
                    )
            elif current is None or current.record_revision != expected:
                raise PlayerCharacterRepositoryConflictError(
                    "player-character current compare-and-swap conflict"
                )

        if set(self._pending_run_revisions) & set(authority.run_revisions):
            raise RunRepositoryConflictError("Run revision insertion conflict")
        if set(self._pending_run_participations) & set(
            authority.run_participations
        ):
            raise RunSessionParticipationUniquenessConflictError(
                "Run Session participation conflict"
            )
        if set(self._pending_run_creation_receipts) & set(
            authority.run_creation_receipts
        ) or any(
            pending.result_run_id == existing.result_run_id
            for pending in self._pending_run_creation_receipts.values()
            for existing in authority.run_creation_receipts.values()
        ):
            raise RunReceiptUniquenessConflictError(
                "Run creation receipt conflict"
            )
        if set(self._pending_run_mutation_receipts) & set(
            authority.run_mutation_receipts
        ) or any(
            pending.run_id == existing.run_id
            and pending.resulting_state_version
            == existing.resulting_state_version
            for pending in self._pending_run_mutation_receipts.values()
            for existing in authority.run_mutation_receipts.values()
        ):
            raise RunReceiptUniquenessConflictError(
                "Run mutation receipt conflict"
            )
        for identity, expected in self._pending_run_current_expected.items():
            current = authority.run_current.get(identity)
            if expected is None:
                if current is not None:
                    raise RunRepositoryConflictError(
                        "initial current Run conflict"
                    )
            elif current is None or current.state_version != expected:
                raise RunRepositoryConflictError(
                    "Run current compare-and-swap conflict"
                )

        authority.controller_bindings.update(
            deepcopy(self._pending_controller_bindings)
        )
        authority.player_character_id_allocations.update(
            deepcopy(self._pending_player_character_id_allocations)
        )
        authority.player_character_revisions.update(
            deepcopy(self._pending_player_character_revisions)
        )
        authority.player_character_current.update(
            deepcopy(self._pending_player_character_current)
        )
        authority.player_character_creation_receipts.update(
            deepcopy(self._pending_player_character_creation_receipts)
        )
        authority.player_character_mutation_receipts.update(
            deepcopy(self._pending_player_character_mutation_receipts)
        )
        authority.run_revisions.update(deepcopy(self._pending_run_revisions))
        authority.run_current.update(deepcopy(self._pending_run_current))
        authority.run_participations.update(
            deepcopy(self._pending_run_participations)
        )
        authority.run_creation_receipts.update(
            deepcopy(self._pending_run_creation_receipts)
        )
        authority.run_mutation_receipts.update(
            deepcopy(self._pending_run_mutation_receipts)
        )

        for key, value in authority.controller_bindings.items():
            if key != value.controller_binding.value:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "controller-binding map key is mismatched"
                )
        character_ids = set(authority.player_character_id_allocations)
        character_ids.update(authority.player_character_current)
        character_ids.update(key[0] for key in authority.player_character_revisions)
        character_ids.update(
            item.result_player_character_id.value
            for item in authority.player_character_creation_receipts.values()
        )
        character_ids.update(
            key[0] for key in authority.player_character_mutation_receipts
        )
        for identity in sorted(character_ids):
            if _character_from_maps(
                authority, PlayerCharacterId(value=identity)
            ) is None:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "player-character authoritative family is incomplete"
                )

        run_ids = set(authority.run_current)
        run_ids.update(key[0] for key in authority.run_revisions)
        run_ids.update(
            item.run_id.value for item in authority.run_participations.values()
        )
        run_ids.update(
            item.result_run_id.value
            for item in authority.run_creation_receipts.values()
        )
        run_ids.update(key[0] for key in authority.run_mutation_receipts)
        active_bindings: dict[str, str] = {}
        line_ids: set[str] = set()
        for identity in sorted(run_ids):
            run = _run_from_maps(authority, RunId(value=identity))
            if run is None:
                raise RunStoredRecordIntegrityError(
                    "Run authoritative family is incomplete"
                )
            line_identity = run.continuous_story_line_id.value
            if line_identity in line_ids:
                raise RunRepositoryConflictError(
                    "continuous-story-line identity conflict"
                )
            line_ids.add(line_identity)
            binding = run.player_character_binding
            if binding is not None and run.lifecycle_status.is_active_line:
                character_identity = (
                    binding.applicable_character_reference.player_character_id.value
                )
                if character_identity in active_bindings:
                    raise _RunActiveBindingUniquenessConflictError(
                        "active player-character binding conflict"
                    )
                active_bindings[character_identity] = identity
        for session_id, participation in authority.run_participations.items():
            if session_id != participation.session_id:
                raise RunStoredRecordIntegrityError(
                    "Run participation map key is mismatched"
                )
            if session_id not in sessions:
                raise RunStoredRecordIntegrityError(
                    "Run participation refers to an unknown Session"
                )

        self._store._sessions = sessions
        self._store._snapshots = snapshots
        self._store._creation_keys = creation_keys
        self._store._turn_requests = turn_requests
        self._store._narrative_jobs = jobs
        self._store._events = events
        self._store._provider_progress = provider_progress
        self._store._controller_bindings = authority.controller_bindings
        self._store._player_character_id_allocations = (
            authority.player_character_id_allocations
        )
        self._store._player_character_revisions = (
            authority.player_character_revisions
        )
        self._store._player_character_current = authority.player_character_current
        self._store._player_character_creation_receipts = (
            authority.player_character_creation_receipts
        )
        self._store._player_character_mutation_receipts = (
            authority.player_character_mutation_receipts
        )
        self._store._run_revisions = authority.run_revisions
        self._store._run_current = authority.run_current
        self._store._run_participations = authority.run_participations
        self._store._run_creation_receipts = authority.run_creation_receipts
        self._store._run_mutation_receipts = authority.run_mutation_receipts
        self._clear_staged()

    def _clear_staged(self) -> None:
        self._pending_session = None
        self._pending_snapshot = None
        self._pending_state_update = None
        self._pending_events = ()
        self._pending_turn_requests.clear()
        self._pending_job_adds.clear()
        self._pending_job_replacements.clear()
        self._pending_provider_progress = None
        self._pending_controller_bindings.clear()
        self._pending_player_character_id_allocations.clear()
        self._pending_player_character_revisions.clear()
        self._pending_player_character_current.clear()
        self._pending_player_character_current_expected.clear()
        self._pending_player_character_creation_receipts.clear()
        self._pending_player_character_mutation_receipts.clear()
        self._pending_run_revisions.clear()
        self._pending_run_current.clear()
        self._pending_run_current_expected.clear()
        self._pending_run_participations.clear()
        self._pending_run_creation_receipts.clear()
        self._pending_run_mutation_receipts.clear()

    def _ensure_open(self, *, allow_committed: bool = False) -> None:
        if not self._entered or self._closed:
            raise RuntimeError("Demo UnitOfWork is not active")
        if self._committed and not allow_committed:
            raise RuntimeError("Demo UnitOfWork has already committed")


def _job_matches(
    job: NarrativeJob | None,
    *,
    expected_status: NarrativeJobStatus,
    expected_lease_token: str | None,
    expected_lease_owner: str | None,
) -> bool:
    return (
        job is not None
        and job.status is expected_status
        and job.lease_token == expected_lease_token
        and job.lease_owner == expected_lease_owner
    )
