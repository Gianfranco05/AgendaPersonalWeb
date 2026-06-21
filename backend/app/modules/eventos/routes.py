import logging

from datetime import datetime, date, timedelta, timezone
from uuid import uuid4
import json

from app.core.security import get_user_id_from_request

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.eventos.models import Event
from app.modules.anotaciones.models import Note

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.get("/")
async def calendario(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(Event.user_id == get_user_id_from_request(request))
    )
    events = result.scalars().all()

    notes_result = await db.execute(
        select(Note).where(
            Note.user_id == get_user_id_from_request(request),
            Note.is_archived == False,
            Note.event_date != None,
        )
    )
    notes = notes_result.scalars().all()

    events_list = []
    for e in events:
        events_list.append(
            {
                "id": e.id,
                "title": e.title,
                "start": e.start_datetime.isoformat() if e.start_datetime else None,
                "end": e.end_datetime.isoformat() if e.end_datetime else None,
                "color": e.color,
                "allDay": e.is_all_day,
                "description": e.description,
                "location": e.location,
                "type": "event",
            }
        )

    for n in notes:
        events_list.append(
            {
                "id": f"note_{n.id}",
                "title": f"📝 {n.title}",
                "start": n.event_date.isoformat() if n.event_date else None,
                "color": n.color,
                "allDay": True,
                "description": n.content,
                "type": "note",
                "note_id": n.id,
            }
        )

    today = date.today().isoformat()
    return HTMLResponse(content=render_calendario(events_list, today))


@router.get("/nuevo")
async def nuevo_evento(request: Request, db: AsyncSession = Depends(get_db)):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    note_id = request.query_params.get("from_note")
    note = None
    if note_id:
        result = await db.execute(
            select(Note).where(
                Note.id == note_id, Note.user_id == get_user_id_from_request(request)
            )
        )
        note = result.scalar_one_or_none()

    return HTMLResponse(content=render_form(note))


@router.post("/nuevo")
async def crear_evento(
    request: Request,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(...),
    start_time: str = Form("09:00"),
    is_all_day: str = Form("false"),
    color: str = Form("#3b82f6"),
    location: str = Form(""),
    from_note_id: str = Form(""),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    try:
        start_dt = datetime.strptime(
            f"{start_date} {start_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=timezone.utc)

        event = Event(
            id=str(uuid4()),
            user_id=get_user_id_from_request(request),
            title=title,
            description=description or None,
            start_datetime=start_dt,
            is_all_day=is_all_day.lower() == "true",
            color=color,
            location=location or None,
        )
        db.add(event)

        if from_note_id:
            note_result = await db.execute(
                select(Note).where(
                    Note.id == from_note_id, Note.user_id == get_user_id_from_request(request)
                )
            )
            note = note_result.scalar_one_or_none()
            if note:
                note.event_date = None

        await db.commit()
    except Exception as e:
        logger.exception("Error creating event")
        await db.rollback()

    return RedirectResponse(url="/finanzas/", status_code=303)


@router.get("/editar/{event_id}")
async def editar_evento_form(
    request: Request, event_id: str, db: AsyncSession = Depends(get_db)
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.user_id == get_user_id_from_request(request)
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        return RedirectResponse(url="/finanzas/", status_code=303)

    return HTMLResponse(content=render_form(event))


@router.post("/editar/{event_id}")
async def editar_evento(
    request: Request,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(...),
    start_time: str = Form("09:00"),
    is_all_day: str = Form("false"),
    color: str = Form("#3b82f6"),
    location: str = Form(""),
    action: str = Form("save"),
):
    if not get_user_id_from_request(request):
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.user_id == get_user_id_from_request(request)
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        return RedirectResponse(url="/finanzas/", status_code=303)

    if action == "delete":
        await db.delete(event)
    else:
        event.title = title
        event.description = description or None
        event.start_datetime = datetime.strptime(
            f"{start_date} {start_time}", "%Y-%m-%d %H:%M"
        )
        event.is_all_day = is_all_day.lower() == "true"
        event.color = color
        event.location = location or None

    await db.commit()
    return RedirectResponse(url="/finanzas/", status_code=303)


def render_calendario(events_list, today):
    events_json = json.dumps(events_list)

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calendario - Vida Personal</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.css' rel='stylesheet' />
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.10/index.global.min.js'></script>
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
        .fc {{
            font-family: 'Inter', sans-serif;
        }}
        .fc .fc-button {{
            background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: 500;
        }}
        .fc .fc-button:hover {{
            background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        }}
        .fc .fc-button-primary:not(:disabled).fc-button-active {{
            background: #0F172A;
        }}
        .fc .fc-toolbar-title {{
            font-size: 1.5rem;
            font-weight: 600;
            color: #1E293B;
        }}
        .fc .fc-daygrid-day-number {{
            color: #64748B;
            font-weight: 500;
        }}
        .fc .fc-daygrid-day.fc-day-today {{
            background: rgba(124, 58, 237, 0.1);
        }}
        .fc .fc-event {{
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 0.85rem;
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
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
                <h1 class="text-3xl font-bold text-[#1E293B]">Calendario</h1>
                <p class="text-[#64748B] mt-1">{len(events_list)} elemento{"s" if len(events_list) != 1 else ""}</p>
            </div>
            <a href="/eventos/nuevo" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                <i class="fas fa-plus"></i>Nuevo Evento
            </a>
        </div>

        <div class="bg-white rounded-2xl p-6 card-shadow border border-gray-100">
            <div id='calendar'></div>
        </div>
    </main>

    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        var calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {{
            initialView: 'dayGridMonth',
            initialDate: '{today}',
            headerToolbar: {{
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            }},
            events: {events_json},
            locale: 'es',
            buttonText: {{ today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Día' }},
            monthNames: ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'],
            monthNamesShort: ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'],
            dayNames: ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'],
            dayNamesShort: ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'],
            eventClick: function(info) {{
                var eventId = info.event.id;
                if (eventId.startsWith('note_')) {{
                    var noteId = eventId.replace('note_', '');
                    var noteData = info.event.extendedProps;
                    document.getElementById('noteModalTitle').textContent = info.event.title.replace('📝 ', '');
                    document.getElementById('noteModalContent').textContent = noteData.description || 'Sin contenido';
                    document.getElementById('noteModalLink').href = '/anotaciones/editar/' + noteId;
                    document.getElementById('noteModal').classList.remove('hidden');
                }} else {{
                    if (confirm('¿Editar este evento?')) {{
                        window.location.href = '/eventos/editar/' + eventId;
                    }}
                }}
            }},
            eventDidMount: function(info) {{
                info.el.style.borderLeft = '3px solid ' + info.event.backgroundColor;
            }}
        }});
        calendar.render();
    }});

    function closeModal() {{
        document.getElementById('noteModal').classList.add('hidden');
    }}
    </script>

    <div id="noteModal" class="hidden fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
        <div class="bg-white rounded-2xl p-8 max-w-lg w-full mx-4 shadow-2xl">
            <div class="flex justify-between items-start mb-4">
                <h2 id="noteModalTitle" class="text-xl font-bold text-[#1E293B]"></h2>
                <button onclick="closeModal()" class="w-8 h-8 rounded-lg flex items-center justify-center bg-gray-100 text-gray-500 hover:bg-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <p id="noteModalContent" class="text-[#64748B] whitespace-pre-wrap mb-6"></p>
            <div class="flex gap-4 pt-4 border-t border-gray-100">
                <a id="noteModalLink" href="#" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                    <i class="fas fa-pen"></i>Editar Nota
                </a>
                <button onclick="closeModal()" class="px-6 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition">
                    Cerrar
                </button>
            </div>
        </div>
    </div>
</body>
</html>
"""


def render_form(event=None, note=None):
    is_edit = event is not None
    title_val = event.title if event else (note.title if note else "")
    desc_val = event.description if event else (note.content if note else "")
    loc_val = event.location if event else ""
    color_val = event.color if event else "#7C3AED"

    if note and note.event_date:
        start_date_val = note.event_date.strftime("%Y-%m-%d")
    elif event and event.start_datetime:
        start_date_val = event.start_datetime.strftime("%Y-%m-%d")
    else:
        start_date_val = date.today().isoformat()

    if event and event.start_datetime:
        start_time_val = event.start_datetime.strftime("%H:%M")
    else:
        start_time_val = "09:00"

    colors = [
        ("#7C3AED", "Violeta"),
        ("#3B82F6", "Azul"),
        ("#10B981", "Verde"),
        ("#F59E0B", "Amarillo"),
        ("#EF4444", "Rojo"),
        ("#EC4899", "Rosa"),
    ]

    color_options = ""
    for c, name in colors:
        checked = "ring-2 ring-offset-2 ring-[#7C3AED]" if color_val == c else ""
        color_options += f'''
        <label class="cursor-pointer" title="{name}">
            <input type="radio" name="color" value="{c}" {"checked" if color_val == c else ""} class="sr-only peer">
            <div class="w-10 h-10 rounded-xl {checked} transition-all" style="background-color: {c};"></div>
        </label>
        '''

    note_id_input = (
        f'<input type="hidden" name="from_note_id" value="{note.id}">' if note else ""
    )

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{"Editar Evento" if is_edit else "Nuevo Evento"} - Vida Personal</title>
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
                    <a href="/anotaciones/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Notas</a>
                    <a href="/eventos/" class="px-5 py-2.5 rounded-xl bg-[#7C3AED] text-sm font-medium">Calendario</a>
                    <a href="/metas/" class="px-5 py-2.5 rounded-xl hover:bg-white/10 text-sm font-medium transition">Metas</a>
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
                    <i class="fas fa-calendar-plus text-white"></i>
                </div>
                <h1 class="text-2xl font-bold text-[#1E293B]">{"Editar Evento" if is_edit else "Nuevo Evento"}</h1>
            </div>

            {f'<div class="mb-4 p-3 rounded-xl bg-[#DBEAFE] border border-[#3B82F6]/30 text-sm text-[#1E40AF]"><i class="fas fa-info-circle mr-2"></i>Creando evento desde una nota con fecha</div>' if note else ""}

            <form method="POST" action="{"/eventos/editar/" + event.id if is_edit else "/eventos/nuevo"}" class="space-y-6" onsubmit="return confirm('¿Estás seguro de guardar este evento?');">
                {note_id_input}
                <input type="hidden" name="action" value="save">

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Título del Evento</label>
                    <input type="text" name="title" required value="{title_val}"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                        placeholder="Nombre del evento">
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Descripción</label>
                    <textarea name="description" rows="3"
                        class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none resize-none"
                        placeholder="Agrega una descripción...">{desc_val}</textarea>
                </div>

                <div class="grid grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Fecha</label>
                        <input type="date" name="start_date" required value="{start_date_val}"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-[#374151] mb-2">Hora</label>
                        <input type="time" name="start_time" value="{start_time_val}"
                            class="w-full px-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-2">Ubicación</label>
                    <div class="relative">
                        <i class="fas fa-map-marker-alt absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]"></i>
                        <input type="text" name="location" value="{loc_val}"
                            class="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 input-focus transition outline-none"
                            placeholder="Lugar del evento">
                    </div>
                </div>

                <div>
                    <label class="block text-sm font-medium text-[#374151] mb-3">Color del Evento</label>
                    <div class="flex gap-3">
                        {color_options}
                    </div>
                </div>

                <div class="flex gap-4 pt-4 border-t border-gray-100">
                    <button type="submit" class="btn-primary text-white px-6 py-3 rounded-xl font-medium flex items-center gap-2">
                        <i class="fas fa-check"></i>Guardar
                    </button>
                    {'<button type="submit" name="action" value="delete" class="px-6 py-3 rounded-xl font-medium bg-red-50 text-red-600 hover:bg-red-100 transition flex items-center gap-2">' if is_edit else ""}
                    {'<i class="fas fa-trash"></i>Eliminar' if is_edit else ""}
                    {"</button>" if is_edit else ""}
                    <a href="/finanzas/" class="px-6 py-3 rounded-xl font-medium bg-gray-100 text-[#64748B] hover:bg-gray-200 transition ml-auto">
                        Cancelar
                    </a>
                </div>
            </form>
        </div>
    </main>
</body>
</html>
"""
