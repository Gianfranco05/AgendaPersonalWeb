"""add reminders table

Revision ID: 014_reminders
Revises: 013_work_travel_vehicle_projects
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "014_reminders"
down_revision = "013_work_travel_vehicle_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("message", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(8), nullable=False, server_default="🔔"),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False, server_default="0"),
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
    )


def downgrade() -> None:
    op.drop_table("reminders")
