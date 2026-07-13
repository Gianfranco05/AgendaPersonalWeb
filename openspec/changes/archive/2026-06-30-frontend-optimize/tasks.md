## 1. Dependencies & tooling

- [x] 1.1 Add `rollup-plugin-visualizer` and `vite-plugin-compression` as devDependencies
- [x] 1.2 Install new dependencies with `npm install`

## 2. Vite build configuration

- [x] 2.1 Configure `manualChunks` in `vite.config.ts`: `vendor-react`, `vendor-ui`, `vendor-utils`
- [x] 2.2 Add `rollup-plugin-visualizer` with `gzipSize: true` and `ANALYZE` env gate
- [x] 2.3 Add `vite-plugin-compression` with gzip (and brotli if available) to the plugins array

## 3. Lazy loading routes

- [x] 3.1 Replace static imports in `App.tsx` with `React.lazy()` for FinancePage, NotesPage, KanbanBoard, EventsPage
- [x] 3.2 Add `Suspense` wrapper with `LoadingSkeleton` fallback for each lazy route
- [x] 3.3 Keep DashboardPage, GoalsPage, SettingsPage, LoginPage, RegisterPage as static imports (always needed)

## 4. Dynamic library imports

- [x] 4.1 In `FinancePage.tsx`, replace `import ... from 'recharts'` with `const Recharts = await import('recharts')` pattern
- [x] 4.2 In `NotesPage.tsx`, replace `import ... from '@uiw/react-md-editor'` with dynamic `import()` pattern
- [x] 4.3 Handle loading/error states for dynamic imports within each page component

## 5. LoadingSkeleton integration

- [x] 5.1 Ensure `LoadingSkeleton` has a `page` type variant suitable for full-page fallback
- [x] 5.2 Map each lazy page to the appropriate skeleton type and use it as Suspense fallback

## 6. Build verification & analysis

- [x] 6.1 Run `npm run build` and verify vendor chunks are generated correctly
- [x] 6.2 Verify gzipped total is under 500KB
- [x] 6.3 Run visualizer to confirm recharts and @uiw/react-md-editor are in their respective chunks
- [x] 6.4 Verify all routes work correctly via `npm run dev`
