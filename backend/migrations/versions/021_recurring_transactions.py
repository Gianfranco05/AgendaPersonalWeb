"""recurring transactions + occurrences, transactions index, investments.renewed_from_id

Revision ID: 021_recurring_transactions
Revises: 020_market_data
Create Date: 2026-10-26

"""

from alembic import op
import sqlalchemy as sa

revision = "021_recurring_transactions"
down_revision = "020_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column(
            "bank_account_id", sa.String(36), sa.ForeignKey("bank_accounts.id"), nullable=True
        ),
        sa.Column("account_type", sa.String(10), nullable=False, server_default="cash"),
        sa.Column("payment_method", sa.String(20), nullable=False, server_default="cash"),
        sa.Column("merchant_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("merchant_category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("frequency", sa.String(10), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("weekday", sa.SmallInteger(), nullable=True),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=True),
        sa.Column("month_of_year", sa.SmallInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=False),
        sa.Column("next_occurrence_date", sa.Date(), nullable=True),
        sa.Column("last_occurrence_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount IS NULL OR amount > 0", name="ck_recurring_amount_positive"),
        sa.CheckConstraint(
            "amount IS NOT NULL OR requires_confirmation", name="ck_recurring_amount_or_confirm"
        ),
        sa.CheckConstraint("interval_count >= 1", name="ck_recurring_interval_positive"),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name="ck_recurring_dates_order"
        ),
        sa.CheckConstraint("status IN ('active', 'paused')", name="ck_recurring_status"),
        sa.CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly', 'yearly')", name="ck_recurring_frequency"
        ),
    )
    op.create_index("ix_recurring_user_status", "recurring_transactions", ["user_id", "status"])
    op.create_index(
        "ix_recurring_status_next", "recurring_transactions", ["status", "next_occurrence_date"]
    )

    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column(
            "recurrence_id",
            sa.String(36),
            sa.ForeignKey("recurring_transactions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("suggested_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("recurrence_id", "occurrence_date", name="uq_recurring_occurrence_date"),
        sa.CheckConstraint(
            "status IN ('generated', 'pending', 'confirmed', 'skipped')",
            name="ck_recurring_occurrence_status",
        ),
    )
    op.create_index("ix_occurrences_user_status", "recurring_occurrences", ["user_id", "status"])

    op.create_index(
        "ix_transactions_recurring_parent_id", "transactions", ["recurring_parent_id"]
    )

    # batch_alter_table: SQLite no puede agregar una FK con ALTER TABLE.
    with op.batch_alter_table("investments") as batch:
        batch.add_column(sa.Column("renewed_from_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_investments_renewed_from", "investments", ["renewed_from_id"], ["id"]
        )
    op.create_index("uq_investments_renewed_from", "investments", ["renewed_from_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_investments_renewed_from", table_name="investments")
    with op.batch_alter_table("investments") as batch:
        batch.drop_constraint("fk_investments_renewed_from", type_="foreignkey")
        batch.drop_column("renewed_from_id")

    op.drop_index("ix_transactions_recurring_parent_id", table_name="transactions")

    op.drop_index("ix_occurrences_user_status", table_name="recurring_occurrences")
    op.drop_table("recurring_occurrences")

    op.drop_index("ix_recurring_status_next", table_name="recurring_transactions")
    op.drop_index("ix_recurring_user_status", table_name="recurring_transactions")
    op.drop_table("recurring_transactions")
