"""add push_tokens table and reminders.timezone_offset_minutes

Revision ID: 016_push_notifications
Revises: 015_terms_acceptance
Create Date: 2026-09-21

"""

from alembic import op
import sqlalchemy as sa

revision = "016_push_notifications"
down_revision = "015_terms_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("token", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("device_info", sa.String(255), nullable=True),
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
    op.add_column(
        "reminders", sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("reminders", "timezone_offset_minutes")
    op.drop_table("push_tokens")
