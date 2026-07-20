from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.domain.facts import FactVisibility
from deviation_protocol.domain.player_memory import (
    MemoryCapacityError,
    MemoryAuthorityEventType,
    MemoryAuthoritySource,
    MemoryConflictError,
    MemoryIndexSyncStatus,
    MemoryMutationKind,
    MemoryMutationPlan,
    NpcInteractionMilestone,
    NpcMemoryRecord,
    PlayerMemoryState,
    ScenarioMemoryMilestone,
    ScenarioMemoryRecord,
    ScenarioMemoryStatus,
    SignificantExperienceCategory,
    SignificantExperienceEntry,
    SignificantExperienceSummary,
    _issue_memory_authority_source,
    _issue_memory_authority_source_from_receipt,
    _issue_memory_mutation,
    scenario_definition_fingerprint,
    significant_experience_summary,
    stable_npc_subject_key,
    stable_significant_experience_id,
)
from deviation_protocol.domain.memory_rules import (
    MemoryRuleDefinition,
    MemoryRuleOperation,
    MemoryRuleSourceEventType,
)
from deviation_protocol.domain.persisted_events import PersistedEventReceipt
from deviation_protocol.domain.scenario import (
    EndingStatus,
    ScenarioCatalog,
    ScenarioDefinition,
)
from deviation_protocol.domain.scenario_rules import DeclarativeConditionEvaluator
from deviation_protocol.domain.state import GameState


MAX_PROJECTED_SCENARIOS = 16
MAX_PROJECTED_NPCS = 32
MAX_PROJECTED_EXPERIENCES = 64
MAX_PROJECTED_PUBLIC_FACTS = 128
MAX_MEMORY_PROJECTION_CHARACTERS = 16_000
MAX_MEMORY_PROJECTION_JSON_BYTES = 32_000


class AuthoritativePlayerMemoryPlanFactory:
    """Create sealed plans from current authority and a server event envelope.

    This factory is intentionally not injected into any API or production turn
    orchestrator in Phase 2.3a. Event payloads are ignored: every memory value is
    re-derived from current state, scenario content, and closed enums. Narrative
    frames and event payloads are never authority. A caller must later supply an
    event known to be persisted atomically.
    """

    def start_scenario(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        source_event: MemoryAuthoritySource,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(source_event, MemoryAuthorityEventType.SCENARIO_STARTED)
        existing = next(
            (
                record
                for record in state.player_memory.scenario_records
                if record.scenario_id == runtime.scenario_id
            ),
            None,
        )
        if existing is not None and (
            existing.scenario_content_version
            != runtime.scenario_content_version
        ):
            raise MemoryConflictError("scenario memory content version changed")
        if existing is not None:
            raise ValueError(
                "Phase 2.3a does not support replaying the same scenario identity"
            )
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.START_SCENARIO,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
        )

    def complete_scenario(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        source_event: MemoryAuthoritySource,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(source_event, MemoryAuthorityEventType.SCENARIO_COMPLETED)
        if runtime.ending_status is EndingStatus.ACTIVE or runtime.ending_id is None:
            raise ValueError("only an authoritative completed scenario has an ending")
        if not any(item.ending_id == runtime.ending_id for item in definition.endings):
            raise ValueError("runtime ending is absent from authoritative scenario content")
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.COMPLETE_SCENARIO,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
            ending_id=runtime.ending_id,
        )

    def record_npc_encounter(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        runtime_npc_id: str,
        source_event: MemoryAuthoritySource,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(source_event, MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED)
        npc_definition_id = _visible_npc_definition(
            state, definition, runtime_npc_id
        )
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.RECORD_NPC_ENCOUNTER,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
            npc_definition_id=npc_definition_id,
        )

    def update_npc_milestone(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        runtime_npc_id: str,
        milestone: NpcInteractionMilestone,
        source_event: MemoryAuthoritySource,
        public_fact_ref: str | None = None,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(source_event, MemoryAuthorityEventType.NPC_MILESTONE_CONFIRMED)
        if not isinstance(milestone, NpcInteractionMilestone):
            raise TypeError("NPC memory milestone must use the closed server enum")
        npc_definition_id = _visible_npc_definition(
            state, definition, runtime_npc_id
        )
        if public_fact_ref is not None:
            _require_public_fact(public_fact_ref, definition, runtime)
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.UPDATE_NPC_MILESTONE,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
            npc_definition_id=npc_definition_id,
            npc_milestone=milestone,
            public_fact_ref=public_fact_ref,
        )

    def remember_public_fact(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        fact_ref: str,
        source_event: MemoryAuthoritySource,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(source_event, MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED)
        _require_public_fact(fact_ref, definition, runtime)
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.REMEMBER_PUBLIC_FACT,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
            public_fact_ref=fact_ref,
        )

    def record_significant_experience(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        category: SignificantExperienceCategory,
        source_event: MemoryAuthoritySource,
        runtime_npc_id: str | None = None,
        public_fact_ref: str | None = None,
    ) -> MemoryMutationPlan:
        runtime = _require_runtime(state, definition)
        _require_source(
            source_event, MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED
        )
        if not isinstance(category, SignificantExperienceCategory):
            raise TypeError("experience category must use the closed server enum")
        subjects: tuple[str, ...] = ()
        facts: tuple[str, ...] = ()
        if category is SignificantExperienceCategory.SCENARIO_BEGIN:
            if runtime.phase_visit_counts.get(definition.initial_phase_id, 0) < 1:
                raise ValueError("scenario has not authoritatively started")
        elif category is SignificantExperienceCategory.SCENARIO_COMPLETION:
            if runtime.ending_status is EndingStatus.ACTIVE or runtime.ending_id is None:
                raise ValueError("scenario has not authoritatively completed")
            subjects = (runtime.ending_id,)
        elif category in {
            SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
            SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
        }:
            if runtime_npc_id is None:
                raise ValueError("NPC experience requires a visible runtime NPC")
            definition_id = _visible_npc_definition(
                state, definition, runtime_npc_id
            )
            subjects = (stable_npc_subject_key(runtime.scenario_id, definition_id),)
        elif category is SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY:
            if public_fact_ref is None:
                raise ValueError("public discovery requires a fact reference")
            _require_public_fact(public_fact_ref, definition, runtime)
            facts = (public_fact_ref,)
        entry = SignificantExperienceEntry(
            entry_id=stable_significant_experience_id(
                source_event_id=source_event.event_id,
                scenario_id=runtime.scenario_id,
                category=category,
                subject_refs=subjects,
                public_fact_refs=facts,
            ),
            scenario_id=runtime.scenario_id,
            category=category,
            summary=significant_experience_summary(category),
            subject_refs=subjects,
            public_fact_refs=facts,
            source_event_id=source_event.event_id,
            source_sequence_no=source_event.sequence_no,
        )
        return _issue_for_state(
            state,
            definition,
            state_version,
            source_event,
            kind=MemoryMutationKind.RECORD_SIGNIFICANT_EXPERIENCE,
            scenario_id=runtime.scenario_id,
            scenario_content_version=runtime.scenario_content_version,
            experience=entry,
        )


ProjectionId = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"),
]


class MemoryProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScenarioMemoryProjection(MemoryProjectionModel):
    scenario_id: ProjectionId
    scenario_content_version: ProjectionId
    status: ScenarioMemoryStatus
    ending_id: ProjectionId | None = None
    milestone_refs: Annotated[tuple[ScenarioMemoryMilestone, ...], Field(max_length=32)] = ()
    known_public_fact_refs: Annotated[tuple[ProjectionId, ...], Field(max_length=32)] = ()


class NpcMemoryProjection(MemoryProjectionModel):
    subject_key: ProjectionId
    scenario_id: ProjectionId
    npc_definition_id: ProjectionId
    interaction_milestones: Annotated[tuple[NpcInteractionMilestone, ...], Field(max_length=32)] = ()
    known_public_fact_refs: Annotated[tuple[ProjectionId, ...], Field(max_length=32)] = ()


class SignificantExperienceProjection(MemoryProjectionModel):
    entry_id: ProjectionId
    scenario_id: ProjectionId
    category: SignificantExperienceCategory
    summary: SignificantExperienceSummary
    subject_refs: Annotated[tuple[ProjectionId, ...], Field(max_length=8)] = ()
    public_fact_refs: Annotated[tuple[ProjectionId, ...], Field(max_length=8)] = ()


class KnownPublicFactProjection(MemoryProjectionModel):
    scenario_id: ProjectionId
    fact_ref: ProjectionId


class PlayerMemoryProjection(MemoryProjectionModel):
    projection_version: Annotated[int, Field(strict=True)] = 2
    complete: bool = True
    sync_status: MemoryIndexSyncStatus = MemoryIndexSyncStatus.CURRENT
    scenarios: Annotated[tuple[ScenarioMemoryProjection, ...], Field(max_length=MAX_PROJECTED_SCENARIOS)] = ()
    npcs: Annotated[tuple[NpcMemoryProjection, ...], Field(max_length=MAX_PROJECTED_NPCS)] = ()
    significant_experiences: Annotated[tuple[SignificantExperienceProjection, ...], Field(max_length=MAX_PROJECTED_EXPERIENCES)] = ()
    known_public_facts: Annotated[tuple[KnownPublicFactProjection, ...], Field(max_length=MAX_PROJECTED_PUBLIC_FACTS)] = ()
    total_scenario_records: Annotated[int, Field(strict=True, ge=0)] = 0
    total_npc_records: Annotated[int, Field(strict=True, ge=0)] = 0
    total_significant_experiences: Annotated[int, Field(strict=True, ge=0)] = 0
    total_known_public_facts: Annotated[int, Field(strict=True, ge=0)] = 0
    truncated: bool = False

    @model_validator(mode="after")
    def validate_projection(self) -> PlayerMemoryProjection:
        collections = (
            ("scenarios", self.scenarios, lambda item: item.scenario_id),
            ("npcs", self.npcs, lambda item: item.subject_key),
            (
                "significant_experiences",
                self.significant_experiences,
                lambda item: item.entry_id,
            ),
            (
                "known_public_facts",
                self.known_public_facts,
                lambda item: (item.scenario_id, item.fact_ref),
            ),
        )
        totals = (
            self.total_scenario_records,
            self.total_npc_records,
            self.total_significant_experiences,
            self.total_known_public_facts,
        )
        omitted = False
        for (field_name, records, key), total in zip(collections, totals, strict=True):
            keys = tuple(key(item) for item in records)
            if len(keys) != len(set(keys)):
                raise ValueError(f"memory projection repeats {field_name}")
            if total < len(records):
                raise ValueError("memory projection total is smaller than its records")
            omitted = omitted or total > len(records)
            object.__setattr__(self, field_name, tuple(sorted(records, key=key)))
        if omitted != self.truncated:
            raise ValueError("memory projection truncation marker is inconsistent")
        if self.complete != (
            self.sync_status is MemoryIndexSyncStatus.CURRENT
        ):
            raise ValueError("memory projection completeness marker is inconsistent")
        return self


class PlayerMemoryProjector:
    """Build a deterministic, deeply isolated, player-known-only bounded view."""

    def project(
        self,
        state: GameState,
        scenario_catalog: ScenarioCatalog | None = None,
    ) -> PlayerMemoryProjection:
        if (
            state.player_memory.scenario_records
            or state.player_memory.npc_records
            or state.player_memory.significant_experiences
            or state.player_memory.known_public_facts
        ):
            if scenario_catalog is None:
                raise ValueError(
                    "scenario catalog is required for player-memory projection"
                )
            state.validate_player_memory_against(scenario_catalog)
        # JSON round-trip is an explicit deep isolation boundary and also proves the
        # source subtree is serializable under the strict snapshot contract.
        memory = PlayerMemoryState.model_validate_json(state.player_memory.model_dump_json())
        scenarios = list(_latest(memory.scenario_records, MAX_PROJECTED_SCENARIOS))
        npcs = list(_latest(memory.npc_records, MAX_PROJECTED_NPCS))
        experiences = list(
            _latest(memory.significant_experiences, MAX_PROJECTED_EXPERIENCES)
        )
        facts = list(_latest(memory.known_public_facts, MAX_PROJECTED_PUBLIC_FACTS))

        while True:
            projection = _build_projection(memory, scenarios, npcs, experiences, facts)
            payload = projection.model_dump(mode="json")
            serialized = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            encoded = serialized.encode("utf-8")
            if (
                len(serialized) <= MAX_MEMORY_PROJECTION_CHARACTERS
                and len(encoded) <= MAX_MEMORY_PROJECTION_JSON_BYTES
            ):
                return projection
            for collection in (experiences, npcs, facts, scenarios):
                if collection:
                    collection.pop(0)
                    break
            else:  # pragma: no cover - fixed empty projection is far below limits
                raise ValueError("empty memory projection exceeds fixed bounds")


class DeclarativePlayerMemoryRuleEngine:
    """Apply scenario-authored rules only from authentic flushed-event receipts."""

    def __init__(
        self,
        plan_factory: AuthoritativePlayerMemoryPlanFactory | None = None,
    ) -> None:
        self._plan_factory = plan_factory or AuthoritativePlayerMemoryPlanFactory()

    def apply(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        session_id: str,
        turn_id: str,
        state_version: int,
        receipts: tuple[PersistedEventReceipt, ...],
    ) -> GameState:
        candidate = GameState.model_validate(state.to_snapshot())
        if any(
            not isinstance(receipt, PersistedEventReceipt)
            or not receipt.is_authentic()
            for receipt in receipts
        ):
            raise ValueError("memory rules require a flushed persisted-event receipt")
        ordered = tuple(sorted(receipts, key=lambda item: item.sequence_no))
        seen_sequences: dict[int, str] = {}
        for receipt in ordered:
            if (
                receipt.session_id != session_id
                or receipt.turn_id != turn_id
                or receipt.state_version != state_version
            ):
                raise ValueError("persisted event receipt is bound to another state")
            previous = seen_sequences.setdefault(receipt.sequence_no, receipt.event_id)
            if previous != receipt.event_id:
                raise MemoryConflictError("event sequence is bound to another event")
            rules = tuple(
                sorted(
                    (
                        rule
                        for rule in definition.memory_rules
                        if _memory_rule_matches(rule, receipt, candidate)
                    ),
                    key=lambda item: item.rule_id,
                )
            )
            if not rules:
                continue
            memory = candidate.player_memory
            if memory.sync_status is MemoryIndexSyncStatus.REBUILD_REQUIRED:
                candidate.player_memory = memory.mark_rebuild_required(
                    source_sequence_no=receipt.sequence_no,
                    source_event_id=receipt.event_id,
                )
                continue
            if receipt.sequence_no < memory.last_applied_source_sequence_no:
                raise MemoryConflictError("memory rule event is stale")
            if receipt.sequence_no == memory.last_applied_source_sequence_no:
                if receipt.event_id == memory.last_applied_source_event_id:
                    continue
                raise MemoryConflictError("memory sequence is bound to another event")

            before_event_memory = memory
            try:
                for rule in rules:
                    plan = self._plan_for_rule(
                        state=candidate,
                        definition=definition,
                        state_version=state_version,
                        receipt=receipt,
                        rule=rule,
                    )
                    candidate.apply_memory_plan(
                        plan,
                        session_id=session_id,
                        state_version=state_version,
                        scenario_definition=definition,
                    )
            except MemoryCapacityError:
                candidate.player_memory = before_event_memory.mark_rebuild_required(
                    source_sequence_no=receipt.sequence_no,
                    source_event_id=receipt.event_id,
                )
        return GameState.model_validate(candidate.to_snapshot())

    def _plan_for_rule(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        receipt: PersistedEventReceipt,
        rule: MemoryRuleDefinition,
    ) -> MemoryMutationPlan:
        source_types = {
            MemoryRuleOperation.START_SCENARIO:
                MemoryAuthorityEventType.SCENARIO_STARTED,
            MemoryRuleOperation.COMPLETE_SCENARIO:
                MemoryAuthorityEventType.SCENARIO_COMPLETED,
            MemoryRuleOperation.RECORD_NPC_ENCOUNTER:
                MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED,
            MemoryRuleOperation.UPDATE_NPC_MILESTONE:
                MemoryAuthorityEventType.NPC_MILESTONE_CONFIRMED,
            MemoryRuleOperation.REMEMBER_PUBLIC_FACT:
                MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED,
            MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE:
                MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED,
        }
        source = _issue_memory_authority_source_from_receipt(
            receipt, memory_event_type=source_types[rule.operation]
        )
        common = {
            "state": state,
            "definition": definition,
            "state_version": state_version,
            "source_event": source,
        }
        if rule.operation is MemoryRuleOperation.START_SCENARIO:
            return self._plan_factory.start_scenario(**common)
        if rule.operation is MemoryRuleOperation.COMPLETE_SCENARIO:
            runtime = state.scenario_runtime
            if runtime is None or runtime.ending_id not in rule.allowed_ending_ids:
                raise ValueError("completed scenario ending is not allowed by memory rule")
            return self._plan_factory.complete_scenario(**common)
        runtime_npc_id = None
        if rule.npc_definition_id is not None:
            matching = tuple(
                npc_id
                for npc_id, npc in state.npcs.items()
                if npc.definition_id == rule.npc_definition_id
            )
            if len(matching) != 1:
                raise ValueError("memory rule NPC is not a unique runtime subject")
            runtime_npc_id = matching[0]
        if rule.operation is MemoryRuleOperation.RECORD_NPC_ENCOUNTER:
            assert runtime_npc_id is not None
            return self._plan_factory.record_npc_encounter(
                **common, runtime_npc_id=runtime_npc_id
            )
        if rule.operation is MemoryRuleOperation.UPDATE_NPC_MILESTONE:
            assert runtime_npc_id is not None and rule.npc_milestone is not None
            return self._plan_factory.update_npc_milestone(
                **common,
                runtime_npc_id=runtime_npc_id,
                milestone=rule.npc_milestone,
            )
        if rule.operation is MemoryRuleOperation.REMEMBER_PUBLIC_FACT:
            assert rule.public_fact_id is not None
            return self._plan_factory.remember_public_fact(
                **common, fact_ref=rule.public_fact_id
            )
        assert rule.significant_experience_category is not None
        return self._plan_factory.record_significant_experience(
            **common,
            category=rule.significant_experience_category,
            runtime_npc_id=runtime_npc_id,
            public_fact_ref=rule.public_fact_id,
        )


def _require_runtime(state: GameState, definition: ScenarioDefinition) -> Any:
    runtime = state.scenario_runtime
    if runtime is None:
        raise ValueError("memory update requires authoritative scenario runtime")
    runtime.validate_against(definition)
    return runtime


def _issue_for_state(
    state: GameState,
    definition: ScenarioDefinition,
    state_version: int,
    source_event: MemoryAuthoritySource,
    **values: object,
) -> MemoryMutationPlan:
    return _issue_memory_mutation(
        memory_state=state.player_memory,
        authority_source=source_event,
        state_version=state_version,
        non_memory_state_fingerprint=state.memory_authority_fingerprint(),
        scenario_definition_fingerprint=scenario_definition_fingerprint(
            definition
        ),
        **values,
    )


def _require_source(
    source: MemoryAuthoritySource, expected: MemoryAuthorityEventType
) -> None:
    if not isinstance(source, MemoryAuthoritySource) or not source.is_authentic():
        raise ValueError("memory source lacks server-issued authority")
    if source.event_type is not expected:
        raise ValueError("memory source event type is not authorized")


def _visible_npc_definition(
    state: GameState,
    definition: ScenarioDefinition,
    runtime_npc_id: str,
) -> str:
    runtime = _require_runtime(state, definition)
    location = next(
        item for item in definition.locations
        if item.location_id == runtime.current_location_id
    )
    npc = state.npcs.get(runtime_npc_id)
    if npc is None or npc.definition_id not in location.visible_entity_ids:
        raise ValueError("catalog or runtime existence does not prove an NPC encounter")
    same_definition_ids = tuple(
        npc_id
        for npc_id, candidate in state.npcs.items()
        if candidate.definition_id == npc.definition_id
    )
    if len(same_definition_ids) != 1:
        raise ValueError(
            "NPC definition is not a unique stable subject in this scenario runtime"
        )
    return npc.definition_id


def _require_public_fact(
    fact_ref: str, definition: ScenarioDefinition, runtime: Any
) -> None:
    known_fact_ids = {
        fact.fact_id
        for fact in definition.facts
        if fact.visibility is FactVisibility.PLAYER_KNOWN
    }
    for clue_id in runtime.discovered_clue_ids:
        known_fact_ids.update(definition.clue(clue_id).supports_fact_ids)
    fact = next((item for item in definition.facts if item.fact_id == fact_ref), None)
    if (
        fact_ref not in known_fact_ids
        or fact is None
        or fact.visibility is FactVisibility.HIDDEN
        or DeclarativeConditionEvaluator().fact_value(
            fact_ref, definition, runtime
        )
        is None
    ):
        raise ValueError("fact is not confirmed player-known public information")


def _latest(records: tuple[Any, ...], maximum: int) -> tuple[Any, ...]:
    return tuple(
        sorted(records, key=lambda item: (item.source_sequence_no if hasattr(item, "source_sequence_no") else item.last_source_sequence_no, _record_id(item)))[-maximum:]
    )


def _record_id(record: Any) -> str:
    if hasattr(record, "fact_ref") and hasattr(record, "scenario_id"):
        return f"{record.scenario_id}\0{record.fact_ref}"
    for name in ("scenario_id", "subject_key", "entry_id", "fact_ref"):
        if hasattr(record, name):
            return str(getattr(record, name))
    raise TypeError("unknown memory record")  # pragma: no cover


def _build_projection(
    memory: PlayerMemoryState,
    scenarios: list[ScenarioMemoryRecord],
    npcs: list[NpcMemoryRecord],
    experiences: list[SignificantExperienceEntry],
    facts: list[Any],
) -> PlayerMemoryProjection:
    projection = PlayerMemoryProjection(
        complete=memory.sync_status is MemoryIndexSyncStatus.CURRENT,
        sync_status=memory.sync_status,
        scenarios=tuple(
            ScenarioMemoryProjection(
                scenario_id=item.scenario_id,
                scenario_content_version=item.scenario_content_version,
                status=item.status,
                ending_id=item.ending_id,
                milestone_refs=item.milestone_refs,
                known_public_fact_refs=item.known_public_fact_refs,
            )
            for item in sorted(scenarios, key=lambda x: x.scenario_id)
        ),
        npcs=tuple(
            NpcMemoryProjection(
                subject_key=item.subject_key,
                scenario_id=item.scenario_id,
                npc_definition_id=item.npc_definition_id,
                interaction_milestones=item.interaction_milestones,
                known_public_fact_refs=item.known_public_fact_refs,
            )
            for item in sorted(npcs, key=lambda x: x.subject_key)
        ),
        significant_experiences=tuple(
            SignificantExperienceProjection(
                entry_id=item.entry_id,
                scenario_id=item.scenario_id,
                category=item.category,
                summary=item.summary,
                subject_refs=item.subject_refs,
                public_fact_refs=item.public_fact_refs,
            )
            for item in sorted(experiences, key=lambda x: x.entry_id)
        ),
        known_public_facts=tuple(
            KnownPublicFactProjection(
                scenario_id=item.scenario_id,
                fact_ref=item.fact_ref,
            )
            for item in sorted(
                facts, key=lambda item: (item.scenario_id, item.fact_ref)
            )
        ),
        total_scenario_records=len(memory.scenario_records),
        total_npc_records=len(memory.npc_records),
        total_significant_experiences=len(memory.significant_experiences),
        total_known_public_facts=len(memory.known_public_facts),
        truncated=(
            len(scenarios) < len(memory.scenario_records)
            or len(npcs) < len(memory.npc_records)
            or len(experiences) < len(memory.significant_experiences)
            or len(facts) < len(memory.known_public_facts)
        ),
    )
    return PlayerMemoryProjection.model_validate_json(projection.model_dump_json())


def _memory_rule_matches(
    rule: MemoryRuleDefinition,
    receipt: PersistedEventReceipt,
    state: GameState,
) -> bool:
    if receipt.event_type != rule.source_event_type.value:
        return False
    runtime = state.scenario_runtime
    if runtime is None:
        return False
    payload = receipt.authoritative_payload()
    if rule.source_event_type is MemoryRuleSourceEventType.SCENARIO_STARTED:
        if (
            payload.get("scenario_id") != runtime.scenario_id
            or payload.get("scenario_content_version")
            != runtime.scenario_content_version
        ):
            raise ValueError("scenario-started event payload conflicts with runtime")
    if (
        rule.source_event_type
        is MemoryRuleSourceEventType.SCENARIO_RUNTIME_EVENT_GENERATED
        and rule.required_scenario_event_types
        and payload.get("scenario_event_type")
        not in rule.required_scenario_event_types
    ):
        return False
    if (
        rule.source_event_type
        is MemoryRuleSourceEventType.SCENARIO_DECISION_SELECTED
        and rule.required_scenario_event_types
        and payload.get("scenario_event_type")
        not in rule.required_scenario_event_types
    ):
        return False
    if (
        rule.source_event_type
        is MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED
    ):
        if rule.required_narrative_outcome_rule_ids and payload.get(
            "outcome_rule_id"
        ) not in rule.required_narrative_outcome_rule_ids:
            return False
        if rule.required_scenario_event_types and payload.get(
            "scenario_event_type"
        ) not in rule.required_scenario_event_types:
            return False
        if rule.required_outcome_results and payload.get(
            "outcome_result"
        ) not in tuple(item.value for item in rule.required_outcome_results):
            return False
        if rule.npc_definition_id is not None:
            npc_definitions = payload.get("npc_definition_ids", ())
            if not isinstance(npc_definitions, tuple) or (
                rule.npc_definition_id not in npc_definitions
            ):
                return False
    if rule.requires_scenario_completed and (
        runtime.ending_status is EndingStatus.ACTIVE or runtime.ending_id is None
    ):
        return False
    return True
