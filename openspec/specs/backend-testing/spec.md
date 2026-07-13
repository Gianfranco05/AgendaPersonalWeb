# backend-testing Specification

## Purpose
TBD - created by archiving change backend-more-tests. Update Purpose after archive.
## Requirements
### Requirement: Auth gate — every API endpoint returns 401 without cookie
The system SHALL have a dedicated test proving each `/api/v1/` endpoint returns 401 when called without authentication cookie.

#### Scenario: All API endpoints reject unauthenticated requests
- **WHEN** a GET/POST/PUT/DELETE request is sent to any `/api/v1/*` endpoint without an auth cookie
- **THEN** the response status SHALL be 401

#### Scenario: Auth gate test is parametrized
- **WHEN** the auth gate test runs
- **THEN** it SHALL be parametrized over a list of (method, path) tuples covering all API endpoints:
  - `GET /api/v1/finance/summary`
  - `GET /api/v1/finance/transactions`
  - `POST /api/v1/finance/transactions`
  - `PUT /api/v1/finance/transactions/{id}`
  - `DELETE /api/v1/finance/transactions/{id}`
  - `GET /api/v1/finance/categories`
  - `GET /api/v1/notes`
  - `POST /api/v1/notes`
  - `PUT /api/v1/notes/{id}`
  - `DELETE /api/v1/notes/{id}`
  - `GET /api/v1/notes/tags`
  - `GET /api/v1/events`
  - `POST /api/v1/events`
  - `PUT /api/v1/events/{id}`
  - `DELETE /api/v1/events/{id}`
  - `GET /api/v1/goals`
  - `POST /api/v1/goals`
  - `PUT /api/v1/goals/{id}/checkin`
  - `GET /api/v1/settings`
  - `PUT /api/v1/settings`

### Requirement: CORS headers are present in API responses
The system SHALL have a test validating that CORS headers are returned by the FastAPI application.

#### Scenario: API response includes CORS headers
- **WHEN** a request is sent to an API endpoint
- **THEN** the response SHALL include the `Access-Control-Allow-Origin` header

#### Scenario: CORS allows configured origin
- **WHEN** a request is sent with an `Origin` header matching the configured frontend origin
- **THEN** the response SHALL include `Access-Control-Allow-Origin` set to that origin

### Requirement: Pagination correctness with large datasets
The system SHALL have a test that creates 100 transactions and verifies pagination metadata across multiple pages.

#### Scenario: Pagination returns correct page boundaries
- **WHEN** 100 transactions are created and pages of size 10 are requested
- **THEN** each page SHALL contain exactly 10 items (except possibly the last)
- **AND** the total count SHALL be 100
- **AND** consecutive pages SHALL have non-overlapping items

### Requirement: conftest.py provides reusable seed fixtures
The system SHALL enhance `conftest.py` with fixtures that seed test data for reuse across test files.

#### Scenario: seed_transactions fixture creates N transactions
- **WHEN** a test requests `seed_transactions` fixture with a count parameter
- **THEN** that many transactions SHALL be created in the database for the test user
- **AND** they SHALL be available for pagination or filtering tests

#### Scenario: seed_notes fixture creates N notes
- **WHEN** a test requests `seed_notes` fixture
- **THEN** notes SHALL be created in the database for reuse in note-related tests

