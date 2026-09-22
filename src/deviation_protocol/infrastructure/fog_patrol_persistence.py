"""Storage codec for one root/two visits and the separate patrol entry."""
from datetime import datetime

from deviation_protocol.application.fog_history import event_records, verify_history
from deviation_protocol.application.fog_patrol import FogPatrolPolicy, CONTENT_SHA256
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.session_content_registry import SessionContentRegistry
from deviation_protocol.domain.fog_patrol import (
    FogSourceV1, FogEntryV1, FogVisitV1, FogContinuedV1, FogTerminatedV1,
    FogContinuationEvidenceV1, FogExitEvidenceV1, SOURCE, DESTINATION, WORLD, SOURCE_REGION,
    decode_fog, continue_fog_run,
)
from deviation_protocol.domain.run import revalidate_run_model
from deviation_protocol.domain.world_continuation import snapshot_canonical_bytes
from deviation_protocol.infrastructure.run_protocol_binding_persistence import _require, _utc
from deviation_protocol.infrastructure.world_continuation_persistence import (
    _columns, ROOT_COLUMNS, position_from_storage, _ended,
)


def source_to_storage(root, *, created_at):
    revalidate_run_model(root, FogSourceV1)
    return dict(run_id=root.run_id, continuous_story_line_id=root.continuous_story_line_id,
        world_id=WORLD, world_version=1, first_visit_id=root.first_visit_id,
        scenario_id=root.scenario_id, scenario_content_version=root.scenario_content_version,
        region_id=SOURCE_REGION, region_version=1, state_schema=root.schema_version,
        state_canonical=root.canonical_bytes(), state_sha256=bytes.fromhex(root.digest()),
        materialized_state_version=4, created_at=created_at)


def entry_to_storage(entry, *, created_at):
    revalidate_run_model(entry, FogEntryV1)
    return dict(run_id=entry.run_id, continuous_story_line_id=entry.continuous_story_line_id,
        visit_id=entry.visit_id, session_id=entry.session_id, joined_state_version=4,
        entry_schema=entry.schema_version, entry_canonical=entry.canonical_bytes(),
        entry_sha256=bytes.fromhex(entry.digest()), created_at=created_at)


def fog_rows(family):
    revalidate_run_model(family, FogContinuedV1)
    time = family.canonical_run.current_mutation_provenance.occurred_at
    return [("run_world_states", (family.source_root.run_id, WORLD), source_to_storage(family.source_root, created_at=time)),
        *[("run_world_visits", (v.run_id, v.visit_id), v.model_dump()) for v in family.visits],
        ("run_world_visit_entries", (family.entry.run_id, family.entry.visit_id), entry_to_storage(family.entry, created_at=time)),
        ("run_world_positions", family.position.run_id, family.position.model_dump())]


def _row_matches(row, expected):
    values = _columns(row, expected)
    for key, value in expected.items():
        if isinstance(value, datetime):
            values[key] = _utc(values[key])
        else:
            _require(type(values[key]) is type(value), "fog row original type")
    _require(values == expected, "fog row/payload association")


def reconstruct_fog_family(*, admission, run, mutations, creation_evidence,
        roots, visits, positions, entries, source_session, source_snapshot, source_events,
        destination_session, destination_snapshot, destination_event, registry):
    _require(type(registry) is SessionContentRegistry, "fog registry unavailable")
    _require(len(roots) == 1 and len(visits) == 2 and len(positions) == 1 and len(entries) == 1,
        "fog family row cardinality")
    evidence = decode_fog(mutations[2].operation_evidence_canonical, FogContinuationEvidenceV1)
    request = evidence.request
    time = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    source = decode_fog(_columns(roots[0], ROOT_COLUMNS)["state_canonical"], FogSourceV1)
    entry = decode_fog(entries[0].entry_canonical, FogEntryV1)
    _row_matches(roots[0], source_to_storage(source, created_at=time))
    _row_matches(entries[0], entry_to_storage(entry, created_at=time))
    decoded_visits = []
    for row in visits:
        values = _columns(row, FogVisitV1.model_fields)
        for key in ("created_at", "entered_at"):
            values[key] = _utc(values[key])
        decoded_visits.append(FogVisitV1.model_validate(values, strict=True))
    continued = FogContinuedV1(admission=admission, canonical_run=continue_fog_run(admission, evidence),
        continuation_evidence=evidence, source_root=source, entry=entry,
        visits=tuple(sorted(decoded_visits, key=lambda v: v.visit_ordinal)),
        position=position_from_storage(positions[0]))
    _require(all(row is not None for row in (source_session, source_snapshot, destination_session,
        destination_snapshot, destination_event)), "missing fog Session evidence")
    ss, sp, ds, dp, de = map(vars, (source_session, source_snapshot, destination_session, destination_snapshot, destination_event))
    _require(request.player_id == creation_evidence.player_id == ss["player_id"] == ds["player_id"]
        and request.controller_binding == creation_evidence.controller_operation.controller_binding.value
        and ss["session_id"] == sp["session_id"] == source.session_id
        and (ss["scenario_id"], ss["scenario_version"]) == SOURCE
        and type(ss["state_version"]) is int and type(sp["state_version"]) is int
        and ss["state_version"] == sp["state_version"] == source.snapshot_state_version
        and snapshot_canonical_bytes(sp["state_json"]) == snapshot_canonical_bytes(source.snapshot),
        "fog sealed source state/owner")
    source_bundle = registry.resolve(*SOURCE)
    source_state = source_bundle.validate_snapshot(source.snapshot)
    records = event_records(source_events)
    _require(records == source.events, "fog source committed evidence changed")
    verify_history(source_bundle, source_state, source.session_id, source.snapshot_state_version, records)
    bundle = registry.resolve(*DESTINATION)
    _require(entry.content_sha256 == bundle.content_sha256 == CONTENT_SHA256, "fog target exact content")
    initial = bundle.validate_snapshot(entry.snapshot)
    definition = bundle.scenario_catalog.scenarios[0]
    policy = FogPatrolPolicy()
    _require(policy.validate(initial, entry.session_id, definition) == (), "fog initial path")
    for key in ("state_version", "turn_number", "random_seed"):
        _require(type(ds[key]) is int and 0 <= ds[key] <= 2**63 - 1, "fog Session scalar")
    _require(type(dp["state_version"]) is int and dp["state_version"] == ds["state_version"]
        and ds["session_id"] == dp["session_id"] == de["session_id"] == entry.session_id
        and (ds["scenario_id"], ds["scenario_version"]) == DESTINATION
        and ds["character_definition_id"] == initial.player.character_definition_id
        and ds["creation_client_request_id"] == evidence.destination_creation_request_id
        and ds["random_seed"] == evidence.destination_random_seed
        and _utc(ds["created_at"]) == _utc(de["occurred_at"]) == time
        and _utc(ds["updated_at"]) >= time and _utc(dp["updated_at"]) >= time
        and type(de["sequence_no"]) is int and de["sequence_no"] == 1
        and de["event_id"] == evidence.destination_initial_event_id
        and de["turn_id"] == "session-created" and de["event_type"] == "ScenarioStarted"
        and de["payload_json"] == {"scenario_id": DESTINATION[0], "scenario_content_version": DESTINATION[1]},
        "fog target initialization identity")
    from deviation_protocol.application.scenario_initialization import initialize_scenario_state
    from deviation_protocol.application.story_director import DeterministicStoryDirector
    from deviation_protocol.domain.state import GameState
    from deviation_protocol.domain.player_memory import PlayerMemoryState, ScenarioMemoryRecord, ScenarioMemoryStatus, ScenarioMemoryMilestone
    character = bundle.scenario_catalog.content_catalog.character(initial.player.character_definition_id)
    expected = initialize_scenario_state(GameState(content_version=DESTINATION[1],
        player=source_state.player.model_copy(deep=True)), bundle.scenario_catalog.content_catalog,
        definition, character_tags=character.tags, story_director=DeterministicStoryDirector()).candidate_state
    policy.initialize(expected, entry.session_id, definition)
    expected.player_memory = PlayerMemoryState(last_applied_source_sequence_no=1,
        last_applied_source_event_id=evidence.destination_initial_event_id,
        scenario_records=(ScenarioMemoryRecord(scenario_id=DESTINATION[0], scenario_content_version=DESTINATION[1],
            status=ScenarioMemoryStatus.STARTED, milestone_refs=(ScenarioMemoryMilestone.STARTED,),
            last_source_event_id=evidence.destination_initial_event_id, last_source_sequence_no=1),))
    _require(expected.to_snapshot() == initial.to_snapshot(), "fog fresh initialization/complete PlayerState")
    latest = bundle.validate_snapshot(dp["state_json"])
    codes = policy.validate(latest, entry.session_id, definition)
    _require(ds["state_version"] == len(codes) and ds["turn_number"] == 0
        and latest.player == initial.player and latest.npcs == initial.npcs, "fog target state invariants")
    if not codes:
        _require(latest.to_snapshot() == initial.to_snapshot(), "fog entry snapshot")
    if run.state_version.value == 4:
        _require(run == continued.canonical_run and len(mutations) == 3, "fog active suffix")
        return continued
    _require(run.state_version.value == 5 and len(mutations) == 4, "fog terminal suffix")
    exit_evidence = decode_fog(mutations[-1].operation_evidence_canonical, FogExitEvidenceV1)
    _ended(latest, ending_id=exit_evidence.ending_id, ending_status="RESOLVED")
    _require(exit_evidence.request.player_id == request.player_id
        and exit_evidence.request.controller_binding == request.controller_binding
        and exit_evidence.session_state_version == ds["state_version"]
        and exit_evidence.snapshot_sha256 == state_fingerprint(latest), "fog exit binding")
    return FogTerminatedV1(continued=continued, canonical_run=run, exit_evidence=exit_evidence)
