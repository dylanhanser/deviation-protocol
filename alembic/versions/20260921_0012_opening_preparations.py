"""Persist opening preparation without changing existing business rows.

Revision ID: 20260921_0012
Revises: 20260920_0011
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from contextlib import contextmanager

revision = "20260921_0012"
down_revision = "20260920_0011"
branch_labels = None
depends_on = None


def _ascii(length):
    return mysql.VARCHAR(length, charset="ascii", collation="ascii_bin")


@contextmanager
def _admission_lock():
    connection = op.get_bind()
    name = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"
    if connection.execute(sa.text("SELECT GET_LOCK(:name, 30)"), {"name": name}).scalar_one() != 1:
        raise RuntimeError("Could not lock native admission for opening migration")
    try:
        yield connection
    finally:
        if connection.execute(sa.text("SELECT RELEASE_LOCK(:name)"), {"name": name}).scalar_one() != 1:
            raise RuntimeError("Could not release opening migration admission lock")


def upgrade():
    with _admission_lock():
        _create_table()


def _create_table():
    op.create_table("opening_preparations",
        sa.Column("preparation_id", _ascii(32), primary_key=True),
        sa.Column("owner", _ascii(128), nullable=False),
        sa.Column("character_id", _ascii(128), sa.ForeignKey("player_character_current.player_character_id"), nullable=False),
        sa.Column("ordinal", sa.BigInteger(), nullable=False),
        sa.Column("request_key", _ascii(128), nullable=False),
        sa.Column("pending_character_id", _ascii(128), nullable=True),
        sa.Column("state", _ascii(16), nullable=False),
        sa.Column("run_id", _ascii(128), sa.ForeignKey("run_current.run_id"), nullable=True),
        sa.Column("record_canonical", mysql.BLOB(), nullable=False),
        sa.UniqueConstraint("owner", "request_key", name="uq_opening_request"),
        sa.UniqueConstraint("character_id", "ordinal", name="uq_opening_character_ordinal"),
        sa.UniqueConstraint("pending_character_id", name="uq_opening_pending_character"),
        sa.UniqueConstraint("run_id", name="uq_opening_run"),
        sa.CheckConstraint("ordinal >= 1", name="ck_opening_ordinal"),
        sa.CheckConstraint("OCTET_LENGTH(record_canonical) BETWEEN 1 AND 16384", name="ck_opening_record"),
        sa.CheckConstraint("(state = 'PENDING' AND pending_character_id IS NOT NULL AND pending_character_id = character_id AND run_id IS NULL) OR (state = 'CONFIRMED' AND pending_character_id IS NULL AND run_id IS NOT NULL)", name="ck_opening_lifecycle"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_bin")


def downgrade():
    # Preserve issued offers and immutable selections. Never erase user data.
    with _admission_lock() as connection:
        if connection.execute(sa.text("SELECT COUNT(*) FROM opening_preparations")).scalar_one():
            raise RuntimeError("Opening preparations exist; downgrade requires operator inspection")
        op.drop_table("opening_preparations")
