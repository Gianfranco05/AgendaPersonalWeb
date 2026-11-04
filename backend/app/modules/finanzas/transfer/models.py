from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class ImportBatch(Base):
    """Un archivo importado: la previsualizacion (`preview`), el lote confirmado
    (`confirmed`, deshacible) o el deshecho (`undone`).

    `raw_table` guarda las celdas decodificadas solo mientras esta en `preview`
    (para recalcular el mapeo sin volver a subir el archivo) y se vacia al
    confirmar o descartar.
    """

    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('preview', 'confirmed', 'undone')", name="ck_import_batches_status"
        ),
        Index("ix_import_batches_user_created", "user_id", "created_at"),
        Index("ix_import_batches_user_signature", "user_id", "header_signature"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="preview")
    preset: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    header_signature: Mapped[str] = mapped_column(String(64))
    header_row: Mapped[int] = mapped_column(Integer, default=0)
    mapping: Mapped[dict] = mapped_column(JSON)
    account_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    raw_table: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    undone_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
