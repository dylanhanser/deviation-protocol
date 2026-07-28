"""add structured player-character phase 2 schema

Revision ID: 20260728_0004
Revises: 20260719_0003
Create Date: 2026-07-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260728_0004"
down_revision: str | None = "20260719_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_bin",
}

PHASE_2_TABLES = (
    "player_character_controller_bindings",
    "player_character_id_allocations",
    "player_character_revisions",
    "player_character_current",
    "player_character_creation_receipts",
    "player_character_mutation_receipts",
)


def _ascii_varchar(length: int) -> mysql.VARCHAR:
    return mysql.VARCHAR(length=length, charset="ascii", collation="ascii_bin")


def upgrade() -> None:
    op.create_table(
        "player_character_controller_bindings",
        sa.Column(
            "controller_binding",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_controller_bindings_opaque",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "player_character_id_allocations",
        sa.Column(
            "player_character_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_allocations_identity_opaque",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "player_character_revisions",
        sa.Column(
            "player_character_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "record_revision",
            sa.BigInteger(),
            primary_key=True,
        ),
        sa.Column(
            "contract_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "controller_binding",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "lifecycle",
            _ascii_varchar(16),
            nullable=False,
        ),
        sa.Column(
            "prior_revision",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "mutation_kind",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "authority_class",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "source_reference",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "record_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_identity_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_binding_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(source_reference) >= 1 "
            "AND source_reference REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_source_opaque",
        ),
        sa.CheckConstraint(
            "contract_version = 'structured-player-character/v1'",
            name="ck_spc_revisions_contract",
        ),
        sa.CheckConstraint(
            "record_revision BETWEEN 1 AND 9223372036854775807",
            name="ck_spc_revisions_revision_range",
        ),
        sa.CheckConstraint(
            "prior_revision IS NULL "
            "OR (prior_revision BETWEEN 1 AND 9223372036854775806 "
            "AND prior_revision < record_revision)",
            name="ck_spc_revisions_prior_range",
        ),
        sa.CheckConstraint(
            "("
            "mutation_kind = 'CREATE' "
            "AND record_revision = 1 "
            "AND prior_revision IS NULL "
            "AND lifecycle = 'active' "
            "AND authority_class = 'trusted-creation'"
            ") OR ("
            "mutation_kind = 'RETIRE' "
            "AND prior_revision IS NOT NULL "
            "AND prior_revision = record_revision - 1 "
            "AND lifecycle = 'retired' "
            "AND authority_class = 'authenticated-controller'"
            ") OR ("
            "mutation_kind = 'FINAL_DEATH' "
            "AND prior_revision IS NOT NULL "
            "AND prior_revision = record_revision - 1 "
            "AND lifecycle = 'deceased' "
            "AND authority_class = 'trusted-server-outcome'"
            ")",
            name="ck_spc_revisions_provenance_matrix",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(record_canonical) >= 1",
            name="ck_spc_revisions_canonical_nonempty",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "player_character_current",
        sa.Column(
            "player_character_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "contract_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "record_revision",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "controller_binding",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "lifecycle",
            _ascii_varchar(16),
            nullable=False,
        ),
        sa.Column(
            "record_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_current_identity_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_current_binding_opaque",
        ),
        sa.CheckConstraint(
            "contract_version = 'structured-player-character/v1'",
            name="ck_spc_current_contract",
        ),
        sa.CheckConstraint(
            "record_revision BETWEEN 1 AND 9223372036854775807",
            name="ck_spc_current_revision_range",
        ),
        sa.CheckConstraint(
            "lifecycle IN ('active', 'retired', 'deceased')",
            name="ck_spc_current_lifecycle",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(record_canonical) >= 1",
            name="ck_spc_current_canonical_nonempty",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "player_character_creation_receipts",
        sa.Column(
            "controller_binding",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "operation_namespace",
            _ascii_varchar(64),
            primary_key=True,
        ),
        sa.Column(
            "operation_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "fingerprint",
            mysql.BINARY(32),
            nullable=False,
        ),
        sa.Column(
            "command_kind",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "result_schema_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "result_player_character_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "result_contract_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "resulting_revision",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "resulting_lifecycle",
            _ascii_varchar(16),
            nullable=False,
        ),
        sa.Column(
            "result_record_fingerprint",
            mysql.BINARY(32),
            nullable=False,
        ),
        sa.Column(
            "receipt_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "operation_evidence_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_binding_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_operation_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_result_identity_opaque",
        ),
        sa.CheckConstraint(
            "operation_namespace = 'player-character.create/v1' "
            "AND command_kind = 'CREATE'",
            name="ck_spc_creation_receipts_protocol",
        ),
        sa.CheckConstraint(
            "result_schema_version = 'player-character.create-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1' "
            "AND resulting_revision = 1 "
            "AND resulting_lifecycle = 'active'",
            name="ck_spc_creation_receipts_result",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536",
            name="ck_spc_creation_receipts_canonical_size",
        ),
        sa.UniqueConstraint(
            "result_player_character_id",
            "resulting_revision",
            name="uq_spc_creation_receipts_result_revision",
        ),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "player_character_mutation_receipts",
        sa.Column(
            "player_character_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "operation_namespace",
            _ascii_varchar(64),
            primary_key=True,
        ),
        sa.Column(
            "operation_id",
            _ascii_varchar(128),
            primary_key=True,
        ),
        sa.Column(
            "fingerprint",
            mysql.BINARY(32),
            nullable=False,
        ),
        sa.Column(
            "command_kind",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "result_schema_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "expected_revision",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "result_player_character_id",
            _ascii_varchar(128),
            nullable=False,
        ),
        sa.Column(
            "result_contract_version",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "result_command_kind",
            _ascii_varchar(64),
            nullable=False,
        ),
        sa.Column(
            "command_result",
            _ascii_varchar(32),
            nullable=False,
        ),
        sa.Column(
            "resulting_revision",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "resulting_lifecycle",
            _ascii_varchar(16),
            nullable=False,
        ),
        sa.Column(
            "before_record_fingerprint",
            mysql.BINARY(32),
            nullable=False,
        ),
        sa.Column(
            "after_record_fingerprint",
            mysql.BINARY(32),
            nullable=False,
        ),
        sa.Column(
            "receipt_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "operation_evidence_canonical",
            mysql.MEDIUMBLOB(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_identity_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_operation_opaque",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_result_identity_opaque",
        ),
        sa.CheckConstraint(
            "operation_namespace = 'player-character.mutate/v1' "
            "AND result_schema_version = 'player-character.mutate-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1'",
            name="ck_spc_mutation_receipts_protocol",
        ),
        sa.CheckConstraint(
            "player_character_id = result_player_character_id",
            name="ck_spc_mutation_receipts_owner_result",
        ),
        sa.CheckConstraint(
            "expected_revision BETWEEN 1 AND 9223372036854775806 "
            "AND resulting_revision = expected_revision + 1 "
            "AND resulting_revision <= 9223372036854775807",
            name="ck_spc_mutation_receipts_revision_successor",
        ),
        sa.CheckConstraint(
            "("
            "command_kind = 'RETIRE' "
            "AND result_command_kind = 'RETIRE' "
            "AND command_result = 'RETIRED' "
            "AND resulting_lifecycle = 'retired'"
            ") OR ("
            "command_kind = 'FINAL_DEATH' "
            "AND result_command_kind = 'FINAL_DEATH' "
            "AND command_result = 'DECEASED' "
            "AND resulting_lifecycle = 'deceased'"
            ")",
            name="ck_spc_mutation_receipts_result",
        ),
        sa.CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536",
            name="ck_spc_mutation_receipts_canonical_size",
        ),
        sa.UniqueConstraint(
            "player_character_id",
            "resulting_revision",
            name="uq_spc_mutation_receipts_result_revision",
        ),
        **TABLE_OPTIONS,
    )

    # Declare the complete child-side index inventory before adding foreign
    # keys. MySQL can then reuse these exact indexes instead of generating
    # additional undeclared indexes for the foreign-key constraints.
    op.create_index(
        "ix_spc_revisions_controller_binding",
        "player_character_revisions",
        ("controller_binding",),
    )
    op.create_index(
        "ix_spc_current_controller_identity",
        "player_character_current",
        ("controller_binding", "player_character_id"),
    )
    op.create_index(
        "ix_spc_current_identity_revision",
        "player_character_current",
        ("player_character_id", "record_revision"),
    )
    op.create_index(
        "ix_spc_mutation_receipts_expected_revision",
        "player_character_mutation_receipts",
        ("player_character_id", "expected_revision"),
    )
    op.create_index(
        "ix_spc_mutation_receipts_result_revision",
        "player_character_mutation_receipts",
        ("result_player_character_id", "resulting_revision"),
    )

    op.create_foreign_key(
        "fk_spc_revisions_allocation",
        "player_character_revisions",
        "player_character_id_allocations",
        ("player_character_id",),
        ("player_character_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_revisions_controller_binding",
        "player_character_revisions",
        "player_character_controller_bindings",
        ("controller_binding",),
        ("controller_binding",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_current_allocation",
        "player_character_current",
        "player_character_id_allocations",
        ("player_character_id",),
        ("player_character_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_current_controller_binding",
        "player_character_current",
        "player_character_controller_bindings",
        ("controller_binding",),
        ("controller_binding",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_current_revision",
        "player_character_current",
        "player_character_revisions",
        ("player_character_id", "record_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_creation_receipts_controller_binding",
        "player_character_creation_receipts",
        "player_character_controller_bindings",
        ("controller_binding",),
        ("controller_binding",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_creation_receipts_allocation",
        "player_character_creation_receipts",
        "player_character_id_allocations",
        ("result_player_character_id",),
        ("player_character_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_creation_receipts_revision",
        "player_character_creation_receipts",
        "player_character_revisions",
        ("result_player_character_id", "resulting_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_mutation_receipts_allocation",
        "player_character_mutation_receipts",
        "player_character_id_allocations",
        ("player_character_id",),
        ("player_character_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_mutation_receipts_result_allocation",
        "player_character_mutation_receipts",
        "player_character_id_allocations",
        ("result_player_character_id",),
        ("player_character_id",),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_mutation_receipts_prior_revision",
        "player_character_mutation_receipts",
        "player_character_revisions",
        ("player_character_id", "expected_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )
    op.create_foreign_key(
        "fk_spc_mutation_receipts_result_revision",
        "player_character_mutation_receipts",
        "player_character_revisions",
        ("result_player_character_id", "resulting_revision"),
        ("player_character_id", "record_revision"),
        ondelete="RESTRICT",
        onupdate="RESTRICT",
    )


def _assert_phase_2_tables_empty() -> None:
    connection = op.get_bind()
    populated_tables = tuple(
        table_name
        for table_name in PHASE_2_TABLES
        if connection.execute(
            sa.text(f"SELECT 1 FROM `{table_name}` LIMIT 1")
        ).scalar_one_or_none()
        is not None
    )
    if populated_tables:
        joined = ", ".join(populated_tables)
        raise RuntimeError(
            "Refusing to downgrade structured player-character Phase 2: "
            f"data exists in {joined}; recovery must be forward-only"
        )


def downgrade() -> None:
    # This guard must complete before the first destructive DDL operation. Any
    # committed Phase 2 row makes identity release or history loss unsafe.
    _assert_phase_2_tables_empty()

    op.drop_constraint(
        "fk_spc_mutation_receipts_result_revision",
        "player_character_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_mutation_receipts_prior_revision",
        "player_character_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_mutation_receipts_result_allocation",
        "player_character_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_mutation_receipts_allocation",
        "player_character_mutation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_creation_receipts_revision",
        "player_character_creation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_creation_receipts_allocation",
        "player_character_creation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_creation_receipts_controller_binding",
        "player_character_creation_receipts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_current_revision",
        "player_character_current",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_current_controller_binding",
        "player_character_current",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_current_allocation",
        "player_character_current",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_revisions_controller_binding",
        "player_character_revisions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_spc_revisions_allocation",
        "player_character_revisions",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_spc_mutation_receipts_result_revision",
        table_name="player_character_mutation_receipts",
    )
    op.drop_index(
        "ix_spc_mutation_receipts_expected_revision",
        table_name="player_character_mutation_receipts",
    )
    op.drop_index(
        "ix_spc_current_identity_revision",
        table_name="player_character_current",
    )
    op.drop_index(
        "ix_spc_current_controller_identity",
        table_name="player_character_current",
    )
    op.drop_index(
        "ix_spc_revisions_controller_binding",
        table_name="player_character_revisions",
    )

    op.drop_table("player_character_mutation_receipts")
    op.drop_table("player_character_creation_receipts")
    op.drop_table("player_character_current")
    op.drop_table("player_character_revisions")
    op.drop_table("player_character_id_allocations")
    op.drop_table("player_character_controller_bindings")
