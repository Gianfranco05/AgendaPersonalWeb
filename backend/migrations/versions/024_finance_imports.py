"""importacion de movimientos: lotes (import_batches) + huella/lote en transactions

Revision ID: 024_finance_imports
Revises: 023_habit_reminders
Create Date: 2026-11-04

"""

from alembic import op
import sqlalchemy as sa

revision = "024_finance_imports"
down_revision = "023_habit_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True
        ),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("preset", sa.String(40), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("header_signature", sa.String(64), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column(
            "account_id",
            sa.String(36),
            sa.ForeignKey("bank_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_table", sa.JSON(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('preview', 'confirmed', 'undone')", name="ck_import_batches_status"
        ),
    )
    op.create_index(
        "ix_import_batches_user_created", "import_batches", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_import_batches_user_signature", "import_batches", ["user_id", "header_signature"]
    )

    # batch_alter_table: SQLite no agrega una FK con ALTER TABLE; en Postgres
    # emite ALTERs directos. Columnas nulas, sin backfill.
    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("import_batch_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("import_row_hash", sa.String(64), nullable=True))
        batch.create_foreign_key(
            "fk_transactions_import_batch_id",
            "import_batches",
            ["import_batch_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index(
            "ix_transactions_user_import_hash", ["user_id", "import_row_hash"]
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_index("ix_transactions_user_import_hash")
        batch.drop_constraint("fk_transactions_import_batch_id", type_="foreignkey")
        batch.drop_column("import_row_hash")
        batch.drop_column("import_batch_id")

    op.drop_index("ix_import_batches_user_signature", table_name="import_batches")
    op.drop_index("ix_import_batches_user_created", table_name="import_batches")
    op.drop_table("import_batches")
