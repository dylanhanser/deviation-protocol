"""Detached stored-family results; neither result authorizes a caller."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunId,
    RunLifecycleStatus,
    RunStateVersion,
    revalidate_run_model,
    validate_canonical_run,
    canonical_run_operation_bytes, RunMutationKind, RunMutationProvenance,
    RunOperationId, RunAuthoritySourceRef, ReservedPlayerCharacterBinding,
    _validate_actual_pydantic_state,
)
from deviation_protocol.domain.run_protocol_resolution import (
    ResolvedRunProtocolObjectivesV1,
)


RUN_PROTOCOL_BINDING_EPOCH = "run-protocol-binding"
RUN_PROTOCOL_BINDING_V1_VERSION = 1
RUN_FAMILY_NATIVE_V1 = "phase_3_3_native"


class LegacyRunCompatibilityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    canonical_run: CanonicalRun
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

    @field_validator("canonical_run", mode="before")
    @classmethod
    def _validate_original_run(cls, value: CanonicalRun) -> CanonicalRun:
        return validate_canonical_run(value)

    @model_validator(mode="after")
    def _validate_association(self) -> LegacyRunCompatibilityV1:
        run = self.canonical_run
        if (
            run.state_version.value != 3
            or run.lifecycle_status is not RunLifecycleStatus.ACTIVE
            or run.player_character_binding is None
            or len(run.trusted_participation_references) != 1
            or run.trusted_participation_references[0].session_id != self.session_id
        ):
            raise ValueError("legacy result requires the exact active entry family")
        return self


class NativeRunProtocolBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    bound_state_version: RunStateVersion
    resolved_protocol: ResolvedRunProtocolObjectivesV1

    @field_validator("run_id", "continuous_story_line_id", "bound_state_version", "resolved_protocol", mode="before")
    @classmethod
    def _validate_original_state(cls, value, info):
        expected = {
            "run_id": RunId,
            "continuous_story_line_id": ContinuousStoryLineId,
            "bound_state_version": RunStateVersion,
            "resolved_protocol": ResolvedRunProtocolObjectivesV1,
        }[info.field_name]
        return revalidate_run_model(value, expected)


from deviation_protocol.domain.entry_world import AuthoredEntryWorldV1


class RunEntryWorldBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    bound_state_version: RunStateVersion
    entry_world: AuthoredEntryWorldV1

    @field_validator("run_id", "continuous_story_line_id", "bound_state_version", "entry_world", mode="before")
    @classmethod
    def _original(cls, value, info):
        expected = {"run_id": RunId, "continuous_story_line_id": ContinuousStoryLineId,
                    "bound_state_version": RunStateVersion, "entry_world": AuthoredEntryWorldV1}[info.field_name]
        return revalidate_run_model(value, expected)

    @model_validator(mode="after")
    def _version(self):
        if self.bound_state_version.value != 3:
            raise ValueError("entry-world binding requires revision three")
        return self


class NativeRunAdmissionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    canonical_run: CanonicalRun
    protocol_binding: NativeRunProtocolBindingV1
    world_binding: RunEntryWorldBindingV1

    @field_validator("canonical_run", "protocol_binding", "world_binding", mode="before")
    @classmethod
    def _original(cls, value, info):
        expected = {"canonical_run": CanonicalRun, "protocol_binding": NativeRunProtocolBindingV1,
                    "world_binding": RunEntryWorldBindingV1}[info.field_name]
        return revalidate_run_model(value, expected)

    @model_validator(mode="after")
    def _association(self):
        run = validate_canonical_run(self.canonical_run)
        if (run.state_version.value != 3 or run.lifecycle_status is not RunLifecycleStatus.ACTIVE
                or run.player_character_binding is None
                or len(run.trusted_participation_references) != 1):
            raise ValueError("native admission requires complete active revision three")
        for binding in (self.protocol_binding, self.world_binding):
            if (binding.run_id != run.run_id
                    or binding.continuous_story_line_id != run.continuous_story_line_id
                    or binding.bound_state_version != run.state_version):
                raise ValueError("native admission binding association")
        return self


_ExitId = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]


class _NativeExitModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always", serialize_by_alias=True)

    @model_validator(mode="wrap")
    @classmethod
    def _original(cls, value, handler):
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError("unexpected exit evidence carrier")
            _validate_actual_pydantic_state(value,path=cls.__name__,visited=set())
            value = dict(value.__dict__)
            value["schema"] = value.pop("schema_version")
        return handler(value)


class NativeRunExitRequestV1(_NativeExitModel):
    schema_version: Literal["run.terminate-native-request/v1"] = Field(alias="schema")
    controller_binding: _ExitId
    player_id: _ExitId
    public_operation_key: _ExitId
    run_id: _ExitId
    continuous_story_line_id: _ExitId
    session_id: Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
    expected_run_state_version: int = Field(strict=True, ge=1, le=2**63 - 1)
    expected_session_state_version: int = Field(strict=True, ge=0, le=2**63 - 1)
    source_reference: _ExitId

    def operation_id(self) -> RunOperationId:
        revalidate_run_model(self, NativeRunExitRequestV1)
        payload = {"schema": "run.terminate-native-operation/v1", "controller_binding": self.controller_binding,
                   "public_operation_key": self.public_operation_key, "run_id": self.run_id}
        return RunOperationId(value=hashlib.sha256(canonical_run_operation_bytes(payload)).hexdigest())

    def fingerprint(self) -> str:
        revalidate_run_model(self, NativeRunExitRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()


class NativeRunExitEvidenceV1(_NativeExitModel):
    schema_version: Literal["run.terminate-native-evidence/v1"] = Field(alias="schema")
    request: NativeRunExitRequestV1
    scenario_id: _ExitId
    scenario_content_version: Annotated[str, Field(strict=True, min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
    ending_id: _ExitId
    ending_status: Literal["RESOLVED", "FAILED"]
    session_state_version: int = Field(strict=True, ge=0, le=2**63 - 1)
    snapshot_sha256: str = Field(strict=True, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _association(self):
        if (self.request.expected_run_state_version != 3
                or self.session_state_version != self.request.expected_session_state_version
                or len(canonical_run_operation_bytes(self)) > 4096):
            raise ValueError("invalid exit evidence association or size")
        return self


def decode_native_run_exit_evidence(payload: bytes) -> NativeRunExitEvidenceV1:
    if type(payload) is not bytes or not 1 <= len(payload) <= 4096:
        raise ValueError("invalid exit evidence bytes")
    # Exact canonical equality also rejects duplicate members, BOM and alternate encodings.
    value = NativeRunExitEvidenceV1.model_validate(json.loads(payload.decode("utf-8")), strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical exit evidence")
    return value


def terminate_native_run(admission: NativeRunAdmissionV1, request: NativeRunExitRequestV1,
                         *, occurred_at: datetime) -> CanonicalRun:
    revalidate_run_model(admission, NativeRunAdmissionV1)
    revalidate_run_model(request, NativeRunExitRequestV1)
    run = admission.canonical_run
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.session_id != run.trusted_participation_references[0].session_id
            or request.expected_run_state_version != 3
            or occurred_at < run.current_mutation_provenance.occurred_at):
        raise ValueError("exit request does not bind admission")
    binding = ReservedPlayerCharacterBinding(**{
        **run.player_character_binding.__dict__, "binding_state": "historical", "inactivated_at": occurred_at})
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=4),
        mutation_kind=RunMutationKind.TERMINATE_NATIVE_RUN, operation_id=request.operation_id(),
        source_reference=RunAuthoritySourceRef(value=request.source_reference), occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=4),
        "lifecycle_status": RunLifecycleStatus.TERMINATED, "player_character_binding": binding,
        "current_mutation_provenance": provenance})


class NativeRunTerminatedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    admission: NativeRunAdmissionV1
    canonical_run: CanonicalRun
    exit_evidence: NativeRunExitEvidenceV1

    @model_validator(mode="after")
    def _association(self):
        revalidate_run_model(self.admission, NativeRunAdmissionV1)
        revalidate_run_model(self.exit_evidence, NativeRunExitEvidenceV1)
        validate_canonical_run(self.canonical_run)
        expected = terminate_native_run(self.admission, self.exit_evidence.request,
            occurred_at=self.canonical_run.current_mutation_provenance.occurred_at)
        world = self.admission.world_binding.entry_world
        if (expected != self.canonical_run
                or (self.exit_evidence.scenario_id, self.exit_evidence.scenario_content_version)
                != (world.scenario_id, world.scenario_content_version)):
            raise ValueError("invalid terminal family association")
        return self


from deviation_protocol.domain.world_continuation import (
    NativeRunContinuationEvidenceV1, NativeRunContinuationRequestV1,
    WorldStateRootV1, WorldVisitV1, WorldPositionV1,
)
from deviation_protocol.domain.run import RunSessionParticipationReference


def continue_native_run(admission: NativeRunAdmissionV1,
                        evidence: NativeRunContinuationEvidenceV1) -> CanonicalRun:
    revalidate_run_model(admission, NativeRunAdmissionV1)
    revalidate_run_model(evidence, NativeRunContinuationEvidenceV1)
    run, request = admission.canonical_run, evidence.request
    occurred_at = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.source_session_id != run.trusted_participation_references[0].session_id
            or occurred_at < run.current_mutation_provenance.occurred_at
            or evidence.selection_inputs.resolution_fingerprint != admission.protocol_binding.resolved_protocol.fingerprint.value):
        raise ValueError("continuation does not bind admission")
    participation = RunSessionParticipationReference(session_id=evidence.destination_session_id,
        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
        joined_state_version=RunStateVersion(value=4), operation_id=request.operation_id(),
        source_reference=RunAuthoritySourceRef(value=request.source_reference))
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=4),
        mutation_kind=RunMutationKind.CONTINUE_NATIVE_RUN, operation_id=request.operation_id(),
        source_reference=participation.source_reference, occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=4),
        "current_mutation_provenance": provenance,
        "trusted_participation_references": (*run.trusted_participation_references, participation)})


class NativeRunContinuedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    admission: NativeRunAdmissionV1
    canonical_run: CanonicalRun
    continuation_evidence: NativeRunContinuationEvidenceV1
    source_root: WorldStateRootV1
    destination_root: WorldStateRootV1
    visits: tuple[WorldVisitV1, WorldVisitV1]
    position: WorldPositionV1

    @model_validator(mode="after")
    def _association(self):
        for obj in (self.admission, self.canonical_run, self.continuation_evidence,
                    self.source_root, self.destination_root, *self.visits, self.position):
            revalidate_run_model(obj, type(obj))
        evidence = self.continuation_evidence
        expected = continue_native_run(self.admission, evidence)
        time = expected.current_mutation_provenance.occurred_at
        if (self.canonical_run != expected
                or self.source_root.digest() != evidence.source_world_state_sha256
                or self.destination_root.digest() != evidence.destination_world_state_sha256
                or self.source_root.snapshot_sha256 != evidence.source_ending.snapshot_sha256
                or self.source_root.snapshot_state_version != evidence.source_ending.session_state_version
                or self.source_root.snapshot["player"] != self.destination_root.snapshot["player"]
                or self.position.run_id != expected.run_id.value
                or self.position.continuous_story_line_id != expected.continuous_story_line_id.value
                or self.position.visit_id != evidence.destination_visit_id
                or self.position.session_id != evidence.destination_session_id
                or self.position.created_at != time):
            raise ValueError("invalid continued Run family")
        for ordinal, (visit, root, participation) in enumerate(zip(
                self.visits, (self.source_root, self.destination_root),
                expected.trusted_participation_references), 1):
            if (visit.visit_ordinal != ordinal
                    or visit.run_id != root.run_id or visit.run_id != expected.run_id.value
                    or visit.continuous_story_line_id != root.continuous_story_line_id
                    or visit.continuous_story_line_id != expected.continuous_story_line_id.value
                    or visit.visit_id != root.first_visit_id
                    or visit.session_id != root.session_id or visit.session_id != participation.session_id
                    or (visit.world_id, visit.world_version) != (root.world.world_id, root.world.world_version)
                    or (visit.region_id, visit.region_version) != (root.region.region_id, root.region.region_version)
                    or visit.joined_state_version != participation.joined_state_version.value
                    or visit.created_at != time
                    or visit.entered_at != (expected.creation_provenance.occurred_at if ordinal == 1 else time)
                    or visit.operation_id != evidence.request.operation_id().value
                    or visit.source_reference != evidence.request.source_reference):
                raise ValueError("invalid continued visit/root association")
        return self


class ContinuedNativeRunExitRequestV1(NativeRunExitRequestV1):
    schema_version: Literal["run.terminate-continued-native-request/v1"] = Field(alias="schema")

    def operation_id(self) -> RunOperationId:
        revalidate_run_model(self, ContinuedNativeRunExitRequestV1)
        payload = {"schema": "run.terminate-continued-native-operation/v1",
                   "controller_binding": self.controller_binding,
                   "public_operation_key": self.public_operation_key, "run_id": self.run_id}
        return RunOperationId(value=hashlib.sha256(canonical_run_operation_bytes(payload)).hexdigest())

    def fingerprint(self) -> str:
        revalidate_run_model(self, ContinuedNativeRunExitRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()


class ContinuedNativeRunExitEvidenceV1(_NativeExitModel):
    schema_version: Literal["run.terminate-continued-native-evidence/v1"] = Field(alias="schema")
    request: ContinuedNativeRunExitRequestV1
    scenario_id: Literal["undelivered_receipt"]
    scenario_content_version: Literal["undelivered-receipt-1.0.0"]
    ending_id: _ExitId
    ending_status: Literal["RESOLVED", "FAILED"]
    session_state_version: int = Field(strict=True, ge=0, le=2**63 - 1)
    snapshot_sha256: str = Field(strict=True, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _association(self):
        if (self.request.expected_run_state_version != 4
                or self.session_state_version != self.request.expected_session_state_version
                or len(canonical_run_operation_bytes(self)) > 4096):
            raise ValueError("invalid continued exit evidence")
        return self


def decode_continued_native_run_exit_evidence(payload: bytes) -> ContinuedNativeRunExitEvidenceV1:
    if type(payload) is not bytes or not 1 <= len(payload) <= 4096:
        raise ValueError("invalid continued exit evidence bytes")
    value = ContinuedNativeRunExitEvidenceV1.model_validate(json.loads(payload.decode("utf-8")), strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical continued exit evidence")
    return value


def terminate_continued_native_run(continued: NativeRunContinuedV1,
        request: ContinuedNativeRunExitRequestV1, *, occurred_at: datetime) -> CanonicalRun:
    revalidate_run_model(continued, NativeRunContinuedV1)
    revalidate_run_model(request, ContinuedNativeRunExitRequestV1)
    run = continued.canonical_run
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.session_id != run.trusted_participation_references[1].session_id
            or request.expected_run_state_version != 4
            or occurred_at < run.current_mutation_provenance.occurred_at):
        raise ValueError("continued exit does not bind current visit")
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


class NativeRunContinuedTerminatedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")
    continued: NativeRunContinuedV1
    canonical_run: CanonicalRun
    exit_evidence: ContinuedNativeRunExitEvidenceV1

    @property
    def admission(self):
        return self.continued.admission

    @model_validator(mode="after")
    def _association(self):
        revalidate_run_model(self.continued, NativeRunContinuedV1)
        revalidate_run_model(self.exit_evidence, ContinuedNativeRunExitEvidenceV1)
        validate_canonical_run(self.canonical_run)
        if self.canonical_run != terminate_continued_native_run(self.continued,
                self.exit_evidence.request,
                occurred_at=self.canonical_run.current_mutation_provenance.occurred_at):
            raise ValueError("invalid continued terminal family")
        return self


from deviation_protocol.domain.world_revisit import (
    NativeRunRegionalRevisitEvidenceV1, RegionalEntryV1, WorldVisitV2,
    WorldPositionV2, ARCHIVE_ENDINGS, _decode_object,
)


def revisit_native_region(continued: NativeRunContinuedV1,
                         evidence: NativeRunRegionalRevisitEvidenceV1) -> CanonicalRun:
    revalidate_run_model(continued, NativeRunContinuedV1)
    revalidate_run_model(evidence, NativeRunRegionalRevisitEvidenceV1)
    run, request = continued.canonical_run, evidence.request
    occurred_at = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.source_session_id != run.trusted_participation_references[1].session_id
            or occurred_at < run.current_mutation_provenance.occurred_at
            or evidence.selection_inputs.resolution_fingerprint != continued.admission.protocol_binding.resolved_protocol.fingerprint.value):
        raise ValueError("regional transition does not bind continued prefix")
    for selected, visit in zip(evidence.selection_inputs.visits, continued.visits):
        if ((selected.visit_id, selected.visit_ordinal, selected.session_id,
             selected.world.world_id, selected.world.world_version,
             selected.region.region_id, selected.region.region_version)
                != (visit.visit_id, visit.visit_ordinal, visit.session_id, visit.world_id,
                    visit.world_version, visit.region_id, visit.region_version)):
            raise ValueError("regional selection changed prior visit")
    participation = RunSessionParticipationReference(session_id=evidence.destination_session_id,
        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
        joined_state_version=RunStateVersion(value=5), operation_id=request.operation_id(),
        source_reference=RunAuthoritySourceRef(value=request.source_reference))
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=5),
        mutation_kind=RunMutationKind.REVISIT_NATIVE_REGION, operation_id=request.operation_id(),
        source_reference=participation.source_reference, occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=5),
        "current_mutation_provenance": provenance,
        "trusted_participation_references": (*run.trusted_participation_references, participation)})


class NativeRunRegionalRevisitV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")
    continued: NativeRunContinuedV1
    canonical_run: CanonicalRun
    revisit_evidence: NativeRunRegionalRevisitEvidenceV1
    entry: RegionalEntryV1
    visit: WorldVisitV2
    position: WorldPositionV2

    @property
    def admission(self):
        return self.continued.admission

    @model_validator(mode="after")
    def _association(self):
        for obj in (self.continued, self.canonical_run, self.revisit_evidence,
                    self.entry, self.visit, self.position):
            revalidate_run_model(obj, type(obj))
        evidence, entry, visit, position = self.revisit_evidence, self.entry, self.visit, self.position
        expected = revisit_native_region(self.continued, evidence)
        request = evidence.request
        time = expected.current_mutation_provenance.occurred_at
        if (self.canonical_run != expected or entry.digest() != evidence.destination_entry_sha256
                or entry.base_snapshot_sha256 != evidence.world_base_snapshot_sha256
                or entry.base_session_state_version != evidence.source_ending.session_state_version
                or entry.base_session_id != request.source_session_id
                or entry.base_visit_id != evidence.source_visit_id
                or entry.content_sha256 != evidence.selection_inputs.eligible_pool[0].content_sha256
                or visit.operation_id != request.operation_id().value
                or visit.source_reference != request.source_reference
                or visit.entered_at != time or visit.created_at != time
                or position.created_at != self.continued.position.created_at):
            raise ValueError("invalid regional family association")
        for obj in (entry, visit, position):
            if (obj.run_id != expected.run_id.value
                    or obj.continuous_story_line_id != expected.continuous_story_line_id.value
                    or obj.visit_id != evidence.destination_visit_id
                    or obj.session_id != evidence.destination_session_id):
                raise ValueError("crossed regional family member")
        return self


class RevisitedNativeRunExitRequestV1(NativeRunExitRequestV1):
    schema_version: Literal["run.terminate-revisited-native-request/v1"] = Field(alias="schema")

    def operation_id(self) -> RunOperationId:
        revalidate_run_model(self, RevisitedNativeRunExitRequestV1)
        return RunOperationId(value=hashlib.sha256(canonical_run_operation_bytes({
            "schema": "run.terminate-revisited-native-operation/v1",
            "controller_binding": self.controller_binding,
            "public_operation_key": self.public_operation_key, "run_id": self.run_id})).hexdigest())

    def fingerprint(self) -> str:
        revalidate_run_model(self, RevisitedNativeRunExitRequestV1)
        return hashlib.sha256(canonical_run_operation_bytes(self)).hexdigest()


class RevisitedNativeRunExitEvidenceV1(_NativeExitModel):
    schema_version: Literal["run.terminate-revisited-native-evidence/v1"] = Field(alias="schema")
    request: RevisitedNativeRunExitRequestV1
    scenario_id: Literal["receipt_archive"]
    scenario_content_version: Literal["receipt-archive-1.0.0"]
    ending_id: _ExitId
    ending_status: Literal["RESOLVED", "FAILED"]
    session_state_version: int = Field(strict=True, ge=0, le=2**63 - 1)
    snapshot_sha256: str = Field(strict=True, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _association(self):
        if (self.request.expected_run_state_version != 5
                or self.session_state_version != self.request.expected_session_state_version
                or (self.ending_id, self.ending_status) not in ARCHIVE_ENDINGS
                or len(canonical_run_operation_bytes(self)) > 4096):
            raise ValueError("invalid regional exit evidence")
        return self


def decode_revisited_native_run_exit_evidence(payload: bytes) -> RevisitedNativeRunExitEvidenceV1:
    value = RevisitedNativeRunExitEvidenceV1.model_validate(_decode_object(payload, 4096), strict=True)
    if canonical_run_operation_bytes(value) != payload:
        raise ValueError("noncanonical regional exit evidence")
    return value


def terminate_revisited_native_run(revisited: NativeRunRegionalRevisitV1,
        request: RevisitedNativeRunExitRequestV1, *, occurred_at: datetime) -> CanonicalRun:
    revalidate_run_model(revisited, NativeRunRegionalRevisitV1)
    revalidate_run_model(request, RevisitedNativeRunExitRequestV1)
    run = revisited.canonical_run
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.session_id != run.trusted_participation_references[2].session_id
            or request.expected_run_state_version != 5
            or occurred_at < run.current_mutation_provenance.occurred_at):
        raise ValueError("regional exit does not bind current visit")
    binding = ReservedPlayerCharacterBinding(**{**run.player_character_binding.__dict__,
        "binding_state": "historical", "inactivated_at": occurred_at})
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=6),
        mutation_kind=RunMutationKind.TERMINATE_REVISITED_NATIVE_RUN,
        operation_id=request.operation_id(), source_reference=RunAuthoritySourceRef(value=request.source_reference),
        occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=6),
        "lifecycle_status": RunLifecycleStatus.TERMINATED, "player_character_binding": binding,
        "current_mutation_provenance": provenance})


class NativeRunRegionalRevisitTerminatedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")
    revisited: NativeRunRegionalRevisitV1
    canonical_run: CanonicalRun
    exit_evidence: RevisitedNativeRunExitEvidenceV1

    @property
    def admission(self):
        return self.revisited.admission

    @model_validator(mode="after")
    def _association(self):
        revalidate_run_model(self.revisited, NativeRunRegionalRevisitV1)
        revalidate_run_model(self.exit_evidence, RevisitedNativeRunExitEvidenceV1)
        validate_canonical_run(self.canonical_run)
        if self.canonical_run != terminate_revisited_native_run(self.revisited,
                self.exit_evidence.request,
                occurred_at=self.canonical_run.current_mutation_provenance.occurred_at):
            raise ValueError("invalid regional terminal family")
        return self


from deviation_protocol.domain.run_completion import NativeRunCompletionEvidenceV1


def complete_revisited_native_run(revisited: NativeRunRegionalRevisitV1,
        evidence: NativeRunCompletionEvidenceV1, *, occurred_at: datetime) -> CanonicalRun:
    revalidate_run_model(revisited, NativeRunRegionalRevisitV1)
    revalidate_run_model(evidence, NativeRunCompletionEvidenceV1)
    run, request = revisited.canonical_run, evidence.request
    if (request.run_id != run.run_id.value
            or request.continuous_story_line_id != run.continuous_story_line_id.value
            or request.source_session_id != revisited.visit.session_id
            or occurred_at != datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
            or occurred_at < run.current_mutation_provenance.occurred_at):
        raise ValueError("completion does not bind the regional prefix")
    for source, visit in zip(evidence.sources, (*revisited.continued.visits, revisited.visit)):
        if ((source.visit_id, source.visit_ordinal, source.session_id,
             source.world.world_id, source.world.world_version,
             source.region.region_id, source.region.region_version)
                != (visit.visit_id, visit.visit_ordinal, visit.session_id,
                    visit.world_id, visit.world_version, visit.region_id, visit.region_version)):
            raise ValueError("completion changes a prior visit")
    if (evidence.sources[0].snapshot_sha256 != revisited.continued.source_root.snapshot_sha256
            or evidence.sources[1].snapshot_sha256 != revisited.entry.base_snapshot_sha256):
        raise ValueError("completion changes a frozen source snapshot")
    binding = ReservedPlayerCharacterBinding(**{**run.player_character_binding.__dict__,
        "binding_state": "historical", "inactivated_at": occurred_at})
    provenance = RunMutationProvenance(target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version, resulting_state_version=RunStateVersion(value=6),
        mutation_kind=RunMutationKind.COMPLETE_REVISITED_NATIVE_RUN,
        operation_id=request.operation_id(), source_reference=RunAuthoritySourceRef(value=request.source_reference),
        occurred_at=occurred_at)
    return CanonicalRun(**{**run.__dict__, "state_version": RunStateVersion(value=6),
        "lifecycle_status": RunLifecycleStatus.COMPLETED, "player_character_binding": binding,
        "current_mutation_provenance": provenance})


class NativeRunRegionalCompletedV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")
    revisited: NativeRunRegionalRevisitV1
    canonical_run: CanonicalRun
    completion_evidence: NativeRunCompletionEvidenceV1

    @property
    def admission(self):
        return self.revisited.admission

    @model_validator(mode="after")
    def _association(self):
        validate_canonical_run(self.canonical_run)
        if self.canonical_run != complete_revisited_native_run(self.revisited, self.completion_evidence,
                occurred_at=self.canonical_run.current_mutation_provenance.occurred_at):
            raise ValueError("invalid completed regional family")
        return self


_ClassifiedRun = (LegacyRunCompatibilityV1 | NativeRunProtocolBindingV1 | NativeRunAdmissionV1
                 | NativeRunTerminatedV1 | NativeRunContinuedV1 | NativeRunContinuedTerminatedV1
                 | NativeRunRegionalRevisitV1 | NativeRunRegionalRevisitTerminatedV1 | NativeRunRegionalCompletedV1)
