"""Strict stored regional suffix over the independently reconstructed v1 prefix."""
from datetime import datetime
from types import SimpleNamespace

from deviation_protocol.domain.run import revalidate_run_model
from deviation_protocol.domain.scenario import EndingStatus
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1,
    continue_native_run, revisit_native_region, decode_revisited_native_run_exit_evidence,
)
from deviation_protocol.domain.world_continuation import (
    decode_native_run_continuation_evidence, WorldPositionV1,
)
from deviation_protocol.domain.world_revisit import (
    RegionalEntryV1, WorldVisitV2, WorldPositionV2, decode_regional_entry,
    decode_native_run_regional_revisit_evidence,
)
from deviation_protocol.infrastructure.run_protocol_binding_persistence import _require, _utc
from deviation_protocol.infrastructure.world_continuation_persistence import (
    _columns, _ended, reconstruct_continued_family, visit_from_storage,
)

ENTRY_COLUMNS = frozenset(("run_id", "continuous_story_line_id", "visit_id", "session_id",
    "joined_state_version", "entry_schema", "entry_canonical", "entry_sha256", "created_at"))


def entry_to_storage(entry, *, created_at):
    revalidate_run_model(entry, RegionalEntryV1)
    _utc(created_at)
    return dict(run_id=entry.run_id, continuous_story_line_id=entry.continuous_story_line_id,
        visit_id=entry.visit_id, session_id=entry.session_id, joined_state_version=5,
        entry_schema=entry.schema_version, entry_canonical=entry.canonical_bytes(),
        entry_sha256=bytes.fromhex(entry.digest()), created_at=created_at)


def entry_from_storage(row, *, created_at):
    values = _columns(row, ENTRY_COLUMNS)
    _require(type(values["joined_state_version"]) is int, "entry original joined scalar")
    _require(type(values["entry_sha256"]) is bytes and len(values["entry_sha256"]) == 32,
             "entry digest original bytes")
    entry = decode_regional_entry(values["entry_canonical"])
    values["created_at"] = _utc(values["created_at"])
    _require(values == entry_to_storage(entry, created_at=created_at), "entry row/canonical association")
    return entry


def regional_visit_from_storage(row):
    values = _columns(row, WorldVisitV2.model_fields)
    for field in ("entered_at", "created_at"):
        values[field] = _utc(values[field])
    return WorldVisitV2.model_validate(values, strict=True)


def regional_position_from_storage(row):
    values = _columns(row, WorldPositionV2.model_fields)
    values["created_at"] = _utc(values["created_at"])
    return WorldPositionV2.model_validate(values, strict=True)


def reconstruct_regional_family(*, admission, run, mutations, creation_evidence,
        roots, visits, positions, entries, source_session, source_snapshot,
        destination_session, destination_snapshot, destination_event, source_events,
        regional_session, regional_snapshot, regional_event, registry, regional_has_active_job, regional_events=()):
    from deviation_protocol.application.scenario_initialization import _seal_regional_base, initialize_scenario_state
    from deviation_protocol.application.story_director import DeterministicStoryDirector
    from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
    from deviation_protocol.domain.state import GameState
    from deviation_protocol.domain.player_memory import (
        PlayerMemoryState, ScenarioMemoryRecord, ScenarioMemoryStatus,
        ScenarioMemoryMilestone, KnownPublicFactRecord,
    )
    _require(len(roots) == 2 and len(visits) == 3 and len(positions) == 1 and len(entries) == 1,
             "regional family counts")
    _require(len(mutations) == (4 if run.state_version.value == 5 else 5), "regional receipt count")
    decoded = []
    for row in visits:
        ordinal, join, materialized = row.visit_ordinal, row.joined_state_version, row.materialized_state_version
        _require(all(type(value) is int for value in (ordinal, join, materialized)), "visit original scalars")
        if (ordinal, join, materialized) in ((1, 3, 4), (2, 4, 4)):
            decoded.append(visit_from_storage(row))
        else:
            _require((ordinal, join, materialized) == (3, 5, 5), "regional visit tuple")
            decoded.append(regional_visit_from_storage(row))
    decoded.sort(key=lambda v: v.visit_ordinal)
    _require(tuple(v.visit_ordinal for v in decoded) == (1, 2, 3), "regional ordered visits")
    old_evidence = decode_native_run_continuation_evidence(mutations[2].operation_evidence_canonical)
    old_run = continue_native_run(admission, old_evidence)
    # This is a historical value derived from committed edge evidence, not a second row.
    old_position = WorldPositionV1(run_id=run.run_id.value,
        continuous_story_line_id=run.continuous_story_line_id.value,
        visit_id=old_evidence.destination_visit_id, session_id=old_evidence.destination_session_id,
        position_state_version=4, created_at=old_run.current_mutation_provenance.occurred_at)
    prefix = reconstruct_continued_family(admission=admission, run=old_run, mutations=mutations[:3],
        creation_evidence=creation_evidence, roots=roots,
        visits=tuple(SimpleNamespace(**v.model_dump()) for v in decoded[:2]),
        positions=(SimpleNamespace(**old_position.model_dump()),),
        source_session=source_session, source_snapshot=source_snapshot,
        destination_session=destination_session, destination_snapshot=destination_snapshot,
        destination_event=destination_event, registry=registry)
    evidence = decode_native_run_regional_revisit_evidence(mutations[3].operation_evidence_canonical)
    time = datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00"))
    source_bundle = registry.resolve("undelivered_receipt", "undelivered-receipt-1.0.0")
    base_state = source_bundle.validate_snapshot(destination_snapshot.state_json)
    base = _seal_regional_base(session_id=destination_session.session_id, state=base_state,
        bundle=source_bundle, events=source_events)
    _require(base.digest() == evidence.world_base_snapshot_sha256
        and destination_session.state_version == destination_snapshot.state_version == evidence.source_ending.session_state_version
        and evidence.selection_inputs.eligible_pool == registry.regional_pool(), "regional base and pool")
    entry = entry_from_storage(entries[0], created_at=time)
    revisited = NativeRunRegionalRevisitV1(continued=prefix,
        canonical_run=revisit_native_region(prefix, evidence), revisit_evidence=evidence,
        entry=entry, visit=decoded[2], position=regional_position_from_storage(positions[0]))
    bundle = registry.resolve(entry.scenario_id, entry.scenario_content_version)
    initial = bundle.validate_snapshot(entry.snapshot)
    character = bundle.scenario_catalog.content_catalog.character(base_state.player.character_definition_id)
    expected = initialize_scenario_state(GameState(content_version=entry.scenario_content_version,
        player=base_state.player.model_copy(deep=True)), bundle.scenario_catalog.content_catalog,
        bundle.scenario_catalog.scenarios[0], character_tags=character.tags,
        story_director=DeterministicStoryDirector()).candidate_state
    facts = ("receipt_archive.fact.delivery_unproven", "receipt_archive.fact.hold_effective")
    event_id = evidence.destination_initial_event_id
    expected.player_memory = PlayerMemoryState(last_applied_source_sequence_no=1,
        last_applied_source_event_id=event_id,
        scenario_records=(ScenarioMemoryRecord(scenario_id=entry.scenario_id,
            scenario_content_version=entry.scenario_content_version, status=ScenarioMemoryStatus.STARTED,
            milestone_refs=(ScenarioMemoryMilestone.STARTED, ScenarioMemoryMilestone.IMPORTANT_FACT_CONFIRMED),
            known_public_fact_refs=facts, last_source_event_id=event_id, last_source_sequence_no=1),),
        known_public_facts=tuple(KnownPublicFactRecord(scenario_id=entry.scenario_id, fact_ref=fact,
            source_event_id=event_id, source_sequence_no=1) for fact in facts))
    _require(initial.to_snapshot() == expected.to_snapshot(), "regional sealed initialization reconstruction")
    _require(all(row is not None for row in (regional_session, regional_snapshot, regional_event)),
             "regional Session evidence missing")
    ss, sp, ev = map(vars, (regional_session, regional_snapshot, regional_event))
    _require(all(type(ss.get(k)) is int and 0 <= ss[k] <= 2**63 - 1
                 for k in ("state_version", "turn_number", "random_seed")), "regional Session scalars")
    _require(type(sp.get("state_version")) is int and sp["state_version"] == ss["state_version"]
        and ss["player_id"] == evidence.request.player_id == creation_evidence.player_id
        and evidence.request.controller_binding == creation_evidence.controller_operation.controller_binding.value
        and ss["session_id"] == sp["session_id"] == ev["session_id"] == entry.session_id
        and ss["scenario_id"] == entry.scenario_id and ss["scenario_version"] == entry.scenario_content_version
        and ss["character_definition_id"] == initial.player.character_definition_id
        and ss["creation_client_request_id"] == evidence.destination_creation_request_id
        and ss["random_seed"] == evidence.destination_random_seed
        and _utc(ss["created_at"]) == _utc(ev["occurred_at"]) == time
        and _utc(ss["updated_at"]) >= time and _utc(sp["updated_at"]) >= time
        and type(ev["sequence_no"]) is int and ev["sequence_no"] == 1
        and ev["event_id"] == event_id and ev["turn_id"] == "session-created"
        and ev["event_type"] == "ScenarioStarted"
        and ev["payload_json"] == {"scenario_id": entry.scenario_id,
                                   "scenario_content_version": entry.scenario_content_version},
        "regional Session/initial event association")
    latest = bundle.validate_snapshot(sp["state_json"])
    # Session.phase is the action-loop phase; the validated runtime owns ending.
    _require(latest.scenario_runtime.ending_status is EndingStatus.ACTIVE or not regional_has_active_job,
             "ended archive has active narrative job")
    from deviation_protocol.infrastructure.run_completion_persistence import validate_sealed_archive, reconstruct_completed_suffix
    validate_sealed_archive(revisited, latest, regional_events)
    _require(latest.player.player_id == initial.player.player_id
        and latest.player.character_definition_id == initial.player.character_definition_id,
        "regional current player identity")
    if ss["state_version"] == 0:
        _require(ss["turn_number"] == 0 and ss["phase"] == "AWAITING_ACTION"
                 and latest.to_snapshot() == entry.snapshot, "regional version zero entry")
    if run.state_version.value == 5:
        _require(run == revisited.canonical_run, "regional active suffix")
        return revisited
    _require(run.state_version.value == 6, "regional terminal suffix version")
    from deviation_protocol.domain.run import RunLifecycleStatus
    if run.lifecycle_status is RunLifecycleStatus.COMPLETED:
        # The prefix above consumed only the first four receipts and the actual
        # position at five. Stored history has independently bound that revision;
        # the fifth receipt now belongs exclusively to the completion suffix.
        first = registry.resolve(prefix.source_root.scenario_id, prefix.source_root.scenario_content_version).validate_snapshot(source_snapshot.state_json)
        return reconstruct_completed_suffix(prefix=revisited, run=run, receipt=mutations[-1],
            states=(first, base_state, latest),
            versions=(source_session.state_version, destination_session.state_version, regional_session.state_version),
            event_sets=((), source_events, regional_events), registry=registry)
    exit_evidence = decode_revisited_native_run_exit_evidence(mutations[-1].operation_evidence_canonical)
    _ended(latest, ending_id=exit_evidence.ending_id, ending_status=exit_evidence.ending_status)
    _require(exit_evidence.request.player_id == evidence.request.player_id
        and exit_evidence.request.controller_binding == evidence.request.controller_binding
        and exit_evidence.session_state_version == ss["state_version"]
        and exit_evidence.snapshot_sha256 == state_fingerprint(latest), "regional exit snapshot")
    return NativeRunRegionalRevisitTerminatedV1(revisited=revisited, canonical_run=run,
                                               exit_evidence=exit_evidence)
