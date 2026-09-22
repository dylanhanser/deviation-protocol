"""Authored opening talents. Only clock additions are in the active authority."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

CATALOG_VERSION = "opening-talents/v1"
CATALOG_SHA256 = "1600d3fbaafd4b6e6a47270716556f4b491e8c44f3aef4dddb26ee4cbba4078d"
MODIFIERS = {
    "T001": {"EXPLORE": -1, "CUSTOM": -1},
    "T006": {"TALK": -1, "EXPLORE": 1},
    "T007": {"OBSERVE": -1, "TALK": 1},
    "T008": {"CUSTOM": -1, "OBSERVE": 1},
    "T026": {"TALK": -1}, "T027": {"OBSERVE": -1},
    "T028": {"EXPLORE": -1}, "T029": {"CUSTOM": -1},
    "T061": {"TALK": 1}, "T062": {"OBSERVE": 1},
    "T063": {"EXPLORE": 1}, "T064": {"CUSTOM": 1},
}


@dataclass(frozen=True, slots=True)
class Talent:
    id: str
    name: str
    tier: str
    description: str
    status: str
    effect_and_dependencies: str


def load_catalog(version=CATALOG_VERSION) -> tuple[Talent, ...]:
    if version != CATALOG_VERSION:
        raise ValueError("unsupported opening talent catalog")
    raw = Path(__file__).with_name("opening_talents_v1.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        raise ValueError("opening talent catalog identity")
    entries = tuple(Talent(**v) for v in json.loads(raw))
    if (len(entries) != 100 or {t.id for t in entries} != {f"T{i:03}" for i in range(1, 101)}
            or len({t.name for t in entries}) != 100
            or tuple(sum(t.tier == tier for t in entries) for tier in ("TOP", "TRADEOFF", "ORDINARY", "WEAK")) != (5, 20, 35, 40)
            or {t.id for t in entries if t.status == "CURRENT"} != set(MODIFIERS)
            or sum(t.status == "FUTURE" for t in entries) != 88):
        raise ValueError("invalid opening talent catalog")
    return entries


def roll_candidates(seed: str, version=CATALOG_VERSION) -> tuple[str, ...]:
    """Versioned hash ranking, ties by ID; independent of Python RNG versions."""
    if type(seed) is not str or len(seed) != 64 or any(c not in "0123456789abcdef" for c in seed):
        raise ValueError("invalid opening seed")
    active = [t for t in load_catalog(version) if t.status == "CURRENT"]
    ranked = sorted(active, key=lambda t: (hashlib.sha256(
        f"opening-talents:hash-rank/v1\0{version}\0{seed}\0{t.id}".encode()).digest(), t.id))
    chosen = []
    top = False
    for talent in ranked:
        if talent.tier == "TOP" and top:
            continue
        chosen.append(talent.id)
        top |= talent.tier == "TOP"
        if len(chosen) == 5:
            return tuple(chosen)
    raise ValueError("insufficient active talents")


def validate_selection(candidates, selections, version=CATALOG_VERSION) -> tuple[str, str]:
    active = {t.id for t in load_catalog(version) if t.status == "CURRENT"}
    if (type(candidates) is not tuple or len(candidates) != 5 or len(set(candidates)) != 5
            or not set(candidates) <= active or type(selections) is not tuple
            or len(selections) != 2 or any(type(v) is not str for v in selections)
            or len(set(selections)) != 2 or not set(selections) <= set(candidates)):
        raise ValueError("choose exactly two issued active talents")
    return tuple(sorted(selections))


class OpeningTalentClockPolicy:
    def modifier(self, version: str | None, selections: tuple[str, ...], action: str) -> int:
        if version is None and selections == ():
            return 0  # Explicit legacy Run: no inferred talents.
        active = {t.id for t in load_catalog(version) if t.status == "CURRENT"}
        if len(selections) != 2 or len(set(selections)) != 2 or not set(selections) <= active:
            raise ValueError("invalid confirmed talent binding")
        return sum(MODIFIERS[t].get(action, 0) for t in selections)

    def additional(self, original: int, modifier: int) -> int:
        if type(original) is not int or original < 0 or type(modifier) is not int:
            raise ValueError("invalid additional clock")
        return max(0, original + modifier)
