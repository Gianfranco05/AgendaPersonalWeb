## ADDED Requirements

### Requirement: Structured logging using Python stdlib logging module
The system SHALL use the Python standard library `logging` module to emit structured log messages with timestamp, level, and module name for all backend operations.

#### Scenario: Log messages include timestamp
- **WHEN** a log message is emitted
- **THEN** the log output SHALL include an ISO 8601 timestamp

#### Scenario: Log messages include severity level
- **WHEN** a log message is emitted
- **THEN** the log output SHALL include the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

#### Scenario: Log messages include module name
- **WHEN** a log message is emitted from a specific module
- **THEN** the log output SHALL include the module or logger name that generated the message

#### Scenario: Service operations are logged
- **WHEN** a service method is invoked (create, update, delete)
- **THEN** an INFO-level log message SHALL be emitted recording the operation and relevant parameters

### Requirement: Consistent error responses as JSON
The system SHALL return all error responses as JSON objects with `detail` and `status_code` fields for consistent client-side error handling.

#### Scenario: Validation error returns JSON with detail and status_code
- **WHEN** a request fails validation (e.g., missing required field)
- **THEN** the response body SHALL be `{ "detail": "<error message>", "status_code": 422 }` with Content-Type `application/json`

#### Scenario: Not found error returns JSON with detail and status_code
- **WHEN** a requested resource does not exist
- **THEN** the response body SHALL be `{ "detail": "<error message>", "status_code": 404 }` with Content-Type `application/json`

#### Scenario: Internal server error returns JSON with detail and status_code
- **WHEN** an unhandled exception occurs
- **THEN** the response body SHALL be `{ "detail": "<error message>", "status_code": 500 }` with Content-Type `application/json`

### Requirement: TimestampMixin in core/base.py uses SQLite-compatible column type
The system SHALL replace PG_UUID column types in TimestampMixin with String(36) to ensure compatibility with SQLite, which does not support PostgreSQL UUID.

#### Scenario: Timestamp columns use String type on models
- **WHEN** a model inheriting from TimestampMixin is inspected
- **THEN** its timestamp columns SHALL use `String(36)` instead of PG_UUID

#### Scenario: SQLite database accepts timestamp values
- **WHEN** a record with a timestamp is inserted into SQLite
- **THEN** the insert operation SHALL succeed without type errors

### Requirement: Orphaned Jinja2 templates removed
The system SHALL remove any Jinja2 templates in `app/templates/` that are not referenced by any route handler.

#### Scenario: No orphaned template files remain
- **WHEN** inspecting the `app/templates/` directory
- **THEN** every `.html` file present SHALL be referenced by at least one route handler

#### Scenario: Templates referenced by routes are preserved
- **WHEN** a template is rendered by a route handler
- **THEN** that template file SHALL remain in `app/templates/`

### Requirement: Duplicated navbar HTML extracted to a shared render helper
The system SHALL extract repeated navbar HTML code across different route handlers into a single shared rendering helper function.

#### Scenario: Navbar is rendered from a single helper function
- **WHEN** any page renders the navigation bar
- **THEN** it SHALL call a shared helper function rather than inlining duplicated HTML

#### Scenario: Navbar appearance is consistent across all pages
- **WHEN** navigating between different application pages
- **THEN** the navigation bar SHALL render with identical structure and styling on every page

### Requirement: Try/except blocks log the actual exception
The system SHALL log the actual exception details (message and traceback) in all try/except blocks instead of silently swallowing errors or redirecting without context.

#### Scenario: Exception is logged with full traceback
- **WHEN** an exception is caught in a try/except block
- **THEN** the exception message and traceback SHALL be logged at ERROR level

#### Scenario: Silent redirects are replaced with logged errors
- **WHEN** an operation fails and the handler previously redirected silently
- **THEN** the error SHALL be logged before the redirect occurs
