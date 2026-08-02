from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from pydantic import ValidationError
import pytest

from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    ReservedPlayerCharacterBinding,
    RunAuthoritySourceRef,
    RunId,
    RunLifecycleStatus,
    RunMutationKind,
    RunMutationProvenance,
    RunOperationId,
    RunSessionParticipationReference,
    RunStateVersion,
    canonical_run_operation_bytes,
    validate_canonical_run,
)


def run_id() -> RunId:
    return RunId(value="run.123e4567e89b42d3a456426614174000")


def line_id() -> ContinuousStoryLineId:
    return ContinuousStoryLineId(value="csl.123e4567e89b42d3a456426614174001")


def source_ref() -> RunAuthoritySourceRef:
    return RunAuthoritySourceRef(value="source.run-create")


def provenance(
    *,
    kind: RunMutationKind = RunMutationKind.CREATE,
    prior: RunStateVersion | None = None,
    resulting: RunStateVersion | None = None,
) -> RunMutationProvenance:
    return RunMutationProvenance(
        target_run_id=run_id(),
        target_continuous_story_line_id=line_id(),
        prior_state_version=prior,
        resulting_state_version=(
            resulting if resulting is not None else RunStateVersion(value=1)
        ),
        mutation_kind=kind,
        operation_id=RunOperationId(value=f"operation.{kind.value.lower()}"),
        source_reference=source_ref(),
        occurred_at=datetime(2026, 7, 29, tzinfo=UTC),
    )


def participation(
    version: int,
    *,
    session_id: str | None = None,
) -> RunSessionParticipationReference:
    return RunSessionParticipationReference(
        session_id=session_id or f"session.{version}",
        run_id=run_id(),
        continuous_story_line_id=line_id(),
        joined_state_version=RunStateVersion(value=version),
        operation_id=RunOperationId(value=f"operation.attach-{version}"),
        source_reference=source_ref(),
    )


def canonical_run(
    *,
    state_version: RunStateVersion | None = None,
    current_kind: RunMutationKind = RunMutationKind.CREATE,
    participation: tuple[RunSessionParticipationReference, ...] = (),
    binding: ReservedPlayerCharacterBinding | None = None,
) -> CanonicalRun:
    version = state_version or RunStateVersion(
        value=1 if current_kind is RunMutationKind.CREATE else 2
    )
    current = provenance(
        kind=current_kind,
        prior=None if current_kind is RunMutationKind.CREATE else RunStateVersion(value=version.value - 1),
        resulting=version,
    )
    if current_kind is RunMutationKind.ATTACH_SESSION and participation:
        current = current.model_copy(
            update={
                "operation_id": participation[-1].operation_id,
                "source_reference": participation[-1].source_reference,
            }
        )
    return CanonicalRun(
        run_id=run_id(),
        continuous_story_line_id=line_id(),
        lifecycle_status=RunLifecycleStatus.PRE_FIRST_TURN,
        state_version=version,
        creation_provenance=provenance(),
        current_mutation_provenance=current,
        trusted_participation_references=participation,
        player_character_binding=binding,
    )


def player_character_reference(
    *,
    player_character_id: str = "pc.bound",
) -> ApplicableCharacterReference:
    return ApplicableCharacterReference(
        player_character_id=PlayerCharacterId(value=player_character_id),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=1),
    )


def active_binding(
    *,
    target_run_id: RunId | None = None,
    target_line_id: ContinuousStoryLineId | None = None,
    operation_id: RunOperationId | None = None,
    source: RunAuthoritySourceRef | None = None,
    bound_at: datetime | None = None,
) -> ReservedPlayerCharacterBinding:
    return ReservedPlayerCharacterBinding(
        run_id=target_run_id or run_id(),
        continuous_story_line_id=target_line_id or line_id(),
        applicable_character_reference=player_character_reference(),
        binding_state="active",
        binding_operation_id=operation_id
        or RunOperationId(value="operation.bind_player_character"),
        binding_authority_source_ref=source or source_ref(),
        bound_at=bound_at or datetime(2026, 7, 29, tzinfo=UTC),
    )


def test_run_and_line_identities_are_distinct_opaque_domains() -> None:
    run = RunId(value="same.exact-value")
    line = ContinuousStoryLineId(value="same.exact-value")
    assert run != line
    assert str(run) == str(line) == "same.exact-value"
    for reference_type in (RunId, ContinuousStoryLineId, RunOperationId, RunAuthoritySourceRef):
        assert reference_type(value="ref.MiXeD-1").value == "ref.MiXeD-1"
        for invalid in ("", "contains whitespace", "bad\x00value", "x" * 129, 1):
            with pytest.raises(ValidationError):
                reference_type(value=invalid)


def test_lifecycle_vocabulary_and_version_successor_are_closed() -> None:
    assert RunLifecycleStatus.PRE_FIRST_TURN.is_active_line
    assert RunLifecycleStatus.ACTIVE.is_active_line
    assert not RunLifecycleStatus.COMPLETED.is_active_line
    assert not RunLifecycleStatus.TERMINATED.is_active_line
    with pytest.raises(ValueError):
        RunLifecycleStatus("resumed")
    assert RunStateVersion(value=1).successor() == RunStateVersion(value=2)
    maximum = RunStateVersion(value=2**63 - 1)
    assert not maximum.has_successor
    with pytest.raises(ValueError, match="no signed 64-bit successor"):
        maximum.successor()


def test_canonical_run_accepts_only_initial_unbound_state_and_strict_provenance() -> None:
    run = canonical_run()
    assert validate_canonical_run(run) is run
    assert run.player_character_binding is None
    with pytest.raises(ValidationError, match="pre_first_turn"):
        CanonicalRun.model_validate(
            {**run.model_dump(mode="python"), "lifecycle_status": RunLifecycleStatus.ACTIVE}
        )
    with pytest.raises(ValidationError, match="complete binding"):
        canonical_run(current_kind=RunMutationKind.BIND_PLAYER_CHARACTER)


def test_canonical_run_accepts_one_complete_active_binding_transition() -> None:
    binding = active_binding()
    run = canonical_run(
        state_version=RunStateVersion(value=2),
        current_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        binding=binding,
    )

    assert validate_canonical_run(run) is run
    assert run.player_character_binding == binding
    assert run.trusted_participation_references == ()
    assert (
        run.current_mutation_provenance.operation_id
        == binding.binding_operation_id
    )
    assert (
        run.current_mutation_provenance.source_reference
        == binding.binding_authority_source_ref
    )
    assert run.current_mutation_provenance.occurred_at == binding.bound_at


@pytest.mark.parametrize(
    ("binding_change", "message"),
    (
        (
            {"run_id": RunId(value="run.foreign")},
            "does not bind this Run",
        ),
        (
            {
                "continuous_story_line_id": ContinuousStoryLineId(
                    value="csl.foreign"
                )
            },
            "does not bind this Run",
        ),
        (
            {
                "binding_operation_id": RunOperationId(
                    value="operation.foreign"
                )
            },
            "provenance is inconsistent",
        ),
        (
            {
                "binding_authority_source_ref": RunAuthoritySourceRef(
                    value="source.foreign"
                )
            },
            "provenance is inconsistent",
        ),
        (
            {
                "bound_at": datetime(
                    2026,
                    7,
                    29,
                    0,
                    0,
                    1,
                    tzinfo=UTC,
                )
            },
            "provenance is inconsistent",
        ),
    ),
)
def test_canonical_run_rejects_binding_that_contradicts_run_or_provenance(
    binding_change: dict[str, object],
    message: str,
) -> None:
    binding = active_binding().model_copy(update=binding_change)

    with pytest.raises((ValidationError, ValueError), match=message):
        canonical_run(
            state_version=RunStateVersion(value=2),
            current_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
            binding=binding,
        )


def test_canonical_run_rejects_binding_without_exactly_one_binding_version() -> None:
    binding = active_binding()
    participation_two = participation(2)
    participation_three = participation(3)
    participation_four = participation(4)

    with pytest.raises(
        ValidationError,
        match="every non-binding successor version",
    ):
        canonical_run(
            state_version=RunStateVersion(value=2),
            current_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
            participation=(participation_two,),
            binding=binding,
        )
    later_attachment = canonical_run(
        state_version=RunStateVersion(value=3),
        current_kind=RunMutationKind.ATTACH_SESSION,
        participation=(participation_three,),
        binding=binding,
    )
    assert later_attachment.player_character_binding == binding
    with pytest.raises(
        ValidationError,
        match="every non-binding successor version",
    ):
        canonical_run(
            state_version=RunStateVersion(value=4),
            current_kind=RunMutationKind.ATTACH_SESSION,
            participation=(participation_four,),
            binding=binding,
        )


@pytest.mark.parametrize(
    "occurred_at",
    (
        datetime(2026, 7, 29),
        datetime(
            2026,
            7,
            29,
            tzinfo=timezone(timedelta(hours=1)),
        ),
    ),
)
def test_run_mutation_provenance_rejects_non_utc_timestamps(
    occurred_at: datetime,
) -> None:
    with pytest.raises(ValidationError, match="exact UTC"):
        RunMutationProvenance(
            target_run_id=run_id(),
            target_continuous_story_line_id=line_id(),
            prior_state_version=None,
            resulting_state_version=RunStateVersion(value=1),
            mutation_kind=RunMutationKind.CREATE,
            operation_id=RunOperationId(value="operation.create"),
            source_reference=source_ref(),
            occurred_at=occurred_at,
        )


@pytest.mark.parametrize(
    "bound_at",
    (
        datetime(2026, 7, 29),
        datetime(
            2026,
            7,
            29,
            tzinfo=timezone(timedelta(hours=-1)),
        ),
    ),
)
def test_reserved_binding_audit_time_uses_the_same_utc_boundary(
    bound_at: datetime,
) -> None:
    with pytest.raises(ValidationError, match="exact UTC"):
        ReservedPlayerCharacterBinding(
            run_id=run_id(),
            continuous_story_line_id=line_id(),
            applicable_character_reference=ApplicableCharacterReference(
                player_character_id=PlayerCharacterId(value="pc.reserved"),
                contract_version=PlayerCharacterContractVersion.V1,
                record_revision=PlayerCharacterRevision(value=1),
            ),
            binding_state="active",
            binding_operation_id=RunOperationId(value="operation.bind"),
            binding_authority_source_ref=source_ref(),
            bound_at=bound_at,
        )


@pytest.mark.parametrize(
    ("field_name", "changed_value"),
    (
        (
            "operation_id",
            RunOperationId(value="operation.changed-creation"),
        ),
        (
            "source_reference",
            RunAuthoritySourceRef(value="source.changed-creation"),
        ),
        (
            "occurred_at",
            datetime(2026, 7, 29, 0, 1, tzinfo=UTC),
        ),
    ),
)
def test_creation_state_requires_exact_current_creation_provenance(
    field_name: str,
    changed_value: object,
) -> None:
    creation = provenance()
    changed_current = creation.model_copy(
        update={field_name: changed_value}
    )

    with pytest.raises(ValidationError, match="exact creation provenance"):
        CanonicalRun(
            run_id=run_id(),
            continuous_story_line_id=line_id(),
            lifecycle_status=RunLifecycleStatus.PRE_FIRST_TURN,
            state_version=RunStateVersion(value=1),
            creation_provenance=creation,
            current_mutation_provenance=changed_current,
        )


def test_canonical_run_requires_exact_continuous_participation_versions() -> None:
    version_two = participation(2)
    version_three = participation(3)
    valid_version_two = canonical_run(
        state_version=RunStateVersion(value=2),
        current_kind=RunMutationKind.ATTACH_SESSION,
        participation=(version_two,),
    )
    valid = canonical_run(
        state_version=RunStateVersion(value=3),
        current_kind=RunMutationKind.ATTACH_SESSION,
        participation=(version_two, version_three),
    )
    assert validate_canonical_run(valid) is valid

    invalid_states = (
        canonical_run().model_copy(
            update={
                "trusted_participation_references": (
                    participation(1),
                )
            }
        ),
        valid_version_two.model_copy(
            update={
                "trusted_participation_references": (
                    participation(1),
                    version_two,
                )
            }
        ),
        valid.model_copy(
            update={
                "trusted_participation_references": (version_three,),
            }
        ),
        valid.model_copy(
            update={
                "trusted_participation_references": (
                    version_two,
                    version_two,
                )
            }
        ),
        valid.model_copy(
            update={
                "trusted_participation_references": (
                    version_three,
                    version_two,
                )
            }
        ),
    )
    for invalid in invalid_states:
        with pytest.raises(
            (ValidationError, ValueError),
            match="every non-binding successor version in order",
        ):
            validate_canonical_run(invalid)


def test_canonical_run_rejects_invalid_participation_and_corrupted_instance_state() -> None:
    participation = RunSessionParticipationReference(
        session_id="session.1",
        run_id=run_id(),
        continuous_story_line_id=line_id(),
        joined_state_version=RunStateVersion(value=2),
        operation_id=RunOperationId(value="operation.attach-1"),
        source_reference=source_ref(),
    )
    run = canonical_run(
        state_version=RunStateVersion(value=2),
        current_kind=RunMutationKind.ATTACH_SESSION,
        participation=(participation,),
    )
    assert validate_canonical_run(run) == run
    with pytest.raises(
        ValidationError,
        match="every non-binding successor version in order",
    ):
        canonical_run(
            state_version=RunStateVersion(value=2),
            current_kind=RunMutationKind.ATTACH_SESSION,
            participation=(participation, participation),
        )
    corrupted = run.model_copy(update={"unknown_state": "injected"})
    with pytest.raises(ValueError, match="non-canonical instance state"):
        validate_canonical_run(corrupted)
    nested_corrupted = run.model_copy(
        update={"run_id": run.run_id.model_copy(update={"unknown_state": "injected"})}
    )
    with pytest.raises(ValueError, match="non-canonical instance state"):
        validate_canonical_run(nested_corrupted)
    with pytest.raises(
        ValidationError,
        match="every non-binding successor version in order",
    ):
        CanonicalRun.model_validate(
            {
                **canonical_run().model_dump(mode="python"),
                "trusted_participation_references": (
                    participation.model_copy(
                        update={"joined_state_version": RunStateVersion(value=1)}
                    ),
                ),
            }
        )


def test_canonical_operation_bytes_are_nfc_sorted_and_fail_closed() -> None:
    assert canonical_run_operation_bytes({"b": "Cafe\u0301", "a": 1}) == (
        b'{"a":1,"b":"Caf\xc3\xa9"}'
    )
    with pytest.raises(TypeError):
        canonical_run_operation_bytes({"unsupported": object()})


def test_p8_s2_active_revision_three_is_the_only_new_active_shape() -> None:
    binding = active_binding()
    joined = participation(3, session_id="session.entry")
    active = canonical_run(
        state_version=RunStateVersion(value=3),
        current_kind=RunMutationKind.ATTACH_SESSION,
        participation=(joined,),
        binding=binding,
    ).model_copy(update={"lifecycle_status": RunLifecycleStatus.ACTIVE})

    assert validate_canonical_run(active) == active

    invalid_changes = (
        {"state_version": RunStateVersion(value=2)},
        {"player_character_binding": None},
        {"trusted_participation_references": ()},
        {"lifecycle_status": RunLifecycleStatus.COMPLETED},
    )
    for change in invalid_changes:
        with pytest.raises((ValidationError, ValueError)):
            validate_canonical_run(active.model_copy(update=change))
