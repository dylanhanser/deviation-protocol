from __future__ import annotations

from pathlib import Path

import pytest

from deviation_protocol.application import __all__ as application_exports
from deviation_protocol.application.scenario_event_bridge import (
    ScenarioDecisionResponsePolicy,
    TrustedScenarioEventIssuer,
    ValidatedDecisionResponse,
    bind_public_decision_frame,
)
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.scenario_runtime import VerifiedScenarioEvent
from deviation_protocol.domain.state import GameState, PlayerState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader


SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)


def test_decision_bridge_seals_only_a_validated_current_public_choice() -> None:
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
    started = DeterministicStoryDirector().start_scenario(state, definition)
    public_frame = bind_public_decision_frame(
        started.frame,
        session_id="session-1",
        state_version=0,
        scenario_content_version=definition.content_version,
    )
    assert public_frame.decision_id is not None
    action = ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="decision-1",
        action_type=ActionType.CHOOSE,
        decision_id=public_frame.decision_id,
        choice_id="death_certificate.action.observe_quietly",
    )
    runtime = started.candidate_state.scenario_runtime
    assert runtime is not None and runtime.current_decision_id is not None
    validated = ScenarioDecisionResponsePolicy().validate(
        action,
        public_frame,
        state=started.candidate_state,
        definition=definition,
        state_version=0,
    )
    issued = TrustedScenarioEventIssuer().issue_decision_response(
        validated,
        submission=action,
        state=started.candidate_state,
        definition=definition,
        state_version=0,
        current_decision_id=runtime.current_decision_id,
    )

    assert issued.sealed_event.is_authentic()
    assert issued.sealed_event.model_copy(
        update={"event_type": "vitals.verified"}
    ).is_authentic() is False
    assert issued.sealed_event.model_copy(
        update={"event_id": "decision.modified"}
    ).is_authentic() is False
    assert issued.sealed_event.model_copy(
        update={"source": "VERIFIED_RULE_RESULT"}
    ).is_authentic() is False
    assert issued.sealed_event.model_copy(
        update={"decision_id": "death_certificate.decision.core_one"}
    ).is_authentic() is False
    assert issued.sealed_event.discovered_clue_ids == ()
    assert issued.sealed_event.mutable_fact_updates == ()
    assert issued.audit_event.payload["selected_action_id"] == action.choice_id
    assert "TrustedScenarioEventIssuer" not in application_exports
    assert "_issue_verified_scenario_event" not in application_exports


def test_plain_or_payload_modified_scenario_event_has_no_advancement_authority() -> None:
    ordinary = VerifiedScenarioEvent(
        event_id="event.forged",
        event_type="player.decision.selected",
        decision_id="death_certificate.decision.immediate_survival",
        action_type="observe",
        resolves_current_decision=True,
    )
    assert ordinary.is_authentic() is False

    # Copying or changing a sealed-shaped payload creates an ordinary event with no
    # issuer capability. The seal is never represented in model_dump JSON.
    modified = ordinary.model_copy(update={"event_type": "vitals.verified"})
    assert modified.is_authentic() is False
    assert set(modified.model_dump()) == set(VerifiedScenarioEvent.model_fields)
    assert not ({"_issuer", "_sealed_payload"} & set(modified.model_dump()))

    forged_validation = ValidatedDecisionResponse()
    assert forged_validation.is_authentic() is False


def test_decision_capability_cannot_cross_request_or_authoritative_state() -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character(
        "character.death_certificate.investigator"
    )
    assert character is not None
    started = DeterministicStoryDirector().start_scenario(
        GameState(
            content_version=catalog.content_version,
            player=PlayerState.from_definition("player-1", character),
        ),
        definition,
    )
    frame = bind_public_decision_frame(
        started.frame,
        session_id="session-1",
        state_version=7,
        scenario_content_version=definition.content_version,
    )
    assert frame.decision_id is not None
    action = ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-1",
        action_type=ActionType.CHOOSE,
        decision_id=frame.decision_id,
        choice_id="death_certificate.action.observe_quietly",
    )
    capability = ScenarioDecisionResponsePolicy().validate(
        action,
        frame,
        state=started.candidate_state,
        definition=definition,
        state_version=7,
    )
    runtime = started.candidate_state.scenario_runtime
    assert runtime is not None and runtime.current_decision_id is not None
    issuer = TrustedScenarioEventIssuer()

    for changed_action in (
        action.model_copy(update={"session_id": "session-2"}),
        action.model_copy(update={"turn_id": "turn-2"}),
        action.model_copy(update={"client_request_id": "request-2"}),
        action.model_copy(
            update={"choice_id": "death_certificate.action.check_own_pulse"}
        ),
    ):
        with pytest.raises(ValueError, match="stale"):
            issuer.issue_decision_response(
                capability,
                submission=changed_action,
                state=started.candidate_state,
                definition=definition,
                state_version=7,
                current_decision_id=runtime.current_decision_id,
            )

    with pytest.raises(ValueError, match="stale"):
        issuer.issue_decision_response(
            capability,
            submission=action,
            state=started.candidate_state,
            definition=definition,
            state_version=8,
            current_decision_id=runtime.current_decision_id,
        )

    changed_state = started.candidate_state.model_copy(deep=True)
    changed_state.player.resources["composure"].current -= 1
    with pytest.raises(ValueError, match="stale"):
        issuer.issue_decision_response(
            capability,
            submission=action,
            state=changed_state,
            definition=definition,
            state_version=7,
            current_decision_id=runtime.current_decision_id,
        )

    with pytest.raises(ValueError, match="stale"):
        issuer.issue_decision_response(
            capability,
            submission=action,
            state=started.candidate_state,
            definition=definition,
            state_version=7,
            current_decision_id="death_certificate.decision.core_one",
        )

    with pytest.raises(ValueError, match="scenario_id"):
        issuer.issue_decision_response(
            capability,
            submission=action,
            state=started.candidate_state,
            definition=definition.model_copy(
                update={"scenario_id": "death_certificate.foreign"}
            ),
            state_version=7,
            current_decision_id=runtime.current_decision_id,
        )
