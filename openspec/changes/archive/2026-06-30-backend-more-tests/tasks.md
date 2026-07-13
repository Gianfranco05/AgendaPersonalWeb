## 1. conftest.py — seed fixtures

- [x] 1.1 Add `seed_transactions` fixture that creates N transactions for the test user with varied types/dates
- [x] 1.2 Add `seed_notes` fixture that creates N notes for the test user with varied content

## 2. Security tests

- [x] 2.1 Create `test_auth_gate.py` with parametrized test covering all 20 `/api/v1/` endpoints returning 401 without cookie
- [x] 2.2 Create `test_cors.py` — test that API responses include `Access-Control-Allow-Origin` header

## 3. Pagination load test

- [x] 3.1 Create `test_pagination.py` — seed 100 transactions, verify page boundaries (10 per page), non-overlapping items, total count

## 4. Verify and count

- [x] 4.1 Run full test suite with `pytest backend/tests/ -v`, count passing tests, verify target of 70+
