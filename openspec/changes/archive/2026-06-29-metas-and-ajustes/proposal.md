## Why

Los módulos `metas` y `ajustes` ya tienen schemas, repositorios y servicios definidos, pero las rutas HTML (`/metas/`, `/ajustes/`) siguen accediendo a la base de datos inline en lugar de delegar en service + repository. Esto duplica lógica de negocio, dificulta el testing, y rompe con el patrón que siguen `finanzas`, `anotaciones` y `eventos`. Además, no existen tests unitarios para estos módulos, y algunos type hints aún usan `UUID` en lugar de `str`.

## What Changes

- **Metas**: Refactorizar las rutas HTML (`lista_metas`, `nueva_meta`, `crear_meta`, `editar_meta_form`, `editar_meta`, `registrar_habito`, `completar_meta`) para usar `GoalsService` + `GoalRepository` en lugar de acceso directo a `db.execute()` + `select()`
- **Ajustes**: Refactorizar las rutas HTML (`ajustes_page`, `save_ajustes`) y la helper `get_or_create_prefs` para usar `SettingsService` + `UserPreferenceRepository`
- **Tests**: Crear `tests/test_metas.py` y `tests/test_ajustes.py` con cobertura de CRUD, check-in, completar, progreso, rachas, y auth gate
- **Type hints**: Verificar y corregir cualquier `user_id: UUID` → `str` en repositorios existentes para coincidir con `String(36)` en los modelos
- **No breaking**: No se modifican rutas HTML existentes ni endpoints JSON — todo sigue funcionando igual

## Capabilities

### New Capabilities
- `metas-module`: Gestión de metas con seguimiento de hábitos, rachas, progreso porcentual y check-in diario
- `ajustes-module`: Preferencias de usuario (moneda, tema visual, formato de fecha)

### Modified Capabilities
<!-- No existing specs are modified — these are new modules -->

## Impact

- `backend/app/modules/metas/routes.py` — refactor para usar service + repository
- `backend/app/modules/ajustes/routes.py` — refactor para usar service + repository
- `backend/tests/test_metas.py` — nuevo archivo
- `backend/tests/test_ajustes.py` — nuevo archivo
- Posibles correcciones menores en type hints de otros repositorios
- Ningún cambio en modelos de datos, migraciones, o endpoints existentes
