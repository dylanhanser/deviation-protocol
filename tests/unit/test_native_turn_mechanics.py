from dataclasses import replace
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deviation_protocol.application.native_turn_mechanics import (
    NativeTurnMechanicsCoordinator, TrustedNativeTurnInputs, NativeMechanicsDecision,
    NativeTurnBindingError, NativeMechanicsIntegrityError, _mint, canonical, digest,
    native_request_envelope, parse_job_request,
)
from deviation_protocol.application.narrative_outcome_policy import (
    allowed_narrative_outcomes, select_native_outcome, state_fingerprint,
    NarrativeOutcomePolicy, NarrativeEventIssuer, proposal_digest,
)
from deviation_protocol.application.narrative_models import NarrativeRequest, NarrativePlayerIntent
from deviation_protocol.application.resolution import ResolutionStatus
from tests.unit.test_narrative_outcome_policy import opening_state, purposeful_action, _validated_success


def fixture_inputs(values=(60, 45, 65, 60, 60), presentation=("balanced", "lawful", "off"), *, quiet=False, **binding_updates):
    catalog, definition, state, frame = opening_state()
    # This explicit test mint is never used by production orchestration. MySQL tests
    # separately prove the only production issuer: complete admitted reconstruction.
    coordinator = NativeTurnMechanicsCoordinator(catalog.content_catalog, catalog)
    submission = purposeful_action()
    if quiet:
        from deviation_protocol.domain.actions import ActionType
        submission = purposeful_action(action_type=ActionType.OBSERVE, description="我静静观察周围")
    binding = dict(run_id="run.test", run_revision=3, continuous_story_line_id="line.test",
        session_id=submission.session_id, player_id=state.player.player_id,
        applicable_character_reference={"player_character_id": {"value": "character.test"},
            "contract_version": "structured-player-character/v1", "record_revision": {"value": 1}},
        entry_world={"entry_world_id": {"value": "world.death_certificate"}, "entry_world_version": {"value": 1}},
        scenario_id=definition.scenario_id, scenario_content_version=definition.content_version,
        resolution_fingerprint="a" * 64, mechanics_version="run-mechanics/v1",
        state_version=0, state_fingerprint=state_fingerprint(state), turn_id=submission.turn_id,
        client_request_id=submission.client_request_id, action_signature=submission.action_signature(),
        frame_digest=digest(frame.model_dump(mode="json")))
    fields = dict(binding_bytes=canonical(binding), snapshot_bytes=canonical(state.to_snapshot()),
                  objectives=values, presentation=presentation, resource_id="composure")
    inputs = _mint(TrustedNativeTurnInputs, **fields, _original=tuple(fields.values()))
    selected = select_native_outcome(allowed_narrative_outcomes(submission=submission, state=state,
        state_version=0, definition=definition, frame=frame))[0]
    decision = coordinator.decide(inputs, state, definition, submission, selected=selected)
    if binding_updates:
        binding.update(binding_updates)
        fields["binding_bytes"] = canonical(binding)
        inputs = _mint(TrustedNativeTurnInputs, **fields, _original=tuple(fields.values()))
        object.__setattr__(decision, "inputs", inputs)
        object.__setattr__(decision, "_original", decision._identity())
    return SimpleNamespace(coordinator=coordinator, inputs=inputs, decision=decision, state=state,
        submission=submission, definition=definition, frame=frame, selected=selected)


def execute(fixture):
    f = fixture
    proposal = _validated_success(f.selected)
    args = dict(job_id="job.test", lease_token="a" * 32, lease_owner="worker", submission=f.submission,
                state=f.state, state_version=0, definition=f.definition)
    authorized = NarrativeOutcomePolicy().authorize(proposal, **args, frame=f.frame,
        resolution_status=ResolutionStatus.NARRATIVE_REQUIRED, expected_state_fingerprint=state_fingerprint(f.state),
        expected_proposal_digest=proposal_digest(proposal), native_selection=True)
    sealed = NarrativeEventIssuer().issue(authorized, **args, proposal=proposal)
    candidate, events = f.coordinator.apply_resource(f.state, f.decision)
    from deviation_protocol.application.story_director import DeterministicStoryDirector
    directed = DeterministicStoryDirector().advance_after_verified_result(candidate, f.definition,
        (sealed,), native_plan=f.decision)
    return directed, events


def test_pure_decision_and_mutation_are_detached_and_prompt_independent():
    f = fixture_inputs()
    before = f.state.to_snapshot()
    directed, events = execute(f)
    assert f.state.to_snapshot() == before
    assert directed.candidate_state.player.resources["composure"].current == 5
    assert len(events) == 1
    assert f.decision == f.coordinator.decide(f.inputs, f.state, f.definition, f.submission, selected=f.selected)
    object.__setattr__(f.decision.resource, "actual", 2)
    with pytest.raises(NativeMechanicsIntegrityError):
        f.coordinator.apply_resource(f.state, f.decision)


@pytest.mark.parametrize("value", [True, "6", 6.0])
def test_original_nested_resource_types_reject_without_normalization(value):
    f = fixture_inputs()
    object.__setattr__(f.state.player.resources["composure"], "current", value)
    with pytest.raises(NativeMechanicsIntegrityError):
        f.coordinator.apply_resource(f.state, f.decision)


async def test_missing_participation_with_reverse_receipt_never_falls_back():
    f = fixture_inputs()
    uow = SimpleNamespace(run_participations=SimpleNamespace(get=AsyncMock(return_value=None),
        find_attachment_run_ids=AsyncMock(return_value=("run.orphan",))))
    with pytest.raises(NativeTurnBindingError):
        await f.coordinator.load(uow, SimpleNamespace(session_id="session-1"), f.state, f.definition)
    uow.run_participations.find_attachment_run_ids.return_value = ()
    assert await f.coordinator.load(uow, SimpleNamespace(session_id="session-1"), f.state, f.definition) is None


def test_native_job_envelope_round_trip_and_closed_fields():
    f = fixture_inputs()
    request = NarrativeRequest(frame=f.frame, player_intent=NarrativePlayerIntent.from_submission(f.submission),
        style_profile_id="original-zh-second-person-v1", outcome_candidates=(f.selected.candidate,))
    envelope = native_request_envelope(request, f.decision)
    # Use the actual immutable character contract version in the test-only binding.
    from deviation_protocol.domain.player_character import PlayerCharacterContractVersion
    envelope["binding"]["applicable_character_reference"]["contract_version"] = next(iter(PlayerCharacterContractVersion)).value
    assert parse_job_request(envelope)[0] == request
    for section in (envelope, envelope["binding"], envelope["mechanics"], envelope["mechanics"]["resource"]):
        section["extra"] = "hidden"
        with pytest.raises(ValueError):
            parse_job_request(envelope)
        section.pop("extra")


@pytest.mark.parametrize("field,replace_with", [("inputs", "other"), ("action_type", "other"), ("resource", object())])
def test_mutated_decision_authentication_fails_closed(field, replace_with):
    f = fixture_inputs()
    if field == "inputs":
        replace_with = fixture_inputs(run_id="run.other").inputs
    object.__setattr__(f.decision, field, replace_with)
    assert not f.decision.is_authentic()
    from deviation_protocol.application.run_protocol_prompt_context import compile_run_protocol_context, RunPromptContextError
    with pytest.raises(RunPromptContextError, match="UNTRUSTED_INPUT"):
        compile_run_protocol_context(f.inputs, f.decision)


def test_catalogue_rejects_world_and_resource_mismatch():
    from deviation_protocol.domain.run_protocol_mechanics import MECHANICS_CATALOGUE
    catalog, definition, state, frame = opening_state()
    for entry in (replace(MECHANICS_CATALOGUE[0], world_id="unknown"),
                  replace(MECHANICS_CATALOGUE[0], resource_id="missing")):
        with pytest.raises(ValueError):
            NativeTurnMechanicsCoordinator(catalog.content_catalog, catalog, catalogue=(entry,))
