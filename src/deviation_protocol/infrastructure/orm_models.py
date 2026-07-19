from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
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

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
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
