## Why

The existing backend tests cover basic CRUD and auth flows but leave gaps in REST API integration, module-level tests for metas and ajustes (from C-03), security hardening (auth gate, CORS), and load/pagination scenarios. Adding these improves regression safety before frontend integration.

## What Changes

- New integration tests for `/api/v1/` endpoints (finance, notes, events) using JSON API
- New module tests for `metas` (goals) and `ajustes` (preferences) modules
- Security tests: each endpoint without cookie returns 401, CORS header validation
- Load/pagination test: 100 transactions with pagination correctness
- Enhanced `conftest.py` with reusable fixtures for REST API client
- Target: 70+ passing tests

## Capabilities

### New Capabilities
- `backend-testing`: Integration, module, security, and load tests for the FastAPI backend

### Modified Capabilities
<!-- No existing specs to modify — this extends the test suite defined in the foundation archive spec -->

## Impact

- `backend/tests/conftest.py` — new fixtures (api_auth_client, seeded data)
- `backend/tests/test_api_finance.py` — new file
- `backend/tests/test_api_notes.py` — new file
- `backend/tests/test_api_events.py` — new file
- `backend/tests/test_metas.py` — new file
- `backend/tests/test_ajustes.py` — new file
- `backend/tests/test_auth_gate.py` — new file
- `backend/tests/test_cors.py` — new file
- `backend/tests/test_pagination.py` — new file
- No changes to production code, no new dependencies
