"""add user_preferences table

Revision ID: 002_user_preferences
Revises: 001_initial
Create Date: 2026-06-08

"""

from alembic import op
import sqlalchemy as sa

revision = "002_user_preferences"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("theme_color", sa.String(20), nullable=False, server_default="violet"),
        sa.Column("date_format", sa.String(20), nullable=False, server_default="DD/MM/YYYY"),
        sa.Column("google_access_token", sa.Text(), nullable=True),
        sa.Column("google_refresh_token", sa.Text(), nullable=True),
        sa.Column("google_token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("google_calendar_id", sa.String(100), nullable=False, server_default="primary"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
