## ADDED Requirements

### Requirement: Prometheus metrics endpoint
The backend SHALL expose a `/metrics` endpoint for Prometheus scraping.

#### Scenario: Metrics endpoint returns valid format
- **WHEN** a GET request is sent to `/metrics`
- **THEN** the response SHALL have `Content-Type: text/plain; version=0.0.4`
- **AND** SHALL contain Prometheus-formatted metrics

#### Scenario: Metrics include request count
- **WHEN** the `/metrics` endpoint is scraped
- **THEN** the response SHALL include `http_requests_total` counter with labels: `method`, `path`, `status`

#### Scenario: Metrics include request duration
- **WHEN** the `/metrics` endpoint is scraped
- **THEN** the response SHALL include `http_request_duration_seconds` histogram with labels: `method`, `path`, `status`

#### Scenario: Metrics include in-flight requests
- **WHEN** the `/metrics` endpoint is scraped
- **THEN** the response SHALL include `http_requests_in_progress` gauge with label: `method`

### Requirement: Excluded paths from metrics
The `/metrics` endpoint itself SHALL NOT be instrumented to avoid recursion.

#### Scenario: Self-scrape excluded
- **WHEN** a GET request is sent to `/metrics`
- **THEN** the request counter SHALL NOT increment for this path
