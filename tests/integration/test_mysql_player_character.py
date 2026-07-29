from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_creation_receipt_protocol,
    evaluate_mutation_policy,
    evaluate_mutation_receipt_protocol,
    mutation_fingerprint,
    recover_creation_unique_race_winner,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    Declaration,
    DistinguishingFeatures,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerDeclaredText,
    PlayerSubjectiveAuthority,
    canonical_player_declaration_bytes,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
    TrustedFinalDeathEvidence,
)
from deviation_protocol.infrastructure.database import create_engine
from deviation_protocol.infrastructure.errors import (
    PlayerCharacterRepositoryConflictError,
)
from deviation_protocol.infrastructure.orm_models import (
    Base,
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
)
from deviation_protocol.infrastructure.player_character_persistence import (
    PlayerCharacterStoredRecordIntegrityError,
    canonical_record_to_storage_bytes,
    canonical_state_record_fingerprint,
    creation_operation_evidence_from_storage,
    creation_receipt_to_storage_bytes,
    fingerprint_to_storage_bytes,
    mutation_operation_evidence_from_storage,
    mutation_operation_evidence_to_storage_bytes,
    mutation_receipt_to_storage_bytes,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyPlayerCharacterCreationReceiptRepository,
    SqlAlchemyPlayerCharacterMutationReceiptRepository,
    SqlAlchemyPlayerCharacterRepository,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    REPOSITORY_ROOT
    / "alembic"
    / "versions"
    / "20260728_0004_structured_player_character_phase_2.py"
)
MIGRATION_REVISION = "20260728_0004"
MIGRATION_PARENT = "20260719_0003"
CURRENT_HEAD_REVISION = "20260729_0005"

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
MINIMUM_RUN_CORE_TABLES = {
    "run_current",
    "run_revisions",
    "run_session_participations",
    "run_creation_receipts",
    "run_mutation_receipts",
}

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
    assert set(Base.metadata.tables) == (
        LEGACY_MAPPED_TABLES
        | PHASE_2_TABLE_SET
        | MINIMUM_RUN_CORE_TABLES
    )

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

    assert scripts.get_heads() == [CURRENT_HEAD_REVISION]
    revision = scripts.get_revision(MIGRATION_REVISION)
    assert revision is not None
    assert revision.down_revision == MIGRATION_PARENT
    assert tuple(
        item.revision for item in scripts.walk_revisions()
    ) == (
        CURRENT_HEAD_REVISION,
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

    assert revision == CURRENT_HEAD_REVISION
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
    assert revision == CURRENT_HEAD_REVISION
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

        command.upgrade(config, CURRENT_HEAD_REVISION)
    finally:
        command.upgrade(config, CURRENT_HEAD_REVISION)

    upgraded_revision, upgraded_tables, upgraded_counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert upgraded_revision == CURRENT_HEAD_REVISION
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
    assert revision == CURRENT_HEAD_REVISION
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
        command.upgrade(config, CURRENT_HEAD_REVISION)

    final_revision, final_tables, final_counts = asyncio.run(
        _phase_2_database_state(database_url)
    )
    assert final_revision == CURRENT_HEAD_REVISION
    assert final_tables == PHASE_2_TABLE_SET
    assert final_counts == {
        table_name: 0 for table_name in PHASE_2_TABLES
    }


_REPOSITORY_TEST_TIME = datetime(
    2026,
    7,
    28,
    15,
    16,
    17,
    123456,
    tzinfo=UTC,
)
_REPOSITORY_CAS_WINNER_TIME = datetime(
    2026,
    7,
    28,
    15,
    16,
    18,
    123456,
    tzinfo=UTC,
)
_REPOSITORY_CAS_LOSER_TIME = datetime(
    2026,
    7,
    28,
    15,
    16,
    19,
    123456,
    tzinfo=UTC,
)
_ASYNC_COORDINATION_TIMEOUT = 5.0
_EXPECTED_ROW_BLOCK_TIMEOUT = 0.2


@dataclass(frozen=True, slots=True)
class _RepositoryCharacter:
    creation_command: CharacterCreationCommand
    initial: CanonicalPlayerCharacter
    creation_receipt: StoredCreationSuccessReceipt
    mutation_command: CharacterMutationCommand
    successor: CanonicalPlayerCharacter
    mutation_receipt: StoredMutationSuccessReceipt


@dataclass(slots=True)
class _RepositoryTestScope:
    token: str
    characters: list[_RepositoryCharacter] = field(default_factory=list)

    def character(
        self,
        suffix: str,
        **options: Any,
    ) -> _RepositoryCharacter:
        character = _build_repository_character(
            f"{self.token}-{suffix}",
            **options,
        )
        self.characters.append(character)
        return character


def _build_repository_character(
    label: str,
    *,
    creation_command: CharacterCreationCommand | None = None,
    player_character_id: PlayerCharacterId | None = None,
    controller_binding: ControllerBindingRef | None = None,
) -> _RepositoryCharacter:
    player_character_id = player_character_id or PlayerCharacterId(
        value=f"pc.repo-{label}"
    )
    controller_binding = controller_binding or ControllerBindingRef(
        value=f"binding.repo-{label}"
    )
    creation_command = creation_command or CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    initial = CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=controller_binding,
        character_core=creation_command.character_core,
        narration_preferences=creation_command.narration_preferences,
        source_reference=AuthoritySourceRef(value=f"source.create-{label}"),
    )
    creation_operation_id = PlayerCharacterOperationId(
        value=f"operation.create-{label}"
    )
    _, creation_operation_fingerprint = creation_fingerprint(
        creation_command
    )
    creation_receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=controller_binding,
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=creation_operation_id,
        ),
        fingerprint=creation_operation_fingerprint,
        result=CreationSuccessResult(
            result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=initial.contract_version,
            resulting_revision=initial.record_revision,
            resulting_lifecycle=initial.lifecycle,
        ),
    )

    mutation_operation_id = PlayerCharacterOperationId(
        value=f"operation.mutate-{label}"
    )
    mutation_command = CharacterMutationCommand(
        contract_version=initial.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=player_character_id,
        expected_revision=initial.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=player_character_id,
            contract_version=initial.contract_version,
            record_revision=initial.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=player_character_id,
            expected_revision=initial.record_revision,
            operation_id=mutation_operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value=f"source.retire-{label}"
            ),
        ),
    )
    mutation_decision = evaluate_mutation_policy(
        initial,
        command=mutation_command,
        operation_id=mutation_operation_id,
    )
    assert mutation_decision.accepted
    assert mutation_decision.resulting_record is not None
    successor = mutation_decision.resulting_record
    _, mutation_operation_fingerprint = mutation_fingerprint(
        mutation_command,
        operation_id=mutation_operation_id,
    )
    mutation_receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=mutation_operation_id,
        ),
        fingerprint=mutation_operation_fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=player_character_id,
            contract_version=successor.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
    )
    return _RepositoryCharacter(
        creation_command=creation_command,
        initial=initial,
        creation_receipt=creation_receipt,
        mutation_command=mutation_command,
        successor=successor,
        mutation_receipt=mutation_receipt,
    )


def _repository_player_text(value: str) -> PlayerDeclaredText:
    return PlayerDeclaredText(
        authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
        text=value,
    )


def _repository_name_command(value: str) -> CharacterCreationCommand:
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=Declaration[PlayerDeclaredText].declared(
                _repository_player_text(value)
            )
        ),
        narration_preferences=NarrationPreferences(),
    )


def _repository_feature_command(feature_count: int) -> CharacterCreationCommand:
    features = tuple(
        _repository_player_text(f"repository-feature-{index:03d}")
        for index in range(feature_count)
    )
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            distinguishing_features=Declaration[
                DistinguishingFeatures
            ].declared(DistinguishingFeatures(features=features))
        ),
        narration_preferences=NarrationPreferences(),
    )


async def _stage_repository_creation(
    session: AsyncSession,
    character: _RepositoryCharacter,
) -> None:
    binding_repository = SqlAlchemyControllerBindingRegistryRepository(
        session
    )
    character_repository = SqlAlchemyPlayerCharacterRepository(session)
    receipt_repository = (
        SqlAlchemyPlayerCharacterCreationReceiptRepository(session)
    )
    await binding_repository.add(
        character.initial.controller_binding,
        created_at=_REPOSITORY_TEST_TIME,
    )
    await character_repository.add_allocation(
        character.initial.player_character_id,
        created_at=_REPOSITORY_TEST_TIME,
    )
    await character_repository.add_initial(
        character.initial,
        created_at=_REPOSITORY_TEST_TIME,
    )
    await receipt_repository.add(
        character.creation_receipt,
        created_at=_REPOSITORY_TEST_TIME,
    )


async def _stage_repository_mutation(
    session: AsyncSession,
    character: _RepositoryCharacter,
) -> None:
    character_repository = SqlAlchemyPlayerCharacterRepository(session)
    receipt_repository = (
        SqlAlchemyPlayerCharacterMutationReceiptRepository(session)
    )
    assert (
        await character_repository.get_for_update(
            character.initial.player_character_id
        )
        == character.initial
    )
    await character_repository.append_revision(
        character.successor,
        created_at=_REPOSITORY_TEST_TIME,
    )
    assert await character_repository.compare_and_swap_current(
        character.successor,
        expected_revision=character.initial.record_revision.value,
        created_at=_REPOSITORY_TEST_TIME,
    )
    await receipt_repository.add(
        character.mutation_receipt,
        created_at=_REPOSITORY_TEST_TIME,
    )


@pytest.fixture
async def repository_test_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> Any:
    scope = _RepositoryTestScope(token=uuid4().hex)
    try:
        yield scope
    finally:
        character_ids = tuple(
            character.initial.player_character_id.value
            for character in scope.characters
        )
        controller_bindings = tuple(
            character.initial.controller_binding.value
            for character in scope.characters
        )
        if not character_ids:
            return
        async with mysql_session_factory.begin() as session:
            await session.execute(
                sa.delete(PlayerCharacterMutationReceiptRow).where(
                    PlayerCharacterMutationReceiptRow.player_character_id.in_(
                        character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterCreationReceiptRow).where(
                    PlayerCharacterCreationReceiptRow.result_player_character_id.in_(
                        character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterCurrentRow).where(
                    PlayerCharacterCurrentRow.player_character_id.in_(
                        character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterRevisionRow).where(
                    PlayerCharacterRevisionRow.player_character_id.in_(
                        character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterIdAllocationRow).where(
                    PlayerCharacterIdAllocationRow.player_character_id.in_(
                        character_ids
                    )
                )
            )
            await session.execute(
                sa.delete(PlayerCharacterControllerBindingRow).where(
                    PlayerCharacterControllerBindingRow.controller_binding.in_(
                        controller_bindings
                    )
                )
            )
        async with mysql_session_factory() as session:
            residual = (
                await session.scalar(
                    sa.select(sa.func.count())
                    .select_from(PlayerCharacterRevisionRow)
                    .where(
                        PlayerCharacterRevisionRow.player_character_id.in_(
                            character_ids
                        )
                    )
                )
            )
        assert residual == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repositories_flush_inside_caller_transaction_and_rollback(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("rollback")
    async with mysql_session_factory() as session:
        await _stage_repository_creation(session, character)
        assert (
            await SqlAlchemyPlayerCharacterRepository(session).get(
                character.initial.player_character_id
            )
            == character.initial
        )
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(PlayerCharacterCreationReceiptRow)
                .where(
                    PlayerCharacterCreationReceiptRow.result_player_character_id
                    == character.initial.player_character_id.value
                )
            )
            == 1
        )
        await session.rollback()

    async with mysql_session_factory() as session:
        assert not await SqlAlchemyPlayerCharacterRepository(
            session
        ).allocation_exists(character.initial.player_character_id)
        assert (
            await SqlAlchemyControllerBindingRegistryRepository(session).get(
                character.initial.controller_binding
            )
            is None
        )
        assert (
            await SqlAlchemyPlayerCharacterCreationReceiptRepository(
                session
            ).get(character.creation_receipt.key)
            is None
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_creation_round_trip_replay_and_conflicts(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("creation")
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, character)

    async with mysql_session_factory() as session:
        binding_repository = SqlAlchemyControllerBindingRegistryRepository(
            session
        )
        character_repository = SqlAlchemyPlayerCharacterRepository(session)
        receipt_repository = (
            SqlAlchemyPlayerCharacterCreationReceiptRepository(session)
        )
        assert (
            await binding_repository.lock(
                character.initial.controller_binding
            )
            == character.initial.controller_binding
        )
        assert await character_repository.allocation_exists(
            character.initial.player_character_id
        )
        assert (
            await character_repository.get(
                character.initial.player_character_id
            )
            == character.initial
        )
        stored_receipt = await receipt_repository.get(
            character.creation_receipt.key
        )
        assert stored_receipt == character.creation_receipt
        stored_row = await session.scalar(
            sa.select(PlayerCharacterCreationReceiptRow).where(
                PlayerCharacterCreationReceiptRow.controller_binding
                == character.creation_receipt.key.controller_binding.value,
                PlayerCharacterCreationReceiptRow.operation_namespace
                == character.creation_receipt.key.operation_namespace.value,
                PlayerCharacterCreationReceiptRow.operation_id
                == character.creation_receipt.key.operation_id.value,
            )
        )
        assert stored_row is not None
        assert stored_row.fingerprint == fingerprint_to_storage_bytes(
            character.creation_receipt.fingerprint
        )
        assert stored_row.result_record_fingerprint == (
            canonical_state_record_fingerprint(character.initial)
        )
        assert stored_row.receipt_canonical == (
            creation_receipt_to_storage_bytes(character.creation_receipt)
        )
        assert creation_operation_evidence_from_storage(
            stored_row.operation_evidence_canonical
        ) == character.creation_command
        assert (
            stored_row.result_player_character_id
            == character.initial.player_character_id.value
        )
        assert (
            stored_row.resulting_revision
            == character.initial.record_revision.value
        )

        exact = evaluate_creation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            operation_id=character.creation_receipt.key.operation_id,
            command=character.creation_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        assert exact.code is CharacterOperationProtocolCode.EXACT_REPLAY
        conflicting_command = CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(
                name_or_code_name=Declaration.explicitly_absent()
            ),
            narration_preferences=NarrationPreferences(),
        )
        conflict = evaluate_creation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            operation_id=character.creation_receipt.key.operation_id,
            command=conflicting_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        assert (
            conflict.code
            is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )

    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError):
            await SqlAlchemyControllerBindingRegistryRepository(session).add(
                character.initial.controller_binding,
                created_at=_REPOSITORY_TEST_TIME,
            )
        await session.rollback()
    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError):
            await SqlAlchemyPlayerCharacterRepository(
                session
            ).add_allocation(
                character.initial.player_character_id,
                created_at=_REPOSITORY_TEST_TIME,
            )
        await session.rollback()
    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError):
            await SqlAlchemyPlayerCharacterCreationReceiptRepository(
                session
            ).add(
                character.creation_receipt,
                created_at=_REPOSITORY_TEST_TIME,
            )
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_preserves_declaration_bytes_and_has_no_65_feature_ceiling(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    exact_declaration_command = _repository_name_command(
        (chr(0xE9) * 32_410)
    )
    assert len(
        canonical_player_declaration_bytes(
            character_core=exact_declaration_command.character_core,
            narration_preferences=(
                exact_declaration_command.narration_preferences
            ),
        )
    ) == 65_536

    fixed_65_command = _repository_feature_command(65)
    beyond_65_command = _repository_feature_command(66)
    fixed_65 = fixed_65_command.character_core.distinguishing_features
    beyond_65 = beyond_65_command.character_core.distinguishing_features
    assert fixed_65.value is not None
    assert beyond_65.value is not None
    assert len(fixed_65.value.features) == 65
    assert len(beyond_65.value.features) == 66
    assert len(
        canonical_player_declaration_bytes(
            character_core=beyond_65_command.character_core,
            narration_preferences=beyond_65_command.narration_preferences,
        )
    ) < 65_536

    exact_declaration = repository_test_scope.character(
        "exact-declaration",
        creation_command=exact_declaration_command,
    )
    fixed_65_character = repository_test_scope.character(
        "fixed-65-features",
        creation_command=fixed_65_command,
    )
    beyond_65_character = repository_test_scope.character(
        "beyond-65-features",
        creation_command=beyond_65_command,
    )
    async with mysql_session_factory.begin() as session:
        for character in (
            exact_declaration,
            fixed_65_character,
            beyond_65_character,
        ):
            await _stage_repository_creation(session, character)

    async with mysql_session_factory() as session:
        repository = SqlAlchemyPlayerCharacterRepository(session)
        for character in (
            exact_declaration,
            fixed_65_character,
            beyond_65_character,
        ):
            assert (
                await repository.get(character.initial.player_character_id)
                == character.initial
            )
        reloaded_65 = await repository.get(
            fixed_65_character.initial.player_character_id
        )
        reloaded_66 = await repository.get(
            beyond_65_character.initial.player_character_id
        )
        assert reloaded_65 is not None
        assert reloaded_66 is not None
        reloaded_65_features = (
            reloaded_65.character_core.distinguishing_features.value
        )
        reloaded_66_features = (
            reloaded_66.character_core.distinguishing_features.value
        )
        assert reloaded_65_features is not None
        assert reloaded_66_features is not None
        assert tuple(
            feature.text for feature in reloaded_65_features.features
        ) == tuple(
            feature.text for feature in fixed_65.value.features
        )
        assert tuple(
            feature.text for feature in reloaded_66_features.features
        ) == tuple(
            feature.text for feature in beyond_65.value.features
        )

    over_limit_core = CharacterCore(
        name_or_code_name=Declaration[PlayerDeclaredText].declared(
            _repository_player_text((chr(0xE9) * 32_410) + "x")
        )
    )
    with pytest.raises(ValueError, match="declaration"):
        canonical_player_declaration_bytes(
            character_core=over_limit_core,
            narration_preferences=NarrationPreferences(),
        )
    with pytest.raises(ValueError, match="declaration"):
        CreatePlayerCharacterPolicy().create(
            player_character_id=PlayerCharacterId(
                value=f"pc.repo-{repository_test_scope.token}-over-limit"
            ),
            controller_binding=ControllerBindingRef(
                value=(
                    f"binding.repo-{repository_test_scope.token}-over-limit"
                )
            ),
            character_core=over_limit_core,
            narration_preferences=NarrationPreferences(),
            source_reference=AuthoritySourceRef(
                value=f"source.repo-{repository_test_scope.token}-over-limit"
            ),
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_mutation_preserves_history_and_replay_precedence(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("mutation")
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, character)
    async with mysql_session_factory.begin() as session:
        await _stage_repository_mutation(session, character)

    async with mysql_session_factory() as session:
        character_repository = SqlAlchemyPlayerCharacterRepository(session)
        receipt_repository = (
            SqlAlchemyPlayerCharacterMutationReceiptRepository(session)
        )
        assert (
            await character_repository.get(
                character.initial.player_character_id
            )
            == character.successor
        )
        stored_receipt = await receipt_repository.get(
            character.mutation_receipt.key
        )
        assert stored_receipt == character.mutation_receipt
        stored_row = await session.scalar(
            sa.select(PlayerCharacterMutationReceiptRow).where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == character.mutation_receipt.key.player_character_id.value,
                PlayerCharacterMutationReceiptRow.operation_namespace
                == character.mutation_receipt.key.operation_namespace.value,
                PlayerCharacterMutationReceiptRow.operation_id
                == character.mutation_receipt.key.operation_id.value,
            )
        )
        assert stored_row is not None
        assert stored_row.fingerprint == fingerprint_to_storage_bytes(
            character.mutation_receipt.fingerprint
        )
        assert stored_row.before_record_fingerprint == (
            canonical_state_record_fingerprint(character.initial)
        )
        assert stored_row.after_record_fingerprint == (
            canonical_state_record_fingerprint(character.successor)
        )
        assert stored_row.receipt_canonical == (
            mutation_receipt_to_storage_bytes(character.mutation_receipt)
        )
        assert mutation_operation_evidence_from_storage(
            stored_row.operation_evidence_canonical
        ) == character.mutation_command
        assert (
            stored_row.expected_revision,
            stored_row.resulting_revision,
        ) == (
            character.initial.record_revision.value,
            character.successor.record_revision.value,
        )
        history = tuple(
            (
                await session.scalars(
                    sa.select(PlayerCharacterRevisionRow)
                    .where(
                        PlayerCharacterRevisionRow.player_character_id
                        == character.initial.player_character_id.value
                    )
                    .order_by(PlayerCharacterRevisionRow.record_revision)
                )
            ).all()
        )
        assert tuple(row.record_revision for row in history) == (1, 2)
        assert history[0].record_canonical == canonical_record_to_storage_bytes(
            character.initial
        )
        assert history[1].record_canonical == canonical_record_to_storage_bytes(
            character.successor
        )

        exact = evaluate_mutation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            current_record=character.successor,
            operation_id=character.mutation_receipt.key.operation_id,
            command=character.mutation_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        assert exact.code is CharacterOperationProtocolCode.EXACT_REPLAY

        changed_confirmation = PlayerConfirmation(
            player_character_id=character.initial.player_character_id,
            expected_revision=character.initial.record_revision,
            operation_id=character.mutation_receipt.key.operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value="source.retire-conflicting-intent"
            ),
        )
        conflicting_command = character.mutation_command.model_copy(
            update={"confirmation": changed_confirmation}
        )
        conflict = evaluate_mutation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            current_record=character.successor,
            operation_id=character.mutation_receipt.key.operation_id,
            command=conflicting_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        assert (
            conflict.code
            is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )
        stale_operation_id = PlayerCharacterOperationId(
            value="operation.mutation-stale"
        )
        stale_command = character.mutation_command.model_copy(
            update={
                "confirmation": PlayerConfirmation(
                    player_character_id=character.initial.player_character_id,
                    expected_revision=character.initial.record_revision,
                    operation_id=stale_operation_id,
                    mutation_kind=PlayerCharacterMutationKind.RETIRE,
                    source_reference=AuthoritySourceRef(
                        value="source.retire-stale"
                    ),
                )
            }
        )
        stale = evaluate_mutation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            current_record=character.successor,
            operation_id=stale_operation_id,
            command=stale_command,
            lookup_receipt=lambda _key: None,
        )
        assert stale.code is CharacterOperationProtocolCode.STALE_REVISION
        assert not await character_repository.compare_and_swap_current(
            character.successor,
            expected_revision=character.initial.record_revision.value,
            created_at=_REPOSITORY_TEST_TIME,
        )

    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError):
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).add(
                character.mutation_receipt,
                created_at=_REPOSITORY_TEST_TIME,
            )
        await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_real_compare_and_swap_has_one_deterministic_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("cas")
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, character)
    async with mysql_session_factory.begin() as session:
        await SqlAlchemyPlayerCharacterRepository(session).append_revision(
            character.successor,
            created_at=_REPOSITORY_TEST_TIME,
        )

    winner_ready = asyncio.Event()
    loser_ready = asyncio.Event()
    start_gate = asyncio.Event()
    winner_staged = asyncio.Event()
    loser_entered_cas = asyncio.Event()
    release_winner = asyncio.Event()
    transaction_actions: dict[str, str] = {}

    async def winning_attempt() -> tuple[bool, int]:
        async with mysql_session_factory() as session:
            await session.begin()
            connection_id = await session.scalar(
                sa.text("SELECT CONNECTION_ID()")
            )
            assert connection_id is not None
            winner_ready.set()
            await asyncio.wait_for(
                start_gate.wait(),
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            result = await SqlAlchemyPlayerCharacterRepository(
                session
            ).compare_and_swap_current(
                character.successor,
                expected_revision=character.initial.record_revision.value,
                created_at=_REPOSITORY_CAS_WINNER_TIME,
            )
            assert result
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).add(
                character.mutation_receipt,
                created_at=_REPOSITORY_CAS_WINNER_TIME,
            )
            winner_staged.set()
            await asyncio.wait_for(
                release_winner.wait(),
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            await session.commit()
            transaction_actions["winner"] = "committed"
            assert not session.in_transaction()
            return result, int(connection_id)

    async def losing_attempt() -> tuple[bool, int]:
        async with mysql_session_factory() as session:
            await session.begin()
            connection_id = await session.scalar(
                sa.text("SELECT CONNECTION_ID()")
            )
            assert connection_id is not None
            loser_ready.set()
            await asyncio.wait_for(
                start_gate.wait(),
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            await asyncio.wait_for(
                winner_staged.wait(),
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            # The repository has no production-only SQL hook. This is the
            # narrowest observable boundary immediately before the real CAS.
            loser_entered_cas.set()
            result = await SqlAlchemyPlayerCharacterRepository(
                session
            ).compare_and_swap_current(
                character.successor,
                expected_revision=character.initial.record_revision.value,
                created_at=_REPOSITORY_CAS_LOSER_TIME,
            )
            assert not result
            await session.rollback()
            transaction_actions["loser"] = "rolled back"
            assert not session.in_transaction()
            return result, int(connection_id)

    winner_task = asyncio.create_task(winning_attempt())
    loser_task = asyncio.create_task(losing_attempt())
    tasks = (winner_task, loser_task)
    try:
        await asyncio.wait_for(
            asyncio.gather(winner_ready.wait(), loser_ready.wait()),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
        start_gate.set()
        await asyncio.wait_for(
            winner_staged.wait(),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
        await asyncio.wait_for(
            loser_entered_cas.wait(),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                asyncio.shield(loser_task),
                timeout=_EXPECTED_ROW_BLOCK_TIMEOUT,
            )
        assert not winner_task.done()

        release_winner.set()
        winner_outcome, loser_outcome = await asyncio.wait_for(
            asyncio.gather(winner_task, loser_task),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
    finally:
        release_winner.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    assert (winner_outcome[0], loser_outcome[0]) == (True, False)
    assert winner_outcome[1] != loser_outcome[1]
    assert transaction_actions == {
        "winner": "committed",
        "loser": "rolled back",
    }

    async with mysql_session_factory() as session:
        repository = SqlAlchemyPlayerCharacterRepository(session)
        assert (
            await repository.get(character.initial.player_character_id)
            == character.successor
        )
        current = await session.scalar(
            sa.select(PlayerCharacterCurrentRow).where(
                PlayerCharacterCurrentRow.player_character_id
                == character.initial.player_character_id.value
            )
        )
        assert current is not None
        assert current.record_revision == 2
        assert current.record_canonical == canonical_record_to_storage_bytes(
            character.successor
        )
        assert current.updated_at.replace(tzinfo=UTC) == (
            _REPOSITORY_CAS_WINNER_TIME
        )
        history = tuple(
            (
                await session.scalars(
                    sa.select(PlayerCharacterRevisionRow)
                    .where(
                        PlayerCharacterRevisionRow.player_character_id
                        == character.initial.player_character_id.value
                    )
                    .order_by(PlayerCharacterRevisionRow.record_revision)
                )
            ).all()
        )
        assert tuple(row.record_revision for row in history) == (1, 2)
        assert history[0].record_canonical == canonical_record_to_storage_bytes(
            character.initial
        )
        assert history[1].record_canonical == canonical_record_to_storage_bytes(
            character.successor
        )
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(PlayerCharacterMutationReceiptRow)
                .where(
                    PlayerCharacterMutationReceiptRow.player_character_id
                    == character.initial.player_character_id.value
                )
            )
            == 1
        )
        family_counts = []
        for row_type, predicate in (
            (
                PlayerCharacterControllerBindingRow,
                PlayerCharacterControllerBindingRow.controller_binding
                == character.initial.controller_binding.value,
            ),
            (
                PlayerCharacterIdAllocationRow,
                PlayerCharacterIdAllocationRow.player_character_id
                == character.initial.player_character_id.value,
            ),
            (
                PlayerCharacterRevisionRow,
                PlayerCharacterRevisionRow.player_character_id
                == character.initial.player_character_id.value,
            ),
            (
                PlayerCharacterCurrentRow,
                PlayerCharacterCurrentRow.player_character_id
                == character.initial.player_character_id.value,
            ),
            (
                PlayerCharacterCreationReceiptRow,
                PlayerCharacterCreationReceiptRow.result_player_character_id
                == character.initial.player_character_id.value,
            ),
            (
                PlayerCharacterMutationReceiptRow,
                PlayerCharacterMutationReceiptRow.player_character_id
                == character.initial.player_character_id.value,
            ),
        ):
            family_counts.append(
                await session.scalar(
                    sa.select(sa.func.count())
                    .select_from(row_type)
                    .where(predicate)
                )
            )
        assert family_counts == [1, 1, 2, 1, 1, 1]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_get_for_update_blocks_only_the_exact_current_row(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    locked_character = repository_test_scope.character("row-lock")
    unrelated_character = repository_test_scope.character("row-unrelated")
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, locked_character)
        await _stage_repository_creation(session, unrelated_character)

    same_row_started = asyncio.Event()
    unrelated_started = asyncio.Event()
    transaction_actions: dict[str, str] = {}

    async def locked_read(
        character: _RepositoryCharacter,
        *,
        started: asyncio.Event,
        caller: str,
    ) -> tuple[CanonicalPlayerCharacter | None, int]:
        async with mysql_session_factory() as session:
            await session.begin()
            connection_id = await session.scalar(
                sa.text("SELECT CONNECTION_ID()")
            )
            assert connection_id is not None
            started.set()
            record = await SqlAlchemyPlayerCharacterRepository(
                session
            ).get_for_update(character.initial.player_character_id)
            await session.rollback()
            transaction_actions[caller] = "rolled back"
            assert not session.in_transaction()
            return record, int(connection_id)

    async with mysql_session_factory() as first_session:
        await first_session.begin()
        first_connection_id = await first_session.scalar(
            sa.text("SELECT CONNECTION_ID()")
        )
        assert first_connection_id is not None
        assert (
            await SqlAlchemyPlayerCharacterRepository(
                first_session
            ).get_for_update(locked_character.initial.player_character_id)
            == locked_character.initial
        )

        same_row_task = asyncio.create_task(
            locked_read(
                locked_character,
                started=same_row_started,
                caller="same-row",
            )
        )
        unrelated_task = asyncio.create_task(
            locked_read(
                unrelated_character,
                started=unrelated_started,
                caller="unrelated-row",
            )
        )
        tasks = (same_row_task, unrelated_task)
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    same_row_started.wait(),
                    unrelated_started.wait(),
                ),
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            unrelated_result = await asyncio.wait_for(
                unrelated_task,
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
            assert unrelated_result[0] == unrelated_character.initial
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(
                    asyncio.shield(same_row_task),
                    timeout=_EXPECTED_ROW_BLOCK_TIMEOUT,
                )

            await first_session.commit()
            transaction_actions["lock-holder"] = "committed"
            assert not first_session.in_transaction()
            same_row_result = await asyncio.wait_for(
                same_row_task,
                timeout=_ASYNC_COORDINATION_TIMEOUT,
            )
        finally:
            if first_session.in_transaction():
                await first_session.rollback()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    assert same_row_result[0] == locked_character.initial
    assert len(
        {
            int(first_connection_id),
            same_row_result[1],
            unrelated_result[1],
        }
    ) == 3
    assert transaction_actions == {
        "lock-holder": "committed",
        "unrelated-row": "rolled back",
        "same-row": "rolled back",
    }

    async with mysql_session_factory() as observer:
        repository = SqlAlchemyPlayerCharacterRepository(observer)
        assert (
            await repository.get(locked_character.initial.player_character_id)
            == locked_character.initial
        )
        assert (
            await repository.get(
                unrelated_character.initial.player_character_id
            )
            == unrelated_character.initial
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_distinguishes_missing_current_from_absence(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("missing-current")
    async with mysql_session_factory.begin() as session:
        await SqlAlchemyControllerBindingRegistryRepository(session).add(
            character.initial.controller_binding,
            created_at=_REPOSITORY_TEST_TIME,
        )
        await SqlAlchemyPlayerCharacterRepository(session).add_allocation(
            character.initial.player_character_id,
            created_at=_REPOSITORY_TEST_TIME,
        )

    async with mysql_session_factory() as session:
        repository = SqlAlchemyPlayerCharacterRepository(session)
        with pytest.raises(
            PlayerCharacterStoredRecordIntegrityError,
            match="current row is missing",
        ):
            await repository.get(character.initial.player_character_id)
        assert (
            await repository.get(
                PlayerCharacterId(value=f"pc.absent-{uuid4().hex}")
            )
            is None
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_reconstruction_rejects_corrupt_current_blob(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("corrupt")
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, character)
    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(PlayerCharacterCurrentRow)
            .where(
                PlayerCharacterCurrentRow.player_character_id
                == character.initial.player_character_id.value
            )
            .values(record_canonical=b"{}")
        )

    async with mysql_session_factory() as session:
        with pytest.raises(
            PlayerCharacterStoredRecordIntegrityError,
            match="stored canonical player-character record is invalid",
        ) as exc_info:
            await SqlAlchemyPlayerCharacterRepository(session).get(
                character.initial.player_character_id
            )
        assert exc_info.value.__cause__ is not None
        unchanged_blob = await session.scalar(
            sa.select(PlayerCharacterCurrentRow.record_canonical).where(
                PlayerCharacterCurrentRow.player_character_id
                == character.initial.player_character_id.value
            )
        )
        assert unchanged_blob == b"{}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_reconstruction_rejects_inconsistent_receipt_evidence(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    corrupt_creation = repository_test_scope.character(
        "corrupt-creation-evidence"
    )
    corrupt_mutation_revision = repository_test_scope.character(
        "corrupt-mutation-revision"
    )
    corrupt_mutation_intent = repository_test_scope.character(
        "corrupt-mutation-intent"
    )
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, corrupt_creation)
        await _stage_repository_creation(session, corrupt_mutation_revision)
        await _stage_repository_creation(session, corrupt_mutation_intent)
    async with mysql_session_factory.begin() as session:
        await _stage_repository_mutation(session, corrupt_mutation_revision)
        await _stage_repository_mutation(session, corrupt_mutation_intent)

    changed_confirmation = PlayerConfirmation(
        player_character_id=(
            corrupt_mutation_intent.initial.player_character_id
        ),
        expected_revision=(
            corrupt_mutation_intent.initial.record_revision
        ),
        operation_id=(
            corrupt_mutation_intent.mutation_receipt.key.operation_id
        ),
        mutation_kind=PlayerCharacterMutationKind.RETIRE,
        source_reference=AuthoritySourceRef(
            value="source.corrupt-mutation-intent"
        ),
    )
    changed_command = corrupt_mutation_intent.mutation_command.model_copy(
        update={"confirmation": changed_confirmation}
    )
    changed_evidence = mutation_operation_evidence_to_storage_bytes(
        changed_command
    )
    assert changed_evidence != mutation_operation_evidence_to_storage_bytes(
        corrupt_mutation_intent.mutation_command
    )

    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(PlayerCharacterCreationReceiptRow)
            .where(
                PlayerCharacterCreationReceiptRow.controller_binding
                == corrupt_creation.initial.controller_binding.value,
                PlayerCharacterCreationReceiptRow.operation_namespace
                == corrupt_creation.creation_receipt.key.operation_namespace.value,
                PlayerCharacterCreationReceiptRow.operation_id
                == corrupt_creation.creation_receipt.key.operation_id.value,
            )
            .values(operation_evidence_canonical=b"{}")
        )
        await session.execute(
            sa.update(PlayerCharacterMutationReceiptRow)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == (
                    corrupt_mutation_revision.initial.player_character_id.value
                ),
                PlayerCharacterMutationReceiptRow.operation_namespace
                == (
                    corrupt_mutation_revision.mutation_receipt.key
                    .operation_namespace.value
                ),
                PlayerCharacterMutationReceiptRow.operation_id
                == (
                    corrupt_mutation_revision.mutation_receipt.key
                    .operation_id.value
                ),
            )
            .values(after_record_fingerprint=b"\0" * 32)
        )
        await session.execute(
            sa.update(PlayerCharacterMutationReceiptRow)
            .where(
                PlayerCharacterMutationReceiptRow.player_character_id
                == corrupt_mutation_intent.initial.player_character_id.value,
                PlayerCharacterMutationReceiptRow.operation_namespace
                == (
                    corrupt_mutation_intent.mutation_receipt.key
                    .operation_namespace.value
                ),
                PlayerCharacterMutationReceiptRow.operation_id
                == (
                    corrupt_mutation_intent.mutation_receipt.key
                    .operation_id.value
                ),
            )
            .values(operation_evidence_canonical=changed_evidence)
        )

    async with mysql_session_factory() as session:
        with pytest.raises(
            PlayerCharacterStoredRecordIntegrityError,
            match="creation operation evidence has an invalid shape",
        ):
            await SqlAlchemyPlayerCharacterCreationReceiptRepository(
                session
            ).get(corrupt_creation.creation_receipt.key)
    async with mysql_session_factory() as session:
        with pytest.raises(
            PlayerCharacterStoredRecordIntegrityError,
            match="mutation receipt does not bind adjacent history",
        ):
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).get(corrupt_mutation_revision.mutation_receipt.key)
    async with mysql_session_factory() as session:
        with pytest.raises(
            PlayerCharacterStoredRecordIntegrityError,
            match="mutation receipt columns do not match canonical receipt",
        ):
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).get(corrupt_mutation_intent.mutation_receipt.key)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_repository_128_character_case_variants_remain_distinct(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    upper = repository_test_scope.character(
        "Case",
        player_character_id=PlayerCharacterId(value="P" * 128),
        controller_binding=ControllerBindingRef(value="B" * 128),
    )
    lower = repository_test_scope.character(
        "case",
        player_character_id=PlayerCharacterId(value="p" * 128),
        controller_binding=ControllerBindingRef(value="b" * 128),
    )
    async with mysql_session_factory.begin() as session:
        await _stage_repository_creation(session, upper)
        await _stage_repository_creation(session, lower)

    async with mysql_session_factory() as session:
        repository = SqlAlchemyPlayerCharacterRepository(session)
        assert await repository.get(upper.initial.player_character_id) == (
            upper.initial
        )
        assert await repository.get(lower.initial.player_character_id) == (
            lower.initial
        )
        assert len(upper.initial.player_character_id.value) == 128
        assert len(lower.initial.player_character_id.value) == 128
        assert len(upper.initial.controller_binding.value) == 128
        assert len(lower.initial.controller_binding.value) == 128


@dataclass(frozen=True, slots=True)
class _UowMutation:
    command: CharacterMutationCommand
    successor: CanonicalPlayerCharacter
    receipt: StoredMutationSuccessReceipt


async def _uow_family_counts_in_session(
    session: AsyncSession,
    character: _RepositoryCharacter,
) -> tuple[int, int, int, int, int, int]:
    predicates = (
        (
            PlayerCharacterControllerBindingRow,
            PlayerCharacterControllerBindingRow.controller_binding
            == character.initial.controller_binding.value,
        ),
        (
            PlayerCharacterIdAllocationRow,
            PlayerCharacterIdAllocationRow.player_character_id
            == character.initial.player_character_id.value,
        ),
        (
            PlayerCharacterRevisionRow,
            PlayerCharacterRevisionRow.player_character_id
            == character.initial.player_character_id.value,
        ),
        (
            PlayerCharacterCurrentRow,
            PlayerCharacterCurrentRow.player_character_id
            == character.initial.player_character_id.value,
        ),
        (
            PlayerCharacterCreationReceiptRow,
            PlayerCharacterCreationReceiptRow.result_player_character_id
            == character.initial.player_character_id.value,
        ),
        (
            PlayerCharacterMutationReceiptRow,
            PlayerCharacterMutationReceiptRow.player_character_id
            == character.initial.player_character_id.value,
        ),
    )
    counts = []
    for row_type, predicate in predicates:
        counts.append(
            int(
                await session.scalar(
                    sa.select(sa.func.count())
                    .select_from(row_type)
                    .where(predicate)
                )
                or 0
            )
        )
    return tuple(counts)  # type: ignore[return-value]


async def _uow_family_counts(
    session_factory: async_sessionmaker[AsyncSession],
    character: _RepositoryCharacter,
) -> tuple[int, int, int, int, int, int]:
    async with session_factory() as session:
        return await _uow_family_counts_in_session(session, character)


async def _run_uow_creation(
    session_factory: async_sessionmaker[AsyncSession],
    character: _RepositoryCharacter,
    *,
    command: CharacterCreationCommand | None = None,
    uow: SqlAlchemyUnitOfWork | None = None,
    injected_failure: BaseException | None = None,
    after_staging: Any = None,
) -> Any:
    active_uow = uow or SqlAlchemyUnitOfWork(session_factory)
    async with active_uow:
        locked_binding = await active_uow.controller_bindings.lock(
            character.initial.controller_binding
        )
        if locked_binding is None:
            await active_uow.controller_bindings.add(
                character.initial.controller_binding,
                created_at=_REPOSITORY_TEST_TIME,
            )
        else:
            assert locked_binding == character.initial.controller_binding

        stored_receipt = await active_uow.creation_receipts.get(
            character.creation_receipt.key
        )
        decision = evaluate_creation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            operation_id=character.creation_receipt.key.operation_id,
            command=command or character.creation_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        if (
            decision.code
            is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
        ):
            await active_uow.player_characters.add_allocation(
                character.initial.player_character_id,
                created_at=_REPOSITORY_TEST_TIME,
            )
            await active_uow.player_characters.add_initial(
                character.initial,
                created_at=_REPOSITORY_TEST_TIME,
            )
            await active_uow.creation_receipts.add(
                character.creation_receipt,
                created_at=_REPOSITORY_TEST_TIME,
            )
            if after_staging is not None:
                await after_staging(active_uow)
            if injected_failure is not None:
                raise injected_failure
        await active_uow.commit()
        return decision


async def _run_uow_mutation(
    session_factory: async_sessionmaker[AsyncSession],
    character: _RepositoryCharacter,
    mutation: _UowMutation,
    *,
    command: CharacterMutationCommand | None = None,
    injected_failure: BaseException | None = None,
) -> Any:
    active_command = command or mutation.command
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        current = await uow.player_characters.get_for_update(
            character.initial.player_character_id
        )
        assert current is not None
        assert (
            current.controller_binding
            == character.initial.controller_binding
        )
        stored_receipt = await uow.mutation_receipts.get(
            mutation.receipt.key
        )
        decision = evaluate_mutation_receipt_protocol(
            authentication_succeeded=True,
            trusted_controller_binding=character.initial.controller_binding,
            current_record=current,
            operation_id=mutation.receipt.key.operation_id,
            command=active_command,
            lookup_receipt=lambda _key: stored_receipt,
        )
        if (
            decision.code
            is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
        ):
            policy_decision = evaluate_mutation_policy(
                current,
                command=active_command,
                operation_id=mutation.receipt.key.operation_id,
            )
            assert policy_decision.accepted
            assert policy_decision.resulting_record == mutation.successor
            await uow.player_characters.append_revision(
                mutation.successor,
                created_at=_REPOSITORY_TEST_TIME,
            )
            if not await uow.player_characters.compare_and_swap_current(
                mutation.successor,
                expected_revision=current.record_revision.value,
                created_at=_REPOSITORY_TEST_TIME,
            ):
                raise PlayerCharacterRepositoryConflictError(
                    "player-character current compare-and-swap lost"
                )
            await uow.mutation_receipts.add(
                mutation.receipt,
                created_at=_REPOSITORY_TEST_TIME,
            )
            if injected_failure is not None:
                raise injected_failure
        await uow.commit()
        return decision


def _final_death_uow_mutation(
    current: CanonicalPlayerCharacter,
    *,
    label: str,
) -> _UowMutation:
    operation_id = PlayerCharacterOperationId(
        value=f"operation.final-death-{label}"
    )
    command = CharacterMutationCommand(
        contract_version=current.contract_version,
        command_kind=PlayerCharacterMutationKind.FINAL_DEATH,
        target_player_character_id=current.player_character_id,
        expected_revision=current.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=current.player_character_id,
            contract_version=current.contract_version,
            record_revision=current.record_revision,
        ),
        final_death_evidence=TrustedFinalDeathEvidence(
            player_character_id=current.player_character_id,
            expected_revision=current.record_revision,
            operation_id=operation_id,
            source_reference=AuthoritySourceRef(
                value=f"source.final-death-{label}"
            ),
        ),
    )
    policy_decision = evaluate_mutation_policy(
        current,
        command=command,
        operation_id=operation_id,
    )
    assert policy_decision.accepted
    assert policy_decision.resulting_record is not None
    successor = policy_decision.resulting_record
    _, fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=current.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=current.player_character_id,
            contract_version=current.contract_version,
            command_kind=PlayerCharacterMutationKind.FINAL_DEATH,
            command_result=MutationCommandResult.DECEASED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=successor.lifecycle,
        ),
    )
    return _UowMutation(
        command=command,
        successor=successor,
        receipt=receipt,
    )


class _PreCommitFailingSqlAlchemyUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(session_factory)
        self.commit_attempted = False

    async def commit(self) -> None:
        self.commit_attempted = True
        raise RuntimeError("controlled pre-COMMIT failure")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_uow_commits_atomic_creation_and_exact_replay(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("uow-creation")

    created = await _run_uow_creation(
        mysql_session_factory,
        character,
    )
    assert (
        created.code
        is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    )
    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 1, 1, 1, 0)

    replay = await _run_uow_creation(
        mysql_session_factory,
        character,
    )
    assert replay.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert replay.stored_success_result == character.creation_receipt.result
    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 1, 1, 1, 0)

    conflict = await _run_uow_creation(
        mysql_session_factory,
        character,
        command=_repository_name_command("changed creation command"),
    )
    assert conflict.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 1, 1, 1, 0)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ("exception", "cancellation"))
async def test_mysql_uow_creation_exception_and_cancellation_roll_back_all_families(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
    failure_kind: str,
) -> None:
    character = repository_test_scope.character(
        f"uow-creation-{failure_kind}"
    )
    failure: BaseException
    expected: type[BaseException]
    if failure_kind == "cancellation":
        failure = asyncio.CancelledError()
        expected = asyncio.CancelledError
    else:
        failure = RuntimeError("controlled creation-body failure")
        expected = RuntimeError

    with pytest.raises(expected):
        await _run_uow_creation(
            mysql_session_factory,
            character,
            injected_failure=failure,
        )

    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (0, 0, 0, 0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_uow_pre_commit_failure_rolls_back_and_fresh_uow_succeeds(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    character = repository_test_scope.character("uow-pre-commit")
    failing_uow = _PreCommitFailingSqlAlchemyUnitOfWork(
        mysql_session_factory
    )
    staged_counts: list[tuple[int, int, int, int, int, int]] = []
    async_session_commit_calls: list[AsyncSession] = []
    original_async_session_commit = AsyncSession.commit

    async def tracked_async_session_commit(
        session: AsyncSession,
    ) -> None:
        async_session_commit_calls.append(session)
        await original_async_session_commit(session)

    monkeypatch.setattr(
        AsyncSession,
        "commit",
        tracked_async_session_commit,
    )

    async def observe_staged(active_uow: SqlAlchemyUnitOfWork) -> None:
        assert active_uow._session is not None
        staged_counts.append(
            await _uow_family_counts_in_session(
                active_uow._session,
                character,
            )
        )

    with pytest.raises(RuntimeError, match="controlled pre-COMMIT failure"):
        await _run_uow_creation(
            mysql_session_factory,
            character,
            uow=failing_uow,
            after_staging=observe_staged,
        )

    assert staged_counts == [(1, 1, 1, 1, 1, 0)]
    assert failing_uow.commit_attempted
    assert async_session_commit_calls == []
    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (0, 0, 0, 0, 0, 0)

    completed = await _run_uow_creation(
        mysql_session_factory,
        character,
    )
    assert (
        completed.code
        is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    )
    assert len(async_session_commit_calls) == 1
    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 1, 1, 1, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_uow_creation_unique_race_rolls_back_loser_and_fresh_uow_reads_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    shared_binding = ControllerBindingRef(
        value=f"binding.uow-race-{repository_test_scope.token}"
    )
    winner_candidate = repository_test_scope.character(
        "uow-race",
        player_character_id=PlayerCharacterId(
            value=f"pc.uow-race-a-{repository_test_scope.token}"
        ),
        controller_binding=shared_binding,
    )
    loser_candidate = repository_test_scope.character(
        "uow-race",
        player_character_id=PlayerCharacterId(
            value=f"pc.uow-race-b-{repository_test_scope.token}"
        ),
        controller_binding=shared_binding,
    )
    ready = (asyncio.Event(), asyncio.Event())
    start = asyncio.Event()
    allocation_attempts = 0

    async def attempt(
        character: _RepositoryCharacter,
        ready_event: asyncio.Event,
    ) -> str:
        nonlocal allocation_attempts
        try:
            async with SqlAlchemyUnitOfWork(
                mysql_session_factory
            ) as uow:
                assert uow._session is not None
                await uow._session.connection(
                    execution_options={"isolation_level": "READ COMMITTED"}
                )
                locked = await uow.controller_bindings.lock(shared_binding)
                assert locked is None
                ready_event.set()
                await asyncio.wait_for(
                    start.wait(),
                    timeout=_ASYNC_COORDINATION_TIMEOUT,
                )
                await uow.controller_bindings.add(
                    shared_binding,
                    created_at=_REPOSITORY_TEST_TIME,
                )
                stored_receipt = await uow.creation_receipts.get(
                    character.creation_receipt.key
                )
                decision = evaluate_creation_receipt_protocol(
                    authentication_succeeded=True,
                    trusted_controller_binding=shared_binding,
                    operation_id=character.creation_receipt.key.operation_id,
                    command=character.creation_command,
                    lookup_receipt=lambda _key: stored_receipt,
                )
                assert (
                    decision.code
                    is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
                )
                allocation_attempts += 1
                await uow.player_characters.add_allocation(
                    character.initial.player_character_id,
                    created_at=_REPOSITORY_TEST_TIME,
                )
                await uow.player_characters.add_initial(
                    character.initial,
                    created_at=_REPOSITORY_TEST_TIME,
                )
                await uow.creation_receipts.add(
                    character.creation_receipt,
                    created_at=_REPOSITORY_TEST_TIME,
                )
                await uow.commit()
            return "committed"
        except PlayerCharacterRepositoryConflictError:
            return "conflict-rolled-back"

    tasks = (
        asyncio.create_task(attempt(winner_candidate, ready[0])),
        asyncio.create_task(attempt(loser_candidate, ready[1])),
    )
    try:
        await asyncio.wait_for(
            asyncio.gather(ready[0].wait(), ready[1].wait()),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
        start.set()
        outcomes = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=_ASYNC_COORDINATION_TIMEOUT,
        )
    finally:
        start.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    assert sorted(outcomes) == ["committed", "conflict-rolled-back"]
    committed = (
        winner_candidate
        if outcomes[0] == "committed"
        else loser_candidate
    )
    losing = (
        loser_candidate
        if committed is winner_candidate
        else winner_candidate
    )
    assert allocation_attempts == 1
    assert await _uow_family_counts(
        mysql_session_factory,
        committed,
    ) == (1, 1, 1, 1, 1, 0)
    losing_counts = await _uow_family_counts(
        mysql_session_factory,
        losing,
    )
    assert losing_counts[1:] == (0, 0, 0, 0, 0)

    async with SqlAlchemyUnitOfWork(mysql_session_factory) as recovery_uow:
        assert (
            await recovery_uow.controller_bindings.lock(shared_binding)
            == shared_binding
        )
        stored_winner = await recovery_uow.creation_receipts.get(
            committed.creation_receipt.key
        )
        recovery = recover_creation_unique_race_winner(
            losing_transaction_rolled_back=True,
            authentication_succeeded=True,
            trusted_controller_binding=shared_binding,
            operation_id=committed.creation_receipt.key.operation_id,
            command=committed.creation_command,
            reread_receipt_in_fresh_transaction=lambda _key: stored_winner,
        )
        await recovery_uow.commit()
    assert recovery.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert recovery.stored_success_result == committed.creation_receipt.result
    assert allocation_attempts == 1
    assert await _uow_family_counts(
        mysql_session_factory,
        committed,
    ) == (1, 1, 1, 1, 1, 0)
    assert (
        await _uow_family_counts(mysql_session_factory, losing)
    )[1:] == (0, 0, 0, 0, 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_uow_commits_atomic_mutation_and_replays_after_later_revision(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("uow-mutation")
    await _run_uow_creation(mysql_session_factory, character)
    first_mutation = _UowMutation(
        command=character.mutation_command,
        successor=character.successor,
        receipt=character.mutation_receipt,
    )
    first = await _run_uow_mutation(
        mysql_session_factory,
        character,
        first_mutation,
    )
    assert first.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION

    later_mutation = _final_death_uow_mutation(
        character.successor,
        label=f"uow-mutation-{repository_test_scope.token}",
    )
    later = await _run_uow_mutation(
        mysql_session_factory,
        character,
        later_mutation,
    )
    assert later.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION

    replay = await _run_uow_mutation(
        mysql_session_factory,
        character,
        first_mutation,
    )
    assert replay.code is CharacterOperationProtocolCode.EXACT_REPLAY
    assert replay.stored_success_result == character.mutation_receipt.result

    changed_confirmation = PlayerConfirmation(
        player_character_id=character.initial.player_character_id,
        expected_revision=character.initial.record_revision,
        operation_id=character.mutation_receipt.key.operation_id,
        mutation_kind=PlayerCharacterMutationKind.RETIRE,
        source_reference=AuthoritySourceRef(
            value="source.changed-earlier-mutation"
        ),
    )
    conflict = await _run_uow_mutation(
        mysql_session_factory,
        character,
        first_mutation,
        command=character.mutation_command.model_copy(
            update={"confirmation": changed_confirmation}
        ),
    )
    assert conflict.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT

    stale_operation_id = PlayerCharacterOperationId(
        value=f"operation.stale-{repository_test_scope.token}"
    )
    stale_command = character.mutation_command.model_copy(
        update={
            "confirmation": PlayerConfirmation(
                player_character_id=character.initial.player_character_id,
                expected_revision=character.initial.record_revision,
                operation_id=stale_operation_id,
                mutation_kind=PlayerCharacterMutationKind.RETIRE,
                source_reference=AuthoritySourceRef(
                    value="source.stale-new-operation"
                ),
            )
        }
    )
    stale_mutation = _UowMutation(
        command=stale_command,
        successor=character.successor,
        receipt=character.mutation_receipt.model_copy(
            update={
                "key": MutationReceiptKey(
                    player_character_id=character.initial.player_character_id,
                    operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                    operation_id=stale_operation_id,
                )
            }
        ),
    )
    stale = await _run_uow_mutation(
        mysql_session_factory,
        character,
        stale_mutation,
    )
    assert stale.code is CharacterOperationProtocolCode.STALE_REVISION

    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 3, 1, 1, 2)
    async with mysql_session_factory() as session:
        history = tuple(
            (
                await session.scalars(
                    sa.select(PlayerCharacterRevisionRow)
                    .where(
                        PlayerCharacterRevisionRow.player_character_id
                        == character.initial.player_character_id.value
                    )
                    .order_by(PlayerCharacterRevisionRow.record_revision)
                )
            ).all()
        )
        current = await session.scalar(
            sa.select(PlayerCharacterCurrentRow).where(
                PlayerCharacterCurrentRow.player_character_id
                == character.initial.player_character_id.value
            )
        )
        assert tuple(row.record_revision for row in history) == (1, 2, 3)
        assert current is not None
        assert current.record_revision == 3
        assert current.record_canonical == canonical_record_to_storage_bytes(
            later_mutation.successor
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_uow_mutation_failure_rolls_back_history_current_and_receipt(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    repository_test_scope: _RepositoryTestScope,
) -> None:
    character = repository_test_scope.character("uow-mutation-rollback")
    await _run_uow_creation(mysql_session_factory, character)
    mutation = _UowMutation(
        command=character.mutation_command,
        successor=character.successor,
        receipt=character.mutation_receipt,
    )

    with pytest.raises(RuntimeError, match="mutation-body failure"):
        await _run_uow_mutation(
            mysql_session_factory,
            character,
            mutation,
            injected_failure=RuntimeError(
                "controlled mutation-body failure"
            ),
        )

    assert await _uow_family_counts(
        mysql_session_factory,
        character,
    ) == (1, 1, 1, 1, 1, 0)
    async with mysql_session_factory() as session:
        assert (
            await SqlAlchemyPlayerCharacterRepository(session).get(
                character.initial.player_character_id
            )
            == character.initial
        )
        assert (
            await session.scalar(
                sa.select(sa.func.count())
                .select_from(PlayerCharacterRevisionRow)
                .where(
                    PlayerCharacterRevisionRow.player_character_id
                    == character.initial.player_character_id.value,
                    PlayerCharacterRevisionRow.record_revision
                    == character.successor.record_revision.value,
                )
            )
            == 0
        )
        assert (
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).get(character.mutation_receipt.key)
            is None
        )
