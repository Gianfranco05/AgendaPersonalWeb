## 1. Foundation

- [x] 1.1 Add `Goal` interface to `src/types/index.ts` (fields: id, title, description, goal_type, target, current, unit, deadline, color)
- [x] 1.2 Create `src/hooks/useGoals.ts` with SWR-based hooks: `useGoals()`, `addGoal()`, `updateGoal()`, `removeGoal()`, `updateGoalProgress()`
- [x] 1.3 Add goal API mocks in `src/api/endpoints.ts`: `fetchGoals`, `createGoal`, `updateGoal`, `deleteGoal`, `updateGoalProgress` with `MOCK_ENABLED` pattern
- [x] 1.4 Extend events mocks in `src/api/endpoints.ts` with `updateEvent` and `deleteEvent` (currently only fetch + create exist)

## 2. EventsPage

- [x] 2.1 Create `src/pages/Events/CalendarGrid.tsx` — pure component rendering a monthly calendar grid (Mon–Sun, day cells, prev/next navigation, event dots)
- [x] 2.2 Create `src/pages/Events/EventList.tsx` — sorted upcoming events list with empty state and delete with confirmation
- [x] 2.3 Create `src/pages/Events/EventForm.tsx` — modal form with React Hook Form + Zod validation (title, description, date, time, all_day toggle, location, color)
- [x] 2.4 Create `src/pages/Events/EventsPage.tsx` — orchestrator page composing CalendarGrid + EventList + EventForm, with loading skeleton and empty states

## 3. GoalsPage

- [x] 3.1 Create `src/pages/Goals/GoalCard.tsx` — card with SVG progress ring, horizontal progress bar, deadline indicator, edit/delete/check-in buttons
- [x] 3.2 Create `src/pages/Goals/GoalForm.tsx` — modal form with React Hook Form + Zod (title, description, goal_type, target, unit, deadline, color)
- [x] 3.3 Create `src/pages/Goals/CheckInButton.tsx` — button that calls `updateGoalProgress` (increment for numeric, toggle for binary)
- [x] 3.4 Create `src/pages/Goals/GoalsPage.tsx` — orchestrator with responsive grid of GoalCards, GoalForm modal, loading skeleton, empty state

## 4. SettingsPage

- [x] 4.1 Create `src/context/ThemeContext.tsx` — React context providing theme value and toggle function, applied at `<html>` level
- [x] 4.2 Create `src/pages/Settings/SettingsPage.tsx` — simple form with display name, email (read-only), theme toggle, consuming ThemeContext

## 5. Navigation & Routes

- [x] 5.1 Create `src/pages/Auth/RegisterPage.tsx` — form with name, email, password + POST to auth register endpoint + redirect to /login with success message
- [x] 5.2 Update `src/components/Layout.tsx` — add nav items for Events (Calendar icon), Goals (Target icon), Settings (Settings icon)
- [x] 5.3 Update `src/App.tsx` — add routes: /events → EventsPage, /goals → GoalsPage, /settings → SettingsPage (protected), /register → RegisterPage (public)
