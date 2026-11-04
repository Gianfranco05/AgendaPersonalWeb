"""add age_confirmed_at to users (minimum-age declaration)

Revision ID: 019_age_confirmation
Revises: 018_investments
Create Date: 2026-10-26

"""

from alembic import op
import sqlalchemy as sa

revision = "019_age_confirmation"
down_revision = "018_investments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sin backfill: los usuarios existentes quedan en NULL y el gate de
    # terminos de los clientes les pide declarar la edad en la proxima entrada.
    op.add_column(
        "users", sa.Column("age_confirmed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    # batch_alter_table: SQLite no soporta DROP COLUMN en versiones viejas.
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("age_confirmed_at")
