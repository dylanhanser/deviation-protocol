import pytest

from deviation_protocol.domain.run_protocol_mechanics import (
    ResourcePressurePolicy, SocialTrustPolicy, ConsequenceSeverityPolicy,
    InformationOpacityPolicy, ConflictIntensityPolicy, clock_plan, resource_pressure_label,
)
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult as Result


@pytest.mark.parametrize("value", range(0, 101, 5))
def test_all_lattice_points_against_independent_arithmetic(value):
    expected = 0 if value < 50 else 1 if value < 100 else 2
    for current in (0, 1, 2, 6):
        plan = ResourcePressurePolicy().plan(value, resource_id="composure", current=current, maximum=6, narrative=True)
        assert plan.requested == expected
        assert plan.actual == min(current, expected)
        assert plan.after == max(0, current - expected)
        assert ResourcePressurePolicy().plan(value, resource_id="composure", current=current, maximum=6, narrative=False).actual == 0
    trust = 2 if value == 0 else 1 if value <= 50 else 0
    assert SocialTrustPolicy().extra(value, qualifying_talk=True) == trust
    assert SocialTrustPolicy().extra(value, qualifying_talk=False) == 0
    for result in (*Result, None):
        assert ConsequenceSeverityPolicy().extra(value, result=result) == (expected if result in (Result.FAILURE, Result.AMBIGUOUS, Result.NO_EFFECT) else 0)
    assert InformationOpacityPolicy().extra(value, discovers=True) == expected
    assert InformationOpacityPolicy().extra(value, discovers=False) == 0
    assert ConflictIntensityPolicy().extra(value) == expected


@pytest.mark.parametrize("value", [True, False, 50.0, "50", -5, 105, 51, None])
def test_invalid_objectives_fail(value):
    for invoke in (lambda: ResourcePressurePolicy().plan(value, resource_id="x", current=6, maximum=6, narrative=True),
                   lambda: SocialTrustPolicy().extra(value, qualifying_talk=False),
                   lambda: ConsequenceSeverityPolicy().extra(value, result=None),
                   lambda: InformationOpacityPolicy().extra(value, discovers=False),
                   lambda: ConflictIntensityPolicy().extra(value)):
        with pytest.raises(ValueError):
            invoke()


def test_additive_components_bounds_and_saturation():
    a = clock_plan("deadline", 2, 6, 1, 1, 0, 1, 1)
    assert (a.base, a.social, a.severity, a.opacity, a.conflict, a.amount, a.after) == (1, 1, 0, 1, 1, 4, 6)
    b = clock_plan("deadline", 5, 6, 1, 1, 1, 0, 1)
    assert b.amount == 4 and b.after == 6
    assert clock_plan("max", 0, 1000000, 1000000, 2, 2, 2, 2).amount == 1000008
    with pytest.raises(ValueError):
        clock_plan("bad", 0, 6, 0, 0, 0, 0, 0)
    for value, label in ((0, "Generous"), (30, "Generous"), (35, "Fluid"), (65, "Fluid"), (70, "Scarce"), (100, "Scarce")):
        assert resource_pressure_label(value) == label
