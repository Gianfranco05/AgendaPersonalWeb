"""add subscriptions table

Revision ID: 007_subscriptions
Revises: 006_email_verification
Create Date: 2026-08-06

"""

from alembic import op
import sqlalchemy as sa

revision = "007_subscriptions"
down_revision = "006_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, index=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, index=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
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
    op.drop_table("subscriptions")
