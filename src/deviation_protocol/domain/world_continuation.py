"""Closed same-line continuation identities and canonical evidence.

Operation evidence uses the Run NFC encoding. World roots deliberately retain
the snapshot encoding, including decomposed Unicode, without normalization.
None of these value objects supplies caller or mutation authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.domain.run import (
    RunOperationId, _OpaqueReference, _StrictFrozenModel,
    _validate_actual_pydantic_state, canonical_run_operation_bytes,
    revalidate_run_model, _require_exact_utc_datetime,
)


class WorldId(_OpaqueReference):
    """Authored persistent world identity, separate from a Session or scenario."""


class WorldVisitId(_OpaqueReference):
    """One immutable occurrence of a world within a Run."""


class RegionId(_OpaqueReference):
    """An authored region within a world."""


class WorldVersion(_StrictFrozenModel):
    value: int = Field(strict=True, ge=1, le=2**63 - 1)


class RegionVersion(_StrictFrozenModel):
    value: int = Field(strict=True, ge=1, le=2**63 - 1)


OpaqueId = Annotated[str, Field(strict=True, min_length=1, max_length=128,
                                pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
SessionId = Annotated[str, Field(strict=True, min_length=1, max_length=64,
                                 pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
ContentVersion = Annotated[str, Field(strict=True, min_length=1, max_length=32,
                                      pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
Version = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
SessionVersion = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]


class _Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always", serialize_by_alias=True)

    @model_validator(mode="wrap")
    @classmethod
    def _original(cls, value, handler):
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError("unexpected continuation carrier")
            _validate_actual_pydantic_state(value, path=cls.__name__, visited=set())
            value = dict(value.__dict__)
            if "schema_version" in value:
                value["schema"] = value.pop("schema_version")
        return handler(value)


class WorldRefV1(_Evidence):
    world_id: OpaqueId
    world_version: Version


class RegionRefV1(_Evidence):
    region_id: OpaqueId
    region_version: Version


SELECTOR_VERSION = "same-line-continuation/v1"
CARRYOVER_RULE = "carry-player-state/v1"
SOURCE_WORLD = WorldRefV1(world_id="world.death_certificate", world_version=1)
SOURCE_REGION = RegionRefV1(region_id="region.death_certificate.facility", region_version=1)
DESTINATION_WORLD = WorldRefV1(world_id="world.undelivered_receipt", world_version=1)
DESTINATION_REGION = RegionRefV1(region_id="region.undelivered_receipt.dispatch_hall", region_version=1)
SOURCE_ENDINGS = (
    ("death_certificate.ending.protocol_broken", "RESOLVED"),
    ("death_certificate.ending.record_challenged", "RESOLVED"),
    ("death_certificate.ending.deadline_reached", "FAILED"),
)


class ContinuationPoolEntryV1(_Evidence):
    world_id: OpaqueId
    world_version: Version
    region_id: OpaqueId
    region_version: Version
    scenario_id: OpaqueId
    scenario_content_version: ContentVersion
    content_sha256: Digest
    required_priority: int = Field(strict=True, ge=0, le=0)
    weight: int = Field(strict=True, ge=1, le=1)

    @model_validator(mode="after")
    def _closed_edge(self):
        if (self.world_id, self.world_version, self.region_id, self.region_version,
                self.scenario_id, self.scenario_content_version) != (
                "world.undelivered_receipt", 1, "region.undelivered_receipt.dispatch_hall", 1,
                "undelivered_receipt", "undelivered-receipt-1.0.0"):
            raise ValueError("unsupported continuation edge")
        return self


class ContinuationSelectionInputsV1(_Evidence):
    selector_version: Literal["same-line-continuation/v1"]
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    source_session_id: SessionId
    source_session_state_version: SessionVersion
    source_snapshot_sha256: Digest
    source_world: WorldRefV1
    source_ending_id: OpaqueId
    source_ending_status: Literal["RESOLVED", "FAILED"]
    resolution_fingerprint: Digest
    visited_worlds: tuple[WorldRefV1, ...]
    eligible_pool: tuple[ContinuationPoolEntryV1, ...]

    @model_validator(mode="after")
    def _closed_selection(self):
        for world in self.visited_worlds:
            revalidate_run_model(world, WorldRefV1)
        if (self.source_world != SOURCE_WORLD
                or (self.source_ending_id, self.source_ending_status) not in SOURCE_ENDINGS
                or self.visited_worlds != (SOURCE_WORLD,)
                or len(self.eligible_pool) > 1):
            raise ValueError("unsupported continuation selection")
        for edge in self.eligible_pool:
            revalidate_run_model(edge, ContinuationPoolEntryV1)
            if edge.world_id in {world.world_id for world in self.visited_worlds}:
                raise ValueError("continuation cannot revisit a world")
        return self

    def seed(self) -> str:
        revalidate_run_model(self, ContinuationSelectionInputsV1)
        return hashlib.sha256(
            b"deviation-protocol:world-continuation-selection:v1\0"
            + canonical_run_operation_bytes(self)
        ).hexdigest()


class NativeRunContinuationRequestV1(_Evidence):
    schema_version: Literal["run.continue-native-request/v1"] = Field(alias="schema")
    controller_binding: OpaqueId
    player_id: OpaqueId
    public_operation_key: OpaqueId
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    source_session_id: SessionId
    expected_run_state_version: Version
    expected_session_state_version: SessionVersion
    source_reference: OpaqueId

    def operation_id(self) -> RunOperationId:
        return RunOperationId(value=self._identity("run.continue-native-operation/v1"))

    def creation_request_id(self) -> str:
        return self._identity("run.continuation-session-create/v1")

    def _identity(self, schema: str) -> str:
        revalidate_run_model(self, NativeRunContinuationRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(dict(
            schema=schema, controller_binding=self.controller_binding,
            public_operation_key=self.public_operation_key, run_id=self.run_id,
        ))).hexdigest()

    def fingerprint(self) -> str:
        revalidate_run_model(self, NativeRunContinuationRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()


def derive_world_visit_id(*, run_id: str, continuous_story_line_id: str,
                          session_id: str, joined_state_version: int) -> WorldVisitId:
    RunOperationId(value=run_id)
    RunOperationId(value=continuous_story_line_id)
    # The carrier checks original types before any canonicalization.
    class VisitIdentity(_Evidence):
        schema_version: Literal["run.world-visit-id/v1"] = Field(alias="schema")
        run_id: OpaqueId
        continuous_story_line_id: OpaqueId
        session_id: SessionId
        joined_state_version: int = Field(strict=True, ge=3, le=4)
    identity = VisitIdentity(schema="run.world-visit-id/v1", run_id=run_id,
        continuous_story_line_id=continuous_story_line_id, session_id=session_id,
        joined_state_version=joined_state_version)
    return WorldVisitId(value=hashlib.sha256(canonical_run_operation_bytes(identity)).hexdigest())


class ContinuationSourceEndingV1(_Evidence):
    scenario_id: Literal["death_certificate"]
    scenario_content_version: Literal["death-certificate-1.1.0"]
    ending_id: OpaqueId
    ending_status: Literal["RESOLVED", "FAILED"]
    session_state_version: SessionVersion
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _ending(self):
        if (self.ending_id, self.ending_status) not in SOURCE_ENDINGS:
            raise ValueError("unsupported source ending")
        return self


class NativeRunContinuationEvidenceV1(_Evidence):
    schema_version: Literal["run.continue-native-evidence/v1"] = Field(alias="schema")
    request: NativeRunContinuationRequestV1
    source_ending: ContinuationSourceEndingV1
    selection_inputs: ContinuationSelectionInputsV1
    selection_seed: Digest
    source_visit_id: OpaqueId
    destination_visit_id: OpaqueId
    destination_session_id: SessionId
    destination_creation_request_id: OpaqueId
    destination_initial_event_id: SessionId
    destination_random_seed: int = Field(strict=True, ge=0, le=2**63 - 1)
    source_world_state_sha256: Digest
    destination_world_state_sha256: Digest
    carryover_rule: Literal["carry-player-state/v1"]
    entry_variant: Literal["resolved", "failed"]
    occurred_at: str = Field(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

    @model_validator(mode="after")
    def _association(self):
        request, source, inputs = self.request, self.source_ending, self.selection_inputs
        for obj in (request, source, inputs):
            revalidate_run_model(obj, type(obj))
        stamp = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if stamp.microsecond != 0 or stamp.tzinfo != timezone.utc:
            raise ValueError("continuation time must use Session precision")
        if (request.expected_run_state_version != 3
                or source.session_state_version != request.expected_session_state_version
                or inputs.run_id != request.run_id
                or inputs.continuous_story_line_id != request.continuous_story_line_id
                or inputs.source_session_id != request.source_session_id
                or inputs.source_session_state_version != source.session_state_version
                or inputs.source_snapshot_sha256 != source.snapshot_sha256
                or inputs.source_ending_id != source.ending_id
                or inputs.source_ending_status != source.ending_status
                or len(inputs.eligible_pool) != 1
                or inputs.seed() != self.selection_seed
                or self.entry_variant != source.ending_status.lower()
                or self.destination_session_id == request.source_session_id
                or self.destination_creation_request_id != request.creation_request_id()):
            raise ValueError("invalid continuation evidence association")
        for sid, revision, visit in (
                (request.source_session_id, 3, self.source_visit_id),
                (self.destination_session_id, 4, self.destination_visit_id)):
            if derive_world_visit_id(run_id=request.run_id,
                    continuous_story_line_id=request.continuous_story_line_id,
                    session_id=sid, joined_state_version=revision).value != visit:
                raise ValueError("invalid visit identity")
        if len(canonical_run_operation_bytes(self)) > 16384:
            raise ValueError("continuation evidence exceeds its bound")
        return self


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate canonical member")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite canonical scalar")


def decode_native_run_continuation_evidence(payload: bytes) -> NativeRunContinuationEvidenceV1:
    if type(payload) is not bytes or not 1 <= len(payload) <= 16384:
        raise ValueError("invalid continuation evidence bytes")
    obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                     parse_constant=_reject_constant)
    # JSON arrays represent the two closed tuple-valued input sequences.
    inputs = obj.get("selection_inputs") if type(obj) is dict else None
    if type(inputs) is dict:
        for field in ("visited_worlds", "eligible_pool"):
            if type(inputs.get(field)) is list:
                inputs[field] = tuple(inputs[field])
    value = NativeRunContinuationEvidenceV1.model_validate(obj, strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical continuation evidence")
    return value


def snapshot_canonical_bytes(value: Any) -> bytes:
    """The snapshot convention; never the NFC operation convention."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


class WorldStateRootV1(_Evidence):
    schema_version: Literal["run-world-state/v1"] = Field(alias="schema")
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    world: WorldRefV1
    region: RegionRefV1
    first_visit_id: OpaqueId
    session_id: SessionId
    scenario_id: OpaqueId
    scenario_content_version: ContentVersion
    content_sha256: Digest
    basis: Literal["sealed_ending", "session_initialization"]
    snapshot_state_version: SessionVersion
    snapshot: dict[str, Any]
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _association(self):
        from deviation_protocol.domain.state import GameState
        validated = GameState.model_validate_json(snapshot_canonical_bytes(self.snapshot), strict=True)
        if snapshot_canonical_bytes(validated.to_snapshot()) != snapshot_canonical_bytes(self.snapshot):
            raise ValueError("world root requires the complete original snapshot form")
        source = self.basis == "sealed_ending"
        expected = ((SOURCE_WORLD, SOURCE_REGION, "death_certificate", "death-certificate-1.1.0")
                    if source else (DESTINATION_WORLD, DESTINATION_REGION,
                                    "undelivered_receipt", "undelivered-receipt-1.0.0"))
        if ((self.world, self.region, self.scenario_id, self.scenario_content_version) != expected
                or (not source and self.snapshot_state_version != 0)
                or hashlib.sha256(snapshot_canonical_bytes(self.snapshot)).hexdigest() != self.snapshot_sha256
                or self.first_visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=3 if source else 4).value):
            raise ValueError("invalid world root association")
        if not 1 <= len(snapshot_canonical_bytes(self.model_dump(mode="json"))) <= 1048576:
            raise ValueError("world root exceeds its bound")
        return self

    def canonical_bytes(self) -> bytes:
        revalidate_run_model(self, WorldStateRootV1)
        return snapshot_canonical_bytes(self.model_dump(mode="json"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def decode_world_state_root(payload: bytes) -> WorldStateRootV1:
    if type(payload) is not bytes or not 1 <= len(payload) <= 1048576:
        raise ValueError("invalid world root bytes")
    obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object,
                     parse_constant=_reject_constant)
    value = WorldStateRootV1.model_validate(obj, strict=True)
    if value.canonical_bytes() != payload:
        raise ValueError("noncanonical world root")
    return value


class WorldVisitV1(_Evidence):
    run_id: OpaqueId
    visit_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_ordinal: int = Field(strict=True, ge=1, le=2)
    world_id: OpaqueId
    world_version: Version
    region_id: OpaqueId
    region_version: Version
    session_id: SessionId
    joined_state_version: int = Field(strict=True, ge=3, le=4)
    materialized_state_version: int = Field(strict=True, ge=4, le=4)
    operation_id: OpaqueId
    source_reference: OpaqueId
    entered_at: datetime
    created_at: datetime

    @model_validator(mode="after")
    def _association(self):
        _require_exact_utc_datetime(self.entered_at)
        _require_exact_utc_datetime(self.created_at)
        source = self.visit_ordinal == 1
        world, region = (SOURCE_WORLD, SOURCE_REGION) if source else (DESTINATION_WORLD, DESTINATION_REGION)
        if (self.joined_state_version != self.visit_ordinal + 2
                or (self.world_id, self.world_version) != (world.world_id, world.world_version)
                or (self.region_id, self.region_version) != (region.region_id, region.region_version)
                or self.entered_at > self.created_at
                or self.visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=self.joined_state_version).value):
            raise ValueError("invalid world visit association")
        return self


class WorldPositionV1(_Evidence):
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_id: OpaqueId
    session_id: SessionId
    position_state_version: int = Field(strict=True, ge=4, le=4)
    created_at: datetime

    @model_validator(mode="after")
    def _time(self):
        _require_exact_utc_datetime(self.created_at)
        return self
