"""Side-effect-free, closed native context compiler. Text never grants authority."""
from __future__ import annotations

from dataclasses import dataclass
import json

from deviation_protocol.application.native_turn_mechanics import (
    TrustedNativeTurnInputs, NativeMechanicsDecision, canonical,
)
from deviation_protocol.domain.run_protocol_mechanics import (
    MECHANICS_VERSION, OBJECTIVES, pressure, resource_pressure_label,
)

_COMPILER = object()
MAX_CONTEXT_BYTES = 1024
PRESENTATION = ("world_tone", "reality_boundary", "relationship_overlay")
ENUMS = (("grim", "balanced", "heroic"), ("lawful", "deviant", "chaotic"),
         ("off", "veiled", "charged"))


class RunPromptContextError(ValueError):
    def __init__(self, reason: str):
        if reason not in {"UNTRUSTED_INPUT", "BINDING_MISMATCH", "STALE_INPUT", "INVALID_VALUE", "SIZE_LIMIT"}:
            raise ValueError("invalid compiler error reason")
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True, init=False)
class CompiledRunProtocolContextV1:
    data: bytes
    _authority: object
    _original: bytes

    def validated_object(self) -> dict:
        if getattr(self, "_authority", None) is not _COMPILER:
            raise RunPromptContextError("UNTRUSTED_INPUT")
        if type(self.data) is not bytes or self.data != self._original:
            raise RunPromptContextError("INVALID_VALUE")
        if len(self.data) > MAX_CONTEXT_BYTES:
            raise RunPromptContextError("SIZE_LIMIT")
        return json.loads(self.data)


def compile_run_protocol_context(inputs: TrustedNativeTurnInputs,
                                 decision: NativeMechanicsDecision) -> CompiledRunProtocolContextV1:
    # Authenticate both before reading any binding or projection field.
    if (type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic()
            or type(decision) is not NativeMechanicsDecision or not decision.is_authentic()):
        raise RunPromptContextError("UNTRUSTED_INPUT")
    left, right = json.loads(inputs.binding_bytes), json.loads(decision.inputs.binding_bytes)
    stale_fields = {"state_version", "state_fingerprint", "frame_digest"}
    if any(left[k] != right[k] for k in left.keys() - stale_fields):
        raise RunPromptContextError("BINDING_MISMATCH")
    if left != right or inputs.snapshot_bytes != decision.inputs.snapshot_bytes:
        raise RunPromptContextError("STALE_INPUT")
    if inputs.objectives != decision.inputs.objectives or inputs.presentation != decision.inputs.presentation:
        raise RunPromptContextError("INVALID_VALUE")
    if decision.selected_result is None or left["mechanics_version"] != MECHANICS_VERSION:
        raise RunPromptContextError("INVALID_VALUE")
    for value in inputs.objectives:
        try:
            pressure(value)
        except ValueError:
            raise RunPromptContextError("INVALID_VALUE") from None
    if len(inputs.objectives) != 5 or len(inputs.presentation) != 3 or any(
        type(value) is not str or value not in allowed for value, allowed in zip(inputs.presentation, ENUMS)
    ):
        raise RunPromptContextError("INVALID_VALUE")
    data = canonical({"schema": "run-prompt-context/v1", "mechanics_version": MECHANICS_VERSION,
        "objectives": dict(zip(OBJECTIVES, inputs.objectives)),
        "presentation": dict(zip(PRESENTATION, inputs.presentation)),
        "resource_pressure_label": resource_pressure_label(inputs.objectives[0]),
        "selected_result": decision.selected_result.value})
    if len(data) > MAX_CONTEXT_BYTES:
        raise RunPromptContextError("SIZE_LIMIT")
    result = object.__new__(CompiledRunProtocolContextV1)
    for name, value in (("data", data), ("_authority", _COMPILER), ("_original", data)):
        object.__setattr__(result, name, value)
    return result
