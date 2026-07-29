from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import (
    ContinuousStoryLineIdIssuer,
    RunIdIssuer,
    RunReceiptUniquenessConflictError,
    RunSessionParticipationUniquenessConflictError,
    UnitOfWorkFactory,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    CreateRunCommand,
    ReservedBindPlayerCharacterCommand,
    RunOperationNamespace,
    RunReceiptKey,
    RunReplayDecision,
    RunReplayDecisionCode,
    RunSafeResult,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    attach_session_to_run,
    construct_created_run,
    create_run_fingerprint,
    creation_result,
    evaluate_receipt,
    reject_reserved_bind_player_character,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunLifecycleStatus,
    RunMutationKind,
    RunOperationId,
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


class RunServiceDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    code: RunServiceDecisionCode


@dataclass(slots=True)
class RunService:
    uow_factory: UnitOfWorkFactory
    run_id_issuer: RunIdIssuer
    continuous_story_line_id_issuer: ContinuousStoryLineIdIssuer
    source_reference: RunAuthoritySourceRef
    clock: Callable[[], datetime]

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

            current = await uow.runs.get_for_update(command.run_id)
            if current is None:
                return RunServiceDecision(
                    code=RunServiceDecisionCode.RUN_NOT_FOUND
                )
            current = validate_canonical_run(current)

            stored_receipt = await uow.run_mutation_receipts.get(receipt_key)
            replay = evaluate_receipt(
                stored_receipt,
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
