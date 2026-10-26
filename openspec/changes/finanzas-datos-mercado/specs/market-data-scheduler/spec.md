## ADDED Requirements

### Requirement: Single market data scheduler per process
The system SHALL start a market data scheduler in the application lifespan, next to the existing schedulers, only when `MARKET_DATA_ENABLED` is true, and SHALL cancel it on shutdown. Every 60 seconds it SHALL evaluate the sources `fx` (default every 15 minutes), `inflation` (default every 6 hours) and `crypto` (default every 10 minutes), with intervals configurable by environment. Exceptions SHALL be logged and SHALL NOT stop the loop.

#### Scenario: Disabled by configuration
- **WHEN** `MARKET_DATA_ENABLED` is false
- **THEN** the scheduler SHALL NOT start and the market endpoints SHALL keep serving the stored data

#### Scenario: Error in a provider
- **WHEN** a provider raises an unexpected exception
- **THEN** the error SHALL be logged, the source SHALL be marked as failed and the loop SHALL continue with the next source

### Requirement: Cross-worker lease per source
Before fetching a source, a worker SHALL acquire a lease with a single atomic `UPDATE` on `market_fetch_state` conditioned on `next_run_at <= now` and an absent or expired `lease_until`, and SHALL fetch only if exactly one row was updated. The lease SHALL be committed before any outbound HTTP call and SHALL expire after 120 seconds. On success the source SHALL record `last_success_at`, reset `consecutive_failures` and schedule `next_run_at = now + interval`; on failure it SHALL increment `consecutive_failures`, store a truncated `last_error` and schedule `next_run_at = now + min(interval × 2^failures, cap)` with a cap of 1 hour for `fx` and `crypto` and 24 hours for `inflation`. This SHALL work without Redis.

#### Scenario: Several workers in the same cycle
- **WHEN** three gunicorn workers evaluate the `fx` source at the same time and it is due
- **THEN** exactly one worker SHALL call the external FX sources

#### Scenario: Worker dies holding the lease
- **WHEN** the worker holding the `fx` lease dies before finishing
- **THEN** another worker SHALL be able to acquire the lease after it expires

#### Scenario: Backoff after failures
- **WHEN** the `fx` source fails twice in a row with an interval of 15 minutes
- **THEN** the next attempt SHALL be scheduled 60 minutes after the second failure

#### Scenario: Missing state rows
- **WHEN** the scheduler starts on a database created without the seeded `market_fetch_state` rows
- **THEN** it SHALL create the missing rows and run each source on its first cycle

### Requirement: Safe outbound HTTP
Outbound requests SHALL use a timeout of 10 seconds (5 seconds to connect), an identifying `User-Agent`, no immediate retries, and SHALL parse responses tolerantly, discarding invalid items without discarding the valid ones. No user request SHALL wait on an external source.

#### Scenario: Slow source
- **WHEN** a source does not answer within 10 seconds
- **THEN** the attempt SHALL fail, fallbacks SHALL be tried where defined, and API requests from users SHALL be unaffected

#### Scenario: Partially malformed response
- **WHEN** DolarAPI returns one item without `venta` among valid items
- **THEN** the valid items SHALL be stored and the malformed one SHALL be ignored

### Requirement: Tests never reach the network
The test suite SHALL run with `MARKET_DATA_ENABLED` false, providers SHALL receive their HTTP client as a dependency so tests can use `httpx.MockTransport` with recorded payloads, and an autouse fixture SHALL make any outbound request not served by a mock transport fail the test.

#### Scenario: Accidental real request in a test
- **WHEN** a test triggers a provider with a real HTTP transport
- **THEN** the test SHALL fail instead of contacting the external API

### Requirement: Configuration and secrets
`MARKET_DATA_ENABLED`, `COINGECKO_API_KEY` (optional) and the refresh intervals SHALL be read from the environment, listed explicitly in `docker-compose.prod.yml` and documented in `.env.prod.example`. No key SHALL be committed to the repository. Market data tables SHALL have no `user_id` and SHALL NOT be part of account export or deletion.

#### Scenario: Production without CoinGecko key
- **WHEN** production runs without `COINGECKO_API_KEY`
- **THEN** the crypto provider SHALL use CoinGecko's public access without a key header and the rest of the market data SHALL work normally

#### Scenario: Account deletion
- **WHEN** a user deletes their account
- **THEN** the shared market data tables SHALL remain untouched
