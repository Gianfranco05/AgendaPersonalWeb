## ADDED Requirements

### Requirement: Recurring transaction templates
The system SHALL let each authenticated user create, list, read, update and delete recurring transaction templates under `/api/v1/finance/recurring`, as part of the base Finance module (no module purchase required). A template SHALL store `type` (`income` or `expense`), `name` (1–255 chars, trimmed), optional `description` and `notes`, `amount` (> 0 and ≤ 9.999.999.999,99), `currency` (default `ARS`), optional own `category_id` and own `bank_account_id`, `account_type`, `payment_method`, `merchant_name`, `merchant_category`, a frequency rule, `start_date`, optional inclusive `end_date`, `requires_confirmation` (default false), `notify` (default true) and `timezone_offset_minutes` (−840..840, minutes east of UTC). `amount` MAY be null only when `requires_confirmation` is true. Invalid input SHALL return 422 with a Spanish message, never 500.

#### Scenario: Create a monthly salary
- **WHEN** a user posts `{type: "income", name: "Sueldo", amount: 850000, frequency: "monthly", day_of_month: 5, start_date: "2026-11-01"}`
- **THEN** the API SHALL return 201 with the template, `next_occurrence_date = "2026-11-05"` and `rule_label = "Todos los meses el día 5"`

#### Scenario: Category or account of another user
- **WHEN** a user creates or updates a template with a `category_id` or `bank_account_id` that belongs to another user or does not exist
- **THEN** the API SHALL return 404 and SHALL NOT persist the template

#### Scenario: Amount out of range or invalid enum
- **WHEN** a template is posted with `amount = 10000000000`, `amount = 0`, `payment_method = "Efectivo"` or `end_date` before `start_date`
- **THEN** the API SHALL return 422

#### Scenario: Variable amount without estimate
- **WHEN** a template is posted with `requires_confirmation = true` and no `amount`
- **THEN** the API SHALL accept it, and the same payload with `requires_confirmation = false` SHALL return 422

### Requirement: Frequency rules and calendar edge cases
The system SHALL support the frequencies `daily` (every N days, N 1–365), `weekly` (every N weeks on `weekday` 0=Monday..6=Sunday, N 1–52), `monthly` (every N months on `day_of_month` 1–31, N 1–12) and `yearly` (every N years on `day_of_month`/`month_of_year`, N 1–10). The first occurrence (anchor) SHALL be the first date on or after `start_date` that matches the rule, and occurrence k SHALL be computed from the anchor (never from the previous occurrence). When `day_of_month` does not exist in a month, the occurrence SHALL fall on that month's last day. A yearly rule on February 29 SHALL fall on February 28 in non-leap years. No occurrence SHALL be produced after `end_date`.

#### Scenario: Day 31 in short months
- **WHEN** a monthly rule has `day_of_month = 31` and anchor 2027-01-31
- **THEN** its occurrences SHALL be 2027-01-31, 2027-02-28, 2027-03-31, 2027-04-30

#### Scenario: Day 30 in a leap February
- **WHEN** a monthly rule has `day_of_month = 30` and the month is February 2028
- **THEN** the occurrence SHALL be 2028-02-29

#### Scenario: Bimonthly anchored at the first match
- **WHEN** a monthly rule with `interval_count = 2` and `day_of_month = 5` starts on 2026-10-25
- **THEN** its occurrences SHALL be 2026-11-05, 2027-01-05, 2027-03-05

#### Scenario: Weekly and every N days
- **WHEN** a weekly rule with `weekday = 0` starts on Wednesday 2026-10-28 and a daily rule with `interval_count = 15` starts on 2026-10-28
- **THEN** the weekly rule SHALL first occur on Monday 2026-11-02 and the daily rule SHALL occur on 2026-10-28, 2026-11-12, 2026-11-27

#### Scenario: Yearly on February 29
- **WHEN** a yearly rule has `month_of_year = 2`, `day_of_month = 29` and anchor 2028-02-29
- **THEN** the next occurrences SHALL be 2029-02-28, 2030-02-28, 2031-02-28 and 2032-02-29

#### Scenario: End date reached
- **WHEN** the next occurrence would fall after `end_date`
- **THEN** the template SHALL have `next_occurrence_date = null` and `state = "finished"`

#### Scenario: Preview of next dates
- **WHEN** a client posts a rule to `/api/v1/finance/recurring/preview`
- **THEN** the API SHALL return the anchor and the next 5 occurrence dates computed with the same rules, without persisting anything

### Requirement: Server-side generation in the user's local date
The system SHALL generate due occurrences from a background scheduler running in the application lifespan. An occurrence is due when its date is on or before the user's local date, computed as UTC now plus the template's `timezone_offset_minutes` (or −180 when null). The scheduler SHALL only generate while the user's local time is between 09:00 and 21:59. For a template without `requires_confirmation`, generating an occurrence SHALL create a real transaction dated on the occurrence date with the template's type, amount, currency, category, payment method, merchant fields, `product_name = name`, `product_description = description`, `notes`, `is_recurring = true` and `recurring_parent_id = template id`; the account fields SHALL be copied from the linked own bank account when present (`bank_entity_name`, `account_type`, `account_last4`) or from the template's `account_type` otherwise. Creating a template, changing its rule or resuming it SHALL also generate, immediately, any occurrence already due regardless of the time window.

#### Scenario: Salary at 9:00 local
- **WHEN** a monthly template for day 5 has offset −180 and the scheduler runs at 2026-11-05 12:00 UTC (09:00 local)
- **THEN** exactly one income transaction dated 2026-11-05 SHALL be created and linked to the template

#### Scenario: Before 9:00 local
- **WHEN** the scheduler runs at 2026-11-05 11:59 UTC (08:59 local) for that template
- **THEN** no transaction SHALL be created yet

#### Scenario: Local date differs from UTC date
- **WHEN** a template due on 2026-11-05 has offset −180 and, after a downtime, the first scheduler cycle runs at 2026-11-06 01:30 UTC (2026-11-05 22:30 local)
- **THEN** no transaction SHALL be created in that cycle, and it SHALL be created at 2026-11-06 12:00 UTC dated 2026-11-05

#### Scenario: Positive offset
- **WHEN** a template due on 2026-11-05 has offset +600 and the scheduler runs at 2026-11-04 23:00 UTC (2026-11-05 09:00 local)
- **THEN** the transaction SHALL be created dated 2026-11-05

#### Scenario: Created on its due day
- **WHEN** a user creates at 07:00 local a template whose first occurrence is today
- **THEN** the transaction SHALL be created in the same request

### Requirement: Exactly-once generation
The system SHALL create at most one occurrence (transaction or pending) per template and occurrence date, even with several application workers running the scheduler concurrently, process restarts in the middle of a cycle, or no Redis available. Advancing the template's cursor, inserting the occurrence rows and creating the transactions SHALL happen in a single database transaction guarded by a compare-and-set on `next_occurrence_date` and a unique constraint on (template, occurrence date).

#### Scenario: Two concurrent workers
- **WHEN** two scheduler ticks process the same due template at the same time
- **THEN** exactly one transaction SHALL exist for that date afterwards

#### Scenario: Repeated cycles
- **WHEN** the scheduler runs every minute during the whole window of the due day
- **THEN** only one transaction SHALL exist for that date

#### Scenario: Restart without Redis
- **WHEN** the process restarts after generating an occurrence and Redis is not configured
- **THEN** the next cycles SHALL NOT generate it again

#### Scenario: Failure mid-generation
- **WHEN** creating one of the transactions fails inside the generation transaction
- **THEN** the cursor SHALL remain unchanged, no partial rows SHALL persist and the next cycle SHALL retry

#### Scenario: Deleted generated transaction is not regenerated
- **WHEN** the user deletes a transaction that was generated for 2026-11-05
- **THEN** the system SHALL NOT generate another transaction for 2026-11-05

### Requirement: Catch-up after downtime with a cap
When the scheduler finds several due occurrences for a template (for example after the server was down), it SHALL generate all occurrences dated within the last 62 days up to the local date, at most 62 per template and cycle, each with its original date, and SHALL advance the cursor past older missed occurrences without generating them. When a template is created with a past `start_date` (at most 366 days ago), past occurrences SHALL only be generated if `generate_past = true`, and the request SHALL return 422 if they exceed 120.

#### Scenario: Server down three days
- **WHEN** a daily template was not processed for 3 days and the scheduler runs inside the window
- **THEN** 4 transactions SHALL be created, dated each of the missed days and today

#### Scenario: Downtime longer than the cap
- **WHEN** a daily template has 100 overdue occurrences
- **THEN** only the occurrences of the last 62 days SHALL be generated and the cursor SHALL point to the next future occurrence

#### Scenario: Past start without backfill
- **WHEN** a monthly template is created on 2026-10-25 with `start_date = 2026-07-01` and `generate_past` omitted
- **THEN** no past transaction SHALL be created and the first occurrence SHALL be on or after 2026-10-25

#### Scenario: Past start with backfill
- **WHEN** the same template is created with `generate_past = true` and `day_of_month = 1`
- **THEN** transactions dated 2026-07-01, 2026-08-01, 2026-09-01 and 2026-10-01 SHALL be created

### Requirement: Pending occurrences for variable amounts
For a template with `requires_confirmation = true`, generating an occurrence SHALL create a `pending` occurrence instead of a transaction, with `suggested_amount` equal to the amount of the template's latest confirmed occurrence or, if none, the template amount (possibly null). Pending occurrences SHALL NOT affect balance, budgets or reports. The user SHALL be able to list pending occurrences, confirm one with an amount and optional date and notes (creating the transaction, linked to the template and to the occurrence) or skip it. Confirming or skipping SHALL be idempotent.

#### Scenario: Electricity bill pending
- **WHEN** a "Luz" template with `requires_confirmation = true` and amount 25000 becomes due
- **THEN** a pending occurrence with `suggested_amount = 25000` SHALL exist and no transaction SHALL be created

#### Scenario: Confirm with edited amount
- **WHEN** the user confirms the pending occurrence with `amount = 31250.50`
- **THEN** an expense transaction of 31.250,50 dated on the occurrence date SHALL be created, the occurrence SHALL become `confirmed` and the next pending of that template SHALL suggest 31.250,50

#### Scenario: Confirm twice
- **WHEN** the same confirmation is sent twice (offline queue retry)
- **THEN** only one transaction SHALL exist and both responses SHALL return the same occurrence

#### Scenario: Skip
- **WHEN** the user skips a pending occurrence
- **THEN** it SHALL become `skipped`, no transaction SHALL be created, and confirming it afterwards SHALL return 409

### Requirement: Pause, resume, edit and delete semantics
The system SHALL let the user pause and resume a template. A paused template SHALL NOT generate occurrences, and resuming SHALL continue from the first occurrence on or after the local date of resumption without generating the dates that fell during the pause. Updating a template SHALL NOT modify transactions or pending occurrences already generated; content changes SHALL apply from the next occurrence, and rule changes SHALL recompute the anchor as the first occurrence of the new rule on or after the latest of `start_date`, the local date and the day after the last processed occurrence. Deleting a template SHALL delete the template and its occurrences but SHALL keep its generated transactions, unlinking them (`recurring_parent_id = null`, `is_recurring` kept true). Deleting a category or bank account SHALL unlink it from the templates that reference it.

#### Scenario: Pause during a due date
- **WHEN** a monthly template for day 5 is paused on 2026-11-01 and resumed on 2026-12-10
- **THEN** no transactions SHALL be created for 2026-11-05 or 2026-12-05 and the next occurrence SHALL be 2027-01-05

#### Scenario: Edit amount keeps history
- **WHEN** a template with two generated transactions of 850.000 is updated to 900.000
- **THEN** the existing transactions SHALL keep 850.000 and the next generated one SHALL be 900.000

#### Scenario: Delete keeps transactions
- **WHEN** a user deletes a template with generated transactions
- **THEN** the transactions SHALL remain listed with `is_recurring = true` and `recurrence_id = null`, and the template and its occurrences SHALL no longer exist

#### Scenario: Deleted category
- **WHEN** a user deletes a category used by a template
- **THEN** the template SHALL remain with `category_id = null` and the deletion SHALL succeed on Postgres

### Requirement: Link between transactions and templates
Transaction responses SHALL include `recurrence_id` (the template that generated them, or null). `GET /api/v1/finance/transactions` SHALL accept an optional `recurrence_id` filter restricted to the current user's transactions. Template responses SHALL include `state` (`active`, `paused`, `finished`), `rule_label` in Spanish, `next_occurrence_date`, `pending_count` and `last_amount`, and the template detail SHALL include its latest occurrences (up to 12) and its next 3 dates.

#### Scenario: Movements of a template
- **WHEN** the client requests `/api/v1/finance/transactions?recurrence_id={id}`
- **THEN** only the non-deleted transactions generated by that template for the current user SHALL be returned

#### Scenario: Manual transactions
- **WHEN** a transaction was created manually
- **THEN** its `recurrence_id` SHALL be null and `is_recurring` SHALL be false

### Requirement: Upcoming recurring movements
The system SHALL expose `GET /api/v1/finance/recurring/upcoming?days=N` (N 1–90, default 30) listing, for the user's active templates, every occurrence between the local date and N days ahead with its date, name, type, amount, currency and whether it requires confirmation, plus totals by type and currency, without persisting anything.

#### Scenario: Next 30 days
- **WHEN** a user has a salary on day 5 and rent on day 10 and requests upcoming on 2026-10-25
- **THEN** the response SHALL list 2026-11-05 (income) and 2026-11-10 (expense) with their totals

### Requirement: Recurring data isolation and account lifecycle
Every recurring endpoint SHALL only read or modify the current user's templates and occurrences; ids belonging to another user SHALL return 404. The tables `recurring_transactions` and `recurring_occurrences` SHALL be included in the account export and fully removed by account deletion.

#### Scenario: Another user's template
- **WHEN** a user requests, updates, pauses, resumes or deletes a template of another user, or confirms or skips another user's occurrence
- **THEN** the API SHALL return 404 and nothing SHALL change

#### Scenario: Lists do not leak
- **WHEN** two users have templates and pending occurrences
- **THEN** each user's list, upcoming and pending endpoints SHALL only include their own data

#### Scenario: Export and deletion
- **WHEN** a user exports their account and later deletes it
- **THEN** the export SHALL contain their `recurring_transactions` and `recurring_occurrences` (and not other users'), and after deletion no rows of that user SHALL remain in either table
