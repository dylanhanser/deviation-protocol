from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, BinaryIO, TypeVar

from pydantic import BaseModel
import uvicorn


REPOSITORY_ROOT = Path(__file__).parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from deviation_protocol.api.demo_composition import build_demo_runtime  # noqa: E402
from deviation_protocol.api.main import create_app  # noqa: E402
from deviation_protocol.application.narrative_jobs import NarrativeJob  # noqa: E402
from deviation_protocol.application.narrative_models import (  # noqa: E402
    NarrativeRequest,
    ValidatedNarrativeProposal,
)
from deviation_protocol.application.ports import (  # noqa: E402
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
)
from deviation_protocol.application.turn_response import TurnResponse  # noqa: E402
from deviation_protocol.domain.actions import ActionSubmission, ActionType  # noqa: E402
from deviation_protocol.domain.events import DomainEvent  # noqa: E402
from deviation_protocol.domain.models import GameSession  # noqa: E402
from deviation_protocol.domain.narrative import NarrativeFrame  # noqa: E402
from deviation_protocol.domain.scenario_runtime import (  # noqa: E402
    ScenarioRuntimeState,
)
from deviation_protocol.domain.state import GameState  # noqa: E402
from deviation_protocol.infrastructure.demo_authority import (  # noqa: E402
    CanonicalDemoProviderGuard,
)
from deviation_protocol.infrastructure.demo_generators import (  # noqa: E402
    DemoGenerators,
    new_demo_generators,
)
from deviation_protocol.infrastructure.demo_persistence import (  # noqa: E402
    DemoProcessStore,
    DemoStoreSnapshot,
)
from deviation_protocol.infrastructure.player_character_persistence import (  # noqa: E402
    StoredControllerBindingRecord,
    StoredCreationReceiptRecord,
    StoredCurrentPlayerCharacterRecord,
    StoredMutationReceiptRecord,
    StoredPlayerCharacterIdAllocationRecord,
    StoredPlayerCharacterRevisionRecord,
)
from deviation_protocol.infrastructure.run_persistence import (  # noqa: E402
    StoredCurrentRunRecord,
    StoredRunCreationReceiptRecord,
    StoredRunMutationReceiptRecord,
    StoredRunRevisionRecord,
    StoredRunSessionParticipationRecord,
)


PROTOCOL = "deviation-demo-generator-trace"
PROTOCOL_VERSION = 1
TRACE_CATEGORIES = frozenset(
    {
        "CLOCK",
        "PLAYER_CHARACTER_ID",
        "RUN_ID",
        "CONTINUOUS_STORY_LINE_ID",
        "SESSION_ID",
        "EVENT_ID",
        "JOB_ID",
        "LEASE_TOKEN",
        "WORKER_ID",
        "SEED",
    }
)
_T = TypeVar("_T")

# The field manifests below are independently transcribed from the authoritative
# dataclass/Pydantic contracts. They intentionally fail when a contract field is
# added, removed, renamed, or omitted by this evidence path.
EXPECTED_DATACLASS_FIELDS = {
    DemoStoreSnapshot: (
        "sessions",
        "snapshots",
        "creation_keys",
        "turn_requests",
        "narrative_jobs",
        "events",
        "provider_progress",
        "controller_bindings",
        "player_character_id_allocations",
        "player_character_revisions",
        "player_character_current",
        "player_character_creation_receipts",
        "player_character_mutation_receipts",
        "run_revisions",
        "run_current",
        "run_participations",
        "run_creation_receipts",
        "run_mutation_receipts",
    ),
    StoredControllerBindingRecord: ("controller_binding", "created_at"),
    StoredPlayerCharacterIdAllocationRecord: (
        "player_character_id",
        "created_at",
    ),
    StoredPlayerCharacterRevisionRecord: (
        "player_character_id",
        "record_revision",
        "contract_version",
        "controller_binding",
        "lifecycle",
        "prior_revision",
        "mutation_kind",
        "authority_class",
        "source_reference",
        "record_canonical",
        "created_at",
    ),
    StoredCurrentPlayerCharacterRecord: (
        "player_character_id",
        "contract_version",
        "record_revision",
        "controller_binding",
        "lifecycle",
        "record_canonical",
        "created_at",
        "updated_at",
    ),
    StoredCreationReceiptRecord: (
        "controller_binding",
        "operation_namespace",
        "operation_id",
        "fingerprint",
        "command_kind",
        "result_schema_version",
        "result_player_character_id",
        "result_contract_version",
        "resulting_revision",
        "resulting_lifecycle",
        "result_record_fingerprint",
        "receipt_canonical",
        "operation_evidence_canonical",
        "created_at",
    ),
    StoredMutationReceiptRecord: (
        "player_character_id",
        "operation_namespace",
        "operation_id",
        "fingerprint",
        "command_kind",
        "result_schema_version",
        "expected_revision",
        "result_player_character_id",
        "result_contract_version",
        "result_command_kind",
        "command_result",
        "resulting_revision",
        "resulting_lifecycle",
        "before_record_fingerprint",
        "after_record_fingerprint",
        "receipt_canonical",
        "operation_evidence_canonical",
        "created_at",
    ),
    StoredRunRevisionRecord: (
        "run_id",
        "continuous_story_line_id",
        "lifecycle_status",
        "state_version",
        "creation_operation_id",
        "creation_source_reference",
        "creation_occurred_at",
        "prior_state_version",
        "mutation_kind",
        "operation_id",
        "source_reference",
        "occurred_at",
        "binding_player_character_id",
        "binding_contract_version",
        "binding_record_revision",
        "binding_state",
        "binding_operation_id",
        "binding_authority_source_ref",
        "bound_at",
        "inactivated_at",
        "active_player_character_id",
        "created_at",
    ),
    StoredCurrentRunRecord: (
        "run_id",
        "continuous_story_line_id",
        "lifecycle_status",
        "state_version",
        "creation_operation_id",
        "creation_source_reference",
        "creation_occurred_at",
        "prior_state_version",
        "mutation_kind",
        "operation_id",
        "source_reference",
        "occurred_at",
        "binding_player_character_id",
        "binding_contract_version",
        "binding_record_revision",
        "binding_state",
        "binding_operation_id",
        "binding_authority_source_ref",
        "bound_at",
        "inactivated_at",
        "active_player_character_id",
        "created_at",
        "updated_at",
    ),
    StoredRunSessionParticipationRecord: (
        "session_id",
        "run_id",
        "continuous_story_line_id",
        "joined_state_version",
        "operation_id",
        "source_reference",
        "joined_at",
    ),
    StoredRunCreationReceiptRecord: (
        "operation_namespace",
        "operation_id",
        "fingerprint",
        "command_kind",
        "result_schema_version",
        "result_run_id",
        "result_continuous_story_line_id",
        "resulting_lifecycle_status",
        "resulting_state_version",
        "receipt_canonical",
        "operation_evidence_canonical",
        "created_at",
    ),
    StoredRunMutationReceiptRecord: (
        "run_id",
        "operation_namespace",
        "operation_id",
        "fingerprint",
        "command_kind",
        "result_schema_version",
        "expected_state_version",
        "result_run_id",
        "result_continuous_story_line_id",
        "resulting_lifecycle_status",
        "resulting_state_version",
        "participation_session_id",
        "participation_operation_id",
        "participation_source_reference",
        "result_player_character_id",
        "result_character_contract_version",
        "result_character_record_revision",
        "receipt_canonical",
        "operation_evidence_canonical",
        "created_at",
    ),
    PersistedSession: (
        "session",
        "character_definition_id",
        "creation_client_request_id",
        "created_at",
        "updated_at",
    ),
    GameSession: (
        "session_id",
        "player_id",
        "scenario_id",
        "scenario_version",
        "phase",
        "turn_number",
        "state_version",
        "random_seed",
    ),
    PersistedSnapshot: ("state_version", "state"),
    PersistedTurnRequest: ("turn_id", "action_signature", "response"),
    DomainEvent: (
        "event_id",
        "session_id",
        "turn_id",
        "sequence_no",
        "event_type",
        "payload",
        "occurred_at",
    ),
}
EXPECTED_PYDANTIC_FIELDS = {
    NarrativeJob: (
        "job_id",
        "session_id",
        "turn_id",
        "client_request_id",
        "action_signature",
        "prepared_state_version",
        "state_fingerprint",
        "scenario_id",
        "scenario_content_version",
        "request_fingerprint",
        "narrative_request",
        "prompt_schema_version",
        "style_profile_version",
        "provider_name",
        "model_name",
        "status",
        "attempt_count",
        "lease_token",
        "lease_owner",
        "lease_expires_at",
        "validated_proposal",
        "validated_proposal_digest",
        "outcome_rule_id",
        "accepted_narrative_text",
        "error_code",
        "created_at",
        "updated_at",
    ),
    GameState: (
        "schema_version",
        "content_version",
        "player",
        "npcs",
        "scenario_runtime",
        "player_memory",
    ),
    ScenarioRuntimeState: (
        "scenario_id",
        "scenario_content_version",
        "current_phase_id",
        "phase_beat_index",
        "current_location_id",
        "discovered_clue_ids",
        "completed_clue_group_ids",
        "bound_deferred_facts",
        "mutable_fact_values",
        "dynamic_facts",
        "threat_clocks",
        "opened_location_ids",
        "current_decision_id",
        "decisions_made",
        "rapid_decision_mode",
        "ending_status",
        "ending_id",
        "phase_visit_counts",
        "transition_use_counts",
        "applied_event_ids",
        "narrative_outcome_evidence",
        "decision_outcome_evidence",
    ),
    NarrativeFrame: (
        "frame_id",
        "scenario_id",
        "phase_id",
        "mode",
        "current_location_id",
        "must_render_facts",
        "may_render_facts",
        "visible_entities",
        "visible_clues",
        "must_render_event_types",
        "recent_verified_events",
        "npc_knowledge",
        "tone_hints",
        "target_length",
        "min_length",
        "max_length",
        "decision_required",
        "decision_id",
        "decision_reason",
        "suggested_actions",
        "allowed_custom_action_constraints",
        "stop_condition",
        "player_visible_clocks",
    ),
    NarrativeRequest: (
        "frame",
        "player_memory",
        "player_intent",
        "player_visible_character_tags",
        "recent_narrative_fragments",
        "public_story_summary",
        "language",
        "style_profile_id",
        "outcome_candidates",
        "prompt_schema_version",
    ),
    ValidatedNarrativeProposal: ("proposal", "provider_metadata", "usage"),
    TurnResponse: (
        "session_id",
        "client_request_id",
        "action_signature",
        "resolution_kind",
        "result_code",
        "feedback_code",
        "feedback_parameters",
        "resulting_state_version",
        "state_changed",
        "narrative_required",
        "narrative_pending",
        "narrative_frame",
        "narrative_text",
        "narrative_status",
        "local_query_result",
    ),
}
EXPECTED_PRIVATE_COMPONENTS = frozenset(
    {
        "sessions",
        "snapshots",
        "creation_keys",
        "turn_requests",
        "narrative_jobs",
        "events",
        "provider_progress",
        "controller_bindings",
        "player_character_id_allocations",
        "player_character_revisions",
        "player_character_current",
        "player_character_creation_receipts",
        "player_character_mutation_receipts",
        "run_revisions",
        "run_current",
        "run_participations",
        "run_creation_receipts",
        "run_mutation_receipts",
    }
)

# These content addresses are secondary checks over the schema-complete raw and
# direct-binding representations above. Each identity family has its own raw
# expectation; exact replay never enters the caller-equivalence path.
EXPECTED_RAW_PRIVATE_COMPONENT_DIGESTS: dict[str, dict[str, str]] = {
    "same": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "f4031b48f17f191525aa31cee2ff7c872e46590f4894ae42c3bca94cf64342bf",
        "events": "b5fffb46cb68f3db6f997635c521473e5955a3c88407a1021817d678fe901545",
        "narrative_jobs": "aa287c34318afc51e25d6dab08ce300ce5c72d0ee79c3e5ae0aab1eebae5aca2",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "de6b3950427d1023c19aeaa744fb9a5826a23be4d9123d35cf88bc0394bada37",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "e0b409303318a225a2e57d6a26b187e30e3e45bc5a15ce8889005256c05bff4f",
    },
    "browser-a": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "f4031b48f17f191525aa31cee2ff7c872e46590f4894ae42c3bca94cf64342bf",
        "events": "e7f4e9bbaf6b5603b5c8fb7c1ae9dd01f4b6c0243c60487235d9f9a239171de0",
        "narrative_jobs": "53603023f147bd3dbc13b873563337d601e9920d601562b366c89fe5c3945e8c",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "de6b3950427d1023c19aeaa744fb9a5826a23be4d9123d35cf88bc0394bada37",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "4f82491e6bd8ee038b443d42d71c8a47ad1abd40a75fcaf08ca591c9936c7fbf",
    },
    "browser-b": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "f4031b48f17f191525aa31cee2ff7c872e46590f4894ae42c3bca94cf64342bf",
        "events": "9c72bbe9202d662909d7a11c3fc32a3e783e8dc784d866d45bb7ded9ae264ba3",
        "narrative_jobs": "7fff5f77e375791846c3d49c0cc0f7e976357424bfffa55fe27e5790848a5748",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "de6b3950427d1023c19aeaa744fb9a5826a23be4d9123d35cf88bc0394bada37",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "57fc18776c23492067db55c6f323f7c9eb838778989de17b56d601c1f460d8c5",
    },
}
EXPECTED_CALLER_EQUIVALENCE_COMPONENT_DIGESTS: dict[str, dict[str, str]] = {
    "same": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "232e0faa4a17ece078877b8994eb6ee4142fd8dbea0ccef67a8c76881e4d6731",
        "events": "cedbcbf3f9ccab541ee4435c3e697dda3a2443ea0e6b00bca6691eb3504919a9",
        "narrative_jobs": "299fc04940713ed7b0f1a5132a61683c0845767246bd52473ffd1f5c42408417",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "f076abd23cc7c8936b5b5a8ab54b926b2faac2084998134a024f2aa2be73389e",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "b17ce2605138c933e18fa8f2f93975705823f9bc31e8ccbc3ae1004a92db29bc",
    },
    "browser-a": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "232e0faa4a17ece078877b8994eb6ee4142fd8dbea0ccef67a8c76881e4d6731",
        "events": "a8b601d7d8483f838a8b974f8525d6e9a0d3afe4f2f124b8a31df2521b4f0474",
        "narrative_jobs": "2ab9ce3e2d7f2b7271042e4591360d6a396447d989a74a93cce737a27d0cb6a6",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "f076abd23cc7c8936b5b5a8ab54b926b2faac2084998134a024f2aa2be73389e",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "b61a6f64b2ff3f730c4e108e2795d8a9a43080c52da9bc49f4a7055635aee35c",
    },
    "browser-b": {
        "controller_bindings": "80031bb5a03194c1c71d487b4107133e8ebe8cc2ee5e26a262459d00a757b471",
        "creation_keys": "232e0faa4a17ece078877b8994eb6ee4142fd8dbea0ccef67a8c76881e4d6731",
        "events": "bf0b04b18db04741216566fc827b0bc8b98419f96ec2c04e22889a4f70a9f4f2",
        "narrative_jobs": "2d3d9b89c8711a103f0b0b110f40bae05cb9e93559d21e57041fe9ec296a645a",
        "player_character_creation_receipts": "e16f5bf7877322e67f04bdc9896178a86cdaf426b9fbdf012a7ee03aaeee6f35",
        "player_character_current": "07696f0c0712c57b83d1c5b660d256b5ff829aaffd102a91b2768ffdef394cc9",
        "player_character_id_allocations": "1f81cfeebb6ef32000ee47d9603db3531c540763266f778056bba4bd35724cd4",
        "player_character_mutation_receipts": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
        "player_character_revisions": "8ed83b778e4d97f4a19ec07f546ad4e72694b03c2f2cfed32e91039b0ad8916c",
        "provider_progress": "fbead410a3aa326273c452a3d40e4280a8894c84be5306e1147e9a75c55f0327",
        "run_creation_receipts": "8ecb9d85ec962b5064d22f842c9dc0afdbbcf9424b1a3fa5cd0d76c0f6c9e038",
        "run_current": "5646c9544cbb68c34b31f0b68d3fef5ab6dba6f91df4b98c56516d3d6a35f097",
        "run_mutation_receipts": "71ebd9a2e40c1392b4396b5812fb6d76d600948252bdfbb914ba8cc2ac8c8442",
        "run_participations": "fc53403234547a0fb54a30afb02b0ff10b97e7b01e41cb0b6a2c72c212e19742",
        "run_revisions": "0f8ac851105a91a36ecab90752205accedd21d020733e952b5a4614c5be37717",
        "sessions": "f076abd23cc7c8936b5b5a8ab54b926b2faac2084998134a024f2aa2be73389e",
        "snapshots": "3d8e17bc41f3e33a5cf2fe83ed4848098c0342c47c17556788373ecc4c85117d",
        "turn_requests": "03d9acc99066a7c56c69cea1bf5d5893310aad8de07be51e6f89e8fee348e4b4",
    },
}


class TraceWriter:
    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._global_ordinal = 0
        self._category_ordinals: Counter[str] = Counter()
        self._lock = threading.Lock()
        self._completed = False

    def record(self, category: str, raw_value: str | int) -> None:
        if category not in TRACE_CATEGORIES:
            raise RuntimeError("unknown Demo trace category")
        if (category == "SEED" and type(raw_value) is not int) or (
            category != "SEED" and type(raw_value) is not str
        ):
            raise RuntimeError("invalid Demo trace raw value type")
        with self._lock:
            if self._completed:
                raise RuntimeError("generator record after completion")
            self._global_ordinal += 1
            self._category_ordinals[category] += 1
            self._write(
                {
                    "protocol": PROTOCOL,
                    "version": PROTOCOL_VERSION,
                    "record_type": "GENERATOR",
                    "global_ordinal": self._global_ordinal,
                    "category": category,
                    "category_ordinal": self._category_ordinals[category],
                    "raw_value": raw_value,
                }
            )

    def complete(self) -> None:
        with self._lock:
            if self._completed:
                raise RuntimeError("duplicate Demo trace completion")
            self._completed = True
            self._write(
                {
                    "protocol": PROTOCOL,
                    "version": PROTOCOL_VERSION,
                    "record_type": "COMPLETE",
                    "record_count": self._global_ordinal,
                    "last_global_ordinal": self._global_ordinal,
                }
            )
            self._stream.flush()

    def _write(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        remaining = memoryview(encoded + b"\n")
        while remaining:
            written = self._stream.write(remaining)
            if written is None or written <= 0:
                raise OSError("Demo trace pipe write did not make progress")
            remaining = remaining[written:]
        self._stream.flush()


class _PartialWriteStream:
    def __init__(
        self,
        stream: BinaryIO,
        *,
        maximum_write: int,
        partial_write_count: int | None = None,
        zero_progress: bool = False,
        none_progress: bool = False,
    ) -> None:
        self._stream = stream
        self._maximum_write = maximum_write
        self._partial_write_count = partial_write_count
        self._zero_progress = zero_progress
        self._none_progress = none_progress

    @property
    def closed(self) -> bool:
        return self._stream.closed

    def write(self, data: bytes | memoryview) -> int | None:
        if self._none_progress:
            return None
        if self._zero_progress:
            return 0
        if self._partial_write_count == 0:
            return self._stream.write(data)
        if self._partial_write_count is not None:
            self._partial_write_count -= 1
        return self._stream.write(data[: self._maximum_write])

    def flush(self) -> None:
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


def _traced(
    category: str,
    function: Callable[[], _T],
    trace: TraceWriter,
    *,
    encode: Callable[[_T], str | int] | None = None,
) -> Callable[[], _T]:
    def invoke() -> _T:
        value = function()
        raw_value = encode(value) if encode is not None else value
        if type(raw_value) not in (str, int):
            raise RuntimeError("invalid Demo trace raw value")
        trace.record(category, raw_value)
        return value

    return invoke


def _traced_generators(trace: TraceWriter) -> DemoGenerators:
    underlying = new_demo_generators()
    return DemoGenerators(
        clock=_traced("CLOCK", underlying.clock, trace, encode=lambda value: value.isoformat()),
        player_character_id=_traced(
            "PLAYER_CHARACTER_ID", underlying.player_character_id, trace
        ),
        run_id=_traced("RUN_ID", underlying.run_id, trace),
        continuous_story_line_id=_traced(
            "CONTINUOUS_STORY_LINE_ID",
            underlying.continuous_story_line_id,
            trace,
        ),
        session_id=_traced("SESSION_ID", underlying.session_id, trace),
        event_id=_traced("EVENT_ID", underlying.event_id, trace),
        job_id=_traced("JOB_ID", underlying.job_id, trace),
        lease_token=_traced("LEASE_TOKEN", underlying.lease_token, trace),
        worker_id=_traced("WORKER_ID", underlying.worker_id, trace),
        seed=_traced("SEED", underlying.seed, trace),
    )


def _deny_non_loopback_connections() -> Callable[[], None]:
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_sendto = socket.socket.sendto
    original_getaddrinfo = socket.getaddrinfo

    def allowed(address: object) -> bool:
        if not isinstance(address, tuple) or not address:
            return False
        host = address[0]
        if not isinstance(host, str):
            return False
        if host.casefold() == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def guarded_connect(instance: socket.socket, address: object):
        if not allowed(address):
            raise OSError("non-loopback network access is disabled")
        return original_connect(instance, address)

    def guarded_connect_ex(instance: socket.socket, address: object):
        if not allowed(address):
            raise OSError("non-loopback network access is disabled")
        return original_connect_ex(instance, address)

    def guarded_sendto(instance: socket.socket, data: bytes, *args: object):
        if not args or not allowed(args[-1]):
            raise OSError("non-loopback network access is disabled")
        return original_sendto(instance, data, *args)

    def guarded_getaddrinfo(host: object, *args: object, **kwargs: object):
        if not isinstance(host, str) or not allowed((host, 0)):
            raise OSError("non-loopback network access is disabled")
        return original_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.socket.sendto = guarded_sendto  # type: ignore[method-assign]
    socket.getaddrinfo = guarded_getaddrinfo

    def restore() -> None:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = original_connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = original_sendto  # type: ignore[method-assign]
        socket.getaddrinfo = original_getaddrinfo

    return restore


def _trap_external_runtime_constructors() -> None:
    import deviation_protocol.api.main as api_main

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("external runtime constructor is disabled")

    api_main.build_default_services = forbidden  # type: ignore[assignment]
    api_main.create_engine = forbidden  # type: ignore[assignment]
    api_main.create_session_factory = forbidden  # type: ignore[assignment]
    api_main.DeepSeekNarrativeProvider = forbidden  # type: ignore[assignment,misc]


def _assert_sanitized_environment() -> None:
    forbidden = {
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "DEEPSEEK_API_KEY",
        "RUN_LIVE_DEEPSEEK_TEST",
    }
    environment_names = {key.upper() for key in os.environ}
    if forbidden & environment_names or any(
        key.startswith("DEEPSEEK_") for key in environment_names
    ):
        raise RuntimeError("replay child environment is not sanitized")


def _canonical_private_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise RuntimeError("private replay datetime is not timezone-aware")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Enum):
        return _canonical_private_value(value.value)
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, BaseModel):
        return _schema_complete_pydantic_value(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _schema_complete_dataclass_value(value)
    if isinstance(value, dict):
        if any(type(key) is not str for key in value):
            raise TypeError("private replay JSON mapping has a non-string key")
        return {
            key: _canonical_private_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_private_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical = [_canonical_private_value(item) for item in value]
        return sorted(
            canonical,
            key=lambda item: json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )
    if value is None or type(value) in (bool, int, str):
        return value
    raise TypeError(f"unsupported private replay value type: {type(value).__name__}")


def _schema_complete_dataclass_value(value: Any) -> dict[str, Any]:
    model_type = type(value)
    expected = EXPECTED_DATACLASS_FIELDS.get(model_type)
    actual = tuple(field.name for field in fields(value))
    if expected is None or actual != expected:
        raise RuntimeError(f"private dataclass schema differs: {model_type.__name__}")
    return {
        name: _canonical_private_value(getattr(value, name)) for name in actual
    }


def _schema_complete_pydantic_value(value: BaseModel) -> dict[str, Any]:
    model_type = type(value)
    actual = tuple(model_type.model_fields)
    expected = EXPECTED_PYDANTIC_FIELDS.get(model_type)
    if expected is not None and actual != expected:
        raise RuntimeError(f"private Pydantic schema differs: {model_type.__name__}")
    return {
        name: _canonical_private_value(getattr(value, name)) for name in actual
    }


def _assert_authoritative_field_manifests() -> None:
    for model_type, expected in EXPECTED_DATACLASS_FIELDS.items():
        if tuple(field.name for field in fields(model_type)) != expected:
            raise RuntimeError(
                f"DEMO_CHILD_PRIVATE_{model_type.__name__.upper()}_SCHEMA_MISMATCH"
            )
    for model_type, expected in EXPECTED_PYDANTIC_FIELDS.items():
        if tuple(model_type.model_fields) != expected:
            raise RuntimeError(
                f"DEMO_CHILD_PRIVATE_{model_type.__name__.upper()}_SCHEMA_MISMATCH"
            )


def _complete_raw_private_representation(runtime: Any) -> dict[str, Any]:
    _assert_authoritative_field_manifests()
    snapshot = runtime.store.snapshot()
    if tuple(field.name for field in fields(snapshot)) != EXPECTED_DATACLASS_FIELDS[
        DemoStoreSnapshot
    ]:
        raise RuntimeError("private Demo store snapshot schema differs")
    orchestrator = runtime.services.turn_orchestrator

    sessions = [
        {
            "store_session_id": session_id,
            "value": _schema_complete_dataclass_value(persisted),
        }
        for session_id, persisted in sorted(snapshot.sessions.items())
    ]
    snapshots: list[dict[str, Any]] = []
    for session_id, persisted in sorted(snapshot.snapshots.items()):
        state = GameState.from_snapshot(
            persisted.state,
            catalog=orchestrator.catalog,
            scenario_catalog=orchestrator.scenario_catalog,
        )
        serialized_state = _schema_complete_pydantic_value(state)
        if serialized_state != _canonical_private_value(dict(persisted.state)):
            raise RuntimeError("private snapshot model round-trip differs")
        snapshots.append(
            {
                "store_session_id": session_id,
                "value": _schema_complete_dataclass_value(persisted),
            }
        )

    creation_keys = [
        {
            "player_id": player_id,
            "creation_client_request_id": client_request_id,
            "session_id": session_id,
        }
        for (player_id, client_request_id), session_id in sorted(
            snapshot.creation_keys.items()
        )
    ]
    turn_requests: list[dict[str, Any]] = []
    for (session_id, client_request_id), persisted in sorted(
        snapshot.turn_requests.items(),
        key=lambda item: (
            (
                item[1].response.get("resulting_state_version", -1)
                if item[1].response is not None
                else -1
            ),
            item[0],
        ),
    ):
        if persisted.response is None:
            raise RuntimeError("canonical private turn response is absent")
        response = TurnResponse.model_validate(persisted.response)
        if _schema_complete_pydantic_value(response) != _canonical_private_value(
            dict(persisted.response)
        ):
            raise RuntimeError("private turn response model round-trip differs")
        turn_requests.append(
            {
                "store_session_id": session_id,
                "store_client_request_id": client_request_id,
                "value": _schema_complete_dataclass_value(persisted),
            }
        )

    narrative_jobs: list[dict[str, Any]] = []
    for job_id, job in sorted(snapshot.narrative_jobs.items()):
        if job.prompt_schema_version == "narrative-prompt-v2":
            request = NarrativeRequest.model_validate(
                job.narrative_request, strict=False
            )
            if _schema_complete_pydantic_value(request) != _canonical_private_value(
                job.narrative_request
            ):
                raise RuntimeError("private narrative request model round-trip differs")
            if job.validated_proposal is None:
                raise RuntimeError("canonical private proposal is absent")
            proposal = ValidatedNarrativeProposal.model_validate(
                job.validated_proposal, strict=False
            )
            if _schema_complete_pydantic_value(proposal) != _canonical_private_value(
                job.validated_proposal
            ):
                raise RuntimeError("private proposal model round-trip differs")
        else:
            if set(job.narrative_request) != {
                "source",
                "action_type",
                "choice_id",
                "resulting_frame_id",
            } or job.validated_proposal is None or set(job.validated_proposal) != {
                "source",
                "narrative_text",
            }:
                raise RuntimeError("private local-template schema differs")
        narrative_jobs.append(
            {
                "store_job_id": job_id,
                "value": _schema_complete_pydantic_value(job),
            }
        )

    representation = {
        "sessions": sessions,
        "snapshots": snapshots,
        "creation_keys": creation_keys,
        "turn_requests": turn_requests,
        "narrative_jobs": narrative_jobs,
        "events": [
            {
                "store_ordinal": ordinal,
                "value": _schema_complete_dataclass_value(event),
            }
            for ordinal, event in enumerate(snapshot.events, start=1)
        ],
        "provider_progress": [
            {"session_id": session_id, "completed_calls": completed_calls}
            for session_id, completed_calls in sorted(
                snapshot.provider_progress.items()
            )
        ],
        "controller_bindings": [
            {
                "store_controller_binding": controller_binding,
                "value": _schema_complete_dataclass_value(stored),
            }
            for controller_binding, stored in sorted(
                snapshot.controller_bindings.items()
            )
        ],
        "player_character_id_allocations": [
            {
                "store_player_character_id": player_character_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for player_character_id, stored in sorted(
                snapshot.player_character_id_allocations.items()
            )
        ],
        "player_character_revisions": [
            {
                "store_player_character_id": player_character_id,
                "store_record_revision": record_revision,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (player_character_id, record_revision), stored in sorted(
                snapshot.player_character_revisions.items()
            )
        ],
        "player_character_current": [
            {
                "store_player_character_id": player_character_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for player_character_id, stored in sorted(
                snapshot.player_character_current.items()
            )
        ],
        "player_character_creation_receipts": [
            {
                "store_controller_binding": controller_binding,
                "store_operation_namespace": operation_namespace,
                "store_operation_id": operation_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (
                controller_binding,
                operation_namespace,
                operation_id,
            ), stored in sorted(
                snapshot.player_character_creation_receipts.items()
            )
        ],
        "player_character_mutation_receipts": [
            {
                "store_player_character_id": player_character_id,
                "store_operation_namespace": operation_namespace,
                "store_operation_id": operation_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (
                player_character_id,
                operation_namespace,
                operation_id,
            ), stored in sorted(
                snapshot.player_character_mutation_receipts.items()
            )
        ],
        "run_revisions": [
            {
                "store_run_id": run_id,
                "store_state_version": state_version,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (run_id, state_version), stored in sorted(
                snapshot.run_revisions.items()
            )
        ],
        "run_current": [
            {
                "store_run_id": run_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for run_id, stored in sorted(snapshot.run_current.items())
        ],
        "run_participations": [
            {
                "store_session_id": session_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for session_id, stored in sorted(
                snapshot.run_participations.items()
            )
        ],
        "run_creation_receipts": [
            {
                "store_operation_namespace": operation_namespace,
                "store_operation_id": operation_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (operation_namespace, operation_id), stored in sorted(
                snapshot.run_creation_receipts.items()
            )
        ],
        "run_mutation_receipts": [
            {
                "store_run_id": run_id,
                "store_operation_namespace": operation_namespace,
                "store_operation_id": operation_id,
                "value": _schema_complete_dataclass_value(stored),
            }
            for (run_id, operation_namespace, operation_id), stored in sorted(
                snapshot.run_mutation_receipts.items()
            )
        ],
    }
    canonical = _canonical_private_value(representation)
    _assert_derived_private_bindings(canonical)
    return canonical


def _caller_identity_equivalence_representation(
    raw_representation: dict[str, Any],
) -> dict[str, Any]:
    """Normalize only direct persisted copies of the frozen caller whitelist."""

    representation = json.loads(
        json.dumps(raw_representation, ensure_ascii=False, allow_nan=False)
    )
    raw_to_token: dict[str, str] = {}
    category_counts: Counter[str] = Counter()

    def assign(raw: Any, category: str) -> str:
        if type(raw) is not str:
            raise RuntimeError("private caller identity is not a string")
        token = raw_to_token.get(raw)
        if token is None:
            category_counts[category] += 1
            token = f"<{category}:{category_counts[category]}>"
            raw_to_token[raw] = token
        return token

    for persisted in representation["sessions"]:
        value = persisted["value"]
        raw = value["creation_client_request_id"]
        value["creation_client_request_id"] = assign(raw, "CREATE_REQUEST")
    for key in representation["creation_keys"]:
        raw = key["creation_client_request_id"]
        token = raw_to_token.get(raw)
        if token is None:
            raise RuntimeError("private creation-key binding differs")
        key["creation_client_request_id"] = token

    turn_tokens: dict[str, str] = {}
    request_tokens: dict[str, str] = {}
    signature_tokens: dict[str, str] = {}
    for persisted in representation["turn_requests"]:
        value = persisted["value"]
        raw_turn = value["turn_id"]
        raw_request = persisted["store_client_request_id"]
        raw_signature = value["action_signature"]
        turn_tokens[raw_turn] = assign(raw_turn, "TURN")
        request_tokens[raw_request] = assign(raw_request, "ACTION_REQUEST")
        signature_tokens[raw_signature] = raw_signature
        value["turn_id"] = turn_tokens[raw_turn]
        persisted["store_client_request_id"] = request_tokens[raw_request]
        response = value["response"]
        if (
            not isinstance(response, dict)
            or response.get("client_request_id") != raw_request
            or response.get("action_signature") != raw_signature
        ):
            raise RuntimeError("private turn response binding differs")
        response["client_request_id"] = request_tokens[raw_request]
        # action_signature is a derived value, not a caller-whitelist entry.

    for persisted in representation["narrative_jobs"]:
        job = persisted["value"]
        raw_turn = job["turn_id"]
        raw_request = job["client_request_id"]
        raw_signature = job["action_signature"]
        if (
            raw_turn not in turn_tokens
            or raw_request not in request_tokens
            or raw_signature not in signature_tokens
        ):
            raise RuntimeError("private job has an unknown caller binding")
        job["turn_id"] = turn_tokens[raw_turn]
        job["client_request_id"] = request_tokens[raw_request]

    for persisted in representation["events"]:
        event = persisted["value"]
        raw_turn = event["turn_id"]
        if raw_turn != "session-created":
            token = turn_tokens.get(raw_turn)
            if token is None:
                raise RuntimeError("private event has an unknown turn binding")
            event["turn_id"] = token
    return representation


def _assert_derived_private_bindings(representation: dict[str, Any]) -> None:
    canonical_actions = (
        (ActionType.CHOOSE, None),
        (ActionType.CUSTOM, "请协调员复核我的连续回应和生命体征"),
        (ActionType.CONTINUE, None),
        (ActionType.CONTINUE, None),
        (ActionType.CHOOSE, None),
        (ActionType.CONTINUE, None),
        (ActionType.CONTINUE, None),
        (ActionType.CONTINUE, None),
        (ActionType.CHOOSE, None),
        (ActionType.EXPLORE, "沿记录与档案审计路径核对签发时间"),
        (ActionType.EXPLORE, "核对日志时间顺序以及规程反馈"),
        (ActionType.CHOOSE, None),
        (ActionType.OBSERVE, "复核地下患者的生命体征与连续监测历史"),
        (ActionType.CONTINUE, None),
        (ActionType.CONTINUE, None),
        (ActionType.CHOOSE, None),
        (ActionType.CHOOSE, None),
        (ActionType.CHOOSE, None),
        (ActionType.CHOOSE, None),
    )
    decision_payloads = {
        event["value"]["turn_id"]: event["value"]["payload"]
        for event in representation["events"]
        if event["value"]["event_type"] == "ScenarioDecisionSelected"
    }
    turn_by_request: dict[str, dict[str, Any]] = {}
    for ordinal, persisted in enumerate(representation["turn_requests"], start=1):
        value = persisted["value"]
        response = value["response"]
        if response["resulting_state_version"] != ordinal:
            raise RuntimeError("private turn response version order differs")
        action_type, description = canonical_actions[ordinal - 1]
        decision = decision_payloads.get(value["turn_id"])
        submission = ActionSubmission(
            session_id=persisted["store_session_id"],
            turn_id=value["turn_id"],
            client_request_id=persisted["store_client_request_id"],
            action_type=action_type,
            description=description,
            decision_id=(decision.get("public_decision_id") if decision else None),
            choice_id=(decision.get("selected_action_id") if decision else None),
        )
        expected_signature = submission.action_signature()
        if (
            value["action_signature"] != expected_signature
            or response["action_signature"] != expected_signature
            or response["client_request_id"]
            != persisted["store_client_request_id"]
        ):
            raise RuntimeError("private action signature binding differs")
        turn_by_request[persisted["store_client_request_id"]] = persisted

    proposal_digests: dict[str, str] = {}
    for persisted in representation["narrative_jobs"]:
        job = persisted["value"]
        turn = turn_by_request.get(job["client_request_id"])
        if (
            turn is None
            or job["turn_id"] != turn["value"]["turn_id"]
            or job["action_signature"] != turn["value"]["action_signature"]
            or job["request_fingerprint"]
            != _sha256_private_json(job["narrative_request"])
        ):
            raise RuntimeError("private narrative-job binding differs")
        proposal = job["validated_proposal"]
        digest = job["validated_proposal_digest"]
        if proposal is None or type(digest) is not str:
            raise RuntimeError("private narrative proposal is incomplete")
        if digest != _sha256_private_json(proposal):
            raise RuntimeError("private narrative proposal digest differs")
        proposal_digests[job["job_id"]] = digest
        candidates = job["narrative_request"].get("outcome_candidates", [])
        selected = proposal.get("proposal", {}).get("selected_outcome")
        if candidates and (
            not isinstance(selected, dict)
            or selected.get("outcome_token")
            != candidates[0].get("outcome_token")
        ):
            raise RuntimeError("private narrative outcome token binding differs")

    for persisted in representation["events"]:
        payload = persisted["value"]["payload"]
        if "proposal_digest" in payload:
            if proposal_digests.get(payload.get("job_id")) != payload["proposal_digest"]:
                raise RuntimeError("private event proposal binding differs")


def _assert_independent_private_source_representation(
    representation: dict[str, Any], identity_family: str
) -> None:
    """Check the readable frozen-spec source before using content addresses."""

    if set(representation) != EXPECTED_PRIVATE_COMPONENTS:
        raise RuntimeError("private source representation components differ")
    if len(representation["sessions"]) != 1:
        raise RuntimeError("private source Session count differs")
    persisted = representation["sessions"][0]
    session = persisted["value"]["session"]
    expected_session = {
        "session_id": "demo-session-00000001",
        "player_id": "demo-player",
        "scenario_id": "death_certificate",
        "scenario_version": "death-certificate-1.1.0",
        "phase": "AWAITING_ACTION",
        "turn_number": 0,
        "state_version": 19,
        "random_seed": 1,
    }
    if (
        persisted["store_session_id"] != "demo-session-00000001"
        or session != expected_session
        or persisted["value"]["character_definition_id"]
        != "character.death_certificate.investigator"
        or persisted["value"]["creation_client_request_id"]
        != "cec599f82a5d9e0c60fe5d0cdddaeb33e83ac721009a3800e2d99373cf10b3b9"
        or persisted["value"]["created_at"]
        != "2000-01-01T00:00:01+00:00"
        or persisted["value"]["updated_at"]
        != "2000-01-01T00:00:51+00:00"
    ):
        raise RuntimeError("private source Session representation differs")

    if representation["creation_keys"] != [
        {
            "player_id": "demo-player",
            "creation_client_request_id": (
                "cec599f82a5d9e0c60fe5d0cdddaeb33"
                "e83ac721009a3800e2d99373cf10b3b9"
            ),
            "session_id": "demo-session-00000001",
        }
    ] or representation["provider_progress"] != [
        {"session_id": "demo-session-00000001", "completed_calls": 4}
    ]:
        raise RuntimeError("private source authority index differs")

    character_components = (
        representation["controller_bindings"],
        representation["player_character_id_allocations"],
        representation["player_character_revisions"],
        representation["player_character_current"],
        representation["player_character_creation_receipts"],
    )
    if (
        any(len(component) != 1 for component in character_components)
        or representation["player_character_mutation_receipts"] != []
        or representation["controller_bindings"][0][
            "store_controller_binding"
        ]
        != "binding.demo-player"
        or representation["player_character_id_allocations"][0][
            "store_player_character_id"
        ]
        != "pc.demo-00000001"
        or representation["player_character_revisions"][0][
            "store_record_revision"
        ]
        != 1
        or representation["player_character_current"][0]["value"][
            "lifecycle"
        ]
        != "active"
        or representation["player_character_creation_receipts"][0][
            "store_operation_id"
        ]
        != "Create.Cross-Process-1"
    ):
        raise RuntimeError("private source Player Character authority differs")

    run_components = (
        representation["run_current"],
        representation["run_participations"],
        representation["run_creation_receipts"],
    )
    run_current = representation["run_current"][0]["value"]
    if (
        len(representation["run_revisions"]) != 3
        or any(len(component) != 1 for component in run_components)
        or len(representation["run_mutation_receipts"]) != 2
        or [
            item["store_state_version"]
            for item in representation["run_revisions"]
        ]
        != [1, 2, 3]
        or representation["run_current"][0]["store_run_id"]
        != "run.demo-00000001"
        or run_current["continuous_story_line_id"]["value"]
        != "csl.demo-00000001"
        or run_current["lifecycle_status"] != "active"
        or run_current["state_version"] != 3
        or run_current["active_player_character_id"]
        != "pc.demo-00000001"
        or representation["run_participations"][0]["store_session_id"]
        != "demo-session-00000001"
        or representation["run_creation_receipts"][0]["value"][
            "operation_id"
        ]["value"]
        != "2656a006164478467f59b139701dcf319bb25efb674dad74af0ef5fc7b82a63d"
    ):
        raise RuntimeError("private source Run authority differs")

    if len(representation["snapshots"]) != 1:
        raise RuntimeError("private source snapshot count differs")
    persisted_snapshot = representation["snapshots"][0]
    state = persisted_snapshot["value"]["state"]
    runtime = state["scenario_runtime"]
    if (
        persisted_snapshot["store_session_id"] != "demo-session-00000001"
        or persisted_snapshot["value"]["state_version"] != 19
        or set(state) != set(EXPECTED_PYDANTIC_FIELDS[GameState])
        or set(runtime) != set(EXPECTED_PYDANTIC_FIELDS[ScenarioRuntimeState])
        or state["schema_version"] != 3
        or state["content_version"] != "death-certificate-1.1.0"
        or len(runtime["narrative_outcome_evidence"]) != 4
        or len(runtime["decision_outcome_evidence"]) != 8
        or len(runtime["mutable_fact_values"]) != 2
        or runtime["dynamic_facts"] != {}
        or len(runtime["discovered_clue_ids"]) != 8
        or len(runtime["applied_event_ids"]) != 12
    ):
        raise RuntimeError("private source complete snapshot differs")

    turns = representation["turn_requests"]
    if len(turns) != 19:
        raise RuntimeError("private source turn count differs")
    for ordinal, turn in enumerate(turns, start=1):
        value = turn["value"]
        response = value["response"]
        if (
            turn["store_session_id"] != "demo-session-00000001"
            or turn["store_client_request_id"]
            != f"opaque-{identity_family}-action-{ordinal:02d}"
            or value["turn_id"]
            != f"opaque-{identity_family}-turn-{ordinal:02d}"
            or set(value) != set(EXPECTED_DATACLASS_FIELDS[PersistedTurnRequest])
            or set(response) != set(EXPECTED_PYDANTIC_FIELDS[TurnResponse])
            or response["session_id"] != "demo-session-00000001"
            or response["client_request_id"]
            != f"opaque-{identity_family}-action-{ordinal:02d}"
            or response["resulting_state_version"] != ordinal
        ):
            raise RuntimeError("private source turn representation differs")

    jobs = representation["narrative_jobs"]
    job_action_ordinals = (2, 10, 11, 13, 19)
    expected_created_seconds = (3, 19, 26, 38, 52)
    expected_updated_seconds = (10, 25, 35, 45, 52)
    if len(jobs) != 5:
        raise RuntimeError("private source job count differs")
    for ordinal, (persisted_job, action_ordinal) in enumerate(
        zip(jobs, job_action_ordinals, strict=True), start=1
    ):
        job = persisted_job["value"]
        expected_attempts = 0 if ordinal == 5 else 1
        if (
            persisted_job["store_job_id"] != f"demo-job-{ordinal:08d}"
            or set(job) != set(EXPECTED_PYDANTIC_FIELDS[NarrativeJob])
            or job["job_id"] != persisted_job["store_job_id"]
            or job["session_id"] != "demo-session-00000001"
            or job["turn_id"]
            != f"opaque-{identity_family}-turn-{action_ordinal:02d}"
            or job["client_request_id"]
            != f"opaque-{identity_family}-action-{action_ordinal:02d}"
            or job["status"] != "COMMITTED"
            or job["attempt_count"] != expected_attempts
            or job["lease_token"] is not None
            or job["lease_owner"] is not None
            or job["lease_expires_at"] is not None
            or job["error_code"] is not None
            or job["created_at"]
            != f"2000-01-01T00:00:{expected_created_seconds[ordinal - 1]:02d}+00:00"
            or job["updated_at"]
            != f"2000-01-01T00:00:{expected_updated_seconds[ordinal - 1]:02d}+00:00"
        ):
            raise RuntimeError("private source job representation differs")

    payload_fields = {
        "ScenarioStarted": {"scenario_content_version", "scenario_id"},
        "ScenarioDecisionSelected": {
            "decision_id",
            "public_decision_id",
            "scenario_event_id",
            "scenario_event_type",
            "selected_action_id",
            "selected_action_type",
            "source",
        },
        "NarrativeOutcomeAccepted": {
            "job_id",
            "npc_definition_ids",
            "outcome_result",
            "outcome_rule_id",
            "player_alive_acknowledgement_npc_definition_ids",
            "player_alive_acknowledgement_npc_ids",
            "proposal_digest",
            "scenario_event_id",
            "scenario_event_type",
            "source",
        },
        "ScenarioRuntimeEventGenerated": {
            "scenario_event_id",
            "scenario_event_type",
        },
        "ScenarioAutoBeatAdvanced": {
            "from_beat_index",
            "from_phase_id",
            "scenario_id",
            "source",
            "to_beat_index",
            "to_phase_id",
        },
    }
    events = representation["events"]
    if len(events) != 27:
        raise RuntimeError("private source event count differs")
    for ordinal, persisted_event in enumerate(events, start=1):
        event = persisted_event["value"]
        if (
            persisted_event["store_ordinal"] != ordinal
            or set(event) != set(EXPECTED_DATACLASS_FIELDS[DomainEvent])
            or event["event_id"] != f"demo-event-{ordinal:08d}"
            or event["session_id"] != "demo-session-00000001"
            or event["sequence_no"] != ordinal
            or set(event["payload"]) != payload_fields[event["event_type"]]
        ):
            raise RuntimeError("private source event representation differs")


def _sha256_private_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _private_component_digests(
    representation: dict[str, Any],
) -> dict[str, str]:
    if set(representation) != EXPECTED_PRIVATE_COMPONENTS:
        raise RuntimeError("private replay representation key set differs")
    return {
        key: hashlib.sha256(
            json.dumps(
                representation[key],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        for key in sorted(representation)
    }


def _assert_frozen_private_representation(
    representation: dict[str, Any], identity_family: str
) -> None:
    # The readable specification-derived checks are the source of authority.
    # Content addresses are consulted only after that representation has proved
    # structurally complete and reproducible.
    _assert_independent_private_source_representation(
        representation, identity_family
    )
    expected_raw = EXPECTED_RAW_PRIVATE_COMPONENT_DIGESTS.get(identity_family)
    expected_equivalence = EXPECTED_CALLER_EQUIVALENCE_COMPONENT_DIGESTS.get(
        identity_family
    )
    if (
        expected_raw is None
        or set(expected_raw) != EXPECTED_PRIVATE_COMPONENTS
        or expected_equivalence is None
        or set(expected_equivalence) != EXPECTED_PRIVATE_COMPONENTS
    ):
        raise RuntimeError("private replay expected representation is incomplete")
    raw_digests = _private_component_digests(representation)
    for component, expected_digest in expected_raw.items():
        if raw_digests[component] != expected_digest:
            raise RuntimeError(
                f"DEMO_CHILD_PRIVATE_{component.upper()}_MISMATCH"
            )
    equivalence_digests = _private_component_digests(
        _caller_identity_equivalence_representation(representation)
    )
    for component, expected_digest in expected_equivalence.items():
        if equivalence_digests[component] != expected_digest:
            raise RuntimeError(
                f"DEMO_CHILD_PRIVATE_EQUIVALENCE_{component.upper()}_MISMATCH"
            )


def _assert_final_private_state(
    runtime: Any, provider: CanonicalDemoProviderGuard
) -> None:
    snapshot = runtime.store.snapshot()
    if len(snapshot.sessions) != 1 or len(snapshot.snapshots) != 1:
        raise RuntimeError("canonical replay did not persist exactly one session")
    persisted_session = next(iter(snapshot.sessions.values())).session
    provider.assert_complete(persisted_session.session_id)
    state = next(iter(snapshot.snapshots.values())).state
    scenario_runtime = state["scenario_runtime"]
    expected_event_basis = (
        ("ScenarioStarted", None),
        ("ScenarioDecisionSelected", None),
        ("NarrativeOutcomeAccepted", "clinical.reviewed"),
        ("ScenarioRuntimeEventGenerated", "clue_group.player_alive.completed"),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioRuntimeEventGenerated", "disposal.protocol.accelerated"),
        ("ScenarioDecisionSelected", None),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioDecisionSelected", None),
        ("NarrativeOutcomeAccepted", "record.route.verified"),
        ("NarrativeOutcomeAccepted", "audit.route.verified"),
        ("ScenarioRuntimeEventGenerated", "deadline.critical"),
        ("ScenarioRuntimeEventGenerated", "clue_group.record_order.completed"),
        ("ScenarioRuntimeEventGenerated", "clue_group.causation.completed"),
        ("ScenarioDecisionSelected", None),
        ("ScenarioRuntimeEventGenerated", "patient.stability.critical"),
        ("NarrativeOutcomeAccepted", "patient.route.verified"),
        ("ScenarioRuntimeEventGenerated", "clue_group.patient_alive.completed"),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioAutoBeatAdvanced", None),
        ("ScenarioDecisionSelected", None),
        ("ScenarioDecisionSelected", None),
        ("ScenarioDecisionSelected", None),
        ("ScenarioDecisionSelected", "core.conflict.resolved"),
    )
    actual_event_basis = tuple(
        (
            event.event_type,
            event.payload.get("scenario_event_type")
            if event.event_type
            in {"NarrativeOutcomeAccepted", "ScenarioRuntimeEventGenerated"}
            or event.sequence_no == 27
            else None,
        )
        for event in snapshot.events
    )
    jobs = tuple(
        sorted(
            snapshot.narrative_jobs.values(),
            key=lambda job: (job.created_at, job.job_id),
        )
    )
    clocks = scenario_runtime["threat_clocks"]
    action_event_counts: list[int] = []
    previous_turn_id: str | None = None
    for event in snapshot.events[1:]:
        if event.turn_id != previous_turn_id:
            action_event_counts.append(0)
            previous_turn_id = event.turn_id
        action_event_counts[-1] += 1
    expected_event_times = [
        datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=1)
    ]
    next_clock_offset = 2
    for action_number, event_count in enumerate(
        (1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 4, 2, 2, 1, 1, 1, 1, 1, 1),
        start=1,
    ):
        if action_number in {2, 10, 11, 13}:
            next_clock_offset += 5
        for _ in range(event_count):
            expected_event_times.append(
                datetime(2000, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=next_clock_offset)
            )
            next_clock_offset += 1
        if action_number in {2, 10, 11, 13}:
            next_clock_offset += 1
        if action_number == 19:
            next_clock_offset += 1
    provider_descriptions = tuple(
        job.narrative_request["player_intent"]["description"]
        for job in jobs
        if job.prompt_schema_version != "local-server-template-v1"
    )
    checks = (
        (persisted_session.state_version == 19, "DEMO_CHILD_FINAL_SESSION_VERSION"),
        (len(snapshot.events) == 27, "DEMO_CHILD_FINAL_EVENT_COUNT"),
        (actual_event_basis == expected_event_basis, "DEMO_CHILD_FINAL_EVENT_ORDER"),
        (
            tuple(action_event_counts)
            == (1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 4, 2, 2, 1, 1, 1, 1, 1, 1),
            "DEMO_CHILD_FINAL_EVENT_DISTRIBUTION",
        ),
        (
            tuple(event.event_id for event in snapshot.events)
            == tuple(f"demo-event-{index:08d}" for index in range(1, 28)),
            "DEMO_CHILD_FINAL_EVENT_IDS",
        ),
        (
            tuple(event.occurred_at for event in snapshot.events)
            == tuple(expected_event_times)
            and next_clock_offset == 53,
            "DEMO_CHILD_FINAL_EVENT_TIMES",
        ),
        (len(jobs) == 5, "DEMO_CHILD_FINAL_JOB_COUNT"),
        (
            len(snapshot.turn_requests) == 19,
            "DEMO_CHILD_FINAL_TURN_REQUEST_COUNT",
        ),
        (
            provider.completed_calls(persisted_session.session_id) == 4,
            "DEMO_CHILD_FINAL_PROVIDER_COUNT",
        ),
        (
            all(job.status.value == "COMMITTED" for job in jobs),
            "DEMO_CHILD_FINAL_JOB_STATUS",
        ),
        (
            sum(
                job.prompt_schema_version == "local-server-template-v1"
                for job in jobs
            )
            == 1,
            "DEMO_CHILD_FINAL_LOCAL_JOB",
        ),
        (
            provider_descriptions
            == (
                "请协调员复核我的连续回应和生命体征",
                "沿记录与档案审计路径核对签发时间",
                "核对日志时间顺序以及规程反馈",
                "复核地下患者的生命体征与连续监测历史",
            ),
            "DEMO_CHILD_FINAL_JOB_ORDER",
        ),
        (
            all(job.accepted_narrative_text is not None for job in jobs),
            "DEMO_CHILD_FINAL_RECENT_TEXTS",
        ),
        (
            tuple(job.job_id for job in jobs)
            == tuple(f"demo-job-{index:08d}" for index in range(1, 6)),
            "DEMO_CHILD_FINAL_JOB_IDS",
        ),
        (
            tuple(job.created_at.second for job in jobs) == (3, 19, 26, 38, 52)
            and tuple(job.updated_at.second for job in jobs)
            == (10, 25, 35, 45, 52),
            "DEMO_CHILD_FINAL_JOB_TIMES",
        ),
        (
            next(iter(snapshot.sessions.values())).created_at
            == datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=1)
            and next(iter(snapshot.sessions.values())).updated_at
            == datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=51),
            "DEMO_CHILD_FINAL_SESSION_TIMES",
        ),
        (
            len(snapshot.controller_bindings) == 1
            and len(snapshot.player_character_id_allocations) == 1
            and len(snapshot.player_character_revisions) == 1
            and len(snapshot.player_character_current) == 1
            and len(snapshot.player_character_creation_receipts) == 1
            and not snapshot.player_character_mutation_receipts,
            "DEMO_CHILD_FINAL_PLAYER_CHARACTER_AUTHORITY",
        ),
        (
            len(snapshot.run_revisions) == 3
            and len(snapshot.run_current) == 1
            and len(snapshot.run_participations) == 1
            and len(snapshot.run_creation_receipts) == 1
            and len(snapshot.run_mutation_receipts) == 2
            and next(iter(snapshot.run_current.values())).lifecycle_status
            == "active"
            and next(iter(snapshot.run_current.values())).state_version == 3
            and next(
                iter(snapshot.run_current.values())
            ).active_player_character_id
            == "pc.demo-00000001",
            "DEMO_CHILD_FINAL_RUN_AUTHORITY",
        ),
        (clocks["security_alert"]["value"] == 1, "DEMO_CHILD_FINAL_CLOCK_A"),
        (
            clocks["underground_patient_stability"]["value"] == 5,
            "DEMO_CHILD_FINAL_CLOCK_B",
        ),
        (
            scenario_runtime["ending_status"] == "RESOLVED",
            "DEMO_CHILD_FINAL_ENDING_STATUS",
        ),
        (
            scenario_runtime["ending_id"]
            == "death_certificate.ending.protocol_broken",
            "DEMO_CHILD_FINAL_ENDING_ID",
        ),
        (
            set(scenario_runtime["completed_clue_group_ids"])
            == {
                "death_record_predates_diagnosis",
                "player_is_alive",
                "prediction_causes_outcome",
                "underground_patient_alive",
            },
            "DEMO_CHILD_FINAL_CLUE_GROUPS",
        ),
        (
            not any(
                "patient.stability.failed"
                in json.dumps(event.payload, ensure_ascii=False)
                for event in snapshot.events
            ),
            "DEMO_CHILD_FINAL_FORBIDDEN_EVENT",
        ),
    )
    for passed, code in checks:
        if not passed:
            raise RuntimeError(code)
def _apply_private_mutation(
    representation: dict[str, Any], mutation: str | None
) -> None:
    if mutation is None:
        return
    session = representation["sessions"][0]["value"]
    snapshot = representation["snapshots"][0]["value"]
    state = snapshot["state"]
    turn = representation["turn_requests"][0]
    event = representation["events"][0]["value"]
    job = representation["narrative_jobs"][0]["value"]
    if mutation == "hidden_fact":
        state["scenario_runtime"]["mutable_fact_values"][
            "death_certificate.fact.security_posture"
        ] = "tampered"
    elif mutation == "evidence_entry":
        state["scenario_runtime"]["narrative_outcome_evidence"][0][
            "outcome_rule_id"
        ] = "tampered.rule"
    elif mutation == "event_payload":
        for persisted_event in representation["events"]:
            payload = persisted_event["value"]["payload"]
            for key, value in tuple(payload.items()):
                if type(value) is bool:
                    payload[key] = not value
                elif type(value) is int:
                    payload[key] = value + 1
                elif type(value) is str:
                    payload[key] = value + ".tampered"
                elif isinstance(value, list):
                    payload[key] = [*value, "tampered"]
                else:
                    payload[key] = "tampered"
    elif mutation == "job_field":
        job["model_name"] = "tampered-model"
    elif mutation == "snapshot_field":
        state["player"]["player_id"] = "tampered-player"
    elif mutation == "session_field":
        session["session"]["phase"] = "tampered-phase"
    elif mutation == "session_creation":
        session["created_at"] = "2001-01-01T00:00:00+00:00"
    elif mutation == "session_update":
        session["updated_at"] = "2001-01-01T00:00:00+00:00"
    elif mutation == "public_state":
        state["player"]["resources"]["composure"]["current"] = 5
    elif mutation == "snapshot_metadata":
        snapshot["state_version"] = 18
    elif mutation == "creation_index":
        representation["creation_keys"][0]["session_id"] = "tampered-session"
    elif mutation == "turn_store_session":
        turn["store_session_id"] = "tampered-session"
    elif mutation == "turn_store_request":
        turn["store_client_request_id"] = "tampered-request"
    elif mutation == "turn_id":
        turn["value"]["turn_id"] = "tampered-turn"
    elif mutation == "turn_action_signature":
        turn["value"]["action_signature"] = "0" * 64
    elif mutation == "turn_response":
        turn["value"]["response"]["result_code"] = "TAMPERED"
    elif mutation == "event_id":
        event["event_id"] = "tampered-event"
    elif mutation == "event_sequence":
        event["sequence_no"] = 99
    elif mutation == "event_type":
        event["event_type"] = "TamperedEvent"
    elif mutation == "event_subtype":
        narrative_event = next(
            item["value"]
            for item in representation["events"]
            if "scenario_event_type" in item["value"]["payload"]
        )
        narrative_event["payload"]["scenario_event_type"] = "tampered.subtype"
    elif mutation == "event_timestamp":
        event["occurred_at"] = "2001-01-01T00:00:00+00:00"
    elif mutation == "job_id":
        job["job_id"] = "tampered-job"
    elif mutation == "job_status":
        job["status"] = "FAILED_TERMINAL"
    elif mutation == "job_payload":
        job["narrative_request"]["public_story_summary"] = "tampered"
    elif mutation == "job_created_at":
        job["created_at"] = "2001-01-01T00:00:00+00:00"
    elif mutation == "job_updated_at":
        job["updated_at"] = "2001-01-01T00:00:00+00:00"
    elif mutation == "job_lease_owner":
        job["lease_owner"] = "tampered-worker"
    elif mutation == "job_lease_token":
        job["lease_token"] = "tampered-lease-token-000000000000"
    elif mutation == "job_fencing":
        job["attempt_count"] = 0
    elif mutation == "job_lifecycle":
        job["error_code"] = "TAMPERED"
    elif mutation == "authority_progress":
        representation["provider_progress"][0]["completed_calls"] = 3
    elif mutation == "controller_binding":
        representation["controller_bindings"][0]["value"][
            "created_at"
        ] = "2001-01-01T00:00:00+00:00"
    elif mutation == "player_character_allocation":
        representation["player_character_id_allocations"][0][
            "store_player_character_id"
        ] = "pc.tampered"
    elif mutation == "player_character_revision":
        representation["player_character_revisions"][0]["value"][
            "record_revision"
        ] = 2
    elif mutation == "player_character_current":
        representation["player_character_current"][0]["value"][
            "lifecycle"
        ] = "retired"
    elif mutation == "player_character_creation_receipt":
        representation["player_character_creation_receipts"][0][
            "store_operation_id"
        ] = "tampered-operation"
    elif mutation == "player_character_mutation_receipt":
        representation["player_character_mutation_receipts"].append(
            {"tampered": True}
        )
    elif mutation == "run_revision":
        representation["run_revisions"][0]["value"]["state_version"] = 99
    elif mutation == "run_current":
        representation["run_current"][0]["value"][
            "lifecycle_status"
        ] = "ended"
    elif mutation == "run_participation":
        representation["run_participations"][0][
            "store_session_id"
        ] = "tampered-session"
    elif mutation == "run_creation_receipt":
        representation["run_creation_receipts"][0][
            "store_operation_id"
        ] = "tampered-operation"
    elif mutation == "run_mutation_receipt":
        representation["run_mutation_receipts"][0]["value"][
            "expected_state_version"
        ] = 99
    else:  # pragma: no cover - argparse owns the closed vocabulary
        raise RuntimeError("unknown private mutation")


def _adopt_pipe(handle: int, *, write: bool) -> BinaryIO:
    if os.name == "nt":
        import msvcrt

        flags = os.O_BINARY | (os.O_WRONLY if write else os.O_RDONLY)
        descriptor = msvcrt.open_osfhandle(handle, flags)
    else:
        descriptor = handle
    return os.fdopen(descriptor, "wb" if write else "rb", buffering=0)


async def _run(args: argparse.Namespace, trace_stream: BinaryIO, control_stream: BinaryIO) -> None:
    _assert_sanitized_environment()
    _trap_external_runtime_constructors()
    restore_network = _deny_non_loopback_connections()
    trace = TraceWriter(trace_stream)
    runtime = None
    server = None
    try:
        generators = _traced_generators(trace)
        store = DemoProcessStore()
        runtime = build_demo_runtime(
            store=store,
            generators=generators,
        )
        provider = runtime.services.turn_orchestrator._guard()
        if not isinstance(provider, CanonicalDemoProviderGuard):
            raise RuntimeError("Demo orchestrator did not install its private Provider guard")
        app = create_app(services=runtime.services)
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=args.port,
            workers=1,
            reload=False,
            access_log=False,
            log_level="critical",
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        control_task = asyncio.create_task(asyncio.to_thread(control_stream.read))
        done, _ = await asyncio.wait(
            (server_task, control_task), return_when=asyncio.FIRST_COMPLETED
        )
        if server_task in done:
            await server_task
            raise RuntimeError("Demo replay server exited before STOP")
        control_frame = await control_task
        if control_frame != b"STOP\n":
            raise RuntimeError("invalid Demo replay control frame")
        control_stream.close()
        if args.fault_mode == "hang-after-stop":
            await asyncio.Event().wait()
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=10)
        if not server.started:
            raise RuntimeError("Demo replay server never started")
        _assert_final_private_state(runtime, provider)
        private_representation = _complete_raw_private_representation(runtime)
        _apply_private_mutation(private_representation, args.private_mutation)
        _assert_frozen_private_representation(
            private_representation, args.identity_family
        )
        trace.complete()
    finally:
        if server is not None:
            server.should_exit = True
        if runtime is not None:
            await runtime.provider.aclose()
        restore_network()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--trace-write-handle", type=int, required=True)
    parser.add_argument("--control-read-handle", type=int, required=True)
    parser.add_argument(
        "--identity-family",
        choices=("same", "browser-a", "browser-b"),
        default="same",
    )
    parser.add_argument(
        "--private-mutation",
        choices=(
            "hidden_fact",
            "evidence_entry",
            "event_payload",
            "job_field",
            "snapshot_field",
            "session_field",
            "session_creation",
            "session_update",
            "public_state",
            "snapshot_metadata",
            "creation_index",
            "turn_store_session",
            "turn_store_request",
            "turn_id",
            "turn_action_signature",
            "turn_response",
            "event_id",
            "event_sequence",
            "event_type",
            "event_subtype",
            "event_timestamp",
            "job_id",
            "job_status",
            "job_payload",
            "job_created_at",
            "job_updated_at",
            "job_lease_owner",
            "job_lease_token",
            "job_fencing",
            "job_lifecycle",
            "authority_progress",
            "controller_binding",
            "player_character_allocation",
            "player_character_revision",
            "player_character_current",
            "player_character_creation_receipt",
            "player_character_mutation_receipt",
            "run_revision",
            "run_current",
            "run_participation",
            "run_creation_receipt",
            "run_mutation_receipt",
        ),
    )
    parser.add_argument(
        "--fault-mode",
        choices=(
            "diagnostic-nonzero",
            "early-exit-zero",
            "hang-before-ready",
            "hang-after-stop",
            "partial-trace-write",
            "partial-trace-writes",
            "none-progress-trace-write",
            "zero-progress-trace-write",
        ),
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port is outside the valid range")
    return args


def main() -> int:
    args = _parse_args()
    trace_stream = _adopt_pipe(args.trace_write_handle, write=True)
    control_stream = _adopt_pipe(args.control_read_handle, write=False)
    try:
        if args.fault_mode == "early-exit-zero":
            return 0
        if args.fault_mode == "diagnostic-nonzero":
            sys.stdout.write("faulting-child-stdout\n" * 16_384)
            sys.stderr.write("faulting-child-stderr\n" * 16_384)
            sys.stdout.flush()
            sys.stderr.flush()
            return 7
        if args.fault_mode == "hang-before-ready":
            threading.Event().wait()
            return 1  # pragma: no cover - the parent owns termination
        if args.fault_mode == "partial-trace-write":
            trace_stream = _PartialWriteStream(
                trace_stream,
                maximum_write=7,
                partial_write_count=1,
            )  # type: ignore[assignment]
        elif args.fault_mode == "partial-trace-writes":
            trace_stream = _PartialWriteStream(
                trace_stream, maximum_write=7
            )  # type: ignore[assignment]
        elif args.fault_mode in {
            "none-progress-trace-write",
            "zero-progress-trace-write",
        }:
            trace_stream = _PartialWriteStream(
                trace_stream,
                maximum_write=1,
                none_progress=args.fault_mode == "none-progress-trace-write",
                zero_progress=args.fault_mode == "zero-progress-trace-write",
            )  # type: ignore[assignment]
            TraceWriter(trace_stream).record("SEED", 1)
        asyncio.run(_run(args, trace_stream, control_stream))
        return 0
    except BaseException as exc:
        del exc
        sys.stderr.write("DEMO_REPLAY_CHILD_FAILED\n")
        return 1
    finally:
        if not control_stream.closed:
            control_stream.close()
        if not trace_stream.closed:
            trace_stream.close()


if __name__ == "__main__":
    raise SystemExit(main())
