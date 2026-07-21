from __future__ import annotations

from dataclasses import dataclass

from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.scenario import EndingStatus
from deviation_protocol.domain.state import GameState


@dataclass(frozen=True, slots=True)
class ContinuePolicyViolation(ValueError):
    code: str

    def __str__(self) -> str:
        return self.code


class ScenarioContinuePolicy:
    """Authorize exactly one server-defined auto beat from locked authority."""

    def allows(self, *, state: GameState, frame: NarrativeFrame) -> bool:
        runtime = state.scenario_runtime
        return bool(
            runtime is not None
            and runtime.ending_status is EndingStatus.ACTIVE
            and runtime.current_decision_id is None
            and not frame.decision_required
            and frame.stop_condition == "CONTINUE"
        )

    def validate(
        self,
        submission: ActionSubmission,
        *,
        state: GameState,
        frame: NarrativeFrame,
    ) -> None:
        if submission.action_type is not ActionType.CONTINUE:
            raise ContinuePolicyViolation("CONTINUE_ACTION_REQUIRED")
        if any(
            (
                submission.target_ids,
                submission.tool_ids,
                submission.description is not None,
                submission.dialogue is not None,
                submission.decision_id is not None,
                submission.choice_id is not None,
                submission.item_instance_id is not None,
                submission.equipment_slot_id is not None,
                submission.skill_definition_id is not None,
            )
        ):
            raise ContinuePolicyViolation("CONTINUE_PAYLOAD_FORBIDDEN")
        runtime = state.scenario_runtime
        if runtime is None:
            raise ContinuePolicyViolation("CONTINUE_REQUIRES_ACTIVE_SCENARIO")
        if runtime.ending_status is not EndingStatus.ACTIVE:
            raise ContinuePolicyViolation("SCENARIO_ENDED")
        if runtime.current_decision_id is not None or frame.decision_required:
            raise ContinuePolicyViolation("DECISION_RESPONSE_REQUIRED")
        if frame.stop_condition != "CONTINUE":
            raise ContinuePolicyViolation("CONTINUE_NOT_ALLOWED")
