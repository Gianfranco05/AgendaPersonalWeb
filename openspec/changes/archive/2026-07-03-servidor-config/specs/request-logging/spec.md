## ADDED Requirements

### Requirement: Request logging middleware
The backend SHALL log every HTTP request with method, path, status code, duration, and correlation ID.

#### Scenario: Successful request logged
- **WHEN** a client sends a GET request to `/api/v1/notes`
- **THEN** the middleware SHALL log a JSON line with `method: GET`, `path: /api/v1/notes`, `status: 200`, `duration_ms: <number>`, and `correlation_id: <uuid>`

#### Scenario: Error request logged
- **WHEN** a request results in a 4xx or 5xx response
- **THEN** the middleware SHALL log at `WARNING` or `ERROR` level respectively
- **AND** SHALL include `status`, `method`, `path`, `duration_ms`, and `correlation_id`

#### Scenario: Execution time measured
- **WHEN** a request is processed
- **THEN** the middleware SHALL record wall-clock time from request start to response sent
