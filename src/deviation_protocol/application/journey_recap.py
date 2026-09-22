"""Disposable, version-exact same-Run reading projection. Never a state input."""
from dataclasses import dataclass

from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.session_content_registry import (
    SOURCE_CONTENT_IDENTITY, SOURCE_CONTENT_SHA256,
    DESTINATION_CONTENT_IDENTITY, DESTINATION_CONTENT_SHA256,
    ARCHIVE_CONTENT_IDENTITY, ARCHIVE_CONTENT_SHA256,
)

SCHEMA = "native-run-recap/v1"
LIMIT = 2000


@dataclass(frozen=True)
class FactCopy:
    fact_id: str
    value: object
    text: str
    invariant: bool = False
    ending_values: tuple[tuple[str, object], ...] = ()


# Public templates registered against immutable deployment identities. Boolean
# facts have no human-readable value in the packs; never stringify private keys.
# New packs require an explicit presentation registration, not a latest fallback.
from deviation_protocol.application.fog_station import CONTENT_IDENTITY as STATION_IDENTITY, CONTENT_SHA256 as STATION_SHA256


CONTENT_COPY = {
    (*STATION_IDENTITY, STATION_SHA256): (),
    (*SOURCE_CONTENT_IDENTITY, SOURCE_CONTENT_SHA256): (),
    (*DESTINATION_CONTENT_IDENTITY, DESTINATION_CONTENT_SHA256): (
        FactCopy("undelivered_receipt.fact.hold_is_not_delivery",
                 "暂缓发运不证明此前是否已经送达。", "暂缓发运不证明此前是否已经送达。", True),
        FactCopy("undelivered_receipt.fact.dispatch_held", True, "会签暂缓已生效；发运暂缓，送达仍未得到证明。",
                 ending_values=(("undelivered_receipt.ending.receipt_held", True),
                                ("undelivered_receipt.ending.dispatch_closed", False))),
    ),
    (*ARCHIVE_CONTENT_IDENTITY, ARCHIVE_CONTENT_SHA256): (
        FactCopy("receipt_archive.fact.hold_effective", True, "原有会签暂缓仍然有效。", True),
        FactCopy("receipt_archive.fact.delivery_unproven", True, "送达仍未得到证明。", True),
        FactCopy("receipt_archive.fact.unresolved_sealed", True, "未解决的待核记录已封存；封存不证明送达。",
                 ending_values=(("receipt_archive.ending.unresolved_sealed", True),
                                ("receipt_archive.ending.review_deferred", False))),
    ),
}


@dataclass(frozen=True)
class RecapSource:
    """Private provenance: retained through selection, never serialized publicly."""
    ordinal: int
    session_id: str
    session_version: int
    content_identity: tuple[str, str, str]
    snapshot_sha256: str
    definition: object
    runtime: object


def select_text(required: list[str], optional: list[str], *, optional_missing=False):
    """All separators count. Python len counts Unicode code points, including astral ones."""
    text = "\n\n".join(required)
    if len(text) > LIMIT:
        return "unavailable_overflow", ""
    incomplete = optional_missing
    for paragraph in optional:
        candidate = "\n\n".join(filter(None, (text, paragraph)))
        if len(candidate) <= LIMIT:
            text = candidate
        else:
            incomplete = True
    return "incomplete" if incomplete else "complete", text


def render_sources(sources: tuple[RecapSource, ...], lifecycle: str):
    consequences, visits, optional = [], [], []
    optional_missing = False
    for ordinal, source in enumerate(sources, 1):
        definition, runtime = source.definition, source.runtime
        if (source.ordinal != ordinal or (definition.scenario_id, definition.content_version) != source.content_identity[:2]):
            raise ValueError("source order/content mismatch")
        runtime.validate_against(definition)
        rules = CONTENT_COPY.get(source.content_identity)
        if rules is None or definition.public_client is None:
            raise ValueError("required registered copy missing")
        prefix = f"第 {source.ordinal} 次访问"
        for rule in rules:
            fact = next((f for f in definition.facts if f.fact_id == rule.fact_id), None)
            if fact is None or fact.visibility.value != "PLAYER_KNOWN":
                raise ValueError("required public fact missing")
            value = (fact.value if fact.kind.value == "FIXED" else
                     runtime.mutable_fact_values.get(fact.fact_id) if fact.kind.value == "MUTABLE" else
                     runtime.bound_deferred_facts.get(fact.fact_id))
            matches = type(value) is type(rule.value) and value == rule.value
            if rule.invariant and not matches:
                raise ValueError("required public fact contradicts content")
            for ending_id, expected in rule.ending_values:
                if runtime.ending_id == ending_id and (type(value) is not type(expected) or value != expected):
                    raise ValueError("ending contradicts required fact")
            if matches:
                consequences.append(f"{prefix}：{rule.text}")
        public = definition.public_client
        if runtime.ending_id is not None:
            ending = next((e for e in public.endings if e.ending_id == runtime.ending_id), None)
            if ending is None or runtime.ending_status.value not in ("RESOLVED", "FAILED"):
                raise ValueError("required ending missing")
            outcome = "已形成结果" if runtime.ending_status.value == "RESOLVED" else "以失败结果结束"
            visits.append(f"{prefix} · {public.title}（{outcome}）：{ending.title}。{ending.summary}")
        else:
            visits.append(f"{prefix} · {public.title}：访问尚未结束。")
        scene = next((s for s in public.scenes if s.phase_id == runtime.current_phase_id), None)
        if scene is None:
            optional_missing = True
        else:
            optional.append(f"{prefix}的公开场景：{scene.summary}")
    if lifecycle == "completed":
        visits.append("本次旅程正常完成，待核事项保留；完成不改写发运暂缓、送达未证明或封存事实。")
    elif lifecycle == "terminated":
        visits.append("本次旅程已明确终止；这不是正常完成。" if sources[-1].content_identity[:2] == STATION_IDENTITY
                      else "本次旅程已明确终止；这不是正常完成，也不表示核验已结案。")
    # Required facts and visits use canonical ordinal order; optional recent
    # scene copy uses descending ordinal. No timestamps/navigation ordering.
    return select_text(consequences + visits, list(reversed(optional)), optional_missing=optional_missing)


async def read_recap(service, principal, session_id):
    """One existing read UoW; no locks, writes, cache, Provider or memory projection."""
    authority = service.authority
    controller = await authority._controller(principal, session_id)
    async with authority.session_service.uow_factory() as uow:
        # Ownership/participation failures stay errors, never an empty other-Run recap.
        participation = await authority._target(uow, principal, session_id)
        owned = await uow.sessions.get_owned(session_id, principal.player_id)
        try:
            service.registry.for_session(owned.session)
        except ValueError:
            raise SnapshotInvalidError(session_id) from None
        checked, (family, _, persisted, _) = await service._read(uow, principal, session_id, controller)
        if checked != participation:
            raise SnapshotInvalidError(session_id)
        run = family.canonical_run
        refs = run.trusted_participation_references
        cutoff = next(i for i, ref in enumerate(refs, 1) if ref.session_id == session_id)
        historical = cutoff < len(refs)
        context = dict(run_id=run.run_id.value, run_state_version=run.state_version.value,
            session_state_version=persisted.session.state_version,
            scenario_id=persisted.session.scenario_id, content_version=persisted.session.scenario_version,
            cutoff_visit=cutoff, scope="historical" if historical else "current",
            lifecycle_at_cutoff="active" if historical else run.lifecycle_status.value)
        sources = []
        for ordinal, ref in enumerate(refs[:cutoff], 1):
            actual = await authority._target(uow, principal, ref.session_id)
            if actual != ref:
                raise SnapshotInvalidError(session_id)
            owned = await uow.sessions.get_owned(ref.session_id, principal.player_id)
            try:
                service.registry.for_session(owned.session)
            except ValueError:
                raise SnapshotInvalidError(session_id) from None
            checked, (same_family, _, owned, state) = await service._read(uow, principal, ref.session_id, controller)
            if checked != actual or same_family != family:
                raise SnapshotInvalidError(session_id)
            try:
                bundle = service.registry.for_session(owned.session)
            except ValueError:
                return dict(schema_version=SCHEMA, session_id=session_id, context=None,
                            status="unavailable_evidence", text="")
            if state.scenario_runtime is None:
                raise SnapshotInvalidError(session_id)
            sources.append(RecapSource(ordinal, ref.session_id, owned.session.state_version,
                (bundle.scenario_id, bundle.content_version, bundle.content_sha256),
                state_fingerprint(state), bundle.scenario_catalog.scenarios[0], state.scenario_runtime))
        # This immutable private binding accounts for all contributing versions;
        # the public context exposes only what Web needs to reconcile its View.
        binding = (SCHEMA, run.run_id.value, run.state_version.value, session_id,
                   persisted.session.state_version, tuple(sources))
        try:
            status, text = render_sources(binding[-1], context["lifecycle_at_cutoff"])
        except ValueError:
            status, text = "unavailable_evidence", ""
        return dict(schema_version=SCHEMA, session_id=session_id, context=context, status=status, text=text)
