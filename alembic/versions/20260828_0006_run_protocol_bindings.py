"""add native run protocol binding persistence"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import DBAPIError

revision = "20260828_0006"
down_revision = "20260729_0005"
branch_labels = None
depends_on = None

_LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"
_REFUSAL = "Refusing to downgrade P3.3-S3: native Run Protocol binding data exists; recovery must be forward-only"


def _ascii_varchar(length):
    return mysql.VARCHAR(length=length, charset="ascii", collation="ascii_bin")


def upgrade():
    op.create_table(
        "run_protocol_bindings",
        sa.Column("run_id", _ascii_varchar(128), nullable=False),
        sa.Column("continuous_story_line_id", _ascii_varchar(128), nullable=False),
        sa.Column("bound_state_version", sa.BigInteger, nullable=False),
        sa.Column("family_discriminator", _ascii_varchar(32), nullable=False),
        sa.Column("binding_epoch", _ascii_varchar(64), nullable=False),
        sa.Column("binding_record_version", sa.BigInteger, nullable=False),
        sa.Column("envelope_epoch", _ascii_varchar(64), nullable=False),
        sa.Column("envelope_record_version", sa.BigInteger, nullable=False),
        sa.Column("envelope_canonical", mysql.BLOB, nullable=False),
        sa.Column("resolver_epoch", _ascii_varchar(64), nullable=False),
        sa.Column("resolver_record_version", sa.BigInteger, nullable=False),
        sa.Column("resolution_input_canonical", mysql.BLOB, nullable=False),
        sa.Column("resource_pressure", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("social_trust", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("consequence_severity", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("information_opacity", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("conflict_intensity", mysql.SMALLINT(unsigned=True), nullable=False),
        sa.Column("resolution_fingerprint", mysql.BINARY(32), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("run_id", name="pk_run_protocol_bindings"),
        sa.CheckConstraint("CHAR_LENGTH(run_id) >= 1 AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(continuous_story_line_id) >= 1 AND continuous_story_line_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND bound_state_version BETWEEN 1 AND 9223372036854775807", name="ck_run_protocol_bindings_identity_version"),
        sa.CheckConstraint("family_discriminator = 'phase_3_3_native' AND binding_epoch = 'run-protocol-binding' AND binding_record_version = 1 AND envelope_epoch = 'run-protocol-envelope' AND envelope_record_version = 1 AND resolver_epoch = 'run-protocol-resolution' AND resolver_record_version = 1", name="ck_run_protocol_bindings_discriminators"),
        sa.CheckConstraint("OCTET_LENGTH(envelope_canonical) BETWEEN 1 AND 1024 AND OCTET_LENGTH(resolution_input_canonical) BETWEEN 1 AND 1024 AND OCTET_LENGTH(resolution_fingerprint) = 32", name="ck_run_protocol_bindings_payload_sizes"),
        sa.CheckConstraint("resource_pressure BETWEEN 0 AND 100 AND MOD(resource_pressure, 5) = 0 AND social_trust BETWEEN 0 AND 100 AND MOD(social_trust, 5) = 0 AND consequence_severity BETWEEN 0 AND 100 AND MOD(consequence_severity, 5) = 0 AND information_opacity BETWEEN 0 AND 100 AND MOD(information_opacity, 5) = 0 AND conflict_intensity BETWEEN 0 AND 100 AND MOD(conflict_intensity, 5) = 0", name="ck_run_protocol_bindings_objectives"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin",
    )
    op.create_index(
        "ix_run_protocol_bindings_revision", "run_protocol_bindings",
        ["run_id", "continuous_story_line_id", "bound_state_version"], unique=False,
    )
    op.create_foreign_key(
        "fk_run_protocol_bindings_revision", "run_protocol_bindings", "run_revisions",
        ["run_id", "continuous_story_line_id", "bound_state_version"],
        ["run_id", "continuous_story_line_id", "state_version"],
        ondelete="RESTRICT", onupdate="RESTRICT",
    )


def _error(code, cause=None):
    error = RuntimeError("P3.3-S3 downgrade " + code)
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
    try:
        connection.invalidate()
    except BaseException as error:
        selected.close_error = error
    try:
        connection.close()
    except BaseException as error:
        if not hasattr(selected, "close_error"):
            selected.close_error = error


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
        if type(error) is RuntimeError and str(error).startswith("P3.3-S3 downgrade ACQUIRE_"):
            selected = error
        elif not isinstance(error, Exception):
            selected = error
        elif _lost(connection, error):
            selected = _error("ACQUIRE_CONNECTION_LOST_" + stage, error)
        else:
            selected = _error("ACQUIRE_STATEMENT_FAILED", error)
        if str(selected) != "P3.3-S3 downgrade ACQUIRE_TIMEOUT":
            _discard(connection, selected)
        raise selected

    primary = None
    primary_traceback = None
    observed_loss = None
    stage = "BEFORE_PROBE"
    try:
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_PROBE")
        stage = "PROBE"
        present = connection.execute(sa.text("SELECT 1 FROM run_protocol_bindings LIMIT 1 FOR UPDATE")).first()
        if present is not None:
            raise RuntimeError(_REFUSAL) from None
        stage = "BEFORE_DDL"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_DDL")
        stage = "DDL_FK"
        op.drop_constraint("fk_run_protocol_bindings_revision", "run_protocol_bindings", type_="foreignkey")
        stage = "BEFORE_INDEX"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_INDEX")
        stage = "DDL_INDEX"
        op.drop_index("ix_run_protocol_bindings_revision", table_name="run_protocol_bindings")
        stage = "BEFORE_TABLE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_BEFORE_TABLE")
        stage = "DDL_TABLE"
        op.drop_table("run_protocol_bindings")
        stage = "AFTER_TABLE"
        if _lost(connection):
            raise _error("BODY_CONNECTION_LOST_AFTER_TABLE")
    except BaseException as error:
        if isinstance(error, Exception) and _lost(connection, error):
            if type(error) is RuntimeError and str(error).startswith("P3.3-S3 downgrade BODY_CONNECTION_LOST_"):
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
