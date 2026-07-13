## ADDED Requirements

### Requirement: Backend Sentry integration
The backend SHALL integrate Sentry SDK to capture and report unhandled exceptions and errors.

#### Scenario: Unhandled exception reported
- **WHEN** an unhandled exception occurs in a FastAPI endpoint
- **THEN** Sentry captures the exception with stack trace, request data, and environment context

#### Scenario: Handled exception with manual capture
- **WHEN** code catches an exception and calls `sentry_sdk.capture_exception()`
- **THEN** Sentry records the exception with custom context

#### Scenario: Sentry initialized with DSN
- **WHEN** the application starts
- **THEN** Sentry SHALL be initialized with the DSN from `SENTRY_DSN` environment variable
- **AND** SHALL set `traces_sample_rate` to a configurable value
- **AND** SHALL set `environment` from `ENVIRONMENT` env var (default: `development`)

### Requirement: Frontend Sentry integration
The React frontend SHALL integrate Sentry to capture client-side errors.

#### Scenario: React error boundary catches error
- **WHEN** a React component throws an unhandled error
- **THEN** Sentry captures the error with component stack trace

#### Scenario: Sentry initialized conditionally
- **WHEN** `VITE_SENTRY_DSN` environment variable is set
- **THEN** Sentry SHALL be initialized on app startup
- **AND** SHALL NOT block the app if DSN is missing (graceful degradation)
