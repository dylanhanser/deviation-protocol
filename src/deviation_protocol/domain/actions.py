from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionType(StrEnum):
    CHOOSE = "CHOOSE"
    TALK = "TALK"
    CUSTOM = "CUSTOM"
    INSPECT_STATUS = "INSPECT_STATUS"
    INSPECT_INVENTORY = "INSPECT_INVENTORY"
    INSPECT_QUESTS = "INSPECT_QUESTS"


class ActionSubmission(BaseModel):
    """One semi-structured player intent.

    Cross-field contracts deliberately remain policies so every accept/reject decision
    is represented in the gateway policy trace.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    session_id: str = Field(min_length=1, max_length=64)
    turn_id: str = Field(min_length=1, max_length=64)
    client_request_id: str = Field(min_length=1, max_length=64)
    action_type: ActionType
    target_ids: tuple[str, ...] = ()
    tool_ids: tuple[str, ...] = ()
    description: str | None = Field(default=None, max_length=150)
    dialogue: str | None = Field(default=None, max_length=200)
    choice_id: str | None = Field(default=None, max_length=64)

    @field_validator("target_ids", "tool_ids", mode="before")
    @classmethod
    def normalize_ids(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, (str, bytes)) or not isinstance(
            value, (list, tuple, set, frozenset)
        ):
            raise ValueError("entity and tool ids must be submitted as an array")
        if any(not isinstance(item, str) for item in value):
            raise ValueError("entity and tool ids must contain only strings")
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"\s+", " ", value).strip()

    def signature_payload(self) -> dict[str, Any]:
        """Canonical semantic payload; request id is intentionally excluded."""
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "action_type": self.action_type.value,
            "target_ids": sorted(self.target_ids),
            "tool_ids": sorted(self.tool_ids),
            "description": self._normalize_text(self.description),
            "dialogue": self._normalize_text(self.dialogue),
            "choice_id": self.choice_id,
        }

    def action_signature(self) -> str:
        encoded = json.dumps(
            self.signature_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ActionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    submission: ActionSubmission
    current_turn_id: str
    session_phase: str = "AWAITING_ACTION"
    visible_entity_ids: frozenset[str] = frozenset()
    interactable_entity_ids: frozenset[str] = frozenset()
    inventory_item_ids: frozenset[str] = frozenset()
    environment_tool_ids: frozenset[str] = frozenset()
    processed_client_request_ids: frozenset[str] = frozenset()
