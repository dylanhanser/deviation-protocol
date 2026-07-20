from __future__ import annotations

from collections.abc import Callable
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    CandidateStateInvalidError,
    IdempotencyConflictError,
    NarrativeJobActiveError,
    NarrativeJobStaleError,
    NarrativeOutcomeUnknownError,
    NarrativeOutcomeUnavailableError,
    NarrativeProviderNotConfiguredError,
    SessionNotFoundError,
    SnapshotNotFoundError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
    StoredTurnResponseInvalidError,
    UnsupportedResolutionError,
)
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.narrative_models import (
    PROMPT_SCHEMA_VERSION,
    NarrativeBoundaryError,
    NarrativePlayerIntent,
    NarrativeProposalRejectedError,
    NarrativeProvider,
    NarrativeProviderAuthenticationError,
    NarrativeProviderBalanceError,
    NarrativeProviderRequestError,
    NarrativeProviderResponseError,
    NarrativeProviderTruncatedError,
    NarrativeProviderUnavailableError,
    NarrativeRequest,
    NarrativeRequestRejectedError,
    NarrativePublicReferences,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.narrative_outcome_policy import (
    NarrativeEventIssuer,
    NarrativeOutcomePolicy,
    allowed_narrative_outcomes,
    proposal_digest,
    state_fingerprint,
)
from deviation_protocol.application.narrative_validation import NarrativeProposalValidator
from deviation_protocol.application.resolution import PlayerFeedback, ResolutionResult, ResolutionStatus
from deviation_protocol.application.scenario_event_bridge import bind_public_decision_frame
from deviation_protocol.application.story_director import StoryDirectorError
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.scenario import EndingStatus, ScenarioDefinition
from deviation_protocol.domain.state import GameState


IdGenerator = Callable[[], str]


def _uuid() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class _Prepared:
    job: NarrativeJob
    submission: ActionSubmission


@dataclass(slots=True)
class DurableNarrativeTurnOrchestrator(FirstPhaseTurnOrchestrator):
    """Durable prepare/call/finalize coordination with no provider call in a UoW."""

    narrative_provider: NarrativeProvider | None = None
    provider_name: str = "deepseek"
    model_name: str = "deepseek-v4-flash"
    style_profile_id: str = "original-zh-second-person-v1"
    style_profile_version: str = "1.0.0"
    proposal_validator: NarrativeProposalValidator = field(
        default_factory=NarrativeProposalValidator
    )
    outcome_policy: NarrativeOutcomePolicy = field(default_factory=NarrativeOutcomePolicy)
    narrative_event_issuer: NarrativeEventIssuer = field(default_factory=NarrativeEventIssuer)
    job_id_generator: IdGenerator = _uuid
    lease_token_generator: IdGenerator = _uuid
    worker_id_generator: IdGenerator = _uuid
    lease_duration: timedelta = timedelta(minutes=2)

    def __post_init__(self) -> None:
        FirstPhaseTurnOrchestrator.__post_init__(self)
        if self.lease_duration <= timedelta(seconds=0) or self.lease_duration > timedelta(minutes=10):
            raise ValueError("narrative lease duration is outside the safe bound")

    async def handle(self, submission: ActionSubmission) -> TurnResponse:
        prepared_or_response = await self._prepare_or_execute(submission)
        if isinstance(prepared_or_response, TurnResponse):
            return prepared_or_response
        prepared = prepared_or_response
        claimed = await self._claim(prepared.job.job_id)
        if claimed is None:
            return self._pending_response(prepared.job)

        if claimed.status is NarrativeJobStatus.PROPOSAL_VALIDATED:
            return await self._finalize_or_record(claimed, submission)

        request = NarrativeRequest.model_validate(
            claimed.narrative_request, strict=False
        )
        assert self.narrative_provider is not None
        try:
            untrusted = await self.narrative_provider.generate(request)
        except asyncio.CancelledError as exc:
            await self._record_provider_failure(claimed, exc)
            raise
        except NarrativeBoundaryError as exc:
            await self._record_provider_failure(claimed, exc)
            raise
        except Exception as exc:
            await self._record_provider_failure(claimed, exc)
            raise NarrativeProviderUnavailableError() from None
        try:
            validated = self.proposal_validator.validate(
                untrusted,
                request=request,
                public_references=self._public_references(request),
            )
        except NarrativeBoundaryError as exc:
            await self._record_provider_failure(claimed, exc)
            raise
        except (AttributeError, TypeError, ValueError, ValidationError) as exc:
            safe_error = NarrativeProposalRejectedError()
            await self._record_provider_failure(claimed, safe_error)
            raise safe_error from None

        try:
            stored = await self._store_validated_proposal(claimed, validated)
        except NarrativeJobStaleError:
            await self._set_terminal_status(
                claimed,
                NarrativeJobStatus.OUTCOME_UNKNOWN,
                "NARRATIVE_OUTCOME_UNKNOWN",
            )
            raise NarrativeOutcomeUnknownError(claimed.session_id) from None
        return await self._finalize_or_record(stored, submission)

    async def _finalize_or_record(
        self, job: NarrativeJob, submission: ActionSubmission
    ) -> TurnResponse:
        try:
            return await self._finalize(job, submission)
        except NarrativeJobStaleError:
            await self._set_terminal_status(
                job, NarrativeJobStatus.STALE, "NARRATIVE_JOB_STALE"
            )
            raise
        except (NarrativeProposalRejectedError, ValueError, StoryDirectorError):
            await self._set_terminal_status(
                job,
                NarrativeJobStatus.FAILED_TERMINAL,
                "NARRATIVE_PROPOSAL_REJECTED",
            )
            raise NarrativeProposalRejectedError() from None

    async def _prepare_or_execute(
        self, submission: ActionSubmission
    ) -> _Prepared | TurnResponse:
        async with self.uow_factory() as uow:
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise SessionNotFoundError(submission.session_id)
            stored_response = await uow.turn_requests.get_by_client_request_id(
                submission.session_id, submission.client_request_id
            )
            if stored_response is not None:
                return self._replay_response(stored_response, submission)
            existing_job = await uow.narrative_jobs.get_by_client_request_id(
                submission.session_id,
                submission.client_request_id,
            )
            if existing_job is not None:
                # Re-read the known row with a lock. Avoid SELECT FOR UPDATE on an
                # absent composite-key range, which can introduce next-key locks.
                existing_job = await uow.narrative_jobs.get(
                    existing_job.job_id, for_update=True
                )
                if existing_job is None:
                    raise RuntimeError("narrative job disappeared while locking")
                self._validate_job_request(existing_job, submission)
                if (
                    existing_job.status in ACTIVE_NARRATIVE_JOB_STATUSES
                    and existing_job.prompt_schema_version != PROMPT_SCHEMA_VERSION
                ):
                    stale = self._transition_job(
                        existing_job,
                        {
                            "status": NarrativeJobStatus.STALE,
                            "lease_token": None,
                            "lease_owner": None,
                            "lease_expires_at": None,
                            "error_code": "NARRATIVE_REQUEST_SCHEMA_STALE",
                            "updated_at": self._now(),
                        },
                    )
                    if await uow.narrative_jobs.replace(
                        stale,
                        expected_status=existing_job.status,
                        expected_lease_token=existing_job.lease_token,
                        expected_lease_owner=existing_job.lease_owner,
                    ):
                        await uow.commit()
                    raise NarrativeJobStaleError(submission.session_id)
                if (
                    existing_job.status is NarrativeJobStatus.IN_PROGRESS
                    and self._lease_expired(existing_job, self._now())
                ):
                    unknown = self._transition_job(
                        existing_job,
                        {
                            "status": NarrativeJobStatus.OUTCOME_UNKNOWN,
                            "lease_token": None,
                            "lease_owner": None,
                            "lease_expires_at": None,
                            "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                            "updated_at": self._now(),
                        },
                    )
                    if await uow.narrative_jobs.replace(
                        unknown,
                        expected_status=existing_job.status,
                        expected_lease_token=existing_job.lease_token,
                        expected_lease_owner=existing_job.lease_owner,
                    ):
                        await uow.commit()
                        raise NarrativeOutcomeUnknownError(submission.session_id)
                    return self._pending_response(existing_job)
                return self._existing_job_result(existing_job)

            game_session = await uow.sessions.get(submission.session_id)
            if game_session is None:
                raise SessionNotFoundError(submission.session_id)
            snapshot = await uow.sessions.get_latest_snapshot(submission.session_id)
            if snapshot is None:
                raise SnapshotNotFoundError(submission.session_id)
            if snapshot.state_version != game_session.state_version:
                raise SnapshotStateVersionMismatchError(submission.session_id)
            state = self._load_state(snapshot.state, submission.session_id)
            if state.player.player_id != game_session.player_id:
                raise SnapshotSessionMismatchError(submission.session_id)
            definition = self._scenario_definition(
                state,
                game_session.scenario_id,
                game_session.scenario_version,
                submission.session_id,
            )
            visible_npcs = self._visible_runtime_npc_ids(state, definition)
            trusted = self.context_factory.create_trusted(
                submission,
                state=state,
                catalog=self.catalog,
                current_turn_id=submission.turn_id,
                session_phase=game_session.phase,
                visible_entity_ids=visible_npcs,
                interactable_entity_ids=visible_npcs,
                environment_tool_ids=(),
                skill_learning_authorization=None,
                processed_client_request_ids=(),
            )
            resolution = await self.resolver.resolve(trusted, state, self.catalog)
            if resolution.status is ResolutionStatus.ANOMALY_EVALUATION_REQUIRED:
                raise UnsupportedResolutionError(submission.session_id)
            resolution, frame = self._coordinate_scenario(
                submission,
                state,
                resolution,
                definition,
                state_version=game_session.state_version,
            )
            active = await uow.narrative_jobs.get_active_for_session(
                submission.session_id
            )
            if active is not None:
                is_safe_nonmutation = (
                    resolution.status is ResolutionStatus.REJECTED_LOCAL
                    or (
                        resolution.status is ResolutionStatus.RESOLVED_LOCAL
                        and not resolution.state_changed
                    )
                )
                if not is_safe_nonmutation:
                    raise NarrativeJobActiveError(submission.session_id)

            if resolution.status is not ResolutionStatus.NARRATIVE_REQUIRED:
                return await self._commit_local_result(
                    uow,
                    submission,
                    game_session,
                    resolution,
                    frame,
                    definition,
                )
            if self.narrative_provider is None:
                raise NarrativeProviderNotConfiguredError(submission.session_id)
            if definition is None or frame is None or state.scenario_runtime is None:
                raise NarrativeOutcomeUnavailableError(submission.session_id)
            if state.scenario_runtime.ending_status is not EndingStatus.ACTIVE:
                raise NarrativeOutcomeUnavailableError(submission.session_id)
            allowed = allowed_narrative_outcomes(
                submission=submission,
                state=state,
                state_version=game_session.state_version,
                definition=definition,
                frame=frame,
            )
            if not allowed:
                raise NarrativeOutcomeUnavailableError(submission.session_id)
            recent = await uow.narrative_jobs.recent_committed_texts(
                submission.session_id, limit=6
            )
            character = self.catalog.character(state.player.character_definition_id)
            if character is None:
                raise CandidateStateInvalidError(submission.session_id)
            request = NarrativeRequest(
                frame=frame,
                player_memory=self.memory_projector.project(
                    state, self.scenario_catalog
                ),
                player_intent=NarrativePlayerIntent.from_submission(submission),
                player_visible_character_tags=tuple(sorted(character.tags)),
                recent_narrative_fragments=recent,
                public_story_summary="",
                style_profile_id=self.style_profile_id,
                outcome_candidates=tuple(item.candidate for item in allowed),
            )
            now = self._now()
            request_json = request.model_dump(mode="json")
            job = NarrativeJob(
                job_id=self._generated_id(self.job_id_generator, "job"),
                session_id=submission.session_id,
                turn_id=submission.turn_id,
                client_request_id=submission.client_request_id,
                action_signature=submission.action_signature(),
                prepared_state_version=game_session.state_version,
                state_fingerprint=state_fingerprint(state),
                scenario_id=definition.scenario_id,
                scenario_content_version=definition.content_version,
                request_fingerprint=self._json_digest(request_json),
                narrative_request=request_json,
                prompt_schema_version=request.prompt_schema_version,
                style_profile_version=self.style_profile_version,
                provider_name=self.provider_name,
                model_name=self.model_name,
                created_at=now,
                updated_at=now,
            )
            await uow.narrative_jobs.add(job)
            await uow.commit()
            return _Prepared(job=job, submission=submission)

    async def _commit_local_result(
        self,
        uow: Any,
        submission: ActionSubmission,
        game_session: Any,
        resolution: ResolutionResult,
        frame: NarrativeFrame | None,
        definition: ScenarioDefinition | None,
    ) -> TurnResponse:
        expected_version = game_session.state_version
        resulting_version = expected_version
        if resolution.state_changed:
            await self._persist_state_change(
                uow=uow,
                submission=submission,
                game_session=game_session,
                resolution=resolution,
                definition=definition,
                expected_version=expected_version,
            )
            resulting_version += 1
        response = self._build_response(
            submission, resolution, resulting_version, frame
        )
        await uow.turn_requests.add(
            submission,
            response.action_signature,
            self._route_for(resolution.status),
            response.to_persistence(),
        )
        await uow.commit()
        return response

    async def _claim(self, job_id: str) -> NarrativeJob | None:
        unknown = False
        claimed: NarrativeJob | None = None
        async with self.uow_factory() as uow:
            job = await uow.narrative_jobs.get(job_id, for_update=True)
            if job is None:
                raise RuntimeError("prepared narrative job disappeared")
            now = self._now()
            if job.status is NarrativeJobStatus.PREPARED:
                token = self._generated_id(self.lease_token_generator, "lease")
                owner = self._generated_id(self.worker_id_generator, "worker")
                claimed = self._transition_job(
                    job,
                    {
                        "status": NarrativeJobStatus.IN_PROGRESS,
                        "attempt_count": 1,
                        "lease_token": token,
                        "lease_owner": owner,
                        "lease_expires_at": now + self.lease_duration,
                        "updated_at": now,
                    },
                )
                if not await uow.narrative_jobs.replace(
                    claimed, expected_status=NarrativeJobStatus.PREPARED
                ):
                    return None
                await uow.commit()
            elif job.status is NarrativeJobStatus.IN_PROGRESS:
                if self._aware(job.lease_expires_at) <= now:
                    terminal = self._transition_job(
                        job,
                        {
                            "status": NarrativeJobStatus.OUTCOME_UNKNOWN,
                            "lease_token": None,
                            "lease_owner": None,
                            "lease_expires_at": None,
                            "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                            "updated_at": now,
                        },
                    )
                    if not await uow.narrative_jobs.replace(
                        terminal,
                        expected_status=NarrativeJobStatus.IN_PROGRESS,
                        expected_lease_token=job.lease_token,
                        expected_lease_owner=job.lease_owner,
                    ):
                        return None
                    await uow.commit()
                    unknown = True
                else:
                    return None
            elif job.status is NarrativeJobStatus.PROPOSAL_VALIDATED:
                if not self._lease_expired(job, now):
                    return None
                resumed = self._transition_job(
                    job,
                    {
                        "lease_token": self._generated_id(
                            self.lease_token_generator, "lease"
                        ),
                        "lease_owner": self._generated_id(
                            self.worker_id_generator, "worker"
                        ),
                        "lease_expires_at": now + self.lease_duration,
                        "updated_at": now,
                    },
                )
                if not await uow.narrative_jobs.replace(
                    resumed,
                    expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
                    expected_lease_token=job.lease_token,
                    expected_lease_owner=job.lease_owner,
                ):
                    return None
                await uow.commit()
                claimed = resumed
            else:
                return None
        if unknown:
            raise NarrativeOutcomeUnknownError(job.session_id)
        return claimed

    async def _store_validated_proposal(
        self, claimed: NarrativeJob, proposal: ValidatedNarrativeProposal
    ) -> NarrativeJob:
        payload = proposal.model_dump(mode="json")
        async with self.uow_factory() as uow:
            current = await uow.narrative_jobs.get(claimed.job_id, for_update=True)
            now = self._now()
            if not self._same_lease(current, claimed) or self._lease_expired(claimed, now):
                raise NarrativeJobStaleError(claimed.session_id)
            stored = self._transition_job(
                claimed,
                {
                    "status": NarrativeJobStatus.PROPOSAL_VALIDATED,
                    "validated_proposal": payload,
                    "validated_proposal_digest": proposal_digest(proposal),
                    "updated_at": now,
                },
            )
            if not await uow.narrative_jobs.replace(
                stored,
                expected_status=NarrativeJobStatus.IN_PROGRESS,
                expected_lease_token=claimed.lease_token,
                expected_lease_owner=claimed.lease_owner,
            ):
                raise NarrativeJobStaleError(claimed.session_id)
            await uow.commit()
        return stored

    async def _finalize(
        self, job: NarrativeJob, submission: ActionSubmission
    ) -> TurnResponse:
        async with self.uow_factory() as uow:
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise SessionNotFoundError(submission.session_id)
            current = await uow.narrative_jobs.get(job.job_id, for_update=True)
            now = self._now()
            if (
                current is None
                or current.status is not NarrativeJobStatus.PROPOSAL_VALIDATED
                or not self._same_lease(current, job)
                or self._lease_expired(current, now)
            ):
                raise NarrativeJobStaleError(submission.session_id)
            self._validate_job_request(current, submission)
            game_session = await uow.sessions.get(submission.session_id)
            snapshot = await uow.sessions.get_latest_snapshot(submission.session_id)
            if game_session is None or snapshot is None:
                raise NarrativeJobStaleError(submission.session_id)
            if (
                game_session.state_version != current.prepared_state_version
                or snapshot.state_version != current.prepared_state_version
            ):
                raise NarrativeJobStaleError(submission.session_id)
            state = self._load_state(snapshot.state, submission.session_id)
            definition = self._scenario_definition(
                state,
                game_session.scenario_id,
                game_session.scenario_version,
                submission.session_id,
            )
            if (
                definition is None
                or state_fingerprint(state) != current.state_fingerprint
                or definition.scenario_id != current.scenario_id
                or definition.content_version != current.scenario_content_version
            ):
                raise NarrativeJobStaleError(submission.session_id)
            trusted = self.context_factory.create_trusted(
                submission,
                state=state,
                catalog=self.catalog,
                current_turn_id=submission.turn_id,
                session_phase=game_session.phase,
                visible_entity_ids=self._visible_runtime_npc_ids(state, definition),
                interactable_entity_ids=self._visible_runtime_npc_ids(state, definition),
                environment_tool_ids=(),
                skill_learning_authorization=None,
                processed_client_request_ids=(),
            )
            resolution = await self.resolver.resolve(trusted, state, self.catalog)
            resolution, frame = self._coordinate_scenario(
                submission,
                state,
                resolution,
                definition,
                state_version=game_session.state_version,
            )
            if frame is None or current.validated_proposal is None or current.validated_proposal_digest is None:
                raise NarrativeJobStaleError(submission.session_id)
            persisted_request = NarrativeRequest.model_validate(
                current.narrative_request, strict=False
            )
            if (
                self._json_digest(persisted_request.model_dump(mode="json"))
                != current.request_fingerprint
                or persisted_request.frame != frame
                or persisted_request.player_memory
                != self.memory_projector.project(state, self.scenario_catalog)
            ):
                raise NarrativeJobStaleError(submission.session_id)
            proposal = ValidatedNarrativeProposal.model_validate(
                current.validated_proposal, strict=False
            )
            assert current.lease_token is not None and current.lease_owner is not None
            authorized = self.outcome_policy.authorize(
                proposal,
                job_id=current.job_id,
                lease_token=current.lease_token,
                lease_owner=current.lease_owner,
                submission=submission,
                state=state,
                state_version=game_session.state_version,
                definition=definition,
                frame=frame,
                resolution_status=resolution.status,
                expected_state_fingerprint=current.state_fingerprint,
                expected_proposal_digest=current.validated_proposal_digest,
            )
            sealed = self.narrative_event_issuer.issue(
                authorized,
                job_id=current.job_id,
                lease_token=current.lease_token,
                lease_owner=current.lease_owner,
                submission=submission,
                state=state,
                state_version=game_session.state_version,
                definition=definition,
                proposal=proposal,
            )
            character = self.catalog.character(state.player.character_definition_id)
            if character is None:
                raise CandidateStateInvalidError(submission.session_id)
            directed = self.story_director.advance_after_verified_result(
                state,
                definition,
                (sealed,),
                profession_tags=frozenset(character.tags)
                & set(definition.available_profession_tags),
            )
            generated = tuple(
                DomainEventDraft(
                    "ScenarioRuntimeEventGenerated",
                    {
                        "scenario_event_id": item.event_id,
                        "scenario_event_type": item.event_type,
                    },
                )
                for item in directed.generated_events
            )
            accepted = DomainEventDraft(
                "NarrativeOutcomeAccepted",
                {
                    "source": "VALIDATED_NARRATIVE_OUTCOME",
                    "job_id": current.job_id,
                    "outcome_rule_id": authorized.rule.rule_id,
                    "outcome_result": authorized.result_name,
                    "proposal_digest": current.validated_proposal_digest,
                    "scenario_event_id": sealed.event_id,
                    "scenario_event_type": sealed.event_type,
                    "npc_definition_ids": authorized.npc_definition_ids,
                },
            )
            result = ResolutionResult(
                status=ResolutionStatus.RESOLVED_LOCAL,
                success=True,
                result_code="NARRATIVE_OUTCOME_COMMITTED",
                updated_state=directed.candidate_state,
                state_changed=True,
                events=(accepted, *generated),
                feedback=PlayerFeedback(
                    "NARRATIVE_OUTCOME_COMMITTED",
                    {"outcome_result": authorized.result_name},
                ),
            )
            if self._lease_expired(current, self._now()):
                raise NarrativeJobStaleError(submission.session_id)
            await self._persist_state_change(
                uow=uow,
                submission=submission,
                game_session=game_session,
                resolution=result,
                definition=definition,
                expected_version=current.prepared_state_version,
            )
            final_frame = bind_public_decision_frame(
                directed.frame,
                session_id=submission.session_id,
                state_version=current.prepared_state_version + 1,
                scenario_content_version=definition.content_version,
            )
            response = TurnResponse(
                session_id=submission.session_id,
                client_request_id=submission.client_request_id,
                action_signature=submission.action_signature(),
                resolution_kind=ResolutionStatus.NARRATIVE_COMMITTED,
                result_code="NARRATIVE_OUTCOME_COMMITTED",
                feedback_code="NARRATIVE_OUTCOME_COMMITTED",
                feedback_parameters={"outcome_result": authorized.result_name},
                resulting_state_version=current.prepared_state_version + 1,
                state_changed=True,
                narrative_required=True,
                narrative_pending=False,
                narrative_frame=final_frame,
                narrative_text=proposal.proposal.narrative_text,
                narrative_status="COMMITTED",
            )
            await uow.turn_requests.add(
                submission,
                response.action_signature,
                ActionRoute.NARRATIVE_NORMAL,
                response.to_persistence(),
            )
            commit_now = self._now()
            if self._lease_expired(current, commit_now):
                raise NarrativeJobStaleError(submission.session_id)
            committed = self._transition_job(
                current,
                {
                    "status": NarrativeJobStatus.COMMITTED,
                    "lease_token": None,
                    "lease_owner": None,
                    "lease_expires_at": None,
                    "outcome_rule_id": authorized.rule.rule_id,
                    "accepted_narrative_text": proposal.proposal.narrative_text,
                    "updated_at": commit_now,
                },
            )
            if not await uow.narrative_jobs.replace(
                committed,
                expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
                expected_lease_token=current.lease_token,
                expected_lease_owner=current.lease_owner,
            ):
                raise NarrativeJobStaleError(submission.session_id)
            await uow.commit()
            return response

    async def _record_provider_failure(
        self, job: NarrativeJob, exc: BaseException
    ) -> None:
        terminal = isinstance(
            exc,
            (
                NarrativeProviderAuthenticationError,
                NarrativeProviderBalanceError,
                NarrativeProviderRequestError,
                NarrativeProviderResponseError,
                NarrativeProviderTruncatedError,
                NarrativeRequestRejectedError,
                NarrativeProposalRejectedError,
            ),
        )
        status = (
            NarrativeJobStatus.FAILED_TERMINAL
            if terminal
            else NarrativeJobStatus.OUTCOME_UNKNOWN
        )
        code = getattr(exc, "code", "NARRATIVE_OUTCOME_UNKNOWN")
        await self._set_terminal_status(job, status, code)

    async def _set_terminal_status(
        self, job: NarrativeJob, status: NarrativeJobStatus, code: str
    ) -> None:
        async with self.uow_factory() as uow:
            current = await uow.narrative_jobs.get(job.job_id, for_update=True)
            if current is None or current.status not in {
                NarrativeJobStatus.IN_PROGRESS,
                NarrativeJobStatus.PROPOSAL_VALIDATED,
            }:
                return
            now = self._now()
            if not self._same_lease(current, job) or self._lease_expired(current, now):
                return
            terminal = self._transition_job(
                current,
                {
                    "status": status,
                    "lease_token": None,
                    "lease_owner": None,
                    "lease_expires_at": None,
                    "error_code": code,
                    "updated_at": now,
                },
            )
            if await uow.narrative_jobs.replace(
                terminal,
                expected_status=current.status,
                expected_lease_token=current.lease_token,
                expected_lease_owner=current.lease_owner,
            ):
                await uow.commit()

    def _existing_job_result(self, job: NarrativeJob) -> _Prepared | TurnResponse:
        if job.status is NarrativeJobStatus.PREPARED:
            return _Prepared(job=job, submission=self._submission_from_job(job))
        if job.status in {
            NarrativeJobStatus.IN_PROGRESS,
        }:
            return self._pending_response(job)
        if job.status is NarrativeJobStatus.PROPOSAL_VALIDATED:
            return _Prepared(job=job, submission=self._submission_from_job(job))
        if job.status is NarrativeJobStatus.OUTCOME_UNKNOWN:
            raise NarrativeOutcomeUnknownError(job.session_id)
        if job.status is NarrativeJobStatus.STALE:
            raise NarrativeJobStaleError(job.session_id)
        if job.status is NarrativeJobStatus.COMMITTED:
            raise StoredTurnResponseInvalidError(job.session_id)
        raise NarrativeProposalRejectedError()

    @staticmethod
    def _submission_from_job(job: NarrativeJob) -> ActionSubmission:
        request = NarrativeRequest.model_validate(job.narrative_request, strict=False)
        intent = request.player_intent
        return ActionSubmission(
            session_id=job.session_id,
            turn_id=job.turn_id,
            client_request_id=job.client_request_id,
            action_type=intent.action_type,
            target_ids=intent.target_ids,
            tool_ids=intent.tool_ids,
            description=intent.description,
            dialogue=intent.dialogue,
            choice_id=intent.selected_choice_id,
            item_instance_id=intent.item_instance_id,
            equipment_slot_id=intent.equipment_slot_id,
            skill_definition_id=intent.skill_definition_id,
        )

    @staticmethod
    def _pending_response(job: NarrativeJob) -> TurnResponse:
        request = NarrativeRequest.model_validate(job.narrative_request, strict=False)
        return TurnResponse(
            session_id=job.session_id,
            client_request_id=job.client_request_id,
            action_signature=job.action_signature,
            resolution_kind=ResolutionStatus.NARRATIVE_REQUIRED,
            result_code="NARRATIVE_JOB_PENDING",
            feedback_code="NARRATIVE_JOB_PENDING",
            feedback_parameters={},
            resulting_state_version=job.prepared_state_version,
            state_changed=False,
            narrative_required=True,
            narrative_pending=True,
            narrative_frame=request.frame,
            narrative_status="PENDING",
        )

    @staticmethod
    def _validate_job_request(job: NarrativeJob, submission: ActionSubmission) -> None:
        if (
            job.turn_id != submission.turn_id
            or job.action_signature != submission.action_signature()
        ):
            raise IdempotencyConflictError(submission.session_id)

    @staticmethod
    def _public_references(request: NarrativeRequest) -> NarrativePublicReferences:
        frame = request.frame
        public = {
            *frame.visible_entities,
            *frame.visible_clues,
            frame.current_location_id,
            *request.player_intent.target_ids,
            *request.player_intent.tool_ids,
        }
        if request.player_intent.item_instance_id is not None:
            public.add(request.player_intent.item_instance_id)
        return NarrativePublicReferences(
            allowed_public_entity_ids=frozenset(public),
            visible_runtime_npc_ids=frozenset(
                item.npc_id for item in frame.npc_knowledge
            ),
            player_owned_item_ids=frozenset(
                (request.player_intent.item_instance_id,)
                if request.player_intent.item_instance_id is not None
                else ()
            ),
        )

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("narrative clock must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        if value is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    def _lease_expired(self, job: NarrativeJob, now: datetime) -> bool:
        return self._aware(job.lease_expires_at) <= now

    @staticmethod
    def _same_lease(left: NarrativeJob | None, right: NarrativeJob) -> bool:
        return (
            left is not None
            and left.job_id == right.job_id
            and left.session_id == right.session_id
            and left.turn_id == right.turn_id
            and left.client_request_id == right.client_request_id
            and left.action_signature == right.action_signature
            and left.prepared_state_version == right.prepared_state_version
            and left.state_fingerprint == right.state_fingerprint
            and left.scenario_id == right.scenario_id
            and left.scenario_content_version == right.scenario_content_version
            and left.lease_token == right.lease_token
            and left.lease_owner == right.lease_owner
        )

    @staticmethod
    def _generated_id(generator: IdGenerator, label: str) -> str:
        value = generator()
        minimum = 32 if label == "lease" else 1
        if not isinstance(value, str) or not minimum <= len(value) <= 64:
            raise ValueError(f"{label} ID generator returned an invalid value")
        return value

    @staticmethod
    def _transition_job(job: NarrativeJob, updates: dict[str, Any]) -> NarrativeJob:
        payload = job.model_dump(mode="python")
        payload.update(updates)
        return NarrativeJob.model_validate(payload)

    @staticmethod
    def _json_digest(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
