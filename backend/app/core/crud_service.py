"""Helpers compartidos por los `service.py` de las plantillas de pago.

Cada modulo (biblioteca, peliculas, trabajo, viajes, vehiculo, proyectos,
estudio, recordatorios) resuelve dos cosas de la misma manera:

1. "Traeme la entidad por id, validando que sea del usuario; si no existe o es
   de otro usuario, 404."
2. "Aplicá este dict de cambios (de `body.model_dump(exclude_unset=True)`)
   sobre la entidad."

Estas funciones capturan ese esqueleto sin imponer una jerarquia de clases:
cada servicio las llama desde sus propios metodos (`_get_x`, `update_x`), que
mantienen firma, tipo de retorno y comportamiento observable identicos a
antes. No se extrajo una clase base porque `create_x` y `list_x` varian
demasiado entre modulos (validaciones propias, sub-recursos anidados como
PackingItem/MaintenanceRecord/ProjectTask/Exam) como para forzarlos a un
esqueleto generico sin arriesgar ese comportamiento.
"""
from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


async def get_by_id_or_404(
    db: AsyncSession,
    model: type[ModelT],
    entity_id: str,
    user_id: str,
    *,
    not_found_detail: str = "No encontrado",
) -> ModelT:
    """Busca `model` por id + user_id; 404 si no existe o es de otro usuario."""
    result = await db.execute(
        select(model).where(model.id == entity_id, model.user_id == user_id)
    )
    entity = result.scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return entity


def apply_changes(entity: Any, changes: dict) -> None:
    """Aplica un dict de `exclude_unset=True` sobre `entity`, sin condicion.

    `changes` ya viene filtrado: un campo solo aparece si el cliente lo mando
    de verdad, con cualquier valor — incluido `None` explicito para borrar un
    campo opcional. Filtrar de nuevo por `if value is not None` ignoraria en
    silencio ese borrado.
    """
    columns = getattr(entity, "__table__", None)
    for field, value in changes.items():
        # Un null explicito sobre una columna NOT NULL (p. ej. {"hour": null})
        # no puede borrar nada: iba directo al UPDATE y reventaba con un 500.
        # Se ignora, como un campo omitido.
        column = columns.c.get(field) if columns is not None else None
        if value is None and column is not None and not column.nullable:
            continue
        setattr(entity, field, value)
