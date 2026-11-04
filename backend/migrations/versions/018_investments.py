"""add investments table + exchange rates / net-worth preferences

Revision ID: 018_investments
Revises: 017_withdrawal_requests
Create Date: 2026-10-15

"""

from alembic import op
import sqlalchemy as sa

revision = "018_investments"
down_revision = "017_withdrawal_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=True),
        sa.Column("invested_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("interest_rate_tna", sa.Numeric(7, 4), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("institution", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("notify_maturity", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("timezone_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("price_source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("last_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("last_price_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("value_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eve_notice_for", sa.Date(), nullable=True),
        sa.Column("day_notice_for", sa.Date(), nullable=True),
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
        sa.CheckConstraint("invested_amount >= 0", name="ck_investments_invested_nonneg"),
        sa.CheckConstraint(
            "current_value IS NULL OR current_value >= 0", name="ck_investments_value_nonneg"
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_investments_quantity_nonneg"
        ),
        sa.CheckConstraint(
            "interest_rate_tna IS NULL OR interest_rate_tna >= 0",
            name="ck_investments_tna_nonneg",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR maturity_date IS NULL OR maturity_date >= start_date",
            name="ck_investments_dates_order",
        ),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_investments_status"),
    )
    op.create_index("ix_investments_user_status", "investments", ["user_id", "status"])
    op.create_index("ix_investments_status_maturity", "investments", ["status", "maturity_date"])

    op.add_column("user_preferences", sa.Column("fx_usd_ars", sa.Numeric(14, 4), nullable=True))
    op.add_column("user_preferences", sa.Column("fx_eur_ars", sa.Numeric(14, 4), nullable=True))
    op.add_column(
        "user_preferences",
        sa.Column("fx_rates_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_preferences",
        sa.Column(
            "include_investments_in_balance",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    # SQLite no soporta DROP COLUMN sin recrear la tabla: batch_alter_table
    # hace eso en SQLite y un ALTER directo en Postgres.
    with op.batch_alter_table("user_preferences") as batch:
        batch.drop_column("include_investments_in_balance")
        batch.drop_column("fx_rates_updated_at")
        batch.drop_column("fx_eur_ars")
        batch.drop_column("fx_usd_ars")

    op.drop_index("ix_investments_status_maturity", table_name="investments")
    op.drop_index("ix_investments_user_status", table_name="investments")
    op.drop_table("investments")
