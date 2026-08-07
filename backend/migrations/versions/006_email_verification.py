"""add verification_tokens table and users.is_verified

Revision ID: 006_email_verification
Revises: 005_refresh_tokens
Create Date: 2026-08-06

"""

from alembic import op
import sqlalchemy as sa

revision = "006_email_verification"
down_revision = "005_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Las cuentas que ya existian son reales y venian usando la app: marcarlas
    # como no verificadas les mostraria un aviso que no pueden resolver.
    op.execute("UPDATE users SET is_verified = true")

    op.create_table(
        "verification_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("purpose", sa.String(20), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("verification_tokens")
    op.drop_column("users", "is_verified")
