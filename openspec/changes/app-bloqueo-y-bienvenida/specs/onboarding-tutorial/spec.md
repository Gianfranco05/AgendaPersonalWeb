## ADDED Requirements

### Requirement: Onboarding progress stored per user
The system SHALL store the onboarding version seen by each user in `user_preferences.onboarding_version_seen` (integer, not null, default 0). `GET /api/v1/settings` SHALL return `onboarding_version_seen`. `PUT /api/v1/settings` SHALL accept `onboarding_version_seen` between 0 and 1000, SHALL ignore an explicit null, and SHALL store the maximum of the current and the received value so it never decreases. The value SHALL only be readable and writable by its owner.

#### Scenario: Default for a new user
- **WHEN** a newly registered user calls `GET /api/v1/settings`
- **THEN** the response SHALL include `onboarding_version_seen: 0`

#### Scenario: Marking the tutorial as seen
- **WHEN** the user sends `PUT /api/v1/settings` with `{"onboarding_version_seen": 1}`
- **THEN** subsequent `GET /api/v1/settings` responses SHALL return `onboarding_version_seen: 1`

#### Scenario: Never decreases
- **WHEN** the stored value is 2 and a client sends `{"onboarding_version_seen": 1}`
- **THEN** the stored value SHALL remain 2

#### Scenario: Invalid value
- **WHEN** a client sends `{"onboarding_version_seen": -1}` or `{"onboarding_version_seen": 5000}`
- **THEN** the API SHALL respond 422

#### Scenario: Null ignored
- **WHEN** a client sends `{"onboarding_version_seen": null}`
- **THEN** the stored value SHALL not change and the API SHALL respond 200

#### Scenario: Isolation between users
- **WHEN** user A marks the tutorial as seen
- **THEN** user B's `onboarding_version_seen` SHALL be unchanged

#### Scenario: Account export
- **WHEN** a user exports their account data
- **THEN** the exported `user_preferences` SHALL include `onboarding_version_seen`

### Requirement: Show the tutorial once across devices
The web and mobile clients SHALL show the welcome tutorial after login (and after the terms gate and any other mandatory gate) when `max(onboarding_version_seen, local fallback for that user) < CURRENT_ONBOARDING_VERSION` (initially 1). The clients MUST NOT show it while the settings are still unknown, nor when the settings response lacks `onboarding_version_seen`. Finishing or skipping SHALL first record the version locally for that user and then send `PUT /api/v1/settings` with `onboarding_version_seen = CURRENT_ONBOARDING_VERSION`; on mobile this write SHALL go through the offline queue.

#### Scenario: First login on web
- **WHEN** a user with `onboarding_version_seen = 0` enters the web app
- **THEN** the tutorial SHALL be shown over the Dashboard

#### Scenario: Seen on web, then mobile
- **WHEN** the user finished the tutorial on the web and later signs in on the mobile app
- **THEN** the mobile app SHALL NOT show the tutorial

#### Scenario: Skipped offline on mobile
- **WHEN** the user skips the tutorial on mobile without network and reopens the app before the queue syncs
- **THEN** the tutorial SHALL NOT be shown again, and the queued update SHALL be sent when the network returns

#### Scenario: Settings not yet known
- **WHEN** the app has no cached settings and `/settings` has not answered yet
- **THEN** the tutorial SHALL NOT be shown until the settings are known

#### Scenario: Old backend
- **WHEN** the settings response does not include `onboarding_version_seen`
- **THEN** the tutorial SHALL NOT be shown automatically

#### Scenario: New tutorial version
- **WHEN** `CURRENT_ONBOARDING_VERSION` is raised to 2 and the user had seen version 1
- **THEN** the tutorial SHALL be shown once more

### Requirement: Tutorial content and navigation
The tutorial SHALL have 4 steps: (1) Inicio — on mobile the "+" quick-create button, on web the Dashboard and side menu; (2) Hábitos and metas; (3) Finanzas e Inversiones (on mobile also mentioning the app lock in Ajustes › Seguridad); (4) Tareas, Notas, Eventos and the user's space (web: plantillas in Módulos; mobile: Ajustes › Personalizá tu espacio). It SHALL offer "Saltar" on steps 1–3, "Anterior" on steps 2–4, "Siguiente" and "Empezar" on the last step, and announce "Paso N de 4" to assistive technologies. On mobile, horizontal swipe SHALL also change steps and the Android back button SHALL go to the previous step.

#### Scenario: Skip
- **WHEN** the user taps "Saltar" on step 1
- **THEN** the tutorial SHALL close and be recorded as seen

#### Scenario: Finish
- **WHEN** the user reaches step 4 and taps "Empezar"
- **THEN** the tutorial SHALL close, be recorded as seen, and the user SHALL land on Inicio/Dashboard

#### Scenario: Back navigation
- **WHEN** the user is on step 3 and taps "Anterior"
- **THEN** step 2 SHALL be shown

#### Scenario: Web keyboard and focus
- **WHEN** the tutorial is open on the web
- **THEN** focus SHALL be trapped inside the dialog and pressing Escape SHALL act as "Saltar"

### Requirement: No purchase wording on mobile
The mobile tutorial MUST NOT contain purchase-related text, prices, currency amounts or store references (e.g. "comprar", "compra", "precio", "pago", "tienda", "Pro", "$"), consistent with the hidden mobile store (`IN_APP_PURCHASES_ENABLED=false`).

#### Scenario: Content check
- **WHEN** the mobile tutorial steps are rendered
- **THEN** none of their titles or texts SHALL match the forbidden purchase terms

### Requirement: Replay from settings
Web Settings and mobile Ajustes SHALL offer "Ver tutorial", which opens the same steps in replay mode. Replay mode MUST NOT write to the server or the local fallback, and closing it SHALL return to Settings.

#### Scenario: Replay on mobile
- **WHEN** the user taps Ajustes › Ayuda › "Ver tutorial" and then "Saltar"
- **THEN** the app SHALL return to Ajustes without sending any settings update

#### Scenario: Replay on web
- **WHEN** the user clicks "Ver tutorial" in Configuración
- **THEN** the tutorial dialog SHALL open at step 1 regardless of `onboarding_version_seen`

### Requirement: Tutorial below the app lock
On mobile, when the app lock is enabled and the app is locked, the lock screen SHALL be shown above the tutorial, and the tutorial SHALL be visible only after unlocking.

#### Scenario: Locked during the tutorial
- **WHEN** the user is on step 2, the app goes to the background longer than the lock timeout and returns
- **THEN** the lock screen SHALL be shown and, after unlocking, step 2 SHALL be visible again
