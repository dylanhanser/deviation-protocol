from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import re
from types import SimpleNamespace

import httpx
import pytest

import deviation_protocol.application.dynamic_narrative_orchestrator as dynamic_orchestrator_module
from deviation_protocol.api.demo_composition import (
    _DynamicFakeProvider,
    build_dynamic_demo_runtime,
)
from deviation_protocol.api.main import create_app
from deviation_protocol.application.dynamic_narrative_models import (
    DynamicNarrativeCandidatePayload,
    DynamicNarrativeLength,
    DynamicNarrativeCapacityExhaustedError,
    DynamicNarrativeRequest,
    DynamicNextScene,
    DynamicPublicFactProposal,
    UntrustedDynamicNarrativeCandidate,
    ValidatedDynamicNarrativeCandidate,
    DynamicNarrativeProvider,
    canonical_json,
)
from deviation_protocol.application.dynamic_narrative_orchestrator import (
    AttemptLifecycle,
    DYNAMIC_FACT_SLOTS,
    DYNAMIC_SUGGESTION_SLOTS,
    _ProtectedReference,
    _PublicReferenceRecord,
    _FinalizePublicationClass,
    _apply_candidate_slots,
    _canonical_public_reference_bytes,
    _catalog_hidden_references,
    _committed_suggestion_texts,
    _hidden_reference_index,
    _hidden_condition,
    _normalized_fact_semantic_key,
    _public_reference_digest,
    _public_reference_records,
    _project_dynamic_facts,
    _submission_fingerprint,
    DynamicNarrativeOrchestrator,
    DynamicNarrativeRejectionDiagnostic,
)
from deviation_protocol.application.errors import (
    NarrativeJobStaleError,
    NarrativeOutcomeUnknownError,
    SnapshotInvalidError,
)
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
    NarrativeProviderMetadata,
    NarrativeProviderUnavailableError,
)
from deviation_protocol.application.narrative_prompt import (
    PromptBuilder,
    default_style_profile,
)
from deviation_protocol.application.ports import PersistedSnapshot, PersistedTurnRequest
from deviation_protocol.application.session_service import (
    PlayerVisibleStateProjection,
    PublicNpc,
    PublicPlayableCharacter,
)
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.scenario import (
    AlwaysCondition,
    ClockAtLeastCondition,
    ClockAtMostCondition,
    ClueGroupCompleteCondition,
    DecisionsAtLeastCondition,
    EventOccurredCondition,
    FactEqualsCondition,
    LocationOpenedCondition,
    NpcAliveAcknowledgedCondition,
    PhaseBeatAtLeastCondition,
    PhaseVisitAtLeastCondition,
    ScenarioDefinition,
)
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from deviation_protocol.domain.state import GameState
from deviation_protocol.infrastructure.demo_persistence import (
    DemoNarrativeJobRepository,
    DemoUnitOfWork,
)
from deviation_protocol.infrastructure.deepseek_narrative import (
    DeepSeekHttpResponse,
    DeepSeekNarrativeProvider,
    DeepSeekSettings,
)
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader


def _complete_dynamic_slots(facts: list[tuple[str, str]]) -> dict[str, object]:
    slots: dict[str, object] = {
        f"dynamic.narrative.fact.{index:02d}": {"key": key, "value": value}
        for index, (key, value) in enumerate(facts)
    }
    if facts:
        slots.update(
            {
                "dynamic.narrative.scene.title": "A committed scene",
                "dynamic.narrative.scene.summary": "A committed public summary.",
                "dynamic.narrative.suggestion.00": "Suggestion alpha.",
                "dynamic.narrative.suggestion.01": "Suggestion beta.",
                "dynamic.narrative.suggestion.02": "Suggestion gamma.",
                "dynamic.narrative.result": "SUCCESS",
                "dynamic.narrative.consequences": [],
                "dynamic.narrative.continuation": "CONTINUE",
            }
        )
    return slots


async def _entered_dynamic_client(runtime=None, *, identity_suffix: str = "1"):
    runtime = runtime or build_dynamic_demo_runtime(environ={})
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://dynamic.test"
    )
    created = await client.post(
        "/v1/player-characters",
        headers={"Idempotency-Key": f"Create.Dynamic-{identity_suffix}"},
        json={
            "contract_version": "structured-player-character/v1",
            "character_core": {},
            "narration_preferences": {},
        },
    )
    assert created.status_code == 200, created.text
    entered = await client.post(
        "/v1/runs",
        headers={"Idempotency-Key": f"Entry.Dynamic-{identity_suffix}"},
        json={
            "player_character_id": created.json()["player_character_id"]["value"],
            "expected_record_revision": 1,
            "scenario_id": "death_certificate",
        },
    )
    assert entered.status_code == 200, entered.text
    return runtime, client, entered.json()["session_id"]


def _safe_candidate(
    request,
    *,
    narrative_text: str | None = None,
    public_fact_key: str = "safe.note",
) -> UntrustedDynamicNarrativeCandidate:
    prose = narrative_text or ("你看见琥珀微光轻颤，静候尘埃缓缓落下。" * 40)
    prose = prose[: request.narrative_length.target]
    if len(prose) < request.narrative_length.minimum:
        prose += "公开环境保持稳定。" * 100
        prose = prose[: request.narrative_length.minimum]
    return UntrustedDynamicNarrativeCandidate(
        candidate=DynamicNarrativeCandidatePayload(
            schema_version="dynamic-narrative-candidate-v1",
            narrative_text=prose,
            result=NarrativeOutcomeResult.SUCCESS,
            proposed_consequences=("A harmless public change is noted.",),
            proposed_public_facts=(
                DynamicPublicFactProposal(
                    key=public_fact_key, value="A harmless public observation."
                ),
            ),
            next_scene=DynamicNextScene(
                title="A safe next scene", summary="The public situation continues."
            ),
            suggested_actions=(
                "Consider possibility alpha.",
                "Consider possibility beta.",
                "Consider possibility gamma.",
            ),
            continuation="CONTINUE",
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="test-dynamic",
            model="test-dynamic-v1",
            finish_reason="stop",
            attempts=1,
            latency_ms=0,
        ),
    )


def _candidate_payload(**updates):
    payload = {
        "schema_version": "dynamic-narrative-candidate-v1",
        "narrative_text": "界" * 350,
        "result": "SUCCESS",
        "proposed_consequences": [],
        "proposed_public_facts": [],
        "next_scene": {"title": "Next", "summary": "Summary"},
        "suggested_actions": ["Alpha.", "Beta.", "Gamma."],
        "continuation": "CONTINUE",
    }
    payload.update(updates)
    return payload


def _validated_slot_candidate(
    facts: tuple[tuple[str, str], ...],
) -> ValidatedDynamicNarrativeCandidate:
    payload = _candidate_payload(
        proposed_public_facts=[
            {"key": key, "value": value} for key, value in facts
        ]
    )
    return ValidatedDynamicNarrativeCandidate(
        candidate=DynamicNarrativeCandidatePayload.model_validate_json(
            json.dumps(payload)
        ),
        provider_metadata=NarrativeProviderMetadata(
            provider="slot-test",
            model="slot-test-v1",
            finish_reason="stop",
            attempts=1,
            latency_ms=0,
        ),
    )


async def _prepared_dynamic_attempt(runtime, client, session_id):
    view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
    submission = ActionSubmission(
        session_id=session_id,
        **view["action_affordances"]["suggested_actions"][0]["submission"],
    )
    orchestrator = runtime.services.turn_orchestrator
    resolved = await orchestrator._resolve_attempt(submission)
    role, entry = await orchestrator._reserve(resolved, submission)
    assert role == "OWNER"
    job = await orchestrator._publish_job(
        entry, entry.owner_token, resolved, submission
    )
    claimed = await orchestrator._claim(job)
    request = DynamicNarrativeRequest.model_validate(
        claimed.narrative_request["provider_request"]
    )
    validated = orchestrator._validate_candidate(
        _safe_candidate(request),
        request=request,
        resolved=resolved,
        job=claimed,
    )
    stored = await orchestrator._store_validated(claimed, validated)
    return orchestrator, submission, resolved, entry, request, stored


def _is_finalize_commit(uow: DemoUnitOfWork) -> bool:
    return any(
        replacement.expected_status is NarrativeJobStatus.PROPOSAL_VALIDATED
        and replacement.job.status is NarrativeJobStatus.COMMITTED
        for replacements in uow._pending_job_replacements.values()
        for replacement in replacements
    )


class _GateProvider:
    def __init__(self, *, expected: int = 1, candidate_factory=_safe_candidate) -> None:
        self.expected = expected
        self.candidate_factory = candidate_factory
        self.invocations = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = 0

    async def generate_dynamic(self, request):
        self.invocations += 1
        if self.invocations >= self.expected:
            self.entered.set()
        await self.release.wait()
        return self.candidate_factory(request)

    async def aclose(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_dynamic_run_entry_view_and_server_suggestion_commit_are_direct() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = await client.get(f"/v1/sessions/{session_id}/view")
        assert view.status_code == 200, view.text
        payload = view.json()
        complete_frame_fields = (
            "frame_id",
            "scenario_id",
            "phase_id",
            "mode",
            "current_location_id",
            "must_render_facts",
            "may_render_facts",
            "visible_entities",
            "visible_clues",
            "must_render_event_types",
            "recent_verified_events",
            "npc_knowledge",
            "tone_hints",
            "target_length",
            "min_length",
            "max_length",
            "decision_required",
            "decision_id",
            "decision_reason",
            "suggested_actions",
            "allowed_custom_action_constraints",
            "stop_condition",
            "player_visible_clocks",
        )
        assert tuple(NarrativeFrame.model_fields) == complete_frame_fields
        assert tuple(payload["narrative_frame"]) == tuple(
            field
            for field in complete_frame_fields
            if field
            not in {
                "decision_id",
                "decision_reason",
                "allowed_custom_action_constraints",
            }
        )
        assert payload["narrative_frame"]["mode"] == "FLOW"
        assert payload["narrative_frame"]["frame_id"] == (
            "frame.dynamic.4261aee59febec242a397662b94fcba935536f438b2616fc1abbd856ed3566a9"
        )
        assert payload["narrative_frame"]["suggested_actions"] == []
        suggestions = payload["action_affordances"]["suggested_actions"]
        free_custom = payload["action_affordances"]["actions"]
        assert free_custom == [
            {
                "action_type": "CUSTOM",
                "label": "自由行动",
                "input_kind": "DESCRIPTION",
                "max_input_length": 150,
                "target_required": False,
                "targets": [],
            }
        ]
        assert len(suggestions) == 3
        assert [item["ordinal"] for item in suggestions] == [0, 1, 2]
        assert suggestions[0]["label"] == "Observe the surroundings."
        assert free_custom[0]["label"] not in {
            item["label"] for item in suggestions
        }

        committed = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json=suggestions[0]["submission"],
        )
        assert committed.status_code == 200, committed.text
        body = committed.json()
        assert body["result_code"] == "DYNAMIC_NARRATIVE_COMMITTED"
        assert body["narrative_status"] == "COMMITTED"
        assert body["state_changed"] is True
        assert runtime.provider.invocation_count == 1

        successor = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        assert successor["metadata"]["state_version"] == 1
        assert len(successor["action_affordances"]["suggested_actions"]) == 3
        assert successor["narrative_frame"]["frame_id"] == (
            "frame.dynamic.76c4a26f7e393564187f55ffa704757692f6d0ac9f7c82f429f7f61f2ed36da7"
        )
        assert re.fullmatch(
            r"Dynamic scene [0-9a-f]{12}", successor["presentation"]["scene_title"]
        )
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_complete_narrative_frame_parser_rejects_every_missing_wrong_and_extra_field() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        complete = {
            **view["narrative_frame"],
            "decision_id": None,
            "decision_reason": None,
            "allowed_custom_action_constraints": None,
        }
        complete = {
            name: complete[name] for name in NarrativeFrame.model_fields
        }
        assert tuple(complete) == tuple(NarrativeFrame.model_fields)
        assert NarrativeFrame.model_validate(complete).model_dump(mode="json") == complete

        required = tuple(
            name
            for name, model_field in NarrativeFrame.model_fields.items()
            if model_field.is_required()
        )
        assert required == (
            "frame_id",
            "scenario_id",
            "phase_id",
            "mode",
            "current_location_id",
            "target_length",
            "min_length",
            "max_length",
            "decision_required",
            "stop_condition",
        )
        for field in required:
            missing = dict(complete)
            del missing[field]
            with pytest.raises(ValueError):
                NarrativeFrame.model_validate(missing)

        with pytest.raises(ValueError):
            NarrativeFrame.model_validate({**complete, "unexpected": "forbidden"})

        collection_fields = {
            "must_render_facts",
            "may_render_facts",
            "visible_entities",
            "visible_clues",
            "must_render_event_types",
            "recent_verified_events",
            "npc_knowledge",
            "tone_hints",
            "suggested_actions",
            "player_visible_clocks",
        }
        integer_fields = {"target_length", "min_length", "max_length"}
        boolean_fields = {"decision_required"}
        for field in NarrativeFrame.model_fields:
            wrong = dict(complete)
            if field in collection_fields:
                wrong[field] = "not-an-array"
            elif field in integer_fields:
                wrong[field] = "650"
            elif field in boolean_fields:
                wrong[field] = "false"
            else:
                wrong[field] = 7
            with pytest.raises(ValueError):
                NarrativeFrame.model_validate(wrong)

        malformed_nested = dict(complete)
        malformed_nested["player_visible_clocks"] = [
            {"clock_id": "clock.test", "value": 2, "maximum": 1}
        ]
        with pytest.raises(ValueError):
            NarrativeFrame.model_validate(malformed_nested)
        nonfinite = dict(complete)
        nonfinite["must_render_facts"] = [
            {"fact_id": "public.fact", "value": float("nan")}
        ]
        with pytest.raises((TypeError, ValueError)):
            NarrativeFrame.model_validate(nonfinite)
    finally:
        await client.aclose()
        await runtime.aclose()


def test_dynamic_candidate_requires_exact_three_distinct_suggestions() -> None:
    with pytest.raises(ValueError):
        DynamicNarrativeCandidatePayload.model_validate_json(
            json.dumps(
                {
                "schema_version": "dynamic-narrative-candidate-v1",
                "narrative_text": "x",
                "result": "SUCCESS",
                "proposed_consequences": [],
                "proposed_public_facts": [],
                "next_scene": {"title": "Next", "summary": "Summary"},
                "suggested_actions": ["same", "same", "third"],
                "continuation": "CONTINUE",
                }
            )
        )


@pytest.mark.parametrize("missing", tuple(_candidate_payload()))
def test_every_dynamic_candidate_field_is_required(missing: str) -> None:
    payload = _candidate_payload()
    del payload[missing]
    with pytest.raises(ValueError):
        DynamicNarrativeCandidatePayload.model_validate_json(json.dumps(payload))


def test_required_candidate_collections_accept_explicit_empty_values_only() -> None:
    candidate = DynamicNarrativeCandidatePayload.model_validate_json(
        json.dumps(_candidate_payload())
    )
    assert candidate.proposed_consequences == ()
    assert candidate.proposed_public_facts == ()
    for missing in (
        ("proposed_consequences",),
        ("proposed_public_facts",),
        ("proposed_consequences", "proposed_public_facts"),
    ):
        payload = _candidate_payload()
        for field in missing:
            del payload[field]
        with pytest.raises(ValueError):
            DynamicNarrativeCandidatePayload.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": "forbidden"},
        {"proposed_consequences": "not-an-array"},
        {"proposed_public_facts": [{"key": "safe", "value": 1}]},
        {"next_scene": {"title": "Next", "summary": "Summary", "extra": 1}},
        {"suggested_actions": ["Alpha.", 2, "Gamma."]},
    ],
)
def test_dynamic_candidate_rejects_extra_wrong_and_malformed_nested_values(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        DynamicNarrativeCandidatePayload.model_validate_json(
            json.dumps(_candidate_payload(**updates))
        )


def test_dynamic_candidate_json_parser_rejects_nonfinite_numbers() -> None:
    text = json.dumps(_candidate_payload()).replace(
        '"proposed_consequences": []', '"proposed_consequences": [NaN]'
    )
    with pytest.raises(ValueError):
        DynamicNarrativeCandidatePayload.model_validate_json(text)


@pytest.mark.parametrize(
    ("minimum", "target", "maximum", "valid"),
    (
        (349, 650, 900, False),
        (350, 650, 900, True),
        (351, 650, 900, False),
        (350, 649, 900, False),
        (350, 650, 900, True),
        (350, 651, 900, False),
        (350, 650, 899, False),
        (350, 650, 900, True),
        (350, 650, 901, False),
    ),
)
def test_exact_350_650_900_request_length_contract(
    minimum: int, target: int, maximum: int, valid: bool
) -> None:
    payload = {"minimum": minimum, "target": target, "maximum": maximum}
    if valid:
        assert DynamicNarrativeLength.model_validate(payload).model_dump() == payload
    else:
        with pytest.raises(ValueError):
            DynamicNarrativeLength.model_validate(payload)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("length", "valid"),
    (
        (349, False),
        (350, True),
        (649, True),
        (650, True),
        (651, True),
        (899, True),
        (900, True),
        (901, False),
    ),
)
async def test_candidate_prose_uses_exact_unicode_code_point_measurement(
    length: int, valid: bool
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            _submission,
            resolved,
            entry,
            request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        wrapper = UntrustedDynamicNarrativeCandidate(
            candidate=DynamicNarrativeCandidatePayload.model_validate_json(
                json.dumps(_candidate_payload(narrative_text="界" * length))
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="boundary-test",
                model="boundary-test-v1",
                finish_reason="stop",
                attempts=1,
                latency_ms=0,
            ),
        )
        if valid:
            validated = orchestrator._validate_candidate(
                wrapper, request=request, resolved=resolved, job=stored
            )
            assert len(validated.candidate.narrative_text) == length
        else:
            with pytest.raises(NarrativeProposalRejectedError):
                orchestrator._validate_candidate(
                    wrapper, request=request, resolved=resolved, job=stored
                )
    finally:
        await client.aclose()
        await runtime.aclose()


def test_finalization_diagnostic_categories_are_distinct() -> None:
    malformed = {DYNAMIC_FACT_SLOTS[0]: {"wrong": "shape"}}
    with pytest.raises(Exception) as captured:
        _apply_candidate_slots(malformed, _validated_slot_candidate(()), successor_state_version=1)
    assert captured.value.token is DynamicNarrativeRejectionDiagnostic.FINAL_FACT_RING


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("category", "fault"),
    (
        (DynamicNarrativeRejectionDiagnostic.PRE_REVALIDATION, "revalidation"),
        (DynamicNarrativeRejectionDiagnostic.PRE_LENGTH, "length"),
        (DynamicNarrativeRejectionDiagnostic.PRE_REPEAT_SUBMITTED_ACTION, "repeat"),
        (DynamicNarrativeRejectionDiagnostic.PRE_STORAGE_BOUNDARY, "storage"),
        (DynamicNarrativeRejectionDiagnostic.PRE_REFERENCE_INDEX, "reference"),
        (DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER, "marker"),
        (DynamicNarrativeRejectionDiagnostic.PRE_PROTECTED_REFERENCE, "protected"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_FACT_RING, "fact_ring"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_SLOT_BOUNDARY, "slot"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_MUTATION, "mutation"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_STATE, "state"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_VALUE, "value_error"),
        (DynamicNarrativeRejectionDiagnostic.FINAL_VALUE, "proposal_error"),
    ),
)
async def test_rejected_action_diagnostic_is_single_terminal_token_and_atomic(
    category: DynamicNarrativeRejectionDiagnostic,
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each production rejection owner emits one token without changing its contract."""

    submitted_action = "INERT_SUBMITTED_ACTION_SENTINEL"

    class Provider:
        def __init__(self) -> None:
            self.invocations = 0

        async def generate_dynamic(self, request):
            self.invocations += 1
            if fault == "revalidation":
                return object()
            candidate = _safe_candidate(request)
            payload = candidate.candidate
            if fault == "length":
                payload = payload.model_copy(update={"narrative_text": "x" * 10})
            elif fault == "repeat":
                payload = payload.model_copy(
                    update={
                        "suggested_actions": (
                            submitted_action,
                            "Safe beta.",
                            "Safe gamma.",
                        )
                    }
                )
            elif fault == "marker":
                payload = payload.model_copy(
                    update={"narrative_text": "state_version" + "界" * 350}
                )
            elif fault == "protected":
                payload = payload.model_copy(
                    update={"narrative_text": "INERT_HIDDEN_SENTINEL" + "界" * 350}
                )
            return candidate.model_copy(update={"candidate": payload})

        async def aclose(self) -> None:
            return None

    provider = Provider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    emitted: list[DynamicNarrativeRejectionDiagnostic] = []
    original_apply = dynamic_orchestrator_module._apply_candidate_slots
    try:
        orchestrator = runtime.services.turn_orchestrator
        orchestrator.diagnostic_reporter = emitted.append
        if fault == "storage":
            original_json = dynamic_orchestrator_module.canonical_json
            monkeypatch.setattr(
                dynamic_orchestrator_module,
                "canonical_json",
                lambda value: (
                    "x" * 501
                    if provider.invocations
                    and any(frame.function == "_validate_candidate" for frame in inspect.stack())
                    else original_json(value)
                ),
            )
        elif fault == "reference":
            original_index = dynamic_orchestrator_module._hidden_reference_index
            monkeypatch.setattr(
                dynamic_orchestrator_module,
                "_hidden_reference_index",
                lambda *args, **kwargs: (
                    (_ for _ in ()).throw(ValueError())
                    if provider.invocations
                    else original_index(*args, **kwargs)
                ),
            )
        elif fault == "protected":
            monkeypatch.setattr(
                dynamic_orchestrator_module,
                "_hidden_reference_index",
                lambda *_args, **_kwargs: (
                    _ProtectedReference(
                        "test", "INERT_HIDDEN_SENTINEL", "inert_hidden_sentinel", False
                    ),
                ),
            )
        elif fault == "fact_ring":
            def final_boundary(*_args, **_kwargs):
                raise dynamic_orchestrator_module._FinalizationDiagnosticError(category)

            monkeypatch.setattr(dynamic_orchestrator_module, "_apply_candidate_slots", final_boundary)
        elif fault == "slot":
            original_json = dynamic_orchestrator_module.canonical_json

            def final_slot_boundary_json(value):
                if (
                    provider.invocations
                    and not isinstance(value, dict)
                    and any(
                        frame.function == "_apply_candidate_slots"
                        for frame in inspect.stack()
                    )
                ):
                    return '"' + "x" * 499 + '"'
                return original_json(value)

            monkeypatch.setattr(
                dynamic_orchestrator_module, "canonical_json", final_slot_boundary_json
            )
        elif fault == "state":
            service = orchestrator.dynamic_session_service
            service_type = type(service)
            original_load_authority = service_type._load_dynamic_authority
            finalization_started = False
            orchestrator_type = type(orchestrator)
            original_store_validated = orchestrator_type._store_validated

            async def mark_finalization(self, *args, **kwargs):
                nonlocal finalization_started
                stored = await original_store_validated(self, *args, **kwargs)
                if self is orchestrator:
                    finalization_started = True
                return stored

            async def finalization_authority(self, *args, **kwargs):
                authority = await original_load_authority(self, *args, **kwargs)
                if self is not service:
                    return authority
                if not finalization_started:
                    return authority
                return replace(
                    authority,
                    definition=authority.definition.model_copy(
                        update={"dynamic_fact_limit": 1}
                    ),
                )

            monkeypatch.setattr(
                service_type, "_load_dynamic_authority", finalization_authority
            )
            monkeypatch.setattr(orchestrator_type, "_store_validated", mark_finalization)
        elif fault == "mutation":
            def reject_mutation(*_args, **_kwargs):
                raise dynamic_orchestrator_module.StoryMutationError()

            monkeypatch.setattr(
                dynamic_orchestrator_module.StoryMutationValidator,
                "validate",
                reject_mutation,
            )
        elif fault in {"value_error", "proposal_error"}:
            error = ValueError() if fault == "value_error" else NarrativeProposalRejectedError()

            def final_value(*_args, **_kwargs):
                raise error

            monkeypatch.setattr(dynamic_orchestrator_module, "_apply_candidate_slots", final_value)

        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        body = {
            "turn_id": f"diagnostic-{fault}-turn",
            "client_request_id": f"diagnostic-{fault}-request",
            "action_type": "CUSTOM",
            "description": submitted_action,
        }
        before = runtime.store.snapshot()
        response = await client.post(f"/v1/sessions/{session_id}/actions", json=body)
        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "error_code": "NARRATIVE_PROPOSAL_REJECTED",
                "message": "Narrative processing failed",
            }
        }
        assert category.value not in response.text
        assert emitted == [category]
        after = runtime.store.snapshot()
        assert after.sessions == before.sessions
        assert after.snapshots == before.snapshots
        assert after.events == before.events
        assert after.turn_requests == before.turn_requests
        assert len(after.narrative_jobs) == len(before.narrative_jobs) + 1
        job = next(iter(after.narrative_jobs.values()))
        assert job.status is NarrativeJobStatus.FAILED_TERMINAL
        assert job.error_code == "NARRATIVE_PROPOSAL_REJECTED"
        view_after_first_rejection = (
            await client.get(f"/v1/sessions/{session_id}/view")
        ).json()
        assert view_after_first_rejection == view
        retry = await client.post(f"/v1/sessions/{session_id}/actions", json=body)
        assert retry.status_code == response.status_code
        assert retry.json() == response.json()
        after_retry = runtime.store.snapshot()
        assert after_retry == after
        assert next(iter(after_retry.narrative_jobs.values())).job_id == job.job_id
        assert next(iter(after_retry.narrative_jobs.values())).status is job.status
        assert emitted == [category]
        assert len(emitted) == 1
        view_after_identical_replay = (
            await client.get(f"/v1/sessions/{session_id}/view")
        ).json()
        assert view_after_identical_replay == view
        assert view_after_identical_replay == view_after_first_rejection
        assert provider.invocations == 1
    finally:
        dynamic_orchestrator_module._apply_candidate_slots = original_apply
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_reporter_baseexception_cannot_replace_terminal_rejection(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class ReporterEscape(BaseException):
        pass

    class RejectingProvider:
        def __init__(self) -> None:
            self.invocation_count = 0

        async def generate_dynamic(self, request):
            self.invocation_count += 1
            candidate = _safe_candidate(request)
            return candidate.model_copy(
                update={
                    "candidate": candidate.candidate.model_copy(
                        update={"narrative_text": "state_version" + "界" * 350}
                    )
                }
            )

        async def aclose(self) -> None:
            return None

    provider = RejectingProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    reporter_message = "INERT_REPORTER_BASEEXCEPTION_SENTINEL"
    emitted: list[DynamicNarrativeRejectionDiagnostic] = []
    try:
        orchestrator = runtime.services.turn_orchestrator

        def exploding_reporter(token: DynamicNarrativeRejectionDiagnostic) -> None:
            emitted.append(token)
            raise ReporterEscape(reporter_message)

        orchestrator.diagnostic_reporter = exploding_reporter
        view_before = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        before = runtime.store.snapshot()
        body = {
            "turn_id": "reporter-escape-turn",
            "client_request_id": "reporter-escape-request",
            "action_type": "CUSTOM",
            "description": "ordinary submitted action",
        }
        response = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json=body,
        )
        after = runtime.store.snapshot()
        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "error_code": "NARRATIVE_PROPOSAL_REJECTED",
                "message": "Narrative processing failed",
            }
        }
        assert response.json()["error"]["error_code"] == "NARRATIVE_PROPOSAL_REJECTED"
        assert "ReporterEscape" not in response.text
        assert reporter_message not in response.text
        assert DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER.value not in response.text
        assert emitted == [DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER]
        view_after_first_rejection = (
            await client.get(f"/v1/sessions/{session_id}/view")
        ).json()
        assert view_after_first_rejection == view_before
        assert after.sessions == before.sessions
        assert after.snapshots == before.snapshots
        assert after.events == before.events
        assert after.turn_requests == before.turn_requests
        assert len(after.narrative_jobs) == len(before.narrative_jobs) + 1
        job = next(iter(after.narrative_jobs.values()))
        assert job.status is NarrativeJobStatus.FAILED_TERMINAL
        assert job.error_code == "NARRATIVE_PROPOSAL_REJECTED"
        assert provider.invocation_count == 1
        retry = await client.post(f"/v1/sessions/{session_id}/actions", json=body)
        after_retry = runtime.store.snapshot()
        assert retry.status_code == response.status_code
        assert retry.json() == response.json()
        assert after_retry == after
        assert next(iter(after_retry.narrative_jobs.values())).job_id == job.job_id
        assert emitted == [DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER]
        view_after_identical_replay = (
            await client.get(f"/v1/sessions/{session_id}/view")
        ).json()
        assert (
            view_before
            == view_after_first_rejection
            == view_after_identical_replay
        )
        assert provider.invocation_count == 1
        captured = capsys.readouterr()
        assert captured.out == captured.err == ""
        combined = captured.out + captured.err
        assert reporter_message not in combined
        assert "Traceback" not in combined
        assert DynamicNarrativeRejectionDiagnostic.PRE_INTERNAL_MARKER.value not in combined
    finally:
        await client.aclose()
        await runtime.aclose()

@pytest.mark.asyncio
async def test_dynamic_capacity_attempt_512_proceeds_and_next_distinct_rejects() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    orchestrator = runtime.services.turn_orchestrator
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        suggestion = view["action_affordances"]["suggested_actions"][0]
        # Seed the process-local bucket with 511 permanent terminal reservations;
        # the submitted suggestion becomes exact reservation 512.
        from deviation_protocol.application.dynamic_narrative_orchestrator import (
            _AttemptEntry,
            _SessionAttemptBucket,
            SanitizedAttemptCompletion,
        )
        from deviation_protocol.domain.actions import ActionSubmission, ActionType

        submission = ActionSubmission(session_id=session_id, **suggestion["submission"])
        resolved = await orchestrator._resolve_attempt(submission)
        bucket = _SessionAttemptBucket(
            binding=(
                resolved.identity["run_id"],
                resolved.identity["continuous_story_line_id"],
                resolved.identity["scenario_id"],
                resolved.identity["content_version"],
                resolved.identity["player_character_id"],
                resolved.identity["player_character_revision"],
            )
        )
        loop = asyncio.get_running_loop()
        for index in range(511):
            prior = ActionSubmission(
                session_id=session_id,
                turn_id=f"turn-{index}",
                client_request_id=f"request-{index}",
                action_type=ActionType.CUSTOM,
                description="prior",
            )
            future = loop.create_future()
            future.set_result(
                SanitizedAttemptCompletion(AttemptLifecycle.TERMINAL_NO_JOB)
            )
            bucket.entries[prior.client_request_id] = _AttemptEntry(
                identity={"prior": index},
                submission=prior,
                fingerprint=str(index),
                owner_token=object(),
                lifecycle=AttemptLifecycle.TERMINAL_NO_JOB,
                completion=future,
            )
        orchestrator._buckets[session_id] = bucket
        accepted = await client.post(
            f"/v1/sessions/{session_id}/actions", json=suggestion["submission"]
        )
        assert accepted.status_code == 200, accepted.text
        assert len(bucket.entries) == 512
        assert len(runtime.store.snapshot().narrative_jobs) == 1
        assert runtime.provider.invocation_count == 1

        rejected = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={
                "turn_id": "distinct-turn",
                "client_request_id": "distinct-request",
                "action_type": "CUSTOM",
                "description": "A distinct bounded attempt after capacity.",
            },
        )
        assert rejected.status_code == 503
        assert rejected.json() == {
            "error": {
                "error_code": "DYNAMIC_NARRATIVE_CAPACITY_EXHAUSTED",
                "message": "Narrative processing failed",
            }
        }
        assert len(runtime.store.snapshot().narrative_jobs) == 1
        assert runtime.provider.invocation_count == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_real_511_reservations_have_one_atomic_512th_winner_and_duplicate_follower(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    second_client = None
    try:
        orchestrator = runtime.services.turn_orchestrator
        original_owner = DynamicNarrativeOrchestrator._owner
        original_resolve = DynamicNarrativeOrchestrator._resolve_attempt
        seed_entered = asyncio.Event()
        release_seed = asyncio.Event()
        seed_count = 0

        async def hold_seed_owners(self, entry, token, resolved, submission):
            nonlocal seed_count
            if submission.client_request_id.startswith("capacity-request-"):
                seed_count += 1
                if seed_count == 511:
                    seed_entered.set()
                await release_seed.wait()
            return await original_owner(
                self,
                entry=entry,
                token=token,
                resolved=resolved,
                submission=submission,
            )

        monkeypatch.setattr(DynamicNarrativeOrchestrator, "_owner", hold_seed_owners)
        template_submission = ActionSubmission(
            session_id=session_id,
            turn_id="capacity-template-turn",
            client_request_id="capacity-template-request",
            action_type=ActionType.CUSTOM,
            description="A valid capacity template action.",
        )
        template_resolved = await original_resolve(orchestrator, template_submission)

        async def resolve_capacity_submission(self, submission):
            if submission.session_id == session_id and (
                submission.client_request_id.startswith("capacity-request-")
                or submission.client_request_id.startswith(
                    "capacity-boundary-request-"
                )
                or submission.client_request_id == "capacity-next-request"
            ):
                identity = dict(template_resolved.identity)
                identity.update(
                    {
                        "turn_id": submission.turn_id,
                        "client_request_id": submission.client_request_id,
                        "submission_fingerprint": _submission_fingerprint(submission),
                    }
                )
                return replace(template_resolved, identity=identity)
            return await original_resolve(self, submission)

        monkeypatch.setattr(
            DynamicNarrativeOrchestrator,
            "_resolve_attempt",
            resolve_capacity_submission,
        )
        seed_tasks = tuple(
            asyncio.create_task(
                orchestrator.handle(
                ActionSubmission(
                    session_id=session_id,
                    turn_id=f"capacity-turn-{index}",
                    client_request_id=f"capacity-request-{index}",
                    action_type=ActionType.CUSTOM,
                    description=f"Capacity action {index}.",
                )
            )
            )
            for index in range(511)
        )
        try:
            await asyncio.wait_for(seed_entered.wait(), timeout=10)
        except TimeoutError:
            finished = tuple(task for task in seed_tasks if task.done())
            failures = tuple(
                repr(task.exception())
                for task in finished
                if not task.cancelled() and task.exception() is not None
            )
            pytest.fail(
                f"only {seed_count} seed owners entered; "
                f"{len(finished)} tasks finished; failures={failures[:3]}"
            )
        bucket = orchestrator._buckets[session_id]
        assert len(bucket.entries) == 511
        assert runtime.provider.invocation_count == 0
        assert runtime.store.snapshot().narrative_jobs == {}

        gate = _GateProvider()
        orchestrator.provider = gate
        submissions = tuple(
            ActionSubmission(
                session_id=session_id,
                turn_id=f"capacity-boundary-turn-{index}",
                client_request_id=f"capacity-boundary-request-{index}",
                action_type=ActionType.CUSTOM,
                description=f"Boundary action {index}.",
            )
            for index in (1, 2)
        )
        original_reserve = DynamicNarrativeOrchestrator._reserve
        both_arrived = asyncio.Event()
        release_reserve = asyncio.Event()
        arrival_count = 0

        async def synchronized_reserve(self, resolved, submission):
            nonlocal arrival_count
            if submission.client_request_id.startswith("capacity-boundary-request-"):
                arrival_count += 1
                if arrival_count == 2:
                    both_arrived.set()
                await release_reserve.wait()
            return await original_reserve(self, resolved, submission)

        monkeypatch.setattr(
            DynamicNarrativeOrchestrator, "_reserve", synchronized_reserve
        )
        racers = tuple(
            asyncio.create_task(orchestrator.handle(submission))
            for submission in submissions
        )
        await asyncio.wait_for(both_arrived.wait(), timeout=5)
        release_reserve.set()
        await asyncio.wait_for(gate.entered.wait(), timeout=5)
        assert len(bucket.entries) == 512
        admitted_id = next(
            submission.client_request_id
            for submission in submissions
            if submission.client_request_id in bucket.entries
        )
        admitted = next(
            submission
            for submission in submissions
            if submission.client_request_id == admitted_id
        )
        duplicate = asyncio.create_task(orchestrator.handle(admitted))
        gate.release.set()
        results = await asyncio.gather(*racers, duplicate, return_exceptions=True)
        successes = [item for item in results if not isinstance(item, BaseException)]
        capacity_errors = [
            item
            for item in results
            if isinstance(item, DynamicNarrativeCapacityExhaustedError)
        ]
        assert len(successes) == 2
        assert successes[0] == successes[1]
        assert len(capacity_errors) == 1
        assert gate.invocations == 1
        assert len(bucket.entries) == 512
        assert len(runtime.store.snapshot().narrative_jobs) == 1

        with pytest.raises(DynamicNarrativeCapacityExhaustedError):
            await orchestrator.handle(
                ActionSubmission(
                    session_id=session_id,
                    turn_id="capacity-next-turn",
                    client_request_id="capacity-next-request",
                    action_type=ActionType.CUSTOM,
                    description="The next distinct attempt must fail.",
                )
            )
        assert gate.invocations == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1

        _, second_client, second_session_id = await _entered_dynamic_client(
            runtime, identity_suffix="2"
        )
        second_response = await orchestrator.handle(
            ActionSubmission(
                session_id=second_session_id,
                turn_id="isolated-session-turn",
                client_request_id="isolated-session-request",
                action_type=ActionType.CUSTOM,
                description="A separate Session remains within capacity.",
            )
        )
        assert second_response.resulting_state_version == 1
        assert len(orchestrator._buckets[second_session_id].entries) == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 2

        for task in seed_tasks:
            task.cancel()
        await asyncio.gather(*seed_tasks, return_exceptions=True)
        assert len(bucket.entries) == 512
        assert len(runtime.store.snapshot().narrative_jobs) == 2
    finally:
        release_seed = locals().get("release_seed")
        if release_seed is not None:
            release_seed.set()
        for task in locals().get("seed_tasks", ()):
            if not task.done():
                task.cancel()
        if "seed_tasks" in locals():
            await asyncio.gather(*seed_tasks, return_exceptions=True)
        gate = locals().get("gate")
        if gate is not None:
            gate.release.set()
        if second_client is not None:
            await second_client.aclose()
        await client.aclose()
        await runtime.aclose()


def test_dynamic_fact_slot_inventory_is_exactly_twelve_public_slots() -> None:
    assert DYNAMIC_FACT_SLOTS == tuple(
        f"dynamic.narrative.fact.{index:02d}" for index in range(12)
    )


def test_candidate_slot_application_covers_noop_replacement_overwrite_eviction_and_wrap() -> None:
    no_op_current = _complete_dynamic_slots([("Public.Key", "Same Value")])
    no_op = _apply_candidate_slots(
        no_op_current,
        _validated_slot_candidate((("public.key", "same value"),)),
        successor_state_version=1,
    )
    assert no_op[DYNAMIC_FACT_SLOTS[0]] == {
        "key": "Public.Key",
        "value": "Same Value",
    }
    assert DYNAMIC_FACT_SLOTS[1] not in no_op

    replacement = _apply_candidate_slots(
        no_op_current,
        _validated_slot_candidate((("public.key", "Replacement"),)),
        successor_state_version=1,
    )
    assert DYNAMIC_FACT_SLOTS[0] not in replacement
    assert replacement[DYNAMIC_FACT_SLOTS[1]] == {
        "key": "public.key",
        "value": "Replacement",
    }

    overwritten = _apply_candidate_slots(
        no_op_current,
        _validated_slot_candidate((("different.key", "Different"),)),
        successor_state_version=12,
    )
    assert overwritten[DYNAMIC_FACT_SLOTS[0]] == {
        "key": "different.key",
        "value": "Different",
    }
    assert all(
        value.get("key") != "Public.Key"
        for value in overwritten.values()
        if isinstance(value, dict)
    )

    full = _complete_dynamic_slots(
        [(f"old.{index}", f"Old {index}") for index in range(12)]
    )
    wrapped = _apply_candidate_slots(
        full,
        _validated_slot_candidate(
            (("new.alpha", "Alpha"), ("new.beta", "Beta"), ("new.gamma", "Gamma"))
        ),
        successor_state_version=11,
    )
    assert tuple(wrapped[DYNAMIC_FACT_SLOTS[index]]["key"] for index in (11, 0, 1)) == (
        "new.alpha",
        "new.beta",
        "new.gamma",
    )
    assert len(wrapped) == 20
    assert set(wrapped) == {
        *DYNAMIC_FACT_SLOTS,
        "dynamic.narrative.scene.title",
        "dynamic.narrative.scene.summary",
        *DYNAMIC_SUGGESTION_SLOTS,
        "dynamic.narrative.result",
        "dynamic.narrative.consequences",
        "dynamic.narrative.continuation",
    }


def test_fact_ring_comparison_uses_nfc_without_compatibility_normalization() -> None:
    current = _complete_dynamic_slots([("public.key", "A")])

    compatibility_distinct = _apply_candidate_slots(
        current,
        _validated_slot_candidate((("PUBLIC.KEY", "Ａ"),)),
        successor_state_version=1,
    )
    assert DYNAMIC_FACT_SLOTS[0] not in compatibility_distinct
    assert compatibility_distinct[DYNAMIC_FACT_SLOTS[1]] == {
        "key": "PUBLIC.KEY",
        "value": "Ａ",
    }

    for duplicate in ("A", "a", "A\u0301"):
        committed_value = "Á" if duplicate.endswith("\u0301") else "A"
        duplicate_result = _apply_candidate_slots(
            _complete_dynamic_slots([("public.key", committed_value)]),
            _validated_slot_candidate((("PUBLIC.KEY", duplicate),)),
            successor_state_version=1,
        )
        assert duplicate_result[DYNAMIC_FACT_SLOTS[0]] == {
            "key": "public.key",
            "value": committed_value,
        }
        assert DYNAMIC_FACT_SLOTS[1] not in duplicate_result

    ordered = _apply_candidate_slots(
        _complete_dynamic_slots([("existing.key", "Same")]),
        _validated_slot_candidate(
            (
                ("EXISTING.KEY", "same"),
                ("new.alpha", "Alpha"),
                ("new.beta", "Beta"),
            )
        ),
        successor_state_version=11,
    )
    assert ordered[DYNAMIC_FACT_SLOTS[11]] == {
        "key": "new.alpha",
        "value": "Alpha",
    }
    assert ordered[DYNAMIC_FACT_SLOTS[0]] == {
        "key": "new.beta",
        "value": "Beta",
    }

    with pytest.raises(ValueError):
        _validated_slot_candidate(
            (("Public.Key", "One"), ("public.key", "Two"))
        )


@pytest.mark.parametrize(
    "malformed",
    (
        {DYNAMIC_FACT_SLOTS[0]: "not-an-object"},
        {DYNAMIC_FACT_SLOTS[0]: {"key": "safe.key"}},
        {
            DYNAMIC_FACT_SLOTS[0]: {"key": "Public.Key", "value": "One"},
            DYNAMIC_FACT_SLOTS[1]: {"key": "public.key", "value": "Two"},
        },
    ),
)
def test_candidate_slot_application_rejects_malformed_or_duplicate_committed_ring(
    malformed: dict[str, object],
) -> None:
    with pytest.raises(NarrativeProposalRejectedError):
        _apply_candidate_slots(
            malformed,
            _validated_slot_candidate(()),
            successor_state_version=1,
        )


@pytest.mark.parametrize("count", (0, 1, 3, 12))
@pytest.mark.asyncio
async def test_committed_fact_ring_reconstructs_zero_one_three_and_full_ring(
    count: int,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        snapshot = runtime.store.snapshot().snapshots[session_id]
        state = GameState.from_snapshot(
            snapshot.state,
            catalog=runtime.services.session_service.catalog,
            scenario_catalog=runtime.services.session_service.scenario_catalog,
        )
        assert state.scenario_runtime is not None
        state.scenario_runtime = state.scenario_runtime.model_copy(
            update={
                "dynamic_facts": _complete_dynamic_slots(
                    [(f"Public.Key.{index}", f"Value {index}") for index in range(count)]
                )
            }
        )
        definition = runtime.services.session_service.scenario_catalog.scenario(
            "death_certificate"
        )
        assert definition is not None
        must, may = _project_dynamic_facts(state, definition)
        assert len(must) >= 0
        assert sum(item.fact_id.startswith("Public.Key.") for item in may) == count
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.parametrize(
    "keys",
    [
        ("Public.Key", "Public.Key"),
        ("Public.Key", "public.key"),
        ("e\u0301", "é"),
    ],
)
@pytest.mark.asyncio
async def test_committed_fact_ring_rejects_exact_casefold_and_unicode_collisions(
    keys: tuple[str, str],
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        snapshot = runtime.store.snapshot().snapshots[session_id]
        state = GameState.from_snapshot(
            snapshot.state,
            catalog=runtime.services.session_service.catalog,
            scenario_catalog=runtime.services.session_service.scenario_catalog,
        )
        assert state.scenario_runtime is not None
        state.scenario_runtime = state.scenario_runtime.model_copy(
            update={"dynamic_facts": _complete_dynamic_slots([(keys[0], "One"), (keys[1], "Two")])}
        )
        with pytest.raises(ValueError):
            definition = runtime.services.session_service.scenario_catalog.scenario(
                "death_certificate"
            )
            assert definition is not None
            _project_dynamic_facts(state, definition)
    finally:
        await client.aclose()
        await runtime.aclose()


def test_normalized_fact_semantic_key_uses_nfc_whitespace_and_casefold() -> None:
    assert _normalized_fact_semantic_key(" Public.Key ") == "public.key"
    assert _normalized_fact_semantic_key("PUBLIC.KEY") == "public.key"
    with pytest.raises(ValueError):
        _normalized_fact_semantic_key("e\u0301")


@pytest.mark.asyncio
async def test_malformed_committed_ring_fails_before_job_provider_or_public_view() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        stored = runtime.store._snapshots[session_id]
        state = json.loads(json.dumps(stored.state))
        state["scenario_runtime"]["dynamic_facts"] = _complete_dynamic_slots(
            [("Public.Key", "One"), ("public.key", "Two")]
        )
        runtime.store._snapshots[session_id] = PersistedSnapshot(
            state_version=stored.state_version,
            state=state,
        )
        view = await client.get(f"/v1/sessions/{session_id}/view")
        assert view.status_code == 409
        assert view.json() == {
            "error": {
                "error_code": "SNAPSHOT_INVALID",
                "message": "Session state is unavailable or incompatible",
            }
        }
        action = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={
                "turn_id": "invalid-ring-turn",
                "client_request_id": "invalid-ring-request",
                "action_type": "CUSTOM",
                "description": "Try a safe action.",
            },
        )
        assert action.status_code == 409
        assert action.json() == view.json()
        assert runtime.provider.invocation_count == 0
        assert runtime.store.snapshot().narrative_jobs == {}
    finally:
        await client.aclose()
        await runtime.aclose()


def test_dynamic_canonical_json_rejects_floats_and_normalizes_unicode() -> None:
    assert canonical_json({"e\u0301": "e\u0301"}) == '{"é":"é"}'
    with pytest.raises(TypeError):
        canonical_json({"unsafe": 1.5})
    with pytest.raises(ValueError):
        DynamicPublicFactProposal(key="safe", value="contains\u0000control")


def test_dynamic_provider_protocol_has_the_exact_single_request_signature() -> None:
    parameters = tuple(
        inspect.signature(DynamicNarrativeProvider.generate_dynamic).parameters
    )
    assert parameters == ("self", "request")


def test_finite_authority_aggregate_field_maintenance_literals_are_current() -> None:
    assert tuple(ScenarioDefinition.model_fields) == (
        "scenario_id", "schema_version", "content_version", "title", "summary",
        "initial_phase_id", "initial_location_id", "phases", "locations",
        "npc_references", "facts", "clues", "clue_groups", "threat_clocks",
        "decision_windows", "endings", "available_profession_tags",
        "story_item_definition_ids", "dynamic_fact_limit",
        "dynamic_fact_key_max_length", "dynamic_fact_value_max_length",
        "narrative_length", "narrative_outcome_rules", "memory_rules",
        "public_client",
    )
    assert tuple(ContentCatalog.model_fields) == (
        "schema_version", "content_version", "characters", "npcs", "items",
        "equipment", "skills", "effects",
    )
    assert tuple(ScenarioRuntimeState.model_fields) == (
        "scenario_id", "scenario_content_version", "current_phase_id",
        "phase_beat_index", "current_location_id", "discovered_clue_ids",
        "completed_clue_group_ids", "bound_deferred_facts",
        "mutable_fact_values", "dynamic_facts", "threat_clocks",
        "opened_location_ids", "current_decision_id", "decisions_made",
        "rapid_decision_mode", "ending_status", "ending_id",
        "phase_visit_counts", "transition_use_counts", "applied_event_ids",
        "narrative_outcome_evidence", "decision_outcome_evidence",
    )


def test_frozen_public_hidden_storage_irrelevant_field_classification_is_complete() -> None:
    request_storage = {
        "schema_version",
        "language",
        "scenario_premise",
        "selected_player_character",
        "scenario_role",
        "current_scene",
        "public_npc_labels",
        "recent_turns",
        "player_action",
    }
    request_public = {"canonical_facts"}
    request_irrelevant = {"narrative_length", "projection_truncated"}
    assert request_storage | request_public | request_irrelevant == set(
        DynamicNarrativeRequest.model_fields
    )
    assert not (
        request_storage & request_public
        or request_storage & request_irrelevant
        or request_public & request_irrelevant
    )
    projection_public = {"visible_npcs"}
    projection_irrelevant = {
        "session_id",
        "phase",
        "state_version",
        "content_version",
        "player_id",
        "character_definition_id",
        "attributes",
        "resources",
        "wallet",
        "inventory",
        "equipped_items",
        "skills",
        "quests",
        "player_memory",
    }
    assert projection_public | projection_irrelevant == set(
        PlayerVisibleStateProjection.model_fields
    )
    assert projection_public.isdisjoint(projection_irrelevant)
    assert {"display_name"} | {"npc_id", "npc_definition_id"} == set(
        PublicNpc.model_fields
    )
    assert (
        {"display_name"}
        | {"character_definition_id"}
        | {"description"}
        == set(PublicPlayableCharacter.model_fields)
    )
    assert _ProtectedReference.__annotations__ == {
        "source_key": "str",
        "original": "str",
        "normalized": "str",
        "identifier": "bool",
    }


@pytest.mark.parametrize(
    ("condition", "expected_suffixes"),
    (
        (
            FactEqualsCondition(
                rule_type="FACT_EQUALS",
                fact_id="fact.required",
                value={"nested": ["leaf"]},
            ),
            (".fact_id", ".value#key/nested", ".value#value/nested/0"),
        ),
        (
            ClueGroupCompleteCondition(
                rule_type="CLUE_GROUP_COMPLETE", clue_group_id="clue.group"
            ),
            (".clue_group_id",),
        ),
        (
            ClockAtLeastCondition(
                rule_type="CLOCK_AT_LEAST", clock_id="clock.minimum", value=1
            ),
            (".clock_id",),
        ),
        (
            ClockAtMostCondition(
                rule_type="CLOCK_AT_MOST", clock_id="clock.maximum", value=2
            ),
            (".clock_id",),
        ),
        (
            LocationOpenedCondition(
                rule_type="LOCATION_OPENED", location_id="location.opened"
            ),
            (".location_id",),
        ),
        (
            EventOccurredCondition(
                rule_type="EVENT_OCCURRED", event_type="event.occurred"
            ),
            (".event_type",),
        ),
        (
            PhaseVisitAtLeastCondition(
                rule_type="PHASE_VISIT_AT_LEAST", phase_id="phase.visited", value=1
            ),
            (".phase_id",),
        ),
    ),
)
def test_hidden_condition_extraction_covers_every_string_bearing_concrete_type(
    condition: object,
    expected_suffixes: tuple[str, ...],
) -> None:
    records: list[_ProtectedReference] = []
    _hidden_condition(records, condition, "scenario.conditions[0]")
    assert tuple(record.source_key for record in records) == tuple(
        "hidden:"
        + type(condition).__name__
        + ":scenario.conditions[0]"
        + suffix
        for suffix in expected_suffixes
    )


@pytest.mark.parametrize(
    "condition",
    (
        AlwaysCondition(rule_type="ALWAYS"),
        PhaseBeatAtLeastCondition(rule_type="PHASE_BEAT_AT_LEAST", value=1),
        DecisionsAtLeastCondition(rule_type="DECISIONS_AT_LEAST", value=1),
        NpcAliveAcknowledgedCondition(
            rule_type="NPC_ALIVE_ACKNOWLEDGED", minimum_count=1
        ),
    ),
)
def test_hidden_condition_extraction_excludes_numeric_only_concrete_types(
    condition: object,
) -> None:
    records: list[_ProtectedReference] = []
    _hidden_condition(records, condition, "scenario.conditions[0]")
    assert records == []


def test_hidden_scan_classes_use_complete_identifier_tokens_and_human_substrings() -> None:
    identifier = _ProtectedReference(
        "hidden:probe:id.value", "private.id", "private.id", True
    )
    human = _ProtectedReference(
        "hidden:probe:text.value", "Private phrase", "private phrase", False
    )
    assert identifier.original == "private.id"
    assert human.original == "Private phrase"
    assert identifier.matches("Expose private.id now")
    assert not identifier.matches("prefixprivate.idsuffix")
    assert human.matches("A private phrase appears inside prose")


def test_public_reference_canonical_records_bind_complete_provenance() -> None:
    base = _PublicReferenceRecord(
        classification="STRUCTURED_PUBLIC_REFERENCE",
        frame_id="frame.dynamic.one",
        owner_key="owner:one",
        field_path="public.field.one",
        original="Guide",
        normalized="guide",
    )
    duplicate_value_other_owner = replace(base, owner_key="owner:two")
    duplicate_value_other_field = replace(base, field_path="public.field.two")
    equal_normalization_other_original = replace(base, original="Ｇｕｉｄｅ")
    records = (base, duplicate_value_other_owner)
    expected_bytes = (
        b'[{"classification":"STRUCTURED_PUBLIC_REFERENCE",'
        b'"field_path":"public.field.one","frame_id":"frame.dynamic.one",'
        b'"normalized":"guide","original":"Guide","owner_key":"owner:one"},'
        b'{"classification":"STRUCTURED_PUBLIC_REFERENCE",'
        b'"field_path":"public.field.one","frame_id":"frame.dynamic.one",'
        b'"normalized":"guide","original":"Guide","owner_key":"owner:two"}]'
    )
    expected_digest = "a74f12c24a147c4c6cb5a7e58d7684c2258d0eeef86235a8e227db03816e4880"
    assert _canonical_public_reference_bytes(records) == expected_bytes
    assert _public_reference_digest(records) == expected_digest
    assert tuple(json.loads(expected_bytes)[0]) == (
        "classification",
        "field_path",
        "frame_id",
        "normalized",
        "original",
        "owner_key",
    )
    changed_records = {
        "order": (duplicate_value_other_owner, base),
        "owner": (replace(base, owner_key="owner:changed"), duplicate_value_other_owner),
        "path": (base, duplicate_value_other_field),
        "frame": (
            replace(base, frame_id="frame.dynamic.two"),
            duplicate_value_other_owner,
        ),
        "original_same_normalized": (
            equal_normalization_other_original,
            duplicate_value_other_owner,
        ),
        "classification": (
            replace(base, classification="ENUMERATED_HIDDEN_REFERENCE"),
            duplicate_value_other_owner,
        ),
    }
    assert base.normalized == equal_normalization_other_original.normalized
    assert base.normalized == duplicate_value_other_owner.normalized
    for changed in changed_records.values():
        assert _canonical_public_reference_bytes(changed) != expected_bytes
        assert _public_reference_digest(changed) != expected_digest


@pytest.mark.asyncio
async def test_public_reference_records_retain_owner_field_frame_original_and_normalized() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        orchestrator = runtime.services.turn_orchestrator
        resolved = await orchestrator._resolve_attempt(submission)
        request = orchestrator._build_request(resolved, submission)
        records = _public_reference_records(request, resolved)
        assert records
        assert all(
            record.classification == "STRUCTURED_PUBLIC_REFERENCE"
            and record.frame_id == resolved.view.narrative_frame.frame_id
            and record.owner_key
            and record.field_path
            and record.original
            and record.normalized
            for record in records
        )
        assert any(record.owner_key.startswith("npc:") for record in records)
        assert any(
            record.owner_key.startswith("scenario-role:") for record in records
        )
        assert any(
            record.field_path.startswith("canonical_facts[") for record in records
        )
        assert not any("current_scene" in record.field_path for record in records)
        assert not any("recent_turns" in record.field_path for record in records)
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finalize_rejects_equal_values_when_public_provenance_binding_moves(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        original = _public_reference_records

        def moved_records(request, current_resolved):
            records = original(request, current_resolved)
            return (replace(records[0], owner_key=records[0].owner_key + ":moved"), *records[1:])

        monkeypatch.setattr(
            "deviation_protocol.application.dynamic_narrative_orchestrator._public_reference_records",
            moved_records,
        )
        with pytest.raises(NarrativeJobStaleError):
            await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
        assert runtime.provider.invocation_count == 0
        assert runtime.store.snapshot().snapshots[session_id].state_version == 0
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_dynamic_run_entry_uses_one_based_declared_npc_ids_and_stable_replay() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        snapshot = runtime.store.snapshot().snapshots[session_id].state
        npc_ids = tuple(snapshot["npcs"])
        assert npc_ids == tuple(
            f"scenario-npc-{index}" for index in range(1, len(npc_ids) + 1)
        )
        first = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        second = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        assert first == second
        visible_name = first["player_state"]["visible_npcs"][0]["display_name"]
        assert first["action_affordances"]["suggested_actions"][1]["label"] == (
            f"Speak to {visible_name}."
        )
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_nonlexical_must_fact_order_has_the_frozen_exact_frame_id() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        public_view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **public_view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        orchestrator = runtime.services.turn_orchestrator
        resolved = await orchestrator._resolve_attempt(submission)
        definition = resolved.authority.definition
        runtime_state = resolved.authority.state.scenario_runtime
        assert runtime_state is not None
        current_phase = definition.phase(runtime_state.current_phase_id)
        template = next(
            fact
            for fact in definition.facts
            if fact.kind.value == "FIXED"
            and fact.visibility.value == "PLAYER_KNOWN"
        )
        zeta = template.model_copy(update={"fact_id": "fact.zeta", "value": "Z"})
        alpha = template.model_copy(update={"fact_id": "fact.alpha", "value": "A"})
        synthetic_definition = definition.model_copy(
            update={
                "facts": (*definition.facts, zeta, alpha),
                "phases": tuple(
                    phase.model_copy(
                        update={
                            "must_render_fact_ids": ("fact.zeta", "fact.alpha")
                        }
                    )
                    if phase.phase_id == current_phase.phase_id
                    else phase
                    for phase in definition.phases
                ),
            }
        )
        synthetic_authority = replace(
            resolved.authority, definition=synthetic_definition
        )
        synthetic_view = runtime.services.session_service._build_dynamic_view(
            synthetic_authority, recent=()
        )
        assert tuple(
            (fact.fact_id, fact.value)
            for fact in synthetic_view.narrative_frame.must_render_facts
        ) == (("fact.zeta", "Z"), ("fact.alpha", "A"))
        assert synthetic_view.narrative_frame.frame_id == (
            "frame.dynamic.e5920c8ef96ac0ede9b545c4370a493745e35b2f61713ff34d319b8051808bd6"
        )
        request = orchestrator._build_request(
            replace(
                resolved,
                authority=synthetic_authority,
                view=synthetic_view,
            ),
            submission,
        )
        assert tuple(
            (fact.key, fact.value) for fact in request.canonical_facts[:2]
        ) == (("fact.zeta", "Z"), ("fact.alpha", "A"))
        assert canonical_json(request.model_dump(mode="json")).index("fact.zeta") < (
            canonical_json(request.model_dump(mode="json")).index("fact.alpha")
        )
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_fake_candidate_is_derived_only_from_complete_committed_request_input() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        orchestrator = runtime.services.turn_orchestrator
        resolved = await orchestrator._resolve_attempt(submission)
        request = orchestrator._build_request(resolved, submission)
        other = request.model_copy(
            update={
                "player_action": request.player_action.model_copy(
                    update={"description": "A different committed action."}
                )
            }
        )
        later_committed_input = request.model_copy(
            update={
                "current_scene": request.current_scene.model_copy(
                    update={"title": "A later committed scene"}
                )
            }
        )

        first_fake = _DynamicFakeProvider()
        first = await first_fake.generate_dynamic(request)
        unrelated = await first_fake.generate_dynamic(other)
        repeated = await first_fake.generate_dynamic(request)
        second_fake = _DynamicFakeProvider()
        independent = await second_fake.generate_dynamic(request)
        later = await second_fake.generate_dynamic(later_committed_input)
        concurrent = await asyncio.gather(
            *(_DynamicFakeProvider().generate_dynamic(request) for _ in range(8))
        )

        assert first == repeated == independent
        assert all(item == first for item in concurrent)
        assert unrelated != first
        assert later != first
        assert first_fake.invocation_count == 3
        assert second_fake.invocation_count == 2
        assert runtime.provider.invocation_count == 0
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_fake_failure_selector_uses_provider_instance_ordinals_and_safe_tokens(
    capsys: pytest.CaptureFixture[str],
) -> None:
    canonical_request_bytes = (
        b'{"canonical_facts":[],"current_scene":{"summary":"Scene summary.",'
        b'"title":"Scene"},"language":"zh-CN","narrative_length":{"maximum":900,'
        b'"minimum":350,"target":650},"player_action":{"action_type":"CUSTOM",'
        b'"description":"Observe."},"projection_truncated":false,'
        b'"public_npc_labels":[],"recent_turns":[],"scenario_premise":{'
        b'"hook":"Hook.","title":"Scenario"},"scenario_role":{"description":'
        b'"Role.","display_name":"Player"},"schema_version":'
        b'"dynamic-narrative-prompt-v1","selected_player_character":{'
        b'"contract_version":"structured-player-character/v1","lifecycle":"active"}}'
    )
    literal_digest = (
        "e0ba3562add9a095bafd2ca8719906840c49086f78ca20c96d6be0fd1aea712d"
    )
    unrelated_request_bytes = canonical_request_bytes.replace(
        b'"description":"Observe."', b'"description":"Unrelated."'
    )
    unrelated_literal_digest = (
        "9737a42fc62268875470adff1170c10ef9b9b12b82dcba427569873c73b6ba56"
    )
    request = DynamicNarrativeRequest.model_validate_json(canonical_request_bytes)
    unrelated = DynamicNarrativeRequest.model_validate_json(unrelated_request_bytes)

    assert canonical_json(request.model_dump(mode="json")).encode("utf-8") == (
        canonical_request_bytes
    )
    assert hashlib.sha256(canonical_request_bytes).hexdigest() == literal_digest
    assert hashlib.sha256(unrelated_request_bytes).hexdigest() == (
        unrelated_literal_digest
    )

    later = request.model_copy(
        update={
            "player_action": request.player_action.model_copy(
                update={"description": "A later, different free action."}
            )
        }
    )
    provider = _DynamicFakeProvider(5)
    first = await provider.generate_dynamic(request)
    second = await provider.generate_dynamic(unrelated)
    third = await provider.generate_dynamic(request)
    fourth = await provider.generate_dynamic(later)
    with pytest.raises(NarrativeProviderUnavailableError):
        await provider.generate_dynamic(unrelated)
    recovered = await asyncio.gather(
        provider.generate_dynamic(request),
        provider.generate_dynamic(unrelated),
        provider.generate_dynamic(request),
    )

    assert first == third
    assert first != second != fourth
    assert all(result.candidate.schema_version == "dynamic-narrative-candidate-v1" for result in recovered)
    assert provider.invocation_count == 8
    assert capsys.readouterr().out.splitlines() == [
        "DNVS_FAKE_EVIDENCE event=reset cumulative_invocations=0",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=1 outcome=SUCCESS cumulative_invocations=1",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=2 outcome=SUCCESS cumulative_invocations=2",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=3 outcome=SUCCESS cumulative_invocations=3",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=4 outcome=SUCCESS cumulative_invocations=4",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=5 outcome=INTENTIONAL_FAILURE cumulative_invocations=5",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=6 outcome=SUCCESS cumulative_invocations=6",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=7 outcome=SUCCESS cumulative_invocations=7",
        "DNVS_FAKE_EVIDENCE event=invocation ordinal=8 outcome=SUCCESS cumulative_invocations=8",
    ]


def test_initial_no_visible_npc_suggestion_uses_exact_investigate_literal() -> None:
    assert _committed_suggestion_texts(
        {}, visible_pairs=(), npc_records={}
    ) == (
        "Observe the surroundings.",
        "Investigate the immediate situation.",
        "Attempt a cautious change to the current situation.",
    )


def test_initial_visible_npc_suggestions_cover_one_multiple_and_invalid_selected_names() -> None:
    guide = PublicNpc(
        npc_id="npc.guide",
        npc_definition_id="npc.definition.guide",
        display_name="  Guide  ",
    )
    later = PublicNpc(
        npc_id="npc.later",
        npc_definition_id="npc.definition.later",
        display_name="Later",
    )
    expected = (
        "Observe the surroundings.",
        "Speak to Guide.",
        "Attempt a cautious change to the current situation.",
    )
    assert _committed_suggestion_texts(
        {},
        visible_pairs=((guide.npc_definition_id, guide.npc_id),),
        npc_records={guide.npc_id: guide},
    ) == expected
    assert _committed_suggestion_texts(
        {},
        visible_pairs=(
            (guide.npc_definition_id, guide.npc_id),
            (later.npc_definition_id, later.npc_id),
        ),
        npc_records={guide.npc_id: guide, later.npc_id: later},
    ) == expected

    with pytest.raises(KeyError):
        _committed_suggestion_texts(
            {},
            visible_pairs=(("npc.definition.missing", "npc.missing"),),
            npc_records={},
        )
    for invalid in (None, "", "bad\u0000name", "N" * 121):
        with pytest.raises((TypeError, ValueError)):
            _committed_suggestion_texts(
                {},
                visible_pairs=(("npc.definition.invalid", "npc.invalid"),),
                npc_records={
                    "npc.invalid": SimpleNamespace(display_name=invalid)
                },
            )


@pytest.mark.asyncio
async def test_exact_replay_commits_once_and_known_identity_tampering_conflicts() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = view["action_affordances"]["suggested_actions"][0]["submission"]
        first = await client.post(f"/v1/sessions/{session_id}/actions", json=submission)
        replay = await client.post(f"/v1/sessions/{session_id}/actions", json=submission)
        assert first.status_code == replay.status_code == 200
        assert first.json() == replay.json()
        assert runtime.provider.invocation_count == 1

        tampered = {**submission, "description": "Different normalized action."}
        conflict = await client.post(
            f"/v1/sessions/{session_id}/actions", json=tampered
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
        assert runtime.provider.invocation_count == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("turn_id", "dst.changed"),
        ("action_type", "OBSERVE"),
        ("description", "Changed suggestion text."),
        ("target_ids", ["scenario-npc-1"]),
        ("tool_ids", ["tool.changed"]),
        ("dialogue", "Changed dialogue"),
        ("decision_id", "decision.changed"),
        ("choice_id", "choice.changed"),
        ("item_instance_id", "item.changed"),
        ("equipment_slot_id", "slot.changed"),
        ("skill_definition_id", "skill.changed"),
    ],
)
async def test_current_suggestion_rejects_every_noncanonical_submission_field(
    field: str, value: object
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = view["action_affordances"]["suggested_actions"][0]["submission"]
        response = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={**submission, field: value},
        )
        assert response.status_code == 409
        assert response.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
        assert runtime.provider.invocation_count == 0
        assert runtime.store.snapshot().narrative_jobs == {}
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_suggestion_explicit_empty_and_null_defaults_replay_exactly() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = view["action_affordances"]["suggested_actions"][0]["submission"]
        explicit = {
            **submission,
            "target_ids": [],
            "tool_ids": [],
            "dialogue": None,
            "decision_id": None,
            "choice_id": None,
            "item_instance_id": None,
            "equipment_slot_id": None,
            "skill_definition_id": None,
        }
        first = await client.post(f"/v1/sessions/{session_id}/actions", json=explicit)
        replay = await client.post(
            f"/v1/sessions/{session_id}/actions", json=submission
        )
        assert first.status_code == replay.status_code == 200
        assert first.json() == replay.json()
        assert runtime.provider.invocation_count == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_forged_dynamic_suggestion_is_stale_before_job_or_provider() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        response = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={
                "turn_id": "dst.forged",
                "client_request_id": "dsr.forged",
                "action_type": "CUSTOM",
                "description": "Observe the surroundings.",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["error_code"] == "NARRATIVE_JOB_STALE"
        assert runtime.provider.invocation_count == 0
        assert runtime.store.snapshot().narrative_jobs == {}
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_free_custom_action_is_independent_of_server_suggestion_identity() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        response = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json={
                "turn_id": "free-turn-1",
                "client_request_id": "free-request-1",
                "action_type": "CUSTOM",
                "description": "Try an original bounded action.",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["result_code"] == "DYNAMIC_NARRATIVE_COMMITTED"
        assert runtime.provider.invocation_count == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_exact_concurrent_duplicate_has_one_owner_job_call_and_shared_result(
    monkeypatch,
) -> None:
    provider = _GateProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    follower_entered = asyncio.Event()
    original_follow = DynamicNarrativeOrchestrator._follow

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = view["action_affordances"]["suggested_actions"][0]["submission"]
        owner = asyncio.create_task(
            client.post(f"/v1/sessions/{session_id}/actions", json=submission)
        )
        await provider.entered.wait()
        assert runtime.store.active_uows == 0
        assert not runtime.services.turn_orchestrator._bucket_lock.locked()
        assert not runtime.services.turn_orchestrator._buckets[session_id].lock.locked()
        follower = asyncio.create_task(
            client.post(f"/v1/sessions/{session_id}/actions", json=submission)
        )
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        provider.release.set()
        owner_response, follower_response = await asyncio.gather(owner, follower)
        assert owner_response.status_code == follower_response.status_code == 200, (
            owner_response.text,
            follower_response.text,
        )
        assert owner_response.json() == follower_response.json()
        assert provider.invocations == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_injected_deepseek_transport_suspends_once_with_no_uow_or_lock() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    class SuspendedTransport:
        def __init__(self) -> None:
            self.calls = 0

        async def post_json(self, **_kwargs):
            self.calls += 1
            entered.set()
            await release.wait()
            envelope = {
                "id": "offline-transport-request",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                _candidate_payload(),
                                ensure_ascii=False,
                                separators=(",", ":"),
                            )
                        },
                    }
                ],
                "usage": {},
            }
            return DeepSeekHttpResponse(
                status_code=200,
                body_text=json.dumps(envelope, ensure_ascii=False),
            )

        async def aclose(self) -> None:
            return None

    transport = SuspendedTransport()
    provider = DeepSeekNarrativeProvider(
        DeepSeekSettings(
            api_key="offline-test-sentinel",
            max_retries=0,
            timeout_seconds=5.0,
            max_tokens=512,
        ),
            PromptBuilder(profiles=(default_style_profile(),)),
        transport=transport,
    )
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        task = asyncio.create_task(
            client.post(
                f"/v1/sessions/{session_id}/actions",
                json=view["action_affordances"]["suggested_actions"][0][
                    "submission"
                ],
            )
        )
        await asyncio.wait_for(entered.wait(), timeout=5)
        orchestrator = runtime.services.turn_orchestrator
        assert runtime.store.active_uows == 0
        assert not runtime.store.any_session_lock_held
        assert not orchestrator._bucket_lock.locked()
        assert not orchestrator._buckets[session_id].lock.locked()
        assert transport.calls == 1
        release.set()
        response = await asyncio.wait_for(task, timeout=5)
        assert response.status_code == 200, response.text
        assert transport.calls == 1
    finally:
        release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_follower_cancellation_does_not_cancel_the_owner_or_shared_signal(
    monkeypatch,
) -> None:
    provider = _GateProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    follower_entered = asyncio.Event()
    original_follow = DynamicNarrativeOrchestrator._follow

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = view["action_affordances"]["suggested_actions"][0]["submission"]
        owner = asyncio.create_task(
            client.post(f"/v1/sessions/{session_id}/actions", json=submission)
        )
        await provider.entered.wait()
        assert runtime.store.active_uows == 0
        follower = asyncio.create_task(
            runtime.services.turn_orchestrator.handle(
                ActionSubmission(session_id=session_id, **submission)
            )
        )
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        entry = runtime.services.turn_orchestrator._buckets[session_id].entries[
            submission["client_request_id"]
        ]
        assert not entry.completion.done()
        follower.cancel()
        with pytest.raises(asyncio.CancelledError):
            await follower
        assert follower.cancelled()
        assert not owner.done()
        assert not entry.completion.cancelled()
        provider.release.set()
        assert (await owner).status_code == 200
        assert provider.invocations == 1
        assert entry.completion.done()
        assert entry.completion.exception() is None
        replay = await client.post(
            f"/v1/sessions/{session_id}/actions", json=submission
        )
        assert replay.status_code == 200
        assert provider.invocations == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_same_view_different_requests_call_twice_but_publish_one_successor() -> None:
    provider = _GateProvider(expected=2)
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    try:
        submissions = [
            {
                "turn_id": f"free-race-turn-{index}",
                "client_request_id": f"free-race-request-{index}",
                "action_type": "CUSTOM",
                "description": f"Try distinct safe action {index}.",
            }
            for index in (1, 2)
        ]
        tasks = [
            asyncio.create_task(
                client.post(f"/v1/sessions/{session_id}/actions", json=submission)
            )
            for submission in submissions
        ]
        await provider.entered.wait()
        assert runtime.store.active_uows == 0
        provider.release.set()
        responses = await asyncio.gather(*tasks)
        assert sorted(response.status_code for response in responses) == [200, 409]
        assert provider.invocations == 2
        final = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        assert final["metadata"]["state_version"] == 1
        jobs = runtime.store.snapshot().narrative_jobs.values()
        assert sum(job.status.value == "COMMITTED" for job in jobs) == 1
        assert sum(job.status.value == "STALE" for job in jobs) == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_provider_failure_preserves_byte_identical_last_committed_view() -> None:
    runtime = build_dynamic_demo_runtime(
        environ={"DEVIATION_DEMO_DYNAMIC_FAKE_FAILURE_AT_ACTION": "1"}
    )
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    try:
        before = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = before["action_affordances"]["suggested_actions"][0]["submission"]
        failed = await client.post(
            f"/v1/sessions/{session_id}/actions", json=submission
        )
        assert failed.status_code == 409
        assert failed.json()["error"]["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        after = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        assert after == before
        assert runtime.provider.invocation_count == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_public_role_exact_value_is_declassified_but_public_title_is_not() -> None:
    def role_candidate(request):
        return _safe_candidate(
            request,
            narrative_text=(request.scenario_role.display_name + " 保持公开可见。") * 80,
        )

    allowed_provider = _GateProvider(candidate_factory=role_candidate)
    allowed_provider.release.set()
    allowed_runtime = build_dynamic_demo_runtime(provider=allowed_provider, environ={})
    allowed_runtime, allowed_client, allowed_session = await _entered_dynamic_client(
        allowed_runtime
    )
    try:
        response = await allowed_client.post(
            f"/v1/sessions/{allowed_session}/actions",
            json={
                "turn_id": "free-public-turn",
                "client_request_id": "free-public-request",
                "action_type": "CUSTOM",
                "description": "Use the public role only.",
            },
        )
        assert response.status_code == 200, response.text
    finally:
        await allowed_client.aclose()
        await allowed_runtime.aclose()

    def title_candidate(request):
        return _safe_candidate(
            request,
            narrative_text=(request.scenario_premise.title + "。") * 80,
        )

    rejected_provider = _GateProvider(candidate_factory=title_candidate)
    rejected_provider.release.set()
    rejected_runtime = build_dynamic_demo_runtime(provider=rejected_provider, environ={})
    rejected_runtime, rejected_client, rejected_session = await _entered_dynamic_client(
        rejected_runtime
    )
    try:
        response = await rejected_client.post(
            f"/v1/sessions/{rejected_session}/actions",
            json={
                "turn_id": "free-hidden-turn",
                "client_request_id": "free-hidden-request",
                "action_type": "CUSTOM",
                "description": "Try public prose without reference authority.",
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["error_code"] == "NARRATIVE_PROPOSAL_REJECTED"
        assert (
            await rejected_client.get(f"/v1/sessions/{rejected_session}/view")
        ).json()["metadata"]["state_version"] == 0
    finally:
        await rejected_client.aclose()
        await rejected_runtime.aclose()


@pytest.mark.asyncio
async def test_fact_ring_rolls_over_in_exact_twelve_slot_order() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        committed_keys: list[str] = []
        for action_index in range(15):
            view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
            response = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json=view["action_affordances"]["suggested_actions"][0]["submission"],
            )
            assert response.status_code == 200
            current = runtime.store.snapshot().snapshots[session_id].state[
                "scenario_runtime"
            ]["dynamic_facts"]
            title = current["dynamic.narrative.scene.title"]
            marker = title.removeprefix("Dynamic scene ")
            committed_keys.append(
                "manual.continuity.anchor"
                if action_index in {0, 13}
                else f"note.{marker}"
            )
        slots = runtime.store.snapshot().snapshots[session_id].state[
            "scenario_runtime"
        ]["dynamic_facts"]
        ring = {slots[key]["key"] for key in DYNAMIC_FACT_SLOTS}
        assert ring == set(committed_keys[-12:])
        latest_marker = committed_keys[-1].removeprefix("note.")
        assert tuple(slots[key] for key in DYNAMIC_SUGGESTION_SLOTS) == (
            f"Consider possibility alpha ({latest_marker}).",
            f"Consider possibility beta ({latest_marker}).",
            f"Consider possibility gamma ({latest_marker}).",
        )
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finite_hidden_extractor_records_scenario_catalog_runtime_run_and_job_sources() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        initial = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        committed = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json=initial["action_affordances"]["suggested_actions"][0]["submission"],
        )
        assert committed.status_code == 200
        current = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **current["action_affordances"]["suggested_actions"][0]["submission"],
        )
        resolved = await runtime.services.turn_orchestrator._resolve_attempt(submission)
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        binding = job.narrative_request["authority_binding"]
        assert len(binding["hidden_reference_digest"]) == 64
        assert len(binding["public_reference_digest"]) == 64
        records = _hidden_reference_index(
            resolved, job, runtime.services.turn_orchestrator.catalog
        )
        keys = tuple(record.source_key for record in records)
        assert keys[:6] == (
            "hidden:ScenarioDefinition:scenario.scenario_id",
            "hidden:ScenarioDefinition:scenario.content_version",
            "hidden:ScenarioDefinition:scenario.title",
            "hidden:ScenarioDefinition:scenario.summary",
            "hidden:ScenarioDefinition:scenario.initial_phase_id",
            "hidden:ScenarioDefinition:scenario.initial_location_id",
        )
        for family in (
            "hidden:FactEqualsCondition:scenario.",
            "hidden:DecisionWindowDefinition:scenario.decision_windows",
            "hidden:NarrativeIntentMatcher:scenario.narrative_outcome_rules",
            "hidden:ContentCatalog:catalog.content_version",
            "hidden:CharacterDefinition:catalog.characters",
            "hidden:NpcDefinition:catalog.npcs",
            "hidden:ItemDefinition:catalog.items",
            "hidden:GameSession:session.session_id",
            "hidden:CanonicalRun:run.run_id",
            "hidden:ScenarioRuntimeState:state.scenario_runtime",
            "hidden:NarrativeJob:job.job_id",
        ):
            assert any(key.startswith(family) for key in keys), family
        assert not any(".schema_version" in key for key in keys)
        assert not any("dynamic_facts" in key for key in keys)
        assert not any("narrative_request" in key for key in keys)
    finally:
        await client.aclose()
        await runtime.aclose()


def test_finite_hidden_extractor_traverses_all_six_catalog_collections() -> None:
    catalog = JsonContentCatalogLoader(
        Path(__file__).parents[2] / "config" / "demo_content_pack.json"
    ).load()
    keys = tuple(
        record.source_key for record in _catalog_hidden_references(catalog)
    )
    for family in (
        "hidden:CharacterDefinition:catalog.characters",
        "hidden:NpcDefinition:catalog.npcs",
        "hidden:ItemDefinition:catalog.items",
        "hidden:EquipmentDefinition:catalog.equipment",
        "hidden:SkillDefinition:catalog.skills",
        "hidden:AttributeModifierEffectDefinition:catalog.effects",
        "hidden:ResourceModifierEffectDefinition:catalog.effects",
    ):
        assert any(key.startswith(family) for key in keys), family


@pytest.mark.asyncio
async def test_multiple_owner_cancellations_settle_one_job_unknown_without_retry(
    monkeypatch,
) -> None:
    provider = _GateProvider()
    runtime = build_dynamic_demo_runtime(provider=provider, environ={})
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    follower_entered = asyncio.Event()
    original_follow = DynamicNarrativeOrchestrator._follow

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        owner = asyncio.create_task(
            runtime.services.turn_orchestrator.handle(submission)
        )
        await provider.entered.wait()
        assert runtime.store.active_uows == 0
        assert not runtime.store.any_session_lock_held
        assert not runtime.services.turn_orchestrator._bucket_lock.locked()
        assert not runtime.services.turn_orchestrator._buckets[session_id].lock.locked()
        follower = asyncio.create_task(
            runtime.services.turn_orchestrator.handle(submission)
        )
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        entry = runtime.services.turn_orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        assert not entry.completion.done()
        owner.cancel()
        owner.cancel()
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await asyncio.wait_for(follower, timeout=5)
        assert owner.cancelled()
        with pytest.raises(asyncio.CancelledError):
            owner.exception()
        assert provider.invocations == 1
        jobs = tuple(runtime.store.snapshot().narrative_jobs.values())
        assert len(jobs) == 1
        assert jobs[0].status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert jobs[0].attempt_count == 1
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None
        with pytest.raises(NarrativeOutcomeUnknownError):
            await runtime.services.turn_orchestrator.handle(submission)
        assert provider.invocations == 1
    finally:
        provider.release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_cancellation_after_publication_commit_before_ledger_marker_is_retained(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    entered = asyncio.Event()
    release = asyncio.Event()
    follower_entered = asyncio.Event()
    orchestrator = runtime.services.turn_orchestrator
    original_mark = DynamicNarrativeOrchestrator._mark_published
    original_follow = DynamicNarrativeOrchestrator._follow

    async def gated_mark(self, entry, token, job):
        entered.set()
        await release.wait()
        return await original_mark(self, entry, token, job)

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_mark_published", gated_mark)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(entered.wait(), timeout=5)
        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        assert entry.lifecycle is AttemptLifecycle.OWNER_RESERVED
        published = tuple(runtime.store.snapshot().narrative_jobs.values())
        assert len(published) == 1
        assert published[0].status is NarrativeJobStatus.PREPARED
        follower = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        owner.cancel()
        owner.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await asyncio.wait_for(follower, timeout=5)
        current = runtime.store.snapshot().narrative_jobs[published[0].job_id]
        assert current.status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert current.attempt_count == 1
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None
        assert owner.cancelled()
        assert runtime.provider.invocation_count == 0
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_publication_cancellation_baseline_is_captured_at_the_commit_boundary(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    add_entered = asyncio.Event()
    cancellation_observed = asyncio.Event()
    original_add = DemoNarrativeJobRepository.add

    async def add_with_preserved_outer_cancellation(self, job):
        await original_add(self, job)
        add_entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            # A repository/UoW await may own an earlier cancellation.  Preserve
            # its count so publication records it as the pre-commit baseline.
            cancellation_observed.set()

    monkeypatch.setattr(
        DemoNarrativeJobRepository, "add", add_with_preserved_outer_cancellation
    )
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(add_entered.wait(), timeout=5)
        owner.cancel()
        await asyncio.wait_for(cancellation_observed.wait(), timeout=5)
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)

        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert owner.cancelled()
        assert owner.cancelling() == 1
        with pytest.raises(asyncio.CancelledError):
            owner.exception()
        assert job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert job.attempt_count == 1
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None
        assert runtime.provider.invocation_count == 0
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_three_transient_stabilization_cas_failures_cannot_leave_public_pending(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    published = asyncio.Event()
    release = asyncio.Event()
    failed_cas = 0
    transition_attempts: list[NarrativeJobStatus] = []
    original_mark = DynamicNarrativeOrchestrator._mark_published
    original_replace = DemoNarrativeJobRepository.replace

    async def gated_mark(self, entry, token, job):
        result = await original_mark(self, entry, token, job)
        published.set()
        await release.wait()
        return result

    async def transient_replace(self, job, **kwargs):
        nonlocal failed_cas
        transition_attempts.append(job.status)
        if (
            job.status is NarrativeJobStatus.IN_PROGRESS
            and kwargs.get("expected_status") is NarrativeJobStatus.PREPARED
            and failed_cas < 3
        ):
            failed_cas += 1
            return False
        return await original_replace(self, job, **kwargs)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_mark_published", gated_mark)
    monkeypatch.setattr(DemoNarrativeJobRepository, "replace", transient_replace)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(published.wait(), timeout=5)
        owner.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)

        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert failed_cas == 3
        assert transition_attempts[:4] == [NarrativeJobStatus.IN_PROGRESS] * 4
        assert transition_attempts[-1] is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert job.attempt_count == 1
        assert job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and entry.completion.exception() is None
        assert runtime.provider.invocation_count == 0
        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json()["status"] == "OUTCOME_UNKNOWN"
        assert status.json()["client_action"] == "DO_NOT_RETRY"
        assert status.json()["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(submission)
        assert runtime.provider.invocation_count == 0
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_exhausted_bounded_stabilization_is_public_terminal_uncertainty(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    published = asyncio.Event()
    release = asyncio.Event()
    failed_cas = 0
    original_mark = DynamicNarrativeOrchestrator._mark_published
    original_replace = DemoNarrativeJobRepository.replace

    async def gated_mark(self, entry, token, job):
        result = await original_mark(self, entry, token, job)
        published.set()
        await release.wait()
        return result

    async def unavailable_cas(self, job, **kwargs):
        nonlocal failed_cas
        if (
            job.status is NarrativeJobStatus.IN_PROGRESS
            and kwargs.get("expected_status") is NarrativeJobStatus.PREPARED
        ):
            failed_cas += 1
            return False
        return await original_replace(self, job, **kwargs)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_mark_published", gated_mark)
    monkeypatch.setattr(DemoNarrativeJobRepository, "replace", unavailable_cas)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(published.wait(), timeout=5)
        owner.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)

        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert 3 < failed_cas < 20
        assert job.status is NarrativeJobStatus.PREPARED
        assert job.attempt_count == 0
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
        assert entry.completion.done() and entry.completion.exception() is None
        assert runtime.provider.invocation_count == 0

        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json()["status"] == "OUTCOME_UNKNOWN"
        assert status.json()["client_action"] == "DO_NOT_RETRY"
        assert status.json()["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(submission)
        assert runtime.provider.invocation_count == 0
    finally:
        release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "barrier",
    (
        "after_job_published",
        "before_claim_entry",
        "claim_uow_enter_suspended",
        "claim_commit_suspended",
        "claim_commit_returned",
        "before_provider_entry",
    ),
)
async def test_every_published_pre_provider_cancellation_barrier_is_durably_stable(
    barrier: str,
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    entered = asyncio.Event()
    release = asyncio.Event()
    follower_entered = asyncio.Event()
    status_trace: list[NarrativeJobStatus] = []
    original_claim = DynamicNarrativeOrchestrator._claim
    original_mark = DynamicNarrativeOrchestrator._mark_published
    original_follow = DynamicNarrativeOrchestrator._follow
    original_before_provider = DynamicNarrativeOrchestrator._before_provider_entry
    original_enter = DemoUnitOfWork.__aenter__
    original_commit = DemoUnitOfWork.commit
    claim_commit_gated = False
    claim_enter_gated = False
    request_id: str | None = None

    async def gated_mark(self, entry, token, job):
        result = await original_mark(self, entry, token, job)
        if barrier == "after_job_published":
            entered.set()
            await release.wait()
        return result

    async def gated_claim(self, job):
        if barrier == "before_claim_entry":
            entered.set()
            await release.wait()
        return await original_claim(self, job)

    async def gated_enter(self):
        nonlocal claim_enter_gated
        bucket = runtime.services.turn_orchestrator._buckets.get(session_id)
        entry = (
            None
            if bucket is None or request_id is None
            else bucket.entries.get(request_id)
        )
        current_jobs = tuple(runtime.store.snapshot().narrative_jobs.values())
        should_gate = (
            barrier == "claim_uow_enter_suspended"
            and not claim_enter_gated
            and entry is not None
            and entry.lifecycle is AttemptLifecycle.JOB_PUBLISHED
            and len(current_jobs) == 1
            and current_jobs[0].status is NarrativeJobStatus.PREPARED
        )
        if should_gate:
            claim_enter_gated = True
            entered.set()
            await release.wait()
        return await original_enter(self)

    async def gated_before_provider(self):
        if barrier == "before_provider_entry":
            entered.set()
            await release.wait()
        return await original_before_provider(self)

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    async def observed_commit(self):
        nonlocal claim_commit_gated
        is_claim = any(
            replacement.expected_status is NarrativeJobStatus.PREPARED
            for replacements in self._pending_job_replacements.values()
            for replacement in replacements
        )
        gate_this_claim = is_claim and not claim_commit_gated
        if gate_this_claim:
            claim_commit_gated = True
        if gate_this_claim and barrier == "claim_commit_suspended":
            entered.set()
            await release.wait()
        await original_commit(self)
        current_jobs = tuple(self._store.snapshot().narrative_jobs.values())
        if current_jobs:
            status_trace.append(current_jobs[-1].status)
        if gate_this_claim and barrier == "claim_commit_returned":
            entered.set()
            await release.wait()

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_mark_published", gated_mark)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_claim", gated_claim)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    monkeypatch.setattr(
        DynamicNarrativeOrchestrator, "_before_provider_entry", gated_before_provider
    )
    monkeypatch.setattr(DemoUnitOfWork, "__aenter__", gated_enter)
    monkeypatch.setattr(DemoUnitOfWork, "commit", observed_commit)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        request_id = wire["client_request_id"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(entered.wait(), timeout=5)
        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        assert entry.lifecycle is AttemptLifecycle.JOB_PUBLISHED
        follower = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        owner.cancel()
        if barrier == "after_job_published":
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await asyncio.wait_for(follower, timeout=5)

        jobs = tuple(runtime.store.snapshot().narrative_jobs.values())
        assert len(jobs) == 1
        assert jobs[0].status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert jobs[0].attempt_count == 1
        assert runtime.provider.invocation_count == 0
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None
        assert owner.cancelled()
        assert status_trace[-1] is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert NarrativeJobStatus.PREPARED in status_trace
        assert NarrativeJobStatus.IN_PROGRESS in status_trace

        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json() == {
            "session_id": session_id,
            "client_request_id": submission.client_request_id,
            "status": "OUTCOME_UNKNOWN",
            "client_action": "DO_NOT_RETRY",
            "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
            "retry_after_seconds": None,
            "response": None,
        }
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_post_commit_cancellation_signals_followers_then_replays_success(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    terminal_entered = asyncio.Event()
    terminal_release = asyncio.Event()
    follower_entered = asyncio.Event()
    original_terminal = DynamicNarrativeOrchestrator._terminal
    original_follow = DynamicNarrativeOrchestrator._follow

    async def gated_terminal(self, entry, token, state, *, error_code=None):
        if state is AttemptLifecycle.TERMINAL_AUTHORITATIVE:
            terminal_entered.set()
            await terminal_release.wait()
        return await original_terminal(
            self, entry, token, state, error_code=error_code
        )

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_terminal", gated_terminal)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        submission = ActionSubmission(
            session_id=session_id,
            **view["action_affordances"]["suggested_actions"][0]["submission"],
        )
        owner = asyncio.create_task(
            runtime.services.turn_orchestrator.handle(submission)
        )
        await terminal_entered.wait()
        assert runtime.store.snapshot().turn_requests
        follower = asyncio.create_task(
            runtime.services.turn_orchestrator.handle(submission)
        )
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        owner.cancel()
        owner.cancel()
        terminal_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        follower_response = await asyncio.wait_for(follower, timeout=5)
        assert follower_response.result_code == "DYNAMIC_NARRATIVE_COMMITTED"
        entry = runtime.services.turn_orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        assert entry.completion.done() and entry.completion.exception() is None
        replay = await runtime.services.turn_orchestrator.handle(submission)
        assert replay.result_code == "DYNAMIC_NARRATIVE_COMMITTED"
        assert replay.resulting_state_version == 1
        assert runtime.provider.invocation_count == 1
    finally:
        terminal_release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finalize_commit_preserves_cancellation_owned_before_its_baseline(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    before_baseline = asyncio.Event()
    cancellation_observed = asyncio.Event()
    commit_entered = asyncio.Event()
    commit_release = asyncio.Event()
    follower_entered = asyncio.Event()
    finalize_baselines: list[int] = []
    finalize_commit_calls = 0
    original_replace = DemoNarrativeJobRepository.replace
    original_commit = DemoUnitOfWork.commit
    original_follow = DynamicNarrativeOrchestrator._follow

    async def preserve_prebaseline_cancellation(self, job, **kwargs):
        if (
            job.status is NarrativeJobStatus.COMMITTED
            and kwargs.get("expected_status")
            is NarrativeJobStatus.PROPOSAL_VALIDATED
        ):
            before_baseline.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancellation_observed.set()
        return await original_replace(self, job, **kwargs)

    async def gated_commit(self):
        nonlocal finalize_commit_calls
        if _is_finalize_commit(self):
            finalize_commit_calls += 1
            owner = asyncio.current_task()
            assert owner is not None
            finalize_baselines.append(owner.cancelling())
            commit_entered.set()
            await commit_release.wait()
        await original_commit(self)

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(
        DemoNarrativeJobRepository,
        "replace",
        preserve_prebaseline_cancellation,
    )
    monkeypatch.setattr(DemoUnitOfWork, "commit", gated_commit)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(before_baseline.wait(), timeout=5)
        owner.cancel()
        await asyncio.wait_for(cancellation_observed.wait(), timeout=5)
        await asyncio.wait_for(commit_entered.wait(), timeout=5)
        assert finalize_baselines == [1]

        follower = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(follower_entered.wait(), timeout=5)
        commit_release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        follower_response = await asyncio.wait_for(follower, timeout=5)

        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert owner.cancelled()
        assert owner.cancelling() == 1
        assert finalize_commit_calls == 1
        assert job.status is NarrativeJobStatus.COMMITTED
        assert job.attempt_count == 1
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.result().state is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert follower_response.result_code == "DYNAMIC_NARRATIVE_COMMITTED"
        assert follower_response.resulting_state_version == 1
        assert runtime.provider.invocation_count == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1

        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json()["status"] == "COMMITTED"
        assert status.json()["client_action"] == "RESPONSE_AVAILABLE"
    finally:
        commit_release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finalize_retains_terminal_task_before_suspended_uow_exit(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    exit_entered = asyncio.Event()
    exit_release = asyncio.Event()
    exit_cancelled = asyncio.Event()
    terminal_entered = asyncio.Event()
    terminal_release = asyncio.Event()
    retained_wait_entered = asyncio.Event()
    follower_entered = asyncio.Event()
    finalize_uows: set[int] = set()
    retained_tasks: list[asyncio.Task[object]] = []
    finalize_baselines: list[int] = []
    protected_excess_at_wait: list[int] = []
    trace: list[str] = []
    follower_count = 0
    request_id: str | None = None
    original_commit = DemoUnitOfWork.commit
    original_exit = DemoUnitOfWork.__aexit__
    original_terminal = DynamicNarrativeOrchestrator._terminal
    original_await_retained = DynamicNarrativeOrchestrator._await_retained
    original_follow = DynamicNarrativeOrchestrator._follow

    async def observed_commit(self):
        if _is_finalize_commit(self):
            owner = asyncio.current_task()
            assert owner is not None
            finalize_baselines.append(owner.cancelling())
            trace.append("finalize_commit_enter")
            await original_commit(self)
            finalize_uows.add(id(self))
            trace.append("finalize_commit_return")
            return
        await original_commit(self)

    async def gated_terminal(self, entry, token, state, *, error_code=None):
        if (
            state is AttemptLifecycle.TERMINAL_AUTHORITATIVE
            and entry.submission.client_request_id == request_id
        ):
            current = asyncio.current_task()
            assert current is not None
            if current not in retained_tasks:
                retained_tasks.append(current)
            trace.append("retained_terminal_started")
            terminal_entered.set()
            await terminal_release.wait()
        return await original_terminal(
            self, entry, token, state, error_code=error_code
        )

    async def suspended_exit(self, exc_type, exc, traceback):
        if id(self) not in finalize_uows:
            return await original_exit(self, exc_type, exc, traceback)
        trace.append("finalize_exit_enter")
        candidates = tuple(
            task
            for task in asyncio.all_tasks()
            if getattr(task.get_coro(), "cr_code", None) is gated_terminal.__code__
        )
        assert len(candidates) == 1
        if candidates[0] not in retained_tasks:
            retained_tasks.append(candidates[0])
        trace.append("retained_terminal_observed")
        exit_entered.set()
        caught: asyncio.CancelledError | None = None
        try:
            await exit_release.wait()
        except asyncio.CancelledError as error:
            caught = error
            exit_cancelled.set()
        await original_exit(self, exc_type, exc, traceback)
        trace.append("finalize_exit_complete")
        if caught is not None:
            raise caught
        return None

    async def observed_await_retained(task, owner, baseline, cancellation_requested):
        if task in retained_tasks:
            protected_excess_at_wait.append(owner.cancelling() - baseline)
            trace.append("retained_wait_enter")
            retained_wait_entered.set()
        return await original_await_retained(
            task, owner, baseline, cancellation_requested
        )

    async def observed_follow(self, entry):
        nonlocal follower_count
        follower_count += 1
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DemoUnitOfWork, "commit", observed_commit)
    monkeypatch.setattr(DemoUnitOfWork, "__aexit__", suspended_exit)
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_terminal", gated_terminal)
    monkeypatch.setattr(
        DynamicNarrativeOrchestrator,
        "_await_retained",
        staticmethod(observed_await_retained),
    )
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        request_id = wire["client_request_id"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(exit_entered.wait(), timeout=5)
        await asyncio.wait_for(terminal_entered.wait(), timeout=5)

        retained = retained_tasks[0]
        assert retained is not owner
        assert not retained.done() and not retained.cancelled()
        assert runtime.store.active_uows == 1
        assert trace.index("finalize_commit_enter") < trace.index(
            "finalize_commit_return"
        ) < trace.index("finalize_exit_enter") < trace.index(
            "retained_terminal_observed"
        )
        follower = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(follower_entered.wait(), timeout=5)

        owner.cancel()
        owner.cancel()
        owner.cancel()
        await asyncio.wait_for(exit_cancelled.wait(), timeout=5)
        await asyncio.wait_for(retained_wait_entered.wait(), timeout=5)
        assert protected_excess_at_wait == [3]
        assert not retained.done() and not retained.cancelled()
        owner.cancel()
        owner.cancel()
        assert not retained.cancelled()
        terminal_release.set()

        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        follower_response = await asyncio.wait_for(follower, timeout=5)
        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert finalize_baselines == [0]
        assert owner.cancelled()
        assert owner.cancelling() == 0
        assert retained.done() and not retained.cancelled()
        assert retained.exception() is None
        assert runtime.store.active_uows == 0
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.result().state is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert job.status is NarrativeJobStatus.COMMITTED
        assert job.attempt_count == 1
        assert follower_count == 1
        assert follower_response.result_code == "DYNAMIC_NARRATIVE_COMMITTED"
        assert runtime.provider.invocation_count == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1
        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json()["status"] == "COMMITTED"
        assert status.json()["client_action"] == "RESPONSE_AVAILABLE"
    finally:
        exit_release.set()
        terminal_release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_cancellation_suspended_at_finalize_commit_reconciles_complete_old(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    commit_entered = asyncio.Event()
    commit_release = asyncio.Event()
    retained_wait_entered = asyncio.Event()
    follower_entered = asyncio.Event()
    finalize_baselines: list[int] = []
    protected_excess: list[int] = []
    retained_reconciliations: list[asyncio.Task[object]] = []
    finalize_commit_calls = 0
    original_commit = DemoUnitOfWork.commit
    original_await_retained = DynamicNarrativeOrchestrator._await_retained
    original_follow = DynamicNarrativeOrchestrator._follow

    async def suspended_commit(self):
        nonlocal finalize_commit_calls
        if _is_finalize_commit(self):
            finalize_commit_calls += 1
            owner = asyncio.current_task()
            assert owner is not None
            finalize_baselines.append(owner.cancelling())
            commit_entered.set()
            await commit_release.wait()
            raise AssertionError("cancelled finalize commit unexpectedly resumed")
        await original_commit(self)

    async def observed_await_retained(task, owner, baseline, cancellation_requested):
        if (
            getattr(task.get_coro(), "cr_code", None)
            is DynamicNarrativeOrchestrator._reconcile_finalize_boundary.__code__
        ):
            retained_reconciliations.append(task)
            protected_excess.append(owner.cancelling() - baseline)
            retained_wait_entered.set()
        return await original_await_retained(
            task, owner, baseline, cancellation_requested
        )

    async def observed_follow(self, entry):
        follower_entered.set()
        return await original_follow(self, entry)

    monkeypatch.setattr(DemoUnitOfWork, "commit", suspended_commit)
    monkeypatch.setattr(
        DynamicNarrativeOrchestrator,
        "_await_retained",
        staticmethod(observed_await_retained),
    )
    monkeypatch.setattr(DynamicNarrativeOrchestrator, "_follow", observed_follow)
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        submission = ActionSubmission(session_id=session_id, **wire)
        orchestrator = runtime.services.turn_orchestrator
        owner = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(commit_entered.wait(), timeout=5)
        entry = orchestrator._buckets[session_id].entries[
            submission.client_request_id
        ]
        follower = asyncio.create_task(orchestrator.handle(submission))
        await asyncio.wait_for(follower_entered.wait(), timeout=5)

        owner.cancel()
        await asyncio.wait_for(retained_wait_entered.wait(), timeout=5)
        retained = retained_reconciliations[0]
        assert finalize_baselines == [0]
        assert protected_excess == [1]
        assert not retained.cancelled()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(owner, timeout=5)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await asyncio.wait_for(follower, timeout=5)

        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert finalize_commit_calls == 1
        assert owner.cancelled()
        assert owner.cancelling() == 0
        assert retained.done() and not retained.cancelled()
        assert retained.exception() is None
        assert retained.result().classification is (
            _FinalizePublicationClass.COMPLETE_OLD
        )
        assert runtime.store.active_uows == 0
        assert runtime.store.snapshot().turn_requests == {}
        assert runtime.store.snapshot().snapshots[session_id].state_version == 0
        assert job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
        assert job.attempt_count == 1
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.result().state is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        assert runtime.provider.invocation_count == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1

        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert status.status_code == 200
        assert status.json()["status"] == "OUTCOME_UNKNOWN"
        assert status.json()["client_action"] == "DO_NOT_RETRY"
        assert status.json()["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        replay = await client.post(
            f"/v1/sessions/{session_id}/actions", json=wire
        )
        assert replay.status_code == 409
        assert replay.json()["error"]["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        assert runtime.provider.invocation_count == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        commit_release.set()
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finalize_classifier_proves_exact_complete_old_and_complete_new() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )
        old_result = await orchestrator._classify_finalize_publication(
            stored, resolved, submission, expectation
        )
        assert old_result.classification is _FinalizePublicationClass.COMPLETE_OLD
        response = await orchestrator._finalize(
            stored,
            resolved,
            submission,
            entry=entry,
            token=entry.owner_token,
        )
        new_result = await orchestrator._classify_finalize_publication(
            stored, resolved, submission, expectation
        )
        assert (
            new_result.classification is _FinalizePublicationClass.COMPLETE_NEW
        ), new_result.diagnostics
        assert new_result.response == response == expectation.successor_response
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    (
        "event_only",
        "response_only",
        "story_slots_only",
        "suggestion_mismatch",
        "presentation_mismatch",
        "non_fact_mismatch",
        "prose_mismatch",
        "job_state_old",
        "response_mismatch",
        "view_mismatch",
        "frame_mismatch",
        "missing_response",
        "expired_old_lease",
    ),
)
async def test_finalize_classifier_rejects_every_partial_publication_family(
    fault: str,
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )
        successor_faults = {
            "suggestion_mismatch",
            "presentation_mismatch",
            "non_fact_mismatch",
            "prose_mismatch",
            "job_state_old",
            "response_mismatch",
            "view_mismatch",
            "frame_mismatch",
            "missing_response",
        }
        if fault in successor_faults:
            await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
        if fault == "event_only":
            runtime.store._events.append(
                DomainEvent(
                    event_id="partial-event-only",
                    session_id=session_id,
                    turn_id=submission.turn_id,
                    sequence_no=stored.prepared_state_version + 2,
                    event_type="DynamicNarrativeTurnCommitted",
                    payload={"candidate_digest": "0" * 64},
                    occurred_at=datetime.now(timezone.utc),
                )
            )
        elif fault == "response_only":
            runtime.store._turn_requests[(session_id, submission.client_request_id)] = (
                PersistedTurnRequest(
                    turn_id=submission.turn_id,
                    action_signature=submission.action_signature(),
                    response=expectation.successor_response.to_persistence(),
                )
            )
        elif fault == "story_slots_only":
            current = runtime.store._snapshots[session_id]
            runtime.store._snapshots[session_id] = PersistedSnapshot(
                state_version=current.state_version,
                state=expectation.successor_snapshot,
            )
        elif fault == "suggestion_mismatch":
            current = runtime.store._snapshots[session_id]
            state = json.loads(json.dumps(current.state))
            state["scenario_runtime"]["dynamic_facts"][
                "dynamic.narrative.suggestion.00"
            ] = "A mismatched but structurally valid suggestion."
            runtime.store._snapshots[session_id] = PersistedSnapshot(
                state_version=current.state_version, state=state
            )
        elif fault in {"presentation_mismatch", "non_fact_mismatch"}:
            current = runtime.store._snapshots[session_id]
            state = json.loads(json.dumps(current.state))
            key = (
                "dynamic.narrative.scene.title"
                if fault == "presentation_mismatch"
                else "dynamic.narrative.result"
            )
            state["scenario_runtime"]["dynamic_facts"][key] = (
                "A contradictory committed scene"
                if fault == "presentation_mismatch"
                else "FAILURE"
            )
            runtime.store._snapshots[session_id] = PersistedSnapshot(
                state_version=current.state_version,
                state=state,
            )
        elif fault == "prose_mismatch":
            current_job = runtime.store._narrative_jobs[stored.job_id]
            runtime.store._narrative_jobs[stored.job_id] = current_job.model_copy(
                update={"accepted_narrative_text": "不" * 350}
            )
        elif fault == "job_state_old":
            runtime.store._narrative_jobs[stored.job_id] = stored
        elif fault == "response_mismatch":
            key = (session_id, submission.client_request_id)
            receipt = runtime.store._turn_requests[key]
            response_payload = dict(receipt.response)
            response_payload["narrative_text"] = "异" * 350
            runtime.store._turn_requests[key] = replace(
                receipt,
                response=response_payload,
            )
        elif fault in {"view_mismatch", "frame_mismatch"}:
            service = orchestrator.dynamic_session_service
            assert service is not None
            service_type = type(service)
            original_build = service_type._build_dynamic_view

            def mismatched_view(self, *args, **kwargs):
                current_view = original_build(self, *args, **kwargs)
                if fault == "view_mismatch":
                    return current_view.model_copy(
                        update={
                            "recent_narrative_texts": (
                                *current_view.recent_narrative_texts,
                                "A contradictory reconstructed View residue.",
                            )
                        }
                    )
                return current_view.model_copy(
                    update={
                        "narrative_frame": current_view.narrative_frame.model_copy(
                            update={"frame_id": "frame.dynamic.contradiction"}
                        )
                    }
                )

            monkeypatch.setattr(
                service_type,
                "_build_dynamic_view",
                mismatched_view,
            )
        elif fault == "missing_response":
            runtime.store._turn_requests.pop(
                (session_id, submission.client_request_id)
            )
        elif fault == "expired_old_lease":
            runtime.store._narrative_jobs[stored.job_id] = stored.model_copy(
                update={
                    "lease_expires_at": datetime(2000, 1, 1, tzinfo=timezone.utc)
                }
            )
        result = await orchestrator._classify_finalize_publication(
            stored, resolved, submission, expectation
        )
        assert result.classification is _FinalizePublicationClass.PARTIAL
        assert result.response is None
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    (
        "missing_participation",
        "missing_run",
        "missing_character",
        "impossible_version",
        "receipt_contradiction",
        "event_contradiction",
        "job_identity_contradiction",
    ),
)
async def test_finalize_classifier_identifies_impossible_authority(
    fault: str,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )
        if fault == "missing_participation":
            runtime.store._run_participations.pop(session_id)
        elif fault == "missing_run":
            runtime.store._run_current.pop(resolved.authority.run.run_id.value)
        elif fault == "missing_character":
            runtime.store._player_character_current.pop(
                resolved.authority.player_character.player_character_id.value
            )
        elif fault == "impossible_version":
            persisted = runtime.store._sessions[session_id]
            impossible_version = stored.prepared_state_version + 2
            runtime.store._sessions[session_id] = replace(
                persisted,
                session=replace(
                    persisted.session, state_version=impossible_version
                ),
            )
            snapshot = runtime.store._snapshots[session_id]
            runtime.store._snapshots[session_id] = PersistedSnapshot(
                state_version=impossible_version,
                state=snapshot.state,
            )
        else:
            await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
            if fault == "receipt_contradiction":
                key = (session_id, submission.client_request_id)
                receipt = runtime.store._turn_requests[key]
                runtime.store._turn_requests[key] = replace(
                    receipt,
                    action_signature="f" * 64,
                )
            elif fault == "event_contradiction":
                index = next(
                    index
                    for index, event in enumerate(runtime.store._events)
                    if event.session_id == session_id
                    and event.event_type == "DynamicNarrativeTurnCommitted"
                )
                event = runtime.store._events[index]
                runtime.store._events[index] = replace(
                    event,
                    payload={**event.payload, "candidate_digest": "f" * 64},
                )
            elif fault == "job_identity_contradiction":
                current_job = runtime.store._narrative_jobs[stored.job_id]
                runtime.store._narrative_jobs[stored.job_id] = current_job.model_copy(
                    update={"request_fingerprint": "f" * 64}
                )
        result = await orchestrator._classify_finalize_publication(
            stored, resolved, submission, expectation
        )
        assert result.classification is _FinalizePublicationClass.IMPOSSIBLE
        assert result.response is None
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_finalize_classifier_keeps_unreadable_repository_observation_unknown(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        (
            orchestrator,
            submission,
            resolved,
            _entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )

        async def unreadable(*_args, **_kwargs):
            raise OSError("test-only unreadable repository")

        monkeypatch.setattr(DemoNarrativeJobRepository, "get", unreadable)
        result = await orchestrator._classify_finalize_publication(
            stored, resolved, submission, expectation
        )
        assert result.classification is _FinalizePublicationClass.UNKNOWN
        assert result.response is None
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_partial_finalize_is_durable_public_terminal_uncertainty_without_resend(
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()

    async def publish_partial_then_fail(
        self, job, resolved, submission, *, entry, token
    ):
        del entry, token
        runtime.store._events.append(
            DomainEvent(
                event_id="partial-production-seam-event",
                session_id=session_id,
                turn_id=submission.turn_id,
                sequence_no=job.prepared_state_version + 2,
                event_type="DynamicNarrativeTurnCommitted",
                payload={"candidate_digest": "0" * 64},
                occurred_at=datetime.now(timezone.utc),
            )
        )
        raise OSError("test-only finalize publication uncertainty")

    monkeypatch.setattr(
        DynamicNarrativeOrchestrator, "_finalize", publish_partial_then_fail
    )
    try:
        view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        wire = view["action_affordances"]["suggested_actions"][0]["submission"]
        failed = await client.post(
            f"/v1/sessions/{session_id}/actions", json=wire
        )
        assert failed.status_code == 409
        assert failed.json() == {
            "error": {
                "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                "message": "Narrative turn cannot be committed",
            }
        }

        orchestrator = runtime.services.turn_orchestrator
        entry = orchestrator._buckets[session_id].entries[
            wire["client_request_id"]
        ]
        job = next(iter(runtime.store.snapshot().narrative_jobs.values()))
        assert job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
        assert job.attempt_count == 1
        assert job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
        assert entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None
        assert runtime.provider.invocation_count == 1

        status = await client.get(
            f"/v1/sessions/{session_id}/requests/{wire['client_request_id']}"
        )
        assert status.status_code == 200
        assert status.json() == {
            "session_id": session_id,
            "client_request_id": wire["client_request_id"],
            "status": "OUTCOME_UNKNOWN",
            "client_action": "DO_NOT_RETRY",
            "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
            "retry_after_seconds": None,
            "response": None,
        }
        replay = await client.post(
            f"/v1/sessions/{session_id}/actions", json=wire
        )
        assert replay.status_code == 409
        assert replay.json() == failed.json()
        assert runtime.provider.invocation_count == 1
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_class",
    tuple(_FinalizePublicationClass),
)
async def test_finalize_reconciliation_maps_all_five_classes_to_exact_terminal_outcomes(
    expected_class: _FinalizePublicationClass,
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    original_job_get = DemoNarrativeJobRepository.get
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expected_response = None
        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            expected_response = await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
        elif expected_class is _FinalizePublicationClass.PARTIAL:
            runtime.store._events.append(
                DomainEvent(
                    event_id="partial-reconciliation-event",
                    session_id=session_id,
                    turn_id=submission.turn_id,
                    sequence_no=stored.prepared_state_version + 2,
                    event_type="DynamicNarrativeTurnCommitted",
                    payload={"candidate_digest": "0" * 64},
                    occurred_at=datetime.now(timezone.utc),
                )
            )
        elif expected_class is _FinalizePublicationClass.IMPOSSIBLE:
            runtime.store._run_participations.pop(session_id)
        elif expected_class is _FinalizePublicationClass.UNKNOWN:
            async def unreadable(*_args, **_kwargs):
                raise OSError("test-only unreadable reconciliation")

            monkeypatch.setattr(DemoNarrativeJobRepository, "get", unreadable)

        result = await orchestrator._reconcile_finalize_boundary(
            stored,
            resolved,
            submission,
            entry=entry,
            token=entry.owner_token,
        )
        assert result.classification is expected_class
        current_job = runtime.store.snapshot().narrative_jobs[stored.job_id]
        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
            assert current_job.status is NarrativeJobStatus.COMMITTED
            assert await orchestrator._follow(entry) == expected_response
        elif expected_class is _FinalizePublicationClass.COMPLETE_OLD:
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
            assert current_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
            assert current_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
            with pytest.raises(NarrativeOutcomeUnknownError):
                await orchestrator._follow(entry)
        else:
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
            if expected_class in {
                _FinalizePublicationClass.IMPOSSIBLE,
                _FinalizePublicationClass.UNKNOWN,
            }:
                assert current_job.status is NarrativeJobStatus.PROPOSAL_VALIDATED
            if expected_class is _FinalizePublicationClass.UNKNOWN:
                monkeypatch.setattr(
                    DemoNarrativeJobRepository, "get", original_job_get
                )
            if expected_class is _FinalizePublicationClass.PARTIAL:
                assert current_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
                assert current_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
            with pytest.raises(NarrativeOutcomeUnknownError):
                await orchestrator._follow(entry)
            status = await client.get(
                f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
            )
            assert status.status_code == 200
            assert status.json()["status"] == "OUTCOME_UNKNOWN"
            assert status.json()["client_action"] == "DO_NOT_RETRY"
            assert status.json()["error_code"] == "NARRATIVE_OUTCOME_UNKNOWN"
        assert entry.completion.done() and not entry.completion.cancelled()
        assert runtime.provider.invocation_count == 0
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expected_class", "artifact_kind"),
    (
        (_FinalizePublicationClass.PARTIAL, "matching_response"),
        (_FinalizePublicationClass.IMPOSSIBLE, "contradictory_response"),
        (_FinalizePublicationClass.UNKNOWN, "unreadable_with_response"),
        (_FinalizePublicationClass.COMPLETE_NEW, "complete_new"),
        (_FinalizePublicationClass.COMPLETE_OLD, "complete_old"),
    ),
)
async def test_polling_resolves_finalize_authority_before_response_artifacts(
    expected_class: _FinalizePublicationClass,
    artifact_kind: str,
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    original_job_get = DemoNarrativeJobRepository.get
    unreadable_gets = 0
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )
        artifact_key = (session_id, submission.client_request_id)
        artifact: PersistedTurnRequest | None = None

        if artifact_kind in {
            "matching_response",
            "contradictory_response",
            "unreadable_with_response",
        }:
            artifact = PersistedTurnRequest(
                turn_id=submission.turn_id,
                action_signature=(
                    "f" * 64
                    if artifact_kind == "contradictory_response"
                    else submission.action_signature()
                ),
                response=expectation.successor_response.to_persistence(),
            )
            runtime.store._turn_requests[artifact_key] = artifact

        if artifact_kind == "unreadable_with_response":

            async def unreadable_twice(self, job_id, *, for_update=False):
                nonlocal unreadable_gets
                if job_id == stored.job_id and unreadable_gets < 2:
                    unreadable_gets += 1
                    raise OSError("test-only unreadable finalize observation")
                return await original_job_get(self, job_id, for_update=for_update)

            monkeypatch.setattr(
                DemoNarrativeJobRepository,
                "get",
                unreadable_twice,
            )

        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            response = await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
            classified = await orchestrator._classify_finalize_publication(
                stored, resolved, submission, expectation
            )
            assert classified.response == response == expectation.successor_response
        else:
            classified = await orchestrator._classify_finalize_publication(
                stored, resolved, submission, expectation
            )
            assert classified.response is None
            reconciled = await orchestrator._reconcile_finalize_boundary(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
            assert reconciled.classification is expected_class

        assert classified.classification is expected_class
        if artifact_kind == "unreadable_with_response":
            assert unreadable_gets == 2
            monkeypatch.setattr(
                DemoNarrativeJobRepository,
                "get",
                original_job_get,
            )

        snapshot = runtime.store.snapshot()
        current_job = snapshot.narrative_jobs[stored.job_id]
        assert len(snapshot.narrative_jobs) == 1
        assert current_job.attempt_count == 1
        assert runtime.provider.invocation_count == 0
        assert entry.completion.done() and not entry.completion.cancelled()
        assert entry.completion.exception() is None

        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            assert current_job.status is NarrativeJobStatus.COMMITTED
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
            assert entry.completion.result().state is (
                AttemptLifecycle.TERMINAL_AUTHORITATIVE
            )
            assert artifact_key in snapshot.turn_requests
        elif expected_class is _FinalizePublicationClass.COMPLETE_OLD:
            assert current_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
            assert current_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
            assert entry.completion.result().state is (
                AttemptLifecycle.TERMINAL_AUTHORITATIVE
            )
            assert artifact_key not in snapshot.turn_requests
        else:
            assert artifact is not None
            assert snapshot.turn_requests[artifact_key] == artifact
            assert current_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
            assert current_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
            completion = entry.completion.result()
            assert completion.state is AttemptLifecycle.TERMINAL_UNCERTAIN
            assert completion.error_code == "NARRATIVE_OUTCOME_UNKNOWN"

        public_status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert public_status.status_code == 200
        public_body = public_status.json()
        replay = await client.post(
            f"/v1/sessions/{session_id}/actions",
            json=submission.model_dump(mode="json", exclude={"session_id"}),
        )
        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            assert public_body["status"] == "COMMITTED"
            assert public_body["client_action"] == "RESPONSE_AVAILABLE"
            assert public_body["error_code"] is None
            assert public_body["response"]["result_code"] == (
                "DYNAMIC_NARRATIVE_COMMITTED"
            )
            assert replay.status_code == 200
            assert replay.json()["result_code"] == "DYNAMIC_NARRATIVE_COMMITTED"
        else:
            assert public_body == {
                "session_id": session_id,
                "client_request_id": submission.client_request_id,
                "status": "OUTCOME_UNKNOWN",
                "client_action": "DO_NOT_RETRY",
                "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                "retry_after_seconds": None,
                "response": None,
            }
            assert replay.status_code == 409
            assert replay.json() == {
                "error": {
                    "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                    "message": "Narrative turn cannot be committed",
                }
            }
        assert runtime.provider.invocation_count == 0
        final_snapshot = runtime.store.snapshot()
        assert len(final_snapshot.narrative_jobs) == 1
        assert final_snapshot.narrative_jobs[stored.job_id].attempt_count == 1
        if artifact is not None:
            assert final_snapshot.turn_requests[artifact_key] == artifact
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "expected_class",
    (
        _FinalizePublicationClass.PARTIAL,
        _FinalizePublicationClass.IMPOSSIBLE,
        _FinalizePublicationClass.UNKNOWN,
        _FinalizePublicationClass.COMPLETE_NEW,
    ),
)
async def test_finalize_commit_uncertainty_uses_one_retained_reconciliation(
    expected_class: _FinalizePublicationClass,
    monkeypatch,
) -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    original_commit = DemoUnitOfWork.commit
    original_job_get = DemoNarrativeJobRepository.get
    retained_reconciliations: list[asyncio.Task[object]] = []
    finalize_baselines: list[int] = []
    protected_excess: list[int] = []
    finalize_commit_calls = 0
    finalize_boundary_uncertain = False
    unknown_observation_failed = False
    try:
        (
            orchestrator,
            submission,
            resolved,
            entry,
            _request,
            stored,
        ) = await _prepared_dynamic_attempt(runtime, client, session_id)
        expectation = orchestrator._expected_finalize_publication(
            stored, resolved, submission
        )
        artifact_key = (session_id, submission.client_request_id)

        async def uncertain_commit(self):
            nonlocal finalize_commit_calls, finalize_boundary_uncertain
            if not _is_finalize_commit(self):
                return await original_commit(self)
            finalize_commit_calls += 1
            owner = asyncio.current_task()
            assert owner is not None
            finalize_baselines.append(owner.cancelling())
            if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
                await original_commit(self)
            elif expected_class in {
                _FinalizePublicationClass.PARTIAL,
                _FinalizePublicationClass.IMPOSSIBLE,
            }:
                runtime.store._turn_requests[artifact_key] = PersistedTurnRequest(
                    turn_id=submission.turn_id,
                    action_signature=(
                        "f" * 64
                        if expected_class is _FinalizePublicationClass.IMPOSSIBLE
                        else submission.action_signature()
                    ),
                    response=expectation.successor_response.to_persistence(),
                )
            finalize_boundary_uncertain = True
            raise OSError("test-only finalize commit result unavailable")

        async def unreadable_once_after_commit(self, job_id, *, for_update=False):
            nonlocal unknown_observation_failed
            if (
                expected_class is _FinalizePublicationClass.UNKNOWN
                and finalize_boundary_uncertain
                and not unknown_observation_failed
                and job_id == stored.job_id
            ):
                unknown_observation_failed = True
                raise OSError("test-only unreadable reconciliation observation")
            return await original_job_get(self, job_id, for_update=for_update)

        original_await_retained = DynamicNarrativeOrchestrator._await_retained

        async def observed_await_retained(
            task, owner, baseline, cancellation_requested
        ):
            if (
                getattr(task.get_coro(), "cr_code", None)
                is DynamicNarrativeOrchestrator._reconcile_finalize_boundary.__code__
            ):
                retained_reconciliations.append(task)
                protected_excess.append(owner.cancelling() - baseline)
            return await original_await_retained(
                task, owner, baseline, cancellation_requested
            )

        monkeypatch.setattr(DemoUnitOfWork, "commit", uncertain_commit)
        monkeypatch.setattr(
            DemoNarrativeJobRepository,
            "get",
            unreadable_once_after_commit,
        )
        monkeypatch.setattr(
            DynamicNarrativeOrchestrator,
            "_await_retained",
            staticmethod(observed_await_retained),
        )

        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            response = await orchestrator._finalize(
                stored,
                resolved,
                submission,
                entry=entry,
                token=entry.owner_token,
            )
            assert response == expectation.successor_response
        else:
            with pytest.raises(NarrativeOutcomeUnknownError):
                await orchestrator._finalize(
                    stored,
                    resolved,
                    submission,
                    entry=entry,
                    token=entry.owner_token,
                )

        assert finalize_commit_calls == 1
        assert finalize_baselines == [0]
        assert protected_excess == [0]
        assert len(retained_reconciliations) == 1
        retained = retained_reconciliations[0]
        assert retained.done() and not retained.cancelled()
        assert retained.exception() is None
        assert retained.result().classification is expected_class
        if expected_class is _FinalizePublicationClass.UNKNOWN:
            assert unknown_observation_failed

        current_job = runtime.store.snapshot().narrative_jobs[stored.job_id]
        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            assert current_job.status is NarrativeJobStatus.COMMITTED
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_AUTHORITATIVE
        else:
            assert current_job.status is NarrativeJobStatus.OUTCOME_UNKNOWN
            assert current_job.error_code == "NARRATIVE_OUTCOME_UNKNOWN"
            assert entry.lifecycle is AttemptLifecycle.TERMINAL_UNCERTAIN
        assert entry.completion.done() and not entry.completion.cancelled()
        assert runtime.provider.invocation_count == 0
        assert len(runtime.store.snapshot().narrative_jobs) == 1

        public_status = await client.get(
            f"/v1/sessions/{session_id}/requests/{submission.client_request_id}"
        )
        assert public_status.status_code == 200
        if expected_class is _FinalizePublicationClass.COMPLETE_NEW:
            assert public_status.json()["status"] == "COMMITTED"
            assert public_status.json()["client_action"] == "RESPONSE_AVAILABLE"
        else:
            assert public_status.json()["status"] == "OUTCOME_UNKNOWN"
            assert public_status.json()["client_action"] == "DO_NOT_RETRY"
            assert public_status.json()["error_code"] == (
                "NARRATIVE_OUTCOME_UNKNOWN"
            )
        assert runtime.provider.invocation_count == 0
        assert len(runtime.store.snapshot().narrative_jobs) == 1
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_manual_fake_eight_submission_sequence_recovers_and_continues(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime = build_dynamic_demo_runtime(
        environ={
            "DEVIATION_DEMO_DYNAMIC_PROVIDER": "fake",
            "DEVIATION_DEMO_DYNAMIC_FAKE_FAILURE_AT_ACTION": "5",
        }
    )
    runtime, client, session_id = await _entered_dynamic_client(runtime)
    submitted_bodies: list[dict[str, object]] = []

    async def current_view() -> httpx.Response:
        response = await client.get(f"/v1/sessions/{session_id}/view")
        assert response.status_code == 200
        return response

    async def submit_suggestion(index: int) -> httpx.Response:
        view = (await current_view()).json()
        body = view["action_affordances"]["suggested_actions"][index]["submission"]
        submitted_bodies.append(body)
        return await client.post(f"/v1/sessions/{session_id}/actions", json=body)

    async def submit_custom(item: int, description: str) -> httpx.Response:
        body: dict[str, object] = {
            "turn_id": f"manual-fake-turn-{item}",
            "client_request_id": f"manual-fake-request-{item}",
            "action_type": "CUSTOM",
            "description": description,
        }
        submitted_bodies.append(body)
        return await client.post(f"/v1/sessions/{session_id}/actions", json=body)

    try:
        versions = [(await current_view()).json()["metadata"]["state_version"]]

        first = await submit_suggestion(0)
        assert first.status_code == 200
        assert first.json()["resulting_state_version"] == 1
        assert first.json()["narrative_text"].startswith(
            "A visible amber marker appears beside the sealed doorway."
        )
        versions.append((await current_view()).json()["metadata"]["state_version"])

        second = await submit_custom(
            2,
            "Examine the visible floor markings without touching anything.",
        )
        assert second.status_code == 200
        assert second.json()["resulting_state_version"] == 2
        versions.append((await current_view()).json()["metadata"]["state_version"])

        third = await submit_suggestion(1)
        assert third.status_code == 200
        assert third.json()["resulting_state_version"] == 3
        versions.append((await current_view()).json()["metadata"]["state_version"])

        fourth = await submit_custom(
            4,
            "Wait quietly and compare the current scene with the last visible change.",
        )
        assert fourth.status_code == 200
        assert fourth.json()["resulting_state_version"] == 4
        item_four_view = await current_view()
        item_four_bytes = item_four_view.content
        versions.append(item_four_view.json()["metadata"]["state_version"])

        fifth = await submit_custom(5, "Pause and listen for changes in the room.")
        assert fifth.status_code == 409
        assert fifth.json() == {
            "error": {
                "error_code": "NARRATIVE_OUTCOME_UNKNOWN",
                "message": "Narrative turn cannot be committed",
            }
        }
        recovered = await current_view()
        assert recovered.content == item_four_bytes
        versions.append(recovered.json()["metadata"]["state_version"])

        sixth = await submit_suggestion(2)
        assert sixth.status_code == 200
        assert sixth.json()["resulting_state_version"] == 5
        versions.append((await current_view()).json()["metadata"]["state_version"])

        seventh = await submit_custom(
            7,
            "Follow the earlier visible change and check what it now affects.",
        )
        assert seventh.status_code == 200
        assert seventh.json()["resulting_state_version"] == 6
        versions.append((await current_view()).json()["metadata"]["state_version"])

        eighth = await submit_suggestion(0)
        assert eighth.status_code == 200
        assert eighth.json()["resulting_state_version"] == 7
        final_view = await current_view()
        assert final_view.json()["metadata"]["state_version"] == 7
        assert final_view.json()["presentation"]["scene_summary"] == (
            "The visible amber marker established earlier now identifies the route forward."
        )
        versions.append(final_view.json()["metadata"]["state_version"])

        assert versions == [0, 1, 2, 3, 4, 4, 5, 6, 7]
        assert len(submitted_bodies) == 8
        assert submitted_bodies[0]["description"] == "Observe the surroundings."
        assert submitted_bodies[2]["description"] != submitted_bodies[0]["description"]
        assert submitted_bodies[5]["description"] != submitted_bodies[4]["description"]
        snapshot = runtime.store.snapshot()
        jobs = tuple(snapshot.narrative_jobs.values())
        assert len(jobs) == 8
        assert sum(job.status is NarrativeJobStatus.COMMITTED for job in jobs) == 7
        assert sum(job.status is NarrativeJobStatus.OUTCOME_UNKNOWN for job in jobs) == 1
        assert len(snapshot.turn_requests) == 7
        assert runtime.provider.invocation_count == 8
        assert capsys.readouterr().out.splitlines() == [
            "DNVS_FAKE_EVIDENCE event=reset cumulative_invocations=0",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=1 outcome=SUCCESS cumulative_invocations=1",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=2 outcome=SUCCESS cumulative_invocations=2",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=3 outcome=SUCCESS cumulative_invocations=3",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=4 outcome=SUCCESS cumulative_invocations=4",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=5 outcome=INTENTIONAL_FAILURE cumulative_invocations=5",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=6 outcome=SUCCESS cumulative_invocations=6",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=7 outcome=SUCCESS cumulative_invocations=7",
            "DNVS_FAKE_EVIDENCE event=invocation ordinal=8 outcome=SUCCESS cumulative_invocations=8",
        ]
    finally:
        await client.aclose()
        await runtime.aclose()


@pytest.mark.asyncio
async def test_offline_fake_submits_exactly_510_dynamic_turns_without_termination() -> None:
    runtime, client, session_id = await _entered_dynamic_client()
    try:
        observed_results: set[str] = set()
        observed_continuations: set[str] = set()
        for expected_version in range(1, 511):
            view_response = await client.get(f"/v1/sessions/{session_id}/view")
            assert view_response.status_code == 200
            view = view_response.json()
            assert view["scenario_status"] == "ACTIVE"
            suggestion = view["action_affordances"]["suggested_actions"][0]
            committed = await client.post(
                f"/v1/sessions/{session_id}/actions",
                json=suggestion["submission"],
            )
            assert committed.status_code == 200, committed.text
            assert committed.json()["resulting_state_version"] == expected_version
            observed_results.add(
                committed.json()["feedback_parameters"]["outcome_result"]
            )
            current_slots = runtime.store.snapshot().snapshots[session_id].state[
                "scenario_runtime"
            ]["dynamic_facts"]
            observed_continuations.add(
                current_slots["dynamic.narrative.continuation"]
            )
        final_view = (await client.get(f"/v1/sessions/{session_id}/view")).json()
        assert final_view["metadata"]["state_version"] == 510
        assert final_view["scenario_status"] == "ACTIVE"
        assert len(final_view["action_affordances"]["suggested_actions"]) == 3
        assert runtime.provider.invocation_count == 510
        assert observed_results == {"SUCCESS", "AMBIGUOUS", "FAILURE", "NO_EFFECT"}
        assert observed_continuations == {"CONTINUE", "TERMINAL"}
        snapshot = runtime.store.snapshot().snapshots[session_id].state
        assert len(snapshot["scenario_runtime"]["dynamic_facts"]) == 20
        assert snapshot["scenario_runtime"]["dynamic_facts"][
            "dynamic.narrative.continuation"
        ] in {"CONTINUE", "TERMINAL"}
    finally:
        await client.aclose()
        await runtime.aclose()
