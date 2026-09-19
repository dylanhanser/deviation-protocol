"""Authored archive identity and synthetic selector controls (not public play)."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader

PACK = Path(__file__).parents[2] / "config/scenarios/receipt_archive_v1.json"


def test_r04_independently_pinned_archive_bytes_and_preserved_mechanical_definitions():
    raw = PACK.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39"
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\n")
    archive = json.loads(raw)
    old = json.loads(PACK.with_name("undelivered_receipt_v1.json").read_bytes())
    for field in ("characters", "items", "equipment", "skills", "effects"):
        assert archive["content_catalog"][field] == old["content_catalog"][field]
    definition = JsonScenarioCatalogLoader(PACK).load().scenarios[0]
    assert not definition.threat_clocks and not definition.npc_references
    assert len(definition.locations) == 1


@pytest.mark.parametrize("events,sealed,expected", [
    (("receipt_archive.record.sealed",), True, "unresolved_sealed"),
    (("receipt_archive.review.deferred",), False, "review_deferred"),
    (("receipt_archive.record.sealed", "receipt_archive.review.deferred"), True, "unresolved_sealed"),
])
def test_r10_synthetic_ending_priority_and_reversed_definition_order(events, sealed, expected):
    definition = JsonScenarioCatalogLoader(PACK).load().scenarios[0]
    assert [(e.ending_id, e.priority) for e in definition.endings] == [
        ("receipt_archive.ending.unresolved_sealed", 10),
        ("receipt_archive.ending.review_deferred", 20)]
    runtime = ScenarioRuntimeState(scenario_id="receipt_archive",
        scenario_content_version="receipt-archive-1.0.0", current_phase_id="receipt_archive.decision",
        current_location_id="receipt_archive.audit_desk",
        mutable_fact_values={"receipt_archive.fact.unresolved_sealed": sealed})
    for endings in (definition.endings, tuple(reversed(definition.endings))):
        candidate = deepcopy(runtime)
        DeterministicStoryDirector()._apply_ending(candidate, definition.model_copy(update={"endings": endings}), events)
        assert candidate.ending_id == "receipt_archive.ending." + expected
        assert candidate.ending_status.value == ("RESOLVED" if expected == "unresolved_sealed" else "FAILED")
        assert not candidate.threat_clocks


@pytest.mark.parametrize("mutation", ["missing", "whitespace", "version", "digest", "line_endings"])
def test_required_archive_rejects_missing_and_same_version_substitution(mutation):
    from dataclasses import replace
    from deviation_protocol.application.session_content_registry import SessionContentBundle, SessionContentRegistry
    old = tuple(SessionContentBundle.from_bytes(PACK.with_name(name).read_bytes()) for name in ("death_certificate_v1.json", "undelivered_receipt_v1.json"))
    raw = PACK.read_bytes()
    with pytest.raises(ValueError):
        if mutation == "missing":
            SessionContentRegistry(old)
        elif mutation == "digest":
            replace(SessionContentBundle.from_bytes(raw), content_sha256="a" * 64)
        else:
            payload = raw + b" " if mutation == "whitespace" else raw.replace(b"\n", b"\r\n") if mutation == "line_endings" else raw.replace(b"receipt-archive-1.0.0", b"receipt-archive-1.0.1")
            SessionContentRegistry((*old, SessionContentBundle.from_bytes(payload)))
