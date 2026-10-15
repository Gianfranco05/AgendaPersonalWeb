## ADDED Requirements

### Requirement: User-managed exchange rates
The system SHALL store, per user in `user_preferences`, an optional `fx_usd_ars` (ARS per 1 USD) and an optional `fx_eur_ars` (ARS per 1 EUR), each greater than 0, at most 9.999.999,9999 and with up to 4 decimals, plus `fx_rates_updated_at`. They SHALL be readable and writable through `GET/PUT /api/v1/settings`. The server SHALL set `fx_rates_updated_at` to the current UTC time whenever a rate changes; clients SHALL NOT be able to set it. Sending `null` SHALL clear a rate. USDT SHALL be valued 1:1 with USD.

#### Scenario: Set the dollar rate
- **WHEN** a user sends `PUT /api/v1/settings` with `{fx_usd_ars: 1450.50}`
- **THEN** the settings response SHALL include `fx_usd_ars = 1450.5000` and a non-null `fx_rates_updated_at`

#### Scenario: Invalid rate
- **WHEN** a user sends `fx_usd_ars = 0` or a negative value
- **THEN** the system SHALL respond 422 and keep the previous rate

#### Scenario: Unchanged rate keeps the timestamp
- **WHEN** a user updates only `theme_color`
- **THEN** `fx_rates_updated_at` SHALL NOT change

### Requirement: Currency conversion and rounding of totals
The system SHALL convert totals by first summing effective values per currency, then applying the factor to ARS (`ARS = 1`, `USD = USDT = fx_usd_ars`, `EUR = fx_eur_ars`), computing in `Decimal` and rounding half-up to 2 decimals only on the final totals. `total_usd` SHALL be the ARS-converted total divided by `fx_usd_ars`, with USD/USDT subtotals contributing their exact amount. A total that cannot be computed because a needed rate is missing SHALL be `null`, and the missing pairs SHALL be listed in `missing_rates`.

#### Scenario: Totals in ARS and USD
- **WHEN** a user has active investments worth 500000 ARS and 2000 USD and `fx_usd_ars = 1450.50`
- **THEN** `total_ars` SHALL be `3401000.00` and `total_usd` SHALL be `2344.71`

#### Scenario: No dollar rate configured
- **WHEN** a user has investments in ARS and USD and no `fx_usd_ars`
- **THEN** `total_ars` and `total_usd` SHALL be `null`, `missing_rates` SHALL contain `"USD"`, and `by_currency` SHALL still contain both subtotals

#### Scenario: Only ARS investments without rate
- **WHEN** a user has only ARS investments and no rates
- **THEN** `total_ars` SHALL be computed and `total_usd` SHALL be `null` with `"USD"` in `missing_rates`

#### Scenario: EUR without EUR rate
- **WHEN** a user has an EUR investment, `fx_usd_ars` set and no `fx_eur_ars`
- **THEN** `total_ars` and `total_usd` SHALL be `null` and `missing_rates` SHALL contain `"EUR"`

### Requirement: Net worth (Patrimonio)
The system SHALL provide `GET /api/v1/finance/net-worth` (optional `tz_offset_minutes`) returning the full breakdown of the Patrimonio card, each part in ARS and in USD: `cash_balance_ars` (the existing finance `balance`, assumed ARS) and `cash_balance_usd` (`cash_balance_ars / fx_usd_ars`, rounded half-up to 2 decimals, `null` without `fx_usd_ars`); the investments summary (`investments`, with its own `total_ars` / `total_usd` and per-currency breakdown, active investments only); `net_worth_ars = cash_balance_ars + investments.total_ars` and `net_worth_usd = cash_balance_usd + investments.total_usd`; the rates with `updated_at`; `missing_rates` (the investments' missing rates plus `"USD"` when `fx_usd_ars` is not set); and `include_investments_in_balance`. Any value that depends on a missing rate SHALL be `null`.

#### Scenario: Net worth with cash and investments
- **WHEN** a user has a finance balance of 100000, active investments worth 3401000.00 ARS in total and `fx_usd_ars = 1450.50`
- **THEN** `net_worth_ars` SHALL be `3501000.00`

#### Scenario: Full breakdown in ARS and USD
- **WHEN** a user has a finance balance of 100000, active investments worth 500000 ARS and 2000 USD and `fx_usd_ars = 1450.50`
- **THEN** `cash_balance_ars` SHALL be `100000.00`, `cash_balance_usd` `68.94`, `investments.total_ars` `3401000.00`, `investments.total_usd` `2344.71`, `net_worth_ars` `3501000.00` and `net_worth_usd` `2413.65`

#### Scenario: No dollar rate keeps the ARS part
- **WHEN** a user has a finance balance of 100000, only ARS investments worth 500000 and no `fx_usd_ars`
- **THEN** `cash_balance_ars` SHALL be `100000.00`, `investments.total_ars` `500000.00` and `net_worth_ars` `600000.00`; `cash_balance_usd`, `investments.total_usd` and `net_worth_usd` SHALL be `null` and `missing_rates` SHALL contain `"USD"`

#### Scenario: Closed investments do not count
- **WHEN** a user closes an investment
- **THEN** `net_worth_ars` SHALL decrease by that investment's ARS value

#### Scenario: Net worth isolated per user
- **WHEN** user B requests their net worth
- **THEN** user A's transactions and investments SHALL NOT be counted

### Requirement: Preference to add investments to the balance
The system SHALL store a per-user boolean `include_investments_in_balance`, default `false`, readable and writable through `GET/PUT /api/v1/settings`. The preference SHALL only change presentation: the `balance` field of the finance summary SHALL keep meaning cash only.

#### Scenario: Default is off
- **WHEN** a new user reads their settings
- **THEN** `include_investments_in_balance` SHALL be `false`

#### Scenario: Turning it on does not change balance
- **WHEN** a user turns the preference on
- **THEN** `GET /api/v1/finance/summary` SHALL return the same `balance` as before and `include_investments_in_balance = true`

### Requirement: Differentiated balance presentation in clients
When `include_investments_in_balance` is true, the web Dashboard finance widget, the web Finanzas net-worth card and the mobile Home `BalanceCard` SHALL show `net_worth_ars` as the headline labeled "Balance + inversiones", with the cash part and the investments part rendered as separate segments in different colors and labeled ("Efectivo" / "Inversiones"); the investments color SHALL NOT be the income green nor the expense red. When it is false, they SHALL show the cash balance exactly as today. If the investments total cannot be computed (missing rate), they SHALL show the cash balance and a prompt to set the exchange rate.

#### Scenario: Toggle on in mobile Home
- **WHEN** the preference is on and the user opens Home in the mobile app
- **THEN** `BalanceCard` SHALL show `net_worth_ars`, the label "Balance + inversiones" and a two-segment bar with "Efectivo" and "Inversiones" in distinct colors

#### Scenario: Toggle off
- **WHEN** the preference is off
- **THEN** the balance cards SHALL show only the cash balance, as before this change

#### Scenario: Missing rate with toggle on
- **WHEN** the preference is on and the user has USD investments without `fx_usd_ars`
- **THEN** the cards SHALL show the cash balance and a message inviting to set the dollar rate

### Requirement: Investments UI in web and mobile
The web Finanzas page SHALL have an "Inversiones" tab and the mobile app SHALL have an "Inversiones" screen reachable from the Finanzas tools grid and from a "Inversión" option in the Home "+" menu. Both SHALL show the net-worth card (the breakdown "Disponible", "Inversiones" and "Total", each in ARS and in USD, with a "—" and a prompt to set the rate where a USD value cannot be computed), the editable exchange rate with its last update, the "Sumar inversiones al balance" toggle, the investments grouped by type with per-asset value, gain/loss (green/red), TNA and a maturity chip ("vence en X días", "vence hoy", "venció"), and a create/edit form whose fields adapt to the asset type, accept decimal comma, and preview the fixed-term interest and amount at maturity before saving. All user-facing text SHALL be in Spanish.

#### Scenario: Quick create from Home
- **WHEN** the user taps "+" in mobile Home and chooses "Inversión"
- **THEN** the app SHALL open the Inversiones screen with the create form open

#### Scenario: Fixed-term preview
- **WHEN** the user fills a fixed term with 1.000.000, TNA 30 and 30 days in the form
- **THEN** the form SHALL preview interest $ 24.657,53 and amount at maturity $ 1.024.657,53 before saving

#### Scenario: Decimal comma input
- **WHEN** the user types `1500,50` as invested amount in the mobile form
- **THEN** the investment SHALL be saved with `invested_amount = 1500.50`
