"""Admit only the exact native Run termination suffix; preserve all old branches."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError

revision = "20260917_0008"
down_revision = "20260916_0007"
branch_labels = None
depends_on = None
_LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"
_REFUSAL = "Refusing native Run exit downgrade: terminal evidence exists"

_CONSTRAINTS = (('run_revisions', 'ck_run_revisions_mutation_matrix', "(mutation_kind = 'CREATE' AND state_version = 1 AND prior_state_version IS NULL AND creation_operation_id = operation_id AND creation_source_reference = source_reference AND creation_occurred_at = occurred_at) OR (mutation_kind IN ('ATTACH_SESSION', 'BIND_PLAYER_CHARACTER') AND state_version BETWEEN 2 AND 9223372036854775807 AND prior_state_version = state_version - 1)", "(mutation_kind = 'CREATE' AND state_version = 1 AND prior_state_version IS NULL AND creation_operation_id = operation_id AND creation_source_reference = source_reference AND creation_occurred_at = occurred_at) OR (mutation_kind IN ('ATTACH_SESSION', 'BIND_PLAYER_CHARACTER') AND state_version BETWEEN 2 AND 9223372036854775807 AND prior_state_version = state_version - 1) OR (mutation_kind = 'TERMINATE_NATIVE_RUN' AND prior_state_version IS NOT NULL AND prior_state_version = 3 AND state_version = 4 AND lifecycle_status = 'terminated' AND binding_player_character_id IS NOT NULL AND binding_contract_version IS NOT NULL AND binding_record_revision IS NOT NULL AND binding_state IS NOT NULL AND binding_state = 'historical' AND binding_operation_id IS NOT NULL AND binding_authority_source_ref IS NOT NULL AND bound_at IS NOT NULL AND inactivated_at IS NOT NULL AND inactivated_at = occurred_at AND occurred_at >= bound_at)"), ('run_current', 'ck_run_current_mutation_matrix', "(mutation_kind = 'CREATE' AND state_version = 1 AND prior_state_version IS NULL AND creation_operation_id = operation_id AND creation_source_reference = source_reference AND creation_occurred_at = occurred_at) OR (mutation_kind IN ('ATTACH_SESSION', 'BIND_PLAYER_CHARACTER') AND state_version BETWEEN 2 AND 9223372036854775807 AND prior_state_version = state_version - 1)", "(mutation_kind = 'CREATE' AND state_version = 1 AND prior_state_version IS NULL AND creation_operation_id = operation_id AND creation_source_reference = source_reference AND creation_occurred_at = occurred_at) OR (mutation_kind IN ('ATTACH_SESSION', 'BIND_PLAYER_CHARACTER') AND state_version BETWEEN 2 AND 9223372036854775807 AND prior_state_version = state_version - 1) OR (mutation_kind = 'TERMINATE_NATIVE_RUN' AND prior_state_version IS NOT NULL AND prior_state_version = 3 AND state_version = 4 AND lifecycle_status = 'terminated' AND binding_player_character_id IS NOT NULL AND binding_contract_version IS NOT NULL AND binding_record_revision IS NOT NULL AND binding_state IS NOT NULL AND binding_state = 'historical' AND binding_operation_id IS NOT NULL AND binding_authority_source_ref IS NOT NULL AND bound_at IS NOT NULL AND inactivated_at IS NOT NULL AND inactivated_at = occurred_at AND occurred_at >= bound_at AND active_player_character_id IS NULL)"), ('run_mutation_receipts', 'ck_run_mutation_receipts_protocol_matrix', "(operation_namespace = 'run.attach-session/v1' AND command_kind = 'ATTACH_SESSION' AND result_schema_version = 'run.attach-session-result/v1' AND participation_session_id IS NOT NULL AND participation_operation_id IS NOT NULL AND participation_source_reference IS NOT NULL AND result_player_character_id IS NULL AND result_character_contract_version IS NULL AND result_character_record_revision IS NULL) OR (operation_namespace = 'run.bind-player-character/v1' AND command_kind = 'BIND_PLAYER_CHARACTER' AND result_schema_version = 'run.bind-player-character-result/v1' AND participation_session_id IS NULL AND participation_operation_id IS NULL AND participation_source_reference IS NULL AND result_player_character_id IS NOT NULL AND result_character_contract_version IS NOT NULL AND result_character_record_revision IS NOT NULL)", "(operation_namespace = 'run.attach-session/v1' AND command_kind = 'ATTACH_SESSION' AND result_schema_version = 'run.attach-session-result/v1' AND participation_session_id IS NOT NULL AND participation_operation_id IS NOT NULL AND participation_source_reference IS NOT NULL AND result_player_character_id IS NULL AND result_character_contract_version IS NULL AND result_character_record_revision IS NULL) OR (operation_namespace = 'run.bind-player-character/v1' AND command_kind = 'BIND_PLAYER_CHARACTER' AND result_schema_version = 'run.bind-player-character-result/v1' AND participation_session_id IS NULL AND participation_operation_id IS NULL AND participation_source_reference IS NULL AND result_player_character_id IS NOT NULL AND result_character_contract_version IS NOT NULL AND result_character_record_revision IS NOT NULL) OR (operation_namespace = 'run.terminate-native/v1' AND command_kind = 'TERMINATE_NATIVE_RUN' AND result_schema_version = 'run.terminate-native-result/v1' AND expected_state_version = 3 AND resulting_state_version = 4 AND resulting_lifecycle_status = 'terminated' AND participation_session_id IS NULL AND participation_operation_id IS NULL AND participation_source_reference IS NULL AND result_player_character_id IS NULL AND result_character_contract_version IS NULL AND result_character_record_revision IS NULL)"))

_PROBES = (('run_revisions', "mutation_kind = 'TERMINATE_NATIVE_RUN' OR lifecycle_status = 'terminated'"), ('run_current', "mutation_kind = 'TERMINATE_NATIVE_RUN' OR lifecycle_status = 'terminated'"), ('run_mutation_receipts', "command_kind = 'TERMINATE_NATIVE_RUN' OR resulting_lifecycle_status = 'terminated' OR operation_namespace = 'run.terminate-native/v1' OR result_schema_version = 'run.terminate-native-result/v1'"))

def _error(code, cause=None):
    error = RuntimeError("P3.3-S7-1 migration " + code)
    error.__cause__ = cause
    error.__suppress_context__ = True
    return error


def _lost(connection, error=None):
    if connection.closed or connection.invalidated:
        return True
    if isinstance(error, DBAPIError) and error.connection_invalidated:
        return True
    original = error.orig if isinstance(error, DBAPIError) else error
    return (
        original is not None
        and type(original).__module__.startswith("asyncmy")
        and bool(original.args)
        and original.args[0] in (2006, 2013, 2055)
    )


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


def _amend(*, terminating):
    connection = op.get_bind()
    stage = "BEFORE"
    try:
        if _lost(connection):
            raise _error("ACQUIRE_CONNECTION_LOST_BEFORE")
        if not connection.in_transaction():
            connection.begin()
        owner_connection_id = connection.execute(sa.text("SELECT CONNECTION_ID()")).scalar_one()
        if _lost(connection):
            raise _error("ACQUIRE_CONNECTION_LOST_BEFORE")
        stage = "PENDING"
        result = connection.execute(sa.text(f"SELECT GET_LOCK('{_LOCK}', 30)")).scalar_one()
        if type(result) is int and result == 0:
            raise _error("ACQUIRE_TIMEOUT")
        if result is None:
            raise _error("ACQUIRE_NULL")
        if type(result) is not int or result != 1:
            raise _error("ACQUIRE_INVALID_RESULT")
        stage = "AFTER"
        if _lost(connection):
            raise _error("ACQUIRE_CONNECTION_LOST_AFTER")
    except BaseException as error:
        if type(error) is RuntimeError and str(error).startswith("P3.3-S7-1 migration ACQUIRE_"):
            selected = error
        elif not isinstance(error, Exception):
            selected = error
        elif _lost(connection, error):
            selected = _error("ACQUIRE_CONNECTION_LOST_" + stage, error)
        else:
            selected = _error("ACQUIRE_STATEMENT_FAILED", error)
        if str(selected) != "P3.3-S7-1 migration ACQUIRE_TIMEOUT":
            _discard(connection, selected)
        raise selected

    primary = None
    primary_traceback = None
    observed_loss = None
    stage = "BEFORE_PROBES"
    completed = []
    try:
        if not terminating:
            for table, predicate in _PROBES:
                stage = "PROBE_" + table
                if _lost(connection):
                    raise _error("BODY_CONNECTION_LOST_" + stage)
                if connection.execute(sa.text(f"SELECT 1 FROM {table} WHERE {predicate} LIMIT 1 FOR UPDATE")).first() is not None:
                    raise RuntimeError(_REFUSAL) from None
        for table, name, previous, terminal in _CONSTRAINTS:
            stage = "DDL_" + name
            if _lost(connection):
                raise _error("BODY_CONNECTION_LOST_" + stage)
            expression = terminal if terminating else previous
            # Each ALTER is atomic at the statement boundary, not across tables.
            connection.execute(sa.text(f"ALTER TABLE {table} DROP CHECK {name}, ADD CONSTRAINT {name} CHECK ({expression})"))
            completed.append(name)
            if _lost(connection):
                raise _error("BODY_CONNECTION_LOST_AFTER_" + name)
    except BaseException as error:
        if isinstance(error, Exception) and _lost(connection, error):
            if type(error) is RuntimeError and str(error).startswith("P3.3-S7-1 migration BODY_CONNECTION_LOST_"):
                primary = error
            else:
                observed_loss = error
                primary = _error("BODY_CONNECTION_LOST_" + stage, error)
        else:
            primary = error
        primary.completed_constraints = tuple(completed)
        primary.failed_stage = stage
        primary_traceback = error.__traceback__

    cleanup_error = None
    try:
        if _lost(connection, observed_loss):
            cleanup_error = _error("RELEASE_CONNECTION_LOST_BEFORE", observed_loss)
        else:
            result = connection.execute(sa.text(f"SELECT RELEASE_LOCK('{_LOCK}')")).scalar_one()
            if type(result) is int and result == 1:
                pass
            elif type(result) is int and result == 0:
                cleanup_error = _error("RELEASE_NOT_OWNER")
            elif result is None:
                cleanup_error = _error("RELEASE_NULL")
            else:
                cleanup_error = _error("RELEASE_INVALID_RESULT")
    except BaseException as error:
        if not isinstance(error, Exception):
            cleanup_error = error
        elif _lost(connection, error):
            cleanup_error = _error("RELEASE_CONNECTION_LOST_PENDING", error)
        else:
            cleanup_error = _error("RELEASE_STATEMENT_FAILED", error)
    if cleanup_error is not None:
        _discard(connection, cleanup_error)
    if primary is not None:
        primary.cleanup_error = cleanup_error
        raise primary.with_traceback(primary_traceback)
    if cleanup_error is not None:
        raise cleanup_error


def upgrade():
    _amend(terminating=True)


def downgrade():
    _amend(terminating=False)
