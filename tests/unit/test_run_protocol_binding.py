from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from deviation_protocol.domain.run_protocol_binding import NativeRunProtocolBindingV1, LegacyRunCompatibilityV1
from deviation_protocol.infrastructure import run_protocol_binding_persistence as storage
from tests.unit.test_run_protocol_binding_persistence import literal, native_family, legacy_family


def test_native_carrier_frozen_original_state_and_cross_binding():
    run, _ = native_family()
    result = storage._reconstruct_native_binding(literal(), canonical_run=run, legacy_proof=None)
    with pytest.raises(ValidationError):
        result.run_id = run.run_id
    for name in ("run_id", "continuous_story_line_id", "bound_state_version", "resolved_protocol"):
        values = dict(result)
        values[name] = None
        with pytest.raises((TypeError, ValueError)):
            NativeRunProtocolBindingV1(**values)
    result.resolved_protocol.__dict__["unexpected"] = 1
    with pytest.raises(ValueError):
        NativeRunProtocolBindingV1(**dict(result))


async def test_legacy_carrier_requires_exact_session_association():
    run, _ = await legacy_family()
    result = LegacyRunCompatibilityV1(canonical_run=run, session_id=run.trusted_participation_references[0].session_id)
    with pytest.raises(ValidationError):
        result.session_id = "other"
    with pytest.raises(ValueError):
        LegacyRunCompatibilityV1(canonical_run=run, session_id="other")


def test_stored_carrier_has_exactly_nineteen_frozen_slots():
    stored = literal()
    assert len(type(stored).__slots__) == 19
    assert not hasattr(stored, "__dict__")
    with pytest.raises(FrozenInstanceError):
        stored.run_id = "other"
