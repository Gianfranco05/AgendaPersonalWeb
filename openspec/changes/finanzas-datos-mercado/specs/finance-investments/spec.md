## MODIFIED Requirements

### Requirement: Pluggable price providers extension point
The system SHALL store `ticker`, `price_source`, `last_price` and `last_price_at` on each investment and SHALL route valuation through a provider registry (`PRICE_PROVIDERS`) so that automatic quote providers can be added without schema changes. The API SHALL accept `price_source = "manual"` or the key of a registered provider (in this change: `coingecko`, for `crypto` investments only) and SHALL reject any other value with 422. Providers SHALL support batched quotes (`quote_many`) and SHALL only be called by the market data scheduler, never during a user request. When an investment has a non-manual `price_source`, a `quantity` and a `last_price`, its valuation SHALL be `quantity × last_price` with `value_source = "quote"`, taking precedence over the manual current value.

#### Scenario: Unregistered source rejected
- **WHEN** a user creates or updates an investment with `price_source = "byma"`
- **THEN** the system SHALL respond 422

#### Scenario: Registered provider accepted for crypto
- **WHEN** a user creates a `crypto` investment with ticker `ETH`, `quantity = 1` and `price_source = "coingecko"`
- **THEN** the system SHALL respond 201 with `price_source = "coingecko"`

#### Scenario: Quote takes precedence when present
- **WHEN** an investment has a non-manual `price_source`, `quantity = 2` and `last_price = 100`
- **THEN** the valuation service SHALL return `effective_value = 200.00` with `value_source = "quote"`

#### Scenario: No outbound call during requests
- **WHEN** a user lists or creates investments
- **THEN** the system SHALL NOT perform any outbound HTTP request to price providers
