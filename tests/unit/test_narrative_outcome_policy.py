from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    NarrativeProviderMetadata,
    NpcUtterance,
    SelectedNarrativeOutcome,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.narrative_outcome_policy import (
    AuthorizedNarrativeOutcome,
    NarrativeEventIssuer,
    NarrativeOutcomePolicy,
    ValidatedNarrativeOutcomeCapability,
    allowed_narrative_outcomes,
    proposal_digest,
    state_fingerprint,
)
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.scenario_event_bridge import bind_public_decision_frame
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.state import GameState, PlayerState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader


SCENARIO_PACK = Path(__file__).parents[2] / "config" / "scenarios" / "death_certificate_v1.json"


def opening_state():
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
            f"scenario-npc-{index}",
        )
    started = DeterministicStoryDirector().start_scenario(
        state,
        definition,
        profession_tags=frozenset(character.tags)
        & set(definition.available_profession_tags),
    )
    state = started.candidate_state
    frame = bind_public_decision_frame(
        started.frame,
        session_id="session-1",
        state_version=0,
        scenario_content_version=definition.content_version,
    )
    return catalog, definition, state, frame


def purposeful_action(**updates: object) -> ActionSubmission:
    base = ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-1",
        action_type=ActionType.CUSTOM,
        description="我尝试有规律地移动手指发出生命信号",
    )
    return base.model_copy(update=updates)


def _validated_success(allowed) -> ValidatedNarrativeProposal:
    speaker = allowed.candidate.allowed_entity_ids[0]
    return ValidatedNarrativeProposal(
        proposal=NarrativeProposalPayload(
            schema_version="narrative-proposal-v1",
            narrative_text="你反复移动手指发出规律信号，分诊协调员停下流程核对监护设备。" * 20,
            referenced_entity_ids=(speaker,),
            npc_utterances=(
                NpcUtterance(
                    speaker_entity_id=speaker,
                    text="我看到了，你现在有意识。",
                ),
            ),
            selected_outcome=SelectedNarrativeOutcome(
                outcome_token=allowed.candidate.outcome_token,
                result=NarrativeOutcomeResult.SUCCESS,
                referenced_entity_ids=(speaker,),
            ),
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="fake",
            model="fake-model",
            finish_reason="stop",
            attempts=1,
            latency_ms=1,
        ),
    )


def test_outcome_token_is_bound_to_session_turn_version_action_state_scenario_and_frame() -> None:
    catalog, definition, state, frame = opening_state()
    action = purposeful_action()

    def token(
        candidate_action: ActionSubmission,
        version: int = 0,
        *,
        candidate_state=state,
        candidate_definition=definition,
        candidate_frame=frame,
    ) -> str:
        outcomes = allowed_narrative_outcomes(
            submission=candidate_action,
            state=candidate_state,
            state_version=version,
            definition=candidate_definition,
            frame=candidate_frame,
        )
        assert len(outcomes) == 1
        return outcomes[0].candidate.outcome_token

    original = token(action)
    assert token(action.model_copy(update={"session_id": "session-2"})) != original
    assert token(action.model_copy(update={"turn_id": "turn-2"})) != original
    assert token(action.model_copy(update={"client_request_id": "request-2"})) != original
    assert token(action.model_copy(update={"description": "我移动手指发出另一种信号"})) != original
    assert token(action, 1) != original
    changed_state = GameState.from_snapshot(
        state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    changed_state.player.wallet.balances["currency.test"] = 1
    assert token(action, candidate_state=changed_state) != original
    changed_definition = definition.model_copy(
        update={"content_version": "changed-content-version"}
    )
    changed_scenario_state = GameState.from_snapshot(
        state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    changed_scenario_state.scenario_runtime.scenario_content_version = (
        "changed-content-version"
    )
    assert token(
        action,
        candidate_state=changed_scenario_state,
        candidate_definition=changed_definition,
    ) != original
    assert token(
        action,
        candidate_frame=frame.model_copy(update={"frame_id": "changed-frame"}),
    ) != original


def test_policy_rejects_every_stale_binding_custom_token_and_hidden_entity() -> None:
    catalog, definition, state, frame = opening_state()
    action = purposeful_action()
    allowed = allowed_narrative_outcomes(
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )[0]
    validated = _validated_success(allowed)
    policy = NarrativeOutcomePolicy()
    base = {
        "job_id": "job-1",
        "lease_token": "a" * 32,
        "lease_owner": "worker-1",
        "submission": action,
        "state": state,
        "state_version": 0,
        "definition": definition,
        "frame": frame,
        "resolution_status": ResolutionStatus.NARRATIVE_REQUIRED,
        "expected_state_fingerprint": state_fingerprint(state),
        "expected_proposal_digest": proposal_digest(validated),
    }

    with pytest.raises(ValueError, match="state is stale"):
        policy.authorize(
            validated,
            **{**base, "expected_state_fingerprint": "f" * 64},
        )
    with pytest.raises(ValueError, match="digest changed"):
        policy.authorize(
            validated,
            **{**base, "expected_proposal_digest": "e" * 64},
        )
    for changes in (
        {"state_version": 1},
        {
            "submission": action.model_copy(
                update={"description": "我用另一种规律移动手指发出生命信号"}
            )
        },
        {"frame": frame.model_copy(update={"frame_id": "changed-frame"})},
    ):
        with pytest.raises(ValueError, match="stale or unauthorized"):
            policy.authorize(validated, **{**base, **changes})

    changed_state = GameState.from_snapshot(
        state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    changed_state.player.wallet.balances["currency.test"] = 1
    with pytest.raises(ValueError, match="stale or unauthorized"):
        policy.authorize(
            validated,
            **{
                **base,
                "state": changed_state,
                "expected_state_fingerprint": state_fingerprint(changed_state),
            },
        )

    changed_definition = definition.model_copy(
        update={"content_version": "changed-content-version"}
    )
    changed_scenario_state = GameState.from_snapshot(
        state.to_snapshot(),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    changed_scenario_state.scenario_runtime.scenario_content_version = (
        "changed-content-version"
    )
    with pytest.raises(ValueError, match="stale or unauthorized"):
        policy.authorize(
            validated,
            **{
                **base,
                "state": changed_scenario_state,
                "definition": changed_definition,
                "expected_state_fingerprint": state_fingerprint(
                    changed_scenario_state
                ),
            },
        )

    selected = validated.proposal.selected_outcome
    assert selected is not None
    for replacement in (
        selected.model_copy(update={"outcome_token": "outcome." + "f" * 48}),
        selected.model_copy(update={"referenced_entity_ids": ("npc.runtime.hidden",)}),
    ):
        changed = validated.model_copy(
            update={
                "proposal": validated.proposal.model_copy(
                    update={"selected_outcome": replacement}
                )
            }
        )
        with pytest.raises(ValueError):
            policy.authorize(
                changed,
                **{
                    **base,
                    "expected_proposal_digest": proposal_digest(changed),
                },
            )


def test_issuer_rejects_an_ordinary_unminted_capability() -> None:
    _, definition, state, frame = opening_state()
    action = purposeful_action()
    allowed = allowed_narrative_outcomes(
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )[0]
    proposal = _validated_success(allowed)
    fake_capability = object.__new__(ValidatedNarrativeOutcomeCapability)
    forged = AuthorizedNarrativeOutcome(
        capability=fake_capability,
        rule=allowed.rule,
        result_name=NarrativeOutcomeResult.SUCCESS.value,
    )

    with pytest.raises(ValueError, match="lacks policy authority"):
        NarrativeEventIssuer().issue(
            forged,
            job_id="job-1",
            lease_token="a" * 32,
            lease_owner="worker-1",
            submission=action,
            state=state,
            state_version=0,
            definition=definition,
            proposal=proposal,
        )


def test_opening_rules_separate_purposeful_observe_and_player_ordered_npc_success() -> None:
    _, definition, state, frame = opening_state()
    purposeful = allowed_narrative_outcomes(
        submission=purposeful_action(),
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )
    assert [item.rule.rule_id for item in purposeful] == [
        "death_certificate.outcome.purposeful_life_signal"
    ]
    assert set(purposeful[0].candidate.allowed_results) == {
        NarrativeOutcomeResult.SUCCESS,
        NarrativeOutcomeResult.AMBIGUOUS,
        NarrativeOutcomeResult.FAILURE,
    }

    observed = allowed_narrative_outcomes(
        submission=purposeful_action(
            action_type=ActionType.OBSERVE,
            description="我保持安静并观察",
        ),
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )
    assert [item.rule.rule_id for item in observed] == [
        "death_certificate.outcome.quiet_observation"
    ]
    assert NarrativeOutcomeResult.SUCCESS not in observed[0].candidate.allowed_results

    ordered = allowed_narrative_outcomes(
        submission=purposeful_action(description="让护士承认并确认我活着"),
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )
    assert [item.rule.rule_id for item in ordered] == [
        "death_certificate.outcome.constrained_custom_no_effect"
    ]
    assert ordered[0].candidate.allowed_results == (
        NarrativeOutcomeResult.NO_EFFECT,
    )


def test_policy_and_issuer_only_use_server_template_and_story_director() -> None:
    catalog, definition, state, frame = opening_state()
    action = purposeful_action()
    allowed = allowed_narrative_outcomes(
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )[0]
    speaker = allowed.candidate.allowed_entity_ids[0]
    text = "你用仍能控制的手指重复敲出节奏。设备上的变化被护士注意到，她暂停处置并重新核对你的反应。" * 9
    validated = ValidatedNarrativeProposal(
        proposal=NarrativeProposalPayload(
            schema_version="narrative-proposal-v1",
            narrative_text=text,
            referenced_entity_ids=(speaker,),
            npc_utterances=(
                NpcUtterance(
                    speaker_entity_id=speaker,
                    text="我看到了，你现在有意识。",
                ),
            ),
            selected_outcome=SelectedNarrativeOutcome(
                outcome_token=allowed.candidate.outcome_token,
                result=NarrativeOutcomeResult.SUCCESS,
                referenced_entity_ids=(speaker,),
            ),
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="fake",
            model="fake-model",
            finish_reason="stop",
            attempts=1,
            latency_ms=1,
        ),
    )
    digest = proposal_digest(validated)
    authorized = NarrativeOutcomePolicy().authorize(
        validated,
        job_id="job-1",
        lease_token="a" * 32,
        lease_owner="worker-1",
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
        resolution_status=ResolutionStatus.NARRATIVE_REQUIRED,
        expected_state_fingerprint=state_fingerprint(state),
        expected_proposal_digest=digest,
    )
    event = NarrativeEventIssuer().issue(
        authorized,
        job_id="job-1",
        lease_token="a" * 32,
        lease_owner="worker-1",
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        proposal=validated,
    )
    assert event.source == "VALIDATED_NARRATIVE_OUTCOME"
    assert event.discovered_clue_ids == (
        "death_certificate.clue.vital_response",
    )
    assert text not in event.model_dump_json()
    directed = DeterministicStoryDirector().advance_after_verified_result(
        state,
        definition,
        (event,),
        profession_tags=frozenset(
            catalog.content_catalog.character(
                state.player.character_definition_id
            ).tags
        )
        & set(definition.available_profession_tags),
    )
    assert "death_certificate.clue.vital_response" in (
        directed.candidate_state.scenario_runtime.discovered_clue_ids
    )
    assert state.scenario_runtime.current_phase_id == "death_certificate.arrival_locked"
    assert directed.candidate_state.scenario_runtime.current_phase_id == (
        "death_certificate.life_disputed"
    )


def test_failure_token_with_success_prose_is_rejected_and_model_delta_fields_are_forbidden() -> None:
    _, definition, state, frame = opening_state()
    action = purposeful_action()
    allowed = allowed_narrative_outcomes(
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )[0]
    speaker = allowed.candidate.allowed_entity_ids[0]
    contradictory = ValidatedNarrativeProposal(
        proposal=NarrativeProposalPayload(
            schema_version="narrative-proposal-v1",
            narrative_text=("护士确认你还活着，并宣告成功。" * 30),
            referenced_entity_ids=(speaker,),
            selected_outcome=SelectedNarrativeOutcome(
                outcome_token=allowed.candidate.outcome_token,
                result=NarrativeOutcomeResult.FAILURE,
                referenced_entity_ids=(speaker,),
            ),
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="fake",
            model="fake-model",
            finish_reason="stop",
            attempts=1,
            latency_ms=1,
        ),
    )
    with pytest.raises(ValueError, match="contradicts"):
        NarrativeOutcomePolicy().authorize(
            contradictory,
            job_id="job-1",
            lease_token="a" * 32,
            lease_owner="worker-1",
            submission=action,
            state=state,
            state_version=0,
            definition=definition,
            frame=frame,
            resolution_status=ResolutionStatus.NARRATIVE_REQUIRED,
            expected_state_fingerprint=state_fingerprint(state),
            expected_proposal_digest=proposal_digest(contradictory),
        )

    base = {
        "schema_version": "narrative-proposal-v1",
        "narrative_text": "可见描述" * 100,
        "selected_outcome": {
            "outcome_token": allowed.candidate.outcome_token,
            "result": "FAILURE",
            "referenced_entity_ids": [],
        },
    }
    for forbidden in (
        {"fact_updates": {"fixed.fact": True}},
        {"clue_ids": ["hidden.clue"]},
        {"clock_delta": 99},
        {"outcome_rule_id": allowed.rule.rule_id},
    ):
        with pytest.raises(ValidationError):
            NarrativeProposalPayload.model_validate({**base, **forbidden})


def test_success_requires_visible_npc_utterance_that_supports_the_data_rule() -> None:
    _, definition, state, frame = opening_state()
    action = purposeful_action()
    allowed = allowed_narrative_outcomes(
        submission=action,
        state=state,
        state_version=0,
        definition=definition,
        frame=frame,
    )[0]
    speaker = allowed.candidate.allowed_entity_ids[0]
    unsupported = ValidatedNarrativeProposal(
        proposal=NarrativeProposalPayload(
            schema_version="narrative-proposal-v1",
            narrative_text="你反复移动手指，分诊协调员停下手里的流程继续观察。" * 20,
            referenced_entity_ids=(speaker,),
            npc_utterances=(
                NpcUtterance(
                    speaker_entity_id=speaker,
                    text="我只看见手指移动，继续观察。",
                ),
            ),
            selected_outcome=SelectedNarrativeOutcome(
                outcome_token=allowed.candidate.outcome_token,
                result=NarrativeOutcomeResult.SUCCESS,
                referenced_entity_ids=(speaker,),
            ),
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="fake",
            model="fake-model",
            finish_reason="stop",
            attempts=1,
            latency_ms=1,
        ),
    )

    with pytest.raises(ValueError, match="does not support"):
        NarrativeOutcomePolicy().authorize(
            unsupported,
            job_id="job-1",
            lease_token="a" * 32,
            lease_owner="worker-1",
            submission=action,
            state=state,
            state_version=0,
            definition=definition,
            frame=frame,
            resolution_status=ResolutionStatus.NARRATIVE_REQUIRED,
            expected_state_fingerprint=state_fingerprint(state),
            expected_proposal_digest=proposal_digest(unsupported),
        )
