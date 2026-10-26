## ADDED Requirements

### Requirement: Monthly CPI series storage
The system SHALL periodically fetch the national CPI (IPC INDEC) monthly variation from ArgentinaDatos `GET /v1/finanzas/indices/inflacion`, falling back to the datos.gob.ar time series `148.3_INIVELNAL_DICI_M_26` (percent change) when the primary fails, and SHALL store one row per month (`period` = first day of the month, `pct` = monthly variation in %). Values outside −20..100 % or for a month after the current one SHALL be discarded. The first load SHALL include the whole series available since 2017-01.

#### Scenario: Store a published month
- **WHEN** the inflation job runs and ArgentinaDatos returns `{fecha: "2026-09-30", valor: 1.9}`
- **THEN** the system SHALL store `period = 2026-09-01` with `pct = 1.9000`

#### Scenario: Primary source down
- **WHEN** ArgentinaDatos fails and datos.gob.ar answers with the percent change series
- **THEN** the system SHALL store the months it does not have yet from datos.gob.ar

#### Scenario: Read the series
- **WHEN** an authenticated user calls `GET /api/v1/finance/market/inflation?months=12`
- **THEN** the response SHALL contain the last 12 stored months, `last_published_period` and the `estimate_pct` used for unpublished months, without any outbound HTTP request

### Requirement: Accumulated inflation over a period
The system SHALL compute the accumulated inflation between a start date S and an end date E by compounding each overlapping month's variation pro-rated geometrically by the share of its days covered: `factor = Π (1 + pct_m/100) ^ (covered_days_m / days_in_month_m)`, `inflation_pct = (factor − 1) × 100`. A month without published data SHALL use the latest published month's value and the result SHALL be flagged `estimated = true` listing `estimated_months`. A period starting before the first stored month SHALL yield no result.

#### Scenario: Full published month
- **WHEN** S = 2026-09-01, E = 2026-10-01 and September's pct is 1.9
- **THEN** `inflation_pct` SHALL be 1.90 and `estimated` SHALL be false

#### Scenario: Partial month
- **WHEN** S = 2026-09-16, E = 2026-10-01 and September's pct is 1.9
- **THEN** the factor SHALL be `1.019 ^ (15/30)` and `inflation_pct` SHALL be 0.95

#### Scenario: Current month not yet published
- **WHEN** today is 2026-10-25, the latest published month is September (1.9) and the period covers October
- **THEN** October SHALL be estimated with 1.9, `estimated` SHALL be true and `estimated_months` SHALL include `"2026-10"`

#### Scenario: Start before the series
- **WHEN** S is earlier than the first stored month
- **THEN** no inflation result SHALL be returned and the reason SHALL be `no_inflation_data`

### Requirement: Real return per investment
Each `InvestmentOut` SHALL include `real_return` with `period_start`, `period_end`, `nominal_pct`, `inflation_pct`, `real_pct`, `estimated` and `estimated_months`, where `nominal_pct = (effective_value / invested_amount − 1) × 100` and `real_pct = ((1 + nominal_pct/100) / factor − 1) × 100`, rounded to 2 decimals. It SHALL be computed only for investments in `ARS` with `start_date`; otherwise `real_return` SHALL be null and `real_return_unavailable_reason` SHALL be one of `currency`, `no_start_date`, `no_inflation_data`, `too_short`. The end date SHALL be the user's local today (from `tz_offset_minutes`), the maturity date for a matured fixed-term deposit, and for a closed investment its maturity date if already past or else the date it was last updated. Periods shorter than one day or starting in the future SHALL report `too_short`.

#### Scenario: Fixed-term real return
- **WHEN** a fixed-term ARS deposit of 1000000 at 30 % TNA ran from 2026-09-01 to 2026-10-01, it is matured and September's CPI is 1.9 %
- **THEN** `real_return` SHALL report `nominal_pct = 2.47`, `inflation_pct = 1.90` and `real_pct = 0.56`

#### Scenario: Loss against inflation
- **WHEN** an ARS investment's nominal return over its period is 1.00 % and accumulated inflation is 3.00 %
- **THEN** `real_pct` SHALL be −1.94

#### Scenario: USD investment
- **WHEN** an investment is in `USD`
- **THEN** `real_return` SHALL be null with `real_return_unavailable_reason = "currency"`

#### Scenario: No start date
- **WHEN** an ARS stock position has no `start_date`
- **THEN** `real_return` SHALL be null with `real_return_unavailable_reason = "no_start_date"`

### Requirement: Projected real return at maturity for fixed-term deposits
For an active, not yet matured fixed-term deposit in ARS, `real_return.projected_at_maturity` SHALL report `nominal_pct = interest_total / invested_amount × 100`, the accumulated inflation from `start_date` to `maturity_date` and the resulting `real_pct`, flagged `estimated = true` whenever any covered month lacks published data.

#### Scenario: Projection over unpublished months
- **WHEN** a fixed-term deposit runs from 2026-10-10 to 2026-11-09 and the latest published CPI is September
- **THEN** `projected_at_maturity` SHALL be computed with September's value for October and November and SHALL have `estimated = true`

### Requirement: Aggregated real return in the investments summary
`InvestmentSummary.real_return_ars` SHALL aggregate the active investments that have a computable `real_return`: `nominal_pct = Σvalue / Σinvested − 1`, `inflation_pct = Σ(invested × factor) / Σinvested − 1`, `real_pct = Σvalue / Σ(invested × factor) − 1` (all in %), plus `estimated`, `included_count` and `excluded_count`. It SHALL be null when no investment qualifies.

#### Scenario: Two ARS investments
- **WHEN** a user has two ARS investments with computable real return and one USD investment
- **THEN** `real_return_ars.included_count` SHALL be 2 and `excluded_count` SHALL be 1

#### Scenario: Nothing qualifies
- **WHEN** a user only has USD investments
- **THEN** `real_return_ars` SHALL be null

### Requirement: Real return presentation in clients
Web and mobile investment cards SHALL show a "Real ±x %" chip (green when positive, red when negative) with nominal and inflation details, an "estimado" mark when estimated, and for active fixed-term deposits the projected real return at maturity. The investments summary SHALL show the aggregated real return in pesos and how many investments it covers. Investments without real return SHALL show the reason in plain Spanish (for example "En dólares no se compara con la inflación local" or "Cargá la fecha de compra para ver el rendimiento real").

#### Scenario: Estimated chip
- **WHEN** an investment's `real_return.estimated` is true
- **THEN** the card SHALL show the real return chip with the "estimado" mark and a hint that the CPI of the month is not published yet

#### Scenario: Missing start date hint
- **WHEN** an ARS investment has `real_return_unavailable_reason = "no_start_date"`
- **THEN** the card SHALL invite the user to set the purchase date
