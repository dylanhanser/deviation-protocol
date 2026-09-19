"""Bounded visit annotation, separate from unchanged run-prompt-context/v1."""
from dataclasses import dataclass
import json

from deviation_protocol.application.native_turn_mechanics import TrustedNativeTurnInputs,NativeMechanicsDecision,canonical
from deviation_protocol.application.run_protocol_prompt_context import RunPromptContextError
from deviation_protocol.domain.run import revalidate_run_model
from deviation_protocol.domain.run_protocol_binding import NativeRunContinuedV1

_DETACHED = object()
_COMPILED = object()
ENTRY_NOTICES = {
    "RESOLVED":"上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。",
    "FAILED":"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。",
}
ENDING_TITLES = {
    "death_certificate.ending.protocol_broken":"规程已中断",
    "death_certificate.ending.record_challenged":"记录已被质疑",
    "death_certificate.ending.deadline_reached":"记录成为现实",
}


def project_world_arrival(family):
    """Allowlisted public annotation after the owned family is reconstructed.

    This is distinct from the private turn attachment and contains no root or
    historical memory. The evidence binds the actual ending and entry variant.
    """
    revalidate_run_model(family, NativeRunContinuedV1)
    evidence = family.continuation_evidence
    ending = evidence.source_ending
    if evidence.entry_variant != ending.ending_status.lower():
        raise ValueError("arrival variant mismatch")
    return dict(previous_ending_status=ending.ending_status,
        previous_ending_title=ENDING_TITLES[ending.ending_id],
        entry_notice=ENTRY_NOTICES[ending.ending_status])


@dataclass(frozen=True,slots=True,init=False)
class DetachedWorldVisitEvidence:
    binding: bytes
    snapshot: bytes
    ending_id: str
    ending_status: str
    _seal: object
    _original: tuple

    def authentic(self):
        return (getattr(self,"_seal",None) is _DETACHED
            and self._original == (self.binding,self.snapshot,self.ending_id,self.ending_status))


def detach_world_visit_evidence(family,inputs):
    if type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic():
        raise RunPromptContextError("UNTRUSTED_INPUT")
    revalidate_run_model(family,NativeRunContinuedV1)
    binding = json.loads(inputs.binding_bytes)
    if (binding.get("run_revision") != 4 or binding.get("visit_id") != family.position.visit_id
            or binding.get("session_id") != family.position.session_id
            or binding.get("continuation_fingerprint") != family.continuation_evidence.request.fingerprint()):
        raise RunPromptContextError("BINDING_MISMATCH")
    ending = family.continuation_evidence.source_ending
    result = object.__new__(DetachedWorldVisitEvidence)
    fields=(inputs.binding_bytes,inputs.snapshot_bytes,ending.ending_id,ending.ending_status)
    for key,value in zip(("binding","snapshot","ending_id","ending_status"),fields):
        object.__setattr__(result,key,value)
    object.__setattr__(result,"_seal",_DETACHED)
    object.__setattr__(result,"_original",fields)
    return result


@dataclass(frozen=True,slots=True,init=False)
class CompiledWorldVisitContextV1:
    data: bytes
    _seal: object
    _original: bytes

    def validated_object(self):
        if getattr(self,"_seal",None) is not _COMPILED:
            raise RunPromptContextError("UNTRUSTED_INPUT")
        if type(self.data) is not bytes or self.data != self._original or len(self.data)>2048:
            raise RunPromptContextError("INVALID_VALUE")
        return json.loads(self.data)


def compile_world_visit_context(evidence,inputs,decision):
    if (type(evidence) is not DetachedWorldVisitEvidence or not evidence.authentic()
            or type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic()
            or type(decision) is not NativeMechanicsDecision or not decision.is_authentic()):
        raise RunPromptContextError("UNTRUSTED_INPUT")
    if (evidence.binding != inputs.binding_bytes or inputs.binding_bytes != decision.inputs.binding_bytes
            or evidence.snapshot != inputs.snapshot_bytes or inputs.snapshot_bytes != decision.inputs.snapshot_bytes):
        raise RunPromptContextError("BINDING_MISMATCH")
    obj=dict(schema="world-visit-prompt-context/v1",world_title="未送达的回执",region_title="发运大厅",
        visit_ordinal=2,previous_ending_status=evidence.ending_status,
        previous_ending_title=ENDING_TITLES[evidence.ending_id],entry_notice=ENTRY_NOTICES[evidence.ending_status])
    if any(len(obj[k])>120 for k in ("world_title","region_title","previous_ending_title")) or len(obj["entry_notice"])>300:
        raise RunPromptContextError("SIZE_LIMIT")
    data=canonical(obj)
    if len(data)>2048:
        raise RunPromptContextError("SIZE_LIMIT")
    result=object.__new__(CompiledWorldVisitContextV1)
    for key,value in (("data",data),("_original",data),("_seal",_COMPILED)):
        object.__setattr__(result,key,value)
    return result


from deviation_protocol.domain.run_protocol_binding import NativeRunRegionalRevisitV1
from deviation_protocol.domain.world_revisit import ARCHIVE_NOTICE


@dataclass(frozen=True,slots=True,init=False)
class DetachedRegionalVisitEvidence:
    binding: bytes
    snapshot: bytes
    ending_id: str
    ending_status: str
    base_snapshot_sha256: str
    entry_sha256: str
    receipt_evidence_sha256: str
    _seal: object
    _original: tuple

    def authentic(self):
        return (getattr(self,"_seal",None) is _DETACHED
            and self._original == (self.binding,self.snapshot,self.ending_id,self.ending_status,
                self.base_snapshot_sha256,self.entry_sha256,self.receipt_evidence_sha256))


def detach_regional_visit_evidence(family,inputs):
    if type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic():
        raise RunPromptContextError("UNTRUSTED_INPUT")
    revalidate_run_model(family,NativeRunRegionalRevisitV1)
    binding = json.loads(inputs.binding_bytes)
    if (binding.get("run_revision") != 5 or binding.get("visit_id") != family.position.visit_id
            or binding.get("session_id") != family.position.session_id
            or binding.get("regional_entry_fingerprint") != family.revisit_evidence.request.fingerprint()):
        raise RunPromptContextError("BINDING_MISMATCH")
    ending = family.revisit_evidence.source_ending
    result = object.__new__(DetachedRegionalVisitEvidence)
    import hashlib
    from deviation_protocol.domain.run import canonical_run_operation_bytes
    fields=(inputs.binding_bytes,inputs.snapshot_bytes,ending.ending_id,ending.ending_status,
        family.entry.base_snapshot_sha256,family.entry.digest(),
        hashlib.sha256(canonical_run_operation_bytes(family.revisit_evidence)).hexdigest())
    for key,value in zip(("binding","snapshot","ending_id","ending_status",
                          "base_snapshot_sha256","entry_sha256","receipt_evidence_sha256"),fields):
        object.__setattr__(result,key,value)
    object.__setattr__(result,"_seal",_DETACHED)
    object.__setattr__(result,"_original",fields)
    return result


@dataclass(frozen=True,slots=True,init=False)
class CompiledRegionalVisitContextV1:
    data: bytes
    _seal: object
    _original: bytes

    def validated_object(self):
        if getattr(self,"_seal",None) is not _COMPILED:
            raise RunPromptContextError("UNTRUSTED_INPUT")
        if type(self.data) is not bytes or self.data != self._original or len(self.data)>2048:
            raise RunPromptContextError("INVALID_VALUE")
        return json.loads(self.data)


def compile_regional_visit_context(evidence,inputs,decision):
    if (type(evidence) is not DetachedRegionalVisitEvidence or not evidence.authentic()
            or type(inputs) is not TrustedNativeTurnInputs or not inputs.is_authentic()
            or type(decision) is not NativeMechanicsDecision or not decision.is_authentic()):
        raise RunPromptContextError("UNTRUSTED_INPUT")
    if (evidence.binding != inputs.binding_bytes or inputs.binding_bytes != decision.inputs.binding_bytes
            or evidence.snapshot != inputs.snapshot_bytes or inputs.snapshot_bytes != decision.inputs.snapshot_bytes):
        raise RunPromptContextError("BINDING_MISMATCH")
    obj=dict(schema="world-regional-prompt-context/v1",world_title="未送达的回执",region_title="核验档案室",
        visit_ordinal=3,previous_ending_status=evidence.ending_status,
        previous_ending_title="回执待核，发运暂缓",entry_notice=ARCHIVE_NOTICE)
    if any(len(obj[k])>120 for k in ("world_title","region_title","previous_ending_title")) or len(obj["entry_notice"])>300:
        raise RunPromptContextError("SIZE_LIMIT")
    data=canonical(obj)
    if len(data)>2048:
        raise RunPromptContextError("SIZE_LIMIT")
    result=object.__new__(CompiledRegionalVisitContextV1)
    for key,value in (("data",data),("_original",data),("_seal",_COMPILED)):
        object.__setattr__(result,key,value)
    return result
