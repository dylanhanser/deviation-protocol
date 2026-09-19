"""Closed regional revisit evidence; old world/visit codecs remain unchanged."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from deviation_protocol.domain.run import (
    RunOperationId, canonical_run_operation_bytes, revalidate_run_model,
    _require_exact_utc_datetime,
)
from deviation_protocol.domain.world_continuation import (
    _Evidence, _unique_object, _reject_constant, OpaqueId, SessionId, Digest,
    Version, SessionVersion, WorldRefV1, RegionRefV1, WorldVisitId,
    SOURCE_WORLD, SOURCE_REGION, DESTINATION_WORLD, DESTINATION_REGION,
    derive_world_visit_id, snapshot_canonical_bytes,
)

ARCHIVE_REGION = RegionRefV1(
    region_id="region.undelivered_receipt.verification_archive", region_version=1)
ARCHIVE_IDENTITY = ("receipt_archive", "receipt-archive-1.0.0")
ARCHIVE_NOTICE = "会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。"
HELD_ENDING = "undelivered_receipt.ending.receipt_held"
ARCHIVE_ENDINGS = (
    ("receipt_archive.ending.unresolved_sealed", "RESOLVED"),
    ("receipt_archive.ending.review_deferred", "FAILED"),
)


def derive_regional_visit_id(*, run_id: str, continuous_story_line_id: str,
                            session_id: str, joined_state_version: int) -> WorldVisitId:
    class Identity(_Evidence):
        schema_version: Literal["run.world-visit-id/v2"] = Field(alias="schema")
        run_id: OpaqueId
        continuous_story_line_id: OpaqueId
        session_id: SessionId
        joined_state_version: int = Field(strict=True, ge=5, le=5)
    identity = Identity(schema="run.world-visit-id/v2", run_id=run_id,
        continuous_story_line_id=continuous_story_line_id, session_id=session_id,
        joined_state_version=joined_state_version)
    return WorldVisitId(value=hashlib.sha256(canonical_run_operation_bytes(identity)).hexdigest())


class RegionalPoolEntryV1(_Evidence):
    world: WorldRefV1
    region: RegionRefV1
    scenario_id: Literal["receipt_archive"]
    scenario_content_version: Literal["receipt-archive-1.0.0"]
    content_sha256: Digest
    required_priority: int = Field(strict=True, ge=0, le=0)
    weight: int = Field(strict=True, ge=1, le=1)
    cooldown_completed_visits: int = Field(strict=True, ge=0, le=0)

    @model_validator(mode="after")
    def _edge(self):
        if (self.world, self.region) != (DESTINATION_WORLD, ARCHIVE_REGION):
            raise ValueError("unsupported regional edge")
        return self


class RegionalSelectionVisitV1(_Evidence):
    visit_id: OpaqueId
    visit_ordinal: int = Field(strict=True, ge=1, le=2)
    world: WorldRefV1
    region: RegionRefV1
    session_id: SessionId


class RegionalSelectionInputsV1(_Evidence):
    selector_version: Literal["regional-revisit/v1"]
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    source_session_id: SessionId
    source_session_state_version: SessionVersion
    source_snapshot_sha256: Digest
    resolution_fingerprint: Digest
    visits: tuple[RegionalSelectionVisitV1, RegionalSelectionVisitV1]
    eligible_pool: tuple[RegionalPoolEntryV1, ...]

    @model_validator(mode="after")
    def _history(self):
        if len(self.eligible_pool) > 1 or self.visits[1].session_id != self.source_session_id:
            raise ValueError("invalid regional pool or source")
        if self.visits[0].session_id == self.visits[1].session_id:
            raise ValueError("regional prefix needs distinct Sessions")
        for ordinal, visit, world, region in (
                (1, self.visits[0], SOURCE_WORLD, SOURCE_REGION),
                (2, self.visits[1], DESTINATION_WORLD, DESTINATION_REGION)):
            if ((visit.visit_ordinal, visit.world, visit.region) != (ordinal, world, region)
                    or visit.visit_id != derive_world_visit_id(run_id=self.run_id,
                        continuous_story_line_id=self.continuous_story_line_id,
                        session_id=visit.session_id, joined_state_version=ordinal + 2).value):
                raise ValueError("invalid regional prefix")
        if len(canonical_run_operation_bytes(self)) > 16384:
            raise ValueError("regional selection exceeds its bound")
        return self

    def seed(self) -> str:
        revalidate_run_model(self, RegionalSelectionInputsV1)
        return hashlib.sha256(b"deviation-protocol:regional-revisit-selection:v1\0"
                              + canonical_run_operation_bytes(self)).hexdigest()


class NativeRunRegionalRevisitRequestV1(_Evidence):
    schema_version: Literal["run.revisit-native-region-request/v1"] = Field(alias="schema")
    controller_binding: OpaqueId
    player_id: OpaqueId
    public_operation_key: OpaqueId
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    source_session_id: SessionId
    expected_run_state_version: Version
    expected_session_state_version: SessionVersion
    source_reference: OpaqueId

    def _identity(self, schema: str) -> str:
        revalidate_run_model(self, NativeRunRegionalRevisitRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(dict(schema=schema,
            controller_binding=self.controller_binding,
            public_operation_key=self.public_operation_key, run_id=self.run_id))).hexdigest()

    def operation_id(self) -> RunOperationId:
        return RunOperationId(value=self._identity("run.revisit-native-region-operation/v1"))

    def creation_request_id(self) -> str:
        return self._identity("run.regional-session-create/v1")

    def fingerprint(self) -> str:
        revalidate_run_model(self, NativeRunRegionalRevisitRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()


class RegionalSourceEndingV1(_Evidence):
    scenario_id: Literal["undelivered_receipt"]
    scenario_content_version: Literal["undelivered-receipt-1.0.0"]
    ending_id: Literal["undelivered_receipt.ending.receipt_held"]
    ending_status: Literal["RESOLVED"]
    session_state_version: SessionVersion
    snapshot_sha256: Digest


class NativeRunRegionalRevisitEvidenceV1(_Evidence):
    schema_version: Literal["run.revisit-native-region-evidence/v1"] = Field(alias="schema")
    request: NativeRunRegionalRevisitRequestV1
    source_ending: RegionalSourceEndingV1
    selection_inputs: RegionalSelectionInputsV1
    selection_seed: Digest
    source_visit_id: OpaqueId
    destination_visit_id: OpaqueId
    destination_session_id: SessionId
    destination_creation_request_id: OpaqueId
    destination_initial_event_id: SessionId
    destination_random_seed: int = Field(strict=True, ge=0, le=2**63 - 1)
    world_base_snapshot_sha256: Digest
    destination_entry_sha256: Digest
    carryover_rule: Literal["carry-player-state/v1"]
    occurred_at: str = Field(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

    @model_validator(mode="after")
    def _association(self):
        request, ending, inputs = self.request, self.source_ending, self.selection_inputs
        stamp = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if stamp.microsecond or stamp.tzinfo != timezone.utc:
            raise ValueError("regional time must use Session precision")
        if (request.expected_run_state_version != 4
                or ending.session_state_version != request.expected_session_state_version
                or inputs.run_id != request.run_id
                or inputs.continuous_story_line_id != request.continuous_story_line_id
                or inputs.source_session_id != request.source_session_id
                or inputs.source_session_state_version != ending.session_state_version
                or inputs.source_snapshot_sha256 != ending.snapshot_sha256
                or self.world_base_snapshot_sha256 != ending.snapshot_sha256
                or len(inputs.eligible_pool) != 1 or self.selection_seed != inputs.seed()
                or self.source_visit_id != inputs.visits[1].visit_id
                or self.destination_session_id in tuple(v.session_id for v in inputs.visits)
                or self.destination_creation_request_id != request.creation_request_id()
                or self.destination_visit_id != derive_regional_visit_id(
                    run_id=request.run_id, continuous_story_line_id=request.continuous_story_line_id,
                    session_id=self.destination_session_id, joined_state_version=5).value
                or len(canonical_run_operation_bytes(self)) > 16384):
            raise ValueError("invalid regional evidence association")
        return self


def decode_native_run_regional_revisit_evidence(payload: bytes) -> NativeRunRegionalRevisitEvidenceV1:
    obj = _decode_object(payload, 16384)
    inputs = obj.get("selection_inputs") if type(obj) is dict else None
    if type(inputs) is dict:
        for field in ("visits", "eligible_pool"):
            if type(inputs.get(field)) is list:
                inputs[field] = tuple(inputs[field])
    value = NativeRunRegionalRevisitEvidenceV1.model_validate(obj, strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical regional evidence")
    return value


def _decode_object(payload: bytes, limit: int):
    if type(payload) is not bytes or not 1 <= len(payload) <= limit:
        raise ValueError("invalid regional canonical bytes")
    return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


class WorldVisitV2(_Evidence):
    run_id: OpaqueId
    visit_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_ordinal: int = Field(strict=True, ge=3, le=3)
    world_id: Literal["world.undelivered_receipt"]
    world_version: int = Field(strict=True, ge=1, le=1)
    region_id: Literal["region.undelivered_receipt.verification_archive"]
    region_version: int = Field(strict=True, ge=1, le=1)
    session_id: SessionId
    joined_state_version: int = Field(strict=True, ge=5, le=5)
    materialized_state_version: int = Field(strict=True, ge=5, le=5)
    operation_id: OpaqueId
    source_reference: OpaqueId
    entered_at: datetime
    created_at: datetime

    @model_validator(mode="after")
    def _association(self):
        _require_exact_utc_datetime(self.entered_at)
        _require_exact_utc_datetime(self.created_at)
        if (self.entered_at != self.created_at or self.entered_at.microsecond
                or self.visit_id != derive_regional_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=5).value):
            raise ValueError("invalid regional visit")
        return self


class WorldPositionV2(_Evidence):
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_id: OpaqueId
    session_id: SessionId
    position_state_version: int = Field(strict=True, ge=5, le=5)
    created_at: datetime

    @model_validator(mode="after")
    def _association(self):
        _require_exact_utc_datetime(self.created_at)
        if self.visit_id != derive_regional_visit_id(run_id=self.run_id,
                continuous_story_line_id=self.continuous_story_line_id,
                session_id=self.session_id, joined_state_version=5).value:
            raise ValueError("invalid regional position")
        return self


class RegionalEntryV1(_Evidence):
    schema_version: Literal["run-regional-entry/v1"] = Field(alias="schema")
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_id: OpaqueId
    session_id: SessionId
    world: WorldRefV1
    region: RegionRefV1
    scenario_id: Literal["receipt_archive"]
    scenario_content_version: Literal["receipt-archive-1.0.0"]
    content_sha256: Digest
    base_visit_id: OpaqueId
    base_session_id: SessionId
    base_session_state_version: SessionVersion
    base_snapshot_sha256: Digest
    unlock_ending_id: Literal["undelivered_receipt.ending.receipt_held"]
    snapshot_state_version: int = Field(strict=True, ge=0, le=0)
    snapshot: dict[str, Any]
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _association(self):
        from deviation_protocol.domain.state import GameState
        raw = snapshot_canonical_bytes(self.snapshot)
        validated = GameState.model_validate_json(raw, strict=True)
        if (snapshot_canonical_bytes(validated.to_snapshot()) != raw
                or validated.content_version != self.scenario_content_version
                or validated.scenario_runtime is None
                or validated.scenario_runtime.scenario_id != self.scenario_id
                or (self.world, self.region) != (DESTINATION_WORLD, ARCHIVE_REGION)
                or hashlib.sha256(raw).hexdigest() != self.snapshot_sha256
                or self.session_id == self.base_session_id
                or self.visit_id != derive_regional_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=5).value
                or self.base_visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.base_session_id, joined_state_version=4).value
                or len(snapshot_canonical_bytes(self.model_dump(mode="json"))) > 1048576):
            raise ValueError("invalid regional entry")
        return self

    def canonical_bytes(self) -> bytes:
        revalidate_run_model(self, RegionalEntryV1)
        return snapshot_canonical_bytes(self.model_dump(mode="json"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def decode_regional_entry(payload: bytes) -> RegionalEntryV1:
    value = RegionalEntryV1.model_validate(_decode_object(payload, 1048576), strict=True)
    if value.canonical_bytes() != payload:
        raise ValueError("noncanonical regional entry")
    return value
