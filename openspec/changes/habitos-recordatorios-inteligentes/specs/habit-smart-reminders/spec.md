## ADDED Requirements

### Requirement: Pending habit definition
The system SHALL consider a habit pending on a user's local date when all of the following hold: the goal belongs to that user, its `goal_type` is `binary` or `metric`, its `reminder_enabled` is true, its `start_date` is null or not after the local date, its `end_date` is null or not before the local date, and the sum of `value` of that user's habit records for that goal with `record_date` equal to the local date is less than or equal to 0. The system SHALL NOT use `is_completed` to decide whether a habit is done today. Goals of type `progress` or `savings` SHALL never be pending.

#### Scenario: Binary habit without a record today
- **WHEN** a binary habit has no habit record for the local date
- **THEN** it SHALL be pending

#### Scenario: Binary habit marked today
- **WHEN** a binary habit has a record with value 1 for the local date
- **THEN** it SHALL NOT be pending

#### Scenario: Metric habit with zero value
- **WHEN** a metric habit has only records summing 0 for the local date
- **THEN** it SHALL be pending

#### Scenario: Metric habit with a partial value
- **WHEN** a metric habit with a daily target of 2 has records summing 0.5 for the local date
- **THEN** it SHALL NOT be pending

#### Scenario: Binary habit completed in the past
- **WHEN** a binary habit has `is_completed = true` because of earlier check-ins but no record for the local date
- **THEN** it SHALL be pending

#### Scenario: Outside the habit date range
- **WHEN** a habit has `start_date` after the local date or `end_date` before the local date
- **THEN** it SHALL NOT be pending

#### Scenario: Habit excluded from reminders
- **WHEN** a habit has `reminder_enabled = false`
- **THEN** it SHALL NOT be pending for reminders

#### Scenario: Progress goals ignored
- **WHEN** a user has a `progress` goal without records today
- **THEN** it SHALL NOT be included in any habit reminder

### Requirement: Smart reminder delivery
For every user whose habit reminder settings have `enabled = true`, the system SHALL evaluate each reminder slot (the general time, plus every distinct per-habit time) once per local date, and SHALL send a remote push through the existing push infrastructure and Android channel `recordatorios` only when at least one habit assigned to that slot is pending at evaluation time. The push data SHALL be `{type: "habit_reminder", local_date, goal_ids}` where `goal_ids` lists the pending habits included.

#### Scenario: Habit missing at reminder time
- **WHEN** the general time is 20:00, the user's offset is −180, "Tomar agua" has no record for 2026-10-25 and the scheduler runs at 2026-10-25 23:00 UTC
- **THEN** the user's devices SHALL receive one push whose body is "Todavía no marcaste «Tomar agua» hoy."

#### Scenario: Everything already marked
- **WHEN** every habit assigned to the 20:00 slot has a record with value > 0 for the local date
- **THEN** no push SHALL be sent for that slot and the slot SHALL be recorded with status `nothing`

#### Scenario: Master switch off
- **WHEN** the user's habit reminder settings have `enabled = false` or do not exist
- **THEN** no habit reminder SHALL be sent to that user

#### Scenario: Per-habit time
- **WHEN** "Leer" has its own time 22:30 and the general time is 20:00
- **THEN** "Leer" SHALL only be evaluated in the 22:30 slot and not in the 20:00 slot

#### Scenario: User without push devices
- **WHEN** a pending habit is due but the user has no registered push token
- **THEN** no push SHALL be attempted, no error SHALL be raised and the slot SHALL be recorded with status `no_devices`

### Requirement: User local time for habit reminders
The system SHALL compute the user's local time and local date from `habit_reminder_settings.timezone_offset_minutes` (minutes east of UTC), using −180 when it is null. The local date SHALL be the date compared against `habit_records.record_date`.

#### Scenario: Argentina offset
- **WHEN** the offset is −180 and the general time is 20:00
- **THEN** the slot SHALL be due at 23:00 UTC

#### Scenario: Record on the local date near midnight UTC
- **WHEN** the offset is −180, the slot is 22:30, the scheduler runs at 2026-10-26 01:30 UTC and the habit has a record dated 2026-10-25
- **THEN** the habit SHALL NOT be pending and no push SHALL be sent

#### Scenario: Positive offset
- **WHEN** the offset is 60 and the general time is 20:00
- **THEN** the slot SHALL be due at 19:00 UTC

#### Scenario: Missing offset
- **WHEN** the offset is null
- **THEN** the slot SHALL be evaluated in UTC−3

### Requirement: Grouping and daily cap
The system SHALL send a single push per slot containing all pending habits of that slot. With one pending habit the title SHALL be "{emoji} Can_cen" and the body "Todavía no marcaste «{título}» hoy."; with two or more the title SHALL be "✅ Te faltan {n} hábitos hoy" and the body SHALL list the habit names joined in Spanish ("Agua, Leer y Correr"), showing at most four names followed by "y {k} más". The emoji SHALL be the habit `icon` when it contains a non-ASCII character and "✅" otherwise; names SHALL be truncated to 40 characters. The system SHALL NOT send more habit reminder pushes per user and local date than `daily_cap`; slots beyond the cap SHALL be recorded with status `capped`.

#### Scenario: Three pending habits at the same time
- **WHEN** "Agua", "Leer" and "Correr" are pending in the 20:00 slot
- **THEN** exactly one push SHALL be sent with title "✅ Te faltan 3 hábitos hoy" and body "Agua, Leer y Correr"

#### Scenario: Six pending habits
- **WHEN** six habits are pending in the same slot
- **THEN** the body SHALL list the first four names followed by "y 2 más"

#### Scenario: Different times produce different pushes
- **WHEN** one habit is pending at 08:00 and another at 20:00 and the cap is 3
- **THEN** two pushes SHALL be sent, one per slot

#### Scenario: Daily cap reached
- **WHEN** the cap is 2 and the user has pending habits in the 08:00, 13:00 and 20:00 slots
- **THEN** pushes SHALL be sent for 08:00 and 13:00 only, and the 20:00 slot SHALL be recorded as `capped`

#### Scenario: Web icon name
- **WHEN** a pending habit has icon `fa-bullseye`
- **THEN** the single-habit title SHALL use "✅"

### Requirement: Streak at risk wording
When `streak_alerts` is true and a pending habit has a streak of at least 3 consecutive days with a positive daily total ending the day before the local date, the system SHALL highlight it in the same push, without sending an extra notification: for a single pending habit the body SHALL be "🔥 Llevás {n} días seguidos con «{título}». ¡No la cortes hoy!"; for several pending habits the body SHALL append " · 🔥 «{título}» lleva {n} días seguidos" for the habit with the longest streak.

#### Scenario: Single habit with a 12-day streak
- **WHEN** "Leer" is the only pending habit and has records on each of the previous 12 local days
- **THEN** the body SHALL be "🔥 Llevás 12 días seguidos con «Leer». ¡No la cortes hoy!"

#### Scenario: Short streak
- **WHEN** the pending habit has records only on the previous 2 days
- **THEN** the body SHALL be the plain "Todavía no marcaste «{título}» hoy."

#### Scenario: Streak alerts disabled
- **WHEN** `streak_alerts` is false
- **THEN** the push SHALL use the plain wording regardless of streaks

#### Scenario: No extra push for streaks
- **WHEN** a pending habit has a streak at risk
- **THEN** the number of pushes sent that day SHALL be the same as without the streak

### Requirement: Exactly-once evaluation per user, date and slot
The system SHALL evaluate each (user, local date, slot) at most once and send at most one push for it, even with several gunicorn workers each running the scheduler, repeated cycles, process restarts or Redis being unavailable. It SHALL deduplicate with an in-process set, a Redis `SET NX` claim on `habit-reminder:{user_id}:{local_date}:{slot}` with 36 h TTL (skipped when Redis is not configured or unreachable), and a row in `habit_reminder_dispatches` unique on (`user_id`, `local_date`, `slot`) inserted before sending; the push SHALL only be sent by the process whose insert succeeded. If the insert fails for a reason other than the unique conflict, the system SHALL release the in-process and Redis claims so a later cycle within the window can retry.

#### Scenario: Two workers in the same cycle
- **WHEN** two scheduler instances evaluate the same due slot concurrently
- **THEN** exactly one push SHALL be sent

#### Scenario: Repeated cycles within the window
- **WHEN** the scheduler runs every minute from 20:00 to 20:59 local with pending habits
- **THEN** exactly one push SHALL be sent for the 20:00 slot

#### Scenario: Restart without Redis
- **WHEN** the slot was already sent, the process restarts and Redis is not configured
- **THEN** the dispatch row SHALL prevent sending it again

#### Scenario: Database error while marking
- **WHEN** inserting the dispatch row fails because the database is momentarily unavailable
- **THEN** no push SHALL be sent in that cycle and the slot SHALL be retried in the next cycle within the window

### Requirement: Catch-up window after downtime
The system SHALL treat a slot at local time T as due only while the local time is at or after T and before the earlier of T + 60 minutes and the end of the local day. A slot not evaluated within its window SHALL NOT be sent later. When more than one slot of the same user is due in the same cycle, the system SHALL send a single push with the union of their pending habits, recording the first slot as `sent` and the others as `merged`.

#### Scenario: Server back within the window
- **WHEN** the server was down at 20:00 local and the first cycle runs at 20:40 local with pending habits
- **THEN** the 20:00 push SHALL be sent in that cycle

#### Scenario: Server back after the window
- **WHEN** the first cycle after downtime runs at 21:05 local for a 20:00 slot
- **THEN** no push SHALL be sent for that slot

#### Scenario: Local day changed
- **WHEN** the slot is 23:30 and the first cycle after downtime runs at 00:10 local of the next day
- **THEN** no push SHALL be sent for the previous day's slot

#### Scenario: Not before the time
- **WHEN** the scheduler runs at 19:59 local for a 20:00 slot
- **THEN** the slot SHALL NOT be evaluated yet

#### Scenario: Two slots due after downtime
- **WHEN** the server comes back at 20:20 local and the 20:00 and 20:15 slots both have pending habits
- **THEN** one push SHALL be sent listing the pending habits of both slots

### Requirement: Scheduler resilience and retention
The habit reminder scheduler SHALL run as a background task started in the application lifespan, aligned to the start of each minute, and cancelled on shutdown. A failure while processing one user or contacting Expo SHALL be logged and SHALL NOT stop the loop nor prevent other users from being processed. The system SHALL delete `habit_reminder_dispatches` rows whose `local_date` is more than 30 days old.

#### Scenario: Expo unavailable
- **WHEN** the push provider fails while sending a habit reminder
- **THEN** the error SHALL be logged and the scheduler SHALL continue with the next user and the next cycle

#### Scenario: Old dispatch rows pruned
- **WHEN** the scheduler runs and there are dispatch rows older than 30 days
- **THEN** those rows SHALL be deleted

### Requirement: Opening Habits from a habit reminder
The mobile app SHALL navigate to the Hábitos tab (`HabitsTab` › `HabitsHome`) when the user taps a notification whose data `type` is `habit_reminder`, both when the app is running and when it is launched from the notification.

#### Scenario: Tap on the notification
- **WHEN** the user taps "Te faltan 3 hábitos hoy"
- **THEN** the app SHALL open the Hábitos tab

#### Scenario: Cold start from the notification
- **WHEN** the app is closed and is launched by tapping a habit reminder
- **THEN** the app SHALL open the Hábitos tab once the session is ready
