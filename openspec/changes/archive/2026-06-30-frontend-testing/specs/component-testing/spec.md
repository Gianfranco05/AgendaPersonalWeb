## ADDED Requirements

### Requirement: Layout component renders navigation and user info
The system SHALL render a sidebar with navigation links, a mobile menu toggle, and the current user's initials and name from the auth store.

#### Scenario: Renders all nav items
- **WHEN** Layout is rendered with an authenticated user
- **THEN** it SHALL display links to Dashboard, Finanzas, Eventos, Metas, Notas, Tareas, Configuración

#### Scenario: Shows user initials and name
- **WHEN** Layout is rendered with a user having `full_name: "Gianfranco Ferraro"`
- **THEN** it SHALL display "GF" as initials and "Gianfranco Ferraro" as the name

#### Scenario: Shows fallback for missing user
- **WHEN** Layout is rendered with `user` being null
- **THEN** it SHALL display "U" as initials and "Usuario" as name

#### Scenario: Calls logout on button click
- **WHEN** the logout button is clicked
- **THEN** it SHALL call `logout()` from the auth store and navigate to `/login`

### Requirement: LoadingSkeleton renders skeletons by type
The system SHALL render animated placeholder bars matching the specified skeleton type (card, table, widget).

#### Scenario: Renders card skeleton by default
- **WHEN** LoadingSkeleton is rendered with no type prop
- **THEN** it SHALL render a card layout with 3 skeleton bars (h-5, h-4, h-4)

#### Scenario: Renders table skeleton
- **WHEN** LoadingSkeleton is rendered with `type="table"` and `rows={2}`
- **THEN** it SHALL render a header row with 5 bars + 2 data rows each with 5 bars

#### Scenario: Renders widget skeleton
- **WHEN** LoadingSkeleton is rendered with `type="widget"`
- **THEN** it SHALL render bars with widths 1/3, 1/2, full, and 4/5

### Requirement: ErrorBoundary catches render errors and shows fallback
The system SHALL catch JavaScript errors in its child component tree and display a fallback UI with a retry button.

#### Scenario: Shows default error UI on error
- **WHEN** a child component throws an error
- **THEN** ErrorBoundary SHALL display a red alert box with "Algo salió mal", the error message, and a "Reintentar" button

#### Scenario: Uses custom fallback when provided
- **WHEN** ErrorBoundary is given a `fallback` prop and a child throws
- **THEN** it SHALL render the custom fallback instead of the default error UI

#### Scenario: Resets error state on retry click
- **WHEN** the "Reintentar" button is clicked in the error state
- **THEN** ErrorBoundary SHALL reset its error state and render children again

### Requirement: ProtectedRoute redirects unauthenticated users
The system SHALL show a loading spinner while auth state is loading, render children if authenticated, or redirect to `/login` if not.

#### Scenario: Shows loading spinner while loading
- **WHEN** ProtectedRoute is rendered with `isLoading=true`
- **THEN** it SHALL render a centered spinning border animation

#### Scenario: Renders children when authenticated
- **WHEN** ProtectedRoute is rendered with `isAuthenticated=true` and `isLoading=false`
- **THEN** it SHALL render `<Outlet />`

#### Scenario: Redirects to login when not authenticated
- **WHEN** ProtectedRoute is rendered with `isAuthenticated=false` and `isLoading=false`
- **THEN** it SHALL render `<Navigate to="/login" replace />`

### Requirement: FinanceWidget renders summary cards
The system SHALL display income, expense, and balance summary cards from the SWR finance summary data.

#### Scenario: Shows loading state
- **WHEN** FinanceWidget is loading and has no data yet
- **THEN** it SHALL render LoadingSkeleton widgets

#### Scenario: Displays summary values
- **WHEN** FinanceWidget receives summary data with income, expense, and balance
- **THEN** it SHALL display the formatted values in three color-coded cards (green for income, red for expenses, purple for balance)

### Requirement: TransactionModal creates and edits transactions
The system SHALL display a modal form for creating new or editing existing financial transactions.

#### Scenario: Opens in create mode
- **WHEN** TransactionModal is rendered with `transaction={null}`
- **THEN** it SHALL show "Agregar transacción" as title and empty form fields

#### Scenario: Opens in edit mode with pre-filled data
- **WHEN** TransactionModal is rendered with an existing transaction
- **THEN** it SHALL show "Editar transacción" as title and pre-fill form fields with the transaction data

#### Scenario: Calls onClose when cancel is clicked
- **WHEN** the cancel button is clicked
- **THEN** it SHALL call the `onClose` callback

### Requirement: KanbanBoard renders tasks in columns
The system SHALL display tasks organized in three columns: Pendiente, En Proceso, Completado.

#### Scenario: Renders tasks grouped by status
- **WHEN** KanbanBoard is rendered with tasks in different statuses
- **THEN** each column SHALL display only tasks matching its status

#### Scenario: Shows empty state for a column
- **WHEN** KanbanBoard has no tasks in a given status
- **THEN** the corresponding column SHALL show an empty placeholder

### Requirement: NoteEditor renders markdown editor
The system SHALL render a markdown editor with a textarea for note content and fields for folder and tags.

#### Scenario: Renders editor in create mode
- **WHEN** NoteEditor is rendered without a note prop
- **THEN** it SHALL render a markdown editor textarea, folder input, and save button

#### Scenario: Pre-fills fields in edit mode
- **WHEN** NoteEditor is rendered with an existing note
- **THEN** it SHALL display the note's content, folder, and tags in the form fields
