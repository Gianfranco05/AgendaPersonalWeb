## ADDED Requirements

### Requirement: Today summary endpoint for widgets
The backend SHALL expose `GET /api/v1/widgets/today`, authenticated with the current user, returning in a single response the user's tasks for today and their habits with today's status. It SHALL accept `tz_offset_minutes` (integer, −840..840, default 0, minutes east of UTC), `task_limit` (1..20, default 8) and `habit_limit` (1..20, default 12). The response SHALL contain `date` (the user's local date computed with `local_today(tz_offset_minutes)`), `tasks` (`items`, `due_today`, `overdue`, `total`) and `habits` (`items`, `done`, `total`). The endpoint SHALL NOT create or modify any data and SHALL NOT require new tables.

#### Scenario: Authenticated request
- **WHEN** an authenticated user calls `GET /api/v1/widgets/today?tz_offset_minutes=-180`
- **THEN** the response SHALL be 200 with `date`, `tasks` and `habits` objects

#### Scenario: Unauthenticated request
- **WHEN** the endpoint is called without a valid access token
- **THEN** the response SHALL be 401

#### Scenario: Parameters out of range
- **WHEN** `tz_offset_minutes` is 900, or `task_limit` is 0 or 21, or `habit_limit` is 21
- **THEN** the response SHALL be 422

### Requirement: Task selection for today
The endpoint SHALL include in `tasks.items` only the user's tasks whose `status` is not `completed`, whose `due_date` is not null and whose `due_date` is on or before the local `date`. Each item SHALL contain `id`, `title`, `priority`, `due_date` and `overdue` (`due_date` < `date`). Items SHALL be ordered overdue first by `due_date` ascending, then due-today tasks by priority `alta`, `media`, `baja`, then by `order` and creation time. `tasks.items` SHALL be truncated to `task_limit`, while `due_today`, `overdue` and `total` SHALL count the full selection.

#### Scenario: Due today and overdue included
- **WHEN** the user has a pending task due today, an `in_progress` task due two days ago and a pending task due tomorrow
- **THEN** `tasks.items` SHALL contain the overdue task first and then the task due today, `overdue` SHALL be 1, `due_today` SHALL be 1, `total` SHALL be 2, and the task due tomorrow SHALL NOT appear

#### Scenario: Completed and undated tasks excluded
- **WHEN** the user has a completed task due today and a pending task without `due_date`
- **THEN** neither SHALL appear in `tasks.items` nor be counted

#### Scenario: Priority order among today's tasks
- **WHEN** three pending tasks are due today with priorities `baja`, `alta` and `media`
- **THEN** `tasks.items` SHALL list them as `alta`, `media`, `baja`

#### Scenario: Limit keeps totals
- **WHEN** the user has 12 qualifying tasks and calls with `task_limit=8`
- **THEN** `tasks.items` SHALL have 8 items and `tasks.total` SHALL be 12

#### Scenario: Local date at night in Argentina
- **WHEN** the server time is 2026-10-26 00:30 UTC, `tz_offset_minutes=-180`, and a pending task is due 2026-10-26
- **THEN** `date` SHALL be 2026-10-25 and the task SHALL NOT be included

### Requirement: Habit status for today
The endpoint SHALL include in `habits.items` the user's goals with `goal_type` `binary` or `metric`, ordered by creation time descending (the same order as `GET /api/v1/goals`), truncated to `habit_limit`. Each item SHALL contain `id`, `title`, `icon`, `color`, `goal_type`, `target_value`, `unit`, `today_value` (sum of the goal's habit records dated on the local `date`) and `done_today` (`today_value` > 0). `habits.done` and `habits.total` SHALL count the full selection. Today's values SHALL be computed with a single aggregated query, not one query per habit.

#### Scenario: Binary habit done today
- **WHEN** a binary habit has a record with value 1 dated on the local `date`
- **THEN** its item SHALL have `done_today = true` and `today_value = 1`, and it SHALL count in `habits.done`

#### Scenario: Records from other days ignored
- **WHEN** a binary habit only has a record dated yesterday
- **THEN** its item SHALL have `done_today = false` and `today_value = 0`

#### Scenario: Metric habit value
- **WHEN** a metric habit with unit "L" has two records today with values 0.5 and 1
- **THEN** its item SHALL have `today_value = 1.5` and `done_today = true`

#### Scenario: Other goal types excluded
- **WHEN** the user has `savings` and `progress` goals
- **THEN** they SHALL NOT appear in `habits.items` nor be counted

### Requirement: User isolation of the widget summary
Every query of the endpoint SHALL be filtered by the authenticated user's id; tasks, goals and habit records of other users SHALL never appear or be counted.

#### Scenario: Another user's data
- **WHEN** user B has pending tasks due today and habits done today, and user A calls the endpoint
- **THEN** A's response SHALL NOT include or count any of B's tasks, habits or records
