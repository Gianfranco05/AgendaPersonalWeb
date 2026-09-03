"""Endpoints de autoservicio de la cuenta: exportar los datos y darse de baja.

Un SaaS que guarda finanzas y datos de salud tiene que poder responder "dame
todo lo mio" y "borra todo lo mio" sin intervencion manual del operador.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.security import verify_password
from app.database import get_db
from app.modules.auth.models import User
from app.modules.cuenta.service import AccountService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["account"])


class DeleteAccountRequest(BaseModel):
    # Reautenticacion: el borrado es irreversible, y una sesion abierta en un
    # dispositivo ajeno no deberia alcanzar para destruir la cuenta.
    password: str


@router.get("/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descarga un JSON con todos los datos del usuario."""
    data = await AccountService(db).export(current_user)
    filename = f"vida-personal-export-{current_user.id}.json"
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_my_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Borra la cuenta y todos sus datos. Irreversible."""
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contraseña incorrecta",
        )

    # No hay nada que cancelar en Stripe: las plantillas son de pago unico, no
    # queda ningun cobro corriendo. El customer se deja vivo en Stripe a
    # proposito — es el respaldo contable de las compras y de un eventual
    # reembolso, y no se puede reconstruir despues de borrar la cuenta.
    await AccountService(db).delete_account(current_user)

    response = JSONResponse(content={"detail": "Cuenta eliminada"})
    response.delete_cookie(settings.JWT_COOKIE_NAME)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME)
    return response
