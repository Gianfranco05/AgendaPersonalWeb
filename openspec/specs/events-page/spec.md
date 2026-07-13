# events-page Specification

## Purpose
TBD - created by archiving change frontend-pages-extra. Update Purpose after archive.
## Requirements
### Requirement: EventsPage renders a monthly calendar grid
The system SHALL render a monthly calendar view at `/events` showing a 7-column grid with day cells for the current month.

#### Scenario: Calendar displays current month
- **WHEN** the user navigates to `/events`
- **THEN** the current month SHALL be displayed with day cells arranged in weeks (Mon–Sun), with the month/year shown in the header

#### Scenario: Navigation between months
- **WHEN** the user clicks "Previous" or "Next"
- **THEN** the calendar SHALL shift to the previous or next month and re-render

#### Scenario: Events appear as dots on calendar days
- **WHEN** the calendar renders and events data is loaded
- **THEN** days that have events SHALL show small colored dots matching the event color

### Requirement: EventList shows upcoming events
The system SHALL display a sidebar list of upcoming events sorted by start_datetime ascending.

#### Scenario: EventList shows next events
- **WHEN** the EventsPage mounts and data is loaded
- **THEN** the EventList SHALL show event titles, dates, and colors for all upcoming events, ordered by closest date first

#### Scenario: EventList shows empty state
- **WHEN** there are no upcoming events
- **THEN** the EventList SHALL display "No hay eventos próximos" with a calendar icon

### Requirement: EventForm modal creates and edits events
The system SHALL provide a modal form for creating and editing calendar events with fields: title, description, date, time (optional), all-day toggle, location, and color.

#### Scenario: Create event via EventForm
- **WHEN** the user clicks "Nuevo evento" and fills the form
- **THEN** a new event SHALL be created via the API and appear on the calendar and event list

#### Scenario: Edit event via EventForm
- **WHEN** the user clicks an existing event
- **THEN** the EventForm SHALL open pre-filled and allow editing; on save the event SHALL be updated

#### Scenario: EventForm validates required fields
- **WHEN** the user submits the form with an empty title
- **THEN** the form SHALL show a validation error and NOT submit

### Requirement: Delete event from EventList
The system SHALL allow deleting events from the EventList with a confirmation step.

#### Scenario: Delete event with confirmation
- **WHEN** the user clicks the delete icon on an event
- **THEN** a confirmation prompt SHALL appear; on confirm the event SHALL be deleted and removed from the UI

### Requirement: Loading and empty states
The system SHALL display loading skeletons while fetching events and meaningful empty states.

#### Scenario: Loading skeleton on mount
- **WHEN** the EventsPage mounts and events are loading
- **THEN** a skeleton placeholder SHALL be displayed for both the calendar and event list

#### Scenario: Empty state when no events exist
- **WHEN** there are no events in the database
- **THEN** the calendar SHALL show empty cells and the EventList SHALL display "No hay eventos próximos"

