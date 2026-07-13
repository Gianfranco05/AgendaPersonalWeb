## Context

LifeOS frontend currently imports all page components and third-party libraries statically at the top of `App.tsx`. This means the entire application — including recharts (Finance), @uiw/react-md-editor (Notes), Kanban drag-and-drop, and Events — is loaded on every navigation. The production build produces a single JS bundle with no code splitting.

The existing `LoadingSkeleton` component already supports `card`, `table`, and `widget` variants and can be reused as the Suspense fallback.

## Goals / Non-Goals

**Goals:**
- Reduce initial bundle size by at least 60% via code-splitting
- Implement `React.lazy()` + `Suspense` for FinancePage, NotesPage, KanbanBoard, EventsPage
- Dynamic import of `recharts` and `@uiw/react-md-editor` only in their respective pages
- Configure manual vendor chunks to leverage long-term browser caching
- Add rollup-plugin-visualizer for build analysis
- Add gzip/brotli compression for production builds
- Achieve production build < 500KB gzipped
- Provide LoadingSkeleton fallback for each lazy chunk

**Non-Goals:**
- Not modifying backend or API layer
- Not changing page functionality or layout
- Not implementing SSR or streaming
- Not optimizing images/fonts (out of scope)

## Decisions

### 1. React.lazy + Suspense over loadable-components
React.lazy() is built into React 19 and requires zero additional dependencies. `@loadable/component` adds ~3KB and provides SSR support we don't need. React.lazy is the standard, lightweight choice for client-only code-splitting.

### 2. Manual chunks over automatic splitting
Vite's `manualChunks` gives us explicit control over vendor grouping. This ensures:
- `vendor-react`: Stable, rarely changes → optimal caching
- `vendor-ui`: UI libraries that change together
- `vendor-utils`: Data/logic utilities

Alternatives considered:
- Vite's default chunking: produces many small chunks, less cache-efficient
- `vite-plugin-chunk-split`: adds abstraction without benefit for our case

### 3. `vite-plugin-compression` over build pipeline
`vite-plugin-compression` runs within the Vite build pipeline, producing `.gz` and optionally `.br` files with zero configuration. The alternative (manual compression via npm postbuild script) is fragile.

### 4. Dynamic import inside component files over route-level
Rather than using `React.lazy` for recharts (which wraps the entire chart component), we use a standard dynamic `import()` inside the FinancePage and NotesPage components. This keeps the lazy boundary at the module level and avoids awkward component wrapping.

### 5. LoadingSkeleton reuse over custom fallbacks
The existing `LoadingSkeleton` component already supports `card`, `table`, and `widget` types. We map each page to the appropriate variant rather than creating new skeleton components.

### 6. Environment-gated visualizer
The visualizer is configured with `gzipSize: true` and `emitFile: true` but only activates when `VITE_ANALYZE=true` or `ANALYZE=true` is set. This keeps the dev experience clean.

## Risks / Trade-offs

- [**Lazy load flash**] → Mitigated by using `LoadingSkeleton` that matches the page layout (card for most pages, widget for dashboard-adjacent pages)
- [**Dynamic import error**] → Both `App.tsx` and page components wrap lazy imports in `ErrorBoundary`, which already exists in the app
- [**Vendor chunk staleness**] → Manual chunk lists need maintenance when dependencies change; mitigated by documenting the chunk strategy in `vite.config.ts` comments
- [**Compression doubles build time**] → `vite-plugin-compression` with `threshold: 1024` only compresses files > 1KB, and gzip-only is fast; brotli is optional
