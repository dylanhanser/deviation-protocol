"""create initial MySQL game persistence schema

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19 00:00:00
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260719_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


def upgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("player_id", sa.String(64), nullable=False),
        sa.Column("scenario_id", sa.String(128), nullable=False),
        sa.Column("scenario_version", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_game_sessions_player_id", "game_sessions", ["player_id"])
    op.create_index(
        "ix_game_sessions_scenario", "game_sessions", ["scenario_id", "scenario_version"]
    )

    op.create_table(
        "game_snapshots",
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("game_sessions.session_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("state_version", sa.BigInteger(), nullable=False),
        sa.Column("state_json", mysql.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "domain_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("game_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_id", sa.String(64), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("payload_json", mysql.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id", "sequence_no", name="uq_domain_events_session_sequence"
        ),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_domain_events_session_turn", "domain_events", ["session_id", "turn_id"]
    )
    op.create_index(
        "ix_domain_events_type_occurred", "domain_events", ["event_type", "occurred_at"]
    )

    op.create_table(
        "turn_requests",
        sa.Column("request_id", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("game_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_id", sa.String(64), nullable=False),
        sa.Column("client_request_id", sa.String(64), nullable=False),
        sa.Column("action_signature", sa.String(64), nullable=False),
        sa.Column("route", sa.String(40), nullable=False),
        sa.Column("request_json", mysql.JSON(), nullable=False),
        sa.Column("response_json", mysql.JSON(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "session_id",
            "client_request_id",
            name="uq_turn_requests_session_client_request",
        ),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_turn_requests_session_turn", "turn_requests", ["session_id", "turn_id"]
    )
    op.create_index(
        "ix_turn_requests_signature", "turn_requests", ["session_id", "action_signature"]
    )
    op.create_index("ix_turn_requests_created_at", "turn_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_turn_requests_created_at", table_name="turn_requests")
    op.drop_index("ix_turn_requests_signature", table_name="turn_requests")
    op.drop_index("ix_turn_requests_session_turn", table_name="turn_requests")
    op.drop_table("turn_requests")

    op.drop_index("ix_domain_events_type_occurred", table_name="domain_events")
    op.drop_index("ix_domain_events_session_turn", table_name="domain_events")
    op.drop_table("domain_events")

    op.drop_table("game_snapshots")
    op.drop_index("ix_game_sessions_scenario", table_name="game_sessions")
    op.drop_index("ix_game_sessions_player_id", table_name="game_sessions")
    op.drop_table("game_sessions")
