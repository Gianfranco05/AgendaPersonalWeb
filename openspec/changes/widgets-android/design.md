## Context

- La app mobile (`C:\Proyectos\vida-personal-mobile`) es Expo SDK 57 / React Native 0.86 (New Architecture obligatoria desde RN 0.82), builds con EAS (perfiles `development` con dev client, `preview`, `lan` y `production`), `minSdk` 24. No usa Expo Go: cualquier módulo nativo nuevo pide un build nuevo.
- Entrada en `index.ts` (`registerRootComponent(App)`); `package.json#main` ya apunta a `index.ts`. `app.json` es estático y `app.config.js` lo extiende (Firebase, `expo-build-properties`).
- Sesión: access + refresh en `expo-secure-store` (`TOKEN_KEY`, `REFRESH_KEY` en `src/api/client.ts`). El interceptor de respuesta renueva con **una sola promesa en vuelo** (`refreshInFlight`) porque el backend rota el refresh y trata un refresh repetido como robo. Un rechazo 4xx del refresh borra la sesión; un error de red no.
- Escrituras offline: `queued(label)` marca el pedido; sin respuesta del server se guarda en la cola de AsyncStorage (`mutationQueue.ts`) y se muestra un toast. La cola se vacía tras cualquier respuesta exitosa.
- Tareas: `GET /api/v1/tasks` devuelve todas (sin filtro de fecha); estados `pending | in_progress | completed`; `due_date` es `Date`. Inicio (`DashboardScreen`) marca con `updateTask(id, {status: 'completed'})`.
- Hábitos: son `Goal` con `goal_type` `binary` (sí/no, racha) o `metric` (valor diario). El estado de hoy sale de `GET /goals/{id}/records?year&month` (un pedido por hábito). `setHabitDoneToday` (`src/hooks/useGoals.ts`) lee el total real de hoy y llama `PUT /goals/{id}/checkin` con `+1` solo si no hay registro, o con `-total` para desmarcar; el backend además ignora un `+` repetido en `binary` el mismo día. Ambos son módulos base (siempre activos).
- Backend: `app/core/clock.py::local_today(tz_offset_minutes)` resuelve el "hoy" del usuario; los endpoints de resumen reciben `tz_offset_minutes` (−840..840).
- El cache de SWR se persiste en AsyncStorage (`swrCache.ts`) y el logout lo borra junto con la cola. `allowBackup: false` en Android.
- No hay `linking` de React Navigation configurado, aunque el esquema `cancen` existe en `app.json`.
- El repo mobile no tiene runner de tests.

## Goals / Non-Goals

**Goals:**
- Dos widgets Android ("Tareas de hoy" y "Hábitos de hoy") que se vean y se puedan marcar sin abrir la app.
- Un solo pedido liviano por refresco, compartido por los dos widgets.
- Comportamiento sano sin conexión, con sesión vencida y al cambiar de día.
- No romper la rotación del refresh token ni la cola offline.
- Opción de privacidad coherente con el bloqueo de la app; nada de Finanzas.
- Lógica de selección y marcado cubierta por tests unitarios (backend y mobile).

**Non-Goals:**
- iOS, widgets en la pantalla de bloqueo, widgets configurables por instancia, crear ítems desde el widget, widgets de otros módulos, push silenciosas para refrescar.

## Decisions

### D1. Librería: `react-native-android-widget` (0.24.x)

Se usa `react-native-android-widget` de sAleksovski: widgets Android escritos en JSX con primitivas propias (`FlexWidget`, `TextWidget`, `ImageWidget`, `ListWidget`, `SvgWidget`), config plugin de Expo, un `widgetTaskHandler` que corre como tarea headless de JS y recibe `WIDGET_ADDED | WIDGET_UPDATE | WIDGET_RESIZED | WIDGET_DELETED | WIDGET_CLICK` con `clickAction`/`clickActionData`, `requestWidgetUpdate()` para refrescar desde la app, acciones especiales `OPEN_APP` y `OPEN_URI`, `renderWidget({ light, dark })` para temas (desde 0.19), `widgetCategory` configurable (0.23) y ejecución por WorkManager con pedidos expeditos en Android 12+ (0.21).

Verificado en npm/GitHub (octubre 2026): última versión 0.24.0 del 2026-10-22, `peerDependencies` `expo >= 54` (opcional), `react`/`react-native` `*`; desarrollada contra RN 0.83 / Expo 54, es decir sobre una versión de RN que ya solo corre con la New Architecture, así que no depende del bridge viejo. Licencia MIT, ~900 estrellas, mantenimiento activo (releases en enero, mayo, julio, agosto y octubre de 2026). Paquete de ~500 KB sin compilar.

Límites documentados que condicionan el diseño: el JSX se renderiza a imagen y en algunos launchers el tamaño informado no coincide con el real (se recorta); `updatePeriodMillis` mínimo de 30 minutos (límite de Android); `clickAction` solo desde Android 7 (nuestro `minSdk` es 24, OK); los componentes del widget no pueden usar hooks ni ser async (los datos se traen en el handler).

Alternativas descartadas:
- **`expo-widgets`** (oficial de Expo, estable desde SDK 56): solo iOS en SDK 57.
- **Jetpack Glance / `AppWidgetProvider` en Kotlin con un config plugin propio**: es la vía "nativa" recomendada por Google, pero obliga a escribir y mantener Kotlin, un módulo Expo para pasar datos (SharedPreferences/DataStore) y duplicar en Kotlin la llamada al backend y la renovación del token, que hoy vive en JS con la regla de single-flight. Queda como plan B si la librería se abandona (D13).
- Paquetes chicos de un solo propósito (p. ej. `react-native-todorant-widget`): no son generales.

### D2. Endpoint `GET /api/v1/widgets/today`

Nuevo módulo backend `app/modules/widgets/` (`schemas.py`, `service.py`, `api_routes.py`), router `prefix="/widgets"`, autenticado con `get_current_user`, sin tablas nuevas.

Parámetros: `tz_offset_minutes` (int, −840..840, default 0, mismo contrato que focus), `task_limit` (1..20, default 8), `habit_limit` (1..20, default 12).

Respuesta:

```json
{
  "date": "2026-10-25",
  "tasks": {
    "items": [{"id": "…", "title": "…", "priority": "alta", "due_date": "2026-10-23", "overdue": true}],
    "due_today": 3, "overdue": 1, "total": 4
  },
  "habits": {
    "items": [{"id": "…", "title": "Tomar agua", "icon": "💧", "color": "#2563EB",
               "goal_type": "binary", "done_today": false, "today_value": 0,
               "target_value": 1, "unit": null}],
    "done": 2, "total": 5
  }
}
```

Reglas (en `service.py`, una consulta por tabla, todo filtrado por `user_id`):
- `date = local_today(tz_offset_minutes)`.
- **Tareas**: `status != 'completed'` y `due_date IS NOT NULL` y `due_date <= date`. Orden: vencidas primero (`due_date` ascendente), después las de hoy por prioridad `alta > media > baja`, luego `order` y `created_at`. `overdue = due_date < date`. `due_today`, `overdue` y `total` cuentan sobre el conjunto completo (no sobre lo recortado por `task_limit`). Las tareas sin fecha no entran (ver Preguntas abiertas).
- **Hábitos**: `goal_type IN ('binary', 'metric')`, mismo criterio que `HabitsScreen` del celular; orden estable `created_at DESC` (igual que `GET /goals`) para que los ítems no salten al tocarlos. `today_value` = suma de `HabitRecord.value` con `record_date = date` (una consulta agregada con `GROUP BY goal_id`, no N consultas). `done_today = today_value > 0` (mismo criterio que `habitMonthStats`). `done`/`total` sobre el conjunto completo.
- `icon` se devuelve tal cual: el celular resuelve el emoji con `habitEmoji()` (los nombres Font Awesome de la web se reemplazan por uno sugerido).

Por qué un endpoint y no reutilizar los existentes: un refresco con los endpoints actuales son `GET /tasks` (todas las tareas, también las completadas) + `GET /goals` + un `GET /records` por hábito; con 10 hábitos son 12 pedidos cada 30 minutos desde segundo plano, lo que consume batería/datos, alarga la tarea headless y es lo que Play Vitals marca. Alternativa descartada: calcular en el celular con esos endpoints (más simple en backend, peor en todo lo demás).

### D3. Arquitectura en el celular (`src/widgets/`)

```
index.ts ──registerWidgetTaskHandler (solo Android)──► src/widgets/taskHandler.tsx
                                                            │
             ┌──────────────────────────────────────────────┤
             ▼                                              ▼
 src/widgets/data.ts  (fetch + snapshot)        src/widgets/TasksTodayWidget.tsx
   - fetchWidgetsToday (endpoints.ts)           src/widgets/HabitsTodayWidget.tsx
   - snapshot en AsyncStorage                   (JSX puro, sin hooks, light/dark)
             │
             ▼
 src/widgets/logic.ts  (puro, testeado): estado de vista, filas visibles,
   aplicar marcado optimista, modo conteos, "hace X min", shouldFetch
 src/widgets/refresh.ts: refreshWidgets() con debounce, no-op fuera de Android
```

- `index.ts`: después de `registerRootComponent(App)`, `if (Platform.OS === 'android') registerWidgetTaskHandler(widgetTaskHandler)`. En web/iOS no se importa la librería (import dinámico o archivo `.android.ts`).
- El handler corre en el mismo runtime de JS que la app cuando la app está viva (Android reutiliza el `ReactHost` de la aplicación para las tareas headless), así que comparte módulos: `apiClient`, `refreshInFlight` y la cola. Con el proceso muerto, arranca el bundle sin montar la UI.
- Al empezar cada ejecución el handler llama `loadServerUrlOverride()` (idempotente) para respetar el server elegido en los APK de prueba, igual que `App.tsx`.

### D4. Snapshot compartido y cuándo se pide al server

Un único snapshot en AsyncStorage (`cancen_widget_snapshot_v1`) sirve a los dos widgets:

```ts
{ v: 1, fetchedAt: number, date: 'YYYY-MM-DD', mode: 'full' | 'counts',
  data: WidgetsToday | CountsOnly,
  completedLocally: { id: string; title: string }[],   // tareas tachadas desde el widget hoy
  pending: { kind: 'task' | 'habit'; id: string }[],    // escrituras encoladas sin red
  lastError?: 'offline' | 'signed-out' | 'server' }
```

`shouldFetch(snapshot, now, reason)` (puro): siempre para `click`, `refresh-button` y `app-changed`; para `periodic`/`added`/`resized` solo si el snapshot tiene más de 60 s o es de otro día. Así, cuando Android dispara `WIDGET_UPDATE` para las dos instancias casi juntas, se hace un solo pedido. Un pedido en vuelo se comparte (promesa única en el módulo).

El snapshot guarda títulos de tareas y hábitos, igual que el cache de SWR que ya se persiste en AsyncStorage; con `allowBackup: false` no sale del teléfono. En modo conteos se guarda solo `CountsOnly` (D9).

### D5. Sesión, token vencido y errores

- El pedido sale por `apiClient`, así que hereda el header, la renovación single-flight y la regla de no borrar la sesión por un corte de red.
- **Sin token** o **refresh rechazado** (la sesión ya quedó borrada por el interceptor): se borra el snapshot y se renderiza "Iniciá sesión en Can_cen" (tocar abre la app).
- **Sin respuesta / timeout / 5xx**: se mantiene el último snapshot y se marca `lastError = 'offline'` o `'server'`; el widget muestra el contenido con la leyenda "Sin conexión · hace 25 min" (o "No se pudo actualizar"). El timeout del widget es de 10 s (más corto que los 15 s de la app) para no agotar la ventana de la tarea.
- **Snapshot de otro día** sin poder actualizar: no se muestran las tareas/hábitos de ayer como si fueran de hoy; se muestra "Sin conexión · tocá ↻ para actualizar" con los contadores en blanco.
- Antes del primer desbloqueo tras reiniciar, Keystore y AsyncStorage (almacenamiento cifrado por credencial) pueden no estar disponibles: cualquier excepción del storage se trata como error transitorio y se renderiza el estado neutro "Can_cen" sin borrar nada.
- **Restricción para `app-bloqueo-y-bienvenida`**: los tokens NO deben guardarse con `requireAuthentication: true` de `expo-secure-store` (eso exigiría huella para leerlos y el widget, igual que cualquier pedido en segundo plano, dejaría de funcionar). El bloqueo tiene que ser una compuerta de UI de la app.

### D6. Marcar desde el widget

Las acciones viajan en `clickActionData` con el **estado deseado**, no "toggle": dos toques sobre la misma imagen vieja mandan el mismo pedido y el resultado es idempotente.

- **Tarea**: `clickAction = 'TASK_SET_DONE'`, `{ taskId, done: true }` → `PATCH /tasks/{id}` `{status: 'completed'}`. La fila queda tachada (se agrega a `completedLocally`) con su círculo lleno; tocarla de nuevo manda `{ done: false }` → `{status: 'pending'}` y vuelve a la lista. `completedLocally` se vacía al cambiar el día. Es el "deshacer" ante un toque accidental.
- **Hábito `binary`**: `clickAction = 'HABIT_SET_DONE'`, `{ goalId, done, knownTodayValue }` → `applyHabitDoneToday(goalId, done, knownTodayValue)`.
- **Hábito `metric`**: `OPEN_URI` a `cancen://widget/habitos`.
- Flujo en el handler: (1) aplicar el cambio optimista al snapshot (`applyTaskDone` / `applyHabitDone`, puros) y `renderWidget` inmediatamente; (2) hacer la escritura; (3) `fetch` + render final (y refrescar el otro widget si cambió algo que lo afecta: no aplica hoy, pero `refreshWidgets` acepta nombres).
- Guarda por ítem en memoria del módulo: si ya hay una escritura en vuelo para ese `id`, el segundo toque solo re-renderiza.

**Extracción de la lógica de hábitos** (`src/lib/habitToggle.ts`):
- `habitCheckinDelta(done, todayValue): number | null` (pura): `+1` si `done && todayValue <= 0`; `-todayValue` si `!done && todayValue > 0`; `null` si no hay nada que hacer.
- `applyHabitDoneToday(goalId, done, knownTodayValue)`: lee los registros del mes (si falla, usa el valor conocido), calcula el delta y llama `checkInGoal` de `endpoints.ts`. Sin SWR.
- `setHabitDoneToday` de `useGoals.ts` pasa a ser `applyHabitDoneToday` + `refreshHabitData()` + `refreshWidgets()`. Mismo comportamiento para la app; el widget llama solo a la primera.

### D7. Sin conexión desde el widget

Las escrituras del widget usan la misma cola offline, con una opción nueva `queued(label, { silent: true })` en `client.ts` que no muestra el `ToastAndroid` (desde segundo plano un toast no tiene contexto y Android 11+ los restringe). Cuando la escritura queda encolada (respuesta sintética 202) el cambio optimista se mantiene y el ítem se marca en `pending` con un punto "pendiente de sincronizar". La cola se reenvía con la próxima respuesta exitosa de cualquier pedido (incluido el próximo refresco del widget, que pasa por el mismo interceptor) y al abrir la app. Los pedidos son idempotentes (D6), así que un reenvío no duplica.

Caveat: `applyHabitDoneToday` sin red usa `knownTodayValue` del snapshot; es el mismo compromiso que ya hace la app.

### D8. Refresco

| Disparador | Cómo |
|---|---|
| Periódico | `updatePeriodMillis: 1800000` (30 min, mínimo de Android; Doze lo puede demorar) |
| Botón ↻ del encabezado | `clickAction = 'REFRESH'` |
| Después de marcar | dentro del handler (D6) |
| La app cambia tareas/hábitos | `refreshWidgets()` desde `addTask`, `updateTask`, `deleteTask`, `setHabitDoneToday`, `logHabitToday`, `addGoal`/`editGoal`/`removeGoal` (debounce 2 s) |
| Login / logout / cambio de server | `authStore` llama `clearWidgetSnapshot()` (logout/cambio de server) y `refreshWidgets()` |
| App a segundo plano | listener de `AppState` en `App.tsx` → `refreshWidgets()` si hubo cambios desde el último refresco |
| Cambios hechos en la web | se ven en el próximo periódico, al tocar ↻ o al abrir la app |

`refreshWidgets()` llama `requestWidgetUpdate({ widgetName, renderWidget })` para cada widget; el render usa el snapshot después de `fetch` (con `reason = 'app-changed'`). Fuera de Android es no-op.

**App ← widget**: cuando el widget escribe, guarda `cancen_widget_dirty_at`. Al volver la app a primer plano (`AppState` `active`), si la marca es posterior al último foco, se revalidan las keys `tasks`, `goals` y `habit-records` con `scopedMutate` y se borra la marca. Si la app está viva en segundo plano también sirve: el siguiente foco revalida.

### D9. Privacidad y bloqueo de la app

Preferencia **local del dispositivo** (AsyncStorage `cancen_widget_privacy`: `'full' | 'counts'`), en Ajustes → "Widgets de la pantalla de inicio" → "Contenido de los widgets":
- **Completo**: títulos, emojis y acciones.
- **Solo conteos**: "Tareas de hoy · 3 para hoy · 1 vencida" y "Hábitos de hoy · 2/5"; sin títulos ni acciones de marcado; tocar cualquier parte abre la app (que, si está bloqueada, pide huella/PIN). El snapshot guarda solo los contadores.

`resolvePrivacyMode(stored, appLockEnabled)` (pura): si el usuario eligió explícitamente, se respeta; si no eligió, `counts` cuando el bloqueo está activo y `full` si no. Al activar el bloqueo, la pantalla del change hermano debe llamar `refreshWidgets()` (dependencia). `appLockEnabled` se lee por una función que expone `app-bloqueo-y-bienvenida`; hasta que exista, devuelve `false`.

Además: `widgetCategory` = solo pantalla de inicio (no keyguard); sin widget de Finanzas; los deep links de los widgets solo navegan, nunca escriben (D10).

### D10. Abrir la app en la pantalla correcta

Se agrega `linking` a `NavigationContainer` con `prefixes: ['cancen://']`, un `filter` que solo acepta `cancen://widget/...` (para no interferir con la redirección OAuth de `expo-auth-session`, que usa el mismo esquema) y la config `widget/tareas → TasksTab/TasksHome`, `widget/habitos → HabitsTab/HabitsHome`. Los widgets usan `OPEN_URI` con esos URIs. Sin sesión, la app cae en Login como siempre. Los deep links son públicos (cualquier app puede abrirlos), por eso solo navegan a listas.

### D11. Diseño visual, tamaños y temas

- **Tareas de hoy**: `targetCellWidth 4 × targetCellHeight 2`, `minWidth 250dp × minHeight 110dp`, redimensionable en ambos ejes. Encabezado "Tareas de hoy" + contador + ↻. Filas de 40 dp: círculo (toca = completar), título en una línea con elipsis, chip "Vencida" en rojo o punto de prioridad. Cantidad de filas = `visibleRowCount(heightDp)` (pura) con tope 8; si sobran, "+N más" (abre la app). Vacío: "Nada para hoy 🎉".
- **Hábitos de hoy**: `4 × 2`, mismo mínimo. Grilla de "chips" (emoji + nombre corto), 2 columnas en 4 celdas de ancho y 1 en 2–3 celdas; hechos con fondo del color del hábito y ✓; métricos muestran "1,5/2 L". Encabezado "Hábitos de hoy · 2/5".
- **Temas**: `renderWidget({ light, dark })` con los tokens Stitch (`surface #ffffff / #0b1326`, `on-surface #0f172a / #dae2fd`, `primary #0058be / #adc6ff`, `outline #e2e8f0 / #424754`). Si el usuario forzó claro u oscuro en la app (`themeStore`), se renderiza solo esa variante; con "sistema" se pasan ambas y Android elige.
- **Fuente**: la del sistema (Roboto). Sumar Inter con la opción `fonts` del plugin agrega ~300 KB por peso al APK (Preguntas abiertas).
- `previewImage` por widget en `assets/widget-preview/` (PNG ≤ 100 KB, capturas reales hechas en la verificación).
- Textos en español con voseo, `accessibilityLabel` en las filas (la librería soporta TalkBack desde 0.20).

### D12. Configuración y build

`app.config.js` agrega el plugin al final de `plugins` (no se toca `app.json`):

```js
['react-native-android-widget', {
  widgets: [
    { name: 'TasksToday', label: 'Tareas de hoy', description: 'Tus tareas de hoy y vencidas',
      minWidth: '250dp', minHeight: '110dp', targetCellWidth: 4, targetCellHeight: 2,
      resizeMode: 'horizontal|vertical', updatePeriodMillis: 1800000,
      widgetCategory: 'home_screen', previewImage: './assets/widget-preview/tasks.png' },
    { name: 'HabitsToday', label: 'Hábitos de hoy', /* … */ },
  ],
}]
```

(Los nombres exactos de `resizeMode`/`widgetCategory` se confirman contra la API de la versión instalada.)

- Requiere build nativo nuevo en **todos** los perfiles de EAS, incluido el dev client de `development`; sin eso `registerWidgetTaskHandler` no tiene módulo nativo.
- Tamaño: la librería suma código nativo chico, `androidx.work` (WorkManager) si no estaba ya por otra dependencia, y las dos previews. Estimación +0,5 a +1,5 MB por ABI; se mide comparando el APK `preview` antes/después (tarea de verificación) y se documenta en el README.
- iOS: el plugin solo toca el proyecto Android; nada cambia en iOS.

### D13. Tests

- Backend (`backend/tests/test_widgets_today.py`): selección, orden, límites y totales, borde de zona horaria, hábitos y su valor de hoy, aislamiento por usuario, 401 sin sesión, 422 con `tz_offset_minutes`/límites fuera de rango.
- Mobile: se agrega Jest con `jest-expo` (alineado a SDK 57) y `npm test`, limitado a módulos puros (`src/widgets/logic.ts`, `src/lib/habitToggle.ts`) con el mock oficial de AsyncStorage. No se testean componentes del widget (son JSX renderizado a imagen por la librería): se verifican en dispositivo.

## Dependencias

- **`app-bloqueo-y-bienvenida`**: (a) expone `isAppLockEnabled()` y llama `refreshWidgets()` al activar/desactivar el bloqueo; (b) NO protege los tokens con `requireAuthentication` del Keystore (D5); (c) al abrir la app desde un widget con el bloqueo activo, la app pide desbloqueo antes de mostrar la pantalla del deep link. Si ese change se implementa después, este funciona igual con el default `full` y la opción manual.
- **`habitos-recordatorios-inteligentes`**: si cambia cómo se marca un hábito, debe hacerlo en `applyHabitDoneToday` (función compartida) para que el widget no quede con lógica vieja.
- **`buscador-global`** y los de finanzas: sin relación (Finanzas no va en widgets).
- Este change no depende de ningún otro para funcionar.

## Risks / Trade-offs

- [Launchers que informan mal el tamaño → el bitmap se recorta] → márgenes internos generosos, filas calculadas con margen de seguridad, verificación en Pixel Launcher y One UI (Samsung).
- [OEMs agresivos con la batería (Xiaomi, Samsung) demoran o cortan WorkManager] → leyenda "hace X min" siempre visible, botón ↻, refresco al usar la app.
- [Rotación del refresh entre app y widget] → mismo runtime de JS y `refreshInFlight` compartido (D3); verificación en dispositivo con access token vencido y la app abierta en segundo plano.
- [Keystore/AsyncStorage no disponibles antes del primer desbloqueo] → error transitorio, estado neutro, no se borra la sesión (D5).
- [Datos visibles para cualquiera que mire el teléfono desbloqueado] → modo "Solo conteos", default automático con bloqueo, sin Finanzas, sin keyguard.
- [Librería de un solo mantenedor] → todo aislado en `src/widgets/` y un endpoint agnóstico; plan B Glance nativo reutilizando el endpoint y la lógica de selección del backend.
- [Cambios hechos en la web tardan hasta 30 min (o más con Doze)] → aceptado; ↻ manual. Push silenciosa queda fuera de alcance.
- [Cold start del bundle completo en la tarea headless (importa `App`)] → Hermes con bytecode; si en la verificación supera ~3 s, mover el handler a un entry liviano que no importe `App`.
- [Tocar por error completa una tarea] → queda tachada con deshacer hasta fin del día (D6).

## Migration Plan

1. Deploy del backend con `GET /api/v1/widgets/today` (aditivo, sin migración). Builds viejos de la app no lo usan.
2. Build nuevo de EAS (`lan` para probar; después `preview`/`production`) con la librería y el plugin.
3. Rollback: quitar el plugin y la dependencia y hacer otro build; los widgets ya puestos quedan como "No se puede cargar el widget" hasta que el usuario los saque. El endpoint puede quedar.

## Open Questions

1. **Privacidad por defecto con bloqueo activo**: ¿"Solo conteos" automático? Recomendación: sí, con la opción de volver a "Completo" en Ajustes.
2. **Tareas sin fecha**: ¿mostrarlas en el widget? Recomendación: no (el widget es "de hoy"); alternativa futura: sección "Sin fecha" al final si sobra espacio.
3. **Tareas `in_progress`**: ¿cuentan como pendientes? Recomendación: sí, igual que el Inicio de la app.
4. **Tocar una tarea**: completar directo con tachado y deshacer, ¿o pedir confirmación abriendo la app? Recomendación: directo (un widget que obliga a abrir la app pierde el sentido).
5. **Hábitos métricos**: ¿solo ver y abrir la app, o un "+1" en el widget? Recomendación: solo ver y abrir en esta etapa.
6. **Fuente**: ¿Roboto del sistema o Inter (+~300 KB por peso)? Recomendación: sistema.
7. **Cuántos hábitos**: con 4×2 entran ~8 chips; ¿alcanza o se ofrece elegir cuáles mostrar? Recomendación: mostrar los primeros por orden de la app y dejar la elección para un change posterior.
