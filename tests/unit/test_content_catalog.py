from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.infrastructure.content_loader import (
    ContentPackLoadError,
    JsonContentCatalogLoader,
)


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"


def load_payload() -> dict[str, object]:
    return json.loads(CONTENT_PACK.read_text(encoding="utf-8"))


def write_and_load(tmp_path: Path, payload: dict[str, object]) -> ContentCatalog:
    path = tmp_path / "content.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return JsonContentCatalogLoader(path).load()


def test_valid_versioned_content_catalog_loads_from_utf8_json() -> None:
    catalog = JsonContentCatalogLoader(CONTENT_PACK).load()

    assert catalog.schema_version == 1
    assert catalog.content_version == "demo-1"
    assert catalog.item("item.medkit") is not None
    assert catalog.equipment_for_item("item.training_sword") is not None
    assert catalog.skill("skill.observation") is not None
    assert catalog.npc("npc.demo.guard") is not None
    assert {effect.effect_type for effect in catalog.effects} == {
        "ATTRIBUTE_MODIFIER",
        "RESOURCE_MODIFIER",
    }


def test_static_definitions_are_frozen() -> None:
    catalog = JsonContentCatalogLoader(CONTENT_PACK).load()

    with pytest.raises(ValidationError, match="Instance is frozen"):
        catalog.items[0].display_name = "被运行时篡改"  # type: ignore[misc]


def test_duplicate_definition_id_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    items = payload["items"]
    assert isinstance(items, list)
    duplicate = dict(items[0])
    duplicate["display_name"] = "重复定义"
    items.append(duplicate)
    assert len(items) == 4
    assert items[0]["definition_id"] == items[-1]["definition_id"]

    with pytest.raises(ContentPackLoadError, match="duplicate catalog definition_id"):
        write_and_load(tmp_path, payload)


def test_missing_definition_reference_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    equipment = payload["equipment"]
    assert isinstance(equipment, list)
    equipment[0]["effect_definition_ids"] = ["effect.missing"]

    with pytest.raises(ContentPackLoadError, match="missing definition_id 'effect.missing'"):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("value", [-1, 1.5, "10"])
def test_illegal_numeric_values_are_strictly_rejected(
    tmp_path: Path, value: object
) -> None:
    payload = load_payload()
    items = payload["items"]
    assert isinstance(items, list)
    items[0]["stack_limit"] = value

    with pytest.raises(ContentPackLoadError, match="stack_limit"):
        write_and_load(tmp_path, payload)


def test_unknown_effect_type_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    effects = payload["effects"]
    assert isinstance(effects, list)
    effects[0]["effect_type"] = "EXECUTE_SCRIPT"

    with pytest.raises(ContentPackLoadError, match="effect_type"):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("cycle", ["self", "indirect"])
def test_skill_prerequisite_cycles_are_rejected(
    tmp_path: Path, cycle: str
) -> None:
    payload = load_payload()
    skills = payload["skills"]
    assert isinstance(skills, list)
    if cycle == "self":
        skills[0]["prerequisites"] = [
            {"skill_definition_id": "skill.observation", "minimum_level": 1}
        ]
    else:
        skills[0]["prerequisites"] = [
            {"skill_definition_id": "skill.precision", "minimum_level": 1}
        ]

    with pytest.raises(ContentPackLoadError, match="require itself|prerequisite cycle"):
        write_and_load(tmp_path, payload)


def test_unreachable_skill_prerequisite_level_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    skills = payload["skills"]
    assert isinstance(skills, list)
    skills[1]["prerequisites"][0]["minimum_level"] = 3

    with pytest.raises(ContentPackLoadError, match="impossible skill level"):
        write_and_load(tmp_path, payload)


def test_equipment_missing_item_reference_is_rejected(tmp_path: Path) -> None:
    payload = load_payload()
    equipment = payload["equipment"]
    assert isinstance(equipment, list)
    equipment[0]["item_definition_id"] = "item.missing"

    with pytest.raises(ContentPackLoadError, match="missing definition_id 'item.missing'"):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("slots", [[], ["hand.main", "hand.main"]])
def test_illegal_equipment_slot_definitions_are_rejected(
    tmp_path: Path, slots: list[str]
) -> None:
    payload = load_payload()
    equipment = payload["equipment"]
    assert isinstance(equipment, list)
    equipment[0]["allowed_slots"] = slots

    with pytest.raises(ContentPackLoadError, match="slot|at least one"):
        write_and_load(tmp_path, payload)


def test_item_cannot_have_multiple_equipment_definitions(tmp_path: Path) -> None:
    payload = load_payload()
    equipment = payload["equipment"]
    assert isinstance(equipment, list)
    duplicate = dict(equipment[0])
    duplicate["definition_id"] = "equipment.training_sword.alternate"
    equipment.append(duplicate)

    with pytest.raises(ContentPackLoadError, match="multiple equipment definitions"):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("value", [-1, 1_000_001, 1.5])
def test_illegal_basis_points_are_rejected(tmp_path: Path, value: object) -> None:
    payload = load_payload()
    effects = payload["effects"]
    assert isinstance(effects, list)
    effects[0]["multiplier_bps"] = value

    with pytest.raises(ContentPackLoadError, match="multiplier_bps"):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("field", ["max_durability", "max_charges"])
def test_non_positive_instance_maxima_are_rejected(
    tmp_path: Path, field: str
) -> None:
    payload = load_payload()
    items = payload["items"]
    assert isinstance(items, list)
    items[1][field] = 0

    with pytest.raises(ContentPackLoadError, match=field):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("target", ["resource_cap", "resource_cost"])
def test_illegal_resource_numbers_are_rejected(tmp_path: Path, target: str) -> None:
    payload = load_payload()
    if target == "resource_cap":
        characters = payload["characters"]
        assert isinstance(characters, list)
        characters[0]["resource_caps"][0]["value"] = -1
        message = "value"
    else:
        skills = payload["skills"]
        assert isinstance(skills, list)
        skills[0]["resource_costs"][0]["amount"] = 0
        message = "amount"

    with pytest.raises(ContentPackLoadError, match=message):
        write_and_load(tmp_path, payload)


@pytest.mark.parametrize("target", ["top", "nested"])
def test_extra_json_fields_are_rejected(tmp_path: Path, target: str) -> None:
    payload = load_payload()
    if target == "top":
        payload["unexpected"] = True
    else:
        items = payload["items"]
        assert isinstance(items, list)
        items[0]["unexpected"] = True

    with pytest.raises(ContentPackLoadError, match="Extra inputs are not permitted"):
        write_and_load(tmp_path, payload)


def test_malformed_json_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(ContentPackLoadError, match="invalid content pack"):
        JsonContentCatalogLoader(path).load()


@pytest.mark.parametrize("schema_version", [2, True, 1.0])
def test_unsupported_or_non_integer_content_schema_is_rejected(
    tmp_path: Path, schema_version: object
) -> None:
    payload = load_payload()
    payload["schema_version"] = schema_version

    with pytest.raises(ContentPackLoadError, match="schema_version"):
        write_and_load(tmp_path, payload)


def test_loader_can_enforce_expected_content_version(tmp_path: Path) -> None:
    path = tmp_path / "content.json"
    path.write_text(
        json.dumps(load_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ContentPackLoadError, match="unsupported content_version"):
        JsonContentCatalogLoader(
            path, expected_content_version="demo-2"
        ).load()
