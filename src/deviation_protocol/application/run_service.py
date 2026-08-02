from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import (
    ControllerBindingResolver,
    ContinuousStoryLineIdIssuer,
    PlayerCharacterBindingEvidenceReader,
    RunIdIssuer,
    RunPlayerCharacterBindingUniquenessConflictError,
    RunReceiptUniquenessConflictError,
    RunSessionAttachmentLockEvidence,
    RunSessionParticipationUniquenessConflictError,
    UnitOfWork,
    UnitOfWorkFactory,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    ReservedBindPlayerCharacterCommand,
    RunEntryCreationEvidence,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecision,
    RunReplayDecisionCode,
    RunSafeResult,
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
    evaluate_receipt,
    reject_reserved_bind_player_character,
    run_entry_creation_fingerprint,
)
from deviation_protocol.domain.player_character import (
    ControllerBindingRef,
    PlayerCharacterLifecycle,
    revalidate_player_character_model,
    validate_applicable_character_reference,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunLifecycleStatus,
    RunMutationKind,
    RunOperationId,
    RunStateVersion,
    revalidate_run_model,
    validate_canonical_run,
)


class RunServiceDecisionCode(StrEnum):
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    TARGET_MISMATCH = "TARGET_MISMATCH"
    NON_ACTIVE_RUN = "NON_ACTIVE_RUN"
    STALE_VERSION = "STALE_VERSION"
    VERSION_EXHAUSTED = "VERSION_EXHAUSTED"
    SESSION_PARTICIPATION_CONFLICT = "SESSION_PARTICIPATION_CONFLICT"
    CONCURRENT_STATE_CONFLICT = "CONCURRENT_STATE_CONFLICT"
    PLAYER_CHARACTER_INELIGIBLE = "PLAYER_CHARACTER_INELIGIBLE"
    PLAYER_CHARACTER_BINDING_CONFLICT = (
        "PLAYER_CHARACTER_BINDING_CONFLICT"
    )


class RunServiceDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    code: RunServiceDecisionCode


def _validate_entry_stage_time(run: CanonicalRun, created_at: datetime) -> None:
    if (
        type(created_at) is not datetime
        or created_at.tzinfo is None
        or created_at.utcoffset() != timedelta(0)
        or run.current_mutation_provenance.occurred_at != created_at
    ):
        raise ValueError("Run entry staging timestamp is inconsistent")


async def stage_run_entry_creation(
    uow: UnitOfWork,
    run: CanonicalRun,
    receipt: StoredRunSuccessReceipt,
    evidence: RunEntryCreationEvidence,
    *,
    created_at: datetime,
) -> None:
    """Stage revision one and its composite receipt without committing."""

    run = validate_canonical_run(run)
    receipt = revalidate_run_model(receipt, StoredRunSuccessReceipt)
    evidence = revalidate_run_model(evidence, RunEntryCreationEvidence)
    _validate_entry_stage_time(run, created_at)
    _, fingerprint = run_entry_creation_fingerprint(evidence)
    if (
        run.state_version.value != 1
        or receipt.key.operation_id != run.creation_provenance.operation_id
        or receipt.fingerprint != fingerprint
        or receipt.result != creation_result(run)
        or evidence.trusted_run_source.source_reference
        != run.creation_provenance.source_reference
    ):
        raise ValueError("Run entry creation staging evidence is inconsistent")
    await uow.runs.add_initial(run, created_at=created_at)
    await uow.run_creation_receipts.add_with_evidence(
        receipt, evidence, created_at=created_at
    )


async def stage_run_entry_binding(
    uow: UnitOfWork,
    run: CanonicalRun,
    receipt: StoredRunSuccessReceipt,
    *,
    created_at: datetime,
) -> bool:
    """Stage revision two, its current-row CAS, and receipt without commit."""

    run = validate_canonical_run(run)
    receipt = revalidate_run_model(receipt, StoredRunSuccessReceipt)
    _validate_entry_stage_time(run, created_at)
    binding = run.player_character_binding
    if (
        run.state_version.value != 2
        or run.current_mutation_provenance.mutation_kind
        is not RunMutationKind.BIND_PLAYER_CHARACTER
        or binding is None
        or receipt.key.run_id != run.run_id
        or receipt.key.operation_id
        != run.current_mutation_provenance.operation_id
        or receipt.result != bind_player_character_result(run)
    ):
        raise ValueError("Run entry binding staging evidence is inconsistent")
    command = BindPlayerCharacterCommand(
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        target_player_character_id=(
            binding.applicable_character_reference.player_character_id
        ),
        expected_state_version=RunStateVersion(value=1),
        source_reference=run.current_mutation_provenance.source_reference,
    )
    _, fingerprint = bind_player_character_fingerprint(
        command, operation_id=run.current_mutation_provenance.operation_id
    )
    if receipt.fingerprint != fingerprint:
        raise ValueError("Run entry binding receipt fingerprint is inconsistent")
    await uow.runs.append_revision(run, created_at=created_at)
    won = await uow.runs.compare_and_swap_current(
        run, expected_state_version=1, updated_at=created_at
    )
    if not won:
        return False
    await uow.run_mutation_receipts.add(receipt, created_at=created_at)
    return True


async def stage_run_entry_activation(
    uow: UnitOfWork,
    run: CanonicalRun,
    receipt: StoredRunSuccessReceipt,
    *,
    created_at: datetime,
) -> bool:
    """Stage the sole P8 revision-three activation without committing."""

    run = validate_canonical_run(run)
    receipt = revalidate_run_model(receipt, StoredRunSuccessReceipt)
    _validate_entry_stage_time(run, created_at)
    if (
        run.lifecycle_status is not RunLifecycleStatus.ACTIVE
        or run.state_version.value != 3
        or run.current_mutation_provenance.mutation_kind
        is not RunMutationKind.ATTACH_SESSION
        or len(run.trusted_participation_references) != 1
        or receipt.key.run_id != run.run_id
        or receipt.key.operation_id
        != run.current_mutation_provenance.operation_id
        or receipt.result != attach_session_result(run)
    ):
        raise ValueError("Run entry activation staging evidence is inconsistent")
    participation = run.trusted_participation_references[0]
    command = AttachSessionCommand(
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        session_id=participation.session_id,
        expected_state_version=RunStateVersion(value=2),
        source_reference=run.current_mutation_provenance.source_reference,
    )
    _, fingerprint = attach_session_fingerprint(
        command, operation_id=run.current_mutation_provenance.operation_id
    )
    if receipt.fingerprint != fingerprint:
        raise ValueError("Run entry attachment receipt fingerprint is inconsistent")
    await uow.runs.append_revision(run, created_at=created_at)
    await uow.run_participations.add(participation, joined_at=created_at)
    won = await uow.runs.compare_and_swap_current(
        run, expected_state_version=2, updated_at=created_at
    )
    if not won:
        return False
    await uow.run_mutation_receipts.add(receipt, created_at=created_at)
    return True


@dataclass(slots=True)
class RunService:
    uow_factory: UnitOfWorkFactory
    run_id_issuer: RunIdIssuer
    continuous_story_line_id_issuer: ContinuousStoryLineIdIssuer
    source_reference: RunAuthoritySourceRef
    clock: Callable[[], datetime]
    controller_binding_resolver: ControllerBindingResolver
    player_character_binding_evidence: (
        PlayerCharacterBindingEvidenceReader
    )

    def __post_init__(self) -> None:
        self.source_reference = revalidate_run_model(
            self.source_reference,
            RunAuthoritySourceRef,
        )

    async def create_run(
        self,
        *,
        operation_id: RunOperationId,
        command: CreateRunCommand,
    ) -> RunSafeResult | RunReplayDecision:
        command = self._trusted_command(command, CreateRunCommand)
        operation_id = revalidate_run_model(operation_id, RunOperationId)
        _, fingerprint = create_run_fingerprint(command)
        receipt_key = RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=operation_id,
        )

        async with self.uow_factory() as uow:
            stored_receipt = await uow.run_creation_receipts.get(receipt_key)
            replay = evaluate_receipt(
                stored_receipt,
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.CREATE,
            )
            if replay.code is RunReplayDecisionCode.REPLAY:
                result = replay.stored_success_result
                if not isinstance(result, RunSafeResult):
                    raise ValueError("Run creation replay has no safe result")
                return result
            if replay.code is RunReplayDecisionCode.CONFLICT:
                return replay

            run_id = revalidate_run_model(
                self.run_id_issuer.issue(),
                RunId,
            )
            line_id = revalidate_run_model(
                self.continuous_story_line_id_issuer.issue(),
                ContinuousStoryLineId,
            )
            occurred_at = self._occurred_at()
            run = construct_created_run(
                command,
                run_id=run_id,
                continuous_story_line_id=line_id,
                operation_id=operation_id,
                occurred_at=occurred_at,
            )
            run = validate_canonical_run(run)
            result = creation_result(run)
            receipt = StoredRunSuccessReceipt(
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.CREATE,
                result=result,
            )
            await uow.runs.add_initial(run, created_at=occurred_at)
            try:
                await uow.run_creation_receipts.add(
                    receipt,
                    created_at=occurred_at,
                )
            except RunReceiptUniquenessConflictError:
                return RunReplayDecision(code=RunReplayDecisionCode.CONFLICT)
            await uow.commit()
            return result

    async def get_run(self, *, run_id: RunId) -> CanonicalRun | None:
        run_id = revalidate_run_model(run_id, RunId)
        async with self.uow_factory() as uow:
            run = await uow.runs.get(run_id)
            return validate_canonical_run(run) if run is not None else None

    async def attach_session(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: RunOperationId,
        command: AttachSessionCommand,
    ) -> RunSafeResult | RunReplayDecision | RunServiceDecision:
        principal = self._principal(principal)
        command = self._trusted_command(command, AttachSessionCommand)
        operation_id = revalidate_run_model(operation_id, RunOperationId)
        _, fingerprint = attach_session_fingerprint(
            command,
            operation_id=operation_id,
        )
        receipt_key = RunReceiptKey(
            run_id=command.run_id,
            operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
            operation_id=operation_id,
        )

        async with self.uow_factory() as uow:
            owned_session = await uow.sessions.get_owned_for_update(
                command.session_id,
                principal.player_id,
            )
            if owned_session is None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.AUTHORIZATION_FAILED
                )
            if (
                owned_session.session.session_id != command.session_id
                or owned_session.session.player_id != principal.player_id
            ):
                raise ValueError("Session ownership lookup returned mismatched state")

            lock_evidence = (
                await uow.runs.get_session_attachment_lock_evidence(
                    command.run_id,
                    receipt_key=receipt_key,
                )
            )
            if lock_evidence is None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.RUN_NOT_FOUND
                )
            if type(lock_evidence) is not RunSessionAttachmentLockEvidence:
                raise TypeError(
                    "Run attachment lock returned invalid evidence"
                )
            current = validate_canonical_run(
                lock_evidence.canonical_run
            )
            if current.run_id != command.run_id:
                raise ValueError(
                    "Run attachment lock returned mismatched evidence"
                )

            replay = evaluate_receipt(
                lock_evidence.attachment_receipt,
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.ATTACH_SESSION,
            )
            if replay.code is RunReplayDecisionCode.REPLAY:
                result = replay.stored_success_result
                if not isinstance(result, RunSafeResult):
                    raise ValueError("Run attachment replay has no safe result")
                return result
            if replay.code is RunReplayDecisionCode.CONFLICT:
                return replay

            if current.continuous_story_line_id != command.continuous_story_line_id:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.TARGET_MISMATCH
                )
            if not current.lifecycle_status.is_active_line:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.NON_ACTIVE_RUN
                )
            if not current.state_version.has_successor:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.VERSION_EXHAUSTED
                )
            if command.expected_state_version != current.state_version:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.STALE_VERSION
                )
            if await uow.run_participations.get(command.session_id) is not None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.SESSION_PARTICIPATION_CONFLICT
                )

            occurred_at = self._occurred_at()
            successor = attach_session_to_run(
                current,
                command,
                operation_id=operation_id,
                occurred_at=occurred_at,
            )
            successor = validate_canonical_run(successor)
            result = attach_session_result(successor)
            receipt = StoredRunSuccessReceipt(
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.ATTACH_SESSION,
                result=result,
            )
            participation = successor.trusted_participation_references[-1]
            await uow.runs.append_revision(
                successor,
                created_at=occurred_at,
            )
            try:
                await uow.run_participations.add(
                    participation,
                    joined_at=occurred_at,
                )
            except RunSessionParticipationUniquenessConflictError:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.SESSION_PARTICIPATION_CONFLICT
                )
            won_current = await uow.runs.compare_and_swap_current(
                successor,
                expected_state_version=current.state_version.value,
                updated_at=occurred_at,
            )
            if not won_current:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.CONCURRENT_STATE_CONFLICT
                )
            try:
                await uow.run_mutation_receipts.add(
                    receipt,
                    created_at=occurred_at,
                )
            except RunReceiptUniquenessConflictError:
                return RunReplayDecision(code=RunReplayDecisionCode.CONFLICT)
            await uow.commit()
            return result

    async def bind_player_character_internal(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: RunOperationId,
        command: BindPlayerCharacterCommand,
    ) -> RunSafeResult | RunReplayDecision | RunServiceDecision:
        """Atomically bind one owned active character to one active Run line."""

        principal = self._principal(principal)
        command = self._trusted_command(
            command,
            BindPlayerCharacterCommand,
        )
        operation_id = revalidate_run_model(operation_id, RunOperationId)
        controller_binding = await self.controller_binding_resolver.resolve(
            principal
        )
        try:
            controller_binding = revalidate_player_character_model(
                controller_binding,
                ControllerBindingRef,
            )
        except (AttributeError, TypeError, ValueError):
            return RunServiceDecision(
                code=RunServiceDecisionCode.AUTHORIZATION_FAILED
            )

        _, fingerprint = bind_player_character_fingerprint(
            command,
            operation_id=operation_id,
        )
        receipt_key = RunReceiptKey(
            run_id=command.run_id,
            operation_namespace=(
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            operation_id=operation_id,
        )

        async with self.uow_factory() as uow:
            character_evidence = (
                await self.player_character_binding_evidence.lock_owned_for_binding(
                    uow,
                    trusted_controller_binding=controller_binding,
                    target_player_character_id=(
                        command.target_player_character_id
                    ),
                )
            )
            if character_evidence is None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.AUTHORIZATION_FAILED
                )
            applicable_reference = validate_applicable_character_reference(
                character_evidence.applicable_character_reference
            )
            lifecycle = PlayerCharacterLifecycle(
                character_evidence.lifecycle
            )

            current = await uow.runs.get_for_update(command.run_id)
            if current is None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.RUN_NOT_FOUND
                )
            current = validate_canonical_run(current)

            stored_receipt = await uow.run_mutation_receipts.get(
                receipt_key
            )
            replay = evaluate_receipt(
                stored_receipt,
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
            )
            if replay.code is RunReplayDecisionCode.REPLAY:
                result = replay.stored_success_result
                if not isinstance(result, RunSafeResult):
                    raise ValueError("Run binding replay has no safe result")
                return result
            if replay.code is RunReplayDecisionCode.CONFLICT:
                return replay

            if (
                current.continuous_story_line_id
                != command.continuous_story_line_id
            ):
                return RunServiceDecision(
                    code=RunServiceDecisionCode.TARGET_MISMATCH
                )
            if not current.lifecycle_status.is_active_line:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.NON_ACTIVE_RUN
                )
            if not current.state_version.has_successor:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.VERSION_EXHAUSTED
                )
            if command.expected_state_version != current.state_version:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.STALE_VERSION
                )
            if lifecycle is not PlayerCharacterLifecycle.ACTIVE:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.PLAYER_CHARACTER_INELIGIBLE
                )
            if current.player_character_binding is not None:
                return RunServiceDecision(
                    code=(
                        RunServiceDecisionCode
                        .PLAYER_CHARACTER_BINDING_CONFLICT
                    )
                )
            occupied = await uow.runs.get_active_for_player_character(
                command.target_player_character_id
            )
            if occupied is not None:
                validate_canonical_run(occupied)
                return RunServiceDecision(
                    code=(
                        RunServiceDecisionCode
                        .PLAYER_CHARACTER_BINDING_CONFLICT
                    )
                )

            occurred_at = self._occurred_at()
            successor = bind_player_character_to_run(
                current,
                command,
                applicable_character_reference=applicable_reference,
                operation_id=operation_id,
                occurred_at=occurred_at,
            )
            successor = validate_canonical_run(successor)
            result = bind_player_character_result(successor)
            receipt = StoredRunSuccessReceipt(
                key=receipt_key,
                fingerprint=fingerprint,
                command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
                result=result,
            )
            await uow.runs.append_revision(
                successor,
                created_at=occurred_at,
            )
            try:
                won_current = await uow.runs.compare_and_swap_current(
                    successor,
                    expected_state_version=current.state_version.value,
                    updated_at=occurred_at,
                )
            except RunPlayerCharacterBindingUniquenessConflictError:
                return RunServiceDecision(
                    code=(
                        RunServiceDecisionCode
                        .PLAYER_CHARACTER_BINDING_CONFLICT
                    )
                )
            if not won_current:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.CONCURRENT_STATE_CONFLICT
                )
            try:
                await uow.run_mutation_receipts.add(
                    receipt,
                    created_at=occurred_at,
                )
            except RunReceiptUniquenessConflictError:
                return RunReplayDecision(
                    code=RunReplayDecisionCode.CONFLICT
                )
            await uow.commit()
            return result

    def bind_player_character(
        self,
        *,
        operation_id: RunOperationId,
        command: ReservedBindPlayerCharacterCommand,
    ) -> RunReplayDecision:
        command = self._trusted_command(
            command,
            ReservedBindPlayerCharacterCommand,
        )
        return reject_reserved_bind_player_character(
            command,
            operation_id=operation_id,
        )

    def _trusted_command(self, command: object, command_type: type[object]):
        validated = revalidate_run_model(command, command_type)  # type: ignore[arg-type]
        if validated.source_reference != self.source_reference:  # type: ignore[attr-defined]
            raise ValueError("Run command source is not the configured trusted source")
        return validated

    @staticmethod
    def _principal(principal: RequestPrincipal) -> RequestPrincipal:
        if type(principal) is not RequestPrincipal:
            raise TypeError("expected RequestPrincipal")
        return RequestPrincipal.model_validate(principal.model_dump(mode="python"))

    def _occurred_at(self) -> datetime:
        value = self.clock()
        if (
            type(value) is not datetime
            or value.tzinfo is None
            or value.utcoffset() != timedelta(0)
        ):
            raise ValueError("Run clock must return an exact UTC datetime")
        return value
