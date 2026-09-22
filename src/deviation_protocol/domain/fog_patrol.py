"""Closed, separately versioned same-world patrol continuation carriers.

The original continuation codecs remain closed to their original worlds.
These carriers describe evidence, never caller-issued mutation authority.
"""
from datetime import datetime
import hashlib
import json
from typing import Any, Literal

from pydantic import Field, model_validator

from deviation_protocol.domain.run import (
    CanonicalRun, RunAuthoritySourceRef, RunLifecycleStatus, RunMutationKind,
    RunMutationProvenance, RunSessionParticipationReference, RunStateVersion,
    ReservedPlayerCharacterBinding, canonical_run_operation_bytes, revalidate_run_model,
)
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunAdmissionV1, ContinuedNativeRunExitRequestV1,
)
from deviation_protocol.domain.world_continuation import (
    _Evidence, OpaqueId, SessionId, Digest, SessionVersion,
    NativeRunContinuationRequestV1, WorldPositionV1, derive_world_visit_id,
    snapshot_canonical_bytes, _unique_object, _reject_constant,
)

SOURCE = ("fog_station", "fog-station-1.0.0")
SOURCE_HASH = "898b2557f56d6f41263e1f088358df871453d351f2fce79a8e379416d5873a7b"
DESTINATION = ("fog_patrol", "fog-patrol-1.0.0")
WORLD = "world.fog_station"
SOURCE_REGION = "region.fog_station.station"
REGION = "region.fog_station.patrol_pass"
LOGICAL_NPC = "authored-person.cen-zhou/v1"
SOURCE_NPC = "npc.fog_station.cen_zhou"
DESTINATION_NPC = "npc.fog_patrol.cen_zhou"
ENDINGS = tuple("fog_station.ending." + code for code in ("immediate", "declined", "finished", "reunited"))


class FogSourceV1(_Evidence):
    schema_version: Literal["fog-world-state/v1"] = Field(alias="schema")
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    first_visit_id: OpaqueId
    session_id: SessionId
    scenario_id: Literal["fog_station"] = "fog_station"
    scenario_content_version: Literal["fog-station-1.0.0"] = "fog-station-1.0.0"
    content_sha256: Literal[SOURCE_HASH] = SOURCE_HASH
    snapshot_state_version: SessionVersion
    snapshot: dict[str, Any]
    snapshot_sha256: Digest
    # Exact committed decision/initialization records, not memory-index prose.
    events: tuple[dict[str, Any], ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _binding(self):
        runtime = self.snapshot.get("scenario_runtime", {})
        if (hashlib.sha256(snapshot_canonical_bytes(self.snapshot)).hexdigest() != self.snapshot_sha256
                or runtime.get("ending_id") not in ENDINGS
                or runtime.get("ending_status") != "RESOLVED"
                or self.first_visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=3).value):
            raise ValueError("invalid fog source association")
        if len(self.canonical_bytes()) > 1048576:
            raise ValueError("fog source exceeds storage bound")
        return self

    def canonical_bytes(self):
        return snapshot_canonical_bytes(self.model_dump(mode="json", by_alias=True))

    def digest(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class FogEntryV1(_Evidence):
    schema_version: Literal["fog-patrol-entry/v1"] = Field(alias="schema")
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_id: OpaqueId
    session_id: SessionId
    joined_state_version: Literal[4] = 4
    source_session_id: SessionId
    source_digest: Digest
    logical_npc: Literal[LOGICAL_NPC] = LOGICAL_NPC
    source_npc: Literal[SOURCE_NPC] = SOURCE_NPC
    destination_npc: Literal[DESTINATION_NPC] = DESTINATION_NPC
    scenario_id: Literal["fog_patrol"] = "fog_patrol"
    scenario_content_version: Literal["fog-patrol-1.0.0"] = "fog-patrol-1.0.0"
    content_sha256: Digest
    snapshot: dict[str, Any]
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _binding(self):
        if (self.session_id == self.source_session_id
                or hashlib.sha256(snapshot_canonical_bytes(self.snapshot)).hexdigest() != self.snapshot_sha256
                or self.visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=4).value):
            raise ValueError("invalid fog destination association")
        if len(self.canonical_bytes()) > 1048576:
            raise ValueError("fog entry exceeds storage bound")
        return self

    def canonical_bytes(self):
        return snapshot_canonical_bytes(self.model_dump(mode="json", by_alias=True))

    def digest(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class FogContinuationEvidenceV1(_Evidence):
    schema_version: Literal["run.fog-patrol-evidence/v1"] = Field(alias="schema")
    request: NativeRunContinuationRequestV1
    source_digest: Digest
    destination_entry_digest: Digest
    destination_session_id: SessionId
    destination_creation_request_id: OpaqueId
    destination_initial_event_id: SessionId
    destination_random_seed: int = Field(strict=True, ge=0, le=2**63 - 1)
    resolution_fingerprint: Digest
    occurred_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000000Z$")

    @model_validator(mode="after")
    def _binding(self):
        datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        if (self.request.expected_run_state_version != 3
                or self.destination_session_id == self.request.source_session_id
                or self.destination_creation_request_id != self.request.creation_request_id()):
            raise ValueError("invalid fog continuation request")
        return self


class FogVisitV1(_Evidence):
    run_id: OpaqueId
    continuous_story_line_id: OpaqueId
    visit_id: OpaqueId
    visit_ordinal: Literal[1, 2]
    world_id: Literal[WORLD] = WORLD
    world_version: Literal[1] = 1
    region_id: Literal[SOURCE_REGION, REGION]
    region_version: Literal[1] = 1
    session_id: SessionId
    joined_state_version: Literal[3, 4]
    materialized_state_version: Literal[4] = 4
    operation_id: OpaqueId
    source_reference: OpaqueId
    entered_at: datetime
    created_at: datetime

    @model_validator(mode="after")
    def _binding(self):
        if (self.joined_state_version != self.visit_ordinal + 2
                or self.region_id != (SOURCE_REGION if self.visit_ordinal == 1 else REGION)
                or self.visit_id != derive_world_visit_id(run_id=self.run_id,
                    continuous_story_line_id=self.continuous_story_line_id,
                    session_id=self.session_id, joined_state_version=self.joined_state_version).value):
            raise ValueError("invalid fog visit")
        return self


def continue_fog_run(admission, evidence):
    revalidate_run_model(admission, NativeRunAdmissionV1)
    revalidate_run_model(evidence, FogContinuationEvidenceV1)
    run, request = admission.canonical_run, evidence.request
    time = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    # Native admission has revisions create=1, character bind=2, attach=3.
    # Session choices never append a Run revision. All four endings use this prefix.
    if (run.state_version.value != 3 or run.lifecycle_status is not RunLifecycleStatus.ACTIVE
            or len(run.trusted_participation_references) != 1
            or request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.source_session_id != run.trusted_participation_references[0].session_id
            or time < run.current_mutation_provenance.occurred_at
            or evidence.resolution_fingerprint != admission.protocol_binding.resolved_protocol.fingerprint.value):
        raise ValueError("fog continuation does not bind admission")
    participation = RunSessionParticipationReference(session_id=evidence.destination_session_id,
        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
        joined_state_version=RunStateVersion(value=4), operation_id=request.operation_id(),
        source_reference=RunAuthoritySourceRef(value=request.source_reference))
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=4),
        mutation_kind=RunMutationKind.CONTINUE_NATIVE_RUN, operation_id=request.operation_id(),
        source_reference=participation.source_reference, occurred_at=time)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=4),
        "current_mutation_provenance": provenance,
        "trusted_participation_references": (*run.trusted_participation_references, participation)})


class FogContinuedV1(_Evidence):
    admission: NativeRunAdmissionV1
    canonical_run: CanonicalRun
    continuation_evidence: FogContinuationEvidenceV1
    source_root: FogSourceV1
    entry: FogEntryV1
    visits: tuple[FogVisitV1, FogVisitV1]
    position: WorldPositionV1

    @model_validator(mode="after")
    def _binding(self):
        e, source, entry = self.continuation_evidence, self.source_root, self.entry
        run = continue_fog_run(self.admission, e)
        time = run.current_mutation_provenance.occurred_at
        if (self.canonical_run != run or e.source_digest != source.digest()
                or e.destination_entry_digest != entry.digest() or entry.source_digest != source.digest()
                or entry.source_session_id != source.session_id
                or entry.session_id != e.destination_session_id
                or source.session_id != e.request.source_session_id
                or source.snapshot_state_version != e.request.expected_session_state_version
                or source.snapshot["player"] != entry.snapshot["player"]
                or self.position.visit_id != entry.visit_id or self.position.session_id != entry.session_id
                or self.position.created_at != time):
            raise ValueError("invalid fog family binding")
        for obj in (source, entry, self.position, *self.visits):
            if (obj.run_id != run.run_id.value
                    or obj.continuous_story_line_id != run.continuous_story_line_id.value):
                raise ValueError("crossed fog family")
        for ordinal, (visit, p) in enumerate(zip(self.visits, run.trusted_participation_references), 1):
            if (visit.visit_ordinal != ordinal or visit.session_id != p.session_id
                    or visit.joined_state_version != p.joined_state_version.value
                    or visit.visit_id != (source.first_visit_id if ordinal == 1 else entry.visit_id)
                    or visit.operation_id != e.request.operation_id().value
                    or visit.source_reference != e.request.source_reference
                    or visit.created_at != time
                    or visit.entered_at != (run.creation_provenance.occurred_at if ordinal == 1 else time)):
                raise ValueError("invalid fog visit binding")
        return self


class FogExitEvidenceV1(_Evidence):
    schema_version: Literal["run.fog-patrol-exit-evidence/v1"] = Field(alias="schema")
    request: ContinuedNativeRunExitRequestV1
    scenario_id: Literal["fog_patrol"]
    scenario_content_version: Literal["fog-patrol-1.0.0"]
    ending_id: Literal["fog_patrol.ending.helped", "fog_patrol.ending.bypassed"]
    ending_status: Literal["RESOLVED"]
    session_state_version: Literal[3]
    snapshot_sha256: Digest

    @model_validator(mode="after")
    def _binding(self):
        if self.request.expected_run_state_version != 4 or self.request.expected_session_state_version != self.session_state_version:
            raise ValueError("invalid fog exit request")
        return self


def terminate_fog_run(continued, request, *, occurred_at):
    revalidate_run_model(continued, FogContinuedV1)
    revalidate_run_model(request, ContinuedNativeRunExitRequestV1)
    run = continued.canonical_run
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.session_id != continued.entry.session_id
            or request.expected_run_state_version != 4
            or occurred_at < run.current_mutation_provenance.occurred_at):
        raise ValueError("fog exit does not bind current visit")
    binding = ReservedPlayerCharacterBinding(**{**run.player_character_binding.__dict__,
        "binding_state": "historical", "inactivated_at": occurred_at})
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=5),
        mutation_kind=RunMutationKind.TERMINATE_CONTINUED_NATIVE_RUN,
        operation_id=request.operation_id(), source_reference=RunAuthoritySourceRef(value=request.source_reference),
        occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=5),
        "lifecycle_status": RunLifecycleStatus.TERMINATED, "player_character_binding": binding,
        "current_mutation_provenance": provenance})


class FogTerminatedV1(_Evidence):
    continued: FogContinuedV1
    canonical_run: CanonicalRun
    exit_evidence: FogExitEvidenceV1

    @property
    def admission(self):
        return self.continued.admission

    @model_validator(mode="after")
    def _binding(self):
        if self.canonical_run != terminate_fog_run(self.continued, self.exit_evidence.request,
                occurred_at=self.canonical_run.current_mutation_provenance.occurred_at):
            raise ValueError("invalid fog terminal family")
        return self


def decode_fog(payload, cls):
    if type(payload) is not bytes or not 1 <= len(payload) <= 1048576:
        raise ValueError("invalid fog evidence bytes")
    obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if cls is FogSourceV1 and type(obj) is dict and type(obj.get("events")) is list:
        obj["events"] = tuple(obj["events"])
    value = cls.model_validate(obj, strict=True)
    encoded = value.canonical_bytes() if cls in (FogSourceV1, FogEntryV1) else canonical_run_operation_bytes(value)
    if encoded != payload:
        raise ValueError("noncanonical fog evidence")
    return value


def decode_continuation_evidence(payload):
    """Dispatch by exact schema; never retry another decoder on invalid evidence."""
    if type(payload) is not bytes or not 1 <= len(payload) <= 1048576:
        raise ValueError("invalid continuation evidence bytes")
    obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if type(obj) is dict and obj.get("schema") == "run.fog-patrol-evidence/v1":
        return decode_fog(payload, FogContinuationEvidenceV1)
    from deviation_protocol.domain.world_continuation import decode_native_run_continuation_evidence
    return decode_native_run_continuation_evidence(payload)


def decode_continued_exit_evidence(payload):
    if type(payload) is not bytes or not 1 <= len(payload) <= 1048576:
        raise ValueError("invalid continuation evidence bytes")
    obj = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    if type(obj) is dict and obj.get("schema") == "run.fog-patrol-exit-evidence/v1":
        return decode_fog(payload, FogExitEvidenceV1)
    from deviation_protocol.domain.run_protocol_binding import decode_continued_native_run_exit_evidence
    return decode_continued_native_run_exit_evidence(payload)
