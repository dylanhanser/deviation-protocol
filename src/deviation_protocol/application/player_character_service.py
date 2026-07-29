from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, cast

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_creation_receipt_protocol,
    evaluate_mutation_policy,
    evaluate_mutation_receipt_protocol,
    mutation_fingerprint,
    recover_creation_unique_race_winner,
    recover_mutation_unique_race_winner,
)
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.application.ports import (
    ControllerBindingResolver,
    ControllerBindingUniquenessConflictError,
    MutationReceiptUniquenessConflictError,
    PlayerCharacterIdIssuer,
    UnitOfWork,
    UnitOfWorkFactory,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    ControllerBindingRef,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    revalidate_player_character_model,
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerCharacterPolicyCode,
    PlayerCharacterPolicyDecision,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    validate_canonical_run,
)


class PlayerCharacterBindingEvidenceIntegrityError(ValueError):
    """Canonical binding evidence is contradictory or incomplete."""


@dataclass(frozen=True, slots=True)
class PlayerCharacterBindingEligibilityEvidence:
    """The narrow owned character evidence exposed to internal Run binding."""

    applicable_character_reference: ApplicableCharacterReference
    lifecycle: PlayerCharacterLifecycle


class _ActiveBindingEvidenceRepository(Protocol):
    async def get_active_for_player_character_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalRun | None: ...


@dataclass(slots=True)
class PlayerCharacterService:
    uow_factory: UnitOfWorkFactory
    controller_binding_resolver: ControllerBindingResolver
    player_character_id_issuer: PlayerCharacterIdIssuer
    create_policy: CreatePlayerCharacterPolicy
    source_reference: AuthoritySourceRef
    clock: Callable[[], datetime]
    binding_integrity_guard_enabled: bool = False

    async def create(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: PlayerCharacterOperationId,
        command: CharacterCreationCommand,
    ) -> CreationSuccessResult | CharacterOperationProtocolDecision:
        controller_binding = await self.controller_binding_resolver.resolve(
            principal
        )
        try:
            controller_binding = revalidate_player_character_model(
                controller_binding,
                ControllerBindingRef,
            )
        except (AttributeError, TypeError, ValueError):
            return self._authorization_failed()

        binding_add_exception: (
            ControllerBindingUniquenessConflictError | None
        ) = None
        binding_recovery_authorized = False
        try:
            async with self.uow_factory() as uow:
                locked_binding = await uow.controller_bindings.lock(
                    controller_binding
                )
                created_at: datetime | None = None
                if locked_binding is None:
                    created_at = self._created_at()
                    try:
                        await uow.controller_bindings.add(
                            controller_binding,
                            created_at=created_at,
                        )
                    except ControllerBindingUniquenessConflictError as exc:
                        binding_add_exception = exc
                        raise
                elif locked_binding != controller_binding:
                    return self._authorization_failed()

                operation_id = revalidate_player_character_model(
                    operation_id,
                    PlayerCharacterOperationId,
                )
                _, fingerprint = creation_fingerprint(command)
                receipt_key = CreationReceiptKey(
                    controller_binding=controller_binding,
                    operation_namespace=CharacterOperationNamespace.CREATE_V1,
                    operation_id=operation_id,
                )
                stored_receipt = await uow.creation_receipts.get(receipt_key)
                decision = evaluate_creation_receipt_protocol(
                    authentication_succeeded=True,
                    trusted_controller_binding=controller_binding,
                    operation_id=operation_id,
                    command=command,
                    lookup_receipt=lambda key: (
                        stored_receipt if key == receipt_key else None
                    ),
                )
                if (
                    decision.code
                    is CharacterOperationProtocolCode.EXACT_REPLAY
                ):
                    result = decision.stored_success_result
                    if not isinstance(result, CreationSuccessResult):
                        raise ValueError(
                            "creation replay returned a non-creation result"
                        )
                    return result
                if (
                    decision.code
                    is not CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
                ):
                    return decision

                player_character_id = (
                    self.player_character_id_issuer.issue()
                )
                player_character_id = revalidate_player_character_model(
                    player_character_id,
                    PlayerCharacterId,
                )
                if created_at is None:
                    created_at = self._created_at()
                await uow.player_characters.add_allocation(
                    player_character_id,
                    created_at=created_at,
                )
                record = self.create_policy.create(
                    player_character_id=player_character_id,
                    controller_binding=controller_binding,
                    character_core=command.character_core,
                    narration_preferences=command.narration_preferences,
                    source_reference=self.source_reference,
                )
                record = validate_canonical_player_character(record)
                result = CreationSuccessResult(
                    result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
                    player_character_id=record.player_character_id,
                    contract_version=record.contract_version,
                    resulting_revision=record.record_revision,
                    resulting_lifecycle=record.lifecycle,
                )
                receipt = build_creation_success_receipt(
                    key=receipt_key,
                    fingerprint=fingerprint,
                    result=result,
                )
                await uow.player_characters.add_initial(
                    record,
                    created_at=created_at,
                )
                await uow.creation_receipts.add(
                    receipt,
                    created_at=created_at,
                )
                await uow.commit()
                return result
        except ControllerBindingUniquenessConflictError as escaped_exception:
            if escaped_exception is not binding_add_exception:
                raise
            binding_recovery_authorized = True

        if not binding_recovery_authorized:
            if binding_add_exception is not None:
                raise binding_add_exception
            raise RuntimeError(
                "initial UnitOfWork suppressed an unrecorded exception"
            )

        return await self._recover_binding_winner(
            principal,
            original_controller_binding=controller_binding,
            operation_id=operation_id,
            command=command,
        )

    async def mutate(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: PlayerCharacterOperationId,
        command: CharacterMutationCommand,
    ) -> (
        MutationSuccessResult
        | PlayerCharacterPolicyDecision
        | CharacterOperationProtocolDecision
    ):
        controller_binding = await self.controller_binding_resolver.resolve(
            principal
        )
        try:
            controller_binding = revalidate_player_character_model(
                controller_binding,
                ControllerBindingRef,
            )
        except (AttributeError, TypeError, ValueError):
            return CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
            )

        receipt_add_exception: (
            MutationReceiptUniquenessConflictError | None
        ) = None
        receipt_recovery_authorized = False
        try:
            async with self.uow_factory() as uow:
                current = await uow.player_characters.get_for_update(
                    command.target_player_character_id
                )
                if current is None:
                    return CharacterOperationProtocolDecision(
                        operation_namespace=(
                            CharacterOperationNamespace.MUTATE_V1
                        ),
                        code=(
                            CharacterOperationProtocolCode.AUTHORIZATION_FAILED
                        ),
                    )
                current = validate_canonical_player_character(current)
                if current.controller_binding != controller_binding:
                    return CharacterOperationProtocolDecision(
                        operation_namespace=(
                            CharacterOperationNamespace.MUTATE_V1
                        ),
                        code=(
                            CharacterOperationProtocolCode.AUTHORIZATION_FAILED
                        ),
                    )

                command = revalidate_player_character_model(
                    command,
                    CharacterMutationCommand,
                )
                operation_id = revalidate_player_character_model(
                    operation_id,
                    PlayerCharacterOperationId,
                )
                if not command.expected_revision.has_successor:
                    return CharacterOperationProtocolDecision(
                        operation_namespace=(
                            CharacterOperationNamespace.MUTATE_V1
                        ),
                        code=(
                            CharacterOperationProtocolCode.REVISION_EXHAUSTED
                        ),
                    )

                receipt_key = MutationReceiptKey(
                    player_character_id=current.player_character_id,
                    operation_namespace=(
                        CharacterOperationNamespace.MUTATE_V1
                    ),
                    operation_id=operation_id,
                )
                stored_receipt = await uow.mutation_receipts.get(receipt_key)
                protocol_decision = evaluate_mutation_receipt_protocol(
                    authentication_succeeded=True,
                    trusted_controller_binding=controller_binding,
                    current_record=current,
                    operation_id=operation_id,
                    command=command,
                    lookup_receipt=lambda key: (
                        stored_receipt if key == receipt_key else None
                    ),
                )
                if (
                    protocol_decision.code
                    is CharacterOperationProtocolCode.EXACT_REPLAY
                ):
                    replay_result = (
                        protocol_decision.stored_success_result
                    )
                    if not isinstance(
                        replay_result,
                        MutationSuccessResult,
                    ):
                        raise ValueError(
                            "mutation replay returned a non-mutation result"
                        )
                    return replay_result
                if (
                    protocol_decision.code
                    is not (
                        CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
                    )
                ):
                    return protocol_decision

                if (
                    self.binding_integrity_guard_enabled
                    and command.command_kind
                    in {
                        PlayerCharacterMutationKind.RETIRE,
                        PlayerCharacterMutationKind.FINAL_DEATH,
                    }
                ):
                    active_binding = (
                        await self.get_active_binding_evidence_for_update(
                            uow,
                            locked_player_character=current,
                        )
                    )
                    if active_binding is not None:
                        if (
                            current.lifecycle
                            is not PlayerCharacterLifecycle.ACTIVE
                        ):
                            raise PlayerCharacterBindingEvidenceIntegrityError(
                                "an active Run binding references an inactive "
                                "current player character"
                            )
                        return PlayerCharacterPolicyDecision(
                            code=(
                                PlayerCharacterPolicyCode
                                .ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
                            )
                        )

                policy_decision = evaluate_mutation_policy(
                    current,
                    command=command,
                    operation_id=operation_id,
                )
                if not policy_decision.accepted:
                    return policy_decision
                successor = policy_decision.resulting_record
                if successor is None:
                    raise ValueError(
                        "accepted mutation policy returned no successor"
                    )
                successor = validate_canonical_player_character(successor)
                if (
                    successor.player_character_id
                    != current.player_character_id
                    or successor.controller_binding
                    != current.controller_binding
                    or successor.contract_version != current.contract_version
                    or successor.record_revision
                    != current.record_revision.successor()
                    or successor.authority_provenance.prior_revision
                    != command.expected_revision
                    or successor.authority_provenance.mutation_kind
                    is not command.command_kind
                ):
                    raise ValueError(
                        "mutation successor is inconsistent with the command"
                    )

                _, fingerprint = mutation_fingerprint(
                    command,
                    operation_id=operation_id,
                )
                command_result = {
                    PlayerCharacterMutationKind.RETIRE: (
                        MutationCommandResult.RETIRED
                    ),
                    PlayerCharacterMutationKind.FINAL_DEATH: (
                        MutationCommandResult.DECEASED
                    ),
                }.get(command.command_kind)
                if command_result is None:
                    raise ValueError(
                        "unavailable mutation policy returned acceptance"
                    )
                result = MutationSuccessResult(
                    result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
                    player_character_id=successor.player_character_id,
                    contract_version=successor.contract_version,
                    command_kind=command.command_kind,
                    command_result=command_result,
                    resulting_revision=successor.record_revision,
                    resulting_lifecycle=successor.lifecycle,
                )
                receipt = build_mutation_success_receipt(
                    key=receipt_key,
                    fingerprint=fingerprint,
                    result=result,
                )
                created_at = self._created_at()
                await uow.player_characters.append_revision(
                    successor,
                    created_at=created_at,
                )
                won_current = (
                    await uow.player_characters.compare_and_swap_current(
                        successor,
                        expected_revision=current.record_revision.value,
                        created_at=created_at,
                    )
                )
                if not won_current:
                    return CharacterOperationProtocolDecision(
                        operation_namespace=(
                            CharacterOperationNamespace.MUTATE_V1
                        ),
                        code=CharacterOperationProtocolCode.STALE_REVISION,
                    )
                try:
                    await uow.mutation_receipts.add(
                        receipt,
                        created_at=created_at,
                    )
                except MutationReceiptUniquenessConflictError as exc:
                    receipt_add_exception = exc
                    raise
                await uow.commit()
                return result
        except MutationReceiptUniquenessConflictError as escaped_exception:
            if escaped_exception is not receipt_add_exception:
                raise
            receipt_recovery_authorized = True

        if not receipt_recovery_authorized:
            if receipt_add_exception is not None:
                raise receipt_add_exception
            raise RuntimeError(
                "initial UnitOfWork suppressed an unrecorded exception"
            )

        return await self._recover_mutation_winner(
            principal,
            original_controller_binding=controller_binding,
            operation_id=operation_id,
            command=command,
        )

    async def get_owned(
        self,
        principal: RequestPrincipal,
        *,
        player_character_id: PlayerCharacterId,
    ) -> PlayerCharacterSelfProjection | None:
        controller_binding = await self.controller_binding_resolver.resolve(
            principal
        )
        try:
            controller_binding = revalidate_player_character_model(
                controller_binding,
                ControllerBindingRef,
            )
        except (AttributeError, TypeError, ValueError):
            return None

        player_character_id = revalidate_player_character_model(
            player_character_id,
            PlayerCharacterId,
        )
        async with self.uow_factory() as uow:
            current = await uow.player_characters.get(
                player_character_id
            )
            if current is None:
                return None
            current = validate_canonical_player_character(current)
            if current.controller_binding != controller_binding:
                return None
            if current.player_character_id != player_character_id:
                raise ValueError(
                    "player-character read returned a mismatched identity"
                )
            return PlayerCharacterSelfProjection.from_validated_record(
                current
            )

    async def lock_owned_for_binding(
        self,
        uow: UnitOfWork,
        *,
        trusted_controller_binding: ControllerBindingRef,
        target_player_character_id: PlayerCharacterId,
    ) -> PlayerCharacterBindingEligibilityEvidence | None:
        """Lock and return only the owned character evidence needed by Run."""

        trusted_controller_binding = revalidate_player_character_model(
            trusted_controller_binding,
            ControllerBindingRef,
        )
        target_player_character_id = revalidate_player_character_model(
            target_player_character_id,
            PlayerCharacterId,
        )
        current = await uow.player_characters.get_for_update(
            target_player_character_id
        )
        if current is None:
            return None
        try:
            current = validate_canonical_player_character(current)
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterBindingEvidenceIntegrityError(
                "locked player-character evidence is malformed or corrupt"
            ) from exc
        if current.controller_binding != trusted_controller_binding:
            return None
        if current.player_character_id != target_player_character_id:
            raise PlayerCharacterBindingEvidenceIntegrityError(
                "locked player-character evidence has a mismatched identity"
            )
        return PlayerCharacterBindingEligibilityEvidence(
            applicable_character_reference=ApplicableCharacterReference(
                player_character_id=current.player_character_id,
                contract_version=current.contract_version,
                record_revision=current.record_revision,
            ),
            lifecycle=current.lifecycle,
        )

    async def get_active_binding_evidence_for_update(
        self,
        uow: UnitOfWork,
        *,
        locked_player_character: CanonicalPlayerCharacter,
    ) -> CanonicalRun | None:
        """Load and lock canonical active-line evidence after the character lock."""

        current = validate_canonical_player_character(
            locked_player_character
        )
        repository = cast(_ActiveBindingEvidenceRepository, uow.runs)
        run = await repository.get_active_for_player_character_for_update(
            current.player_character_id
        )
        if run is None:
            return None
        try:
            run = validate_canonical_run(run)
        except (AttributeError, TypeError, ValueError) as exc:
            raise PlayerCharacterBindingEvidenceIntegrityError(
                "active-line lookup returned malformed or corrupt binding "
                "evidence"
            ) from exc
        binding = run.player_character_binding
        if (
            not run.lifecycle_status.is_active_line
            or binding is None
            or binding.binding_state != "active"
            or binding.inactivated_at is not None
            or binding.run_id != run.run_id
            or binding.continuous_story_line_id
            != run.continuous_story_line_id
            or binding.applicable_character_reference.player_character_id
            != current.player_character_id
        ):
            raise PlayerCharacterBindingEvidenceIntegrityError(
                "active-line lookup returned contradictory binding evidence"
            )
        return run

    async def _recover_binding_winner(
        self,
        principal: RequestPrincipal,
        *,
        original_controller_binding: ControllerBindingRef,
        operation_id: PlayerCharacterOperationId,
        command: CharacterCreationCommand,
    ) -> CreationSuccessResult | CharacterOperationProtocolDecision:
        async with self.uow_factory() as recovery_uow:
            recovered_binding = (
                await self.controller_binding_resolver.resolve(principal)
            )
            try:
                recovered_binding = revalidate_player_character_model(
                    recovered_binding,
                    ControllerBindingRef,
                )
            except (AttributeError, TypeError, ValueError):
                return self._authorization_failed()
            if recovered_binding != original_controller_binding:
                return self._authorization_failed()

            locked_binding = await recovery_uow.controller_bindings.lock(
                recovered_binding
            )
            if locked_binding != recovered_binding:
                return self._authorization_failed()

            operation_id = revalidate_player_character_model(
                operation_id,
                PlayerCharacterOperationId,
            )
            receipt_key = CreationReceiptKey(
                controller_binding=recovered_binding,
                operation_namespace=CharacterOperationNamespace.CREATE_V1,
                operation_id=operation_id,
            )
            stored_receipt = await recovery_uow.creation_receipts.get(
                receipt_key
            )
            decision = recover_creation_unique_race_winner(
                losing_transaction_rolled_back=True,
                authentication_succeeded=True,
                trusted_controller_binding=recovered_binding,
                operation_id=operation_id,
                command=command,
                reread_receipt_in_fresh_transaction=lambda key: (
                    stored_receipt if key == receipt_key else None
                ),
            )
            if decision.code is CharacterOperationProtocolCode.EXACT_REPLAY:
                result = decision.stored_success_result
                if not isinstance(result, CreationSuccessResult):
                    raise ValueError(
                        "creation recovery returned a non-creation result"
                    )
                return result
            return decision

    async def _recover_mutation_winner(
        self,
        principal: RequestPrincipal,
        *,
        original_controller_binding: ControllerBindingRef,
        operation_id: PlayerCharacterOperationId,
        command: CharacterMutationCommand,
    ) -> (
        MutationSuccessResult
        | CharacterOperationProtocolDecision
    ):
        async with self.uow_factory() as recovery_uow:
            recovered_binding = (
                await self.controller_binding_resolver.resolve(principal)
            )
            try:
                recovered_binding = revalidate_player_character_model(
                    recovered_binding,
                    ControllerBindingRef,
                )
            except (AttributeError, TypeError, ValueError):
                return CharacterOperationProtocolDecision(
                    operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                    code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
                )
            if recovered_binding != original_controller_binding:
                return CharacterOperationProtocolDecision(
                    operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                    code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
                )

            current = await recovery_uow.player_characters.get_for_update(
                command.target_player_character_id
            )
            if current is None:
                return CharacterOperationProtocolDecision(
                    operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                    code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
                )
            current = validate_canonical_player_character(current)
            if current.controller_binding != recovered_binding:
                return CharacterOperationProtocolDecision(
                    operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                    code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
                )

            operation_id = revalidate_player_character_model(
                operation_id,
                PlayerCharacterOperationId,
            )
            receipt_key = MutationReceiptKey(
                player_character_id=current.player_character_id,
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                operation_id=operation_id,
            )
            stored_receipt = await recovery_uow.mutation_receipts.get(
                receipt_key
            )
            decision = recover_mutation_unique_race_winner(
                losing_transaction_rolled_back=True,
                authentication_succeeded=True,
                trusted_controller_binding=recovered_binding,
                current_record=current,
                operation_id=operation_id,
                command=command,
                reread_receipt_in_fresh_transaction=lambda key: (
                    stored_receipt if key == receipt_key else None
                ),
            )
            if decision.code is CharacterOperationProtocolCode.EXACT_REPLAY:
                result = decision.stored_success_result
                if not isinstance(result, MutationSuccessResult):
                    raise ValueError(
                        "mutation recovery returned a non-mutation result"
                    )
                return result
            return decision

    @staticmethod
    def _authorization_failed() -> CharacterOperationProtocolDecision:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
        )

    def _created_at(self) -> datetime:
        value = self.clock()
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "player-character clock must return a timezone-aware datetime"
            )
        return value.astimezone(timezone.utc)
