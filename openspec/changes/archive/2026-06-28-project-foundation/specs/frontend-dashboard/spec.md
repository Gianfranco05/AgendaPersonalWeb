## ADDED Requirements

### Requirement: Dashboard page at / with bento-box grid layout
The system SHALL render the Dashboard page at the root URL path using a bento-box grid layout that arranges widgets of varying sizes.

#### Scenario: Dashboard renders with bento-box grid
- **WHEN** the user navigates to `/`
- **THEN** the page SHALL display multiple widget cards arranged in a responsive bento-box grid layout

#### Scenario: Dashboard widgets have varying sizes
- **WHEN** the Dashboard page renders
- **THEN** at least one widget SHALL span more grid columns or rows than the others

### Requirement: FinanceWidget showing balance summary and recent transactions
The system SHALL provide a FinanceWidget on the Dashboard that displays the user's balance summary and the last 5 transactions.

#### Scenario: FinanceWidget displays balance summary
- **WHEN** the FinanceWidget mounts and data is loaded
- **THEN** the current balance amount SHALL be displayed prominently

#### Scenario: FinanceWidget displays last 5 transactions
- **WHEN** the FinanceWidget mounts and data is loaded
- **THEN** the 5 most recent transactions SHALL be listed with date, description, and amount

### Requirement: NotesWidget showing recent notes with pinned notes first
The system SHALL provide a NotesWidget on the Dashboard that displays the last 5 notes, ordered with pinned notes appearing first.

#### Scenario: NotesWidget displays recent notes
- **WHEN** the NotesWidget mounts and data is loaded
- **THEN** up to 5 recent notes SHALL be displayed with title preview

#### Scenario: Pinned notes appear before unpinned notes
- **WHEN** there are both pinned and unpinned notes
- **THEN** pinned notes SHALL appear at the top of the list regardless of their creation date

### Requirement: TasksWidget showing task counts per Kanban column
The system SHALL provide a TasksWidget on the Dashboard that displays task counts for each Kanban column.

#### Scenario: TasksWidget displays column counts
- **WHEN** the TasksWidget mounts and data is loaded
- **THEN** the count of tasks in Pendiente, En Proceso, and Completado SHALL each be displayed

#### Scenario: TasksWidget updates counts when tasks change
- **WHEN** a task is moved between columns
- **THEN** the displayed counts SHALL update to reflect the new distribution

### Requirement: EventsWidget showing upcoming events for next 7 days
The system SHALL provide an EventsWidget on the Dashboard that displays upcoming events within the next 7 days.

#### Scenario: EventsWidget displays upcoming events
- **WHEN** the EventsWidget mounts and data is loaded
- **THEN** all events occurring within the next 7 days SHALL be listed with date and title

#### Scenario: EventsWidget excludes past events
- **WHEN** there are events with dates in the past
- **THEN** those past events SHALL NOT appear in the EventsWidget

### Requirement: Each widget shows loading skeleton while fetching
The system SHALL display a loading skeleton placeholder in each widget while its data is being fetched from the API.

#### Scenario: Widget shows skeleton during data fetch
- **WHEN** a widget mounts and begins fetching data
- **THEN** a skeleton placeholder animation SHALL be displayed in place of the actual content

#### Scenario: Skeleton is replaced by content after fetch
- **WHEN** the API response for a widget arrives
- **THEN** the skeleton SHALL be replaced by the actual widget content

### Requirement: Widgets refresh data on mount
The system SHALL trigger a data refresh for each widget when the Dashboard page mounts.

#### Scenario: All widgets fetch data on Dashboard mount
- **WHEN** the user navigates to the Dashboard
- **THEN** each widget SHALL independently fetch its data from the backend API

### Requirement: Empty states for each widget when no data exists
The system SHALL display a meaningful empty state message in each widget when no data exists.

#### Scenario: FinanceWidget shows empty state with no transactions
- **WHEN** the user has no transactions
- **THEN** the FinanceWidget SHALL display a message indicating there are no transactions yet

#### Scenario: NotesWidget shows empty state with no notes
- **WHEN** the user has no notes
- **THEN** the NotesWidget SHALL display a message indicating there are no notes yet

#### Scenario: EventsWidget shows empty state with no upcoming events
- **WHEN** there are no events in the next 7 days
- **THEN** the EventsWidget SHALL display a message indicating no upcoming events
