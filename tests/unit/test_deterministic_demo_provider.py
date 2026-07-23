from __future__ import annotations

import os
from pathlib import Path
import random
import socket
import time

import pytest

from deviation_protocol.application.narrative_models import (
    NarrativeOutcomeCandidate,
    NarrativePlayerIntent,
    NarrativeProposalRejectedError,
    NarrativeRequest,
)
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.domain.scenario import FrameMode
from deviation_protocol.infrastructure.deterministic_narrative import (
    DeterministicDemoNarrativeProvider,
)


def _request(
    *,
    target_length: int = 120,
    visible_entity: str = "npc.visible",
    candidate_entity: str | None = "npc.visible",
    candidates: tuple[NarrativeOutcomeCandidate, ...] | None = None,
) -> NarrativeRequest:
    frame = NarrativeFrame(
        frame_id="frame.public",
        scenario_id="scenario.public",
        phase_id="phase.public",
        mode=FrameMode.FLOW,
        current_location_id="location.public",
        visible_entities=(visible_entity,),
        target_length=target_length,
        min_length=target_length,
        max_length=target_length,
        decision_required=False,
        stop_condition="CONTINUE",
    )
    default_candidates = (
        NarrativeOutcomeCandidate(
            outcome_token="outcome." + "a" * 48,
            safe_description="当前公开行动产生了可复核的有限结果。",
            allowed_results=(
                NarrativeOutcomeResult.SUCCESS,
                NarrativeOutcomeResult.AMBIGUOUS,
            ),
            allowed_entity_ids=(candidate_entity,) if candidate_entity else (),
        ),
        NarrativeOutcomeCandidate(
            outcome_token="outcome." + "b" * 48,
            safe_description="不得选择的后续候选。",
            allowed_results=(NarrativeOutcomeResult.FAILURE,),
        ),
    )
    return NarrativeRequest(
        frame=frame,
        player_intent=NarrativePlayerIntent(
            action_type=ActionType.OBSERVE,
            description="复核当前公开状态",
        ),
        style_profile_id="style.public",
        outcome_candidates=default_candidates if candidates is None else candidates,
    )


@pytest.mark.asyncio
async def test_provider_is_pure_selects_first_candidate_and_emits_fixed_metadata() -> None:
    provider = DeterministicDemoNarrativeProvider()
    request = _request()

    first = await provider.generate(request)
    second = await provider.generate(
        NarrativeRequest.model_validate(request.model_dump(mode="python"))
    )

    assert first == second
    assert len(first.proposal.narrative_text) == request.frame.target_length
    assert first.proposal.referenced_entity_ids == ("npc.visible",)
    assert first.proposal.npc_utterances == ()
    assert first.proposal.continuity_notes == ()
    assert first.proposal.selected_outcome is not None
    assert first.proposal.selected_outcome.outcome_token == "outcome." + "a" * 48
    assert first.proposal.selected_outcome.result is NarrativeOutcomeResult.SUCCESS
    assert first.proposal.selected_outcome.referenced_entity_ids == ("npc.visible",)
    assert first.provider_metadata.model_dump(mode="json") == {
        "provider": "deterministic-demo",
        "model": "deterministic-demo-v1",
        "request_id": None,
        "finish_reason": "stop",
        "attempts": 1,
        "latency_ms": 0,
    }
    assert all(value is None for value in first.usage.model_dump().values())
    await provider.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "narrative_request",
    (
        _request(candidates=()),
        _request(visible_entity="npc.visible", candidate_entity="npc.hidden"),
        _request(target_length=5),
    ),
    ids=("missing-candidate", "non-public-reference", "impossible-length"),
)
async def test_provider_fails_closed_with_exact_boundary_error(
    narrative_request: NarrativeRequest,
) -> None:
    provider = DeterministicDemoNarrativeProvider()

    with pytest.raises(NarrativeProposalRejectedError) as raised:
        await provider.generate(narrative_request)

    assert type(raised.value) is NarrativeProposalRejectedError
    assert str(raised.value) == "NARRATIVE_PROPOSAL_REJECTED"


@pytest.mark.asyncio
async def test_provider_does_not_read_environment_time_random_filesystem_or_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _request()

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("deterministic Provider attempted external input")

    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(random, "random", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)

    proposal = await DeterministicDemoNarrativeProvider().generate(request)

    assert proposal.provider_metadata.provider == "deterministic-demo"
