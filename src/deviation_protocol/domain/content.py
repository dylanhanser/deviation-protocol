from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Annotated, Literal, Protocol, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DefinitionId: TypeAlias = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
DisplayName: TypeAlias = Annotated[str, Field(strict=True, min_length=1, max_length=120)]
NonNegativeInt: TypeAlias = Annotated[int, Field(strict=True, ge=0)]
PositiveInt: TypeAlias = Annotated[int, Field(strict=True, ge=1)]
BasisPoints: TypeAlias = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]


class ContentDefinitionError(ValueError):
    """A content pack is internally inconsistent."""


class DefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NamedIntegerDefinition(DefinitionModel):
    key: DefinitionId
    value: NonNegativeInt


class AttributeRequirement(DefinitionModel):
    attribute_id: DefinitionId
    minimum: NonNegativeInt


class SkillRequirement(DefinitionModel):
    skill_definition_id: DefinitionId
    minimum_level: PositiveInt = 1


class ResourceCost(DefinitionModel):
    resource_id: DefinitionId
    amount: PositiveInt


class CharacterDefinition(DefinitionModel):
    definition_id: DefinitionId
    display_name: DisplayName
    base_attributes: tuple[NamedIntegerDefinition, ...] = ()
    resource_caps: tuple[NamedIntegerDefinition, ...] = ()
    equipment_slots: tuple[DefinitionId, ...] = ()
    tags: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_unique_keys(self) -> CharacterDefinition:
        _reject_duplicates(
            (item.key for item in self.base_attributes),
            f"character {self.definition_id!r} attribute",
        )
        _reject_duplicates(
            (item.key for item in self.resource_caps),
            f"character {self.definition_id!r} resource",
        )
        _reject_duplicates(self.equipment_slots, f"character {self.definition_id!r} slot")
        return self


class NpcDefinition(DefinitionModel):
    definition_id: DefinitionId
    character_definition_id: DefinitionId
    display_name: DisplayName
    persona_summary: Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    tags: tuple[DefinitionId, ...] = ()


class ItemDefinition(DefinitionModel):
    definition_id: DefinitionId
    display_name: DisplayName
    stack_limit: PositiveInt = 1
    max_durability: PositiveInt | None = None
    max_charges: PositiveInt | None = None
    tags: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_stackable_state(self) -> ItemDefinition:
        if self.stack_limit > 1 and (
            self.max_durability is not None or self.max_charges is not None
        ):
            raise ValueError("stackable items cannot have per-instance durability or charges")
        return self


class AttributeModifierEffectDefinition(DefinitionModel):
    definition_id: DefinitionId
    effect_type: Literal["ATTRIBUTE_MODIFIER"]
    attribute_id: DefinitionId
    flat_delta: Annotated[int, Field(strict=True)] = 0
    multiplier_bps: BasisPoints = 10_000


class ResourceModifierEffectDefinition(DefinitionModel):
    definition_id: DefinitionId
    effect_type: Literal["RESOURCE_MODIFIER"]
    resource_id: DefinitionId
    delta: Annotated[int, Field(strict=True)]


EffectDefinition: TypeAlias = Annotated[
    AttributeModifierEffectDefinition | ResourceModifierEffectDefinition,
    Field(discriminator="effect_type"),
]


class EquipmentDefinition(DefinitionModel):
    definition_id: DefinitionId
    item_definition_id: DefinitionId
    allowed_slots: tuple[DefinitionId, ...]
    attribute_requirements: tuple[AttributeRequirement, ...] = ()
    skill_requirements: tuple[SkillRequirement, ...] = ()
    effect_definition_ids: tuple[DefinitionId, ...] = ()
    max_enhancement_level: NonNegativeInt = 0

    @model_validator(mode="after")
    def validate_equipment_shape(self) -> EquipmentDefinition:
        if not self.allowed_slots:
            raise ValueError("equipment must allow at least one slot")
        _reject_duplicates(self.allowed_slots, f"equipment {self.definition_id!r} slot")
        _reject_duplicates(
            (item.attribute_id for item in self.attribute_requirements),
            f"equipment {self.definition_id!r} attribute requirement",
        )
        _reject_duplicates(
            (item.skill_definition_id for item in self.skill_requirements),
            f"equipment {self.definition_id!r} skill requirement",
        )
        _reject_duplicates(
            self.effect_definition_ids,
            f"equipment {self.definition_id!r} effect reference",
        )
        return self


class SkillDefinition(DefinitionModel):
    definition_id: DefinitionId
    display_name: DisplayName
    max_level: PositiveInt = 1
    prerequisites: tuple[SkillRequirement, ...] = ()
    resource_costs: tuple[ResourceCost, ...] = ()
    effect_definition_ids: tuple[DefinitionId, ...] = ()
    tags: tuple[DefinitionId, ...] = ()

    @model_validator(mode="after")
    def validate_skill_shape(self) -> SkillDefinition:
        _reject_duplicates(
            (item.skill_definition_id for item in self.prerequisites),
            f"skill {self.definition_id!r} prerequisite",
        )
        _reject_duplicates(
            (item.resource_id for item in self.resource_costs),
            f"skill {self.definition_id!r} resource cost",
        )
        _reject_duplicates(
            self.effect_definition_ids,
            f"skill {self.definition_id!r} effect reference",
        )
        if any(
            requirement.skill_definition_id == self.definition_id
            for requirement in self.prerequisites
        ):
            raise ValueError("a skill cannot require itself")
        return self


class ContentCatalog(BaseModel):
    """Versioned, validated static definitions; no file-system knowledge lives here."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(strict=True)]
    content_version: DefinitionId
    characters: tuple[CharacterDefinition, ...] = ()
    npcs: tuple[NpcDefinition, ...] = ()
    items: tuple[ItemDefinition, ...] = ()
    equipment: tuple[EquipmentDefinition, ...] = ()
    skills: tuple[SkillDefinition, ...] = ()
    effects: tuple[EffectDefinition, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def require_supported_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("unsupported content schema_version; expected 1")
        return value

    @model_validator(mode="after")
    def validate_catalog(self) -> ContentCatalog:
        all_definitions = (
            *self.characters,
            *self.npcs,
            *self.items,
            *self.equipment,
            *self.skills,
            *self.effects,
        )
        _reject_duplicates(
            (definition.definition_id for definition in all_definitions),
            "catalog definition_id",
        )

        characters = {item.definition_id: item for item in self.characters}
        items = {item.definition_id: item for item in self.items}
        skills = {item.definition_id: item for item in self.skills}
        effects = {item.definition_id: item for item in self.effects}

        for npc in self.npcs:
            _require_reference(
                npc.character_definition_id,
                characters,
                f"NPC {npc.definition_id!r} character",
            )

        equipment_items: set[str] = set()
        for equipment in self.equipment:
            item = _require_reference(
                equipment.item_definition_id,
                items,
                f"equipment {equipment.definition_id!r} item",
            )
            if item.stack_limit != 1:
                raise ContentDefinitionError(
                    f"equipment item {item.definition_id!r} must have stack_limit 1"
                )
            if equipment.item_definition_id in equipment_items:
                raise ContentDefinitionError(
                    f"item {equipment.item_definition_id!r} has multiple equipment definitions"
                )
            equipment_items.add(equipment.item_definition_id)
            for requirement in equipment.skill_requirements:
                referenced = _require_reference(
                    requirement.skill_definition_id,
                    skills,
                    f"equipment {equipment.definition_id!r} skill requirement",
                )
                if requirement.minimum_level > referenced.max_level:
                    raise ContentDefinitionError(
                        f"equipment {equipment.definition_id!r} requires impossible skill level"
                    )
            for effect_id in equipment.effect_definition_ids:
                _require_reference(
                    effect_id, effects, f"equipment {equipment.definition_id!r} effect"
                )

        for skill in self.skills:
            for requirement in skill.prerequisites:
                referenced = _require_reference(
                    requirement.skill_definition_id,
                    skills,
                    f"skill {skill.definition_id!r} prerequisite",
                )
                if requirement.minimum_level > referenced.max_level:
                    raise ContentDefinitionError(
                        f"skill {skill.definition_id!r} requires impossible skill level"
                    )
            for effect_id in skill.effect_definition_ids:
                _require_reference(effect_id, effects, f"skill {skill.definition_id!r} effect")
        _reject_skill_cycles(skills)
        return self

    def character(self, definition_id: str) -> CharacterDefinition | None:
        return next(
            (item for item in self.characters if item.definition_id == definition_id), None
        )

    def npc(self, definition_id: str) -> NpcDefinition | None:
        return next((item for item in self.npcs if item.definition_id == definition_id), None)

    def item(self, definition_id: str) -> ItemDefinition | None:
        return next((item for item in self.items if item.definition_id == definition_id), None)

    def equipment_for_item(self, item_definition_id: str) -> EquipmentDefinition | None:
        return next(
            (
                item
                for item in self.equipment
                if item.item_definition_id == item_definition_id
            ),
            None,
        )

    def skill(self, definition_id: str) -> SkillDefinition | None:
        return next((item for item in self.skills if item.definition_id == definition_id), None)


class ContentCatalogLoader(Protocol):
    def load(self) -> ContentCatalog: ...


def _reject_duplicates(values: Iterable[str], label: str) -> None:
    sequence = tuple(values)
    duplicates = sorted(value for value, count in Counter(sequence).items() if count > 1)
    if duplicates:
        raise ContentDefinitionError(f"duplicate {label}: {', '.join(duplicates)}")


Definition = TypeVar("Definition")


def _require_reference(
    definition_id: str, definitions: Mapping[str, Definition], label: str
) -> Definition:
    try:
        return definitions[definition_id]
    except KeyError as exc:
        raise ContentDefinitionError(
            f"{label} references missing definition_id {definition_id!r}"
        ) from exc


def _reject_skill_cycles(skills: dict[str, SkillDefinition]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(skill_id: str) -> None:
        if skill_id in visiting:
            raise ContentDefinitionError(f"skill prerequisite cycle includes {skill_id!r}")
        if skill_id in visited:
            return
        visiting.add(skill_id)
        for requirement in skills[skill_id].prerequisites:
            visit(requirement.skill_definition_id)
        visiting.remove(skill_id)
        visited.add(skill_id)

    for definition_id in skills:
        visit(definition_id)
