"""Read-only strict persistence reconstruction for Run Protocol bindings."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import UTC, datetime
import json
import re

from deviation_protocol.domain import run_protocol as s1
from deviation_protocol.domain import run_protocol_resolution as s2
from deviation_protocol.domain.run_protocol_resolution import lookup_run_protocol_profile
from deviation_protocol.domain.run import CanonicalRun, RunStateVersion, validate_canonical_run
from deviation_protocol.domain.run_protocol_binding import (
    LegacyRunCompatibilityV1, NativeRunProtocolBindingV1,
    RUN_PROTOCOL_BINDING_EPOCH, RUN_PROTOCOL_BINDING_V1_VERSION,
    RUN_FAMILY_NATIVE_V1,
)


class RunProtocolBindingStoredIntegrityError(ValueError):
    """Stored binding or family evidence is malformed or incomplete."""


class UnsupportedRunProtocolBindingVersionError(RunProtocolBindingStoredIntegrityError):
    """The S3 binding discriminator or selector is unsupported."""


class ContradictoryRunFamilyError(RunProtocolBindingStoredIntegrityError):
    """Both complete legacy and native proofs exist."""


class RunProtocolBindingRepositoryError(RuntimeError):
    """A binding-classification SQL read failed."""


@dataclass(frozen=True, slots=True)
class _StoredRunProtocolBindingV1:
    run_id: str
    continuous_story_line_id: str
    bound_state_version: int
    family_discriminator: str
    binding_epoch: str
    binding_record_version: int
    envelope_epoch: str
    envelope_record_version: int
    envelope_canonical: bytes
    resolver_epoch: str
    resolver_record_version: int
    resolution_input_canonical: bytes
    resource_pressure: int
    social_trust: int
    consequence_severity: int
    information_opacity: int
    conflict_intensity: int
    resolution_fingerprint: bytes
    created_at: datetime


_OBJECTIVES = (
    "resource_pressure", "social_trust", "consequence_severity",
    "information_opacity", "conflict_intensity",
)
_COLUMNS = tuple(field.name for field in fields(_StoredRunProtocolBindingV1))
_OPAQUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RunProtocolBindingStoredIntegrityError(message) from None


def _stored_binding_from_row(row, session) -> _StoredRunProtocolBindingV1:
    from sqlalchemy import inspect
    from deviation_protocol.infrastructure.orm_models import RunProtocolBindingRow

    _require(type(row) is RunProtocolBindingRow, "binding row type")
    state = inspect(row)
    _require(
        state.session is session.sync_session
        and state.persistent
        and not state.modified
        and not state.expired_attributes
        and not state.unloaded
        and set(vars(row)) == set(_COLUMNS) | {"_sa_instance_state"},
        "binding row must be completely loaded by this Session",
    )
    values = vars(row)
    _require(
        state.key == (RunProtocolBindingRow, (values["run_id"],), None),
        "binding row identity-map key",
    )
    return _StoredRunProtocolBindingV1(**{name: values[name] for name in _COLUMNS})


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise s2.RunProtocolResolutionIntegrityError("duplicate resolution member") from None
        result[name] = value
    return result


def _reject_constant(value):
    raise s2.RunProtocolResolutionIntegrityError("non-finite resolution number") from None


def _resolution_payload(payload: bytes):
    try:
        parsed = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise s2.RunProtocolResolutionIntegrityError("invalid resolution JSON") from error
    if type(parsed) is not dict or set(parsed) != {
        "authorized_overrides", "authorized_profile_id", "authorized_profile_version",
        "canonical_envelope_hex", "resolver_version", "schema",
    }:
        raise s2.RunProtocolResolutionIntegrityError("resolution member allowlist") from None
    if type(parsed["schema"]) is not str or type(parsed["resolver_version"]) is not int:
        raise s2.RunProtocolResolutionIntegrityError("resolution selector types") from None
    if parsed["schema"] != s2.RUN_PROTOCOL_RESOLUTION_V1_SCHEMA or parsed["resolver_version"] != 1:
        raise s2.UnsupportedRunProtocolResolverVersionError("unsupported stored resolution schema") from None
    return parsed


def _reconstruct_native_binding(
    stored, *, canonical_run: CanonicalRun, legacy_proof: LegacyRunCompatibilityV1 | None
) -> NativeRunProtocolBindingV1:
    _require(type(stored) is _StoredRunProtocolBindingV1, "stored binding type")
    _require(all(hasattr(stored, name) for name in _COLUMNS), "stored binding fields")
    for name in _COLUMNS:
        if name in ("run_id", "continuous_story_line_id", "family_discriminator", "binding_epoch", "envelope_epoch", "resolver_epoch"):
            _require(type(getattr(stored, name)) is str, name)
        elif name in ("envelope_canonical", "resolution_input_canonical", "resolution_fingerprint"):
            _require(type(getattr(stored, name)) is bytes, name)
        elif name == "created_at":
            _require(type(stored.created_at) is datetime and stored.created_at.tzinfo is None, name)
    for name in ("bound_state_version", "binding_record_version", "envelope_record_version", "resolver_record_version", *_OBJECTIVES):
        _require(type(getattr(stored, name)) is int, name)
    for name in _COLUMNS:
        value = getattr(stored, name)
        if name in ("run_id", "continuous_story_line_id"):
            _require(1 <= len(value) <= 128 and value.isascii() and _OPAQUE.fullmatch(value) is not None, name)
        elif name in ("family_discriminator", "binding_epoch", "envelope_epoch", "resolver_epoch"):
            maximum = 32 if name == "family_discriminator" else 64
            _require(1 <= len(value) <= maximum and value.isascii(), name)
        elif name in ("bound_state_version", "binding_record_version", "envelope_record_version", "resolver_record_version"):
            _require(1 <= value <= 2**63 - 1, name)
        elif name in ("envelope_canonical", "resolution_input_canonical"):
            _require(1 <= len(value) <= 1024, name)
        elif name in _OBJECTIVES:
            _require(0 <= value <= 100 and value % 5 == 0, name)
        elif name == "resolution_fingerprint":
            _require(len(value) == 32, name)
        elif name == "created_at":
            _require(1000 <= value.year <= 9999, name)
    try:
        run = validate_canonical_run(canonical_run)
    except (TypeError, ValueError, AttributeError) as error:
        raise RunProtocolBindingStoredIntegrityError("invalid canonical Run context") from error
    _require(
        stored.run_id == run.run_id.value
        and stored.continuous_story_line_id == run.continuous_story_line_id.value
        and stored.bound_state_version <= run.state_version.value,
        "binding Run association",
    )
    for actual, expected in (
        (stored.family_discriminator, RUN_FAMILY_NATIVE_V1),
        (stored.binding_epoch, RUN_PROTOCOL_BINDING_EPOCH),
        (stored.binding_record_version, RUN_PROTOCOL_BINDING_V1_VERSION),
    ):
        if actual != expected:
            raise UnsupportedRunProtocolBindingVersionError("unsupported native binding") from None
    try:
        envelope = s1.decode_run_protocol_envelope(
            stored.envelope_canonical, expected_epoch=stored.envelope_epoch,
            expected_version=stored.envelope_record_version,
        )
        profile = lookup_run_protocol_profile(envelope.profile_ref)
        if stored.resolver_epoch != s2.RUN_PROTOCOL_RESOLUTION_EPOCH or stored.resolver_record_version != 1:
            s2.resolve_run_protocol_objectives(
                envelope, s2.RunProtocolOverrideProposalV1(profile_ref=envelope.profile_ref, entries=()),
                expected_epoch=stored.resolver_epoch, expected_version=stored.resolver_record_version,
            )
        payload = _resolution_payload(stored.resolution_input_canonical)
        _require(
            type(payload["canonical_envelope_hex"]) is str
            and payload["canonical_envelope_hex"] == stored.envelope_canonical.hex(),
            "resolution envelope binding",
        )
        _require(
            type(payload["authorized_profile_id"]) is str
            and type(payload["authorized_profile_version"]) is int
            and payload["authorized_profile_id"] == envelope.profile_ref.profile_id.value
            and payload["authorized_profile_version"] == envelope.profile_ref.profile_version.value
            and profile.profile_ref == envelope.profile_ref,
            "resolution profile binding",
        )
        entries = payload["authorized_overrides"]
        if type(entries) is not list or len(entries) > 5:
            raise s2.RunProtocolResolutionIntegrityError("override array") from None
        overrides = []
        prior = -1
        for entry in entries:
            if type(entry) is not dict or set(entry) != {"parameter", "value"}:
                raise s2.RunProtocolResolutionIntegrityError("override members") from None
            if type(entry["parameter"]) is not str or entry["parameter"] not in _OBJECTIVES or type(entry["value"]) is not int:
                raise s2.RunProtocolResolutionIntegrityError("override types") from None
            ordinal = _OBJECTIVES.index(entry["parameter"])
            if ordinal <= prior:
                raise s2.RunProtocolResolutionIntegrityError("override order") from None
            prior = ordinal
            overrides.append(s2.RunProtocolObjectiveOverrideV1(
                parameter=s2.ObjectiveParameterName(entry["parameter"]),
                value=s2.ObjectiveParameterValue(value=entry["value"]),
            ))
        proposal = s2.RunProtocolOverrideProposalV1(profile_ref=envelope.profile_ref, entries=tuple(overrides))
        authorized = s2.validate_run_protocol_overrides(profile, proposal)
        resolution_input = s2.construct_run_protocol_resolution_input_v1(
            envelope, authorized_profile=profile, authorized_overrides=authorized,
        )
        if s2.encode_run_protocol_resolution_input_v1(resolution_input) != stored.resolution_input_canonical:
            raise s2.RunProtocolResolutionIntegrityError("noncanonical resolution bytes") from None
        resolved = s2.resolve_run_protocol_objectives(
            envelope, proposal, expected_epoch=stored.resolver_epoch,
            expected_version=stored.resolver_record_version,
        )
        for name in _OBJECTIVES:
            _require(getattr(stored, name) == getattr(resolved.final_values, name).value, "stored objective mismatch")
        _require(stored.resolution_fingerprint == bytes.fromhex(resolved.fingerprint.value), "stored fingerprint mismatch")
        _require(resolved.resolution_input == resolution_input, "resolved input association")
        if legacy_proof is not None:
            _require(
                type(legacy_proof) is LegacyRunCompatibilityV1
                and legacy_proof.canonical_run == run,
                "legacy context association",
            )
            raise ContradictoryRunFamilyError("complete legacy and native proofs") from None
        return NativeRunProtocolBindingV1(
            run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
            bound_state_version=RunStateVersion(value=stored.bound_state_version),
            resolved_protocol=resolved,
        )
    except (RunProtocolBindingStoredIntegrityError, RunProtocolBindingRepositoryError):
        raise
    except (TypeError, ValueError, AttributeError) as error:
        raise RunProtocolBindingStoredIntegrityError("native stored reconstruction failed") from error


def _utc(value):
    _require(type(value) is datetime, "stored datetime type")
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    _require(value.utcoffset().total_seconds() == 0, "stored datetime must be UTC")
    return value


def _stored_record(row, carrier):
    from deviation_protocol.domain.run import RunId, ContinuousStoryLineId, RunOperationId, RunAuthoritySourceRef
    from deviation_protocol.domain.player_character import PlayerCharacterId, ControllerBindingRef, AuthoritySourceRef
    from deviation_protocol.infrastructure import player_character_persistence as character_storage
    from deviation_protocol.infrastructure.run_persistence import StoredRunRevisionRecord

    character = carrier in (character_storage.StoredPlayerCharacterRevisionRecord, character_storage.StoredCurrentPlayerCharacterRecord)
    wrappers = {
        "run_id": RunId, "result_run_id": RunId,
        "continuous_story_line_id": ContinuousStoryLineId,
        "result_continuous_story_line_id": ContinuousStoryLineId,
        "operation_id": RunOperationId, "creation_operation_id": RunOperationId,
        "source_reference": AuthoritySourceRef if character else RunAuthoritySourceRef,
        "creation_source_reference": RunAuthoritySourceRef,
        "player_character_id": PlayerCharacterId, "controller_binding": ControllerBindingRef,
    }
    values = {}
    state = vars(row)
    for field in fields(carrier):
        name = field.name
        if carrier is StoredRunRevisionRecord and name == "active_player_character_id":
            values[name] = None
            continue
        _require(name in state, "missing stored column: " + name)
        value = state[name]
        if name in wrappers:
            value = wrappers[name](value=value)
        elif value is not None and (name.endswith("_at") or name == "creation_occurred_at"):
            value = _utc(value)
        values[name] = value
    return carrier(**values)


def _reference_from_current(current):
    from deviation_protocol.domain.player_character import (
        ApplicableCharacterReference, PlayerCharacterId,
        PlayerCharacterContractVersion, PlayerCharacterRevision,
    )
    values = (current.binding_player_character_id, current.binding_contract_version, current.binding_record_revision)
    if all(value is None for value in values):
        return None
    _require(all(value is not None for value in values), "partial character reference")
    _require(
        type(values[0]) is str and type(values[1]) is str
        and type(values[2]) is int and 1 <= values[2] <= 2**63 - 1,
        "physical character reference",
    )
    identity = PlayerCharacterId(value=values[0])
    contract = PlayerCharacterContractVersion(values[1])
    revision = PlayerCharacterRevision(value=values[2])
    return ApplicableCharacterReference(
        player_character_id=identity, contract_version=contract, record_revision=revision,
    )


def _legacy_entry_evidence(run, revisions, creation, mutations, participations):
    from deviation_protocol.application.run_operations import RunEntryCreationEvidence, RunEntryPublicOperationKey, derive_run_entry_internal_id
    from deviation_protocol.infrastructure.run_persistence import creation_evidence_from_storage

    evidence = creation_evidence_from_storage(creation.operation_evidence_canonical)
    if type(evidence) is not RunEntryCreationEvidence:
        return None
    _require(
        tuple(item.state_version for item in revisions) == (1, 2, 3)
        and tuple(item.mutation_kind for item in revisions) == ("CREATE", "BIND_PLAYER_CHARACTER", "ATTACH_SESSION")
        and tuple(item.lifecycle_status for item in revisions) == ("pre_first_turn", "pre_first_turn", "active")
        and len(mutations) == 2 and len(participations) == 1,
        "incomplete legacy entry family",
    )
    operation_ids = tuple(
        derive_run_entry_internal_id(
            purpose=purpose,
            controller_binding=evidence.controller_operation.controller_binding,
            public_operation_key=RunEntryPublicOperationKey(value=evidence.controller_operation.public_operation_key),
        )
        for purpose in ("run.create/v1", "run.bind-player-character/v1", "run.attach-session/v1", "session.create/v1")
    )
    _require(tuple(item.operation_id.value for item in revisions) == operation_ids[:3], "legacy operation identities")
    _require(
        run.player_character_binding.bound_at == run.creation_provenance.occurred_at,
        "legacy binding time differs from entry transaction time",
    )
    return evidence, operation_ids[3]


def _validate_legacy_character(run, evidence, immutable, current_row, controller_row):
    from deviation_protocol.infrastructure.player_character_persistence import StoredCurrentPlayerCharacterRecord, canonical_record_from_current_storage

    _require(current_row is not None, "missing current character")
    current = canonical_record_from_current_storage(_stored_record(current_row, StoredCurrentPlayerCharacterRecord))
    _require(current == immutable, "current character differs from immutable reference")
    _require(
        run.player_character_binding.applicable_character_reference.player_character_id
        == current.player_character_id == evidence.player_character.player_character_id
        and current.record_revision == evidence.player_character.pre_entry_record_revision,
        "legacy character evidence",
    )
    _require(controller_row is not None, "missing controller binding")
    _require(
        evidence.controller_operation.controller_binding == immutable.controller_binding
        and vars(current_row)["controller_binding"] == immutable.controller_binding.value
        and vars(controller_row).get("controller_binding") == immutable.controller_binding.value,
        "legacy controller evidence",
    )
    _utc(vars(controller_row).get("created_at"))


def _validate_legacy_session(run, evidence, creation_request_id, participation, session_row, event_row, snapshot_row):
    _validate_entry_session_fields(run, evidence, creation_request_id, participation, session_row, event_row, snapshot_row)
    return LegacyRunCompatibilityV1(canonical_run=run, session_id=participation.session_id)


def _validate_entry_session_fields(run, evidence, creation_request_id, participation, session_row, event_row, snapshot_row):
    from copy import deepcopy
    from deviation_protocol.domain.state import GameState

    _require(all(row is not None for row in (session_row, event_row, snapshot_row)), "missing legacy Session family")
    session = vars(session_row)
    event = vars(event_row)
    snapshot = vars(snapshot_row)
    for name, maximum in (
        ("session_id", 64), ("player_id", 64), ("scenario_id", 128),
        ("character_definition_id", 128), ("scenario_version", 32),
    ):
        value = session.get(name)
        _require(type(value) is str and 1 <= len(value) <= maximum and _OPAQUE.fullmatch(value) is not None, "Session " + name)
    _require(type(session.get("phase")) is str and 1 <= len(session["phase"]) <= 32, "Session phase")
    for name in ("turn_number", "state_version", "random_seed"):
        value = session.get(name)
        _require(type(value) is int and 0 <= value <= 2**63 - 1, "Session " + name)
    request = session.get("creation_client_request_id")
    _require(type(request) is str and re.fullmatch(r"[0-9a-f]{64}", request) is not None, "Session creation request")
    created_at = _utc(session.get("created_at"))
    _utc(session.get("updated_at"))
    _require(type(snapshot.get("state_version")) is int and snapshot["state_version"] == session["state_version"], "snapshot version")
    original = deepcopy(snapshot.get("state_json"))
    _require(type(original) is dict and type(original.get("schema_version")) is int and original["schema_version"] == 3, "snapshot schema")
    encoded = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    state = GameState.model_validate_json(encoded, strict=True)
    _require(state.to_snapshot() == original, "snapshot canonical form")
    scenario = evidence.scenario
    _require(
        state.player.player_id == session["player_id"]
        and session["scenario_id"] == scenario.scenario_id
        and session["scenario_version"] == state.content_version == scenario.content_version
        and session["character_definition_id"] == state.player.character_definition_id == scenario.default_character_definition_id,
        "Session content association",
    )
    for name, maximum in (("event_id", 64), ("session_id", 64), ("turn_id", 64), ("event_type", 128)):
        value = event.get(name)
        _require(type(value) is str and 1 <= len(value) <= maximum and _OPAQUE.fullmatch(value) is not None, "event " + name)
    _require(type(event.get("sequence_no")) is int and event["sequence_no"] == 1, "initial event sequence")
    _require(type(event.get("payload_json")) is dict, "event payload type")
    _utc(snapshot.get("updated_at"))
    transaction_time = run.creation_provenance.occurred_at
    _require(
        session["session_id"] == participation.session_id == event["session_id"] == snapshot.get("session_id")
        and request == creation_request_id and event["turn_id"] == "session-created"
        and event["event_type"] == "ScenarioStarted"
        and event["payload_json"] == {"scenario_id": scenario.scenario_id, "scenario_content_version": scenario.content_version}
        and _utc(event.get("occurred_at")) == created_at == participation.joined_at == transaction_time,
        "legacy initialization evidence",
    )
    runtime = state.scenario_runtime
    _require(
        runtime is not None and runtime.scenario_id == scenario.scenario_id
        and runtime.scenario_content_version == scenario.content_version,
        "legacy scenario runtime",
    )
    records = tuple(item for item in state.player_memory.scenario_records if item.scenario_id == scenario.scenario_id)
    _require(len(records) == 1 and records[0].scenario_content_version == scenario.content_version, "legacy scenario memory")
    record = records[0]
    if session["state_version"] == 0:
        _require(
            session["turn_number"] == 0 and session["phase"] == "AWAITING_ACTION"
            and runtime.ending_status.value == "ACTIVE"
            and record.status.value == "STARTED" and record.ending_id is None
            and any(item.value == "STARTED" for item in record.milestone_refs)
            and record.last_source_event_id == event["event_id"]
            and record.last_source_sequence_no == 1
            and state.player_memory.last_applied_source_sequence_no == 1
            and state.player_memory.last_applied_source_event_id == event["event_id"],
            "initial Session memory",
        )
    source = evidence.trusted_run_source.source_reference
    _require(
        source == run.creation_provenance.source_reference
        == run.player_character_binding.binding_authority_source_ref
        == run.current_mutation_provenance.source_reference
        == participation.source_reference,
        "legacy source consistency",
    )


@dataclass(frozen=True, slots=True)
class _StoredRunEntryWorldBindingV1:
    run_id: str
    continuous_story_line_id: str
    bound_state_version: int
    binding_epoch: str
    binding_record_version: int
    entry_world_id: str
    entry_world_version: int
    scenario_id: str
    scenario_content_version: str
    default_character_definition_id: str
    created_at: datetime


def _stored_world_from_row(row, session):
    from sqlalchemy import inspect
    from deviation_protocol.infrastructure.orm_models import RunEntryWorldBindingRow
    _require(type(row) is RunEntryWorldBindingRow, "world row type")
    state = inspect(row)
    names = {f.name for f in fields(_StoredRunEntryWorldBindingV1)}
    _require(state.session is session.sync_session and state.persistent
             and not state.modified and not state.expired_attributes and not state.unloaded
             and set(vars(row)) == names | {"_sa_instance_state"}
             and state.key == (RunEntryWorldBindingRow, (row.run_id,), None), "world row original state")
    return _StoredRunEntryWorldBindingV1(**{name: vars(row)[name] for name in names})


def _reconstruct_world_binding(stored, run):
    from deviation_protocol.domain.entry_world import EntryWorldRefV1, EntryWorldId, EntryWorldVersion, lookup_entry_world
    from deviation_protocol.domain.run_protocol_binding import RunEntryWorldBindingV1
    _require(type(stored) is _StoredRunEntryWorldBindingV1, "world storage carrier")
    for name, maximum in (("run_id", 128), ("continuous_story_line_id", 128), ("entry_world_id", 128),
                          ("scenario_id", 128), ("scenario_content_version", 32), ("default_character_definition_id", 128)):
        value = getattr(stored, name)
        _require(type(value) is str and 1 <= len(value) <= maximum and value.isascii()
                 and _OPAQUE.fullmatch(value) is not None, "world " + name)
    _require(type(stored.binding_epoch) is str and stored.binding_epoch == "run-entry-world-binding", "world epoch")
    _require(type(stored.bound_state_version) is int and stored.bound_state_version == 3
             and type(stored.binding_record_version) is int and stored.binding_record_version == 1
             and type(stored.entry_world_version) is int and 1 <= stored.entry_world_version <= 2**63 - 1, "world versions")
    _require(type(stored.created_at) is datetime and stored.created_at.tzinfo is None
             and stored.created_at.replace(tzinfo=UTC) == run.creation_provenance.occurred_at, "world timestamp")
    _require(stored.run_id == run.run_id.value and stored.continuous_story_line_id == run.continuous_story_line_id.value
             and run.state_version.value == 3, "world Run association")
    try:
        world = lookup_entry_world(EntryWorldRefV1(entry_world_id=EntryWorldId(value=stored.entry_world_id),
                                                 entry_world_version=EntryWorldVersion(value=stored.entry_world_version)))
    except (ValueError, TypeError, AttributeError) as error:
        raise RunProtocolBindingStoredIntegrityError("world authority validation") from error
    _require((world.scenario_id, world.scenario_content_version, world.default_character_definition_id)
             == (stored.scenario_id, stored.scenario_content_version, stored.default_character_definition_id), "world scenario mapping")
    return RunEntryWorldBindingV1(run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
                                  bound_state_version=RunStateVersion(value=3), entry_world=world)


def _validate_native_receipt_protocol(evidence, stored):
    # These are deliberately separate assertions: internal S3 consistency proves neither.
    _require(bytes.fromhex(evidence.resolution_input_hex) == stored.resolution_input_canonical,
             "native receipt resolution input differs from binding")
    _require(evidence.resolution_fingerprint == stored.resolution_fingerprint.hex(),
             "native receipt resolution fingerprint differs from binding")


def _native_binding_values(binding, *, created_at):
    from deviation_protocol.domain.run import revalidate_run_model, _require_exact_utc_datetime
    revalidate_run_model(binding, NativeRunProtocolBindingV1)
    _require_exact_utc_datetime(created_at)
    if binding.bound_state_version.value != 3:
        raise ValueError("native writer requires revision three")
    resolved = binding.resolved_protocol
    envelope = resolved.resolution_input.envelope
    values = dict(run_id=binding.run_id.value, continuous_story_line_id=binding.continuous_story_line_id.value,
                  bound_state_version=3, family_discriminator=RUN_FAMILY_NATIVE_V1,
                  binding_epoch=RUN_PROTOCOL_BINDING_EPOCH, binding_record_version=1,
                  envelope_epoch=s1.RUN_PROTOCOL_ENVELOPE_EPOCH, envelope_record_version=1,
                  envelope_canonical=s1.encode_run_protocol_envelope_v1(envelope),
                  resolver_epoch=s2.RUN_PROTOCOL_RESOLUTION_EPOCH, resolver_record_version=1,
                  resolution_input_canonical=s2.encode_run_protocol_resolution_input_v1(resolved.resolution_input),
                  resolution_fingerprint=bytes.fromhex(resolved.fingerprint.value), created_at=created_at.replace(tzinfo=None))
    values.update({name: getattr(resolved.final_values, name).value for name in _OBJECTIVES})
    return values


def _world_binding_values(binding, *, created_at):
    from deviation_protocol.domain.run import revalidate_run_model, _require_exact_utc_datetime
    from deviation_protocol.domain.run_protocol_binding import RunEntryWorldBindingV1
    from deviation_protocol.domain.entry_world import EntryWorldRefV1, lookup_entry_world
    revalidate_run_model(binding, RunEntryWorldBindingV1)
    _require_exact_utc_datetime(created_at)
    world = binding.entry_world
    reference = EntryWorldRefV1(entry_world_id=world.entry_world_id, entry_world_version=world.entry_world_version)
    if world != lookup_entry_world(reference):
        raise ValueError("world writer requires authored mapping")
    return dict(run_id=binding.run_id.value, continuous_story_line_id=binding.continuous_story_line_id.value,
                bound_state_version=3, binding_epoch="run-entry-world-binding", binding_record_version=1,
                entry_world_id=world.entry_world_id.value, entry_world_version=world.entry_world_version.value,
                scenario_id=world.scenario_id, scenario_content_version=world.scenario_content_version,
                default_character_definition_id=world.default_character_definition_id,
                created_at=created_at.replace(tzinfo=None))


def _native_entry_evidence(run, revisions, creation, mutations, participations, evidence, protocol, world, stored):
    from deviation_protocol.application.native_run_admission import derive_native_run_entry_internal_id
    from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
    _validate_native_receipt_protocol(evidence, stored)
    _require(tuple(r.state_version for r in revisions) == (1, 2, 3)
             and tuple(r.mutation_kind for r in revisions) == ("CREATE", "BIND_PLAYER_CHARACTER", "ATTACH_SESSION")
             and len(mutations) == 2 and len(participations) == 1
             and protocol.bound_state_version.value == world.bound_state_version.value == run.state_version.value == 3,
             "native revision family")
    ids = tuple(derive_native_run_entry_internal_id(purpose=purpose,
                controller_binding=evidence.controller_operation.controller_binding,
                public_operation_key=RunEntryPublicOperationKey(value=evidence.controller_operation.public_operation_key))
                for purpose in ("run.create/v1", "run.bind-player-character/v1", "run.attach-session/v1", "session.create/v1"))
    _require(tuple(r.operation_id.value for r in revisions) == ids[:3], "native operation identities")
    time = run.creation_provenance.occurred_at
    _require(all(r.created_at == time for r in revisions) and all(r.created_at == time for r in mutations)
             and creation.created_at == time and run.player_character_binding.bound_at == time
             and run.current_mutation_provenance.occurred_at == time
             and stored.created_at.replace(tzinfo=UTC) == time, "native transaction timestamp")
    authored = world.entry_world
    _require(evidence.entry_world.entry_world_id == authored.entry_world_id
             and evidence.entry_world.entry_world_version == authored.entry_world_version
             and evidence.scenario.scenario_id == authored.scenario_id
             and evidence.scenario.content_version == authored.scenario_content_version
             and evidence.scenario.default_character_definition_id == authored.default_character_definition_id, "native evidence world association")
    return ids[3]


def _validate_native_character(run, evidence, immutable, current_row, controller_row):
    from deviation_protocol.infrastructure.player_character_persistence import StoredCurrentPlayerCharacterRecord, canonical_record_from_current_storage
    _require(immutable is not None and current_row is not None and controller_row is not None, "missing native character authority")
    current = canonical_record_from_current_storage(_stored_record(current_row, StoredCurrentPlayerCharacterRecord))
    reference = run.player_character_binding.applicable_character_reference
    _require(current.player_character_id == immutable.player_character_id == reference.player_character_id
             == evidence.player_character.player_character_id
             and reference.record_revision == immutable.record_revision == evidence.player_character.pre_entry_record_revision
             and current.record_revision.value >= immutable.record_revision.value
             and current.controller_binding == immutable.controller_binding == evidence.controller_operation.controller_binding
             and vars(controller_row).get("controller_binding") == immutable.controller_binding.value, "native character authority association")
    _utc(vars(controller_row).get("created_at"))


def _complete_native_admission(run, protocol, world, evidence, request_id, participation, session_row, event_row, snapshot_row):
    from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1
    _validate_entry_session_fields(run, evidence, request_id, participation, session_row, event_row, snapshot_row)
    _require(vars(session_row)["player_id"] == evidence.player_id, "native Session player association")
    return NativeRunAdmissionV1(canonical_run=run, protocol_binding=protocol, world_binding=world)


def _native_admission_prefix(run, revisions, mutations):
    from deviation_protocol.domain.run import RunLifecycleStatus
    from deviation_protocol.infrastructure.run_persistence import canonical_run_from_revision_storage
    if run.lifecycle_status is not RunLifecycleStatus.TERMINATED:
        return run, revisions, mutations
    _require(tuple(r.state_version for r in revisions) == (1, 2, 3, 4)
             and tuple(r.resulting_state_version for r in mutations) == (2, 3, 4), "terminal history shape")
    prefix = canonical_run_from_revision_storage(revisions[2], participations=run.trusted_participation_references)
    return prefix, revisions[:3], mutations[:2]


def _complete_native_family(admission, run, mutations, creation_evidence, session_row, snapshot_row):
    from deviation_protocol.domain.run import RunLifecycleStatus
    from deviation_protocol.domain.run_protocol_binding import NativeRunTerminatedV1, decode_native_run_exit_evidence
    from deviation_protocol.domain.state import GameState
    from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
    if run.lifecycle_status is not RunLifecycleStatus.TERMINATED:
        return admission
    evidence = decode_native_run_exit_evidence(mutations[-1].operation_evidence_canonical)
    request = evidence.request
    state = GameState.model_validate_json(json.dumps(vars(snapshot_row)["state_json"], ensure_ascii=False), strict=True)
    runtime = state.scenario_runtime
    records = tuple(r for r in state.player_memory.scenario_records if r.scenario_id == evidence.scenario_id)
    _require(vars(session_row)["state_version"] == vars(snapshot_row)["state_version"] == evidence.session_state_version
             and request.player_id == creation_evidence.player_id == vars(session_row)["player_id"]
             and request.controller_binding == creation_evidence.controller_operation.controller_binding.value
             and runtime is not None and runtime.ending_status.value == evidence.ending_status
             and runtime.ending_id == evidence.ending_id
             and runtime.scenario_id == evidence.scenario_id
             and runtime.scenario_content_version == state.content_version == evidence.scenario_content_version
             and len(records) == 1 and records[0].status.value == "COMPLETED"
             and records[0].ending_id == evidence.ending_id
             and records[0].scenario_content_version == evidence.scenario_content_version
             and state_fingerprint(state) == evidence.snapshot_sha256, "terminal ending evidence")
    return NativeRunTerminatedV1(admission=admission, canonical_run=run, exit_evidence=evidence)
