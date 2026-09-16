"""add native run entry-world binding"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import DBAPIError

revision = "20260916_0007"
down_revision = "20260828_0006"
branch_labels = None
depends_on = None

_LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"
_REFUSAL = "Refusing to downgrade P3.3-S4: native admission data exists; recovery must be forward-only"


def _ascii_varchar(length):
    return mysql.VARCHAR(length=length, charset="ascii", collation="ascii_bin")


def upgrade():
    op.create_table(
        "run_entry_world_bindings",
        sa.Column("run_id", _ascii_varchar(128), nullable=False),
        sa.Column("continuous_story_line_id", _ascii_varchar(128), nullable=False),
        sa.Column("bound_state_version", sa.BigInteger(), nullable=False),
        sa.Column("binding_epoch", _ascii_varchar(64), nullable=False),
        sa.Column("binding_record_version", sa.BigInteger(), nullable=False),
        sa.Column("entry_world_id", _ascii_varchar(128), nullable=False),
        sa.Column("entry_world_version", sa.BigInteger(), nullable=False),
        sa.Column("scenario_id", _ascii_varchar(128), nullable=False),
        sa.Column("scenario_content_version", _ascii_varchar(32), nullable=False),
        sa.Column("default_character_definition_id", _ascii_varchar(128), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("run_id", name="pk_run_entry_world_bindings"),
        sa.CheckConstraint("CHAR_LENGTH(run_id) >= 1 AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(continuous_story_line_id) >= 1 AND continuous_story_line_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(entry_world_id) >= 1 AND entry_world_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(scenario_id) >= 1 AND scenario_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(scenario_content_version) >= 1 AND scenario_content_version REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(default_character_definition_id) >= 1 AND default_character_definition_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'", name="ck_run_entry_world_bindings_identity"),
        sa.CheckConstraint('bound_state_version = 3 AND binding_record_version = 1 AND entry_world_version BETWEEN 1 AND 9223372036854775807', name="ck_run_entry_world_bindings_versions"),
        sa.CheckConstraint("binding_epoch = 'run-entry-world-binding'", name="ck_run_entry_world_bindings_epoch"),
        sa.ForeignKeyConstraint(["run_id"], ["run_protocol_bindings.run_id"], name="fk_run_entry_world_bindings_protocol", ondelete="RESTRICT", onupdate="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id", "continuous_story_line_id", "bound_state_version"], ["run_revisions.run_id", "run_revisions.continuous_story_line_id", "run_revisions.state_version"], name="fk_run_entry_world_bindings_revision", ondelete="RESTRICT", onupdate="RESTRICT"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    op.create_index("ix_run_entry_world_bindings_revision", "run_entry_world_bindings", ["run_id", "continuous_story_line_id", "bound_state_version"])


def _error(code, cause=None):
    error = RuntimeError("P3.3-S4 downgrade " + code)
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


def downgrade():
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
        if type(error) is RuntimeError and str(error).startswith("P3.3-S4 downgrade ACQUIRE_"):
            selected = error
        elif not isinstance(error, Exception):
            selected = error
        elif _lost(connection, error):
            selected = _error("ACQUIRE_CONNECTION_LOST_" + stage, error)
        else:
            selected = _error("ACQUIRE_STATEMENT_FAILED", error)
        if str(selected) != "P3.3-S4 downgrade ACQUIRE_TIMEOUT":
            _discard(connection, selected)
        raise selected

    primary = None
    primary_traceback = None
    observed_loss = None
    stage = "BEFORE_WORLD_PROBE"
    try:
        stage = "BEFORE_WORLD_PROBE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_WORLD_PROBE")
        stage = "WORLD_PROBE"
        present = connection.execute(sa.text("SELECT 1 FROM run_entry_world_bindings LIMIT 1 FOR UPDATE")).first()
        if present is not None:
            raise RuntimeError(_REFUSAL) from None
        stage = "BEFORE_EVIDENCE_PROBE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_EVIDENCE_PROBE")
        stage = "EVIDENCE_PROBE"
        present = connection.execute(sa.text("SELECT 1 FROM run_creation_receipts WHERE LEFT(operation_evidence_canonical, 1) = X'8A' LIMIT 1 FOR UPDATE")).first()
        if present is not None:
            raise RuntimeError(_REFUSAL) from None
        stage = "BEFORE_DDL_PROTOCOL_FK"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_DDL_PROTOCOL_FK")
        stage = "DDL_PROTOCOL_FK"
        op.drop_constraint("fk_run_entry_world_bindings_protocol", "run_entry_world_bindings", type_="foreignkey")
        stage = "BEFORE_DDL_REVISION_FK"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_DDL_REVISION_FK")
        stage = "DDL_REVISION_FK"
        op.drop_constraint("fk_run_entry_world_bindings_revision", "run_entry_world_bindings", type_="foreignkey")
        stage = "BEFORE_DDL_INDEX"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_DDL_INDEX")
        stage = "DDL_INDEX"
        op.drop_index("ix_run_entry_world_bindings_revision", table_name="run_entry_world_bindings")
        stage = "BEFORE_DDL_TABLE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_DDL_TABLE")
        stage = "DDL_TABLE"
        op.drop_table("run_entry_world_bindings")
        stage = "AFTER_TABLE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_AFTER_TABLE")
    except BaseException as error:
        if isinstance(error, Exception) and _lost(connection, error):
            if type(error) is RuntimeError and str(error).startswith("P3.3-S4 downgrade BODY_CONNECTION_LOST_"):
                primary = error
            else:
                observed_loss = error
                primary = _error("BODY_CONNECTION_LOST_" + stage, error)
        else:
            primary = error
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
