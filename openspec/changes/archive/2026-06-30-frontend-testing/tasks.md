## 1. Setup

- [x] 1.1 Install Vitest, React Testing Library, jsdom, and related dev dependencies
- [x] 1.2 Create `vitest.config.ts` with `@/` → `src/` alias using `resolve.alias`
- [x] 1.3 Add `test` and `test:coverage` scripts to `package.json`
- [x] 1.4 Add global test setup file with `@testing-library/jest-dom` import
- [x] 1.5 Create test utility helpers (`renderWithProviders`, mock auth store, mock router wrapper)

## 2. API Client Tests

- [x] 2.1 Write test verifying Axios client baseURL uses `VITE_API_URL` with fallback to `""`
- [x] 2.2 Write test verifying `withCredentials: true` and `Content-Type: application/json` headers
- [x] 2.3 Write test verifying 401 response interceptor redirects to `/login`
- [x] 2.4 Write test verifying non-401 errors are rejected without redirect

## 3. Shared Component Tests

- [x] 3.1 Write tests for `LoadingSkeleton`: card, table, and widget variants render correct bar counts
- [x] 3.2 Write tests for `ErrorBoundary`: catches errors, shows default fallback, uses custom fallback, resets on retry
- [x] 3.3 Write tests for `ProtectedRoute`: shows spinner while loading, renders Outlet when authenticated, redirects to /login when not
- [x] 3.4 Write tests for `Layout`: renders all nav items, shows user initials/name, shows fallback for null user

## 4. Hook Tests

- [x] 4.1 Write tests for `useKanban`: loads mock data when localStorage is empty, loads persisted data, addTask creates pending task, moveTask changes status, deleteTask removes task
- [x] 4.2 Write test for `useKanban` localStorage persistence after mutations
- [x] 4.3 Write tests for `useFinanceSummary` and `useTransactions` with SWR `provider` + `fallback`
- [x] 4.4 Write tests for `saveTransaction` (create + update modes) and `removeTransaction` using mocked API functions

## 5. Feature Component Tests

- [x] 5.1 Write tests for `FinanceWidget`: loading state renders skeletons, summary displays formatted values
- [x] 5.2 Write tests for `TransactionModal`: create mode shows empty form with "Agregar transacción", edit mode pre-fills data, cancel calls onClose
- [x] 5.3 Write tests for `KanbanBoard`: renders tasks grouped by status, shows empty state
- [x] 5.4 Write tests for `NoteEditor`: renders markdown editor in create mode, pre-fills fields in edit mode

## 6. Page Smoke Tests

- [x] 6.1 Write smoke test for `DashboardPage`: renders without crashing with mocked widget data
- [x] 6.2 Write smoke test for `FinancePage`: renders without crashing with mocked SWR data

## 7. Coverage & CI

- [x] 7.1 Configure coverage threshold at 50%+ for shared components (`src/components/`)
- [x] 7.2 Verify all tests pass with `npm run test`
- [x] 7.3 Verify coverage report with `npm run test:coverage`
