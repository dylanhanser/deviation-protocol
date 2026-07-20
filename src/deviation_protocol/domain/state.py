from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Annotated, Any, Mapping, cast
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)

from deviation_protocol.domain.content import (
    CharacterDefinition,
    ContentCatalog,
    DefinitionId,
    NpcDefinition,
    SkillRequirement,
)
from deviation_protocol.domain.scenario import ScenarioCatalog, ScenarioDefinition
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from deviation_protocol.domain.player_memory import (
    MemoryMutationPlan,
    MemoryIndexSyncStatus,
    NpcInteractionMilestone,
    PlayerMemoryState,
    ScenarioMemoryMilestone,
    ScenarioMemoryStatus,
    SignificantExperienceCategory,
    migrate_player_memory_payload,
    memory_state_fingerprint,
    scenario_definition_fingerprint,
    stable_npc_subject_key,
)


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
RelationshipBasisPoints = Annotated[int, Field(strict=True, ge=-10_000, le=10_000)]
MAX_ATTRIBUTE_VALUE = 2**63 - 1
AttributeValue = Annotated[int, Field(strict=True, ge=0, le=MAX_ATTRIBUTE_VALUE)]


class DomainErrorCode(StrEnum):
    INVALID_IDENTIFIER = "invalid_identifier"
    INVALID_AMOUNT = "invalid_amount"
    INVALID_ATTRIBUTE_MODIFIER = "invalid_attribute_modifier"
    UNKNOWN_ATTRIBUTE = "unknown_attribute"
    RUNTIME_ID_COLLISION = "runtime_id_collision"
    UNKNOWN_ITEM_DEFINITION = "unknown_item_definition"
    UNKNOWN_ITEM_INSTANCE = "unknown_item_instance"
    DUPLICATE_ITEM_INSTANCE = "duplicate_item_instance"
    STACK_LIMIT_EXCEEDED = "stack_limit_exceeded"
    ITEM_EQUIPPED = "item_equipped"
    ITEM_NOT_CONSUMABLE = "item_not_consumable"
    INSUFFICIENT_ITEM_CHARGES = "insufficient_item_charges"
    NOT_EQUIPMENT = "not_equipment"
    NOT_EQUIPPED = "not_equipped"
    SLOT_NOT_ALLOWED = "slot_not_allowed"
    SLOT_OCCUPIED = "slot_occupied"
    EQUIPMENT_REQUIREMENT_NOT_MET = "equipment_requirement_not_met"
    BROKEN_EQUIPMENT = "broken_equipment"
    ITEM_NOT_DURABLE = "item_not_durable"
    DURABILITY_OUT_OF_RANGE = "durability_out_of_range"
    UNKNOWN_SKILL_DEFINITION = "unknown_skill_definition"
    SKILL_ALREADY_LEARNED = "skill_already_learned"
    SKILL_NOT_LEARNED = "skill_not_learned"
    SKILL_PREREQUISITE_NOT_MET = "skill_prerequisite_not_met"
    SKILL_MAX_LEVEL = "skill_max_level"
    SKILL_ON_COOLDOWN = "skill_on_cooldown"
    UNKNOWN_NPC_DEFINITION = "unknown_npc_definition"
    DUPLICATE_NPC = "duplicate_npc"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    UNKNOWN_RESOURCE = "unknown_resource"
    INSUFFICIENT_RESOURCE = "insufficient_resource"
    SNAPSHOT_CONTENT_MISMATCH = "snapshot_content_mismatch"
    INVALID_SNAPSHOT_REFERENCE = "invalid_snapshot_reference"


class DomainRuleViolation(ValueError):
    def __init__(self, code: DomainErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code.value}: {detail}")


class RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EquipmentState(RuntimeModel):
    enhancement_level: NonNegativeInt = 0
    equipped_slot: DefinitionId | None = None


class ItemInstance(RuntimeModel):
    instance_id: DefinitionId
    definition_id: DefinitionId
    quantity: PositiveInt = 1
    durability: NonNegativeInt | None = None
    charges: NonNegativeInt | None = None
    equipment: EquipmentState | None = None


class InventoryState(RuntimeModel):
    items: dict[DefinitionId, ItemInstance] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_inventory(self) -> InventoryState:
        for instance_id, item in self.items.items():
            if instance_id != item.instance_id:
                raise ValueError("inventory key must match item instance_id")
        equipped_slots = [
            item.equipment.equipped_slot
            for item in self.items.values()
            if item.equipment is not None and item.equipment.equipped_slot is not None
        ]
        if len(equipped_slots) != len(set(equipped_slots)):
            raise ValueError("only one item may occupy an equipment slot")
        return self


class WalletState(RuntimeModel):
    balances: dict[DefinitionId, NonNegativeInt] = Field(default_factory=dict)

    def credit(self, currency_id: str, amount: int) -> None:
        _require_definition_id(currency_id, "currency_id")
        _require_positive_amount(amount)
        self.balances[currency_id] = self.balances.get(currency_id, 0) + amount

    def debit(self, currency_id: str, amount: int) -> None:
        _require_definition_id(currency_id, "currency_id")
        _require_positive_amount(amount)
        current = self.balances.get(currency_id, 0)
        if current < amount:
            raise DomainRuleViolation(
                DomainErrorCode.INSUFFICIENT_FUNDS,
                f"currency {currency_id!r} balance {current} is less than {amount}",
            )
        self.balances[currency_id] = current - amount

    def has(self, currency_id: str, amount: int) -> bool:
        return _is_non_negative_int(amount) and self.balances.get(currency_id, 0) >= amount


class ResourceState(RuntimeModel):
    current: NonNegativeInt
    maximum: NonNegativeInt

    @model_validator(mode="after")
    def current_does_not_exceed_maximum(self) -> ResourceState:
        if self.current > self.maximum:
            raise ValueError("resource current cannot exceed maximum")
        return self


class SkillState(RuntimeModel):
    level: PositiveInt = 1
    proficiency: NonNegativeInt = 0
    cooldown_remaining: NonNegativeInt = 0
    uses: NonNegativeInt = 0


class PlayerState(RuntimeModel):
    player_id: DefinitionId
    character_definition_id: DefinitionId
    attributes: dict[DefinitionId, AttributeValue] = Field(default_factory=dict)
    resources: dict[DefinitionId, ResourceState] = Field(default_factory=dict)
    inventory: InventoryState = Field(default_factory=InventoryState)
    wallet: WalletState = Field(default_factory=WalletState)
    skills: dict[DefinitionId, SkillState] = Field(default_factory=dict)

    @classmethod
    def from_definition(
        cls, player_id: str, definition: CharacterDefinition
    ) -> PlayerState:
        return cls(
            player_id=player_id,
            character_definition_id=definition.definition_id,
            attributes={item.key: item.value for item in definition.base_attributes},
            resources={
                item.key: ResourceState(current=item.value, maximum=item.value)
                for item in definition.resource_caps
            },
        )


class NpcState(RuntimeModel):
    npc_id: DefinitionId
    definition_id: DefinitionId
    resources: dict[DefinitionId, ResourceState] = Field(default_factory=dict)
    relationship_bps: RelationshipBasisPoints = 0
    runtime_flags: frozenset[DefinitionId] = frozenset()

    @field_serializer("runtime_flags")
    def serialize_runtime_flags(
        self, runtime_flags: frozenset[str]
    ) -> list[str]:
        return sorted(runtime_flags)

    @classmethod
    def from_definition(
        cls,
        npc_id: str,
        definition: NpcDefinition,
        character: CharacterDefinition,
    ) -> NpcState:
        return cls(
            npc_id=npc_id,
            definition_id=definition.definition_id,
            resources={
                item.key: ResourceState(current=item.value, maximum=item.value)
                for item in character.resource_caps
            },
        )


class GameState(RuntimeModel):
    """Authoritative snapshot aggregate for frequently changing gameplay state."""

    schema_version: Annotated[int, Field(strict=True)] = 3
    content_version: DefinitionId
    player: PlayerState
    npcs: dict[DefinitionId, NpcState] = Field(default_factory=dict)
    scenario_runtime: ScenarioRuntimeState | None = None
    player_memory: PlayerMemoryState = Field(default_factory=PlayerMemoryState)

    @field_validator("schema_version")
    @classmethod
    def require_supported_schema_version(cls, value: int) -> int:
        if value != 3:
            raise ValueError("unsupported snapshot schema_version; expected 3")
        return value

    @model_validator(mode="after")
    def validate_npc_keys(self) -> GameState:
        for npc_id, npc in self.npcs.items():
            if npc_id != npc.npc_id:
                raise ValueError("NPC state key must match npc_id")
            if npc_id == self.player.player_id:
                raise ValueError("NPC runtime ID must not collide with player_id")
        return self

    def to_snapshot(self) -> dict[str, Any]:
        """Return a MySQL JSON-compatible shape with an explicit schema version."""
        payload = cast(dict[str, Any], _canonical_json(self.model_dump(mode="json")))
        # Nested dict mutation does not trigger Pydantic assignment validation on
        # its parent. Re-validating here prevents an invalid in-memory structure
        # from crossing the snapshot persistence boundary.
        type(self).model_validate(payload)
        return payload

    def detached_copy(self, catalog: ContentCatalog) -> GameState:
        """Deeply clone a validated aggregate without re-resolving scenario files.

        Transaction boundaries validate scenario runtime against ScenarioCatalog.
        Pure mechanical rules only need a detached copy and must not gain a file or
        scenario-catalog dependency merely to preserve the untouched runtime subtree.
        """
        self.validate_against(catalog)
        copied = type(self).model_validate(self.to_snapshot())
        copied.validate_against(catalog)
        return copied

    def memory_authority_fingerprint(self) -> str:
        """Bind a memory plan to every authoritative non-memory field."""
        payload = self.to_snapshot()
        del payload["player_memory"]
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def apply_memory_plan(
        self,
        plan: MemoryMutationPlan,
        *,
        session_id: str,
        state_version: int,
        scenario_definition: ScenarioDefinition,
    ) -> None:
        """Atomically apply one sealed, deterministic long-term-memory update."""
        if type(state_version) is not int or state_version < 0:
            raise ValueError("memory mutation state_version must be non-negative integer")
        before = self.to_snapshot()
        current_memory_fingerprint = memory_state_fingerprint(self.player_memory)
        if not isinstance(plan, MemoryMutationPlan) or not plan.is_authentic_for(
            session_id=session_id,
            state_version=state_version,
            non_memory_state_fingerprint=self.memory_authority_fingerprint(),
            scenario_definition_fingerprint=scenario_definition_fingerprint(
                scenario_definition
            ),
            memory_fingerprint=current_memory_fingerprint,
        ):
            raise ValueError("memory mutation is forged, stale, or bound elsewhere")
        candidate = self.player_memory._apply_issued_plan(plan)
        # model_copy intentionally does not validate updates. Rebuild from JSON so
        # collection order, duplicate checks and every nested bound are enforced
        # before the authoritative aggregate is touched.
        candidate = PlayerMemoryState.model_validate(candidate.model_dump(mode="json"))
        if memory_state_fingerprint(candidate) != plan.memory_after_fingerprint:
            raise ValueError("memory mutation result does not match its sealed post-state")
        validated_state = type(self).model_validate(
            {**before, "player_memory": candidate.model_dump(mode="json")}
        )
        self.player_memory = validated_state.player_memory

    @classmethod
    def from_snapshot(
        cls,
        payload: Mapping[str, Any],
        *,
        catalog: ContentCatalog | None = None,
        scenario_catalog: ScenarioCatalog | None = None,
    ) -> GameState:
        try:
            migrated = migrate_snapshot_payload(payload)
        except ValueError:
            # Preserve the established Pydantic validation contract at this public
            # boundary while keeping the migration helper itself strict.
            cls.model_validate(deepcopy(dict(payload)))
            raise  # pragma: no cover - model_validate above always rejects here
        state = cls.model_validate(migrated)
        if catalog is not None:
            state.validate_against(catalog)
        if scenario_catalog is not None:
            if state.content_version != scenario_catalog.content_version:
                raise ValueError(
                    "snapshot content version does not match scenario catalog"
                )
            if catalog is not None and catalog != scenario_catalog.content_catalog:
                raise ValueError("content and scenario catalogs do not match")
            if catalog is None:
                state.validate_against(scenario_catalog.content_catalog)
        if state.scenario_runtime is not None:
            if scenario_catalog is None:
                raise ValueError("scenario catalog is required for a scenario runtime snapshot")
            definition = scenario_catalog.scenario(state.scenario_runtime.scenario_id)
            if definition is None:
                raise ValueError("snapshot references an unknown scenario")
            state.scenario_runtime.validate_against(definition)
        if _memory_has_records(state.player_memory):
            if scenario_catalog is None:
                raise ValueError("scenario catalog is required for a player-memory snapshot")
            state.validate_player_memory_against(scenario_catalog)
        return state

    def validate_player_memory_against(
        self, scenario_catalog: ScenarioCatalog
    ) -> None:
        """Reject catalog-invalid or not-yet-known authoritative memory."""

        from deviation_protocol.domain.facts import FactVisibility
        from deviation_protocol.domain.memory_rules import (
            MemoryRuleOperation,
            MemoryRuleSourceEventType,
        )
        from deviation_protocol.domain.scenario import EndingStatus

        memory = self.player_memory
        if not _memory_has_records(memory):
            return
        runtime = self.scenario_runtime
        scenario_records = {
            item.scenario_id: item for item in memory.scenario_records
        }
        definitions: dict[str, ScenarioDefinition] = {}

        def definition_for(scenario_id: str) -> ScenarioDefinition:
            existing = definitions.get(scenario_id)
            if existing is not None:
                return existing
            definition = scenario_catalog.scenario(scenario_id)
            if definition is None:
                self._invalid_snapshot(
                    f"player memory references unknown scenario {scenario_id!r}"
                )
            record = scenario_records[scenario_id]
            if record.scenario_content_version != definition.content_version:
                self._invalid_snapshot(
                    f"player memory scenario {scenario_id!r} has a mismatched content version"
                )
            definitions[scenario_id] = definition
            return definition

        # Catalog membership and public visibility do not prove that the player
        # participated in a scenario.  This phase has only one authoritative
        # participation source: the matching runtime carried by this snapshot.
        for record in memory.scenario_records:
            definition_for(record.scenario_id)

        participating_runtimes: dict[str, ScenarioRuntimeState] = {}
        for record in memory.scenario_records:
            if (
                runtime is None
                or runtime.scenario_id != record.scenario_id
                or runtime.scenario_content_version
                != record.scenario_content_version
            ):
                self._invalid_snapshot(
                    f"player memory scenario {record.scenario_id!r} lacks "
                    "authoritative runtime participation"
                )
            participating_runtimes[record.scenario_id] = runtime

        def runtime_for(scenario_id: str) -> ScenarioRuntimeState | None:
            return participating_runtimes.get(scenario_id)

        def rule_occurrence_is_proven(
            rule: Any,
            scenario_runtime: ScenarioRuntimeState | None,
            *,
            npc_definition_id: str | None = None,
        ) -> bool:
            if scenario_runtime is None:
                return False
            if (
                rule.source_event_type
                is MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED
            ):
                return any(
                    (
                        not rule.required_narrative_outcome_rule_ids
                        or evidence.outcome_rule_id
                        in rule.required_narrative_outcome_rule_ids
                    )
                    and (
                        not rule.required_outcome_results
                        or evidence.outcome_result in rule.required_outcome_results
                    )
                    and (
                        not rule.required_scenario_event_types
                        or evidence.scenario_event_type
                        in rule.required_scenario_event_types
                    )
                    and (
                        npc_definition_id is None
                        or npc_definition_id in evidence.npc_definition_ids
                    )
                    for evidence in scenario_runtime.narrative_outcome_evidence
                )
            if rule.source_event_type is MemoryRuleSourceEventType.SCENARIO_STARTED:
                return True
            if (
                rule.source_event_type
                is MemoryRuleSourceEventType.SCENARIO_DECISION_SELECTED
            ):
                return bool(scenario_runtime.decisions_made)
            if (
                rule.source_event_type
                is MemoryRuleSourceEventType.SCENARIO_RUNTIME_EVENT_GENERATED
            ):
                # The target-specific runtime checks below prove the generated
                # result itself (discovered fact or ending), rather than treating
                # the mere declaration of a rule as occurrence evidence.
                return True
            return False

        def fact_is_player_known(
            scenario_id: str, fact_ref: str
        ) -> bool:
            definition = definition_for(scenario_id)
            fact = next(
                (item for item in definition.facts if item.fact_id == fact_ref),
                None,
            )
            if fact is None or fact.visibility is FactVisibility.HIDDEN:
                return False
            if fact.visibility is FactVisibility.PLAYER_KNOWN:
                # Participation was independently established for every scenario
                # record before any fact validation reached this branch.
                return True
            scenario_runtime = runtime_for(scenario_id)
            if scenario_runtime is None:
                return False
            discovered = any(
                fact_ref in definition.clue(clue_id).supports_fact_ids
                for clue_id in scenario_runtime.discovered_clue_ids
            )
            if not discovered:
                return False
            return any(
                rule.operation is MemoryRuleOperation.REMEMBER_PUBLIC_FACT
                and rule.public_fact_id == fact_ref
                and rule_occurrence_is_proven(rule, scenario_runtime)
                for rule in definition.memory_rules
            )

        for record in memory.scenario_records:
            definition = definition_for(record.scenario_id)
            rules = definition.memory_rules
            expected_milestones = {ScenarioMemoryMilestone.STARTED}
            if record.known_public_fact_refs:
                expected_milestones.add(
                    ScenarioMemoryMilestone.IMPORTANT_FACT_CONFIRMED
                )
            if record.status is ScenarioMemoryStatus.COMPLETED:
                expected_milestones.update(
                    {
                        ScenarioMemoryMilestone.COMPLETED,
                        ScenarioMemoryMilestone.ENDING_CONFIRMED,
                    }
                )
                ending_ids = {item.ending_id for item in definition.endings}
                scenario_runtime = runtime_for(record.scenario_id)
                if (
                    scenario_runtime is None
                    or scenario_runtime.ending_status is EndingStatus.ACTIVE
                    or scenario_runtime.ending_id != record.ending_id
                    or record.ending_id not in ending_ids
                    or not any(
                        rule.operation is MemoryRuleOperation.COMPLETE_SCENARIO
                        and record.ending_id in rule.allowed_ending_ids
                        and rule_occurrence_is_proven(rule, scenario_runtime)
                        for rule in rules
                    )
                ):
                    self._invalid_snapshot(
                        f"player memory scenario {record.scenario_id!r} has an unauthorized ending"
                    )
            if set(record.milestone_refs) != expected_milestones:
                self._invalid_snapshot(
                    f"player memory scenario {record.scenario_id!r} has inconsistent milestones"
                )
            for fact_ref in record.known_public_fact_refs:
                if not fact_is_player_known(record.scenario_id, fact_ref):
                    self._invalid_snapshot(
                        f"player memory contains unknown public fact {fact_ref!r}"
                    )
            scenario_runtime = runtime_for(record.scenario_id)
            if scenario_runtime is not None:
                if (
                    memory.sync_status is MemoryIndexSyncStatus.CURRENT
                    and scenario_runtime.ending_status is not EndingStatus.ACTIVE
                    and record.status is not ScenarioMemoryStatus.COMPLETED
                ):
                    self._invalid_snapshot(
                        "current player memory omits the authoritative ending"
                    )

        known_fact_pairs = {
            (item.scenario_id, item.fact_ref)
            for item in memory.known_public_facts
        }
        for fact in memory.known_public_facts:
            definition_for(fact.scenario_id)
            if not fact_is_player_known(fact.scenario_id, fact.fact_ref):
                self._invalid_snapshot(
                    f"player memory contains unknown public fact {fact.fact_ref!r}"
                )

        npc_records = {item.subject_key: item for item in memory.npc_records}
        for npc in memory.npc_records:
            definition = definition_for(npc.scenario_id)
            if npc.npc_definition_id not in {
                item.npc_definition_id for item in definition.npc_references
            }:
                self._invalid_snapshot(
                    f"player memory references unknown NPC {npc.npc_definition_id!r}"
                )
            encounter_rules = tuple(
                rule
                for rule in definition.memory_rules
                if rule.operation is MemoryRuleOperation.RECORD_NPC_ENCOUNTER
                and rule.npc_definition_id == npc.npc_definition_id
            )
            if not encounter_rules or (
                NpcInteractionMilestone.FIRST_ENCOUNTER
                not in npc.interaction_milestones
            ):
                self._invalid_snapshot(
                    f"player memory NPC {npc.npc_definition_id!r} lacks encounter authority"
                )
            for milestone in npc.interaction_milestones:
                if milestone is NpcInteractionMilestone.FIRST_ENCOUNTER:
                    continue
                if not any(
                    rule.operation is MemoryRuleOperation.UPDATE_NPC_MILESTONE
                    and rule.npc_definition_id == npc.npc_definition_id
                    and rule.npc_milestone is milestone
                    for rule in definition.memory_rules
                ):
                    self._invalid_snapshot(
                        f"player memory NPC milestone {milestone.value!r} is undeclared"
                    )
            for fact_ref in npc.known_public_fact_refs:
                if not fact_is_player_known(npc.scenario_id, fact_ref):
                    self._invalid_snapshot(
                        f"player memory NPC references unknown fact {fact_ref!r}"
                    )
            scenario_runtime = runtime_for(npc.scenario_id)
            runtime_subjects = tuple(
                candidate
                for candidate in self.npcs.values()
                if candidate.definition_id == npc.npc_definition_id
            )
            if (
                scenario_runtime is None
                or len(runtime_subjects) != 1
                or not any(
                    rule_occurrence_is_proven(
                        rule,
                        scenario_runtime,
                        npc_definition_id=npc.npc_definition_id,
                    )
                    for rule in encounter_rules
                )
            ):
                self._invalid_snapshot(
                    f"player memory NPC {npc.npc_definition_id!r} was not encountered"
                )
            for milestone in npc.interaction_milestones:
                if milestone is NpcInteractionMilestone.FIRST_ENCOUNTER:
                    continue
                milestone_rules = tuple(
                    rule
                    for rule in definition.memory_rules
                    if rule.operation is MemoryRuleOperation.UPDATE_NPC_MILESTONE
                    and rule.npc_definition_id == npc.npc_definition_id
                    and rule.npc_milestone is milestone
                )
                if not any(
                    rule_occurrence_is_proven(
                        rule,
                        scenario_runtime,
                        npc_definition_id=npc.npc_definition_id,
                    )
                    for rule in milestone_rules
                ):
                    self._invalid_snapshot(
                        f"player memory NPC milestone {milestone.value!r} lacks occurrence evidence"
                    )

        for experience in memory.significant_experiences:
            definition = definition_for(experience.scenario_id)
            scenario_record = scenario_records[experience.scenario_id]
            matching_rules = tuple(
                rule
                for rule in definition.memory_rules
                if rule.operation
                is MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE
                and rule.significant_experience_category is experience.category
                and rule.significant_experience_summary is experience.summary
            )
            if experience.category is SignificantExperienceCategory.SCENARIO_BEGIN:
                valid = (
                    not (experience.subject_refs or experience.public_fact_refs)
                    and any(
                        rule_occurrence_is_proven(
                            rule, runtime_for(experience.scenario_id)
                        )
                        for rule in matching_rules
                    )
                )
            elif (
                experience.category
                is SignificantExperienceCategory.SCENARIO_COMPLETION
            ):
                valid = (
                    scenario_record.status is ScenarioMemoryStatus.COMPLETED
                    and experience.subject_refs == (scenario_record.ending_id,)
                    and any(
                        rule.requires_scenario_completed
                        and rule_occurrence_is_proven(
                            rule, runtime_for(experience.scenario_id)
                        )
                        for rule in matching_rules
                    )
                )
            elif experience.category in {
                SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
                SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
            }:
                valid = any(
                    rule.npc_definition_id is not None
                    and experience.subject_refs
                    == (
                        stable_npc_subject_key(
                            experience.scenario_id, rule.npc_definition_id
                        ),
                    )
                    and experience.subject_refs[0] in npc_records
                    and rule_occurrence_is_proven(
                        rule,
                        runtime_for(experience.scenario_id),
                        npc_definition_id=rule.npc_definition_id,
                    )
                    for rule in matching_rules
                )
            else:
                valid = any(
                    rule.public_fact_id is not None
                    and experience.public_fact_refs == (rule.public_fact_id,)
                    and (experience.scenario_id, rule.public_fact_id)
                    in known_fact_pairs
                    and rule_occurrence_is_proven(
                        rule, runtime_for(experience.scenario_id)
                    )
                    for rule in matching_rules
                )
            if not valid:
                self._invalid_snapshot(
                    f"player memory experience {experience.entry_id!r} is undeclared or unknown"
                )

    def validate_against(self, catalog: ContentCatalog) -> None:
        if self.content_version != catalog.content_version:
            raise DomainRuleViolation(
                DomainErrorCode.SNAPSHOT_CONTENT_MISMATCH,
                f"snapshot content {self.content_version!r} does not match catalog "
                f"{catalog.content_version!r}",
            )
        player_character = catalog.character(self.player.character_definition_id)
        if player_character is None:
            self._invalid_snapshot(
                f"unknown player character {self.player.character_definition_id!r}"
            )

        occupied_slots: set[str] = set()
        for instance in self.player.inventory.items.values():
            if instance.instance_id in catalog.definition_ids:
                self._invalid_snapshot(
                    f"item runtime ID {instance.instance_id!r} collides with a static definition"
                )
            item_definition = catalog.item(instance.definition_id)
            if item_definition is None:
                self._invalid_snapshot(
                    f"item instance {instance.instance_id!r} has unknown definition"
                )
            if instance.quantity > item_definition.stack_limit:
                self._invalid_snapshot(
                    f"item instance {instance.instance_id!r} exceeds stack limit"
                )
            if item_definition.max_durability is None:
                if instance.durability is not None:
                    self._invalid_snapshot(
                        f"item instance {instance.instance_id!r} has unexpected durability"
                    )
            elif instance.durability is None or instance.durability > item_definition.max_durability:
                self._invalid_snapshot(
                    f"item instance {instance.instance_id!r} has invalid durability"
                )
            if item_definition.max_charges is None:
                if instance.charges is not None:
                    self._invalid_snapshot(
                        f"item instance {instance.instance_id!r} has unexpected charges"
                    )
            elif instance.charges is None or instance.charges > item_definition.max_charges:
                self._invalid_snapshot(
                    f"item instance {instance.instance_id!r} has invalid charges"
                )

            equipment_definition = catalog.equipment_for_item(instance.definition_id)
            if equipment_definition is None:
                if instance.equipment is not None:
                    self._invalid_snapshot(
                        f"non-equipment item {instance.instance_id!r} has equipment state"
                    )
                continue
            if instance.equipment is None:
                self._invalid_snapshot(
                    f"equipment item {instance.instance_id!r} lacks equipment state"
                )
            if instance.equipment.enhancement_level > equipment_definition.max_enhancement_level:
                self._invalid_snapshot(
                    f"equipment item {instance.instance_id!r} exceeds enhancement limit"
                )
            slot = instance.equipment.equipped_slot
            if slot is not None:
                if slot not in equipment_definition.allowed_slots:
                    self._invalid_snapshot(
                        f"equipment item {instance.instance_id!r} uses an invalid slot"
                    )
                if slot not in player_character.equipment_slots:
                    self._invalid_snapshot(
                        f"player character does not expose equipment slot {slot!r}"
                    )
                if slot in occupied_slots:
                    self._invalid_snapshot(f"equipment slot {slot!r} is occupied twice")
                occupied_slots.add(slot)

        for definition_id, skill_state in self.player.skills.items():
            skill_definition = catalog.skill(definition_id)
            if skill_definition is None:
                self._invalid_snapshot(f"unknown learned skill {definition_id!r}")
            if skill_state.level > skill_definition.max_level:
                self._invalid_snapshot(f"skill {definition_id!r} exceeds max level")

        for npc in self.npcs.values():
            if npc.npc_id in catalog.definition_ids:
                self._invalid_snapshot(
                    f"NPC runtime ID {npc.npc_id!r} collides with a static definition"
                )
            if catalog.npc(npc.definition_id) is None:
                self._invalid_snapshot(
                    f"NPC {npc.npc_id!r} has unknown definition {npc.definition_id!r}"
                )

    def grant_item(
        self,
        catalog: ContentCatalog,
        item_definition_id: str,
        quantity: int = 1,
        *,
        instance_id: str | None = None,
    ) -> tuple[str, ...]:
        _require_positive_amount(quantity)
        definition = catalog.item(item_definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
                f"unknown item definition {item_definition_id!r}",
            )
        inventory = self.player.inventory.items
        if instance_id is not None:
            _require_definition_id(instance_id, "instance_id")
            if instance_id in catalog.definition_ids:
                raise DomainRuleViolation(
                    DomainErrorCode.RUNTIME_ID_COLLISION,
                    f"item runtime ID {instance_id!r} collides with a static definition",
                )
            if instance_id in inventory:
                raise DomainRuleViolation(
                    DomainErrorCode.DUPLICATE_ITEM_INSTANCE,
                    f"item instance {instance_id!r} already exists",
                )
            if quantity > definition.stack_limit:
                raise DomainRuleViolation(
                    DomainErrorCode.STACK_LIMIT_EXCEEDED,
                    f"quantity {quantity} exceeds stack limit {definition.stack_limit}",
                )
            instance = self._new_item_instance(
                catalog, item_definition_id, quantity, instance_id
            )
            inventory[instance_id] = instance
            return (instance_id,)

        changes: list[tuple[ItemInstance, int]] = []
        created: list[ItemInstance] = []
        remaining = quantity
        if definition.stack_limit > 1:
            for existing in inventory.values():
                if existing.definition_id != item_definition_id:
                    continue
                available = definition.stack_limit - existing.quantity
                if available <= 0:
                    continue
                added = min(available, remaining)
                changes.append((existing, existing.quantity + added))
                remaining -= added
                if remaining == 0:
                    break

        reserved_ids = set(inventory) | set(catalog.definition_ids)
        while remaining > 0:
            stack_quantity = min(definition.stack_limit, remaining)
            new_instance_id = _unique_instance_id(reserved_ids)
            reserved_ids.add(new_instance_id)
            created.append(
                self._new_item_instance(
                    catalog, item_definition_id, stack_quantity, new_instance_id
                )
            )
            remaining -= stack_quantity

        for existing, new_quantity in changes:
            existing.quantity = new_quantity
        for instance in created:
            inventory[instance.instance_id] = instance
        return tuple(
            [existing.instance_id for existing, _ in changes]
            + [instance.instance_id for instance in created]
        )

    def remove_item(self, instance_id: str, quantity: int = 1) -> None:
        _require_positive_amount(quantity)
        instance = self.player.inventory.items.get(instance_id)
        if instance is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_INSTANCE,
                f"unknown item instance {instance_id!r}",
            )
        if quantity > instance.quantity:
            raise DomainRuleViolation(
                DomainErrorCode.INVALID_AMOUNT,
                f"cannot remove {quantity} from quantity {instance.quantity}",
            )
        if (
            quantity == instance.quantity
            and instance.equipment is not None
            and instance.equipment.equipped_slot is not None
        ):
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_EQUIPPED,
                f"item instance {instance_id!r} must be unequipped before removal",
            )
        if quantity == instance.quantity:
            del self.player.inventory.items[instance_id]
        else:
            instance.quantity -= quantity

    def consume_item(
        self, catalog: ContentCatalog, instance_id: str
    ) -> tuple[str, int, int | None]:
        """Consume one locally usable unit or charge after validating all guards."""
        instance = self._require_item_instance(instance_id)
        definition = catalog.item(instance.definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
                f"unknown item definition {instance.definition_id!r}",
            )
        if "consumable" not in definition.tags:
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_NOT_CONSUMABLE,
                f"item instance {instance_id!r} is not a consumable",
            )
        if instance.equipment is not None and instance.equipment.equipped_slot is not None:
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_EQUIPPED,
                f"item instance {instance_id!r} must be unequipped before consumption",
            )
        if instance.charges is not None and instance.charges == 0:
            raise DomainRuleViolation(
                DomainErrorCode.INSUFFICIENT_ITEM_CHARGES,
                f"item instance {instance_id!r} has no remaining charges",
            )

        if instance.charges is not None:
            next_charges = instance.charges - 1
            if next_charges == 0:
                del self.player.inventory.items[instance_id]
                return definition.definition_id, 0, 0
            instance.charges = next_charges
            return definition.definition_id, instance.quantity, next_charges

        next_quantity = instance.quantity - 1
        self.remove_item(instance_id, 1)
        return definition.definition_id, next_quantity, None

    def equip(self, catalog: ContentCatalog, instance_id: str, slot: str) -> None:
        instance = self._require_item_instance(instance_id)
        equipment_definition = catalog.equipment_for_item(instance.definition_id)
        if equipment_definition is None or instance.equipment is None:
            raise DomainRuleViolation(
                DomainErrorCode.NOT_EQUIPMENT,
                f"item instance {instance_id!r} is not equipment",
            )
        character_definition = catalog.character(self.player.character_definition_id)
        if character_definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.INVALID_SNAPSHOT_REFERENCE,
                f"unknown player character {self.player.character_definition_id!r}",
            )
        if (
            slot not in equipment_definition.allowed_slots
            or slot not in character_definition.equipment_slots
        ):
            raise DomainRuleViolation(
                DomainErrorCode.SLOT_NOT_ALLOWED,
                f"equipment {instance_id!r} or player character cannot use slot {slot!r}",
            )
        for other in self.player.inventory.items.values():
            if (
                other.instance_id != instance_id
                and other.equipment is not None
                and other.equipment.equipped_slot == slot
            ):
                raise DomainRuleViolation(
                    DomainErrorCode.SLOT_OCCUPIED,
                    f"slot {slot!r} is occupied by {other.instance_id!r}",
                )
        for requirement in equipment_definition.attribute_requirements:
            actual = self.player.attributes.get(requirement.attribute_id, 0)
            if actual < requirement.minimum:
                raise DomainRuleViolation(
                    DomainErrorCode.EQUIPMENT_REQUIREMENT_NOT_MET,
                    f"attribute {requirement.attribute_id!r} requires "
                    f"{requirement.minimum}, has {actual}",
                )
        for requirement in equipment_definition.skill_requirements:
            skill = self.player.skills.get(requirement.skill_definition_id)
            actual = skill.level if skill is not None else 0
            if actual < requirement.minimum_level:
                raise DomainRuleViolation(
                    DomainErrorCode.EQUIPMENT_REQUIREMENT_NOT_MET,
                    f"skill {requirement.skill_definition_id!r} requires level "
                    f"{requirement.minimum_level}, has {actual}",
                )
        if instance.durability == 0:
            raise DomainRuleViolation(
                DomainErrorCode.BROKEN_EQUIPMENT,
                f"equipment {instance_id!r} has zero durability",
            )
        instance.equipment.equipped_slot = slot

    def unequip(self, instance_id: str) -> None:
        instance = self._require_item_instance(instance_id)
        if instance.equipment is None:
            raise DomainRuleViolation(
                DomainErrorCode.NOT_EQUIPMENT,
                f"item instance {instance_id!r} is not equipment",
            )
        if instance.equipment.equipped_slot is None:
            raise DomainRuleViolation(
                DomainErrorCode.NOT_EQUIPPED,
                f"item instance {instance_id!r} is not equipped",
            )
        instance.equipment.equipped_slot = None

    def set_durability(
        self, catalog: ContentCatalog, instance_id: str, durability: int
    ) -> None:
        if not _is_non_negative_int(durability):
            raise DomainRuleViolation(
                DomainErrorCode.DURABILITY_OUT_OF_RANGE,
                "durability must be a non-negative integer",
            )
        instance = self._require_item_instance(instance_id)
        definition = catalog.item(instance.definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
                f"unknown item definition {instance.definition_id!r}",
            )
        if definition.max_durability is None:
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_NOT_DURABLE,
                f"item instance {instance_id!r} has no durability",
            )
        if durability > definition.max_durability:
            raise DomainRuleViolation(
                DomainErrorCode.DURABILITY_OUT_OF_RANGE,
                f"durability {durability} exceeds maximum {definition.max_durability}",
            )
        instance.durability = durability

    def damage_item(self, catalog: ContentCatalog, instance_id: str, amount: int) -> None:
        _require_positive_amount(amount)
        instance = self._require_item_instance(instance_id)
        if instance.durability is None:
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_NOT_DURABLE,
                f"item instance {instance_id!r} has no durability",
            )
        self.set_durability(catalog, instance_id, max(0, instance.durability - amount))

    def repair_item(self, catalog: ContentCatalog, instance_id: str, amount: int) -> None:
        _require_positive_amount(amount)
        instance = self._require_item_instance(instance_id)
        definition = catalog.item(instance.definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
                f"unknown item definition {instance.definition_id!r}",
            )
        if instance.durability is None or definition.max_durability is None:
            raise DomainRuleViolation(
                DomainErrorCode.ITEM_NOT_DURABLE,
                f"item instance {instance_id!r} has no durability",
            )
        self.set_durability(
            catalog,
            instance_id,
            min(definition.max_durability, instance.durability + amount),
        )

    def learn_skill(self, catalog: ContentCatalog, skill_definition_id: str) -> None:
        definition = catalog.skill(skill_definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_SKILL_DEFINITION,
                f"unknown skill definition {skill_definition_id!r}",
            )
        if skill_definition_id in self.player.skills:
            raise DomainRuleViolation(
                DomainErrorCode.SKILL_ALREADY_LEARNED,
                f"skill {skill_definition_id!r} is already learned",
            )
        self._check_skill_prerequisites(definition.prerequisites)
        self.player.skills[skill_definition_id] = SkillState()

    def spawn_npc(
        self, catalog: ContentCatalog, npc_definition_id: str, npc_id: str
    ) -> None:
        definition = catalog.npc(npc_definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_NPC_DEFINITION,
                f"unknown NPC definition {npc_definition_id!r}",
            )
        _require_definition_id(npc_id, "npc_id")
        if npc_id in catalog.definition_ids:
            raise DomainRuleViolation(
                DomainErrorCode.RUNTIME_ID_COLLISION,
                f"NPC runtime ID {npc_id!r} collides with a static definition",
            )
        if npc_id == self.player.player_id:
            raise DomainRuleViolation(
                DomainErrorCode.RUNTIME_ID_COLLISION,
                f"NPC runtime ID {npc_id!r} collides with player_id",
            )
        if npc_id in self.npcs:
            raise DomainRuleViolation(
                DomainErrorCode.DUPLICATE_NPC,
                f"NPC state {npc_id!r} already exists",
            )
        character = catalog.character(definition.character_definition_id)
        if character is None:  # catalog validation makes this unreachable
            raise DomainRuleViolation(
                DomainErrorCode.INVALID_SNAPSHOT_REFERENCE,
                f"NPC definition {npc_definition_id!r} has no character definition",
            )
        self.npcs[npc_id] = NpcState.from_definition(npc_id, definition, character)

    def upgrade_skill(self, catalog: ContentCatalog, skill_definition_id: str) -> None:
        definition = catalog.skill(skill_definition_id)
        if definition is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_SKILL_DEFINITION,
                f"unknown skill definition {skill_definition_id!r}",
            )
        state = self.player.skills.get(skill_definition_id)
        if state is None:
            raise DomainRuleViolation(
                DomainErrorCode.SKILL_NOT_LEARNED,
                f"skill {skill_definition_id!r} has not been learned",
            )
        if state.level >= definition.max_level:
            raise DomainRuleViolation(
                DomainErrorCode.SKILL_MAX_LEVEL,
                f"skill {skill_definition_id!r} is already at max level",
            )
        self._check_skill_prerequisites(definition.prerequisites)
        state.level += 1

    def record_skill_use(self, skill_definition_id: str) -> int:
        state = self.player.skills.get(skill_definition_id)
        if state is None:
            raise DomainRuleViolation(
                DomainErrorCode.SKILL_NOT_LEARNED,
                f"skill {skill_definition_id!r} has not been learned",
            )
        if state.cooldown_remaining > 0:
            raise DomainRuleViolation(
                DomainErrorCode.SKILL_ON_COOLDOWN,
                f"skill {skill_definition_id!r} has cooldown remaining",
            )
        state.uses += 1
        return state.uses

    def apply_attribute_modifier(
        self,
        attribute_id: str,
        *,
        flat_delta: int = 0,
        multiplier_bps: int = 10_000,
    ) -> tuple[int, int]:
        _require_definition_id(attribute_id, "attribute_id")
        if (
            isinstance(flat_delta, bool)
            or not isinstance(flat_delta, int)
            or isinstance(multiplier_bps, bool)
            or not isinstance(multiplier_bps, int)
            or not 0 <= multiplier_bps <= 1_000_000
        ):
            raise DomainRuleViolation(
                DomainErrorCode.INVALID_ATTRIBUTE_MODIFIER,
                "attribute modifier must use bounded integer values",
            )
        if attribute_id not in self.player.attributes:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ATTRIBUTE,
                f"unknown player attribute {attribute_id!r}",
            )
        before = self.player.attributes[attribute_id]
        after = (before * multiplier_bps) // 10_000 + flat_delta
        if not 0 <= after <= MAX_ATTRIBUTE_VALUE:
            raise DomainRuleViolation(
                DomainErrorCode.INVALID_ATTRIBUTE_MODIFIER,
                f"attribute {attribute_id!r} is outside the supported integer range",
            )
        self.player.attributes[attribute_id] = after
        return before, after

    def credit_currency(self, currency_id: str, amount: int) -> None:
        self.player.wallet.credit(currency_id, amount)

    def debit_currency(self, currency_id: str, amount: int) -> None:
        self.player.wallet.debit(currency_id, amount)

    def consume_resource(self, resource_id: str, amount: int) -> None:
        _require_positive_amount(amount)
        resource = self.player.resources.get(resource_id)
        if resource is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_RESOURCE,
                f"unknown player resource {resource_id!r}",
            )
        if resource.current < amount:
            raise DomainRuleViolation(
                DomainErrorCode.INSUFFICIENT_RESOURCE,
                f"resource {resource_id!r} has {resource.current}, needs {amount}",
            )
        resource.current -= amount

    def restore_resource(self, resource_id: str, amount: int) -> None:
        _require_positive_amount(amount)
        resource = self.player.resources.get(resource_id)
        if resource is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_RESOURCE,
                f"unknown player resource {resource_id!r}",
            )
        resource.current = min(resource.maximum, resource.current + amount)

    def _new_item_instance(
        self,
        catalog: ContentCatalog,
        item_definition_id: str,
        quantity: int,
        instance_id: str,
    ) -> ItemInstance:
        definition = catalog.item(item_definition_id)
        if definition is None:  # guarded by grant_item; retained as a safe invariant
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
                f"unknown item definition {item_definition_id!r}",
            )
        equipment = (
            EquipmentState()
            if catalog.equipment_for_item(item_definition_id) is not None
            else None
        )
        return ItemInstance(
            instance_id=instance_id,
            definition_id=item_definition_id,
            quantity=quantity,
            durability=definition.max_durability,
            charges=definition.max_charges,
            equipment=equipment,
        )

    def _require_item_instance(self, instance_id: str) -> ItemInstance:
        instance = self.player.inventory.items.get(instance_id)
        if instance is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_ITEM_INSTANCE,
                f"unknown item instance {instance_id!r}",
            )
        return instance

    def _check_skill_prerequisites(
        self, prerequisites: Iterable[SkillRequirement]
    ) -> None:
        for requirement in prerequisites:
            state = self.player.skills.get(requirement.skill_definition_id)
            actual = state.level if state is not None else 0
            if actual < requirement.minimum_level:
                raise DomainRuleViolation(
                    DomainErrorCode.SKILL_PREREQUISITE_NOT_MET,
                    f"skill {requirement.skill_definition_id!r} requires level "
                    f"{requirement.minimum_level}, has {actual}",
                )

    @staticmethod
    def _invalid_snapshot(detail: str) -> None:
        raise DomainRuleViolation(DomainErrorCode.INVALID_SNAPSHOT_REFERENCE, detail)


@dataclass(frozen=True, slots=True, init=False)
class AuthoritativeStateView:
    """Detached, immutable capability projection for application adapters."""

    _item_instance_ids: frozenset[str]
    _item_definitions: tuple[tuple[str, str], ...]
    _item_quantities: tuple[tuple[str, int], ...]
    _equipment_instance_ids: frozenset[str]
    _equipment_definitions: tuple[tuple[str, str], ...]
    _equipped_instance_ids: frozenset[str]
    _skills: tuple[tuple[str, int], ...]
    _npc_ids: frozenset[str]
    _npc_definitions: tuple[tuple[str, str], ...]
    _resources: tuple[tuple[str, int], ...]
    _currencies: tuple[tuple[str, int], ...]

    def __init__(self, state: GameState, catalog: ContentCatalog) -> None:
        state = state.detached_copy(catalog)
        quantities: dict[str, int] = {}
        item_definitions: list[tuple[str, str]] = []
        equipment_instance_ids: set[str] = set()
        equipment_definitions: list[tuple[str, str]] = []
        equipped_instance_ids: set[str] = set()
        for instance in state.player.inventory.items.values():
            item_definitions.append((instance.instance_id, instance.definition_id))
            quantities[instance.definition_id] = (
                quantities.get(instance.definition_id, 0) + instance.quantity
            )
            equipment_definition = catalog.equipment_for_item(instance.definition_id)
            if equipment_definition is not None:
                equipment_instance_ids.add(instance.instance_id)
                equipment_definitions.append(
                    (instance.instance_id, equipment_definition.definition_id)
                )
            if (
                instance.equipment is not None
                and instance.equipment.equipped_slot is not None
            ):
                equipped_instance_ids.add(instance.instance_id)

        object.__setattr__(
            self,
            "_item_instance_ids",
            frozenset(state.player.inventory.items),
        )
        object.__setattr__(self, "_item_definitions", tuple(sorted(item_definitions)))
        object.__setattr__(self, "_item_quantities", tuple(sorted(quantities.items())))
        object.__setattr__(
            self, "_equipment_instance_ids", frozenset(equipment_instance_ids)
        )
        object.__setattr__(
            self, "_equipment_definitions", tuple(sorted(equipment_definitions))
        )
        object.__setattr__(
            self, "_equipped_instance_ids", frozenset(equipped_instance_ids)
        )
        object.__setattr__(
            self,
            "_skills",
            tuple(sorted((key, value.level) for key, value in state.player.skills.items())),
        )
        object.__setattr__(self, "_npc_ids", frozenset(state.npcs))
        object.__setattr__(
            self,
            "_npc_definitions",
            tuple(sorted((key, value.definition_id) for key, value in state.npcs.items())),
        )
        object.__setattr__(
            self,
            "_resources",
            tuple(
                sorted((key, value.current) for key, value in state.player.resources.items())
            ),
        )
        object.__setattr__(
            self,
            "_currencies",
            tuple(sorted(state.player.wallet.balances.items())),
        )

    def has_item_instance(self, instance_id: str) -> bool:
        return instance_id in self._item_instance_ids

    def owns_item_definition(self, definition_id: str, quantity: int = 1) -> bool:
        if not _is_positive_int(quantity):
            return False
        owned = next(
            (amount for item_id, amount in self._item_quantities if item_id == definition_id),
            0,
        )
        return owned >= quantity

    def owns_equipment(self, instance_id: str) -> bool:
        return instance_id in self._equipment_instance_ids

    def is_equipped(self, instance_id: str) -> bool:
        return instance_id in self._equipped_instance_ids

    def has_skill(self, skill_definition_id: str, minimum_level: int = 1) -> bool:
        if not _is_positive_int(minimum_level):
            return False
        level = next(
            (value for key, value in self._skills if key == skill_definition_id),
            0,
        )
        return level >= minimum_level

    def npc_exists(self, npc_id: str) -> bool:
        return npc_id in self._npc_ids

    def has_resource(self, resource_id: str, amount: int) -> bool:
        current = next(
            (value for key, value in self._resources if key == resource_id),
            None,
        )
        return _is_non_negative_int(amount) and current is not None and current >= amount

    def has_currency(self, currency_id: str, amount: int) -> bool:
        balance = next(
            (value for key, value in self._currencies if key == currency_id),
            None,
        )
        return _is_non_negative_int(amount) and balance is not None and balance >= amount

    @property
    def inventory_item_instance_ids(self) -> frozenset[str]:
        return self._item_instance_ids

    @property
    def item_definition_by_instance(self) -> tuple[tuple[str, str], ...]:
        return self._item_definitions

    @property
    def equipment_definition_by_instance(self) -> tuple[tuple[str, str], ...]:
        return self._equipment_definitions

    @property
    def learned_skill_levels(self) -> tuple[tuple[str, int], ...]:
        return self._skills

    @property
    def npc_definition_by_id(self) -> tuple[tuple[str, str], ...]:
        return self._npc_definitions

    @property
    def resource_ids(self) -> frozenset[str]:
        return frozenset(key for key, _ in self._resources)

    @property
    def currency_ids(self) -> frozenset[str]:
        return frozenset(key for key, _ in self._currencies)

    @property
    def npc_ids(self) -> frozenset[str]:
        return self._npc_ids


def _require_positive_amount(amount: int) -> None:
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise DomainRuleViolation(
            DomainErrorCode.INVALID_AMOUNT, "amount must be a positive integer"
        )


_DEFINITION_ID_ADAPTER = TypeAdapter(DefinitionId)


def _require_definition_id(value: object, label: str) -> None:
    try:
        _DEFINITION_ID_ADAPTER.validate_python(value)
    except ValidationError as exc:
        raise DomainRuleViolation(
            DomainErrorCode.INVALID_IDENTIFIER,
            f"{label} must be a stable definition-style identifier",
        ) from exc


def _is_non_negative_int(value: int) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _is_positive_int(value: int) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def migrate_snapshot_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Purely upgrade supported historical snapshot shapes to the current schema."""
    copied = deepcopy(dict(payload))
    version = copied.get("schema_version")
    if type(version) is not int:
        raise ValueError("snapshot schema_version must be a strict integer")
    if version == 1:
        if "scenario_runtime" in copied:
            raise ValueError("v1 snapshot cannot contain scenario_runtime")
        copied["schema_version"] = 2
        copied["scenario_runtime"] = None
        version = 2
    if version == 2:
        if "player_memory" in copied:
            raise ValueError("v2 snapshot cannot contain player_memory")
        copied["schema_version"] = 3
        copied["player_memory"] = PlayerMemoryState().model_dump(mode="json")
        _require_json_snapshot_value(copied)
        return copied
    if version == 3:
        memory = copied.get("player_memory")
        if not isinstance(memory, dict):
            raise ValueError("v3 snapshot requires a player_memory object")
        if memory.get("memory_model_version") == 1:
            copied["player_memory"] = migrate_player_memory_payload(memory)
        _require_json_snapshot_value(copied)
        return copied
    raise ValueError(f"unsupported snapshot schema_version: {version}")


def _require_json_snapshot_value(value: Any, *, path: str = "snapshot") -> None:
    """Reject Python-only or lossy values before validating a v3 JSON snapshot."""
    if value is None or type(value) in (bool, int, str):
        return
    if isinstance(value, float):
        raise TypeError(f"{path} contains a float")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string object key")
            _require_json_snapshot_value(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _require_json_snapshot_value(nested, path=f"{path}[{index}]")
        return
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _canonical_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonical_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical_json(item) for item in value]
    return value


def _unique_instance_id(reserved_ids: set[str]) -> str:
    while True:
        candidate = f"item-{uuid4().hex}"
        if candidate not in reserved_ids:
            return candidate


def _memory_has_records(memory: PlayerMemoryState) -> bool:
    return bool(
        memory.scenario_records
        or memory.npc_records
        or memory.significant_experiences
        or memory.known_public_facts
    )
