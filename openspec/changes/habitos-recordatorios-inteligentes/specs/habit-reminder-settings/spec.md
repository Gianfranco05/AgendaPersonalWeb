## ADDED Requirements

### Requirement: Read habit reminder settings
The system SHALL expose `GET /api/v1/habit-reminders/settings` for the authenticated user returning `enabled`, `time` ("HH:MM"), `daily_cap`, `streak_alerts`, `timezone_offset_minutes` and `has_push_devices` (true when the user has at least one registered push token). When the user has no settings row the system SHALL return the defaults (`enabled = true`, `time = "20:00"`, `daily_cap = 3`, `streak_alerts = true`, `timezone_offset_minutes = null`) without creating a row.

#### Scenario: Defaults for a new user
- **WHEN** a user who never configured habit reminders requests the settings
- **THEN** the response SHALL contain the defaults with `enabled: true` and no `habit_reminder_settings` row SHALL be created

#### Scenario: Push device flag
- **WHEN** the user has one registered push token
- **THEN** `has_push_devices` SHALL be true

#### Scenario: Without authentication
- **WHEN** the endpoint is called without a valid session
- **THEN** the system SHALL respond 401

### Requirement: Update habit reminder settings
The system SHALL expose `PUT /api/v1/habit-reminders/settings` accepting a partial body with `enabled`, `time`, `daily_cap`, `streak_alerts` and `timezone_offset_minutes`, creating the user's row on first use and returning the same shape as the GET. It SHALL reject with 422 and a Spanish message a `time` not matching `HH:MM` (00:00–23:59), a `daily_cap` outside 1–5 and a `timezone_offset_minutes` outside −840..840. An explicit null on a non-nullable field SHALL be ignored.

#### Scenario: Enable with a custom time
- **WHEN** the user sends `{enabled: true, time: "21:15", timezone_offset_minutes: -180}`
- **THEN** the settings SHALL be stored and returned with those values

#### Scenario: Invalid time
- **WHEN** the user sends `time: "24:00"`
- **THEN** the system SHALL respond 422

#### Scenario: Cap out of range
- **WHEN** the user sends `daily_cap: 6`
- **THEN** the system SHALL respond 422

#### Scenario: Partial update keeps other fields
- **WHEN** the user sends only `{streak_alerts: false}`
- **THEN** `enabled`, `time`, `daily_cap` and the offset SHALL keep their previous values

### Requirement: Per-habit reminder fields
Goal create, update and responses under `/api/v1/goals` SHALL include `reminder_enabled` (boolean, default true) and `reminder_time` ("HH:MM" or null, default null meaning "use the general time"). An explicit `reminder_time: null` on update SHALL clear the habit's own time. An invalid `reminder_time` SHALL be rejected with 422. These fields SHALL only affect reminders for `binary` and `metric` goals. Existing clients that do not send them SHALL keep working.

#### Scenario: Create a habit with its own time
- **WHEN** the user creates a binary habit with `reminder_time: "07:30"`
- **THEN** the response SHALL include `reminder_enabled: true` and `reminder_time: "07:30"`

#### Scenario: Clear the own time
- **WHEN** the user updates a habit with `reminder_time: null`
- **THEN** the habit SHALL use the general time

#### Scenario: Exclude a habit
- **WHEN** the user updates a habit with `reminder_enabled: false`
- **THEN** the response SHALL include `reminder_enabled: false` and the habit SHALL not appear in reminders

#### Scenario: Old client
- **WHEN** a client creates a goal without the new fields
- **THEN** the goal SHALL be created with `reminder_enabled: true` and `reminder_time: null`

### Requirement: Today's reminder overview
The system SHALL expose `GET /api/v1/habit-reminders/today` with optional `tz_offset_minutes` (−840..840) returning the local date, whether reminders are enabled, `pending_count`, and the list of slots for that day, each with its `time`, `status` (`upcoming`, `due`, or the recorded `sent`, `merged`, `nothing`, `capped`, `no_devices`) and the pending habits assigned to it (`id`, `title`, `icon`, `streak`). It SHALL use the same pending logic as the scheduler. When `tz_offset_minutes` is missing the stored offset SHALL be used, falling back to −180.

#### Scenario: Pending habits before the time
- **WHEN** at 18:00 local "Agua" and "Leer" are pending for the 20:00 slot
- **THEN** the response SHALL list the 20:00 slot with status `upcoming` and both habits

#### Scenario: Slot already sent
- **WHEN** the 20:00 slot was sent and the user requests the overview at 21:00 local
- **THEN** the slot SHALL have status `sent`

#### Scenario: All marked
- **WHEN** every habit has a positive record today
- **THEN** `pending_count` SHALL be 0

### Requirement: Isolation and account data
All habit reminder settings, overview and dispatch data SHALL be scoped to the authenticated user; a user SHALL never see, modify or be notified about another user's habits or records. The tables `habit_reminder_settings` and `habit_reminder_dispatches` SHALL be listed in `OWNED_TABLES`, so they are included in the account export and deleted with the account. The new routes SHALL require authentication.

#### Scenario: Records of another user do not count
- **WHEN** user B has a record dated today for a goal id that belongs to user A
- **THEN** user A's habit SHALL still be pending

#### Scenario: Settings are per user
- **WHEN** user A enables habit reminders
- **THEN** user B's settings SHALL remain at their own values

#### Scenario: Updating another user's habit
- **WHEN** user B sends `PUT /api/v1/goals/{id}` with reminder fields for user A's habit
- **THEN** the system SHALL respond 404 and A's habit SHALL not change

#### Scenario: Account export and deletion
- **WHEN** a user with habit reminder settings and dispatch rows exports or deletes the account
- **THEN** the export SHALL include both tables and the deletion SHALL remove their rows

### Requirement: Mobile habit reminder configuration
The mobile app SHALL offer, in Ajustes › Recordatorios, a "Hábitos sin marcar" section with the master switch, the general time, the daily cap (1–5), the streak toggle and today's overview; and in the habit form a "Recordarme si no lo marqué" switch with "Hora general" or a custom time. Habit reminders SHALL be enabled by default. The Hábitos screen SHALL offer a one-tap switch to turn the reminders off and on. When reminders are enabled, the user has at least one habit and the device has no registered push token, the Hábitos screen SHALL show a dismissible banner that requests notification permission in context and registers the token. Enabling reminders from settings SHALL also request notification permission and register the device push token; when the device cannot receive server push the app SHALL say so instead of promising the reminder. On app start and return to foreground with reminders enabled, the app SHALL re-register the push token silently and update `timezone_offset_minutes` if the device offset changed.

#### Scenario: Grant permission from the banner
- **WHEN** the user taps "Permitir" on the Hábitos banner and grants notification permission
- **THEN** the device push token SHALL be registered and the device offset SHALL be saved

#### Scenario: Turn off with one tap
- **WHEN** the user taps the reminders switch on the Hábitos screen
- **THEN** the settings SHALL be saved with `enabled: false`

#### Scenario: Device without server push
- **WHEN** the user enables reminders on a device where push registration fails
- **THEN** the settings SHALL be saved and the app SHALL show that this device cannot receive the reminders

#### Scenario: Timezone changed
- **WHEN** the app opens with reminders enabled and the device offset differs from the stored one
- **THEN** the app SHALL update the stored offset

#### Scenario: Banner dismissed
- **WHEN** the user taps "Ahora no"
- **THEN** the banner SHALL not be shown again on that device for that user

### Requirement: Web habit reminder configuration
The web app SHALL offer in Configuración a habit reminders section with the same controls and today's overview (and a one-tap switch to turn the reminders off in the Hábitos page), stating that notifications are delivered to the Android app and warning when `has_push_devices` is false; and in the goal form, for `binary` and `metric` types only, a "Recordarme si no lo marqué" checkbox and an optional time input (empty = general time). Forms SHALL validate with Zod without `z.coerce`. Mock mode SHALL support the new endpoints.

#### Scenario: Save settings on the web
- **WHEN** the user enables habit reminders at 21:00 in Configuración
- **THEN** the web SHALL send `PUT /api/v1/habit-reminders/settings` with `enabled: true`, `time: "21:00"` and the browser offset

#### Scenario: Progress goal form
- **WHEN** the user opens the goal form for a `progress` goal
- **THEN** the reminder fields SHALL NOT be shown

#### Scenario: No devices warning
- **WHEN** the settings report `has_push_devices: false`
- **THEN** the section SHALL warn that the reminders need the Android app with the session started
