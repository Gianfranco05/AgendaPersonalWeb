"""add books and media_items tables (plantillas Biblioteca y Peliculas)

Revision ID: 012_library_media
Revises: 011_module_purchases
Create Date: 2026-09-03

"""

from alembic import op
import sqlalchemy as sa

revision = "012_library_media"
down_revision = "011_module_purchases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendiente", index=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("started_date", sa.Date(), nullable=True),
        sa.Column("finished_date", sa.Date(), nullable=True),
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
        "media_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False, server_default="pelicula"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pendiente", index=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
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
    op.drop_table("media_items")
    op.drop_table("books")
