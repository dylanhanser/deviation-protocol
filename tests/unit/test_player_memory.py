from __future__ import annotations

from copy import copy, deepcopy
from datetime import datetime, timezone
import hashlib
import inspect
import json
import pickle

import pytest
from pydantic import TypeAdapter, ValidationError

from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.player_memory import (
    AuthoritativePlayerMemoryPlanFactory,
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
    NpcInteractionMilestone,
    SignificantExperienceCategory,
    _issue_memory_mutation,
    scenario_definition_fingerprint,
    stable_npc_subject_key,
    stable_significant_experience_id,
)
from deviation_protocol.domain.scenario import ScenarioDefinition
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    _issue_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState
from tests.unit.test_story_director import mini_catalog, state_for


NOW = datetime(2026, 7, 20, tzinfo=timezone.utc)
SESSION_ID = "session-1"
STATE_VERSION = 7


def _started():
    catalog = mini_catalog()
    definition = catalog.scenarios[0]
    directed = DeterministicStoryDirector().start_scenario(state_for(catalog), definition)
    return catalog, definition, directed.candidate_state, directed.frame


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
    _, definition, state, frame = _started()
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
    first = projector.project(state)
    second = projector.project(state)
    assert first == second
    encoded = first.model_dump_json()
    payload = first.model_dump(mode="json")
    assert first.known_public_facts[0].scenario_id == "alpine_signal"
    assert first.known_public_facts[0].fact_ref == "alpine.fact.weather"
    assert len(encoded.encode("utf-8")) <= MAX_MEMORY_PROJECTION_JSON_BYTES
    assert _string_characters(payload) <= MAX_MEMORY_PROJECTION_CHARACTERS
    with pytest.raises(ValidationError):
        first.scenarios[0].scenario_id = "changed"  # type: ignore[misc]

    _apply(
        state,
        factory.record_npc_encounter(
            state=state,
            definition=definition,
            state_version=STATE_VERSION,
            runtime_npc_id="alpine-ranger-runtime",
            source_event=_event(MemoryAuthorityEventType.NPC_ENCOUNTER_CONFIRMED, 3),
        ),
        definition,
    )
    assert not first.npcs
    assert projector.project(state).npcs
    for forbidden in (
        "event_id", "source_sequence", "capability", "seal", "action_signature",
        "outcome_token", "policy_trace", "scenario_runtime", "narrative_text",
        "signal_origin", "alpine.ending.arrived",
    ):
        assert forbidden not in encoded


def test_projection_collection_limit_keeps_newest_records_and_reports_truncation() -> None:
    catalog, _, state, _ = _started()
    payload = state.to_snapshot()
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": f"memory-scenario-{index:02d}",
            "scenario_content_version": "content-1",
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": f"memory-source-{index:02d}",
            "last_source_sequence_no": index + 1,
        }
        for index in range(17)
    ]
    payload["player_memory"]["last_applied_source_sequence_no"] = 17
    restored = GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    projection = PlayerMemoryProjector().project(restored)
    assert projection.truncated is True
    assert projection.total_scenario_records == 17
    assert len(projection.scenarios) == 16
    assert "memory-scenario-00" not in {
        item.scenario_id for item in projection.scenarios
    }


def test_projection_enforces_real_character_and_utf8_byte_budgets() -> None:
    catalog, _, state, _ = _started()
    payload = state.to_snapshot()
    scenario_id = "s" * 128
    content_version = "c" * 128
    payload["player_memory"]["scenario_records"] = [
        {
            "scenario_id": scenario_id,
            "scenario_content_version": content_version,
            "status": "STARTED",
            "ending_id": None,
            "milestone_refs": ["STARTED"],
            "known_public_fact_refs": [],
            "last_source_event_id": "event.start",
            "last_source_sequence_no": 1,
        }
    ]
    experiences = []
    for index in range(64):
        source_event_id = f"event.{index:02d}." + "e" * 119
        fact_ref = f"fact.{index:02d}." + "f" * 120
        entry_id = stable_significant_experience_id(
            source_event_id=source_event_id,
            scenario_id=scenario_id,
            category=SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
            subject_refs=(),
            public_fact_refs=(fact_ref,),
        )
        experiences.append(
            {
                "entry_id": entry_id,
                "scenario_id": scenario_id,
                "category": "IMPORTANT_PUBLIC_DISCOVERY",
                "summary": "CRITICAL_PUBLIC_FACT_LEARNED",
                "subject_refs": [],
                "public_fact_refs": [fact_ref],
                "source_event_id": source_event_id,
                "source_sequence_no": index + 2,
            }
        )
    payload["player_memory"]["significant_experiences"] = experiences
    payload["player_memory"]["last_applied_source_sequence_no"] = 65
    restored = GameState.from_snapshot(
        payload,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    projector = PlayerMemoryProjector()
    first = projector.project(restored)
    second = projector.project(restored)
    projection_payload = first.model_dump(mode="json")
    encoded = json.dumps(
        projection_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert first == second
    assert first.truncated is True
    assert len(first.significant_experiences) < 64
    assert len(encoded) <= MAX_MEMORY_PROJECTION_JSON_BYTES
    assert _string_characters(projection_payload) <= MAX_MEMORY_PROJECTION_CHARACTERS
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


def _string_characters(value: object) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        return sum(len(key) + _string_characters(item) for key, item in value.items())
    if isinstance(value, list):
        return sum(_string_characters(item) for item in value)
    return 0
