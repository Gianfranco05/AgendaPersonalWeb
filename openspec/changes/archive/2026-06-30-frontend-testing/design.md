## Context

The frontend is a React + Vite + TypeScript app with zero test coverage. Existing dependencies include Vitest-compatible tools (Vite, React Testing Library ecosystem). The `@/` → `src/` path alias is already configured in `tsconfig.json` but not in the Vite config.

Components range from pure presentational (`LoadingSkeleton`) to stateful with hooks (`Layout`, `ProtectedRoute`, `KanbanBoard`). Custom hooks use localStorage (`useKanban`) and SWR for API data fetching (`useFinance`). The API client is a thin Axios wrapper with a 401 interceptor.

## Goals / Non-Goals

**Goals:**
- Establish a repeatable test infrastructure (Vitest + RTL + jsdom) for all future development
- Achieve 50%+ coverage on shared components (`src/components/`)
- Cover core business logic hooks (useKanban CRUD, useFinance SWR integration)
- Validate API client configuration (baseURL, withCredentials, interceptor)
- Add smoke tests for key pages to catch render regressions

**Non-Goals:**
- 100% coverage across the entire frontend
- E2E or integration tests with a real backend
- Visual regression / snapshot testing
- Performance or load testing
- Testing third-party library internals (recharts, md-editor, dnd)

## Decisions

| Decision | Choice | Rationale | Alternatives Considered |
|----------|--------|-----------|------------------------|
| Test runner | Vitest | Native Vite integration, fast, same TS config | Jest (needs separate config, slower) |
| DOM environment | jsdom | Standard for React component testing, no browser needed | happy-dom (less mature, fewer RTL issues) |
| Component testing | React Testing Library | Encourages testing behavior over implementation | Enzyme (unmaintained), React Test Renderer (limited) |
| Path alias | Reuse `@/` → `src/` from tsconfig | Add `resolve.alias` to `vitest.config.ts` — no duplication | Inline paths in every import (tedious) |
| Hook testing | `renderHook` from RTL | Standard pattern for hooks, works with SWR via wrapper | Manual test components (boilerplate-heavy) |
| SWR mocking | Global `SWRConfig` with `provider` + `fallback` | No need to mock network — inject cached data directly | `vi.mock('swr')` (fragile, couples to implementation) |
| Coverage reporter | `v8` | Native, fast, no Istanbul dependency | `istanbul` (slower, extra binary) |

## Risks / Trade-offs

- **SWR behavior changes between versions** → Pin swr version in tests. If SWR major version bumps, test patterns may need updates.
- **jsdom does not support `window.location` redirects** → The 401 interceptor test needs a mock on `window.location.href` assignment.
- **localStorage tests leak between runs** → Each test must clear `localStorage` in `beforeEach` to avoid state pollution.
- **Drag-and-drop (`@hello-pangea/dnd`) is hard to test** → Skip DnD interactions in unit tests; test the data flow directly via `useKanban` hook.
- **RTL `render` with Router context** → Components using `useNavigate` / `NavLink` need `MemoryRouter` wrapper.
