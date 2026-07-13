## ADDED Requirements

### Requirement: Liveness endpoint
The backend SHALL expose `/livez` to indicate the application process is alive.

#### Scenario: Liveness probe succeeds
- **WHEN** a GET request is sent to `/livez`
- **THEN** the response SHALL have status 200
- **AND** body SHALL contain `{"status": "alive"}`

### Requirement: Readiness endpoint
The backend SHALL expose `/readyz` to indicate the application is ready to serve traffic.

#### Scenario: Readiness probe succeeds
- **WHEN** a GET request is sent to `/readyz`
- **THEN** the response SHALL have status 200
- **AND** body SHALL contain `{"status": "ready"}`

#### Scenario: Readiness probe fails on DB
- **WHEN** the database connection is unavailable
- **THEN** a GET request to `/readyz` SHALL return status 503
- **AND** body SHALL contain `{"status": "not ready", "detail": "database: unreachable"}`

### Requirement: Healthcheck separation
`/livez` SHALL be a simple process check (no dependencies), while `/readyz` SHALL verify database connectivity.

#### Scenario: Livez is always fast
- **WHEN** the process is running
- **THEN** `/livez` SHALL respond within 100ms regardless of dependency states
