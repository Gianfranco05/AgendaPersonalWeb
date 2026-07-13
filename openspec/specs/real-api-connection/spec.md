# real-api-connection Specification

## Purpose
TBD - created by archiving change frontend-real-api. Update Purpose after archive.
## Requirements
### Requirement: Axios client configurable via env vars
The system SHALL read `VITE_API_URL` from environment to set the Axios `baseURL`. If `VITE_API_URL` is not set, it SHALL default to empty string (Vite proxy mode).

#### Scenario: VITE_API_URL is set
- **WHEN** `VITE_API_URL` equals `http://localhost:8000`
- **THEN** Axios client SHALL use `http://localhost:8000` as `baseURL`

#### Scenario: VITE_API_URL is not set
- **WHEN** `VITE_API_URL` is undefined or empty
- **THEN** Axios client SHALL use `baseURL: ''` (requests go through Vite proxy)

### Requirement: Vite proxy covers /api/v1
The Vite dev server SHALL proxy `/api/v1/*` requests to the backend server at `VITE_PROXY_TARGET` (default `http://localhost:8000`).

#### Scenario: Proxy forwards /api/v1 requests
- **WHEN** frontend makes a request to `/api/v1/finance/summary`
- **THEN** Vite proxy SHALL forward it to `http://localhost:8000/api/v1/finance/summary`

#### Scenario: Proxy target configurable
- **WHEN** `VITE_PROXY_TARGET` env var is set to `http://backend:8000`
- **THEN** Vite proxy SHALL forward to `http://backend:8000`

### Requirement: Mock mode controlled by env var
The system SHALL read `VITE_MOCK_ENABLED` from environment (default `false`) to determine whether to return mock data.

#### Scenario: Mock enabled
- **WHEN** `VITE_MOCK_ENABLED` equals `true`
- **THEN** all API functions SHALL return mock data

#### Scenario: Mock disabled
- **WHEN** `VITE_MOCK_ENABLED` is `false` or unset
- **THEN** all API functions SHALL make real HTTP requests

### Requirement: 401 interceptor redirects to login
The Axios client SHALL have a response interceptor that redirects to `/login` on 401 responses.

#### Scenario: Backend returns 401
- **WHEN** any API request receives a 401 response
- **THEN** the user SHALL be redirected to `/login`

#### Scenario: Successful request does not redirect
- **WHEN** any API request succeeds (non-401 status)
- **THEN** no redirect SHALL occur

