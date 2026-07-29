from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


TABLE_OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
PLAYER_CHARACTER_TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_bin",
}


def _ascii_varchar(length: int) -> mysql.VARCHAR:
    return mysql.VARCHAR(length=length, charset="ascii", collation="ascii_bin")


def _legacy_session_id_varchar() -> mysql.VARCHAR:
    return mysql.VARCHAR(
        length=64,
        charset="utf8mb4",
        collation="utf8mb4_0900_ai_ci",
    )


class GameSessionRow(Base):
    __tablename__ = "game_sessions"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "creation_client_request_id",
            name="uq_game_sessions_player_creation_request",
        ),
        Index("ix_game_sessions_player_id", "player_id"),
        Index("ix_game_sessions_scenario", "scenario_id", "scenario_version"),
        TABLE_OPTIONS,
    )

    session_id: Mapped[str] = mapped_column(_legacy_session_id_varchar(), primary_key=True)
    player_id: Mapped[str] = mapped_column(String(64), nullable=False)
    creation_client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    character_definition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    random_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class GameSnapshotRow(Base):
    __tablename__ = "game_snapshots"
    __table_args__ = TABLE_OPTIONS

    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), primary_key=True
    )
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(mysql.JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class DomainEventRow(Base):
    __tablename__ = "domain_events"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_no", name="uq_domain_events_session_sequence"),
        Index("ix_domain_events_session_turn", "session_id", "turn_id"),
        Index("ix_domain_events_type_occurred", "event_type", "occurred_at"),
        TABLE_OPTIONS,
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence_no: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(mysql.JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TurnRequestRow(Base):
    __tablename__ = "turn_requests"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "client_request_id", name="uq_turn_requests_session_client_request"
        ),
        Index("ix_turn_requests_session_turn", "session_id", "turn_id"),
        Index("ix_turn_requests_signature", "session_id", "action_signature"),
        Index("ix_turn_requests_created_at", "created_at"),
        TABLE_OPTIONS,
    )

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    route: Mapped[str] = mapped_column(String(40), nullable=False)
    request_json: Mapped[dict[str, Any]] = mapped_column(mysql.JSON, nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(mysql.JSON, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class NarrativeJobRow(Base):
    __tablename__ = "narrative_jobs"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "client_request_id",
            name="uq_narrative_jobs_session_client_request",
        ),
        Index("ix_narrative_jobs_session_status", "session_id", "status"),
        Index("ix_narrative_jobs_status_lease", "status", "lease_expires_at"),
        Index("ix_narrative_jobs_session_turn", "session_id", "turn_id"),
        TABLE_OPTIONS,
    )

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    prepared_state_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scenario_content_version: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    narrative_request_json: Mapped[dict[str, Any]] = mapped_column(mysql.JSON, nullable=False)
    prompt_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    style_profile_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    lease_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_proposal_json: Mapped[dict[str, Any] | None] = mapped_column(mysql.JSON, nullable=True)
    validated_proposal_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome_rule_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_narrative_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlayerCharacterControllerBindingRow(Base):
    __tablename__ = "player_character_controller_bindings"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_controller_bindings_opaque",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    controller_binding: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class PlayerCharacterIdAllocationRow(Base):
    __tablename__ = "player_character_id_allocations"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_allocations_identity_opaque",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class PlayerCharacterRevisionRow(Base):
    __tablename__ = "player_character_revisions"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_identity_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_binding_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(source_reference) >= 1 "
            "AND source_reference REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_revisions_source_opaque",
        ),
        CheckConstraint(
            "contract_version = 'structured-player-character/v1'",
            name="ck_spc_revisions_contract",
        ),
        CheckConstraint(
            "record_revision BETWEEN 1 AND 9223372036854775807",
            name="ck_spc_revisions_revision_range",
        ),
        CheckConstraint(
            "prior_revision IS NULL "
            "OR (prior_revision BETWEEN 1 AND 9223372036854775806 "
            "AND prior_revision < record_revision)",
            name="ck_spc_revisions_prior_range",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "OCTET_LENGTH(record_canonical) >= 1",
            name="ck_spc_revisions_canonical_nonempty",
        ),
        ForeignKeyConstraint(
            ("player_character_id",),
            ("player_character_id_allocations.player_character_id",),
            name="fk_spc_revisions_allocation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("controller_binding",),
            ("player_character_controller_bindings.controller_binding",),
            name="fk_spc_revisions_controller_binding",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_spc_revisions_controller_binding",
            "controller_binding",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    record_revision: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    contract_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    controller_binding: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        nullable=False,
    )
    lifecycle: Mapped[str] = mapped_column(
        _ascii_varchar(16),
        nullable=False,
    )
    prior_revision: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    mutation_kind: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    authority_class: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        nullable=False,
    )
    record_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class PlayerCharacterCurrentRow(Base):
    __tablename__ = "player_character_current"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_current_identity_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_current_binding_opaque",
        ),
        CheckConstraint(
            "contract_version = 'structured-player-character/v1'",
            name="ck_spc_current_contract",
        ),
        CheckConstraint(
            "record_revision BETWEEN 1 AND 9223372036854775807",
            name="ck_spc_current_revision_range",
        ),
        CheckConstraint(
            "lifecycle IN ('active', 'retired', 'deceased')",
            name="ck_spc_current_lifecycle",
        ),
        CheckConstraint(
            "OCTET_LENGTH(record_canonical) >= 1",
            name="ck_spc_current_canonical_nonempty",
        ),
        ForeignKeyConstraint(
            ("player_character_id",),
            ("player_character_id_allocations.player_character_id",),
            name="fk_spc_current_allocation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("controller_binding",),
            ("player_character_controller_bindings.controller_binding",),
            name="fk_spc_current_controller_binding",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("player_character_id", "record_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_spc_current_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_spc_current_controller_identity",
            "controller_binding",
            "player_character_id",
        ),
        Index(
            "ix_spc_current_identity_revision",
            "player_character_id",
            "record_revision",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    contract_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    record_revision: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    controller_binding: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        nullable=False,
    )
    lifecycle: Mapped[str] = mapped_column(
        _ascii_varchar(16),
        nullable=False,
    )
    record_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class PlayerCharacterCreationReceiptRow(Base):
    __tablename__ = "player_character_creation_receipts"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(controller_binding) >= 1 "
            "AND controller_binding REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_binding_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_operation_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_creation_receipts_result_identity_opaque",
        ),
        CheckConstraint(
            "operation_namespace = 'player-character.create/v1' "
            "AND command_kind = 'CREATE'",
            name="ck_spc_creation_receipts_protocol",
        ),
        CheckConstraint(
            "result_schema_version = 'player-character.create-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1' "
            "AND resulting_revision = 1 "
            "AND resulting_lifecycle = 'active'",
            name="ck_spc_creation_receipts_result",
        ),
        CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536",
            name="ck_spc_creation_receipts_canonical_size",
        ),
        UniqueConstraint(
            "result_player_character_id",
            "resulting_revision",
            name="uq_spc_creation_receipts_result_revision",
        ),
        ForeignKeyConstraint(
            ("controller_binding",),
            ("player_character_controller_bindings.controller_binding",),
            name="fk_spc_creation_receipts_controller_binding",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("result_player_character_id",),
            ("player_character_id_allocations.player_character_id",),
            name="fk_spc_creation_receipts_allocation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("result_player_character_id", "resulting_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_spc_creation_receipts_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    controller_binding: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    operation_namespace: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        primary_key=True,
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    fingerprint: Mapped[bytes] = mapped_column(
        mysql.BINARY(32),
        nullable=False,
    )
    command_kind: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    result_schema_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    result_player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        nullable=False,
    )
    result_contract_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    resulting_revision: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    resulting_lifecycle: Mapped[str] = mapped_column(
        _ascii_varchar(16),
        nullable=False,
    )
    result_record_fingerprint: Mapped[bytes] = mapped_column(
        mysql.BINARY(32),
        nullable=False,
    )
    receipt_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    operation_evidence_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class PlayerCharacterMutationReceiptRow(Base):
    __tablename__ = "player_character_mutation_receipts"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(player_character_id) >= 1 "
            "AND player_character_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_identity_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(operation_id) >= 1 "
            "AND operation_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_operation_opaque",
        ),
        CheckConstraint(
            "CHAR_LENGTH(result_player_character_id) >= 1 "
            "AND result_player_character_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_spc_mutation_receipts_result_identity_opaque",
        ),
        CheckConstraint(
            "operation_namespace = 'player-character.mutate/v1' "
            "AND result_schema_version = 'player-character.mutate-result/v1' "
            "AND result_contract_version = 'structured-player-character/v1'",
            name="ck_spc_mutation_receipts_protocol",
        ),
        CheckConstraint(
            "player_character_id = result_player_character_id",
            name="ck_spc_mutation_receipts_owner_result",
        ),
        CheckConstraint(
            "expected_revision BETWEEN 1 AND 9223372036854775806 "
            "AND resulting_revision = expected_revision + 1 "
            "AND resulting_revision <= 9223372036854775807",
            name="ck_spc_mutation_receipts_revision_successor",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536",
            name="ck_spc_mutation_receipts_canonical_size",
        ),
        UniqueConstraint(
            "player_character_id",
            "resulting_revision",
            name="uq_spc_mutation_receipts_result_revision",
        ),
        ForeignKeyConstraint(
            ("player_character_id",),
            ("player_character_id_allocations.player_character_id",),
            name="fk_spc_mutation_receipts_allocation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("result_player_character_id",),
            ("player_character_id_allocations.player_character_id",),
            name="fk_spc_mutation_receipts_result_allocation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("player_character_id", "expected_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_spc_mutation_receipts_prior_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("result_player_character_id", "resulting_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_spc_mutation_receipts_result_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_spc_mutation_receipts_expected_revision",
            "player_character_id",
            "expected_revision",
        ),
        Index(
            "ix_spc_mutation_receipts_result_revision",
            "result_player_character_id",
            "resulting_revision",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    operation_namespace: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        primary_key=True,
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        primary_key=True,
    )
    fingerprint: Mapped[bytes] = mapped_column(
        mysql.BINARY(32),
        nullable=False,
    )
    command_kind: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    result_schema_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    expected_revision: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    result_player_character_id: Mapped[str] = mapped_column(
        _ascii_varchar(128),
        nullable=False,
    )
    result_contract_version: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    result_command_kind: Mapped[str] = mapped_column(
        _ascii_varchar(64),
        nullable=False,
    )
    command_result: Mapped[str] = mapped_column(
        _ascii_varchar(32),
        nullable=False,
    )
    resulting_revision: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    resulting_lifecycle: Mapped[str] = mapped_column(
        _ascii_varchar(16),
        nullable=False,
    )
    before_record_fingerprint: Mapped[bytes] = mapped_column(
        mysql.BINARY(32),
        nullable=False,
    )
    after_record_fingerprint: Mapped[bytes] = mapped_column(
        mysql.BINARY(32),
        nullable=False,
    )
    receipt_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    operation_evidence_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
    )


class RunRevisionRow(Base):
    __tablename__ = "run_revisions"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(run_id) >= 1 "
            "AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' "
            "AND CHAR_LENGTH(continuous_story_line_id) >= 1 "
            "AND continuous_story_line_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_run_revisions_identities_opaque",
        ),
        CheckConstraint(
            "state_version BETWEEN 1 AND 9223372036854775807",
            name="ck_run_revisions_version_range",
        ),
        CheckConstraint(
            "lifecycle_status IN "
            "('pre_first_turn', 'active', 'completed', 'terminated')",
            name="ck_run_revisions_lifecycle",
        ),
        CheckConstraint(
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
            name="ck_run_revisions_mutation_matrix",
        ),
        CheckConstraint(
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
        ),
        CheckConstraint(
            "("
            "lifecycle_status IN ('pre_first_turn', 'active') "
            "AND (binding_state IS NULL OR binding_state = 'active')"
            ") OR ("
            "lifecycle_status IN ('completed', 'terminated') "
            "AND (binding_state IS NULL OR binding_state = 'historical')"
            ")",
            name="ck_run_revisions_lifecycle_binding",
        ),
        UniqueConstraint(
            "run_id",
            "continuous_story_line_id",
            "state_version",
            name="uq_run_revisions_exact",
        ),
        ForeignKeyConstraint(
            ("binding_player_character_id", "binding_record_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_run_revisions_character_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_run_revisions_line_version",
            "continuous_story_line_id",
            "state_version",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    run_id: Mapped[str] = mapped_column(_ascii_varchar(128), primary_key=True)
    state_version: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    continuous_story_line_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    lifecycle_status: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    creation_operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    creation_source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    creation_occurred_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
    prior_state_version: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    mutation_kind: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
    binding_player_character_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    binding_contract_version: Mapped[str | None] = mapped_column(
        _ascii_varchar(64), nullable=True
    )
    binding_record_revision: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    binding_state: Mapped[str | None] = mapped_column(
        _ascii_varchar(16), nullable=True
    )
    binding_operation_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    binding_authority_source_ref: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    bound_at: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=True
    )
    inactivated_at: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )


class RunCurrentRow(Base):
    __tablename__ = "run_current"
    __table_args__ = (
        CheckConstraint(
            "CHAR_LENGTH(run_id) >= 1 "
            "AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' "
            "AND CHAR_LENGTH(continuous_story_line_id) >= 1 "
            "AND continuous_story_line_id REGEXP "
            "'^[A-Za-z0-9][A-Za-z0-9_.:-]*$'",
            name="ck_run_current_identities_opaque",
        ),
        CheckConstraint(
            "state_version BETWEEN 1 AND 9223372036854775807",
            name="ck_run_current_version_range",
        ),
        CheckConstraint(
            "lifecycle_status IN "
            "('pre_first_turn', 'active', 'completed', 'terminated')",
            name="ck_run_current_lifecycle",
        ),
        CheckConstraint(
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
            name="ck_run_current_mutation_matrix",
        ),
        CheckConstraint(
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
        ),
        CheckConstraint(
            "("
            "lifecycle_status IN ('pre_first_turn', 'active') "
            "AND (binding_state IS NULL OR binding_state = 'active')"
            ") OR ("
            "lifecycle_status IN ('completed', 'terminated') "
            "AND (binding_state IS NULL OR binding_state = 'historical')"
            ")",
            name="ck_run_current_lifecycle_binding",
        ),
        UniqueConstraint(
            "continuous_story_line_id",
            name="uq_run_current_story_line",
        ),
        UniqueConstraint(
            "active_player_character_id",
            name="uq_run_current_active_character",
        ),
        ForeignKeyConstraint(
            ("run_id", "continuous_story_line_id", "state_version"),
            (
                "run_revisions.run_id",
                "run_revisions.continuous_story_line_id",
                "run_revisions.state_version",
            ),
            name="fk_run_current_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("binding_player_character_id", "binding_record_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_run_current_character_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_run_current_identity_version",
            "run_id",
            "state_version",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    run_id: Mapped[str] = mapped_column(_ascii_varchar(128), primary_key=True)
    continuous_story_line_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    lifecycle_status: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    state_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    creation_operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    creation_source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    creation_occurred_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
    prior_state_version: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    mutation_kind: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
    binding_player_character_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    binding_contract_version: Mapped[str | None] = mapped_column(
        _ascii_varchar(64), nullable=True
    )
    binding_record_revision: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    binding_state: Mapped[str | None] = mapped_column(
        _ascii_varchar(16), nullable=True
    )
    binding_operation_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    binding_authority_source_ref: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    bound_at: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=True
    )
    inactivated_at: Mapped[datetime | None] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=True
    )
    active_player_character_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )


class RunSessionParticipationRow(Base):
    __tablename__ = "run_session_participations"
    __table_args__ = (
        CheckConstraint(
            "joined_state_version BETWEEN 2 AND 9223372036854775807",
            name="ck_run_participations_version_range",
        ),
        UniqueConstraint(
            "session_id",
            "run_id",
            "continuous_story_line_id",
            "joined_state_version",
            name="uq_run_participations_exact",
        ),
        UniqueConstraint(
            "run_id",
            "joined_state_version",
            name="uq_run_participations_revision",
        ),
        UniqueConstraint(
            "run_id",
            "operation_id",
            name="uq_run_participations_operation",
        ),
        ForeignKeyConstraint(
            ("session_id",),
            ("game_sessions.session_id",),
            name="fk_run_participations_session",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("run_id", "continuous_story_line_id", "joined_state_version"),
            (
                "run_revisions.run_id",
                "run_revisions.continuous_story_line_id",
                "run_revisions.state_version",
            ),
            name="fk_run_participations_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_run_participations_run_version",
            "run_id",
            "joined_state_version",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    session_id: Mapped[str] = mapped_column(
        _legacy_session_id_varchar(), primary_key=True
    )
    run_id: Mapped[str] = mapped_column(_ascii_varchar(128), nullable=False)
    continuous_story_line_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    joined_state_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    source_reference: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )


class RunCreationReceiptRow(Base):
    __tablename__ = "run_creation_receipts"
    __table_args__ = (
        CheckConstraint(
            "operation_namespace = 'run.create/v1' "
            "AND command_kind = 'CREATE' "
            "AND result_schema_version = 'run.create-result/v1' "
            "AND resulting_lifecycle_status = 'pre_first_turn' "
            "AND resulting_state_version = 1",
            name="ck_run_creation_receipts_protocol",
        ),
        CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536 "
            "AND OCTET_LENGTH(operation_evidence_canonical) >= 1",
            name="ck_run_creation_receipts_canonical",
        ),
        UniqueConstraint(
            "result_run_id",
            "resulting_state_version",
            name="uq_run_creation_receipts_result",
        ),
        ForeignKeyConstraint(
            (
                "result_run_id",
                "result_continuous_story_line_id",
                "resulting_state_version",
            ),
            (
                "run_revisions.run_id",
                "run_revisions.continuous_story_line_id",
                "run_revisions.state_version",
            ),
            name="fk_run_creation_receipts_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_run_creation_receipts_result",
            "result_run_id",
            "resulting_state_version",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    operation_namespace: Mapped[str] = mapped_column(
        _ascii_varchar(64), primary_key=True
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), primary_key=True
    )
    fingerprint: Mapped[bytes] = mapped_column(mysql.BINARY(32), nullable=False)
    command_kind: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    result_schema_version: Mapped[str] = mapped_column(
        _ascii_varchar(64), nullable=False
    )
    result_run_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    result_continuous_story_line_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    resulting_lifecycle_status: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    resulting_state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    receipt_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(), nullable=False
    )
    operation_evidence_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )


class RunMutationReceiptRow(Base):
    __tablename__ = "run_mutation_receipts"
    __table_args__ = (
        CheckConstraint(
            "expected_state_version BETWEEN 1 AND 9223372036854775806 "
            "AND resulting_state_version = expected_state_version + 1",
            name="ck_run_mutation_receipts_version_successor",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "run_id = result_run_id "
            "AND resulting_lifecycle_status IN "
            "('pre_first_turn', 'active', 'completed', 'terminated')",
            name="ck_run_mutation_receipts_result",
        ),
        CheckConstraint(
            "OCTET_LENGTH(receipt_canonical) BETWEEN 1 AND 65536 "
            "AND OCTET_LENGTH(operation_evidence_canonical) >= 1",
            name="ck_run_mutation_receipts_canonical",
        ),
        UniqueConstraint(
            "run_id",
            "resulting_state_version",
            name="uq_run_mutation_receipts_result",
        ),
        ForeignKeyConstraint(
            (
                "result_run_id",
                "result_continuous_story_line_id",
                "resulting_state_version",
            ),
            (
                "run_revisions.run_id",
                "run_revisions.continuous_story_line_id",
                "run_revisions.state_version",
            ),
            name="fk_run_mutation_receipts_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            (
                "participation_session_id",
                "result_run_id",
                "result_continuous_story_line_id",
                "resulting_state_version",
            ),
            (
                "run_session_participations.session_id",
                "run_session_participations.run_id",
                "run_session_participations.continuous_story_line_id",
                "run_session_participations.joined_state_version",
            ),
            name="fk_run_mutation_receipts_participation",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ("result_player_character_id", "result_character_record_revision"),
            (
                "player_character_revisions.player_character_id",
                "player_character_revisions.record_revision",
            ),
            name="fk_run_mutation_receipts_character_revision",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        Index(
            "ix_run_mutation_receipts_result",
            "result_run_id",
            "resulting_state_version",
        ),
        Index(
            "ix_run_mutation_receipts_participation",
            "participation_session_id",
            "result_run_id",
            "result_continuous_story_line_id",
            "resulting_state_version",
        ),
        PLAYER_CHARACTER_TABLE_OPTIONS,
    )

    run_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), primary_key=True
    )
    operation_namespace: Mapped[str] = mapped_column(
        _ascii_varchar(64), primary_key=True
    )
    operation_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), primary_key=True
    )
    fingerprint: Mapped[bytes] = mapped_column(mysql.BINARY(32), nullable=False)
    command_kind: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    result_schema_version: Mapped[str] = mapped_column(
        _ascii_varchar(64), nullable=False
    )
    expected_state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    result_run_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    result_continuous_story_line_id: Mapped[str] = mapped_column(
        _ascii_varchar(128), nullable=False
    )
    resulting_lifecycle_status: Mapped[str] = mapped_column(
        _ascii_varchar(32), nullable=False
    )
    resulting_state_version: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    participation_session_id: Mapped[str | None] = mapped_column(
        _legacy_session_id_varchar(), nullable=True
    )
    participation_operation_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    participation_source_reference: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    result_player_character_id: Mapped[str | None] = mapped_column(
        _ascii_varchar(128), nullable=True
    )
    result_character_contract_version: Mapped[str | None] = mapped_column(
        _ascii_varchar(64), nullable=True
    )
    result_character_record_revision: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    receipt_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(), nullable=False
    )
    operation_evidence_canonical: Mapped[bytes] = mapped_column(
        mysql.MEDIUMBLOB(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6), nullable=False
    )
