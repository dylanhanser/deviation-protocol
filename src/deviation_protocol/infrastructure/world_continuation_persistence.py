"""Strict storage codecs for the closed two-visit continuation family."""
from __future__ import annotations

from datetime import datetime
import hashlib

from deviation_protocol.application.session_content_registry import SessionContentRegistry
from deviation_protocol.domain.run import revalidate_run_model
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunContinuedV1, NativeRunContinuedTerminatedV1,
    continue_native_run, decode_continued_native_run_exit_evidence,
)
from deviation_protocol.domain.world_continuation import (
    WorldStateRootV1, WorldVisitV1, WorldPositionV1,
    decode_world_state_root, decode_native_run_continuation_evidence,
    snapshot_canonical_bytes,
)
from deviation_protocol.infrastructure.run_protocol_binding_persistence import _require, _utc


ROOT_COLUMNS = frozenset(("run_id", "continuous_story_line_id", "world_id", "world_version",
    "first_visit_id", "scenario_id", "scenario_content_version", "region_id", "region_version",
    "state_schema", "state_canonical", "state_sha256", "materialized_state_version", "created_at"))


def _columns(row, names):
    values = dict(vars(row))
    values.pop("_sa_instance_state", None)
    _require(set(values) == set(names), "world storage columns")
    return values


def root_to_storage(root: WorldStateRootV1, *, created_at: datetime) -> dict:
    revalidate_run_model(root, WorldStateRootV1)
    _utc(created_at)
    return dict(run_id=root.run_id, continuous_story_line_id=root.continuous_story_line_id,
        world_id=root.world.world_id,world_version=root.world.world_version,
        first_visit_id=root.first_visit_id,scenario_id=root.scenario_id,
        scenario_content_version=root.scenario_content_version,
        region_id=root.region.region_id,region_version=root.region.region_version,
        state_schema=root.schema_version,state_canonical=root.canonical_bytes(),
        state_sha256=bytes.fromhex(root.digest()),materialized_state_version=4,created_at=created_at)


def root_from_storage(row, *, created_at: datetime) -> WorldStateRootV1:
    values = _columns(row, ROOT_COLUMNS)
    root = decode_world_state_root(values["state_canonical"])
    _require(type(values["state_sha256"]) is bytes and len(values["state_sha256"]) == 32,
             "root digest original bytes")
    for key in ("world_version", "region_version", "materialized_state_version"):
        _require(type(values[key]) is int, "root version original scalar")
    values["created_at"] = _utc(values["created_at"])
    _require(values == root_to_storage(root, created_at=created_at), "root row/payload association")
    return root


def visit_from_storage(row) -> WorldVisitV1:
    values = _columns(row, WorldVisitV1.model_fields)
    for key in ("entered_at", "created_at"):
        values[key] = _utc(values[key])
    return WorldVisitV1.model_validate(values, strict=True)


def position_from_storage(row) -> WorldPositionV1:
    values = _columns(row, WorldPositionV1.model_fields)
    values["created_at"] = _utc(values["created_at"])
    return WorldPositionV1.model_validate(values, strict=True)


def _ended(state, *, ending_id, ending_status):
    runtime = state.scenario_runtime
    _require(runtime is not None and runtime.ending_id == ending_id
        and runtime.ending_status.value == ending_status, "sealed ending/runtime mismatch")
    records = state.player_memory.scenario_records
    _require(len(records) == 1 and records[0].scenario_id == runtime.scenario_id
        and records[0].scenario_content_version == state.content_version
        and records[0].status.value == "COMPLETED" and records[0].ending_id == ending_id,
        "sealed ending/completed memory mismatch")


def reconstruct_continued_family(*, admission, run, mutations, creation_evidence,
        roots, visits, positions, source_session, source_snapshot,
        destination_session, destination_snapshot, destination_event,
        registry: SessionContentRegistry):
    _require(type(registry) is SessionContentRegistry, "continuation content registry unavailable")
    _require(len(roots) == 2 and len(visits) == 2 and len(positions) == 1,
             "incomplete or extra continuation family rows")
    evidence = decode_native_run_continuation_evidence(mutations[2].operation_evidence_canonical)
    request = evidence.request
    time = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    decoded_roots = tuple(root_from_storage(row, created_at=time) for row in roots)
    by_basis = {root.basis: root for root in decoded_roots}
    _require(set(by_basis) == {"sealed_ending", "session_initialization"}, "world root roles")
    source, destination = by_basis["sealed_ending"], by_basis["session_initialization"]
    decoded_visits = tuple(sorted((visit_from_storage(row) for row in visits), key=lambda x:x.visit_ordinal))
    continued = NativeRunContinuedV1(admission=admission,
        canonical_run=continue_native_run(admission,evidence), continuation_evidence=evidence,
        source_root=source,destination_root=destination,visits=decoded_visits,
        position=position_from_storage(positions[0]))
    _require(evidence.selection_inputs.eligible_pool == registry.continuation_pool(), "continuation pool/content identity")
    source_state = registry.validate_root(source)
    initial_state = registry.validate_root(destination)
    _ended(source_state,ending_id=evidence.source_ending.ending_id,ending_status=evidence.source_ending.ending_status)
    _require(all(row is not None for row in (source_session,source_snapshot,destination_session,destination_snapshot,destination_event)),
             "missing continuation Session evidence")
    ss, sp, ds, dp, de = map(vars,(source_session,source_snapshot,destination_session,destination_snapshot,destination_event))
    _require(request.player_id == creation_evidence.player_id == ss["player_id"] == ds["player_id"]
        and request.controller_binding == creation_evidence.controller_operation.controller_binding.value
        and ss["session_id"] == sp["session_id"] == source.session_id
        and ss["state_version"] == sp["state_version"] == source.snapshot_state_version
        and snapshot_canonical_bytes(sp["state_json"]) == snapshot_canonical_bytes(source.snapshot), "sealed source state/owner")
    for key in ("state_version", "turn_number", "random_seed"):
        _require(type(ds.get(key)) is int and 0 <= ds[key] <= 2**63-1, "destination Session scalar")
    _require(type(dp.get("state_version")) is int and dp["state_version"] == ds["state_version"], "destination snapshot version")
    _require(ds["session_id"] == dp["session_id"] == de["session_id"] == destination.session_id
        and ds["scenario_id"] == destination.scenario_id
        and ds["scenario_version"] == destination.scenario_content_version
        and ds["character_definition_id"] == initial_state.player.character_definition_id
        and ds["creation_client_request_id"] == evidence.destination_creation_request_id
        and ds["random_seed"] == evidence.destination_random_seed
        and _utc(ds["created_at"]) == _utc(de["occurred_at"]) == time
        and _utc(ds["updated_at"]) >= time and _utc(dp["updated_at"]) >= time
        and type(de["sequence_no"]) is int and de["sequence_no"] == 1
        and de["event_id"] == evidence.destination_initial_event_id
        and de["turn_id"] == "session-created" and de["event_type"] == "ScenarioStarted"
        and de["payload_json"] == {"scenario_id":destination.scenario_id,"scenario_content_version":destination.scenario_content_version},
        "destination initialization/Session association")
    memory = initial_state.player_memory
    _require(initial_state.player.player_id == request.player_id
        and len(memory.scenario_records) == 1 and memory.scenario_records[0].status.value == "STARTED"
        and memory.scenario_records[0].last_source_event_id == evidence.destination_initial_event_id
        and memory.last_applied_source_sequence_no == 1
        and memory.last_applied_source_event_id == evidence.destination_initial_event_id,
        "destination initial memory evidence")
    # Compare the complete, closed initial memory without issuing mutation
    # authority or pretending that a read is a flushed event receipt.
    from deviation_protocol.domain.player_memory import (
        PlayerMemoryState, ScenarioMemoryRecord, ScenarioMemoryStatus, ScenarioMemoryMilestone, KnownPublicFactRecord,
    )
    initial_facts = tuple("undelivered_receipt.fact." + name for name in
        ("hold_is_not_delivery", "hold_prevents_dispatch", "receipt_absent", "schedule_complete"))
    expected_memory = PlayerMemoryState(last_applied_source_sequence_no=1,
        last_applied_source_event_id=evidence.destination_initial_event_id,
        scenario_records=(ScenarioMemoryRecord(scenario_id=destination.scenario_id,
            scenario_content_version=destination.scenario_content_version,
            status=ScenarioMemoryStatus.STARTED,
            milestone_refs=(ScenarioMemoryMilestone.STARTED,ScenarioMemoryMilestone.IMPORTANT_FACT_CONFIRMED),
            known_public_fact_refs=initial_facts,
            last_source_event_id=evidence.destination_initial_event_id,last_source_sequence_no=1),),
        known_public_facts=tuple(KnownPublicFactRecord(scenario_id=destination.scenario_id,fact_ref=fact,
            source_event_id=evidence.destination_initial_event_id,source_sequence_no=1) for fact in initial_facts))
    _require(memory == expected_memory, "destination initial memory must match its authored initialization")
    # Reconstruct the sealed initialization from the carried PlayerState and authored variant.
    from deviation_protocol.application.scenario_initialization import initialize_scenario_state
    from deviation_protocol.application.story_director import DeterministicStoryDirector
    from deviation_protocol.domain.state import GameState
    bundle = registry.resolve(destination.scenario_id,destination.scenario_content_version)
    character = bundle.scenario_catalog.content_catalog.character(initial_state.player.character_definition_id)
    expected = initialize_scenario_state(GameState(content_version=destination.scenario_content_version,
        player=source_state.player.model_copy(deep=True)),bundle.scenario_catalog.content_catalog,
        bundle.scenario_catalog.scenarios[0],character_tags=character.tags,
        story_director=DeterministicStoryDirector()).candidate_state
    expected.scenario_runtime.threat_clocks["dispatch_deadline"].value = 4 if evidence.entry_variant == "failed" else 0
    expected.player_memory = expected_memory
    _require(expected.to_snapshot() == initial_state.to_snapshot(), "destination sealed initialization")
    latest = bundle.validate_snapshot(dp["state_json"])
    _require(latest.player.player_id == request.player_id
        and latest.player.character_definition_id == initial_state.player.character_definition_id,
        "destination current player identity")
    if ds["state_version"] == 0:
        _require(ds["turn_number"] == 0 and ds["phase"] == "AWAITING_ACTION"
            and latest.to_snapshot() == destination.snapshot, "destination version zero root")
    if run.state_version.value == 4:
        _require(run == continued.canonical_run and len(mutations) == 3, "continued revision suffix")
        return continued
    _require(run.state_version.value == 5 and len(mutations) == 4, "continued terminal suffix")
    exit_evidence = decode_continued_native_run_exit_evidence(mutations[-1].operation_evidence_canonical)
    _ended(latest,ending_id=exit_evidence.ending_id,ending_status=exit_evidence.ending_status)
    _require(exit_evidence.request.player_id == request.player_id
        and exit_evidence.request.controller_binding == request.controller_binding
        and exit_evidence.session_state_version == ds["state_version"]
        and exit_evidence.snapshot_sha256 == hashlib.sha256(snapshot_canonical_bytes(dp["state_json"])).hexdigest(),
        "continued exit snapshot binding")
    return NativeRunContinuedTerminatedV1(continued=continued,canonical_run=run,exit_evidence=exit_evidence)
