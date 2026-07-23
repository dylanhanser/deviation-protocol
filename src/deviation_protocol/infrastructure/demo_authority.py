from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextvars import ContextVar, Token
from dataclasses import dataclass
import hashlib
from typing import Any

from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
    NarrativeProvider,
    NarrativeRequest,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.scenario_event_bridge import (
    TrustedScenarioEventIssuer,
)
from deviation_protocol.domain.actions import ActionSubmission, ActionType


@dataclass(frozen=True, slots=True)
class DemoProviderCall:
    action_type: ActionType
    description: str
    safe_description: str
    state_version: int
    phase_id: str
    phase_beat_index: int
    current_location_id: str
    event_count: int
    turn_request_count: int
    prior_provider_job_count: int
    allowed_entity_ids: tuple[str, ...]


DEMO_PROVIDER_SCRIPT = (
    DemoProviderCall(
        ActionType.CUSTOM,
        "请协调员复核我的连续回应和生命体征",
        "请求基于可重复反应进行临床复核；成功时由现场协调员明确确认生命状态。",
        1,
        "death_certificate.life_disputed",
        0,
        "death_certificate.intake_room",
        2,
        1,
        0,
        ("scenario-npc-1",),
    ),
    DemoProviderCall(
        ActionType.EXPLORE,
        "沿记录与档案审计路径核对签发时间",
        "沿公开记录链核对签发顺序，并由固定结果开放档案路径。",
        9,
        "death_certificate.investigation",
        2,
        "death_certificate.records_room",
        12,
        9,
        1,
        ("scenario-npc-2",),
    ),
    DemoProviderCall(
        ActionType.EXPLORE,
        "核对日志时间顺序以及规程反馈",
        "核验审计顺序与处置反馈，并由固定结果开放地下观察路径。",
        10,
        "death_certificate.investigation",
        3,
        "death_certificate.records_room",
        13,
        10,
        2,
        ("scenario-npc-2",),
    ),
    DemoProviderCall(
        ActionType.OBSERVE,
        "复核地下患者的生命体征与连续监测历史",
        "复核地下观察对象的即时指标与连续监测历史，并开放控制室路径。",
        12,
        "death_certificate.investigation",
        5,
        "death_certificate.observation_level",
        19,
        12,
        3,
        ("scenario-npc-3",),
    ),
)

_DEMO_PUBLIC_ACTION_TYPES = (
    ActionType.CONTINUE,
    ActionType.CUSTOM,
    ActionType.EXPLORE,
    ActionType.OBSERVE,
    ActionType.TALK,
)

_DEMO_PROVIDER_ACTION_TYPES = frozenset(
    {
        ActionType.CUSTOM,
        ActionType.EXPLORE,
        ActionType.MOVE,
        ActionType.OBSERVE,
        ActionType.TALK,
    }
)


@dataclass(frozen=True, slots=True)
class DemoProviderCheckpoint:
    state_version: int
    turn_number: int
    session_phase: str
    scenario_id: str
    scenario_version: str
    character_definition_id: str | None
    snapshot_state_version: int
    snapshot_round_trips_exactly: bool
    state_schema_version: int
    state_content_version: str
    player_id: str
    phase_id: str
    phase_beat_index: int
    current_location_id: str
    ending_status: str
    current_decision_id: str | None
    event_count: int
    event_sequence_numbers: tuple[int, ...]
    turn_request_count: int
    resulting_state_versions: tuple[int, ...]
    narrative_job_count: int
    provider_job_prepared_versions: tuple[int, ...]
    provider_job_statuses: tuple[str, ...]
    frame_scenario_id: str
    frame_phase_id: str
    frame_location_id: str
    frame_decision_required: bool
    public_action_types: tuple[ActionType, ...]


@dataclass(slots=True)
class _DemoProviderAuthorization:
    authority_marker: object
    originating_task: asyncio.Task[Any]
    session_id: str
    turn_id: str
    client_request_id: str
    action_signature: str
    stage_index: int
    provider_call_consumed: bool
    provider_returned: bool


_CURRENT_AUTHORIZATION: ContextVar[_DemoProviderAuthorization | None] = ContextVar(
    "demo_provider_authorization", default=None
)


class CanonicalDemoProviderGuard:
    """Fail closed around the one frozen Provider script used by Demo mode."""

    def __init__(
        self,
        provider: NarrativeProvider,
        store: Any,
        *,
        authority_capability: object,
    ) -> None:
        self.__provider = provider
        self._store = store
        self._authority_capability = authority_capability
        self._authority_marker = object()
        self._session_sequence_locks: dict[str, asyncio.Lock] = {}

    def completed_calls(self, session_id: str) -> int:
        progress = self._store.snapshot().provider_progress.get(session_id)
        if progress is None:
            raise NarrativeProposalRejectedError()
        return progress

    def sequence_lock(self, session_id: str) -> asyncio.Lock:
        return self._session_sequence_locks.setdefault(session_id, asyncio.Lock())

    def authority_snapshot(self) -> Any:
        return self._store.snapshot()

    @staticmethod
    def governs(submission: ActionSubmission) -> bool:
        return submission.action_type in _DEMO_PROVIDER_ACTION_TYPES

    @staticmethod
    def _reject_active_authorization() -> None:
        if _CURRENT_AUTHORIZATION.get() is not None:
            raise NarrativeProposalRejectedError()

    def authorize_submission(
        self,
        capability: object,
        submission: ActionSubmission,
        *,
        checkpoint_factory: Callable[[], DemoProviderCheckpoint],
    ) -> Token[_DemoProviderAuthorization | None]:
        self._reject_active_authorization()
        checkpoint = checkpoint_factory()
        if capability is not self._authority_capability:
            raise NarrativeProposalRejectedError()
        snapshot = self._store.snapshot()
        key = (submission.session_id, submission.client_request_id)
        if key in snapshot.turn_requests:
            raise RuntimeError("committed Demo retry must bypass Provider authorization")
        matching_job = next(
            (
                job
                for job in snapshot.narrative_jobs.values()
                if job.session_id == submission.session_id
                and job.client_request_id == submission.client_request_id
            ),
            None,
        )
        stage_index, expected = self._next_expected(submission.session_id, snapshot)
        if matching_job is None and any(
            job.session_id == submission.session_id
            and job.prepared_state_version == expected.state_version
            for job in snapshot.narrative_jobs.values()
        ):
            raise NarrativeProposalRejectedError()
        self._validate_submission(submission, expected)
        if matching_job is not None and (
            matching_job.prepared_state_version != expected.state_version
            or matching_job.provider_name != "deterministic-demo"
            or matching_job.model_name != "deterministic-demo-v1"
        ):
            raise NarrativeProposalRejectedError()
        self._validate_checkpoint(
            checkpoint,
            expected,
            stage_index,
            expected_job_count=(
                expected.prior_provider_job_count
                + (1 if matching_job is not None else 0)
            ),
        )
        authorization = _DemoProviderAuthorization(
            authority_marker=self._authority_marker,
            originating_task=self._current_task(),
            session_id=submission.session_id,
            turn_id=submission.turn_id,
            client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(),
            stage_index=stage_index,
            provider_call_consumed=(
                matching_job is not None
                and matching_job.status is not NarrativeJobStatus.PREPARED
            ),
            provider_returned=(
                matching_job is not None
                and matching_job.status is NarrativeJobStatus.PROPOSAL_VALIDATED
            ),
        )
        return _CURRENT_AUTHORIZATION.set(authorization)

    @staticmethod
    def reset_authorization(
        token: Token[_DemoProviderAuthorization | None],
    ) -> None:
        _CURRENT_AUTHORIZATION.reset(token)

    def has_committed_request(self, submission: ActionSubmission) -> bool:
        snapshot = self._store.snapshot()
        return (
            submission.session_id,
            submission.client_request_id,
        ) in snapshot.turn_requests

    @staticmethod
    def _validate_submission(
        submission: ActionSubmission, expected: DemoProviderCall
    ) -> None:
        if (
            submission.action_type is not expected.action_type
            or submission.description != expected.description
            or submission.dialogue is not None
            or submission.target_ids
            or submission.tool_ids
            or submission.decision_id is not None
            or submission.choice_id is not None
            or submission.item_instance_id is not None
            or submission.equipment_slot_id is not None
            or submission.skill_definition_id is not None
        ):
            raise NarrativeProposalRejectedError()

    async def generate(
        self, request: NarrativeRequest
    ) -> UntrustedNarrativeProposal:
        authorization = _CURRENT_AUTHORIZATION.get()
        current_task = self._current_task()
        if (
            authorization is None
            or authorization.authority_marker is not self._authority_marker
            or authorization.originating_task is not current_task
            or authorization.provider_call_consumed
        ):
            raise NarrativeProposalRejectedError()
        authorization.provider_call_consumed = True
        snapshot = self._store.snapshot()
        stage_index, expected = self._next_expected(
            authorization.session_id, snapshot
        )
        intent = request.player_intent
        candidates = request.outcome_candidates
        first_candidate = candidates[0] if candidates else None
        if (
            stage_index != authorization.stage_index
            or not self.sequence_lock(authorization.session_id).locked()
            or self._store.session_lock_held(authorization.session_id)
            or intent.action_type is not expected.action_type
            or intent.description != expected.description
            or intent.dialogue is not None
            or intent.target_ids
            or intent.tool_ids
            or intent.selected_choice_id is not None
            or intent.item_instance_id is not None
            or intent.equipment_slot_id is not None
            or intent.skill_definition_id is not None
            or len(candidates) != 1
            or first_candidate is None
            or first_candidate.safe_description != expected.safe_description
            or tuple(item.value for item in first_candidate.allowed_results)
            != ("SUCCESS",)
            or first_candidate.allowed_entity_ids != expected.allowed_entity_ids
            or request.frame.scenario_id != "death_certificate"
            or request.frame.phase_id != expected.phase_id
            or request.frame.current_location_id != expected.current_location_id
            or request.frame.decision_required
        ):
            raise NarrativeProposalRejectedError()
        proposal = await self.__provider.generate(request)
        authorization.provider_returned = True
        return proposal

    async def aclose(self) -> None:
        await self.__provider.aclose()

    def stage_progress(
        self,
        capability: object,
        uow: Any,
        submission: ActionSubmission,
    ) -> None:
        authorization = _CURRENT_AUTHORIZATION.get()
        current_task = self._current_task()
        if (
            capability is not self._authority_capability
            or authorization is None
            or authorization.authority_marker is not self._authority_marker
            or authorization.originating_task is not current_task
            or authorization.session_id != submission.session_id
            or authorization.turn_id != submission.turn_id
            or authorization.client_request_id != submission.client_request_id
            or authorization.action_signature != submission.action_signature()
            or not authorization.provider_call_consumed
            or not authorization.provider_returned
        ):
            raise NarrativeProposalRejectedError()
        uow.stage_provider_progress(
            submission.session_id,
            expected_progress=authorization.stage_index,
            next_progress=authorization.stage_index + 1,
        )

    def assert_complete(self, session_id: str) -> None:
        if self.completed_calls(session_id) != len(DEMO_PROVIDER_SCRIPT):
            raise NarrativeProposalRejectedError()

    @staticmethod
    def _current_task() -> asyncio.Task[Any]:
        try:
            task = asyncio.current_task()
        except RuntimeError:
            raise NarrativeProposalRejectedError() from None
        if task is None:
            raise NarrativeProposalRejectedError()
        return task

    def _next_expected(
        self, session_id: str, snapshot: Any | None = None
    ) -> tuple[int, DemoProviderCall]:
        current = snapshot if snapshot is not None else self._store.snapshot()
        completed_calls = current.provider_progress.get(session_id)
        if (
            completed_calls is None
            or completed_calls < 0
            or completed_calls >= len(DEMO_PROVIDER_SCRIPT)
        ):
            raise NarrativeProposalRejectedError()
        return completed_calls, DEMO_PROVIDER_SCRIPT[completed_calls]

    @staticmethod
    def _validate_checkpoint(
        actual: DemoProviderCheckpoint,
        expected: DemoProviderCall,
        stage_index: int,
        expected_job_count: int,
    ) -> None:
        expected_job_versions = tuple(
            item.state_version for item in DEMO_PROVIDER_SCRIPT[:stage_index]
        )
        if (
            actual.state_version != expected.state_version
            or actual.turn_number != 0
            or actual.session_phase != "AWAITING_ACTION"
            or actual.scenario_id != "death_certificate"
            or actual.scenario_version != "death-certificate-1.1.0"
            or actual.character_definition_id
            != "character.death_certificate.investigator"
            or actual.snapshot_state_version != expected.state_version
            or not actual.snapshot_round_trips_exactly
            or actual.state_schema_version != 3
            or actual.state_content_version != "death-certificate-1.1.0"
            or actual.player_id != "demo-player"
            or actual.phase_id != expected.phase_id
            or actual.phase_beat_index != expected.phase_beat_index
            or actual.current_location_id != expected.current_location_id
            or actual.ending_status != "ACTIVE"
            or actual.current_decision_id is not None
            or actual.event_count != expected.event_count
            or actual.event_sequence_numbers
            != tuple(range(1, expected.event_count + 1))
            or actual.turn_request_count != expected.turn_request_count
            or actual.resulting_state_versions
            != tuple(range(1, expected.state_version + 1))
            or actual.narrative_job_count != expected_job_count
            or actual.provider_job_prepared_versions != expected_job_versions
            or actual.provider_job_statuses
            != ("COMMITTED",) * expected.prior_provider_job_count
            or actual.frame_scenario_id != "death_certificate"
            or actual.frame_phase_id != expected.phase_id
            or actual.frame_location_id != expected.current_location_id
            or actual.frame_decision_required
            or actual.public_action_types != _DEMO_PUBLIC_ACTION_TYPES
        ):
            raise NarrativeProposalRejectedError()


class DeterministicDemoScenarioEventIssuer(TrustedScenarioEventIssuer):
    """Keep Demo decision evidence stable across caller-owned opaque identities."""

    @staticmethod
    def _event_id(submission: ActionSubmission) -> str:
        if submission.decision_id is None or submission.choice_id is None:
            raise ValueError("Demo decision event requires a bound decision and choice")
        digest = hashlib.sha256(
            "\0".join(
                (
                    submission.session_id,
                    submission.decision_id,
                    submission.choice_id,
                )
            ).encode("utf-8")
        ).hexdigest()[:32]
        return f"decision.{digest}"
