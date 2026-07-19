"""add durable narrative jobs

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260719_0003"
down_revision: str | None = "20260719_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "narrative_jobs",
        sa.Column("job_id", sa.String(64), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("turn_id", sa.String(64), nullable=False),
        sa.Column("client_request_id", sa.String(64), nullable=False),
        sa.Column("action_signature", sa.String(64), nullable=False),
        sa.Column("prepared_state_version", sa.BigInteger(), nullable=False),
        sa.Column("state_fingerprint", sa.String(64), nullable=False),
        sa.Column("scenario_id", sa.String(128), nullable=False),
        sa.Column("scenario_content_version", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("narrative_request_json", mysql.JSON(), nullable=False),
        sa.Column("prompt_schema_version", sa.String(64), nullable=False),
        sa.Column("style_profile_version", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_token", sa.String(128), nullable=True),
        sa.Column("lease_owner", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validated_proposal_json", mysql.JSON(), nullable=True),
        sa.Column("validated_proposal_digest", sa.String(64), nullable=True),
        sa.Column("outcome_rule_id", sa.String(128), nullable=True),
        sa.Column("accepted_narrative_text", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ("session_id",), ("game_sessions.session_id",), ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "session_id",
            "client_request_id",
            name="uq_narrative_jobs_session_client_request",
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_narrative_jobs_session_status",
        "narrative_jobs",
        ("session_id", "status"),
    )
    op.create_index(
        "ix_narrative_jobs_status_lease",
        "narrative_jobs",
        ("status", "lease_expires_at"),
    )
    op.create_index(
        "ix_narrative_jobs_session_turn",
        "narrative_jobs",
        ("session_id", "turn_id"),
    )


def downgrade() -> None:
    op.drop_index("ix_narrative_jobs_session_turn", table_name="narrative_jobs")
    op.drop_index("ix_narrative_jobs_status_lease", table_name="narrative_jobs")
    op.drop_index("ix_narrative_jobs_session_status", table_name="narrative_jobs")
    op.drop_table("narrative_jobs")
