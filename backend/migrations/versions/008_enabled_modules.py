"""add enabled_modules table

Revision ID: 008_enabled_modules
Revises: 007_subscriptions
Create Date: 2026-09-02

"""

from alembic import op
import sqlalchemy as sa

revision = "008_enabled_modules"
down_revision = "007_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enabled_modules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("user_id", "module_key", name="uq_enabled_module_user_key"),
    )


def downgrade() -> None:
    op.drop_table("enabled_modules")
