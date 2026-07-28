from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import re
from types import ModuleType
from typing import Any
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from deviation_protocol.infrastructure.database import create_engine
from deviation_protocol.infrastructure.orm_models import Base


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "alembic"
    / "versions"
    / "20260728_0004_structured_player_character_phase_2.py"
)
MIGRATION_REVISION = "20260728_0004"
MIGRATION_PARENT = "20260719_0003"

LEGACY_MAPPED_TABLES = {
    "domain_events",
    "game_sessions",
    "game_snapshots",
    "turn_requests",
    "narrative_jobs",
}
PHASE_2_TABLES = (
    "player_character_controller_bindings",
    "player_character_id_allocations",
    "player_character_revisions",
    "player_character_current",
    "player_character_creation_receipts",
    "player_character_mutation_receipts",
)
PHASE_2_TABLE_SET = set(PHASE_2_TABLES)

# Each entry is (column name, MySQL DDL type, nullable, primary key).
EXPECTED_COLUMNS: dict[str, tuple[tuple[str, str, bool, bool], ...]] = {
    "player_character_controller_bindings": (
        (
            "controller_binding",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        ("created_at", "DATETIME(6)", False, False),
    ),
    "player_character_id_allocations": (
        (
            "player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        ("created_at", "DATETIME(6)", False, False),
    ),
    "player_character_revisions": (
        (
            "player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        ("record_revision", "BIGINT", False, True),
        (
            "contract_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "controller_binding",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "lifecycle",
            "VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("prior_revision", "BIGINT", True, False),
        (
            "mutation_kind",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "authority_class",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "source_reference",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("record_canonical", "MEDIUMBLOB", False, False),
        ("created_at", "DATETIME(6)", False, False),
    ),
    "player_character_current": (
        (
            "player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        (
            "contract_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("record_revision", "BIGINT", False, False),
        (
            "controller_binding",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "lifecycle",
            "VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("record_canonical", "MEDIUMBLOB", False, False),
        ("created_at", "DATETIME(6)", False, False),
        ("updated_at", "DATETIME(6)", False, False),
    ),
    "player_character_creation_receipts": (
        (
            "controller_binding",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        (
            "operation_namespace",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        (
            "operation_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        ("fingerprint", "BINARY(32)", False, False),
        (
            "command_kind",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_schema_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_contract_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("resulting_revision", "BIGINT", False, False),
        (
            "resulting_lifecycle",
            "VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("result_record_fingerprint", "BINARY(32)", False, False),
        ("receipt_canonical", "MEDIUMBLOB", False, False),
        ("operation_evidence_canonical", "MEDIUMBLOB", False, False),
        ("created_at", "DATETIME(6)", False, False),
    ),
    "player_character_mutation_receipts": (
        (
            "player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        (
            "operation_namespace",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        (
            "operation_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            True,
        ),
        ("fingerprint", "BINARY(32)", False, False),
        (
            "command_kind",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_schema_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("expected_revision", "BIGINT", False, False),
        (
            "result_player_character_id",
            "VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_contract_version",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "result_command_kind",
            "VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        (
            "command_result",
            "VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("resulting_revision", "BIGINT", False, False),
        (
            "resulting_lifecycle",
            "VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin",
            False,
            False,
        ),
        ("before_record_fingerprint", "BINARY(32)", False, False),
        ("after_record_fingerprint", "BINARY(32)", False, False),
        ("receipt_canonical", "MEDIUMBLOB", False, False),
        ("operation_evidence_canonical", "MEDIUMBLOB", False, False),
        ("created_at", "DATETIME(6)", False, False),
    ),
}

EXPECTED_PRIMARY_KEYS = {
    "player_character_controller_bindings": ("controller_binding",),
    "player_character_id_allocations": ("player_character_id",),
    "player_character_revisions": (
        "player_character_id",
        "record_revision",
    ),
    "player_character_current": ("player_character_id",),
    "player_character_creation_receipts": (
        "controller_binding",
        "operation_namespace",
        "operation_id",
    ),
    "player_character_mutation_receipts": (
        "player_character_id",
        "operation_namespace",
        "operation_id",
    ),
}

EXPECTED_UNIQUES = {
    "player_character_controller_bindings": {},
    "player_character_id_allocations": {},
    "player_character_revisions": {},
    "player_character_current": {},
    "player_character_creation_receipts": {
        "uq_spc_creation_receipts_result_revision": (
            "result_player_character_id",
            "resulting_revision",
        ),
    },
    "player_character_mutation_receipts": {
        "uq_spc_mutation_receipts_result_revision": (
            "player_character_id",
            "resulting_revision",
        ),
    },
}

EXPECTED_INDEXES = {
    "player_character_controller_bindings": {},
    "player_character_id_allocations": {},
    "player_character_revisions": {
        "ix_spc_revisions_controller_binding": (
            False,
            ("controller_binding",),
        ),
    },
    "player_character_current": {
        "ix_spc_current_controller_identity": (
            False,
            ("controller_binding", "player_character_id"),
        ),
        "ix_spc_current_identity_revision": (
            False,
            ("player_character_id", "record_revision"),
        ),
    },
    "player_character_creation_receipts": {},
    "player_character_mutation_receipts": {
        "ix_spc_mutation_receipts_expected_revision": (
            False,
            ("player_character_id", "expected_revision"),
        ),
        "ix_spc_mutation_receipts_result_revision": (
            False,
            ("result_player_character_id", "resulting_revision"),
        ),
    },
}

EXPECTED_FOREIGN_KEYS = {
    "fk_spc_current_allocation": (
        "player_character_current",
        ("player_character_id",),
        "player_character_id_allocations",
        ("player_character_id",),
    ),
    "fk_spc_current_controller_binding": (
        "player_character_current",
        ("controller_binding",),
        "player_character_controller_bindings",
        ("controller_binding",),
    ),
    "fk_spc_current_revision": (
        "player_character_current",
        ("player_character_id", "record_revision"),
        "player_character_revisions",
        ("player_character_id", "record_revision"),
    ),
    "fk_spc_revisions_allocation": (
        "player_character_revisions",
        ("player_character_id",),
        "player_character_id_allocations",
        ("player_character_id",),
    ),
    "fk_spc_revisions_controller_binding": (
        "player_character_revisions",
        ("controller_binding",),
        "player_character_controller_bindings",
        ("controller_binding",),
    ),
    "fk_spc_creation_receipts_controller_binding": (
        "player_character_creation_receipts",
        ("controller_binding",),
        "player_character_controller_bindings",
        ("controller_binding",),
    ),
    "fk_spc_creation_receipts_allocation": (
        "player_character_creation_receipts",
        ("result_player_character_id",),
        "player_character_id_allocations",
        ("player_character_id",),
    ),
    "fk_spc_creation_receipts_revision": (
        "player_character_creation_receipts",
        ("result_player_character_id", "resulting_revision"),
        "player_character_revisions",
        ("player_character_id", "record_revision"),
    ),
    "fk_spc_mutation_receipts_allocation": (
        "player_character_mutation_receipts",
        ("player_character_id",),
        "player_character_id_allocations",
        ("player_character_id",),
    ),
    "fk_spc_mutation_receipts_result_allocation": (
        "player_character_mutation_receipts",
        ("result_player_character_id",),
        "player_character_id_allocations",
        ("player_character_id",),
    ),
    "fk_spc_mutation_receipts_prior_revision": (
        "player_character_mutation_receipts",
        ("player_character_id", "expected_revision"),
        "player_character_revisions",
        ("player_character_id", "record_revision"),
    ),
    "fk_spc_mutation_receipts_result_revision": (
        "player_character_mutation_receipts",
        ("result_player_character_id", "resulting_revision"),
        "player_character_revisions",
        ("player_character_id", "record_revision"),
    ),
}

EXPECTED_CHECKS = {
    "player_character_controller_bindings": {
        "ck_spc_controller_bindings_opaque": (
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
    },
    "player_character_id_allocations": {
        "ck_spc_allocations_identity_opaque": (
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
    },
    "player_character_revisions": {
        "ck_spc_revisions_identity_opaque": (
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_revisions_binding_opaque": (
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_revisions_source_opaque": (
            "CHAR_LENGTH(source_reference) >= 1 "
            "AND source_reference REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_revisions_contract": (
            "contract_version = 'structured-player-character/v1'"
        ),
        "ck_spc_revisions_revision_range": (
            "record_revision BETWEEN 1 AND 9223372036854775807"
        ),
        "ck_spc_revisions_prior_range": (
            "prior_revision IS NULL "
            "OR (prior_revision BETWEEN 1 AND 9223372036854775806 "
            "AND prior_revision < record_revision)"
        ),
        "ck_spc_revisions_provenance_matrix": (
            "(mutation_kind = 'CREATE' AND record_revision = 1 "
            "AND prior_revision IS NULL AND lifecycle = 'active' "
            "AND authority_class = 'trusted-creation') "
            "OR (mutation_kind = 'RETIRE' "
            "AND prior_revision IS NOT NULL "
            "AND prior_revision = record_revision - 1 "
            "AND lifecycle = 'retired' "
            "AND authority_class = 'authenticated-controller') "
            "OR (mutation_kind = 'FINAL_DEATH' "
            "AND prior_revision IS NOT NULL "
            "AND prior_revision = record_revision - 1 "
            "AND lifecycle = 'deceased' "
            "AND authority_class = 'trusted-server-outcome')"
        ),
        "ck_spc_revisions_canonical_nonempty": (
            "OCTET_LENGTH(record_canonical) >= 1"
        ),
    },
    "player_character_current": {
        "ck_spc_current_identity_opaque": (
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_current_binding_opaque": (
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_current_contract": (
            "contract_version = 'structured-player-character/v1'"
        ),
        "ck_spc_current_revision_range": (
            "record_revision BETWEEN 1 AND 9223372036854775807"
        ),
        "ck_spc_current_lifecycle": (
            "lifecycle IN ('active', 'retired', 'deceased')"
        ),
        "ck_spc_current_canonical_nonempty": (
            "OCTET_LENGTH(record_canonical) >= 1"
        ),
    },
    "player_character_creation_receipts": {
        "ck_spc_creation_receipts_binding_opaque": (
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_creation_receipts_operation_opaque": (
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_creation_receipts_result_identity_opaque": (
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_creation_receipts_protocol": (
            "operation_namespace = 'player-character.create/v1' "
            "AND command_kind = 'CREATE'"
        ),
        "ck_spc_creation_receipts_result": (
            "result_schema_version = 'player-character.create-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1' "
            "AND resulting_revision = 1 "
            "AND resulting_lifecycle = 'active'"
        ),
        "ck_spc_creation_receipts_canonical_size": (
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536"
        ),
    },
    "player_character_mutation_receipts": {
        "ck_spc_mutation_receipts_identity_opaque": (
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_mutation_receipts_operation_opaque": (
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_mutation_receipts_result_identity_opaque": (
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'"
        ),
        "ck_spc_mutation_receipts_protocol": (
            "operation_namespace = 'player-character.mutate/v1' "
            "AND result_schema_version = 'player-character.mutate-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1'"
        ),
        "ck_spc_mutation_receipts_owner_result": (
            "player_character_id = result_player_character_id"
        ),
        "ck_spc_mutation_receipts_revision_successor": (
            "expected_revision BETWEEN 1 AND 9223372036854775806 "
            "AND resulting_revision = expected_revision + 1 "
            "AND resulting_revision <= 9223372036854775807"
        ),
        "ck_spc_mutation_receipts_result": (
            "(command_kind = 'RETIRE' AND result_command_kind = 'RETIRE' "
            "AND command_result = 'RETIRED' "
            "AND resulting_lifecycle = 'retired') "
            "OR (command_kind = 'FINAL_DEATH' "
            "AND result_command_kind = 'FINAL_DEATH' "
            "AND command_result = 'DECEASED' "
            "AND resulting_lifecycle = 'deceased')"
        ),
        "ck_spc_mutation_receipts_canonical_size": (
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536"
        ),
    },
}


def _normalize_sql(value: Any) -> str:
    return " ".join(str(value).split())


def _column_signature(table: sa.Table) -> tuple[tuple[Any, ...], ...]:
    dialect = mysql.dialect()
    return tuple(
        (
            column.name,
            column.type.compile(dialect=dialect),
            column.nullable,
            column.primary_key,
            column.default,
            column.server_default,
        )
        for column in table.columns
    )


def _unique_signature(table: sa.Table) -> dict[str, tuple[str, ...]]:
    return {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
        and constraint.name is not None
    }


def _index_signature(
    table: sa.Table,
) -> dict[str, tuple[bool, tuple[str, ...]]]:
    return {
        index.name: (
            index.unique,
            tuple(column.name for column in index.columns),
        )
        for index in table.indexes
    }


def _foreign_key_signature(
    table: sa.Table,
) -> dict[str, tuple[Any, ...]]:
    return {
        constraint.name: (
            table.name,
            tuple(column.name for column in constraint.columns),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
            constraint.onupdate,
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
        if constraint.name is not None
    }


def _check_signature(table: sa.Table) -> dict[str, str]:
    return {
        constraint.name: _normalize_sql(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
        and constraint.name is not None
    }


def _table_signature(table: sa.Table) -> tuple[Any, ...]:
    return (
        _column_signature(table),
        tuple(column.name for column in table.primary_key.columns),
        _unique_signature(table),
        _index_signature(table),
        _foreign_key_signature(table),
        _check_signature(table),
        table.dialect_options["mysql"]["engine"],
        table.dialect_options["mysql"]["charset"],
        table.dialect_options["mysql"]["collate"],
    )


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"spc_phase_2_migration_{uuid4().hex}",
        MIGRATION_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _MigrationRecorder:
    def __init__(self) -> None:
        self.metadata = sa.MetaData()
        self.events: list[tuple[Any, ...]] = []

    def create_table(
        self,
        table_name: str,
        *elements: Any,
        **options: Any,
    ) -> None:
        self.events.append(("create_table", table_name))
        sa.Table(table_name, self.metadata, *elements, **options)

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        unique: bool = False,
        **_: Any,
    ) -> None:
        self.events.append(("create_index", index_name, table_name))
        table = self.metadata.tables[table_name]
        sa.Index(
            index_name,
            *(table.c[column_name] for column_name in columns),
            unique=unique,
        )

    def create_foreign_key(
        self,
        constraint_name: str,
        source_table: str,
        referent_table: str,
        local_columns: tuple[str, ...],
        remote_columns: tuple[str, ...],
        **options: Any,
    ) -> None:
        self.events.append(
            ("create_foreign_key", constraint_name, source_table)
        )
        constraint = sa.ForeignKeyConstraint(
            local_columns,
            tuple(
                f"{referent_table}.{column_name}"
                for column_name in remote_columns
            ),
            name=constraint_name,
            ondelete=options.get("ondelete"),
            onupdate=options.get("onupdate"),
        )
        self.metadata.tables[source_table].append_constraint(constraint)


def _record_migration_upgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> _MigrationRecorder:
    migration = _load_migration()
    recorder = _MigrationRecorder()
    monkeypatch.setattr(migration.op, "create_table", recorder.create_table)
    monkeypatch.setattr(migration.op, "create_index", recorder.create_index)
    monkeypatch.setattr(
        migration.op,
        "create_foreign_key",
        recorder.create_foreign_key,
    )
    migration.upgrade()
    return recorder


def test_phase_2_metadata_has_exact_six_table_contract() -> None:
    assert set(Base.metadata.tables) == LEGACY_MAPPED_TABLES | PHASE_2_TABLE_SET

    for table_name in PHASE_2_TABLES:
        table = Base.metadata.tables[table_name]
        expected_columns = tuple(
            (name, sql_type, nullable, primary_key, None, None)
            for name, sql_type, nullable, primary_key in EXPECTED_COLUMNS[
                table_name
            ]
        )
        assert _column_signature(table) == expected_columns
        assert tuple(
            column.name for column in table.primary_key.columns
        ) == EXPECTED_PRIMARY_KEYS[table_name]
        assert _unique_signature(table) == EXPECTED_UNIQUES[table_name]
        assert _index_signature(table) == EXPECTED_INDEXES[table_name]
        assert _check_signature(table) == {
            name: _normalize_sql(expression)
            for name, expression in EXPECTED_CHECKS[table_name].items()
        }
        assert table.dialect_options["mysql"]["engine"] == "InnoDB"
        assert table.dialect_options["mysql"]["charset"] == "utf8mb4"
        assert table.dialect_options["mysql"]["collate"] == "utf8mb4_bin"

    observed_foreign_keys = {}
    for table_name in PHASE_2_TABLES:
        observed_foreign_keys.update(
            _foreign_key_signature(Base.metadata.tables[table_name])
        )
    assert observed_foreign_keys == {
        name: (*definition, "RESTRICT", "RESTRICT")
        for name, definition in EXPECTED_FOREIGN_KEYS.items()
    }


def test_migration_metadata_matches_orm_and_adds_indexes_before_foreign_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _record_migration_upgrade(monkeypatch)

    assert tuple(recorder.metadata.tables) == PHASE_2_TABLES
    for table_name in PHASE_2_TABLES:
        assert _table_signature(recorder.metadata.tables[table_name]) == (
            _table_signature(Base.metadata.tables[table_name])
        )

    first_foreign_key = next(
        index
        for index, event in enumerate(recorder.events)
        if event[0] == "create_foreign_key"
    )
    assert all(
        event[0] != "create_index"
        for event in recorder.events[first_foreign_key:]
    )
    assert sum(
        event[0] == "create_foreign_key" for event in recorder.events
    ) == 12


def test_migration_is_one_linear_head_after_0003() -> None:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == [MIGRATION_REVISION]
    revision = scripts.get_revision(MIGRATION_REVISION)
    assert revision is not None
    assert revision.down_revision == MIGRATION_PARENT
    assert tuple(
        item.revision for item in scripts.walk_revisions()
    ) == (
        "20260728_0004",
        "20260719_0003",
        "20260719_0002",
        "20260719_0001",
    )


class _ScalarResult:
    def __init__(self, value: int | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> int | None:
        return self.value


class _DowngradeGuardConnection:
    def __init__(
        self,
        populated_table: str | None,
        events: list[tuple[Any, ...]],
    ) -> None:
        self.populated_table = populated_table
        self.events = events

    def execute(self, statement: Any) -> _ScalarResult:
        match = re.search(r"`([^`]+)`", str(statement))
        assert match is not None
        table_name = match.group(1)
        self.events.append(("probe", table_name))
        return _ScalarResult(
            1 if table_name == self.populated_table else None
        )


def _patch_downgrade_operations(
    migration: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    *,
    populated_table: str | None,
) -> list[tuple[Any, ...]]:
    events: list[tuple[Any, ...]] = []
    connection = _DowngradeGuardConnection(populated_table, events)
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    def record(operation: str) -> Any:
        def recorder(*args: Any, **kwargs: Any) -> None:
            events.append((operation, *args, kwargs))

        return recorder

    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        record("drop_constraint"),
    )
    monkeypatch.setattr(migration.op, "drop_index", record("drop_index"))
    monkeypatch.setattr(migration.op, "drop_table", record("drop_table"))
    return events


@pytest.mark.parametrize("populated_table", PHASE_2_TABLES)
def test_downgrade_refuses_each_populated_family_before_destructive_ddl(
    monkeypatch: pytest.MonkeyPatch,
    populated_table: str,
) -> None:
    migration = _load_migration()
    events = _patch_downgrade_operations(
        migration,
        monkeypatch,
        populated_table=populated_table,
    )

    with pytest.raises(RuntimeError, match=populated_table):
        migration.downgrade()

    assert tuple(event[0] for event in events) == ("probe",) * 6
    assert tuple(event[1] for event in events) == PHASE_2_TABLES


def test_empty_downgrade_probes_every_family_before_safe_reverse_drop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    events = _patch_downgrade_operations(
        migration,
        monkeypatch,
        populated_table=None,
    )

    migration.downgrade()

    assert tuple(event[0] for event in events[:6]) == ("probe",) * 6
    assert tuple(event[1] for event in events[:6]) == PHASE_2_TABLES
    assert tuple(
        event[1] for event in events if event[0] == "drop_table"
    ) == (
        "player_character_mutation_receipts",
        "player_character_creation_receipts",
        "player_character_current",
        "player_character_revisions",
        "player_character_id_allocations",
        "player_character_controller_bindings",
    )


def test_upgrade_propagates_ddl_failure_without_backfill_or_later_ddl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_migration()
    attempts: list[str] = []

    def fail_on_revisions(table_name: str, *_: Any, **__: Any) -> None:
        attempts.append(table_name)
        if table_name == "player_character_revisions":
            raise RuntimeError("injected DDL failure")

    def unexpected_later_operation(*_: Any, **__: Any) -> None:
        pytest.fail("migration continued after the injected DDL failure")

    monkeypatch.setattr(migration.op, "create_table", fail_on_revisions)
    monkeypatch.setattr(
        migration.op,
        "create_index",
        unexpected_later_operation,
    )
    monkeypatch.setattr(
        migration.op,
        "create_foreign_key",
        unexpected_later_operation,
    )

    with pytest.raises(RuntimeError, match="injected DDL failure"):
        migration.upgrade()

    assert attempts == [
        "player_character_controller_bindings",
        "player_character_id_allocations",
        "player_character_revisions",
    ]


def _expected_mysql_column_type(sql_type: str) -> str:
    if sql_type.startswith("VARCHAR"):
        return sql_type.split(" CHARACTER SET", 1)[0].lower()
    return sql_type.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_phase_2_schema_is_exact(
    mysql_engine: AsyncEngine,
) -> None:
    async with mysql_engine.connect() as connection:
        tables = (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION "
                    "FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME LIKE 'player_character_%'"
                )
            )
        ).all()
        columns = (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, "
                    "IS_NULLABLE, COLUMN_DEFAULT, CHARACTER_SET_NAME, "
                    "COLLATION_NAME, DATETIME_PRECISION, ORDINAL_POSITION "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME LIKE 'player_character_%' "
                    "ORDER BY TABLE_NAME, ORDINAL_POSITION"
                )
            )
        ).all()
        index_rows = (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, "
                    "COLUMN_NAME, NON_UNIQUE "
                    "FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME LIKE 'player_character_%' "
                    "ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
                )
            )
        ).all()
        foreign_key_rows = (
            await connection.execute(
                text(
                    "SELECT k.CONSTRAINT_NAME, k.TABLE_NAME, k.COLUMN_NAME, "
                    "k.ORDINAL_POSITION, k.REFERENCED_TABLE_NAME, "
                    "k.REFERENCED_COLUMN_NAME, r.UPDATE_RULE, r.DELETE_RULE "
                    "FROM information_schema.KEY_COLUMN_USAGE AS k "
                    "JOIN information_schema.REFERENTIAL_CONSTRAINTS AS r "
                    "ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA "
                    "AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME "
                    "AND r.TABLE_NAME = k.TABLE_NAME "
                    "WHERE k.CONSTRAINT_SCHEMA = DATABASE() "
                    "AND k.TABLE_NAME LIKE 'player_character_%' "
                    "AND k.REFERENCED_TABLE_NAME IS NOT NULL "
                    "ORDER BY k.CONSTRAINT_NAME, k.ORDINAL_POSITION"
                )
            )
        ).all()
        check_rows = (
            await connection.execute(
                text(
                    "SELECT CONSTRAINT_NAME, TABLE_NAME, ENFORCED "
                    "FROM information_schema.TABLE_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() "
                    "AND TABLE_NAME LIKE 'player_character_%' "
                    "AND CONSTRAINT_TYPE = 'CHECK'"
                )
            )
        ).all()
        counts = {
            table_name: (
                await connection.execute(
                    text(f"SELECT COUNT(*) FROM `{table_name}`")
                )
            ).scalar_one()
            for table_name in PHASE_2_TABLES
        }

    assert {
        row[0]: (row[1], row[2])
        for row in tables
    } == {
        table_name: ("InnoDB", "utf8mb4_bin")
        for table_name in PHASE_2_TABLES
    }

    actual_columns: dict[str, list[tuple[Any, ...]]] = {
        table_name: [] for table_name in PHASE_2_TABLES
    }
    for row in columns:
        actual_columns[row[0]].append(tuple(row[1:]))
    for table_name, expected in EXPECTED_COLUMNS.items():
        assert actual_columns[table_name] == [
            (
                name,
                _expected_mysql_column_type(sql_type),
                "YES" if nullable else "NO",
                None,
                "ascii" if sql_type.startswith("VARCHAR") else None,
                "ascii_bin" if sql_type.startswith("VARCHAR") else None,
                6 if sql_type == "DATETIME(6)" else None,
                ordinal,
            )
            for ordinal, (
                name,
                sql_type,
                nullable,
                _primary_key,
            ) in enumerate(expected, start=1)
        ]

    actual_indexes: dict[
        str,
        dict[str, tuple[bool, tuple[str, ...]]],
    ] = {table_name: {} for table_name in PHASE_2_TABLES}
    for table_name in PHASE_2_TABLES:
        table_rows = [row for row in index_rows if row[0] == table_name]
        for index_name in {row[1] for row in table_rows}:
            ordered = [
                row for row in table_rows if row[1] == index_name
            ]
            actual_indexes[table_name][index_name] = (
                not bool(ordered[0][4]),
                tuple(row[3] for row in ordered),
            )

    expected_mysql_indexes = {}
    for table_name in PHASE_2_TABLES:
        expected_mysql_indexes[table_name] = {
            "PRIMARY": (True, EXPECTED_PRIMARY_KEYS[table_name]),
            **{
                name: (True, columns)
                for name, columns in EXPECTED_UNIQUES[table_name].items()
            },
            **{
                name: (unique, columns)
                for name, (unique, columns) in EXPECTED_INDEXES[
                    table_name
                ].items()
            },
        }
    assert actual_indexes == expected_mysql_indexes

    expected_foreign_key_rows = {
        (
            constraint_name,
            table_name,
            local_column,
            ordinal,
            referred_table,
            remote_column,
            "RESTRICT",
            "RESTRICT",
        )
        for constraint_name, (
            table_name,
            local_columns,
            referred_table,
            remote_columns,
        ) in EXPECTED_FOREIGN_KEYS.items()
        for ordinal, (
            local_column,
            remote_column,
        ) in enumerate(zip(local_columns, remote_columns), start=1)
    }
    assert set(foreign_key_rows) == expected_foreign_key_rows

    expected_checks = {
        (check_name, table_name, "YES")
        for table_name, checks in EXPECTED_CHECKS.items()
        for check_name in checks
    }
    assert set(check_rows) == expected_checks
    assert counts == {table_name: 0 for table_name in PHASE_2_TABLES}


async def _insert_revision_test_parents(
    connection: AsyncConnection,
    *,
    player_character_id: str,
    controller_binding: str,
) -> None:
    await connection.execute(
        text(
            "INSERT INTO player_character_controller_bindings "
            "(controller_binding, created_at) "
            "VALUES (:controller_binding, UTC_TIMESTAMP(6))"
        ),
        {"controller_binding": controller_binding},
    )
    await connection.execute(
        text(
            "INSERT INTO player_character_id_allocations "
            "(player_character_id, created_at) "
            "VALUES (:player_character_id, UTC_TIMESTAMP(6))"
        ),
        {"player_character_id": player_character_id},
    )


async def _insert_revision_test_row(
    connection: AsyncConnection,
    *,
    player_character_id: str,
    controller_binding: str,
    record_revision: int,
    prior_revision: int | None,
    mutation_kind: str,
    lifecycle: str,
    authority_class: str,
) -> None:
    await connection.execute(
        text(
            "INSERT INTO player_character_revisions "
            "(player_character_id, record_revision, contract_version, "
            "controller_binding, lifecycle, prior_revision, mutation_kind, "
            "authority_class, source_reference, record_canonical, created_at) "
            "VALUES (:player_character_id, :record_revision, "
            "'structured-player-character/v1', :controller_binding, "
            ":lifecycle, :prior_revision, :mutation_kind, :authority_class, "
            ":source_reference, :record_canonical, UTC_TIMESTAMP(6))"
        ),
        {
            "player_character_id": player_character_id,
            "record_revision": record_revision,
            "controller_binding": controller_binding,
            "lifecycle": lifecycle,
            "prior_revision": prior_revision,
            "mutation_kind": mutation_kind,
            "authority_class": authority_class,
            "source_reference": f"source.{mutation_kind.lower()}",
            "record_canonical": mutation_kind.encode("ascii"),
        },
    )


async def _assert_revision_test_rows_absent(
    mysql_engine: AsyncEngine,
    *,
    player_character_id: str,
    controller_binding: str,
) -> None:
    async with mysql_engine.connect() as connection:
        revision = (
            await connection.execute(
                text("SELECT version_num FROM alembic_version")
            )
        ).scalar_one()
        revision_count = (
            await connection.execute(
                text(
                    "SELECT COUNT(*) FROM player_character_revisions "
                    "WHERE player_character_id = :player_character_id"
                ),
                {"player_character_id": player_character_id},
            )
        ).scalar_one()
        allocation_count = (
            await connection.execute(
                text(
                    "SELECT COUNT(*) FROM player_character_id_allocations "
                    "WHERE player_character_id = :player_character_id"
                ),
                {"player_character_id": player_character_id},
            )
        ).scalar_one()
        binding_count = (
            await connection.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM player_character_controller_bindings "
                    "WHERE controller_binding = :controller_binding"
                ),
                {"controller_binding": controller_binding},
            )
        ).scalar_one()

    assert revision == MIGRATION_REVISION
    assert (revision_count, allocation_count, binding_count) == (0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation_kind", "lifecycle", "authority_class"),
    (
        ("RETIRE", "retired", "authenticated-controller"),
        ("FINAL_DEATH", "deceased", "trusted-server-outcome"),
    ),
)
async def test_mysql_revision_provenance_rejects_null_prior_for_mutation(
    mysql_engine: AsyncEngine,
    mutation_kind: str,
    lifecycle: str,
    authority_class: str,
) -> None:
    suffix = uuid4().hex
    player_character_id = f"pc.null-prior-{suffix}"
    controller_binding = f"binding.null-prior-{suffix}"

    async with mysql_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await _insert_revision_test_parents(
                connection,
                player_character_id=player_character_id,
                controller_binding=controller_binding,
            )
            await _insert_revision_test_row(
                connection,
                player_character_id=player_character_id,
                controller_binding=controller_binding,
                record_revision=1,
                prior_revision=None,
                mutation_kind="CREATE",
                lifecycle="active",
                authority_class="trusted-creation",
            )

            with pytest.raises(DBAPIError) as exc_info:
                await _insert_revision_test_row(
                    connection,
                    player_character_id=player_character_id,
                    controller_binding=controller_binding,
                    record_revision=2,
                    prior_revision=None,
                    mutation_kind=mutation_kind,
                    lifecycle=lifecycle,
                    authority_class=authority_class,
                )

            assert exc_info.value.orig.args[0] == 3819
            assert (
                "ck_spc_revisions_provenance_matrix"
                in str(exc_info.value.orig)
            )
        finally:
            await transaction.rollback()

    await _assert_revision_test_rows_absent(
        mysql_engine,
        player_character_id=player_character_id,
        controller_binding=controller_binding,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_revision_provenance_accepts_creation_and_mutations(
    mysql_engine: AsyncEngine,
) -> None:
    suffix = uuid4().hex
    player_character_id = f"pc.valid-provenance-{suffix}"
    controller_binding = f"binding.valid-provenance-{suffix}"

    async with mysql_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await _insert_revision_test_parents(
                connection,
                player_character_id=player_character_id,
                controller_binding=controller_binding,
            )
            for (
                record_revision,
                prior_revision,
                mutation_kind,
                lifecycle,
                authority_class,
            ) in (
                (1, None, "CREATE", "active", "trusted-creation"),
                (
                    2,
                    1,
                    "RETIRE",
                    "retired",
                    "authenticated-controller",
                ),
                (
                    3,
                    2,
                    "FINAL_DEATH",
                    "deceased",
                    "trusted-server-outcome",
                ),
            ):
                await _insert_revision_test_row(
                    connection,
                    player_character_id=player_character_id,
                    controller_binding=controller_binding,
                    record_revision=record_revision,
                    prior_revision=prior_revision,
                    mutation_kind=mutation_kind,
                    lifecycle=lifecycle,
                    authority_class=authority_class,
                )

            rows = (
                await connection.execute(
                    text(
                        "SELECT record_revision, prior_revision, mutation_kind "
                        "FROM player_character_revisions "
                        "WHERE player_character_id = :player_character_id "
                        "ORDER BY record_revision"
                    ),
                    {"player_character_id": player_character_id},
                )
            ).all()
            assert rows == [
                (1, None, "CREATE"),
                (2, 1, "RETIRE"),
                (3, 2, "FINAL_DEATH"),
            ]
        finally:
            await transaction.rollback()

    await _assert_revision_test_rows_absent(
        mysql_engine,
        player_character_id=player_character_id,
        controller_binding=controller_binding,
    )


def _validated_test_database_url() -> str:
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip(
            "TEST_DATABASE_URL is not configured; no SQLite fallback is used"
        )
    url = make_url(value)
    if url.drivername != "mysql+asyncmy":
        pytest.fail("TEST_DATABASE_URL must use mysql+asyncmy")
    if url.database != "deviation_protocol_test":
        pytest.fail(
            "integration tests may only use deviation_protocol_test"
        )
    return value


def _alembic_config() -> Config:
    return Config(str(REPOSITORY_ROOT / "alembic.ini"))


async def _phase_2_database_state(
    database_url: str,
) -> tuple[str, set[str], dict[str, int]]:
    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            revision = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()
            tables = set(
                (
                    await connection.execute(
                        text(
                            "SELECT TABLE_NAME "
                            "FROM information_schema.TABLES "
                            "WHERE TABLE_SCHEMA = DATABASE() "
                            "AND TABLE_NAME LIKE 'player_character_%'"
                        )
                    )
                ).scalars()
            )
            counts = {
                table_name: (
                    await connection.execute(
                        text(f"SELECT COUNT(*) FROM `{table_name}`")
                    )
                ).scalar_one()
                for table_name in tables
            }
        return revision, tables, counts
    finally:
        await engine.dispose()


async def _legacy_database_snapshot(
    database_url: str,
) -> tuple[Any, ...]:
    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            columns = (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, "
                        "IS_NULLABLE, COLUMN_DEFAULT, ORDINAL_POSITION "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
                    )
                )
            ).all()
            indexes = (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, "
                        "COLUMN_NAME, NON_UNIQUE "
                        "FROM information_schema.STATISTICS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX"
                    )
                )
            ).all()
            constraints = (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE "
                        "FROM information_schema.TABLE_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE() "
                        "ORDER BY TABLE_NAME, CONSTRAINT_NAME"
                    )
                )
            ).all()
            counts = {
                table_name: (
                    await connection.execute(
                        text(f"SELECT COUNT(*) FROM `{table_name}`")
                    )
                ).scalar_one()
                for table_name in LEGACY_MAPPED_TABLES
            }
        return (
            tuple(row for row in columns if row[0] in LEGACY_MAPPED_TABLES),
            tuple(row for row in indexes if row[0] in LEGACY_MAPPED_TABLES),
            tuple(
                row for row in constraints
                if row[0] in LEGACY_MAPPED_TABLES
            ),
            counts,
        )
    finally:
        await engine.dispose()


def test_mysql_empty_schema_downgrade_and_upgrade_preserve_legacy_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _validated_test_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()

    revision, tables, counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert revision == MIGRATION_REVISION
    assert tables == PHASE_2_TABLE_SET
    assert counts == {table_name: 0 for table_name in PHASE_2_TABLES}
    legacy_before = asyncio.run(_legacy_database_snapshot(database_url))

    try:
        command.downgrade(config, MIGRATION_PARENT)
        downgraded_revision, downgraded_tables, downgraded_counts = (
            asyncio.run(_phase_2_database_state(database_url))
        )
        assert downgraded_revision == MIGRATION_PARENT
        assert downgraded_tables == set()
        assert downgraded_counts == {}
        assert asyncio.run(
            _legacy_database_snapshot(database_url)
        ) == legacy_before

        command.upgrade(config, MIGRATION_REVISION)
    finally:
        command.upgrade(config, MIGRATION_REVISION)

    upgraded_revision, upgraded_tables, upgraded_counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert upgraded_revision == MIGRATION_REVISION
    assert upgraded_tables == PHASE_2_TABLE_SET
    assert upgraded_counts == {
        table_name: 0 for table_name in PHASE_2_TABLES
    }
    assert asyncio.run(_legacy_database_snapshot(database_url)) == legacy_before


async def _insert_owned_binding(
    database_url: str,
    controller_binding: str,
) -> None:
    engine = create_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO player_character_controller_bindings "
                    "(controller_binding, created_at) "
                    "VALUES (:controller_binding, UTC_TIMESTAMP(6))"
                ),
                {"controller_binding": controller_binding},
            )
    finally:
        await engine.dispose()


async def _delete_owned_binding(
    database_url: str,
    controller_binding: str,
) -> None:
    engine = create_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM player_character_controller_bindings "
                    "WHERE controller_binding = :controller_binding"
                ),
                {"controller_binding": controller_binding},
            )
    finally:
        await engine.dispose()


def test_mysql_downgrade_refuses_data_before_removing_any_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = _validated_test_database_url()
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    controller_binding = f"downgrade.guard-{uuid4().hex}"

    revision, tables, counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert revision == MIGRATION_REVISION
    assert tables == PHASE_2_TABLE_SET
    assert counts == {table_name: 0 for table_name in PHASE_2_TABLES}

    asyncio.run(_insert_owned_binding(database_url, controller_binding))
    try:
        with pytest.raises(
            RuntimeError,
            match=(
                "Refusing to downgrade structured player-character Phase 2"
            ),
        ):
            command.downgrade(config, MIGRATION_PARENT)

        guarded_revision, guarded_tables, guarded_counts = asyncio.run(
            _phase_2_database_state(database_url)
        )
        assert guarded_revision == MIGRATION_REVISION
        assert guarded_tables == PHASE_2_TABLE_SET
        assert guarded_counts == {
            **{table_name: 0 for table_name in PHASE_2_TABLES},
            "player_character_controller_bindings": 1,
        }
    finally:
        asyncio.run(
            _delete_owned_binding(database_url, controller_binding)
        )
        command.upgrade(config, MIGRATION_REVISION)

    final_revision, final_tables, final_counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert final_revision == MIGRATION_REVISION
    assert final_tables == PHASE_2_TABLE_SET
    assert final_counts == {
        table_name: 0 for table_name in PHASE_2_TABLES
    }
