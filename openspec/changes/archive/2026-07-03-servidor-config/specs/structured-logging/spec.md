## ADDED Requirements

### Requirement: JSON structured logging
All backend log output SHALL be in JSON format for machine-parsable log aggregation.

#### Scenario: Request log in JSON
- **WHEN** the application logs any message
- **THEN** the output SHALL be a single-line JSON object with `timestamp`, `level`, `logger`, `message`, and `correlation_id` fields

#### Scenario: JSON log level control
- **WHEN** `LOG_LEVEL` environment variable is set
- **THEN** the logger SHALL use that level (default: `INFO`)

### Requirement: Correlation ID propagation
Every request SHALL have a unique correlation ID that propagates through logs.

#### Scenario: Correlation ID generated per request
- **WHEN** a new request arrives at the backend
- **THEN** a UUID correlation ID SHALL be generated if not present in `X-Correlation-ID` header
- **AND** ALL log entries for that request SHALL include the correlation ID

#### Scenario: Correlation ID forwarded from client
- **WHEN** the request includes `X-Correlation-ID` header
- **THEN** the backend SHALL use that value as the correlation ID
