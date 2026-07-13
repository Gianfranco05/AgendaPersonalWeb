## 1. Type hints — user_id UUID → str

- [x] 1.1 Scannear todos los repositorios en `backend/app/modules/` buscando `user_id: UUID` → corregir a `user_id: str`
- [x] 1.2 Verificar que ningún schema Pydantic use `UUID` para `user_id`

## 2. Metas — Refactor routes → service + repository

- [x] 2.1 Refactor `lista_meta` (GET /metas/) para usar `GoalsService.list_active_goals()` y `list_completed_goals()`
- [x] 2.2 Refactor `nueva_meta` (GET /metas/nueva) — sin cambios (solo render), verificar que funcione
- [x] 2.3 Refactor `crear_meta` (POST /metas/nueva) para usar `GoalsService.create_goal()`
- [x] 2.4 Refactor `editar_meta_form` (GET /metas/editar/{goal_id}) para usar `GoalsService.get_goal()`
- [x] 2.5 Refactor `editar_meta` (POST /metas/editar/{goal_id}) para usar `GoalsService.update_goal()` y `GoalsService.delete_goal()`
- [x] 2.6 Refactor `registrar_habito` (POST /metas/registrar/{goal_id}) para usar `GoalsService.checkin_habit()`
- [x] 2.7 Refactor `completar_meta` (POST /metas/completar/{goal_id}) para usar `GoalsService.complete_goal()`
- [x] 2.8 Eliminar imports de SQLAlchemy directos (`select`, `delete`, `func`) de routes.py que ya no se usen
- [x] 2.9 Verificar que `GET /metas/api/goals` ya funciona con el service (existe — confirmar)

## 3. Ajustes — Refactor routes → service + repository

- [x] 3.1 Reemplazar helper `get_or_create_prefs` inline por `SettingsService.get_preferences()` en todas las rutas
- [x] 3.2 Refactor `ajustes_page` (GET /ajustes/) para usar `SettingsService.get_preferences()`
- [x] 3.3 Refactor `save_ajustes` (POST /ajustes/) para usar `SettingsService.update_preferences()`
- [x] 3.4 Mantener intactas las rutas de Google OAuth y sync (google_connect, google_callback, google_disconnect, google_sync)
- [x] 3.5 Eliminar imports de SQLAlchemy directos de routes.py que ya no se usen
- [x] 3.6 Verificar que `GET /ajustes/api/preferences` ya funciona con el service (existe — confirmar)

## 4. Tests — Metas

- [x] 4.1 Crear `backend/tests/test_metas.py` con fixture de goal de prueba
- [x] 4.2 Test: crear meta exitosamente via POST /metas/nueva
- [x] 4.3 Test: listar metas activas (GET /metas/) sin metas completadas
- [x] 4.4 Test: listar separa activas de completadas
- [x] 4.5 Test: editar meta (POST /metas/editar/{id}) actualiza campos
- [x] 4.6 Test: eliminar meta via action=delete
- [x] 4.7 Test: check-in diario crea HabitRecord
- [x] 4.8 Test: check-in duplicado actualiza en lugar de crear duplicado
- [x] 4.9 Test: check-in auto-completa meta binaria si current >= target
- [x] 4.10 Test: completar meta manualmente (POST /metas/completar/{id})
- [x] 4.11 Test: auth gate — rutas sin cookie redirigen a /auth/login
- [x] 4.12 Test: endpoint JSON GET /metas/api/goals devuelve lista

## 5. Tests — Ajustes

- [x] 5.1 Crear `backend/tests/test_ajustes.py` con fixture de preferencias
- [x] 5.2 Test: obtener preferencias via GET /ajustes/
- [x] 5.3 Test: auto-creación de preferencias si no existen
- [x] 5.4 Test: actualizar preferencias via POST /ajustes/
- [x] 5.5 Test: auth gate — rutas sin cookie redirigen a /auth/login
- [x] 5.6 Test: endpoint JSON GET /ajustes/api/preferences devuelve preferencias

## 6. Verificación final

- [x] 6.1 Ejecutar `pytest backend/tests/test_metas.py -v` — todos los tests pasan
- [x] 6.2 Ejecutar `pytest backend/tests/test_ajustes.py -v` — todos los tests pasan
- [x] 6.3 Ejecutar `pytest backend/tests/ -v` — no hay regresiones en tests existentes
- [x] 6.4 Verificar que las rutas HTML de metas y ajustes siguen funcionando (navegación manual)
