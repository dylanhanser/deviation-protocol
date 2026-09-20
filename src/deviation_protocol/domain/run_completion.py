"""Closed, canon-preserving completion values. These values confer no authority."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Literal

from pydantic import Field, model_validator

from deviation_protocol.domain.run import (
    RunOperationId, canonical_run_operation_bytes, revalidate_run_model,
)
from deviation_protocol.domain.world_continuation import (
    _Evidence, OpaqueId, SessionId, Digest, Version, SessionVersion,
    WorldRefV1, RegionRefV1, SOURCE_WORLD, SOURCE_REGION, SOURCE_ENDINGS,
    DESTINATION_WORLD, DESTINATION_REGION,
)
from deviation_protocol.domain.world_revisit import ARCHIVE_REGION, _decode_object

COMPLETION_RULE = "receipt-archive-closure/v1"
SEALED_ENDING = "receipt_archive.ending.unresolved_sealed"
MAX_COMPLETION_BYTES = 16384


class NativeRunCompletionRequestV1(_Evidence):
    schema_version: Literal["run.complete-revisited-native-request/v1"] = Field(alias="schema")
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
        revalidate_run_model(self, NativeRunCompletionRequestV1)
        return RunOperationId(value=hashlib.sha256(canonical_run_operation_bytes({
            "schema": "run.complete-revisited-native-operation/v1",
            "controller_binding": self.controller_binding,
            "public_operation_key": self.public_operation_key,
            "run_id": self.run_id,
        })).hexdigest())

    def fingerprint(self) -> str:
        revalidate_run_model(self, NativeRunCompletionRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()

    def completion_id(self) -> str:
        return hashlib.sha256(canonical_run_operation_bytes({
            "schema": "run.completion-id/v1", "run_id": self.run_id,
            "continuous_story_line_id": self.continuous_story_line_id,
            "operation_id": self.operation_id().value,
        })).hexdigest()


class CompletionSourceV1(_Evidence):
    visit_id: OpaqueId
    visit_ordinal: int = Field(strict=True, ge=1, le=3)
    session_id: SessionId
    session_state_version: SessionVersion
    world: WorldRefV1
    region: RegionRefV1
    scenario_id: OpaqueId
    scenario_content_version: OpaqueId
    content_sha256: Digest
    snapshot_sha256: Digest
    ending_id: OpaqueId
    ending_status: Literal["RESOLVED", "FAILED"]


class CompletionDecisionEventV1(_Evidence):
    session_id: SessionId
    event_id: SessionId
    sequence_no: Version
    scenario_event_id: OpaqueId
    decision_id: OpaqueId
    selected_action_id: OpaqueId


class CompletionPreservedFactsV1(_Evidence):
    dispatch_held: Literal[True]
    delivery_unproven: Literal[True]
    unresolved_sealed: Literal[True]

    @model_validator(mode="before")
    @classmethod
    def _actual_booleans(cls, value):
        if type(value) is dict and any(type(v) is not bool for v in value.values()):
            raise ValueError("preserved facts must be actual booleans")
        return value


class CanonTransitionV1(_Evidence):
    schema_version: Literal["run.canon-transition/v1"] = Field(alias="schema")
    kind: Literal["close_unresolved_verification/v1"]
    world: WorldRefV1
    from_disposition: Literal["open_unresolved"]
    to_disposition: Literal["closed_unresolved"]
    preserved_facts: CompletionPreservedFactsV1

    @model_validator(mode="after")
    def _world(self):
        if self.world != DESTINATION_WORLD:
            raise ValueError("completion affects only the existing second world")
        return self


class NativeRunCompletionEvidenceV1(_Evidence):
    schema_version: Literal["run.complete-revisited-native-evidence/v1"] = Field(alias="schema")
    request: NativeRunCompletionRequestV1
    completion_id: Digest
    rule_version: Literal["receipt-archive-closure/v1"]
    sources: tuple[CompletionSourceV1, CompletionSourceV1, CompletionSourceV1]
    held_event: CompletionDecisionEventV1
    sealed_event: CompletionDecisionEventV1
    transition: CanonTransitionV1
    occurred_at: str = Field(strict=True, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

    @model_validator(mode="after")
    def _association(self):
        stamp = datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if stamp.tzinfo != timezone.utc:
            raise ValueError("completion time must be UTC")
        request = self.request
        if (request.expected_run_state_version != 5
                or self.completion_id != request.completion_id()
                or len({s.session_id for s in self.sources}) != 3
                or len({s.visit_id for s in self.sources}) != 3
                or self.sources[2].session_id != request.source_session_id
                or self.sources[2].session_state_version != request.expected_session_state_version):
            raise ValueError("invalid completion source association")
        identities = (
            (SOURCE_WORLD, SOURCE_REGION, "death_certificate", "death-certificate-1.1.0"),
            (DESTINATION_WORLD, DESTINATION_REGION, "undelivered_receipt", "undelivered-receipt-1.0.0"),
            (DESTINATION_WORLD, ARCHIVE_REGION, "receipt_archive", "receipt-archive-1.0.0"),
        )
        for ordinal, (source, identity) in enumerate(zip(self.sources, identities), 1):
            if (source.visit_ordinal != ordinal
                    or (source.world, source.region, source.scenario_id,
                        source.scenario_content_version) != identity):
                raise ValueError("unsupported completion source")
        if ((self.sources[0].ending_id, self.sources[0].ending_status) not in SOURCE_ENDINGS
                or (self.sources[1].ending_id, self.sources[1].ending_status)
                != ("undelivered_receipt.ending.receipt_held", "RESOLVED")
                or (self.sources[2].ending_id, self.sources[2].ending_status)
                != (SEALED_ENDING, "RESOLVED")):
            raise ValueError("completion requires hold and seal endings")
        for event, source, decision, action in (
            (self.held_event, self.sources[1], "undelivered_receipt.decision.dispatch", "undelivered_receipt.action.hold"),
            (self.sealed_event, self.sources[2], "receipt_archive.decision.record", "receipt_archive.action.seal"),
        ):
            if (event.session_id != source.session_id or event.decision_id != decision
                    or event.selected_action_id != action):
                raise ValueError("completion decision association")
        if len(canonical_run_operation_bytes(self)) > MAX_COMPLETION_BYTES:
            raise ValueError("completion evidence exceeds its bound")
        return self


def decode_native_run_completion_request(payload: bytes) -> NativeRunCompletionRequestV1:
    value = NativeRunCompletionRequestV1.model_validate(_decode_object(payload, MAX_COMPLETION_BYTES), strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical completion request")
    return value


def decode_native_run_completion_evidence(payload: bytes) -> NativeRunCompletionEvidenceV1:
    raw = _decode_object(payload, MAX_COMPLETION_BYTES)
    if type(raw.get("sources")) is not list:
        raise ValueError("completion sources must be a JSON array")
    raw["sources"] = tuple(raw["sources"])
    value = NativeRunCompletionEvidenceV1.model_validate(raw, strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical completion evidence")
    return value


class RunCompletionEligibilityPolicy:
    """Pure ending rule, applied only after full stored-family validation."""

    def qualifies(self, state) -> bool:
        runtime = state.scenario_runtime
        return (runtime is not None and runtime.scenario_id == "receipt_archive"
                and runtime.scenario_content_version == "receipt-archive-1.0.0"
                and runtime.ending_id == SEALED_ENDING
                and runtime.ending_status.value == "RESOLVED"
                and runtime.mutable_fact_values.get("receipt_archive.fact.unresolved_sealed") is True)
