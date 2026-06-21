import logging

from uuid import uuid4
from datetime import datetime, date
import json

from app.core.security import get_user_id_from_request

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.anotaciones.models import Note, Tag, note_tags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anotaciones", tags=["anotaciones"])


@router.get("/")
async def lista_notas(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(Note.user_id == get_user_id_from_request(request))
        .where(Note.is_archived == False)
        .order_by(Note.is_pinned.desc(), Note.updated_at.desc())
    )
    notes = result.scalars().all()

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return HTMLResponse(content=render_lista(notes, tags))


@router.get("/nueva")
async def nueva_nota(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return HTMLResponse(content=render_form(tags=tags))


@router.post("/nueva")
async def crear_nota(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    content: str = Form(""),
    color: str = Form("#ffffff"),
    event_date: str = Form(""),
    tags: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        event_date_val = None
        if event_date:
            event_date_val = datetime.strptime(event_date, "%Y-%m-%d").date()

        note = Note(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            title=title,
            content=content,
            color=color,
            event_date=event_date_val,
        )
        db.add(note)
        await db.flush()

        if tags:
            tag_ids = [t.strip() for t in tags.split(",") if t.strip()]
            for tag_id in tag_ids:
                tag_result = await db.execute(
                    select(Tag).where(
                        Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request)
                    )
                )
                tag = tag_result.scalar_one_or_none()
                if tag:
                    await db.execute(
                        note_tags.insert().values(note_id=note.id, tag_id=tag.id)
                    )

        await db.commit()
    except Exception:
        logger.exception("Error creating note")
        await db.rollback()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/editar/{note_id}")
async def editar_nota_form(
    request: Request, note_id: str, db: AsyncSession = Depends(get_db)
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(
            Note.id == note_id, Note.user_id == get_user_id_from_request(request)
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/anotaciones/", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return HTMLResponse(content=render_form(note, tags))


@router.post("/editar/{note_id}")
async def editar_nota(
    request: Request,
    note_id: str,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    content: str = Form(""),
    color: str = Form("#ffffff"),
    event_date: str = Form(""),
    tags: str = Form(""),
    action: str = Form("save"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Note)
        .options(selectinload(Note.tags))
        .where(
            Note.id == note_id, Note.user_id == get_user_id_from_request(request)
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        return RedirectResponse(url="/anotaciones/", status_code=303)

    if action == "delete":
        note.is_archived = True
    else:
        note.title = title
        note.content = content
        note.color = color
        if event_date:
            try:
                note.event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
            except ValueError:
                note.event_date = None
        else:
            note.event_date = None

        note.tags.clear()
        if tags:
            tag_ids = [t.strip() for t in tags.split(",") if t.strip()]
            for tag_id in tag_ids:
                tag_result = await db.execute(
                    select(Tag).where(
                        Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request)
                    )
                )
                tag = tag_result.scalar_one_or_none()
                if tag:
                    note.tags.append(tag)

    await db.commit()
    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/etiquetas")
async def etiquetas(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tags_result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = tags_result.scalars().all()

    return HTMLResponse(content=render_etiquetas(tags))


@router.post("/etiquetas")
async def crear_etiqueta(
    request: Request,
    db: AsyncSession = Depends(get_db),
    name: str = Form(...),
    color: str = Form("#6366f1"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    tag = Tag(
        id=str(uuid4()),
        user_id=get_user_id_from_request(request),
        name=name,
        color=color,
    )
    db.add(tag)
    await db.commit()

    return RedirectResponse(url="/anotaciones/etiquetas", status_code=303)


@router.post("/etiquetas/eliminar/{tag_id}")
async def eliminar_etiqueta(
    request: Request,
    tag_id: str,
    db: AsyncSession = Depends(get_db),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == get_user_id_from_request(request))
    )
    tag = result.scalar_one_or_none()
    if tag:
        await db.delete(tag)
        await db.commit()

    return RedirectResponse(url="/anotaciones/etiquetas", status_code=303)


@router.get("/api/tags")
async def api_tags(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Tag).where(Tag.user_id == get_user_id_from_request(request)).order_by(Tag.name)
    )
    tags = result.scalars().all()

    return {"tags": [{"id": t.id, "name": t.name, "color": t.color} for t in tags]}


def render_lista(notes, tags):
    notes_html = ""
    if not notes:
        notes_html = """
        <div class="text-center py-20">
            <div class="w-20 h-20 rounded-2xl bg-[#F1F5F9] flex items-center justify-center mx-auto mb-4">
                <i class="fas fa-sticky-note text-3xl text-[#CBD5E1]"></i>
            </div>
            <p class="text-lg font-medium text-[#64748B]">No hay notas todavía</p>
            <p class="text-sm text-[#94A3B8] mt-1">Crea tu primera nota para comenzar</p>
        </div>
        """
    else:
        notes_html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">'
        for note in notes:
            color_soft = note.color + "20"
            note_tags = getattr(note, "tags", []) or []
            tags_html = ""
            for tag in note_tags:
                tags_html += f'<span class="px-2 py-0.5 rounded text-xs" style="background-color: {tag.color}20; color: {tag.color};">{tag.name}</span>'

            event_date_str = (
                note.event_date.strftime("%d %b") if note.event_date else ""
            )
            content_json = json.dumps(note.content or "")
            empty_placeholder = '<span class=\\"text-[#CBD5E1] italic\\">Sin contenido</span>'

            notes_html += f"""
            <div class="bg-white rounded-2xl overflow-hidden card-shadow card-hover border border-gray-100 group" style="border-top: 4px solid {note.color};">
                <div class="p-5">
                    <div class="flex justify-between items-start mb-3">
                        <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background-color: {color_soft};">
                            <i class="fas fa-sticky-note" style="color: {note.color};"></i>
                        </div>
                        <div class="flex items-center gap-2">
                            <a href="/eventos/nuevo?from_note={note.id}" class="w-8 h-8 rounded-lg flex items-center justify-center bg-[#DBEAFE] text-[#2563EB] hover:bg-[#BFDBFE] transition" title="Crear evento">
                                <i class="fas fa-calendar-plus text-sm"></i>
                            </a>
                            <a href="/anotaciones/editar/{note.id}" class="w-8 h-8 rounded-lg flex items-center justify-center bg-[#F1F5F9] text-[#64748B] hover:bg-[#7C3AED] hover:text-white transition">
                                <i class="fas fa-pen text-sm"></i>
                            </a>
                        </div>
                    </div>
                    <h3 class="font-semibold text-[#1E293B] mb-2 line-clamp-1">{note.title}</h3>
                    <div class="prose text-sm text-[#64748B] line-clamp-2" id="preview-{note.id}"></div>
                    <script>
                    (function() {{
                        var raw = {content_json};
                        var el = document.getElementById('preview-{note.id}');
                        if (raw && raw.trim()) {{
                            el.innerHTML = marked.parse(raw);
                        }} else {{
                            el.innerHTML = '<span class="text-[#CBD5E1] italic">Sin contenido</span>';
                        }}
                    }})();
                    </script>
                    {"<div class='flex flex-wrap gap-1 mt-3'>" + tags_html + "</div>" if tags_html else ""}
                    <div class="flex justify-between items-center mt-4">
                        <p class="text-xs text-[#94A3B8]">{note.updated_at.strftime("%d %b %Y, %H:%M")}</p>
                        {('<span class="text-xs text-[#7C3AED]"><i class="fas fa-calendar mr-1"></i>' + event_date_str + "</span>") if event_date_str else ""}
                    </div>
                </div>
            </div>
            """
        notes_html += "</div>"

    tags_html = ""
    if tags:
        tags_html = '<div class="flex flex-wrap gap-2">'
        for t in tags:
            tags_html += f'<span class="px-3 py-1 rounded-full text-sm" style="background-color: {t.color}20; color: {t.color};">{t.name}</span>'
        tags_html += "</div>"

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anotaciones - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .card-hover {{ transition: all 0.3s ease; }}
        .card-hover:hover {{ transform: translateY(-4px); }}
        .line-clamp-1 {{ display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }}
        .line-clamp-3 {{ display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
        .prose p {{ margin: 0; }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition"><i class="fas fa-cog mr-1"></i>Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-6 py-10">
        <div class="flex justify-between items-center mb-8">
            <div>
                <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-2 inline-flex items-center gap-1">
                    <i class="fas fa-arrow-left"></i>Volver al Dashboard
                </a>
                <h1 class="text-3xl font-bold text-[#1E293B]">Mis Notas</h1>
                <p class="text-[#64748B] mt-1">{len(notes) if notes else 0} nota{"s" if len(notes) != 1 else ""} guardada{"s" if len(notes) != 1 else ""}</p>
            </div>
            <div class="flex gap-3">
                <a href="/anotaciones/etiquetas" class="px-5 py-3 rounded-xl font-medium bg-[#EDE9FE] text-[#7C3AED] hover:bg-[#DDD6FE] transition flex items-center gap-2">
                    <i class="fas fa-tags"></i>Etiquetas
                </a>
                <a href="/anotaciones/nueva" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                    <i class="fas fa-plus"></i>Nueva Nota
                </a>
            </div>
        </div>

        {notes_html}
    </main>
</body>
</html>
"""


def render_form(note=None, tags=None):
    is_edit = note is not None
    title_val = note.title if note else ""
    content_val = note.content if note else ""
    color_val = note.color if note else "#ffffff"
    event_date_val = note.event_date.isoformat() if note and note.event_date else ""

    note_tags = [t.id for t in (getattr(note, "tags", []) or [])] if note else []

    colors = [
        ("#ffffff", "Blanco", "border-gray-300"),
        ("#fef3c7", "Amarillo", "border-yellow-400"),
        ("#dcfce7", "Verde", "border-green-400"),
        ("#dbeafe", "Azul", "border-blue-400"),
        ("#fce7f3", "Rosa", "border-pink-400"),
        ("#ede9fe", "Violeta", "border-purple-400"),
    ]

    color_options = ""
    for c, name, border in colors:
        checked = "ring-2 ring-[#7C3AED] ring-offset-2" if color_val == c else ""
        color_options += f'''
        <label class="cursor-pointer">
            <input type="radio" name="color" value="{c}" {"checked" if color_val == c else ""} class="sr-only peer">
            <div class="w-10 h-10 rounded-xl border-2 {border} {checked} peer-checked:ring-2 peer-checked:ring-[#7C3AED] peer-checked:ring-offset-2 transition-all" style="background-color: {c};"></div>
        </label>
        '''

    tags_options_html = ""
    if tags:
        tags_options_html = '<div class="flex flex-wrap gap-2">'
        for t in tags:
            checked = "ring-2 ring-[#7C3AED]" if t.id in note_tags else ""
            tags_options_html += f'''
            <label class="cursor-pointer">
                <input type="checkbox" name="tag_{t.id}" value="{t.id}" {"checked" if t.id in note_tags else ""} class="sr-only peer" onchange="updateTags()">
                <span class="px-3 py-1.5 rounded-full text-sm border-2 transition-all {checked}" style="border-color: {t.color}40; background-color: {t.color}10; color: {t.color};">{t.name}</span>
            </label>
            '''
        tags_options_html += '</div><input type="hidden" name="tags" id="tagsInput" value="{",".join(note_tags)}">'

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{"Editar Nota" if is_edit else "Nueva Nota"} - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css">
    <script src="https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js"></script>
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .input-focus:focus {{
            border-color: #7C3AED;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }}
        .peer:checked + span {{
            border-color: #7C3AED !important;
            background-color: rgba(124, 58, 237, 0.1) !important;
        }}
        .EasyMDEContainer .CodeMirror {{
            border-radius: 0.75rem;
            border-color: #E5E7EB;
            font-family: 'Inter', sans-serif;
        }}
        .editor-toolbar {{
            border-radius: 0.75rem 0.75rem 0 0;
            border-color: #E5E7EB;
        }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition"><i class="fas fa-cog mr-1"></i>Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-2xl mx-auto px-6 py-10">
        <a href="/finanzas/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver al Dashboard
        </a>

        <div class="bg-white rounded-2xl p-8 card-shadow border border-gray-100">
            <div class="flex items-center gap-3 mb-6">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                    <i class="fas fa-{"pen" if is_edit else "plus"} text-white"></i>
                </div>
                <h1 class="text-2xl font-bold text-[#1E293B]">{
        "Editar Nota" if is_edit else "Nueva Nota"
    }</h1>
            </div>

            <form method="POST" action="{
        "/anotaciones/editar/" + note.id if is_edit else "/anotaciones/nueva"
    }" class="space-y-6" onsubmit="if(typeof easyMDE !== 'undefined'){{ easyMDE.codemirror.save(); }} return true;">
                <input type="hidden" name="action" value="save">

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Título</label>
                    <input type="text" name="title" required value="{title_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Escribe un título...">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Contenido</label>
                    <textarea id="content-editor" name="content">{content_val}</textarea>
                    <script>
                      var easyMDE = new EasyMDE({{
                        element: document.getElementById('content-editor'),
                        spellChecker: false,
                        autosave: {{ enabled: false }},
                        toolbar: ['bold','italic','heading','|','quote','unordered-list','ordered-list','|','link','|','preview','side-by-side','fullscreen'],
                        minHeight: "200px",
                      }});
                    </script>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-3">Color de Nota</label>
                    <div class="flex gap-3">
                        {color_options}
                    </div>
                </div>

                {
        f'''
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-3">Etiquetas</label>
                    {tags_options_html}
                </div>
                '''
        if tags_options_html
        else ""
    }

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Fecha (opcional, para mostrar en calendario)</label>
                    <input type="date" name="event_date" value="{event_date_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    <p class="text-xs text-[#94A3B8] mt-1">Dejá vacío si no querés que aparezca en el calendario</p>
                </div>

                <div class="flex gap-4 pt-4 border-t border-gray-100">
                    <button type="submit" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                        <i class="fas fa-check"></i>Guardar
                    </button>
                    {
        '<button type="submit" name="action" value="delete" class="px-6 py-3 rounded-xl font-medium bg-red-50 text-red-600 hover:bg-red-100 transition flex items-center gap-2">'
        if is_edit
        else ""
    }
                    {'<i class="fas fa-trash"></i>Eliminar' if is_edit else ""}
                    {"</button>" if is_edit else ""}
                    <a href="/finanzas/" class="px-6 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition ml-auto">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </main>

    <script>
    function updateTags() {{
        const checkboxes = document.querySelectorAll('input[type="checkbox"][name^="tag_"]');
        const selected = [];
        checkboxes.forEach(cb => {{
            if (cb.checked) selected.push(cb.value);
        }});
        document.getElementById('tagsInput').value = selected.join(',');
    }}

    document.querySelectorAll('input[type="checkbox"][name^="tag_"]').forEach(cb => {{
        cb.addEventListener('change', updateTags);
    }});
    </script>
</body>
</html>
"""


def render_etiquetas(tags):
    cards = ""
    if not tags:
        cards = """
        <div class="text-center py-12 text-[#94A3B8]">
            <i class="fas fa-tags text-5xl mb-4 opacity-50"></i>
            <p class="text-lg font-medium">No hay etiquetas</p>
            <p class="text-sm">Crea tu primera etiqueta</p>
        </div>
        """
    else:
        for t in tags:
            cards += f"""
            <div class="bg-white rounded-xl p-4 border border-gray-100 flex items-center gap-4">
                <div class="w-10 h-10 rounded-lg flex items-center justify-center" style="background-color: {t.color}20;">
                    <i class="fas fa-tag" style="color: {t.color};"></i>
                </div>
                <span class="font-medium text-[#1E293B] flex-1">{t.name}</span>
                <form action="/anotaciones/etiquetas/eliminar/{t.id}" method="POST" onsubmit="return confirm('¿Eliminar esta etiqueta?');">
                    <button type="submit" class="text-[#94A3B8] hover:text-red-500 transition">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </form>
            </div>
            """

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Etiquetas - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * {{ font-family: 'Inter', sans-serif; }}
        .btn-primary {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            transition: all 0.3s ease;
        }}
        .btn-primary:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(124, 58, 237, 0.4);
        }}
        .input-focus:focus {{
            border-color: #7C3AED;
            box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }}
    </style>
</head>
<body class="bg-[#F8FAFC] min-h-screen">
    <nav class="bg-[#0F172A] text-white sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4">
            <div class="flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#22D3EE] flex items-center justify-center">
                        <i class="fas fa-sparkles"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">Vida Personal</span>
                </div>
                <div class="flex items-center gap-2">
                    <a href="/finanzas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Dashboard</a>
                    <a href="/finanzas/transacciones" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Finanzas</a>
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Calendario</a>
                    <a href="/ajustes/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition"><i class="fas fa-cog mr-1"></i>Ajustes</a>
                    <div class="w-px h-8 bg-white/20 mx-2"></div>
                    <a href="/auth/logout" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">
                        <i class="fas fa-sign-out-alt mr-2"></i>Salir
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-6 py-10">
        <a href="/anotaciones/" class="text-[#64748B] hover:text-[#7C3AED] transition text-sm mb-4 inline-flex items-center gap-1">
            <i class="fas fa-arrow-left"></i>Volver a Notas
        </a>
        <h1 class="text-3xl font-bold text-[#1E293B] mb-8">Etiquetas</h1>

        <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100 mb-8">
            <h2 class="text-lg font-semibold text-[#1E293B] mb-4">Crear Nueva Etiqueta</h2>
            <form method="POST" action="/anotaciones/etiquetas" class="flex gap-4 items-end">
                <div class="flex-1">
                    <label class="block text-sm font-medium text-[#374151] mb-2">Nombre</label>
                    <input type="text" name="name" required
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Nombre de la etiqueta">
                </div>
                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Color</label>
                    <input type="color" name="color" value="#7C3AED"
                        class="h-12 w-20 rounded-xl cursor-pointer border-2 border-gray-200">
                </div>
                <button type="submit" class="btn-primary text-white px-6 py-3 rounded-xl font-medium h-fit">
                    <i class="fas fa-plus mr-2"></i>Crear
                </button>
            </form>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            {cards}
        </div>
    </main>
</body>
</html>
"""
