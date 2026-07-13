## ADDED Requirements

### Requirement: HTML routes respond with valid HTTP status

The system SHALL confirm that all HTML routes render successfully after the Jinja2 template migration, returning HTTP 200 (or 302 redirect to login when unauthenticated).

#### Scenario: Authenticated route returns 200

- **WHEN** a request is made to an HTML route with a valid authentication cookie
- **THEN** the response SHALL have HTTP status 200

#### Scenario: Unauthenticated route redirects to login

- **WHEN** a request is made to an HTML route without authentication
- **THEN** the response SHALL have HTTP status 302 and redirect to `/auth/login`

### Requirement: No orphaned dependency declarations

The system SHALL not declare dependencies in `requirements.txt` that are not imported by any module.

#### Scenario: slowapi is not declared

- **WHEN** inspecting `backend/requirements.txt`
- **THEN** `slowapi` SHALL NOT appear in the file

### Requirement: No orphaned utility code

The system SHALL not retain utility modules that are no longer referenced by any route or service.

#### Scenario: render_utils.py does not exist

- **WHEN** inspecting the `backend/app/core/` directory
- **THEN** `render_utils.py` SHALL NOT exist
