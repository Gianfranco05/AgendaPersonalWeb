## Why

Los hábitos se cortan por olvido, no por falta de ganas: hoy la app solo tiene recordatorios fijos ("Tomar agua" todos los días a las 20:00) que suenan aunque el hábito ya esté marcado, así que la gente los apaga. Ya existe la infraestructura de push remota (módulo `push`, schedulers en el lifespan con dedup entre workers), así que se puede avisar **solo cuando hace falta**: "Todavía no marcaste «Tomar agua» hoy".

## What Changes

- **Recordatorio inteligente de hábitos**: a la hora elegida (default 20:00 local), el server revisa qué hábitos (`goal_type` `binary` o `metric`) del usuario **no tienen registro hoy** (binario sin registro; métrico sin valor > 0) y manda una push solo si falta alguno. Si el usuario ya marcó todo, no llega nada.
- **Configuración global por usuario** (nueva tabla `habit_reminder_settings`): interruptor general (apagado por defecto, se activa desde Hábitos o Ajustes), hora general, tope diario de notificaciones (default 3, de 1 a 5), aviso de racha en riesgo (encendido por defecto) y huso horario (`timezone_offset_minutes`, lo manda el cliente; fallback Argentina −180).
- **Configuración por hábito** (columnas nuevas en `goals`): incluir o no ese hábito en el recordatorio (default sí) y hora propia opcional (vacía = usa la general).
- **Agrupación**: todos los hábitos pendientes con la misma hora van en **una sola push** ("Te faltan 3 hábitos hoy" · "Agua, Leer y Correr"). Horas distintas generan pushes distintas, hasta el tope diario.
- **Racha en riesgo** (entra, pero sin push extra): si un hábito pendiente viene con 3 o más días seguidos hasta ayer, el texto de esa misma push lo destaca ("🔥 Llevás 12 días seguidos con «Leer». ¡No la cortes hoy!"). No suma notificaciones.
- **Fechas del hábito**: no se recuerda un hábito antes de su `start_date` ni después de su `end_date`. Los hábitos no tienen frecuencia ni días de la semana: se recuerda todos los días (frecuencia queda fuera de alcance).
- **Scheduler in-process** nuevo en el lifespan, un ciclo por minuto, con dedup en tres capas (memoria, `claim_once` en Redis y una fila única en la tabla nueva `habit_reminder_dispatches`) y ventana de recuperación de 60 minutos tras una caída: pasada la ventana, o cambiado el día local, el aviso no sale.
- **API**: `GET/PUT /api/v1/habit-reminders/settings` (incluye si el usuario tiene dispositivos con push) y `GET /api/v1/habit-reminders/today` (qué se recordaría hoy, para la UI y la verificación). `GoalCreate`/`GoalUpdate`/`GoalResponse` suman `reminder_enabled` y `reminder_time` (cambio aditivo).
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): sección "Hábitos sin marcar" en Ajustes › Recordatorios, toggle y hora propia en el formulario del hábito, banner para activarlo en Hábitos, registro del push token al activarlo y al abrir la app, y tocar la push (`type: "habit_reminder"`) abre la pestaña Hábitos.
- **Web** (`frontend/`): sección en Configuración y campos en el formulario de hábito, con aviso de que la notificación llega a la app de Android; modo mock mantenido.
- Export y borrado de cuenta incluyen las dos tablas nuevas.

### Fuera de alcance

- **Frecuencia de hábitos** (días de la semana, "3 veces por semana"): cambia rachas y estadísticas, merece su propio change. Sin frecuencia, se recuerda todos los días.
- **Fallback local en el celular** (Expo Go, sin push o sin permiso): una notificación local programada no sabe si el hábito se marcó desde otro dispositivo o la web. Sin push remota la UI lo avisa y no promete el recordatorio.
- Recordar metas métricas por debajo de la meta diaria ("te falta 1 L"): con un valor > 0 el hábito cuenta como hecho.
- Notificaciones web (Web Push) y por email.
- Suprimir el aviso porque el usuario "abrió la app": solo lo suprime marcar los hábitos.
- Recordatorios para metas de progreso/ahorro (`progress`, `savings`).

## Capabilities

### New Capabilities
- `habit-smart-reminders`: cálculo de hábitos pendientes del día local, envío agrupado por hora, tope diario, mensaje de racha en riesgo, scheduler con dedup multi-worker y ventana de recuperación, datos de la push y apertura de Hábitos al tocarla.
- `habit-reminder-settings`: configuración global (`/api/v1/habit-reminders/settings`) y por hábito (`reminder_enabled`, `reminder_time` en goals), vista del día, UI web y mobile, registro de push al activar, aislamiento por usuario y export/borrado de cuenta.

### Modified Capabilities
<!-- Ninguna: los campos nuevos de goals son aditivos y quedan especificados en habit-reminder-settings. -->

## Impact

- **Backend**: nuevo módulo `backend/app/modules/habitos_recordatorios/` (models, schemas, service, scheduler, api_routes); router en `backend/app/api/v1/router.py`; `backend/app/modules/metas/models.py` + `backend/app/api/v1/goals.py` + `backend/app/modules/metas/schemas.py` (columnas y campos de recordatorio); `backend/app/main.py` (lifespan arranca el scheduler); `backend/app/modules/cuenta/service.py` (`OWNED_TABLES`); migración nueva en `backend/migrations/versions/` (número y `down_revision` según el head al implementar).
- **Tests**: nuevo `backend/tests/test_habit_reminders.py` (+ scheduler), extensiones en `test_metas.py`, `test_tenant_isolation.py`, `test_account.py`, `test_infra.py` (ruta nueva protegida).
- **Web**: `frontend/src/pages/Settings/HabitReminderSection.tsx` (nuevo), `SettingsPage.tsx`, `pages/Goals/GoalForm.tsx` (solo para `binary`/`metric`), `src/api/endpoints.ts` (+ mock), `src/hooks/useHabitReminders.ts`, `src/types`.
- **Mobile**: `src/screens/RemindersScreen.tsx`, `src/components/HabitFormSheet.tsx`, `src/screens/HabitsScreen.tsx`, `src/lib/notifications.ts` (nuevo `type` y `ensurePushRegistered`), `src/hooks/useNotificationTaps.ts`, `src/hooks/useHabitReminders.ts`, `src/api/endpoints.ts`, `src/types`.
- **Infra**: sin dependencias ni APIs externas nuevas; un loop más por worker en el lifespan; Redis opcional como hoy.
