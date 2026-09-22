"""Committed source verification; absence of an activity is not missing evidence."""
from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.application.fog_station import FogStationPolicy, ACTIVITIES
from deviation_protocol.domain.fog_patrol import SOURCE, SOURCE_HASH, ENDINGS


def event_records(events):
    return tuple(dict(session_id=e.session_id, event_id=e.event_id, sequence_no=e.sequence_no,
        event_type=e.event_type, payload=e.payload) for e in events)


def verify_history(bundle, state, session_id, version, records):
    """Caller obtains the complete event stream from its owned, locked repository.

    Also used against the sealed stream on reads. No names, recap or NPC memory
    indices participate in this proof.
    """
    try:
        if (bundle.scenario_id, bundle.content_version, bundle.content_sha256) != (*SOURCE, SOURCE_HASH):
            raise ValueError("source content")
        state = bundle.validate_snapshot(state.to_snapshot())
        codes = FogStationPolicy().validate(state, session_id, bundle.scenario_catalog.scenarios[0])
        r = state.scenario_runtime
        if version != len(codes) or r.ending_id not in ENDINGS or r.ending_status.value != "RESOLVED":
            raise ValueError("source ending")
        ids, sequences = set(), set()
        for e in records:
            if (set(e) != {"session_id", "event_id", "sequence_no", "event_type", "payload"}
                    or e["session_id"] != session_id or type(e["event_id"]) is not str
                    or not 1 <= len(e["event_id"]) <= 64 or type(e["event_type"]) is not str
                    or type(e["payload"]) is not dict or type(e["sequence_no"]) is not int
                    or e["sequence_no"] < 1 or e["sequence_no"] in sequences or e["event_id"] in ids):
                raise ValueError("event identity")
            ids.add(e["event_id"])
            sequences.add(e["sequence_no"])
        if [e["sequence_no"] for e in records] != list(range(1, len(records) + 1)):
            raise ValueError("event stream order/gap")
        started = [e for e in records if e["event_type"] == "ScenarioStarted"]
        if len(started) != 1 or started[0]["sequence_no"] != 1 or started[0]["payload"] != {
                "scenario_id": SOURCE[0], "scenario_content_version": SOURCE[1]}:
            raise ValueError("initial event")
        decisions = [e for e in records if e["event_type"] == "ScenarioDecisionSelected"]
        if len(decisions) != len(codes):
            raise ValueError("missing/extra decision")
        applied = []
        outcomes = {e.decision_id: e for e in r.decision_outcome_evidence}
        for e, decision_id in zip(decisions, r.decisions_made):
            outcome = outcomes[decision_id]
            payload = e["payload"]
            action = next(a for d in bundle.scenario_catalog.scenarios[0].decision_windows
                if d.decision_id == decision_id for a in d.suggested_actions
                if a.server_event_type == outcome.scenario_event_type)
            if (payload.get("decision_id") != decision_id or outcome.decision_id != decision_id
                    or payload.get("scenario_event_type") != outcome.scenario_event_type
                    or payload.get("selected_action_id") != action.action_id
                    or payload.get("selected_action_type") != "choose"
                    or payload.get("source") != "VALIDATED_DECISION_RESPONSE"):
                raise ValueError("contradictory decision")
            applied.append(payload.get("scenario_event_id"))
        if len(set(applied)) != len(applied) or set(applied) != set(r.applied_event_ids):
            raise ValueError("event/runtime mismatch")
        memory = state.player_memory
        if len(memory.scenario_records) != 1:
            raise ValueError("source memory")
        record, last = memory.scenario_records[0], decisions[-1]
        if (record.status.value != "COMPLETED" or record.ending_id != r.ending_id
                or record.scenario_id != SOURCE[0] or record.scenario_content_version != SOURCE[1]
                or record.last_source_event_id != last["event_id"]
                or record.last_source_sequence_no != last["sequence_no"]
                or memory.last_applied_source_event_id != last["event_id"]
                or memory.last_applied_source_sequence_no != last["sequence_no"]):
            raise ValueError("completion evidence")
        return codes
    except (TypeError, ValueError, KeyError, AttributeError, IndexError, StopIteration):
        raise SnapshotInvalidError(session_id) from None


def previous_visit_text(codes):
    """At most two actual experiences, with accurate stay/early-departure wording."""
    first = "岑舟提起上次在雾哨站与你一起固定挡板的事。"
    if "finish_work" not in codes:
        second = "那次险情平息后你便离开了；他没有把短暂的合作说成深交。"
    elif "decline" in codes:
        second = "他还记得你谢绝了暂住，只点头致意，没有再劝你留下。"
    else:
        activities = [c.split("_")[0] for c in codes if c.split("_")[0] in ACTIVITIES]
        if activities:
            second = {"review": "他想起暂住时与你复盘脱险的那一刻，随后指了指正在晃动的灯架。",
                "story": "他想起暂住时给你讲过的那段巡路往事：今天的风口也不太安稳。",
                "records": "他想起暂住时与你一起整理观察记录的情景，向你示意站到背风处。"}[activities[0]]
        else:
            second = "上次你短暂停留便离开，没有一起做过暂住活动。他给你让出路边的位置。"
    return "上次访问的回响：" + first + second
