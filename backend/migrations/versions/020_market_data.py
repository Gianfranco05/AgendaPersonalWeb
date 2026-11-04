"""market data tables (fx, inflation, crypto prices, fetch state) + fx source prefs

Revision ID: 020_market_data
Revises: 019_age_confirmation
Create Date: 2026-10-26

"""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "020_market_data"
down_revision = "019_age_confirmation"
branch_labels = None
depends_on = None

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def upgrade() -> None:
    op.create_table(
        "fx_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("quote_date", sa.Date(), nullable=False),
        sa.Column("buy", sa.Numeric(14, 4), nullable=True),
        sa.Column("sell", sa.Numeric(14, 4), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("currency", "kind", "quote_date", name="uq_fx_quotes_day"),
    )
    op.create_index("ix_fx_quotes_latest", "fx_quotes", ["currency", "kind", "quote_date"])

    op.create_table(
        "inflation_monthly",
        sa.Column("period", sa.Date(), primary_key=True),
        sa.Column("pct", sa.Numeric(7, 4), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "market_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("vs_currency", sa.String(5), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "symbol", "vs_currency", name="uq_market_prices_pair"),
    )

    state = op.create_table(
        "market_fetch_state",
        sa.Column("source", sa.String(20), primary_key=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(300), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
    )
    # next_run_at en el pasado: el primer ciclo del scheduler consulta enseguida.
    op.bulk_insert(
        state,
        [
            {"source": s, "next_run_at": _EPOCH, "consecutive_failures": 0}
            for s in ("fx", "inflation", "crypto")
        ],
    )

    op.add_column(
        "user_preferences",
        sa.Column("fx_usd_source", sa.String(10), nullable=False, server_default="mep"),
    )
    op.add_column(
        "user_preferences",
        sa.Column("fx_eur_source", sa.String(10), nullable=False, server_default="oficial"),
    )
    # Quien ya cargo una cotizacion sigue viendo exactamente lo mismo.
    op.execute(
        "UPDATE user_preferences SET fx_usd_source = 'manual' WHERE fx_usd_ars IS NOT NULL"
    )
    op.execute(
        "UPDATE user_preferences SET fx_eur_source = 'manual' WHERE fx_eur_ars IS NOT NULL"
    )


def downgrade() -> None:
    # Sin el provider automatico, esos activos vuelven a valuarse a mano.
    op.execute("UPDATE investments SET price_source = 'manual' WHERE price_source = 'coingecko'")

    # batch_alter_table: SQLite no soporta DROP COLUMN sin recrear la tabla.
    with op.batch_alter_table("user_preferences") as batch:
        batch.drop_column("fx_eur_source")
        batch.drop_column("fx_usd_source")

    op.drop_table("market_fetch_state")
    op.drop_table("market_prices")
    op.drop_table("inflation_monthly")
    op.drop_index("ix_fx_quotes_latest", table_name="fx_quotes")
    op.drop_table("fx_quotes")
