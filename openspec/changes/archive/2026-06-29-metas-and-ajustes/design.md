## Context

Los módulos `metas` y `ajustes` ya existen con schemas Pydantic, repositorios y servicios definidos. Sin embargo, las rutas HTML de ambos módulos siguen accediendo directamente a la base de datos mediante `db.execute()` + `select()` en lugar de delegar en `service` + `repository`.

- `metas/routes.py`: ~280 líneas, 7 rutas HTML + 1 endpoint JSON. Toda la lógica de negocio (crear meta, check-in, completar, streak) está inline en las rutas.
- `ajustes/routes.py`: ~366 líneas, 4 rutas HTML + 1 endpoint JSON + Google Calendar OAuth. La helper `get_or_create_prefs` hace DB inline.
- `finanzas/`, `anotaciones/`, `eventos/` ya usan el patrón service + repository correctamente.

Este change refactoriza las rutas HTML de ambos módulos para usar el patrón establecido, y agrega tests unitarios.

## Goals / Non-Goals

**Goals:**
- Refactorizar rutas HTML de `metas` para usar `GoalsService` + `GoalRepository`
- Refactorizar rutas HTML de `ajustes` para usar `SettingsService` + `UserPreferenceRepository`
- Eliminar todo acceso directo a `db.execute()` + `select()` en las rutas
- Escribir tests unitarios para `metas` (CRUD, check-in, completar, progreso, rachas, auth gate)
- Escribir tests unitarios para `ajustes` (obtener/actualizar preferencias, auth gate)
- Corregir type hints `user_id: UUID` → `str` donde sea necesario

**Non-Goals:**
- NO modificar la estructura de las rutas HTML ni sus URLs
- NO modificar la lógica de negocio existente (solo moverla de lugar)
- NO modificar modelos de datos ni migraciones
- NO tocar el frontend
- NO modificar Google OAuth flow en ajustes
- NO agregar nuevas funcionalidades ni endpoints

## Decisions

| # | Decisión | Alternativas | Por qué esta |
|---|----------|-------------|-------------|
| 1 | **Refactor por extracción**: las rutas HTML existentes se mantienen intactas en estructura, solo se reemplaza DB inline por llamadas a service | Reescribir las rutas desde cero | Menor riesgo de romper algo, cambios localizados y verificables |
| 2 | **Mantener `calculate_streak` en routes.py como helper privado** inicialmente, con opción de moverlo al service en el refactor | Mover todo al service de una vez | La función ya es pura y está probada; evita cambios innecesarios en el service existente |
| 3 | **Tests con pytest + httpx.AsyncClient + SQLite in-memory** (mismo patrón que `test_finanzas.py`) | Usar TestClient síncrono | Consistencia con el resto de tests del proyecto |
| 4 | **No tocar el Google OAuth flow** en ajustes (google_connect, google_callback, google_disconnect, google_sync) | Refactorizarlo también | Son rutas complejas con dependencias externas; refactorizarlas sin tests es riesgoso y está fuera del alcance |
| 5 | **Type hints: scan de todos los repositorios** para encontrar `UUID` → `str` | Asumir que están todos correctos | Los modelos ya usan `String(36)` — los repos deben coincidir |

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| Al extraer lógica del route al service, se puede cambiar comportamiento inadvertidamente | Cada ruta refactorizada se verifica manualmente: mismos params, mismo redirect, mismo comportamiento en error |
| El refactor de `registrar_habito` (check-in) es el más riesgoso porque tiene lógica condicional compleja (ya existe vs nuevo record, auto-completar si target alcanzado) | Mantener la lógica condicional idéntica en el service; el route solo llama a `service.checkin_habit()` |
| `get_or_create_prefs` se usa en 4 rutas — reemplazarla por `service.get_preferences()` que ya implementa la misma lógica | Verificar que `SettingsService.get_preferences()` hace create automático si no existe (ya lo hace) |
| Tests pueden fallar si la DB de test no está configurada correctamente | Usar `conftest.py` existente que provee `async_client` + `test_db` con SQLite in-memory |
