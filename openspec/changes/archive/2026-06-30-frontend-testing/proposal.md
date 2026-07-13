## Why

The frontend currently has zero tests. As the codebase grows, manual regression becomes error-prone and slows down development. Adding tests ensures components render correctly, hooks behave as expected, and API calls are properly configured — reducing the risk of breaking existing functionality when adding new features.

## What Changes

- Install and configure Vitest + React Testing Library + jsdom as the test runner and utilities
- Add `vitest.config.ts` with `@/` → `src/` path alias resolution matching the existing tsconfig
- Write unit tests for shared components: Layout, LoadingSkeleton, ErrorBoundary, ProtectedRoute
- Write unit tests for feature components: FinanceWidget, TransactionModal, KanbanBoard, NoteEditor
- Write unit tests for hooks: useKanban (CRUD + localStorage sync), useFinance (SWR mocking)
- Write smoke tests for pages: DashboardPage, FinancePage
- Write unit tests for the API client: Axios interceptor, baseURL, withCredentials
- Add `npm run test` and `npm run test:coverage` scripts
- Configure coverage reporting targeting 50%+ on shared components

## Capabilities

### New Capabilities
- `component-testing`: Unit and integration tests for React components using Vitest + RTL
- `hook-testing`: Unit tests for custom hooks, including localStorage and SWR mocking
- `api-client-testing`: Unit tests for Axios client configuration and interceptors

### Modified Capabilities

None — no existing specs to modify.

## Impact

- **Dependencies**: Adds `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`, `@vitejs/plugin-react` (already present)
- **Config**: New `vitest.config.ts` file; no changes to existing configs beyond possible tsconfig alignment
- **Code**: No production code changes — all additions are test files alongside existing source files
- **Workflow**: Adds `npm run test` and `npm run test:coverage` commands
