from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json

from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.narrative import NarrativeFrame, SuggestedAction
from deviation_protocol.domain.scenario import ScenarioDefinition
from deviation_protocol.domain.scenario_runtime import (
    VerifiedScenarioEvent,
    _seal_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState


class TrustedScenarioEventSource(StrEnum):
    """Closed server-side authorities allowed to mint scenario events."""

    VALIDATED_DECISION_RESPONSE = "VALIDATED_DECISION_RESPONSE"
    VERIFIED_RULE_RESULT = "VERIFIED_RULE_RESULT"
    VERIFIED_NARRATIVE_RESULT = "VERIFIED_NARRATIVE_RESULT"
    VALIDATED_NARRATIVE_OUTCOME = "VALIDATED_NARRATIVE_OUTCOME"


_EVENT_TYPE_WHITELIST: dict[TrustedScenarioEventSource, frozenset[str]] = {
    TrustedScenarioEventSource.VALIDATED_DECISION_RESPONSE: frozenset(
        {"player.decision.selected"}
    ),
    # Phase 2.2a deliberately has no mechanical-story mapping and no narrative
    # result validator. Keeping the sources closed and empty reserves the two
    # future verification boundaries without granting either one authority now.
    TrustedScenarioEventSource.VERIFIED_RULE_RESULT: frozenset(),
    TrustedScenarioEventSource.VERIFIED_NARRATIVE_RESULT: frozenset(),
    # NarrativeEventIssuer owns this source and derives payloads only from
    # catalog-validated templates; this legacy issuer cannot mint it.
    TrustedScenarioEventSource.VALIDATED_NARRATIVE_OUTCOME: frozenset(),
}
_DECISION_VALIDATION_ISSUER = object()


@dataclass(frozen=True, slots=True, init=False)
class ValidatedDecisionResponse:
    decision_id: str
    decision_definition_id: str
    selected_action: SuggestedAction
    session_id: str
    turn_id: str
    client_request_id: str
    action_signature: str
    state_version: int
    scenario_id: str
    scenario_content_version: str
    state_fingerprint: str
    _issuer: object

    def is_authentic(self) -> bool:
        return getattr(self, "_issuer", None) is _DECISION_VALIDATION_ISSUER


class ScenarioDecisionResponsePolicy:
    """Validate CHOOSE against the one decision currently exposed in a frame."""

    def validate(
        self,
        submission: ActionSubmission,
        frame: NarrativeFrame,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
    ) -> ValidatedDecisionResponse:
        if submission.action_type is not ActionType.CHOOSE:
            raise ValueError("only CHOOSE can select a declared decision response")
        runtime = state.scenario_runtime
        if runtime is None or not frame.decision_required:
            raise ValueError("there is no active decision")
        runtime.validate_against(definition)
        current_decision_id = runtime.current_decision_id
        public_decision_id = _public_decision_id(
            submission.session_id,
            state_version,
            runtime.scenario_id,
            runtime.scenario_content_version,
            current_decision_id or "",
        )
        if (
            current_decision_id is None
            or submission.decision_id != public_decision_id
            or frame.decision_id != public_decision_id
            or frame.scenario_id != runtime.scenario_id
            or frame.phase_id != runtime.current_phase_id
            or frame.current_location_id != runtime.current_location_id
        ):
            raise ValueError("decision response is stale or not authoritative")
        choice_id = submission.choice_id
        selected = next(
            (item for item in frame.suggested_actions if item.action_id == choice_id),
            None,
        )
        if selected is None:
            raise ValueError("choice is not allowed by the active decision")
        declared = next(
            (
                item
                for item in definition.decision_window(
                    current_decision_id
                ).suggested_actions
                if item.action_id == selected.action_id
            ),
            None,
        )
        if declared is None or declared.action_type != selected.action_type:
            raise ValueError("choice is not declared by the authoritative decision")
        validated = object.__new__(ValidatedDecisionResponse)
        object.__setattr__(validated, "decision_id", public_decision_id)
        object.__setattr__(
            validated, "decision_definition_id", current_decision_id
        )
        object.__setattr__(validated, "selected_action", selected)
        object.__setattr__(validated, "session_id", submission.session_id)
        object.__setattr__(validated, "turn_id", submission.turn_id)
        object.__setattr__(
            validated, "client_request_id", submission.client_request_id
        )
        object.__setattr__(
            validated, "action_signature", submission.action_signature()
        )
        object.__setattr__(validated, "state_version", state_version)
        object.__setattr__(validated, "scenario_id", runtime.scenario_id)
        object.__setattr__(
            validated,
            "scenario_content_version",
            runtime.scenario_content_version,
        )
        object.__setattr__(
            validated, "state_fingerprint", _state_fingerprint(state)
        )
        object.__setattr__(validated, "_issuer", _DECISION_VALIDATION_ISSUER)
        return validated


@dataclass(frozen=True, slots=True)
class IssuedScenarioDecisionEvent:
    sealed_event: VerifiedScenarioEvent
    audit_event: DomainEventDraft


class TrustedScenarioEventIssuer:
    """Narrow capability: mint only a server-validated current decision choice."""

    def issue_decision_response(
        self,
        validated: ValidatedDecisionResponse,
        *,
        submission: ActionSubmission,
        state: GameState,
        definition: ScenarioDefinition,
        state_version: int,
        current_decision_id: str,
    ) -> IssuedScenarioDecisionEvent:
        source = TrustedScenarioEventSource.VALIDATED_DECISION_RESPONSE
        event_type = "player.decision.selected"
        if not isinstance(validated, ValidatedDecisionResponse) or not validated.is_authentic():
            raise ValueError("decision response lacks server validation authority")
        if event_type not in _EVENT_TYPE_WHITELIST[source]:  # pragma: no cover
            raise ValueError("scenario event type is not allowed for its source")
        runtime = state.scenario_runtime
        if runtime is None:
            raise ValueError("decision response has no authoritative scenario runtime")
        runtime.validate_against(definition)
        if (
            validated.decision_definition_id != current_decision_id
            or submission.decision_id != validated.decision_id
            or runtime.current_decision_id != current_decision_id
            or validated.session_id != submission.session_id
            or validated.turn_id != submission.turn_id
            or validated.client_request_id != submission.client_request_id
            or validated.action_signature != submission.action_signature()
            or validated.state_version != state_version
            or validated.scenario_id != runtime.scenario_id
            or validated.scenario_id != definition.scenario_id
            or validated.scenario_content_version
            != runtime.scenario_content_version
            or validated.scenario_content_version != definition.content_version
            or validated.state_fingerprint != _state_fingerprint(state)
        ):
            raise ValueError("validated decision response is stale")
        declared = next(
            (
                item
                for item in definition.decision_window(
                    current_decision_id
                ).suggested_actions
                if item.action_id == validated.selected_action.action_id
            ),
            None,
        )
        if (
            declared is None
            or declared.action_type != validated.selected_action.action_type
            or submission.choice_id != validated.selected_action.action_id
        ):
            raise ValueError("validated choice does not match authoritative content")
        event_id = self._event_id(submission)
        event = _seal_verified_scenario_event(
            VerifiedScenarioEvent(
                event_id=event_id,
                event_type=event_type,
                source=source.value,
                decision_id=current_decision_id,
                action_type=validated.selected_action.action_type,
                resolves_current_decision=True,
                expose_in_frame=True,
            )
        )
        audit = DomainEventDraft(
            "ScenarioDecisionSelected",
            {
                "source": source.value,
                "scenario_event_type": event_type,
                "scenario_event_id": event_id,
                "decision_id": current_decision_id,
                "public_decision_id": validated.decision_id,
                "selected_action_id": validated.selected_action.action_id,
                "selected_action_type": validated.selected_action.action_type,
            },
        )
        return IssuedScenarioDecisionEvent(event, audit)

    @staticmethod
    def _event_id(submission: ActionSubmission) -> str:
        digest = hashlib.sha256(
            (
                submission.session_id
                + "\0"
                + submission.turn_id
                + "\0"
                + submission.client_request_id
                + "\0"
                + (submission.decision_id or "")
                + "\0"
                + (submission.choice_id or "")
            ).encode("utf-8")
        ).hexdigest()[:32]
        return f"decision.{digest}"


def _state_fingerprint(state: GameState) -> str:
    encoded = json.dumps(
        state.to_snapshot(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bind_public_decision_frame(
    frame: NarrativeFrame,
    *,
    session_id: str,
    state_version: int,
    scenario_content_version: str,
) -> NarrativeFrame:
    """Replace an internal definition ID with a session/version-bound public ID."""

    if not frame.decision_required:
        return frame
    if frame.decision_id is None:
        raise ValueError("decision frame has no internal decision definition ID")
    public_id = _public_decision_id(
        session_id,
        state_version,
        frame.scenario_id,
        scenario_content_version,
        frame.decision_id,
    )
    payload = frame.model_dump(mode="json")
    payload["frame_id"] = "frame.pending"
    payload["decision_id"] = public_id
    draft = NarrativeFrame.model_validate(payload)
    frame_seed = draft.model_dump(mode="json", exclude={"frame_id"})
    digest = hashlib.sha256(
        json.dumps(
            frame_seed,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()[:24]
    return draft.model_copy(update={"frame_id": f"frame.{digest}"})


def _public_decision_id(
    session_id: str,
    state_version: int,
    scenario_id: str,
    scenario_content_version: str,
    decision_definition_id: str,
) -> str:
    digest = hashlib.sha256(
        "\0".join(
            (
                session_id,
                str(state_version),
                scenario_id,
                scenario_content_version,
                decision_definition_id,
            )
        ).encode("utf-8")
    ).hexdigest()[:32]
    return f"decision.{digest}"
