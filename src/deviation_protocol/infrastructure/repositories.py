from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import func, select, update
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
    PlayerCharacterId,
    PlayerCharacterMutationKind,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    PlayerConfirmation,
    TrustedFinalDeathEvidence,
)
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import (
    OptimisticLockError,
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

    async def _flush_row(self, row: Any, *, conflict_message: str) -> None:
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise PlayerCharacterRepositoryConflictError(
                    conflict_message
                ) from exc
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
    ) -> CanonicalPlayerCharacter | None:
        if current_row is None:
            current_row = await self._scalar(
                select(PlayerCharacterCurrentRow).where(
                    PlayerCharacterCurrentRow.player_character_id
                    == player_character_id.value
                )
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
        exact_revision_row = await self._load_revision_row(
            player_character_id,
            current_record.record_revision.value,
        )
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

        revision_rows = await self._scalars(
            select(PlayerCharacterRevisionRow)
            .where(
                PlayerCharacterRevisionRow.player_character_id
                == player_character_id.value
            )
            .order_by(PlayerCharacterRevisionRow.record_revision)
        )
        creation_row = await self._scalar(
            select(PlayerCharacterCreationReceiptRow).where(
                PlayerCharacterCreationReceiptRow.result_player_character_id
                == player_character_id.value
            )
        )
        mutation_rows = await self._scalars(
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
        binding_row = await self._scalar(
            select(PlayerCharacterControllerBindingRow).where(
                PlayerCharacterControllerBindingRow.controller_binding
                == current_record.controller_binding.value
            )
        )
        allocation_row = await self._scalar(
            select(PlayerCharacterIdAllocationRow).where(
                PlayerCharacterIdAllocationRow.player_character_id
                == player_character_id.value
            )
        )

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
        )

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
        )


def _is_mysql_duplicate_key(error: IntegrityError) -> bool:
    arguments = getattr(error.orig, "args", ())
    error_code = arguments[0] if arguments else None
    return type(error_code) is int and error_code == 1062
