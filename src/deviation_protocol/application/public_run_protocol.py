"""Closed public Run setup projections. No rendering or mutation authority."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.application.player_character_projection import PlayerCharacterSelfProjection
from deviation_protocol.domain import run_protocol_resolution as s2
from deviation_protocol.domain.entry_world import EntryWorldRefV1, lookup_entry_world
from deviation_protocol.domain.run import revalidate_run_model
from deviation_protocol.domain.run_protocol_mechanics import resource_pressure_label

SafeId128 = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
PositiveInt64 = Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
ObjectiveValue = Annotated[int, Field(strict=True, ge=0, le=100, multiple_of=5)]
ObjectiveName = Literal["resource_pressure", "social_trust", "consequence_severity", "information_opacity", "conflict_intensity"]


class PublicRunModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")


class PublicProfileRef(PublicRunModel):
    profile_id: SafeId128
    profile_version: PositiveInt64


class PublicWorldRef(PublicRunModel):
    entry_world_id: SafeId128
    entry_world_version: PositiveInt64


class FiveObjectives(PublicRunModel):
    resource_pressure: ObjectiveValue
    social_trust: ObjectiveValue
    consequence_severity: ObjectiveValue
    information_opacity: ObjectiveValue
    conflict_intensity: ObjectiveValue


class PublicRunPresentation(PublicRunModel):
    world_tone: Literal["grim", "balanced", "heroic"]
    reality_boundary: Literal["lawful", "deviant", "chaotic"]
    relationship_overlay: Literal["off", "veiled", "charged"]


class PublicNativeRunContext(PublicRunModel):
    schema_version: Literal["public-run-context/v1"]
    run_id: SafeId128
    player_character: PlayerCharacterSelfProjection
    entry_world: PublicWorldRef
    profile_ref: PublicProfileRef
    objectives: FiveObjectives
    presentation: PublicRunPresentation
    resource_pressure_label: Literal["Generous", "Fluid", "Scarce"]

    @model_validator(mode="after")
    def validate_label(self):
        if self.resource_pressure_label != resource_pressure_label(self.objectives.resource_pressure):
            raise ValueError("inconsistent pressure label")
        return self


class PublicOverrideRule(PublicRunModel):
    parameter: ObjectiveName
    minimum: ObjectiveValue
    maximum: ObjectiveValue
    step: Annotated[int, Field(strict=True, ge=5, le=5)]


class PublicRunProfile(PublicRunModel):
    profile_ref: PublicProfileRef
    label: Annotated[str, Field(min_length=1, max_length=128)]
    defaults: FiveObjectives
    override_rules: Annotated[tuple[PublicOverrideRule, ...], Field(min_length=5, max_length=5)]


class PublicEntryWorld(PublicRunModel):
    entry_world: PublicWorldRef
    scenario_id: SafeId128
    scenario_content_version: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
    title: Annotated[str, Field(min_length=1, max_length=120)]
    hook: Annotated[str, Field(min_length=1, max_length=300)]
    eligible_profiles: Annotated[tuple[PublicProfileRef, ...], Field(min_length=3, max_length=3)]


class PublicPresentationOptions(PublicRunModel):
    world_tone: tuple[Literal["grim"], Literal["balanced"], Literal["heroic"]]
    reality_boundary: tuple[Literal["lawful"], Literal["deviant"], Literal["chaotic"]]
    relationship_overlay: tuple[Literal["off"], Literal["veiled"], Literal["charged"]]


class RunEntryOptionsResponse(PublicRunModel):
    schema_version: Literal["run-entry-options/v1"]
    native_entry_available: bool
    profiles: Annotated[tuple[PublicRunProfile, ...], Field(max_length=3)]
    entry_worlds: Annotated[tuple[PublicEntryWorld, ...], Field(max_length=1)]
    presentation_options: PublicPresentationOptions


def project_profile_ref(reference):
    return PublicProfileRef(profile_id=reference.profile_id.value, profile_version=reference.profile_version.value)


def project_world_ref(reference):
    return PublicWorldRef(entry_world_id=reference.entry_world_id.value, entry_world_version=reference.entry_world_version.value)


def project_objectives(values):
    return FiveObjectives(**{name.value: getattr(values, name.value).value for name in s2.RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER})


def project_native_context(result):
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionResult
    from deviation_protocol.domain.player_character import PlayerCharacterId, PlayerCharacterRevision, PlayerCharacterLifecycle
    revalidate_run_model(result, NativeRunAdmissionResult)
    resolved = result.resolved_protocol
    s2._validate_resolved_output_state(resolved)
    envelope = resolved.resolution_input.envelope
    world = lookup_entry_world(result.entry_world)
    character = result.applicable_character_reference
    if (result.scenario_id, result.scenario_content_version) != (world.scenario_id, world.scenario_content_version):
        raise ValueError("invalid native public association")
    return PublicNativeRunContext(
        schema_version="public-run-context/v1", run_id=result.run_id.value,
        player_character=PlayerCharacterSelfProjection(
            player_character_id=PlayerCharacterId(value=character.player_character_id.value),
            contract_version=character.contract_version,
            record_revision=PlayerCharacterRevision(value=character.record_revision.value), lifecycle=PlayerCharacterLifecycle.ACTIVE),
        entry_world=project_world_ref(result.entry_world), profile_ref=project_profile_ref(envelope.profile_ref),
        objectives=project_objectives(resolved.final_values),
        presentation=PublicRunPresentation(world_tone=envelope.world_tone.value,
            reality_boundary=envelope.reality_boundary.value, relationship_overlay=envelope.relationship_overlay.value),
        resource_pressure_label=resource_pressure_label(resolved.final_values.resource_pressure.value))


def project_entry_options(session_service, coordinator):
    from deviation_protocol.domain.entry_world import AUTHORED_ENTRY_WORLDS_V1
    profiles, worlds = [], []
    if coordinator is not None:
        for candidate in s2.RUN_PROTOCOL_PROFILE_CATALOGUE_V1:
            profile = s2.lookup_run_protocol_profile(candidate.profile_ref)
            profiles.append(PublicRunProfile(profile_ref=project_profile_ref(profile.profile_ref), label=profile.label,
                defaults=project_objectives(profile.base_values), override_rules=tuple(PublicOverrideRule(
                    parameter=r.parameter.value, minimum=r.minimum.value, maximum=r.maximum.value, step=r.step)
                    for r in profile.override_rules)))
        for candidate in AUTHORED_ENTRY_WORLDS_V1:
            world = lookup_entry_world(EntryWorldRefV1(entry_world_id=candidate.entry_world_id, entry_world_version=candidate.entry_world_version))
            definition = session_service.resolve_run_entry_definition(world.scenario_id)
            if (definition.content_version != world.scenario_content_version
                    or definition.public_client.default_character_definition_id != world.default_character_definition_id
                    or not any((e.world_id, e.world_version, e.scenario_id, e.content_version, e.character_id) == (
                        world.entry_world_id.value, world.entry_world_version.value, world.scenario_id,
                        world.scenario_content_version, world.default_character_definition_id) for e in coordinator.catalogue)):
                raise ValueError("invalid native discovery association")
            worlds.append(PublicEntryWorld(entry_world=project_world_ref(world), scenario_id=world.scenario_id,
                scenario_content_version=world.scenario_content_version, title=definition.public_client.title,
                hook=definition.public_client.hook, eligible_profiles=tuple(p.profile_ref for p in profiles)))
        if len(profiles) != 3 or len(worlds) != 1:
            raise ValueError("incomplete native discovery catalogue")
    return RunEntryOptionsResponse(schema_version="run-entry-options/v1", native_entry_available=coordinator is not None,
        profiles=tuple(profiles), entry_worlds=tuple(sorted(worlds, key=lambda w: (w.entry_world.entry_world_id, w.entry_world.entry_world_version))),
        presentation_options=PublicPresentationOptions(world_tone=("grim", "balanced", "heroic"),
            reality_boundary=("lawful", "deviant", "chaotic"), relationship_overlay=("off", "veiled", "charged")))


async def read_native_context(uow, principal, persisted, state, definition, coordinator, controller_resolver):
    from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
    from deviation_protocol.application.native_run_admission import _result
    from deviation_protocol.application.native_turn_mechanics import NativeMechanicsIntegrityError
    from deviation_protocol.domain.player_character import ControllerBindingRef, validate_canonical_player_character
    session_id = persisted.session.session_id
    try:
        family = await coordinator.load(uow, persisted.session, state, definition)
        if family is None:
            return None
        controller = await controller_resolver.resolve(principal)
        if controller is None:
            raise SessionNotFoundError(session_id)
        try:
            revalidate_run_model(controller, ControllerBindingRef)
        except (TypeError, ValueError, AttributeError):
            raise SessionNotFoundError(session_id) from None
        reference = family.canonical_run.player_character_binding.applicable_character_reference
        character = await uow.player_characters.get(reference.player_character_id)
        if character is None:
            raise SessionNotFoundError(session_id)
        validate_canonical_player_character(character)
        registered = await uow.controller_bindings.get(controller)
        if character.controller_binding != controller or registered is None:
            raise SessionNotFoundError(session_id)
        revalidate_run_model(registered, ControllerBindingRef)
        if (registered != controller or character.player_character_id != reference.player_character_id
                or character.contract_version != reference.contract_version
                or character.record_revision.value < reference.record_revision.value):
            raise SnapshotInvalidError(session_id)
        from deviation_protocol.application.run_continuation_service import original_admission
        admission = original_admission(family)
        return project_native_context(_result(admission))
    except (NativeMechanicsIntegrityError, ValueError, TypeError, AttributeError, s2._S2StateError):
        raise SnapshotInvalidError(session_id) from None
