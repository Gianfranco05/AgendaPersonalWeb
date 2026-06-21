## ADDED Requirements

### Requirement: Tasks page with Kanban board layout
The system SHALL render the Tasks page at `/tasks` with a Kanban board layout containing three columns: Pendiente, En Proceso, and Completado.

#### Scenario: Kanban board renders three columns
- **WHEN** the user navigates to `/tasks`
- **THEN** three columns SHALL be displayed side by side labeled Pendiente, En Proceso, and Completado

#### Scenario: Tasks are displayed in their respective columns
- **WHEN** tasks exist in different statuses
- **THEN** each task SHALL appear in the column matching its status

### Requirement: Drag and drop tasks between columns
The system SHALL support dragging and dropping tasks between Kanban columns to change their status.

#### Scenario: Dragging a task to a different column changes its status
- **WHEN** the user drags a task from Pendiente and drops it into En Proceso
- **THEN** the task SHALL move to the En Proceso column and its status SHALL update

#### Scenario: Dragging a task within the same column reorders it
- **WHEN** the user drags a task to a different position within the same column
- **THEN** the task SHALL be reordered at the new position

### Requirement: Add new task with title and description
The system SHALL provide a way to create a new task by entering a title and optional description.

#### Scenario: Adding a new task places it in Pendiente
- **WHEN** the user creates a new task with a title
- **THEN** the task SHALL appear in the Pendiente column with the given title

#### Scenario: Adding a task with description stores the description
- **WHEN** the user creates a new task with both title and description
- **THEN** both the title and description SHALL be stored and visible on the task card

### Requirement: Edit task inline
The system SHALL support inline editing of task title and description directly on the task card.

#### Scenario: Editing task title updates the task card
- **WHEN** the user clicks on the task title and edits it
- **THEN** the updated title SHALL be displayed on the task card immediately

#### Scenario: Editing task description updates the task data
- **WHEN** the user edits the task description inline
- **THEN** the new description SHALL be stored and visible when the task card is expanded

### Requirement: Delete task with confirmation
The system SHALL require confirmation before deleting a task to prevent accidental removal.

#### Scenario: Delete confirmation dialog appears
- **WHEN** the user clicks the delete action on a task
- **THEN** a confirmation dialog SHALL appear asking the user to confirm the deletion

#### Scenario: Confirmed deletion removes the task
- **WHEN** the user confirms the deletion in the dialog
- **THEN** the task SHALL be removed from the Kanban board

#### Scenario: Cancelled deletion keeps the task
- **WHEN** the user cancels the deletion dialog
- **THEN** the task SHALL remain in its current column unchanged

### Requirement: Task count per column header
The system SHALL display the number of tasks in each column within the column header.

#### Scenario: Column headers show task count
- **WHEN** the Kanban board renders with tasks
- **THEN** each column header SHALL display the count of tasks in that column

#### Scenario: Task count updates after drag and drop
- **WHEN** a task is moved from one column to another
- **THEN** the task counts in both the source and destination column headers SHALL update

### Requirement: Mock data seeded on first render
The system SHALL seed the Kanban board with mock task data on the first render when no backend data exists.

#### Scenario: First visit shows mock tasks
- **WHEN** the user visits the Tasks page for the first time with no backend configured
- **THEN** sample tasks SHALL be displayed across the three columns demonstrating the Kanban board functionality

#### Scenario: Mock data does not replace backend data
- **WHEN** the backend API returns task data
- **THEN** the actual backend data SHALL be displayed instead of the mock data

### Requirement: Tasks persist in localStorage
The system SHALL persist all task data (including mock data) in the browser's localStorage so it survives page refreshes and browser sessions.

#### Scenario: Tasks survive page refresh
- **WHEN** the user creates tasks and refreshes the page
- **THEN** all previously created tasks SHALL reappear in their correct columns

#### Scenario: Tasks persist across browser sessions
- **WHEN** the user closes and reopens the browser to the Tasks page
- **THEN** all tasks from the previous session SHALL still be present on the Kanban board
