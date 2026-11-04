## ADDED Requirements

### Requirement: Server-side retrieval of dollar and euro rates
The system SHALL periodically fetch exchange rates from public sources on the server, never on behalf of an individual user request. It SHALL fetch USD rates of kinds `oficial`, `mep` (DolarAPI `bolsa`), `blue`, `ccl`, `mayorista`, `cripto` and `tarjeta` from DolarAPI `GET /v1/dolares`, and EUR `oficial` from DolarAPI `GET /v1/cotizaciones/eur`. When the primary source fails or omits a kind, it SHALL try the fallback chain: Bluelytics for USD `oficial`/`blue` and EUR `oficial`/`blue`, and ArgentinaDatos for USD `oficial`/`mep`/`blue`. Each stored quote SHALL include currency, kind, buy (optional), sell, provider and the source's update timestamp. No user data SHALL be sent to these sources.

#### Scenario: Primary source returns all kinds
- **WHEN** the FX job runs and DolarAPI answers `/v1/dolares` with `bolsa` sell 1563.9 updated `2026-10-25T20:58:00Z`
- **THEN** the system SHALL store a `USD`/`mep` quote with `sell = 1563.9000`, `provider = "dolarapi"` and `source_updated_at = 2026-10-25T20:58:00Z`

#### Scenario: Primary source down
- **WHEN** DolarAPI times out and Bluelytics answers `blue.value_sell = 1562`
- **THEN** the system SHALL store the `USD`/`blue` quote from `bluelytics` and SHALL try ArgentinaDatos for `mep`

#### Scenario: Older fallback data does not overwrite newer data
- **WHEN** a fallback returns a quote whose `source_updated_at` is older than the stored one for the same currency, kind and date
- **THEN** the stored quote SHALL NOT change

#### Scenario: EUR blue only from Bluelytics
- **WHEN** the FX job runs and Bluelytics answers `blue_euro.value_sell = 1698`
- **THEN** the system SHALL store an `EUR`/`blue` quote with `sell = 1698.0000`

### Requirement: Rate sanity validation
The system SHALL discard a fetched quote when `sell` is not greater than 0, when `sell` exceeds 10,000,000, when `buy` exceeds 1.5 × `sell`, or when `sell` deviates more than 50 % from the last stored quote of the same currency and kind, logging a warning and keeping the previous value.

#### Scenario: Zero rate from a source
- **WHEN** a source returns `venta = 0` for `blue`
- **THEN** the system SHALL NOT store it and the last known `blue` quote SHALL remain the effective one

#### Scenario: Implausible jump
- **WHEN** the last stored `mep` sell is 1563.90 and a source returns 15639
- **THEN** the system SHALL discard the new value

### Requirement: Minimal daily history of rates
The system SHALL keep one row per currency, kind and Argentine local date (UTC−3), updated during the day so that each past day keeps its last quote. Rows older than 730 days SHALL be deleted by the FX job at most once per day.

#### Scenario: Two fetches on the same day
- **WHEN** the FX job stores `blue` at 11:00 and again at 15:00 Argentine time on 2026-10-26
- **THEN** there SHALL be a single `USD`/`blue` row for `2026-10-26` holding the 15:00 value

#### Scenario: Retention
- **WHEN** the FX job runs and there are rows dated more than 730 days ago
- **THEN** those rows SHALL be deleted

### Requirement: User selection of the dollar and euro rate type
The system SHALL store per user `fx_usd_source` in `{oficial, mep, blue, manual}` and `fx_eur_source` in `{oficial, blue, manual}`, readable and writable via `GET/PUT /api/v1/settings`. Invalid values SHALL be rejected with 422. The default for users without a manually entered rate SHALL be `mep` for USD and `oficial` for EUR; users that had `fx_usd_ars` (or `fx_eur_ars`) set before this change SHALL be migrated to `manual` for that currency. Changing the source SHALL NOT clear the manual rate fields.

#### Scenario: Existing manual user keeps their rate
- **WHEN** a user had `fx_usd_ars = 1450.50` before the migration
- **THEN** after the migration `fx_usd_source` SHALL be `manual` and their totals SHALL still use 1450.50

#### Scenario: Choose blue
- **WHEN** a user sends `PUT /api/v1/settings` with `{fx_usd_source: "blue"}`
- **THEN** the settings response SHALL include `fx_usd_source = "blue"` and `fx_usd_ars` SHALL keep its previous value

#### Scenario: Invalid source
- **WHEN** a user sends `fx_usd_source = "ccl"` or `fx_eur_source = "mep"`
- **THEN** the system SHALL respond 422

### Requirement: Effective rate resolution with fallback
For each currency the system SHALL resolve the effective rate as follows: with source `manual`, the user's manual rate; with an automatic source, the `sell` of the most recent stored quote of that kind, regardless of whether the latest fetch failed; with an automatic source and no stored quote at all, the user's manual rate if present, reported as `manual_fallback`; otherwise no rate, adding the currency to `missing_rates`. The effective rate SHALL be used for investment totals, net worth and `/finance/summary`. The rates payload SHALL report, per currency, the requested source, the effective source, the provider, the quote timestamp (`as_of`) and a `stale` flag; `rates.updated_at` SHALL be the `as_of` of the effective USD rate.

#### Scenario: Automatic rate applied to totals
- **WHEN** a user with `fx_usd_source = "mep"` holds 500000 ARS and 2000 USD and the latest `mep` sell is 1563.90
- **THEN** the investments summary SHALL report `total_ars = 3627800.00` and the rates SHALL show `usd_effective_source = "mep"` and `usd_provider = "dolarapi"`

#### Scenario: API down uses last known quote
- **WHEN** every FX source has failed for the last 3 hours and the latest stored `blue` quote is from 3 hours ago
- **THEN** a user with `fx_usd_source = "blue"` SHALL still get that quote as effective rate

#### Scenario: No data ever fetched
- **WHEN** no USD `mep` quote has ever been stored and the user has `fx_usd_source = "mep"` and `fx_usd_ars = 1400`
- **THEN** the effective USD rate SHALL be 1400 with `usd_effective_source = "manual_fallback"`

#### Scenario: No data and no manual rate
- **WHEN** no USD quote has ever been stored and the user has no manual rate
- **THEN** `total_usd` SHALL be null and `missing_rates` SHALL include `USD`

#### Scenario: Stale quote
- **WHEN** the effective quote's `as_of` is more than 96 hours old, or the last successful FX fetch was more than 6 hours ago
- **THEN** `usd_stale` SHALL be true

### Requirement: Market FX endpoint
The system SHALL expose `GET /api/v1/finance/market/fx` to authenticated users, returning the latest stored quote of each kind for USD and EUR with `kind`, `label`, `buy`, `sell`, `provider`, `as_of` and `stale`, plus `last_success_at` and a `degraded` flag (true when the last attempt failed or the last success is older than 6 hours). It SHALL never call external sources during the request.

#### Scenario: Read market rates
- **WHEN** an authenticated user calls `GET /api/v1/finance/market/fx`
- **THEN** the response SHALL list the stored `oficial`, `mep` and `blue` USD quotes and SHALL NOT trigger any outbound HTTP request

#### Scenario: Unauthenticated access
- **WHEN** the endpoint is called without a session
- **THEN** the system SHALL respond 401

### Requirement: Dollar type selector and freshness in clients
The web Inversiones quote card and the mobile `FxRatesEditor` SHALL offer the choices Oficial, MEP, Blue and Manual for the dollar, show the sell (and buy) of the three automatic kinds with "hace X" and the provider name, show a "desactualizada" badge when stale, and explain when the manual rate is being used as fallback. The euro row (Oficial, Blue, Manual) SHALL be shown only when the user has EUR investments. The net worth card SHALL show which dollar, value, provider and age are being used. Changing the selection SHALL revalidate settings, net worth, investments summary and finance summary.

#### Scenario: Switch to MEP in web
- **WHEN** the user selects "MEP" in the quote card
- **THEN** the client SHALL send `PUT /settings` with `fx_usd_source = "mep"` and the net worth card SHALL show "Dólar MEP" with its value, "DolarAPI" and the age

#### Scenario: Manual edit sets manual source
- **WHEN** the user types a manual dollar rate and saves it
- **THEN** the client SHALL send both `fx_usd_ars` and `fx_usd_source = "manual"`
