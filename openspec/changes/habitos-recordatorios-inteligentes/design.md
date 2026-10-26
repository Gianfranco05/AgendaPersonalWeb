## Context

- **Hábitos hoy**: no hay un modelo "hábito" propio. Un hábito es una `Goal` (`backend/app/modules/metas/models.py`) con `goal_type = "binary"` (check diario) o `"metric"` (valor diario); `progress` y `savings` son metas, no hábitos (mobile filtra igual en `HabitsScreen`/`useProgressGoals`). Cada marca es un `HabitRecord` (`goal_id`, `user_id`, `record_date` = **fecha local del cliente**, `value`). El check-in vive en `PUT /api/v1/goals/{id}/checkin` (`backend/app/api/v1/goals.py`): binario guarda un registro de valor 1 (deshacer lo borra), métrico suma registros del día.
  - **Gotcha**: para binarios `is_completed = current_value > 0`, o sea queda `true` para siempre después del primer check-in de la historia. **No sirve** para saber si el hábito está hecho hoy: hay que mirar los `HabitRecord` del día local.
  - Los hábitos **no tienen frecuencia ni días de la semana**; solo `start_date`/`end_date` opcionales.
  - `GoalsService.get_streak` usa `date.today()` del server y una ventana de 30 días: no sirve para la racha en la fecha local del usuario.
- **Recordatorios hoy** (`backend/app/modules/recordatorios/`): `Reminder` con `hour`, `minute`, `timezone_offset_minutes` (minutos al este de UTC; lo manda el cliente en cada create/update). `scheduler.py` corre un loop por minuto por worker (arrancado en el `lifespan` de `backend/app/main.py`), dispara en el minuto exacto con 3 minutos de recuperación, y deduplica con un dict en memoria + `claim_once` (`backend/app/core/redis_claim.py`, `SET NX`, sin Redis devuelve True).
- **Avisos de inversiones** (`backend/app/modules/inversiones/scheduler.py`): patrón más robusto, con **ventana** horaria y tres capas de dedup (memoria → Redis → marca atómica en la fila). Es el modelo a seguir.
- **Push** (`backend/app/modules/push/service.py`): `PushService.send_to_user(user_id, title, body, data)` manda a todos los tokens del usuario por Expo, canal Android `recordatorios`, nunca levanta excepción y limpia `DeviceNotRegistered`.
- **Mobile**: el push token se registra solo dentro de `applyReminder`/`syncReminders` (`src/lib/notifications.ts` → `initPush()`); un usuario que nunca tocó Recordatorios puede no tener token. El tap ya se resuelve en `targetFromData` (`investment_maturity`, `reminder`) y `useNotificationTaps` navega. Las pestañas son `HabitsTab` (stack `HabitsHome`, `Goals`) y `SettingsTab` (`Reminders`, …).
- **Web**: no hay push web; `ReminderSection` usa notificaciones del navegador para los recordatorios fijos. `GoalForm` (RHF + Zod, sin `z.coerce`) se usa para metas y para hábitos (`HabitsPage` lo abre con `binary`/`metric`). `endpoints.ts` ya tiene `localTzOffsetMinutes()` y modo mock.
- **Guardas**: `OWNED_TABLES` + test que falla si falta una tabla con `user_id`; `test_infra.py::test_no_api_route_is_public_by_accident`; `test_tenant_isolation.py`. Módulo `habits` es base (`registry.py`): sin `require_module`.

## Goals / Non-Goals

**Goals:**
- Una push solo cuando falta marcar algún hábito del día local del usuario, agrupada por hora, con tope diario.
- Hora general por usuario (default 20:00) y hora propia opcional por hábito; incluir/excluir cada hábito.
- Destacar la racha en riesgo sin sumar notificaciones.
- Exactamente una evaluación por (usuario, día local, hora) aunque haya varios workers, reinicios o Redis caído; sin mandar avisos viejos tras una caída.
- Tocar la push abre Hábitos. Configuración en web y mobile. Aislamiento por usuario, export y borrado de cuenta.

**Non-Goals:**
- Frecuencia de hábitos / días de la semana.
- Fallback con notificaciones locales en el celular.
- Web Push o email.
- Recordar metas `progress`/`savings`, o métricas por debajo de su meta diaria.
- Reconciliación automática de huso horario en segundo plano en el server (la hacen los clientes, ver D7).

## Decisions

### D1. Módulo nuevo `habitos_recordatorios`, rutas bajo `/api/v1/habit-reminders`

`backend/app/modules/habitos_recordatorios/` con `models.py`, `schemas.py`, `service.py` (cálculo de pendientes, racha y mensajes: funciones puras + consultas), `scheduler.py` y `api_routes.py` (`prefix="/habit-reminders"`, `tags=["habits"]`, todas con `get_current_user`). Router incluido en `backend/app/api/v1/router.py`.

*Alternativa*: `/api/v1/goals/reminder-settings`. Descartada: `PUT /goals/{goal_id}` capturaría `PUT /goals/reminder-settings` según el orden de declaración, y `goals.py` ya es grande. *Alternativa*: extender `Reminder` con un `kind = "habit"`. Descartada: `Reminder` tiene mensaje fijo y semántica de "sonar siempre"; mezclarlo complica el scheduler existente y su programación local en mobile (que lo trataría como un recordatorio local más).

### D2. Modelo de datos

**Tabla nueva `habit_reminder_settings`** (una fila por usuario, se crea en el primer `PUT`):

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | uuid4 |
| `user_id` | `String(36)` FK `users.id` | no | `unique`, index |
| `enabled` | `Boolean` | no | default/server_default **false** (interruptor general) |
| `hour` | `Integer` | no | default 20, check 0–23 |
| `minute` | `Integer` | no | default 0, check 0–59 |
| `daily_cap` | `Integer` | no | default 3, check 1–5 (pushes de hábitos por día local) |
| `streak_alerts` | `Boolean` | no | default/server_default true |
| `timezone_offset_minutes` | `Integer` | sí | −840..840; null → −180 (Argentina) |
| `created_at`, `updated_at` | `DateTime(timezone=True)` | no | |

**Columnas nuevas en `goals`**:

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `reminder_enabled` | `Boolean` | no | default/server_default **true**: con el interruptor general encendido, todos los hábitos entran salvo que se excluyan |
| `reminder_hour` | `Integer` | sí | 0–23; null = usa la hora general |
| `reminder_minute` | `Integer` | sí | 0–59; `CheckConstraint` "ambas null o ambas con valor" |

**Tabla nueva `habit_reminder_dispatches`** (marca persistente de dedup + contador del tope):

| Columna | Tipo | Null | Notas |
|---|---|---|---|
| `id` | `String(36)` PK | no | |
| `user_id` | `String(36)` FK `users.id` | no | index |
| `local_date` | `Date` | no | día local del usuario |
| `slot` | `String(5)` | no | `"HH:MM"` |
| `status` | `String(12)` | no | `sent`, `merged`, `nothing`, `capped`, `no_devices` |
| `goal_ids` | `Text` | sí | JSON con los ids incluidos (solo ids, sin títulos) |
| `created_at` | `DateTime(timezone=True)` | no | |

`UniqueConstraint("user_id", "local_date", "slot", name="uq_habit_reminder_dispatch")`. Retención: el scheduler borra filas con `local_date` anterior a 30 días, una vez por día UTC por proceso (borrado idempotente).

*Alternativa*: columnas en `user_preferences` (como la cotización de inversiones). Descartada: varios changes hermanos tocan `user_preferences`/`settings.py` en paralelo, y la configuración de hábitos tiene su propio endpoint y validaciones. *Alternativa para el dedup*: marca `last_reminded_on` en `goals` con `UPDATE` condicional (patrón inversiones). Descartada: la unidad de envío es (usuario, día, hora) y agrupa varios hábitos; una fila única por slot es atómica en SQLite y Postgres (`INSERT` + `IntegrityError`) y además da el conteo para el tope diario.

API: las horas viajan como `"HH:MM"` (`^([01]\d|2[0-3]):[0-5]\d$`) y se guardan como dos enteros (comparaciones baratas en el scheduler).

### D3. API

- `GET /api/v1/habit-reminders/settings` → `{enabled, time, daily_cap, streak_alerts, timezone_offset_minutes, has_push_devices}`. Sin fila devuelve los defaults **sin escribir** (un GET no crea filas). `has_push_devices` = el usuario tiene ≥ 1 `push_tokens`.
- `PUT /api/v1/habit-reminders/settings` → parcial (`exclude_unset`), upsert, misma respuesta. Validación 422 en español: `time` con el regex, `daily_cap` 1–5, `timezone_offset_minutes` −840..840. Un `null` explícito en un campo no nulo se ignora (mismo criterio que `/settings`).
- `GET /api/v1/habit-reminders/today?tz_offset_minutes=` → `{local_date, enabled, slots: [{time, status, habits: [{id, title, icon, streak}]}], pending_count}`. `status` por slot: `upcoming` (todavía no llegó la hora), `due` (en ventana, sin evaluar), o el `status` de la fila de dispatch si ya se evaluó. Reusa exactamente la lógica del scheduler (D4) — sirve para la UI ("Hoy a las 20:00 te avisamos de: Agua, Leer") y para verificar contra el backend real sin esperar a la hora. `tz_offset_minutes` opcional: si falta usa el de la configuración, y si tampoco hay, −180.
- Goals (`backend/app/api/v1/goals.py` + `metas/schemas.py`): `GoalCreate` suma `reminder_enabled: bool = True` y `reminder_time: "HH:MM" | null = null`; `GoalUpdateRequest` los suma opcionales (`reminder_time: null` explícito borra la hora propia); `GoalResponse` devuelve ambos en las 4 rutas que lo arman (conviene un helper `_to_response(goal)` para no repetir el constructor). El service traduce `reminder_time` ↔ `reminder_hour`/`reminder_minute`. Aplica a todos los tipos pero solo tiene efecto en `binary`/`metric`.

### D4. Hábito pendiente (fuente única: `service.pending_habits(db, user_id, local_date)`)

Un hábito está **pendiente** en `local_date` si:
1. `goal.user_id == user_id`, `goal_type IN ("binary", "metric")`, `reminder_enabled = true`;
2. `start_date IS NULL OR start_date <= local_date` y `end_date IS NULL OR end_date >= local_date`;
3. `COALESCE(SUM(habit_records.value), 0) <= 0` para `record_date = local_date` (registros filtrados también por `user_id`). Binario sin registro → pendiente; métrico con valor 0 o sin registros → pendiente; métrico con cualquier valor > 0 → hecho.

**Nunca** se usa `is_completed`. Una sola consulta con `LEFT JOIN` agregado; orden estable por `created_at`, `id`. La hora del hábito es `(reminder_hour, reminder_minute)` o la general.

**Racha** (`service.streak_until_yesterday`): días consecutivos con suma > 0 terminando en `local_date − 1`, mirando hasta 365 días atrás, en una consulta por usuario evaluado (solo de los hábitos pendientes). Misma semántica que `habitMonthStats` en mobile. Umbral `STREAK_MIN_DAYS = 3`.

### D5. Scheduler (`habitos_recordatorios/scheduler.py`)

Loop por minuto alineado al inicio del minuto (como los otros dos), arrancado y cancelado en el `lifespan` junto a `run_reminder_scheduler` y `run_investment_alert_scheduler`. Cada `_tick(now_utc)`:

1. **Una consulta liviana**: hábitos (`id`, `user_id`, horas) con `reminder_enabled` y tipo hábito de usuarios con `habit_reminder_settings.enabled = true`, más la hora general y el offset de cada uno. Se agrupa en memoria por usuario → conjunto de slots.
2. Por usuario: `local_now = now_utc + offset` (offset o −180), `local_date`, `m = minutos del día`. Un slot `T` está **en ventana** si `T <= m < min(T + 60, 1440)`. Fuera de la ventana no se evalúa nunca: tras una caída de más de 60 minutos, o si cambió el día local, el aviso de ese slot se pierde (no se mandan avisos viejos).
3. Se toman los slots en ventana cuya clave `(user_id, local_date, slot)` no esté en el set en memoria del proceso; se agregan al set.
4. Por cada slot: `claim_once(f"habit-reminder:{user_id}:{local_date}:{slot}", 129600)`. Si lo ganó otro worker, se saltea.
5. Se calculan los pendientes **en ese momento** para los hábitos de esos slots, los envíos `sent` del día (para el tope) y si hay tokens.
6. **Fusión en recuperación**: si en un mismo ciclo hay más de un slot en ventana para el usuario (solo pasa tras una caída: 20:00 y 20:15 pendientes al volver a las 20:20), se manda **una** push con la unión de pendientes; el primer slot queda `sent` y los demás `merged`.
7. Estado: sin pendientes → `nothing`; `sent` del día ≥ `daily_cap` → `capped`; sin tokens → `no_devices`; si no → `sent`.
8. **Marca persistente**: `INSERT` en `habit_reminder_dispatches` en una transacción propia. `IntegrityError` → rollback y no se manda (lo hizo otro proceso o un ciclo previo antes de un reinicio). Otra excepción (DB caída) → se saca la clave del set, se libera el claim de Redis (nuevo `release_claim(key)` best-effort en `core/redis_claim.py`) y se relanza para reintentar en el próximo ciclo dentro de la ventana.
9. Si el estado es `sent`: `PushService.send_to_user(...)` (D6). Semántica **at-most-once**: la marca se escribe antes de mandar; si Expo falla, el aviso se pierde (igual que recordatorios e inversiones).
10. Poda del set en memoria (fechas anteriores a ayer UTC) y poda diaria de dispatches > 30 días.

Errores por usuario se loguean y no frenan a los demás; el loop atrapa todo salvo `CancelledError`.

*Alternativa*: disparo en el minuto exacto con 3 minutos de recuperación (patrón recordatorios). Descartada: el pedido es no perder el aviso si el server se reinicia (deploy) cerca de la hora; 60 minutos sigue siendo "a la hora que pediste". *Alternativa*: precalcular `next_fire_at` por usuario. Descartada por ahora: la consulta del paso 1 es O(hábitos con recordatorio) por minuto, suficiente para el volumen actual; queda anotado en Riesgos.

### D6. Mensaje y datos de la push

- Nombre: título del hábito truncado a 40 caracteres con "…". Emoji: `goal.icon` si tiene algún carácter no ASCII; si no (p. ej. `fa-bullseye` de la web), `✅`.
- **1 pendiente**: título `"{emoji} Can_cen"`, cuerpo `Todavía no marcaste «{título}» hoy.` Con racha ≥ 3 y `streak_alerts`: `🔥 Llevás {n} días seguidos con «{título}». ¡No la cortes hoy!`
- **2+ pendientes**: título `✅ Te faltan {n} hábitos hoy`, cuerpo con los nombres (`Agua, Leer y Correr`; más de 4: `Agua, Leer, Correr, Meditar y 2 más`). Con racha: se agrega ` · 🔥 «{título}» lleva {n} días seguidos` (la racha más larga).
- `data = {type: "habit_reminder", local_date: "YYYY-MM-DD", goal_ids: [...]}`. Canal `recordatorios` (el de siempre).
- La racha en riesgo **no genera una push aparte**: solo cambia el texto. Así el tope diario y la agrupación siguen valiendo.

### D7. Huso horario

Se guarda en `habit_reminder_settings.timezone_offset_minutes`. Los clientes lo mandan en cada `PUT` de configuración y, además, **lo resincronizan al abrir la app** (mobile: montaje de `TabNavigator` y vuelta a primer plano; web: al cargar Hábitos o Configuración) si la configuración está activa y el offset del dispositivo difiere del guardado. Cubre viajes y cambios de horario sin reconciliación en el server. Null → −180. El día local del scheduler coincide con el `record_date` que mandan los clientes al marcar (fecha local del dispositivo).

### D8. Mobile

- `src/lib/notifications.ts`: exportar `ensurePushRegistered(): Promise<boolean>` (envuelve `initPush()`), sumar `{ kind: 'habits' }` a `NotificationTarget` y `type === 'habit_reminder'` en `targetFromData`.
- `src/hooks/useNotificationTaps.ts`: `habits` → `navigate('HabitsTab', { screen: 'HabitsHome' })`.
- `src/hooks/useHabitReminders.ts` (SWR de `settings` y `today`) y funciones en `src/api/endpoints.ts` (escrituras con `queued(...)`, `tzOffsetMinutes()` en cada `PUT`).
- **Ajustes › Recordatorios** (`RemindersScreen`): tarjeta "Hábitos sin marcar" arriba de la lista: switch "Avisarme si me falta marcar un hábito", `TimeField` "Hora", `NumberStepper` "Máximo de avisos por día" (1–5), switch "Destacar rachas en riesgo", y el resumen de `/today` ("Hoy a las 20:00: Agua, Leer" / "Ya marcaste todo hoy"). Al encender: `ensurePushRegistered()`; si devuelve false, aviso "Este celular no puede recibir avisos del servidor (permiso de notificaciones o versión de la app)" y la configuración se guarda igual.
- **Formulario del hábito** (`HabitFormSheet`): sección "Recordatorio": switch "Recordarme si no lo marqué" (default on) y chips "Hora general (20:00)" / "Otra hora" + `TimeField`. Con el interruptor general apagado, una línea "Activá los avisos de hábitos" que lo enciende (con la misma lógica de permiso).
- **Hábitos** (`HabitsScreen`): banner descartable si el interruptor general está apagado y hay ≥ 1 hábito: "¿Te avisamos a las 20:00 si te falta marcar algún hábito?" [Activar] [Ahora no]; el descarte se guarda en el almacenamiento local del dispositivo por usuario.
- Al abrir la app con la configuración activa: `ensurePushRegistered()` silencioso (sin pedir permiso si ya fue denegado) + resincronización del offset (D7).
- Sin textos de compra ni precios (no aplica).

### D9. Web

- `frontend/src/pages/Settings/HabitReminderSection.tsx` junto a `ReminderSection`: mismos controles que mobile, el resumen de `/today` y la nota "Las notificaciones llegan a la app de Android donde tengas la sesión iniciada" + aviso si `has_push_devices` es false.
- `GoalForm`: para `binary`/`metric`, checkbox "Recordarme si no lo marqué" e input `type="time"` opcional ("vacío = hora general"). Zod con `z.boolean()` y `z.string()` + `refine` del formato; nunca `z.coerce`.
- `src/api/endpoints.ts` (+ mock: configuración en memoria y `/today` derivado de los hábitos mock), `src/hooks/useHabitReminders.ts`, tipos en `src/types`.

### D10. Cuenta, seguridad y migración

- `OWNED_TABLES`: `("habit_reminder_dispatches", HabitReminderDispatch)` y `("habit_reminder_settings", HabitReminderSettings)` (sin FKs entre sí ni hacia goals: el orden no importa, van con las tablas independientes).
- Toda consulta filtra por `user_id`; el scheduler arma claves y consultas por usuario y nunca mezcla registros de un usuario con hábitos de otro (el `JOIN` de registros filtra por `goal_id` **y** `user_id`).
- Migración nueva (número siguiente al head al momento de implementar, hoy sería `019_habit_reminders`; `down_revision` = head vigente): `add_column` en `goals` (`reminder_enabled` con `server_default=true`), `create_table` de las dos tablas con checks/índices/unique; `downgrade` con `batch_alter_table` para SQLite. Verificación en Postgres (PGlite) del upgrade, del `INSERT`/`IntegrityError` y del rollback de sesión tras el conflicto.

## Dependencias

- **Migraciones de changes hermanos** (`finanzas-recurrentes`, `finanzas-datos-mercado`, `app-bloqueo-y-bienvenida`, …): todos pueden crear una migración `019_*`. Esta propuesta no fija número: al implementar se toma el siguiente libre y se verifica `alembic heads` = un solo head.
- **`app-bloqueo-y-bienvenida`**: (a) si la app está bloqueada, la navegación del tap a Hábitos debe ocurrir después de desbloquear (lo resuelve ese change; acá solo se agrega el `type`); (b) si ese change suma una preferencia para ocultar el contenido de las notificaciones, el armado del mensaje (D6) debe usar un texto genérico ("Te faltan hábitos por marcar hoy") — punto de extensión: `build_message(..., hide_content: bool)`; (c) la bienvenida puede ofrecer activar estos avisos usando `PUT /habit-reminders/settings`.
- **`widgets-android`**: si el widget marca hábitos, tiene que pasar por la misma API de check-in para que el server los vea; marcas en la cola offline todavía no enviadas pueden producir un aviso de algo ya marcado (ver Riesgos). El widget puede reusar `GET /habit-reminders/today` para mostrar pendientes.
- **Cualquier change que agregue tipos de push** (p. ej. `finanzas-recurrentes`): `NotificationTarget`/`targetFromData`/`useNotificationTaps` se editan en paralelo; al integrar se unen los casos.
- `OWNED_TABLES` y `backend/app/api/v1/router.py` también los tocan otros changes: conflictos triviales de merge.

## Risks / Trade-offs

- [Celular sin push remota (Expo Go, permiso denegado, sin `projectId`)] → no llega nada; la UI lo dice (`has_push_devices`, resultado de `ensurePushRegistered`) en vez de prometer el aviso.
- [Marca hecha offline todavía en la cola] → puede llegar un aviso de un hábito ya marcado. Impacto bajo; la cola se vacía al abrir la app. No se intenta suprimir en el cliente.
- [Offset desactualizado (viaje, DST)] → el aviso llega a otra hora o el "hoy" no coincide; se corrige solo al abrir la app (D7).
- [Expo caído en el momento del envío] → aviso perdido (at-most-once), igual que el resto de los schedulers; preferible a duplicados.
- [Varios workers sin Redis] → cada worker evalúa el slot una vez; la fila única garantiza un solo envío. Costo: N consultas de pendientes por slot.
- [Escalabilidad] → la consulta por minuto crece con los hábitos con recordatorio; si hiciera falta, precalcular `next_fire_at` por usuario o filtrar por offsets en ventana en SQL.
- [Postgres aborta la transacción tras `IntegrityError`] → el `INSERT` va en su propia transacción/sesión y se hace rollback explícito; se prueba en PGlite (SQLite no reproduce esto).
- [Hábitos con muchas horas distintas] → el tope diario corta los últimos (`capped`); la UI sugiere usar la hora general.
- [Nombres de hábitos en la pantalla bloqueada] → por defecto se muestran (es el valor del aviso); ver Dependencias (b).

## Migration Plan

1. Deploy con la migración (`alembic upgrade head` en el arranque de prod): columnas nuevas con defaults, tablas vacías. Nadie recibe nada hasta activar (interruptor general apagado por defecto).
2. Clientes viejos: los campos nuevos de `GoalResponse` son aditivos y `reminder_enabled` tiene default, así que crear/editar hábitos desde una app vieja sigue funcionando.
3. Rollback: apagar el scheduler (quitarlo del lifespan) basta para detener envíos; `alembic downgrade` al head anterior elimina tablas y columnas.

## Open Questions

1. **¿Apagado por defecto?** Recomendación: sí, interruptor general apagado + banner en Hábitos para activarlo (evita pushes sorpresa a usuarios existentes y pide el permiso de Android en contexto). Alternativa: encendido para todos con push registrada.
2. **Hora por defecto**: recomendación 20:00 (queda tiempo para hacer el hábito). Alternativa 21:00.
3. **Tope diario**: recomendación default 3, configurable 1–5.
4. **Racha en riesgo**: recomendación incluirla solo como texto dentro de la misma push, desde 3 días seguidos (sin push extra). Alternativa: push aparte más tarde (p. ej. 22:00) solo para rachas ≥ 7.
5. **Métricas por debajo de la meta diaria**: recomendación contarlas como hechas con cualquier valor > 0 en esta versión (lo pedido). Alternativa futura: "Te falta 1 L de Agua".
6. **Frecuencia / días de la semana**: recomendación dejarlo para un change propio ("habitos-frecuencia") que también ajuste rachas y estadísticas; este scheduler ya filtra por un predicado (D4) donde se enchufaría.
7. **Ventana de recuperación**: recomendación 60 minutos.
8. **Botón "Probar ahora"** (push de prueba con los pendientes actuales): recomendación no en esta versión; `GET /today` alcanza para verificar. Si se agrega, con rate limit.
