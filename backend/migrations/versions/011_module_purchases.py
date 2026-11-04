"""compras de plantillas en vez de suscripcion

Cambio de modelo de negocio: no hay plan mensual. Cada plantilla paga se
compra una vez y queda en la cuenta.

- `subscriptions` se reemplaza por `stripe_customers` (solo el vinculo con
  Stripe) + `module_purchases` (lo que la persona compro).
- Los stripe_customer_id existentes se copian para no perder el vinculo con
  Stripe de las cuentas que ya lo tenian.

Revision ID: 011_module_purchases
Revises: 010_study
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "011_module_purchases"
down_revision = "010_study"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stripe_customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False, index=True),
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

    op.create_table(
        "module_purchases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("amount_paid", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("stripe_session_id", sa.String(255), nullable=True, index=True),
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
        sa.UniqueConstraint("user_id", "module_key", name="uq_module_purchase_user_key"),
    )

    # Se rescata el vinculo con Stripe de las cuentas que ya lo tenian; el plan
    # y el estado de la suscripcion no se migran porque ya no existen como
    # concepto.
    op.execute(
        """
        INSERT INTO stripe_customers (id, user_id, stripe_customer_id, created_at, updated_at)
        SELECT id, user_id, stripe_customer_id, created_at, updated_at
        FROM subscriptions
        WHERE stripe_customer_id IS NOT NULL
        """
    )

    op.drop_table("subscriptions")


def downgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True, index=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, index=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
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

    op.execute(
        """
        INSERT INTO subscriptions (id, user_id, plan, stripe_customer_id, created_at, updated_at)
        SELECT id, user_id, 'free', stripe_customer_id, created_at, updated_at
        FROM stripe_customers
        """
    )

    op.drop_table("module_purchases")
    op.drop_table("stripe_customers")
