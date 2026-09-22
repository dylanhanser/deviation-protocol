"""Pure, integer-only mechanics for the published S5 balance contract."""
from __future__ import annotations

from dataclasses import dataclass

from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.scenario import MAX_SCENARIO_COUNTER

MECHANICS_VERSION = "run-mechanics/v1"
OBJECTIVES = ("resource_pressure", "social_trust", "consequence_severity",
              "information_opacity", "conflict_intensity")


def pressure(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 100 or value % 5:
        raise ValueError("invalid objective value")
    return value // 50


def resource_pressure_label(value: int) -> str:
    pressure(value)
    return "Generous" if value <= 30 else "Fluid" if value <= 65 else "Scarce"


@dataclass(frozen=True, slots=True)
class MechanicsCatalogueEntry:
    world_id: str
    world_version: int
    scenario_id: str
    content_version: str
    character_id: str
    resource_id: str


MECHANICS_CATALOGUE = (
    MechanicsCatalogueEntry("world.death_certificate", 1, "death_certificate",
                            "death-certificate-1.1.0",
                            "character.death_certificate.investigator", "composure"),
    MechanicsCatalogueEntry("world.undelivered_receipt", 1, "undelivered_receipt",
                            "undelivered-receipt-1.0.0",
                            "character.death_certificate.investigator", "composure"),
    MechanicsCatalogueEntry("world.undelivered_receipt", 1, "receipt_archive",
                            "receipt-archive-1.0.0",
                            "character.death_certificate.investigator", "composure"),
)


@dataclass(frozen=True, slots=True)
class ResourcePlan:
    resource_id: str
    before: int
    requested: int
    actual: int
    after: int


class ResourcePressurePolicy:
    def plan(self, value: int, *, resource_id: str, current: int,
             maximum: int, narrative: bool) -> ResourcePlan:
        q = pressure(value)
        if (type(current) is not int or type(maximum) is not int
                or not 0 <= current <= maximum or maximum <= 0
                or type(narrative) is not bool or type(resource_id) is not str
                or not resource_id):
            raise ValueError("invalid resource input")
        requested = q if narrative else 0
        actual = min(current, requested)
        return ResourcePlan(resource_id, current, requested, actual, current - actual)


class SocialTrustPolicy:
    def extra(self, value: int, *, qualifying_talk: bool) -> int:
        pressure(value)
        if type(qualifying_talk) is not bool:
            raise ValueError("invalid social qualifier")
        return pressure(100 - value) if qualifying_talk else 0


class ConsequenceSeverityPolicy:
    def extra(self, value: int, *, result: NarrativeOutcomeResult | None) -> int:
        q = pressure(value)
        if result is not None and type(result) is not NarrativeOutcomeResult:
            raise ValueError("invalid selected result")
        return q if result is not None and result is not NarrativeOutcomeResult.SUCCESS else 0


class InformationOpacityPolicy:
    def extra(self, value: int, *, discovers: bool) -> int:
        q = pressure(value)
        if type(discovers) is not bool:
            raise ValueError("invalid discovery qualifier")
        return q if discovers else 0


class ConflictIntensityPolicy:
    def extra(self, value: int) -> int:
        return pressure(value)


@dataclass(frozen=True, slots=True)
class ClockPlan:
    clock_id: str
    before: int
    base: int
    social: int
    severity: int
    opacity: int
    conflict: int
    after: int
    talent: int = 0

    @property
    def amount(self) -> int:
        return self.base + self.social + self.severity + self.opacity + self.conflict + self.talent


def clock_plan(clock_id: str, before: int, maximum: int, base: int,
               social: int, severity: int, opacity: int, conflict: int) -> ClockPlan:
    if (any(type(x) is not int for x in (before, maximum, base, social, severity, opacity, conflict))
            or not 0 <= before <= maximum <= MAX_SCENARIO_COUNTER
            or not 1 <= base <= MAX_SCENARIO_COUNTER
            or any(not 0 <= x <= 2 for x in (social, severity, opacity, conflict))):
        raise ValueError("invalid clock plan")
    amount = base + social + severity + opacity + conflict
    return ClockPlan(clock_id, before, base, social, severity, opacity, conflict,
                     min(maximum, before + amount))
