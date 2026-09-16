import itertools
import json
import os
import subprocess
import sys

import pytest

from deviation_protocol.application.run_protocol_prompt_context import (
    compile_run_protocol_context, RunPromptContextError, CompiledRunProtocolContextV1,
)
from deviation_protocol.application.native_turn_mechanics import TrustedNativeTurnInputs, NativeMechanicsDecision
from tests.unit.test_native_turn_mechanics import fixture_inputs, execute

STANDARD = b'{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":60,"consequence_severity":65,"information_opacity":60,"resource_pressure":60,"social_trust":45},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"balanced"},"resource_pressure_label":"Fluid","schema":"run-prompt-context/v1","selected_result":"SUCCESS"}'
EASIER = b'{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":35,"consequence_severity":35,"information_opacity":30,"resource_pressure":25,"social_trust":70},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"balanced"},"resource_pressure_label":"Generous","schema":"run-prompt-context/v1","selected_result":"SUCCESS"}'
EXTREME = b'{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":90,"consequence_severity":90,"information_opacity":90,"resource_pressure":90,"social_trust":10},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"grim"},"resource_pressure_label":"Scarce","schema":"run-prompt-context/v1","selected_result":"AMBIGUOUS"}'


def test_extreme_override_literal_golden():
    f = fixture_inputs((90,10,90,90,90), ("grim", "lawful", "off"), quiet=True)
    assert compile_run_protocol_context(f.inputs, f.decision).data == EXTREME


@pytest.mark.parametrize("values,golden", [((60,45,65,60,60), STANDARD), ((25,70,35,30,35), EASIER)])
def test_literal_golden_repeat_and_closed_disclosure(values, golden):
    f = fixture_inputs(values)
    for _ in range(3):
        compiled = compile_run_protocol_context(f.inputs, f.decision)
        assert compiled.data == golden
        assert len(compiled.data) <= 1024 and not compiled.data.endswith(b"\n")
        assert set(compiled.validated_object()) == {"schema", "mechanics_version", "objectives", "presentation", "resource_pressure_label", "selected_result"}


@pytest.mark.parametrize("values", [(25,70,35,30,35), (60,45,65,60,60), (95,10,95,90,90)])
def test_all_presentations_have_identical_objective_state_events_and_results(values, monkeypatch):
    from deviation_protocol.application.narrative_prompt import PromptBuilder
    monkeypatch.setattr(PromptBuilder, "build", lambda *a: pytest.fail("mechanics used prompt"))
    expected = None
    for presentation in itertools.product(("grim", "balanced", "heroic"), ("lawful", "deviant", "chaotic"), ("off", "veiled", "charged")):
        f = fixture_inputs(values, presentation)
        for compile_on in (False, True):
            if compile_on:
                compile_run_protocol_context(f.inputs, f.decision)
            directed, events = execute(f)
            actual = (directed.candidate_state.to_snapshot(), events, f.decision.evidence())
            if expected is None:
                expected = actual
            assert actual == expected


@pytest.mark.parametrize("bad", [{}, "json", object.__new__(TrustedNativeTurnInputs)])
def test_forged_inputs_fail_before_fields(bad):
    f = fixture_inputs()
    with pytest.raises(RunPromptContextError, match="UNTRUSTED_INPUT"):
        compile_run_protocol_context(bad, f.decision)


@pytest.mark.parametrize("field", ["session_id", "run_id", "player_id", "turn_id", "action_signature", "continuous_story_line_id"])
def test_cross_binding_rejected(field):
    a, b = fixture_inputs(), fixture_inputs(**{field: "different"})
    with pytest.raises(RunPromptContextError, match="BINDING_MISMATCH"):
        compile_run_protocol_context(a.inputs, b.decision)


def test_stale_and_mutated_context_rejected():
    a, b = fixture_inputs(), fixture_inputs(state_version=1)
    with pytest.raises(RunPromptContextError, match="STALE_INPUT"):
        compile_run_protocol_context(a.inputs, b.decision)
    compiled = compile_run_protocol_context(a.inputs, a.decision)
    object.__setattr__(compiled, "data", b'{}')
    with pytest.raises(RunPromptContextError, match="INVALID_VALUE"):
        compiled.validated_object()


def test_process_hash_seed_and_locale_stability():
    script = "import locale; from tests.unit.test_native_turn_mechanics import fixture_inputs; from deviation_protocol.application.run_protocol_prompt_context import compile_run_protocol_context; locale.setlocale(locale.LC_ALL, 'C'); f=fixture_inputs(); print(compile_run_protocol_context(f.inputs,f.decision).data.decode())"
    for seed in ("1", "9281"):
        env = os.environ.copy()
        for key in ("DATABASE_URL", "TEST_DATABASE_URL", "DEEPSEEK_API_KEY", "RUN_LIVE_DEEPSEEK_TEST"):
            env.pop(key, None)
        env["PYTHONHASHSEED"] = seed
        result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, check=True)
        assert result.stdout.strip() == STANDARD


def test_available_locales_and_no_io(monkeypatch):
    import builtins
    import locale
    import random
    import socket
    import time
    f = fixture_inputs()
    saved = locale.setlocale(locale.LC_ALL)
    try:
        for candidate in ("C", "English_United States.1252", "Chinese_China.936", "Turkish_Turkey.1254"):
            try:
                locale.setlocale(locale.LC_ALL, candidate)
            except locale.Error:
                print("S5_LOCALE_UNAVAILABLE", candidate)
                continue
            assert compile_run_protocol_context(f.inputs, f.decision).data == STANDARD
            print("S5_LOCALE_VERIFIED", candidate)
    finally:
        locale.setlocale(locale.LC_ALL, saved)
    def forbidden(*a, **kw):
        pytest.fail("compiler attempted I/O, clock or randomness")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins,"open"),(os,"open"),(socket,"socket"),(time,"time"),(random,"random")):
            patch.setattr(owner, name, forbidden)
        assert compile_run_protocol_context(f.inputs, f.decision).data == STANDARD


@pytest.mark.parametrize("value,label", [(30,"Generous"),(35,"Fluid"),(65,"Fluid"),(70,"Scarce")])
def test_exact_projection_and_mapping_order(value, label):
    f = fixture_inputs((value,45,65,60,60))
    expected = compile_run_protocol_context(f.inputs, f.decision).data
    # Canonical encoding ignores mapping insertion order, including the private binding.
    from deviation_protocol.application.native_turn_mechanics import canonical
    binding = json.loads(f.inputs.binding_bytes)
    assert canonical(dict(reversed(list(binding.items())))) == f.inputs.binding_bytes
    output = json.loads(expected)
    assert output["resource_pressure_label"] == label and output["objectives"]["resource_pressure"] == value


def test_size_guard_and_forged_decision_are_closed(monkeypatch):
    from deviation_protocol.application import run_protocol_prompt_context as compiler
    f = fixture_inputs()
    with pytest.raises(RunPromptContextError, match="UNTRUSTED_INPUT"):
        compile_run_protocol_context(f.inputs, object.__new__(NativeMechanicsDecision))
    monkeypatch.setattr(compiler, "MAX_CONTEXT_BYTES", 1)
    with pytest.raises(RunPromptContextError, match="SIZE_LIMIT"):
        compile_run_protocol_context(f.inputs, f.decision)
