"""add terms acceptance tracking to users

Revision ID: 015_terms_acceptance
Revises: 014_reminders
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "015_terms_acceptance"
down_revision = "014_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("terms_accepted_version", sa.String(20), nullable=True))
    op.add_column(
        "users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "terms_accepted_version")
