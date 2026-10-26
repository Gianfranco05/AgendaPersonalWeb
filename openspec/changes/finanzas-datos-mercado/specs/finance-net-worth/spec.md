## MODIFIED Requirements

### Requirement: User-managed exchange rates
The system SHALL store, per user in `user_preferences`, an optional `fx_usd_ars` (ARS per 1 USD) and an optional `fx_eur_ars` (ARS per 1 EUR), each greater than 0, at most 9.999.999,9999 and with up to 4 decimals, plus `fx_rates_updated_at`. They SHALL be readable and writable through `GET/PUT /api/v1/settings`. The server SHALL set `fx_rates_updated_at` to the current UTC time whenever a rate changes; clients SHALL NOT be able to set it. Sending `null` SHALL clear a rate. USDT SHALL be valued 1:1 with USD. These manual rates SHALL be the effective rates when the user's `fx_usd_source` / `fx_eur_source` is `manual`, and SHALL act as fallback when an automatic source has never produced a quote; otherwise the automatic market rate selected by the user SHALL be used for totals and net worth.

#### Scenario: Set the dollar rate
- **WHEN** a user sends `PUT /api/v1/settings` with `{fx_usd_ars: 1450.50}`
- **THEN** the settings response SHALL include `fx_usd_ars = 1450.5000` and a non-null `fx_rates_updated_at`

#### Scenario: Invalid rate
- **WHEN** a user sends `fx_usd_ars = 0` or a negative value
- **THEN** the system SHALL respond 422 and keep the previous rate

#### Scenario: Unchanged rate keeps the timestamp
- **WHEN** a user updates only `theme_color`
- **THEN** `fx_rates_updated_at` SHALL NOT change

#### Scenario: Manual rate ignored while an automatic source is selected
- **WHEN** a user has `fx_usd_ars = 1450.50`, `fx_usd_source = "blue"` and a stored blue quote with sell 1562
- **THEN** totals and net worth SHALL convert USD at 1562
