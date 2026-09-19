"""Preloaded, version-exact content for owned Sessions.

Registry construction belongs to composition. Lookup and reconstruction perform
no filesystem access and never combine definitions from different packs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Any

from deviation_protocol.domain.scenario import ScenarioCatalog
from deviation_protocol.domain.state import GameState
from deviation_protocol.domain.world_continuation import (
    ContinuationPoolEntryV1, WorldStateRootV1,
)

# Approved raw UTF-8 deployment bytes, fixed independently of runtime input.
# This pack's .gitattributes override preserves its frozen CRLF bytes; do not
# normalize or refresh this pin on load.
DESTINATION_CONTENT_IDENTITY = ("undelivered_receipt", "undelivered-receipt-1.0.0")
DESTINATION_CONTENT_SHA256 = "74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c"
ARCHIVE_CONTENT_IDENTITY = ("receipt_archive", "receipt-archive-1.0.0")
ARCHIVE_CONTENT_SHA256 = "fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39"


@dataclass(frozen=True, slots=True)
class SessionContentBundle:
    scenario_id: str
    content_version: str
    content_sha256: str
    scenario_catalog: ScenarioCatalog
    session_service: Any = None
    turn_orchestrator: Any = None

    @classmethod
    def from_bytes(cls, payload: bytes, **services) -> SessionContentBundle:
        from json import loads
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate content member")
                result[key] = value
            return result
        if type(payload) is not bytes or not 1 <= len(payload) <= 2_000_000:
            raise ValueError("invalid content pack bytes")
        catalog = ScenarioCatalog.model_validate(loads(payload.decode("utf-8"), object_pairs_hook=unique))
        if len(catalog.scenarios) != 1:
            raise ValueError("owned content bundle requires one scenario")
        scenario = catalog.scenarios[0]
        return cls(scenario.scenario_id, catalog.content_version,
                   hashlib.sha256(payload).hexdigest(), catalog, **services)

    def __post_init__(self):
        if (type(self.scenario_id) is not str or type(self.content_version) is not str
                or type(self.content_sha256) is not str or len(self.content_sha256) != 64
                or any(c not in "0123456789abcdef" for c in self.content_sha256)
                or self.scenario_catalog.content_version != self.content_version
                or len(self.scenario_catalog.scenarios) != 1
                or self.scenario_catalog.scenarios[0].scenario_id != self.scenario_id):
            raise ValueError("invalid content bundle identity")
        if (self.scenario_id == DESTINATION_CONTENT_IDENTITY[0]
                or self.content_version == DESTINATION_CONTENT_IDENTITY[1]):
            if ((self.scenario_id, self.content_version) != DESTINATION_CONTENT_IDENTITY
                    or self.content_sha256 != DESTINATION_CONTENT_SHA256):
                raise ValueError("required destination content identity mismatch")
        if self.session_service is not None and (
                self.session_service.catalog != self.scenario_catalog.content_catalog
                or self.session_service.scenario_catalog != self.scenario_catalog):
            raise ValueError("service/content association mismatch")
        if (self.scenario_id == ARCHIVE_CONTENT_IDENTITY[0]
                or self.content_version == ARCHIVE_CONTENT_IDENTITY[1]):
            if ((self.scenario_id, self.content_version) != ARCHIVE_CONTENT_IDENTITY
                    or self.content_sha256 != ARCHIVE_CONTENT_SHA256):
                raise ValueError("required archive content identity mismatch")

    def validate_snapshot(self, snapshot: dict) -> GameState:
        state = GameState.from_snapshot(snapshot, catalog=self.scenario_catalog.content_catalog,
                                        scenario_catalog=self.scenario_catalog)
        runtime = state.scenario_runtime
        if runtime is None or runtime.scenario_id != self.scenario_id:
            raise ValueError("snapshot scenario/content association mismatch")
        runtime.validate_against(self.scenario_catalog.scenarios[0])
        state.validate_player_memory_against(self.scenario_catalog)
        return state


class SessionContentRegistry:
    def __init__(self, bundles: tuple[SessionContentBundle, ...]):
        if type(bundles) is not tuple or not bundles:
            raise ValueError("content registry requires preloaded bundles")
        by_identity = {}
        for bundle in bundles:
            if type(bundle) is not SessionContentBundle:
                raise TypeError("expected content bundle")
            key = (bundle.scenario_id, bundle.content_version)
            if key in by_identity:
                raise ValueError("duplicate content identity")
            by_identity[key] = bundle
        if DESTINATION_CONTENT_IDENTITY not in by_identity:
            raise ValueError("required destination content missing")
        if ARCHIVE_CONTENT_IDENTITY not in by_identity:
            raise ValueError("required archive content missing")
        self._bundles = MappingProxyType(by_identity)

    def resolve(self, scenario_id: str, content_version: str) -> SessionContentBundle:
        if type(scenario_id) is not str or type(content_version) is not str:
            raise TypeError("exact Session content identity required")
        try:
            return self._bundles[(scenario_id, content_version)]
        except KeyError:
            raise ValueError("unsupported owned Session content") from None

    def for_session(self, session) -> SessionContentBundle:
        return self.resolve(session.scenario_id, session.scenario_version)

    def validate_root(self, root: WorldStateRootV1) -> GameState:
        root = WorldStateRootV1.model_validate(root)
        bundle = self.resolve(root.scenario_id, root.scenario_content_version)
        if root.content_sha256 != bundle.content_sha256:
            raise ValueError("world root content digest mismatch")
        return bundle.validate_snapshot(root.snapshot)

    def continuation_pool(self) -> tuple[ContinuationPoolEntryV1, ...]:
        bundle = self.resolve(*DESTINATION_CONTENT_IDENTITY)
        return (ContinuationPoolEntryV1(world_id="world.undelivered_receipt",world_version=1,
            region_id="region.undelivered_receipt.dispatch_hall",region_version=1,
            scenario_id=bundle.scenario_id,scenario_content_version=bundle.content_version,
            content_sha256=bundle.content_sha256,required_priority=0,weight=1),)

    def regional_pool(self):
        from deviation_protocol.domain.world_continuation import DESTINATION_WORLD
        from deviation_protocol.domain.world_revisit import ARCHIVE_REGION, RegionalPoolEntryV1
        bundle = self.resolve(*ARCHIVE_CONTENT_IDENTITY)
        return (RegionalPoolEntryV1(world=DESTINATION_WORLD, region=ARCHIVE_REGION,
            scenario_id=bundle.scenario_id, scenario_content_version=bundle.content_version,
            content_sha256=bundle.content_sha256, required_priority=0, weight=1,
            cooldown_completed_visits=0),)
