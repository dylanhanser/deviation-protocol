from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
    ScenarioPackLoadError,
)


PACK = Path(__file__).parents[2] / "config" / "scenarios" / "death_certificate_v1.json"
DESIGN_DOC = Path(__file__).parents[2] / "docs" / "scenarios" / "death_certificate_v1.md"


def payload() -> dict[str, object]:
    return json.loads(PACK.read_text(encoding="utf-8"))


def scenario(data: dict[str, object]) -> dict[str, object]:
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list) and isinstance(scenarios[0], dict)
    return scenarios[0]


def load_changed(tmp_path: Path, data: dict[str, object]):
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return JsonScenarioCatalogLoader(path).load()


def test_death_certificate_pack_loads_as_strict_versioned_scenario() -> None:
    catalog = JsonScenarioCatalogLoader(PACK).load()
    definition = catalog.scenario("death_certificate")
    assert definition is not None
    assert definition.content_version == "death-certificate-1.1.0"
    assert tuple(item.phase_id for item in definition.phases) == (
        "death_certificate.arrival_locked",
        "death_certificate.life_disputed",
        "death_certificate.disposal_escape",
        "death_certificate.investigation",
        "death_certificate.self_fulfilling_truth",
        "death_certificate.core_conflict",
        "death_certificate.resolution",
    )
    assert {item.clock_id for item in definition.threat_clocks} == {
        "disposal_protocol",
        "predicted_death_deadline",
        "security_alert",
        "underground_patient_stability",
    }
    assert len(definition.facts) == 15
    assert len(definition.clue_groups) == 4
    clues = {item.clue_id: item for item in definition.clues}
    for group in definition.clue_groups:
        assert len(group.clue_ids) == 3
        assert group.required_count == 2
        assert sum(
            not clues[clue_id].required_any_profession_tags
            for clue_id in group.clue_ids
        ) >= 2
    npc_fact_ids = {
        fact_id
        for reference in definition.npc_references
        for fact_id in reference.known_fact_ids
    }
    assert "death_certificate.fact.prediction_causes_outcome" not in npc_fact_ids
    assert len(definition.memory_rules) == 19
    assert tuple(rule.rule_id for rule in definition.memory_rules) == tuple(
        sorted(rule.rule_id for rule in definition.memory_rules)
    )
    assert all(
        effect.fixed_public_narrative_text is not None
        for rule in definition.narrative_outcome_rules
        for effect in rule.effects
    )


def test_decision_server_effect_must_use_a_declared_transition_event(
    tmp_path: Path,
) -> None:
    data = payload()
    windows = scenario(data)["decision_windows"]
    assert isinstance(windows, list)
    final_window = next(
        item
        for item in windows
        if item["decision_id"] == "death_certificate.decision.core_four"
    )
    final_window["suggested_actions"][0]["server_event_type"] = (
        "untrusted.arbitrary.event"
    )

    with pytest.raises(ScenarioPackLoadError):
        load_changed(tmp_path, data)


@pytest.mark.parametrize("mutation", ["unknown_location", "invisible_destination"])
def test_narrative_location_effects_are_catalog_bounded(
    tmp_path: Path, mutation: str
) -> None:
    data = payload()
    rules = scenario(data)["narrative_outcome_rules"]
    assert isinstance(rules, list)
    records = next(
        item
        for item in rules
        if item["rule_id"]
        == "death_certificate.outcome.investigation_records_route"
    )
    effect = records["effects"][0]
    if mutation == "unknown_location":
        effect["opened_location_ids"] = ["death_certificate.missing"]
    else:
        effect["new_location_id"] = "death_certificate.intake_room"

    with pytest.raises(ScenarioPackLoadError):
        load_changed(tmp_path, data)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_rule",
        "unknown_event_type",
        "extra_field",
        "unknown_fact",
        "unknown_npc",
        "non_target_npc",
        "unknown_ending",
        "unknown_outcome_rule",
        "incompatible_operation",
    ],
)
def test_memory_rules_reject_ambiguous_or_unreachable_authority(
    tmp_path: Path, mutation: str
) -> None:
    data = payload()
    rules = scenario(data)["memory_rules"]
    assert isinstance(rules, list) and isinstance(rules[0], dict)
    if mutation == "duplicate_rule":
        rules.append(deepcopy(rules[0]))
    elif mutation == "unknown_event_type":
        rules[0]["source_event_type"] = "player.free_text"
    elif mutation == "extra_field":
        rules[0]["script"] = "setattr(memory, 'ending', 'forged')"
    elif mutation == "unknown_fact":
        fact_rule = next(item for item in rules if "public_fact_id" in item)
        fact_rule["public_fact_id"] = "death_certificate.fact.missing"
    elif mutation == "unknown_npc":
        npc_rule = next(item for item in rules if "npc_definition_id" in item)
        npc_rule["npc_definition_id"] = "npc.death_certificate.missing"
    elif mutation == "non_target_npc":
        npc_rule = next(item for item in rules if "npc_definition_id" in item)
        npc_rule["npc_definition_id"] = (
            "npc.death_certificate.records_custodian"
        )
    elif mutation == "unknown_ending":
        completion = next(item for item in rules if "allowed_ending_ids" in item)
        completion["allowed_ending_ids"] = ["death_certificate.ending.missing"]
    elif mutation == "unknown_outcome_rule":
        outcome = next(
            item for item in rules if "required_narrative_outcome_rule_ids" in item
        )
        outcome["required_narrative_outcome_rule_ids"] = [
            "death_certificate.outcome.missing"
        ]
    else:
        rules[0]["operation"] = "RECORD_NPC_ENCOUNTER"
    with pytest.raises(ScenarioPackLoadError):
        load_changed(tmp_path, data)


def test_death_certificate_opening_facts_are_structured_and_clock_consistent() -> None:
    definition = JsonScenarioCatalogLoader(PACK).load().scenario("death_certificate")
    assert definition is not None
    facts = {item.fact_id: item for item in definition.facts}

    body_bag = facts["death_certificate.fact.opening_body_bag_state"]
    assert body_bag.kind.value == "FIXED"
    assert body_bag.visibility.value == "PLAYER_KNOWN"
    assert body_bag.value["container_type"] == "BODY_BAG"
    assert body_bag.value["player_position"] == "INSIDE"
    assert body_bag.value["zipper_motion"] == "CLOSING"

    time_conflict = facts["death_certificate.fact.opening_time_conflict"].value
    assert time_conflict["awareness_time"] == {
        "hour": 2,
        "minute": 18,
        "minutes_after_midnight": 138,
        "semantics": "HISTORICAL_OPENING_TIME",
    }
    assert time_conflict["recorded_death_time"] == {
        "hour": 2,
        "minute": 31,
        "minutes_after_midnight": 151,
        "semantics": "ISSUED_CERTIFICATE_DEATH_TIME",
    }
    assert time_conflict["difference_minutes"] == 13
    assert time_conflict["deadline_clock_id"] == "predicted_death_deadline"
    assert time_conflict["deadline_clock_start_value"] == 0
    assert time_conflict["deadline_clock_due_value"] == 13
    assert time_conflict["deadline_clock_unit"] == "ELAPSED_MINUTES_SINCE_AWARENESS"

    assert facts["death_certificate.fact.death_certificate_issued"].value is True
    disposition = facts[
        "death_certificate.fact.comfort_disposition_imminent"
    ].value
    assert disposition["planned_procedure_types"] == (
        "INJECTION",
        "COMFORT_DISPOSITION",
    )
    assert disposition["procedure_selection"] == "ANY_LISTED_PROCEDURE"
    assert disposition["status"] == "IMMINENT"

    objective = facts["death_certificate.fact.initial_survival_objective"].value
    assert objective["objective_type"] == "NPC_ACKNOWLEDGES_PLAYER_ALIVE"
    assert objective["acknowledgement_mode"] == "EXPLICIT"
    assert objective["minimum_acknowledging_npcs"] == 1
    assert objective["npc_scope"] == "RUNTIME_NPC"
    assert objective["deadline_relation"] == "BEFORE"
    assert objective["deadline_time"] == {
        "hour": 2,
        "minute": 31,
        "minutes_after_midnight": 151,
    }
    assert objective["deadline_clock_id"] == "predicted_death_deadline"
    assert objective["deadline_clock_value"] == 13

    record_predates_diagnosis = facts[
        "death_certificate.fact.record_predates_diagnosis"
    ]
    assert record_predates_diagnosis.value is True
    assert record_predates_diagnosis.visibility.value == "DISCOVERABLE"
    assert "diagnosis" not in json.dumps(time_conflict, sort_keys=True)

    deadline = next(
        item
        for item in definition.threat_clocks
        if item.clock_id == "predicted_death_deadline"
    )
    assert deadline.initial == 0
    assert deadline.maximum == 13
    assert [(item.threshold, item.event_type) for item in deadline.thresholds] == [
        (8, "deadline.critical"),
        (13, "deadline.reached"),
    ]
    underground_clock = next(
        item
        for item in definition.threat_clocks
        if item.clock_id == "underground_patient_stability"
    )
    assert underground_clock.player_visible is False
    deadline_ending = next(
        item
        for item in definition.endings
        if item.ending_id == "death_certificate.ending.deadline_reached"
    )
    assert deadline_ending.conditions[0].clock_id == "predicted_death_deadline"
    assert deadline_ending.conditions[0].value == 13


def test_death_certificate_fact_count_matches_design_document() -> None:
    definition = JsonScenarioCatalogLoader(PACK).load().scenario("death_certificate")
    assert definition is not None
    document = DESIGN_DOC.read_text(encoding="utf-8")
    assert len(definition.facts) == 15
    assert "内容包共声明 15 个事实" in document
    assert "10 个事实" not in document
    assert "十个事实" not in document


def test_duplicate_scenario_ids_are_rejected(tmp_path: Path) -> None:
    data = payload()
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list)
    scenarios.append(deepcopy(scenarios[0]))
    with pytest.raises(ScenarioPackLoadError, match="duplicate scenario"):
        load_changed(tmp_path, data)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_clue_fact", "missing ID"),
        ("missing_initial_phase", "initial phase does not exist"),
        ("missing_transition_phase", "missing phase"),
        ("unknown_rule", "rule_type"),
        ("extra_field", "Extra inputs are not permitted"),
        ("content_version", "content_version"),
        ("schema_version", "schema_version"),
        ("profession_tag", "missing ID"),
    ],
)
def test_invalid_references_rules_fields_and_versions_fail_explicitly(
    tmp_path: Path, mutation: str, message: str
) -> None:
    data = payload()
    definition = scenario(data)
    if mutation == "missing_clue_fact":
        definition["clues"][0]["supports_fact_ids"] = ["fact.missing"]
    elif mutation == "missing_initial_phase":
        definition["initial_phase_id"] = "phase.missing"
    elif mutation == "missing_transition_phase":
        definition["phases"][0]["transitions"][0]["target_phase_id"] = "phase.missing"
    elif mutation == "unknown_rule":
        definition["phases"][0]["transitions"][0]["conditions"] = [
            {"rule_type": "EXECUTE_SCRIPT", "source": "anything"}
        ]
    elif mutation == "extra_field":
        definition["unexpected"] = True
    elif mutation == "schema_version":
        definition["schema_version"] = 2
    elif mutation == "profession_tag":
        definition["available_profession_tags"].append("UNKNOWN_PROFESSION")
    else:
        definition["content_version"] = "unsupported-2"
    with pytest.raises(ScenarioPackLoadError, match=message):
        load_changed(tmp_path, data)


def test_unreachable_required_phase_is_rejected(tmp_path: Path) -> None:
    data = payload()
    definition = scenario(data)
    definition["phases"][4]["required"] = True
    definition["phases"][3]["transitions"][0]["target_phase_id"] = (
        "death_certificate.core_conflict"
    )
    with pytest.raises(ScenarioPackLoadError, match="required phase is unreachable"):
        load_changed(tmp_path, data)


def test_unbounded_automatic_cycle_is_rejected(tmp_path: Path) -> None:
    data = payload()
    definition = scenario(data)
    phases = definition["phases"]
    exit_transition = deepcopy(phases[2]["transitions"][0])
    phases[2]["transitions"][0]["target_phase_id"] = phases[2]["phase_id"]
    exit_transition["transition_id"] = "death_certificate.transition.escape_exit"
    phases[2]["transitions"].append(exit_transition)
    with pytest.raises(ScenarioPackLoadError, match="unbounded automatic transition cycle"):
        load_changed(tmp_path, data)


def test_illegal_clock_bounds_and_impossible_clue_group_are_rejected(tmp_path: Path) -> None:
    bad_clock = payload()
    scenario(bad_clock)["threat_clocks"][0]["initial"] = 99
    with pytest.raises(ScenarioPackLoadError, match="outside its bounds"):
        load_changed(tmp_path, bad_clock)

    bad_group = payload()
    scenario(bad_group)["clue_groups"][0]["required_count"] = 4
    with pytest.raises(ScenarioPackLoadError, match="threshold exceeds"):
        load_changed(tmp_path, bad_group)


def test_profession_tags_are_referenced_but_never_required_for_group_completion(
    tmp_path: Path,
) -> None:
    data = payload()
    definition = scenario(data)
    group = definition["clue_groups"][0]
    clue_ids = set(group["clue_ids"])
    for clue in definition["clues"]:
        if clue["clue_id"] in clue_ids:
            clue["required_any_profession_tags"] = ["CLINICAL_LITERACY"]
    with pytest.raises(ScenarioPackLoadError, match="requires a profession tag"):
        load_changed(tmp_path, data)


def test_expected_content_version_is_enforced() -> None:
    with pytest.raises(ScenarioPackLoadError, match="unsupported content_version"):
        JsonScenarioCatalogLoader(PACK, expected_content_version="later-version").load()


@pytest.mark.parametrize("bad_value", [True, 1.5, "1"])
def test_clock_amounts_require_strict_integers(
    tmp_path: Path, bad_value: object
) -> None:
    data = payload()
    scenario(data)["phases"][1]["auto_beat_clock_advances"][0][
        "amount"
    ] = bad_value
    with pytest.raises(ScenarioPackLoadError, match="integer"):
        load_changed(tmp_path, data)


def test_impossible_decision_window_is_rejected(tmp_path: Path) -> None:
    data = payload()
    definition = scenario(data)
    definition["decision_windows"][1]["earliest_beat"] = 0
    definition["decision_windows"][1]["latest_beat"] = 1
    with pytest.raises(ScenarioPackLoadError, match="can never open"):
        load_changed(tmp_path, data)


def test_scenario_counts_strings_and_nesting_are_bounded(tmp_path: Path) -> None:
    too_many = payload()
    definition = scenario(too_many)
    template = deepcopy(definition["facts"][0])
    definition["facts"] = []
    for index in range(257):
        fact = deepcopy(template)
        fact["fact_id"] = f"bounded.fact.{index}"
        definition["facts"].append(fact)
    for clue in definition["clues"]:
        clue["supports_fact_ids"] = ["bounded.fact.0"]
    for npc in definition["npc_references"]:
        npc["known_fact_ids"] = ["bounded.fact.0"]
    for phase in definition["phases"]:
        phase["must_render_fact_ids"] = []
    for ending in definition["endings"]:
        ending["conditions"] = [
            {"rule_type": "FACT_EQUALS", "fact_id": "bounded.fact.0", "value": True}
        ]
    with pytest.raises(ScenarioPackLoadError, match="fact count exceeds"):
        load_changed(tmp_path, too_many)

    oversized = payload()
    scenario(oversized)["summary"] = "x" * 4_001
    with pytest.raises(ScenarioPackLoadError, match="oversized string"):
        load_changed(tmp_path, oversized)

    nested = payload()
    value: object = "leaf"
    for _ in range(40):
        value = {"nested": value}
    scenario(nested)["facts"][0]["value"] = value
    with pytest.raises(ScenarioPackLoadError, match="nesting depth"):
        load_changed(tmp_path, nested)


def test_terminal_phase_cannot_open_decisions_or_advance_clocks(
    tmp_path: Path,
) -> None:
    data = payload()
    terminal = scenario(data)["phases"][-1]
    terminal["decision_window_ids"] = ["death_certificate.decision.core_one"]
    with pytest.raises(ScenarioPackLoadError, match="terminal phase"):
        load_changed(tmp_path, data)


def test_rapid_phase_rejects_repeatable_decision_windows(tmp_path: Path) -> None:
    data = payload()
    definition = scenario(data)
    definition["decision_windows"][5]["once"] = False
    with pytest.raises(ScenarioPackLoadError, match="rapid phase.*cannot repeat"):
        load_changed(tmp_path, data)


def test_fact_condition_uses_type_strict_json_equality(tmp_path: Path) -> None:
    data = payload()
    scenario(data)["endings"][0]["conditions"] = [
        {
            "rule_type": "FACT_EQUALS",
            "fact_id": "death_certificate.fact.player_conscious",
            "value": 1,
        }
    ]
    with pytest.raises(ScenarioPackLoadError, match="can never equal"):
        load_changed(tmp_path, data)


def test_loader_rejects_duplicate_object_keys_and_non_standard_numbers(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":1,"schema_version":1}', encoding="utf-8"
    )
    with pytest.raises(ScenarioPackLoadError, match="duplicate JSON object key"):
        JsonScenarioCatalogLoader(duplicate).load()

    non_standard = tmp_path / "nan.json"
    non_standard.write_text('{"schema_version":NaN}', encoding="utf-8")
    with pytest.raises(ScenarioPackLoadError, match="non-standard JSON number"):
        JsonScenarioCatalogLoader(non_standard).load()
