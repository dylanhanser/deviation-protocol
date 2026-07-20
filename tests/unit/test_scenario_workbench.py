from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import pytest

from deviation_protocol.application.scenario_analysis import (
    ProofState,
    ScenarioAnalyzer,
    build_initial_preview,
    frame_budget,
)
from deviation_protocol.application.scenario_event_bridge import (
    ScenarioDecisionResponsePolicy,
    bind_public_decision_frame,
)
from deviation_protocol.application.scenario_initialization import (
    initialize_scenario_state,
    profession_tags_for,
)
from deviation_protocol.application.story_director import DeterministicStoryDirector
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.scenario import ScenarioCatalog
from deviation_protocol.domain.state import DomainRuleViolation, GameState, PlayerState
from deviation_protocol.infrastructure.content_loader import (
    ContentPackLoadError,
    JsonContentCatalogLoader,
    MAX_CONTENT_PACK_BYTES,
)
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.tools.scenario import main
from tests.unit.test_story_director import mini_catalog


ROOT = Path(__file__).parents[2]
FORMAL_PACK = ROOT / "config" / "scenarios" / "death_certificate_v1.json"
FORMAL_CHARACTER = "character.death_certificate.investigator"


@pytest.fixture
def non_hospital_pack(tmp_path: Path) -> tuple[Path, ScenarioCatalog]:
    catalog = mini_catalog()
    path = tmp_path / "alpine.json"
    path.write_text(catalog.model_dump_json(), encoding="utf-8")
    return path, catalog


def invoke_json(capsys: pytest.CaptureFixture[str], *arguments: str) -> tuple[int, dict]:
    code = main([*arguments, "--json"])
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    return code, json.loads(captured.out)


def write_payload(tmp_path: Path, payload: dict, name: str = "scenario.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_formal_scenario_validate_succeeds_with_authoritative_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, payload = invoke_json(capsys, "validate", str(FORMAL_PACK))
    assert code == 0
    result = payload["result"]
    assert result["counts"] == {
        "clocks": 4,
        "clue_groups": 4,
        "clues": 12,
        "decisions": 9,
        "endings": 3,
        "facts": 15,
        "outcome_rules": 11,
        "phases": 7,
        "transitions": 6,
    }
    assert result["diagnostic_counts"] == {"error": 0, "info": 1, "warning": 0}


def test_non_hospital_fixture_uses_validate_analyze_and_preview(
    non_hospital_pack: tuple[Path, ScenarioCatalog],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, _ = non_hospital_pack
    validate_code, _ = invoke_json(capsys, "validate", str(path))
    analyze_code, analysis = invoke_json(capsys, "analyze", str(path))
    preview_code, preview = invoke_json(
        capsys,
        "preview",
        str(path),
        "--character-id",
        "character.alpine.scout",
    )
    assert validate_code == analyze_code == preview_code == 0
    assert analysis["result"]["scenario_id"] == "alpine_signal"
    assert preview["result"]["visible_npc_ids"] == ["scenario-npc-1"]


def test_cli_runs_outside_repository_and_never_prints_absolute_input_path(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "deviation_protocol.tools.scenario",
            "validate",
            str(FORMAL_PACK),
            "--json",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert str(ROOT) not in completed.stdout
    assert "Traceback" not in completed.stderr


def test_json_output_is_byte_stable_and_input_is_not_modified(
    non_hospital_pack: tuple[Path, ScenarioCatalog],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, _ = non_hospital_pack
    before = hashlib.sha256(path.read_bytes()).digest()
    before_stat = path.stat()
    assert main(["analyze", str(path), "--json"]) == 0
    first = capsys.readouterr().out.encode("utf-8")
    assert main(["analyze", str(path), "--json"]) == 0
    second = capsys.readouterr().out.encode("utf-8")
    assert first == second
    assert hashlib.sha256(path.read_bytes()).digest() == before
    after_stat = path.stat()
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_mode == before_stat.st_mode
    preview_args = [
        "preview",
        str(path),
        "--character-id",
        "character.alpine.scout",
        "--json",
    ]
    assert main(preview_args) == 0
    first_preview = capsys.readouterr().out.encode("utf-8")
    assert main(preview_args) == 0
    second_preview = capsys.readouterr().out.encode("utf-8")
    assert first_preview == second_preview


@pytest.mark.parametrize("kind", ["invalid_json", "duplicate_key", "extra_field"])
def test_invalid_json_duplicate_keys_and_extra_fields_fail_safely(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    path = tmp_path / "unsafe.json"
    if kind == "invalid_json":
        path.write_text("{", encoding="utf-8")
    elif kind == "duplicate_key":
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    else:
        payload = mini_catalog().model_dump(mode="json")
        payload["scenarios"][0]["unexpected"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
    code, output = invoke_json(capsys, "validate", str(path))
    assert code == 1
    assert output["error"]["code"] == "SCENARIO_PACK_INVALID"
    assert str(path) not in json.dumps(output)


def test_optional_unreachable_phase_is_a_blocking_analysis_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = mini_catalog().model_dump(mode="json")
    payload["scenarios"][0]["phases"].append(
        {
            "phase_id": "alpine.unused",
            "title": "Unused",
            "visible_location_ids": ["alpine.camp"],
            "allowed_action_types": ["observe"],
            "min_auto_beats": 0,
            "max_auto_beats": 0,
            "terminal": True,
            "required": False,
        }
    )
    path = write_payload(tmp_path, payload)
    code, output = invoke_json(capsys, "analyze", str(path))
    assert code == 2
    assert output["result"]["graph"]["unreachable_phase_ids"] == ["alpine.unused"]
    assert any(
        item["code"] == "PHASE_UNREACHABLE"
        for item in output["result"]["diagnostics"]
    )
    validate_code, validation = invoke_json(capsys, "validate", str(path))
    assert validate_code == 2
    assert validation["result"]["diagnostic_counts"]["error"] == 1
    assert [
        item["code"] for item in validation["result"]["diagnostics"]
        if item["severity"] == "error"
    ] == ["PHASE_UNREACHABLE"]


def test_illegal_endpoint_and_unbounded_automatic_cycle_fail_in_loader(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    endpoint = mini_catalog().model_dump(mode="json")
    endpoint_phase = endpoint["scenarios"][0]["phases"][0]
    endpoint_phase["transitions"] = []
    endpoint_path = write_payload(tmp_path, endpoint, "endpoint.json")
    endpoint_code, _ = invoke_json(capsys, "analyze", str(endpoint_path))
    assert endpoint_code == 1

    cycle = mini_catalog().model_dump(mode="json")
    transition = cycle["scenarios"][0]["phases"][0]["transitions"][0]
    transition["target_phase_id"] = "alpine.search"
    transition["trigger"] = "AUTOMATIC"
    cycle["scenarios"][0]["phases"][1]["required"] = False
    cycle_path = write_payload(tmp_path, cycle, "cycle.json")
    cycle_code, _ = invoke_json(capsys, "analyze", str(cycle_path))
    assert cycle_code == 1


def test_bounded_cycle_analysis_finishes_and_reports_cycle(tmp_path: Path) -> None:
    payload = mini_catalog().model_dump(mode="json")
    transition = payload["scenarios"][0]["phases"][0]["transitions"][0]
    transition["target_phase_id"] = "alpine.search"
    transition["trigger"] = "AUTOMATIC"
    transition["max_uses"] = 1
    payload["scenarios"][0]["phases"][1]["required"] = False
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    assert len(report.graph.cycles) == 1
    assert report.graph.cycles[0].bounded is True
    assert report.graph.cycles[0].automatic_only is True
    assert any(item.code == "AUTOMATIC_CYCLE_BOUNDED" for item in report.diagnostics)


def test_clue_source_states_do_not_claim_guaranteed_discovery(tmp_path: Path) -> None:
    payload = mini_catalog().model_dump(mode="json")
    definition = payload["scenarios"][0]
    definition["narrative_outcome_rules"] = [
        {
            "rule_id": "alpine.outcome.signal",
            "rule_version": "1",
            "allowed_phase_ids": ["alpine.summit"],
            "intent": {"action_types": ["OBSERVE"]},
            "safe_description": "Observe a declared public signal.",
            "effects": [
                {
                    "result": "SUCCESS",
                    "event_type": "signal.verified",
                    "action_type": "observe",
                    "discovered_clue_ids": ["alpine.clue.signal_trace"],
                }
            ],
            "mutex_group": "alpine.signal",
        }
    ]
    loaded = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    clue = ScenarioAnalyzer().analyze(loaded).clues[0]
    assert clue.has_declared_source is True
    assert clue.source_structurally_reachable is False
    assert clue.source_condition_satisfiable_unknown is ProofState.NO
    assert clue.guaranteed_discoverable is ProofState.NO


def test_no_declared_clue_producer_and_clock_without_source_are_reported(
    tmp_path: Path,
) -> None:
    payload = mini_catalog().model_dump(mode="json")
    payload["scenarios"][0]["phases"][0]["action_time_costs"] = []
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    codes = {item.code for item in report.diagnostics}
    assert "CLUE_NO_DECLARED_DISCOVERY_PRODUCER" in codes
    assert "CLOCK_NO_PROGRESSION_SOURCE" in codes
    assert report.clocks[0].unreachable_thresholds == (2,)
    assert report.clocks[0].has_declared_progression_source is False
    assert report.clocks[0].source_structurally_reachable is False
    assert report.clocks[0].guaranteed_to_progress is ProofState.NO


def test_illegal_clock_threshold_is_rejected_by_authoritative_loader(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = mini_catalog().model_dump(mode="json")
    payload["scenarios"][0]["threat_clocks"][0]["thresholds"][0]["threshold"] = 99
    code, _ = invoke_json(capsys, "analyze", str(write_payload(tmp_path, payload)))
    assert code == 1


def test_decision_analysis_distinguishes_sparse_and_dense_rapid_phases() -> None:
    catalog = JsonScenarioCatalogLoader(FORMAL_PACK).load()
    report = ScenarioAnalyzer().analyze(catalog.scenarios[0])
    phases = {item.phase_id: item for item in report.decision_cadence}
    sparse = phases["death_certificate.investigation"]
    rapid = phases["death_certificate.core_conflict"]
    assert sparse.cadence_type == "sparse"
    assert sparse.rapid_decision_allowed is False
    assert sparse.signals_are_heuristic is True
    assert rapid.cadence_type == "rapid"
    assert rapid.rapid_has_high_choice_density is ProofState.YES
    heuristic_diagnostics = [
        item for item in report.diagnostics if item.code.endswith("_HEURISTIC")
    ]
    assert all(item.severity.value == "warning" for item in heuristic_diagnostics)
    assert all(item.metadata.get("heuristic") is True for item in heuristic_diagnostics)


def test_preview_uses_real_character_and_does_not_leak_hidden_authority() -> None:
    catalog = JsonScenarioCatalogLoader(FORMAL_PACK).load()
    definition = catalog.scenarios[0]
    build = build_initial_preview(
        catalog.content_catalog,
        definition,
        character_definition_id=FORMAL_CHARACTER,
    )
    encoded = build.report.model_dump_json()
    assert build.report.character_definition_id == FORMAL_CHARACTER
    assert build.report.active_decision is not None
    assert build.report.active_decision.decision_id.startswith("decision.")
    assert build.report.preview_identity_kind == "LOCAL_SYNTHETIC_PREVIEW"
    assert build.report.decision_binding_scope == "LOCAL_PREVIEW_ONLY"
    assert build.report.production_api_credential is False
    assert str(ROOT) not in encoded
    assert "Traceback" not in encoded
    assert " object at 0x" not in encoded
    for fact in definition.facts:
        if fact.visibility.value == "HIDDEN":
            assert fact.fact_id not in encoded
    for clue in definition.clues:
        assert clue.clue_id not in encoded
        assert clue.visible_summary not in encoded
    for clock in definition.threat_clocks:
        if not clock.player_visible:
            assert clock.clock_id not in encoded
            assert all(item.event_type not in encoded for item in clock.thresholds)
    assert all(ending.ending_id not in encoded for ending in definition.endings)
    assert all(
        reference.npc_definition_id not in encoded
        for reference in definition.npc_references
    )
    assert set(build.candidate_state.npcs) == {
        "scenario-npc-1",
        "scenario-npc-2",
        "scenario-npc-3",
    }
    for forbidden in (
        "death_certificate.decision.immediate_survival",
        "prediction_causes_outcome",
        "underground_patient_alive",
        "death_certificate.ending.",
        "death_certificate.outcome.",
        "npc.death_certificate.underground_patient",
        "security_alert",
        "underground_patient_stability",
        "outcome_token",
        "rule_id",
        "capability",
        "seal",
    ):
        assert forbidden not in encoded


def test_preview_report_is_deeply_isolated_from_temporary_game_state() -> None:
    catalog = mini_catalog()
    build = build_initial_preview(
        catalog.content_catalog,
        catalog.scenarios[0],
        character_definition_id="character.alpine.scout",
    )
    before = build.report.model_dump_json()
    frame_before = build.frame.model_dump_json()
    runtime = build.candidate_state.scenario_runtime
    assert runtime is not None
    runtime.dynamic_facts["dynamic.after_preview"] = "changed"
    build.candidate_state.player.wallet.credit("local", 1)
    assert build.report.model_dump_json() == before
    assert build.frame.model_dump_json() == frame_before


def test_preview_requires_character_and_rejects_bad_content_pack_safely(
    non_hospital_pack: tuple[Path, ScenarioCatalog],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, catalog = non_hospital_pack
    missing_code, missing = invoke_json(capsys, "preview", str(path))
    assert missing_code == 1
    assert missing["error"]["code"] == "CHARACTER_REQUIRED"

    invalid_code, invalid = invoke_json(
        capsys,
        "preview",
        str(path),
        "--character-id",
        "character.missing",
    )
    assert invalid_code == 1
    assert invalid["error"]["code"] == "CHARACTER_INVALID"

    content_payload = catalog.content_catalog.model_dump(mode="json")
    valid_content_path = write_payload(tmp_path, content_payload, "valid-content.json")
    valid_content_code, _ = invoke_json(
        capsys,
        "validate",
        str(path),
        "--content-pack",
        str(valid_content_path),
    )
    assert valid_content_code == 0

    content_payload["characters"] = []
    content_path = write_payload(tmp_path, content_payload, "content.json")
    content_code, content = invoke_json(
        capsys,
        "validate",
        str(path),
        "--content-pack",
        str(content_path),
    )
    assert content_code == 1
    assert content["error"]["code"] == "CONTENT_PACK_INVALID"


def test_cli_output_ignores_environment_secrets_and_urls(
    non_hospital_pack: tuple[Path, ScenarioCatalog],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, _ = non_hospital_pack
    secret = "workbench-secret-value"
    database_url = "mysql+asyncmy://user:password@example.invalid/private"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)
    monkeypatch.setenv("DATABASE_URL", database_url)
    code = main(["validate", str(path), "--json"])
    output = capsys.readouterr().out
    assert code == 0
    assert secret not in output
    assert database_url not in output
    assert str(path.parent.resolve()) not in output


def test_generic_modules_have_no_scenario_specific_identifiers_or_forbidden_layers() -> None:
    generic_files = (
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_analysis.py",
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_initialization.py",
        ROOT / "src" / "deviation_protocol" / "tools" / "scenario.py",
    )
    forbidden_identifiers = (
        "death_certificate",
        "hospital",
        "body_bag",
        "nurse",
        "唐芮",
        "段闻",
        "尸袋",
        "护士",
    )
    for path in generic_files:
        source = path.read_text(encoding="utf-8").lower()
        assert all(value not in source for value in forbidden_identifiers)

    application_sources = (
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_analysis.py",
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_initialization.py",
    )
    for path in application_sources:
        source = path.read_text(encoding="utf-8")
        assert "deviation_protocol.infrastructure" not in source
        assert "sqlalchemy" not in source.lower()
        assert "NarrativeProvider" not in source
        assert "Repository" not in source
        assert "UnitOfWork" not in source


def test_analysis_output_is_bounded() -> None:
    report = ScenarioAnalyzer().analyze(mini_catalog().scenarios[0])
    assert len(report.diagnostics) <= 256
    assert len(report.graph.reachable_phase_ids) <= 64


def test_shared_initialization_is_atomic_on_late_npc_id_collision() -> None:
    catalog = JsonScenarioCatalogLoader(FORMAL_PACK).load()
    character = catalog.content_catalog.character(FORMAL_CHARACTER)
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("scenario-npc-2", character),
    )
    before = state.to_snapshot()
    with pytest.raises(DomainRuleViolation):
        initialize_scenario_state(
            state,
            catalog.content_catalog,
            catalog.scenarios[0],
            character_tags=character.tags,
            story_director=DeterministicStoryDirector(),
        )
    assert state.to_snapshot() == before
    assert state.npcs == {}
    assert state.scenario_runtime is None


def test_conditional_transition_and_ending_remain_unknown(tmp_path: Path) -> None:
    payload = mini_catalog().model_dump(mode="json")
    transition = payload["scenarios"][0]["phases"][0]["transitions"][0]
    transition["conditions"] = [
        {"rule_type": "EVENT_OCCURRED", "event_type": "route.chosen"}
    ]
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    analyzed_transition = report.graph.transitions[0]
    assert analyzed_transition.source_phase_reachable is True
    assert analyzed_transition.conditions_present is True
    assert analyzed_transition.condition_satisfiable_unknown is ProofState.UNKNOWN
    assert analyzed_transition.guaranteed_traversable is ProofState.UNKNOWN
    ending = report.graph.endings[0]
    assert ending.structurally_referenced is True
    assert ending.source_phase_reachable is ProofState.UNKNOWN
    assert ending.condition_satisfiable_unknown is ProofState.UNKNOWN
    assert ending.guaranteed_reachable is ProofState.UNKNOWN


def test_clue_producer_four_level_semantics_and_duplicate_idempotence(
    tmp_path: Path,
) -> None:
    no_source = ScenarioAnalyzer().analyze(mini_catalog().scenarios[0]).clues[0]
    assert no_source.has_declared_source is False
    assert no_source.source_structurally_reachable is False
    assert no_source.source_condition_satisfiable_unknown is ProofState.NO
    assert no_source.guaranteed_discoverable is ProofState.NO

    payload = mini_catalog().model_dump(mode="json")
    rule = {
        "rule_id": "alpine.outcome.signal.primary",
        "rule_version": "1",
        "allowed_phase_ids": ["alpine.search"],
        "intent": {"action_types": ["OBSERVE"]},
        "safe_description": "Observe a declared signal.",
        "effects": [
            {
                "result": "SUCCESS",
                "event_type": "signal.verified",
                "action_type": "observe",
                "discovered_clue_ids": ["alpine.clue.signal_trace"],
            }
        ],
        "mutex_group": "alpine.signal.primary",
    }
    duplicate = {
        **rule,
        "rule_id": "alpine.outcome.signal.secondary",
        "mutex_group": "alpine.signal.secondary",
    }
    payload["scenarios"][0]["narrative_outcome_rules"] = [rule, duplicate]
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    clue = report.clues[0]
    assert clue.has_declared_source is True
    assert clue.source_structurally_reachable is True
    assert clue.source_condition_satisfiable_unknown is ProofState.UNKNOWN
    assert clue.guaranteed_discoverable is ProofState.UNKNOWN
    assert clue.producer_types == ("narrative_outcome_rule",)
    assert report.clue_groups[0].declared_clue_count == 1
    assert report.clue_groups[0].structurally_sourceable_count == 1


def test_cadence_warning_is_explicitly_heuristic_and_non_blocking(
    tmp_path: Path,
) -> None:
    payload = mini_catalog().model_dump(mode="json")
    scenario = payload["scenarios"][0]
    scenario["decision_windows"][0]["conditions"] = []
    scenario["phases"][0]["max_auto_beats"] = 8
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    warning = next(
        item for item in report.diagnostics
        if item.code == "DECISION_GAP_LONG_HEURISTIC"
    )
    assert warning.severity.value == "warning"
    assert warning.metadata == {"gap_beats": 7, "heuristic": True, "threshold_beats": 4}
    assert report.diagnostic_counts.error == 0


def test_hidden_clock_change_cannot_change_public_frame_id_or_budget() -> None:
    catalog = JsonScenarioCatalogLoader(FORMAL_PACK).load()
    definition = catalog.scenarios[0]
    character = catalog.content_catalog.character(FORMAL_CHARACTER)
    assert character is not None
    build = build_initial_preview(
        catalog.content_catalog,
        definition,
        character_definition_id=FORMAL_CHARACTER,
    )
    changed = build.candidate_state.detached_copy(catalog.content_catalog)
    runtime = changed.scenario_runtime
    assert runtime is not None
    hidden_clock = next(item for item in definition.threat_clocks if not item.player_visible)
    runtime.threat_clocks[hidden_clock.clock_id].value += 1
    raw = DeterministicStoryDirector().plan_frame(
        changed,
        definition,
        profession_tags=profession_tags_for(character.tags, definition),
    )
    rebound = bind_public_decision_frame(
        raw,
        session_id="scenario-workbench-preview",
        state_version=0,
        scenario_content_version=definition.content_version,
    )
    assert rebound == build.frame
    assert rebound.frame_id == build.report.frame_id
    assert frame_budget(rebound, label="initial_public_frame") == build.report.budget


def test_preview_decision_binding_is_rejected_for_a_real_session() -> None:
    catalog = JsonScenarioCatalogLoader(FORMAL_PACK).load()
    definition = catalog.scenarios[0]
    build = build_initial_preview(
        catalog.content_catalog,
        definition,
        character_definition_id=FORMAL_CHARACTER,
    )
    assert build.report.active_decision is not None
    raw_real = DeterministicStoryDirector().plan_frame(
        build.candidate_state,
        definition,
    )
    real_frame = bind_public_decision_frame(
        raw_real,
        session_id="session-real",
        state_version=0,
        scenario_content_version=definition.content_version,
    )
    preview_decision = build.report.active_decision
    submission = ActionSubmission(
        session_id="session-real",
        turn_id="turn-1",
        client_request_id="preview-cross-session",
        action_type=ActionType.CHOOSE,
        decision_id=preview_decision.decision_id,
        choice_id=preview_decision.suggested_actions[0].action_id,
    )
    assert preview_decision.decision_id != real_frame.decision_id
    with pytest.raises(ValueError, match="stale or not authoritative"):
        ScenarioDecisionResponsePolicy().validate(
            submission,
            real_frame,
            state=build.candidate_state,
            definition=definition,
            state_version=0,
        )


def test_json_error_is_byte_stable_and_path_free(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "不存在 secret scenario.json"
    arguments = ["validate", str(missing), "--json"]
    assert main(arguments) == 1
    first = capsys.readouterr()
    assert main(arguments) == 1
    second = capsys.readouterr()
    assert first.out.encode("utf-8") == second.out.encode("utf-8")
    assert first.err == second.err == ""
    assert str(missing) not in first.out
    assert str(tmp_path.resolve()) not in first.out
    assert "Traceback" not in first.out
    assert json.loads(first.out)["error"]["code"] == "INPUT_PATH_INVALID"


@pytest.mark.parametrize("kind", ["duplicate_key", "nonstandard_number", "too_deep", "oversized"])
def test_external_content_loader_has_strict_json_resource_boundaries(
    tmp_path: Path,
    kind: str,
) -> None:
    path = tmp_path / "external content 中文.json"
    if kind == "duplicate_key":
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    elif kind == "nonstandard_number":
        path.write_text('{"schema_version":NaN}', encoding="utf-8")
    elif kind == "too_deep":
        path.write_text("[" * 34 + "0" + "]" * 34, encoding="utf-8")
    else:
        path.write_text(" " * (MAX_CONTENT_PACK_BYTES + 1), encoding="utf-8")
    with pytest.raises(ContentPackLoadError):
        JsonContentCatalogLoader(path).load()


def test_cli_rejects_oversized_paths_and_character_ids_without_echoing_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    oversized_path = "x" * 1_025
    path_code, path_error = invoke_json(capsys, "validate", oversized_path)
    assert path_code == 1
    assert path_error["error"]["code"] == "INPUT_PATH_INVALID"
    assert oversized_path not in json.dumps(path_error)
    character_code, character_error = invoke_json(
        capsys,
        "preview",
        str(FORMAL_PACK),
        "--character-id",
        "c" * 129,
    )
    assert character_code == 1
    assert character_error["error"]["code"] == "CHARACTER_INVALID"


def test_dense_acyclic_graph_validation_is_bounded(tmp_path: Path) -> None:
    payload = mini_catalog().model_dump(mode="json")
    scenario = payload["scenarios"][0]
    phases: list[dict] = []
    phase_ids = ["alpine.search", *(f"alpine.dag.{index:02d}" for index in range(1, 47)), "alpine.summit"]
    for index, phase_id in enumerate(phase_ids):
        if index == len(phase_ids) - 1:
            phases.append(
                {
                    "phase_id": phase_id,
                    "title": "Terminal",
                    "visible_location_ids": ["alpine.ridge"],
                    "allowed_action_types": ["observe"],
                    "min_auto_beats": 0,
                    "max_auto_beats": 0,
                    "terminal": True,
                }
            )
            continue
        transitions = [
            {
                "transition_id": f"alpine.dag.transition.{index:02d}.{target:02d}",
                "target_phase_id": phase_ids[target],
                "trigger": "VERIFIED_EVENT",
            }
            for target in range(index + 1, len(phase_ids))
        ]
        phase = {
            "phase_id": phase_id,
            "title": f"Node {index}",
            "visible_location_ids": ["alpine.camp", "alpine.ridge"],
            "allowed_action_types": ["observe"],
            "min_auto_beats": 0,
            "max_auto_beats": 0,
            "transitions": transitions,
        }
        if index == 0:
            phase.update(
                {
                    "must_render_fact_ids": ["alpine.fact.weather"],
                    "allowed_clue_ids": ["alpine.clue.signal_trace"],
                }
            )
        phases.append(phase)
    scenario["phases"] = phases
    scenario["decision_windows"] = []
    started = perf_counter()
    definition = JsonScenarioCatalogLoader(write_payload(tmp_path, payload)).load().scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    elapsed = perf_counter() - started
    assert len(report.graph.transitions) == len(phase_ids) * (len(phase_ids) - 1) // 2
    assert report.graph.cycles == ()
    assert elapsed < 2.0


def test_cli_import_has_no_database_provider_or_engine_side_effects(tmp_path: Path) -> None:
    command = (
        "import json,sys; import deviation_protocol.tools.scenario; "
        "names=('deviation_protocol.infrastructure.database',"
        "'deviation_protocol.infrastructure.deepseek_narrative',"
        "'deviation_protocol.infrastructure.orm_models',"
        "'sqlalchemy'); "
        "print(json.dumps([name for name in names if name in sys.modules]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == []


def test_domain_and_application_dependency_direction_scan() -> None:
    source_root = ROOT / "src" / "deviation_protocol"
    forbidden = {
        "domain": ("deviation_protocol.application", "deviation_protocol.infrastructure", "deviation_protocol.tools"),
        "application": ("deviation_protocol.infrastructure", "deviation_protocol.tools"),
    }
    for layer, prefixes in forbidden.items():
        for path in (source_root / layer).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert all(prefix not in source for prefix in prefixes), path
