## ADDED Requirements

### Requirement: User can register an investment
The system SHALL allow an authenticated user to create an investment via `POST /api/v1/finance/investments` with: `asset_type` (one of `stock`, `fixed_term`, `crypto`, `bond`, `fund`, `fx`, `real_estate`, `vehicle`, `other`), `name`, optional `ticker`, `currency` (one of `ARS`, `USD`, `USDT`, `EUR`), optional `quantity`, `invested_amount`, optional `current_value`, optional `interest_rate_tna`, optional `start_date` and `maturity_date`, optional `institution`, optional `notes`, `notify_maturity` (default true) and optional `timezone_offset_minutes`. The investment SHALL belong to the authenticated user, start with `status = "active"` and `price_source = "manual"`. This feature SHALL be available to every user without purchasing any plantilla.

#### Scenario: Create a stock position
- **WHEN** an authenticated user posts `{asset_type: "stock", name: "Apple CEDEAR", ticker: "aapl", currency: "ARS", quantity: 10, invested_amount: 150000, current_value: 172500}`
- **THEN** the system SHALL respond 201 with the investment, `ticker` normalized to `"AAPL"`, `status = "active"`, `effective_value = 172500.00`, `gain = 22500.00`, `gain_pct = 15.00` and `value_source = "manual"`

#### Scenario: Create without authentication
- **WHEN** an unauthenticated client posts to `/api/v1/finance/investments`
- **THEN** the system SHALL respond 401 and SHALL NOT create anything

#### Scenario: Available without a paid plantilla
- **WHEN** a user who has not purchased any paid plantilla creates an investment
- **THEN** the system SHALL accept the request (no module entitlement check)

### Requirement: Investment input validation and bounds
The system SHALL reject invalid input with 422 (never 500), including on PostgreSQL: unknown `asset_type` or `currency`; empty `name` or longer than 120 characters; `ticker` not matching `^[A-Z0-9.\-]{1,20}$` after upper-casing; `invested_amount` or `current_value` negative or greater than 9.999.999.999,99; `quantity` negative, greater than 999.999.999.999 or with more than 8 decimals; `interest_rate_tna` negative, greater than 999,9999 or with more than 4 decimals; `maturity_date` earlier than `start_date`; dates outside 1970-01-01..2100-12-31; `institution` longer than 120; `notes` longer than 2000; `timezone_offset_minutes` outside −840..840; `price_source` other than `manual`.

#### Scenario: Amount above the finance limit
- **WHEN** a user creates an investment with `invested_amount = 10000000000`
- **THEN** the system SHALL respond 422

#### Scenario: Negative current value
- **WHEN** a user creates an investment with `current_value = -1`
- **THEN** the system SHALL respond 422

#### Scenario: Maturity before start
- **WHEN** a user creates an investment with `start_date = 2026-10-10` and `maturity_date = 2026-10-01`
- **THEN** the system SHALL respond 422

#### Scenario: Unsupported currency
- **WHEN** a user creates an investment with `currency = "BTC"`
- **THEN** the system SHALL respond 422

#### Scenario: Crypto quantity with 8 decimals
- **WHEN** a user creates a `crypto` investment with `quantity = 0.00012345`
- **THEN** the system SHALL accept it and return `quantity` with its 8 decimals intact

### Requirement: Fixed-term deposit rules and automatic calculation
For `asset_type = "fixed_term"` the system SHALL require `start_date`, `maturity_date` strictly after `start_date`, `interest_rate_tna` and `currency` in `ARS` or `USD`. The system SHALL compute, using simple interest on a 365-day base with `Decimal` arithmetic and half-up rounding to 2 decimals: `term_days = maturity_date − start_date`, `interest_total = P × TNA/100 × term_days/365`, `amount_at_maturity = P + interest_total`, `accrued_interest = P × TNA/100 × elapsed/365` where `elapsed` is the days from `start_date` to the user's today clamped to `[0, term_days]`, and an informative `tea_pct = ((1 + TNA/100 × term_days/365)^(365/term_days) − 1) × 100`. These values SHALL be returned in a `fixed_term` object of the investment response.

#### Scenario: Interest and amount at maturity
- **WHEN** a user creates a fixed term with `invested_amount = 1000000`, `interest_rate_tna = 30`, `start_date = 2026-10-01`, `maturity_date = 2026-10-31`
- **THEN** the response SHALL include `fixed_term.term_days = 30`, `interest_total = 24657.53`, `amount_at_maturity = 1024657.53` and `tea_pct = 34.50`

#### Scenario: Accrued interest to the user's today
- **WHEN** that fixed term is listed with `tz_offset_minutes = -180` and the user's local date is 2026-10-13
- **THEN** `fixed_term.accrued_interest` SHALL be `9863.01` and, with no `current_value`, `effective_value` SHALL be `1009863.01` with `value_source = "fixed_term_accrued"`

#### Scenario: Accrual stops at maturity
- **WHEN** the user's local date is after `maturity_date`
- **THEN** `accrued_interest` SHALL equal `interest_total` and `is_matured` SHALL be true

#### Scenario: Fixed term missing the rate
- **WHEN** a user creates a `fixed_term` without `interest_rate_tna`
- **THEN** the system SHALL respond 422

#### Scenario: Fixed term in EUR
- **WHEN** a user creates a `fixed_term` with `currency = "EUR"`
- **THEN** the system SHALL respond 422

### Requirement: Effective value and gain/loss
The system SHALL compute an `effective_value` for each investment with this precedence: (1) `quantity × last_price` when `price_source` is not `manual` and both are present (`value_source = "quote"`); (2) `current_value` when set (`"manual"`); (3) fixed-term `invested_amount + accrued_interest` (`"fixed_term_accrued"`); (4) otherwise `invested_amount` (`"invested"`). It SHALL return `gain = effective_value − invested_amount`, `gain_pct = gain / invested_amount × 100` rounded to 2 decimals (null when `invested_amount` is 0), `days_to_maturity` (null without maturity, 0 on the maturity day, negative after it) and `is_matured`.

#### Scenario: Loss is negative
- **WHEN** an investment has `invested_amount = 1000` and `current_value = 800`
- **THEN** `gain` SHALL be `-200.00` and `gain_pct` SHALL be `-20.00`

#### Scenario: Value defaults to invested amount
- **WHEN** a `real_estate` investment has `invested_amount = 50000` and no `current_value`
- **THEN** `effective_value` SHALL be `50000.00`, `gain` `0.00` and `value_source = "invested"`

#### Scenario: Days to maturity in the user's timezone
- **WHEN** an investment matures 2026-10-20 and is requested with the user's local date 2026-10-15
- **THEN** `days_to_maturity` SHALL be `5`

### Requirement: Pluggable price providers extension point
The system SHALL store `ticker`, `price_source`, `last_price` and `last_price_at` on each investment and SHALL route valuation through a provider registry so that automatic quote providers can be added later without schema changes. In this change the registry SHALL contain no external providers, SHALL perform no outbound HTTP calls for prices, and the API SHALL only accept `price_source = "manual"`.

#### Scenario: Only manual source accepted
- **WHEN** a user creates or updates an investment with `price_source = "coingecko"`
- **THEN** the system SHALL respond 422

#### Scenario: Quote takes precedence when present
- **WHEN** an investment (set up internally, e.g. in a unit test) has a non-manual `price_source`, `quantity = 2` and `last_price = 100`
- **THEN** the valuation service SHALL return `effective_value = 200.00` with `value_source = "quote"`

### Requirement: User can list, read, update, close and delete investments
The system SHALL provide `GET /api/v1/finance/investments` (query `status=active|closed|all`, default `active`; optional `asset_type`; optional `tz_offset_minutes`), `GET /api/v1/finance/investments/{id}`, `PUT /api/v1/finance/investments/{id}` (partial update; a `null` sent for a required field SHALL be ignored; cross-field rules SHALL be validated on the resulting state) and `DELETE /api/v1/finance/investments/{id}` (204). Setting `status = "closed"` SHALL keep the record but exclude it from totals. Changing `current_value` SHALL set `value_updated_at`. The list SHALL be ordered by `asset_type`, then `maturity_date` ascending with nulls last, then `name`.

#### Scenario: Close an investment
- **WHEN** a user updates an investment with `{status: "closed"}`
- **THEN** it SHALL no longer appear in the default list nor in totals, and SHALL appear with `status=closed`

#### Scenario: Partial update keeps other fields
- **WHEN** a user updates only `current_value`
- **THEN** every other field SHALL keep its value and `value_updated_at` SHALL be set

#### Scenario: Update breaks a cross-field rule
- **WHEN** a user updates a fixed term's `maturity_date` to a date before its `start_date`
- **THEN** the system SHALL respond 422 and SHALL NOT persist the change

#### Scenario: Delete
- **WHEN** a user deletes one of their investments
- **THEN** the system SHALL respond 204 and a later `GET` of that id SHALL respond 404

### Requirement: Tenant isolation for investments
Every investment query SHALL be filtered by the authenticated user. Reading, updating or deleting an investment owned by another user SHALL respond 404, and lists and summaries SHALL never include other users' investments.

#### Scenario: Another user's investment is unreachable
- **WHEN** user B requests `GET`, `PUT` or `DELETE` on an investment of user A
- **THEN** the system SHALL respond 404 and user A's investment SHALL remain unchanged

#### Scenario: Lists are per user
- **WHEN** user B lists investments or requests the investments summary
- **THEN** the response SHALL NOT include nor count user A's investments

### Requirement: Investments summary
The system SHALL provide `GET /api/v1/finance/investments/summary` returning, for active investments only: `by_currency` (invested, current value and gain per currency), `by_type` (count and value per type, converted to ARS when possible), `total_ars`, `total_usd`, `missing_rates`, `count_active` and `upcoming_maturities` (up to 5 active investments maturing within the next 30 days of the user's today, soonest first).

#### Scenario: Subtotals per currency
- **WHEN** a user has active investments worth 500000 ARS and 2000 USD
- **THEN** `by_currency` SHALL contain an ARS entry with `current_value = 500000.00` and a USD entry with `current_value = 2000.00`

#### Scenario: Upcoming maturities
- **WHEN** a user has fixed terms maturing in 3, 10 and 45 days
- **THEN** `upcoming_maturities` SHALL list the ones at 3 and 10 days, in that order

### Requirement: Account export and deletion include investments
The `investments` table SHALL be part of the account data inventory (`OWNED_TABLES`), so that the account export includes the user's investments and account deletion removes them.

#### Scenario: Export includes investments
- **WHEN** a user with investments requests the account export
- **THEN** the export SHALL include their investments and SHALL NOT include other users' investments

#### Scenario: Account deletion removes investments
- **WHEN** a user deletes their account
- **THEN** none of their investments SHALL remain in the database
