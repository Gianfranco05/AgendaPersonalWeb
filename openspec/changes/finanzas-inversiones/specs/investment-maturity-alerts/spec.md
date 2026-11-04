## ADDED Requirements

### Requirement: Maturity push notifications
The system SHALL send a remote push notification, through the existing push infrastructure and Android channel `recordatorios`, for every investment with `status = "active"`, `notify_maturity = true` and a `maturity_date`: one on the day before the maturity ("Vence mañana: {name}") and one on the maturity day ("Vence hoy: {name}"), both at or after 09:00 in the user's local time and before 22:00 local. The notification data SHALL be `{type: "investment_maturity", investment_id}`. For fixed terms the body SHALL include the amount at maturity formatted in es-AR with its currency.

#### Scenario: Day-before notice at 9:00 local
- **WHEN** an active fixed term matures on 2026-10-20, its `timezone_offset_minutes` is −180 and the scheduler runs at 2026-10-19 12:00 UTC (09:00 local)
- **THEN** the user's devices SHALL receive "Vence mañana: {name}" with the amount at maturity in the body

#### Scenario: Maturity-day notice
- **WHEN** the scheduler runs on the maturity date at 09:00 local
- **THEN** the user's devices SHALL receive "Vence hoy: {name}"

#### Scenario: Not before 9:00 local
- **WHEN** the scheduler runs on the day before maturity at 08:59 local
- **THEN** no notification SHALL be sent yet

#### Scenario: Catch-up after downtime within the window
- **WHEN** the server was down at 09:00 local and the first scheduler cycle runs at 11:30 local on the maturity day
- **THEN** the maturity-day notice SHALL be sent in that cycle

#### Scenario: Not after 22:00 local
- **WHEN** the first scheduler cycle of the day runs at 22:00 local or later
- **THEN** no notice for that day SHALL be sent

#### Scenario: Disabled, closed or without maturity
- **WHEN** an investment has `notify_maturity = false`, `status = "closed"` or no `maturity_date`
- **THEN** no maturity notification SHALL be sent for it

#### Scenario: User without push tokens
- **WHEN** the owner has no registered push token
- **THEN** the scheduler SHALL skip sending without error

### Requirement: User local date for maturity alerts
The system SHALL determine the user's local time for maturity alerts from the investment's `timezone_offset_minutes` (minutes east of UTC), which clients SHALL send on every create and update. When it is null the system SHALL use −180 (Argentina).

#### Scenario: Offset sent by the client
- **WHEN** a client creates an investment with `timezone_offset_minutes = 60`
- **THEN** its notices SHALL be evaluated at 09:00 of UTC+1

#### Scenario: Missing offset falls back to Argentina
- **WHEN** an investment has `timezone_offset_minutes = null`
- **THEN** its notices SHALL be evaluated at 09:00 of UTC−3

### Requirement: Exactly one notice per investment, kind and maturity date
The system SHALL send each notice (day-before and maturity-day) at most once per investment and maturity date, even with several gunicorn workers each running the scheduler, repeated cycles within the window, process restarts, or Redis being unavailable. It SHALL deduplicate with an in-process set, a Redis `SET NX` claim on `investment-maturity:{id}:{kind}:{maturity_date}` with 36 h TTL (skipped when Redis is not configured or unreachable), and a persistent atomic conditional update of `eve_notice_for` / `day_notice_for` to the maturity date, sending only when that update affects exactly one row. Changing `maturity_date` SHALL re-enable both notices for the new date.

#### Scenario: Two workers in the same cycle
- **WHEN** two scheduler instances evaluate the same due notice concurrently
- **THEN** exactly one push SHALL be sent

#### Scenario: Repeated cycles within the window
- **WHEN** the scheduler runs every minute from 09:00 to 21:59 local on the maturity day
- **THEN** exactly one maturity-day push SHALL be sent

#### Scenario: Restart without Redis
- **WHEN** the notice was already sent, the process restarts and Redis is not configured
- **THEN** the persistent marker SHALL prevent sending it again

#### Scenario: Maturity date changed after a notice
- **WHEN** a user moves the maturity date of an investment whose notices were already sent
- **THEN** the notices SHALL be sent again for the new maturity date

### Requirement: Scheduler resilience
The maturity scheduler SHALL run as a background task started in the application lifespan and cancelled on shutdown. A failure while processing one investment or while contacting Expo SHALL be logged and SHALL NOT stop the loop nor prevent other investments from being processed.

#### Scenario: Expo unavailable
- **WHEN** the push provider fails while sending a maturity notice
- **THEN** the error SHALL be logged and the scheduler SHALL continue with the next investment and the next cycle

### Requirement: Opening the app from a maturity notification
The mobile app SHALL navigate to the Inversiones screen when the user taps a notification whose data `type` is `investment_maturity`, both when the app is running and when it is launched from the notification.

#### Scenario: Tap on the notification
- **WHEN** the user taps "Vence hoy: Plazo fijo Galicia"
- **THEN** the app SHALL open Finanzas › Inversiones
