"""Admit only the closed Fog Station patrol root and second-visit entry.

Revision ID: 20260922_0013
Revises: 20260921_0012
"""
from contextlib import contextmanager
import re

from alembic import op
import sqlalchemy as sa

revision = "20260922_0013"
down_revision = "20260921_0012"
branch_labels = None
depends_on = None

OLD = {
    "run_world_states": {"ck_run_world_states_schema": "state_schema = 'run-world-state/v1'"},
    "run_world_visit_entries": {
        "ck_run_world_visit_entries_version": "joined_state_version = 5",
        "ck_run_world_visit_entries_schema": "entry_schema = 'run-regional-entry/v1'",
    },
}
NEW = {
    "run_world_states": {"ck_run_world_states_schema": "state_schema IN ('run-world-state/v1', 'fog-world-state/v1')"},
    "run_world_visit_entries": {
        "ck_run_world_visit_entries_version": "(entry_schema = 'run-regional-entry/v1' AND joined_state_version = 5) OR (entry_schema = 'fog-patrol-entry/v1' AND joined_state_version = 4)",
        "ck_run_world_visit_entries_schema": "entry_schema IN ('run-regional-entry/v1', 'fog-patrol-entry/v1')",
    },
}
LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"


@contextmanager
def _locked():
    connection = op.get_bind()
    # A failed statement can still have acquired the server-side named lock.
    # Never return such an owner to the pool; preserve the primary error.
    try:
        acquired = connection.execute(sa.text("SELECT GET_LOCK(:name, 30)"), {"name": LOCK}).scalar_one()
        if type(acquired) is not int or acquired != 1:
            raise RuntimeError("Could not lock native admission for patrol migration")
    except BaseException as error:
        _discard(connection, error)
        raise
    primary = None
    try:
        yield connection
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            released = connection.execute(sa.text("SELECT RELEASE_LOCK(:name)"), {"name": LOCK}).scalar_one()
            if type(released) is not int or released != 1:
                raise RuntimeError("Could not release patrol migration lock")
        except BaseException as cleanup:
            _discard(connection, cleanup)
            if primary is not None:
                primary.cleanup_error = cleanup
            else:
                raise


def _discard(connection, selected):
    def record(error):
        if not hasattr(selected, "close_error"):
            selected.close_error = error
        else:
            selected.disposal_errors = getattr(selected, "disposal_errors", ()) + (error,)

    pool_connection = driver = None
    try:
        # Alembic runs this synchronous Connection inside run_sync. Retain both
        # handles before invalidation/detach can erase access to the asyncmy owner;
        # never acquire a replacement through an invalidated Connection.
        if not connection.closed and not connection.invalidated:
            pool_connection = connection.connection
            driver = pool_connection.driver_connection
    except BaseException as error:
        record(error)
    invalidation_failed = False
    try:
        connection.invalidate()
    except BaseException as error:
        invalidation_failed = True
        record(error)
        if pool_connection is not None:
            try:
                # Remove the owner from reusable circulation before trying any
                # physical close, including when that close itself fails.
                pool_connection.detach()
            except BaseException as error:
                record(error)
    if driver is not None:
        try:
            # asyncmy.Connection.close() closes the transport synchronously;
            # adapter.close() instead awaits graceful I/O through the greenlet.
            driver.close()
        except BaseException as error:
            record(error)
    if invalidation_failed and pool_connection is not None:
        try:
            # Invalidate the detached proxy so wrapper close cannot attempt a
            # transaction rollback on the terminated driver. This alone proves
            # neither physical termination nor server-side named-lock release.
            pool_connection.invalidate()
        except BaseException as error:
            record(error)
    try:
        connection.close()
    except BaseException as error:
        record(error)

def _normalize(value):
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


def _check(connection, expected):
    inspector = sa.inspect(connection)
    for table, checks in expected.items():
        actual = {row["name"]: row["sqltext"] for row in inspector.get_check_constraints(table)}
        for name, sql in checks.items():
            if name not in actual or _normalize(actual[name]) != _normalize(sql):
                raise RuntimeError("Patrol migration CHECK precondition mismatch; operator inspection required")
            enforced = connection.execute(sa.text("SELECT ENFORCED FROM information_schema.TABLE_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA=DATABASE() AND TABLE_NAME=:table AND CONSTRAINT_NAME=:name"),
                {"table": table, "name": name}).scalar_one()
            if enforced != "YES":
                raise RuntimeError("Patrol migration requires enforced CHECK constraints")


def _alter(connection, table, checks):
    # One atomic MySQL ALTER per table, retaining enforcement throughout.
    parts = []
    for name, sql in checks.items():
        parts.extend((f"DROP CHECK `{name}`", f"ADD CONSTRAINT `{name}` CHECK ({sql})"))
    connection.execute(sa.text(f"ALTER TABLE `{table}` " + ", ".join(parts)))


def _change(connection, before, after):
    _check(connection, before)
    changed = []
    try:
        for table, checks in after.items():
            _alter(connection, table, checks)
            changed.append(table)
        _check(connection, after)
    except BaseException as primary:
        # MySQL DDL commits statement by statement. Restore only changes this
        # invocation completed; never erase data or disable FK/CHECK enforcement.
        primary.completed_tables = tuple(changed)
        try:
            for table in reversed(changed):
                _alter(connection, table, before[table])
            _check(connection, before)
        except BaseException as restoration_error:
            primary.restoration_error = restoration_error
        raise


def upgrade():
    with _locked() as connection:
        _change(connection, OLD, NEW)


def downgrade():
    with _locked() as connection:
        _check(connection, NEW)
        for table, predicate in (
                ("run_world_states", "state_schema <> 'run-world-state/v1'"),
                ("run_world_visit_entries", "entry_schema <> 'run-regional-entry/v1' OR joined_state_version <> 5")):
            if connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}` WHERE {predicate}")).scalar_one():
                raise RuntimeError("Patrol evidence exists; downgrade requires operator inspection")
        _change(connection, NEW, OLD)
