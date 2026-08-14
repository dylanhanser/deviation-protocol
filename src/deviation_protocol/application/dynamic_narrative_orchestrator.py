from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
import copy
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Literal
import unicodedata
from uuid import uuid4

from pydantic import ValidationError

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.dynamic_narrative_models import (
    DYNAMIC_ACCEPTED_OUTCOME_RULE_ID,
    DYNAMIC_PROMPT_SCHEMA_VERSION,
    DynamicAllocatedPublicFact,
    DynamicCanonicalFact,
    DynamicCurrentScene,
    DynamicNarrativeCapacityExhaustedError,
    DynamicGenerationInstruction,
    DynamicGeneratedPublicFactKeyAllocator,
    DynamicGeneratedPublicFactKeyGrammar,
    DynamicNarrativeLengthBand,
    DynamicNarrativeLengthPolicy,
    DynamicNarrativeLength,
    DynamicNarrativeProvider,
    DynamicNarrativeRequest,
    DynamicNarrativeResponseCategory,
    DynamicNarrativeResponseError,
    DynamicNarrativeSchemaFailureFamily,
    DynamicPlayerAction,
    DynamicProviderCandidateContract,
    DynamicScenarioPremise,
    DynamicScenarioRole,
    DynamicSelectedPlayerCharacter,
    UntrustedDynamicNarrativeCandidate,
    ValidatedDynamicNarrativeCandidate,
    canonical_json,
    meets_zh_cn_action_text_minimum,
    normalize_dynamic_text,
)
from deviation_protocol.application.errors import (
    CandidateStateInvalidError,
    IdempotencyConflictError,
    InvalidScenarioDefinitionError,
    NarrativeJobStaleError,
    NarrativeOutcomeUnknownError,
    SessionNotFoundError,
    SnapshotInvalidError,
    SnapshotNotFoundError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
    StoredTurnResponseInvalidError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_jobs import NarrativeJob, NarrativeJobStatus
from deviation_protocol.application.narrative_models import (
    NarrativeBoundaryError,
    NarrativeProposalRejectedError,
    NarrativeProviderAuthenticationError,
    NarrativeProviderBalanceError,
    NarrativeProviderRateLimitError,
    NarrativeProviderRequestError,
    NarrativeProviderResponseError,
    NarrativeProviderTruncatedError,
    NarrativeProviderUnavailableError,
    NarrativeRequestRejectedError,
)
from deviation_protocol.application.ports import PersistedTurnRequest, UnitOfWork
from deviation_protocol.application.resolution import (
    PlayerFeedback,
    ResolutionResult,
    ResolutionStatus,
)
from deviation_protocol.application.session_service import (
    PlayerSessionView,
    PreparedRunEntryInitialization,
    PublicActionAffordance,
    PublicActionAffordanceSet,
    PublicActionMode,
    PublicActionTarget,
    PublicScenarioPresentation,
    PublicSuggestedAction,
    PublicSuggestedActionSubmission,
    SessionService,
)
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.application.turn_response import (
    CommittedTurnResponseValidationError,
    TurnResponse,
    validate_committed_turn_response_for_recovery,
)
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.content import (
    AttributeModifierEffectDefinition,
    ContentCatalog,
    ResourceModifierEffectDefinition,
)
from deviation_protocol.domain.events import DomainEvent, DomainEventDraft
from deviation_protocol.domain.facts import (
    FactKind,
    FactVisibility,
    StoryMutation,
    StoryMutationError,
    StoryMutationValidator,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.narrative import (
    NarrativeFrame,
    NpcKnowledgeFrame,
    RenderableFact,
    VisibleClock,
)
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.policies import ActionInputKind
from deviation_protocol.domain.run import RunLifecycleStatus, validate_canonical_run
from deviation_protocol.domain.scenario import (
    AlwaysCondition,
    ClockAtLeastCondition,
    ClockAtMostCondition,
    ClueGroupCompleteCondition,
    DecisionsAtLeastCondition,
    EndingStatus,
    EventOccurredCondition,
    FactEqualsCondition,
    FrameMode,
    LocationOpenedCondition,
    NpcAliveAcknowledgedCondition,
    PhaseBeatAtLeastCondition,
    PhaseVisitAtLeastCondition,
    ScenarioDefinition,
)
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from deviation_protocol.domain.state import DomainRuleViolation, GameState, PlayerState


DYNAMIC_FACT_SLOTS = tuple(f"dynamic.narrative.fact.{index:02d}" for index in range(12))
DYNAMIC_SCENE_TITLE = "dynamic.narrative.scene.title"
DYNAMIC_SCENE_SUMMARY = "dynamic.narrative.scene.summary"
DYNAMIC_SUGGESTION_SLOTS = tuple(
    f"dynamic.narrative.suggestion.{index:02d}" for index in range(3)
)
DYNAMIC_RESULT = "dynamic.narrative.result"
DYNAMIC_CONSEQUENCES = "dynamic.narrative.consequences"
DYNAMIC_CONTINUATION = "dynamic.narrative.continuation"
_TERMINAL_STABILIZATION_CAS_LIMIT = 8
DYNAMIC_ALL_SLOTS = frozenset(
    (*DYNAMIC_FACT_SLOTS, DYNAMIC_SCENE_TITLE, DYNAMIC_SCENE_SUMMARY,
     *DYNAMIC_SUGGESTION_SLOTS, DYNAMIC_RESULT, DYNAMIC_CONSEQUENCES,
     DYNAMIC_CONTINUATION)
)
INITIAL_SUGGESTION_0 = "观察周围可见的环境。"
INITIAL_SUGGESTION_1_NONE = "调查眼前的情况。"
INITIAL_SUGGESTION_2 = "谨慎尝试改变当前局面。"
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_INTERNAL_TEXT_MARKERS = (
    "action_signature", "state_version", "client_request_id", "turn_id",
    "rule_id", "rule id", "outcome_token", "outcome token", "job_id",
    "job id", "lease_token", "lease token", "receipt", "provider_name",
    "provider name", "model_name", "model name", "narrative_job",
    "narrative job", "future ending", "trustedscenarioeventissuer",
    "trusted_scenario_event_issuer", "verifiedscenarioevent",
    "verified_scenario_event", "domaineventdraft", "domain_event_draft",
    "capability", "event_seal", "event seal", "policy_trace",
    "anomaly_route", "grant_item", "grant item", "clock_delta",
    "beat_delta", "phase_delta", "fact_update", "clue_update",
    "currency_delta", "resource_delta", "attribute_delta", "skill_grant",
    "anomaly_evaluation_required", "api_key", "authorization",
)
_INTERNAL_ID_PATTERN = re.compile(
    r"\b(?:frame|scenario|phase|decision|fact|clue|event|seal|capability|npc|"
    r"location|item|skill|clock|resource|currency|attribute|choice|ending|"
    r"outcome|rule|job|lease|provider|model|receipt)\."
    r"[A-Za-z0-9_.:-]+",
    re.IGNORECASE,
)
_LONG_SECRET_SHAPE = re.compile(r"\b[0-9a-f]{48,}\b", re.IGNORECASE)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _submission_payload(submission: ActionSubmission) -> dict[str, Any]:
    return {
        "session_id": submission.session_id,
        "turn_id": submission.turn_id,
        "client_request_id": submission.client_request_id,
        "action_type": submission.action_type.value,
        "target_ids": list(submission.target_ids),
        "tool_ids": list(submission.tool_ids),
        "description": submission.description,
        "dialogue": submission.dialogue,
        "decision_id": submission.decision_id,
        "choice_id": submission.choice_id,
        "item_instance_id": submission.item_instance_id,
        "equipment_slot_id": submission.equipment_slot_id,
        "skill_definition_id": submission.skill_definition_id,
    }


def _submission_fingerprint(submission: ActionSubmission) -> str:
    return _digest(_submission_payload(submission))


def _normalize_public_text(value: object, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError("public text is not a string")
    result = normalize_dynamic_text(value)
    if not 1 <= len(result) <= maximum or any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in result
    ):
        raise ValueError("public text is outside its safe boundary")
    return result


def _normalized_fact_semantic_key(value: object) -> str:
    """Return the frozen NFC/whitespace/case-fold identity for a public fact."""

    normalized = _normalize_public_text(value, maximum=80)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", normalized) is None:
        raise ValueError("dynamic public fact key is malformed")
    return normalized.casefold()


@dataclass(frozen=True, slots=True)
class _DynamicAuthority:
    persisted: Any
    state: GameState
    definition: ScenarioDefinition
    participation: Any
    run: Any
    player_character: Any


def _spawn_dynamic_scenario_npcs(
    state: GameState,
    definition: ScenarioDefinition,
    catalog: Any,
) -> None:
    for index, reference in enumerate(definition.npc_references, start=1):
        npc = catalog.npc(reference.npc_definition_id)
        character = (
            catalog.character(npc.character_definition_id) if npc is not None else None
        )
        if (
            npc is None
            or character is None
            or "npc" not in character.tags
            or character.definition_id == state.player.character_definition_id
        ):
            raise InvalidScenarioDefinitionError(definition.scenario_id)
        try:
            state.spawn_npc(catalog, reference.npc_definition_id, f"scenario-npc-{index}")
        except (DomainRuleViolation, TypeError, ValueError):
            raise InvalidScenarioDefinitionError(definition.scenario_id) from None


@dataclass(slots=True)
class DynamicSessionService(SessionService):
    """Director-free Run entry and reconstruction for the bounded spike."""

    def prepare_run_entry_initialization(
        self,
        principal: RequestPrincipal,
        *,
        creation_request_id: str,
        definition: ScenarioDefinition,
        character_definition_id: str,
        created_at: datetime,
    ) -> PreparedRunEntryInitialization:
        if type(principal) is not RequestPrincipal:
            raise TypeError("expected RequestPrincipal")
        if (
            type(creation_request_id) is not str
            or re.fullmatch(r"[0-9a-f]{64}", creation_request_id) is None
        ):
            raise ValueError("Session creation-request identity is invalid")
        if (
            type(created_at) is not datetime
            or created_at.tzinfo is None
            or created_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("Run entry Session timestamp must be exact UTC")
        public = definition.public_client if type(definition) is ScenarioDefinition else None
        character = self.catalog.character(character_definition_id)
        if (
            public is None
            or definition.content_version != self.catalog.content_version
            or character_definition_id != public.default_character_definition_id
            or character is None
            or "npc" in character.tags
        ):
            raise InvalidScenarioDefinitionError(getattr(definition, "scenario_id", "invalid"))
        session_id = self.session_id_generator()
        random_seed = self.seed_generator()
        event_id = self.event_id_generator()
        if (
            type(session_id) is not str
            or not 1 <= len(session_id) <= 64
            or _OPAQUE_ID.fullmatch(session_id) is None
            or type(event_id) is not str
            or not 1 <= len(event_id) <= 64
            or _OPAQUE_ID.fullmatch(event_id) is None
            or type(random_seed) is not int
            or not 0 <= random_seed <= 2**63 - 1
        ):
            raise ValueError("dynamic Run-entry generator returned invalid authority")
        session = GameSession(
            session_id=session_id,
            player_id=principal.player_id,
            scenario_id=definition.scenario_id,
            scenario_version=definition.content_version,
            phase="AWAITING_ACTION",
            turn_number=0,
            state_version=0,
            random_seed=random_seed,
        )
        state = GameState(
            schema_version=3,
            content_version=self.catalog.content_version,
            player=PlayerState.from_definition(principal.player_id, character),
        )
        _spawn_dynamic_scenario_npcs(state, definition, self.catalog)
        state.scenario_runtime = ScenarioRuntimeState.from_definition(definition)
        runtime = state.scenario_runtime
        if (
            runtime.current_decision_id is not None
            or runtime.decisions_made
            or runtime.phase_beat_index != 0
            or runtime.ending_status is not EndingStatus.ACTIVE
            or runtime.ending_id is not None
        ):
            raise InvalidScenarioDefinitionError(definition.scenario_id)
        try:
            state.validate_against(self.catalog)
            runtime.validate_against(definition)
        except (DomainRuleViolation, TypeError, ValueError):
            raise InvalidScenarioDefinitionError(definition.scenario_id) from None
        event = DomainEvent(
            event_id=event_id,
            session_id=session_id,
            turn_id="session-created",
            sequence_no=1,
            event_type="ScenarioStarted",
            payload={
                "scenario_id": definition.scenario_id,
                "scenario_content_version": definition.content_version,
            },
            occurred_at=created_at,
        )
        return PreparedRunEntryInitialization(
            session=session,
            definition=definition,
            character_definition_id=character_definition_id,
            creation_request_id=creation_request_id,
            initial_state=state,
            initial_frame=None,
            initialization_event=event,
            created_at=created_at,
        )

    async def _load_dynamic_authority(
        self, uow: Any, session_id: str, *, player_id: str | None = None
    ) -> _DynamicAuthority:
        persisted = (
            await uow.sessions.get_owned(session_id, player_id)
            if player_id is not None
            else None
        )
        if player_id is None:
            session = await uow.sessions.get(session_id)
            if session is not None:
                # The application route has already performed the ownership check.
                persisted = await uow.sessions.get_owned(session_id, session.player_id)
        if persisted is None:
            raise SessionNotFoundError(session_id)
        snapshot = await uow.sessions.get_latest_snapshot(session_id)
        if snapshot is None:
            raise SnapshotNotFoundError(session_id)
        if snapshot.state_version != persisted.session.state_version:
            raise SnapshotStateVersionMismatchError(session_id)
        state = self._load_state(persisted, snapshot.state_version, snapshot.state)
        runtime = state.scenario_runtime
        if runtime is None or state.player.player_id != persisted.session.player_id:
            raise SnapshotSessionMismatchError(session_id)
        definition = self._scenario_definition(runtime.scenario_id)
        if definition is None or runtime.scenario_content_version != definition.content_version:
            raise SnapshotInvalidError(session_id)
        participation = await uow.run_participations.get(session_id)
        if participation is None:
            raise SnapshotInvalidError(session_id)
        run = await uow.runs.get(participation.run_id)
        if run is None:
            raise SnapshotInvalidError(session_id)
        try:
            run = validate_canonical_run(run)
        except (TypeError, ValueError):
            raise SnapshotInvalidError(session_id) from None
        binding = run.player_character_binding
        if (
            run.lifecycle_status is not RunLifecycleStatus.ACTIVE
            or participation not in run.trusted_participation_references
            or participation.run_id != run.run_id
            or participation.continuous_story_line_id != run.continuous_story_line_id
            or binding is None
            or binding.binding_state != "active"
        ):
            raise SnapshotInvalidError(session_id)
        character = await uow.player_characters.get(
            binding.applicable_character_reference.player_character_id
        )
        if (
            character is None
            or character.lifecycle is not PlayerCharacterLifecycle.ACTIVE
            or character.player_character_id
            != binding.applicable_character_reference.player_character_id
            or character.contract_version
            != binding.applicable_character_reference.contract_version
            or character.record_revision
            != binding.applicable_character_reference.record_revision
        ):
            raise SnapshotInvalidError(session_id)
        return _DynamicAuthority(
            persisted=persisted,
            state=state,
            definition=definition,
            participation=participation,
            run=run,
            player_character=character,
        )

    async def get_view(
        self, principal: RequestPrincipal, session_id: str
    ) -> PlayerSessionView:
        async with self.uow_factory() as uow:
            authority = await self._load_dynamic_authority(
                uow, session_id, player_id=principal.player_id
            )
            recent = await uow.narrative_jobs.recent_committed_texts(session_id, limit=6)
            try:
                return self._build_dynamic_view(authority, recent=recent)
            except SnapshotInvalidError:
                raise
            except (KeyError, TypeError, ValueError):
                raise SnapshotInvalidError(session_id) from None

    def _build_dynamic_view(
        self,
        authority: _DynamicAuthority,
        *,
        recent: tuple[str, ...],
        state_override: GameState | None = None,
        state_version_override: int | None = None,
    ) -> PlayerSessionView:
        state = state_override or authority.state
        definition = authority.definition
        runtime = state.scenario_runtime
        public = definition.public_client
        if (
            runtime is None
            or public is None
            or runtime.ending_status is not EndingStatus.ACTIVE
            or runtime.ending_id is not None
            or runtime.current_decision_id is not None
        ):
            raise SnapshotInvalidError(authority.persisted.session.session_id)
        version = (
            authority.persisted.session.state_version
            if state_version_override is None
            else state_version_override
        )
        projected = self._project(authority.persisted, state)
        if state_version_override is not None:
            projected = projected.model_copy(update={"state_version": version})
        must, may = _project_dynamic_facts(state, definition)
        location = next(
            (item for item in definition.locations if item.location_id == runtime.current_location_id),
            None,
        )
        if location is None:
            raise SnapshotInvalidError(authority.persisted.session.session_id)
        visible_definition_ids = set(location.visible_entity_ids)
        visible_pairs = tuple(
            (npc.definition_id, npc_id)
            for npc_id, npc in state.npcs.items()
            if npc.definition_id in visible_definition_ids
        )
        visible_pairs = tuple(sorted(visible_pairs))
        visible_entities = tuple(item[1] for item in visible_pairs)
        npc_records = {item.npc_id: item for item in projected.visible_npcs}
        if set(visible_entities) != set(npc_records):
            raise SnapshotInvalidError(authority.persisted.session.session_id)
        public_npc_labels = tuple(
            sorted(
                (_normalize_public_text(npc_records[npc_id].display_name, maximum=120)
                 for npc_id in visible_entities),
                key=lambda value: (value.casefold(), value),
            )
        )
        scene_title = runtime.dynamic_facts.get(DYNAMIC_SCENE_TITLE)
        scene_summary = runtime.dynamic_facts.get(DYNAMIC_SCENE_SUMMARY)
        if (scene_title is None) != (scene_summary is None):
            raise SnapshotInvalidError(authority.persisted.session.session_id)
        if scene_title is None:
            scene_title = _normalize_public_text(public.title, maximum=120)
            scene_summary = _normalize_public_text(public.hook, maximum=300)
        else:
            scene_title = _normalize_public_text(scene_title, maximum=120)
            scene_summary = _normalize_public_text(scene_summary, maximum=300)
        presentation = PublicScenarioPresentation(
            title=_normalize_public_text(public.title, maximum=120),
            scene_title=scene_title,
            scene_summary=scene_summary,
            ending=None,
        )
        suggestions = _committed_suggestion_texts(
            runtime.dynamic_facts, visible_pairs=visible_pairs, npc_records=npc_records
        )
        free_label = _dynamic_custom_label(definition)
        clocks = tuple(
            VisibleClock(
                clock_id=clock.clock_id,
                value=runtime.threat_clocks[clock.clock_id].value,
                maximum=clock.maximum,
            )
            for clock in definition.threat_clocks
            if clock.player_visible
        )
        npc_knowledge = _npc_knowledge(
            definition, visible_pairs=visible_pairs, renderable=(*must, *may)
        )
        pending = NarrativeFrame(
            frame_id="frame.dynamic.pending",
            scenario_id=definition.scenario_id,
            phase_id=runtime.current_phase_id,
            mode=FrameMode.FLOW,
            current_location_id=runtime.current_location_id,
            must_render_facts=must,
            may_render_facts=may,
            visible_entities=visible_entities,
            visible_clues=tuple(
                sorted(set(runtime.discovered_clue_ids) & set(definition.phase(runtime.current_phase_id).allowed_clue_ids))
            ),
            must_render_event_types=(),
            recent_verified_events=(),
            npc_knowledge=npc_knowledge,
            tone_hints=(),
            target_length=definition.narrative_length.target,
            min_length=definition.narrative_length.minimum,
            max_length=definition.narrative_length.maximum,
            decision_required=False,
            decision_id=None,
            decision_reason=None,
            suggested_actions=(),
            allowed_custom_action_constraints=None,
            stop_condition="AWAIT_PLAYER",
            player_visible_clocks=clocks,
        )
        presentation_digest = _presentation_digest(
            presentation=presentation,
            free_label=free_label,
            public_npc_labels=public_npc_labels,
            must=must,
            may=may,
            suggestions=suggestions,
        )
        frame_payload = pending.model_dump(mode="json")
        frame_payload.pop("frame_id")
        outer = {
            "schema_version": "dynamic-frame-v1",
            "session_id": authority.persisted.session.session_id,
            "run_id": authority.run.run_id.value,
            "continuous_story_line_id": authority.run.continuous_story_line_id.value,
            "player_character": {
                "player_character_id": authority.player_character.player_character_id.value,
                "contract_version": authority.player_character.contract_version.value,
                "revision": authority.player_character.record_revision.value,
                "lifecycle": authority.player_character.lifecycle.value,
            },
            "scenario": {
                "scenario_id": definition.scenario_id,
                "content_version": definition.content_version,
            },
            "snapshot_state_version": version,
            "story_state_version": version,
            "view_version": version,
            "presentation_digest": presentation_digest,
            "frame": frame_payload,
        }
        frame = pending.model_copy(
            update={"frame_id": "frame.dynamic." + _digest(outer)}
        )
        public_suggestions = _build_public_suggestions(
            authority=authority,
            frame=frame,
            presentation_digest=presentation_digest,
            version=version,
            suggestions=suggestions,
        )
        targets = tuple(
            PublicActionTarget(target_id=npc_id, display_name=npc_records[npc_id].display_name)
            for npc_id in visible_entities
        )
        affordances = PublicActionAffordanceSet(
            mode=PublicActionMode.FREE_ACTIONS,
            actions=(
                PublicActionAffordance(
                    action_type=ActionType.CUSTOM,
                    label=free_label,
                    input_kind=ActionInputKind.DESCRIPTION,
                    max_input_length=150,
                    target_required=False,
                    targets=(),
                ),
            ),
            suggested_actions=public_suggestions,
        )
        metadata = self._metadata(authority.persisted)
        if state_version_override is not None:
            metadata = metadata.model_copy(update={"state_version": version})
        return PlayerSessionView(
            metadata=metadata,
            narrative_frame=frame,
            player_state=projected,
            player_memory=projected.player_memory,
            presentation=presentation,
            action_affordances=affordances,
            scenario_status="ACTIVE",
            ending_status=None,
            public_clocks=clocks,
            recent_narrative_texts=self._bounded_recent_texts(recent),
            ending_id=None,
        )


def _dynamic_custom_label(definition: ScenarioDefinition) -> str:
    public = definition.public_client
    if public is None:
        raise InvalidScenarioDefinitionError(definition.scenario_id)
    indexed = sorted(
        enumerate(public.actions), key=lambda pair: (pair[1].action_type.value, pair[0])
    )
    matches = tuple(item for _, item in indexed if item.action_type is ActionType.CUSTOM)
    if len(matches) != 1:
        raise InvalidScenarioDefinitionError(definition.scenario_id)
    try:
        label = _normalize_public_text(matches[0].label, maximum=80)
    except ValueError:
        raise InvalidScenarioDefinitionError(definition.scenario_id) from None
    if not meets_zh_cn_action_text_minimum(label):
        raise InvalidScenarioDefinitionError(definition.scenario_id)
    return label


def _committed_suggestion_texts(
    dynamic_facts: Mapping[str, Any],
    *,
    visible_pairs: tuple[tuple[str, str], ...],
    npc_records: Mapping[str, Any],
) -> tuple[str, str, str]:
    present = tuple(dynamic_facts.get(key) for key in DYNAMIC_SUGGESTION_SLOTS)
    if all(item is None for item in present):
        middle = INITIAL_SUGGESTION_1_NONE
        if visible_pairs:
            selected_id = visible_pairs[0][1]
            name = _normalize_public_text(
                npc_records[selected_id].display_name, maximum=120
            )
            middle = _normalize_public_text(f"与{name}交谈。", maximum=150)
            if not meets_zh_cn_action_text_minimum(middle):
                raise ValueError(
                    "initial dynamic suggestion must meet the zh-CN text minimum"
                )
        return (INITIAL_SUGGESTION_0, middle, INITIAL_SUGGESTION_2)
    if any(item is None for item in present):
        raise ValueError("committed dynamic suggestions are incomplete")
    normalized = tuple(_normalize_public_text(item, maximum=150) for item in present)
    if len(normalized) != len(set(normalized)):
        raise ValueError("committed dynamic suggestions repeat")
    if any(not meets_zh_cn_action_text_minimum(item) for item in normalized):
        raise ValueError("committed dynamic suggestions must meet the zh-CN text minimum")
    return normalized  # type: ignore[return-value]


def _fact_value(state: GameState, definition: ScenarioDefinition, fact_id: str) -> Any:
    fact = definition.fact(fact_id)
    runtime = state.scenario_runtime
    assert runtime is not None
    if fact.kind is FactKind.FIXED:
        return fact.value
    if fact.kind is FactKind.DEFERRED:
        return runtime.bound_deferred_facts.get(fact_id)
    if fact.kind is FactKind.MUTABLE:
        if fact_id not in runtime.mutable_fact_values:
            raise ValueError("mutable fact is absent")
        return runtime.mutable_fact_values[fact_id]
    raise ValueError("unsupported declared fact kind")


def _project_dynamic_facts(
    state: GameState, definition: ScenarioDefinition
) -> tuple[tuple[RenderableFact, ...], tuple[RenderableFact, ...]]:
    runtime = state.scenario_runtime
    if runtime is None or set(runtime.dynamic_facts) - DYNAMIC_ALL_SLOTS:
        raise ValueError("dynamic runtime contains an unknown slot")
    if runtime.dynamic_facts:
        required_non_fact_slots = {
            DYNAMIC_SCENE_TITLE,
            DYNAMIC_SCENE_SUMMARY,
            *DYNAMIC_SUGGESTION_SLOTS,
            DYNAMIC_RESULT,
            DYNAMIC_CONSEQUENCES,
            DYNAMIC_CONTINUATION,
        }
        if not required_non_fact_slots.issubset(runtime.dynamic_facts):
            raise ValueError("committed dynamic slot set is incomplete")
        if runtime.dynamic_facts[DYNAMIC_RESULT] not in {
            "SUCCESS",
            "AMBIGUOUS",
            "FAILURE",
            "NO_EFFECT",
        }:
            raise ValueError("committed dynamic result is invalid")
        if runtime.dynamic_facts[DYNAMIC_CONTINUATION] not in {
            "CONTINUE",
            "TERMINAL",
        }:
            raise ValueError("committed dynamic continuation is invalid")
        consequences = runtime.dynamic_facts[DYNAMIC_CONSEQUENCES]
        if (
            not isinstance(consequences, (tuple, list))
            or len(consequences) > 3
            or any(
                not isinstance(item, str)
                or not 1 <= len(_normalize_public_text(item, maximum=120)) <= 120
                for item in consequences
            )
        ):
            raise ValueError("committed dynamic consequences are invalid")
        if any(
            len(canonical_json(runtime.dynamic_facts[key])) > 500
            for key in required_non_fact_slots
        ):
            raise ValueError("committed dynamic slot exceeds its storage boundary")
    phase = definition.phase(runtime.current_phase_id)
    known = {
        fact.fact_id
        for fact in definition.facts
        if fact.visibility is FactVisibility.PLAYER_KNOWN
    }
    for clue in definition.clues:
        if clue.clue_id in runtime.discovered_clue_ids:
            known.update(clue.supports_fact_ids)
    if len(phase.must_render_fact_ids) != len(set(phase.must_render_fact_ids)):
        raise ValueError("phase repeats a must-render fact")
    must: list[RenderableFact] = []
    for fact_id in phase.must_render_fact_ids:
        if fact_id not in known:
            raise ValueError("must-render fact is not player-known")
        value = _fact_value(state, definition, fact_id)
        if value is None:
            raise ValueError("must-render fact is unresolved")
        must.append(RenderableFact(fact_id=fact_id, value=value))
    may: list[RenderableFact] = []
    for fact_id in sorted(known - set(phase.must_render_fact_ids)):
        value = _fact_value(state, definition, fact_id)
        if value is not None:
            may.append(RenderableFact(fact_id=fact_id, value=value))
    seen = {_normalized_fact_semantic_key(item.fact_id) for item in (*must, *may)}
    for slot in DYNAMIC_FACT_SLOTS:
        if slot not in runtime.dynamic_facts:
            continue
        value = runtime.dynamic_facts[slot]
        if not isinstance(value, Mapping) or set(value) != {"key", "value"}:
            raise ValueError("committed dynamic fact is malformed")
        key = _normalize_public_text(value["key"], maximum=80)
        statement = _normalize_public_text(value["value"], maximum=300)
        semantic_key = _normalized_fact_semantic_key(key)
        if semantic_key in seen:
            raise ValueError("committed dynamic fact identity is invalid")
        seen.add(semantic_key)
        may.append(RenderableFact(fact_id=key, value=statement))
    return tuple(must), tuple(may)


def _npc_knowledge(
    definition: ScenarioDefinition,
    *,
    visible_pairs: tuple[tuple[str, str], ...],
    renderable: tuple[RenderableFact, ...],
) -> tuple[NpcKnowledgeFrame, ...]:
    by_id = {item.fact_id: item for item in renderable}
    references = {item.npc_definition_id: item for item in definition.npc_references}
    return tuple(
        NpcKnowledgeFrame(
            npc_id=npc_id,
            npc_definition_id=definition_id,
            known_facts=tuple(
                by_id[fact_id]
                for fact_id in sorted(references[definition_id].known_fact_ids)
                if fact_id in by_id
            ),
        )
        for definition_id, npc_id in visible_pairs
    )


def _presentation_digest(
    *,
    presentation: PublicScenarioPresentation,
    free_label: str,
    public_npc_labels: tuple[str, ...],
    must: tuple[RenderableFact, ...],
    may: tuple[RenderableFact, ...],
    suggestions: tuple[str, str, str],
) -> str:
    return _digest(
        {
            "schema_version": "dynamic-presentation-v1",
            "free_custom": {
                "action_type": "CUSTOM",
                "input_kind": "DESCRIPTION",
                "label": free_label,
                "max_input_length": 150,
                "target_policy": "NONE",
            },
            "must_render_facts": [item.model_dump(mode="json") for item in must],
            "may_render_facts": [item.model_dump(mode="json") for item in may],
            "presentation": presentation.model_dump(mode="json"),
            "public_npc_labels": list(public_npc_labels),
            "suggestion_texts": list(suggestions),
        }
    )


def _build_public_suggestions(
    *,
    authority: _DynamicAuthority,
    frame: NarrativeFrame,
    presentation_digest: str,
    version: int,
    suggestions: tuple[str, str, str],
) -> tuple[PublicSuggestedAction, ...]:
    result: list[PublicSuggestedAction] = []
    for ordinal, text in enumerate(suggestions):
        binding = {
            "schema_version": "dynamic-suggestion-v1",
            "session_id": authority.persisted.session.session_id,
            "run_id": authority.run.run_id.value,
            "continuous_story_line_id": authority.run.continuous_story_line_id.value,
            "player_character_id": authority.player_character.player_character_id.value,
            "player_character_revision": authority.player_character.record_revision.value,
            "scenario_id": authority.definition.scenario_id,
            "content_version": authority.definition.content_version,
            "state_version": version,
            "view_version": version,
            "frame_id": frame.frame_id,
            "presentation_digest": presentation_digest,
            "ordinal": ordinal,
            "action_type": "CUSTOM",
            "text": text,
        }
        digest = _digest(binding)
        turn_id = "dst." + hashlib.sha256(
            ("dynamic-suggestion-turn-v1:" + digest).encode("utf-8")
        ).hexdigest()[:60]
        request_id = "dsr." + hashlib.sha256(
            ("dynamic-suggestion-request-v1:" + digest).encode("utf-8")
        ).hexdigest()[:60]
        result.append(
            PublicSuggestedAction(
                suggestion_id="sug." + digest,
                ordinal=ordinal,
                label=text,
                description=text,
                submission=PublicSuggestedActionSubmission(
                    turn_id=turn_id,
                    client_request_id=request_id,
                    action_type=ActionType.CUSTOM,
                    description=text,
                ),
            )
        )
    return tuple(result)


class DynamicAttemptClassification(StrEnum):
    RETURNED_SUGGESTION = "RETURNED_SUGGESTION"
    FREE_CUSTOM = "FREE_CUSTOM"


class AttemptLifecycle(StrEnum):
    OWNER_RESERVED = "OWNER_RESERVED"
    JOB_PUBLISHED = "JOB_PUBLISHED"
    TERMINAL_AUTHORITATIVE = "TERMINAL_AUTHORITATIVE"
    TERMINAL_NO_JOB = "TERMINAL_NO_JOB"
    TERMINAL_UNCERTAIN = "TERMINAL_UNCERTAIN"


class _FinalizePublicationClass(StrEnum):
    COMPLETE_NEW = "COMPLETE_NEW"
    COMPLETE_OLD = "COMPLETE_OLD"
    PARTIAL = "PARTIAL"
    IMPOSSIBLE = "IMPOSSIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class _FinalizeExpectation:
    old_snapshot: dict[str, Any]
    successor_snapshot: dict[str, Any]
    old_view: PlayerSessionView
    successor_view: PlayerSessionView
    successor_response: TurnResponse
    old_recent: tuple[str, ...]
    successor_recent: tuple[str, ...]
    successor_event_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _FinalizeReconciliation:
    classification: _FinalizePublicationClass
    response: TurnResponse | None = None
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SanitizedAttemptCompletion:
    state: AttemptLifecycle
    error_code: str | None = None


@dataclass(slots=True)
class _AttemptEntry:
    identity: dict[str, Any]
    submission: ActionSubmission
    fingerprint: str
    owner_token: object
    lifecycle: AttemptLifecycle
    completion: asyncio.Future[SanitizedAttemptCompletion]
    locator: tuple[str, str] | None = None


@dataclass(slots=True)
class _SessionAttemptBucket:
    binding: tuple[Any, ...]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    entries: dict[str, _AttemptEntry] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _ResolvedAttempt:
    authority: _DynamicAuthority
    view: PlayerSessionView
    classification: DynamicAttemptClassification
    suggestion_id: str | None
    ordinal: int | None
    identity: dict[str, Any]


class DynamicActionPolicy:
    """The spike's independent CUSTOM-only admission policy."""

    @staticmethod
    def validate(submission: ActionSubmission) -> str:
        if (
            submission.action_type is not ActionType.CUSTOM
            or submission.target_ids
            or submission.tool_ids
            or submission.dialogue is not None
            or submission.decision_id is not None
            or submission.choice_id is not None
            or submission.item_instance_id is not None
            or submission.equipment_slot_id is not None
            or submission.skill_definition_id is not None
            or submission.description is None
        ):
            raise NarrativeRequestRejectedError()
        description = submission.description
        if not 1 <= len(description) <= 150:
            raise NarrativeRequestRejectedError()
        return description


class DynamicNarrativeRejectionDiagnostic(StrEnum):
    """Closed, sanitized local-only proposal-rejection classifications."""

    PRE_REVALIDATION = "DNVS_LIVE_DIAG_PRE_REVALIDATION"
    PRE_RESPONSE_UNPARSEABLE = "DNVS_LIVE_DIAG_PRE_RESPONSE_UNPARSEABLE"
    PRE_RESPONSE_SCHEMA_INVALID = "DNVS_LIVE_DIAG_PRE_RESPONSE_SCHEMA_INVALID"
    TERMINAL_RESPONSE_TRUNCATED = "DNVS_LIVE_DIAG_TERMINAL_RESPONSE_TRUNCATED"
    RECOVERY_SCHEMA_ROOT_OR_OBJECT_SHAPE = (
        "DNVS_LIVE_DIAG_RECOVERY_SCHEMA_ROOT_OR_OBJECT_SHAPE"
    )
    RECOVERY_SCHEMA_REQUIRED_OR_EXTRA_FIELDS = (
        "DNVS_LIVE_DIAG_RECOVERY_SCHEMA_REQUIRED_OR_EXTRA_FIELDS"
    )
    RECOVERY_SCHEMA_TYPE_OR_LITERAL = (
        "DNVS_LIVE_DIAG_RECOVERY_SCHEMA_TYPE_OR_LITERAL"
    )
    RECOVERY_SCHEMA_BOUNDS_OR_UNIQUENESS = (
        "DNVS_LIVE_DIAG_RECOVERY_SCHEMA_BOUNDS_OR_UNIQUENESS"
    )
    FINAL_SCHEMA_ROOT_OR_OBJECT_SHAPE = (
        "DNVS_LIVE_DIAG_FINAL_SCHEMA_ROOT_OR_OBJECT_SHAPE"
    )
    FINAL_SCHEMA_REQUIRED_OR_EXTRA_FIELDS = (
        "DNVS_LIVE_DIAG_FINAL_SCHEMA_REQUIRED_OR_EXTRA_FIELDS"
    )
    FINAL_SCHEMA_TYPE_OR_LITERAL = "DNVS_LIVE_DIAG_FINAL_SCHEMA_TYPE_OR_LITERAL"
    FINAL_SCHEMA_BOUNDS_OR_UNIQUENESS = (
        "DNVS_LIVE_DIAG_FINAL_SCHEMA_BOUNDS_OR_UNIQUENESS"
    )
    PRE_LENGTH = "DNVS_LIVE_DIAG_PRE_LENGTH"
    PRE_LENGTH_BELOW_MINIMUM = "DNVS_LIVE_DIAG_PRE_LENGTH_BELOW_MINIMUM"
    PRE_LENGTH_ABOVE_MAXIMUM = "DNVS_LIVE_DIAG_PRE_LENGTH_ABOVE_MAXIMUM"
    PRE_REPEAT_SUBMITTED_ACTION = "DNVS_LIVE_DIAG_PRE_REPEAT_SUBMITTED_ACTION"
    PRE_STORAGE_BOUNDARY = "DNVS_LIVE_DIAG_PRE_STORAGE_BOUNDARY"
    PRE_REFERENCE_INDEX = "DNVS_LIVE_DIAG_PRE_REFERENCE_INDEX"
    PRE_INTERNAL_MARKER = "DNVS_LIVE_DIAG_PRE_INTERNAL_MARKER"
    PRE_PROTECTED_REFERENCE = "DNVS_LIVE_DIAG_PRE_PROTECTED_REFERENCE"
    FINAL_FACT_RING = "DNVS_LIVE_DIAG_FINAL_FACT_RING"
    FINAL_SLOT_BOUNDARY = "DNVS_LIVE_DIAG_FINAL_SLOT_BOUNDARY"
    FINAL_MUTATION = "DNVS_LIVE_DIAG_FINAL_MUTATION"
    FINAL_STATE = "DNVS_LIVE_DIAG_FINAL_STATE"
    FINAL_VALUE = "DNVS_LIVE_DIAG_FINAL_VALUE"
    FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION = (
        "DNVS_LIVE_DIAG_FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION"
    )


_SCHEMA_RECOVERY_INSTRUCTION = {
    DynamicNarrativeSchemaFailureFamily.ROOT_OR_OBJECT_SHAPE: (
        DynamicGenerationInstruction.REPLACE_SCHEMA_ROOT_OR_OBJECT_SHAPE
    ),
    DynamicNarrativeSchemaFailureFamily.REQUIRED_OR_EXTRA_FIELDS: (
        DynamicGenerationInstruction.REPLACE_SCHEMA_REQUIRED_OR_EXTRA_FIELDS
    ),
    DynamicNarrativeSchemaFailureFamily.TYPE_OR_LITERAL: (
        DynamicGenerationInstruction.REPLACE_SCHEMA_TYPE_OR_LITERAL
    ),
    DynamicNarrativeSchemaFailureFamily.BOUNDS_OR_UNIQUENESS: (
        DynamicGenerationInstruction.REPLACE_SCHEMA_BOUNDS_OR_UNIQUENESS
    ),
}

_SCHEMA_RECOVERY_DIAGNOSTIC = {
    DynamicNarrativeSchemaFailureFamily.ROOT_OR_OBJECT_SHAPE: (
        DynamicNarrativeRejectionDiagnostic.RECOVERY_SCHEMA_ROOT_OR_OBJECT_SHAPE
    ),
    DynamicNarrativeSchemaFailureFamily.REQUIRED_OR_EXTRA_FIELDS: (
        DynamicNarrativeRejectionDiagnostic.RECOVERY_SCHEMA_REQUIRED_OR_EXTRA_FIELDS
    ),
    DynamicNarrativeSchemaFailureFamily.TYPE_OR_LITERAL: (
        DynamicNarrativeRejectionDiagnostic.RECOVERY_SCHEMA_TYPE_OR_LITERAL
    ),
    DynamicNarrativeSchemaFailureFamily.BOUNDS_OR_UNIQUENESS: (
        DynamicNarrativeRejectionDiagnostic.RECOVERY_SCHEMA_BOUNDS_OR_UNIQUENESS
    ),
}

_SCHEMA_FINAL_DIAGNOSTIC = {
    DynamicNarrativeSchemaFailureFamily.ROOT_OR_OBJECT_SHAPE: (
        DynamicNarrativeRejectionDiagnostic.FINAL_SCHEMA_ROOT_OR_OBJECT_SHAPE
    ),
    DynamicNarrativeSchemaFailureFamily.REQUIRED_OR_EXTRA_FIELDS: (
        DynamicNarrativeRejectionDiagnostic.FINAL_SCHEMA_REQUIRED_OR_EXTRA_FIELDS
    ),
    DynamicNarrativeSchemaFailureFamily.TYPE_OR_LITERAL: (
        DynamicNarrativeRejectionDiagnostic.FINAL_SCHEMA_TYPE_OR_LITERAL
    ),
    DynamicNarrativeSchemaFailureFamily.BOUNDS_OR_UNIQUENESS: (
        DynamicNarrativeRejectionDiagnostic.FINAL_SCHEMA_BOUNDS_OR_UNIQUENESS
    ),
}


def _noop_rejection_diagnostic(_token: DynamicNarrativeRejectionDiagnostic) -> None:
    return None


class _FinalizationDiagnosticError(NarrativeProposalRejectedError):
    def __init__(self, token: DynamicNarrativeRejectionDiagnostic) -> None:
        super().__init__()
        self.token = token


class _RecoverableGenerationError(NarrativeProposalRejectedError):
    """Internal-only replacement signal; it contains no candidate data."""

    def __init__(self, instruction: DynamicGenerationInstruction) -> None:
        super().__init__()
        self.instruction = instruction


@dataclass(slots=True)
class DynamicNarrativeOrchestrator(FirstPhaseTurnOrchestrator):
    """One-owner dynamic prepare/call/finalize coordinator with a 512 ledger."""

    provider: DynamicNarrativeProvider | None = None
    dynamic_session_service: DynamicSessionService | None = None
    provider_name: str = "dynamic-fake"
    model_name: str = "dynamic-fake-v1"
    live_provider_references: tuple[str, ...] = ()
    publication_event_reader: Callable[[str, int], tuple[DomainEvent, ...]] | None = None
    job_id_generator: Any = lambda: str(uuid4())
    lease_token_generator: Any = lambda: uuid4().hex
    worker_id_generator: Any = lambda: str(uuid4())
    lease_duration: timedelta = timedelta(minutes=2)
    action_policy: DynamicActionPolicy = field(default_factory=DynamicActionPolicy)
    diagnostic_reporter: Callable[[DynamicNarrativeRejectionDiagnostic], None] = (
        _noop_rejection_diagnostic
    )
    _buckets: dict[str, _SessionAttemptBucket] = field(default_factory=dict, init=False)
    _bucket_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        FirstPhaseTurnOrchestrator.__post_init__(self)
        if (
            self.provider is None
            or self.dynamic_session_service is None
            or self.publication_event_reader is None
        ):
            raise ValueError("dynamic orchestration requires its provider and Session service")
        if self.lease_duration <= timedelta(0) or self.lease_duration > timedelta(minutes=10):
            raise ValueError("dynamic narrative lease duration is outside the safe bound")

    def _report_rejection(
        self, token: DynamicNarrativeRejectionDiagnostic
    ) -> None:
        """Best-effort local diagnostic seam; reporting is never authoritative."""

        try:
            self.diagnostic_reporter(token)
        except BaseException:
            pass

    @staticmethod
    def _replay_response(
        stored: PersistedTurnRequest,
        submission: ActionSubmission,
        job: NarrativeJob | None = None,
    ) -> TurnResponse:
        inherited_response_invalid = False
        try:
            response = FirstPhaseTurnOrchestrator._replay_response(stored, submission)
        except StoredTurnResponseInvalidError:
            inherited_response_invalid = True
        if inherited_response_invalid:
            raise StoredTurnResponseInvalidError(submission.session_id)
        invalid = False
        try:
            validate_committed_turn_response_for_recovery(
                response,
                job,
                stored_turn_id=stored.turn_id,
            )
        except CommittedTurnResponseValidationError:
            invalid = True
        if invalid:
            raise StoredTurnResponseInvalidError(submission.session_id)
        return response

    async def handle(self, submission: ActionSubmission) -> TurnResponse:
        existing = await self._existing_reservation(submission)
        if existing is not None:
            return await self._follow(existing)
        resolved_or_response = await self._resolve_attempt(submission)
        if isinstance(resolved_or_response, TurnResponse):
            return resolved_or_response
        resolved = resolved_or_response
        role, entry = await self._reserve(resolved, submission)
        if role == "FOLLOWER":
            return await self._follow(entry)
        token = entry.owner_token
        owner_task = asyncio.current_task()
        if owner_task is None:
            raise RuntimeError("dynamic attempt requires an owner task")
        cancellation_baseline = owner_task.cancelling()
        try:
            response = await self._owner(entry, token, resolved, submission)
        except asyncio.CancelledError:
            if entry.lifecycle in {
                AttemptLifecycle.TERMINAL_AUTHORITATIVE,
                AttemptLifecycle.TERMINAL_NO_JOB,
                AttemptLifecycle.TERMINAL_UNCERTAIN,
            }:
                raise
            marker = asyncio.create_task(
                self._stabilize_cancelled_owner(entry, token)
            )
            await self._await_retained(
                marker, owner_task, cancellation_baseline, True
            )
            raise
        except BaseException:
            if entry.lifecycle is AttemptLifecycle.OWNER_RESERVED:
                marker = asyncio.create_task(
                    self._terminal(
                        entry,
                        token,
                        AttemptLifecycle.TERMINAL_NO_JOB,
                        error_code="NARRATIVE_REQUEST_REJECTED",
                    )
                )
            elif entry.lifecycle is AttemptLifecycle.JOB_PUBLISHED:
                marker = asyncio.create_task(self._reconcile_terminal(entry, token))
            else:
                marker = None
            if marker is not None:
                _, cancelled = await self._await_retained(
                    marker, owner_task, cancellation_baseline, False
                )
                if cancelled:
                    raise asyncio.CancelledError
            raise
        if entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE:
            if not entry.completion.done() or entry.completion.cancelled():
                raise RuntimeError("dynamic terminal completion is not stable")
            return response
        marker = asyncio.create_task(
            self._terminal(entry, token, AttemptLifecycle.TERMINAL_AUTHORITATIVE)
        )
        _, cancelled = await self._await_retained(
            marker, owner_task, cancellation_baseline, False
        )
        if cancelled:
            raise asyncio.CancelledError
        return response

    async def request_is_terminal_uncertain(
        self, session_id: str, client_request_id: str
    ) -> bool:
        """Return the stable sanitized ledger classification for public polling."""

        async with self._bucket_lock:
            bucket = self._buckets.get(session_id)
        if bucket is None:
            return False
        async with bucket.lock:
            entry = bucket.entries.get(client_request_id)
            return (
                entry is not None
                and entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
                and entry.completion.done()
                and not entry.completion.cancelled()
            )

    async def _existing_reservation(
        self, submission: ActionSubmission
    ) -> _AttemptEntry | None:
        """Join the one process-local owner before consulting its pending job."""

        async with self._bucket_lock:
            bucket = self._buckets.get(submission.session_id)
        if bucket is None:
            return None
        async with bucket.lock:
            entry = bucket.entries.get(submission.client_request_id)
            if entry is None:
                return None
            if (
                entry.fingerprint != _submission_fingerprint(submission)
                or entry.submission != submission
            ):
                raise IdempotencyConflictError(submission.session_id)
            return entry

    async def _resolve_attempt(
        self, submission: ActionSubmission
    ) -> _ResolvedAttempt | TurnResponse:
        assert self.dynamic_session_service is not None
        known_job: NarrativeJob | None = None
        async with self.uow_factory() as uow:
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise SessionNotFoundError(submission.session_id)
            stored = await uow.turn_requests.get_by_client_request_id(
                submission.session_id, submission.client_request_id
            )
            if stored is not None:
                job = await uow.narrative_jobs.get_by_client_request_id(
                    submission.session_id,
                    submission.client_request_id,
                    for_update=True,
                )
                return self._replay_response(stored, submission, job)
            job = await uow.narrative_jobs.get_by_client_request_id(
                submission.session_id,
                submission.client_request_id,
                for_update=True,
            )
            if job is not None:
                known_job = await self._recover_known_job(uow, job, submission)
            else:
                authority = await self.dynamic_session_service._load_dynamic_authority(
                    uow, submission.session_id
                )
                recent = await uow.narrative_jobs.recent_committed_texts(
                    submission.session_id, limit=6
                )
                try:
                    view = self.dynamic_session_service._build_dynamic_view(
                        authority, recent=recent
                    )
                except SnapshotInvalidError:
                    raise
                except (KeyError, TypeError, ValueError):
                    raise SnapshotInvalidError(submission.session_id) from None
        if known_job is not None:
            return self._known_job_result(known_job)
        matched: PublicSuggestedAction | None = None
        suggestions = view.action_affordances.suggested_actions or ()
        if submission.client_request_id.startswith("dsr."):
            for suggestion in suggestions:
                canonical = ActionSubmission(
                    session_id=submission.session_id,
                    turn_id=suggestion.submission.turn_id,
                    client_request_id=suggestion.submission.client_request_id,
                    action_type=ActionType.CUSTOM,
                    description=suggestion.submission.description,
                )
                if _submission_payload(canonical) == _submission_payload(submission):
                    matched = suggestion
                    break
            if matched is None:
                if any(
                    item.submission.client_request_id == submission.client_request_id
                    for item in suggestions
                ):
                    raise IdempotencyConflictError(submission.session_id)
                raise NarrativeJobStaleError(submission.session_id)
            classification = DynamicAttemptClassification.RETURNED_SUGGESTION
            self.action_policy.validate(submission)
        else:
            if submission.client_request_id.startswith("dsr"):
                raise NarrativeJobStaleError(submission.session_id)
            classification = DynamicAttemptClassification.FREE_CUSTOM
            self.action_policy.validate(submission)
        pc = authority.player_character
        run = authority.run
        identity = {
            "schema_version": "dynamic-attempt-identity-v1",
            "session_id": submission.session_id,
            "run_id": run.run_id.value,
            "continuous_story_line_id": run.continuous_story_line_id.value,
            "scenario_id": authority.definition.scenario_id,
            "content_version": authority.definition.content_version,
            "player_character_id": pc.player_character_id.value,
            "player_character_revision": pc.record_revision.value,
            "snapshot_state_version": authority.persisted.session.state_version,
            "story_state_version": authority.persisted.session.state_version,
            "view_version": view.metadata.state_version,
            "frame_id": view.narrative_frame.frame_id,
            "presentation_digest": _view_presentation_digest(view),
            "classification": classification.value,
            "suggestion_id": matched.suggestion_id if matched else None,
            "ordinal": matched.ordinal if matched else None,
            "turn_id": submission.turn_id,
            "client_request_id": submission.client_request_id,
            "submission_fingerprint": _submission_fingerprint(submission),
        }
        return _ResolvedAttempt(
            authority=authority,
            view=view,
            classification=classification,
            suggestion_id=matched.suggestion_id if matched else None,
            ordinal=matched.ordinal if matched else None,
            identity=identity,
        )

    async def _reserve(
        self, resolved: _ResolvedAttempt, submission: ActionSubmission
    ) -> tuple[Literal["OWNER", "FOLLOWER"], _AttemptEntry]:
        binding = (
            resolved.identity["run_id"],
            resolved.identity["continuous_story_line_id"],
            resolved.identity["scenario_id"],
            resolved.identity["content_version"],
            resolved.identity["player_character_id"],
            resolved.identity["player_character_revision"],
        )
        async with self._bucket_lock:
            bucket = self._buckets.get(submission.session_id)
            if bucket is None:
                bucket = _SessionAttemptBucket(binding=binding)
                self._buckets[submission.session_id] = bucket
            elif bucket.binding != binding:
                raise NarrativeJobStaleError(submission.session_id)
        async with bucket.lock:
            existing = bucket.entries.get(submission.client_request_id)
            fingerprint = _submission_fingerprint(submission)
            if existing is not None:
                if existing.identity != resolved.identity or existing.fingerprint != fingerprint:
                    raise IdempotencyConflictError(submission.session_id)
                return "FOLLOWER", existing
            if len(bucket.entries) >= 512:
                raise DynamicNarrativeCapacityExhaustedError()
            future: asyncio.Future[SanitizedAttemptCompletion] = (
                asyncio.get_running_loop().create_future()
            )
            entry = _AttemptEntry(
                identity=copy.deepcopy(resolved.identity),
                submission=submission,
                fingerprint=fingerprint,
                owner_token=object(),
                lifecycle=AttemptLifecycle.OWNER_RESERVED,
                completion=future,
            )
            bucket.entries[submission.client_request_id] = entry
            return "OWNER", entry

    async def _owner(
        self,
        entry: _AttemptEntry,
        token: object,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
    ) -> TurnResponse:
        owner_task = asyncio.current_task()
        if owner_task is None:
            raise RuntimeError("dynamic attempt requires an owner task")
        cancellation_baseline = owner_task.cancelling()
        job = await self._publish_job(entry, token, resolved, submission)
        claimed = await self._claim(job)
        request = DynamicNarrativeRequest.model_validate(
            claimed.narrative_request["provider_request"]
        )
        # This lock-free yield is the last cancellable boundary before entering
        # the Provider.  A delivered cancellation is therefore stabilized from
        # durable job authority without executing model work.
        await self._before_provider_entry()
        try:
            untrusted = await self._generate_dynamic(
                request,
                claimed,
                owner_task,
                cancellation_baseline,
                allow_response_recovery=True,
            )
            validated = self._validate_candidate(
                untrusted,
                request=request,
                resolved=resolved,
                job=claimed,
                allow_length_recovery=True,
            )
        except _RecoverableGenerationError as recovery:
            replacement_request = request.with_generation_instruction(recovery.instruction)
            replacement = await self._generate_dynamic(
                replacement_request, claimed, owner_task, cancellation_baseline
            )
            try:
                validated = self._validate_candidate(
                    replacement,
                    request=replacement_request,
                    resolved=resolved,
                    job=claimed,
                )
            except NarrativeBoundaryError:
                await self._record_terminal_job(
                    claimed,
                    NarrativeJobStatus.FAILED_TERMINAL,
                    "NARRATIVE_PROPOSAL_REJECTED",
                )
                raise
        except NarrativeBoundaryError:
            await self._record_terminal_job(
                claimed, NarrativeJobStatus.FAILED_TERMINAL, "NARRATIVE_PROPOSAL_REJECTED"
            )
            raise
        stored = await self._store_validated(claimed, validated)
        try:
            return await self._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=token,
            )
        except asyncio.CancelledError:
            if entry.lifecycle in {
                AttemptLifecycle.TERMINAL_AUTHORITATIVE,
                AttemptLifecycle.TERMINAL_UNCERTAIN,
            }:
                raise
            marker = asyncio.create_task(
                self._reconcile_finalize_boundary(
                    stored, resolved, submission, entry=entry, token=token
                )
            )
            await self._await_retained(
                marker, owner_task, cancellation_baseline, True
            )
            raise asyncio.CancelledError
        except NarrativeJobStaleError:
            await self._record_terminal_job(
                stored, NarrativeJobStatus.STALE, "NARRATIVE_JOB_STALE"
            )
            raise
        except CandidateStateInvalidError:
            self._report_rejection(DynamicNarrativeRejectionDiagnostic.FINAL_STATE)
            await self._record_terminal_job(
                stored,
                NarrativeJobStatus.FAILED_TERMINAL,
                "NARRATIVE_PROPOSAL_REJECTED",
            )
            raise NarrativeProposalRejectedError() from None
        except _FinalizationDiagnosticError as exc:
            self._report_rejection(exc.token)
            await self._record_terminal_job(
                stored,
                NarrativeJobStatus.FAILED_TERMINAL,
                "NARRATIVE_PROPOSAL_REJECTED",
            )
            raise NarrativeProposalRejectedError() from None
        except (NarrativeProposalRejectedError, ValueError):
            self._report_rejection(DynamicNarrativeRejectionDiagnostic.FINAL_VALUE)
            await self._record_terminal_job(
                stored,
                NarrativeJobStatus.FAILED_TERMINAL,
                "NARRATIVE_PROPOSAL_REJECTED",
            )
            raise NarrativeProposalRejectedError() from None
        except NarrativeOutcomeUnknownError:
            raise
        except BaseException:
            marker = asyncio.create_task(
                self._reconcile_finalize_boundary(
                    stored, resolved, submission, entry=entry, token=token
                )
            )
            reconciled, cancelled = await self._await_retained(
                marker, owner_task, cancellation_baseline, False
            )
            if cancelled:
                raise asyncio.CancelledError
            if reconciled.response is not None:
                return reconciled.response
            raise NarrativeOutcomeUnknownError(submission.session_id) from None

    async def _generate_dynamic(
        self,
        request: DynamicNarrativeRequest,
        claimed: NarrativeJob,
        owner_task: asyncio.Task[Any],
        cancellation_baseline: int,
        *,
        allow_response_recovery: bool = False,
    ) -> UntrustedDynamicNarrativeCandidate:
        assert self.provider is not None
        try:
            return await self.provider.generate_dynamic(request)
        except asyncio.CancelledError:
            marker = asyncio.create_task(
                self._record_terminal_job(
                    claimed,
                    NarrativeJobStatus.OUTCOME_UNKNOWN,
                    "NARRATIVE_OUTCOME_UNKNOWN",
                )
            )
            await self._await_retained(
                marker, owner_task, cancellation_baseline, True
            )
            raise asyncio.CancelledError
        except DynamicNarrativeResponseError as exc:
            if allow_response_recovery:
                if (
                    exc.category
                    is DynamicNarrativeResponseCategory.SCHEMA_INVALID_RESPONSE
                ):
                    assert exc.schema_failure_family is not None
                    self._report_rejection(
                        _SCHEMA_RECOVERY_DIAGNOSTIC[exc.schema_failure_family]
                    )
                    instruction = _SCHEMA_RECOVERY_INSTRUCTION[
                        exc.schema_failure_family
                    ]
                else:
                    instruction = DynamicGenerationInstruction.REPLACE_RESPONSE_INVALID
                raise _RecoverableGenerationError(
                    instruction
                ) from None
            if (
                exc.category
                is DynamicNarrativeResponseCategory.SCHEMA_INVALID_RESPONSE
            ):
                assert exc.schema_failure_family is not None
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_RESPONSE_SCHEMA_INVALID
                )
                self._report_rejection(
                    _SCHEMA_FINAL_DIAGNOSTIC[exc.schema_failure_family]
                )
            else:
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_RESPONSE_UNPARSEABLE
                )
            await self._record_terminal_job(
                claimed, NarrativeJobStatus.FAILED_TERMINAL, exc.code
            )
            raise
        except NarrativeBoundaryError as exc:
            if isinstance(exc, NarrativeProviderTruncatedError):
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.TERMINAL_RESPONSE_TRUNCATED
                )
            uncertain = exc.code == "NARRATIVE_PROVIDER_UNAVAILABLE"
            status = (
                NarrativeJobStatus.OUTCOME_UNKNOWN
                if uncertain
                else NarrativeJobStatus.FAILED_TERMINAL
            )
            await self._record_terminal_job(claimed, status, exc.code)
            if uncertain:
                raise NarrativeOutcomeUnknownError(claimed.session_id) from None
            raise
        except Exception:
            await self._record_terminal_job(
                claimed, NarrativeJobStatus.OUTCOME_UNKNOWN, "NARRATIVE_OUTCOME_UNKNOWN"
            )
            raise NarrativeOutcomeUnknownError(claimed.session_id) from None

    async def _publish_job(
        self,
        entry: _AttemptEntry,
        token: object,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
    ) -> NarrativeJob:
        try:
            request = self._build_request(resolved, submission)
        except NarrativeBoundaryError:
            raise
        except (TypeError, ValueError):
            raise NarrativeRequestRejectedError() from None
        now = self._now()
        try:
            hidden_reference_digest = _hidden_reference_digest(
                _hidden_reference_index(
                    resolved,
                    None,
                    self.catalog,
                    live_provider_references=self.live_provider_references,
                )
            )
            public_reference_digest = _public_reference_digest(
                _public_reference_records(request, resolved, self.catalog)
            )
        except (TypeError, ValueError):
            raise NarrativeRequestRejectedError() from None
        binding = {
            **resolved.identity,
            "session_phase": resolved.authority.persisted.session.phase,
            "submission": _submission_payload(submission),
            "hidden_reference_digest": hidden_reference_digest,
            "public_reference_digest": public_reference_digest,
        }
        envelope = {
            "provider_request": request.model_dump(mode="json"),
            "authority_binding": binding,
        }
        job = NarrativeJob(
            job_id=self._generated_id(self.job_id_generator, "job"),
            session_id=submission.session_id,
            turn_id=submission.turn_id,
            client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(),
            prepared_state_version=resolved.authority.persisted.session.state_version,
            state_fingerprint=_digest(resolved.authority.state.to_snapshot()),
            scenario_id=resolved.authority.definition.scenario_id,
            scenario_content_version=resolved.authority.definition.content_version,
            request_fingerprint=_digest(envelope),
            narrative_request=envelope,
            prompt_schema_version=DYNAMIC_PROMPT_SCHEMA_VERSION,
            style_profile_version="dynamic-original-zh-v1",
            provider_name=self.provider_name,
            model_name=self.model_name,
            created_at=now,
            updated_at=now,
        )
        owner_task: asyncio.Task[Any] | None = None
        baseline: int | None = None
        publication_started = False
        marker: asyncio.Task[str] | None = None
        try:
            async with self.uow_factory() as uow:
                if not await uow.sessions.lock_for_turn(submission.session_id):
                    raise SessionNotFoundError(submission.session_id)
                if await uow.turn_requests.get_by_client_request_id(
                    submission.session_id, submission.client_request_id
                ) is not None:
                    raise IdempotencyConflictError(submission.session_id)
                if await uow.narrative_jobs.get_by_client_request_id(
                    submission.session_id, submission.client_request_id
                ) is not None:
                    raise IdempotencyConflictError(submission.session_id)
                await uow.narrative_jobs.add(job)
                owner_task = asyncio.current_task()
                if owner_task is None:
                    raise RuntimeError("protected completion requires an owner task")
                baseline = owner_task.cancelling()
                publication_started = True
                await uow.commit()
                # A normal return proves publication.  Retain the marker task
                # synchronously before the context manager performs another await.
                marker = asyncio.create_task(self._mark_published(entry, token, job))
        except BaseException as exc:
            if not publication_started or owner_task is None or baseline is None:
                raise
            was_cancelled = isinstance(exc, asyncio.CancelledError)
            if marker is None:
                marker = asyncio.create_task(
                    self._reconcile_publication(entry, token, job)
                )
            result, cancelled = await self._await_retained(
                marker, owner_task, baseline, was_cancelled or baseline > 0
            )
            if cancelled:
                if result == "PUBLISHED":
                    terminal = asyncio.create_task(
                        self._reconcile_terminal(entry, token)
                    )
                    await self._await_retained(
                        terminal, owner_task, baseline, True
                    )
                raise asyncio.CancelledError
            if result == "PUBLISHED":
                await self._record_terminal_job(
                    job,
                    NarrativeJobStatus.OUTCOME_UNKNOWN,
                    "NARRATIVE_OUTCOME_UNKNOWN",
                )
                raise NarrativeOutcomeUnknownError(job.session_id) from None
            if result == "UNCERTAIN":
                raise NarrativeOutcomeUnknownError(job.session_id) from None
            if isinstance(exc, NarrativeBoundaryError):
                raise exc
            raise NarrativeRequestRejectedError() from None
        assert owner_task is not None and baseline is not None and marker is not None
        result, cancelled = await self._await_retained(
            marker, owner_task, baseline, baseline > 0
        )
        if cancelled:
            terminal = asyncio.create_task(
                self._reconcile_terminal(entry, token)
            )
            await self._await_retained(terminal, owner_task, baseline, True)
            raise asyncio.CancelledError
        if result != "PUBLISHED":
            terminal = asyncio.create_task(
                self._terminal(
                    entry,
                    token,
                    AttemptLifecycle.TERMINAL_UNCERTAIN,
                    error_code="NARRATIVE_OUTCOME_UNKNOWN",
                )
            )
            await self._await_retained(terminal, owner_task, baseline, False)
            raise NarrativeOutcomeUnknownError(job.session_id)
        return job

    async def _mark_published(
        self, entry: _AttemptEntry, token: object, job: NarrativeJob
    ) -> str:
        bucket = self._buckets[job.session_id]
        async with bucket.lock:
            if entry.owner_token is not token or entry.lifecycle is not AttemptLifecycle.OWNER_RESERVED:
                return "UNCERTAIN"
            entry.locator = (job.session_id, job.client_request_id)
            entry.lifecycle = AttemptLifecycle.JOB_PUBLISHED
            return "PUBLISHED"

    async def _reconcile_publication(
        self, entry: _AttemptEntry, token: object, job: NarrativeJob
    ) -> str:
        result = "UNCERTAIN"
        try:
            async with self.uow_factory() as uow:
                current = await uow.narrative_jobs.get_by_client_request_id(
                    job.session_id, job.client_request_id
                )
                if current is None:
                    result = "NO_JOB"
                elif (
                    current.job_id == job.job_id
                    and current.action_signature == job.action_signature
                    and current.request_fingerprint == job.request_fingerprint
                ):
                    result = "PUBLISHED"
        except BaseException:
            result = "UNCERTAIN"
        if result == "PUBLISHED":
            await self._mark_published(entry, token, job)
        elif result == "NO_JOB":
            await self._terminal(
                entry, token, AttemptLifecycle.TERMINAL_NO_JOB,
                error_code="NARRATIVE_REQUEST_REJECTED"
            )
        else:
            await self._terminal(
                entry, token, AttemptLifecycle.TERMINAL_UNCERTAIN,
                error_code="NARRATIVE_OUTCOME_UNKNOWN"
            )
        return result

    async def _claim(self, job: NarrativeJob) -> NarrativeJob:
        async with self.uow_factory() as uow:
            current = await uow.narrative_jobs.get(job.job_id, for_update=True)
            if current is None or current.status is not NarrativeJobStatus.PREPARED:
                raise NarrativeJobStaleError(job.session_id)
            now = self._now()
            claimed = self._transition_job(
                current,
                status=NarrativeJobStatus.IN_PROGRESS,
                attempt_count=1,
                lease_token=self._generated_id(self.lease_token_generator, "lease"),
                lease_owner=self._generated_id(self.worker_id_generator, "worker"),
                lease_expires_at=now + self.lease_duration,
                updated_at=now,
            )
            if not await uow.narrative_jobs.replace(
                claimed, expected_status=NarrativeJobStatus.PREPARED
            ):
                raise NarrativeJobStaleError(job.session_id)
            await uow.commit()
            return claimed

    async def _before_provider_entry(self) -> None:
        await asyncio.sleep(0)

    def _build_request(
        self, resolved: _ResolvedAttempt, submission: ActionSubmission
    ) -> DynamicNarrativeRequest:
        view = resolved.view
        public = resolved.authority.definition.public_client
        if public is None:
            raise NarrativeRequestRejectedError()
        role = next(
            (
                item
                for item in public.playable_characters
                if item.character_definition_id
                == resolved.authority.state.player.character_definition_id
            ),
            None,
        )
        if role is None or submission.description is None:
            raise NarrativeRequestRejectedError()
        role_character = self.catalog.character(role.character_definition_id)
        if role_character is None:
            raise NarrativeRequestRejectedError()
        visible_by_id = {item.npc_id: item for item in view.player_state.visible_npcs}
        labels = tuple(
            sorted(
                (
                    _normalize_public_text(visible_by_id[npc_id].display_name, maximum=120)
                    for npc_id in view.narrative_frame.visible_entities
                ),
                key=lambda value: (value.casefold(), value),
            )
        )
        must = tuple(
            DynamicCanonicalFact(key=item.fact_id, value=item.value)
            for item in view.narrative_frame.must_render_facts
        )
        if len(must) > 12:
            raise NarrativeRequestRejectedError()
        may = tuple(
            DynamicCanonicalFact(key=item.fact_id, value=item.value)
            for item in view.narrative_frame.may_render_facts
        )
        selected_may = may[: 12 - len(must)]
        truncated = len(selected_may) != len(may)
        history = tuple(view.recent_narrative_texts[-6:])
        while True:
            try:
                return DynamicNarrativeRequest(
                    scenario_premise=DynamicScenarioPremise(
                        title=_normalize_public_text(public.title, maximum=120),
                        hook=_normalize_public_text(public.hook, maximum=300),
                    ),
                    selected_player_character=DynamicSelectedPlayerCharacter(
                        contract_version=resolved.authority.player_character.contract_version.value,
                        lifecycle="active",
                    ),
                    scenario_role=DynamicScenarioRole(
                        display_name=_normalize_public_text(role_character.display_name, maximum=120),
                        description=_normalize_public_text(role.description, maximum=300),
                    ),
                    current_scene=DynamicCurrentScene(
                        title=view.presentation.scene_title,
                        summary=view.presentation.scene_summary,
                    ),
                    public_npc_labels=labels,
                    canonical_facts=(*must, *selected_may),
                    recent_turns=history,
                    player_action=DynamicPlayerAction(description=submission.description),
                    narrative_length=DynamicNarrativeLength(
                        minimum=resolved.authority.definition.narrative_length.minimum,
                        target=resolved.authority.definition.narrative_length.target,
                        maximum=resolved.authority.definition.narrative_length.maximum,
                    ),
                    projection_truncated=truncated,
                )
            except ValidationError as exc:
                if not any(
                    "provider boundary" in error.get("msg", "")
                    for error in exc.errors()
                ):
                    raise NarrativeRequestRejectedError() from None
                if history:
                    history = history[1:]
                    truncated = True
                    continue
                if selected_may:
                    selected_may = selected_may[:-1]
                    truncated = True
                    continue
                raise NarrativeRequestRejectedError() from None

    def _validate_candidate(
        self,
        untrusted: UntrustedDynamicNarrativeCandidate,
        *,
        request: DynamicNarrativeRequest,
        resolved: _ResolvedAttempt,
        job: NarrativeJob,
        allow_length_recovery: bool = False,
    ) -> ValidatedDynamicNarrativeCandidate:
        try:
            detached = UntrustedDynamicNarrativeCandidate.model_validate_json(
                untrusted.model_dump_json()
            )
        except (AttributeError, TypeError, ValueError, ValidationError):
            self._report_rejection(DynamicNarrativeRejectionDiagnostic.PRE_REVALIDATION)
            raise NarrativeProposalRejectedError() from None
        candidate = detached.candidate
        length_band = DynamicNarrativeLengthPolicy.classify(
            len(candidate.narrative_text), preferred=request.narrative_length
        )
        is_replacement = (
            request.generation_instruction is not DynamicGenerationInstruction.ORDINARY
        )
        if length_band is DynamicNarrativeLengthBand.DEGRADED:
            if allow_length_recovery:
                raise _RecoverableGenerationError(
                    DynamicGenerationInstruction.REPLACE_BELOW_MINIMUM
                )
            if not is_replacement:
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_LENGTH_BELOW_MINIMUM
                )
                raise NarrativeProposalRejectedError()
        elif length_band is DynamicNarrativeLengthBand.BELOW_ABSOLUTE_FLOOR:
            if allow_length_recovery:
                raise _RecoverableGenerationError(
                    DynamicGenerationInstruction.REPLACE_BELOW_MINIMUM
                )
            self._report_rejection(
                DynamicNarrativeRejectionDiagnostic.PRE_LENGTH_BELOW_MINIMUM
            )
            raise NarrativeProposalRejectedError()
        elif length_band is DynamicNarrativeLengthBand.ABOVE_CEILING:
            if allow_length_recovery:
                raise _RecoverableGenerationError(
                    DynamicGenerationInstruction.REPLACE_ABOVE_MAXIMUM
                )
            self._report_rejection(
                DynamicNarrativeRejectionDiagnostic.PRE_LENGTH_ABOVE_MAXIMUM
            )
            raise NarrativeProposalRejectedError()
        if DynamicProviderCandidateContract.SUBMITTED_ACTION_EXCLUSION_RULE.is_violated(
            candidate.suggested_actions,
            submitted_action=request.player_action.description,
        ):
            self._report_rejection(
                DynamicNarrativeRejectionDiagnostic.PRE_REPEAT_SUBMITTED_ACTION
            )
            raise NarrativeProposalRejectedError()
        for value in (
            candidate.next_scene.title,
            candidate.next_scene.summary,
            candidate.result.value,
            list(candidate.proposed_consequences),
            *candidate.suggested_actions,
            candidate.continuation,
        ):
            if len(canonical_json(value)) > 500:
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_STORAGE_BOUNDARY
                )
                raise NarrativeProposalRejectedError()
        for item in candidate.proposed_public_facts:
            if len(canonical_json({"value": item.value})) > 500:
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_STORAGE_BOUNDARY
                )
                raise NarrativeProposalRejectedError()
        try:
            hidden = _hidden_reference_index(
                resolved,
                job,
                self.catalog,
                live_provider_references=self.live_provider_references,
            )
            public = {
                record.normalized
                for record in _public_reference_records(request, resolved, self.catalog)
            }
            hidden = tuple(
                record for record in hidden if record.normalized not in public
            )
            hidden_by_value: dict[str, list[_ProtectedReference]] = {}
            for record in hidden:
                hidden_by_value.setdefault(record.normalized, []).append(record)
            hidden_values = tuple(
                sorted(hidden_by_value, key=lambda value: (-len(value), value))
            )
        except (AttributeError, TypeError, ValueError, ValidationError):
            self._report_rejection(DynamicNarrativeRejectionDiagnostic.PRE_REFERENCE_INDEX)
            raise NarrativeProposalRejectedError() from None
        for leaf in _candidate_strings(candidate.model_dump(mode="json")):
            normalized = _comparison_text(leaf)
            if (
                any(marker in normalized for marker in _INTERNAL_TEXT_MARKERS)
                or _INTERNAL_ID_PATTERN.search(leaf)
                or _LONG_SECRET_SHAPE.search(leaf)
            ):
                self._report_rejection(
                    DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER
                )
                raise NarrativeProposalRejectedError()
            for protected_value in hidden_values:
                if any(
                    record.matches(normalized)
                    for record in hidden_by_value[protected_value]
                ):
                    self._report_rejection(
                        DynamicNarrativeRejectionDiagnostic.PRE_PROTECTED_REFERENCE
                    )
                    raise NarrativeProposalRejectedError()
        return ValidatedDynamicNarrativeCandidate(
            candidate=detached.candidate,
            provider_metadata=detached.provider_metadata,
            usage=detached.usage,
        )

    async def _store_validated(
        self, job: NarrativeJob, validated: ValidatedDynamicNarrativeCandidate
    ) -> NarrativeJob:
        async with self.uow_factory() as uow:
            current = await uow.narrative_jobs.get(job.job_id, for_update=True)
            now = self._now()
            if not self._same_lease(current, job) or self._lease_expired(job, now):
                raise NarrativeJobStaleError(job.session_id)
            assert current is not None
            payload = validated.model_dump(mode="json")
            stored = self._transition_job(
                current,
                status=NarrativeJobStatus.PROPOSAL_VALIDATED,
                validated_proposal=payload,
                validated_proposal_digest=_digest(payload),
                updated_at=now,
            )
            if not await uow.narrative_jobs.replace(
                stored,
                expected_status=NarrativeJobStatus.IN_PROGRESS,
                expected_lease_token=current.lease_token,
                expected_lease_owner=current.lease_owner,
            ):
                raise NarrativeJobStaleError(job.session_id)
            await uow.commit()
            return stored

    async def _finalize(
        self,
        job: NarrativeJob,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
        *,
        entry: _AttemptEntry,
        token: object,
    ) -> TurnResponse:
        assert self.dynamic_session_service is not None
        owner_task: asyncio.Task[Any] | None = None
        cancellation_baseline: int | None = None
        commit_started = False
        retained_terminal: asyncio.Task[Any] | None = None
        response: TurnResponse | None = None
        boundary_error: BaseException | None = None
        try:
            async with self.uow_factory() as uow:
                if not await uow.sessions.lock_for_turn(submission.session_id):
                    raise SessionNotFoundError(submission.session_id)
                current = await uow.narrative_jobs.get(job.job_id, for_update=True)
                now = self._now()
                if (
                    not self._same_lease(current, job)
                    or current is None
                    or self._lease_expired(job, now)
                ):
                    raise NarrativeJobStaleError(submission.session_id)
                authority = await self.dynamic_session_service._load_dynamic_authority(
                    uow, submission.session_id
                )
                recent = await uow.narrative_jobs.recent_committed_texts(
                    submission.session_id, limit=6
                )
                view = self.dynamic_session_service._build_dynamic_view(
                    authority, recent=recent
                )
                DynamicNarrativeRequest.model_validate(
                    current.narrative_request["provider_request"]
                )
                prepared_binding = current.narrative_request["authority_binding"]
                current_resolved = _ResolvedAttempt(
                    authority=authority,
                    view=view,
                    classification=resolved.classification,
                    suggestion_id=resolved.suggestion_id,
                    ordinal=resolved.ordinal,
                    identity=resolved.identity,
                )
                try:
                    current_hidden = _hidden_reference_index(
                        current_resolved,
                        None,
                        self.catalog,
                        live_provider_references=self.live_provider_references,
                    )
                    current_hidden_digest = _hidden_reference_digest(current_hidden)
                    current_request = self._build_request(current_resolved, submission)
                except (NarrativeBoundaryError, TypeError, ValueError):
                    raise NarrativeJobStaleError(submission.session_id) from None
                current_public_digest = _public_reference_digest(
                    _public_reference_records(current_request, current_resolved, self.catalog)
                )
                if (
                    authority.persisted.session.state_version
                    != job.prepared_state_version
                    or _digest(authority.state.to_snapshot()) != job.state_fingerprint
                    or view.narrative_frame.frame_id
                    != resolved.view.narrative_frame.frame_id
                    or _view_presentation_digest(view)
                    != resolved.identity["presentation_digest"]
                    or _digest(_submission_payload(submission))
                    != _digest(
                        current.narrative_request["authority_binding"]["submission"]
                    )
                    or _digest(current.narrative_request) != current.request_fingerprint
                    or prepared_binding.get("hidden_reference_digest")
                    != current_hidden_digest
                    or prepared_binding.get("public_reference_digest")
                    != current_public_digest
                    or prepared_binding.get("session_phase")
                    != authority.persisted.session.phase
                ):
                    raise NarrativeJobStaleError(submission.session_id)
                if (
                    current.validated_proposal is None
                    or current.validated_proposal_digest is None
                ):
                    raise NarrativeJobStaleError(submission.session_id)
                validated = ValidatedDynamicNarrativeCandidate.model_validate(
                    current.validated_proposal, strict=False
                )
                if _digest(current.validated_proposal) != current.validated_proposal_digest:
                    raise NarrativeJobStaleError(submission.session_id)
                successor_state_version = _validated_successor_state_version(
                    authority.persisted.session.state_version
                )
                allocated_public_facts = _allocate_public_facts(
                    validated,
                    successor_state_version=successor_state_version,
                    view=view,
                    hidden_references=current_hidden,
                )
                candidate_state = GameState.model_validate_json(
                    authority.state.model_dump_json()
                )
                runtime = candidate_state.scenario_runtime
                if runtime is None:
                    raise NarrativeJobStaleError(submission.session_id)
                slots = _apply_candidate_slots(
                    runtime.dynamic_facts,
                    validated,
                    successor_state_version=successor_state_version,
                    allocated_public_facts=allocated_public_facts,
                )
                candidate_state.scenario_runtime = runtime.model_copy(
                    update={"dynamic_facts": slots}
                )
                try:
                    candidate_state.validate_against(self.catalog)
                    candidate_state.scenario_runtime.validate_against(
                        authority.definition
                    )
                except (DomainRuleViolation, TypeError, ValueError):
                    raise CandidateStateInvalidError(submission.session_id) from None
                public_fact_count = len(allocated_public_facts)
                payload_digest = _digest(validated.candidate.model_dump(mode="json"))
                result = ResolutionResult(
                    status=ResolutionStatus.RESOLVED_LOCAL,
                    success=True,
                    result_code="DYNAMIC_NARRATIVE_COMMITTED",
                    updated_state=candidate_state,
                    state_changed=True,
                    events=(
                        DomainEventDraft(
                            "DynamicNarrativeTurnCommitted",
                            {
                                "result": validated.candidate.result.value,
                                "public_fact_count": public_fact_count,
                                "consequence_count": len(
                                    validated.candidate.proposed_consequences
                                ),
                                "candidate_digest": payload_digest,
                            },
                        ),
                    ),
                    feedback=PlayerFeedback(
                        "DYNAMIC_NARRATIVE_COMMITTED",
                        {
                            "outcome_result": validated.candidate.result.value,
                            "public_fact_count": public_fact_count,
                        },
                    ),
                )
                candidate_state = await self._persist_state_change(
                    uow=uow,
                    submission=submission,
                    game_session=authority.persisted.session,
                    resolution=result,
                    definition=authority.definition,
                    expected_version=job.prepared_state_version,
                )
                successor_recent = (*recent, validated.candidate.narrative_text)[-6:]
                successor_view = self.dynamic_session_service._build_dynamic_view(
                    authority,
                    recent=successor_recent,
                    state_override=candidate_state,
                    state_version_override=successor_state_version,
                )
                response = TurnResponse(
                    session_id=submission.session_id,
                    client_request_id=submission.client_request_id,
                    action_signature=submission.action_signature(),
                    resolution_kind=ResolutionStatus.NARRATIVE_COMMITTED,
                    result_code="DYNAMIC_NARRATIVE_COMMITTED",
                    feedback_code="DYNAMIC_NARRATIVE_COMMITTED",
                    feedback_parameters={
                        "outcome_result": validated.candidate.result.value,
                        "public_fact_count": public_fact_count,
                    },
                    resulting_state_version=successor_state_version,
                    state_changed=True,
                    narrative_required=True,
                    narrative_pending=False,
                    narrative_frame=successor_view.narrative_frame,
                    narrative_text=validated.candidate.narrative_text,
                    narrative_status="COMMITTED",
                )
                await uow.turn_requests.add(
                    submission,
                    response.action_signature,
                    ActionRoute.NARRATIVE_NORMAL,
                    response.to_persistence(),
                )
                committed = self._transition_job(
                    current,
                    status=NarrativeJobStatus.COMMITTED,
                    lease_token=None,
                    lease_owner=None,
                    lease_expires_at=None,
                    outcome_rule_id=DYNAMIC_ACCEPTED_OUTCOME_RULE_ID,
                    accepted_narrative_text=validated.candidate.narrative_text,
                    updated_at=self._now(),
                )
                if not await uow.narrative_jobs.replace(
                    committed,
                    expected_status=NarrativeJobStatus.PROPOSAL_VALIDATED,
                    expected_lease_token=current.lease_token,
                    expected_lease_owner=current.lease_owner,
                ):
                    raise NarrativeJobStaleError(submission.session_id)
                owner_task = asyncio.current_task()
                if owner_task is None:
                    raise RuntimeError("protected completion requires an owner task")
                cancellation_baseline = owner_task.cancelling()
                commit_started = True
                await uow.commit()
                # A normal return proves COMPLETE_NEW.  Establish the retained
                # terminal task synchronously before UoW exit can await.
                retained_terminal = asyncio.create_task(
                    self._terminal(
                        entry,
                        token,
                        AttemptLifecycle.TERMINAL_AUTHORITATIVE,
                    )
                )
        except BaseException as exc:
            if (
                not commit_started
                or owner_task is None
                or cancellation_baseline is None
            ):
                raise
            boundary_error = exc

        assert owner_task is not None
        assert cancellation_baseline is not None
        assert response is not None
        cancellation_requested = (
            cancellation_baseline > 0
            or isinstance(boundary_error, asyncio.CancelledError)
        )
        if retained_terminal is not None:
            _, cancelled = await self._await_retained(
                retained_terminal,
                owner_task,
                cancellation_baseline,
                cancellation_requested,
            )
            if cancelled:
                raise asyncio.CancelledError
            return response

        retained_reconciliation = asyncio.create_task(
            self._reconcile_finalize_boundary(
                job,
                resolved,
                submission,
                entry=entry,
                token=token,
            )
        )
        reconciled, cancelled = await self._await_retained(
            retained_reconciliation,
            owner_task,
            cancellation_baseline,
            cancellation_requested,
        )
        if cancelled:
            raise asyncio.CancelledError
        if reconciled.response is not None:
            return reconciled.response
        raise NarrativeOutcomeUnknownError(submission.session_id) from None

    async def _reconcile_finalize_boundary(
        self,
        job: NarrativeJob,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
        *,
        entry: _AttemptEntry,
        token: object,
    ) -> _FinalizeReconciliation:
        """Classify and stabilize the complete atomic publication set."""

        try:
            expectation = self._expected_finalize_publication(job, resolved, submission)
            result = await self._classify_finalize_publication(
                job, resolved, submission, expectation
            )
        except BaseException:
            result = _FinalizeReconciliation(_FinalizePublicationClass.UNKNOWN)

        if result.classification is _FinalizePublicationClass.COMPLETE_NEW:
            await self._terminal(
                entry, token, AttemptLifecycle.TERMINAL_AUTHORITATIVE
            )
            return result
        if result.classification is _FinalizePublicationClass.COMPLETE_OLD:
            try:
                await self._record_terminal_job(
                    job,
                    NarrativeJobStatus.OUTCOME_UNKNOWN,
                    "NARRATIVE_OUTCOME_UNKNOWN",
                )
                async with self.uow_factory() as uow:
                    settled = await uow.narrative_jobs.get(job.job_id)
                if (
                    settled is not None
                    and settled.status is NarrativeJobStatus.OUTCOME_UNKNOWN
                    and settled.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
                ):
                    await self._terminal(
                        entry, token, AttemptLifecycle.TERMINAL_AUTHORITATIVE
                    )
                    return result
            except BaseException:
                pass
            result = _FinalizeReconciliation(_FinalizePublicationClass.UNKNOWN)
        try:
            await self._record_terminal_job(
                job,
                NarrativeJobStatus.OUTCOME_UNKNOWN,
                "NARRATIVE_OUTCOME_UNKNOWN",
            )
        except BaseException:
            # The ledger still publishes terminal uncertainty below.  Public
            # polling consults that stable classification and must not report a
            # partial-looking durable artifact as pending.
            pass
        await self._terminal(
            entry,
            token,
            AttemptLifecycle.TERMINAL_UNCERTAIN,
            error_code="NARRATIVE_OUTCOME_UNKNOWN",
        )
        return result

    def _expected_finalize_publication(
        self,
        job: NarrativeJob,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
    ) -> _FinalizeExpectation:
        assert self.dynamic_session_service is not None
        if job.validated_proposal is None or job.validated_proposal_digest is None:
            raise ValueError("finalize expectation requires a validated proposal")
        validated = ValidatedDynamicNarrativeCandidate.model_validate(
            job.validated_proposal, strict=False
        )
        if _digest(job.validated_proposal) != job.validated_proposal_digest:
            raise ValueError("finalize expectation proposal digest differs")
        if (
            resolved.authority.persisted.session.state_version
            != job.prepared_state_version
        ):
            raise ValueError("finalize expectation state version differs")
        successor_state_version = _validated_successor_state_version(
            resolved.authority.persisted.session.state_version
        )
        hidden_references = _hidden_reference_index(
            resolved,
            None,
            self.catalog,
            live_provider_references=self.live_provider_references,
        )
        allocated_public_facts = _allocate_public_facts(
            validated,
            successor_state_version=successor_state_version,
            view=resolved.view,
            hidden_references=hidden_references,
        )
        candidate_state = GameState.model_validate_json(
            resolved.authority.state.model_dump_json()
        )
        runtime = candidate_state.scenario_runtime
        if runtime is None:
            raise ValueError("finalize expectation has no scenario runtime")
        slots = _apply_candidate_slots(
            runtime.dynamic_facts,
            validated,
            successor_state_version=successor_state_version,
            allocated_public_facts=allocated_public_facts,
        )
        candidate_state.scenario_runtime = runtime.model_copy(
            update={"dynamic_facts": slots}
        )
        candidate_state.validate_against(self.catalog)
        candidate_state.scenario_runtime.validate_against(
            resolved.authority.definition
        )
        public_fact_count = len(allocated_public_facts)
        old_recent = tuple(resolved.view.recent_narrative_texts)
        successor_recent = (*old_recent, validated.candidate.narrative_text)[-6:]
        successor_view = self.dynamic_session_service._build_dynamic_view(
            resolved.authority,
            recent=successor_recent,
            state_override=candidate_state,
            state_version_override=successor_state_version,
        )
        response = TurnResponse(
            session_id=submission.session_id,
            client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(),
            resolution_kind=ResolutionStatus.NARRATIVE_COMMITTED,
            result_code="DYNAMIC_NARRATIVE_COMMITTED",
            feedback_code="DYNAMIC_NARRATIVE_COMMITTED",
            feedback_parameters={
                "outcome_result": validated.candidate.result.value,
                "public_fact_count": public_fact_count,
            },
            resulting_state_version=successor_state_version,
            state_changed=True,
            narrative_required=True,
            narrative_pending=False,
            narrative_frame=successor_view.narrative_frame,
            narrative_text=validated.candidate.narrative_text,
            narrative_status="COMMITTED",
        )
        return _FinalizeExpectation(
            old_snapshot=resolved.authority.state.to_snapshot(),
            successor_snapshot=candidate_state.to_snapshot(),
            old_view=resolved.view,
            successor_view=successor_view,
            successor_response=response,
            old_recent=old_recent,
            successor_recent=successor_recent,
            successor_event_payload={
                "result": validated.candidate.result.value,
                "public_fact_count": public_fact_count,
                "consequence_count": len(
                    validated.candidate.proposed_consequences
                ),
                "candidate_digest": _digest(
                    validated.candidate.model_dump(mode="json")
                ),
            },
        )

    async def _classify_finalize_publication(
        self,
        job: NarrativeJob,
        resolved: _ResolvedAttempt,
        submission: ActionSubmission,
        expectation: _FinalizeExpectation,
    ) -> _FinalizeReconciliation:
        assert self.dynamic_session_service is not None
        old = resolved.authority
        try:
            async with self.uow_factory() as uow:
                persisted = await uow.sessions.get_owned(
                    submission.session_id, old.persisted.session.player_id
                )
                snapshot = await uow.sessions.get_latest_snapshot(
                    submission.session_id
                )
                current_job = await uow.narrative_jobs.get(
                    job.job_id, for_update=True
                )
                stored = await uow.turn_requests.get_by_client_request_id(
                    submission.session_id, submission.client_request_id
                )
                participation = await uow.run_participations.get(
                    submission.session_id
                )
                run = await uow.runs.get(old.run.run_id)
                character = await uow.player_characters.get(
                    old.player_character.player_character_id
                )
                recent = await uow.narrative_jobs.recent_committed_texts(
                    submission.session_id, limit=6
                )
                next_event_sequence = await uow.sessions.next_event_sequence_no(
                    submission.session_id
                )
                assert self.publication_event_reader is not None
                publication_events = self.publication_event_reader(
                    submission.session_id,
                    job.prepared_state_version + 2,
                )
        except (TypeError, ValueError, ValidationError):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.IMPOSSIBLE,
                diagnostics=("authoritative_record_integrity_failure",),
            )
        except BaseException:
            return _FinalizeReconciliation(
                _FinalizePublicationClass.UNKNOWN,
                diagnostics=("authoritative_repository_observation_unreadable",),
            )

        if any(
            value is None
            for value in (persisted, snapshot, current_job, participation, run, character)
        ):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.IMPOSSIBLE,
                diagnostics=("required_authoritative_component_missing",),
            )
        assert persisted is not None
        assert snapshot is not None
        assert current_job is not None
        assert participation is not None
        assert run is not None
        assert character is not None
        if (
            not isinstance(publication_events, tuple)
            or any(not isinstance(event, DomainEvent) for event in publication_events)
        ):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.IMPOSSIBLE,
                diagnostics=("publication_event_observation_invalid",),
            )
        if len(publication_events) > 1:
            return _FinalizeReconciliation(
                _FinalizePublicationClass.IMPOSSIBLE,
                diagnostics=("publication_event_singleton_contradiction",),
            )

        binding_exact = (
            participation == old.participation
            and run == old.run
            and character == old.player_character
            and run.lifecycle_status is RunLifecycleStatus.ACTIVE
            and run.player_character_binding is not None
            and run.player_character_binding.binding_state == "active"
        )
        if not binding_exact:
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)
        if (
            current_job.job_id != job.job_id
            or current_job.session_id != job.session_id
            or current_job.turn_id != job.turn_id
            or current_job.client_request_id != job.client_request_id
            or current_job.action_signature != job.action_signature
            or current_job.request_fingerprint != job.request_fingerprint
        ):
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)

        old_version = job.prepared_state_version
        new_version = old_version + 1
        if (
            persisted.session.session_id != old.persisted.session.session_id
            or persisted.session.player_id != old.persisted.session.player_id
            or persisted.session.scenario_id != old.persisted.session.scenario_id
            or persisted.session.scenario_version
            != old.persisted.session.scenario_version
            or persisted.session.phase != old.persisted.session.phase
            or persisted.session.turn_number != old.persisted.session.turn_number
            or persisted.session.random_seed != old.persisted.session.random_seed
            or persisted.character_definition_id
            != old.persisted.character_definition_id
            or persisted.creation_client_request_id
            != old.persisted.creation_client_request_id
            or persisted.created_at != old.persisted.created_at
        ):
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)
        if persisted.session.state_version not in {old_version, new_version}:
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)
        if snapshot.state_version != persisted.session.state_version:
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)

        try:
            state = self.dynamic_session_service._load_state(
                persisted, snapshot.state_version, snapshot.state
            )
            runtime = state.scenario_runtime
            if runtime is None:
                raise ValueError("reconciled snapshot has no scenario runtime")
            definition = self.dynamic_session_service._scenario_definition(
                runtime.scenario_id
            )
            if definition != old.definition:
                return _FinalizeReconciliation(
                    _FinalizePublicationClass.IMPOSSIBLE
                )
            current_authority = _DynamicAuthority(
                persisted=persisted,
                state=state,
                definition=definition,
                participation=participation,
                run=run,
                player_character=character,
            )
            current_view = self.dynamic_session_service._build_dynamic_view(
                current_authority, recent=recent
            )
        except (KeyError, TypeError, ValueError, ValidationError, NarrativeBoundaryError):
            return _FinalizeReconciliation(_FinalizePublicationClass.IMPOSSIBLE)

        snapshot_json = canonical_json(snapshot.state)
        old_snapshot_exact = snapshot_json == canonical_json(
            expectation.old_snapshot
        )
        new_snapshot_exact = snapshot_json == canonical_json(
            expectation.successor_snapshot
        )
        old_session_exact = (
            persisted == old.persisted
            and persisted.session.state_version == old_version
        )
        expected_new_session = replace(
            old.persisted.session, state_version=new_version
        )
        new_session_exact = (
            persisted.session == expected_new_session
            and persisted.updated_at >= old.persisted.updated_at
        )
        expected_event_sequence = old_version + 2
        old_event_exact = (
            next_event_sequence == expected_event_sequence
            and not publication_events
        )
        publication_event = publication_events[0] if publication_events else None
        new_event_exact = (
            next_event_sequence == expected_event_sequence + 1
            and publication_event is not None
            and bool(publication_event.event_id)
            and publication_event.session_id == submission.session_id
            and publication_event.turn_id == submission.turn_id
            and publication_event.sequence_no == expected_event_sequence
            and publication_event.event_type == "DynamicNarrativeTurnCommitted"
            and canonical_json(publication_event.payload)
            == canonical_json(expectation.successor_event_payload)
            and publication_event.occurred_at.tzinfo is not None
            and publication_event.occurred_at.utcoffset() is not None
        )
        old_job_exact = (
            current_job == job
            and current_job.status is NarrativeJobStatus.PROPOSAL_VALIDATED
            and self._same_lease(current_job, job)
            and not self._lease_expired(current_job, self._now())
        )
        expected_committed_job = self._transition_job(
            job,
            status=NarrativeJobStatus.COMMITTED,
            lease_token=None,
            lease_owner=None,
            lease_expires_at=None,
            outcome_rule_id=DYNAMIC_ACCEPTED_OUTCOME_RULE_ID,
            accepted_narrative_text=expectation.successor_response.narrative_text,
            error_code=None,
            updated_at=current_job.updated_at,
        )
        new_job_exact = current_job == expected_committed_job
        old_response_exact = stored is None
        response: TurnResponse | None = None
        new_response_exact = False
        if stored is not None:
            try:
                response = FirstPhaseTurnOrchestrator._replay_response(
                    stored, submission
                )
                new_response_exact = (
                    stored.turn_id == submission.turn_id
                    and stored.action_signature == submission.action_signature()
                    and response == expectation.successor_response
                )
            except BaseException:
                return _FinalizeReconciliation(
                    _FinalizePublicationClass.IMPOSSIBLE
                )
        old_recent_exact = tuple(recent) == expectation.old_recent
        new_recent_exact = tuple(recent) == expectation.successor_recent
        old_view_exact = current_view == expectation.old_view
        expected_successor_view = expectation.successor_view.model_copy(
            update={"metadata": current_view.metadata}
        )
        new_view_exact = current_view == expected_successor_view

        old_checks = {
            "session": old_session_exact,
            "snapshot": old_snapshot_exact,
            "event": old_event_exact,
            "job": old_job_exact,
            "response_receipt": old_response_exact,
            "prose": old_recent_exact,
            "view_frame": old_view_exact,
        }
        new_checks = {
            "session": new_session_exact,
            "snapshot": new_snapshot_exact,
            "event": new_event_exact,
            "job": new_job_exact,
            "response_receipt": new_response_exact,
            "prose": new_recent_exact,
            "view_frame": new_view_exact,
        }
        complete_old = all(old_checks.values())
        if complete_old:
            return _FinalizeReconciliation(_FinalizePublicationClass.COMPLETE_OLD)
        complete_new = all(new_checks.values())
        if complete_new:
            return _FinalizeReconciliation(
                _FinalizePublicationClass.COMPLETE_NEW,
                response=response,
            )

        if publication_event is not None and not new_event_exact and any(
            (
                new_session_exact,
                new_snapshot_exact,
                new_job_exact,
                new_response_exact,
                new_recent_exact,
                new_view_exact,
            )
        ):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.IMPOSSIBLE,
                diagnostics=("publication_event_contradicts_successor",),
            )

        if (
            persisted.session.state_version == new_version
            or snapshot.state_version == new_version
            or new_event_exact
            or stored is not None
            or current_job.status is NarrativeJobStatus.COMMITTED
            or new_snapshot_exact
            or new_recent_exact
        ):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.PARTIAL,
                diagnostics=tuple(
                    f"successor_{name}_mismatch"
                    for name, exact in new_checks.items()
                    if not exact
                ),
            )
        if (
            persisted.session.state_version == old_version
            and snapshot.state_version == old_version
            and (old_snapshot_exact or old_view_exact or old_event_exact)
        ):
            return _FinalizeReconciliation(
                _FinalizePublicationClass.PARTIAL,
                diagnostics=tuple(
                    f"old_{name}_mismatch"
                    for name, exact in old_checks.items()
                    if not exact
                ),
            )
        return _FinalizeReconciliation(
            _FinalizePublicationClass.IMPOSSIBLE,
            diagnostics=("publication_state_contradiction",),
        )

    async def _follow(self, entry: _AttemptEntry) -> TurnResponse:
        completion = await asyncio.shield(entry.completion)
        if completion.state is AttemptLifecycle.TERMINAL_NO_JOB:
            raise NarrativeRequestRejectedError()
        if completion.state is AttemptLifecycle.TERMINAL_UNCERTAIN:
            raise NarrativeOutcomeUnknownError(entry.submission.session_id)
        return await self._authoritative_replay(entry.submission)

    async def _authoritative_replay(self, submission: ActionSubmission) -> TurnResponse:
        known_job: NarrativeJob | None = None
        async with self.uow_factory() as uow:
            stored = await uow.turn_requests.get_by_client_request_id(
                submission.session_id, submission.client_request_id
            )
            if stored is not None:
                job = await uow.narrative_jobs.get_by_client_request_id(
                    submission.session_id,
                    submission.client_request_id,
                    for_update=True,
                )
                return self._replay_response(stored, submission, job)
            job = await uow.narrative_jobs.get_by_client_request_id(
                submission.session_id,
                submission.client_request_id,
                for_update=True,
            )
            if job is None:
                raise NarrativeOutcomeUnknownError(submission.session_id)
            known_job = await self._recover_known_job(uow, job, submission)
        assert known_job is not None
        return self._known_job_result(known_job)

    async def _terminal(
        self,
        entry: _AttemptEntry,
        token: object,
        state: AttemptLifecycle,
        *,
        error_code: str | None = None,
    ) -> None:
        bucket = self._buckets[entry.submission.session_id]
        async with bucket.lock:
            if entry.owner_token is not token or entry.lifecycle in {
                AttemptLifecycle.TERMINAL_AUTHORITATIVE,
                AttemptLifecycle.TERMINAL_NO_JOB,
                AttemptLifecycle.TERMINAL_UNCERTAIN,
            }:
                return
            allowed = (
                entry.lifecycle is AttemptLifecycle.OWNER_RESERVED
                and state in {AttemptLifecycle.TERMINAL_NO_JOB, AttemptLifecycle.TERMINAL_UNCERTAIN}
            ) or (
                entry.lifecycle is AttemptLifecycle.JOB_PUBLISHED
                and state in {AttemptLifecycle.TERMINAL_AUTHORITATIVE, AttemptLifecycle.TERMINAL_UNCERTAIN}
            )
            if not allowed:
                raise RuntimeError("invalid dynamic attempt transition")
            entry.lifecycle = state
            completion = SanitizedAttemptCompletion(state=state, error_code=error_code)
            if not entry.completion.done():
                entry.completion.set_result(completion)

    async def _reconcile_terminal(self, entry: _AttemptEntry, token: object) -> None:
        job: NarrativeJob | None = None
        try:
            async with self.uow_factory() as uow:
                stored = await uow.turn_requests.get_by_client_request_id(
                    entry.submission.session_id, entry.submission.client_request_id
                )
                job = await uow.narrative_jobs.get_by_client_request_id(
                    entry.submission.session_id, entry.submission.client_request_id
                )
                authoritative = stored is not None
        except BaseException:
            authoritative = False
        if not authoritative and job is not None:
            authoritative = await self._stabilize_published_job(job)
        await self._terminal(
            entry,
            token,
            AttemptLifecycle.TERMINAL_AUTHORITATIVE
            if authoritative
            else AttemptLifecycle.TERMINAL_UNCERTAIN,
            error_code=None if authoritative else "NARRATIVE_OUTCOME_UNKNOWN",
        )

    async def _stabilize_cancelled_owner(
        self, entry: _AttemptEntry, token: object
    ) -> None:
        if entry.lifecycle is AttemptLifecycle.OWNER_RESERVED:
            await self._terminal(
                entry, token, AttemptLifecycle.TERMINAL_NO_JOB,
                error_code="NARRATIVE_REQUEST_REJECTED"
            )
        elif entry.lifecycle is AttemptLifecycle.JOB_PUBLISHED:
            await self._reconcile_terminal(entry, token)

    async def _stabilize_published_job(self, expected: NarrativeJob) -> bool:
        """Settle one proven-published job without entering the Provider.

        PREPARED is first durably claimed as attempt one and only then settled
        OUTCOME_UNKNOWN, preserving the plan's observable durable sequence.
        Existing stable terminal/committed states are only reconciled.
        """

        terminal_statuses = {
            NarrativeJobStatus.COMMITTED,
            NarrativeJobStatus.FAILED_TERMINAL,
            NarrativeJobStatus.STALE,
            NarrativeJobStatus.OUTCOME_UNKNOWN,
        }
        for _ in range(_TERMINAL_STABILIZATION_CAS_LIMIT):
            try:
                async with self.uow_factory() as uow:
                    current = await uow.narrative_jobs.get(
                        expected.job_id, for_update=True
                    )
                    if (
                        current is None
                        or current.session_id != expected.session_id
                        or current.client_request_id != expected.client_request_id
                        or current.action_signature != expected.action_signature
                        or current.request_fingerprint != expected.request_fingerprint
                    ):
                        return False
                    if current.status in terminal_statuses:
                        return True
                    if current.status is NarrativeJobStatus.PREPARED:
                        now = self._now()
                        claimed = self._transition_job(
                            current,
                            status=NarrativeJobStatus.IN_PROGRESS,
                            attempt_count=1,
                            lease_token=self._generated_id(
                                self.lease_token_generator, "lease"
                            ),
                            lease_owner=self._generated_id(
                                self.worker_id_generator, "worker"
                            ),
                            lease_expires_at=now + self.lease_duration,
                            updated_at=now,
                        )
                        if not await uow.narrative_jobs.replace(
                            claimed,
                            expected_status=NarrativeJobStatus.PREPARED,
                        ):
                            continue
                        await uow.commit()
                        continue
                    if current.status in {
                        NarrativeJobStatus.IN_PROGRESS,
                        NarrativeJobStatus.PROPOSAL_VALIDATED,
                    }:
                        terminal = self._transition_job(
                            current,
                            status=NarrativeJobStatus.OUTCOME_UNKNOWN,
                            attempt_count=1,
                            lease_token=None,
                            lease_owner=None,
                            lease_expires_at=None,
                            error_code="NARRATIVE_OUTCOME_UNKNOWN",
                            updated_at=self._now(),
                        )
                        if not await uow.narrative_jobs.replace(
                            terminal,
                            expected_status=current.status,
                            expected_lease_token=current.lease_token,
                            expected_lease_owner=current.lease_owner,
                        ):
                            continue
                        await uow.commit()
                        return True
                    return False
            except BaseException:
                return False
        try:
            async with self.uow_factory() as uow:
                current = await uow.narrative_jobs.get(expected.job_id)
                return current is not None and current.status in terminal_statuses
        except BaseException:
            return False

    async def _record_terminal_job(
        self, job: NarrativeJob, status: NarrativeJobStatus, code: str
    ) -> None:
        if status is NarrativeJobStatus.OUTCOME_UNKNOWN:
            if not await self._stabilize_published_job(job):
                raise NarrativeOutcomeUnknownError(job.session_id)
            return
        async with self.uow_factory() as uow:
            current = await uow.narrative_jobs.get(job.job_id, for_update=True)
            if current is None or current.status not in {
                NarrativeJobStatus.IN_PROGRESS,
                NarrativeJobStatus.PROPOSAL_VALIDATED,
                NarrativeJobStatus.PREPARED,
            }:
                return
            terminal = self._transition_job(
                current,
                status=status,
                attempt_count=current.attempt_count,
                lease_token=None,
                lease_owner=None,
                lease_expires_at=None,
                error_code=code,
                updated_at=self._now(),
            )
            if await uow.narrative_jobs.replace(
                terminal,
                expected_status=current.status,
                expected_lease_token=current.lease_token,
                expected_lease_owner=current.lease_owner,
            ):
                await uow.commit()

    @staticmethod
    async def _await_retained(
        task: asyncio.Task[Any],
        owner: asyncio.Task[Any],
        baseline: int,
        cancellation_requested: bool,
    ) -> tuple[Any, bool]:
        def balance() -> None:
            nonlocal cancellation_requested
            current = owner.cancelling()
            if current < baseline:
                raise RuntimeError("protected cancellation count fell below baseline")
            excess = current - baseline
            if excess:
                cancellation_requested = True
            for _ in range(excess):
                if owner.uncancel() < baseline:
                    raise RuntimeError("protected cancellation balancing crossed baseline")

        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancellation_requested = True
            finally:
                balance()
        balance()
        return task.result(), cancellation_requested

    async def _recover_known_job(
        self,
        uow: UnitOfWork,
        job: NarrativeJob,
        submission: ActionSubmission,
    ) -> NarrativeJob:
        """Durably stale incompatible pre-commit work before public mapping."""

        self._validate_known_job(job, submission)
        if (
            job.status
            not in {
                NarrativeJobStatus.PREPARED,
                NarrativeJobStatus.IN_PROGRESS,
                NarrativeJobStatus.PROPOSAL_VALIDATED,
            }
            or job.prompt_schema_version == DYNAMIC_PROMPT_SCHEMA_VERSION
        ):
            return job
        stale = self._transition_job(
            job,
            status=NarrativeJobStatus.STALE,
            lease_token=None,
            lease_owner=None,
            lease_expires_at=None,
            error_code="NARRATIVE_JOB_STALE",
            updated_at=self._now(),
        )
        if not await uow.narrative_jobs.replace(
            stale,
            expected_status=job.status,
            expected_lease_token=job.lease_token,
            expected_lease_owner=job.lease_owner,
        ):
            raise NarrativeOutcomeUnknownError(job.session_id)
        await uow.commit()
        return stale

    def _known_job_result(self, job: NarrativeJob) -> TurnResponse:
        if job.status in {
            NarrativeJobStatus.PREPARED,
            NarrativeJobStatus.IN_PROGRESS,
            NarrativeJobStatus.PROPOSAL_VALIDATED,
        }:
            request = DynamicNarrativeRequest.model_validate(
                job.narrative_request["provider_request"]
            )
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
                narrative_frame=None,
                narrative_status="PENDING",
            )
        if job.status is NarrativeJobStatus.OUTCOME_UNKNOWN:
            raise NarrativeOutcomeUnknownError(job.session_id)
        if job.status is NarrativeJobStatus.STALE:
            raise NarrativeJobStaleError(job.session_id)
        failures: dict[str | None, type[NarrativeBoundaryError]] = {
            "NARRATIVE_REQUEST_REJECTED": NarrativeRequestRejectedError,
            "NARRATIVE_PROVIDER_REQUEST_INVALID": NarrativeProviderRequestError,
            "NARRATIVE_PROVIDER_AUTHENTICATION_FAILED": NarrativeProviderAuthenticationError,
            "NARRATIVE_PROVIDER_BALANCE_INSUFFICIENT": NarrativeProviderBalanceError,
            "NARRATIVE_PROVIDER_RATE_LIMITED": NarrativeProviderRateLimitError,
            "NARRATIVE_PROVIDER_UNAVAILABLE": NarrativeProviderUnavailableError,
            "NARRATIVE_PROVIDER_RESPONSE_INVALID": NarrativeProviderResponseError,
            "NARRATIVE_PROVIDER_RESPONSE_TRUNCATED": NarrativeProviderTruncatedError,
            "NARRATIVE_PROPOSAL_REJECTED": NarrativeProposalRejectedError,
        }
        raise failures.get(job.error_code, NarrativeProposalRejectedError)()

    @staticmethod
    def _validate_known_job(job: NarrativeJob, submission: ActionSubmission) -> None:
        if job.turn_id != submission.turn_id or job.action_signature != submission.action_signature():
            raise IdempotencyConflictError(submission.session_id)

    def _now(self) -> datetime:
        value = self.clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dynamic narrative clock must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _generated_id(generator: Any, label: str) -> str:
        value = generator()
        minimum = 32 if label == "lease" else 1
        if not isinstance(value, str) or not minimum <= len(value) <= 64:
            raise ValueError(f"{label} ID generator returned an invalid value")
        return value

    @staticmethod
    def _transition_job(job: NarrativeJob, **updates: Any) -> NarrativeJob:
        payload = job.model_dump(mode="python")
        payload.update(updates)
        return NarrativeJob.model_validate(payload)

    @staticmethod
    def _same_lease(left: NarrativeJob | None, right: NarrativeJob) -> bool:
        return (
            left is not None
            and left.job_id == right.job_id
            and left.session_id == right.session_id
            and left.action_signature == right.action_signature
            and left.request_fingerprint == right.request_fingerprint
            and left.lease_token == right.lease_token
            and left.lease_owner == right.lease_owner
            and left.status is right.status
        )

    @staticmethod
    def _lease_expired(job: NarrativeJob, now: datetime) -> bool:
        expires = job.lease_expires_at
        if expires is None:
            return True
        if expires.tzinfo is None or expires.utcoffset() is None:
            raise ValueError("dynamic narrative lease expiry must be timezone-aware")
        return expires.astimezone(timezone.utc) <= now


def _view_presentation_digest(view: PlayerSessionView) -> str:
    suggestions = view.action_affordances.suggested_actions or ()
    custom = view.action_affordances.actions
    return _presentation_digest(
        presentation=view.presentation,
        free_label=custom[0].label,
        public_npc_labels=tuple(
            sorted(
                (item.display_name for item in view.player_state.visible_npcs),
                key=lambda value: (value.casefold(), value),
            )
        ),
        must=view.narrative_frame.must_render_facts,
        may=view.narrative_frame.may_render_facts,
        suggestions=tuple(item.description for item in suggestions),  # type: ignore[arg-type]
    )


def _validated_successor_state_version(current_state_version: object) -> int:
    """Guard the signed-BIGINT committed domain before the one successor addition."""

    maximum = DynamicGeneratedPublicFactKeyGrammar.MAXIMUM_SUCCESSOR_STATE_VERSION
    if type(current_state_version) is not int or not 0 <= current_state_version <= maximum:
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION
        )
    if current_state_version == maximum:
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION
        )
    successor = current_state_version + 1
    try:
        return DynamicGeneratedPublicFactKeyGrammar.validate_successor_state_version(
            successor
        )
    except (TypeError, ValueError):
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION
        ) from None


def _allocate_public_facts(
    validated: ValidatedDynamicNarrativeCandidate,
    *,
    successor_state_version: int,
    view: PlayerSessionView,
    hidden_references: tuple[_ProtectedReference, ...],
) -> tuple[DynamicAllocatedPublicFact, ...]:
    unavailable_identifiers = {
        fact.fact_id
        for fact in (
            *view.narrative_frame.must_render_facts,
            *view.narrative_frame.may_render_facts,
        )
    }
    unavailable_identifiers.update(
        record.original for record in hidden_references if record.identifier
    )
    allocated: list[DynamicAllocatedPublicFact] = []
    try:
        for ordinal, proposal in enumerate(validated.candidate.proposed_public_facts):
            key = DynamicGeneratedPublicFactKeyAllocator.allocate(
                successor_state_version=successor_state_version,
                proposal_ordinal=ordinal,
                unavailable_identifiers=unavailable_identifiers,
            )
            DynamicGeneratedPublicFactKeyGrammar.validate(key)
            _normalized_fact_semantic_key(key)
            if (
                any(marker in _comparison_text(key) for marker in _INTERNAL_TEXT_MARKERS)
                or _INTERNAL_ID_PATTERN.search(key)
                or _LONG_SECRET_SHAPE.search(key)
            ):
                raise ValueError("generated public fact key has an unavailable shape")
            allocated.append(DynamicAllocatedPublicFact(key=key, value=proposal.value))
    except (TypeError, ValueError):
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION
        ) from None
    return tuple(allocated)


def _apply_candidate_slots(
    current: Mapping[str, Any],
    validated: ValidatedDynamicNarrativeCandidate,
    *,
    successor_state_version: int,
    allocated_public_facts: tuple[DynamicAllocatedPublicFact, ...] = (),
) -> dict[str, Any]:
    # Runtime JSON values are deliberately frozen; canonical serialization is
    # the detached-copy seam for the candidate state.
    slots = json.loads(canonical_json(dict(current)))
    candidate = validated.candidate
    ring: dict[str, tuple[str, str]] = {}
    key_slot: dict[str, str] = {}
    for slot in DYNAMIC_FACT_SLOTS:
        value = slots.get(slot)
        if value is None:
            continue
        if not isinstance(value, Mapping) or set(value) != {"key", "value"}:
            raise _FinalizationDiagnosticError(
                DynamicNarrativeRejectionDiagnostic.FINAL_FACT_RING
            )
        try:
            key = _normalize_public_text(value["key"], maximum=80)
            statement = _normalize_public_text(value["value"], maximum=300)
        except (KeyError, TypeError, ValueError):
            raise _FinalizationDiagnosticError(
                DynamicNarrativeRejectionDiagnostic.FINAL_FACT_RING
            ) from None
        folded = _normalized_fact_semantic_key(key)
        if folded in key_slot:
            raise _FinalizationDiagnosticError(
                DynamicNarrativeRejectionDiagnostic.FINAL_FACT_RING
            )
        key_slot[folded] = slot
        ring[slot] = (key, statement)
    base = successor_state_version % 12
    for offset, fact in enumerate(allocated_public_facts):
        key, value = fact.key, fact.value
        folded = _normalized_fact_semantic_key(key)
        old = key_slot.get(folded)
        if old is not None:
            slots.pop(old, None)
            ring.pop(old, None)
        destination = DYNAMIC_FACT_SLOTS[(base + offset) % 12]
        displaced = ring.pop(destination, None)
        if displaced is not None:
            key_slot.pop(_normalized_fact_semantic_key(displaced[0]), None)
        slots[destination] = {"key": key, "value": value}
        ring[destination] = (key, value)
        key_slot[folded] = destination
    slots[DYNAMIC_SCENE_TITLE] = candidate.next_scene.title
    slots[DYNAMIC_SCENE_SUMMARY] = candidate.next_scene.summary
    for key, value in zip(DYNAMIC_SUGGESTION_SLOTS, candidate.suggested_actions, strict=True):
        slots[key] = value
    slots[DYNAMIC_RESULT] = candidate.result.value
    slots[DYNAMIC_CONSEQUENCES] = list(candidate.proposed_consequences)
    slots[DYNAMIC_CONTINUATION] = candidate.continuation
    if set(slots) != DYNAMIC_ALL_SLOTS and set(slots) - DYNAMIC_ALL_SLOTS:
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_SLOT_BOUNDARY
        )
    for value in slots.values():
        if len(canonical_json(value)) > 500:
            raise _FinalizationDiagnosticError(
                DynamicNarrativeRejectionDiagnostic.FINAL_SLOT_BOUNDARY
            )
    mutation_validator = StoryMutationValidator()
    validated_slots: dict[str, Any] = {}
    ordered_slots = (
        *DYNAMIC_FACT_SLOTS,
        DYNAMIC_SCENE_TITLE,
        DYNAMIC_SCENE_SUMMARY,
        *DYNAMIC_SUGGESTION_SLOTS,
        DYNAMIC_RESULT,
        DYNAMIC_CONSEQUENCES,
        DYNAMIC_CONTINUATION,
    )
    try:
        for key in ordered_slots:
            if key not in slots:
                continue
            fact = mutation_validator.validate_dynamic_collection(
                validated_slots,
                StoryMutation(
                    key=key,
                    value=slots[key],
                    kind=FactKind.DYNAMIC,
                    causal_event_id=f"dynamic-state-{successor_state_version}",
                    visibility=FactVisibility.PLAYER_KNOWN,
                ),
            )
            validated_slots[key] = fact
    except StoryMutationError:
        raise _FinalizationDiagnosticError(
            DynamicNarrativeRejectionDiagnostic.FINAL_MUTATION
        ) from None
    return slots


def _fact_ring_comparison_text(value: str) -> str:
    """Apply only the fact-ring's frozen NFC/whitespace/case-fold semantics."""

    return normalize_dynamic_text(value).casefold()


def _comparison_text(value: str) -> str:
    return unicodedata.normalize("NFKC", normalize_dynamic_text(value)).casefold()


def _candidate_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield key
            yield from _candidate_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _candidate_strings(item)


@dataclass(frozen=True, slots=True)
class _ProtectedReference:
    source_key: str
    original: str
    normalized: str
    identifier: bool

    def matches(self, candidate: str) -> bool:
        if not self.normalized:
            return False
        if not self.identifier:
            return self.normalized in candidate
        atom = r"A-Za-z0-9_.:\-"
        return re.search(
            rf"(?<![{atom}]){re.escape(self.normalized)}(?![{atom}])",
            candidate,
        ) is not None


def _hidden_scalar(
    records: list[_ProtectedReference],
    source_key: str,
    value: str | None,
    *,
    human: bool = False,
) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise TypeError("hidden reference must be a string")
    original = normalize_dynamic_text(value)
    normalized = unicodedata.normalize("NFKC", original).casefold()
    if not normalized:
        raise ValueError("required hidden reference is empty")
    records.append(_ProtectedReference(source_key, original, normalized, not human))


def _hidden_tuple(
    records: list[_ProtectedReference],
    source_key: str,
    values: tuple[str, ...] | list[str],
    *,
    human: bool = False,
) -> None:
    for index, value in enumerate(values):
        _hidden_scalar(records, f"{source_key}[{index}]", value, human=human)


def _hidden_json(
    records: list[_ProtectedReference], source_key: str, value: Any, pointer: str = ""
) -> None:
    if isinstance(value, str):
        original = normalize_dynamic_text(value)
        normalized = unicodedata.normalize("NFKC", original).casefold()
        if normalized:
            records.append(
                _ProtectedReference(
                    f"{source_key}#value/{pointer}", original, normalized, False
                )
            )
        return
    if isinstance(value, Mapping):
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("trusted JSON object key must be a string")
            escaped = key.replace("~", "~0").replace("/", "~1")
            child = f"{pointer}/{escaped}" if pointer else escaped
            original = normalize_dynamic_text(key)
            normalized = unicodedata.normalize("NFKC", original).casefold()
            if normalized:
                records.append(
                    _ProtectedReference(
                        f"{source_key}#key/{child}", original, normalized, False
                    )
                )
            _hidden_json(records, source_key, value[key], child)
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            child = f"{pointer}/{index}" if pointer else str(index)
            _hidden_json(records, source_key, item, child)


def _hidden_condition(
    records: list[_ProtectedReference], condition: Any, owner: str
) -> None:
    prefix = f"hidden:{type(condition).__name__}:{owner}"
    if isinstance(condition, FactEqualsCondition):
        _hidden_scalar(records, f"{prefix}.fact_id", condition.fact_id)
        _hidden_json(records, f"{prefix}.value", condition.value)
    elif isinstance(condition, ClueGroupCompleteCondition):
        _hidden_scalar(records, f"{prefix}.clue_group_id", condition.clue_group_id)
    elif isinstance(condition, (ClockAtLeastCondition, ClockAtMostCondition)):
        _hidden_scalar(records, f"{prefix}.clock_id", condition.clock_id)
    elif isinstance(condition, LocationOpenedCondition):
        _hidden_scalar(records, f"{prefix}.location_id", condition.location_id)
    elif isinstance(condition, EventOccurredCondition):
        _hidden_scalar(records, f"{prefix}.event_type", condition.event_type)
    elif isinstance(condition, PhaseVisitAtLeastCondition):
        _hidden_scalar(records, f"{prefix}.phase_id", condition.phase_id)
    elif not isinstance(
        condition,
        (
            AlwaysCondition,
            PhaseBeatAtLeastCondition,
            DecisionsAtLeastCondition,
            NpcAliveAcknowledgedCondition,
        ),
    ):
        raise TypeError("unsupported scenario condition type")


def _scenario_hidden_references(
    definition: ScenarioDefinition,
) -> list[_ProtectedReference]:
    records: list[_ProtectedReference] = []
    root = "hidden:ScenarioDefinition:scenario"
    for name, value, human in (
        ("scenario_id", definition.scenario_id, False),
        ("content_version", definition.content_version, False),
        ("title", definition.title, True),
        ("summary", definition.summary, True),
        ("initial_phase_id", definition.initial_phase_id, False),
        ("initial_location_id", definition.initial_location_id, False),
    ):
        _hidden_scalar(records, f"{root}.{name}", value, human=human)
    for p, phase in enumerate(definition.phases):
        owner = f"scenario.phases[{p}]"
        prefix = f"hidden:{type(phase).__name__}:{owner}"
        _hidden_scalar(records, f"{prefix}.phase_id", phase.phase_id)
        _hidden_scalar(records, f"{prefix}.title", phase.title, human=True)
        for c, condition in enumerate(phase.entry_conditions):
            _hidden_condition(records, condition, f"{owner}.entry_conditions[{c}]")
        for name in (
            "must_render_fact_ids", "required_event_types", "allowed_clue_ids",
            "visible_location_ids", "objective_ids", "allowed_action_types",
            "decision_window_ids",
        ):
            _hidden_tuple(records, f"{prefix}.{name}", getattr(phase, name))
        for t, transition in enumerate(phase.transitions):
            transition_owner = f"{owner}.transitions[{t}]"
            transition_prefix = f"hidden:{type(transition).__name__}:{transition_owner}"
            _hidden_scalar(records, f"{transition_prefix}.transition_id", transition.transition_id)
            _hidden_scalar(records, f"{transition_prefix}.target_phase_id", transition.target_phase_id)
            for c, condition in enumerate(transition.conditions):
                _hidden_condition(records, condition, f"{transition_owner}.conditions[{c}]")
        for a, cost in enumerate(phase.action_time_costs):
            cost_owner = f"{owner}.action_time_costs[{a}]"
            _hidden_scalar(records, f"hidden:{type(cost).__name__}:{cost_owner}.action_type", cost.action_type)
            for c, advance in enumerate(cost.clock_advances):
                _hidden_scalar(records, f"hidden:{type(advance).__name__}:{cost_owner}.clock_advances[{c}].clock_id", advance.clock_id)
        for c, advance in enumerate(phase.auto_beat_clock_advances):
            _hidden_scalar(records, f"hidden:{type(advance).__name__}:{owner}.auto_beat_clock_advances[{c}].clock_id", advance.clock_id)
        _hidden_tuple(records, f"{prefix}.tone_hints", phase.tone_hints, human=True)
    for index, location in enumerate(definition.locations):
        prefix = f"hidden:{type(location).__name__}:scenario.locations[{index}]"
        _hidden_scalar(records, f"{prefix}.location_id", location.location_id)
        _hidden_scalar(records, f"{prefix}.title", location.title, human=True)
        _hidden_scalar(records, f"{prefix}.summary", location.summary, human=True)
        _hidden_tuple(records, f"{prefix}.visible_entity_ids", location.visible_entity_ids)
    for index, npc in enumerate(definition.npc_references):
        prefix = f"hidden:{type(npc).__name__}:scenario.npc_references[{index}]"
        _hidden_scalar(records, f"{prefix}.npc_definition_id", npc.npc_definition_id)
        _hidden_tuple(records, f"{prefix}.known_fact_ids", npc.known_fact_ids)
    for index, fact in enumerate(definition.facts):
        prefix = f"hidden:{type(fact).__name__}:scenario.facts[{index}]"
        _hidden_scalar(records, f"{prefix}.fact_id", fact.fact_id)
        _hidden_json(records, f"{prefix}.value", fact.value)
        for candidate_index, candidate in enumerate(fact.deferred_candidates):
            _hidden_json(records, f"{prefix}.deferred_candidates[{candidate_index}]", candidate)
        for transition_index, transition in enumerate(fact.mutable_transitions):
            transition_prefix = f"hidden:{type(transition).__name__}:scenario.facts[{index}].mutable_transitions[{transition_index}]"
            _hidden_json(records, f"{transition_prefix}.from_value", transition.from_value)
            _hidden_json(records, f"{transition_prefix}.to_value", transition.to_value)
            _hidden_scalar(records, f"{transition_prefix}.event_type", transition.event_type)
    for index, clue in enumerate(definition.clues):
        prefix = f"hidden:{type(clue).__name__}:scenario.clues[{index}]"
        _hidden_scalar(records, f"{prefix}.clue_id", clue.clue_id)
        for name in ("supports_fact_ids", "source_event_types", "allowed_phase_ids", "required_any_profession_tags"):
            _hidden_tuple(records, f"{prefix}.{name}", getattr(clue, name))
        _hidden_scalar(records, f"{prefix}.visible_summary", clue.visible_summary, human=True)
    for index, group in enumerate(definition.clue_groups):
        prefix = f"hidden:{type(group).__name__}:scenario.clue_groups[{index}]"
        _hidden_scalar(records, f"{prefix}.clue_group_id", group.clue_group_id)
        _hidden_tuple(records, f"{prefix}.clue_ids", group.clue_ids)
        _hidden_scalar(records, f"{prefix}.completion_event_type", group.completion_event_type)
    for index, clock in enumerate(definition.threat_clocks):
        prefix = f"hidden:{type(clock).__name__}:scenario.threat_clocks[{index}]"
        _hidden_scalar(records, f"{prefix}.clock_id", clock.clock_id)
        for threshold_index, threshold in enumerate(clock.thresholds):
            _hidden_scalar(records, f"hidden:{type(threshold).__name__}:scenario.threat_clocks[{index}].thresholds[{threshold_index}].event_type", threshold.event_type)
    for index, window in enumerate(definition.decision_windows):
        owner = f"scenario.decision_windows[{index}]"
        prefix = f"hidden:{type(window).__name__}:{owner}"
        _hidden_scalar(records, f"{prefix}.decision_id", window.decision_id)
        for c, condition in enumerate(window.conditions):
            _hidden_condition(records, condition, f"{owner}.conditions[{c}]")
        for a, action in enumerate(window.suggested_actions):
            action_prefix = f"hidden:{type(action).__name__}:{owner}.suggested_actions[{a}]"
            _hidden_scalar(records, f"{action_prefix}.action_id", action.action_id)
            _hidden_scalar(records, f"{action_prefix}.action_type", action.action_type)
            _hidden_scalar(records, f"{action_prefix}.label_hint", action.label_hint, human=True)
            _hidden_tuple(records, f"{action_prefix}.target_ids", action.target_ids)
            _hidden_tuple(records, f"{action_prefix}.required_any_profession_tags", action.required_any_profession_tags)
            _hidden_scalar(records, f"{action_prefix}.server_event_type", action.server_event_type)
            for f, effect in enumerate(action.mutable_fact_updates):
                effect_prefix = f"hidden:{type(effect).__name__}:{owner}.suggested_actions[{a}].mutable_fact_updates[{f}]"
                _hidden_scalar(records, f"{effect_prefix}.fact_id", effect.fact_id)
                _hidden_json(records, f"{effect_prefix}.value", effect.value)
            _hidden_tuple(records, f"{action_prefix}.opened_location_ids", action.opened_location_ids)
            _hidden_scalar(records, f"{action_prefix}.new_location_id", action.new_location_id)
            _hidden_scalar(records, f"{action_prefix}.server_narrative_text", action.server_narrative_text, human=True)
        constraints = window.custom_action_constraints
        _hidden_tuple(records, f"hidden:{type(constraints).__name__}:{owner}.custom_action_constraints.allowed_action_types", constraints.allowed_action_types)
    for index, ending in enumerate(definition.endings):
        owner = f"scenario.endings[{index}]"
        prefix = f"hidden:{type(ending).__name__}:{owner}"
        _hidden_scalar(records, f"{prefix}.ending_id", ending.ending_id)
        for c, condition in enumerate(ending.conditions):
            _hidden_condition(records, condition, f"{owner}.conditions[{c}]")
    _hidden_tuple(records, f"{root}.available_profession_tags", definition.available_profession_tags)
    _hidden_tuple(records, f"{root}.story_item_definition_ids", definition.story_item_definition_ids)
    for index, rule in enumerate(definition.narrative_outcome_rules):
        owner = f"scenario.narrative_outcome_rules[{index}]"
        prefix = f"hidden:{type(rule).__name__}:{owner}"
        _hidden_scalar(records, f"{prefix}.rule_id", rule.rule_id)
        _hidden_scalar(records, f"{prefix}.rule_version", rule.rule_version)
        _hidden_tuple(records, f"{prefix}.allowed_phase_ids", rule.allowed_phase_ids)
        _hidden_tuple(records, f"{prefix}.required_visible_npc_definition_ids", rule.required_visible_npc_definition_ids)
        for q, requirement in enumerate(rule.required_fact_values):
            requirement_prefix = f"hidden:{type(requirement).__name__}:{owner}.required_fact_values[{q}]"
            _hidden_scalar(records, f"{requirement_prefix}.fact_id", requirement.fact_id)
            _hidden_json(records, f"{requirement_prefix}.value", requirement.value)
        for name in ("required_clue_ids", "required_current_decision_ids", "required_current_location_ids"):
            _hidden_tuple(records, f"{prefix}.{name}", getattr(rule, name))
        _hidden_scalar(records, f"{prefix}.safe_description", rule.safe_description, human=True)
        for e, effect in enumerate(rule.effects):
            effect_owner = f"{owner}.effects[{e}]"
            effect_prefix = f"hidden:{type(effect).__name__}:{effect_owner}"
            _hidden_scalar(records, f"{effect_prefix}.event_type", effect.event_type)
            _hidden_scalar(records, f"{effect_prefix}.action_type", effect.action_type)
            _hidden_tuple(records, f"{effect_prefix}.discovered_clue_ids", effect.discovered_clue_ids)
            for collection in ("deferred_bindings", "mutable_fact_updates"):
                for f, fact_effect in enumerate(getattr(effect, collection)):
                    fact_prefix = f"hidden:{type(fact_effect).__name__}:{effect_owner}.{collection}[{f}]"
                    _hidden_scalar(records, f"{fact_prefix}.fact_id", fact_effect.fact_id)
                    _hidden_json(records, f"{fact_prefix}.value", fact_effect.value)
            _hidden_tuple(records, f"{effect_prefix}.opened_location_ids", effect.opened_location_ids)
            _hidden_scalar(records, f"{effect_prefix}.new_location_id", effect.new_location_id)
            _hidden_tuple(records, f"{effect_prefix}.player_alive_acknowledgement_npc_definition_ids", effect.player_alive_acknowledgement_npc_definition_ids)
            _hidden_scalar(records, f"{effect_prefix}.player_alive_acknowledgement_public_text", effect.player_alive_acknowledgement_public_text, human=True)
            _hidden_scalar(records, f"{effect_prefix}.fixed_public_narrative_text", effect.fixed_public_narrative_text, human=True)
            _hidden_tuple(records, f"{effect_prefix}.forbidden_prose_terms", effect.forbidden_prose_terms, human=True)
        _hidden_scalar(records, f"{prefix}.mutex_group", rule.mutex_group)
    for index, rule in enumerate(definition.memory_rules):
        prefix = f"hidden:{type(rule).__name__}:scenario.memory_rules[{index}]"
        _hidden_scalar(records, f"{prefix}.rule_id", rule.rule_id)
        _hidden_scalar(records, f"{prefix}.rule_version", rule.rule_version)
        _hidden_tuple(records, f"{prefix}.required_narrative_outcome_rule_ids", rule.required_narrative_outcome_rule_ids)
        _hidden_tuple(records, f"{prefix}.required_scenario_event_types", rule.required_scenario_event_types)
        _hidden_scalar(records, f"{prefix}.npc_definition_id", rule.npc_definition_id)
        _hidden_scalar(records, f"{prefix}.npc_milestone", rule.npc_milestone.value if rule.npc_milestone else None)
        _hidden_scalar(records, f"{prefix}.public_fact_id", rule.public_fact_id)
        _hidden_tuple(records, f"{prefix}.allowed_ending_ids", rule.allowed_ending_ids)
        _hidden_scalar(records, f"{prefix}.significant_experience_category", rule.significant_experience_category.value if rule.significant_experience_category else None)
        _hidden_scalar(records, f"{prefix}.significant_experience_summary", rule.significant_experience_summary.value if rule.significant_experience_summary else None, human=True)
    public = definition.public_client
    if public is not None:
        owner = "scenario.public_client"
        for index, character in enumerate(public.playable_characters):
            _hidden_scalar(records, f"hidden:{type(character).__name__}:{owner}.playable_characters[{index}].character_definition_id", character.character_definition_id)
        _hidden_scalar(records, f"hidden:{type(public).__name__}:{owner}.default_character_definition_id", public.default_character_definition_id)
        for index, scene in enumerate(public.scenes):
            prefix = f"hidden:{type(scene).__name__}:{owner}.scenes[{index}]"
            _hidden_scalar(records, f"{prefix}.phase_id", scene.phase_id)
            _hidden_scalar(records, f"{prefix}.title", scene.title, human=True)
            _hidden_scalar(records, f"{prefix}.summary", scene.summary, human=True)
        for index, ending in enumerate(public.endings):
            prefix = f"hidden:{type(ending).__name__}:{owner}.endings[{index}]"
            _hidden_scalar(records, f"{prefix}.ending_id", ending.ending_id)
            _hidden_scalar(records, f"{prefix}.title", ending.title, human=True)
            _hidden_scalar(records, f"{prefix}.summary", ending.summary, human=True)
    return records


def _catalog_hidden_references(catalog: ContentCatalog) -> list[_ProtectedReference]:
    records: list[_ProtectedReference] = []
    _hidden_scalar(records, "hidden:ContentCatalog:catalog.content_version", catalog.content_version)
    for index, character in enumerate(catalog.characters):
        prefix = f"hidden:{type(character).__name__}:catalog.characters[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", character.definition_id)
        _hidden_scalar(records, f"{prefix}.display_name", character.display_name, human=True)
        for collection in ("base_attributes", "resource_caps"):
            for item_index, item in enumerate(getattr(character, collection)):
                _hidden_scalar(records, f"hidden:{type(item).__name__}:catalog.characters[{index}].{collection}[{item_index}].key", item.key)
        _hidden_tuple(records, f"{prefix}.equipment_slots", character.equipment_slots)
        _hidden_tuple(records, f"{prefix}.tags", character.tags)
    for index, npc in enumerate(catalog.npcs):
        prefix = f"hidden:{type(npc).__name__}:catalog.npcs[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", npc.definition_id)
        _hidden_scalar(records, f"{prefix}.character_definition_id", npc.character_definition_id)
        _hidden_scalar(records, f"{prefix}.display_name", npc.display_name, human=True)
        _hidden_scalar(records, f"{prefix}.persona_summary", npc.persona_summary, human=True)
        _hidden_tuple(records, f"{prefix}.tags", npc.tags)
    for index, item in enumerate(catalog.items):
        prefix = f"hidden:{type(item).__name__}:catalog.items[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", item.definition_id)
        _hidden_scalar(records, f"{prefix}.display_name", item.display_name, human=True)
        _hidden_tuple(records, f"{prefix}.tags", item.tags)
    for index, equipment in enumerate(catalog.equipment):
        prefix = f"hidden:{type(equipment).__name__}:catalog.equipment[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", equipment.definition_id)
        _hidden_scalar(records, f"{prefix}.item_definition_id", equipment.item_definition_id)
        _hidden_tuple(records, f"{prefix}.allowed_slots", equipment.allowed_slots)
        for item_index, item in enumerate(equipment.attribute_requirements):
            _hidden_scalar(records, f"hidden:{type(item).__name__}:catalog.equipment[{index}].attribute_requirements[{item_index}].attribute_id", item.attribute_id)
        for item_index, item in enumerate(equipment.skill_requirements):
            _hidden_scalar(records, f"hidden:{type(item).__name__}:catalog.equipment[{index}].skill_requirements[{item_index}].skill_definition_id", item.skill_definition_id)
        _hidden_tuple(records, f"{prefix}.effect_definition_ids", equipment.effect_definition_ids)
    for index, skill in enumerate(catalog.skills):
        prefix = f"hidden:{type(skill).__name__}:catalog.skills[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", skill.definition_id)
        _hidden_scalar(records, f"{prefix}.display_name", skill.display_name, human=True)
        for item_index, item in enumerate(skill.prerequisites):
            _hidden_scalar(records, f"hidden:{type(item).__name__}:catalog.skills[{index}].prerequisites[{item_index}].skill_definition_id", item.skill_definition_id)
        for item_index, item in enumerate(skill.resource_costs):
            _hidden_scalar(records, f"hidden:{type(item).__name__}:catalog.skills[{index}].resource_costs[{item_index}].resource_id", item.resource_id)
        _hidden_tuple(records, f"{prefix}.effect_definition_ids", skill.effect_definition_ids)
        _hidden_tuple(records, f"{prefix}.tags", skill.tags)
    for index, effect in enumerate(catalog.effects):
        prefix = f"hidden:{type(effect).__name__}:catalog.effects[{index}]"
        _hidden_scalar(records, f"{prefix}.definition_id", effect.definition_id)
        if isinstance(effect, AttributeModifierEffectDefinition):
            _hidden_scalar(records, f"{prefix}.attribute_id", effect.attribute_id)
        elif isinstance(effect, ResourceModifierEffectDefinition):
            _hidden_scalar(records, f"{prefix}.resource_id", effect.resource_id)
        else:
            raise TypeError("unsupported catalog effect type")
    return records


def _sorted_mapping_items(value: Mapping[str, Any]) -> list[tuple[str, Any]]:
    return sorted(value.items(), key=lambda item: (_comparison_text(item[0]), item[0]))


def _hidden_reference_index(
    resolved: _ResolvedAttempt,
    job: NarrativeJob | None,
    catalog: ContentCatalog,
    *,
    live_provider_references: tuple[str, ...] = (),
) -> tuple[_ProtectedReference, ...]:
    authority = resolved.authority
    if (
        catalog.content_version != authority.definition.content_version
        or catalog.content_version != authority.state.content_version
    ):
        raise ValueError("dynamic authority content versions differ")
    records = _scenario_hidden_references(authority.definition)
    records.extend(_catalog_hidden_references(catalog))
    session = authority.persisted.session
    for name in ("session_id", "player_id", "scenario_id", "scenario_version"):
        _hidden_scalar(records, f"hidden:GameSession:session.{name}", getattr(session, name))
    run = authority.run
    _hidden_scalar(records, "hidden:CanonicalRun:run.run_id", run.run_id.value)
    _hidden_scalar(records, "hidden:CanonicalRun:run.continuous_story_line_id", run.continuous_story_line_id.value)
    for provenance_name in ("creation_provenance", "current_mutation_provenance"):
        provenance = getattr(run, provenance_name)
        prefix = f"hidden:{type(provenance).__name__}:run.{provenance_name}"
        _hidden_scalar(records, f"{prefix}.target_run_id", provenance.target_run_id.value)
        _hidden_scalar(records, f"{prefix}.target_continuous_story_line_id", provenance.target_continuous_story_line_id.value)
        _hidden_scalar(records, f"{prefix}.operation_id", provenance.operation_id.value)
        _hidden_scalar(records, f"{prefix}.source_reference", provenance.source_reference.value)
    for index, participation in enumerate(run.trusted_participation_references):
        prefix = f"hidden:{type(participation).__name__}:run.trusted_participation_references[{index}]"
        _hidden_scalar(records, f"{prefix}.session_id", participation.session_id)
        _hidden_scalar(records, f"{prefix}.run_id", participation.run_id.value)
        _hidden_scalar(records, f"{prefix}.continuous_story_line_id", participation.continuous_story_line_id.value)
        _hidden_scalar(records, f"{prefix}.operation_id", participation.operation_id.value)
        _hidden_scalar(records, f"{prefix}.source_reference", participation.source_reference.value)
    binding = run.player_character_binding
    if binding is not None:
        prefix = f"hidden:{type(binding).__name__}:binding"
        _hidden_scalar(records, f"{prefix}.run_id", binding.run_id.value)
        _hidden_scalar(records, f"{prefix}.continuous_story_line_id", binding.continuous_story_line_id.value)
        reference = binding.applicable_character_reference
        _hidden_scalar(records, f"hidden:{type(reference).__name__}:binding.applicable_character_reference.player_character_id", reference.player_character_id.value)
        _hidden_scalar(records, f"{prefix}.binding_operation_id", binding.binding_operation_id.value)
        _hidden_scalar(records, f"{prefix}.binding_authority_source_ref", binding.binding_authority_source_ref.value)
    state = authority.state
    _hidden_scalar(records, "hidden:GameState:state.content_version", state.content_version)
    _hidden_scalar(records, "hidden:PlayerState:state.player.player_id", state.player.player_id)
    _hidden_scalar(records, "hidden:PlayerState:state.player.character_definition_id", state.player.character_definition_id)
    for index, (npc_key, npc) in enumerate(_sorted_mapping_items(state.npcs)):
        prefix = f"hidden:NpcState:state.npcs[{index}]"
        _hidden_scalar(records, f"{prefix}#key", npc_key)
        _hidden_scalar(records, f"{prefix}.npc_id", npc.npc_id)
        _hidden_scalar(records, f"{prefix}.definition_id", npc.definition_id)
    runtime = state.scenario_runtime
    if runtime is not None:
        prefix = "hidden:ScenarioRuntimeState:state.scenario_runtime"
        for name in ("scenario_id", "scenario_content_version", "current_phase_id", "current_location_id"):
            _hidden_scalar(records, f"{prefix}.{name}", getattr(runtime, name))
        for name in ("discovered_clue_ids", "completed_clue_group_ids", "opened_location_ids"):
            _hidden_tuple(records, f"{prefix}.{name}", sorted(getattr(runtime, name)))
        for name in ("bound_deferred_facts", "mutable_fact_values"):
            for index, (key, value) in enumerate(_sorted_mapping_items(getattr(runtime, name))):
                _hidden_scalar(records, f"{prefix}.{name}[{index}]#key", key)
                _hidden_json(records, f"{prefix}.{name}[{index}]", value)
        for index, (key, clock) in enumerate(_sorted_mapping_items(runtime.threat_clocks)):
            _hidden_scalar(records, f"{prefix}.threat_clocks[{index}]#key", key)
            _hidden_scalar(records, f"hidden:{type(clock).__name__}:state.scenario_runtime.threat_clocks[{index}].clock_id", clock.clock_id)
        _hidden_scalar(records, f"{prefix}.current_decision_id", runtime.current_decision_id)
        _hidden_tuple(records, f"{prefix}.decisions_made", runtime.decisions_made)
        _hidden_scalar(records, f"{prefix}.ending_id", runtime.ending_id)
        for name in ("phase_visit_counts", "transition_use_counts"):
            for index, (key, _value) in enumerate(_sorted_mapping_items(getattr(runtime, name))):
                _hidden_scalar(records, f"{prefix}.{name}[{index}]#key", key)
        _hidden_tuple(records, f"{prefix}.applied_event_ids", runtime.applied_event_ids)
        for index, evidence in enumerate(runtime.narrative_outcome_evidence):
            evidence_prefix = f"hidden:{type(evidence).__name__}:state.scenario_runtime.narrative_outcome_evidence[{index}]"
            _hidden_scalar(records, f"{evidence_prefix}.outcome_rule_id", evidence.outcome_rule_id)
            _hidden_scalar(records, f"{evidence_prefix}.scenario_event_type", evidence.scenario_event_type)
            for name in ("npc_definition_ids", "player_alive_acknowledgement_npc_definition_ids", "player_alive_acknowledgement_npc_ids"):
                _hidden_tuple(records, f"{evidence_prefix}.{name}", getattr(evidence, name))
        for index, evidence in enumerate(runtime.decision_outcome_evidence):
            evidence_prefix = f"hidden:{type(evidence).__name__}:state.scenario_runtime.decision_outcome_evidence[{index}]"
            _hidden_scalar(records, f"{evidence_prefix}.decision_id", evidence.decision_id)
            _hidden_scalar(records, f"{evidence_prefix}.scenario_event_type", evidence.scenario_event_type)
    if job is not None:
        job_prefix = "hidden:NarrativeJob:job"
        for name in (
            "job_id", "session_id", "turn_id", "client_request_id",
            "action_signature", "state_fingerprint", "scenario_id",
            "scenario_content_version", "request_fingerprint", "lease_token",
            "lease_owner", "validated_proposal_digest", "outcome_rule_id",
        ):
            _hidden_scalar(records, f"{job_prefix}.{name}", getattr(job, name))
    for index, value in enumerate(live_provider_references):
        field_name = "base_url" if index == 0 else "model"
        _hidden_scalar(records, f"hidden:DeepSeekSettings:live_settings.{field_name}", value)
    return tuple(records)


def _hidden_reference_digest(records: tuple[_ProtectedReference, ...]) -> str:
    return _digest(
        [
            {
                "classification": "ENUMERATED_HIDDEN_REFERENCE",
                "source_key": record.source_key,
                "original": record.original,
                "normalized": record.normalized,
                "scan_class": "IDENTIFIER" if record.identifier else "HUMAN_TEXT",
            }
            for record in records
        ]
    )


@dataclass(frozen=True, slots=True)
class _PublicReferenceRecord:
    classification: Literal["STRUCTURED_PUBLIC_REFERENCE"]
    frame_id: str
    owner_key: str
    field_path: str
    original: str
    normalized: str


def _append_public_reference(
    records: list[_PublicReferenceRecord],
    *,
    frame_id: str,
    owner_key: str,
    field_path: str,
    value: str,
) -> None:
    original = normalize_dynamic_text(value)
    if not original:
        return
    records.append(
        _PublicReferenceRecord(
            classification="STRUCTURED_PUBLIC_REFERENCE",
            frame_id=frame_id,
            owner_key=owner_key,
            field_path=field_path,
            original=original,
            normalized=unicodedata.normalize("NFKC", original).casefold(),
        )
    )


def _append_public_json_references(
    records: list[_PublicReferenceRecord],
    *,
    frame_id: str,
    owner_key: str,
    field_path: str,
    value: Any,
    pointer: str = "",
) -> None:
    if isinstance(value, str):
        suffix = f"/{pointer}" if pointer else "/"
        _append_public_reference(
            records,
            frame_id=frame_id,
            owner_key=owner_key,
            field_path=f"{field_path}#value{suffix}",
            value=value,
        )
        return
    if isinstance(value, Mapping):
        normalized_items: list[tuple[str, str, Any]] = []
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError("public fact JSON object key must be a string")
            normalized_key = unicodedata.normalize("NFC", key)
            normalized_items.append((normalized_key, key, nested))
        normalized_items.sort(key=lambda item: item[0])
        seen: set[str] = set()
        for normalized_key, _original_key, nested in normalized_items:
            if normalized_key in seen:
                raise ValueError("public fact JSON keys collide after NFC normalization")
            seen.add(normalized_key)
            escaped = normalized_key.replace("~", "~0").replace("/", "~1")
            child = f"{pointer}/{escaped}" if pointer else escaped
            suffix = f"/{child}" if child else "/"
            _append_public_reference(
                records,
                frame_id=frame_id,
                owner_key=owner_key,
                field_path=f"{field_path}#key{suffix}",
                value=normalized_key,
            )
            _append_public_json_references(
                records,
                frame_id=frame_id,
                owner_key=owner_key,
                field_path=field_path,
                value=nested,
                pointer=child,
            )
        return
    if isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            child = f"{pointer}/{index}" if pointer else str(index)
            _append_public_json_references(
                records,
                frame_id=frame_id,
                owner_key=owner_key,
                field_path=field_path,
                value=nested,
                pointer=child,
            )


def _public_reference_records(
    request: DynamicNarrativeRequest,
    resolved: _ResolvedAttempt,
    catalog: ContentCatalog,
) -> tuple[_PublicReferenceRecord, ...]:
    frame_id = resolved.view.narrative_frame.frame_id
    records: list[_PublicReferenceRecord] = []
    public = resolved.authority.definition.public_client
    if public is None:
        raise ValueError("public projection is unavailable")
    if (
        _normalize_public_text(public.title, maximum=120)
        != request.scenario_premise.title
        or _normalize_public_text(public.hook, maximum=300)
        != request.scenario_premise.hook
    ):
        raise ValueError("public premise provenance does not match the Provider request")
    premise_owner = (
        f"scenario-public-projection:{resolved.authority.definition.scenario_id}:"
        f"{resolved.authority.definition.content_version}"
    )
    _append_public_reference(
        records,
        frame_id=frame_id,
        owner_key=premise_owner,
        field_path="ScenarioDefinition.public_client.title",
        value=public.title,
    )
    _append_public_reference(
        records,
        frame_id=frame_id,
        owner_key=premise_owner,
        field_path="ScenarioDefinition.public_client.hook",
        value=public.hook,
    )
    visible_ids = set(resolved.view.narrative_frame.visible_entities)
    visible_npcs = tuple(
        sorted(
            (
                npc
                for npc in resolved.view.player_state.visible_npcs
                if npc.npc_id in visible_ids
            ),
            key=lambda npc: (npc.npc_definition_id, npc.npc_id),
        )
    )
    if {npc.npc_id for npc in visible_npcs} != visible_ids:
        raise ValueError("public NPC provenance does not match the committed Frame")
    expected_labels = tuple(
        sorted(
            (
                _normalize_public_text(npc.display_name, maximum=120)
                for npc in visible_npcs
            ),
            key=lambda value: (value.casefold(), value),
        )
    )
    if expected_labels != request.public_npc_labels:
        raise ValueError("public NPC provenance does not match the Provider request")
    for npc in visible_npcs:
        _append_public_reference(
            records,
            frame_id=frame_id,
            owner_key=f"npc:{npc.npc_definition_id}:{npc.npc_id}",
            field_path="PlayerVisibleStateProjection.visible_npcs[*].display_name",
            value=npc.display_name,
        )

    role_owner = resolved.authority.state.player.character_definition_id
    role = next(
        (
            item
            for item in public.playable_characters
            if item.character_definition_id == role_owner
        ),
        None,
    )
    role_character = catalog.character(role_owner)
    if role is None or role_character is None:
        raise ValueError("selected public role cannot be reconstructed")
    if (
        _normalize_public_text(role_character.display_name, maximum=120)
        != request.scenario_role.display_name
        or _normalize_public_text(role.description, maximum=300)
        != request.scenario_role.description
    ):
        raise ValueError("public role provenance does not match the Provider request")
    _append_public_reference(
        records,
        frame_id=frame_id,
        owner_key=f"scenario-role:{role_owner}",
        field_path="CharacterDefinition.display_name",
        value=role_character.display_name,
    )
    _append_public_reference(
        records,
        frame_id=frame_id,
        owner_key=f"scenario-role:{role_owner}",
        field_path="PublicPlayableCharacter.description",
        value=role.description,
    )

    for index, fact in enumerate(request.canonical_facts):
        owner_key = f"canonical-fact:{index}:{fact.key}"
        _append_public_reference(
            records,
            frame_id=frame_id,
            owner_key=owner_key,
            field_path=f"canonical_facts[{index}].key",
            value=fact.key,
        )
        _append_public_json_references(
            records,
            frame_id=frame_id,
            owner_key=owner_key,
            field_path=f"canonical_facts[{index}].value",
            value=fact.value,
        )
    return tuple(records)


def _canonical_public_reference_bytes(
    records: tuple[_PublicReferenceRecord, ...],
) -> bytes:
    return canonical_json(
        [
            {
                "classification": record.classification,
                "frame_id": record.frame_id,
                "owner_key": record.owner_key,
                "field_path": record.field_path,
                "original": record.original,
                "normalized": record.normalized,
            }
            for record in records
        ]
    ).encode("utf-8")


def _public_reference_digest(
    records: tuple[_PublicReferenceRecord, ...],
) -> str:
    return hashlib.sha256(_canonical_public_reference_bytes(records)).hexdigest()
