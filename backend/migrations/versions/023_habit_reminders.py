"""avisos de habitos sin marcar: configuracion, marcas de envio y campos en goals

Revision ID: 023_habit_reminders
Revises: 022_onboarding_seen
Create Date: 2026-11-03

"""

from alembic import op
import sqlalchemy as sa

revision = "023_habit_reminders"
down_revision = "022_onboarding_seen"
branch_labels = None
depends_on = None

GOAL_TIME_CHECK = (
    "(reminder_hour IS NULL AND reminder_minute IS NULL) OR "
    "(reminder_hour IS NOT NULL AND reminder_minute IS NOT NULL AND "
    "reminder_hour >= 0 AND reminder_hour <= 23 AND "
    "reminder_minute >= 0 AND reminder_minute <= 59)"
)


def upgrade() -> None:
    # batch_alter_table: SQLite no puede agregar un CHECK con ALTER TABLE; en
    # Postgres emite ALTERs directos. Los avisos arrancan ENCENDIDOS para los
    # habitos existentes (server_default true).
    with op.batch_alter_table("goals") as batch:
        batch.add_column(
            sa.Column(
                "reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
            )
        )
        batch.add_column(sa.Column("reminder_hour", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("reminder_minute", sa.Integer(), nullable=True))
        batch.create_check_constraint("ck_goals_reminder_time", GOAL_TIME_CHECK)

    op.create_table(
        "habit_reminder_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("hour", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_cap", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("streak_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("hour >= 0 AND hour <= 23", name="ck_habit_reminder_hour"),
        sa.CheckConstraint("minute >= 0 AND minute <= 59", name="ck_habit_reminder_minute"),
        sa.CheckConstraint("daily_cap >= 1 AND daily_cap <= 5", name="ck_habit_reminder_cap"),
        sa.CheckConstraint(
            "timezone_offset_minutes IS NULL OR "
            "(timezone_offset_minutes >= -840 AND timezone_offset_minutes <= 840)",
            name="ck_habit_reminder_tz",
        ),
    )
    op.create_index(
        "ix_habit_reminder_settings_user_id", "habit_reminder_settings", ["user_id"], unique=True
    )

    op.create_table(
        "habit_reminder_dispatches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(5), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("goal_ids", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "local_date", "slot", name="uq_habit_reminder_dispatch"),
    )
    op.create_index(
        "ix_habit_reminder_dispatches_user_id", "habit_reminder_dispatches", ["user_id"]
    )
    op.create_index(
        "ix_habit_reminder_dispatch_user_date",
        "habit_reminder_dispatches",
        ["user_id", "local_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_habit_reminder_dispatch_user_date", table_name="habit_reminder_dispatches")
    op.drop_index("ix_habit_reminder_dispatches_user_id", table_name="habit_reminder_dispatches")
    op.drop_table("habit_reminder_dispatches")

    op.drop_index("ix_habit_reminder_settings_user_id", table_name="habit_reminder_settings")
    op.drop_table("habit_reminder_settings")

    with op.batch_alter_table("goals") as batch:
        batch.drop_constraint("ck_goals_reminder_time", type_="check")
        batch.drop_column("reminder_minute")
        batch.drop_column("reminder_hour")
        batch.drop_column("reminder_enabled")
