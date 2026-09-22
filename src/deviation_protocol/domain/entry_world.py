"""Versioned authored authority for internal entry-world selection."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

from deviation_protocol.domain.run import (
    _validate_actual_pydantic_state, revalidate_run_model,
)


class EntryWorldValidationError(ValueError):
    """Malformed world reference or definition."""


class EntryWorldLookupError(ValueError):
    """No authored entry exists for the exact reference."""


class EntryWorldCatalogueIntegrityError(ValueError):
    """The server-owned catalogue is malformed."""


class _WorldModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    @model_serializer(mode="wrap")
    def _serialize_original(self, handler):
        revalidate_run_model(self, type(self))
        return handler(self)

    @model_validator(mode="before")
    @classmethod
    def _original_state(cls, value):
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise EntryWorldValidationError("unexpected world carrier")
            _validate_actual_pydantic_state(value, path=cls.__name__, visited=set())
        elif type(value) is dict:
            for nested in value.values():
                if isinstance(nested, BaseModel):
                    _validate_actual_pydantic_state(nested, path=cls.__name__, visited=set())
        return value


class EntryWorldId(_WorldModel):
    value: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class EntryWorldVersion(_WorldModel):
    value: int = Field(ge=1, le=9223372036854775807)


class EntryWorldRefV1(_WorldModel):
    entry_world_id: EntryWorldId
    entry_world_version: EntryWorldVersion


class AuthoredEntryWorldV1(_WorldModel):
    entry_world_id: EntryWorldId
    entry_world_version: EntryWorldVersion
    scenario_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    scenario_content_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    default_character_definition_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


AUTHORED_ENTRY_WORLDS_V1 = (
    AuthoredEntryWorldV1(
        entry_world_id=EntryWorldId(value="world.death_certificate"),
        entry_world_version=EntryWorldVersion(value=1),
        scenario_id="death_certificate",
        scenario_content_version="death-certificate-1.1.0",
        default_character_definition_id="character.death_certificate.investigator",
    ),
    AuthoredEntryWorldV1(
        entry_world_id=EntryWorldId(value="world.fog_station"),
        entry_world_version=EntryWorldVersion(value=1),
        scenario_id="fog_station",
        scenario_content_version="fog-station-1.0.0",
        default_character_definition_id="character.fog_station.traveler",
    ),
)


def lookup_entry_world(reference: EntryWorldRefV1) -> AuthoredEntryWorldV1:
    try:
        revalidate_run_model(reference, EntryWorldRefV1)
    except (TypeError, ValueError, AttributeError) as error:
        raise EntryWorldValidationError("invalid entry-world reference") from error
    try:
        if type(AUTHORED_ENTRY_WORLDS_V1) is not tuple or not AUTHORED_ENTRY_WORLDS_V1:
            raise ValueError("invalid catalogue tuple")
        keys = set()
        for entry in AUTHORED_ENTRY_WORLDS_V1:
            revalidate_run_model(entry, AuthoredEntryWorldV1)
            key = (entry.entry_world_id.value, entry.entry_world_version.value)
            if key in keys:
                raise ValueError("duplicate authored reference")
            keys.add(key)
    except (TypeError, ValueError, AttributeError) as error:
        raise EntryWorldCatalogueIntegrityError("invalid authored catalogue") from error
    for entry in AUTHORED_ENTRY_WORLDS_V1:
        if (entry.entry_world_id == reference.entry_world_id
                and entry.entry_world_version == reference.entry_world_version):
            return entry
    raise EntryWorldLookupError("unknown entry-world reference") from None
