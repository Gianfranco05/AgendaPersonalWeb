"""user_preferences.onboarding_version_seen (tutorial de bienvenida)

Revision ID: 022_onboarding_seen
Revises: 021_recurring_transactions
Create Date: 2026-10-27

"""

from alembic import op
import sqlalchemy as sa

revision = "022_onboarding_seen"
down_revision = "021_recurring_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sin backfill: los usuarios existentes ven el tutorial una vez.
    op.add_column(
        "user_preferences",
        sa.Column(
            "onboarding_version_seen",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    # SQLite no soporta DROP COLUMN sin recrear la tabla: batch_alter_table
    # hace eso en SQLite y un ALTER directo en Postgres.
    with op.batch_alter_table("user_preferences") as batch:
        batch.drop_column("onboarding_version_seen")
