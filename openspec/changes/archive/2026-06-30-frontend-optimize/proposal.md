## Why

The frontend build bundles all pages and third-party libraries into a single monolithic chunk, resulting in slow initial load times and poor performance. Users download the entire Finance page (including recharts) and Notes page (including the MD editor) even when navigating only to Dashboard or Settings. Optimizing the bundle is critical for perceived performance and resource efficiency.

## What Changes

- **Code-splitting**: Convert FinancePage, NotesPage, KanbanBoard, and EventsPage to lazy-loaded routes via `React.lazy()` + `Suspense`
- **Dynamic imports**: `recharts` imported only within FinancePage, `@uiw/react-md-editor` only within NotesPage
- **Loading indicators**: Add `LoadingSkeleton` wrapper for each lazy chunk
- **Build optimization**: Configure `rollup-plugin-visualizer`, manual vendor chunks, and gzip/brotli compression in Vite
- **Vendor chunking**: Split vendor code into `vendor-react.js`, `vendor-ui.js`, `vendor-utils.js`
- **Target**: Production build < 500KB gzipped

## Capabilities

### New Capabilities
- `frontend-build-optimization`: Build-time optimization configuration (manual chunks, compression, visualizer)

### Modified Capabilities
<!-- No existing specs are modified — behavior is unchanged, only loading mechanism changes -->

## Impact

- **`frontend/vite.config.ts`**: Add manual chunks, compression plugin, visualizer plugin
- **`frontend/src/App.tsx`**: Replace static imports with `React.lazy()` + `Suspense` for 4 pages
- **`frontend/src/pages/Finance/FinancePage.tsx`**: Dynamic import of `recharts`
- **`frontend/src/pages/Notes/NotesPage.tsx`**: Dynamic import of `@uiw/react-md-editor`
- **`frontend/package.json`**: Add devDependencies for `rollup-plugin-visualizer`, `vite-plugin-compression`
- **No API or backend changes**
