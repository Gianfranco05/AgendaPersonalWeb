"""Exportar (xlsx/pdf) e importar (csv/xlsx) movimientos de Finanzas.

Finanzas es plantilla base: sin `require_module`, todas las rutas con
`get_current_user` y filtradas por usuario.
"""

import logging
import tempfile
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.dependencies import get_current_user
from app.core.http_security import rate_limit_finance_export
from app.database import get_db
from app.modules.auth.models import User
from app.modules.finanzas.transfer.export_pdf import build_pdf
from app.modules.finanzas.transfer.export_xlsx import build_xlsx
from app.modules.finanzas.transfer.report_data import (
    ReportFilters,
    build_report,
    check_row_limit,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["finance"])

MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
CHUNK = 64 * 1024


def _iter_file(f):
    try:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            yield chunk
    finally:
        f.close()


@router.get("/export", dependencies=[Depends(rate_limit_finance_export)])
async def export_finance(
    format: Literal["xlsx", "pdf"],
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    type: Optional[Literal["income", "expense"]] = None,
    category_id: Optional[str] = Query(None, max_length=36),
    account_id: Optional[str] = Query(None, max_length=36),
    include_investments: bool = False,
    tz_offset_minutes: int = Query(0, ge=-840, le=840),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = str(current_user.id)
    filters = ReportFilters.resolve(
        date_from,
        date_to,
        tz_offset_minutes,
        type=type,
        category_id=category_id,
        account_id=account_id,
        include_investments=include_investments,
    )
    category, account = await check_row_limit(db, user_id, filters, format)
    data = await build_report(db, user_id, filters, tz_offset_minutes, category, account)

    def _generate():
        # Un .xlsx (zip) o un PDF no se pueden emitir antes de terminarlos:
        # se arman completos en un temporal (en memoria hasta 8 MiB) y se
        # devuelven por chunks. Corre en un thread: no bloquea el event loop.
        buffer = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        try:
            (build_xlsx if format == "xlsx" else build_pdf)(data, buffer)
            size = buffer.tell()
            buffer.seek(0)
        except Exception:
            buffer.close()
            raise
        return buffer, size

    buffer, size = await run_in_threadpool(_generate)
    filename = f"cancen-finanzas-{filters.date_from.isoformat()}_{filters.date_to.isoformat()}.{format}"
    return StreamingResponse(
        _iter_file(buffer),
        media_type=MEDIA_TYPES[format],
        headers={
            "Content-Length": str(size),
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
