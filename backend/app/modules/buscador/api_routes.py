from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.http_security import rate_limit_search
from app.database import get_db
from app.modules.auth.models import User
from app.modules.buscador.normalize import QueryError
from app.modules.buscador.schemas import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    SearchResponse,
    parse_types,
)
from app.modules.buscador.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.get("", response_model=SearchResponse)
async def search(
    response: Response,
    q: str = Query(..., max_length=1000),
    types: Optional[str] = Query(None, max_length=300),
    limit: int = Query(DEFAULT_LIMIT),
    current_user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_search),
    db: AsyncSession = Depends(get_db),
):
    """Busca en las entidades del usuario autenticado, agrupadas por tipo.

    Solo lectura. Los terminos pueden ser sensibles (salud, plata): la
    respuesta no se cachea y la app no los escribe en ningun log.
    """
    if not 1 <= limit <= MAX_LIMIT:
        raise _unprocessable(f"El límite debe estar entre 1 y {MAX_LIMIT}")
    try:
        wanted = parse_types(types)
    except ValueError as exc:
        raise _unprocessable(str(exc))
    response.headers["Cache-Control"] = "no-store"
    try:
        return await SearchService(db).search(str(current_user.id), q, wanted, limit)
    except QueryError as exc:
        raise _unprocessable(str(exc))
