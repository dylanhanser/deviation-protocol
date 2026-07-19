from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Any
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActionType(StrEnum):
    CHOOSE = "CHOOSE"
    TALK = "TALK"
    CUSTOM = "CUSTOM"
    EXPLORE = "EXPLORE"
    OBSERVE = "OBSERVE"
    MOVE = "MOVE"
    INSPECT_STATUS = "INSPECT_STATUS"
    INSPECT_INVENTORY = "INSPECT_INVENTORY"
    INSPECT_EQUIPMENT = "INSPECT_EQUIPMENT"
    INSPECT_SKILLS = "INSPECT_SKILLS"
    INSPECT_RESOURCES = "INSPECT_RESOURCES"
    INSPECT_CURRENCIES = "INSPECT_CURRENCIES"
    INSPECT_QUESTS = "INSPECT_QUESTS"
    EQUIP = "EQUIP"
    UNEQUIP = "UNEQUIP"
    USE_ITEM = "USE_ITEM"
    LEARN_SKILL = "LEARN_SKILL"
    UPGRADE_SKILL = "UPGRADE_SKILL"
    USE_SKILL = "USE_SKILL"


class ActionSubmission(BaseModel):
    """One semi-structured player intent.

    Cross-field contracts deliberately remain policies so every accept/reject decision
    is represented in the gateway policy trace.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    session_id: str = Field(min_length=1, max_length=64)
    turn_id: str = Field(min_length=1, max_length=64)
    client_request_id: str = Field(min_length=1, max_length=64)
    action_type: ActionType
    target_ids: tuple[str, ...] = ()
    tool_ids: tuple[str, ...] = ()
    description: str | None = Field(default=None, max_length=150)
    dialogue: str | None = Field(default=None, max_length=200)
    decision_id: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    )
    choice_id: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    )
    item_instance_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    )
    equipment_slot_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    )
    skill_definition_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    )

    @field_validator(
        "session_id",
        "turn_id",
        "client_request_id",
        "description",
        "dialogue",
        "decision_id",
        "choice_id",
        mode="before",
    )
    @classmethod
    def normalize_unicode(cls, value: Any) -> Any:
        return unicodedata.normalize("NFC", value) if isinstance(value, str) else value

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
        normalized = (
            unicodedata.normalize("NFC", item).strip()
            for item in value
        )
        return tuple(dict.fromkeys(item for item in normalized if item))

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()

    def signature_payload(self) -> dict[str, Any]:
        """Canonical semantic payload; request id is intentionally excluded."""
        payload = {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "action_type": self.action_type.value,
            "target_ids": sorted(self.target_ids),
            "tool_ids": sorted(self.tool_ids),
            "description": self._normalize_text(self.description),
            "dialogue": self._normalize_text(self.dialogue),
            "decision_id": self.decision_id,
            "choice_id": self.choice_id,
        }
        # Preserve Phase 1 signatures for legacy actions while including every new
        # structured identifier when it carries semantic meaning.
        if self.item_instance_id is not None:
            payload["item_instance_id"] = self.item_instance_id
        if self.equipment_slot_id is not None:
            payload["equipment_slot_id"] = self.equipment_slot_id
        if self.skill_definition_id is not None:
            payload["skill_definition_id"] = self.skill_definition_id
        return payload

    def action_signature(self) -> str:
        encoded = json.dumps(
            self.signature_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ActionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    submission: ActionSubmission
    current_turn_id: str
    session_phase: str = "AWAITING_ACTION"
    visible_entity_ids: frozenset[str] = frozenset()
    interactable_entity_ids: frozenset[str] = frozenset()
    inventory_item_ids: frozenset[str] = frozenset()
    environment_tool_ids: frozenset[str] = frozenset()
    item_definition_by_instance: tuple[tuple[str, str], ...] = ()
    equipment_definition_by_instance: tuple[tuple[str, str], ...] = ()
    learned_skill_levels: tuple[tuple[str, int], ...] = ()
    available_skill_definition_ids: frozenset[str] = frozenset()
    npc_definition_by_id: tuple[tuple[str, str], ...] = ()
    resource_ids: frozenset[str] = frozenset()
    currency_ids: frozenset[str] = frozenset()
    processed_client_request_ids: frozenset[str] = frozenset()
