## ADDED Requirements

### Requirement: Home screen widgets on Android
The mobile app SHALL provide two Android home screen widgets, "Tareas de hoy" (`TasksToday`) and "Hábitos de hoy" (`HabitsToday`), declared through the `react-native-android-widget` Expo config plugin in `app.config.js`, available only for the home screen (not the lock screen), resizable, with a default size of 4×2 cells, a picker preview image and a periodic update interval of 30 minutes. The widget task handler SHALL be registered in `index.ts` only on Android; on iOS and web the widget code SHALL NOT be loaded and widget refresh calls SHALL be no-ops. No widget SHALL show finance data.

#### Scenario: Adding a widget
- **WHEN** the user adds "Tareas de hoy" from the launcher's widget picker while signed in
- **THEN** the widget SHALL render the current tasks for today fetched from `GET /api/v1/widgets/today`

#### Scenario: Not on iOS or web
- **WHEN** the app runs on iOS or with `expo start --web`
- **THEN** no widget handler SHALL be registered and calling `refreshWidgets()` SHALL do nothing and not throw

### Requirement: Tasks widget content and actions
In full mode the "Tareas de hoy" widget SHALL show a header with the title, the pending count and a refresh button, and one row per task from the snapshot, as many as fit in the widget height (maximum 8), each with a check circle, the title on one line and a "Vencida" mark when `overdue`. When more tasks exist than shown it SHALL show "+N más". With no tasks it SHALL show "Nada para hoy". Tapping a task's circle SHALL mark it completed (`PATCH /api/v1/tasks/{id}` with `status: completed`) without opening the app, and the row SHALL stay visible struck through until the local day changes; tapping a struck-through row SHALL reopen it (`status: pending`). Tapping the header title or "+N más" SHALL open the app on the Tasks screen through `cancen://widget/tareas`.

#### Scenario: Complete a task from the widget
- **WHEN** the user taps the circle of a pending task in the widget
- **THEN** the row SHALL immediately render struck through, the task SHALL be updated to `completed` in the backend, and the app SHALL not open

#### Scenario: Undo an accidental completion
- **WHEN** the user taps a row the widget shows as struck through
- **THEN** the task SHALL be set back to `pending` and the row SHALL render as pending

#### Scenario: Rows limited by height
- **WHEN** the widget has room for 3 rows and the snapshot has 5 tasks
- **THEN** it SHALL show the first 3 tasks and "+2 más"

#### Scenario: Open the app on Tasks
- **WHEN** the user taps the widget header
- **THEN** the app SHALL open on the Tasks tab

### Requirement: Habits widget content and actions
In full mode the "Hábitos de hoy" widget SHALL show a header with the title, "{done}/{total}" and a refresh button, and one item per habit with its emoji resolved with `habitEmoji()` and its color; done habits SHALL be visually marked. Tapping a binary habit SHALL set it done or not done for today, sending the desired state (not a toggle) and applying it with the shared idempotent function `applyHabitDoneToday`, which is also used by the app's `setHabitDoneToday`. Metric habits SHALL show today's value and unit and tapping them SHALL open the app on the Habits screen through `cancen://widget/habitos`.

#### Scenario: Mark a habit done
- **WHEN** the user taps a binary habit not done today
- **THEN** the item SHALL render as done and the backend SHALL receive one check-in of +1 for today's local date

#### Scenario: Double tap does not duplicate
- **WHEN** the user taps the same not-done habit twice before the widget re-renders
- **THEN** both taps SHALL request the state "done", and the habit SHALL end with exactly one record for today

#### Scenario: Unmark a habit
- **WHEN** the user taps a binary habit already done today with a today total of 1
- **THEN** the backend SHALL receive a check-in of −1 for today and the item SHALL render as not done

#### Scenario: Metric habit opens the app
- **WHEN** the user taps a metric habit
- **THEN** the app SHALL open on the Habits tab and no value SHALL be written

### Requirement: Shared habit toggle logic
The logic that decides the check-in for "done today" SHALL live in a pure function `habitCheckinDelta(done, todayValue)` returning +1 when `done` and `todayValue` ≤ 0, −`todayValue` when not `done` and `todayValue` > 0, and no change otherwise. `applyHabitDoneToday(goalId, done, knownTodayValue)` SHALL read today's real total from the habit records before deciding, falling back to `knownTodayValue` when the read fails.

#### Scenario: Already done
- **WHEN** `habitCheckinDelta(true, 1)` is evaluated
- **THEN** it SHALL return no change

#### Scenario: Undo exact total
- **WHEN** `habitCheckinDelta(false, 3)` is evaluated
- **THEN** it SHALL return −3

### Requirement: Background data fetching with the stored session
The widget task handler SHALL fetch data without the app UI open, using the app's `apiClient` (token from `expo-secure-store`, single-flight refresh on 401, server URL override loaded with `loadServerUrlOverride()`), with a 10-second timeout. Both widgets SHALL share one snapshot stored in AsyncStorage; periodic, added and resized updates SHALL reuse a snapshot younger than 60 seconds from the same local day instead of fetching again, and concurrent fetches SHALL share one in-flight request. Clicks, the refresh button and changes made in the app SHALL always fetch.

#### Scenario: Expired access token
- **WHEN** the access token is expired and the refresh token is valid
- **THEN** the handler SHALL renew the session through the existing single-flight refresh and render fresh data

#### Scenario: Two widgets updated together
- **WHEN** Android triggers the periodic update for both widgets within a few seconds
- **THEN** only one request to `GET /api/v1/widgets/today` SHALL be made

#### Scenario: Signed out or refresh rejected
- **WHEN** there is no stored session or the backend rejects the refresh token
- **THEN** the widget snapshot SHALL be deleted and both widgets SHALL show "Iniciá sesión en Can_cen", opening the app when tapped

### Requirement: Offline and stale states
When the request fails without a server response, times out or returns 5xx, the widgets SHALL keep showing the last snapshot of the same local day with the caption "Sin conexión · hace {X}" (or "No se pudo actualizar"). A snapshot from a previous local day SHALL NOT be shown as today's data: the widget SHALL show an offline message prompting to refresh, without yesterday's items. Storage errors (for example before the first unlock after a reboot) SHALL render a neutral state without deleting the session.

#### Scenario: No connection
- **WHEN** the periodic update runs without network and the snapshot is 25 minutes old and from today
- **THEN** the widget SHALL show the snapshot items and "Sin conexión · hace 25 min"

#### Scenario: Day changed without connection
- **WHEN** the snapshot is from yesterday and the update fails for lack of network
- **THEN** the widget SHALL NOT list yesterday's tasks or habits and SHALL show an offline message with the refresh button

### Requirement: Offline writes from the widget
When a write from the widget gets no server response, it SHALL be stored in the existing offline mutation queue without showing a toast (`queued(label, { silent: true })`), the optimistic change SHALL remain in the snapshot and the item SHALL show a pending-sync mark. Queued writes SHALL be resent by the existing queue flush after any later successful response, including the widget's next successful refresh.

#### Scenario: Complete a task offline
- **WHEN** the user completes a task from the widget without network
- **THEN** the row SHALL stay struck through with a pending mark, the PATCH SHALL be in the offline queue, and after the connection returns the task SHALL be `completed` in the backend exactly once

### Requirement: Widget refresh triggers
The widgets SHALL refresh: periodically every 30 minutes (subject to Android power limits), when the refresh button is tapped, after every action from the widget, and when the app creates, updates or deletes tasks or habits, marks or logs a habit, signs in, signs out, changes server or goes to background after such changes (debounced to 2 seconds). Signing out or changing server SHALL delete the widget snapshot before refreshing. When the widget writes data, the app SHALL revalidate its tasks, goals and habit records caches the next time it becomes active.

#### Scenario: Change in the app updates the widget
- **WHEN** the user completes a task inside the app
- **THEN** the "Tareas de hoy" widget SHALL be refreshed within a few seconds without waiting for the periodic update

#### Scenario: Logout clears the widget
- **WHEN** the user signs out in the app
- **THEN** the snapshot SHALL be deleted and both widgets SHALL show "Iniciá sesión en Can_cen"

#### Scenario: App reflects widget changes
- **WHEN** the user marks a habit from the widget and then opens the app
- **THEN** the Habits screen and Home SHALL show the habit as done after revalidation

### Requirement: Widget privacy mode
The app SHALL offer in Settings a device-local option "Contenido de los widgets" with values "Completo" and "Solo conteos". In counts mode the widgets SHALL show only counts ("3 para hoy · 1 vencida", "2/5"), no titles, emojis or per-item actions, tapping anywhere SHALL open the app, and the stored snapshot SHALL contain only counts. When the user has not chosen a value, the mode SHALL be "Solo conteos" if the app lock from `app-bloqueo-y-bienvenida` is enabled and "Completo" otherwise. Changing the option SHALL refresh the widgets.

#### Scenario: Counts only
- **WHEN** the privacy mode is "Solo conteos" and the user has 3 tasks for today
- **THEN** the tasks widget SHALL show "3 para hoy" without any task title and tapping it SHALL open the app

#### Scenario: Default with app lock
- **WHEN** the app lock is enabled and the user never chose a widget privacy value
- **THEN** the widgets SHALL render in counts mode

#### Scenario: Explicit choice wins
- **WHEN** the app lock is enabled and the user chose "Completo"
- **THEN** the widgets SHALL render in full mode

### Requirement: Widget deep links only navigate
The app SHALL handle `cancen://widget/tareas` and `cancen://widget/habitos` by opening the Tasks and Habits tabs, and SHALL ignore other `cancen://` paths in this linking configuration so the OAuth redirect keeps working. Deep links SHALL never create, update or delete data. Without a session the app SHALL show the login screen.

#### Scenario: Deep link without session
- **WHEN** the user is signed out and opens `cancen://widget/tareas`
- **THEN** the app SHALL show the login screen and SHALL NOT perform any write

### Requirement: Light and dark themes
The widgets SHALL render with the Stitch light and dark tokens. When the app theme is set to light or dark, the widgets SHALL use that theme; when it follows the system, both variants SHALL be provided so Android picks the one matching the system.

#### Scenario: System dark mode
- **WHEN** the app theme follows the system and the phone is in dark mode
- **THEN** the widgets SHALL render with the dark surface `#0b1326` and text `#dae2fd`
