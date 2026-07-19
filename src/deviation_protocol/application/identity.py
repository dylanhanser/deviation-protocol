from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class RequestPrincipal(BaseModel):
    """Trusted application identity supplied by an API authentication dependency."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    player_id: str = Field(strict=True, min_length=1, max_length=64)
    authentication_scheme: str = Field(strict=True, min_length=1, max_length=32)

    @field_validator("player_id", "authentication_scheme")
    @classmethod
    def validate_safe_identifier(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value)
        if not _SAFE_ID.fullmatch(normalized):
            raise ValueError("identity fields must be safe identifiers")
        return normalized
