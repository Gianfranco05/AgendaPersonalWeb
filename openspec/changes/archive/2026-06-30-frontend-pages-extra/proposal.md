## Why

LifeOS currently has Dashboard, Finance, Notes, and Tasks modules, but lacks dedicated pages for Events and Goals — two core personal management domains. The existing EventsWidget on the Dashboard only shows upcoming events; there's no full calendar view, no event CRUD, and no Goals module at all. Settings are also missing, and RegisterPage is just a TODO. This change closes those gaps with fully functional pages.

## What Changes

- **EventsPage**: Monthly calendar grid with day cells, EventForm modal (create/edit), EventList sidebar showing upcoming events, consuming `/api/v1/events`
- **GoalsPage**: Kanban-style board of goals with visual progress bars, GoalCard with progress ring, GoalForm modal, CheckInButton for daily check-in, consuming `/api/v1/goals`
- **SettingsPage**: Simple form with display name, email, theme toggle (light/dark as localStorage preference)
- **RegisterPage**: Minimal functional component that POSTs to auth register endpoint and redirects to `/login`
- **Sidebar**: Update `Layout.tsx` navigation with links to Events, Goals, Settings (RegisterPage does not get a sidebar link)
- **New types**: `Goal` interface in `src/types/index.ts`
- **New hooks**: `useGoals.ts` (SWR-based, following useEvents.ts pattern)
- **New API endpoints in mock**: `fetchGoals`, `createGoal`, `updateGoal`, `deleteGoal`, `updateGoalProgress` in `src/api/endpoints.ts`

## Capabilities

### New Capabilities
- `events-page`: Full monthly calendar, event CRUD, upcoming events list
- `goals-page`: Goals board with progress tracking, check-in system

### Modified Capabilities
*(No existing specs to modify — initial spec creation)*

## Impact

- `frontend/src/pages/Events/EventsPage.tsx` — new page
- `frontend/src/pages/Goals/GoalsPage.tsx` — new page
- `frontend/src/pages/Settings/SettingsPage.tsx` — new page
- `frontend/src/pages/Auth/RegisterPage.tsx` — new page
- `frontend/src/components/Layout.tsx` — add nav links
- `frontend/src/App.tsx` — add routes
- `frontend/src/types/index.ts` — add Goal interface
- `frontend/src/hooks/useGoals.ts` — new hook
- `frontend/src/api/endpoints.ts` — add goal mocks + endpoints
- No backend changes — existing `/api/v1/events` endpoint consumed; goals consume `/api/v1/goals` when available (mock data fallback)
