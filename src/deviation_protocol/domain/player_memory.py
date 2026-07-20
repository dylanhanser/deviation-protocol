from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from enum import StrEnum
import hashlib
import json
from typing import Annotated, Literal, Mapping, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import PersistedEventReceipt

if TYPE_CHECKING:
    from deviation_protocol.domain.scenario import ScenarioDefinition


MEMORY_MODEL_VERSION = 2
MAX_DEFERRED_MEMORY_EVENTS = 1_000_000
MAX_SCENARIO_MEMORY_RECORDS = 64
MAX_NPC_MEMORY_RECORDS = 256
MAX_SIGNIFICANT_EXPERIENCES = 256
MAX_KNOWN_PUBLIC_FACTS = 512
MAX_MEMORY_REFS_PER_RECORD = 32

MemorySequence = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
MemoryIndexSequence = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
MemoryStateVersion = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
Fingerprint = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
StableMemoryId = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
_DEFINITION_ID_ADAPTER = TypeAdapter(DefinitionId)
_STABLE_MEMORY_ID_ADAPTER = TypeAdapter(StableMemoryId)


class MemoryCapacityError(ValueError):
    """A bounded memory index cannot accept another distinct record."""


class MemoryConflictError(ValueError):
    """A memory update conflicts with already confirmed authority."""


class MemoryAuthorityEventType(StrEnum):
    """Closed future server event vocabulary; Phase 2.3a does not emit these."""

    SCENARIO_STARTED = "PlayerMemoryScenarioStarted"
    SCENARIO_COMPLETED = "PlayerMemoryScenarioCompleted"
    NPC_ENCOUNTER_CONFIRMED = "PlayerMemoryNpcEncounterConfirmed"
    NPC_MILESTONE_CONFIRMED = "PlayerMemoryNpcMilestoneConfirmed"
    PUBLIC_FACT_CONFIRMED = "PlayerMemoryPublicFactConfirmed"
    SIGNIFICANT_EXPERIENCE_CONFIRMED = "PlayerMemorySignificantExperienceConfirmed"


class MemoryIndexSyncStatus(StrEnum):
    CURRENT = "CURRENT"
    REBUILD_REQUIRED = "REBUILD_REQUIRED"


_MEMORY_AUTHORITY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class _MemoryAuthoritySeal:
    target: object
    issuer: object
    digest: str


@dataclass(frozen=True, slots=True, init=False)
class MemoryAuthoritySource:
    """Opaque server-internal event authority; it is not persistence proof."""

    event_id: str
    session_id: str
    sequence_no: int
    event_type: MemoryAuthorityEventType
    _seal: _MemoryAuthoritySeal

    def __copy__(self) -> MemoryAuthoritySource:
        return self

    def is_authentic(self) -> bool:
        try:
            seal = self._seal
            return (
                seal.target is self
                and seal.issuer is _MEMORY_AUTHORITY_ISSUER
                and seal.digest == _memory_authority_digest(self)
            )
        except (AttributeError, TypeError, ValueError):
            return False


def _issue_memory_authority_source(event: DomainEvent) -> MemoryAuthoritySource:
    """Test/future adapter seam; Phase 2.3a never calls it from production."""

    if not isinstance(event, DomainEvent):
        raise TypeError("memory authority requires a server domain event envelope")
    try:
        event_type = MemoryAuthorityEventType(event.event_type)
    except (TypeError, ValueError) as exc:
        raise ValueError("domain event type is not a memory authority event") from exc
    if type(event.sequence_no) is not int or event.sequence_no < 1:
        raise ValueError("memory authority sequence must be a positive integer")
    source = object.__new__(MemoryAuthoritySource)
    object.__setattr__(source, "event_id", event.event_id)
    object.__setattr__(source, "session_id", event.session_id)
    object.__setattr__(source, "sequence_no", event.sequence_no)
    object.__setattr__(source, "event_type", event_type)
    object.__setattr__(
        source,
        "_seal",
        _MemoryAuthoritySeal(
            target=source,
            issuer=_MEMORY_AUTHORITY_ISSUER,
            digest=_memory_authority_digest(source),
        ),
    )
    return source


def _issue_memory_authority_source_from_receipt(
    receipt: PersistedEventReceipt,
    *,
    memory_event_type: MemoryAuthorityEventType,
) -> MemoryAuthoritySource:
    if not isinstance(receipt, PersistedEventReceipt) or not receipt.is_authentic():
        raise ValueError("memory authority requires a flushed persisted-event receipt")
    source = object.__new__(MemoryAuthoritySource)
    object.__setattr__(source, "event_id", receipt.event_id)
    object.__setattr__(source, "session_id", receipt.session_id)
    object.__setattr__(source, "sequence_no", receipt.sequence_no)
    object.__setattr__(source, "event_type", memory_event_type)
    object.__setattr__(
        source,
        "_seal",
        _MemoryAuthoritySeal(
            target=source,
            issuer=_MEMORY_AUTHORITY_ISSUER,
            digest=_memory_authority_digest(source),
        ),
    )
    return source


class MemoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScenarioMemoryStatus(StrEnum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"


class ScenarioMemoryMilestone(StrEnum):
    STARTED = "STARTED"
    IMPORTANT_FACT_CONFIRMED = "IMPORTANT_FACT_CONFIRMED"
    COMPLETED = "COMPLETED"
    ENDING_CONFIRMED = "ENDING_CONFIRMED"


class NpcInteractionMilestone(StrEnum):
    FIRST_ENCOUNTER = "FIRST_ENCOUNTER"
    COOPERATED = "COOPERATED"
    CONFLICT_OCCURRED = "CONFLICT_OCCURRED"
    ASSISTED_PLAYER = "ASSISTED_PLAYER"
    TRUST_CONFIRMED = "TRUST_CONFIRMED"


class SignificantExperienceCategory(StrEnum):
    SCENARIO_BEGIN = "SCENARIO_BEGIN"
    SCENARIO_COMPLETION = "SCENARIO_COMPLETION"
    IMPORTANT_NPC_ENCOUNTER = "IMPORTANT_NPC_ENCOUNTER"
    NPC_RELATIONSHIP_MILESTONE = "NPC_RELATIONSHIP_MILESTONE"
    IMPORTANT_PUBLIC_DISCOVERY = "IMPORTANT_PUBLIC_DISCOVERY"


class SignificantExperienceSummary(StrEnum):
    SCENARIO_BEGAN = "SCENARIO_BEGAN"
    SCENARIO_RESOLVED = "SCENARIO_RESOLVED"
    IMPORTANT_NPC_MET = "IMPORTANT_NPC_MET"
    NPC_RELATIONSHIP_CHANGED = "NPC_RELATIONSHIP_CHANGED"
    CRITICAL_PUBLIC_FACT_LEARNED = "CRITICAL_PUBLIC_FACT_LEARNED"


_EXPERIENCE_SUMMARIES = {
    SignificantExperienceCategory.SCENARIO_BEGIN:
        SignificantExperienceSummary.SCENARIO_BEGAN,
    SignificantExperienceCategory.SCENARIO_COMPLETION:
        SignificantExperienceSummary.SCENARIO_RESOLVED,
    SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER:
        SignificantExperienceSummary.IMPORTANT_NPC_MET,
    SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE:
        SignificantExperienceSummary.NPC_RELATIONSHIP_CHANGED,
    SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY:
        SignificantExperienceSummary.CRITICAL_PUBLIC_FACT_LEARNED,
}


class ScenarioMemoryRecord(MemoryModel):
    scenario_id: DefinitionId
    scenario_content_version: DefinitionId
    status: ScenarioMemoryStatus
    ending_id: DefinitionId | None = None
    milestone_refs: Annotated[
        tuple[ScenarioMemoryMilestone, ...],
        Field(max_length=MAX_MEMORY_REFS_PER_RECORD),
    ] = ()
    known_public_fact_refs: Annotated[
        tuple[StableMemoryId, ...],
        Field(max_length=MAX_MEMORY_REFS_PER_RECORD),
    ] = ()
    last_source_event_id: StableMemoryId
    last_source_sequence_no: MemorySequence

    @model_validator(mode="after")
    def validate_record(self) -> ScenarioMemoryRecord:
        milestones = tuple(sorted(self.milestone_refs, key=str))
        facts = tuple(sorted(self.known_public_fact_refs))
        if len(milestones) != len(set(milestones)):
            raise ValueError("scenario memory repeats a milestone")
        if len(facts) != len(set(facts)):
            raise ValueError("scenario memory repeats a public fact reference")
        if self.status is ScenarioMemoryStatus.STARTED and self.ending_id is not None:
            raise ValueError("started scenario memory cannot contain an ending")
        if self.status is ScenarioMemoryStatus.COMPLETED and self.ending_id is None:
            raise ValueError("completed scenario memory requires a confirmed ending")
        object.__setattr__(self, "milestone_refs", milestones)
        object.__setattr__(self, "known_public_fact_refs", facts)
        return self


class NpcMemoryRecord(MemoryModel):
    subject_key: StableMemoryId
    scenario_id: DefinitionId
    npc_definition_id: DefinitionId
    encountered: Literal[True] = True
    interaction_milestones: Annotated[
        tuple[NpcInteractionMilestone, ...],
        Field(max_length=MAX_MEMORY_REFS_PER_RECORD),
    ] = ()
    known_public_fact_refs: Annotated[
        tuple[StableMemoryId, ...],
        Field(max_length=MAX_MEMORY_REFS_PER_RECORD),
    ] = ()
    last_source_event_id: StableMemoryId
    last_source_sequence_no: MemorySequence

    @model_validator(mode="after")
    def validate_record(self) -> NpcMemoryRecord:
        expected = stable_npc_subject_key(self.scenario_id, self.npc_definition_id)
        if self.subject_key != expected:
            raise ValueError("NPC memory subject key does not match stable identity")
        milestones = tuple(sorted(self.interaction_milestones, key=str))
        facts = tuple(sorted(self.known_public_fact_refs))
        if len(milestones) != len(set(milestones)):
            raise ValueError("NPC memory repeats an interaction milestone")
        if len(facts) != len(set(facts)):
            raise ValueError("NPC memory repeats a public fact reference")
        object.__setattr__(self, "interaction_milestones", milestones)
        object.__setattr__(self, "known_public_fact_refs", facts)
        return self


class KnownPublicFactRecord(MemoryModel):
    fact_ref: StableMemoryId
    scenario_id: DefinitionId
    source_event_id: StableMemoryId
    source_sequence_no: MemorySequence


class SignificantExperienceEntry(MemoryModel):
    entry_id: StableMemoryId
    scenario_id: DefinitionId
    category: SignificantExperienceCategory
    summary: SignificantExperienceSummary
    subject_refs: Annotated[
        tuple[StableMemoryId, ...], Field(max_length=8)
    ] = ()
    public_fact_refs: Annotated[
        tuple[StableMemoryId, ...], Field(max_length=8)
    ] = ()
    source_event_id: StableMemoryId
    source_sequence_no: MemorySequence

    @model_validator(mode="after")
    def validate_entry(self) -> SignificantExperienceEntry:
        if self.summary is not _EXPERIENCE_SUMMARIES[self.category]:
            raise ValueError("experience summary does not match its closed category")
        subjects = tuple(sorted(self.subject_refs))
        facts = tuple(sorted(self.public_fact_refs))
        if len(subjects) != len(set(subjects)) or len(facts) != len(set(facts)):
            raise ValueError("significant experience repeats a reference")
        if self.category in {
            SignificantExperienceCategory.SCENARIO_BEGIN,
        } and (subjects or facts):
            raise ValueError("scenario-begin experience cannot contain references")
        if self.category is SignificantExperienceCategory.SCENARIO_COMPLETION and (
            len(subjects) != 1 or facts
        ):
            raise ValueError(
                "scenario-completion experience requires one ending reference"
            )
        if self.category in {
            SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
            SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
        } and (len(subjects) != 1 or facts):
            raise ValueError("NPC experience requires one subject reference")
        if self.category is SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY and (
            subjects or len(facts) != 1
        ):
            raise ValueError("public-discovery experience requires one fact reference")
        expected_id = stable_significant_experience_id(
            source_event_id=self.source_event_id,
            scenario_id=self.scenario_id,
            category=self.category,
            subject_refs=subjects,
            public_fact_refs=facts,
        )
        if self.entry_id != expected_id:
            raise ValueError(
                "significant experience ID does not match its bound content"
            )
        object.__setattr__(self, "subject_refs", subjects)
        object.__setattr__(self, "public_fact_refs", facts)
        return self


class PlayerMemoryState(MemoryModel):
    """Bounded long-term index; never a replacement for current authoritative state."""

    memory_model_version: Annotated[int, Field(strict=True)] = MEMORY_MODEL_VERSION
    sync_status: MemoryIndexSyncStatus = MemoryIndexSyncStatus.CURRENT
    last_applied_source_sequence_no: MemoryIndexSequence = 0
    last_applied_source_event_id: StableMemoryId | None = None
    first_deferred_source_sequence_no: MemorySequence | None = None
    last_deferred_source_sequence_no: MemorySequence | None = None
    deferred_event_count: Annotated[
        int, Field(strict=True, ge=0, le=MAX_DEFERRED_MEMORY_EVENTS)
    ] = 0
    scenario_records: Annotated[
        tuple[ScenarioMemoryRecord, ...], Field(max_length=MAX_SCENARIO_MEMORY_RECORDS)
    ] = ()
    npc_records: Annotated[
        tuple[NpcMemoryRecord, ...], Field(max_length=MAX_NPC_MEMORY_RECORDS)
    ] = ()
    significant_experiences: Annotated[
        tuple[SignificantExperienceEntry, ...],
        Field(max_length=MAX_SIGNIFICANT_EXPERIENCES),
    ] = ()
    known_public_facts: Annotated[
        tuple[KnownPublicFactRecord, ...], Field(max_length=MAX_KNOWN_PUBLIC_FACTS)
    ] = ()

    @model_validator(mode="after")
    def validate_memory(self) -> PlayerMemoryState:
        if self.memory_model_version != MEMORY_MODEL_VERSION:
            raise ValueError("unsupported player memory model version")
        if self.sync_status is MemoryIndexSyncStatus.CURRENT:
            if any(
                value is not None
                for value in (
                    self.first_deferred_source_sequence_no,
                    self.last_deferred_source_sequence_no,
                )
            ) or self.deferred_event_count != 0:
                raise ValueError("current memory index cannot contain deferred markers")
        else:
            if (
                self.first_deferred_source_sequence_no is None
                or self.last_deferred_source_sequence_no is None
                or self.deferred_event_count < 1
                or self.first_deferred_source_sequence_no
                > self.last_deferred_source_sequence_no
                or self.first_deferred_source_sequence_no
                <= self.last_applied_source_sequence_no
            ):
                raise ValueError("rebuild-required memory has invalid deferred markers")
        groups = (
            ("scenario", self.scenario_records, lambda item: item.scenario_id),
            ("NPC", self.npc_records, lambda item: item.subject_key),
            ("experience", self.significant_experiences, lambda item: item.entry_id),
            (
                "public fact",
                self.known_public_facts,
                lambda item: (item.scenario_id, item.fact_ref),
            ),
        )
        for label, records, key in groups:
            keys = tuple(key(item) for item in records)
            if len(keys) != len(set(keys)):
                raise ValueError(f"player memory repeats a {label} record")
        scenario_ids = {item.scenario_id for item in self.scenario_records}
        related_scenario_ids = {
            *(item.scenario_id for item in self.npc_records),
            *(item.scenario_id for item in self.significant_experiences),
            *(item.scenario_id for item in self.known_public_facts),
        }
        if not related_scenario_ids <= scenario_ids:
            raise ValueError("player memory contains an orphan scenario reference")
        scenario_fact_pairs = {
            (record.scenario_id, fact_ref)
            for record in self.scenario_records
            for fact_ref in record.known_public_fact_refs
        }
        indexed_fact_pairs = {
            (record.scenario_id, record.fact_ref)
            for record in self.known_public_facts
        }
        if scenario_fact_pairs != indexed_fact_pairs:
            raise ValueError(
                "scenario and public-fact memory indexes do not match"
            )
        experience_sources = tuple(
            item.source_event_id for item in self.significant_experiences
        )
        if len(experience_sources) != len(set(experience_sources)):
            raise ValueError("player memory repeats an experience source event")
        source_sequences = (
            *(item.last_source_sequence_no for item in self.scenario_records),
            *(item.last_source_sequence_no for item in self.npc_records),
            *(item.source_sequence_no for item in self.significant_experiences),
            *(item.source_sequence_no for item in self.known_public_facts),
        )
        if self.last_applied_source_sequence_no != max(source_sequences, default=0):
            raise ValueError(
                "player memory ordering marker does not match its newest record"
            )
        newest_event_ids = {
            *(
                item.last_source_event_id
                for item in self.scenario_records
                if item.last_source_sequence_no
                == self.last_applied_source_sequence_no
            ),
            *(
                item.last_source_event_id
                for item in self.npc_records
                if item.last_source_sequence_no
                == self.last_applied_source_sequence_no
            ),
            *(
                item.source_event_id
                for item in self.significant_experiences
                if item.source_sequence_no
                == self.last_applied_source_sequence_no
            ),
            *(
                item.source_event_id
                for item in self.known_public_facts
                if item.source_sequence_no
                == self.last_applied_source_sequence_no
            ),
        }
        if self.last_applied_source_sequence_no == 0:
            if self.last_applied_source_event_id is not None:
                raise ValueError("empty memory cannot name an applied source event")
        elif newest_event_ids != {self.last_applied_source_event_id}:
            raise ValueError("memory applied source event marker is inconsistent")
        object.__setattr__(
            self, "scenario_records", tuple(sorted(self.scenario_records, key=lambda x: x.scenario_id))
        )
        object.__setattr__(
            self, "npc_records", tuple(sorted(self.npc_records, key=lambda x: x.subject_key))
        )
        object.__setattr__(
            self,
            "significant_experiences",
            tuple(sorted(self.significant_experiences, key=lambda x: x.entry_id)),
        )
        object.__setattr__(
            self,
            "known_public_facts",
            tuple(
                sorted(
                    self.known_public_facts,
                    key=lambda x: (x.scenario_id, x.fact_ref),
                )
            ),
        )
        return self

    def _apply_issued_plan(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        if not isinstance(plan, MemoryMutationPlan) or not plan.is_authentic():
            raise ValueError("memory mutation lacks server-issued authority")
        if plan.kind is MemoryMutationKind.START_SCENARIO:
            candidate = self._start_scenario(plan)
        elif plan.kind is MemoryMutationKind.COMPLETE_SCENARIO:
            candidate = self._complete_scenario(plan)
        elif plan.kind is MemoryMutationKind.RECORD_NPC_ENCOUNTER:
            candidate = self._record_npc_encounter(plan)
        elif plan.kind is MemoryMutationKind.UPDATE_NPC_MILESTONE:
            candidate = self._update_npc(plan)
        elif plan.kind is MemoryMutationKind.REMEMBER_PUBLIC_FACT:
            candidate = self._remember_public_fact(plan)
        elif plan.kind is MemoryMutationKind.RECORD_SIGNIFICANT_EXPERIENCE:
            candidate = self._record_experience(plan)
        else:  # pragma: no cover
            raise ValueError("unsupported memory mutation")
        if candidate != self:
            _require_newer(
                plan,
                self.last_applied_source_sequence_no,
                self.last_applied_source_event_id,
            )
            candidate = candidate.model_copy(
                update={
                    "last_applied_source_sequence_no": plan.source_sequence_no,
                    "last_applied_source_event_id": plan.source_event_id,
                }
            )
        return type(self).model_validate(candidate.model_dump(mode="json"))

    def mark_rebuild_required(
        self, *, source_sequence_no: int, source_event_id: str
    ) -> PlayerMemoryState:
        if type(source_sequence_no) is not int or source_sequence_no < 1:
            raise ValueError("deferred memory sequence must be positive")
        _STABLE_MEMORY_ID_ADAPTER.validate_python(source_event_id)
        if source_sequence_no <= self.last_applied_source_sequence_no:
            if (
                source_sequence_no == self.last_applied_source_sequence_no
                and source_event_id == self.last_applied_source_event_id
            ):
                return self
            raise MemoryConflictError("deferred memory source is stale")
        if self.sync_status is MemoryIndexSyncStatus.CURRENT:
            candidate = self.model_copy(
                update={
                    "sync_status": MemoryIndexSyncStatus.REBUILD_REQUIRED,
                    "first_deferred_source_sequence_no": source_sequence_no,
                    "last_deferred_source_sequence_no": source_sequence_no,
                    "deferred_event_count": 1,
                }
            )
            return type(self).model_validate(candidate.model_dump(mode="json"))
        assert self.last_deferred_source_sequence_no is not None
        if source_sequence_no == self.last_deferred_source_sequence_no:
            return self
        if source_sequence_no < self.last_deferred_source_sequence_no:
            raise MemoryConflictError("deferred memory source is stale")
        candidate = self.model_copy(
            update={
                "last_deferred_source_sequence_no": source_sequence_no,
                "deferred_event_count": min(
                    MAX_DEFERRED_MEMORY_EVENTS, self.deferred_event_count + 1
                ),
            }
        )
        return type(self).model_validate(candidate.model_dump(mode="json"))

    def _start_scenario(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        existing = _find(self.scenario_records, "scenario_id", plan.scenario_id)
        if existing is not None:
            if existing.scenario_content_version != plan.scenario_content_version:
                raise MemoryConflictError("scenario memory content version changed")
            return self
        _require_capacity(self.scenario_records, MAX_SCENARIO_MEMORY_RECORDS, "scenario")
        record = ScenarioMemoryRecord(
            scenario_id=plan.scenario_id,
            scenario_content_version=plan.scenario_content_version,
            status=ScenarioMemoryStatus.STARTED,
            milestone_refs=(ScenarioMemoryMilestone.STARTED,),
            last_source_event_id=plan.source_event_id,
            last_source_sequence_no=plan.source_sequence_no,
        )
        return self.model_copy(update={"scenario_records": (*self.scenario_records, record)})

    def _complete_scenario(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        existing = _find(self.scenario_records, "scenario_id", plan.scenario_id)
        if existing is None:
            raise MemoryConflictError("scenario memory must be started before completion")
        if existing.scenario_content_version != plan.scenario_content_version:
            raise MemoryConflictError("scenario memory content version changed")
        if existing.status is ScenarioMemoryStatus.COMPLETED:
            if existing.ending_id != plan.ending_id:
                raise MemoryConflictError("scenario memory has a different confirmed ending")
            return self
        _require_newer(plan, existing.last_source_sequence_no, existing.last_source_event_id)
        updated = existing.model_copy(
            update={
                "status": ScenarioMemoryStatus.COMPLETED,
                "ending_id": plan.ending_id,
                "milestone_refs": tuple(
                    set(existing.milestone_refs)
                    | {ScenarioMemoryMilestone.COMPLETED, ScenarioMemoryMilestone.ENDING_CONFIRMED}
                ),
                "last_source_event_id": plan.source_event_id,
                "last_source_sequence_no": plan.source_sequence_no,
            }
        )
        return self._replace("scenario_records", "scenario_id", updated)

    def _record_npc_encounter(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        self._require_scenario_record(plan)
        subject_key = stable_npc_subject_key(plan.scenario_id, plan.npc_definition_id)
        existing = _find(self.npc_records, "subject_key", subject_key)
        if existing is not None:
            return self
        _require_capacity(self.npc_records, MAX_NPC_MEMORY_RECORDS, "NPC")
        record = NpcMemoryRecord(
            subject_key=subject_key,
            scenario_id=plan.scenario_id,
            npc_definition_id=plan.npc_definition_id,
            interaction_milestones=(NpcInteractionMilestone.FIRST_ENCOUNTER,),
            last_source_event_id=plan.source_event_id,
            last_source_sequence_no=plan.source_sequence_no,
        )
        return self.model_copy(update={"npc_records": (*self.npc_records, record)})

    def _update_npc(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        self._require_scenario_record(plan)
        subject_key = stable_npc_subject_key(plan.scenario_id, plan.npc_definition_id)
        existing = _find(self.npc_records, "subject_key", subject_key)
        if existing is None:
            raise MemoryConflictError("NPC must be encountered before a milestone is recorded")
        milestones = set(existing.interaction_milestones)
        facts = set(existing.known_public_fact_refs)
        if plan.npc_milestone is not None:
            milestones.add(plan.npc_milestone)
        if plan.public_fact_ref is not None:
            facts.add(plan.public_fact_ref)
        if milestones == set(existing.interaction_milestones) and facts == set(
            existing.known_public_fact_refs
        ):
            return self
        if len(milestones) > MAX_MEMORY_REFS_PER_RECORD or len(facts) > MAX_MEMORY_REFS_PER_RECORD:
            raise MemoryCapacityError("NPC memory reference capacity reached")
        _require_newer(plan, existing.last_source_sequence_no, existing.last_source_event_id)
        updated = existing.model_copy(
            update={
                "interaction_milestones": tuple(milestones),
                "known_public_fact_refs": tuple(facts),
                "last_source_event_id": plan.source_event_id,
                "last_source_sequence_no": plan.source_sequence_no,
            }
        )
        return self._replace("npc_records", "subject_key", updated)

    def _remember_public_fact(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        scenario = self._require_scenario_record(plan)
        existing = next(
            (
                item
                for item in self.known_public_facts
                if item.scenario_id == plan.scenario_id
                and item.fact_ref == plan.public_fact_ref
            ),
            None,
        )
        if existing is not None:
            return self
        _require_capacity(self.known_public_facts, MAX_KNOWN_PUBLIC_FACTS, "public fact")
        fact = KnownPublicFactRecord(
            fact_ref=plan.public_fact_ref,
            scenario_id=plan.scenario_id,
            source_event_id=plan.source_event_id,
            source_sequence_no=plan.source_sequence_no,
        )
        facts = set(scenario.known_public_fact_refs) | {plan.public_fact_ref}
        if len(facts) > MAX_MEMORY_REFS_PER_RECORD:
            raise MemoryCapacityError("scenario public fact reference capacity reached")
        _require_newer(plan, scenario.last_source_sequence_no, scenario.last_source_event_id)
        updated_scenario = scenario.model_copy(
            update={
                "known_public_fact_refs": tuple(facts),
                "milestone_refs": tuple(
                    set(scenario.milestone_refs)
                    | {ScenarioMemoryMilestone.IMPORTANT_FACT_CONFIRMED}
                ),
                "last_source_event_id": plan.source_event_id,
                "last_source_sequence_no": plan.source_sequence_no,
            }
        )
        candidate = self._replace("scenario_records", "scenario_id", updated_scenario)
        return candidate.model_copy(update={"known_public_facts": (*candidate.known_public_facts, fact)})

    def _record_experience(self, plan: MemoryMutationPlan) -> PlayerMemoryState:
        assert plan.experience is not None
        self._require_scenario_record(plan)
        same_source = next(
            (
                item
                for item in self.significant_experiences
                if item.source_event_id == plan.experience.source_event_id
            ),
            None,
        )
        if same_source is not None and same_source != plan.experience:
            raise MemoryConflictError(
                "source event is already bound to a different experience"
            )
        existing = _find(self.significant_experiences, "entry_id", plan.experience.entry_id)
        if existing is not None:
            if existing != plan.experience:
                raise MemoryConflictError("experience ID is already bound to different content")
            return self
        _require_capacity(
            self.significant_experiences,
            MAX_SIGNIFICANT_EXPERIENCES,
            "significant experience",
        )
        return self.model_copy(
            update={"significant_experiences": (*self.significant_experiences, plan.experience)}
        )

    def _require_scenario_record(
        self, plan: MemoryMutationPlan
    ) -> ScenarioMemoryRecord:
        scenario = _find(self.scenario_records, "scenario_id", plan.scenario_id)
        if scenario is None:
            raise MemoryConflictError(
                "scenario memory must exist before related memory is recorded"
            )
        if scenario.scenario_content_version != plan.scenario_content_version:
            raise MemoryConflictError("related memory uses another scenario content version")
        return scenario

    def _replace(self, field: str, key: str, updated: MemoryModel) -> PlayerMemoryState:
        records = getattr(self, field)
        value = getattr(updated, key)
        replaced = tuple(updated if getattr(item, key) == value else item for item in records)
        return self.model_copy(update={field: replaced})


class MemoryMutationKind(StrEnum):
    START_SCENARIO = "START_SCENARIO"
    COMPLETE_SCENARIO = "COMPLETE_SCENARIO"
    RECORD_NPC_ENCOUNTER = "RECORD_NPC_ENCOUNTER"
    UPDATE_NPC_MILESTONE = "UPDATE_NPC_MILESTONE"
    REMEMBER_PUBLIC_FACT = "REMEMBER_PUBLIC_FACT"
    RECORD_SIGNIFICANT_EXPERIENCE = "RECORD_SIGNIFICANT_EXPERIENCE"


_MEMORY_PLAN_ISSUER = object()


@dataclass(frozen=True, slots=True, init=False)
class MemoryMutationPlan:
    kind: MemoryMutationKind
    session_id: str
    state_version: int
    non_memory_state_fingerprint: str
    scenario_definition_fingerprint: str
    memory_before_fingerprint: str
    memory_after_fingerprint: str
    source_event_id: str
    source_sequence_no: int
    scenario_id: str
    scenario_content_version: str | None
    npc_definition_id: str | None
    ending_id: str | None
    npc_milestone: NpcInteractionMilestone | None
    public_fact_ref: str | None
    experience: SignificantExperienceEntry | None
    _seal: _MemoryAuthoritySeal

    def __copy__(self) -> MemoryMutationPlan:
        return self

    def is_authentic(self) -> bool:
        try:
            seal = self._seal
            return (
                seal.target is self
                and seal.issuer is _MEMORY_PLAN_ISSUER
                and seal.digest == _plan_digest(self)
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def is_authentic_for(
        self,
        *,
        session_id: str,
        state_version: int,
        non_memory_state_fingerprint: str,
        scenario_definition_fingerprint: str,
        memory_fingerprint: str,
    ) -> bool:
        return (
            self.is_authentic()
            and self.session_id == session_id
            and self.state_version == state_version
            and self.non_memory_state_fingerprint == non_memory_state_fingerprint
            and self.scenario_definition_fingerprint
            == scenario_definition_fingerprint
            and memory_fingerprint
            in {self.memory_before_fingerprint, self.memory_after_fingerprint}
        )


class _MemoryPlanPayload(MemoryModel):
    kind: MemoryMutationKind
    session_id: StableMemoryId
    state_version: MemoryStateVersion
    non_memory_state_fingerprint: Fingerprint
    scenario_definition_fingerprint: Fingerprint
    memory_before_fingerprint: Fingerprint
    memory_after_fingerprint: Fingerprint
    source_event_id: StableMemoryId
    source_sequence_no: MemorySequence
    scenario_id: DefinitionId
    scenario_content_version: DefinitionId | None = None
    npc_definition_id: DefinitionId | None = None
    ending_id: DefinitionId | None = None
    npc_milestone: NpcInteractionMilestone | None = None
    public_fact_ref: StableMemoryId | None = None
    experience: SignificantExperienceEntry | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> _MemoryPlanPayload:
        required: dict[MemoryMutationKind, frozenset[str]] = {
            MemoryMutationKind.START_SCENARIO: frozenset({"scenario_content_version"}),
            MemoryMutationKind.COMPLETE_SCENARIO: frozenset(
                {"scenario_content_version", "ending_id"}
            ),
            MemoryMutationKind.RECORD_NPC_ENCOUNTER: frozenset(
                {"scenario_content_version", "npc_definition_id"}
            ),
            MemoryMutationKind.UPDATE_NPC_MILESTONE: frozenset(
                {"scenario_content_version", "npc_definition_id"}
            ),
            MemoryMutationKind.REMEMBER_PUBLIC_FACT: frozenset(
                {"scenario_content_version", "public_fact_ref"}
            ),
            MemoryMutationKind.RECORD_SIGNIFICANT_EXPERIENCE: frozenset(
                {"scenario_content_version", "experience"}
            ),
        }
        optional_fields = {
            "scenario_content_version",
            "npc_definition_id",
            "ending_id",
            "npc_milestone",
            "public_fact_ref",
            "experience",
        }
        present = {name for name in optional_fields if getattr(self, name) is not None}
        allowed = set(required[self.kind])
        if self.kind is MemoryMutationKind.UPDATE_NPC_MILESTONE:
            allowed |= {"npc_milestone", "public_fact_ref"}
            if self.npc_milestone is None and self.public_fact_ref is None:
                raise ValueError("NPC memory update must contain a milestone or public fact")
        if present != allowed and not (
            self.kind is MemoryMutationKind.UPDATE_NPC_MILESTONE
            and required[self.kind] <= present <= allowed
        ):
            raise ValueError("memory mutation fields do not match its closed operation")
        if self.experience is not None and (
            self.experience.scenario_id != self.scenario_id
            or self.experience.source_event_id != self.source_event_id
            or self.experience.source_sequence_no != self.source_sequence_no
        ):
            raise ValueError("experience does not match its source plan")
        return self


def _issue_memory_mutation(
    *,
    memory_state: PlayerMemoryState,
    authority_source: MemoryAuthoritySource,
    **values: object,
) -> MemoryMutationPlan:
    if not isinstance(authority_source, MemoryAuthoritySource) or not (
        authority_source.is_authentic()
    ):
        raise ValueError("memory plan source lacks server-issued authority")
    kind = values.get("kind")
    expected_source_types = {
        MemoryMutationKind.START_SCENARIO:
            MemoryAuthorityEventType.SCENARIO_STARTED,
        MemoryMutationKind.COMPLETE_SCENARIO:
            MemoryAuthorityEventType.SCENARIO_COMPLETED,
        MemoryMutationKind.RECORD_NPC_ENCOUNTER:
            MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED,
        MemoryMutationKind.UPDATE_NPC_MILESTONE:
            MemoryAuthorityEventType.NPC_MILESTONE_CONFIRMED,
        MemoryMutationKind.REMEMBER_PUBLIC_FACT:
            MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED,
        MemoryMutationKind.RECORD_SIGNIFICANT_EXPERIENCE:
            MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED,
    }
    if (
        not isinstance(kind, MemoryMutationKind)
        or authority_source.event_type is not expected_source_types[kind]
    ):
        raise ValueError("memory authority event does not match the mutation kind")
    before_fingerprint = memory_state_fingerprint(memory_state)
    payload = _MemoryPlanPayload.model_validate(
        {
            **values,
            "session_id": authority_source.session_id,
            "source_event_id": authority_source.event_id,
            "source_sequence_no": authority_source.sequence_no,
            "memory_before_fingerprint": before_fingerprint,
            "memory_after_fingerprint": before_fingerprint,
        }
    )
    preliminary = _materialize_plan(payload)
    candidate = memory_state._apply_issued_plan(preliminary)
    payload = payload.model_copy(
        update={"memory_after_fingerprint": memory_state_fingerprint(candidate)}
    )
    return _materialize_plan(payload)


def _materialize_plan(payload: _MemoryPlanPayload) -> MemoryMutationPlan:
    plan = object.__new__(MemoryMutationPlan)
    for field, value in payload.model_dump().items():
        object.__setattr__(plan, field, getattr(payload, field))
    object.__setattr__(
        plan,
        "_seal",
        _MemoryAuthoritySeal(
            target=plan,
            issuer=_MEMORY_PLAN_ISSUER,
            digest=_plan_digest(plan),
        ),
    )
    return plan


def significant_experience_summary(
    category: SignificantExperienceCategory,
) -> SignificantExperienceSummary:
    return _EXPERIENCE_SUMMARIES[category]


def stable_npc_subject_key(scenario_id: str, npc_definition_id: str) -> str:
    _DEFINITION_ID_ADAPTER.validate_python(scenario_id)
    _DEFINITION_ID_ADAPTER.validate_python(npc_definition_id)
    digest = hashlib.sha256(
        (
            "deviation-protocol:npc-subject:v1\0"
            f"{scenario_id}\0{npc_definition_id}"
        ).encode("utf-8")
    ).hexdigest()
    return f"npc-subject.{digest}"


def stable_significant_experience_id(
    *,
    source_event_id: str,
    scenario_id: str,
    category: SignificantExperienceCategory,
    subject_refs: tuple[str, ...],
    public_fact_refs: tuple[str, ...],
) -> str:
    _STABLE_MEMORY_ID_ADAPTER.validate_python(source_event_id)
    _DEFINITION_ID_ADAPTER.validate_python(scenario_id)
    if not isinstance(category, SignificantExperienceCategory):
        raise TypeError("experience category must use the closed enum")
    for reference in (*subject_refs, *public_fact_refs):
        _STABLE_MEMORY_ID_ADAPTER.validate_python(reference)
    payload = json.dumps(
        {
            "category": category.value,
            "event_id": source_event_id,
            "public_fact_refs": sorted(public_fact_refs),
            "scenario_id": scenario_id,
            "subject_refs": sorted(subject_refs),
            "summary": significant_experience_summary(category).value,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(
        f"deviation-protocol:memory-experience:v1\0{payload}".encode("utf-8")
    ).hexdigest()
    return f"memory-entry.{digest}"


def memory_state_fingerprint(memory: PlayerMemoryState) -> str:
    encoded = json.dumps(
        memory.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scenario_definition_fingerprint(definition: ScenarioDefinition) -> str:
    from deviation_protocol.domain.scenario import ScenarioDefinition

    if not isinstance(definition, ScenarioDefinition):
        raise TypeError("memory authority requires a scenario definition")
    encoded = json.dumps(
        definition.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _memory_authority_digest(source: MemoryAuthoritySource) -> str:
    encoded = json.dumps(
        {
            "event_id": getattr(source, "event_id", None),
            "event_type": getattr(source, "event_type", None),
            "sequence_no": getattr(source, "sequence_no", None),
            "session_id": getattr(source, "session_id", None),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_digest(plan: MemoryMutationPlan) -> str:
    experience = getattr(plan, "experience", None)
    payload = {
        "kind": getattr(plan, "kind", None),
        "session_id": getattr(plan, "session_id", None),
        "state_version": getattr(plan, "state_version", None),
        "non_memory_state_fingerprint": getattr(
            plan, "non_memory_state_fingerprint", None
        ),
        "scenario_definition_fingerprint": getattr(
            plan, "scenario_definition_fingerprint", None
        ),
        "memory_before_fingerprint": getattr(plan, "memory_before_fingerprint", None),
        "memory_after_fingerprint": getattr(plan, "memory_after_fingerprint", None),
        "source_event_id": getattr(plan, "source_event_id", None),
        "source_sequence_no": getattr(plan, "source_sequence_no", None),
        "scenario_id": getattr(plan, "scenario_id", None),
        "scenario_content_version": getattr(plan, "scenario_content_version", None),
        "npc_definition_id": getattr(plan, "npc_definition_id", None),
        "ending_id": getattr(plan, "ending_id", None),
        "npc_milestone": getattr(plan, "npc_milestone", None),
        "public_fact_ref": getattr(plan, "public_fact_ref", None),
        "experience": experience.model_dump(mode="json") if experience is not None else None,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _find(records: tuple[MemoryModel, ...], field: str, value: object) -> MemoryModel | None:
    return next((item for item in records if getattr(item, field) == value), None)


def _require_capacity(records: tuple[MemoryModel, ...], maximum: int, label: str) -> None:
    if len(records) >= maximum:
        raise MemoryCapacityError(f"{label} memory capacity reached")


def _require_newer(
    plan: MemoryMutationPlan,
    current_sequence: int,
    current_event_id: str | None,
) -> None:
    if plan.source_sequence_no < current_sequence or (
        plan.source_sequence_no == current_sequence
        and plan.source_event_id != current_event_id
    ):
        raise MemoryConflictError("memory update is stale")


def migrate_player_memory_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Purely upgrade the independent player-memory model without snapshot v4."""

    copied = deepcopy(dict(payload))
    version = copied.get("memory_model_version")
    if type(version) is not int:
        raise ValueError("memory_model_version must be a strict integer")
    if version == 1:
        source_records: list[tuple[int, str]] = []
        for field, sequence_field, event_field in (
            ("scenario_records", "last_source_sequence_no", "last_source_event_id"),
            ("npc_records", "last_source_sequence_no", "last_source_event_id"),
            ("significant_experiences", "source_sequence_no", "source_event_id"),
            ("known_public_facts", "source_sequence_no", "source_event_id"),
        ):
            records = copied.get(field, [])
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        sequence = record.get(sequence_field)
                        event_id = record.get(event_field)
                        if type(sequence) is int and isinstance(event_id, str):
                            source_records.append((sequence, event_id))
        newest_sequence = copied.get("last_applied_source_sequence_no", 0)
        newest_ids = {
            event_id
            for sequence, event_id in source_records
            if sequence == newest_sequence
        }
        if newest_sequence and len(newest_ids) != 1:
            raise ValueError("v1 memory has an ambiguous newest source event")
        copied.update(
            {
                "memory_model_version": 2,
                "sync_status": MemoryIndexSyncStatus.CURRENT.value,
                "last_applied_source_event_id": (
                    next(iter(newest_ids)) if newest_ids else None
                ),
                "first_deferred_source_sequence_no": None,
                "last_deferred_source_sequence_no": None,
                "deferred_event_count": 0,
            }
        )
        return copied
    if version == MEMORY_MODEL_VERSION:
        return copied
    raise ValueError(f"unsupported player memory model version: {version}")
