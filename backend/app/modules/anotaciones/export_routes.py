import json

from app.core.security import get_user_id_from_request

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.anotaciones.models import Note, Tag

router = APIRouter(prefix="/anotaciones", tags=["anotaciones-export"])


@router.get("/exportar/json")
async def exportar_notas_json(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id_from_request(request)
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .where(Note.user_id == user_id)
        .where(Note.is_archived == False)
        .order_by(Note.updated_at.desc())
    )
    notes = result.scalars().all()

    data = []
    for note in notes:
        note_tags = getattr(note, "tags", []) or []
        data.append(
            {
                "id": note.id,
                "title": note.title,
                "content": note.content,
                "color": note.color,
                "tags": [t.name for t in note_tags],
                "event_date": note.event_date.isoformat() if note.event_date else None,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            }
        )

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    return StreamingResponse(
        iter([json_bytes]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=notas.json"},
    )
