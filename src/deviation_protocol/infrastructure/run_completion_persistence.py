"""Completion suffix validation; never decode completion bytes as exit evidence."""
from datetime import datetime

from deviation_protocol.application.run_completion_service import (
    completion_evidence, validated_completion_decision,
)
from deviation_protocol.domain.run_completion import (
    RunCompletionEligibilityPolicy, decode_native_run_completion_evidence,
)
from deviation_protocol.domain.run_protocol_binding import NativeRunRegionalCompletedV1
from deviation_protocol.infrastructure.run_protocol_binding_persistence import _require


def validate_sealed_archive(prefix, state, events):
    if state.scenario_runtime.ending_id == "receipt_archive.ending.unresolved_sealed":
        _require(RunCompletionEligibilityPolicy().qualifies(state), "sealed archive facts contradict ending")
        validated_completion_decision(prefix.visit.session_id, state, events, seal=True)


def reconstruct_completed_suffix(*, prefix, run, receipt, states, versions, event_sets, registry):
    evidence = decode_native_run_completion_evidence(receipt.operation_evidence_canonical)
    expected = completion_evidence(prefix=prefix, request=evidence.request, states=states,
        versions=versions, event_sets=event_sets, registry=registry,
        occurred_at=datetime.fromisoformat(evidence.occurred_at.replace("Z", "+00:00")))
    _require(evidence == expected, "completion source/decision/transition association")
    return NativeRunRegionalCompletedV1(revisited=prefix, canonical_run=run, completion_evidence=evidence)

async def require_completion_schema(session):
    """Check the deployed writer contract while the native physical lock is held."""
    from sqlalchemy import text
    from deviation_protocol.infrastructure.orm_models import Base
    from deviation_protocol.infrastructure.run_persistence import RunStoredRecordIntegrityError

    head = await session.scalar(text("SELECT version_num FROM alembic_version FOR UPDATE"))
    if head != "20260920_0011":
        raise RunStoredRecordIntegrityError("completion requires deployed schema 011")
    for table in ("run_current", "run_revisions", "run_mutation_receipts"):
        expected = next(c for c in Base.metadata.tables[table].constraints
                        if hasattr(c, "sqltext") and "COMPLETE_REVISITED_NATIVE_RUN" in str(c.sqltext))
        row = (await session.execute(text("""SELECT cc.CHECK_CLAUSE, tc.ENFORCED
            FROM information_schema.CHECK_CONSTRAINTS cc
            JOIN information_schema.TABLE_CONSTRAINTS tc
              ON tc.CONSTRAINT_SCHEMA=cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME=cc.CONSTRAINT_NAME
            WHERE cc.CONSTRAINT_SCHEMA=DATABASE() AND tc.TABLE_NAME=:table AND cc.CONSTRAINT_NAME=:name"""),
            {"table": table, "name": expected.name})).one_or_none()
        if row is None or row[1] != "YES" or completion_check_expression(row[0]) != completion_check_expression(str(expected.sqltext)):
            raise RunStoredRecordIntegrityError("completion schema constraint mismatch")


def completion_check_expression(value):
    import re
    # MySQL adds redundant parentheses/backticks and character introducers.
    # Parse boolean structure rather than deleting meaningful grouping.
    value = value.replace("\\'", "'")
    value = re.sub(r"(`?[A-Za-z_][A-Za-z_0-9]*`?)\s+REGEXP\s+('(?:''|[^'])*')",
                   r"REGEXP_LIKE(\1,\2)", value, flags=re.IGNORECASE)
    tokens = re.findall(r"'(?:''|[^'])*'|`[^`]*`|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|>=|<=|<>|!=|[^\s]", value)
    tokens = [t if t.startswith("'") else t.strip('`').upper() for t in tokens]
    tokens = [t for t in tokens if t not in ('_ASCII', '_UTF8MB4', '_UTF8MB3', '_UTF8')]
    tokens = ['LENGTH' if t == 'OCTET_LENGTH' else t for t in tokens]
    for index in range(len(tokens)-5,-1,-1):
        if (tokens[index] == '(' and re.fullmatch(r'[A-Z_][A-Z_0-9]*', tokens[index+1])
                and tokens[index+2] in ('+', '-') and tokens[index+3].isdigit() and tokens[index+4] == ')'):
            tokens[index:index+5] = tokens[index+1:index+4]
    def parse(items):
        while items and items[0] == '(':
            depth = 0
            for index, token in enumerate(items):
                depth += (token == '(') - (token == ')')
                if depth == 0: break
            if index != len(items) - 1: break
            items = items[1:-1]
        for separator in ('OR', 'AND'):
            depth = 0; between = False; start = 0; groups = []
            for index, token in enumerate(items):
                depth += (token == '(') - (token == ')')
                if depth: continue
                if token == 'BETWEEN': between = True
                elif token == 'AND' and between: between = False
                elif token == separator:
                    groups.append(parse(items[start:index])); start = index + 1
            if groups:
                groups.append(parse(items[start:]))
                flattened = []
                for group in groups:
                    if group and group[0] == separator: flattened.extend(group[1:])
                    else: flattened.append(group)
                return (separator, *flattened)
        return ('ATOM', *items)
    return parse(tokens)
