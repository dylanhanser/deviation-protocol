from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from deviation_protocol.domain.player_character import (
    CanonicalPlayerCharacter,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
)


class PlayerCharacterSelfProjection(BaseModel):
    """Detached, allowlisted current state for an authorized controller."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    player_character_id: PlayerCharacterId
    contract_version: PlayerCharacterContractVersion
    record_revision: PlayerCharacterRevision
    lifecycle: PlayerCharacterLifecycle

    @classmethod
    def from_validated_record(
        cls,
        record: CanonicalPlayerCharacter,
    ) -> PlayerCharacterSelfProjection:
        return cls(
            player_character_id=PlayerCharacterId(
                value=record.player_character_id.value
            ),
            contract_version=record.contract_version,
            record_revision=PlayerCharacterRevision(
                value=record.record_revision.value
            ),
            lifecycle=record.lifecycle,
        )


class EligiblePlayerCharacterCollection(BaseModel):
    """Bounded detached discovery result for prospective Run entry."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    eligible_player_characters: Annotated[
        tuple[PlayerCharacterSelfProjection, ...], Field(max_length=32)
    ]
    truncated: bool
