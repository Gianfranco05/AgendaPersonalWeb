## ADDED Requirements

### Requirement: Events from real API
The system SHALL fetch events from `GET /api/v1/events` when mock mode is disabled.

#### Scenario: Successful events fetch
- **WHEN** `fetchEvents()` is called and mock is disabled
- **THEN** it SHALL fetch from `GET /api/v1/events`

#### Scenario: Create event
- **WHEN** `createEvent()` is called and mock is disabled
- **THEN** it SHALL `POST` to `/api/v1/events` with the event body

### Requirement: Events error handling
When an API request for events fails, the hook SHALL expose the error without clearing previously loaded data.

#### Scenario: Events fetch error
- **WHEN** the backend returns an error for events
- **THEN** `useEvents()` SHALL expose the error and keep stale data
