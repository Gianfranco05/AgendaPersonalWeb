## ADDED Requirements

### Requirement: Axios client uses correct base configuration
The system SHALL create an Axios instance with the correct baseURL, withCredentials flag, and JSON content type header.

#### Scenario: Uses VITE_API_URL as baseURL
- **WHEN** `VITE_API_URL` is set to `http://localhost:8000`
- **THEN** the Axios client SHALL have `baseURL` set to `http://localhost:8000`

#### Scenario: Falls back to empty baseURL
- **WHEN** `VITE_API_URL` is not set
- **THEN** the Axios client SHALL have `baseURL` set to `""`

#### Scenario: Sets withCredentials to true
- **WHEN** the Axios client is created
- **THEN** it SHALL have `withCredentials` set to `true`

#### Scenario: Sets default Content-Type header
- **WHEN** the Axios client is created
- **THEN** it SHALL have `Content-Type` header set to `application/json`

### Requirement: Axios interceptor handles 401 responses
The system SHALL intercept HTTP 401 responses and redirect the user to the login page.

#### Scenario: Passes through successful responses
- **WHEN** a successful response (status 200) is received
- **THEN** the interceptor SHALL return the response unchanged

#### Scenario: Redirects to login on 401
- **WHEN** a 401 response is received
- **THEN** the interceptor SHALL set `window.location.href` to `/login` and reject the promise

#### Scenario: Passes through non-401 errors
- **WHEN** a 403 or 500 response is received
- **THEN** the interceptor SHALL reject the promise without redirecting
