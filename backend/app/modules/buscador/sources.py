"""Registro declarativo de las entidades buscables.

Agregar un tipo nuevo es sumar una entrada a `SEARCH_SOURCES`; el servicio no
cambia. Cada fuente declara sus columnas (titulo y contenido), los filtros fijos
(`is_deleted = false`, `goal_type IN (...)`), la fecha de orden y como armar el
item de respuesta a partir de la fila.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Awaitable, Callable, Optional, Sequence
from urllib.parse import quote

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.anotaciones.models import Note, Tag, note_tags
from app.modules.biblioteca.models import Book
from app.modules.estudio.models import Exam, Subject
from app.modules.eventos.models import Event
from app.modules.eventos.schemas import to_wall_clock
from app.modules.finanzas.models import Transaction
from app.modules.inversiones.models import Investment
from app.modules.metas.models import Goal
from app.modules.peliculas.models import MediaItem
from app.modules.proyectos.models import Project, ProjectTask
from app.modules.tareas.models import Task
from app.modules.trabajo.models import WorkOpportunity
from app.modules.vehiculo.models import MaintenanceRecord, Vehicle
from app.modules.viajes.models import PackingItem, Trip

#: Datos que `enrich` carga en lote para las filas de una fuente (etiquetas de
#: las notas, nombre del vehiculo de un mantenimiento).
Context = dict[str, Any]
EnrichFn = Callable[[AsyncSession, str, Sequence[Any]], Awaitable[Context]]
#: Condicion extra por token (p. ej. el nombre de una etiqueta de la nota).
TokenMatchFn = Callable[[str, str], ColumnElement]


@dataclass(frozen=True)
class ItemData:
    """Lo que cada fuente aporta a un item; el servicio agrega snippet y resaltados."""

    title: str
    date: Optional[str]
    parent_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class SearchSource:
    type: str
    entity: str
    module_key: str
    model: Any
    title_col: Any
    content_cols: tuple = ()
    extra_where: tuple = ()
    #: Expresion SQL para ordenar por fecha (mas reciente primero).
    date_expr: Any = None
    parent_col: Any = None
    to_item: Callable[[Any, Context], ItemData] = None  # type: ignore[assignment]
    #: Ruta web de destino. Recibe el item (id, parent_id).
    path_base: str = ""
    path_extra: str = ""
    token_match: Optional[TokenMatchFn] = None
    enrich: Optional[EnrichFn] = None
    #: Columnas que se muestran como snippet, en orden de prioridad (por
    #: defecto `content_cols`).
    snippet_cols: Optional[tuple] = None

    def path_for(self, item_id: str, parent_id: Optional[str]) -> str:
        sep = "&" if "?" in self.path_base else "?"
        path = f"{self.path_base}{sep}open={quote(str(item_id), safe='')}{self.path_extra}"
        if self.parent_col is not None and parent_id:
            path += f"&parent={quote(str(parent_id), safe='')}"
        return path


# ── Helpers de fechas ────────────────────────────────────────────────────────


def iso_date(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def iso_utc(value: Optional[datetime]) -> Optional[str]:
    """Timestamp -> ISO 8601 en UTC con `Z` (un valor naive se toma como UTC)."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def first(*values: Optional[str]) -> Optional[str]:
    for v in values:
        if v:
            return v
    return None


def _money(value) -> Optional[str]:
    return f"{value:.2f}" if value is not None else None


# ── Notas: etiquetas ─────────────────────────────────────────────────────────


def _note_tag_match(pattern: str, user_id: str) -> ColumnElement:
    """El token aparece en el nombre de alguna etiqueta de la nota.

    Filtra `tags.user_id`: aunque `note_tags` ya enlaza ids propios, no se
    confia en el enlace para no filtrar etiquetas de otra cuenta.
    """
    from app.modules.buscador.normalize import LIKE_ESCAPE, fold

    return exists().where(
        note_tags.c.note_id == Note.id,
        note_tags.c.tag_id == Tag.id,
        Tag.user_id == user_id,
        fold(Tag.name).like(pattern, escape=LIKE_ESCAPE),
    )


async def _enrich_notes(db: AsyncSession, user_id: str, rows: Sequence[Note]) -> Context:
    ids = [n.id for n in rows]
    tags: dict[str, list[str]] = {i: [] for i in ids}
    if ids:
        result = await db.execute(
            select(note_tags.c.note_id, Tag.name)
            .join(Tag, Tag.id == note_tags.c.tag_id)
            .where(note_tags.c.note_id.in_(ids), Tag.user_id == user_id)
            .order_by(Tag.name)
        )
        for note_id, name in result.all():
            tags[note_id].append(name)
    return {"tags": tags}


async def _enrich_maintenance(
    db: AsyncSession, user_id: str, rows: Sequence[MaintenanceRecord]
) -> Context:
    ids = {r.vehicle_id for r in rows}
    names: dict[str, str] = {}
    if ids:
        result = await db.execute(
            select(Vehicle.id, Vehicle.name).where(Vehicle.user_id == user_id, Vehicle.id.in_(ids))
        )
        names = {vid: name for vid, name in result.all()}
    return {"vehicles": names}


# ── to_item por fuente ───────────────────────────────────────────────────────


def _note_item(n: Note, ctx: Context) -> ItemData:
    return ItemData(
        title=n.title,
        date=iso_utc(n.updated_at or n.created_at),
        meta={"tags": ctx["tags"].get(n.id, []), "archived": bool(n.is_archived)},
    )


def _task_item(t: Task, ctx: Context) -> ItemData:
    return ItemData(
        title=t.title,
        date=first(iso_date(t.due_date), iso_utc(t.updated_at or t.created_at)),
        meta={"status": t.status},
    )


def _event_item(e: Event, ctx: Context) -> ItemData:
    # Hora de pared sin zona, igual que la API de eventos: con "Z" el cliente
    # la correria 3 horas.
    return ItemData(
        title=e.title,
        date=to_wall_clock(e.start_datetime).isoformat(timespec="seconds"),
        meta={"is_all_day": bool(e.is_all_day)},
    )


def _transaction_item(t: Transaction, ctx: Context) -> ItemData:
    return ItemData(
        title=t.product_name,
        date=str(t.transaction_date) if t.transaction_date else None,
        meta={"amount": _money(t.amount), "currency": t.currency, "type": t.type},
    )


def _habit_item(g: Goal, ctx: Context) -> ItemData:
    return ItemData(
        title=g.title,
        date=iso_utc(g.updated_at or g.created_at),
        meta={"goal_type": g.goal_type},
    )


def _goal_item(g: Goal, ctx: Context) -> ItemData:
    return ItemData(
        title=g.title,
        date=first(iso_date(g.end_date), iso_utc(g.updated_at or g.created_at)),
        meta={"goal_type": g.goal_type, "is_completed": bool(g.is_completed)},
    )


def _investment_item(i: Investment, ctx: Context) -> ItemData:
    return ItemData(
        title=i.name,
        date=first(iso_date(i.maturity_date), iso_utc(i.updated_at or i.created_at)),
        meta={"asset_type": i.asset_type, "currency": i.currency, "status": i.status},
    )


def _subject_item(s: Subject, ctx: Context) -> ItemData:
    return ItemData(title=s.name, date=iso_utc(s.updated_at or s.created_at), meta={"status": s.status})


def _exam_item(e: Exam, ctx: Context) -> ItemData:
    return ItemData(title=e.title, date=iso_date(e.exam_date), parent_id=e.subject_id, meta=None)


def _book_item(b: Book, ctx: Context) -> ItemData:
    return ItemData(
        title=b.title,
        date=first(iso_date(b.finished_date), iso_date(b.started_date), iso_utc(b.updated_at or b.created_at)),
        meta={"status": b.status},
    )


def _media_item(m: MediaItem, ctx: Context) -> ItemData:
    return ItemData(
        title=m.title,
        date=iso_utc(m.updated_at or m.created_at),
        meta={"status": m.status, "media_type": m.media_type},
    )


def _work_item(w: WorkOpportunity, ctx: Context) -> ItemData:
    return ItemData(
        title=f"{w.role} · {w.company}",
        date=first(iso_date(w.applied_date), iso_utc(w.updated_at or w.created_at)),
        meta={"status": w.status},
    )


def _trip_item(t: Trip, ctx: Context) -> ItemData:
    return ItemData(
        title=t.destination,
        date=first(iso_date(t.start_date), iso_utc(t.updated_at or t.created_at)),
        meta={"status": t.status},
    )


def _packing_item(p: PackingItem, ctx: Context) -> ItemData:
    return ItemData(
        title=p.name, date=iso_utc(p.created_at), parent_id=p.trip_id, meta={"packed": bool(p.packed)}
    )


def _vehicle_item(v: Vehicle, ctx: Context) -> ItemData:
    return ItemData(title=v.name, date=iso_utc(v.updated_at or v.created_at))


def _maintenance_item(m: MaintenanceRecord, ctx: Context) -> ItemData:
    vehicle = ctx["vehicles"].get(m.vehicle_id)
    label = m.record_type.capitalize() if m.record_type else "Registro"
    return ItemData(
        title=f"{label} · {vehicle}" if vehicle else label,
        date=iso_date(m.record_date),
        parent_id=m.vehicle_id,
        meta={"record_type": m.record_type},
    )


def _project_item(p: Project, ctx: Context) -> ItemData:
    return ItemData(title=p.name, date=iso_utc(p.updated_at or p.created_at), meta={"status": p.status})


def _project_task_item(t: ProjectTask, ctx: Context) -> ItemData:
    return ItemData(
        title=t.title,
        date=first(iso_date(t.due_date), iso_utc(t.updated_at or t.created_at)),
        parent_id=t.project_id,
        meta={"status": t.status},
    )


# ── Registro ─────────────────────────────────────────────────────────────────

#: Orden fijo de los grupos de la respuesta: primero las base y despues las
#: plantillas en el orden de `MODULE_REGISTRY`.
TYPE_ORDER: tuple[str, ...] = (
    "notes",
    "tasks",
    "events",
    "transactions",
    "habits",
    "goals",
    "investments",
    "study",
    "library",
    "media",
    "work",
    "travel",
    "vehicle",
    "projects",
)

TYPE_LABELS: dict[str, str] = {
    "notes": "Notas",
    "tasks": "Tareas",
    "events": "Eventos",
    "transactions": "Movimientos",
    "habits": "Hábitos",
    "goals": "Metas",
    "investments": "Inversiones",
    "study": "Estudio",
    "library": "Biblioteca",
    "media": "Películas y series",
    "work": "Trabajo",
    "travel": "Viajes",
    "vehicle": "Vehículo",
    "projects": "Proyectos",
}


def _src(type_: str, entity: str, module_key: str, model, title_col, **kw) -> SearchSource:
    return SearchSource(type=type_, entity=entity, module_key=module_key, model=model, title_col=title_col, **kw)


SEARCH_SOURCES: list[SearchSource] = [
    _src(
        "notes", "note", "notes", Note, Note.title,
        content_cols=(Note.content,),
        date_expr=func.coalesce(Note.updated_at, Note.created_at),
        to_item=_note_item, path_base="/notes",
        token_match=_note_tag_match, enrich=_enrich_notes,
    ),
    _src(
        "tasks", "task", "tasks", Task, Task.title,
        content_cols=(Task.description, Task.area),
        date_expr=func.coalesce(Task.due_date, Task.updated_at, Task.created_at),
        to_item=_task_item, path_base="/tasks",
    ),
    _src(
        "events", "event", "calendar", Event, Event.title,
        content_cols=(Event.description, Event.location),
        date_expr=Event.start_datetime,
        to_item=_event_item, path_base="/events",
    ),
    _src(
        "transactions", "transaction", "finance", Transaction, Transaction.product_name,
        content_cols=(Transaction.merchant_name, Transaction.product_description, Transaction.notes),
        extra_where=(Transaction.is_deleted.is_(False),),
        date_expr=Transaction.transaction_date,
        to_item=_transaction_item, path_base="/finances?tab=transacciones",
    ),
    _src(
        "habits", "habit", "habits", Goal, Goal.title,
        content_cols=(Goal.description,),
        extra_where=(Goal.goal_type.in_(("binary", "metric")),),
        date_expr=func.coalesce(Goal.updated_at, Goal.created_at),
        to_item=_habit_item, path_base="/habits",
    ),
    _src(
        "goals", "goal", "habits", Goal, Goal.title,
        content_cols=(Goal.description,),
        extra_where=(Goal.goal_type.in_(("progress", "savings")),),
        date_expr=func.coalesce(Goal.end_date, Goal.updated_at, Goal.created_at),
        to_item=_goal_item, path_base="/goals",
    ),
    _src(
        "investments", "investment", "finance", Investment, Investment.name,
        content_cols=(Investment.ticker, Investment.institution, Investment.notes),
        date_expr=func.coalesce(Investment.maturity_date, Investment.updated_at, Investment.created_at),
        to_item=_investment_item, path_base="/finances?tab=inversiones",
    ),
    _src(
        "study", "subject", "study", Subject, Subject.name,
        content_cols=(Subject.professor,),
        date_expr=func.coalesce(Subject.updated_at, Subject.created_at),
        to_item=_subject_item, path_base="/study", path_extra="&entity=subject",
    ),
    _src(
        "study", "exam", "study", Exam, Exam.title,
        content_cols=(Exam.notes,), parent_col=Exam.subject_id,
        date_expr=Exam.exam_date,
        to_item=_exam_item, path_base="/study", path_extra="&entity=exam",
    ),
    _src(
        "library", "book", "library", Book, Book.title,
        content_cols=(Book.author, Book.notes),
        date_expr=func.coalesce(Book.finished_date, Book.started_date, Book.updated_at, Book.created_at),
        to_item=_book_item, path_base="/library", path_extra="&entity=book",
    ),
    _src(
        "media", "media_item", "media", MediaItem, MediaItem.title,
        content_cols=(MediaItem.notes,),
        date_expr=func.coalesce(MediaItem.updated_at, MediaItem.created_at),
        to_item=_media_item, path_base="/media", path_extra="&entity=media_item",
    ),
    _src(
        "work", "opportunity", "work", WorkOpportunity, WorkOpportunity.role,
        content_cols=(WorkOpportunity.company, WorkOpportunity.notes),
        date_expr=func.coalesce(WorkOpportunity.applied_date, WorkOpportunity.updated_at, WorkOpportunity.created_at),
        to_item=_work_item, path_base="/work", path_extra="&entity=opportunity",
    ),
    _src(
        "travel", "trip", "travel", Trip, Trip.destination,
        content_cols=(Trip.notes,),
        date_expr=func.coalesce(Trip.start_date, Trip.updated_at, Trip.created_at),
        to_item=_trip_item, path_base="/travel", path_extra="&entity=trip",
    ),
    _src(
        "travel", "packing_item", "travel", PackingItem, PackingItem.name,
        parent_col=PackingItem.trip_id,
        date_expr=PackingItem.created_at,
        to_item=_packing_item, path_base="/travel", path_extra="&entity=packing_item",
    ),
    _src(
        "vehicle", "vehicle", "vehicle", Vehicle, Vehicle.name,
        content_cols=(Vehicle.brand, Vehicle.model, Vehicle.plate),
        date_expr=func.coalesce(Vehicle.updated_at, Vehicle.created_at),
        to_item=_vehicle_item, path_base="/vehicle", path_extra="&entity=vehicle",
    ),
    _src(
        "vehicle", "maintenance", "vehicle", MaintenanceRecord, MaintenanceRecord.notes,
        snippet_cols=(MaintenanceRecord.notes,), parent_col=MaintenanceRecord.vehicle_id,
        date_expr=MaintenanceRecord.record_date,
        to_item=_maintenance_item, path_base="/vehicle", path_extra="&entity=maintenance",
        enrich=_enrich_maintenance,
    ),
    _src(
        "projects", "project", "projects", Project, Project.name,
        content_cols=(Project.description,),
        date_expr=func.coalesce(Project.updated_at, Project.created_at),
        to_item=_project_item, path_base="/projects", path_extra="&entity=project",
    ),
    _src(
        "projects", "project_task", "projects", ProjectTask, ProjectTask.title,
        content_cols=(ProjectTask.notes,), parent_col=ProjectTask.project_id,
        date_expr=func.coalesce(ProjectTask.due_date, ProjectTask.updated_at, ProjectTask.created_at),
        to_item=_project_task_item, path_base="/projects", path_extra="&entity=project_task",
    ),
]
