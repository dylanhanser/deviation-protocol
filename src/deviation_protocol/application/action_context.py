from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re

from deviation_protocol.domain.actions import ActionContext, ActionSubmission
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.state import AuthoritativeStateView, GameState


_TRUSTED_CONTEXT_ISSUER = object()
_SKILL_AUTHORIZATION_ISSUER = object()
_STABLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class SkillLearningAuthorizationSource(StrEnum):
    PERSISTED_FACT = "PERSISTED_FACT"
    REWARD_SETTLEMENT = "REWARD_SETTLEMENT"
    SYSTEM_RULE = "SYSTEM_RULE"


@dataclass(frozen=True, slots=True, init=False)
class SkillLearningAuthorization:
    """Opaque application capability that cannot be reconstructed from request data."""

    skill_definition_ids: frozenset[str]
    source: SkillLearningAuthorizationSource
    source_id: str
    _issuer: object

    def is_authentic(self) -> bool:
        return getattr(self, "_issuer", None) is _SKILL_AUTHORIZATION_ISSUER


@dataclass(frozen=True, slots=True, init=False)
class TrustedResolutionContext:
    """Sealed action context bound to one detached state and catalog projection."""

    action_context: ActionContext
    _skill_learning_authorization: SkillLearningAuthorization | None
    _state_signature: str
    _catalog_signature: str
    _issuer: object

    def is_authentic_for(self, state: GameState, catalog: ContentCatalog) -> bool:
        return (
            getattr(self, "_issuer", None) is _TRUSTED_CONTEXT_ISSUER
            and getattr(self, "_state_signature", None)
            == _json_signature(state.to_snapshot())
            and getattr(self, "_catalog_signature", None)
            == _json_signature(catalog.model_dump(mode="json"))
        )

    def authorizes_skill_learning(self, skill_definition_id: str) -> bool:
        authorization = getattr(self, "_skill_learning_authorization", None)
        return (
            getattr(self, "_issuer", None) is _TRUSTED_CONTEXT_ISSUER
            and authorization is not None
            and authorization.is_authentic()
            and skill_definition_id in authorization.skill_definition_ids
        )

    def skill_learning_authority(
        self, skill_definition_id: str
    ) -> tuple[SkillLearningAuthorizationSource, str] | None:
        authorization = getattr(self, "_skill_learning_authorization", None)
        if not self.authorizes_skill_learning(skill_definition_id) or authorization is None:
            return None
        return authorization.source, authorization.source_id


@dataclass(frozen=True, slots=True)
class AuthoritativeActionContextFactory:
    """Projects detached authoritative capabilities into the gateway context.

    Scene visibility remains an application input because GameState deliberately does
    not model scenes. Inventory instances, learned skills, runtime NPC identities and
    static definition identities are always projected from authoritative objects.
    """

    def create(
        self,
        submission: ActionSubmission,
        *,
        state: GameState,
        catalog: ContentCatalog,
        authoritative_view: AuthoritativeStateView | None = None,
        current_turn_id: str | None = None,
        session_phase: str = "AWAITING_ACTION",
        visible_entity_ids: Iterable[str] | None = None,
        interactable_entity_ids: Iterable[str] | None = None,
        environment_tool_ids: Iterable[str] = (),
        processed_client_request_ids: Iterable[str] = (),
    ) -> ActionContext:
        return self._create_action_context(
            submission,
            state=state,
            catalog=catalog,
            authoritative_view=authoritative_view,
            current_turn_id=current_turn_id,
            session_phase=session_phase,
            visible_entity_ids=visible_entity_ids,
            interactable_entity_ids=interactable_entity_ids,
            environment_tool_ids=environment_tool_ids,
            learnable_skill_definition_ids=(),
            processed_client_request_ids=processed_client_request_ids,
        )

    def create_trusted(
        self,
        submission: ActionSubmission,
        *,
        state: GameState,
        catalog: ContentCatalog,
        authoritative_view: AuthoritativeStateView | None = None,
        current_turn_id: str | None = None,
        session_phase: str = "AWAITING_ACTION",
        visible_entity_ids: Iterable[str] | None = None,
        interactable_entity_ids: Iterable[str] | None = None,
        environment_tool_ids: Iterable[str] = (),
        skill_learning_authorization: SkillLearningAuthorization | None = None,
        processed_client_request_ids: Iterable[str] = (),
    ) -> TrustedResolutionContext:
        if (
            skill_learning_authorization is not None
            and not skill_learning_authorization.is_authentic()
        ):
            raise ValueError("skill learning authorization was not issued by the application")
        learnable_skill_definition_ids = (
            skill_learning_authorization.skill_definition_ids
            if skill_learning_authorization is not None
            else frozenset()
        )
        context = self._create_action_context(
            submission,
            state=state,
            catalog=catalog,
            authoritative_view=authoritative_view,
            current_turn_id=current_turn_id,
            session_phase=session_phase,
            visible_entity_ids=visible_entity_ids,
            interactable_entity_ids=interactable_entity_ids,
            environment_tool_ids=environment_tool_ids,
            learnable_skill_definition_ids=learnable_skill_definition_ids,
            processed_client_request_ids=processed_client_request_ids,
        )
        trusted = object.__new__(TrustedResolutionContext)
        object.__setattr__(trusted, "action_context", context)
        object.__setattr__(
            trusted,
            "_skill_learning_authorization",
            skill_learning_authorization,
        )
        object.__setattr__(trusted, "_state_signature", _json_signature(state.to_snapshot()))
        object.__setattr__(
            trusted,
            "_catalog_signature",
            _json_signature(catalog.model_dump(mode="json")),
        )
        object.__setattr__(trusted, "_issuer", _TRUSTED_CONTEXT_ISSUER)
        return trusted

    def issue_skill_learning_authorization(
        self,
        skill_definition_ids: Iterable[str],
        *,
        catalog: ContentCatalog,
        source: SkillLearningAuthorizationSource,
        source_id: str,
    ) -> SkillLearningAuthorization:
        if not isinstance(source, SkillLearningAuthorizationSource):
            raise TypeError("skill authorization source must be a trusted source enum")
        if not _STABLE_ID_PATTERN.fullmatch(source_id):
            raise ValueError("skill authorization source_id must be a stable identifier")
        available_skill_ids = frozenset(
            definition.definition_id for definition in catalog.skills
        )
        authorized_ids = frozenset(skill_definition_ids)
        if not authorized_ids:
            raise ValueError("skill learning authorization cannot be empty")
        if not authorized_ids <= available_skill_ids:
            unknown = ", ".join(sorted(authorized_ids - available_skill_ids))
            raise ValueError(f"authorized skills are absent from ContentCatalog: {unknown}")
        authorization = object.__new__(SkillLearningAuthorization)
        object.__setattr__(authorization, "skill_definition_ids", authorized_ids)
        object.__setattr__(authorization, "source", source)
        object.__setattr__(authorization, "source_id", source_id)
        object.__setattr__(authorization, "_issuer", _SKILL_AUTHORIZATION_ISSUER)
        return authorization

    def _create_action_context(
        self,
        submission: ActionSubmission,
        *,
        state: GameState,
        catalog: ContentCatalog,
        authoritative_view: AuthoritativeStateView | None,
        current_turn_id: str | None,
        session_phase: str,
        visible_entity_ids: Iterable[str] | None,
        interactable_entity_ids: Iterable[str] | None,
        environment_tool_ids: Iterable[str],
        learnable_skill_definition_ids: Iterable[str],
        processed_client_request_ids: Iterable[str],
    ) -> ActionContext:
        expected_view = AuthoritativeStateView(state, catalog)
        view = authoritative_view or expected_view
        if view != expected_view:
            raise ValueError("authoritative_view does not match GameState and ContentCatalog")

        runtime_npc_ids = view.npc_ids
        visible = (
            frozenset()
            if visible_entity_ids is None
            else frozenset(visible_entity_ids)
        )
        interactable = (
            frozenset()
            if interactable_entity_ids is None
            else frozenset(interactable_entity_ids)
        )
        npc_definition_ids = frozenset(item.definition_id for item in catalog.npcs)
        invalid_npc_references = {
            entity_id
            for entity_id in visible | interactable
            if entity_id in npc_definition_ids
        }
        if invalid_npc_references:
            invalid = ", ".join(sorted(invalid_npc_references))
            raise ValueError(f"NPC definition IDs cannot be used as runtime npc_id: {invalid}")

        environment_tools = frozenset(environment_tool_ids)
        static_definition_ids = _catalog_definition_ids(catalog)
        invalid_environment_tools = environment_tools & static_definition_ids
        if invalid_environment_tools:
            invalid = ", ".join(sorted(invalid_environment_tools))
            raise ValueError(
                f"static definition IDs cannot be used as environment tool IDs: {invalid}"
            )

        available_skill_ids = frozenset(
            definition.definition_id for definition in catalog.skills
        )
        learnable_skill_ids = frozenset(learnable_skill_definition_ids)
        if not learnable_skill_ids <= available_skill_ids:
            unknown = ", ".join(sorted(learnable_skill_ids - available_skill_ids))
            raise ValueError(f"learnable skills are absent from ContentCatalog: {unknown}")

        return ActionContext(
            submission=submission.model_copy(deep=True),
            current_turn_id=current_turn_id or submission.turn_id,
            session_phase=session_phase,
            visible_entity_ids=frozenset(visible),
            interactable_entity_ids=frozenset(interactable),
            inventory_item_ids=view.inventory_item_instance_ids,
            environment_tool_ids=environment_tools,
            item_definition_by_instance=view.item_definition_by_instance,
            equipment_definition_by_instance=view.equipment_definition_by_instance,
            learned_skill_levels=view.learned_skill_levels,
            available_skill_definition_ids=available_skill_ids,
            npc_definition_by_id=view.npc_definition_by_id,
            resource_ids=view.resource_ids,
            currency_ids=view.currency_ids,
            processed_client_request_ids=frozenset(processed_client_request_ids),
        )

    project = create


def _catalog_definition_ids(catalog: ContentCatalog) -> frozenset[str]:
    return frozenset(
        definition.definition_id
        for definitions in (
            catalog.characters,
            catalog.npcs,
            catalog.items,
            catalog.equipment,
            catalog.skills,
            catalog.effects,
        )
        for definition in definitions
    )


def _json_signature(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
