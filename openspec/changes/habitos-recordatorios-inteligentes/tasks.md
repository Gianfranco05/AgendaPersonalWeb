## 1. Backend — Modelo y migración

- [x] 1.1 Crear `backend/app/modules/habitos_recordatorios/__init__.py` y `models.py` con `HabitReminderSettings` (`user_id` único, `enabled` default/server_default **true**, `hour` 20, `minute` 0, `daily_cap` 3, `streak_alerts` true, `timezone_offset_minutes` null, `CheckConstraint` de rangos) y `HabitReminderDispatch` (`local_date` `Date`, `slot` `String(5)`, `status`, `goal_ids` JSON en `Text`, `UniqueConstraint("user_id", "local_date", "slot")`, índice `(user_id, local_date)`) según design D2
- [x] 1.2 Agregar a `Goal` (`backend/app/modules/metas/models.py`) `reminder_enabled` (`server_default=true()`), `reminder_hour`, `reminder_minute` (null) y el check "ambas null o ambas con valor"
- [x] 1.3 Registrar los modelos donde se importan para `Base.metadata`/Alembic (mismo lugar que el resto de los módulos)
- [x] 1.4 Crear la migración en `backend/migrations/versions/` con el número siguiente al head vigente (`023_habit_reminders`, `down_revision = "022_onboarding_seen"`): `add_column` en `goals`, `create_table` de las dos tablas con checks/índices/unique; `downgrade` con `batch_alter_table` para SQLite
- [x] 1.5 Verificar `alembic heads` = un solo head y `upgrade head` / `downgrade -1` / `upgrade head` en SQLite

## 2. Backend — Lógica de pendientes, racha y mensajes

- [x] 2.1 `habitos_recordatorios/service.py`: helpers `parse_hhmm`/`format_hhmm`, `local_now(now_utc, offset)` con fallback −180 y `window_contains(slot_minutes, local_minutes)` (ventana `[T, min(T+60, 1440))`)
- [x] 2.2 `pending_habits(db, user_id, local_date)`: una consulta con `LEFT JOIN` agregado sobre `habit_records` filtrado por `goal_id` y `user_id` y `record_date = local_date`; tipos `binary`/`metric`, `reminder_enabled`, rango `start_date`/`end_date`, suma ≤ 0; sin usar `is_completed`; orden `created_at`, `id`; devuelve el slot efectivo de cada hábito
- [x] 2.3 `streaks_until_yesterday(db, user_id, goal_ids, local_date)`: días consecutivos con suma > 0 terminando ayer, hasta 365 días, en una consulta
- [x] 2.4 `build_message(habits, streaks, streak_alerts, hide_content=False)` → `(title, body)` con los textos de design D6 (emoji no ASCII o ✅, truncado a 40, "y N más" pasado 4, racha ≥ 3); `hide_content` queda como punto de extensión para `app-bloqueo-y-bienvenida`
- [x] 2.5 `today_overview(db, user_id, tz_offset)` reutilizando `pending_habits` y las filas de dispatch del día para el `status` por slot (`upcoming`/`due`/estado registrado)

## 3. Backend — API

- [x] 3.1 `habitos_recordatorios/schemas.py`: `HabitReminderSettingsOut`, `HabitReminderSettingsUpdate` (`time` con regex `^([01]\d|2[0-3]):[0-5]\d$`, `daily_cap` 1–5, offset −840..840, mensajes 422 en español), `TodayOverviewOut`
- [x] 3.2 `habitos_recordatorios/api_routes.py` (`prefix="/habit-reminders"`, `get_current_user` en todas): `GET /settings` (defaults sin crear fila, `has_push_devices`), `PUT /settings` (upsert parcial, null explícito ignorado), `GET /today?tz_offset_minutes=`
- [x] 3.3 Incluir el router en `backend/app/api/v1/router.py`
- [x] 3.4 Goals: sumar `reminder_enabled`/`reminder_time` a `GoalCreate`, `GoalUpdateRequest` y `GoalResponse` en `backend/app/api/v1/goals.py` y a `GoalUpdate` en `metas/schemas.py`; helper `_to_response(goal)` para las 4 rutas; traducción `reminder_time` ↔ `reminder_hour`/`reminder_minute` (null explícito borra); 422 ante formato inválido
- [x] 3.5 Confirmar que las rutas HTML legacy de `metas/routes.py` siguen creando metas (defaults de columna)
- [x] 3.6 Sumar `("habit_reminder_dispatches", HabitReminderDispatch)` y `("habit_reminder_settings", HabitReminderSettings)` a `OWNED_TABLES` en `backend/app/modules/cuenta/service.py`

## 4. Backend — Scheduler

- [x] 4.1 `core/redis_claim.py`: agregar `release_claim(key)` best-effort (no lanza; sin Redis no hace nada)
- [x] 4.2 `habitos_recordatorios/scheduler.py`: `_tick(now_utc)` con la consulta liviana de hábitos con recordatorio de usuarios con push token y con configuración habilitada o sin fila (ON por defecto), agrupado por usuario → slots, cálculo de hora/día local y slots en ventana (design D5 pasos 1–3)
- [x] 4.3 Dedup en tres capas: set en memoria `(user_id, local_date, slot)`, `claim_once("habit-reminder:{user}:{date}:{slot}", 129600)` e `INSERT` en `habit_reminder_dispatches` en transacción propia; `IntegrityError` → rollback y no enviar; otro error → sacar del set, `release_claim` y relanzar
- [x] 4.4 Estados `nothing` / `capped` (conteo de `sent` del día vs `daily_cap`) / `no_devices` / `sent`, y fusión de varios slots del mismo usuario en el mismo ciclo (`sent` + `merged`)
- [x] 4.5 Envío con `PushService.send_to_user` y `data = {type: "habit_reminder", local_date, goal_ids}`; errores por usuario logueados sin cortar el ciclo
- [x] 4.6 Poda del set en memoria y poda diaria de dispatches con más de 30 días
- [x] 4.7 `run_habit_reminder_scheduler()` alineado al minuto; arrancarlo y cancelarlo en el `lifespan` de `backend/app/main.py` junto a los otros dos

## 5. Backend — Tests

- [x] 5.1 `backend/tests/test_habit_reminders.py` — pendientes: binario sin registro sí; binario marcado no; métrico 0 sí; métrico 0,5 con meta 2 no; binario con `is_completed=true` histórico y sin registro hoy sí (regresión del gotcha); fuera de `start_date`/`end_date` no; `reminder_enabled=false` no; `progress`/`savings` nunca
- [x] 5.2 Zona horaria: offset −180 dispara a las 23:00 UTC para 20:00; slot 22:30 con registro del día local evaluado a la 01:30 UTC del día siguiente no envía; offset +60; offset null → −180
- [x] 5.3 Agrupación y mensajes: 3 pendientes → una push "✅ Te faltan 3 hábitos hoy" / "Agua, Leer y Correr"; 6 → "y 2 más"; uno solo → "Todavía no marcaste «…» hoy."; `fa-bullseye` → ✅; truncado a 40; horas propias generan pushes separadas
- [x] 5.4 Tope diario: cap 2 con slots 08:00/13:00/20:00 → 2 envíos y `capped`; racha: 12 días → texto 🔥, 2 días → texto plano, `streak_alerts=false` → plano, la racha no agrega pushes
- [x] 5.5 Ventana: caída y vuelta a las 20:40 envía; a las 21:05 no; slot 23:30 y vuelta a las 00:10 del día siguiente no; 19:59 no evalúa; 20:00 y 20:15 al volver a las 20:20 → una push con la unión (`sent` + `merged`)
- [x] 5.6 Dedup: dos `_tick` concurrentes → una push; ciclos cada minuto de 20:00 a 20:59 → una; "reinicio" (limpiar set) sin Redis → no reenvía por la fila única; claim de Redis perdido → no envía; error de DB al insertar → no envía y reintenta en el ciclo siguiente (mock); probar con `send_to_user` mockeado
- [x] 5.7 Interruptor general apagado → nada; usuario con token y sin fila → recibe con defaults; usuario sin token → nada; usuario sin tokens → `no_devices` sin error; Expo caído no corta el ciclo; poda de dispatches > 30 días
- [x] 5.8 API: GET con defaults no crea fila; `has_push_devices`; PUT parcial conserva el resto; 422 para `24:00`, `daily_cap` 0/6, offset ±841; `/today` con `upcoming`, `sent` y `pending_count = 0`; 401 sin sesión
- [x] 5.9 `test_metas.py`: crear/editar hábito con `reminder_time`, borrar la hora con null, `reminder_enabled=false`, cliente viejo sin campos nuevos → defaults, formato inválido → 422
- [x] 5.10 Aislamiento (`test_tenant_isolation.py` + casos propios): registros de B no marcan el hábito de A; settings y `/today` por usuario; `PUT /goals/{id}` de otro usuario → 404; el scheduler no mezcla usuarios
- [x] 5.11 `test_account.py`: export incluye `habit_reminder_settings` y `habit_reminder_dispatches` propios y no ajenos; borrado no deja filas; guarda de `OWNED_TABLES` en verde
- [x] 5.12 `test_infra.py::test_no_api_route_is_public_by_accident` pasa sin rutas públicas nuevas; `test_reminders.py` y `test_investment_alerts.py` siguen verdes tras `release_claim`
- [x] 5.13 Correr `cd backend && python -m pytest -q` completo sin regresiones

## 6. Web — API, tipos y hooks (`frontend/`)

- [x] 6.1 Tipos en `src/types`: `HabitReminderSettings`, `HabitReminderToday`; extender `Goal` con `reminder_enabled` y `reminder_time` (opcionales)
- [x] 6.2 `src/api/endpoints.ts`: `fetchHabitReminderSettings`, `updateHabitReminderSettings` (siempre con `timezone_offset_minutes: localTzOffsetMinutes()`), `fetchHabitReminderToday` (con `tz_offset_minutes`); mocks en memoria con las mismas formas cuando `MOCK_ENABLED` (`/today` derivado de los hábitos mock); goals mock con los campos nuevos
- [x] 6.3 `src/hooks/useHabitReminders.ts`: SWR de settings y today, `save` que revalida ambos; marcar/editar hábitos revalida `today`; resincronizar el offset al cargar Hábitos/Configuración si está activo y difiere
- [x] 6.4 Tests de endpoints/hooks (URL, params de tz, invalidación, mock)

## 7. Web — UI (`frontend/`)

- [x] 7.1 `src/pages/Settings/HabitReminderSection.tsx` (y un interruptor de un toque para apagar los avisos en `HabitsPage`): switch general, hora, máximo por día (1–5), rachas, resumen de hoy, nota "llegan a la app de Android" y aviso si `has_push_devices` es false; dark mode; agregarla en `SettingsPage.tsx` junto a `ReminderSection`
- [x] 7.2 `src/pages/Goals/GoalForm.tsx`: para `binary`/`metric`, checkbox "Recordarme si no lo marqué" + `input type="time"` opcional (vacío = hora general); Zod con `z.boolean()`/`z.string()` + `refine`, sin `z.coerce`; ocultos para `progress`/`savings`
- [x] 7.3 Tests de componentes: la sección guarda `{enabled, time, …}`; aviso sin dispositivos; el form de `progress` no muestra los campos; el de hábito envía `reminder_time` o null
- [x] 7.4 `npx vitest run --maxWorkers=2`, `npm run build` y lint sin errores

## 8. Mobile — API, tipos y hooks (`C:\Proyectos\vida-personal-mobile`)

- [ ] 8.1 [mobile] `src/types`: `HabitReminderSettings`, `HabitReminderToday`; `Goal` con `reminder_enabled`/`reminder_time`
- [ ] 8.2 [mobile] `src/api/endpoints.ts`: settings (PUT con `queued(...)` y `tzOffsetMinutes()`), today (`tz_offset_minutes`), y los campos nuevos en crear/editar hábito
- [ ] 8.3 [mobile] `src/hooks/useHabitReminders.ts` (SWR); revalidar `today` al marcar/editar hábitos (`src/hooks/useGoals.ts`)
- [ ] 8.4 [mobile] `src/lib/notifications.ts`: exportar `ensurePushRegistered()` (envuelve `initPush`), `{ kind: 'habits' }` en `NotificationTarget` y `type === 'habit_reminder'` en `targetFromData`
- [ ] 8.5 [mobile] `src/hooks/useNotificationTaps.ts`: `habits` → `navigate('HabitsTab', { screen: 'HabitsHome' })`
- [ ] 8.6 [mobile] Al montar `TabNavigator` y al volver a primer plano (`AppState`), con la configuración activa: `ensurePushRegistered()` silencioso y resincronizar el offset si difiere

## 9. Mobile — UI (`C:\Proyectos\vida-personal-mobile`)

- [ ] 9.1 [mobile] `src/screens/RemindersScreen.tsx`: tarjeta "Hábitos sin marcar" (switch, `TimeField`, `NumberStepper` 1–5, switch de rachas, resumen de hoy); al encender pedir permiso + `ensurePushRegistered()` y avisar si el celular no puede recibir push
- [ ] 9.2 [mobile] `src/components/HabitFormSheet.tsx`: sección "Recordatorio" con switch "Recordarme si no lo marqué", chips "Hora general (HH:MM)" / "Otra hora" + `TimeField`; atajo para activar el interruptor general si está apagado
- [ ] 9.3 [mobile] `src/screens/HabitsScreen.tsx`: interruptor de un toque (campana) para apagar/encender los avisos, y banner descartable "permití las notificaciones" [Permitir] [Ahora no] cuando están encendidos y falta el token, con el descarte guardado por usuario en el almacenamiento local
- [ ] 9.4 [mobile] Modo claro/oscuro con tokens Stitch y safe-area en los sheets; sin textos de compra
- [ ] 9.5 [mobile] `npx tsc --noEmit` sin errores

## 10. Verificación contra el backend real (no mock)

- [ ] 10.1 Aplicar la migración en Postgres (PGlite o docker compose) y probar `upgrade`/`downgrade`; verificar en Postgres el `INSERT` duplicado en `habit_reminder_dispatches` (`IntegrityError` + rollback sin romper la sesión del ciclo)
- [ ] 10.2 Por API contra el backend real: `GET/PUT /habit-reminders/settings`, hábito con hora propia, `GET /today` antes y después de marcar (métrico 0 vs > 0)
- [ ] 10.3 Web con `VITE_MOCK_ENABLED=false`: configurar en Configuración y en el formulario del hábito; recargar y ver los valores persistidos
- [ ] 10.4 Mobile (build lan contra el backend real): dar el permiso desde el banner (token registrado, `has_push_devices` true), configurar una hora 2–3 minutos adelante, dejar dos hábitos sin marcar → llega **una** push agrupada; marcar todo y configurar otra hora → no llega nada; tocar la push abre Hábitos (en caliente y en frío)
- [ ] 10.5 Dedup real: gunicorn con 2+ workers y Redis → una sola push; sin Redis y reiniciando el proceso dentro de la ventana → no se repite
- [ ] 10.6 Recuperación: apagar el backend antes de la hora y levantarlo dentro de los 60 minutos (llega) y pasado ese plazo (no llega)
- [ ] 10.7 Export de cuenta contiene las tablas nuevas; borrar una cuenta de prueba no deja filas
- [ ] 10.8 `openspec validate habitos-recordatorios-inteligentes --strict` y marcar las tareas completadas
