"""P8-S2's internal, single-UoW Run-entry coordinator."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from collections.abc import Callable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    InvalidScenarioDefinitionError,
    SnapshotNotFoundError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.application.ports import (
    ContinuousStoryLineIdIssuer,
    ControllerBindingResolver,
    PlayerCharacterBindingEvidenceReader,
    RunIdIssuer,
    RunPlayerCharacterBindingUniquenessConflictError,
    RunReceiptUniquenessConflictError,
    RunSessionParticipationUniquenessConflictError,
    RunWriteConflictError,
    StoredRunCreationEvidence,
    UnitOfWork,
    UnitOfWorkFactory,
)
from deviation_protocol.application.run_operations import (
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    RunEntryCreationEvidence,
    RunEntryPublicOperationKey,
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
    creation_result,
    derive_run_entry_internal_id,
    run_entry_creation_fingerprint,
    run_entry_evidence_bytes,
)
from deviation_protocol.application.run_service import (
    stage_run_entry_activation,
    stage_run_entry_binding,
    stage_run_entry_creation,
)
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.player_character import (
    ControllerBindingRef,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
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


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")


class RunEntryCommand(_StrictFrozenModel):
    public_operation_key: RunEntryPublicOperationKey
    player_character_id: PlayerCharacterId
    expected_record_revision: PlayerCharacterRevision
    scenario_id: DefinitionId


class RunEntryResult(_StrictFrozenModel):
    run_id: RunId
    session_id: Annotated[
        str,
        Field(
            strict=True,
            min_length=1,
            max_length=64,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
        ),
    ]
    scenario_id: DefinitionId
    player_character: PlayerCharacterSelfProjection


class RunEntryDecisionCode(StrEnum):
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    PLAYER_CHARACTER_STALE = "PLAYER_CHARACTER_STALE"
    PLAYER_CHARACTER_NOT_ELIGIBLE = "PLAYER_CHARACTER_NOT_ELIGIBLE"
    INVALID_SCENARIO_DEFINITION = "INVALID_SCENARIO_DEFINITION"
    RUN_ENTRY_CONFLICT = "RUN_ENTRY_CONFLICT"


class RunEntryDecision(_StrictFrozenModel):
    code: RunEntryDecisionCode


class RunEntryIntegrityError(RuntimeError):
    """Trusted Run-entry evidence is impossible, incomplete, or cross-bound."""


@dataclass(frozen=True, slots=True)
class _RunEntryInternalIds:
    creation: RunOperationId
    binding: RunOperationId
    attachment: RunOperationId
    session_creation_request_id: str


@dataclass(slots=True)
class RunEntryService:
    uow_factory: UnitOfWorkFactory
    run_id_issuer: RunIdIssuer
    continuous_story_line_id_issuer: ContinuousStoryLineIdIssuer
    source_reference: RunAuthoritySourceRef
    clock: Callable[[], datetime]
    controller_binding_resolver: ControllerBindingResolver
    player_character_binding_evidence: PlayerCharacterBindingEvidenceReader
    session_service: SessionService

    def __post_init__(self) -> None:
        self.source_reference = revalidate_run_model(
            self.source_reference, RunAuthoritySourceRef
        )

    async def enter(
        self,
        principal: RequestPrincipal,
        *,
        command: RunEntryCommand,
    ) -> RunEntryResult | RunEntryDecision:
        principal = self._principal(principal)
        command = revalidate_run_model(command, RunEntryCommand)
        controller = await self.controller_binding_resolver.resolve(principal)
        if controller is None:
            return self._decision(RunEntryDecisionCode.AUTHORIZATION_FAILED)
        try:
            controller = revalidate_player_character_model(
                controller, ControllerBindingRef
            )
        except (AttributeError, TypeError, ValueError):
            return self._decision(RunEntryDecisionCode.AUTHORIZATION_FAILED)
        ids = self._derive_ids(controller, command.public_operation_key)
        receipt_key = RunReceiptKey(
            operation_namespace=RunOperationNamespace.CREATE_V1,
            operation_id=ids.creation,
        )

        async with self.uow_factory() as uow:
            character = await (
                self.player_character_binding_evidence.lock_owned_for_binding(
                    uow,
                    trusted_controller_binding=controller,
                    target_player_character_id=command.player_character_id,
                )
            )
            if character is None:
                return self._decision(RunEntryDecisionCode.AUTHORIZATION_FAILED)
            reference = validate_applicable_character_reference(
                character.applicable_character_reference
            )
            lifecycle = PlayerCharacterLifecycle(character.lifecycle)
            if reference.player_character_id != command.player_character_id:
                raise RunEntryIntegrityError(
                    "owned character evidence has a mismatched identity"
                )

            stored = await uow.run_creation_receipts.get_with_evidence(receipt_key)
            if stored is not None:
                return await self._replay(
                    uow,
                    principal=principal,
                    command=command,
                    controller=controller,
                    stored=stored,
                )

            if reference.record_revision != command.expected_record_revision:
                return self._decision(RunEntryDecisionCode.PLAYER_CHARACTER_STALE)
            if (
                lifecycle is not PlayerCharacterLifecycle.ACTIVE
                or not reference.record_revision.has_successor
            ):
                return self._decision(
                    RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE
                )
            occupied = await uow.runs.get_active_for_player_character_for_update(
                command.player_character_id
            )
            if occupied is not None:
                validate_canonical_run(occupied)
                return self._decision(
                    RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE
                )
            try:
                definition = self.session_service.resolve_run_entry_definition(
                    command.scenario_id
                )
            except InvalidScenarioDefinitionError:
                return self._decision(
                    RunEntryDecisionCode.INVALID_SCENARIO_DEFINITION
                )
            if definition.public_client is None:
                raise RunEntryIntegrityError(
                    "resolved Run-entry scenario lost its public definition"
                )
            evidence = RunEntryCreationEvidence.model_validate(
                {
                    "controller_operation": {
                        "controller_binding": {"value": controller.value},
                        "public_operation_key": command.public_operation_key.value,
                    },
                    "player_character": {
                        "player_character_id": {
                            "value": command.player_character_id.value
                        },
                        "pre_entry_record_revision": {
                            "value": command.expected_record_revision.value
                        },
                    },
                    "scenario": {
                        "scenario_id": definition.scenario_id,
                        "content_version": definition.content_version,
                        "default_character_definition_id": (
                            definition.public_client.default_character_definition_id
                        ),
                    },
                    "trusted_run_source": {
                        "source_reference": {"value": self.source_reference.value}
                    },
                },
                strict=True,
            )
            if self._derive_ids_from_evidence(evidence) != ids:
                raise RunEntryIntegrityError(
                    "Run-entry evidence changed deterministic identities"
                )
            if (
                await uow.sessions.get_by_creation_request(
                    principal.player_id, ids.session_creation_request_id
                )
                is not None
            ):
                return self._decision(RunEntryDecisionCode.RUN_ENTRY_CONFLICT)

            occurred_at = self._occurred_at()
            run_id = revalidate_run_model(self.run_id_issuer.issue(), RunId)
            line_id = revalidate_run_model(
                self.continuous_story_line_id_issuer.issue(),
                ContinuousStoryLineId,
            )
            prepared_session = self.session_service.prepare_run_entry_initialization(
                principal,
                creation_request_id=ids.session_creation_request_id,
                definition=definition,
                character_definition_id=(
                    definition.public_client.default_character_definition_id
                ),
                created_at=occurred_at,
            )
            initial, creation_receipt = self._build_creation(
                run_id,
                line_id,
                ids=ids,
                evidence=evidence,
                occurred_at=occurred_at,
            )
            bound, binding_receipt = self._build_binding(
                initial,
                reference=reference,
                ids=ids,
                occurred_at=occurred_at,
            )
            active, attachment_receipt = self._build_activation(
                bound,
                session_id=prepared_session.session.session_id,
                ids=ids,
                occurred_at=occurred_at,
            )
            result = self._result(
                active,
                evidence=evidence,
                lifecycle=PlayerCharacterLifecycle.ACTIVE,
            )

            try:
                await stage_run_entry_creation(
                    uow,
                    initial,
                    creation_receipt,
                    evidence,
                    created_at=occurred_at,
                )
            except RunReceiptUniquenessConflictError:
                return self._decision(RunEntryDecisionCode.IDEMPOTENCY_CONFLICT)
            except RunWriteConflictError:
                return self._decision(RunEntryDecisionCode.RUN_ENTRY_CONFLICT)
            try:
                if not await stage_run_entry_binding(
                    uow, bound, binding_receipt, created_at=occurred_at
                ):
                    return self._decision(RunEntryDecisionCode.RUN_ENTRY_CONFLICT)
                await self.session_service.stage_run_entry_initialization(
                    uow, prepared_session
                )
                if not await stage_run_entry_activation(
                    uow, active, attachment_receipt, created_at=occurred_at
                ):
                    return self._decision(RunEntryDecisionCode.RUN_ENTRY_CONFLICT)
            except (
                ConcurrentSessionCreateError,
                RunPlayerCharacterBindingUniquenessConflictError,
                RunReceiptUniquenessConflictError,
                RunSessionParticipationUniquenessConflictError,
                RunWriteConflictError,
            ):
                return self._decision(RunEntryDecisionCode.RUN_ENTRY_CONFLICT)
            await uow.commit()
            return result

    async def _replay(
        self,
        uow: UnitOfWork,
        *,
        principal: RequestPrincipal,
        command: RunEntryCommand,
        controller: ControllerBindingRef,
        stored: StoredRunCreationEvidence,
    ) -> RunEntryResult | RunEntryDecision:
        if type(stored) is not StoredRunCreationEvidence:
            raise RunEntryIntegrityError("Run creation evidence carrier is invalid")
        receipt = revalidate_run_model(stored.receipt, StoredRunSuccessReceipt)
        evidence = stored.evidence
        if type(evidence) is CreateRunCommand:
            revalidate_run_model(evidence, CreateRunCommand)
            return self._decision(RunEntryDecisionCode.IDEMPOTENCY_CONFLICT)
        if type(evidence) is not RunEntryCreationEvidence:
            raise RunEntryIntegrityError("Run creation evidence family is invalid")
        evidence = revalidate_run_model(evidence, RunEntryCreationEvidence)
        if evidence.controller_operation.controller_binding != controller:
            return self._decision(RunEntryDecisionCode.AUTHORIZATION_FAILED)
        ids = self._derive_ids_from_evidence(evidence)
        if (
            stored.evidence_canonical != run_entry_evidence_bytes(evidence)
            or receipt.key.operation_id != ids.creation
        ):
            raise RunEntryIntegrityError(
                "Run creation evidence does not bind its deterministic key"
            )
        if (
            evidence.controller_operation.public_operation_key
            != command.public_operation_key.value
            or evidence.player_character.player_character_id
            != command.player_character_id
            or evidence.player_character.pre_entry_record_revision
            != command.expected_record_revision
            or evidence.scenario.scenario_id != command.scenario_id
        ):
            return self._decision(RunEntryDecisionCode.IDEMPOTENCY_CONFLICT)
        run = await uow.runs.get_for_update(receipt.result.run_id)
        if run is None:
            raise RunEntryIntegrityError("stored P8 Run family is missing")
        run = validate_canonical_run(run)
        participation, transaction_time = self._validate_replay_run_family(
            run, receipt=receipt, evidence=evidence, ids=ids
        )
        persisted_session = await uow.sessions.get_owned_for_update(
            participation.session_id, principal.player_id
        )
        if persisted_session is None:
            raise RunEntryIntegrityError("stored P8 Session family is missing")
        initialization_event = await uow.sessions.get_initialization_event(
            participation.session_id
        )
        if initialization_event is None:
            raise RunEntryIntegrityError(
                "stored P8 initialization event is missing"
            )
        snapshot = await uow.sessions.get_latest_snapshot_for_update(
            participation.session_id
        )
        if snapshot is None:
            raise SnapshotNotFoundError(participation.session_id)
        binding = run.player_character_binding
        if binding is None:
            raise RunEntryIntegrityError("stored P8 binding is missing")
        self.session_service.validate_run_entry_replay_initialization(
            persisted_session,
            snapshot,
            initialization_event,
            evidence,
            ids.session_creation_request_id,
            participation=participation,
            applicable_character_reference=(
                binding.applicable_character_reference
            ),
            transaction_time=transaction_time,
        )
        return self._result(
            run,
            evidence=evidence,
            lifecycle=PlayerCharacterLifecycle.ACTIVE,
        )

    def _validate_replay_run_family(
        self,
        run: CanonicalRun,
        *,
        receipt: StoredRunSuccessReceipt,
        evidence: RunEntryCreationEvidence,
        ids: _RunEntryInternalIds,
    ):
        binding = run.player_character_binding
        if (
            run.lifecycle_status is not RunLifecycleStatus.ACTIVE
            or run.state_version.value != 3
            or run.current_mutation_provenance.mutation_kind
            is not RunMutationKind.ATTACH_SESSION
            or len(run.trusted_participation_references) != 1
            or binding is None
        ):
            raise RunEntryIntegrityError("stored P8 Run shape is not revision three")
        participation = run.trusted_participation_references[0]
        transaction_time = run.creation_provenance.occurred_at
        if (
            receipt.result.run_id != run.run_id
            or receipt.result.continuous_story_line_id
            != run.continuous_story_line_id
            or receipt.result.resulting_state_version.value != 1
            or receipt.result.lifecycle_status
            is not RunLifecycleStatus.PRE_FIRST_TURN
            or run.creation_provenance.operation_id != ids.creation
            or binding.binding_operation_id != ids.binding
            or run.current_mutation_provenance.operation_id != ids.attachment
            or participation.operation_id != ids.attachment
            or participation.joined_state_version.value != 3
            or participation.run_id != run.run_id
            or participation.continuous_story_line_id
            != run.continuous_story_line_id
            or evidence.player_character.player_character_id
            != binding.applicable_character_reference.player_character_id
            or evidence.player_character.pre_entry_record_revision
            != binding.applicable_character_reference.record_revision
            or evidence.trusted_run_source.source_reference
            != self.source_reference
            or run.creation_provenance.source_reference != self.source_reference
            or binding.binding_authority_source_ref != self.source_reference
            or run.current_mutation_provenance.source_reference
            != self.source_reference
            or participation.source_reference != self.source_reference
            or binding.bound_at != transaction_time
            or run.current_mutation_provenance.occurred_at != transaction_time
        ):
            raise RunEntryIntegrityError(
                "stored P8 Run family is not cross-bound to its evidence"
            )
        return participation, transaction_time

    def _build_creation(
        self,
        run_id: RunId,
        line_id: ContinuousStoryLineId,
        *,
        ids: _RunEntryInternalIds,
        evidence: RunEntryCreationEvidence,
        occurred_at: datetime,
    ) -> tuple[CanonicalRun, StoredRunSuccessReceipt]:
        run = construct_created_run(
            CreateRunCommand(source_reference=self.source_reference),
            run_id=run_id,
            continuous_story_line_id=line_id,
            operation_id=ids.creation,
            occurred_at=occurred_at,
        )
        _, fingerprint = run_entry_creation_fingerprint(evidence)
        receipt = StoredRunSuccessReceipt(
            key=RunReceiptKey(
                operation_namespace=RunOperationNamespace.CREATE_V1,
                operation_id=ids.creation,
            ),
            fingerprint=fingerprint,
            command_kind=RunMutationKind.CREATE,
            result=creation_result(run),
        )
        return run, receipt

    def _build_binding(
        self,
        initial: CanonicalRun,
        *,
        reference: object,
        ids: _RunEntryInternalIds,
        occurred_at: datetime,
    ) -> tuple[CanonicalRun, StoredRunSuccessReceipt]:
        reference = validate_applicable_character_reference(reference)
        command = BindPlayerCharacterCommand(
            run_id=initial.run_id,
            continuous_story_line_id=initial.continuous_story_line_id,
            target_player_character_id=reference.player_character_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=self.source_reference,
        )
        run = bind_player_character_to_run(
            initial,
            command,
            applicable_character_reference=reference,
            operation_id=ids.binding,
            occurred_at=occurred_at,
        )
        _, fingerprint = bind_player_character_fingerprint(
            command, operation_id=ids.binding
        )
        receipt = StoredRunSuccessReceipt(
            key=RunReceiptKey(
                run_id=run.run_id,
                operation_namespace=(
                    RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
                ),
                operation_id=ids.binding,
            ),
            fingerprint=fingerprint,
            command_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
            result=bind_player_character_result(run),
        )
        return run, receipt

    def _build_activation(
        self,
        bound: CanonicalRun,
        *,
        session_id: str,
        ids: _RunEntryInternalIds,
        occurred_at: datetime,
    ) -> tuple[CanonicalRun, StoredRunSuccessReceipt]:
        command = AttachSessionCommand(
            run_id=bound.run_id,
            continuous_story_line_id=bound.continuous_story_line_id,
            session_id=session_id,
            expected_state_version=RunStateVersion(value=2),
            source_reference=self.source_reference,
        )
        run = activate_first_session_for_run(
            bound,
            command,
            operation_id=ids.attachment,
            occurred_at=occurred_at,
        )
        _, fingerprint = attach_session_fingerprint(
            command, operation_id=ids.attachment
        )
        receipt = StoredRunSuccessReceipt(
            key=RunReceiptKey(
                run_id=run.run_id,
                operation_namespace=RunOperationNamespace.ATTACH_SESSION_V1,
                operation_id=ids.attachment,
            ),
            fingerprint=fingerprint,
            command_kind=RunMutationKind.ATTACH_SESSION,
            result=attach_session_result(run),
        )
        return run, receipt

    @staticmethod
    def _result(
        run: CanonicalRun,
        *,
        evidence: RunEntryCreationEvidence,
        lifecycle: PlayerCharacterLifecycle,
    ) -> RunEntryResult:
        run = validate_canonical_run(run)
        binding = run.player_character_binding
        if binding is None or len(run.trusted_participation_references) != 1:
            raise RunEntryIntegrityError("Run entry result evidence is incomplete")
        reference = binding.applicable_character_reference
        return RunEntryResult(
            run_id=run.run_id,
            session_id=run.trusted_participation_references[0].session_id,
            scenario_id=evidence.scenario.scenario_id,
            player_character=PlayerCharacterSelfProjection(
                player_character_id=reference.player_character_id,
                contract_version=reference.contract_version,
                record_revision=reference.record_revision,
                lifecycle=lifecycle,
            ),
        )

    @staticmethod
    def _principal(principal: RequestPrincipal) -> RequestPrincipal:
        if (
            type(principal) is not RequestPrincipal
            or set(principal.__dict__) != set(RequestPrincipal.model_fields)
            or getattr(principal, "__pydantic_extra__", None)
            or getattr(principal, "__pydantic_private__", None)
        ):
            raise TypeError("expected canonical RequestPrincipal")
        validated = RequestPrincipal.model_validate(dict(principal.__dict__))
        if validated != principal:
            raise ValueError("RequestPrincipal is not already canonical")
        return principal

    @staticmethod
    def _derive_ids(
        controller: ControllerBindingRef,
        public_operation_key: RunEntryPublicOperationKey,
    ) -> _RunEntryInternalIds:
        def derive(purpose: str) -> str:
            return derive_run_entry_internal_id(
                purpose=purpose,
                controller_binding=controller,
                public_operation_key=public_operation_key,
            )

        return _RunEntryInternalIds(
            creation=RunOperationId(value=derive("run.create/v1")),
            binding=RunOperationId(
                value=derive("run.bind-player-character/v1")
            ),
            attachment=RunOperationId(value=derive("run.attach-session/v1")),
            session_creation_request_id=derive("session.create/v1"),
        )

    @classmethod
    def _derive_ids_from_evidence(
        cls, evidence: RunEntryCreationEvidence
    ) -> _RunEntryInternalIds:
        return cls._derive_ids(
            evidence.controller_operation.controller_binding,
            RunEntryPublicOperationKey(
                value=evidence.controller_operation.public_operation_key
            ),
        )

    def _occurred_at(self) -> datetime:
        value = self.clock()
        if (
            type(value) is not datetime
            or value.tzinfo is None
            or value.utcoffset() != timedelta(0)
        ):
            raise ValueError("Run clock must return exact UTC")
        return value

    @staticmethod
    def _decision(code: RunEntryDecisionCode) -> RunEntryDecision:
        return RunEntryDecision(code=code)
