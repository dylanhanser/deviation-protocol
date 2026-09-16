import hashlib
import json
from types import SimpleNamespace

import pytest

from deviation_protocol.application.native_run_admission import (
    NativeRunEntryCreationEvidenceV1, NativeRunAdmissionCommand,
    native_run_entry_evidence_bytes, native_run_entry_creation_fingerprint,
    derive_native_run_entry_internal_id,
)
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey, derive_run_entry_internal_id
from deviation_protocol.domain.player_character import ControllerBindingRef, PlayerCharacterRevision
from deviation_protocol.domain import run_protocol as s1, run_protocol_resolution as s2
from deviation_protocol.infrastructure.run_persistence import creation_evidence_from_storage, RunStoredRecordIntegrityError
from deviation_protocol.infrastructure.run_protocol_binding_persistence import (
    _validate_native_receipt_protocol, RunProtocolBindingStoredIntegrityError,
)
from tests.unit.test_entry_world import reference
from tests.unit.test_run_protocol_resolution import S1_001, RESOLUTION_001


def command(character_id, key="native.operation"):
    envelope = s1.decode_run_protocol_envelope(S1_001, expected_epoch="run-protocol-envelope", expected_version=1)
    return NativeRunAdmissionCommand(public_operation_key=RunEntryPublicOperationKey(value=key),
        player_character_id=character_id, expected_record_revision=PlayerCharacterRevision(value=1),
        protocol=envelope, overrides=s2.RunProtocolOverrideProposalV1(profile_ref=envelope.profile_ref, entries=()),
        entry_world=reference())


def evidence():
    return NativeRunEntryCreationEvidenceV1.model_validate({
        "controller_operation": {"controller_binding": {"value": "controller.golden"}, "public_operation_key": "operation.golden"},
        "player_id": "player.golden", "player_character": {"player_character_id": {"value": "character.golden"}, "pre_entry_record_revision": {"value": 1}},
        "scenario": {"scenario_id": "death_certificate", "content_version": "death-certificate-1.1.0", "default_character_definition_id": "character.death_certificate.investigator"},
        "trusted_run_source": {"source_reference": {"value": "source.production-run"}},
        "entry_world": reference().model_dump(), "resolution_input_hex": RESOLUTION_001.hex(),
        "resolution_fingerprint": "2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac",
    }, strict=True)


def test_native_codec_round_trip():
    value = evidence()
    encoded, fingerprint = native_run_entry_creation_fingerprint(value)
    assert encoded[:13] == b"\x8aDP33S4E\r\n\x1a\n\x01"
    assert creation_evidence_from_storage(encoded) == value
    assert fingerprint.value == hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize("mutate", [
    lambda b: b[:12], lambda b: b[:12] + b"\x02" + b[13:],
    lambda b: b[:13] + b"\xef\xbb\xbf" + b[13:],
    lambda b: b + b" ", lambda b: b[:13] + b'{"player_id":"duplicate",' + b[14:],
    lambda b: b.replace(b'"value":1}', b'"value":1.0}', 1),
    lambda b: b.replace(b'"player_id":', b'"unexpected":', 1),
    lambda b: b[:5] + b"X" + b[6:], lambda b: b"\x89" + b[1:],
])
def test_codec_rejects_ambiguous_or_noncanonical_storage(mutate):
    with pytest.raises(RunStoredRecordIntegrityError):
        creation_evidence_from_storage(mutate(native_run_entry_evidence_bytes(evidence())))


@pytest.mark.parametrize("input_matches,fingerprint_matches", [(False, True), (True, False), (False, False)])
def test_both_receipt_comparisons_are_independently_enforced(input_matches, fingerprint_matches):
    value = evidence()
    binding = SimpleNamespace(resolution_input_canonical=RESOLUTION_001 if input_matches else b"different",
        resolution_fingerprint=bytes.fromhex(value.resolution_fingerprint) if fingerprint_matches else b"\x00" * 32)
    with pytest.raises(RunProtocolBindingStoredIntegrityError) as caught:
        _validate_native_receipt_protocol(value, binding)
    assert type(caught.value) is RunProtocolBindingStoredIntegrityError
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("purpose", ["run.create/v1", "run.bind-player-character/v1", "run.attach-session/v1", "session.create/v1"])
def test_native_ids_are_distinct_from_p8(purpose):
    args = dict(purpose=purpose, controller_binding=ControllerBindingRef(value="controller.golden"),
                public_operation_key=RunEntryPublicOperationKey(value="operation.golden"))
    assert derive_native_run_entry_internal_id(**args) != derive_run_entry_internal_id(**args)


NATIVE_LITERAL = b'\x8aDP33S4E\r\n\x1a\n\x01{"controller_operation":{"controller_binding":{"value":"controller.golden"},"public_operation_key":"operation.golden"},"entry_world":{"entry_world_id":{"value":"world.death_certificate"},"entry_world_version":{"value":1}},"evidence_schema":"run-entry.native-creation-evidence/v1","player_character":{"player_character_id":{"value":"character.golden"},"pre_entry_record_revision":{"value":1}},"player_id":"player.golden","resolution_fingerprint":"2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac","resolution_input_hex":"7b22617574686f72697a65645f6f7665727269646573223a5b5d2c22617574686f72697a65645f70726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c22617574686f72697a65645f70726f66696c655f76657273696f6e223a312c2263616e6f6e6963616c5f656e76656c6f70655f686578223a223762323237303732366636363639366336353566373236353636323233613762323237303732366636363639366336353566363936343232336132323634363936363636363936333735366337343739326536363732363136373639366336353264363136633663363936313665363336353232326332323730373236663636363936633635356637363635373237333639366636653232336133313764326332323732363536313663363937343739356636323666373536653634363137323739323233613232366336313737363637353663323232633232373236353663363137343639366636653733363836393730356636663736363537323663363137393232336132323666363636363232326332323733363336383635366436313566373636353732373336393666366532323361323237323735366532643730373236663734366636333666366332643635366537363635366336663730363532663736333132323263323237373666373236633634356637343666366536353232336132323632363136633631366536333635363432323764222c227265736f6c7665725f76657273696f6e223a312c22736368656d61223a2272756e2d70726f746f636f6c2d7265736f6c7574696f6e2f7631227d","scenario":{"content_version":"death-certificate-1.1.0","default_character_definition_id":"character.death_certificate.investigator","scenario_id":"death_certificate"},"trusted_run_source":{"source_reference":{"value":"source.production-run"}}}'
NATIVE_LITERAL_SHA256 = '570adfa8b9ecb88a1825a69d72dd4678eb2655a5f55d2932a28e1a49f43509f5'
NATIVE_ID_LITERALS = {'run.create/v1': 'f08a60310f717d91ddbde5ad7b61b8429b9604475926321e870fd1b9a2873674', 'run.bind-player-character/v1': 'd320bd693596781cf2657f3bba2b65afe31c4750ffcc232c6d66ef7362202207', 'run.attach-session/v1': 'dc7e5c5e0937762467de5597ac8d915036bc3dd7da851f8a6f605831009cd5a7', 'session.create/v1': '4a3e3448d3ef67eefb02f74bc29741fd75a389db782fda002bc2d7b1e677d266'}

def test_independent_literal_goldens():
    assert native_run_entry_evidence_bytes(evidence()) == NATIVE_LITERAL
    assert native_run_entry_creation_fingerprint(evidence())[1].value == NATIVE_LITERAL_SHA256
    for purpose, expected in NATIVE_ID_LITERALS.items():
        assert derive_native_run_entry_internal_id(purpose=purpose, controller_binding=ControllerBindingRef(value="controller.golden"), public_operation_key=RunEntryPublicOperationKey(value="operation.golden")) == expected


def native_service_fixture(events):
    from dataclasses import fields
    from unittest.mock import AsyncMock
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionService
    from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1
    from tests.unit import test_run_entry_service as legacy

    class NativeUnit(legacy._Uow):
        def __init__(self):
            super().__init__(events)
            self.run_creation_receipts.add_native_with_evidence = AsyncMock(side_effect=lambda *a, **k: events.append("native.receipt"))
            self.run_protocol_bindings = SimpleNamespace(add_native=AsyncMock(side_effect=lambda *a, **k: events.append("native.protocol")),
                                                        get_classified_for_update=AsyncMock(side_effect=self.classify))
            self.run_entry_world_bindings = SimpleNamespace(add_native=AsyncMock(side_effect=lambda *a, **k: events.append("native.world")))
        async def classify(self, *, run_id):
            events.append("native.reconstruct")
            return NativeRunAdmissionV1(canonical_run=self.runs.append_revision.await_args_list[-1].args[0],
                protocol_binding=self.run_protocol_bindings.add_native.await_args.args[0],
                world_binding=self.run_entry_world_bindings.add_native.await_args.args[0])
    unit = NativeUnit()
    factory = legacy._Factory(unit)
    old, *_ = legacy._service(factory, events)
    service = NativeRunAdmissionService(**{f.name: getattr(old, f.name) for f in fields(old)})
    return service, unit, factory, legacy


async def test_native_service_order_and_application_owned_commit():
    events = []
    service, unit, factory, legacy = native_service_fixture(events)
    result = await service.enter(legacy.PRINCIPAL, command=command(legacy.REFERENCE.player_character_id))
    assert result.admitted_run_revision.value == 3
    assert events[:6] == ["controller.resolve", "uow.enter", "pc.lock", "creation-receipt.read", "run.active-lock", "session.creation-read"]
    assert events[-5:] == ["native.protocol", "native.world", "native.reconstruct", "commit", "uow.close"]
    assert events.index("run.revision-1") < events.index("native.receipt") < events.index("session.row") < events.index("participation.write")
    assert unit.commit.await_count == 1 and unit.rollback_calls == 0
    unit.run_creation_receipts.add_with_evidence.assert_not_awaited()


@pytest.mark.parametrize("kind", ["principal", "command", "nested", "controller"])
async def test_native_preflight_has_no_uow_issuer_or_clock(kind):
    from unittest.mock import AsyncMock
    events = []
    service, unit, factory, legacy = native_service_fixture(events)
    principal = legacy.PRINCIPAL
    proposed = command(legacy.REFERENCE.player_character_id)
    if kind == "principal":
        principal = object()
    elif kind == "command":
        proposed.__dict__["untrusted_run_id"] = "run.forged"
    elif kind == "nested":
        proposed.entry_world.entry_world_id.__dict__["hidden"] = True
    else:
        service.controller_binding_resolver.resolve = AsyncMock(return_value=None)
    if kind == "controller":
        assert (await service.enter(principal, command=proposed)).code.value == "AUTHORIZATION_FAILED"
    else:
        with pytest.raises((TypeError, ValueError)):
            await service.enter(principal, command=proposed)
    assert factory.calls == service.run_id_issuer.calls == service.continuous_story_line_id_issuer.calls == 0
    assert "clock" not in events


def test_native_maximum_scalar_sizes_and_total_byte_ceiling():
    payload = evidence().model_dump()
    payload["controller_operation"] = {"controller_binding": {"value": "c" * 128}, "public_operation_key": "o" * 128}
    payload["player_id"] = "p" * 64
    payload["player_character"] = {"player_character_id": {"value": "c" * 128}, "pre_entry_record_revision": {"value": 2**63 - 1}}
    payload["scenario"] = {"scenario_id": "s" * 128, "content_version": "v" * 32, "default_character_definition_id": "c" * 128}
    payload["trusted_run_source"] = {"source_reference": {"value": "s" * 128}}
    payload["entry_world"] = {"entry_world_id": {"value": "w" * 128}, "entry_world_version": {"value": 2**63 - 1}}
    value = NativeRunEntryCreationEvidenceV1.model_validate(payload, strict=True)
    encoded = native_run_entry_evidence_bytes(value)
    assert len(encoded) <= 4096 and creation_evidence_from_storage(encoded) == value
    with pytest.raises(RunStoredRecordIntegrityError):
        creation_evidence_from_storage(encoded + b" " * (4097 - len(encoded)))


@pytest.mark.parametrize("inner", [b"{}", RESOLUTION_001 + b" ", RESOLUTION_001.replace(b'"resolver_version":1', b'"resolver_version":1.0'),
    RESOLUTION_001.replace(b'"authorized_overrides":[]', b'"authorized_overrides":[],"authorized_overrides":[]')])
def test_native_receipt_rejects_malformed_inner_intent_before_binding_comparison(inner):
    payload = json.loads(NATIVE_LITERAL[13:])
    payload["resolution_input_hex"] = inner.hex()
    raw = b"\x8aDP33S4E\r\n\x1a\n\x01" + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(RunStoredRecordIntegrityError) as caught:
        creation_evidence_from_storage(raw)
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("kind", ["foreign", "retired", "exhausted", "scenario-version", "scenario-character"])
async def test_native_authority_and_eligibility_boundaries_precede_staging(kind, monkeypatch):
    from unittest.mock import AsyncMock
    from deviation_protocol.application.player_character_service import PlayerCharacterBindingEligibilityEvidence
    from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
    events = []
    service, unit, factory, legacy = native_service_fixture(events)
    proposed = command(legacy.REFERENCE.player_character_id)
    if kind in ("foreign", "retired", "exhausted"):
        reference = legacy.REFERENCE
        if kind == "exhausted":
            reference = reference.model_copy(update={"record_revision": PlayerCharacterRevision(value=2**63 - 1)})
            proposed = proposed.model_copy(update={"expected_record_revision": reference.record_revision})
        service.player_character_binding_evidence.lock_owned_for_binding = AsyncMock(return_value=None if kind == "foreign" else
            PlayerCharacterBindingEligibilityEvidence(applicable_character_reference=reference,
                lifecycle=PlayerCharacterLifecycle.RETIRED if kind == "retired" else PlayerCharacterLifecycle.ACTIVE))
        expected = "AUTHORIZATION_FAILED" if kind == "foreign" else "PLAYER_CHARACTER_NOT_ELIGIBLE"
    else:
        definition = service.session_service.resolve_run_entry_definition("death_certificate")
        incompatible = SimpleNamespace(scenario_id=definition.scenario_id,
            content_version="different.version" if kind == "scenario-version" else definition.content_version,
            public_client=SimpleNamespace(default_character_definition_id="different.character" if kind == "scenario-character"
                else definition.public_client.default_character_definition_id))
        monkeypatch.setattr(type(service.session_service), "resolve_run_entry_definition", lambda *args: incompatible)
        expected = "INVALID_SCENARIO_DEFINITION"
    assert (await service.enter(legacy.PRINCIPAL, command=proposed)).code.value == expected
    assert service.run_id_issuer.calls == service.continuous_story_line_id_issuer.calls == 0
    unit.runs.add_initial.assert_not_awaited()
    unit.commit.assert_not_awaited()
    assert unit.rollback_calls == unit.close_calls == 1
