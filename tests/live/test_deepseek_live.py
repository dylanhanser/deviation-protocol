from __future__ import annotations

import os

import pytest

from deviation_protocol.application.narrative_models import (
    NarrativeBoundaryError,
    NarrativePlayerIntent,
    NarrativePublicReferences,
    NarrativeRequest,
)
from deviation_protocol.application.narrative_prompt import (
    PromptBuilder,
    default_style_profile,
)
from deviation_protocol.application.narrative_validation import NarrativeProposalValidator
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.narrative import NarrativeFrame, NpcKnowledgeFrame, RenderableFact
from deviation_protocol.domain.scenario import FrameMode
from deviation_protocol.infrastructure.deepseek_narrative import (
    DeepSeekNarrativeProvider,
    DeepSeekSettings,
    OFFICIAL_DEEPSEEK_BASE_URL,
)


LIVE_ENABLED = (
    os.environ.get("RUN_LIVE_DEEPSEEK_TEST") == "1"
    and "DEEPSEEK_API_KEY" in os.environ
)


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE_ENABLED,
    reason="requires RUN_LIVE_DEEPSEEK_TEST=1 and process DEEPSEEK_API_KEY",
)
@pytest.mark.asyncio
async def test_one_safe_deepseek_v4_flash_narrative_smoke() -> None:
    """One explicit call, no MySQL, no raw provider failure or response reporting."""

    loaded = DeepSeekSettings.from_environment()
    settings = DeepSeekSettings(
        api_key=loaded.api_key,
        base_url=OFFICIAL_DEEPSEEK_BASE_URL,
        model="deepseek-v4-flash",
        timeout_seconds=min(loaded.timeout_seconds, 30.0),
        max_tokens=800,
        max_retries=0,
        backoff_base_seconds=0.0,
    )
    visible_npc = "npc.runtime.smoke"
    location = "location.smoke"
    frame = NarrativeFrame(
        frame_id="frame.smoke",
        scenario_id="scenario.smoke",
        phase_id="phase.opening",
        mode=FrameMode.FLOW,
        current_location_id=location,
        must_render_facts=(
            RenderableFact(fact_id="public.fact.awake", value=True),
        ),
        visible_entities=(visible_npc,),
        npc_knowledge=(
            NpcKnowledgeFrame(
                npc_id=visible_npc,
                npc_definition_id="npc.definition.smoke",
                known_facts=(
                    RenderableFact(fact_id="public.fact.awake", value=True),
                ),
            ),
        ),
        tone_hints=("restrained", "clear"),
        target_length=220,
        min_length=100,
        max_length=500,
        decision_required=False,
        stop_condition="CONTINUE",
    )
    request = NarrativeRequest(
        frame=frame,
        player_intent=NarrativePlayerIntent(
            action_type=ActionType.OBSERVE,
            description="观察眼前公开可见的人和环境",
            target_ids=(visible_npc,),
        ),
        public_story_summary="你刚刚恢复清醒，只能确认眼前公开可见的环境。",
        style_profile_id="original-zh-second-person-v1",
    )
    references = NarrativePublicReferences(
        allowed_public_entity_ids=frozenset({visible_npc, location}),
        visible_runtime_npc_ids=frozenset({visible_npc}),
    )
    provider = DeepSeekNarrativeProvider(
        settings,
        PromptBuilder(profiles=(default_style_profile(),)),
    )
    try:
        candidate = await provider.generate(request)
        validated = NarrativeProposalValidator().validate(
            candidate,
            request=request,
            public_references=references,
        )
    except NarrativeBoundaryError as exc:
        pytest.fail(exc.code, pytrace=False)
    except Exception:
        pytest.fail("LIVE_DEEPSEEK_SMOKE_FAILED", pytrace=False)
    finally:
        await provider.aclose()

    print(validated.proposal.narrative_text)
    print(validated.provider_metadata.model)
    print(validated.provider_metadata.finish_reason)
    print(validated.usage.model_dump(mode="json"))
