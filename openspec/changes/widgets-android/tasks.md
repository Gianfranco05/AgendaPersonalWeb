## 1. Backend — Endpoint `GET /api/v1/widgets/today`

- [ ] 1.1 Crear `backend/app/modules/widgets/__init__.py` y `schemas.py` con `WidgetTaskItem`, `WidgetTasks`, `WidgetHabitItem`, `WidgetHabits` y `WidgetsTodayOut` (design D2)
- [ ] 1.2 `backend/app/modules/widgets/service.py`: `today_summary(user_id, tz_offset_minutes, task_limit, habit_limit)` con `local_today`; selección y orden de tareas (vencidas primero, prioridad `alta > media > baja`, `order`, `created_at`), conteos sobre el conjunto completo; hábitos `binary`/`metric` en orden `created_at DESC` con `today_value` por una sola consulta agregada (`GROUP BY goal_id`) sobre `HabitRecord` del día; todo filtrado por `user_id`
- [ ] 1.3 `backend/app/modules/widgets/api_routes.py`: router `prefix="/widgets"`, `GET /today` con `tz_offset_minutes` (−840..840), `task_limit` y `habit_limit` (1..20), `get_current_user`
- [ ] 1.4 Incluir el router en `backend/app/api/v1/router.py` y confirmar que el test guardia de rutas públicas sigue pasando (la ruta es autenticada)

## 2. Mobile — Dependencias, config y build

- [ ] 2.1 [mobile] `C:\Proyectos\vida-personal-mobile`: instalar `react-native-android-widget` (0.24.x) con `npx expo install` y confirmar en la doc de la versión instalada los nombres exactos de `resizeMode`, `widgetCategory` y `renderWidget({ light, dark })`
- [ ] 2.2 [mobile] `app.config.js`: agregar el plugin con los widgets `TasksToday` y `HabitsToday` (labels, descripciones, 4×2, mínimos 250dp×110dp, redimensionables, `updatePeriodMillis: 1800000`, solo pantalla de inicio, `previewImage`) y comentar por qué está ahí y que exige build nuevo (design D12)
- [ ] 2.3 [mobile] `index.ts`: registrar `registerWidgetTaskHandler(widgetTaskHandler)` solo en Android, sin cargar la librería en iOS/web (archivo `.android.ts` o import condicional)
- [ ] 2.4 [mobile] Previews provisorias en `assets/widget-preview/tasks.png` y `habits.png` (se reemplazan por capturas reales en 8.6)
- [ ] 2.5 [mobile] Agregar Jest con `jest-expo` (versión de SDK 57), `@types/jest`, script `"test": "jest"` y mock oficial de AsyncStorage; config limitada a `src/**/__tests__`

## 3. Mobile — Lógica compartida y API

- [ ] 3.1 [mobile] `src/api/endpoints.ts`: `fetchWidgetsToday()` con `tz_offset_minutes`, timeout de 10 s; tipos `WidgetsToday` en `src/types`
- [ ] 3.2 [mobile] `src/api/client.ts`: `queued(label, { silent: true })` que encola sin `notifyQueued` (sin toast); mantener el comportamiento actual por defecto
- [ ] 3.3 [mobile] `src/lib/habitToggle.ts`: `habitCheckinDelta(done, todayValue)` puro y `applyHabitDoneToday(goalId, done, knownTodayValue)` sin SWR (design D6); `setHabitDoneToday` de `src/hooks/useGoals.ts` pasa a usarla + `refreshHabitData()` sin cambiar su comportamiento
- [ ] 3.4 [mobile] `src/widgets/logic.ts` (puro): `visibleRowCount(heightDp)`, `shouldFetch(snapshot, now, reason)`, `widgetViewState(snapshot, now)` (ok / offline / otro día / sin sesión / vacío), `applyTaskDone`, `applyHabitDone`, `toCountsOnly`, `resolvePrivacyMode(stored, appLockEnabled)`, `formatAgo(fetchedAt, now)` ("hace 25 min")
- [ ] 3.5 [mobile] `src/widgets/data.ts`: snapshot `cancen_widget_snapshot_v1` en AsyncStorage (leer/escribir/borrar con try/catch), `fetchSnapshot(reason)` con promesa única en vuelo, manejo de sin sesión / refresh rechazado / sin red / 5xx (design D5), modo conteos, `completedLocally` y `pending`, limpieza al cambiar de día
- [ ] 3.6 [mobile] `src/widgets/refresh.ts`: `refreshWidgets(names?)` con debounce de 2 s usando `requestWidgetUpdate`, `clearWidgetSnapshot()`, marca `cancen_widget_dirty_at`; no-op fuera de Android

## 4. Mobile — Widgets y task handler

- [ ] 4.1 [mobile] `src/widgets/theme.ts`: tokens Stitch claro/oscuro para widgets y elección de variante según `themeStore` (forzado → una variante; sistema → `{ light, dark }`)
- [ ] 4.2 [mobile] `src/widgets/TasksTodayWidget.tsx`: encabezado con contador y ↻, filas con círculo (`TASK_SET_DONE` con estado deseado), chip "Vencida", tachado + punto pendiente, "+N más", vacío "Nada para hoy", leyenda de estado, variante "Solo conteos", estado "Iniciá sesión en Can_cen"; sin hooks; `accessibilityLabel` en filas
- [ ] 4.3 [mobile] `src/widgets/HabitsTodayWidget.tsx`: encabezado "{done}/{total}" y ↻, chips con `habitEmoji()` y color, `HABIT_SET_DONE` con estado deseado para `binary`, `OPEN_URI cancen://widget/habitos` para `metric` con "valor/meta unidad", variantes de conteos y sin sesión
- [ ] 4.4 [mobile] `src/widgets/taskHandler.tsx`: `loadServerUrlOverride()`, despacho de `WIDGET_ADDED/UPDATE/RESIZED/CLICK/DELETED`, render optimista → escritura (`updateTask` de endpoints con `silent`, `applyHabitDoneToday`) → fetch → render final, guarda por ítem en vuelo, `REFRESH`, marca `dirty_at` tras escribir, captura de cualquier error con estado neutro

## 5. Mobile — Integración con la app

- [ ] 5.1 [mobile] `src/hooks/useTasks.ts` y `src/hooks/useGoals.ts`: llamar `refreshWidgets()` tras `addTask`, `updateTask`, `deleteTask`, `addGoal`, `editGoal`, `removeGoal`, `setHabitDoneToday`, `logHabitToday`
- [ ] 5.2 [mobile] `src/store/authStore.ts`: `clearWidgetSnapshot()` + `refreshWidgets()` en `logout` y `changeServer`; `refreshWidgets()` tras login exitoso (email y Google)
- [ ] 5.3 [mobile] `App.tsx`: listener de `AppState` — al pasar a `active`, si `cancen_widget_dirty_at` es posterior al último foco, `scopedMutate` de `tasks`, `goals` y `habit-records` y borrar la marca; al pasar a `background`, `refreshWidgets()` si hubo cambios
- [ ] 5.4 [mobile] Navegación: `linking` en `NavigationContainer` con `prefixes: ['cancen://']`, `filter` que solo acepte `cancen://widget/...` y rutas `widget/tareas → TasksTab/TasksHome`, `widget/habitos → HabitsTab/HabitsHome`; confirmar que el login con Google (expo-auth-session) sigue funcionando
- [ ] 5.5 [mobile] `src/screens/SettingsScreen.tsx`: sección "Widgets de la pantalla de inicio" con "Contenido de los widgets" (Completo / Solo conteos, guardado en AsyncStorage `cancen_widget_privacy`), texto explicando el default con bloqueo, y `refreshWidgets()` al cambiar; solo visible en Android
- [ ] 5.6 [mobile] Punto de integración con `app-bloqueo-y-bienvenida`: `src/widgets/appLock.ts` con `isAppLockEnabled()` que devuelve `false` hasta que ese change exponga su función (dejar comentario de la dependencia)

## 6. Tests — Backend

- [ ] 6.1 `backend/tests/test_widgets_today.py`: incluye tareas de hoy y vencidas (`pending` e `in_progress`), excluye futuras, completadas y sin fecha; orden vencidas → prioridad; `task_limit` recorta `items` pero no `total`/`overdue`/`due_today`
- [ ] 6.2 Borde de zona horaria: 00:30 UTC con `tz_offset_minutes=-180` sigue siendo el día anterior (usar el mismo mecanismo de fecha controlada que los tests de focus/inversiones)
- [ ] 6.3 Hábitos: `done_today`/`today_value` solo con registros del día local, suma de varios registros en métricos, excluye `savings` y `progress`, orden `created_at DESC`, `done`/`total` correctos, `habit_limit`
- [ ] 6.4 401 sin sesión y 422 con `tz_offset_minutes=900`, `task_limit=0`, `task_limit=21`, `habit_limit=21`
- [ ] 6.5 Aislamiento: caso en `backend/tests/test_tenant_isolation.py` (o en el archivo nuevo) donde las tareas/hábitos/registros de otro usuario no aparecen ni cuentan
- [ ] 6.6 Regresión: correr la suite completa `cd backend && python -m pytest -q` (sin tablas nuevas: `OWNED_TABLES` y export/borrado de cuenta no cambian)

## 7. Tests — Mobile (unitarios, Jest)

- [ ] 7.1 [mobile] `src/lib/__tests__/habitToggle.test.ts`: `habitCheckinDelta` para (true,0)=+1, (true,1)=sin cambio, (false,3)=−3, (false,0)=sin cambio; `applyHabitDoneToday` con lectura fallida usa el valor conocido (endpoints mockeados) y nunca manda dos +1 para el mismo estado deseado
- [ ] 7.2 [mobile] `src/widgets/__tests__/logic.test.ts`: `visibleRowCount` por alturas, tope 8; `shouldFetch` (click siempre, periódico reutiliza < 60 s del mismo día, otro día siempre); `widgetViewState` para offline del día, offline de otro día, sin sesión y vacío; `applyTaskDone` (tachar y deshacer, `completedLocally`), `applyHabitDone` (actualiza `done`/`today_value` y el contador); `toCountsOnly` no conserva títulos; `resolvePrivacyMode` (elección explícita gana, default según bloqueo); `formatAgo`
- [ ] 7.3 [mobile] `src/widgets/__tests__/data.test.ts`: con AsyncStorage mockeado, un snapshot de ayer se descarta al leer; logout (`clearWidgetSnapshot`) borra la key; dos `fetchSnapshot` simultáneos hacen un solo pedido
- [ ] 7.4 [mobile] `npx tsc --noEmit` sin errores nuevos y `npm test` en verde

## 8. Verificación contra backend real (no mock) en dispositivo

- [ ] 8.1 Levantar el backend real con datos de prueba (tareas vencidas, de hoy, de mañana, sin fecha; hábitos binarios y métricos) y probar `GET /api/v1/widgets/today` con el token de un usuario y con `tz_offset_minutes=-180`
- [ ] 8.2 [mobile] Build EAS perfil `lan` con la librería; instalar en un Android real y agregar los dos widgets desde el selector (Pixel Launcher u otro AOSP y, si hay, Samsung One UI): tamaños por defecto, redimensionar y ver que no se recorta
- [ ] 8.3 [mobile] Con la app cerrada (deslizada de recientes): marcar/desmarcar un hábito y completar/deshacer una tarea desde el widget; confirmar en el backend que no hay registros duplicados con doble toque rápido; abrir la app y ver los cambios en Inicio, Tareas y Hábitos
- [ ] 8.4 [mobile] Token vencido: forzar vencimiento del access token (o esperar) con la app en segundo plano y tocar ↻; la sesión sigue viva en la app (sin "sesión cerrada" por rotación duplicada). Revocar la sesión desde la web → el widget muestra "Iniciá sesión en Can_cen"
- [ ] 8.5 [mobile] Modo avión: el widget muestra "Sin conexión · hace X"; completar una tarea sin red queda pendiente y se sincroniza al volver la señal; cambio de día sin red no muestra datos de ayer
- [ ] 8.6 [mobile] Temas claro/oscuro (sistema y forzado desde la app), modo "Solo conteos", deep links desde el encabezado y desde un hábito métrico, login con Google sigue funcionando; capturar las previews reales para `assets/widget-preview/`
- [ ] 8.7 [mobile] Logout: ambos widgets pasan a "Iniciá sesión en Can_cen"; login con otra cuenta no muestra datos de la anterior
- [ ] 8.8 [mobile] Medir el tamaño del APK `preview` antes y después de la librería y anotarlo (README del repo mobile, sección widgets) junto con la nota de que todos los perfiles de EAS necesitan build nuevo
- [ ] 8.9 [mobile] Medir el tiempo de la tarea headless con la app muerta (cold start); si supera ~3 s, mover el handler a un entry liviano que no importe `App` (design, Risks)
