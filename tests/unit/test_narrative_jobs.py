from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from deviation_protocol.application.narrative_jobs import (
    MAX_NARRATIVE_JOB_JSON_BYTES,
    NarrativeJob,
    NarrativeJobStatus,
)


NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


def _job(**updates: object) -> NarrativeJob:
    payload: dict[str, object] = {
        "job_id": "job-1",
        "session_id": "session-1",
        "turn_id": "turn-1",
        "client_request_id": "request-1",
        "action_signature": "a" * 64,
        "prepared_state_version": 0,
        "state_fingerprint": "b" * 64,
        "scenario_id": "scenario-1",
        "scenario_content_version": "1.0.0",
        "request_fingerprint": "c" * 64,
        "narrative_request": {"safe": "request"},
        "prompt_schema_version": "prompt-v1",
        "style_profile_version": "style-v1",
        "provider_name": "fake",
        "model_name": "fake-model",
        "created_at": NOW,
        "updated_at": NOW,
    }
    payload.update(updates)
    return NarrativeJob.model_validate(payload)


def test_job_json_rejects_floats_depth_and_encoded_storage_overflow() -> None:
    nested: object = "leaf"
    for _ in range(25):
        nested = {"next": nested}
    oversized = {f"field-{index}": "界" * 8_000 for index in range(8)}
    assert sum(len(value.encode("utf-8")) for value in oversized.values()) > (
        MAX_NARRATIVE_JOB_JSON_BYTES
    )

    for unsafe in ({"value": 1.5}, nested, oversized):
        with pytest.raises(ValidationError):
            _job(narrative_request=unsafe)


def test_only_committed_job_can_hold_player_visible_accepted_text() -> None:
    proposal = {"proposal": {"narrative_text": "candidate"}}
    with pytest.raises(ValidationError, match="only a committed job"):
        _job(
            status=NarrativeJobStatus.FAILED_TERMINAL,
            attempt_count=1,
            error_code="NARRATIVE_PROPOSAL_REJECTED",
            validated_proposal=proposal,
            validated_proposal_digest="d" * 64,
            accepted_narrative_text="must not be visible",
        )

    terminal = _job(
        status=NarrativeJobStatus.FAILED_TERMINAL,
        attempt_count=1,
        error_code="NARRATIVE_PROPOSAL_REJECTED",
        validated_proposal=proposal,
        validated_proposal_digest="d" * 64,
    )
    assert terminal.validated_proposal is not None
    assert terminal.accepted_narrative_text is None


def test_committed_job_requires_complete_candidate_rule_and_accepted_text() -> None:
    with pytest.raises(ValidationError, match="committed narrative job is incomplete"):
        _job(status=NarrativeJobStatus.COMMITTED, attempt_count=1)

    committed = _job(
        status=NarrativeJobStatus.COMMITTED,
        attempt_count=1,
        validated_proposal={"proposal": {"narrative_text": "candidate"}},
        validated_proposal_digest="d" * 64,
        outcome_rule_id="server.rule",
        accepted_narrative_text="accepted",
    )
    assert committed.accepted_narrative_text == "accepted"

