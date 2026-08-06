from __future__ import annotations

import os

import pytest

from deviation_protocol.application.dynamic_narrative_models import (
    DynamicCurrentScene,
    DynamicNarrativeLength,
    DynamicNarrativeRequest,
    DynamicPlayerAction,
    DynamicScenarioPremise,
    DynamicScenarioRole,
    DynamicSelectedPlayerCharacter,
)
from deviation_protocol.application.narrative_models import NarrativeBoundaryError
from deviation_protocol.application.narrative_prompt import PromptBuilder
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
async def test_one_safe_deepseek_dynamic_narrative_smoke() -> None:
    """Exactly one separately authorized call; no retry, browser, or MySQL."""

    loaded = DeepSeekSettings.from_environment()
    settings = DeepSeekSettings(
        api_key=loaded.api_key,
        base_url=OFFICIAL_DEEPSEEK_BASE_URL,
        model="deepseek-v4-flash",
        timeout_seconds=min(loaded.timeout_seconds, 30.0),
        max_tokens=1_200,
        max_retries=0,
        backoff_base_seconds=0.0,
    )
    request = DynamicNarrativeRequest(
        scenario_premise=DynamicScenarioPremise(
            title="公开测试场景", hook="只延续当前公开可见的测试情境。"
        ),
        selected_player_character=DynamicSelectedPlayerCharacter(
            contract_version="structured-player-character/v1", lifecycle="active"
        ),
        scenario_role=DynamicScenarioRole(
            display_name="调查者", description="谨慎观察并选择公开行动。"
        ),
        current_scene=DynamicCurrentScene(
            title="安静的房间", summary="你只能确认眼前公开可见的环境。"
        ),
        player_action=DynamicPlayerAction(description="观察房间中的光线变化。"),
        narrative_length=DynamicNarrativeLength(
            minimum=350, target=650, maximum=900
        ),
    )
    provider = DeepSeekNarrativeProvider(settings, PromptBuilder())
    try:
        candidate = await provider.generate_dynamic(request)
    except NarrativeBoundaryError as exc:
        pytest.fail(exc.code, pytrace=False)
    except Exception:
        pytest.fail("LIVE_DYNAMIC_DEEPSEEK_SMOKE_FAILED", pytrace=False)
    finally:
        await provider.aclose()

    assert candidate.provider_metadata.attempts == 1
    assert candidate.candidate.schema_version == "dynamic-narrative-candidate-v1"
    print(f"model={settings.model}")
    print(f"latency_ms={candidate.provider_metadata.latency_ms}")
    print("schema_valid=true")
    print(f"finish_reason={candidate.provider_metadata.finish_reason}")
