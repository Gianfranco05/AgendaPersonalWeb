"""Catalogo de plantillas de la app.

Es codigo, no datos: que plantillas existen, cuales vienen incluidas y cual es
el Price ID de las que se compran lo decide el backend, no el usuario.

Modelo de negocio: no hay suscripcion. Las plantillas base vienen incluidas y
siempre activas; las demas se compran una vez (pago unico) y quedan en la
cuenta para siempre. Lo que el usuario controla es:
  - comprar una plantilla paga  -> ModulePurchase
  - prenderla o apagarla        -> EnabledModule
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModuleDef:
    key: str
    label: str
    description: str
    icon: str
    #: Incluida en la app: gratis y no se puede desactivar.
    is_base: bool
    #: Nombre del setting que guarda el Price ID de Stripe. Si el setting esta
    #: vacio, la plantilla existe en el catalogo pero todavia no se puede
    #: comprar (se muestra como "proximamente" en vez de romper el checkout).
    price_setting: Optional[str] = None


MODULE_REGISTRY: list[ModuleDef] = [
    # ── Incluidas ────────────────────────────────────────────────────────────
    ModuleDef("habits", "Hábitos", "Seguimiento diario de hábitos", "check_circle", True),
    ModuleDef("tasks", "Tareas", "Tareas y tablero por estado", "task_alt", True),
    ModuleDef("notes", "Notas y Documentos", "Notas rápidas y adjuntos", "description", True),
    ModuleDef("finance", "Finanzas Personales", "Ingresos, gastos y balance", "payments", True),
    ModuleDef("fitness_nutrition", "Rutinas y Dietas", "Entrenamiento y nutrición", "fitness_center", True),
    ModuleDef("calendar", "Calendario y Eventos", "Agenda y eventos", "calendar_today", True),
    # ── De pago (compra unica) ───────────────────────────────────────────────
    ModuleDef(
        "study",
        "Estudio & Universidad",
        "Materias, exámenes y promedio",
        "school",
        False,
        "STRIPE_PRICE_ID_MODULE_STUDY",
    ),
    ModuleDef(
        "library",
        "Biblioteca & Lecturas",
        "Libros leídos y pendientes, con puntaje",
        "menu_book",
        False,
        "STRIPE_PRICE_ID_MODULE_LIBRARY",
    ),
    ModuleDef(
        "media",
        "Películas & Series",
        "Lo que viste y lo que querés ver, con puntaje",
        "movie",
        False,
        "STRIPE_PRICE_ID_MODULE_MEDIA",
    ),
    ModuleDef(
        "work",
        "Trabajo & Carrera",
        "Tareas laborales, reuniones y pipeline",
        "work",
        False,
        "STRIPE_PRICE_ID_MODULE_WORK",
    ),
    ModuleDef(
        "travel",
        "Viajes & Equipaje",
        "Itinerarios, reservas y checklist de equipaje",
        "flight",
        False,
        "STRIPE_PRICE_ID_MODULE_TRAVEL",
    ),
    ModuleDef(
        "vehicle",
        "Vehículo & Mantenimiento",
        "Combustible, revisiones técnicas e ITV",
        "directions_car",
        False,
        "STRIPE_PRICE_ID_MODULE_VEHICLE",
    ),
    ModuleDef(
        "projects",
        "Gestión de Proyectos",
        "Tableros Kanban, sprints y entregables",
        "view_kanban",
        False,
        "STRIPE_PRICE_ID_MODULE_PROJECTS",
    ),
]

MODULE_BY_KEY: dict[str, ModuleDef] = {m.key: m for m in MODULE_REGISTRY}

PAID_MODULES: list[ModuleDef] = [m for m in MODULE_REGISTRY if not m.is_base]
