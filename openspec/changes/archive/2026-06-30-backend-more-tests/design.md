## Context

The backend test suite (17 tests in test_finanzas.py + test_auth.py) covers basic form-based CRUD and auth flows but has no tests for:
- REST API JSON endpoints under `/api/v1/` (finance summary, notes CRUD, events)
- Module-level tests for metas (goals) and ajustes (preferences) added in C-03
- Security hardening: verifying every endpoint rejects unauthenticated requests
- CORS header validation
- Pagination correctness under load

The existing conftest.py provides `engine`, `db_session`, `client`, `auth_client`, and `test_user`/`test_category` fixtures. Tests use `pytest.mark.asyncio` and `httpx.AsyncClient`.

## Goals / Non-Goals

**Goals:**
- Integration tests for all `/api/v1/` endpoints (finance, notes, events) via JSON API
- Module tests for metas and ajustes (service layer)
- Security gate: every endpoint without cookie returns 401
- CORS header presence validation
- Pagination load test (100 transactions, verify page boundaries)
- 70+ total passing tests
- Reusable fixtures in conftest.py for API testing

**Non-Goals:**
- No changes to production code
- No new external dependencies
- No frontend tests
- No performance benchmarks (only pagination correctness)

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test style | pytest + httpx.AsyncClient via existing fixtures | Matches existing pattern; zero new deps |
| API vs form tests | New API test files test JSON endpoints directly | Form-based tests already exist in test_finanzas.py; API tests cover the other access path |
| Module tests | Test service functions directly using db_session | Avoid HTTP layer for pure business logic; faster, more precise |
| Auth gate | Dedicated test file with parametrized endpoint list | DRY: one test function iterates all protected endpoints |
| CORS test | Single test checking response headers | Simple validation that CORS middleware is active |
| Pagination test | Single file creating 100 transactions via test helper | Verifies backend pagination logic, not frontend |
| conftest.py enhancements | Add `seed_transactions` and `seed_notes` fixtures | Reduce duplication across test files |

## Risks / Trade-offs

- [Risk] API endpoints may differ from expected paths → Mitigation: enumerate actual routes from `app/main.py`
- [Risk] In-memory SQLite vs production SQLite differences → Mitigation: same DB engine, our tests validate behavior not performance
- [Risk] Auth gate test may fail if endpoint requires specific preconditions → Mitigation: test for 401/403 before any data setup
- [Trade-off] Module tests for metas/ajustes duplicate some integration coverage → Acceptable: module tests catch logic errors faster
