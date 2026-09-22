"""Trusted native reconstruction and detached decisions; never a second commit."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from pydantic import BaseModel

from deviation_protocol.application.errors import CandidateStateInvalidError, SnapshotInvalidError
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.entry_world import AUTHORED_ENTRY_WORLDS_V1, EntryWorldRefV1, lookup_entry_world
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.run import revalidate_run_model, _validate_actual_pydantic_state
from deviation_protocol.domain.run_protocol_mechanics import (
    MECHANICS_CATALOGUE, MECHANICS_VERSION, OBJECTIVES, ResourcePressurePolicy,
    SocialTrustPolicy, ConsequenceSeverityPolicy, InformationOpacityPolicy,
    ConflictIntensityPolicy, clock_plan,
    ResourcePlan, ClockPlan, MechanicsCatalogueEntry,
)
from deviation_protocol.domain.state import GameState, DomainRuleViolation

NATIVE_REQUEST_SCHEMA = "native-turn-request/v1"
_AUTHORITY = object()


class NativeTurnBindingError(SnapshotInvalidError):
    pass


class NativeMechanicsIntegrityError(CandidateStateInvalidError):
    pass


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _original_values(value):
    if isinstance(value, BaseModel):
        return {key: _original_values(item) for key, item in value.__dict__.items()}
    if isinstance(value, dict):
        return {key: _original_values(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return type(value)(_original_values(item) for item in value)
    return value


@dataclass(frozen=True, slots=True, init=False)
class TrustedNativeTurnInputs:
    binding_bytes: bytes
    snapshot_bytes: bytes
    objectives: tuple[int, ...]
    presentation: tuple[str, str, str]
    resource_id: str
    _authority: object
    _original: tuple
    visit_evidence: object

    def is_authentic(self) -> bool:
        return (getattr(self, "_authority", None) is _AUTHORITY
                and self._original == (self.binding_bytes, self.snapshot_bytes,
                                       self.objectives, self.presentation, self.resource_id))


@dataclass(frozen=True, slots=True, init=False)
class NativeMechanicsDecision:
    inputs: TrustedNativeTurnInputs
    resource: ResourcePlan
    clocks: tuple[ClockPlan, ...]
    selected_rule: str | None
    selected_result: object
    action_type: str | None
    _authority: object
    _original: tuple

    def is_authentic(self) -> bool:
        if getattr(self, "_authority", None) is not _AUTHORITY:
            return False
        try:
            return (type(self.inputs) is TrustedNativeTurnInputs and self.inputs.is_authentic()
                    and type(self.resource) is ResourcePlan and type(self.clocks) is tuple
                    and all(type(row) is ClockPlan for row in self.clocks)
                    and self.inputs is self._original[0]
                    and self._original == self._identity())
        except (AttributeError, TypeError, IndexError):
            return False

    def _identity(self) -> tuple:
        # Preserve original scalar types and carrier identity. Authentication must
        # not serialize private job evidence when the pure compiler invokes it.
        resource = tuple((type(value), value) for value in (
            self.resource.resource_id, self.resource.before, self.resource.requested,
            self.resource.actual, self.resource.after))
        clocks = tuple(tuple((type(value), value) for value in (
            row.clock_id, row.before, row.base, row.social, row.severity, row.opacity,
            row.conflict, row.after, row.talent)) for row in self.clocks)
        return (self.inputs, resource, clocks, self.selected_rule,
                type(self.selected_result), self.selected_result, self.action_type)

    def evidence(self) -> dict:
        return {"schema": MECHANICS_VERSION,
                "objectives": dict(zip(OBJECTIVES, self.inputs.objectives)),
                "selected_rule": self.selected_rule,
                "selected_result": self.selected_result.value if self.selected_result is not None else None,
                "resource": asdict(self.resource),
                "clocks": [{k: v for k, v in asdict(row).items()
                    if k != "talent" or "opening_talents" in json.loads(self.inputs.binding_bytes)}
                    for row in sorted(self.clocks, key=lambda r: r.clock_id)]}


def _mint(cls, **fields):
    value = object.__new__(cls)
    for name, field in fields.items():
        object.__setattr__(value, name, field)
    object.__setattr__(value, "_authority", _AUTHORITY)
    return value


class NativeTurnMechanicsCoordinator:
    def __init__(self, catalog, scenario_catalog, *, catalogue=None,
                 worlds=AUTHORED_ENTRY_WORLDS_V1):
        self.catalog = catalog
        self.scenario_catalog = scenario_catalog
        self.catalogue = tuple(e for e in MECHANICS_CATALOGUE if e.content_version == catalog.content_version) if catalogue is None else tuple(catalogue)
        keys = set()
        for entry in self.catalogue:
            if type(entry) is not MechanicsCatalogueEntry:
                raise ValueError("invalid native mechanics catalogue entry")
            key = (entry.world_id, entry.world_version)
            world = next((w for w in worlds if (w.entry_world_id.value, w.entry_world_version.value) == key), None)
            # Only the explicitly registered continuation packs bypass starting-world lookup.
            # Adding a starting world must not expand this exception.
            destination = entry in (MECHANICS_CATALOGUE[1], MECHANICS_CATALOGUE[2], MECHANICS_CATALOGUE[4])
            if not destination and (key in keys or world is None or (world.scenario_id, world.scenario_content_version,
                    world.default_character_definition_id) != (entry.scenario_id, entry.content_version, entry.character_id)):
                raise ValueError("native mechanics world association is incompatible")
            keys.add(key)
            definition = scenario_catalog.scenario(entry.scenario_id)
            character = catalog.character(entry.character_id)
            if (definition is None or definition.content_version != entry.content_version
                    or character is None
                    or not any(r.key == entry.resource_id for r in character.resource_caps)):
                raise ValueError("native mechanics catalogue is incompatible")

    async def load(self, uow, game_session, state, definition):
        from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1, NativeRunTerminatedV1, LegacyRunCompatibilityV1,NativeRunContinuedV1,NativeRunContinuedTerminatedV1,NativeRunRegionalRevisitV1,NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1
        session_id = game_session.session_id
        try:
            participation = await uow.run_participations.get(session_id)
            reverse = await uow.run_participations.find_attachment_run_ids(session_id)
        except ValueError:
            raise NativeTurnBindingError(session_id) from None
        if participation is None:
            if reverse:
                raise NativeTurnBindingError(session_id)
            return None
        if reverse != (participation.run_id,):
            raise NativeTurnBindingError(session_id)
        try:
            family = await uow.run_protocol_bindings.get_classified(run_id=participation.run_id)
        except ValueError:
            raise NativeTurnBindingError(session_id) from None
        if type(family) is LegacyRunCompatibilityV1:
            revalidate_run_model(family, LegacyRunCompatibilityV1)
            if family.session_id != session_id:
                raise NativeTurnBindingError(session_id)
            return None
        from deviation_protocol.domain.fog_patrol import FogContinuedV1, FogTerminatedV1
        classified = family
        if type(family) in (FogContinuedV1, FogTerminatedV1):
            revalidate_run_model(family, type(family))
            fog = family.continued if type(family) is FogTerminatedV1 else family
            if participation not in family.canonical_run.trusted_participation_references:
                raise NativeTurnBindingError(session_id)
            if participation.joined_state_version.value == 4:
                entry = fog.entry
                if (definition is None or (game_session.scenario_id, game_session.scenario_version)
                        != (entry.scenario_id, entry.scenario_content_version)
                        or (definition.scenario_id, definition.content_version) != (entry.scenario_id, entry.scenario_content_version)
                        or game_session.player_id != state.player.player_id
                        or state.player.character_definition_id != entry.snapshot["player"]["character_definition_id"]):
                    raise NativeTurnBindingError(session_id)
                self.validate_state(state, session_id)
                return classified
            family = fog.admission
        if type(family) in (NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1):
            revalidate_run_model(family, type(family))
            regional = family.revisited if type(family) in (NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1) else family
            if participation not in family.canonical_run.trusted_participation_references:
                raise NativeTurnBindingError(session_id)
            if participation.joined_state_version.value == 5:
                entry = regional.entry
                if (definition is None or (game_session.scenario_id, game_session.scenario_version)
                        != (entry.scenario_id, entry.scenario_content_version)
                        or (definition.scenario_id, definition.content_version) != (entry.scenario_id, entry.scenario_content_version)
                        or game_session.player_id != state.player.player_id
                        or state.player.character_definition_id != entry.snapshot["player"]["character_definition_id"]):
                    raise NativeTurnBindingError(session_id)
                self.validate_state(state, session_id)
                return classified
            family = regional.continued
        if type(family) in (NativeRunContinuedV1,NativeRunContinuedTerminatedV1):
            revalidate_run_model(family,type(family))
            continued = family.continued if type(family) is NativeRunContinuedTerminatedV1 else family
            if participation not in family.canonical_run.trusted_participation_references:
                raise NativeTurnBindingError(session_id)
            if participation.joined_state_version.value == 4:
                root = continued.destination_root
                if (definition is None or (game_session.scenario_id,game_session.scenario_version)
                        != (root.scenario_id,root.scenario_content_version)
                        or (definition.scenario_id,definition.content_version) != (root.scenario_id,root.scenario_content_version)
                        or game_session.player_id != state.player.player_id
                        or state.player.character_definition_id != root.snapshot["player"]["character_definition_id"]):
                    raise NativeTurnBindingError(session_id)
                self.validate_state(state,session_id)
                return classified
            family = continued.admission
        if type(family) is NativeRunTerminatedV1:
            revalidate_run_model(family, NativeRunTerminatedV1)
            family = family.admission
        if type(family) is not NativeRunAdmissionV1:
            raise NativeTurnBindingError(session_id)
        revalidate_run_model(family, NativeRunAdmissionV1)
        run = family.canonical_run
        world = family.world_binding.entry_world
        authored = lookup_entry_world(EntryWorldRefV1(
            entry_world_id=world.entry_world_id, entry_world_version=world.entry_world_version))
        if (run.trusted_participation_references != (participation,)
                or world != authored or definition is None
                or definition.scenario_id != world.scenario_id
                or definition.content_version != world.scenario_content_version
                or game_session.scenario_id != world.scenario_id
                or game_session.scenario_version != world.scenario_content_version
                or state.player.player_id != game_session.player_id
                or state.player.character_definition_id != world.default_character_definition_id):
            raise NativeTurnBindingError(session_id)
        # Validate original state before snapshot serialization can normalize it.
        self.validate_state(state, session_id)
        return classified

    def validate_state(self, state, session_id):
        try:
            if type(state) is not GameState:
                raise ValueError("invalid state carrier")
            _validate_actual_pydantic_state(state, path="GameState", visited=set())
            GameState.model_validate(_original_values(state), strict=True)
            state.validate_against(self.catalog)
            restored = GameState.from_snapshot(state.to_snapshot(), catalog=self.catalog,
                                               scenario_catalog=self.scenario_catalog)
            if restored != state:
                raise ValueError("state normalization")
        except (TypeError, ValueError, AttributeError, DomainRuleViolation):
            raise NativeMechanicsIntegrityError(session_id) from None

    def bind(self, family, state, submission, state_version, frame, *, talents=None) -> TrustedNativeTurnInputs:
        from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1,NativeRunContinuedV1,NativeRunRegionalRevisitV1
        from deviation_protocol.domain.fog_patrol import FogContinuedV1
        fog = type(family) is FogContinuedV1
        if type(family) not in (FogContinuedV1,NativeRunAdmissionV1,NativeRunContinuedV1,NativeRunRegionalRevisitV1):
            raise NativeTurnBindingError(submission.session_id)
        revalidate_run_model(family, type(family))
        continued = type(family) is NativeRunContinuedV1
        regional = type(family) is NativeRunRegionalRevisitV1
        admission = family.admission if fog or continued or regional else family
        self.validate_state(state, submission.session_id)
        run = family.canonical_run
        world = admission.world_binding.entry_world
        scenario_id = family.entry.scenario_id if regional or fog else family.destination_root.scenario_id if continued else world.scenario_id
        content_version = family.entry.scenario_content_version if regional or fog else family.destination_root.scenario_content_version if continued else world.scenario_content_version
        world_id = "world.undelivered_receipt" if continued or regional else world.entry_world_id.value
        world_version = 1 if continued or regional else world.entry_world_version.value
        if (run.trusted_participation_references[-1].session_id != submission.session_id
                or type(state_version) is not int or state_version < 0
                or state.content_version != content_version
                or state.player.character_definition_id != world.default_character_definition_id):
            raise NativeTurnBindingError(submission.session_id)
        protocol = admission.protocol_binding.resolved_protocol
        entry = next((e for e in self.catalogue if (
            e.world_id, e.world_version, e.scenario_id, e.content_version, e.character_id
        ) == (world_id, world_version, scenario_id,
              content_version, world.default_character_definition_id)), None)
        if entry is None or entry.resource_id not in state.player.resources:
            raise NativeMechanicsIntegrityError(submission.session_id)
        binding = dict(run_id=run.run_id.value, run_revision=5 if regional else 4 if continued or fog else 3,
            continuous_story_line_id=run.continuous_story_line_id.value,
            session_id=submission.session_id, player_id=state.player.player_id,
            applicable_character_reference=run.player_character_binding.applicable_character_reference.model_dump(mode="json"),
            entry_world=EntryWorldRefV1(entry_world_id=world.entry_world_id,
                                      entry_world_version=world.entry_world_version).model_dump(mode="json"),
            scenario_id=scenario_id, scenario_content_version=content_version,
            resolution_fingerprint=protocol.fingerprint.value, mechanics_version=MECHANICS_VERSION,
            state_version=state_version, state_fingerprint=state_fingerprint(state),
            turn_id=submission.turn_id, client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(), frame_digest=digest(frame.model_dump(mode="json")))
        if continued:
            binding.update(visit_id=family.position.visit_id,visit_ordinal=2,
                world=family.destination_root.world.model_dump(),region=family.destination_root.region.model_dump(),
                continuation_fingerprint=family.continuation_evidence.request.fingerprint())
        if regional:
            binding.update(visit_id=family.position.visit_id, visit_ordinal=3,
                world=family.entry.world.model_dump(), region=family.entry.region.model_dump(),
                regional_entry_fingerprint=family.revisit_evidence.request.fingerprint())
        if fog:
            binding.update(visit_id=family.position.visit_id, visit_ordinal=2,
                fog_entry_sha256=family.entry.digest(), fog_source_sha256=family.source_root.digest())
        if talents is not None:
            talents.validate()
            if talents.run_id != run.run_id.value or talents.state != "CONFIRMED":
                raise NativeTurnBindingError(submission.session_id)
            binding["opening_talents"] = {"catalog_version": talents.catalog_version, "selected_ids": list(talents.selections)}
        elif run.run_id.value.startswith("opening."):
            raise NativeTurnBindingError(submission.session_id)
        envelope = protocol.resolution_input.envelope
        fields = dict(binding_bytes=canonical(binding), snapshot_bytes=canonical(state.to_snapshot()),
                      objectives=tuple(getattr(protocol.final_values, name).value for name in OBJECTIVES),
                      presentation=(envelope.world_tone.value, envelope.reality_boundary.value,
                                    envelope.relationship_overlay.value), resource_id=entry.resource_id)
        inputs = _mint(TrustedNativeTurnInputs, **fields, _original=tuple(fields.values()))
        if continued:
            from deviation_protocol.application.world_visit_context import detach_world_visit_evidence
            object.__setattr__(inputs,"visit_evidence",detach_world_visit_evidence(family,inputs))
        if regional:
            from deviation_protocol.application.world_visit_context import detach_regional_visit_evidence
            object.__setattr__(inputs, "visit_evidence", detach_regional_visit_evidence(family, inputs))
        return inputs

    def decide(self, inputs, state, definition, submission, *, selected=None, event=None):
        if type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic():
            raise NativeMechanicsIntegrityError(submission.session_id)
        self.validate_state(state, submission.session_id)
        if canonical(state.to_snapshot()) != inputs.snapshot_bytes:
            raise NativeMechanicsIntegrityError(submission.session_id)
        binding = json.loads(inputs.binding_bytes)
        if (binding["session_id"] != submission.session_id or binding["turn_id"] != submission.turn_id
                or binding["client_request_id"] != submission.client_request_id
                or binding["action_signature"] != submission.action_signature()
                or binding["state_fingerprint"] != state_fingerprint(state)
                or binding["player_id"] != state.player.player_id
                or binding["scenario_id"] != definition.scenario_id
                or binding["scenario_content_version"] != definition.content_version):
            raise NativeTurnBindingError(submission.session_id)
        if event is not None:
            from deviation_protocol.domain.scenario_runtime import VerifiedScenarioEvent
            if type(event) is not VerifiedScenarioEvent or not event.is_authentic():
                raise NativeMechanicsIntegrityError(submission.session_id)
        if selected is not None:
            from deviation_protocol.application.narrative_outcome_policy import allowed_narrative_outcomes, select_native_outcome
            from deviation_protocol.application.scenario_event_bridge import bind_public_decision_frame
            from deviation_protocol.application.story_director import DeterministicStoryDirector
            tags = frozenset(self.catalog.character(state.player.character_definition_id).tags) & set(definition.available_profession_tags)
            frame = bind_public_decision_frame(DeterministicStoryDirector().plan_frame(state, definition, profession_tags=tags),
                session_id=submission.session_id, state_version=binding["state_version"], scenario_content_version=definition.content_version)
            eligible = select_native_outcome(allowed_narrative_outcomes(submission=submission, state=state,
                state_version=binding["state_version"], definition=definition, frame=frame))
            if (not eligible or eligible[0] != selected
                    or digest(frame.model_dump(mode="json")) != binding["frame_digest"]):
                raise NativeMechanicsIntegrityError(submission.session_id)
        runtime = state.scenario_runtime
        phase = definition.phase(runtime.current_phase_id)
        result = selected.candidate.allowed_results[0] if selected is not None else None
        rule = selected.rule if selected is not None else None
        effect = rule.effect(result) if rule is not None else None
        if effect is not None:
            from deviation_protocol.application.story_director import validate_reveals
            tags = frozenset(self.catalog.character(state.player.character_definition_id).tags)
            validate_reveals(runtime, definition, effect.discovered_clue_ids, effect.event_type, tags)
        action_type = effect.action_type if effect is not None else event.action_type if event is not None else None
        if action_type is None:
            advances = phase.auto_beat_clock_advances if event is None and selected is None else ()
        else:
            if action_type not in phase.allowed_action_types:
                raise NativeMechanicsIntegrityError(submission.session_id)
            cost = next((c for c in phase.action_time_costs if c.action_type == action_type), None)
            advances = cost.clock_advances if cost is not None else ()
        p, t, s, o, c = inputs.objectives
        resource = state.player.resources[inputs.resource_id]
        rp = ResourcePressurePolicy().plan(p, resource_id=inputs.resource_id,
            current=resource.current, maximum=resource.maximum, narrative=selected is not None)
        social = SocialTrustPolicy().extra(t, qualifying_talk=bool(rule is not None
            and submission.action_type is ActionType.TALK and rule.required_visible_npc_definition_ids))
        severity = ConsequenceSeverityPolicy().extra(s, result=result)
        opacity = InformationOpacityPolicy().extra(o, discovers=bool(effect is not None
            and set(effect.discovered_clue_ids) - runtime.discovered_clue_ids))
        conflict = ConflictIntensityPolicy().extra(c)
        clocks = tuple(clock_plan(a.clock_id, runtime.threat_clocks[a.clock_id].value,
            definition.clock(a.clock_id).maximum, a.amount, social, severity, opacity, conflict) for a in advances)
        talent_binding = json.loads(inputs.binding_bytes).get("opening_talents")
        if talent_binding is not None and action_type is not None:
            from dataclasses import replace
            from deviation_protocol.domain.opening_talents import OpeningTalentClockPolicy
            policy = OpeningTalentClockPolicy()
            modifier = policy.modifier(talent_binding["catalog_version"], tuple(talent_binding["selected_ids"]), submission.action_type.value)
            adjusted = []
            for row in clocks:
                original = row.social + row.severity + row.opacity + row.conflict
                delta = policy.additional(original, modifier) - original
                adjusted.append(replace(row, talent=delta,
                    after=min(definition.clock(row.clock_id).maximum, row.before + row.amount + delta)))
            clocks = tuple(adjusted)
        decision = _mint(NativeMechanicsDecision, inputs=inputs, resource=rp, clocks=clocks,
                         selected_rule=rule.rule_id if rule is not None else None,
                         selected_result=result, action_type=action_type)
        object.__setattr__(decision, "_original", decision._identity())
        return decision

    def apply_resource(self, state, decision):
        if type(decision) is not NativeMechanicsDecision or not decision.is_authentic():
            raise NativeMechanicsIntegrityError("native")
        binding = json.loads(decision.inputs.binding_bytes)
        self.validate_state(state, binding["session_id"])
        if canonical(state.to_snapshot()) != decision.inputs.snapshot_bytes:
            raise NativeMechanicsIntegrityError(binding["session_id"])
        candidate = deepcopy(state)
        resource = decision.resource
        events = ()
        if resource.actual > 0:
            candidate.consume_resource(resource.resource_id, resource.actual)
            events = (DomainEventDraft("RunProtocolResourceSpent", asdict(resource)),)
        return candidate, events

    @staticmethod
    def audit(decision):
        if type(decision) is not NativeMechanicsDecision or not decision.is_authentic():
            raise NativeMechanicsIntegrityError("native")
        binding = json.loads(decision.inputs.binding_bytes)
        payload = decision.evidence()
        payload.update(binding_digest=hashlib.sha256(
            b"deviation-protocol:native-turn-binding:v1\0" + decision.inputs.binding_bytes).hexdigest(),
            original_state_version=binding["state_version"])
        return DomainEventDraft("RunProtocolMechanicsApplied", payload)


def native_request_envelope(request, decision):
    if type(decision) is not NativeMechanicsDecision or not decision.is_authentic():
        raise NativeMechanicsIntegrityError("native")
    revision = json.loads(decision.inputs.binding_bytes)["run_revision"]
    return {"schema": {3:NATIVE_REQUEST_SCHEMA, 4:"native-visit-turn-request/v1", 5:"native-regional-turn-request/v1"}[revision], "request": request.model_dump(mode="json"),
            "binding": json.loads(decision.inputs.binding_bytes), "mechanics": decision.evidence()}


def parse_job_request(payload):
    """Parsing is evidence only. Native authority is freshly reconstructed in a UoW."""
    from deviation_protocol.application.narrative_models import NarrativeRequest
    if not isinstance(payload, dict):
        raise ValueError("invalid narrative request")
    if "schema" not in payload:
        return NarrativeRequest.model_validate(payload, strict=False), None
    if set(payload) != {"schema", "request", "binding", "mechanics"} or payload["schema"] not in (NATIVE_REQUEST_SCHEMA,"native-visit-turn-request/v1","native-regional-turn-request/v1"):
        raise ValueError("invalid native request envelope")
    # Byte equality to recomputed evidence at detach/finalize validates every nested field.
    if not isinstance(payload["binding"], dict) or not isinstance(payload["mechanics"], dict):
        raise ValueError("invalid native evidence")
    _validate_evidence(payload["binding"], payload["mechanics"],visit=payload["schema"] == "native-visit-turn-request/v1", regional=payload["schema"] == "native-regional-turn-request/v1")
    return NarrativeRequest.model_validate(payload["request"], strict=False), payload


def _validate_evidence(binding, mechanics, *, visit=False, regional=False):
    from deviation_protocol.domain.player_character import ApplicableCharacterReference
    from deviation_protocol.domain.run_protocol_mechanics import pressure, MAX_SCENARIO_COUNTER
    keys = {"run_id", "run_revision", "continuous_story_line_id", "session_id", "player_id",
        "applicable_character_reference", "entry_world", "scenario_id", "scenario_content_version",
        "resolution_fingerprint", "mechanics_version", "state_version", "state_fingerprint",
        "turn_id", "client_request_id", "action_signature", "frame_digest"}
    if visit:
        keys |= {"visit_id","visit_ordinal","world","region","continuation_fingerprint"}
        from deviation_protocol.domain.world_continuation import WorldRefV1,RegionRefV1,DESTINATION_WORLD,DESTINATION_REGION
        if (type(binding.get("visit_ordinal")) is not int or binding["visit_ordinal"] != 2
                or WorldRefV1.model_validate(binding.get("world")) != DESTINATION_WORLD
                or RegionRefV1.model_validate(binding.get("region")) != DESTINATION_REGION
                or any(type(binding.get(k)) is not str or re.fullmatch(r"[0-9a-f]{64}",binding[k]) is None for k in ("visit_id","continuation_fingerprint"))):
            raise ValueError("invalid native visit binding")
    if regional:
        from deviation_protocol.domain.world_continuation import WorldRefV1, RegionRefV1, DESTINATION_WORLD
        from deviation_protocol.domain.world_revisit import ARCHIVE_REGION, ARCHIVE_IDENTITY
        keys |= {"visit_id", "visit_ordinal", "world", "region", "regional_entry_fingerprint"}
        if (visit or type(binding.get("visit_ordinal")) is not int or binding["visit_ordinal"] != 3
                or WorldRefV1.model_validate(binding.get("world")) != DESTINATION_WORLD
                or RegionRefV1.model_validate(binding.get("region")) != ARCHIVE_REGION
                or (binding.get("scenario_id"), binding.get("scenario_content_version")) != ARCHIVE_IDENTITY
                or any(type(binding.get(k)) is not str or re.fullmatch(r"[0-9a-f]{64}", binding[k]) is None
                       for k in ("visit_id", "regional_entry_fingerprint"))):
            raise ValueError("invalid regional turn binding")
    opening = binding.get("opening_talents")
    if opening is not None:
        from deviation_protocol.domain.opening_talents import OpeningTalentClockPolicy
        if not isinstance(opening, dict) or set(opening) != {"catalog_version", "selected_ids"}:
            raise ValueError("invalid opening talent evidence")
        OpeningTalentClockPolicy().modifier(opening["catalog_version"], tuple(opening["selected_ids"]), "OBSERVE")
        keys.add("opening_talents")
    if set(binding) != keys or binding["mechanics_version"] != MECHANICS_VERSION:
        raise ValueError("invalid native binding fields")
    for key in ("run_revision", "state_version"):
        if type(binding[key]) is not int or not 0 <= binding[key] <= 2**63 - 1:
            raise ValueError("invalid native revision")
    if binding["run_revision"] != (5 if regional else 4 if visit else 3):
        raise ValueError("invalid native Run revision")
    for key in ("resolution_fingerprint", "state_fingerprint", "action_signature", "frame_digest"):
        if type(binding[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", binding[key]) is None:
            raise ValueError("invalid native fingerprint")
    for key in ("run_id", "continuous_story_line_id", "session_id", "player_id", "scenario_id",
                "scenario_content_version", "turn_id", "client_request_id"):
        bound = 64 if key in {"session_id", "turn_id", "client_request_id"} else 32 if key == "scenario_content_version" else 128
        if (type(binding[key]) is not str or not 1 <= len(binding[key]) <= bound
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", binding[key]) is None):
            raise ValueError("invalid native identifier")
    ApplicableCharacterReference.model_validate_json(canonical(binding["applicable_character_reference"]))
    EntryWorldRefV1.model_validate_json(canonical(binding["entry_world"]))
    if set(mechanics) != {"schema", "objectives", "selected_rule", "selected_result", "resource", "clocks"} or mechanics["schema"] != MECHANICS_VERSION:
        raise ValueError("invalid mechanics fields")
    if not isinstance(mechanics["objectives"], dict) or set(mechanics["objectives"]) != set(OBJECTIVES):
        raise ValueError("invalid mechanics objectives")
    for value in mechanics["objectives"].values():
        pressure(value)
    if (type(mechanics["selected_rule"]) is not str or not 1 <= len(mechanics["selected_rule"]) <= 128
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", mechanics["selected_rule"]) is None
            or mechanics["selected_result"] not in {"SUCCESS", "AMBIGUOUS", "NO_EFFECT", "FAILURE"}):
        raise ValueError("invalid mechanics selection")
    resource = mechanics["resource"]
    if not isinstance(resource, dict) or set(resource) != {"resource_id", "before", "requested", "actual", "after"}:
        raise ValueError("invalid resource evidence")
    if type(resource["resource_id"]) is not str or not 1 <= len(resource["resource_id"]) <= 128:
        raise ValueError("invalid resource ID")
    if any(type(resource[k]) is not int or not 0 <= resource[k] <= 2**63 - 1 for k in ("before", "requested", "actual", "after")):
        raise ValueError("invalid resource counters")
    if (resource["requested"] > 2 or resource["actual"] != min(resource["before"], resource["requested"])
            or resource["after"] != resource["before"] - resource["actual"]):
        raise ValueError("inconsistent resource evidence")
    rows = mechanics["clocks"]
    if not isinstance(rows, (tuple, list)) or len(rows) > 512:
        raise ValueError("invalid clock rows")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != ({"clock_id", "before", "base", "social", "severity", "opacity", "conflict", "after"} | ({"talent"} if opening is not None else set())):
            raise ValueError("invalid clock row")
        if type(row["clock_id"]) is not str or not 1 <= len(row["clock_id"]) <= 128:
            raise ValueError("invalid clock ID")
        if opening is not None and (type(row["talent"]) is not int or not -2 <= row["talent"] <= 2
                or sum(row[k] for k in ("social", "severity", "opacity", "conflict")) + row["talent"] < 0):
            raise ValueError("invalid talent clock adjustment")
        ids.append(row["clock_id"])
        for key in ("before", "base", "after", "social", "severity", "opacity", "conflict"):
            maximum = 2 if key in {"social", "severity", "opacity", "conflict"} else MAX_SCENARIO_COUNTER
            if type(row[key]) is not int or not (1 if key == "base" else 0) <= row[key] <= maximum:
                raise ValueError("invalid clock component")
    if ids != sorted(set(ids)):
        raise ValueError("unordered or duplicate clock rows")


def validate_director_plan(decision, state, definition, events):
    if type(decision) is not NativeMechanicsDecision or not decision.is_authentic():
        raise NativeMechanicsIntegrityError("native")
    original = json.loads(decision.inputs.snapshot_bytes)
    expected = deepcopy(original)
    # Snapshot shape belongs to GameState; compare the declared change without granting
    # arbitrary candidate state authority to a seal.
    current = state.to_snapshot()
    resource_id = decision.resource.resource_id
    if decision.resource.actual:
        expected["player"]["resources"][resource_id]["current"] = decision.resource.after
    if canonical(current) != canonical(expected):
        raise NativeMechanicsIntegrityError("native")
    phase = definition.phase(state.scenario_runtime.current_phase_id)
    if events:
        if len(events) != 1 or events[0].action_type != decision.action_type:
            raise NativeMechanicsIntegrityError("native")
        event = events[0]
        if (event.narrative_outcome_rule_id != decision.selected_rule
                or event.narrative_outcome_result != decision.selected_result):
            raise NativeMechanicsIntegrityError("native")
        cost = next((c for c in phase.action_time_costs if c.action_type == event.action_type), None)
        base = cost.clock_advances if cost else ()
    else:
        if decision.selected_rule is not None or decision.action_type is not None:
            raise NativeMechanicsIntegrityError("native")
        base = phase.auto_beat_clock_advances
    if tuple((a.clock_id, a.amount) for a in base) != tuple((c.clock_id, c.base) for c in decision.clocks):
        raise NativeMechanicsIntegrityError("native")
    return decision.clocks
