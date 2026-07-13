## Context

El backend de LifeOS ya cuenta con endpoints REST JSON funcionales bajo `/api/v1/` en `backend/app/api/v1/` para los 5 módulos (finanzas, anotaciones, eventos, metas, ajustes). El soft-delete de transacciones financieras ya está implementado a nivel de modelo (`is_deleted`, `deleted_at`), repositorio y servicio. Sin embargo:

- `GET /api/v1/finance/transactions` retorna una lista plana sin metadatos de paginación (total de registros, página actual)
- Los schemas de algunos endpoints están definidos inline en los routers (`NoteCreateRequest`, `NoteUpdateRequest`, `GoalResponse`, `HabitCheckIn`) en lugar de usar los schemas del módulo
- No existe documentación formal del contrato de API

## Goals / Non-Goals

**Goals:**
- Agregar `PaginatedResponse` wrapper a `GET /api/v1/finance/transactions` con `items`, `total`, `page`, `page_size`
- Migrar schemas inline de notes (`NoteCreateRequest`, `NoteUpdateRequest`) a los schemas del módulo `anotaciones`
- Unificar formato de timestamps ISO 8601 en todas las respuestas
- Documentar el API contract completo en spec formal
- Verificar que `DELETE /api/v1/finance/transactions/{id}` haga soft-delete (ya implementado)

**Non-Goals:**
- NO modificar la estructura de respuesta de endpoints que no sean de listado (summary, categories, tags)
- NO cambiar modelos de datos ni migraciones
- NO tocar rutas HTML existentes
- NO implementar nuevos módulos o capacidades
- NO modificar endpoints de events, goals, settings (ya están correctos)

## Decisions

| # | Decisión | Alternativas | Por qué esta |
|---|----------|-------------|-------------|
| 1 | **`PaginatedResponse` genérico** en `app/api/v1/schemas.py` | Schema inline en cada router | Reutilizable, tipado con generic type, consistente |
| 2 | **Migrar schemas inline de notes** a `NoteCreate`/`NoteUpdate` del módulo `anotaciones.schemas` | Dejarlos inline | Los schemas del módulo ya existen, evita duplicación y drift |
| 3 | **Timestamp ISO 8601** como string en responses | datetime nativo de Pydantic | FastAPI serializa `datetime` a ISO 8601 por defecto — no requiere cambios |
| 4 | **Soft-delete ya implementado** — solo verificar en endpoint DELETE | Reimplementar | El modelo tiene `is_deleted`/`deleted_at`, el repositorio filtra por `is_deleted == False`, el servicio delega correctamente. Solo confirmar que el endpoint lo use. |
| 5 | **Sin cambios en events, goals, settings** | Unificar todos los módulos | Ya cumplen con el contrato esperado: schemas correctos, timestamps ISO, filtros por query params |

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| `PaginatedResponse` cambia el contrato del endpoint — frontend existente podría romperse | El frontend actual no consume estos endpoints (aún es HTML). Cambiar antes de que haya consumo real. |
| `list[TransactionResponse]` → `PaginatedResponse[TransactionResponse]` rompe tipado en frontend | Es el momento correcto — no hay frontend React conectado aún. |
| Migrar schemas inline puede requerir ajustar campos faltantes en `NoteCreate`/`NoteUpdate` del módulo | Verificar que los schemas del módulo cubran todos los campos que usan los endpoints inline. |

## Open Questions

- Ninguna — el alcance está bien definido y el código actual es conocido.
