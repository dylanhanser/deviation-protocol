from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from deviation_protocol.application.narrative_models import (
    NarrativeOutcomeCandidate,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.memory_rules import MemoryRuleSourceEventType
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.narrative_outcome import (
    NarrativeOutcomeResult,
    NarrativeOutcomeRuleDefinition,
)
from deviation_protocol.domain.scenario import ScenarioDefinition
from deviation_protocol.domain.scenario_rules import DeclarativeConditionEvaluator
from deviation_protocol.domain.scenario_runtime import (
    FactValueUpdate,
    VerifiedScenarioEvent,
    _seal_verified_scenario_event,
)
from deviation_protocol.domain.state import GameState


_NARRATIVE_OUTCOME_AUTHORITY = object()


def state_fingerprint(state: GameState) -> str:
    return _sha256_json(state.to_snapshot())


def proposal_digest(proposal: ValidatedNarrativeProposal) -> str:
    return _sha256_json(proposal.model_dump(mode="json"))


@dataclass(frozen=True, slots=True)
class AllowedNarrativeOutcome:
    rule: NarrativeOutcomeRuleDefinition
    candidate: NarrativeOutcomeCandidate


def allowed_narrative_outcomes(
    *,
    submission: ActionSubmission,
    state: GameState,
    state_version: int,
    definition: ScenarioDefinition,
    frame: NarrativeFrame,
) -> tuple[AllowedNarrativeOutcome, ...]:
    runtime = state.scenario_runtime
    if runtime is None:
        return ()
    runtime.validate_against(definition)
    applied_outcome_rule_ids = {
        item.outcome_rule_id for item in runtime.narrative_outcome_evidence
    }
    visible_npcs_by_definition: dict[str, list[str]] = {}
    visible_ids = set(frame.visible_entities)
    for npc_id, npc in state.npcs.items():
        if npc_id in visible_ids:
            visible_npcs_by_definition.setdefault(npc.definition_id, []).append(npc_id)
    text = " ".join(
        item for item in (submission.description, submission.dialogue) if item
    ).casefold()
    eligible: list[tuple[NarrativeOutcomeRuleDefinition, tuple[str, ...]]] = []
    evaluator = DeclarativeConditionEvaluator()
    for rule in definition.narrative_outcome_rules:
        if runtime.current_phase_id not in rule.allowed_phase_ids:
            continue
        if submission.action_type not in rule.intent.action_types:
            continue
        if rule.intent.required_any_terms and not any(
            term in text for term in rule.intent.required_any_terms
        ):
            continue
        if rule.intent.required_action_terms and not any(
            term in text for term in rule.intent.required_action_terms
        ):
            continue
        if any(term in text for term in rule.intent.forbidden_terms):
            continue
        if rule.intent.requires_target and not submission.target_ids:
            continue
        if rule.required_current_decision_ids and (
            runtime.current_decision_id not in rule.required_current_decision_ids
        ):
            continue
        if rule.required_current_location_ids and (
            runtime.current_location_id not in rule.required_current_location_ids
        ):
            continue
        if runtime.current_decision_id is not None and (
            runtime.current_decision_id not in rule.required_current_decision_ids
            or any(not effect.resolves_current_decision for effect in rule.effects)
        ):
            continue
        if not set(rule.required_clue_ids) <= set(runtime.discovered_clue_ids):
            continue
        if any(
            not evaluator.values_equal(
                evaluator.fact_value(item.fact_id, definition, runtime), item.value
            )
            for item in rule.required_fact_values
        ):
            continue
        required_runtime_npcs: list[str] = []
        if any(
            not visible_npcs_by_definition.get(definition_id)
            for definition_id in rule.required_visible_npc_definition_ids
        ):
            continue
        for definition_id in rule.required_visible_npc_definition_ids:
            required_runtime_npcs.extend(visible_npcs_by_definition[definition_id])
        if rule.once and rule.rule_id in applied_outcome_rule_ids:
            continue
        eligible.append((rule, tuple(sorted(required_runtime_npcs))))

    # A mutex group is deterministic: only its highest-priority matching rule is
    # exposed. Equal priorities are rejected while loading the catalog.
    selected: dict[str, tuple[NarrativeOutcomeRuleDefinition, tuple[str, ...]]] = {}
    for rule, runtime_npcs in eligible:
        current = selected.get(rule.mutex_group)
        if current is None or rule.priority > current[0].priority:
            selected[rule.mutex_group] = (rule, runtime_npcs)

    bindings = _token_bindings(
        submission=submission,
        state=state,
        state_version=state_version,
        definition=definition,
        frame=frame,
    )
    results: list[AllowedNarrativeOutcome] = []
    for rule, runtime_npcs in sorted(selected.values(), key=lambda item: item[0].rule_id):
        token = "outcome." + hashlib.sha256(
            (bindings + "\0" + rule.rule_id + "\0" + rule.rule_version).encode("utf-8")
        ).hexdigest()[:48]
        results.append(
            AllowedNarrativeOutcome(
                rule=rule,
                candidate=NarrativeOutcomeCandidate(
                    outcome_token=token,
                    safe_description=rule.safe_description,
                    allowed_results=tuple(item.result for item in rule.effects),
                    allowed_entity_ids=runtime_npcs,
                ),
            )
        )
    return tuple(results)


@dataclass(frozen=True, slots=True, init=False)
class ValidatedNarrativeOutcomeCapability:
    job_id: str
    lease_token: str
    lease_owner: str
    session_id: str
    turn_id: str
    client_request_id: str
    action_signature: str
    state_version: int
    state_fingerprint: str
    scenario_id: str
    scenario_content_version: str
    outcome_rule_id: str
    npc_definition_ids: tuple[str, ...]
    proposal_digest: str
    _authority: object

    def is_authentic(self) -> bool:
        return getattr(self, "_authority", None) is _NARRATIVE_OUTCOME_AUTHORITY


@dataclass(frozen=True, slots=True)
class AuthorizedNarrativeOutcome:
    capability: ValidatedNarrativeOutcomeCapability
    rule: NarrativeOutcomeRuleDefinition
    result_name: str
    npc_definition_ids: tuple[str, ...]


class NarrativeOutcomePolicy:
    """Cross-check a safe proposal against freshly recomputed authoritative rules."""

    def authorize(
        self,
        proposal: ValidatedNarrativeProposal,
        *,
        job_id: str,
        lease_token: str,
        lease_owner: str,
        submission: ActionSubmission,
        state: GameState,
        state_version: int,
        definition: ScenarioDefinition,
        frame: NarrativeFrame,
        resolution_status: ResolutionStatus,
        expected_state_fingerprint: str,
        expected_proposal_digest: str,
    ) -> AuthorizedNarrativeOutcome:
        if resolution_status is not ResolutionStatus.NARRATIVE_REQUIRED:
            raise ValueError("action did not pass the narrative gateway")
        if state_fingerprint(state) != expected_state_fingerprint:
            raise ValueError("narrative outcome state is stale")
        if proposal_digest(proposal) != expected_proposal_digest:
            raise ValueError("narrative proposal digest changed")
        selected = proposal.proposal.selected_outcome
        if selected is None:
            raise ValueError("proposal does not use the authorized outcome schema")
        allowed = allowed_narrative_outcomes(
            submission=submission,
            state=state,
            state_version=state_version,
            definition=definition,
            frame=frame,
        )
        matched = next(
            (item for item in allowed if item.candidate.outcome_token == selected.outcome_token),
            None,
        )
        if matched is None or selected.result not in matched.candidate.allowed_results:
            raise ValueError("outcome token is stale or unauthorized")
        if not set(selected.referenced_entity_ids) <= set(
            matched.candidate.allowed_entity_ids
        ):
            raise ValueError("outcome references a non-visible entity")
        effect = matched.rule.effect(selected.result)
        prose = "\n".join(
            (
                proposal.proposal.narrative_text,
                *(item.text for item in proposal.proposal.npc_utterances),
            )
        ).casefold()
        if any(term in prose for term in effect.forbidden_prose_terms):
            raise ValueError("narrative prose contradicts the structured outcome")
        if effect.required_prose_any_terms and not any(
            term in prose for term in effect.required_prose_any_terms
        ):
            raise ValueError("narrative prose does not render the authorized outcome")

        npc_definition_ids = _authorized_memory_npc_definition_ids(
            definition=definition,
            outcome_rule=matched.rule,
            result=selected.result,
        )
        capability = object.__new__(ValidatedNarrativeOutcomeCapability)
        values = {
            "job_id": job_id,
            "lease_token": lease_token,
            "lease_owner": lease_owner,
            "session_id": submission.session_id,
            "turn_id": submission.turn_id,
            "client_request_id": submission.client_request_id,
            "action_signature": submission.action_signature(),
            "state_version": state_version,
            "state_fingerprint": expected_state_fingerprint,
            "scenario_id": definition.scenario_id,
            "scenario_content_version": definition.content_version,
            "outcome_rule_id": matched.rule.rule_id,
            "npc_definition_ids": npc_definition_ids,
            "proposal_digest": expected_proposal_digest,
            "_authority": _NARRATIVE_OUTCOME_AUTHORITY,
        }
        for name, value in values.items():
            object.__setattr__(capability, name, value)
        return AuthorizedNarrativeOutcome(
            capability=capability,
            rule=matched.rule,
            result_name=selected.result.value,
            npc_definition_ids=npc_definition_ids,
        )


class NarrativeEventIssuer:
    """Mint one sealed scenario event exclusively from a server rule template."""

    def issue(
        self,
        authorized: AuthorizedNarrativeOutcome,
        *,
        job_id: str,
        lease_token: str,
        lease_owner: str,
        submission: ActionSubmission,
        state: GameState,
        state_version: int,
        definition: ScenarioDefinition,
        proposal: ValidatedNarrativeProposal,
    ) -> VerifiedScenarioEvent:
        capability = authorized.capability
        runtime = state.scenario_runtime
        if runtime is None or not capability.is_authentic():
            raise ValueError("narrative outcome lacks policy authority")
        if (
            capability.job_id != job_id
            or capability.lease_token != lease_token
            or capability.lease_owner != lease_owner
            or capability.session_id != submission.session_id
            or capability.turn_id != submission.turn_id
            or capability.client_request_id != submission.client_request_id
            or capability.action_signature != submission.action_signature()
            or capability.state_version != state_version
            or capability.state_fingerprint != state_fingerprint(state)
            or capability.scenario_id != definition.scenario_id
            or capability.scenario_content_version != definition.content_version
            or capability.outcome_rule_id != authorized.rule.rule_id
            or capability.npc_definition_ids != authorized.npc_definition_ids
            or capability.proposal_digest != proposal_digest(proposal)
        ):
            raise ValueError("narrative outcome capability binding changed")
        result = proposal.proposal.selected_outcome
        if result is None or result.result.value != authorized.result_name:
            raise ValueError("narrative result changed after authorization")
        effect = authorized.rule.effect(result.result)
        acknowledgement_definitions = set(
            effect.player_alive_acknowledgement_npc_definition_ids
        )
        acknowledgement_runtime_ids = tuple(
            sorted(
                npc_id
                for npc_id, npc in state.npcs.items()
                if npc.definition_id in acknowledgement_definitions
            )
        )
        if acknowledgement_definitions and {
            state.npcs[npc_id].definition_id
            for npc_id in acknowledgement_runtime_ids
        } != acknowledgement_definitions:
            raise ValueError(
                "player-alive acknowledgement lacks a concrete runtime NPC"
            )
        event_id_seed = (
            authorized.rule.rule_id + "\0" + definition.content_version
            if authorized.rule.once
            else job_id
        )
        event_id = "narrative." + hashlib.sha256(
            event_id_seed.encode("utf-8")
        ).hexdigest()[:32]
        return _seal_verified_scenario_event(
            VerifiedScenarioEvent(
                event_id=event_id,
                event_type=effect.event_type,
                source="VALIDATED_NARRATIVE_OUTCOME",
                decision_id=(
                    runtime.current_decision_id if effect.resolves_current_decision else None
                ),
                action_type=effect.action_type,
                discovered_clue_ids=effect.discovered_clue_ids,
                deferred_bindings=tuple(
                    FactValueUpdate(fact_id=item.fact_id, value=item.value)
                    for item in effect.deferred_bindings
                ),
                mutable_fact_updates=tuple(
                    FactValueUpdate(fact_id=item.fact_id, value=item.value)
                    for item in effect.mutable_fact_updates
                ),
                opened_location_ids=effect.opened_location_ids,
                new_location_id=effect.new_location_id,
                resolves_current_decision=effect.resolves_current_decision,
                expose_in_frame=effect.expose_in_frame,
                narrative_outcome_rule_id=authorized.rule.rule_id,
                narrative_outcome_result=result.result,
                narrative_outcome_npc_definition_ids=authorized.npc_definition_ids,
                player_alive_acknowledgement_npc_definition_ids=(
                    effect.player_alive_acknowledgement_npc_definition_ids
                ),
                player_alive_acknowledgement_npc_ids=(
                    acknowledgement_runtime_ids
                ),
            )
        )


def _token_bindings(
    *,
    submission: ActionSubmission,
    state: GameState,
    state_version: int,
    definition: ScenarioDefinition,
    frame: NarrativeFrame,
) -> str:
    return "\0".join(
        (
            submission.session_id,
            submission.turn_id,
            submission.client_request_id,
            submission.action_signature(),
            str(state_version),
            state_fingerprint(state),
            definition.scenario_id,
            definition.content_version,
            _sha256_json(frame.model_dump(mode="json")),
        )
    )


def _authorized_memory_npc_definition_ids(
    *,
    definition: ScenarioDefinition,
    outcome_rule: NarrativeOutcomeRuleDefinition,
    result: NarrativeOutcomeResult,
) -> tuple[str, ...]:
    """Derive memory subjects only from server-owned declarative authority."""

    effect = outcome_rule.effect(result)
    involved_npcs = set(outcome_rule.required_visible_npc_definition_ids)
    return tuple(
        sorted(
            {
                rule.npc_definition_id
                for rule in definition.memory_rules
                if rule.source_event_type
                is MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED
                and rule.npc_definition_id is not None
                and rule.npc_definition_id in involved_npcs
                and (
                    not rule.required_narrative_outcome_rule_ids
                    or outcome_rule.rule_id
                    in rule.required_narrative_outcome_rule_ids
                )
                and (
                    not rule.required_scenario_event_types
                    or effect.event_type in rule.required_scenario_event_types
                )
                and (
                    not rule.required_outcome_results
                    or result in rule.required_outcome_results
                )
            }
        )
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
