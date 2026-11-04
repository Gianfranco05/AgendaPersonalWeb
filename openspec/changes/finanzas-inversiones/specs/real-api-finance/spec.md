## ADDED Requirements

### Requirement: Finance summary exposes investments fields additively
`GET /api/v1/finance/summary` SHALL keep `total_income`, `total_expenses` and `balance` with their current meaning (cash only, regardless of the investments preference) and SHALL additionally return `investments_value_ars` (active investments converted to ARS, `null` if a needed rate is missing), `net_worth_ars` (`balance + investments_value_ars`, `null` if the former is `null`), `investments_missing_rates` and `include_investments_in_balance`. It SHALL accept an optional `tz_offset_minutes` query parameter (−840..840, default 0) used for fixed-term accrual. Clients that ignore the new fields SHALL keep working unchanged.

#### Scenario: Summary without investments
- **WHEN** a user without investments requests the summary
- **THEN** `balance` SHALL be unchanged, `investments_value_ars` SHALL be `0.00` and `net_worth_ars` SHALL equal `balance`

#### Scenario: Summary with investments and preference off
- **WHEN** a user with investments and `include_investments_in_balance = false` requests the summary
- **THEN** `balance` SHALL only reflect transactions and `investments_value_ars` and `net_worth_ars` SHALL be present

#### Scenario: Summary with a missing rate
- **WHEN** a user has USD investments and no `fx_usd_ars`
- **THEN** `investments_value_ars` and `net_worth_ars` SHALL be `null` and `investments_missing_rates` SHALL contain `"USD"`

### Requirement: Investments from real API
When mock mode is disabled, the web and mobile clients SHALL call `GET/POST /api/v1/finance/investments`, `GET/PUT/DELETE /api/v1/finance/investments/{id}`, `GET /api/v1/finance/investments/summary` and `GET /api/v1/finance/net-worth`, always sending `tz_offset_minutes` on reads and `timezone_offset_minutes` on writes. When mock mode is enabled, the web client SHALL serve equivalent mock data with the same shapes.

#### Scenario: List investments
- **WHEN** `fetchInvestments()` is called with mock disabled
- **THEN** it SHALL `GET /api/v1/finance/investments` with `tz_offset_minutes` set to the browser's offset in minutes east of UTC

#### Scenario: Create investment
- **WHEN** `createInvestment(data)` is called
- **THEN** it SHALL `POST` to `/api/v1/finance/investments` including `timezone_offset_minutes`

#### Scenario: Investment request error
- **WHEN** any investments request fails
- **THEN** the hook SHALL expose the error and SWR SHALL NOT clear existing data

### Requirement: Investments cache invalidation
After creating, updating, closing or deleting an investment, the clients SHALL revalidate the investments list, the investments summary, the net worth and `finance/summary` cache keys. After changing an exchange rate or the investments preference, they SHALL also revalidate `settings`.

#### Scenario: After creating an investment
- **WHEN** an investment is created successfully
- **THEN** the investments list, investments summary, net worth and `finance/summary` SHALL be revalidated

#### Scenario: After changing the dollar rate
- **WHEN** the user saves a new `fx_usd_ars`
- **THEN** `settings`, investments summary, net worth and `finance/summary` SHALL be revalidated
