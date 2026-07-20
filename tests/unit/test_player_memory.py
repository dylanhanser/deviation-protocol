from __future__ import annotations

from copy import copy, deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import pickle
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.player_memory import (
    AuthoritativePlayerMemoryPlanFactory,
    DeclarativePlayerMemoryRuleEngine,
    MAX_MEMORY_PROJECTION_CHARACTERS,
    MAX_MEMORY_PROJECTION_JSON_BYTES,
    MemoryAuthorityEventType,
    MemoryAuthoritySource,
    PlayerMemoryProjection,
    PlayerMemoryProjector,
    _issue_memory_authority_source,
)
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.api.schemas import ActionRequest
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.player_memory import (
    MAX_SIGNIFICANT_EXPERIENCES,
    MemoryCapacityError,
    MemoryConflictError,
    MemoryMutationKind,
    MemoryMutationPlan,
    MemoryIndexSyncStatus,
    NpcInteractionMilestone,
    ScenarioMemoryStatus,
    SignificantExperienceCategory,
    _issue_memory_mutation,
    migrate_player_memory_payload,
    scenario_definition_fingerprint,
    stable_npc_subject_key,
    stable_significant_experience_id,
)
from deviation_protocol.domain.memory_rules import MemoryRuleDefinition
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.domain.scenario import ScenarioCatalog, ScenarioDefinition
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    NarrativeOutcomeEvidence,
    _issue_verified_scenario_event,
)
from deviation_protocol.domain.state import DomainRuleViolation, GameState, PlayerState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from tests.unit.test_story_director import mini_catalog, state_for


NOW = datetime(2026, 7, 20, tzinfo=timezone.utc)
SESSION_ID = "session-1"
STATE_VERSION = 7
SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)


def _started():
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    directed = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    return catalog, definition, directed.candidate_state, directed.frame


def _production_started_with_memory():
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character(
        "character.death_certificate.investigator"
    )
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    for index, reference in enumerate(definition.npc_references, start=1):
        state.spawn_npc(
            catalog.content_catalog,
            reference.npc_definition_id,
            f"runtime-npc-{index}",
        )
    directed = DeterministicStoryDirector().start_scenario(
        state,
        definition,
        profession_tags=frozenset(character.tags)
        & set(definition.available_profession_tags),
    )
    with_memory = DeclarativePlayerMemoryRuleEngine().apply(
        state=directed.candidate_state,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="session-created",
        state_version=0,
        receipts=(
            _receipt(
                event_type="ScenarioStarted",
                sequence=1,
                turn_id="session-created",
                state_version=0,
                payload={
                    "scenario_id": definition.scenario_id,
                    "scenario_content_version": definition.content_version,
                },
            ),
        ),
    )
    return catalog, definition, with_memory


def _production_success_memory():
    catalog, definition, state = _production_started_with_memory()
    runtime = state.scenario_runtime
    assert runtime is not None
    runtime.discovered_clue_ids = frozenset(
        {*runtime.discovered_clue_ids, "death_certificate.clue.vital_response"}
    )
    runtime.applied_event_ids = (
        *runtime.applied_event_ids,
        "death_certificate.outcome.purposeful_life_signal",
    )
    runtime.narrative_outcome_evidence = (
        NarrativeOutcomeEvidence(
            outcome_rule_id="death_certificate.outcome.purposeful_life_signal",
            outcome_result=NarrativeOutcomeResult.SUCCESS,
            scenario_event_type="vitals.verified",
            npc_definition_ids=(
                "npc.death_certificate.triage_coordinator",
            ),
            player_alive_acknowledgement_npc_definition_ids=(
                "npc.death_certificate.triage_coordinator",
            ),
            player_alive_acknowledgement_npc_ids=("runtime-npc-1",),
        ),
    )
    learned = DeclarativePlayerMemoryRuleEngine().apply(
        state=state,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-2",
        state_version=0,
        receipts=(
            _receipt(
                event_type="NarrativeOutcomeAccepted",
                sequence=2,
                turn_id="turn-2",
                state_version=0,
                payload={
                    "outcome_rule_id": (
                        "death_certificate.outcome.purposeful_life_signal"
                    ),
                    "outcome_result": "SUCCESS",
                    "scenario_event_type": "vitals.verified",
                    "npc_definition_ids": (
                        "npc.death_certificate.triage_coordinator",
                    ),
                    "player_alive_acknowledgement_npc_definition_ids": (
                        "npc.death_certificate.triage_coordinator",
                    ),
                },
            ),
        ),
    )
    return catalog, definition, learned


def _catalog_with_scenario_clones(
    catalog: ScenarioCatalog,
    scenario_ids: tuple[str, ...],
    *,
    scenario_begin_experience: bool = False,
) -> ScenarioCatalog:
    payload = catalog.model_dump(mode="json")
    base = payload["scenarios"][0]
    scenarios = []
    for index, scenario_id in enumerate(scenario_ids):
        definition = deepcopy(base)
        definition["scenario_id"] = scenario_id
        if scenario_begin_experience:
            definition["memory_rules"] = [
                {
                    "rule_id": f"memory.begin.{index:02d}",
                    "rule_version": "1.0.0",
                    "source_event_type": "ScenarioStarted",
                    "operation": "RECORD_SIGNIFICANT_EXPERIENCE",
                    "significant_experience_category": "SCENARIO_BEGIN",
                    "significant_experience_summary": "SCENARIO_BEGAN",
                    "important_experience": True,
                }
            ]
        scenarios.append(definition)
    payload["scenarios"] = scenarios
    return ScenarioCatalog.model_validate(payload)


def _unparticipated_scenario_memory_payload(
    *, include_player_known_fact: bool
) -> tuple[ScenarioCatalog, dict[str, object]]:
    catalog, _, state = _production_started_with_memory()
    catalog = _catalog_with_scenario_clones(
        catalog, ("death_certificate", "scenario.never_entered")
    )
    payload = state.to_snapshot()
    memory = payload["player_memory"]
    source_record = memory["scenario_records"][0]
    injected_record = deepcopy(source_record)
    injected_record.update(
        {
            "scenario_id": "scenario.never_entered",
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
        }
    )
    if include_player_known_fact:
        fact_ref = source_record["known_public_fact_refs"][0]
        injected_record["milestone_refs"] = [
            "STARTED",
            "IMPORTANT_FACT_CONFIRMED",
        ]
        injected_record["known_public_fact_refs"] = [fact_ref]
        source_fact = next(
            item
            for item in memory["known_public_facts"]
            if item["fact_ref"] == fact_ref
        )
        injected_fact = deepcopy(source_fact)
        injected_fact["scenario_id"] = "scenario.never_entered"
        memory["known_public_facts"].append(injected_fact)
    memory["scenario_records"].append(injected_record)
    return catalog, payload


def _catalog_with_public_capacity_facts(
    catalog: ScenarioCatalog, count: int
) -> tuple[ScenarioCatalog, tuple[str, ...]]:
    payload = catalog.model_dump(mode="json")
    definition = payload["scenarios"][0]
    template = next(
        item for item in definition["facts"] if item["fact_id"] == "alpine.fact.weather"
    )
    fact_refs = tuple(f"alpine.fact.capacity-{index:02d}" for index in range(count))
    definition["facts"].extend(
        [{**template, "fact_id": fact_ref} for fact_ref in fact_refs]
    )
    return ScenarioCatalog.model_validate(payload), fact_refs


def _domain_event(
    event_type: MemoryAuthorityEventType, sequence: int
) -> DomainEvent:
    return DomainEvent(
        event_id=f"memory-source.{sequence}",
        session_id=SESSION_ID,
        turn_id=f"turn-{sequence}",
        sequence_no=sequence,
        event_type=event_type.value,
        payload={"ignored": "server envelope payload is not copied"},
        occurred_at=NOW,
    )


def _event(
    event_type: MemoryAuthorityEventType, sequence: int
) -> MemoryAuthoritySource:
    return _issue_memory_authority_source(_domain_event(event_type, sequence))


def _receipt(
    *,
    event_type: str,
    sequence: int,
    turn_id: str,
    state_version: int = STATE_VERSION,
    session_id: str = SESSION_ID,
    payload: dict[str, object] | None = None,
):
    event = DomainEvent(
        event_id=f"persisted-event.{sequence}",
        session_id=session_id,
        turn_id=turn_id,
        sequence_no=sequence,
        event_type=event_type,
        payload=payload or {},
        occurred_at=NOW,
    )
    return _issue_persisted_event_receipt(event, state_version=state_version)


def _start_memory(state, definition, frame, *, sequence: int = 1):
    plan = AuthoritativePlayerMemoryPlanFactory().start_scenario(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        source_event=_event(MemoryAuthorityEventType.SCENARIO_STARTED, sequence),
    )
    _apply(state, plan, definition)
    return plan


def _apply(
    state: GameState,
    plan: MemoryMutationPlan,
    definition: ScenarioDefinition,
) -> None:
    state.apply_memory_plan(
        plan,
        session_id=SESSION_ID,
        state_version=STATE_VERSION,
        scenario_definition=definition,
    )


def _ended():
    catalog, definition, state, _ = _started()
    director = DeterministicStoryDirector()
    investigated = director.advance_after_verified_result(
        state,
        definition,
        (
            _issue_verified_scenario_event(
                event_id="event.signal",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
                deferred_bindings=(
                    FactValueUpdate(fact_id="alpine.fact.route", value="north"),
                ),
            ),
        ),
    )
    ended = director.advance_after_verified_result(
        investigated.candidate_state,
        definition,
        (
            _issue_verified_scenario_event(
                event_id="event.route",
                event_type="route.chosen",
                action_type="move",
                decision_id="alpine.decision.route",
                resolves_current_decision=True,
            ),
        ),
    )
    return catalog, definition, ended.candidate_state, ended.frame


def _assert_json_safe(value: object) -> None:
    assert not isinstance(value, (float, set, frozenset, BaseException))
    if isinstance(value, dict):
        assert all(isinstance(key, str) for key in value)
        for nested in value.values():
            _assert_json_safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_json_safe(nested)
    else:
        assert value is None or type(value) in (bool, int, str)


def test_scenario_record_updates_in_place_and_public_fact_is_idempotent() -> None:
    _, definition, state, frame = _started()
    start = _start_memory(state, definition, frame)
    first = state.to_snapshot()
    _apply(state, start, definition)
    assert state.to_snapshot() == first
    assert len(state.player_memory.scenario_records) == 1

    fact = AuthoritativePlayerMemoryPlanFactory().remember_public_fact(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        fact_ref="alpine.fact.weather",
        source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 2),
    )
    _apply(state, fact, definition)
    changed = state.to_snapshot()
    _apply(state, fact, definition)
    assert state.to_snapshot() == changed
    assert len(state.player_memory.scenario_records) == 1
    assert state.player_memory.scenario_records[0].known_public_fact_refs == (
        "alpine.fact.weather",
    )


def test_scenario_completion_updates_existing_record_without_runtime_copy() -> None:
    _, definition, ended_state, frame = _ended()
    _start_memory(ended_state, definition, frame, sequence=1)
    plan = AuthoritativePlayerMemoryPlanFactory().complete_scenario(
        state=ended_state,
        definition=definition,
        state_version=STATE_VERSION,
        source_event=_event(MemoryAuthorityEventType.SCENARIO_COMPLETED, 2),
    )
    _apply(ended_state, plan, definition)
    record = ended_state.player_memory.scenario_records[0]
    assert record.status.value == "COMPLETED"
    assert record.ending_id == "alpine.ending.arrived"
    dumped = json.dumps(record.model_dump(mode="json"), sort_keys=True)
    for forbidden in ("current_phase", "current_decision", "threat_clock", "NarrativeFrame"):
        assert forbidden not in dumped


def test_npc_identity_uses_definition_not_runtime_id_and_updates_in_place() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    factory = AuthoritativePlayerMemoryPlanFactory()
    encounter = factory.record_npc_encounter(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        runtime_npc_id="alpine-ranger-runtime",
        source_event=_event(MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED, 2),
    )
    _apply(state, encounter, definition)
    _apply(state, encounter, definition)
    assert len(state.player_memory.npc_records) == 1
    record = state.player_memory.npc_records[0]
    assert record.npc_definition_id == "npc.alpine.ranger"
    assert record.subject_key == stable_npc_subject_key(
        "alpine_signal", "npc.alpine.ranger"
    )
    assert "alpine-ranger-runtime" not in record.model_dump_json()

    milestone = factory.update_npc_milestone(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        runtime_npc_id="alpine-ranger-runtime",
        milestone=NpcInteractionMilestone.COOPERATED,
        public_fact_ref="alpine.fact.weather",
        source_event=_event(MemoryAuthorityEventType.NPC_MILESTONE_CONFIRMED, 3),
    )
    _apply(state, milestone, definition)
    _apply(state, milestone, definition)
    assert len(state.player_memory.npc_records) == 1
    assert NpcInteractionMilestone.COOPERATED in state.player_memory.npc_records[0].interaction_milestones


def test_catalog_existence_and_definition_id_do_not_prove_npc_encounter() -> None:
    _, definition, state, frame = _started()
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="does not prove"):
        AuthoritativePlayerMemoryPlanFactory().record_npc_encounter(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            runtime_npc_id="npc.alpine.ranger",
            source_event=_event(MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED, 1),
        )
    assert state.to_snapshot() == before
    assert not state.player_memory.npc_records


def test_npc_subject_key_is_domain_separated_and_rejects_ambiguous_inputs() -> None:
    subject_key = stable_npc_subject_key(
        "alpine_signal", "npc.alpine.ranger"
    )
    legacy_digest = hashlib.sha256(
        b"alpine_signal\0npc.alpine.ranger"
    ).hexdigest()
    assert subject_key != f"npc-subject.{legacy_digest}"
    assert subject_key == stable_npc_subject_key(
        "alpine_signal", "npc.alpine.ranger"
    )
    with pytest.raises(ValidationError):
        stable_npc_subject_key("alpine_signal\0forged", "npc.alpine.ranger")


def test_duplicate_runtime_npc_definition_is_rejected_instead_of_merged() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    original = state.npcs["alpine-ranger-runtime"]
    state.npcs["second-ranger-runtime"] = original.model_copy(
        update={"npc_id": "second-ranger-runtime"}, deep=True
    )
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="not a unique stable subject"):
        AuthoritativePlayerMemoryPlanFactory().record_npc_encounter(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            runtime_npc_id="alpine-ranger-runtime",
            source_event=_event(
                MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED, 2
            ),
        )
    assert state.to_snapshot() == before


def test_hidden_fact_and_future_ending_cannot_enter_memory() -> None:
    _, definition, state, frame = _started()
    factory = AuthoritativePlayerMemoryPlanFactory()
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="not confirmed player-known"):
        factory.remember_public_fact(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            fact_ref="alpine.fact.signal_origin",
            source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 1),
        )
    with pytest.raises(ValueError, match="completed scenario"):
        factory.complete_scenario(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            source_event=_event(MemoryAuthorityEventType.SCENARIO_COMPLETED, 1),
        )
    assert state.to_snapshot() == before


def test_unbound_deferred_fact_is_not_remembered_from_clue_id_alone() -> None:
    catalog = mini_catalog()
    payload = catalog.scenarios[0].model_dump(mode="json")
    payload["clues"][0]["supports_fact_ids"] = ["alpine.fact.route"]
    definition = type(catalog.scenarios[0]).model_validate(payload)
    director = DeterministicStoryDirector()
    started = director.start_scenario(state_for(catalog), definition)
    discovered = director.advance_after_verified_result(
        started.candidate_state,
        definition,
        (
            _issue_verified_scenario_event(
                event_id="event.signal-without-binding",
                event_type="signal.verified",
                action_type="investigate",
                discovered_clue_ids=("alpine.clue.signal_trace",),
            ),
        ),
    )
    state = discovered.candidate_state
    _start_memory(state, definition, discovered.frame)
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="not confirmed player-known"):
        AuthoritativePlayerMemoryPlanFactory().remember_public_fact(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            fact_ref="alpine.fact.route",
            source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 2),
        )
    assert state.to_snapshot() == before


def test_significant_experience_is_closed_structured_and_idempotent() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    plan = AuthoritativePlayerMemoryPlanFactory().record_significant_experience(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        category=SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
        runtime_npc_id="alpine-ranger-runtime",
        source_event=_event(
            MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED, 2
        ),
    )
    _apply(state, plan, definition)
    snapshot = state.to_snapshot()
    _apply(state, plan, definition)
    assert state.to_snapshot() == snapshot
    entry = state.player_memory.significant_experiences[0]
    assert entry.summary.value == "IMPORTANT_NPC_MET"
    assert "narrative_text" not in entry.model_dump_json()
    assert "ignored" not in entry.model_dump_json()


def test_experience_identity_binds_all_refs_and_source_reuse_conflicts() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    factory = AuthoritativePlayerMemoryPlanFactory()
    source = _event(
        MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED, 2
    )
    first = factory.record_significant_experience(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        category=SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
        public_fact_ref="alpine.fact.weather",
        source_event=source,
    )
    different_content = factory.record_significant_experience(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        category=SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
        public_fact_ref="alpine.fact.beacon_active",
        source_event=source,
    )
    assert first.experience is not None
    assert different_content.experience is not None
    assert first.experience.entry_id != different_content.experience.entry_id

    _apply(state, first, definition)
    before = state.to_snapshot()
    with pytest.raises(MemoryConflictError, match="source event"):
        factory.record_significant_experience(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            category=SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
            public_fact_ref="alpine.fact.beacon_active",
            source_event=source,
        )
    assert state.to_snapshot() == before


def test_significant_experience_capacity_is_explicit_and_atomic() -> None:
    _, definition, state, frame = _started()
    factory = AuthoritativePlayerMemoryPlanFactory()
    _start_memory(state, definition, frame)
    for sequence in range(2, MAX_SIGNIFICANT_EXPERIENCES + 2):
        _apply(
            state,
            factory.record_significant_experience(
                state=state,
                definition=definition,
                state_version=STATE_VERSION,
                category=SignificantExperienceCategory.SCENARIO_BEGIN,
                source_event=_event(
                    MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED,
                    sequence,
                ),
            ),
            definition,
        )
    before = state.to_snapshot()
    with pytest.raises(MemoryCapacityError, match="capacity"):
        factory.record_significant_experience(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            category=SignificantExperienceCategory.SCENARIO_BEGIN,
            source_event=_event(
                MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED,
                MAX_SIGNIFICANT_EXPERIENCES + 2,
            ),
        )
    assert state.to_snapshot() == before


def test_plan_is_sealed_not_json_constructible_and_tampering_is_atomic() -> None:
    _, definition, state, frame = _started()
    plan = AuthoritativePlayerMemoryPlanFactory().start_scenario(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        source_event=_event(MemoryAuthorityEventType.SCENARIO_STARTED, 1),
    )
    with pytest.raises(TypeError):
        MemoryMutationPlan(kind="START_SCENARIO")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        TypeAdapter(MemoryMutationPlan).validate_python(
            {
                name: getattr(plan, name)
                for name in plan.__slots__
                if not name.startswith("_")
            }
        )
    object.__setattr__(plan, "scenario_id", "forged-scenario")
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="forged|stale|bound"):
        _apply(state, plan, definition)
    assert state.to_snapshot() == before


def test_plan_copy_pickle_and_nested_tampering_cannot_preserve_authority() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    plan = AuthoritativePlayerMemoryPlanFactory().record_significant_experience(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        category=SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
        public_fact_ref="alpine.fact.weather",
        source_event=_event(
            MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED, 2
        ),
    )
    assert not hasattr(plan, "model_copy")
    assert copy(plan) is plan
    assert deepcopy(plan).is_authentic() is False
    assert pickle.loads(pickle.dumps(plan)).is_authentic() is False
    cloned = object.__new__(MemoryMutationPlan)
    for name in plan.__slots__:
        object.__setattr__(cloned, name, getattr(plan, name))
    assert cloned.is_authentic() is False
    assert plan.experience is not None
    object.__setattr__(plan.experience, "public_fact_refs", ("forged.fact",))
    assert plan.is_authentic() is False
    before = state.to_snapshot()
    with pytest.raises(ValueError, match="forged|stale|bound"):
        _apply(state, plan, definition)
    assert state.to_snapshot() == before


def test_plan_is_bound_to_session_version_and_full_authoritative_state() -> None:
    _, definition, state, frame = _started()
    plan = AuthoritativePlayerMemoryPlanFactory().start_scenario(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        source_event=_event(MemoryAuthorityEventType.SCENARIO_STARTED, 1),
    )
    before = state.to_snapshot()
    for session_id, state_version in (
        ("another-session", STATE_VERSION),
        (SESSION_ID, STATE_VERSION + 1),
        ):
        with pytest.raises(ValueError, match="forged|stale|bound"):
            state.apply_memory_plan(
                plan,
                session_id=session_id,
                state_version=state_version,
                scenario_definition=definition,
            )
        assert state.to_snapshot() == before

    changed_definition_payload = definition.model_dump(mode="json")
    changed_definition_payload["title"] = "Same version, different content"
    changed_definition = ScenarioDefinition.model_validate(
        changed_definition_payload
    )
    with pytest.raises(ValueError, match="forged|stale|bound"):
        state.apply_memory_plan(
            plan,
            session_id=SESSION_ID,
            state_version=STATE_VERSION,
            scenario_definition=changed_definition,
        )
    assert state.to_snapshot() == before

    _, _, another_state, _ = _started()
    another_state.player.player_id = "another-player"
    another_before = another_state.to_snapshot()
    with pytest.raises(ValueError, match="forged|stale|bound"):
        _apply(another_state, plan, definition)
    assert another_state.to_snapshot() == another_before

    state.player.player_id = "changed-player"
    changed_before = state.to_snapshot()
    with pytest.raises(ValueError, match="forged|stale|bound"):
        _apply(state, plan, definition)
    assert state.to_snapshot() == changed_before


def test_phase_23a_rejects_a_second_run_of_the_same_scenario_identity() -> None:
    _, definition, state, frame = _started()
    first = _start_memory(state, definition, frame)
    after_first = state.to_snapshot()
    _apply(state, first, definition)
    assert state.to_snapshot() == after_first
    with pytest.raises(ValueError, match="does not support replaying"):
        AuthoritativePlayerMemoryPlanFactory().start_scenario(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            source_event=_event(MemoryAuthorityEventType.SCENARIO_STARTED, 2),
        )
    assert state.to_snapshot() == after_first

    runtime = state.scenario_runtime
    assert runtime is not None
    runtime.scenario_content_version = "alpine-signal-2"
    changed_definition = definition.model_copy(
        update={"content_version": "alpine-signal-2"}
    )
    changed_before = state.to_snapshot()
    with pytest.raises(MemoryConflictError, match="content version"):
        AuthoritativePlayerMemoryPlanFactory().start_scenario(
            state=state,
            definition=changed_definition,
            state_version=STATE_VERSION,
            source_event=_event(MemoryAuthorityEventType.SCENARIO_STARTED, 3),
        )
    assert state.to_snapshot() == changed_before


def test_out_of_order_memory_mutations_fail_before_state_change() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame, sequence=10)
    before = state.to_snapshot()
    factory = AuthoritativePlayerMemoryPlanFactory()
    operations = (
        lambda: factory.record_npc_encounter(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            runtime_npc_id="alpine-ranger-runtime",
            source_event=_event(
                MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED, 9
            ),
        ),
        lambda: factory.remember_public_fact(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            fact_ref="alpine.fact.weather",
            source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 8),
        ),
        lambda: factory.record_significant_experience(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            category=SignificantExperienceCategory.SCENARIO_BEGIN,
            source_event=_event(
                MemoryAuthorityEventType.SIGNIFICANT_EXPERIENCE_CONFIRMED, 7
            ),
        ),
    )
    for operation in operations:
        with pytest.raises(MemoryConflictError, match="stale"):
            operation()
        assert state.to_snapshot() == before


def test_application_package_does_not_export_memory_plan_issuer() -> None:
    import deviation_protocol.application as application_package

    assert not hasattr(
        application_package, "AuthoritativePlayerMemoryPlanFactory"
    )
    assert not hasattr(application_package, "MemoryAuthoritySource")


def test_plain_domain_event_json_and_copied_source_cannot_issue_a_plan() -> None:
    _, definition, state, _ = _started()
    source = _event(MemoryAuthorityEventType.SCENARIO_STARTED, 1)
    with pytest.raises(TypeError):
        MemoryAuthoritySource(  # type: ignore[call-arg]
            event_id=source.event_id,
            session_id=source.session_id,
            sequence_no=source.sequence_no,
            event_type=source.event_type,
        )
    with pytest.raises(ValidationError):
        TypeAdapter(MemoryAuthoritySource).validate_python(
            {
                "event_id": source.event_id,
                "session_id": source.session_id,
                "sequence_no": source.sequence_no,
                "event_type": source.event_type.value,
            }
        )
    assert deepcopy(source).is_authentic() is False
    assert copy(source) is source
    assert pickle.loads(pickle.dumps(source)).is_authentic() is False
    cloned_source = object.__new__(MemoryAuthoritySource)
    for name in source.__slots__:
        object.__setattr__(cloned_source, name, getattr(source, name))
    assert cloned_source.is_authentic() is False

    before = state.to_snapshot()
    with pytest.raises(ValueError, match="server-issued authority"):
        AuthoritativePlayerMemoryPlanFactory().start_scenario(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            source_event=_domain_event(
                MemoryAuthorityEventType.SCENARIO_STARTED, 1
            ),  # type: ignore[arg-type]
        )
    assert state.to_snapshot() == before

    with pytest.raises(ValueError, match="does not match the mutation kind"):
        _issue_memory_mutation(
            memory_state=state.player_memory,
            authority_source=source,
            state_version=STATE_VERSION,
            non_memory_state_fingerprint=state.memory_authority_fingerprint(),
            scenario_definition_fingerprint=scenario_definition_fingerprint(
                definition
            ),
            kind=MemoryMutationKind.COMPLETE_SCENARIO,
            scenario_id="alpine_signal",
            scenario_content_version="alpine-signal-1",
            ending_id="alpine.ending.arrived",
        )
    assert state.to_snapshot() == before


def test_mutable_source_event_payload_is_never_shared_or_copied_to_memory() -> None:
    _, definition, state, _ = _started()
    envelope = _domain_event(MemoryAuthorityEventType.SCENARIO_STARTED, 1)
    source = _issue_memory_authority_source(envelope)
    plan = AuthoritativePlayerMemoryPlanFactory().start_scenario(
        state=state,
        definition=definition,
        state_version=STATE_VERSION,
        source_event=source,
    )
    envelope.payload["ignored"] = {"later": "mutation"}
    _apply(state, plan, definition)
    encoded = state.player_memory.model_dump_json()
    assert "later" not in encoded
    assert "mutation" not in encoded


def test_player_and_model_shapes_have_no_memory_write_fields() -> None:
    action = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "client_request_id": "request-1",
        "action_type": ActionType.MOVE,
        "description": "remember ending",
        "memory_source": "memory-source.1",
    }
    with pytest.raises(ValidationError, match="memory_source"):
        ActionSubmission.model_validate(action)
    with pytest.raises(ValidationError, match="important_experience"):
        NarrativeProposalPayload.model_validate(
            {
                "schema_version": "narrative-proposal-v1",
                "narrative_text": "只是候选文本",
                "continuity_notes": ["请记住隐藏结局"],
                "important_experience": True,
            }
        )
    assert "player_memory" not in ValidatedNarrativeProposal.model_fields
    assert not {
        "memory", "importance", "relationship", "milestone", "ending_id",
        "known_fact", "event_id", "memory_source", "memory_version",
    } & set(ActionRequest.model_fields)
    factory = AuthoritativePlayerMemoryPlanFactory()
    for method in (
        factory.start_scenario,
        factory.complete_scenario,
        factory.record_npc_encounter,
        factory.update_npc_milestone,
        factory.remember_public_fact,
        factory.record_significant_experience,
    ):
        assert "frame" not in inspect.signature(method).parameters


@pytest.mark.parametrize(
    "action_type", [ActionType.MOVE, ActionType.OBSERVE, ActionType.INSPECT_STATUS]
)
def test_ordinary_actions_and_continuity_text_do_not_create_memory(action_type) -> None:
    _, _, state, _ = _started()
    before = state.to_snapshot()
    ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-1",
        action_type=action_type,
        description="这是普通行动，不是重要经历",
    )
    NarrativeProposalPayload(
        schema_version="narrative-proposal-v1",
        narrative_text="结构合法但不具备事实权威。",
        continuity_notes=("请把这段话记成长期关系",),
    )
    assert state.to_snapshot() == before


def test_memory_contains_no_duplicate_current_character_state() -> None:
    catalog, definition, state, frame = _started()
    state.player.attributes["strength"] = 9
    state.player.wallet.balances["credits"] = 77
    _start_memory(state, definition, frame)
    memory = state.to_snapshot()["player_memory"]
    forbidden = {
        "attributes", "resources", "wallet", "inventory", "equipment",
        "skills", "balances", "current_phase_id", "current_decision_id",
        "threat_clocks", "npcs",
    }
    assert not forbidden & set(_all_keys(memory))
    assert state.content_version == catalog.content_version


def test_detached_copy_deeply_isolates_memory() -> None:
    catalog, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    copied = state.detached_copy(catalog.content_catalog)
    fact = AuthoritativePlayerMemoryPlanFactory().remember_public_fact(
        state=copied,
        definition=definition,
        state_version=STATE_VERSION,
        fact_ref="alpine.fact.weather",
        source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 2),
    )
    _apply(copied, fact, definition)
    assert copied.player_memory != state.player_memory
    assert not state.player_memory.known_public_facts


def test_projection_is_stable_bounded_frozen_and_deeply_isolated() -> None:
    catalog, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    factory = AuthoritativePlayerMemoryPlanFactory()
    _apply(
        state,
        factory.remember_public_fact(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            fact_ref="alpine.fact.weather",
            source_event=_event(MemoryAuthorityEventType.PUBLIC_FACT_CONFIRMED, 2),
        ),
        definition,
    )
    projector = PlayerMemoryProjector()
    first = projector.project(state, catalog)
    second = projector.project(state, catalog)
    assert first == second
    encoded = first.model_dump_json()
    assert first.known_public_facts[0].scenario_id == "alpine_signal"
    assert first.known_public_facts[0].fact_ref == "alpine.fact.weather"
    assert len(encoded.encode("utf-8")) <= MAX_MEMORY_PROJECTION_JSON_BYTES
    assert len(encoded) <= MAX_MEMORY_PROJECTION_CHARACTERS
    with pytest.raises(ValidationError):
        first.scenarios[0].scenario_id = "changed"  # type: ignore[misc]

    state.player_memory = state.player_memory.mark_rebuild_required(
        source_sequence_no=3,
        source_event_id="memory-source.3",
    )
    assert first.complete is True
    assert projector.project(state, catalog).complete is False
    for forbidden in (
        "event_id", "source_sequence", "capability", "seal", "action_signature",
        "outcome_token", "policy_trace", "scenario_runtime", "narrative_text",
        "signal_origin", "alpine.ending.arrived",
    ):
        assert forbidden not in encoded


def test_memory_integrity_rejects_unknown_and_not_encountered_npcs() -> None:
    catalog, _, state = _production_started_with_memory()
    source_event_id = state.player_memory.last_applied_source_event_id
    assert source_event_id is not None
    for npc_definition_id in (
        "npc.death_certificate.not_in_catalog",
        "npc.death_certificate.triage_coordinator",
    ):
        payload = state.to_snapshot()
        payload["player_memory"]["npc_records"] = [
            {
                "subject_key": stable_npc_subject_key(
                    "death_certificate", npc_definition_id
                ),
                "scenario_id": "death_certificate",
                "npc_definition_id": npc_definition_id,
                "encountered": True,
                "interaction_milestones": ["FIRST_ENCOUNTER"],
                "known_public_fact_refs": [],
                "last_source_event_id": source_event_id,
                "last_source_sequence_no": 1,
            }
        ]
        with pytest.raises(DomainRuleViolation):
            GameState.from_snapshot(
                payload,
                catalog=catalog.content_catalog,
                scenario_catalog=catalog,
            )

    structurally_valid = GameState.model_validate(payload)
    with pytest.raises(DomainRuleViolation):
        PlayerMemoryProjector().project(structurally_valid, catalog)


@pytest.mark.parametrize(
    ("scenario_id", "content_version"),
    [
        ("scenario.not_in_catalog", "death-certificate-1.0.0"),
        ("death_certificate", "content.wrong-version"),
    ],
)
def test_memory_integrity_rejects_unknown_scenario_or_content_version(
    scenario_id: str, content_version: str
) -> None:
    catalog, _, state = _production_started_with_memory()
    payload = state.to_snapshot()
    payload["player_memory"] = {
        "memory_model_version": 2,
        "sync_status": "CURRENT",
        "last_applied_source_sequence_no": 1,
        "last_applied_source_event_id": "event.memory-start",
        "first_deferred_source_sequence_no": None,
        "last_deferred_source_sequence_no": None,
        "deferred_event_count": 0,
        "scenario_records": [
            {
                "scenario_id": scenario_id,
                "scenario_content_version": content_version,
                "status": "STARTED",
                "ending_id": None,
                "milestone_refs": ["STARTED"],
                "known_public_fact_refs": [],
                "last_source_event_id": "event.memory-start",
                "last_source_sequence_no": 1,
            }
        ],
        "npc_records": [],
        "significant_experiences": [],
        "known_public_facts": [],
    }

    with pytest.raises(DomainRuleViolation):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_memory_integrity_rejects_hidden_fact_and_unfinished_ending() -> None:
    catalog, definition, state = _production_started_with_memory()
    hidden_fact = next(
        item.fact_id
        for item in definition.facts
        if item.visibility.value == "DISCOVERABLE"
        and item.fact_id != "death_certificate.fact.player_is_alive"
    )
    hidden_payload = state.to_snapshot()
    old_fact = hidden_payload["player_memory"]["known_public_facts"][0]["fact_ref"]
    hidden_payload["player_memory"]["known_public_facts"][0]["fact_ref"] = hidden_fact
    scenario_facts = hidden_payload["player_memory"]["scenario_records"][0][
        "known_public_fact_refs"
    ]
    scenario_facts[scenario_facts.index(old_fact)] = hidden_fact
    with pytest.raises(DomainRuleViolation):
        GameState.from_snapshot(
            hidden_payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )

    ending_payload = state.to_snapshot()
    scenario_record = ending_payload["player_memory"]["scenario_records"][0]
    scenario_record.update(
        {
            "status": "COMPLETED",
            "ending_id": definition.endings[0].ending_id,
            "milestone_refs": [
                "STARTED",
                "IMPORTANT_FACT_CONFIRMED",
                "COMPLETED",
                "ENDING_CONFIRMED",
            ],
        }
    )
    with pytest.raises(DomainRuleViolation, match="ending"):
        GameState.from_snapshot(
            ending_payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_initial_public_memory_and_authoritatively_learned_npc_fact_pass() -> None:
    catalog, definition, state = _production_started_with_memory()
    restored = GameState.from_snapshot(
        state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    assert len(restored.player_memory.known_public_facts) == 7
    initial_projection = PlayerMemoryProjector().project(restored, catalog)
    assert len(initial_projection.known_public_facts) == 7

    _, _, learned = _production_success_memory()
    validated = GameState.from_snapshot(
        learned.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    projection = PlayerMemoryProjector().project(validated, catalog)
    assert projection.npcs[0].npc_definition_id == (
        "npc.death_certificate.triage_coordinator"
    )
    assert "death_certificate.fact.player_is_alive" in {
        item.fact_ref for item in projection.known_public_facts
    }
    evidence = validated.scenario_runtime.narrative_outcome_evidence
    assert tuple(item.model_dump(mode="json") for item in evidence) == (
        {
            "outcome_rule_id": "death_certificate.outcome.purposeful_life_signal",
            "outcome_result": "SUCCESS",
            "scenario_event_type": "vitals.verified",
                "npc_definition_ids": [
                    "npc.death_certificate.triage_coordinator"
                ],
                "player_alive_acknowledgement_npc_definition_ids": [
                    "npc.death_certificate.triage_coordinator"
                ],
                "player_alive_acknowledgement_npc_ids": ["runtime-npc-1"],
        },
    )


def test_missing_runtime_rejects_nonempty_memory_with_player_known_facts() -> None:
    catalog, _, state = _production_started_with_memory()
    payload = state.to_snapshot()
    payload["scenario_runtime"] = None
    payload["player_memory"]["significant_experiences"] = []

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_unparticipated_scenario_record_and_player_known_fact_are_rejected() -> None:
    catalog, payload = _unparticipated_scenario_memory_payload(
        include_player_known_fact=True
    )

    with pytest.raises(DomainRuleViolation, match="scenario.never_entered"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_unparticipated_scenario_record_without_facts_is_rejected() -> None:
    catalog, payload = _unparticipated_scenario_memory_payload(
        include_player_known_fact=False
    )

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_projector_rejects_unparticipated_scenario_memory() -> None:
    catalog, payload = _unparticipated_scenario_memory_payload(
        include_player_known_fact=True
    )
    structurally_valid = GameState.model_validate(payload)

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        PlayerMemoryProjector().project(structurally_valid, catalog)


def test_missing_runtime_rejects_undiscovered_fact_memory() -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    payload["scenario_runtime"] = None
    payload["player_memory"]["npc_records"] = []
    payload["player_memory"]["significant_experiences"] = []

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_missing_runtime_rejects_npc_memory_and_projector_refuses_it() -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    payload["scenario_runtime"] = None
    payload["player_memory"]["significant_experiences"] = []
    dynamic_fact = "death_certificate.fact.player_is_alive"
    payload["player_memory"]["known_public_facts"] = [
        item
        for item in payload["player_memory"]["known_public_facts"]
        if item["fact_ref"] != dynamic_fact
    ]
    record = payload["player_memory"]["scenario_records"][0]
    record["known_public_fact_refs"].remove(dynamic_fact)
    structurally_valid = GameState.model_validate(payload)

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )
    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        PlayerMemoryProjector().project(structurally_valid, catalog)


def test_missing_runtime_rejects_ending_memory() -> None:
    catalog, definition, state = _production_started_with_memory()
    payload = state.to_snapshot()
    payload["scenario_runtime"] = None
    payload["player_memory"]["significant_experiences"] = []
    record = payload["player_memory"]["scenario_records"][0]
    record.update(
        {
            "status": "COMPLETED",
            "ending_id": definition.endings[0].ending_id,
            "milestone_refs": [
                "STARTED",
                "IMPORTANT_FACT_CONFIRMED",
                "COMPLETED",
                "ENDING_CONFIRMED",
            ],
        }
    )

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_missing_runtime_rejects_dynamic_experience() -> None:
    catalog, _, state = _production_started_with_memory()
    payload = state.to_snapshot()
    payload["scenario_runtime"] = None

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_missing_runtime_rejects_dynamic_npc_milestone() -> None:
    catalog, _, learned = _production_success_memory()
    catalog_payload = catalog.model_dump(mode="json")
    catalog_payload["scenarios"][0]["memory_rules"].append(
        {
            "rule_id": "death_certificate.memory.41_cooperated",
            "rule_version": "1.0.0",
            "source_event_type": "NarrativeOutcomeAccepted",
            "operation": "UPDATE_NPC_MILESTONE",
            "required_narrative_outcome_rule_ids": [
                "death_certificate.outcome.purposeful_life_signal"
            ],
            "required_scenario_event_types": ["vitals.verified"],
            "required_outcome_results": ["SUCCESS"],
            "npc_definition_id": "npc.death_certificate.triage_coordinator",
            "npc_milestone": "COOPERATED",
        }
    )
    catalog = ScenarioCatalog.model_validate(catalog_payload)
    payload = learned.to_snapshot()
    payload["player_memory"]["npc_records"][0]["interaction_milestones"].append(
        "COOPERATED"
    )
    GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    payload["player_memory"]["significant_experiences"] = []
    dynamic_fact = "death_certificate.fact.player_is_alive"
    payload["player_memory"]["known_public_facts"] = [
        item
        for item in payload["player_memory"]["known_public_facts"]
        if item["fact_ref"] != dynamic_fact
    ]
    payload["player_memory"]["scenario_records"][0][
        "known_public_fact_refs"
    ].remove(dynamic_fact)
    payload["scenario_runtime"] = None

    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


@pytest.mark.parametrize(
    ("result", "event_type"),
    [
        ("FAILURE", "vitals.signal.failed"),
        ("AMBIGUOUS", "vitals.signal.ambiguous"),
    ],
)
def test_success_only_npc_memory_rejects_other_once_rule_results(
    result: str, event_type: str
) -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    payload["player_memory"]["significant_experiences"] = []
    dynamic_fact = "death_certificate.fact.player_is_alive"
    payload["player_memory"]["known_public_facts"] = [
        item
        for item in payload["player_memory"]["known_public_facts"]
        if item["fact_ref"] != dynamic_fact
    ]
    payload["player_memory"]["scenario_records"][0][
        "known_public_fact_refs"
    ].remove(dynamic_fact)
    evidence = payload["scenario_runtime"]["narrative_outcome_evidence"][0]
    evidence["outcome_result"] = result
    evidence["scenario_event_type"] = event_type
    evidence["player_alive_acknowledgement_npc_definition_ids"] = []
    evidence["player_alive_acknowledgement_npc_ids"] = []

    with pytest.raises(DomainRuleViolation, match="was not encountered"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_player_alive_acknowledgement_rejects_unknown_runtime_npc_id() -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    evidence = payload["scenario_runtime"]["narrative_outcome_evidence"][0]
    evidence["player_alive_acknowledgement_npc_ids"].append(
        "zz-missing-runtime-npc"
    )

    with pytest.raises(ValueError, match="unknown runtime NPC"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


@pytest.mark.parametrize(
    ("result", "event_type"),
    [
        ("SUCCESS", "vitals.signal.failed"),
        ("FAILURE", "vitals.verified"),
    ],
)
def test_outcome_evidence_rejects_mismatched_result_event_pair(
    result: str, event_type: str
) -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    evidence = payload["scenario_runtime"]["narrative_outcome_evidence"][0]
    evidence["outcome_result"] = result
    evidence["scenario_event_type"] = event_type

    with pytest.raises(ValueError, match="mismatched event type"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_success_only_npc_memory_requires_matching_evidence_target() -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    payload["scenario_runtime"]["narrative_outcome_evidence"][0][
        "npc_definition_ids"
    ] = []

    with pytest.raises(DomainRuleViolation, match="was not encountered"):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_old_snapshot_without_outcome_evidence_loads_only_without_dynamic_memory() -> None:
    catalog, _, state = _production_started_with_memory()
    payload = state.to_snapshot()
    payload["scenario_runtime"].pop("narrative_outcome_evidence")
    payload["player_memory"]["significant_experiences"] = []

    restored = GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    assert restored.scenario_runtime.narrative_outcome_evidence == ()


def test_old_snapshot_claiming_dynamic_memory_without_evidence_is_rejected() -> None:
    catalog, _, learned = _production_success_memory()
    payload = learned.to_snapshot()
    payload["scenario_runtime"].pop("narrative_outcome_evidence")

    with pytest.raises(DomainRuleViolation):
        GameState.from_snapshot(
            payload,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
        )


def test_multi_scenario_memory_shape_is_retained_but_requires_participation() -> None:
    catalog, definition, state, _ = _started()
    scenario_ids = (
        definition.scenario_id,
        *(f"memory-scenario-{index:02d}" for index in range(16)),
    )
    catalog = _catalog_with_scenario_clones(catalog, scenario_ids)
    payload = state.to_snapshot()
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": scenario_id,
            "scenario_content_version": definition.content_version,
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": f"memory-source-{index:02d}",
            "last_source_sequence_no": index + 1,
        }
        for index, scenario_id in enumerate(scenario_ids)
    ]
    payload["player_memory"]["last_applied_source_sequence_no"] = 17
    payload["player_memory"]["last_applied_source_event_id"] = "memory-source-16"
    structurally_valid = GameState.model_validate(payload)

    assert len(structurally_valid.player_memory.scenario_records) == 17
    with pytest.raises(DomainRuleViolation, match="runtime participation"):
        PlayerMemoryProjector().project(structurally_valid, catalog)


def test_projection_enforces_real_character_and_utf8_byte_budgets() -> None:
    catalog, definition, state, _ = _started()
    scenario_id = "scenario." + "s" * 119
    catalog = _catalog_with_scenario_clones(
        catalog, (scenario_id,), scenario_begin_experience=True
    )
    payload = state.to_snapshot()
    payload["scenario_runtime"]["scenario_id"] = scenario_id
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": scenario_id,
            "scenario_content_version": definition.content_version,
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": "event.start",
            "last_source_sequence_no": 1,
        }
    ]
    experiences = []
    for occurrence in range(100):
        sequence = occurrence + 2
        source_event_id = f"event.begin.{occurrence:03d}." + "e" * 100
        entry_id = stable_significant_experience_id(
            source_event_id=source_event_id,
            scenario_id=scenario_id,
            category=SignificantExperienceCategory.SCENARIO_BEGIN,
            subject_refs=(),
            public_fact_refs=(),
        )
        experiences.append(
            {
                "entry_id": entry_id,
                "scenario_id": scenario_id,
                "category": "SCENARIO_BEGIN",
                "summary": "SCENARIO_BEGAN",
                "subject_refs": [],
                "public_fact_refs": [],
                "source_event_id": source_event_id,
                "source_sequence_no": sequence,
            }
        )
    payload["player_memory"]["significant_experiences"] = experiences
    payload["player_memory"]["last_applied_source_sequence_no"] = 101
    payload["player_memory"]["last_applied_source_event_id"] = experiences[-1][
        "source_event_id"
    ]
    restored = GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    projector = PlayerMemoryProjector()
    first = projector.project(restored, catalog)
    second = projector.project(restored, catalog)
    projection_payload = first.model_dump(mode="json")
    serialized = json.dumps(
        projection_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    encoded = serialized.encode("utf-8")
    assert first == second
    assert first.truncated is True
    assert len(first.significant_experiences) < 64
    assert len(encoded) <= MAX_MEMORY_PROJECTION_JSON_BYTES
    assert len(serialized) <= MAX_MEMORY_PROJECTION_CHARACTERS
    with pytest.raises(ValidationError):
        PlayerMemoryProjection.model_validate(
            {
                "known_public_facts": [
                    {"scenario_id": "场景", "fact_ref": "fact.public"}
                ]
            }
        )


def test_memory_snapshot_json_has_no_float_exception_set_or_internal_object() -> None:
    _, definition, state, frame = _started()
    _start_memory(state, definition, frame)
    snapshot = state.to_snapshot()
    _assert_json_safe(snapshot["player_memory"])
    assert json.loads(json.dumps(snapshot, allow_nan=False)) == snapshot


def test_non_hospital_memory_rule_requires_an_authentic_bound_receipt() -> None:
    catalog, definition, state, _ = _started()
    payload = definition.model_dump(mode="json")
    payload["memory_rules"] = [
        {
            "rule_id": "alpine.memory.started",
            "rule_version": "1.0.0",
            "source_event_type": "ScenarioStarted",
            "operation": "START_SCENARIO",
        }
    ]
    definition = ScenarioDefinition.model_validate(payload)
    receipt = _receipt(
        event_type="ScenarioStarted",
        sequence=1,
        turn_id="session-created",
        payload={
            "scenario_id": definition.scenario_id,
            "scenario_content_version": definition.content_version,
        },
    )
    engine = DeclarativePlayerMemoryRuleEngine()
    applied = engine.apply(
        state=state,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="session-created",
        state_version=STATE_VERSION,
        receipts=(receipt,),
    )
    assert len(applied.player_memory.scenario_records) == 1
    assert state.player_memory.scenario_records == ()

    for changes in (
        {"session_id": "another-session"},
        {"turn_id": "another-turn"},
        {"state_version": STATE_VERSION + 1},
        {"sequence_no": 2},
        {"event_type": "NarrativeOutcomeAccepted"},
        {"payload_digest": "0" * 64},
    ):
        tampered = object.__new__(PersistedEventReceipt)
        for field_name in (
            "session_id",
            "event_id",
            "sequence_no",
            "turn_id",
            "state_version",
            "event_type",
            "payload_digest",
            "_payload",
            "_seal",
        ):
            object.__setattr__(tampered, field_name, getattr(receipt, field_name))
        for name, value in changes.items():
            object.__setattr__(tampered, name, value)
        with pytest.raises(ValueError, match="receipt"):
            engine.apply(
                state=state,
                definition=definition,
                session_id=SESSION_ID,
                turn_id="session-created",
                state_version=STATE_VERSION,
                receipts=(tampered,),
            )
    for foreign in (
        _receipt(
            event_type="ScenarioStarted",
            sequence=1,
            turn_id="session-created",
            session_id="another-session",
            payload={
                "scenario_id": definition.scenario_id,
                "scenario_content_version": definition.content_version,
            },
        ),
        _receipt(
            event_type="ScenarioStarted",
            sequence=1,
            turn_id="another-turn",
            payload={
                "scenario_id": definition.scenario_id,
                "scenario_content_version": definition.content_version,
            },
        ),
        _receipt(
            event_type="ScenarioStarted",
            sequence=1,
            turn_id="session-created",
            state_version=STATE_VERSION + 1,
            payload={
                "scenario_id": definition.scenario_id,
                "scenario_content_version": definition.content_version,
            },
        ),
    ):
        assert foreign.is_authentic()
        with pytest.raises(ValueError, match="bound"):
            engine.apply(
                state=state,
                definition=definition,
                session_id=SESSION_ID,
                turn_id="session-created",
                state_version=STATE_VERSION,
                receipts=(foreign,),
            )
    with pytest.raises(ValueError, match="receipt"):
        engine.apply(
            state=state,
            definition=definition,
            session_id=SESSION_ID,
            turn_id="session-created",
            state_version=STATE_VERSION,
            receipts=("ScenarioStarted",),  # type: ignore[arg-type]
        )


def test_one_event_multiple_rules_are_atomic_on_later_rule_failure() -> None:
    _, definition, state, _ = _started()
    started_payload = definition.model_dump(mode="json")
    started_payload["memory_rules"] = [
        {
            "rule_id": "alpine.memory.00_started",
            "rule_version": "1.0.0",
            "source_event_type": "ScenarioStarted",
            "operation": "START_SCENARIO",
        }
    ]
    started_definition = ScenarioDefinition.model_validate(started_payload)
    engine = DeclarativePlayerMemoryRuleEngine()
    state = engine.apply(
        state=state,
        definition=started_definition,
        session_id=SESSION_ID,
        turn_id="session-created",
        state_version=STATE_VERSION,
        receipts=(
            _receipt(
                event_type="ScenarioStarted",
                sequence=1,
                turn_id="session-created",
                payload={
                    "scenario_id": definition.scenario_id,
                    "scenario_content_version": definition.content_version,
                },
            ),
        ),
    )
    failing_payload = definition.model_dump(mode="json")
    failing_payload["memory_rules"] = [
        {
            "rule_id": "alpine.memory.10_fact",
            "rule_version": "1.0.0",
            "source_event_type": "NarrativeOutcomeAccepted",
            "operation": "REMEMBER_PUBLIC_FACT",
            "public_fact_id": "alpine.fact.weather",
        },
        {
            "rule_id": "alpine.memory.20_missing_encounter",
            "rule_version": "1.0.0",
            "source_event_type": "NarrativeOutcomeAccepted",
            "operation": "UPDATE_NPC_MILESTONE",
            "npc_definition_id": "npc.alpine.ranger",
            "npc_milestone": "COOPERATED",
        },
    ]
    failing_definition = ScenarioDefinition.model_validate(failing_payload)
    before = state.to_snapshot()
    with pytest.raises(MemoryConflictError, match="encountered"):
        engine.apply(
            state=state,
            definition=failing_definition,
            session_id=SESSION_ID,
            turn_id="turn-2",
            state_version=STATE_VERSION,
            receipts=(
                _receipt(
                    event_type="NarrativeOutcomeAccepted",
                    sequence=2,
                    turn_id="turn-2",
                    payload={"npc_definition_ids": ("npc.alpine.ranger",)},
                ),
            ),
        )
    assert state.to_snapshot() == before


def test_trusted_decision_event_can_complete_scenario_but_not_invent_world_success() -> None:
    _, definition, ended_state, _ = _ended()
    payload = definition.model_dump(mode="json")
    payload["memory_rules"] = [
        {
            "rule_id": "alpine.memory.00_started",
            "rule_version": "1.0.0",
            "source_event_type": "ScenarioStarted",
            "operation": "START_SCENARIO",
        },
        {
            "rule_id": "alpine.memory.90_completed_by_choice",
            "rule_version": "1.0.0",
            "source_event_type": "ScenarioDecisionSelected",
            "operation": "COMPLETE_SCENARIO",
            "required_scenario_event_types": ["beacon.disabled"],
            "requires_scenario_completed": True,
            "allowed_ending_ids": ["alpine.ending.arrived"],
        },
    ]
    definition = ScenarioDefinition.model_validate(payload)
    engine = DeclarativePlayerMemoryRuleEngine()
    started = engine.apply(
        state=ended_state,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="session-created",
        state_version=STATE_VERSION,
        receipts=(
            _receipt(
                event_type="ScenarioStarted",
                sequence=1,
                turn_id="session-created",
                payload={
                    "scenario_id": definition.scenario_id,
                    "scenario_content_version": definition.content_version,
                },
            ),
        ),
    )
    unrelated = engine.apply(
        state=started,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-choice",
        state_version=STATE_VERSION,
        receipts=(
            _receipt(
                event_type="ScenarioDecisionSelected",
                sequence=2,
                turn_id="turn-choice",
                payload={
                    "choice_id": "alpine.choice.wait",
                    "scenario_event_type": "unrelated.world.event",
                },
            ),
        ),
    )
    assert unrelated.player_memory.scenario_records[0].status is (
        ScenarioMemoryStatus.STARTED
    )
    completed = engine.apply(
        state=unrelated,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-choice-verified",
        state_version=STATE_VERSION,
        receipts=(
            _receipt(
                event_type="ScenarioDecisionSelected",
                sequence=3,
                turn_id="turn-choice-verified",
                payload={
                    "choice_id": "alpine.choice.wait",
                    "scenario_event_type": "beacon.disabled",
                },
            ),
        ),
    )

    record = completed.player_memory.scenario_records[0]
    assert record.status is ScenarioMemoryStatus.COMPLETED
    assert record.ending_id == "alpine.ending.arrived"
    assert completed.player_memory.npc_records == ()
    assert completed.player_memory.known_public_facts == ()


def test_capacity_enters_rebuild_required_without_crossing_the_gap() -> None:
    catalog, definition, state, _ = _started()
    catalog, fact_refs = _catalog_with_public_capacity_facts(catalog, 32)
    definition = catalog.scenarios[0]
    payload = state.to_snapshot()
    payload["player_memory"] = {
        "memory_model_version": 2,
        "sync_status": "CURRENT",
        "last_applied_source_sequence_no": 1,
        "last_applied_source_event_id": "event.start",
        "first_deferred_source_sequence_no": None,
        "last_deferred_source_sequence_no": None,
        "deferred_event_count": 0,
        "scenario_records": [
            {
                "scenario_id": definition.scenario_id,
                "scenario_content_version": definition.content_version,
                "status": "STARTED",
                "ending_id": None,
                "milestone_refs": ["STARTED", "IMPORTANT_FACT_CONFIRMED"],
                "known_public_fact_refs": list(fact_refs),
                "last_source_event_id": "event.start",
                "last_source_sequence_no": 1,
            }
        ],
        "npc_records": [],
        "significant_experiences": [],
        "known_public_facts": [
            {
                "scenario_id": definition.scenario_id,
                "fact_ref": fact_ref,
                "source_event_id": "event.start",
                "source_sequence_no": 1,
            }
            for fact_ref in fact_refs
        ],
    }
    state = GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    rule_payload = definition.model_dump(mode="json")
    rule_payload["memory_rules"] = [
        {
            "rule_id": "alpine.memory.capacity_fact",
            "rule_version": "1.0.0",
            "source_event_type": "NarrativeOutcomeAccepted",
            "operation": "REMEMBER_PUBLIC_FACT",
            "public_fact_id": "alpine.fact.weather",
        }
    ]
    definition = ScenarioDefinition.model_validate(rule_payload)
    engine = DeclarativePlayerMemoryRuleEngine()
    first = _receipt(
        event_type="NarrativeOutcomeAccepted", sequence=2, turn_id="turn-2"
    )
    lagging = engine.apply(
        state=state,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-2",
        state_version=STATE_VERSION,
        receipts=(first,),
    )
    assert lagging.player_memory.sync_status is MemoryIndexSyncStatus.REBUILD_REQUIRED
    assert lagging.player_memory.last_applied_source_sequence_no == 1
    assert lagging.player_memory.first_deferred_source_sequence_no == 2
    assert lagging.player_memory.deferred_event_count == 1
    assert len(lagging.player_memory.known_public_facts) == 32
    projection = PlayerMemoryProjector().project(lagging, catalog)
    assert projection.complete is False
    assert projection.sync_status is MemoryIndexSyncStatus.REBUILD_REQUIRED

    second = _receipt(
        event_type="NarrativeOutcomeAccepted", sequence=3, turn_id="turn-3"
    )
    later = engine.apply(
        state=lagging,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-3",
        state_version=STATE_VERSION,
        receipts=(second,),
    )
    replay = engine.apply(
        state=later,
        definition=definition,
        session_id=SESSION_ID,
        turn_id="turn-3",
        state_version=STATE_VERSION,
        receipts=(second,),
    )
    assert later.player_memory.last_applied_source_sequence_no == 1
    assert later.player_memory.last_deferred_source_sequence_no == 3
    assert later.player_memory.deferred_event_count == 2
    assert replay == later


def test_player_memory_v1_to_v2_migration_is_pure() -> None:
    v1 = {
        "memory_model_version": 1,
        "last_applied_source_sequence_no": 0,
        "scenario_records": [],
        "npc_records": [],
        "significant_experiences": [],
        "known_public_facts": [],
    }
    before = deepcopy(v1)
    migrated = migrate_player_memory_payload(v1)
    assert v1 == before
    assert migrated["memory_model_version"] == 2
    assert migrated["sync_status"] == "CURRENT"
    assert migrated["last_applied_source_event_id"] is None
    assert migrated["deferred_event_count"] == 0


def _all_keys(value: object) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(key)
            keys.extend(_all_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.extend(_all_keys(nested))
    return tuple(keys)
