"""add minimum Run core persistence

Revision ID: 20260729_0005
Revises: 20260728_0004
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260729_0005"
down_revision: str | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_bin",
}
RUN_TABLES = (
    "run_revisions",
    "run_current",
    "run_session_participations",
    "run_creation_receipts",
    "run_mutation_receipts",
)


def _ascii_varchar(length: int) -> mysql.VARCHAR:
    return mysql.VARCHAR(length=length, charset="ascii", collation="ascii_bin")


def _legacy_session_id_varchar() -> mysql.VARCHAR:
    return mysql.VARCHAR(
        length=64,
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
    )


def _core_columns(*, current: bool) -> tuple[sa.Column[object], ...]:
    columns: tuple[sa.Column[object], ...] = (
        sa.Column("run_id", _ascii_varchar(128), primary_key=True),
        *(
            ()
            if current
            else (sa.Column("state_version", sa.BigInteger(), primary_key=True),)
        ),
        sa.Column(
            "continuous_story_line_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column("lifecycle_status", _ascii_varchar(32), nullable=False),
        *(
            (sa.Column("state_version", sa.BigInteger(), nullable=False),)
            if current
            else ()
        ),
        sa.Column("creation_operation_id", _ascii_varchar(128), nullable=False),
        sa.Column(
            "creation_source_reference",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "creation_occurred_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.Column("prior_state_version", sa.BigInteger(), nullable=True),
        sa.Column("mutation_kind", _ascii_varchar(32), nullable=False),
        sa.Column("operation_id", _ascii_varchar(128), nullable=False),
        sa.Column("source_reference", _ascii_varchar(128), nullable=False),
        sa.Column("occurred_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "binding_player_character_id",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column(
            "binding_contract_version",
            _ascii_varchar(64),
            nullable=True,
        ),
        sa.Column("binding_record_revision", sa.BigInteger(), nullable=True),
        sa.Column("binding_state", _ascii_varchar(16), nullable=True),
        sa.Column(
            "binding_operation_id",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column(
            "binding_authority_source_ref",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column("bound_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("inactivated_at", mysql.DATETIME(fsp=6), nullable=True),
    )
    return columns


def _identity_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "CHAR_LENGTH(run_id) >= 1 "
        "AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' "
        "AND CHAR_LENGTH(continuous_story_line_id) >= 1 "
        "AND continuous_story_line_id REGEXP "
        "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
        name=f"ck_{table}_identities_opaque",
    )


def _lifecycle_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "lifecycle_status IN "
        "('pre_first_turn', 'active', 'completed', 'terminated')",
        name=f"ck_{table}_lifecycle",
    )


def _mutation_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "("
        "mutation_kind = 'CREATE' AND state_version = 1 "
        "AND prior_state_version IS NULL "
        "AND creation_operation_id = operation_id "
        "AND creation_source_reference = source_reference "
        "AND creation_occurred_at = occurred_at"
        ") OR ("
        "mutation_kind IN ('ATTACH_SESSION', 'BIND_PLAYER_CHARACTER') "
        "AND state_version BETWEEN 2 AND 9223372036854775807 "
        "AND prior_state_version = state_version - 1"
        ")",
        name=f"ck_{table}_mutation_matrix",
    )


def _revision_binding_check() -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "("
        "binding_player_character_id IS NULL "
        "AND binding_contract_version IS NULL "
        "AND binding_record_revision IS NULL "
        "AND binding_state IS NULL "
        "AND binding_operation_id IS NULL "
        "AND binding_authority_source_ref IS NULL "
        "AND bound_at IS NULL AND inactivated_at IS NULL"
        ") OR ("
        "binding_player_character_id IS NOT NULL "
        "AND binding_contract_version IS NOT NULL "
        "AND binding_record_revision IS NOT NULL "
        "AND binding_operation_id IS NOT NULL "
        "AND binding_authority_source_ref IS NOT NULL "
        "AND bound_at IS NOT NULL "
        "AND ("
        "binding_state = 'active' AND inactivated_at IS NULL"
        " OR "
        "binding_state = 'historical' AND inactivated_at IS NOT NULL"
        ")"
        ")",
        name="ck_run_revisions_binding_matrix",
    )


def _current_binding_check() -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "("
        "binding_player_character_id IS NULL "
        "AND binding_contract_version IS NULL "
        "AND binding_record_revision IS NULL "
        "AND binding_state IS NULL "
        "AND binding_operation_id IS NULL "
        "AND binding_authority_source_ref IS NULL "
        "AND bound_at IS NULL AND inactivated_at IS NULL "
        "AND active_player_character_id IS NULL"
        ") OR ("
        "binding_player_character_id IS NOT NULL "
        "AND binding_contract_version IS NOT NULL "
        "AND binding_record_revision IS NOT NULL "
        "AND binding_operation_id IS NOT NULL "
        "AND binding_authority_source_ref IS NOT NULL "
        "AND bound_at IS NOT NULL "
        "AND ("
        "binding_state = 'active' AND inactivated_at IS NULL "
        "AND active_player_character_id = binding_player_character_id"
        " OR "
        "binding_state = 'historical' AND inactivated_at IS NOT NULL "
        "AND active_player_character_id IS NULL"
        ")"
        ")",
        name="ck_run_current_binding_matrix",
    )


def _lifecycle_binding_check(table: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "("
        "lifecycle_status IN ('pre_first_turn', 'active') "
        "AND (binding_state IS NULL OR binding_state = 'active')"
        ") OR ("
        "lifecycle_status IN ('completed', 'terminated') "
        "AND (binding_state IS NULL OR binding_state = 'historical')"
        ")",
        name=f"ck_{table}_lifecycle_binding",
    )


def upgrade() -> None:
    op.create_table(
        "run_revisions",
        *_core_columns(current=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        _identity_check("run_revisions"),
        sa.CheckConstraint(
            "state_version BETWEEN 1 AND 9223372036854775807",
            name="ck_run_revisions_version_range",
        ),
        _lifecycle_check("run_revisions"),
        _mutation_check("run_revisions"),
        _revision_binding_check(),
        _lifecycle_binding_check("run_revisions"),
        sa.UniqueConstraint(
            "run_id",
            "continuous_story_line_id",
            "state_version",
            name="uq_run_revisions_exact",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "run_current",
        *_core_columns(current=True),
        sa.Column(
            "active_player_character_id",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        _identity_check("run_current"),
        sa.CheckConstraint(
            "state_version BETWEEN 1 AND 9223372036854775807",
            name="ck_run_current_version_range",
        ),
        _lifecycle_check("run_current"),
        _mutation_check("run_current"),
        _current_binding_check(),
        _lifecycle_binding_check("run_current"),
        sa.UniqueConstraint(
            "continuous_story_line_id",
            name="uq_run_current_story_line",
        ),
        sa.UniqueConstraint(
            "active_player_character_id",
            name="uq_run_current_active_character",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "run_session_participations",
        sa.Column(
            "session_id",
            _legacy_session_id_varchar(),
            primary_key=True,
        ),
        sa.Column("run_id", _ascii_varchar(128), nullable=False),
        sa.Column(
            "continuous_story_line_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column("joined_state_version", sa.BigInteger(), nullable=False),
        sa.Column("operation_id", _ascii_varchar(128), nullable=False),
        sa.Column("source_reference", _ascii_varchar(128), nullable=False),
        sa.Column("joined_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "joined_state_version BETWEEN 2 AND 9223372036854775807",
            name="ck_run_participations_version_range",
        ),
        sa.UniqueConstraint(
            "session_id",
            "run_id",
            "continuous_story_line_id",
            "joined_state_version",
            name="uq_run_participations_exact",
        ),
        sa.UniqueConstraint(
            "run_id",
            "joined_state_version",
            name="uq_run_participations_revision",
        ),
        sa.UniqueConstraint(
            "run_id",
            "operation_id",
            name="uq_run_participations_operation",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "run_creation_receipts",
        sa.Column(
            "operation_namespace",
            _ascii_varchar(64),
            primary_key=True,
        ),
        sa.Column("operation_id", _ascii_varchar(128), primary_key=True),
        sa.Column("fingerprint", mysql.BINARY(32), nullable=False),
        sa.Column("command_kind", _ascii_varchar(32), nullable=False),
        sa.Column(
            "result_schema_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column("result_run_id", _ascii_varchar(128), nullable=False),
        sa.Column(
            "result_continuous_story_line_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "resulting_lifecycle_status",
            _ascii_varchar(32),
            nullable=False,
        ),
        sa.Column("resulting_state_version", sa.BigInteger(), nullable=False),
        sa.Column("receipt_canonical", mysql.MEDIUMBLOB(), nullable=False),
        sa.Column(
            "operation_evidence_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "operation_namespace = 'run.create/v1' "
            "AND command_kind = 'CREATE' "
            "AND result_schema_version = 'run.create-result/v1' "
            "AND resulting_lifecycle_status = 'pre_first_turn' "
            "AND resulting_state_version = 1",
            name="ck_run_creation_receipts_protocol",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536 "
            "AND OCTET_LENGTH(operation_evidence_canonical) >= 1",
            name="ck_run_creation_receipts_canonical",
        ),
        sa.UniqueConstraint(
            "result_run_id",
            "resulting_state_version",
            name="uq_run_creation_receipts_result",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "run_mutation_receipts",
        sa.Column("run_id", _ascii_varchar(128), primary_key=True),
        sa.Column(
            "operation_namespace",
            _ascii_varchar(64),
            primary_key=True,
        ),
        sa.Column("operation_id", _ascii_varchar(128), primary_key=True),
        sa.Column("fingerprint", mysql.BINARY(32), nullable=False),
        sa.Column("command_kind", _ascii_varchar(32), nullable=False),
        sa.Column(
            "result_schema_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column("expected_state_version", sa.BigInteger(), nullable=False),
        sa.Column("result_run_id", _ascii_varchar(128), nullable=False),
        sa.Column(
            "result_continuous_story_line_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "resulting_lifecycle_status",
            _ascii_varchar(32),
            nullable=False,
        ),
        sa.Column("resulting_state_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "participation_session_id",
            _legacy_session_id_varchar(),
            nullable=True,
        ),
        sa.Column(
            "participation_operation_id",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column(
            "participation_source_reference",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column(
            "result_player_character_id",
            _ascii_varchar(128),
            nullable=True,
        ),
        sa.Column(
            "result_character_contract_version",
            _ascii_varchar(64),
            nullable=True,
        ),
        sa.Column(
            "result_character_record_revision",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column("receipt_canonical", mysql.MEDIUMBLOB(), nullable=False),
        sa.Column(
            "operation_evidence_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "expected_state_version BETWEEN 1 AND 9223372036854775806 "
            "AND resulting_state_version = expected_state_version + 1",
            name="ck_run_mutation_receipts_version_successor",
        ),
        sa.CheckConstraint(
            "("
            "operation_namespace = 'run.attach-session/v1' "
            "AND command_kind = 'ATTACH_SESSION' "
            "AND result_schema_version = 'run.attach-session-result/v1' "
            "AND participation_session_id IS NOT NULL "
            "AND participation_operation_id IS NOT NULL "
            "AND participation_source_reference IS NOT NULL "
            "AND result_player_character_id IS NULL "
            "AND result_character_contract_version IS NULL "
            "AND result_character_record_revision IS NULL"
            ") OR ("
            "operation_namespace = 'run.bind-player-character/v1' "
            "AND command_kind = 'BIND_PLAYER_CHARACTER' "
            "AND result_schema_version = 'run.bind-player-character-result/v1' "
            "AND participation_session_id IS NULL "
            "AND participation_operation_id IS NULL "
            "AND participation_source_reference IS NULL "
            "AND result_player_character_id IS NOT NULL "
            "AND result_character_contract_version IS NOT NULL "
            "AND result_character_record_revision IS NOT NULL"
            ")",
            name="ck_run_mutation_receipts_protocol_matrix",
        ),
        sa.CheckConstraint(
            "run_id = result_run_id "
            "AND resulting_lifecycle_status IN "
            "('pre_first_turn', 'active', 'completed', 'terminated')",
            name="ck_run_mutation_receipts_result",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536 "
            "AND OCTET_LENGTH(operation_evidence_canonical) >= 1",
            name="ck_run_mutation_receipts_canonical",
        ),
        sa.UniqueConstraint(
            "run_id",
            "resulting_state_version",
            name="uq_run_mutation_receipts_result",
        ),
        **TABLE_OPTIONS,
    )

    op.create_index(
        "ix_run_revisions_line_version",
        "run_revisions",
        ("continuous_story_line_id", "state_version"),
    )
    op.create_index(
        "ix_run_current_identity_version",
        "run_current",
        ("run_id", "state_version"),
    )
    op.create_index(
        "ix_run_participations_run_version",
        "run_session_participations",
        ("run_id", "joined_state_version"),
    )
    op.create_index(
        "ix_run_creation_receipts_result",
        "run_creation_receipts",
        ("result_run_id", "resulting_state_version"),
    )
    op.create_index(
        "ix_run_mutation_receipts_result",
        "run_mutation_receipts",
        ("result_run_id", "resulting_state_version"),
    )
    op.create_index(
        "ix_run_mutation_receipts_participation",
        "run_mutation_receipts",
        (
            "participation_session_id",
            "result_run_id",
            "result_continuous_story_line_id",
            "resulting_state_version",
        ),
    )

    op.create_foreign_key(
        "fk_run_revisions_character_revision",
        "run_revisions",
        "player_character_revisions",
        ("binding_player_character_id", "binding_record_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_current_revision",
        "run_current",
        "run_revisions",
        ("run_id", "continuous_story_line_id", "state_version"),
        ("run_id", "continuous_story_line_id", "state_version"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_current_character_revision",
        "run_current",
        "player_character_revisions",
        ("binding_player_character_id", "binding_record_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_participations_session",
        "run_session_participations",
        "game_sessions",
        ("session_id",),
        ("session_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_participations_revision",
        "run_session_participations",
        "run_revisions",
        ("run_id", "continuous_story_line_id", "joined_state_version"),
        ("run_id", "continuous_story_line_id", "state_version"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_creation_receipts_revision",
        "run_creation_receipts",
        "run_revisions",
        (
            "result_run_id",
            "result_continuous_story_line_id",
            "resulting_state_version",
        ),
        ("run_id", "continuous_story_line_id", "state_version"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_mutation_receipts_revision",
        "run_mutation_receipts",
        "run_revisions",
        (
            "result_run_id",
            "result_continuous_story_line_id",
            "resulting_state_version",
        ),
        ("run_id", "continuous_story_line_id", "state_version"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_mutation_receipts_participation",
        "run_mutation_receipts",
        "run_session_participations",
        (
            "participation_session_id",
            "result_run_id",
            "result_continuous_story_line_id",
            "resulting_state_version",
        ),
        (
            "session_id",
            "run_id",
            "continuous_story_line_id",
            "joined_state_version",
        ),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_run_mutation_receipts_character_revision",
        "run_mutation_receipts",
        "player_character_revisions",
        ("result_player_character_id", "result_character_record_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )


def _assert_run_tables_empty() -> None:
    connection = op.get_bind()
    populated = tuple(
        table_name
        for table_name in RUN_TABLES
        if connection.execute(
            sa.text(f"SELECT 1 FROM `{table_name}` LIMIT 1")
        ).scalar_one_or_none()
        is not None
    )
    if populated:
        raise RuntimeError(
            "Refusing to downgrade the minimum Run core: data exists in "
            f"{', '.join(populated)}; recovery must be forward-only"
        )


def downgrade() -> None:
    _assert_run_tables_empty()

    op.drop_constraint(
        "fk_run_mutation_receipts_character_revision",
        "run_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_mutation_receipts_participation",
        "run_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_mutation_receipts_revision",
        "run_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_creation_receipts_revision",
        "run_creation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_participations_revision",
        "run_session_participations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_participations_session",
        "run_session_participations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_current_character_revision",
        "run_current",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_current_revision",
        "run_current",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_run_revisions_character_revision",
        "run_revisions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_run_mutation_receipts_participation",
        table_name="run_mutation_receipts",
    )
    op.drop_index(
        "ix_run_mutation_receipts_result",
        table_name="run_mutation_receipts",
    )
    op.drop_index(
        "ix_run_creation_receipts_result",
        table_name="run_creation_receipts",
    )
    op.drop_index(
        "ix_run_participations_run_version",
        table_name="run_session_participations",
    )
    op.drop_index(
        "ix_run_current_identity_version",
        table_name="run_current",
    )
    op.drop_index(
        "ix_run_revisions_line_version",
        table_name="run_revisions",
    )

    op.drop_table("run_mutation_receipts")
    op.drop_table("run_creation_receipts")
    op.drop_table("run_session_participations")
    op.drop_table("run_current")
    op.drop_table("run_revisions")
