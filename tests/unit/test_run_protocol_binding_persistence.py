from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.orm import Session, make_transient_to_detached

from deviation_protocol.domain import run_protocol as s1
from deviation_protocol.domain import run_protocol_resolution as s2
from deviation_protocol.domain.run import RunId, ContinuousStoryLineId, RunOperationId, RunAuthoritySourceRef
from deviation_protocol.application.run_operations import (
    CreateRunCommand, construct_created_run, create_run_fingerprint, creation_result,
    StoredRunSuccessReceipt, RunReceiptKey, RunOperationNamespace,
)
from deviation_protocol.infrastructure import orm_models as orm
from deviation_protocol.infrastructure import repositories as repositories
from deviation_protocol.infrastructure import run_protocol_binding_persistence as storage
from deviation_protocol.infrastructure import run_persistence
from deviation_protocol.domain.run_protocol_binding import LegacyRunCompatibilityV1, NativeRunProtocolBindingV1

L_S1 = b'{"profile_ref":{"profile_id":"difficulty.fragile-alliance","profile_version":1},"reality_boundary":"lawful","relationship_overlay":"off","schema_version":"run-protocol-envelope/v1","world_tone":"balanced"}'
L_S2 = b'{"authorized_overrides":[],"authorized_profile_id":"difficulty.fragile-alliance","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e636564227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}'
NOW = datetime(2026, 8, 28, 0, 0, 0, 123456, tzinfo=UTC)
RUN_ID = RunId(value="run.s3.literal")
LINE_ID = ContinuousStoryLineId(value="line.s3.literal")


def literal():
    return storage._StoredRunProtocolBindingV1(
        RUN_ID.value, LINE_ID.value, 1, "phase_3_3_native", "run-protocol-binding", 1,
        "run-protocol-envelope", 1, L_S1, "run-protocol-resolution", 1, L_S2,
        60, 45, 65, 60, 60,
        bytes.fromhex("2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac"),
        NOW.replace(tzinfo=None),
    )


def native_family():
    command = CreateRunCommand(source_reference=RunAuthoritySourceRef(value="source.s3"))
    run = construct_created_run(command, run_id=RUN_ID, continuous_story_line_id=LINE_ID,
        operation_id=RunOperationId(value="operation.s3"), occurred_at=NOW)
    _, fingerprint = create_run_fingerprint(command)
    evidence = run_persistence.creation_operation_evidence_to_storage_bytes(command)
    receipt = StoredRunSuccessReceipt(
        key=RunReceiptKey(operation_namespace=RunOperationNamespace.CREATE_V1, operation_id=run.creation_provenance.operation_id),
        fingerprint=fingerprint, command_kind=run.creation_provenance.mutation_kind, result=creation_result(run),
    )
    creation = orm.RunCreationReceiptRow(
        operation_namespace=receipt.key.operation_namespace.value,
        operation_id=receipt.key.operation_id.value, fingerprint=bytes.fromhex(fingerprint.value),
        command_kind="CREATE", result_schema_version=receipt.result.result_schema_version,
        result_run_id=RUN_ID.value, result_continuous_story_line_id=LINE_ID.value,
        resulting_lifecycle_status=run.lifecycle_status.value, resulting_state_version=1,
        receipt_canonical=run_persistence.run_receipt_to_storage_bytes(receipt),
        operation_evidence_canonical=evidence, created_at=NOW,
    )
    return run, {
        orm.RunCurrentRow: [repositories.SqlAlchemyRunRepository._current_run_row(run, created_at=NOW)],
        orm.RunRevisionRow: [repositories.SqlAlchemyRunRepository._run_revision_row(run, created_at=NOW)],
        orm.RunSessionParticipationRow: [], orm.RunCreationReceiptRow: [creation], orm.RunMutationReceiptRow: [],
        orm.RunProtocolBindingRow: [],
    }


class ReadSession:
    def __init__(self, family):
        self.family = family
        self.sync_session = Session()
        self.no_autoflush = nullcontext()
        self.statements = []
        self.execute = AsyncMock(side_effect=self._execute)
        self.add = Mock(side_effect=AssertionError("production staged a row"))
        self.flush = AsyncMock(side_effect=AssertionError("production flushed"))
        self.commit = AsyncMock(side_effect=AssertionError("production committed"))

    async def _execute(self, statement):
        self.statements.append(statement)
        model = statement.column_descriptions[0]["entity"]
        rows = self.family.get(model, [])
        return SimpleNamespace(scalar_one_or_none=lambda: rows[0] if rows else None,
            scalars=lambda: SimpleNamespace(all=lambda: list(rows)))

    def close(self):
        self.sync_session.close()


def loaded_native(session, **changes):
    values = asdict(replace(literal(), **changes))
    row = orm.RunProtocolBindingRow._sa_class_manager.new_instance()
    vars(row).update(values)
    make_transient_to_detached(row)
    session.sync_session.add(row)
    session.family[orm.RunProtocolBindingRow] = [row]
    return row


async def legacy_family():
    from tests.unit import test_run_entry_service as entry
    from tests.unit.test_run_repositories import _SessionProbe
    from deviation_protocol.domain.player_character import AuthoritySourceRef, CharacterCore, NarrationPreferences
    from deviation_protocol.domain.player_character_policies import CreatePlayerCharacterPolicy

    events = []
    unit = entry._Uow(events)
    service, *_ = entry._service(entry._Factory(unit), events)
    await service.enter(entry.PRINCIPAL, command=entry._command())
    runs = [unit.runs.add_initial.await_args.args[0]] + [call.args[0] for call in unit.runs.append_revision.await_args_list]
    family = {
        orm.RunCurrentRow: [repositories.SqlAlchemyRunRepository._current_run_row(runs[-1], created_at=entry.NOW)],
        orm.RunRevisionRow: [repositories.SqlAlchemyRunRepository._run_revision_row(run, created_at=entry.NOW) for run in runs],
        orm.RunProtocolBindingRow: [],
    }
    probe = _SessionProbe()
    creation_repo = repositories.SqlAlchemyRunCreationReceiptRepository(probe)
    creation_repo._run_at_revision = AsyncMock(return_value=runs[0])
    call = unit.run_creation_receipts.add_with_evidence.await_args
    await creation_repo.add_with_evidence(*call.args, **call.kwargs)
    family[orm.RunCreationReceiptRow] = [probe.added[-1]]
    family[orm.RunMutationReceiptRow] = []
    for index, call in enumerate(unit.run_mutation_receipts.add.await_args_list):
        adapter = repositories.SqlAlchemyRunMutationReceiptRepository(probe)
        adapter._run_at_revision = AsyncMock(side_effect=(runs[index], runs[index + 1]))
        adapter._validate_complete_run = AsyncMock(return_value=runs[index + 1])
        await adapter.add(*call.args, **call.kwargs)
        family[orm.RunMutationReceiptRow].append(probe.added[-1])
    participation = runs[-1].trusted_participation_references[0]
    family[orm.RunSessionParticipationRow] = [orm.RunSessionParticipationRow(
        session_id=participation.session_id, run_id=participation.run_id.value,
        continuous_story_line_id=participation.continuous_story_line_id.value,
        joined_state_version=3, operation_id=participation.operation_id.value,
        source_reference=participation.source_reference.value, joined_at=entry.NOW,
    )]
    character = CreatePlayerCharacterPolicy().create(
        player_character_id=entry.REFERENCE.player_character_id, controller_binding=entry.CONTROLLER,
        character_core=CharacterCore(), narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(value="source.s3-character"),
    )
    family[orm.PlayerCharacterRevisionRow] = [repositories.SqlAlchemyPlayerCharacterRepository._revision_row(character, created_at=entry.NOW)]
    family[orm.PlayerCharacterCurrentRow] = [repositories.SqlAlchemyPlayerCharacterRepository._current_row(character, created_at=entry.NOW)]
    family[orm.PlayerCharacterControllerBindingRow] = [orm.PlayerCharacterControllerBindingRow(controller_binding=entry.CONTROLLER.value, created_at=entry.NOW)]
    session_call = unit.sessions.add_initial_session.await_args
    session = session_call.args[0]
    family[orm.GameSessionRow] = [orm.GameSessionRow(
        **{name: getattr(session, name) for name in ("session_id", "player_id", "scenario_id", "scenario_version", "phase", "turn_number", "state_version", "random_seed")},
        character_definition_id=session_call.kwargs["character_definition_id"],
        creation_client_request_id=session_call.kwargs["creation_client_request_id"], created_at=entry.NOW, updated_at=entry.NOW,
    )]
    event = unit.sessions.persist_events.await_args.args[0][0]
    family[orm.DomainEventRow] = [orm.DomainEventRow(
        **{name: getattr(event, name) for name in ("event_id", "session_id", "turn_id", "sequence_no", "event_type", "occurred_at")},
        payload_json=event.payload,
    )]
    family[orm.GameSnapshotRow] = [orm.GameSnapshotRow(session_id=session.session_id, state_version=0,
        state_json=unit.sessions.add_initial_snapshot.await_args.kwargs["state"], updated_at=entry.NOW)]
    return runs[-1], family


def snapshot(family):
    return {model.__name__: [repr({name: value for name, value in vars(row).items() if name != "_sa_instance_state"}) for row in rows] for model, rows in family.items()}


async def reject_native(changes, expected=storage.RunProtocolBindingStoredIntegrityError, cause=None, mutate=None):
    run, family = native_family()
    session = ReadSession(family)
    row = loaded_native(session, **changes)
    if mutate:
        mutate(row)
    before = snapshot(family)
    try:
        with pytest.raises(expected) as caught:
            await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
        assert type(caught.value) is expected
        assert (type(caught.value.__cause__) is cause) if cause else caught.value.__cause__ is None
        assert snapshot(family) == before
        session.add.assert_not_called()
        session.flush.assert_not_awaited()
        session.commit.assert_not_awaited()
        return caught.value
    finally:
        session.close()


def test_s3_v03(monkeypatch):
    import builtins
    from pathlib import Path
    import socket
    import time

    run, _ = native_family()
    stored = literal()
    before_stored = asdict(stored)
    before_run = run.model_dump()
    lookup = Mock(wraps=s2.lookup_run_protocol_profile)
    monkeypatch.setattr(storage, "lookup_run_protocol_profile", lookup)
    forbidden = Mock(side_effect=AssertionError("reconstruction performed I/O or read a clock"))
    for owner, name in ((builtins, "open"), (Path, "read_bytes"), (Path, "read_text"), (socket, "create_connection"), (time, "time")):
        monkeypatch.setattr(owner, name, forbidden)
    before_namespace = {name: id(value) for name, value in vars(storage).items()}
    first = storage._reconstruct_native_binding(stored, canonical_run=run, legacy_proof=None)
    second = storage._reconstruct_native_binding(stored, canonical_run=run, legacy_proof=None)
    assert first == second and first is not second
    assert first.resolved_protocol is not second.resolved_protocol
    assert first.resolved_protocol.resolution_input is not second.resolved_protocol.resolution_input
    assert first.resolved_protocol.resolution_input.envelope is not second.resolved_protocol.resolution_input.envelope
    assert first.resolved_protocol.resolution_input.authorized_profile is second.resolved_protocol.resolution_input.authorized_profile
    assert lookup.call_count == 2
    assert stored == literal()
    assert asdict(stored) == before_stored and run.model_dump() == before_run
    assert {name: id(value) for name, value in vars(storage).items()} == before_namespace
    forbidden.assert_not_called()
    assert first.resolved_protocol.fingerprint.value == stored.resolution_fingerprint.hex()
    assert s1.encode_run_protocol_envelope_v1(first.resolved_protocol.resolution_input.envelope) == L_S1
    assert s2.encode_run_protocol_resolution_input_v1(first.resolved_protocol.resolution_input) == L_S2


async def test_s3_v01_a(monkeypatch):
    run, family = await legacy_family()
    session = ReadSession(family)
    before = snapshot(family)
    decoded = []
    original_decode = repositories.canonical_record_from_revision_storage
    def remember_decode(stored):
        result = original_decode(stored)
        decoded.append(result)
        return result
    decode = Mock(side_effect=remember_decode)
    validate = Mock(wraps=repositories.validate_stored_run_record_set)
    monkeypatch.setattr(repositories, "canonical_record_from_revision_storage", decode)
    monkeypatch.setattr(repositories, "validate_stored_run_record_set", validate)
    result = await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
    assert type(result) is LegacyRunCompatibilityV1 and result.canonical_run == run
    assert decode.call_count == validate.call_count == 1
    assert validate.call_args.kwargs["referenced_player_character_revision"] is decoded[0]
    assert snapshot(family) == before
    assert all(statement._for_update_arg is None for statement in session.statements)
    session.close()
    session = ReadSession(family)
    locked = await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified_for_update(run_id=run.run_id)
    assert locked == result and locked is not result
    assert all(statement._for_update_arg is not None for statement in session.statements)
    assert [statement.column_descriptions[0]["entity"] for statement in session.statements] == [
        orm.RunCurrentRow, orm.RunRevisionRow, orm.RunSessionParticipationRow,
        orm.RunCreationReceiptRow, orm.RunMutationReceiptRow, orm.PlayerCharacterRevisionRow,
        orm.RunProtocolBindingRow, orm.RunEntryWorldBindingRow,
        orm.RunWorldStateRow, orm.RunWorldVisitRow, orm.RunWorldPositionRow, orm.RunWorldVisitEntryRow,
        orm.PlayerCharacterCurrentRow,
        orm.PlayerCharacterControllerBindingRow, orm.GameSessionRow, orm.DomainEventRow, orm.GameSnapshotRow,
    ]
    session.close()
    from sqlalchemy import exc as sql_errors
    from asyncmy import errors as driver_errors
    from deviation_protocol.application import errors as session_errors
    from deviation_protocol.domain.state import DomainRuleViolation, DomainErrorCode
    from pydantic import ValidationError
    import asyncio

    failures = [
        sql_errors.SQLAlchemyError("read"), sql_errors.StatementError("read", None, None, RuntimeError("driver")),
        sql_errors.InvalidRequestError("read"), sql_errors.TimeoutError("read"),
    ]
    for name in ("DBAPIError", "DatabaseError", "OperationalError", "InterfaceError", "IntegrityError", "ProgrammingError", "DataError", "InternalError", "NotSupportedError"):
        failures.append(getattr(sql_errors, name)(None, None, RuntimeError("driver")))
    for name in ("Error", "InterfaceError", "DatabaseError", "OperationalError", "IntegrityError", "ProgrammingError", "DataError", "InternalError", "NotSupportedError"):
        failures.append(getattr(driver_errors, name)("read"))
    for failure in failures:
        for retrieval in (False, True):
            session = ReadSession(family)
            if retrieval:
                session.execute.side_effect = None
                session.execute.return_value = SimpleNamespace(scalar_one_or_none=Mock(side_effect=failure))
            else:
                session.execute.side_effect = failure
            with pytest.raises(storage.RunProtocolBindingRepositoryError) as caught:
                await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert type(caught.value) is storage.RunProtocolBindingRepositoryError and caught.value.__cause__ is failure
            assert session.execute.await_count == 1
            assert snapshot(family) == before
            session.close()
    try:
        RunId(value="")
    except ValidationError as error:
        validation_error = error
    lower = [DomainRuleViolation(DomainErrorCode.INVALID_SNAPSHOT_REFERENCE, "invalid"), TypeError("stored"), ValueError("stored"), validation_error]
    lower += [getattr(session_errors, name)("stored") for name in (
        "SnapshotNotFoundError", "SnapshotInvalidError", "SnapshotSchemaVersionMismatchError",
        "SnapshotStateVersionMismatchError", "SnapshotSessionMismatchError", "SnapshotContentVersionMismatchError",
    )]
    for failure in lower:
        session = ReadSession(family)
        with monkeypatch.context() as patch:
            seam = Mock(side_effect=failure)
            patch.setattr(storage, "_validate_legacy_session", seam)
            with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
                await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert caught.value.__cause__ is failure and seam.call_count == 1
            assert snapshot(family) == before
        session.close()
    for failure in (
        storage.RunProtocolBindingStoredIntegrityError("same"),
        storage.UnsupportedRunProtocolBindingVersionError("same"),
        storage.ContradictoryRunFamilyError("same"), storage.RunProtocolBindingRepositoryError("same"),
        asyncio.CancelledError(), KeyboardInterrupt(), SystemExit(), AssertionError("unexpected"),
    ):
        session = ReadSession(family)
        session.execute.side_effect = failure
        with pytest.raises(type(failure)) as caught:
            await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
        assert caught.value is failure and session.execute.await_count == 1
        session.close()


@pytest.mark.parametrize("locking", [False, True])
async def test_legacy_binding_requires_common_entry_time(monkeypatch, locking):
    run, family = await legacy_family()
    binding_time = run.creation_provenance.occurred_at + timedelta(seconds=1)
    for row in family[orm.RunRevisionRow][1:] + family[orm.RunCurrentRow]:
        row.bound_at = binding_time
    family[orm.RunRevisionRow][1].occurred_at = binding_time
    family[orm.RunRevisionRow][1].created_at = binding_time
    family[orm.RunMutationReceiptRow][0].created_at = binding_time
    before = snapshot(family)
    validated = []
    original = repositories.validate_stored_run_record_set

    def validate(**kwargs):
        result = original(**kwargs)
        validated.append(result)
        return result

    monkeypatch.setattr(repositories, "validate_stored_run_record_set", validate)
    later = Mock(wraps=storage._validate_legacy_character)
    monkeypatch.setattr(storage, "_validate_legacy_character", later)
    session = ReadSession(family)
    try:
        repository = repositories.SqlAlchemyRunProtocolBindingRepository(session)
        read = repository.get_classified_for_update if locking else repository.get_classified
        with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
            await read(run_id=run.run_id)
        assert type(caught.value) is storage.RunProtocolBindingStoredIntegrityError
        assert str(caught.value) == "legacy binding time differs from entry transaction time"
        assert caught.value.__cause__ is None
        assert len(validated) == 1
        assert validated[0].player_character_binding.bound_at == binding_time
        assert validated[0].creation_provenance.occurred_at == run.creation_provenance.occurred_at
        later.assert_not_called()
        assert snapshot(family) == before
        session.add.assert_not_called()
        session.flush.assert_not_awaited()
        session.commit.assert_not_awaited()
    finally:
        session.close()


async def test_s3_v04():
    await reject_native({"binding_record_version": 2}, storage.UnsupportedRunProtocolBindingVersionError)


async def test_s3_v05(monkeypatch):
    for change, expected, cause in (
        ({"envelope_record_version": 2}, storage.RunProtocolBindingStoredIntegrityError, s1.UnsupportedRunProtocolVersionError),
        ({"envelope_record_version": 2, "resolver_record_version": 2}, storage.RunProtocolBindingStoredIntegrityError, s1.UnsupportedRunProtocolVersionError),
        ({"envelope_canonical": b"{", "resolver_record_version": 2}, storage.RunProtocolBindingStoredIntegrityError, s1.RunProtocolValidationError),
        ({"binding_record_version": 2, "envelope_canonical": b"{"}, storage.UnsupportedRunProtocolBindingVersionError, None),
    ):
        with monkeypatch.context() as patch:
            lookup = Mock(wraps=storage.lookup_run_protocol_profile)
            resolve = Mock(wraps=s2.resolve_run_protocol_objectives)
            decode = Mock(wraps=s1.decode_run_protocol_envelope)
            payload = Mock(wraps=s1.decode_run_protocol_envelope_v1)
            patch.setattr(storage, "lookup_run_protocol_profile", lookup)
            patch.setattr(s2, "resolve_run_protocol_objectives", resolve)
            patch.setattr(s1, "decode_run_protocol_envelope", decode)
            patch.setattr(s1, "decode_run_protocol_envelope_v1", payload)
            await reject_native(change, expected, cause)
            lookup.assert_not_called()
            resolve.assert_not_called()
            assert decode.call_count == (0 if "binding_record_version" in change else 1)
            assert payload.call_count == (1 if cause is s1.RunProtocolValidationError else 0)


async def test_s3_v06(monkeypatch):
    for changes, cause in (
        ({"resolver_record_version": 2}, s2.UnsupportedRunProtocolResolverVersionError),
        ({"resolver_record_version": "2", "envelope_canonical": b"{"}, None),
        ({"resource_pressure": 101, "resolver_record_version": 2}, None),
    ):
        with monkeypatch.context() as patch:
            lookup = Mock(wraps=storage.lookup_run_protocol_profile)
            resolve = Mock(wraps=s2.resolve_run_protocol_objectives)
            decode = Mock(wraps=s1.decode_run_protocol_envelope)
            payload = Mock(wraps=storage._resolution_payload)
            patch.setattr(storage, "lookup_run_protocol_profile", lookup)
            patch.setattr(s2, "resolve_run_protocol_objectives", resolve)
            patch.setattr(s1, "decode_run_protocol_envelope", decode)
            patch.setattr(storage, "_resolution_payload", payload)
            await reject_native(changes, cause=cause)
            assert lookup.call_count == resolve.call_count == decode.call_count == (1 if cause else 0)
            payload.assert_not_called()


async def test_s3_v07(monkeypatch):
    await reject_native({"envelope_canonical": json.dumps(json.loads(L_S1)).encode()}, cause=s1.RunProtocolValidationError)
    from deviation_protocol.infrastructure.run_protocol_persistence import RunProtocolStoredRecordIntegrityError
    for failure in (s1.RunProtocolValidationError("lower"), s1.UnsupportedRunProtocolVersionError("lower"), RunProtocolStoredRecordIntegrityError("lower")):
        nested = ValueError("preserved nested cause")
        failure.__cause__ = nested
        with monkeypatch.context() as patch:
            seam = Mock(side_effect=failure)
            patch.setattr(storage.s1, "decode_run_protocol_envelope", seam)
            caught = await reject_native({}, cause=type(failure))
            assert caught.__cause__ is failure and failure.__cause__ is nested and seam.call_count == 1


async def test_s3_v08(monkeypatch):
    payload = json.loads(L_S2)
    payload["authorized_profile_id"] = "difficulty.standard"
    await reject_native({"resolution_input_canonical": json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()})
    for failure in (s2.RunProtocolProfileLookupError("lookup"), s2.RunProtocolResolutionIntegrityError("catalogue")):
        with monkeypatch.context() as patch:
            seam = Mock(side_effect=failure)
            patch.setattr(storage, "lookup_run_protocol_profile", seam)
            caught = await reject_native({}, cause=type(failure))
            assert caught.__cause__ is failure and seam.call_count == 1


async def test_s3_v09(monkeypatch):
    await reject_native({"resolution_input_canonical": json.dumps(json.loads(L_S2)).encode()}, cause=s2.RunProtocolResolutionIntegrityError)
    from pydantic import ValidationError
    try:
        RunId(value="")
    except ValidationError as error:
        validation_error = error
    for failure in (s2.RunProtocolResolutionError("base"), s2.RunProtocolOverrideValidationError("override"), s2.RunProtocolResolutionIntegrityError("input"), TypeError("input"), ValueError("input"), validation_error):
        with monkeypatch.context() as patch:
            seam = Mock(side_effect=failure)
            patch.setattr(storage.s2, "construct_run_protocol_resolution_input_v1", seam)
            caught = await reject_native({}, cause=type(failure))
            assert caught.__cause__ is failure and seam.call_count == 1


async def test_s3_v10():
    await reject_native({"resource_pressure": 65})


async def test_s3_v11():
    await reject_native({"resolution_fingerprint": b"x" * 32})


async def test_s3_v12():
    await reject_native({"bound_state_version": 2})


async def test_s3_v15():
    run, family = native_family()
    session = ReadSession(family)
    with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
        await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
    assert caught.value.__cause__ is None
    session.close()
    session = ReadSession({})
    assert await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id) is None
    session.family[orm.RunRevisionRow] = family[orm.RunRevisionRow]
    with pytest.raises(storage.RunProtocolBindingStoredIntegrityError):
        await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
    session.close()


async def test_s3_v13(monkeypatch):
    from pydantic import ValidationError
    from deviation_protocol.infrastructure.player_character_persistence import PlayerCharacterStoredRecordIntegrityError

    cases = [
        ("history", None, run_persistence.RunStoredRecordIntegrityError),
        ("immutable", None, PlayerCharacterStoredRecordIntegrityError),
        ("missing-immutable", None, None),
        ("missing-current", None, None),
        ("missing-controller", None, None),
        ("binding_contract_version", None, None),
        ("binding_player_character_id", 1, None),
        ("binding_contract_version", 1, None),
        ("binding_record_revision", "1", None),
        ("binding_record_revision", True, None),
        ("binding_record_revision", 0, None),
        ("binding_record_revision", 2**63, None),
        ("binding_player_character_id", "", ValidationError),
        ("binding_contract_version", "unsupported", ValueError),
        ("mixed", None, PlayerCharacterStoredRecordIntegrityError),
    ]
    for name, value, cause in cases:
        run, family = await legacy_family()
        if name in ("history", "mixed"):
            family[orm.RunRevisionRow][-1].binding_player_character_id = "pc.other"
        if name in ("immutable", "mixed"):
            family[orm.PlayerCharacterRevisionRow][0].record_canonical = b"{"
        if name.startswith("binding_"):
            setattr(family[orm.RunCurrentRow][0], name, value)
        for label, model in (("missing-immutable", orm.PlayerCharacterRevisionRow), ("missing-current", orm.PlayerCharacterCurrentRow), ("missing-controller", orm.PlayerCharacterControllerBindingRow)):
            if name == label:
                family[model] = []
        session = ReadSession(family)
        before = snapshot(family)
        with monkeypatch.context() as patch:
            validate = Mock(wraps=repositories.validate_stored_run_record_set)
            decode = Mock(wraps=repositories.canonical_record_from_revision_storage)
            native = Mock(wraps=storage._reconstruct_native_binding)
            session_validation = Mock(wraps=storage._validate_legacy_session)
            patch.setattr(repositories, "validate_stored_run_record_set", validate)
            patch.setattr(repositories, "canonical_record_from_revision_storage", decode)
            patch.setattr(storage, "_reconstruct_native_binding", native)
            patch.setattr(storage, "_validate_legacy_session", session_validation)
            with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
                await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            native.assert_not_called()
            session_validation.assert_not_called()
            selected = [statement.column_descriptions[0]["entity"] for statement in session.statements]
            if name.startswith("binding_"):
                assert orm.PlayerCharacterRevisionRow not in selected
                decode.assert_not_called()
                validate.assert_not_called()
            elif name in ("immutable", "missing-immutable", "mixed"):
                assert orm.PlayerCharacterRevisionRow in selected
                assert decode.call_count == (0 if name == "missing-immutable" else 1)
                validate.assert_not_called()
                assert orm.RunProtocolBindingRow not in selected
            elif name == "history":
                assert decode.call_count == validate.call_count == 1
                assert orm.RunProtocolBindingRow not in selected
                assert orm.PlayerCharacterCurrentRow not in selected
            else:
                assert decode.call_count == validate.call_count == 1
                assert orm.GameSessionRow not in selected
        assert type(caught.value) is storage.RunProtocolBindingStoredIntegrityError
        assert type(caught.value.__cause__) is cause if cause else caught.value.__cause__ is None
        assert snapshot(family) == before
        session.close()
    for error, seam in ((TypeError("constructor"), "_reference_from_current"), (AttributeError("codec"), "_reference_from_current")):
        run, family = await legacy_family()
        session = ReadSession(family)
        with monkeypatch.context() as patch:
            patch.setattr(storage, seam, Mock(side_effect=error))
            with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
                await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
            assert caught.value.__cause__ is error
            assert not any(statement.column_descriptions[0]["entity"] is orm.PlayerCharacterRevisionRow for statement in session.statements)
        session.close()
    run, family = await legacy_family()
    from tests.unit.test_run_repositories import _active_character
    family[orm.PlayerCharacterRevisionRow] = [repositories.SqlAlchemyPlayerCharacterRepository._revision_row(_active_character(), created_at=NOW)]
    session = ReadSession(family)
    with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
        await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
    assert caught.value.__cause__ is None
    session.close()


async def test_s3_v16():
    await reject_native({}, mutate=lambda row: vars(row).pop("resolution_fingerprint"))
    for condition in ("expired", "detached", "dirty", "wrong-key"):
        run, family = native_family()
        session = ReadSession(family)
        row = loaded_native(session)
        if condition == "expired":
            session.sync_session.expire(row, ["resolution_fingerprint"])
        elif condition == "detached":
            session.sync_session.expunge(row)
        elif condition == "dirty":
            row.resource_pressure = 65
        else:
            row._sa_instance_state.key = (orm.RunProtocolBindingRow, ("run.other",), None)
        with pytest.raises(storage.RunProtocolBindingStoredIntegrityError) as caught:
            await repositories.SqlAlchemyRunProtocolBindingRepository(session).get_classified(run_id=run.run_id)
        assert caught.value.__cause__ is None
        session.close()


async def test_s3_v17():
    await reject_native({"family_discriminator": None})


async def test_s3_v18():
    await reject_native({"family_discriminator": "phase_3_4_native"}, storage.UnsupportedRunProtocolBindingVersionError)


async def test_s3_v19():
    await reject_native({"binding_record_version": True})


async def test_s3_v20_a():
    await reject_native({"run_id": 1})


async def test_s3_v20_b():
    await reject_native({"envelope_canonical": "bad"})


async def test_s3_v20_c():
    await reject_native({"resource_pressure": "60"})


async def test_s3_v20_d():
    await reject_native({"created_at": "bad"})


async def test_s3_v21_b():
    await reject_native({"resolution_input_canonical": b" " * 1025})


async def test_s3_v28_a():
    await reject_native({}, mutate=lambda row: vars(row).pop("bound_state_version"))


async def test_s3_v28_b():
    await reject_native({"continuous_story_line_id": "line.other"})


async def test_s3_v28_c():
    await reject_native({}, mutate=lambda row: vars(row).update(run_family={}))


async def test_s3_v35_a():
    payload = json.loads(L_S2)
    payload["world_id"] = "not-authorized"
    await reject_native({"resolution_input_canonical": json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()}, cause=s2.RunProtocolResolutionIntegrityError)
    for payload, parser in ((b"{", json.JSONDecodeError), (b"\xff", UnicodeDecodeError), (b"[" * 1024, json.JSONDecodeError)):
        failure = await reject_native({"resolution_input_canonical": payload}, cause=s2.RunProtocolResolutionIntegrityError)
        assert type(failure.__cause__.__cause__) is parser


async def test_s3_v35_b():
    await reject_native({}, mutate=lambda row: vars(row).update(writer=object()))
