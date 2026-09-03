"""add subjects and exams tables (modulo Estudio)

Revision ID: 010_study
Revises: 009_focus_sessions
Create Date: 2026-09-02

"""

from alembic import op
import sqlalchemy as sa

revision = "010_study"
down_revision = "009_focus_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("professor", sa.String(120), nullable=True),
        sa.Column("color", sa.String(9), nullable=False, server_default="#6366F1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="cursando"),
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
        "exams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "subject_id",
            sa.String(36),
            sa.ForeignKey("subjects.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False, index=True),
        sa.Column("grade", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
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
    op.drop_table("exams")
    op.drop_table("subjects")
