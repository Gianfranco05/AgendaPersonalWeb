"""add withdrawal_requests table (Boton de arrepentimiento, Res. 424/2020)

Revision ID: 017_withdrawal_requests
Revises: 016_push_notifications
Create Date: 2026-10-06

"""

from alembic import op
import sqlalchemy as sa

revision = "017_withdrawal_requests"
down_revision = "016_push_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("purchase_detail", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "needs_review", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("withdrawal_requests")
