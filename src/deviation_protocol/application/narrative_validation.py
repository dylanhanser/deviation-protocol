from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
    NarrativePublicReferences,
    NarrativeRequest,
    NpcReactionProposal,
    PerceptibleOutcomeProposal,
    UntrustedNarrativeProposal,
    ValidatedNarrativeProposal,
)


_INTERNAL_TEXT_MARKERS = (
    "action_signature",
    "state_version",
    "client_request_id",
    "turn_id",
    "trustedscenarioeventissuer",
    "trusted_scenario_event_issuer",
    "verifiedscenarioevent",
    "verified_scenario_event",
    "domaineventdraft",
    "domain_event_draft",
    "capability",
    "event_seal",
    "event seal",
    "policy_trace",
    "anomaly_route",
    "grant_item",
    "grant item",
    "clock_delta",
    "beat_delta",
    "phase_delta",
    "fact_update",
    "clue_update",
    "currency_delta",
    "resource_delta",
    "attribute_delta",
    "skill_grant",
    "anomaly_evaluation_required",
    "api_key",
    "authorization",
)
_INTERNAL_ID_PATTERN = re.compile(
    r"\b(?:frame|scenario|phase|decision|fact|clue|event|seal|capability|npc|"
    r"location|item|skill|clock|resource|currency|attribute|choice)\."
    r"[A-Za-z0-9_.:-]+",
    re.IGNORECASE,
)
_LONG_SECRET_SHAPE = re.compile(r"\b[0-9a-f]{48,}\b", re.IGNORECASE)


class NarrativeProposalValidator:
    """Validate model output without issuing events or touching mutable state."""

    def validate(
        self,
        untrusted: UntrustedNarrativeProposal,
        *,
        request: NarrativeRequest,
        public_references: NarrativePublicReferences,
    ) -> ValidatedNarrativeProposal:
        try:
            self._validate(
                untrusted,
                request=request,
                public_references=public_references,
            )
        except NarrativeProposalRejectedError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            raise NarrativeProposalRejectedError() from None

        # Re-validate a JSON-mode deep copy. No nested object from the provider or
        # request is shared with the validated candidate.
        return ValidatedNarrativeProposal.model_validate_json(
            untrusted.model_dump_json()
        )

    def _validate(
        self,
        untrusted: UntrustedNarrativeProposal,
        *,
        request: NarrativeRequest,
        public_references: NarrativePublicReferences,
    ) -> None:
        proposal = untrusted.proposal
        frame = request.frame
        if not frame.min_length <= len(proposal.narrative_text) <= frame.max_length:
            raise NarrativeProposalRejectedError()

        player_exposed_ids = {
            *frame.visible_entities,
            *frame.visible_clues,
            frame.current_location_id,
            *request.player_intent.target_ids,
            *request.player_intent.tool_ids,
        }
        if request.player_intent.item_instance_id is not None:
            player_exposed_ids.add(request.player_intent.item_instance_id)
        allowed = player_exposed_ids & set(
            public_references.allowed_public_entity_ids
        )
        referenced = set(proposal.referenced_entity_ids)
        if not referenced <= allowed:
            raise NarrativeProposalRejectedError()

        item_instance_id = request.player_intent.item_instance_id
        if (
            item_instance_id is not None
            and item_instance_id not in public_references.player_owned_item_ids
        ):
            raise NarrativeProposalRejectedError()

        visible_npcs = set(frame.visible_entities) & set(
            public_references.visible_runtime_npc_ids
        )
        for utterance in proposal.npc_utterances:
            if (
                utterance.speaker_entity_id not in visible_npcs
                or utterance.speaker_entity_id not in referenced
            ):
                raise NarrativeProposalRejectedError()

        for outcome in proposal.untrusted_outcome_proposals:
            if isinstance(outcome, NpcReactionProposal):
                if (
                    outcome.npc_entity_id not in visible_npcs
                    or outcome.npc_entity_id not in referenced
                ):
                    raise NarrativeProposalRejectedError()
            elif isinstance(outcome, PerceptibleOutcomeProposal):
                outcome_ids = set(outcome.referenced_entity_ids)
                if not outcome_ids <= allowed or not outcome_ids <= referenced:
                    raise NarrativeProposalRejectedError()

        strings = [
            proposal.narrative_text,
            *(item.text for item in proposal.npc_utterances),
            *(item.summary for item in proposal.untrusted_outcome_proposals),
            *proposal.continuity_notes,
        ]
        forbidden = tuple(
            identifier.casefold()
            for identifier in public_references.forbidden_identifiers
        )
        for value in strings:
            folded = value.casefold()
            if any(marker in folded for marker in _INTERNAL_TEXT_MARKERS):
                raise NarrativeProposalRejectedError()
            if _INTERNAL_ID_PATTERN.search(value) or _LONG_SECRET_SHAPE.search(value):
                raise NarrativeProposalRejectedError()
            if any(identifier in folded for identifier in forbidden):
                raise NarrativeProposalRejectedError()

        _validate_safe_json(untrusted.model_dump(mode="json"))


def _validate_safe_json(value: Any, *, depth: int = 0) -> None:
    if depth > 16:
        raise ValueError("JSON nesting exceeds validation boundary")
    if value is None or type(value) in (bool, int, str):
        return
    if isinstance(value, float):
        raise TypeError("floats are not accepted from narrative output")
    if isinstance(value, Mapping):
        if len(value) > 512:
            raise ValueError("JSON object exceeds validation boundary")
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            _validate_safe_json(nested, depth=depth + 1)
        return
    if isinstance(value, (list, tuple)):
        if len(value) > 512:
            raise ValueError("JSON array exceeds validation boundary")
        for nested in value:
            _validate_safe_json(nested, depth=depth + 1)
        return
    raise TypeError("narrative output contains a non-JSON value")
