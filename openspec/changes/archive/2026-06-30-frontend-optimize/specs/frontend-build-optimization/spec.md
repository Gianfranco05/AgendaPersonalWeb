## ADDED Requirements

### Requirement: Build with manual vendor chunks
The Vite build SHALL split vendor dependencies into three manual chunks: `vendor-react` (react, react-dom, react-router-dom), `vendor-ui` (lucide-react, recharts, @uiw/react-md-editor), and `vendor-utils` (axios, swr, zustand, zod, react-hook-form).

#### Scenario: Production build produces vendor chunks
- **WHEN** `npm run build` executes
- **THEN** the output `dist/` directory SHALL contain `vendor-react-*.js`, `vendor-ui-*.js`, and `vendor-utils-*.js` files

### Requirement: Lazy-loaded page routes
FinancePage, NotesPage, KanbanBoard, and EventsPage SHALL be loaded via `React.lazy()` with `Suspense` fallback.

#### Scenario: Navigation triggers lazy load
- **WHEN** user navigates to `/finances` for the first time
- **THEN** the FinancePage chunk SHALL be fetched dynamically and rendered with a `LoadingSkeleton` fallback

#### Scenario: Non-visited pages are not loaded
- **WHEN** user visits only `/` (Dashboard)
- **THEN** the JavaScript chunks for FinancePage, NotesPage, KanbanBoard, and EventsPage SHALL NOT be loaded

### Requirement: Dynamic imports for heavy libraries
`recharts` SHALL be dynamically imported only within FinancePage. `@uiw/react-md-editor` SHALL be dynamically imported only within NotesPage.

#### Scenario: FinancePage without recharts in main bundle
- **WHEN** user loads any page other than `/finances`
- **THEN** `recharts` SHALL NOT appear in the initial JavaScript bundle

#### Scenario: NotesPage without MD editor in main bundle
- **WHEN** user loads any page other than `/notes`
- **THEN** `@uiw/react-md-editor` SHALL NOT appear in the initial JavaScript bundle

### Requirement: LoadingSkeleton fallback
Each lazy-loaded page SHALL display a `LoadingSkeleton` component while its chunk is being fetched.

#### Scenario: Skeleton shows during chunk fetch
- **WHEN** user navigates to a lazy-loaded page and the chunk is loading
- **THEN** the `LoadingSkeleton` component SHALL be visible until the chunk resolves

### Requirement: Bundle size target
The total gzipped production build SHALL be under 500KB.

#### Scenario: Build size verification
- **WHEN** `npm run build` completes
- **THEN** the total gzip size of all output `.js` files SHALL be less than 512000 bytes

### Requirement: Build analysis visualizer
The project SHALL include a `rollup-plugin-visualizer` configuration to analyze bundle composition.

#### Scenario: Visualizer generates report
- **WHEN** `npm run build` executes with `ANALYZE=true` or the visualizer is enabled
- **THEN** a `stats.html` or bundle visualization file SHALL be generated in the output directory

### Requirement: Gzip/brotli compression
Production builds SHALL generate pre-compressed `.gz` and/or `.br` variants of all output files for CDN/serving optimization.

#### Scenario: Compressed artifacts exist
- **WHEN** `npm run build` completes
- **THEN** the `dist/` directory SHALL contain `.gz` files for each `.js` and `.css` output file
