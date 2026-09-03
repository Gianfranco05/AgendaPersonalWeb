"""Catalogo de modulos/plantillas de la app.

Es codigo, no datos: que modulos existen y cuales son "base" (siempre
activos, no se pueden apagar) lo decide el backend, no el usuario. Lo unico
que el usuario controla es el on/off de los modulos no-base, persistido en
`EnabledModule`.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleDef:
    key: str
    label: str
    description: str
    icon: str
    is_base: bool


MODULE_REGISTRY: list[ModuleDef] = [
    # Base: ya construidos, siempre visibles, no se pueden desactivar.
    ModuleDef("habits", "Hábitos", "Seguimiento diario de hábitos", "check_circle", True),
    ModuleDef("notes", "Notas y Documentos", "Notas rápidas y adjuntos", "description", True),
    ModuleDef("finance", "Finanzas Personales", "Ingresos, gastos y balance", "payments", True),
    ModuleDef("fitness_nutrition", "Rutinas y Dietas", "Entrenamiento y nutrición", "fitness_center", True),
    ModuleDef("calendar", "Calendario y Eventos", "Agenda y eventos", "calendar_today", True),
    # Nuevos: togglables, sin funcionalidad propia todavia (pantalla "Próximamente").
    ModuleDef("study", "Estudio & Universidad", "Materias, exámenes y promedio", "school", False),
    ModuleDef("work", "Trabajo & Carrera", "Tareas laborales, reuniones y pipeline", "work", False),
    ModuleDef("vehicle", "Vehículo & Mantenimiento", "Combustible, revisiones técnicas e ITV", "directions_car", False),
    ModuleDef("projects", "Gestión de Proyectos", "Tableros Kanban, sprints y entregables", "view_kanban", False),
]

MODULE_BY_KEY: dict[str, ModuleDef] = {m.key: m for m in MODULE_REGISTRY}
