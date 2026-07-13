# real-api-auth Specification

## Purpose
TBD - created by archiving change frontend-real-api. Update Purpose after archive.
## Requirements
### Requirement: Login against real backend
The system SHALL authenticate users via `POST /api/v1/auth/login` when mock mode is disabled.

#### Scenario: Successful login
- **WHEN** `login(email, password)` is called with valid credentials
- **THEN** `authApi.login()` SHALL `POST` to `/api/v1/auth/login`

#### Scenario: Invalid credentials
- **WHEN** `login(email, password)` is called with invalid credentials
- **THEN** it SHALL throw an error with a descriptive message

### Requirement: Logout against real backend
The system SHALL end the session via `POST /api/v1/auth/logout` when mock mode is disabled.

#### Scenario: Successful logout
- **WHEN** `logout()` is called
- **THEN** `authApi.logout()` SHALL `POST` to `/api/v1/auth/logout`

### Requirement: Get current user from backend
The system SHALL fetch the authenticated user via `GET /api/v1/auth/me` when mock mode is disabled.

#### Scenario: Authenticated user
- **WHEN** `getMe()` is called and user is authenticated
- **THEN** `authApi.getMe()` SHALL `GET` from `/api/v1/auth/me` and return `AuthUser`

#### Scenario: Unauthenticated user
- **WHEN** `getMe()` is called and user is not authenticated
- **THEN** it SHALL throw a 401 error

### Requirement: LoginPage hides registration link
The LoginPage SHALL NOT display a link to `/auth/register` since registration is not available.

#### Scenario: LoginPage renders
- **WHEN** LoginPage is rendered
- **THEN** there SHALL be no clickable link to `/auth/register`

