from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import String, and_, cast, func, or_, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.ports import (
    ControllerBindingRegistryRepository,
    GameSessionRepository,
    PlayerCharacterCreationReceiptRepository,
    PlayerCharacterMutationReceiptRepository,
    PlayerCharacterRepository,
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
    TurnRequestRepository,
    NarrativeJobRepository,
    RunCreationReceiptRepository,
    RunMutationReceiptRepository,
    RunPlayerCharacterBindingUniquenessConflictError,
    RunReceiptUniquenessConflictError,
    RunRepository,
    RunSessionAttachmentLockEvidence,
    RunSessionParticipationRepository,
    RunSessionParticipationUniquenessConflictError,
    StoredRunCreationEvidence,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunEntryCreationEvidence,
    RunOperationNamespace,
    RunReceiptKey,
    StoredRunSuccessReceipt,
    run_entry_creation_fingerprint,
    run_entry_evidence_bytes,
)
from deviation_protocol.application.player_character_operations import (
    CharacterCreationCommand,
    CharacterMutationCommand,
    CreationReceiptKey,
    MutationReceiptKey,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
)
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    ControllerBindingRef,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterMutationKind,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    PlayerConfirmation,
    TrustedFinalDeathEvidence,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunMutationKind,
    RunOperationId,
    RunSessionParticipationReference,
    validate_canonical_run,
)
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import (
    OptimisticLockError,
    PlayerCharacterControllerBindingConflictError,
    PlayerCharacterMutationReceiptConflictError,
    PlayerCharacterRepositoryConflictError,
    PlayerCharacterRepositoryError,
)
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    NarrativeJobRow,
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
    TurnRequestRow,
    utc_now,
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
    RunRepositoryError,
    RunStoredRecordIntegrityError,
    StoredCurrentRunRecord,
    StoredRunCreationReceiptRecord,
    StoredRunMutationReceiptRecord,
    StoredRunRevisionRecord,
    StoredRunSessionParticipationRecord,
    attach_operation_evidence_to_storage_bytes,
    binding_operation_evidence_to_storage_bytes,
    canonical_run_from_revision_storage,
    canonical_run_from_current_storage,
    creation_evidence_from_storage,
    creation_operation_evidence_to_storage_bytes as run_creation_evidence_bytes,
    creation_receipt_from_storage as run_creation_receipt_from_storage,
    fingerprint_to_storage_bytes as run_fingerprint_to_storage_bytes,
    mutation_receipt_from_storage as run_mutation_receipt_from_storage,
    participation_from_storage,
    run_receipt_to_storage_bytes,
    validate_stored_run_record_set,
)


def _as_utc(value: datetime) -> datetime:
    """Restore MySQL DATETIME values to the application UTC contract."""

    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


class SqlAlchemyGameSessionRepository(GameSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pending_session_versions: list[tuple[GameSession, int]] = []

    @staticmethod
    def _persisted(row: GameSessionRow) -> PersistedSession:
        return PersistedSession(
            session=GameSession(
                session_id=row.session_id,
                player_id=row.player_id,
                scenario_id=row.scenario_id,
                scenario_version=row.scenario_version,
                phase=row.phase,
                turn_number=row.turn_number,
                state_version=row.state_version,
                random_seed=row.random_seed,
            ),
            character_definition_id=row.character_definition_id,
            creation_client_request_id=row.creation_client_request_id,
            created_at=_as_utc(row.created_at),
            updated_at=_as_utc(row.updated_at),
        )

    async def get_owned(self, session_id: str, player_id: str) -> PersistedSession | None:
        row = await self._session.scalar(
            select(GameSessionRow).where(
                GameSessionRow.session_id == session_id,
                GameSessionRow.player_id == player_id,
            )
        )
        return self._persisted(row) if row is not None else None

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ) -> PersistedSession | None:
        row = await self._session.scalar(
            select(GameSessionRow)
            .where(
                GameSessionRow.session_id == session_id,
                GameSessionRow.player_id == player_id,
            )
            .with_for_update()
        )
        return self._persisted(row) if row is not None else None

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        row = await self._session.scalar(
            select(GameSessionRow).where(
                GameSessionRow.player_id == player_id,
                GameSessionRow.creation_client_request_id == client_request_id,
            )
        )
        return self._persisted(row) if row is not None else None

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
        await self.add_initial_snapshot(
            session, state=state, created_at=created_at
        )

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        session_row = GameSessionRow(
            session_id=session.session_id,
            player_id=session.player_id,
            creation_client_request_id=creation_client_request_id,
            character_definition_id=character_definition_id,
            scenario_id=session.scenario_id,
            scenario_version=session.scenario_version,
            phase=session.phase,
            turn_number=session.turn_number,
            state_version=session.state_version,
            random_seed=session.random_seed,
            created_at=created_at,
            updated_at=created_at,
        )
        self._session.add(session_row)
        try:
            await self._session.flush((session_row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentSessionCreateError from exc
            raise

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        self._session.add(
            GameSnapshotRow(
                session_id=session.session_id,
                state_version=session.state_version,
                state_json=dict(state),
                updated_at=created_at,
            )
        )

    async def lock_for_turn(self, session_id: str) -> bool:
        result = await self._session.execute(
            select(GameSessionRow.session_id)
            .where(GameSessionRow.session_id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none() is not None

    async def get(self, session_id: str) -> GameSession | None:
        row = await self._session.get(GameSessionRow, session_id)
        if row is None:
            return None
        return self._persisted(row).session

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        row = await self._session.get(GameSnapshotRow, session_id)
        if row is None:
            return None
        return PersistedSnapshot(
            state_version=row.state_version,
            state=dict(row.state_json),
        )

    async def get_latest_snapshot_for_update(
        self, session_id: str,
    ) -> PersistedSnapshot | None:
        row = await self._session.scalar(
            select(GameSnapshotRow)
            .where(GameSnapshotRow.session_id == session_id)
            .execution_options(populate_existing=True)
            .with_for_update()
        )
        if row is None:
            return None
        return PersistedSnapshot(
            state_version=row.state_version,
            state=dict(row.state_json),
        )

    async def get_initialization_event(self, session_id: str) -> DomainEvent | None:
        row = await self._session.scalar(
            select(DomainEventRow).where(
                DomainEventRow.session_id == session_id,
                DomainEventRow.sequence_no == 1,
            )
        )
        if row is None:
            return None
        return DomainEvent(
            event_id=row.event_id,
            session_id=row.session_id,
            turn_id=row.turn_id,
            sequence_no=row.sequence_no,
            event_type=row.event_type,
            payload=dict(row.payload_json),
            occurred_at=_as_utc(row.occurred_at),
        )

    async def next_event_sequence_no(self, session_id: str) -> int:
        latest = await self._session.scalar(
            select(func.max(DomainEventRow.sequence_no)).where(
                DomainEventRow.session_id == session_id
            )
        )
        return int(latest or 0) + 1

    async def persist_events(
        self,
        events: Sequence[DomainEvent],
        *,
        state_version: int,
    ) -> tuple[PersistedEventReceipt, ...]:
        rows = tuple(
            DomainEventRow(
                event_id=event.event_id,
                session_id=event.session_id,
                turn_id=event.turn_id,
                sequence_no=event.sequence_no,
                event_type=event.event_type,
                payload_json=dict(event.payload),
                occurred_at=event.occurred_at,
            )
            for event in events
        )
        if not rows:
            return ()
        self._session.add_all(rows)
        await self._session.flush(rows)
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
        next_version = expected_state_version + 1
        result = await self._session.execute(
            update(GameSessionRow)
            .where(
                GameSessionRow.session_id == session.session_id,
                GameSessionRow.state_version == expected_state_version,
            )
            .values(
                phase=session.phase,
                turn_number=session.turn_number,
                state_version=next_version,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            raise OptimisticLockError(
                f"session {session.session_id!r} state_version changed concurrently"
            )

        snapshot_result = await self._session.execute(
            update(GameSnapshotRow)
            .where(
                GameSnapshotRow.session_id == session.session_id,
                GameSnapshotRow.state_version == expected_state_version,
            )
            .values(
                state_version=next_version,
                state_json=dict(state),
                updated_at=utc_now(),
            )
        )
        if snapshot_result.rowcount != 1:
            persisted_snapshot_version = await self._session.scalar(
                select(GameSnapshotRow.state_version).where(
                    GameSnapshotRow.session_id == session.session_id
                )
            )
            if persisted_snapshot_version is not None:
                raise OptimisticLockError(
                    f"session {session.session_id!r} snapshot version changed concurrently"
                )
            self._session.add(
                GameSnapshotRow(
                    session_id=session.session_id,
                    state_version=next_version,
                    state_json=dict(state),
                    updated_at=utc_now(),
                )
            )
        if events:
            await self.persist_events(events, state_version=next_version)
        self._pending_session_versions.append((session, session.state_version))
        session.state_version = next_version

    def confirm_pending_versions(self) -> None:
        self._pending_session_versions.clear()

    def restore_pending_versions(self) -> None:
        for session, previous_version in reversed(self._pending_session_versions):
            session.state_version = previous_version
        self._pending_session_versions.clear()


class SqlAlchemyTurnRequestRepository(TurnRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        row = await self._session.scalar(
            select(TurnRequestRow).where(
                TurnRequestRow.session_id == session_id,
                TurnRequestRow.client_request_id == client_request_id,
            )
        )
        if row is None:
            return None
        return PersistedTurnRequest(
            turn_id=row.turn_id,
            action_signature=row.action_signature,
            response=(
                dict(row.response_json) if row.response_json is not None else None
            ),
        )

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        row = TurnRequestRow(
            request_id=str(uuid4()),
            session_id=submission.session_id,
            turn_id=submission.turn_id,
            client_request_id=submission.client_request_id,
            action_signature=action_signature,
            route=route.value,
            request_json=submission.model_dump(mode="json"),
            response_json=dict(response),
            error_text=None,
        )
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentTurnRequestError from exc
            raise


class SqlAlchemyNarrativeJobRepository(NarrativeJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _persisted(row: NarrativeJobRow) -> NarrativeJob:
        return NarrativeJob(
            job_id=row.job_id,
            session_id=row.session_id,
            turn_id=row.turn_id,
            client_request_id=row.client_request_id,
            action_signature=row.action_signature,
            prepared_state_version=row.prepared_state_version,
            state_fingerprint=row.state_fingerprint,
            scenario_id=row.scenario_id,
            scenario_content_version=row.scenario_content_version,
            request_fingerprint=row.request_fingerprint,
            narrative_request=dict(row.narrative_request_json),
            prompt_schema_version=row.prompt_schema_version,
            style_profile_version=row.style_profile_version,
            provider_name=row.provider_name,
            model_name=row.model_name,
            status=NarrativeJobStatus(row.status),
            attempt_count=row.attempt_count,
            lease_token=row.lease_token,
            lease_owner=row.lease_owner,
            lease_expires_at=row.lease_expires_at,
            validated_proposal=(
                dict(row.validated_proposal_json)
                if row.validated_proposal_json is not None
                else None
            ),
            validated_proposal_digest=row.validated_proposal_digest,
            outcome_rule_id=row.outcome_rule_id,
            accepted_narrative_text=row.accepted_narrative_text,
            error_code=row.error_code,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        statement = select(NarrativeJobRow).where(
            NarrativeJobRow.session_id == session_id,
            NarrativeJobRow.client_request_id == client_request_id,
        )
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return self._persisted(row) if row is not None else None

    async def get(self, job_id: str, *, for_update: bool = False) -> NarrativeJob | None:
        statement = select(NarrativeJobRow).where(NarrativeJobRow.job_id == job_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return self._persisted(row) if row is not None else None

    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        row = await self._session.scalar(
            select(NarrativeJobRow)
            .where(
                NarrativeJobRow.session_id == session_id,
                NarrativeJobRow.status.in_(
                    tuple(item.value for item in ACTIVE_NARRATIVE_JOB_STATUSES)
                ),
            )
            .order_by(NarrativeJobRow.created_at)
            .limit(1)
        )
        return self._persisted(row) if row is not None else None

    async def add(self, job: NarrativeJob) -> None:
        row = NarrativeJobRow(
            job_id=job.job_id,
            session_id=job.session_id,
            turn_id=job.turn_id,
            client_request_id=job.client_request_id,
            action_signature=job.action_signature,
            prepared_state_version=job.prepared_state_version,
            state_fingerprint=job.state_fingerprint,
            scenario_id=job.scenario_id,
            scenario_content_version=job.scenario_content_version,
            request_fingerprint=job.request_fingerprint,
            narrative_request_json=dict(job.narrative_request),
            prompt_schema_version=job.prompt_schema_version,
            style_profile_version=job.style_profile_version,
            provider_name=job.provider_name,
            model_name=job.model_name,
            status=job.status.value,
            attempt_count=job.attempt_count,
            lease_token=job.lease_token,
            lease_owner=job.lease_owner,
            lease_expires_at=job.lease_expires_at,
            validated_proposal_json=job.validated_proposal,
            validated_proposal_digest=job.validated_proposal_digest,
            outcome_rule_id=job.outcome_rule_id,
            accepted_narrative_text=job.accepted_narrative_text,
            error_code=job.error_code,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentTurnRequestError from exc
            raise

    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        result = await self._session.execute(
            update(NarrativeJobRow)
            .where(
                NarrativeJobRow.job_id == job.job_id,
                NarrativeJobRow.status == expected_status.value,
                NarrativeJobRow.lease_token == expected_lease_token,
                NarrativeJobRow.lease_owner == expected_lease_owner,
            )
            .values(
                status=job.status.value,
                attempt_count=job.attempt_count,
                lease_token=job.lease_token,
                lease_owner=job.lease_owner,
                lease_expires_at=job.lease_expires_at,
                validated_proposal_json=job.validated_proposal,
                validated_proposal_digest=job.validated_proposal_digest,
                outcome_rule_id=job.outcome_rule_id,
                accepted_narrative_text=job.accepted_narrative_text,
                error_code=job.error_code,
                updated_at=job.updated_at,
            )
        )
        return result.rowcount == 1

    async def recent_committed_texts(
        self, session_id: str, *, limit: int
    ) -> tuple[str, ...]:
        rows = (
            await self._session.scalars(
                select(NarrativeJobRow.accepted_narrative_text)
                .where(
                    NarrativeJobRow.session_id == session_id,
                    NarrativeJobRow.status == NarrativeJobStatus.COMMITTED.value,
                    NarrativeJobRow.accepted_narrative_text.is_not(None),
                )
                .order_by(
                    NarrativeJobRow.updated_at.desc(),
                    NarrativeJobRow.job_id.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(reversed(tuple(item for item in rows if item is not None)))


class _SqlAlchemyPlayerCharacterRepositorySupport:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _scalar(self, statement: Any) -> Any:
        try:
            with self._session.no_autoflush:
                return await self._session.scalar(statement)
        except DBAPIError as exc:
            raise PlayerCharacterRepositoryError(
                "structured player-character repository read failed"
            ) from exc

    async def _scalars(self, statement: Any) -> tuple[Any, ...]:
        try:
            with self._session.no_autoflush:
                result = await self._session.scalars(statement)
            return tuple(result.all())
        except DBAPIError as exc:
            raise PlayerCharacterRepositoryError(
                "structured player-character repository read failed"
            ) from exc

    async def _rows(self, statement: Any) -> tuple[Any, ...]:
        """Read a bounded multi-entity result without lazy follow-up queries."""

        try:
            with self._session.no_autoflush:
                result = await self._session.execute(statement)
            return tuple(result.all())
        except DBAPIError as exc:
            raise PlayerCharacterRepositoryError(
                "structured player-character repository read failed"
            ) from exc

    async def _flush_row(
        self,
        row: Any,
        *,
        conflict_message: str,
        conflict_type: type[PlayerCharacterRepositoryConflictError] = (
            PlayerCharacterRepositoryConflictError
        ),
    ) -> None:
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise conflict_type(conflict_message) from exc
            raise PlayerCharacterRepositoryError(
                "structured player-character repository write failed"
            ) from exc
        except DBAPIError as exc:
            raise PlayerCharacterRepositoryError(
                "structured player-character repository write failed"
            ) from exc

    @staticmethod
    def _controller_binding_record(
        row: PlayerCharacterControllerBindingRow,
    ) -> StoredControllerBindingRecord:
        try:
            return StoredControllerBindingRecord(
                controller_binding=ControllerBindingRef(
                    value=row.controller_binding
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored controller-binding row is invalid"
            ) from exc

    @staticmethod
    def _allocation_record(
        row: PlayerCharacterIdAllocationRow,
    ) -> StoredPlayerCharacterIdAllocationRecord:
        try:
            return StoredPlayerCharacterIdAllocationRecord(
                player_character_id=PlayerCharacterId(
                    value=row.player_character_id
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored player-character allocation row is invalid"
            ) from exc

    @staticmethod
    def _current_record(
        row: PlayerCharacterCurrentRow,
    ) -> StoredCurrentPlayerCharacterRecord:
        try:
            return StoredCurrentPlayerCharacterRecord(
                player_character_id=PlayerCharacterId(
                    value=row.player_character_id
                ),
                contract_version=row.contract_version,
                record_revision=row.record_revision,
                controller_binding=ControllerBindingRef(
                    value=row.controller_binding
                ),
                lifecycle=row.lifecycle,
                record_canonical=row.record_canonical,
                created_at=_as_utc(row.created_at),
                updated_at=_as_utc(row.updated_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored current player-character row is invalid"
            ) from exc

    @staticmethod
    def _revision_record(
        row: PlayerCharacterRevisionRow,
    ) -> StoredPlayerCharacterRevisionRecord:
        try:
            return StoredPlayerCharacterRevisionRecord(
                player_character_id=PlayerCharacterId(
                    value=row.player_character_id
                ),
                record_revision=row.record_revision,
                contract_version=row.contract_version,
                controller_binding=ControllerBindingRef(
                    value=row.controller_binding
                ),
                lifecycle=row.lifecycle,
                prior_revision=row.prior_revision,
                mutation_kind=row.mutation_kind,
                authority_class=row.authority_class,
                source_reference=AuthoritySourceRef(
                    value=row.source_reference
                ),
                record_canonical=row.record_canonical,
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored player-character revision row is invalid"
            ) from exc

    @staticmethod
    def _creation_receipt_record(
        row: PlayerCharacterCreationReceiptRow,
    ) -> StoredCreationReceiptRecord:
        try:
            return StoredCreationReceiptRecord(
                controller_binding=ControllerBindingRef(
                    value=row.controller_binding
                ),
                operation_namespace=row.operation_namespace,
                operation_id=row.operation_id,
                fingerprint=row.fingerprint,
                command_kind=row.command_kind,
                result_schema_version=row.result_schema_version,
                result_player_character_id=PlayerCharacterId(
                    value=row.result_player_character_id
                ),
                result_contract_version=row.result_contract_version,
                resulting_revision=row.resulting_revision,
                resulting_lifecycle=row.resulting_lifecycle,
                result_record_fingerprint=row.result_record_fingerprint,
                receipt_canonical=row.receipt_canonical,
                operation_evidence_canonical=(
                    row.operation_evidence_canonical
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored creation receipt row is invalid"
            ) from exc

    @staticmethod
    def _mutation_receipt_record(
        row: PlayerCharacterMutationReceiptRow,
    ) -> StoredMutationReceiptRecord:
        try:
            return StoredMutationReceiptRecord(
                player_character_id=PlayerCharacterId(
                    value=row.player_character_id
                ),
                operation_namespace=row.operation_namespace,
                operation_id=row.operation_id,
                fingerprint=row.fingerprint,
                command_kind=row.command_kind,
                result_schema_version=row.result_schema_version,
                expected_revision=row.expected_revision,
                result_player_character_id=PlayerCharacterId(
                    value=row.result_player_character_id
                ),
                result_contract_version=row.result_contract_version,
                result_command_kind=row.result_command_kind,
                command_result=row.command_result,
                resulting_revision=row.resulting_revision,
                resulting_lifecycle=row.resulting_lifecycle,
                before_record_fingerprint=row.before_record_fingerprint,
                after_record_fingerprint=row.after_record_fingerprint,
                receipt_canonical=row.receipt_canonical,
                operation_evidence_canonical=(
                    row.operation_evidence_canonical
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored mutation receipt row is invalid"
            ) from exc

    @staticmethod
    def _revision_row(
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> PlayerCharacterRevisionRow:
        provenance = record.authority_provenance
        return PlayerCharacterRevisionRow(
            player_character_id=record.player_character_id.value,
            record_revision=record.record_revision.value,
            contract_version=record.contract_version.value,
            controller_binding=record.controller_binding.value,
            lifecycle=record.lifecycle.value,
            prior_revision=(
                provenance.prior_revision.value
                if provenance.prior_revision is not None
                else None
            ),
            mutation_kind=provenance.mutation_kind.value,
            authority_class=provenance.authority_class.value,
            source_reference=provenance.source_reference.value,
            record_canonical=canonical_record_to_storage_bytes(record),
            created_at=created_at,
        )

    @staticmethod
    def _current_row(
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> PlayerCharacterCurrentRow:
        return PlayerCharacterCurrentRow(
            player_character_id=record.player_character_id.value,
            contract_version=record.contract_version.value,
            record_revision=record.record_revision.value,
            controller_binding=record.controller_binding.value,
            lifecycle=record.lifecycle.value,
            record_canonical=canonical_record_to_storage_bytes(record),
            created_at=created_at,
            updated_at=created_at,
        )

    async def _load_revision_row(
        self,
        player_character_id: PlayerCharacterId,
        record_revision: int,
    ) -> PlayerCharacterRevisionRow | None:
        return await self._scalar(
            select(PlayerCharacterRevisionRow).where(
                PlayerCharacterRevisionRow.player_character_id
                == player_character_id.value,
                PlayerCharacterRevisionRow.record_revision
                == record_revision,
            )
        )

    async def _raise_if_missing_current_has_evidence(
        self,
        player_character_id: PlayerCharacterId,
    ) -> None:
        statements = (
            select(PlayerCharacterIdAllocationRow.player_character_id).where(
                PlayerCharacterIdAllocationRow.player_character_id
                == player_character_id.value
            ),
            select(PlayerCharacterRevisionRow.player_character_id)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == player_character_id.value
            )
            .limit(1),
            select(
                PlayerCharacterCreationReceiptRow.result_player_character_id
            )
            .where(
                PlayerCharacterCreationReceiptRow.result_player_character_id
                == player_character_id.value
            )
            .limit(1),
            select(PlayerCharacterMutationReceiptRow.player_character_id)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == player_character_id.value
            )
            .limit(1),
        )
        for statement in statements:
            if await self._scalar(statement) is not None:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "player-character current row is missing"
                )

    async def _validate_complete_character(
        self,
        player_character_id: PlayerCharacterId,
        *,
        current_row: PlayerCharacterCurrentRow | None = None,
        creation_receipt_override: StoredCreationReceiptRecord | None = None,
        mutation_receipt_override: StoredMutationReceiptRecord | None = None,
        lock_related: bool = False,
    ) -> CanonicalPlayerCharacter | None:
        if current_row is None:
            current_statement = select(PlayerCharacterCurrentRow).where(
                PlayerCharacterCurrentRow.player_character_id
                == player_character_id.value
            )
            if lock_related:
                current_statement = current_statement.with_for_update()
            current_row = await self._scalar(
                current_statement
            )
        if current_row is None:
            await self._raise_if_missing_current_has_evidence(
                player_character_id
            )
            return None

        current_stored = self._current_record(current_row)
        current_record = canonical_record_from_current_storage(
            current_stored
        )
        if current_record.player_character_id != player_character_id:
            raise PlayerCharacterStoredRecordIntegrityError(
                "current player-character lookup identity is mismatched"
            )
        exact_revision_statement = select(
            PlayerCharacterRevisionRow
        ).where(
            PlayerCharacterRevisionRow.player_character_id
            == player_character_id.value,
            PlayerCharacterRevisionRow.record_revision
            == current_record.record_revision.value,
        )
        if lock_related:
            exact_revision_statement = (
                exact_revision_statement.with_for_update(read=True)
            )
        exact_revision_row = await self._scalar(exact_revision_statement)
        if exact_revision_row is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "current player-character revision reference is dangling"
            )
        exact_revision = canonical_record_from_revision_storage(
            self._revision_record(exact_revision_row)
        )
        if exact_revision != current_record:
            raise PlayerCharacterStoredRecordIntegrityError(
                "current player-character row does not match its revision"
            )

        revision_statement = (
            select(PlayerCharacterRevisionRow)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == player_character_id.value
            )
            .order_by(PlayerCharacterRevisionRow.record_revision)
        )
        creation_statement = select(
            PlayerCharacterCreationReceiptRow
        ).where(
            PlayerCharacterCreationReceiptRow.result_player_character_id
            == player_character_id.value
        )
        mutation_statement = (
            select(PlayerCharacterMutationReceiptRow)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == player_character_id.value
            )
            .order_by(
                PlayerCharacterMutationReceiptRow.resulting_revision,
                PlayerCharacterMutationReceiptRow.operation_id,
            )
        )
        binding_statement = select(
            PlayerCharacterControllerBindingRow
        ).where(
            PlayerCharacterControllerBindingRow.controller_binding
            == current_record.controller_binding.value
        )
        allocation_statement = select(
            PlayerCharacterIdAllocationRow
        ).where(
            PlayerCharacterIdAllocationRow.player_character_id
            == player_character_id.value
        )
        if lock_related:
            revision_statement = revision_statement.with_for_update(
                read=True
            )
            creation_statement = creation_statement.with_for_update()
            mutation_statement = mutation_statement.with_for_update()
            binding_statement = binding_statement.with_for_update()
            allocation_statement = allocation_statement.with_for_update()
        revision_rows = await self._scalars(revision_statement)
        creation_row = await self._scalar(creation_statement)
        mutation_rows = await self._scalars(mutation_statement)
        binding_row = await self._scalar(binding_statement)
        allocation_row = await self._scalar(allocation_statement)

        creation_stored = (
            creation_receipt_override
            if creation_receipt_override is not None
            else (
                self._creation_receipt_record(creation_row)
                if creation_row is not None
                else None
            )
        )
        mutation_stored = tuple(
            self._mutation_receipt_record(row) for row in mutation_rows
        )
        if mutation_receipt_override is not None:
            mutation_stored += (mutation_receipt_override,)
        validate_stored_player_character_record_set(
            creation_receipt=creation_stored,
            mutation_receipts=mutation_stored,
            revisions=tuple(
                self._revision_record(row) for row in revision_rows
            ),
            current=current_stored,
            controller_binding=(
                self._controller_binding_record(binding_row)
                if binding_row is not None
                else None
            ),
            allocation=(
                self._allocation_record(allocation_row)
                if allocation_row is not None
                else None
            ),
        )
        return current_record


class SqlAlchemyControllerBindingRegistryRepository(
    _SqlAlchemyPlayerCharacterRepositorySupport,
    ControllerBindingRegistryRepository,
):
    async def get(
        self,
        controller_binding: ControllerBindingRef,
    ) -> ControllerBindingRef | None:
        row = await self._scalar(
            select(PlayerCharacterControllerBindingRow).where(
                PlayerCharacterControllerBindingRow.controller_binding
                == controller_binding.value
            )
        )
        if row is None:
            return None
        stored = self._controller_binding_record(row).controller_binding
        if stored != controller_binding:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored controller-binding lookup identity is mismatched"
            )
        return stored

    async def add(
        self,
        controller_binding: ControllerBindingRef,
        *,
        created_at: datetime,
    ) -> None:
        await self._flush_row(
            PlayerCharacterControllerBindingRow(
                controller_binding=controller_binding.value,
                created_at=created_at,
            ),
            conflict_message="controller-binding insertion conflict",
            conflict_type=PlayerCharacterControllerBindingConflictError,
        )

    async def lock(
        self,
        controller_binding: ControllerBindingRef,
    ) -> ControllerBindingRef | None:
        row = await self._scalar(
            select(PlayerCharacterControllerBindingRow)
            .where(
                PlayerCharacterControllerBindingRow.controller_binding
                == controller_binding.value
            )
            .with_for_update()
        )
        if row is None:
            return None
        stored = self._controller_binding_record(row).controller_binding
        if stored != controller_binding:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored controller-binding lock identity is mismatched"
            )
        return stored


class SqlAlchemyPlayerCharacterRepository(
    _SqlAlchemyPlayerCharacterRepositorySupport,
    PlayerCharacterRepository,
):
    async def allocation_exists(
        self,
        player_character_id: PlayerCharacterId,
    ) -> bool:
        value = await self._scalar(
            select(PlayerCharacterIdAllocationRow.player_character_id).where(
                PlayerCharacterIdAllocationRow.player_character_id
                == player_character_id.value
            )
        )
        if value is None:
            return False
        try:
            stored_id = PlayerCharacterId(value=value)
        except (TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored player-character allocation identity is invalid"
            ) from exc
        if stored_id != player_character_id:
            raise PlayerCharacterStoredRecordIntegrityError(
                "stored player-character allocation identity is mismatched"
            )
        return True

    async def add_allocation(
        self,
        player_character_id: PlayerCharacterId,
        *,
        created_at: datetime,
    ) -> None:
        await self._flush_row(
            PlayerCharacterIdAllocationRow(
                player_character_id=player_character_id.value,
                created_at=created_at,
            ),
            conflict_message="player-character allocation conflict",
        )

    async def get(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalPlayerCharacter | None:
        row = await self._scalar(
            select(PlayerCharacterCurrentRow).where(
                PlayerCharacterCurrentRow.player_character_id
                == player_character_id.value
            )
        )
        if row is None:
            await self._raise_if_missing_current_has_evidence(
                player_character_id
            )
            return None
        return await self._validate_complete_character(
            player_character_id,
            current_row=row,
        )

    async def get_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalPlayerCharacter | None:
        row = await self._scalar(
            select(PlayerCharacterCurrentRow)
            .where(
                PlayerCharacterCurrentRow.player_character_id
                == player_character_id.value
            )
            .with_for_update()
        )
        if row is None:
            await self._raise_if_missing_current_has_evidence(
                player_character_id
            )
            return None
        return await self._validate_complete_character(
            player_character_id,
            current_row=row,
            lock_related=True,
        )

    async def list_eligible_for_run_entry(
        self,
        controller_binding: ControllerBindingRef,
        *,
        limit: int,
    ) -> tuple[CanonicalPlayerCharacter, ...]:
        if type(limit) is not int or limit < 1 or limit > 33:
            raise ValueError("eligible-character discovery limit is outside its bound")
        try:
            controller_binding = ControllerBindingRef(value=controller_binding.value)
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "eligible-character discovery controller binding is invalid"
            ) from exc
        canonical_record = cast(
            PlayerCharacterCurrentRow.record_canonical,
            String,
        )
        canonical_lifecycle = func.JSON_UNQUOTE(
            func.JSON_EXTRACT(
                canonical_record,
                "$.lifecycle",
            )
        )
        canonical_controller_binding = func.JSON_UNQUOTE(
            func.JSON_EXTRACT(
                canonical_record,
                "$.controller_binding.value",
            )
        )
        authoritative_later_revision_exists = (
            select(PlayerCharacterRevisionRow.player_character_id)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == PlayerCharacterCurrentRow.player_character_id,
                PlayerCharacterRevisionRow.record_revision
                > PlayerCharacterCurrentRow.record_revision,
            )
            .correlate(PlayerCharacterCurrentRow)
            .exists()
        )
        active_binding_is_consistent = and_(
            RunCurrentRow.binding_state == "active",
            RunCurrentRow.inactivated_at.is_(None),
            RunCurrentRow.binding_player_character_id
            == PlayerCharacterCurrentRow.player_character_id,
            RunCurrentRow.lifecycle_status.in_(("pre_first_turn", "active")),
            RunRevisionRow.run_id.is_not(None),
            RunRevisionRow.lifecycle_status == RunCurrentRow.lifecycle_status,
            RunRevisionRow.state_version == RunCurrentRow.state_version,
            RunRevisionRow.binding_player_character_id
            == RunCurrentRow.binding_player_character_id,
            RunCurrentRow.binding_contract_version
            == PlayerCharacterContractVersion.V1.value,
            RunRevisionRow.binding_contract_version
            == PlayerCharacterContractVersion.V1.value,
            RunRevisionRow.binding_contract_version
            == RunCurrentRow.binding_contract_version,
            RunRevisionRow.binding_record_revision
            == RunCurrentRow.binding_record_revision,
            RunRevisionRow.binding_state == RunCurrentRow.binding_state,
            RunRevisionRow.binding_operation_id
            == RunCurrentRow.binding_operation_id,
            RunRevisionRow.binding_authority_source_ref
            == RunCurrentRow.binding_authority_source_ref,
            RunRevisionRow.bound_at == RunCurrentRow.bound_at,
            RunRevisionRow.inactivated_at == RunCurrentRow.inactivated_at,
        )
        rows = await self._rows(
            select(
                PlayerCharacterCurrentRow,
                RunCurrentRow,
                RunRevisionRow,
                authoritative_later_revision_exists,
            )
            .outerjoin(
                RunCurrentRow,
                RunCurrentRow.active_player_character_id
                == PlayerCharacterCurrentRow.player_character_id,
            )
            .outerjoin(
                RunRevisionRow,
                and_(
                    RunRevisionRow.run_id == RunCurrentRow.run_id,
                    RunRevisionRow.state_version == RunCurrentRow.state_version,
                ),
            )
            .where(
                PlayerCharacterCurrentRow.controller_binding
                == controller_binding.value,
                or_(
                    and_(
                        PlayerCharacterCurrentRow.lifecycle == "active",
                        RunCurrentRow.run_id.is_(None),
                    ),
                    canonical_lifecycle.is_(None),
                    canonical_controller_binding.is_(None),
                    canonical_lifecycle != PlayerCharacterCurrentRow.lifecycle,
                    canonical_controller_binding
                    != PlayerCharacterCurrentRow.controller_binding,
                    authoritative_later_revision_exists,
                    and_(
                        RunCurrentRow.run_id.is_not(None),
                        ~active_binding_is_consistent,
                    ),
                ),
            )
            .order_by(PlayerCharacterCurrentRow.player_character_id.asc())
            .limit(limit)
        )
        if len(rows) > limit:
            raise PlayerCharacterStoredRecordIntegrityError(
                "eligible-character discovery exceeded its query bound"
            )
        records: list[CanonicalPlayerCharacter] = []
        for (
            row,
            active_run_row,
            active_run_revision_row,
            has_authoritative_later_revision,
        ) in rows:
            player_character_id = PlayerCharacterId(value=row.player_character_id)
            current_stored = self._current_record(row)
            current_record = canonical_record_from_current_storage(current_stored)
            if current_record.player_character_id != player_character_id:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery row has a mismatched identity"
                )
            if current_record.controller_binding != controller_binding:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery row does not match query evidence"
                )
            if has_authoritative_later_revision:
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery current row is not the latest revision"
                )
            if active_run_row is not None:
                try:
                    active_run = canonical_run_from_current_storage(
                        _SqlAlchemyRunRepositorySupport._current_run_record(
                            active_run_row
                        ),
                        participations=(),
                    )
                    if active_run_revision_row is None:
                        raise RunStoredRecordIntegrityError(
                            "active Run has no matching current revision"
                        )
                    canonical_run_from_revision_storage(
                        _SqlAlchemyRunRepositorySupport._run_revision_record(
                            active_run_revision_row
                        ),
                        participations=(),
                    )
                except RunStoredRecordIntegrityError as exc:
                    raise PlayerCharacterStoredRecordIntegrityError(
                        "eligible-character discovery active binding evidence is invalid"
                    ) from exc
                binding = active_run.player_character_binding
                if (
                    binding is None
                    or not active_run.lifecycle_status.is_active_line
                    or binding.binding_state != "active"
                    or binding.applicable_character_reference.player_character_id
                    != player_character_id
                ):
                    raise PlayerCharacterStoredRecordIntegrityError(
                        "eligible-character discovery active binding evidence is inconsistent"
                    )
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery included an active binding"
                )
            if current_record.lifecycle.value != "active":
                raise PlayerCharacterStoredRecordIntegrityError(
                    "eligible-character discovery row does not match query evidence"
                )
            records.append(current_record)
        return tuple(records)

    async def add_initial(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        revision_row = self._revision_row(record, created_at=created_at)
        current_row = self._current_row(record, created_at=created_at)
        revision_record = self._revision_record(revision_row)
        current_record = self._current_record(current_row)
        if (
            canonical_record_from_revision_storage(revision_record) != record
            or canonical_record_from_current_storage(current_record) != record
            or record.record_revision.value != 1
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "initial player-character record is inconsistent"
            )

        binding_row = await self._scalar(
            select(PlayerCharacterControllerBindingRow).where(
                PlayerCharacterControllerBindingRow.controller_binding
                == record.controller_binding.value
            )
        )
        allocation_row = await self._scalar(
            select(PlayerCharacterIdAllocationRow).where(
                PlayerCharacterIdAllocationRow.player_character_id
                == record.player_character_id.value
            )
        )
        if binding_row is None or allocation_row is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "initial player-character companions are missing"
            )
        self._controller_binding_record(binding_row)
        self._allocation_record(allocation_row)

        await self._flush_row(
            revision_row,
            conflict_message="initial player-character revision conflict",
        )
        await self._flush_row(
            current_row,
            conflict_message="initial current player-character conflict",
        )

    async def append_revision(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        revision_row = self._revision_row(record, created_at=created_at)
        stored_revision = self._revision_record(revision_row)
        if canonical_record_from_revision_storage(stored_revision) != record:
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor player-character revision is inconsistent"
            )
        prior_revision = record.authority_provenance.prior_revision
        if prior_revision is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor player-character revision has no predecessor"
            )
        current = await self._validate_complete_character(
            record.player_character_id
        )
        if current is None:
            raise PlayerCharacterRepositoryConflictError(
                "successor player-character has no current row"
            )
        if (
            current.record_revision != prior_revision
            or current.player_character_id != record.player_character_id
            or current.controller_binding != record.controller_binding
            or current.contract_version != record.contract_version
        ):
            raise PlayerCharacterRepositoryConflictError(
                "successor player-character revision is stale"
            )
        await self._flush_row(
            revision_row,
            conflict_message="player-character revision insertion conflict",
        )

    async def compare_and_swap_current(
        self,
        record: CanonicalPlayerCharacter,
        *,
        expected_revision: int,
        created_at: datetime,
    ) -> bool:
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("expected revision is outside its domain")
        try:
            expected = PlayerCharacterRevision(value=expected_revision)
        except ValueError as exc:
            raise ValueError("expected revision is outside its domain") from exc
        if (
            record.record_revision.value != expected_revision + 1
            or record.authority_provenance.prior_revision != expected
        ):
            raise ValueError(
                "expected revision does not match successor record"
            )
        revision_row = await self._load_revision_row(
            record.player_character_id,
            record.record_revision.value,
        )
        if revision_row is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor player-character revision is missing"
            )
        if (
            canonical_record_from_revision_storage(
                self._revision_record(revision_row)
            )
            != record
        ):
            raise PlayerCharacterStoredRecordIntegrityError(
                "successor revision does not match current-row candidate"
            )
        canonical = canonical_record_to_storage_bytes(record)
        try:
            result = await self._session.execute(
                update(PlayerCharacterCurrentRow)
                .where(
                    PlayerCharacterCurrentRow.player_character_id
                    == record.player_character_id.value,
                    PlayerCharacterCurrentRow.record_revision
                    == expected_revision,
                    PlayerCharacterCurrentRow.controller_binding
                    == record.controller_binding.value,
                )
                .values(
                    contract_version=record.contract_version.value,
                    record_revision=record.record_revision.value,
                    lifecycle=record.lifecycle.value,
                    record_canonical=canonical,
                    updated_at=created_at,
                )
            )
        except DBAPIError as exc:
            raise PlayerCharacterRepositoryError(
                "player-character current compare-and-swap failed"
            ) from exc
        return result.rowcount == 1


class SqlAlchemyPlayerCharacterCreationReceiptRepository(
    _SqlAlchemyPlayerCharacterRepositorySupport,
    PlayerCharacterCreationReceiptRepository,
):
    async def get(
        self,
        key: CreationReceiptKey,
    ) -> StoredCreationSuccessReceipt | None:
        row = await self._scalar(
            select(PlayerCharacterCreationReceiptRow).where(
                PlayerCharacterCreationReceiptRow.controller_binding
                == key.controller_binding.value,
                PlayerCharacterCreationReceiptRow.operation_namespace
                == key.operation_namespace.value,
                PlayerCharacterCreationReceiptRow.operation_id
                == key.operation_id.value,
            )
        )
        if row is None:
            return None
        stored = self._creation_receipt_record(row)
        receipt = creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt lookup identity is mismatched"
            )
        await self._validate_complete_character(
            receipt.result.player_character_id
        )
        return receipt

    async def add(
        self,
        receipt: StoredCreationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        result = receipt.result
        revision_row = await self._load_revision_row(
            result.player_character_id,
            result.resulting_revision.value,
        )
        if revision_row is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt result revision is missing"
            )
        record = canonical_record_from_revision_storage(
            self._revision_record(revision_row)
        )
        try:
            command = CharacterCreationCommand(
                contract_version=record.contract_version,
                character_core=record.character_core,
                narration_preferences=record.narration_preferences,
            )
            evidence = creation_operation_evidence_to_storage_bytes(
                command,
                source_reference=record.authority_provenance.source_reference,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt operation evidence is inconsistent"
            ) from exc
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
            result_record_fingerprint=canonical_state_record_fingerprint(
                record
            ),
            receipt_canonical=creation_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=evidence,
            created_at=created_at,
        )
        if creation_receipt_from_storage(stored) != receipt:
            raise PlayerCharacterStoredRecordIntegrityError(
                "creation receipt storage mapping is inconsistent"
            )

        existing_key = await self._scalar(
            select(PlayerCharacterCreationReceiptRow.controller_binding).where(
                PlayerCharacterCreationReceiptRow.controller_binding
                == receipt.key.controller_binding.value,
                PlayerCharacterCreationReceiptRow.operation_namespace
                == receipt.key.operation_namespace.value,
                PlayerCharacterCreationReceiptRow.operation_id
                == receipt.key.operation_id.value,
            )
        )
        existing_result = await self._scalar(
            select(
                PlayerCharacterCreationReceiptRow.result_player_character_id
            ).where(
                PlayerCharacterCreationReceiptRow.result_player_character_id
                == result.player_character_id.value,
                PlayerCharacterCreationReceiptRow.resulting_revision
                == result.resulting_revision.value,
            )
        )
        if existing_key is not None or existing_result is not None:
            raise PlayerCharacterRepositoryConflictError(
                "creation receipt unique-race conflict"
            )
        await self._validate_complete_character(
            result.player_character_id,
            creation_receipt_override=stored,
        )
        row = PlayerCharacterCreationReceiptRow(
            controller_binding=stored.controller_binding.value,
            operation_namespace=stored.operation_namespace,
            operation_id=stored.operation_id,
            fingerprint=stored.fingerprint,
            command_kind=stored.command_kind,
            result_schema_version=stored.result_schema_version,
            result_player_character_id=(
                stored.result_player_character_id.value
            ),
            result_contract_version=stored.result_contract_version,
            resulting_revision=stored.resulting_revision,
            resulting_lifecycle=stored.resulting_lifecycle,
            result_record_fingerprint=stored.result_record_fingerprint,
            receipt_canonical=stored.receipt_canonical,
            operation_evidence_canonical=(
                stored.operation_evidence_canonical
            ),
            created_at=created_at,
        )
        await self._flush_row(
            row,
            conflict_message="creation receipt unique-race conflict",
        )


class SqlAlchemyPlayerCharacterMutationReceiptRepository(
    _SqlAlchemyPlayerCharacterRepositorySupport,
    PlayerCharacterMutationReceiptRepository,
):
    async def get(
        self,
        key: MutationReceiptKey,
    ) -> StoredMutationSuccessReceipt | None:
        row = await self._scalar(
            select(PlayerCharacterMutationReceiptRow).where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == key.player_character_id.value,
                PlayerCharacterMutationReceiptRow.operation_namespace
                == key.operation_namespace.value,
                PlayerCharacterMutationReceiptRow.operation_id
                == key.operation_id.value,
            )
        )
        if row is None:
            return None
        stored = self._mutation_receipt_record(row)
        receipt = mutation_receipt_from_storage(stored)
        if receipt.key != key:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt lookup identity is mismatched"
            )
        await self._validate_complete_character(key.player_character_id)
        return receipt

    @staticmethod
    def _operation_evidence(
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
        confirmation: PlayerConfirmation | None = None
        final_death_evidence: TrustedFinalDeathEvidence | None = None
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

    async def add(
        self,
        receipt: StoredMutationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        result = receipt.result
        expected_revision = result.resulting_revision.value - 1
        before_row = await self._load_revision_row(
            receipt.key.player_character_id,
            expected_revision,
        )
        after_row = await self._load_revision_row(
            receipt.key.player_character_id,
            result.resulting_revision.value,
        )
        if before_row is None or after_row is None:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt revision evidence is missing"
            )
        before = canonical_record_from_revision_storage(
            self._revision_record(before_row)
        )
        after = canonical_record_from_revision_storage(
            self._revision_record(after_row)
        )
        evidence = self._operation_evidence(
            receipt,
            before=before,
            after=after,
        )
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
            before_record_fingerprint=canonical_state_record_fingerprint(
                before
            ),
            after_record_fingerprint=canonical_state_record_fingerprint(
                after
            ),
            receipt_canonical=mutation_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=evidence,
            created_at=created_at,
        )
        if mutation_receipt_from_storage(stored) != receipt:
            raise PlayerCharacterStoredRecordIntegrityError(
                "mutation receipt storage mapping is inconsistent"
            )

        existing_key = await self._scalar(
            select(PlayerCharacterMutationReceiptRow.player_character_id).where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == receipt.key.player_character_id.value,
                PlayerCharacterMutationReceiptRow.operation_namespace
                == receipt.key.operation_namespace.value,
                PlayerCharacterMutationReceiptRow.operation_id
                == receipt.key.operation_id.value,
            )
        )
        existing_result = await self._scalar(
            select(PlayerCharacterMutationReceiptRow.player_character_id).where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == receipt.key.player_character_id.value,
                PlayerCharacterMutationReceiptRow.resulting_revision
                == result.resulting_revision.value,
            )
        )
        if existing_key is not None or existing_result is not None:
            raise PlayerCharacterRepositoryConflictError(
                "mutation receipt unique-race conflict"
            )
        await self._validate_complete_character(
            receipt.key.player_character_id,
            mutation_receipt_override=stored,
        )
        row = PlayerCharacterMutationReceiptRow(
            player_character_id=stored.player_character_id.value,
            operation_namespace=stored.operation_namespace,
            operation_id=stored.operation_id,
            fingerprint=stored.fingerprint,
            command_kind=stored.command_kind,
            result_schema_version=stored.result_schema_version,
            expected_revision=stored.expected_revision,
            result_player_character_id=(
                stored.result_player_character_id.value
            ),
            result_contract_version=stored.result_contract_version,
            result_command_kind=stored.result_command_kind,
            command_result=stored.command_result,
            resulting_revision=stored.resulting_revision,
            resulting_lifecycle=stored.resulting_lifecycle,
            before_record_fingerprint=stored.before_record_fingerprint,
            after_record_fingerprint=stored.after_record_fingerprint,
            receipt_canonical=stored.receipt_canonical,
            operation_evidence_canonical=(
                stored.operation_evidence_canonical
            ),
            created_at=created_at,
        )
        await self._flush_row(
            row,
            conflict_message="mutation receipt unique-race conflict",
            conflict_type=PlayerCharacterMutationReceiptConflictError,
        )


class _SqlAlchemyRunRepositorySupport:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _run_scalar(self, statement: Any) -> Any:
        try:
            with self._session.no_autoflush:
                return await self._session.scalar(statement)
        except DBAPIError as exc:
            raise RunRepositoryError("minimum Run repository read failed") from exc

    async def _run_scalars(self, statement: Any) -> tuple[Any, ...]:
        try:
            with self._session.no_autoflush:
                result = await self._session.scalars(statement)
            return tuple(result.all())
        except DBAPIError as exc:
            raise RunRepositoryError("minimum Run repository read failed") from exc

    async def _flush_run_row(
        self,
        row: Any,
        *,
        conflict_message: str,
        conflict_type: type[RuntimeError] = RunRepositoryConflictError,
    ) -> None:
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise conflict_type(conflict_message) from exc
            raise RunRepositoryError("minimum Run repository write failed") from exc
        except DBAPIError as exc:
            raise RunRepositoryError("minimum Run repository write failed") from exc

    @staticmethod
    def _current_run_record(row: RunCurrentRow) -> StoredCurrentRunRecord:
        try:
            return StoredCurrentRunRecord(
                run_id=RunId(value=row.run_id),
                continuous_story_line_id=ContinuousStoryLineId(
                    value=row.continuous_story_line_id
                ),
                lifecycle_status=row.lifecycle_status,
                state_version=row.state_version,
                creation_operation_id=RunOperationId(
                    value=row.creation_operation_id
                ),
                creation_source_reference=RunAuthoritySourceRef(
                    value=row.creation_source_reference
                ),
                creation_occurred_at=_as_utc(row.creation_occurred_at),
                prior_state_version=row.prior_state_version,
                mutation_kind=row.mutation_kind,
                operation_id=RunOperationId(value=row.operation_id),
                source_reference=RunAuthoritySourceRef(
                    value=row.source_reference
                ),
                occurred_at=_as_utc(row.occurred_at),
                binding_player_character_id=row.binding_player_character_id,
                binding_contract_version=row.binding_contract_version,
                binding_record_revision=row.binding_record_revision,
                binding_state=row.binding_state,
                binding_operation_id=row.binding_operation_id,
                binding_authority_source_ref=(
                    row.binding_authority_source_ref
                ),
                bound_at=(
                    _as_utc(row.bound_at) if row.bound_at is not None else None
                ),
                inactivated_at=(
                    _as_utc(row.inactivated_at)
                    if row.inactivated_at is not None
                    else None
                ),
                active_player_character_id=row.active_player_character_id,
                created_at=_as_utc(row.created_at),
                updated_at=_as_utc(row.updated_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "stored current Run row is invalid"
            ) from exc

    @staticmethod
    def _run_revision_record(row: RunRevisionRow) -> StoredRunRevisionRecord:
        try:
            return StoredRunRevisionRecord(
                run_id=RunId(value=row.run_id),
                continuous_story_line_id=ContinuousStoryLineId(
                    value=row.continuous_story_line_id
                ),
                lifecycle_status=row.lifecycle_status,
                state_version=row.state_version,
                creation_operation_id=RunOperationId(
                    value=row.creation_operation_id
                ),
                creation_source_reference=RunAuthoritySourceRef(
                    value=row.creation_source_reference
                ),
                creation_occurred_at=_as_utc(row.creation_occurred_at),
                prior_state_version=row.prior_state_version,
                mutation_kind=row.mutation_kind,
                operation_id=RunOperationId(value=row.operation_id),
                source_reference=RunAuthoritySourceRef(
                    value=row.source_reference
                ),
                occurred_at=_as_utc(row.occurred_at),
                binding_player_character_id=row.binding_player_character_id,
                binding_contract_version=row.binding_contract_version,
                binding_record_revision=row.binding_record_revision,
                binding_state=row.binding_state,
                binding_operation_id=row.binding_operation_id,
                binding_authority_source_ref=(
                    row.binding_authority_source_ref
                ),
                bound_at=(
                    _as_utc(row.bound_at) if row.bound_at is not None else None
                ),
                inactivated_at=(
                    _as_utc(row.inactivated_at)
                    if row.inactivated_at is not None
                    else None
                ),
                active_player_character_id=None,
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "stored Run revision row is invalid"
            ) from exc

    @staticmethod
    def _run_participation_record(
        row: RunSessionParticipationRow,
    ) -> StoredRunSessionParticipationRecord:
        try:
            return StoredRunSessionParticipationRecord(
                session_id=row.session_id,
                run_id=RunId(value=row.run_id),
                continuous_story_line_id=ContinuousStoryLineId(
                    value=row.continuous_story_line_id
                ),
                joined_state_version=row.joined_state_version,
                operation_id=RunOperationId(value=row.operation_id),
                source_reference=RunAuthoritySourceRef(
                    value=row.source_reference
                ),
                joined_at=_as_utc(row.joined_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "stored Run participation row is invalid"
            ) from exc

    @staticmethod
    def _run_creation_receipt_record(
        row: RunCreationReceiptRow,
    ) -> StoredRunCreationReceiptRecord:
        try:
            return StoredRunCreationReceiptRecord(
                operation_namespace=row.operation_namespace,
                operation_id=RunOperationId(value=row.operation_id),
                fingerprint=row.fingerprint,
                command_kind=row.command_kind,
                result_schema_version=row.result_schema_version,
                result_run_id=RunId(value=row.result_run_id),
                result_continuous_story_line_id=ContinuousStoryLineId(
                    value=row.result_continuous_story_line_id
                ),
                resulting_lifecycle_status=(
                    row.resulting_lifecycle_status
                ),
                resulting_state_version=row.resulting_state_version,
                receipt_canonical=row.receipt_canonical,
                operation_evidence_canonical=(
                    row.operation_evidence_canonical
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "stored Run creation receipt row is invalid"
            ) from exc

    @staticmethod
    def _run_mutation_receipt_record(
        row: RunMutationReceiptRow,
    ) -> StoredRunMutationReceiptRecord:
        try:
            return StoredRunMutationReceiptRecord(
                run_id=RunId(value=row.run_id),
                operation_namespace=row.operation_namespace,
                operation_id=RunOperationId(value=row.operation_id),
                fingerprint=row.fingerprint,
                command_kind=row.command_kind,
                result_schema_version=row.result_schema_version,
                expected_state_version=row.expected_state_version,
                result_run_id=RunId(value=row.result_run_id),
                result_continuous_story_line_id=ContinuousStoryLineId(
                    value=row.result_continuous_story_line_id
                ),
                resulting_lifecycle_status=(
                    row.resulting_lifecycle_status
                ),
                resulting_state_version=row.resulting_state_version,
                participation_session_id=row.participation_session_id,
                participation_operation_id=(
                    row.participation_operation_id
                ),
                participation_source_reference=(
                    row.participation_source_reference
                ),
                result_player_character_id=row.result_player_character_id,
                result_character_contract_version=(
                    row.result_character_contract_version
                ),
                result_character_record_revision=(
                    row.result_character_record_revision
                ),
                receipt_canonical=row.receipt_canonical,
                operation_evidence_canonical=(
                    row.operation_evidence_canonical
                ),
                created_at=_as_utc(row.created_at),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "stored Run mutation receipt row is invalid"
            ) from exc

    @staticmethod
    def _run_core_values(run: CanonicalRun) -> dict[str, Any]:
        run = validate_canonical_run(run)
        creation = run.creation_provenance
        current = run.current_mutation_provenance
        binding = run.player_character_binding
        return {
            "run_id": run.run_id.value,
            "continuous_story_line_id": (
                run.continuous_story_line_id.value
            ),
            "lifecycle_status": run.lifecycle_status.value,
            "state_version": run.state_version.value,
            "creation_operation_id": creation.operation_id.value,
            "creation_source_reference": creation.source_reference.value,
            "creation_occurred_at": creation.occurred_at,
            "prior_state_version": (
                current.prior_state_version.value
                if current.prior_state_version is not None
                else None
            ),
            "mutation_kind": current.mutation_kind.value,
            "operation_id": current.operation_id.value,
            "source_reference": current.source_reference.value,
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
            "binding_state": (
                binding.binding_state if binding is not None else None
            ),
            "binding_operation_id": (
                binding.binding_operation_id.value
                if binding is not None
                else None
            ),
            "binding_authority_source_ref": (
                binding.binding_authority_source_ref.value
                if binding is not None
                else None
            ),
            "bound_at": (
                binding.bound_at if binding is not None else None
            ),
            "inactivated_at": (
                binding.inactivated_at if binding is not None else None
            ),
        }

    @classmethod
    def _run_revision_row(
        cls,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> RunRevisionRow:
        return RunRevisionRow(
            **cls._run_core_values(run),
            created_at=created_at,
        )

    @classmethod
    def _current_run_row(
        cls,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> RunCurrentRow:
        return RunCurrentRow(
            **cls._run_core_values(run),
            active_player_character_id=(
                run.player_character_binding.applicable_character_reference
                .player_character_id.value
                if run.player_character_binding is not None
                else None
            ),
            created_at=created_at,
            updated_at=created_at,
        )

    async def _load_run_revision(
        self,
        run_id: RunId,
        state_version: int,
    ) -> RunRevisionRow | None:
        return await self._run_scalar(
            select(RunRevisionRow).where(
                RunRevisionRow.run_id == run_id.value,
                RunRevisionRow.state_version == state_version,
            )
        )

    async def _load_participation_records(
        self,
        run_id: RunId,
        *,
        through_version: int | None = None,
    ) -> tuple[StoredRunSessionParticipationRecord, ...]:
        statement = select(RunSessionParticipationRow).where(
            RunSessionParticipationRow.run_id == run_id.value
        )
        if through_version is not None:
            statement = statement.where(
                RunSessionParticipationRow.joined_state_version
                <= through_version
            )
        rows = await self._run_scalars(
            statement.order_by(
                RunSessionParticipationRow.joined_state_version,
                RunSessionParticipationRow.session_id,
            )
        )
        return tuple(self._run_participation_record(row) for row in rows)

    async def _run_at_revision(
        self,
        run_id: RunId,
        state_version: int,
    ) -> CanonicalRun:
        row = await self._load_run_revision(run_id, state_version)
        if row is None:
            raise RunStoredRecordIntegrityError(
                "referenced Run revision is missing"
            )
        participation_records = await self._load_participation_records(
            run_id,
            through_version=state_version,
        )
        return canonical_run_from_revision_storage(
            self._run_revision_record(row),
            participations=tuple(
                participation_from_storage(item)
                for item in participation_records
            ),
        )

    async def _raise_if_missing_run_has_evidence(self, run_id: RunId) -> None:
        statements = (
            select(RunRevisionRow.run_id)
            .where(RunRevisionRow.run_id == run_id.value)
            .limit(1),
            select(RunSessionParticipationRow.run_id)
            .where(RunSessionParticipationRow.run_id == run_id.value)
            .limit(1),
            select(RunCreationReceiptRow.result_run_id)
            .where(RunCreationReceiptRow.result_run_id == run_id.value)
            .limit(1),
            select(RunMutationReceiptRow.run_id)
            .where(RunMutationReceiptRow.run_id == run_id.value)
            .limit(1),
        )
        for statement in statements:
            if await self._run_scalar(statement) is not None:
                raise RunStoredRecordIntegrityError(
                    "current Run row is missing"
                )

    async def _active_run_for_player_character(
        self,
        player_character_id: PlayerCharacterId,
        *,
        for_update: bool,
    ) -> CanonicalRun | None:
        try:
            player_character_id = PlayerCharacterId(
                value=player_character_id.value
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RunStoredRecordIntegrityError(
                "active-binding lookup identity is invalid"
            ) from exc
        evidence_statements = (
            select(RunCurrentRow.run_id).where(
                RunCurrentRow.active_player_character_id
                == player_character_id.value
            ),
            select(RunCurrentRow.run_id).where(
                RunCurrentRow.binding_player_character_id
                == player_character_id.value
            ),
            select(RunRevisionRow.run_id).where(
                RunRevisionRow.binding_player_character_id
                == player_character_id.value
            ),
            select(RunMutationReceiptRow.run_id).where(
                RunMutationReceiptRow.result_player_character_id
                == player_character_id.value
            ),
        )
        evidence_run_ids: set[str] = set()
        for statement in evidence_statements:
            evidence_run_ids.update(await self._run_scalars(statement))
        if not evidence_run_ids:
            return None
        if len(evidence_run_ids) != 1:
            raise RunStoredRecordIntegrityError(
                "player character has contradictory surviving binding evidence"
            )

        run_id = RunId(value=next(iter(evidence_run_ids)))
        statement = select(RunCurrentRow).where(
            RunCurrentRow.run_id == run_id.value
        )
        if for_update:
            statement = statement.with_for_update()
        current_row = await self._run_scalar(statement)
        if current_row is None:
            raise RunStoredRecordIntegrityError(
                "active binding has no current Run row"
            )
        run = await self._validate_complete_run(
            run_id,
            current_row=current_row,
            lock_related=for_update,
        )
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

    async def _validate_complete_run_family(
        self,
        run_id: RunId,
        *,
        current_row: RunCurrentRow | None = None,
        creation_receipt_override: StoredRunCreationReceiptRecord | None = None,
        mutation_receipt_override: StoredRunMutationReceiptRecord | None = None,
        lock_related: bool = False,
    ) -> (
        tuple[
            CanonicalRun,
            tuple[StoredRunMutationReceiptRecord, ...],
        ]
        | None
    ):
        if current_row is None:
            current_statement = select(RunCurrentRow).where(
                RunCurrentRow.run_id == run_id.value
            )
            if lock_related:
                current_statement = current_statement.with_for_update()
            current_row = await self._run_scalar(
                current_statement
            )
        if current_row is None:
            await self._raise_if_missing_run_has_evidence(run_id)
            return None
        current = self._current_run_record(current_row)
        if current.run_id != run_id:
            raise RunStoredRecordIntegrityError(
                "current Run lookup identity is mismatched"
            )
        revision_statement = (
            select(RunRevisionRow)
            .where(RunRevisionRow.run_id == run_id.value)
            .order_by(RunRevisionRow.state_version)
        )
        participation_statement = (
            select(RunSessionParticipationRow)
            .where(RunSessionParticipationRow.run_id == run_id.value)
            .order_by(
                RunSessionParticipationRow.joined_state_version,
                RunSessionParticipationRow.session_id,
            )
        )
        creation_statement = select(RunCreationReceiptRow).where(
            RunCreationReceiptRow.result_run_id == run_id.value
        )
        mutation_statement = (
            select(RunMutationReceiptRow)
            .where(RunMutationReceiptRow.run_id == run_id.value)
            .order_by(
                RunMutationReceiptRow.resulting_state_version,
                RunMutationReceiptRow.operation_id,
            )
        )
        if lock_related:
            revision_statement = revision_statement.with_for_update()
            participation_statement = (
                participation_statement.with_for_update()
            )
            creation_statement = creation_statement.with_for_update()
            mutation_statement = mutation_statement.with_for_update()
        revision_rows = await self._run_scalars(revision_statement)
        participation_rows = await self._run_scalars(participation_statement)
        creation_row = await self._run_scalar(creation_statement)
        mutation_rows = await self._run_scalars(mutation_statement)
        creation = (
            creation_receipt_override
            if creation_receipt_override is not None
            else (
                self._run_creation_receipt_record(creation_row)
                if creation_row is not None
                else None
            )
        )
        mutations = tuple(
            self._run_mutation_receipt_record(row) for row in mutation_rows
        )
        if mutation_receipt_override is not None:
            mutations += (mutation_receipt_override,)
        referenced_player_character_revision = None
        if (
            current.binding_player_character_id is not None
            and current.binding_contract_version is not None
            and current.binding_record_revision is not None
        ):
            try:
                reference = ApplicableCharacterReference(
                    player_character_id=PlayerCharacterId(
                        value=current.binding_player_character_id
                    ),
                    contract_version=PlayerCharacterContractVersion(
                        current.binding_contract_version
                    ),
                    record_revision=PlayerCharacterRevision(
                        value=current.binding_record_revision
                    ),
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise RunStoredRecordIntegrityError(
                    "stored Run binding reference is invalid"
                ) from exc
            reference_statement = select(
                PlayerCharacterRevisionRow
            ).where(
                PlayerCharacterRevisionRow.player_character_id
                == reference.player_character_id.value,
                PlayerCharacterRevisionRow.record_revision
                == reference.record_revision.value,
            )
            referenced_row = await self._run_scalar(
                reference_statement
            )
            if referenced_row is not None:
                try:
                    referenced_player_character_revision = (
                        canonical_record_from_revision_storage(
                            _SqlAlchemyPlayerCharacterRepositorySupport._revision_record(
                                referenced_row
                            )
                        )
                    )
                except PlayerCharacterStoredRecordIntegrityError as exc:
                    raise RunStoredRecordIntegrityError(
                        "referenced immutable player-character revision "
                        "is invalid"
                    ) from exc
        run = validate_stored_run_record_set(
            creation_receipt=creation,
            mutation_receipts=mutations,
            revisions=tuple(
                self._run_revision_record(row) for row in revision_rows
            ),
            current=current,
            participations=tuple(
                self._run_participation_record(row)
                for row in participation_rows
            ),
            referenced_player_character_revision=(
                referenced_player_character_revision
            ),
        )
        return run, mutations

    async def _validate_complete_run(
        self,
        run_id: RunId,
        *,
        current_row: RunCurrentRow | None = None,
        creation_receipt_override: StoredRunCreationReceiptRecord | None = None,
        mutation_receipt_override: StoredRunMutationReceiptRecord | None = None,
        lock_related: bool = False,
    ) -> CanonicalRun | None:
        family = await self._validate_complete_run_family(
            run_id,
            current_row=current_row,
            creation_receipt_override=creation_receipt_override,
            mutation_receipt_override=mutation_receipt_override,
            lock_related=lock_related,
        )
        return family[0] if family is not None else None


class SqlAlchemyRunRepository(_SqlAlchemyRunRepositorySupport, RunRepository):
    async def get(self, run_id: RunId) -> CanonicalRun | None:
        row = await self._run_scalar(
            select(RunCurrentRow).where(RunCurrentRow.run_id == run_id.value)
        )
        if row is None:
            await self._raise_if_missing_run_has_evidence(run_id)
            return None
        return await self._validate_complete_run(
            run_id,
            current_row=row,
        )

    async def get_for_update(self, run_id: RunId) -> CanonicalRun | None:
        row = await self._run_scalar(
            select(RunCurrentRow)
            .where(RunCurrentRow.run_id == run_id.value)
            .with_for_update()
        )
        if row is None:
            await self._raise_if_missing_run_has_evidence(run_id)
            return None
        return await self._validate_complete_run(
            run_id,
            current_row=row,
            lock_related=True,
        )

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
        current_row = await self._run_scalar(
            select(RunCurrentRow)
            .where(RunCurrentRow.run_id == run_id.value)
            .with_for_update()
        )
        if current_row is None:
            await self._raise_if_missing_run_has_evidence(run_id)
            return None
        current_record = self._current_run_record(current_row)
        if current_record.run_id != run_id:
            raise RunStoredRecordIntegrityError(
                "current Run lookup identity is mismatched"
            )
        family = await self._validate_complete_run_family(
            run_id,
            current_row=current_row,
            lock_related=True,
        )
        if family is None:
            raise RunStoredRecordIntegrityError(
                "locked Run family is missing"
            )
        current, mutation_receipts = family
        attachment_receipt_records = tuple(
            stored
            for stored in mutation_receipts
            if (
                stored.run_id == run_id
                and stored.operation_namespace
                == receipt_key.operation_namespace.value
                and stored.operation_id == receipt_key.operation_id
            )
        )
        if len(attachment_receipt_records) > 1:
            raise RunStoredRecordIntegrityError(
                "Run attachment receipt evidence is duplicated"
            )
        attachment_receipt = None
        if attachment_receipt_records:
            attachment_receipt = run_mutation_receipt_from_storage(
                attachment_receipt_records[0]
            )
            if attachment_receipt.key != receipt_key:
                raise RunStoredRecordIntegrityError(
                    "Run attachment receipt lookup identity is mismatched"
                )

        return RunSessionAttachmentLockEvidence(
            canonical_run=current,
            attachment_receipt=attachment_receipt,
        )

    async def get_active_for_player_character(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalRun | None:
        return await self._active_run_for_player_character(
            player_character_id,
            for_update=False,
        )

    async def get_active_for_player_character_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalRun | None:
        return await self._active_run_for_player_character(
            player_character_id,
            for_update=True,
        )

    async def add_initial(
        self,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> None:
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
        revision_row = self._run_revision_row(run, created_at=created_at)
        current_row = self._current_run_row(run, created_at=created_at)
        if canonical_run_from_revision_storage(
            self._run_revision_record(revision_row),
            participations=(),
        ) != run:
            raise RunStoredRecordIntegrityError(
                "initial Run storage mapping is inconsistent"
            )
        await self._flush_run_row(
            revision_row,
            conflict_message="initial Run revision conflict",
        )
        await self._flush_run_row(
            current_row,
            conflict_message="initial current Run conflict",
        )

    async def append_revision(
        self,
        run: CanonicalRun,
        *,
        created_at: datetime,
    ) -> None:
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
        current = await self._validate_complete_run(run.run_id)
        if current is None:
            raise RunRepositoryConflictError(
                "successor Run has no current row"
            )
        if (
            current.state_version != prior
            or current.run_id != run.run_id
            or current.continuous_story_line_id
            != run.continuous_story_line_id
            or run.state_version.value != current.state_version.value + 1
        ):
            raise RunRepositoryConflictError("successor Run revision is stale")
        row = self._run_revision_row(run, created_at=created_at)
        mutation_kind = run.current_mutation_provenance.mutation_kind
        if mutation_kind is RunMutationKind.ATTACH_SESSION:
            if not run.trusted_participation_references:
                raise RunStoredRecordIntegrityError(
                    "successor Run participation is missing"
                )
            participation = run.trusted_participation_references[-1]
            if (
                participation.joined_state_version != run.state_version
                or participation.operation_id
                != run.current_mutation_provenance.operation_id
                or run.player_character_binding
                != current.player_character_binding
            ):
                raise RunStoredRecordIntegrityError(
                    "successor Run participation is inconsistent"
                )
        else:
            binding = run.player_character_binding
            if (
                current.player_character_binding is not None
                or binding is None
                or run.trusted_participation_references
                != current.trusted_participation_references
                or binding.binding_operation_id
                != run.current_mutation_provenance.operation_id
                or binding.binding_authority_source_ref
                != run.current_mutation_provenance.source_reference
                or binding.bound_at
                != run.current_mutation_provenance.occurred_at
            ):
                raise RunStoredRecordIntegrityError(
                    "successor Run binding is inconsistent"
                )
        await self._flush_run_row(
            row,
            conflict_message="Run revision insertion conflict",
        )

    async def compare_and_swap_current(
        self,
        run: CanonicalRun,
        *,
        expected_state_version: int,
        updated_at: datetime,
    ) -> bool:
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
        persisted = await self._run_at_revision(
            run.run_id,
            run.state_version.value,
        )
        if persisted != run:
            raise RunStoredRecordIntegrityError(
                "successor Run revision does not match current candidate"
            )
        values = self._run_core_values(run)
        values.pop("run_id")
        values.pop("continuous_story_line_id")
        values["active_player_character_id"] = (
            run.player_character_binding.applicable_character_reference
            .player_character_id.value
            if run.player_character_binding is not None
            else None
        )
        values["updated_at"] = updated_at
        try:
            result = await self._session.execute(
                update(RunCurrentRow)
                .where(
                    RunCurrentRow.run_id == run.run_id.value,
                    RunCurrentRow.continuous_story_line_id
                    == run.continuous_story_line_id.value,
                    RunCurrentRow.state_version == expected_state_version,
                )
                .values(**values)
            )
        except IntegrityError as exc:
            if (
                run.current_mutation_provenance.mutation_kind
                is RunMutationKind.BIND_PLAYER_CHARACTER
                and _is_mysql_duplicate_key(exc)
            ):
                raise RunPlayerCharacterBindingUniquenessConflictError(
                    "active player-character binding conflict"
                ) from exc
            raise RunRepositoryError(
                "Run current compare-and-swap failed"
            ) from exc
        except DBAPIError as exc:
            raise RunRepositoryError(
                "Run current compare-and-swap failed"
            ) from exc
        return result.rowcount == 1


class SqlAlchemyRunSessionParticipationRepository(
    _SqlAlchemyRunRepositorySupport,
    RunSessionParticipationRepository,
):
    async def get(
        self,
        session_id: str,
    ) -> RunSessionParticipationReference | None:
        row = await self._run_scalar(
            select(RunSessionParticipationRow).where(
                RunSessionParticipationRow.session_id == session_id
            )
        )
        if row is None:
            return None
        stored = self._run_participation_record(row)
        participation = participation_from_storage(stored)
        if participation.session_id != session_id:
            raise RunStoredRecordIntegrityError(
                "Run participation lookup identity is mismatched"
            )
        run = await self._validate_complete_run(participation.run_id)
        if run is None or participation not in run.trusted_participation_references:
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
        stored = StoredRunSessionParticipationRecord(
            session_id=participation.session_id,
            run_id=participation.run_id,
            continuous_story_line_id=(
                participation.continuous_story_line_id
            ),
            joined_state_version=participation.joined_state_version.value,
            operation_id=participation.operation_id,
            source_reference=participation.source_reference,
            joined_at=joined_at,
        )
        if participation_from_storage(stored) != participation:
            raise RunStoredRecordIntegrityError(
                "Run participation storage mapping is inconsistent"
            )
        revision = await self._load_run_revision(
            participation.run_id,
            participation.joined_state_version.value,
        )
        if revision is None:
            raise RunStoredRecordIntegrityError(
                "Run participation revision is missing"
            )
        revision_stored = self._run_revision_record(revision)
        if (
            revision_stored.run_id != participation.run_id
            or revision_stored.continuous_story_line_id
            != participation.continuous_story_line_id
            or revision_stored.mutation_kind
            != RunMutationKind.ATTACH_SESSION.value
            or revision_stored.operation_id != participation.operation_id
            or revision_stored.source_reference
            != participation.source_reference
            or revision_stored.occurred_at != joined_at
        ):
            raise RunStoredRecordIntegrityError(
                "Run participation does not bind its revision"
            )
        row = RunSessionParticipationRow(
            session_id=stored.session_id,
            run_id=stored.run_id.value,
            continuous_story_line_id=(
                stored.continuous_story_line_id.value
            ),
            joined_state_version=stored.joined_state_version,
            operation_id=stored.operation_id.value,
            source_reference=stored.source_reference.value,
            joined_at=joined_at,
        )
        await self._flush_run_row(
            row,
            conflict_message="Run Session participation conflict",
            conflict_type=RunSessionParticipationUniquenessConflictError,
        )


class SqlAlchemyRunCreationReceiptRepository(
    _SqlAlchemyRunRepositorySupport,
    RunCreationReceiptRepository,
):
    async def get(
        self,
        key: RunReceiptKey,
    ) -> StoredRunSuccessReceipt | None:
        if key.operation_namespace is not RunOperationNamespace.CREATE_V1:
            raise ValueError("Run creation receipt repository rejects namespace")
        row = await self._run_scalar(
            select(RunCreationReceiptRow).where(
                RunCreationReceiptRow.operation_namespace
                == key.operation_namespace.value,
                RunCreationReceiptRow.operation_id
                == key.operation_id.value,
            )
        )
        if row is None:
            return None
        stored = self._run_creation_receipt_record(row)
        receipt = run_creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt lookup identity is mismatched"
            )
        await self._validate_complete_run(receipt.result.run_id)
        return receipt

    async def get_with_evidence(
        self, key: RunReceiptKey
    ) -> StoredRunCreationEvidence | None:
        if key.operation_namespace is not RunOperationNamespace.CREATE_V1:
            raise ValueError("Run creation receipt repository rejects namespace")
        row = await self._run_scalar(
            select(RunCreationReceiptRow).where(
                RunCreationReceiptRow.operation_namespace
                == key.operation_namespace.value,
                RunCreationReceiptRow.operation_id == key.operation_id.value,
            )
        )
        if row is None:
            return None
        stored = self._run_creation_receipt_record(row)
        receipt = run_creation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt lookup identity is mismatched"
            )
        evidence = creation_evidence_from_storage(
            stored.operation_evidence_canonical
        )
        await self._validate_complete_run(receipt.result.run_id)
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
        """Persist the validated P8 composite in the existing receipt column."""
        if (
            receipt.key.operation_namespace
            is not RunOperationNamespace.CREATE_V1
            or receipt.command_kind is not RunMutationKind.CREATE
        ):
            raise ValueError("Run creation receipt repository rejects command")
        evidence_bytes, fingerprint = run_entry_creation_fingerprint(evidence)
        if receipt.fingerprint != fingerprint:
            raise RunStoredRecordIntegrityError(
                "P8 receipt fingerprint does not bind composite evidence"
            )
        result = receipt.result
        revision = await self._run_at_revision(
            result.run_id, result.resulting_state_version.value
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
            operation_evidence_canonical=evidence_bytes,
            created_at=created_at,
        )
        if (
            run_creation_receipt_from_storage(stored) != receipt
            or revision.creation_provenance.source_reference
            != evidence.trusted_run_source.source_reference
            or revision.creation_provenance.operation_id
            != receipt.key.operation_id
            or revision.creation_provenance.occurred_at != created_at
        ):
            raise RunStoredRecordIntegrityError(
                "P8 Run creation receipt storage mapping is inconsistent"
            )
        row = RunCreationReceiptRow(
            operation_namespace=stored.operation_namespace,
            operation_id=stored.operation_id.value,
            fingerprint=stored.fingerprint,
            command_kind=stored.command_kind,
            result_schema_version=stored.result_schema_version,
            result_run_id=stored.result_run_id.value,
            result_continuous_story_line_id=(
                stored.result_continuous_story_line_id.value
            ),
            resulting_lifecycle_status=stored.resulting_lifecycle_status,
            resulting_state_version=stored.resulting_state_version,
            receipt_canonical=stored.receipt_canonical,
            operation_evidence_canonical=stored.operation_evidence_canonical,
            created_at=created_at,
        )
        await self._flush_run_row(
            row,
            conflict_message="Run creation receipt conflict",
            conflict_type=RunReceiptUniquenessConflictError,
        )

    async def add(
        self,
        receipt: StoredRunSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        if (
            receipt.key.operation_namespace
            is not RunOperationNamespace.CREATE_V1
            or receipt.command_kind is not RunMutationKind.CREATE
        ):
            raise ValueError("Run creation receipt repository rejects command")
        result = receipt.result
        revision = await self._run_at_revision(
            result.run_id,
            result.resulting_state_version.value,
        )
        command = CreateRunCommand(
            source_reference=revision.creation_provenance.source_reference
        )
        stored = StoredRunCreationReceiptRecord(
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id,
            fingerprint=run_fingerprint_to_storage_bytes(
                receipt.fingerprint
            ),
            command_kind=receipt.command_kind.value,
            result_schema_version=result.result_schema_version,
            result_run_id=result.run_id,
            result_continuous_story_line_id=(
                result.continuous_story_line_id
            ),
            resulting_lifecycle_status=result.lifecycle_status.value,
            resulting_state_version=result.resulting_state_version.value,
            receipt_canonical=run_receipt_to_storage_bytes(receipt),
            operation_evidence_canonical=(
                run_creation_evidence_bytes(command)
            ),
            created_at=created_at,
        )
        if run_creation_receipt_from_storage(stored) != receipt:
            raise RunStoredRecordIntegrityError(
                "Run creation receipt storage mapping is inconsistent"
            )
        await self._validate_complete_run(
            result.run_id,
            creation_receipt_override=stored,
        )
        row = RunCreationReceiptRow(
            operation_namespace=stored.operation_namespace,
            operation_id=stored.operation_id.value,
            fingerprint=stored.fingerprint,
            command_kind=stored.command_kind,
            result_schema_version=stored.result_schema_version,
            result_run_id=stored.result_run_id.value,
            result_continuous_story_line_id=(
                stored.result_continuous_story_line_id.value
            ),
            resulting_lifecycle_status=(
                stored.resulting_lifecycle_status
            ),
            resulting_state_version=stored.resulting_state_version,
            receipt_canonical=stored.receipt_canonical,
            operation_evidence_canonical=(
                stored.operation_evidence_canonical
            ),
            created_at=created_at,
        )
        await self._flush_run_row(
            row,
            conflict_message="Run creation receipt conflict",
            conflict_type=RunReceiptUniquenessConflictError,
        )


class SqlAlchemyRunMutationReceiptRepository(
    _SqlAlchemyRunRepositorySupport,
    RunMutationReceiptRepository,
):
    async def get(
        self,
        key: RunReceiptKey,
    ) -> StoredRunSuccessReceipt | None:
        if key.operation_namespace not in {
            RunOperationNamespace.ATTACH_SESSION_V1,
            RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
        }:
            raise ValueError("minimum Run mutation repository rejects namespace")
        row = await self._run_scalar(
            select(RunMutationReceiptRow).where(
                RunMutationReceiptRow.run_id == key.run_id.value,
                RunMutationReceiptRow.operation_namespace
                == key.operation_namespace.value,
                RunMutationReceiptRow.operation_id
                == key.operation_id.value,
            )
        )
        if row is None:
            return None
        stored = self._run_mutation_receipt_record(row)
        receipt = run_mutation_receipt_from_storage(stored)
        if receipt.key != key:
            raise RunStoredRecordIntegrityError(
                "Run mutation receipt lookup identity is mismatched"
            )
        await self._validate_complete_run(key.run_id)
        return receipt

    async def add(
        self,
        receipt: StoredRunSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
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
        result = receipt.result
        expected_version = result.resulting_state_version.value - 1
        before = await self._run_at_revision(
            receipt.key.run_id,
            expected_version,
        )
        after = await self._run_at_revision(
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
            command: AttachSessionCommand | BindPlayerCharacterCommand = (
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
            if (
                before.player_character_binding is not None
                or after.player_character_binding is None
                or after.player_character_binding.applicable_character_reference
                != character_reference
            ):
                raise RunStoredRecordIntegrityError(
                    "Run binding receipt does not match Run history"
                )
            command = BindPlayerCharacterCommand(
                run_id=after.run_id,
                continuous_story_line_id=after.continuous_story_line_id,
                target_player_character_id=(
                    character_reference.player_character_id
                ),
                expected_state_version=before.state_version,
                source_reference=(
                    after.current_mutation_provenance.source_reference
                ),
            )
            operation_evidence = (
                binding_operation_evidence_to_storage_bytes(command)
            )
        stored = StoredRunMutationReceiptRecord(
            run_id=receipt.key.run_id,
            operation_namespace=receipt.key.operation_namespace.value,
            operation_id=receipt.key.operation_id,
            fingerprint=run_fingerprint_to_storage_bytes(
                receipt.fingerprint
            ),
            command_kind=receipt.command_kind.value,
            result_schema_version=result.result_schema_version,
            expected_state_version=expected_version,
            result_run_id=result.run_id,
            result_continuous_story_line_id=(
                result.continuous_story_line_id
            ),
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
        await self._validate_complete_run(
            receipt.key.run_id,
            mutation_receipt_override=stored,
        )
        row = RunMutationReceiptRow(
            run_id=stored.run_id.value,
            operation_namespace=stored.operation_namespace,
            operation_id=stored.operation_id.value,
            fingerprint=stored.fingerprint,
            command_kind=stored.command_kind,
            result_schema_version=stored.result_schema_version,
            expected_state_version=stored.expected_state_version,
            result_run_id=stored.result_run_id.value,
            result_continuous_story_line_id=(
                stored.result_continuous_story_line_id.value
            ),
            resulting_lifecycle_status=(
                stored.resulting_lifecycle_status
            ),
            resulting_state_version=stored.resulting_state_version,
            participation_session_id=stored.participation_session_id,
            participation_operation_id=stored.participation_operation_id,
            participation_source_reference=(
                stored.participation_source_reference
            ),
            result_player_character_id=stored.result_player_character_id,
            result_character_contract_version=(
                stored.result_character_contract_version
            ),
            result_character_record_revision=(
                stored.result_character_record_revision
            ),
            receipt_canonical=stored.receipt_canonical,
            operation_evidence_canonical=(
                stored.operation_evidence_canonical
            ),
            created_at=created_at,
        )
        await self._flush_run_row(
            row,
            conflict_message="Run mutation receipt conflict",
            conflict_type=RunReceiptUniquenessConflictError,
        )


def _is_mysql_duplicate_key(error: IntegrityError) -> bool:
    arguments = getattr(error.orig, "args", ())
    error_code = arguments[0] if arguments else None
    return type(error_code) is int and error_code == 1062
