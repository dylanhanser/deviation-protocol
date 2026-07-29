from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationReceiptKey,
    CreationSuccessResult,
    build_creation_success_receipt,
    creation_fingerprint,
    evaluate_creation_receipt_protocol,
    recover_creation_unique_race_winner,
)
from deviation_protocol.application.ports import (
    ControllerBindingResolver,
    ControllerBindingUniquenessConflictError,
    PlayerCharacterIdIssuer,
    UnitOfWorkFactory,
)
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    ControllerBindingRef,
    PlayerCharacterId,
    PlayerCharacterOperationId,
    revalidate_player_character_model,
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)


@dataclass(slots=True)
class PlayerCharacterService:
    uow_factory: UnitOfWorkFactory
    controller_binding_resolver: ControllerBindingResolver
    player_character_id_issuer: PlayerCharacterIdIssuer
    create_policy: CreatePlayerCharacterPolicy
    source_reference: AuthoritySourceRef
    clock: Callable[[], datetime]

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
