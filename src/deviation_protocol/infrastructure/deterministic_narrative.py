from __future__ import annotations

from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    NarrativeProposalRejectedError,
    NarrativeProviderMetadata,
    NarrativeRequest,
    NarrativeUsage,
    SelectedNarrativeOutcome,
    UntrustedNarrativeProposal,
)


_DEMO_SENTENCE = "这是仅依据当前公开行动生成的本地确定性叙事。"


class DeterministicDemoNarrativeProvider:
    """Generic, secrets-free Provider for the isolated deterministic Demo."""

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        try:
            candidate = request.outcome_candidates[0]
            result = candidate.allowed_results[0]
            referenced_entity_ids = candidate.allowed_entity_ids[:1]
            if referenced_entity_ids and referenced_entity_ids[0] not in _player_exposed_ids(
                request
            ):
                raise NarrativeProposalRejectedError()
            narrative_text = _bounded_demo_text(
                candidate.safe_description,
                target_length=request.frame.target_length,
                min_length=request.frame.min_length,
                max_length=request.frame.max_length,
            )
            proposal = NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text=narrative_text,
                referenced_entity_ids=referenced_entity_ids,
                npc_utterances=(),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=result,
                    referenced_entity_ids=referenced_entity_ids,
                ),
                continuity_notes=(),
            )
            return UntrustedNarrativeProposal(
                proposal=proposal,
                provider_metadata=NarrativeProviderMetadata(
                    provider="deterministic-demo",
                    model="deterministic-demo-v1",
                    request_id=None,
                    finish_reason="stop",
                    attempts=1,
                    latency_ms=0,
                ),
                usage=NarrativeUsage(),
            )
        except NarrativeProposalRejectedError:
            raise
        except (AttributeError, IndexError, TypeError, ValueError):
            raise NarrativeProposalRejectedError() from None

    async def aclose(self) -> None:
        return None


def _player_exposed_ids(request: NarrativeRequest) -> frozenset[str]:
    values = {
        *request.frame.visible_entities,
        *request.frame.visible_clues,
        request.frame.current_location_id,
        *request.player_intent.target_ids,
        *request.player_intent.tool_ids,
    }
    if request.player_intent.item_instance_id is not None:
        values.add(request.player_intent.item_instance_id)
    return frozenset(values)


def _bounded_demo_text(
    safe_description: str,
    *,
    target_length: int,
    min_length: int,
    max_length: int,
) -> str:
    unit = f"{_DEMO_SENTENCE}{safe_description}"
    if (
        not unit
        or target_length < len(unit)
        or not min_length <= target_length <= max_length
    ):
        raise NarrativeProposalRejectedError()
    repetitions = (target_length + len(unit) - 1) // len(unit)
    text = (unit * repetitions)[:target_length]
    if len(text) != target_length or not min_length <= len(text) <= max_length:
        raise NarrativeProposalRejectedError()
    return text
