"""add session creation idempotency and character identity

Revision ID: 20260719_0002
Revises: 20260719_0001
Create Date: 2026-07-19 00:00:01
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_0002"
down_revision: str | None = "20260719_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing pre-Phase-1.4 rows remain NULL and are intentionally not assigned a
    # synthetic client request key. New API-created rows always provide both fields.
    op.add_column(
        "game_sessions",
        sa.Column("creation_client_request_id", sa.String(64), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("character_definition_id", sa.String(128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_game_sessions_player_creation_request",
        "game_sessions",
        ["player_id", "creation_client_request_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_game_sessions_player_creation_request",
        "game_sessions",
        type_="unique",
    )
    op.drop_column("game_sessions", "character_definition_id")
    op.drop_column("game_sessions", "creation_client_request_id")
