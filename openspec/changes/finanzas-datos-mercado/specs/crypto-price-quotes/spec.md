## ADDED Requirements

### Requirement: CoinGecko price provider
The system SHALL register a `coingecko` provider in `PRICE_PROVIDERS` supporting asset type `crypto`. It SHALL map tickers to CoinGecko ids through a curated list (at least BTC, ETH, USDT, USDC, DAI, SOL, BNB, XRP, ADA, DOGE) and SHALL NOT resolve unknown tickers by searching. It SHALL quote in the investment's currency: `USD` and `USDT` as `usd`, `ARS` as `ars`, `EUR` as `eur`. When `COINGECKO_API_KEY` is configured it SHALL send it in the `x-cg-demo-api-key` header; the key SHALL come only from the environment.

#### Scenario: Supported tickers list
- **WHEN** an authenticated user calls `GET /api/v1/finance/market/crypto-assets`
- **THEN** the response SHALL include `{ticker: "BTC", name: "Bitcoin"}` and SHALL NOT trigger any outbound HTTP request

#### Scenario: API key header
- **WHEN** `COINGECKO_API_KEY` is set and the crypto job queries CoinGecko
- **THEN** the request SHALL carry the `x-cg-demo-api-key` header

### Requirement: Batched crypto quote refresh
The crypto job SHALL collect the distinct `(ticker, currency)` pairs of active investments with `price_source = "coingecko"` across all users and query them in a single `GET /simple/price` request with `include_last_updated_at=true`, at most once every 10 minutes by default. When no investment uses the provider it SHALL make no request. It SHALL store each price in the shared price cache and SHALL update `last_price` and `last_price_at` of every matching active investment. Prices not greater than 0 or above 1e11 SHALL be discarded. A `429` response SHALL postpone the next attempt honoring `Retry-After`.

#### Scenario: One request for many users
- **WHEN** user A holds BTC in USD and user B holds BTC in USD and ETH in ARS, all with `price_source = "coingecko"`
- **THEN** the job SHALL make exactly one request with `ids=bitcoin,ethereum` and `vs_currencies` including `usd` and `ars`, and SHALL update the three investments

#### Scenario: No crypto in use
- **WHEN** no active investment has `price_source = "coingecko"`
- **THEN** the crypto job SHALL NOT make any outbound request

#### Scenario: Rate limited
- **WHEN** CoinGecko answers 429 with `Retry-After: 120`
- **THEN** the next crypto attempt SHALL NOT happen before 120 seconds and investments SHALL keep their previous `last_price`

### Requirement: Automatic or manual valuation per crypto investment
A user SHALL be able to choose per investment between `price_source = "coingecko"` (automatic) and `manual`. Choosing `coingecko` SHALL require `asset_type = "crypto"`, a supported ticker and `quantity > 0`, validated on the resulting state for updates, otherwise the system SHALL respond 422 with a Spanish message. On save the system SHALL fill `last_price`/`last_price_at` from the shared cache when a price for that pair exists, without outbound HTTP; when none exists it SHALL schedule the crypto job to run on its next cycle. With a price, valuation SHALL be `quantity × last_price` with `value_source = "quote"`; switching back to `manual` SHALL value the investment as before (manual value, or invested amount).

#### Scenario: Create automatic BTC
- **WHEN** a user creates a `crypto` investment with ticker `BTC`, currency `USD`, `quantity = 0.5` and `price_source = "coingecko"`, and the cache holds BTC/USD at 79509
- **THEN** the response SHALL have `last_price = 79509`, `effective_value = 39754.50` and `value_source = "quote"`

#### Scenario: Unknown ticker
- **WHEN** a user sets `price_source = "coingecko"` on a crypto investment with ticker `FOOCOIN`
- **THEN** the system SHALL respond 422

#### Scenario: Missing quantity
- **WHEN** a user sets `price_source = "coingecko"` on a crypto investment without `quantity`
- **THEN** the system SHALL respond 422

#### Scenario: Not yet quoted
- **WHEN** a user creates an automatic ETH investment in EUR and the cache has no ETH/EUR price
- **THEN** the investment SHALL be valued without a quote (manual value or invested amount) until the next crypto cycle stores a price

#### Scenario: Switch back to manual
- **WHEN** a user updates an automatic BTC investment to `price_source = "manual"` with `current_value = 30000`
- **THEN** `effective_value` SHALL be 30000.00 with `value_source = "manual"`

### Requirement: Quote freshness and attribution
`InvestmentOut` SHALL include `quote_provider` ("CoinGecko" for automatic crypto) and `quote_stale`, true when `last_price_at` is older than 1 hour. Clients SHALL show "Cotización automática · hace X" (highlighted when stale) and the attribution "Datos de CoinGecko" linking to coingecko.com wherever automatic crypto prices are displayed. The investment form SHALL offer an "Cotización automática" switch for crypto, enabled only for supported tickers, requiring quantity and hiding the manual current value field.

#### Scenario: Stale quote
- **WHEN** an automatic investment's `last_price_at` is 3 hours old
- **THEN** `quote_stale` SHALL be true

#### Scenario: Attribution shown
- **WHEN** the investments list shows an automatic crypto investment in web or mobile
- **THEN** the screen SHALL display "Datos de CoinGecko"

### Requirement: Stocks and CEDEARs remain manual
The system SHALL NOT provide automatic quotes for `stock`, `bond` or `fund` investments in this change, and SHALL reject any non-manual `price_source` for them with 422.

#### Scenario: Automatic stock rejected
- **WHEN** a user sets `price_source = "coingecko"` on a `stock` investment
- **THEN** the system SHALL respond 422
