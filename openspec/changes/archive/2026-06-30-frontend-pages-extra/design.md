## Context

LifeOS currently has four modules (Dashboard, Finance, Notes, Tasks) with a consistent pattern: page component, hooks for SWR data fetching, endpoint mocks in `src/api/endpoints.ts`, and types in `src/types/index.ts`. Events already has a `CalendarEvent` type, a `useEvents` hook (SWR), and mock endpoints (`fetchEvents`, `createEvent`) — but no dedicated page. Goals has nothing yet. Settings and RegisterPage are missing entirely.

## Goals / Non-Goals

**Goals:**
- EventsPage with monthly calendar grid, CRUD modal, upcoming list
- GoalsPage with board, progress visualization, check-in mechanism
- SettingsPage with display name, email, theme toggle (light/dark)
- RegisterPage that POSTs to auth endpoint and redirects to /login
- Update Layout.tsx sidebar with new links; update App.tsx routing
- Consume existing `/api/v1/events` endpoint; prepare goals mock layer for `/api/v1/goals`

**Non-Goals:**
- No backend changes (mock data fallback for goals)
- No drag-and-drop calendar (simplified month grid with click-to-select dates)
- No recurring event support
- No user registration validation (minimal form)
- No complex settings (no password change, no 2FA)

## Decisions

1. **Calendar: Pure CSS grid, no library**
   - Why: Avoiding a heavy calendar dependency for a simple month grid. Build a `CalendarGrid` component using Tailwind grid + manual month/week/day calculation. Date selection via state, event dots overlay.
   - Trade-off: No drag-to-create events; user clicks a day and opens EventForm modal.

2. **Goals progress: SVG ring per goal + horizontal bar**
   - Why: Visual progress is the primary UX goal. Use inline SVG for a circular progress ring on each GoalCard (lightweight, no charting dep), plus a thin horizontal bar below for quick scanning.

3. **Check-in: Toggle button per goal**
   - Why: Daily check-in is a simple yes/no action. A `CheckInButton` calls `updateGoalProgress` which increments the `current` count. No separate "check-in date" tracking needed for MVP.

4. **Settings: localStorage for theme**
   - Why: No backend settings endpoint yet. Theme preference stored in localStorage, applied via a `<html data-theme="dark">` attribute toggle in a simple React context.

5. **RegisterPage: standalone, no sidebar link**
   - Why: Registration is a pre-auth flow. It lives at `/register`, uses the same auth API client. After successful POST, redirects to `/login` with a success message.

6. **Mock-first for goals**
   - Why: Goals backend endpoint doesn't exist yet. Follow the established `MOCK_ENABLED` pattern in `endpoints.ts` so the page works immediately and seamlessly switches to real API when available.

7. **Route paths**: `/events`, `/goals`, `/settings` under the protected layout; `/register` outside it (public).

## Risks / Trade-offs

- **Mock goals data diverges from real API shape** → Mitigation: keep the `Goal` interface lean and match expected backend contract (`id`, `title`, `description`, `goal_type`, `target`, `current`, `unit`, `deadline`, `color`).
- **Calendar grid logic is error-prone** → Mitigation: implement as a pure utility function `getMonthGrid(year, month)` that returns a flat array of date objects, tested against known calendar months.
- **Settings page is low priority and may change** → Mitigation: keep it minimal; only persist what's needed for MVP (display name, theme). Expand later when backend settings endpoint exists.
