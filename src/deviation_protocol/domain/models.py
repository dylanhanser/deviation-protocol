from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Player:
    """Legacy Phase 1 DTO; authoritative Phase 1.1 state uses PlayerState."""

    player_id: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NPC:
    """Legacy Phase 1 DTO; authoritative Phase 1.1 state uses NpcState."""

    npc_id: str
    name: str
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Inventory:
    """Legacy Phase 1 DTO; authoritative Phase 1.1 state uses InventoryState."""

    owner_id: str
    item_ids: set[str] = field(default_factory=set)


@dataclass(slots=True)
class Scene:
    scene_id: str
    visible_entity_ids: set[str] = field(default_factory=set)
    environment_tool_ids: set[str] = field(default_factory=set)


@dataclass(slots=True)
class GameSession:
    session_id: str
    player_id: str
    scenario_id: str
    scenario_version: str
    phase: str
    turn_number: int
    state_version: int
    random_seed: int
