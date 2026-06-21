## ADDED Requirements

### Requirement: conftest.py provides async SQLite in-memory database with fixture scope
The system SHALL provide a `conftest.py` that creates an async SQLite in-memory database for test isolation, scoped to each test function.

#### Scenario: Each test gets a fresh in-memory database
- **WHEN** two different test functions run
- **THEN** each SHALL have its own isolated SQLite in-memory database with no shared state

#### Scenario: Database tables are created before tests run
- **WHEN** a test function executes
- **THEN** all database tables SHALL be created via metadata.create_all before the test begins

#### Scenario: Database is cleaned up after test completes
- **WHEN** a test function finishes
- **THEN** the in-memory database SHALL be dropped

### Requirement: conftest.py provides httpx.AsyncClient fixture for FastAPI TestClient
The system SHALL provide an `httpx.AsyncClient` fixture configured with the FastAPI app for making async HTTP requests in tests.

#### Scenario: AsyncClient can make requests to the FastAPI app
- **WHEN** a test sends a GET request using the AsyncClient fixture
- **THEN** the response SHALL be returned from the FastAPI application as if it were running

#### Scenario: AsyncClient supports async context manager
- **WHEN** the AsyncClient fixture is used in an async test function
- **THEN** the test SHALL execute without transport errors

### Requirement: test_auth.py covers authentication scenarios
The system SHALL have a `test_auth.py` file covering login success, login failure, registration, and logout.

#### Scenario: Login with valid credentials returns success
- **WHEN** a POST request is sent to the login endpoint with correct username and password
- **THEN** the response status SHALL be 200 and a session cookie SHALL be set

#### Scenario: Login with invalid credentials returns error
- **WHEN** a POST request is sent to the login endpoint with incorrect credentials
- **THEN** the response status SHALL be 401

#### Scenario: Registration creates a new user
- **WHEN** a POST request is sent to the register endpoint with valid user data
- **THEN** the response status SHALL be 200 and the user SHALL be persisted in the database

#### Scenario: Logout clears the session
- **WHEN** a POST request is sent to the logout endpoint with an active session
- **THEN** the response SHALL indicate the session is cleared

### Requirement: test_finanzas.py covers transaction operations
The system SHALL have a `test_finanzas.py` file covering create transaction, list transactions, soft delete, and get balance.

#### Scenario: Create a transaction persists to the database
- **WHEN** a POST request is sent to the transactions endpoint with valid transaction data
- **THEN** the response status SHALL be 200 and the transaction SHALL be retrievable from the database

#### Scenario: List transactions returns all transactions for the user
- **WHEN** a GET request is sent to the transactions list endpoint
- **THEN** the response SHALL include all transactions belonging to the authenticated user

#### Scenario: Soft delete marks a transaction as deleted
- **WHEN** a DELETE request is sent for a specific transaction
- **THEN** the transaction SHALL be marked as deleted but SHALL NOT be physically removed from the database

#### Scenario: Get balance returns correct calculated balance
- **WHEN** a GET request is sent to the balance endpoint
- **THEN** the response SHALL include the correct sum of income minus expenses

### Requirement: test_anotaciones.py covers note operations
The system SHALL have a `test_anotaciones.py` file covering create note with tags, list notes, and archive note.

#### Scenario: Create a note with tags persists correctly
- **WHEN** a POST request is sent to the notes endpoint with title, content, and tags
- **THEN** the response status SHALL be 200 and both note and tag associations SHALL be persisted

#### Scenario: List notes returns all notes for the user
- **WHEN** a GET request is sent to the notes list endpoint
- **THEN** the response SHALL include all notes belonging to the authenticated user

#### Scenario: Archive note marks note as archived
- **WHEN** a note archive operation is performed
- **THEN** the note SHALL be marked as archived without physical deletion

### Requirement: test_eventos.py covers event operations
The system SHALL have a `test_eventos.py` file covering create event, list events, and edit event.

#### Scenario: Create an event persists to the database
- **WHEN** a POST request is sent to the events endpoint with valid event data
- **THEN** the response status SHALL be 200 and the event SHALL be retrievable

#### Scenario: List events returns all events
- **WHEN** a GET request is sent to the events list endpoint
- **THEN** the response SHALL include all events belonging to the authenticated user

#### Scenario: Edit event updates fields correctly
- **WHEN** a PUT request is sent to update an existing event
- **THEN** the event SHALL be updated with the new values in the database

### Requirement: All tests run with pytest and pass
The system SHALL ensure all tests execute successfully using `pytest backend/tests/` with no failures.

#### Scenario: Full test suite passes
- **WHEN** running `pytest backend/tests/`
- **THEN** all discovered tests SHALL pass with exit code 0

#### Scenario: Tests are discoverable by pytest
- **WHEN** pytest scans the `backend/tests/` directory
- **THEN** all test files matching `test_*.py` SHALL be discovered and executed
