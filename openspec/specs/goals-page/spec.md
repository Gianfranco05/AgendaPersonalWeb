# goals-page Specification

## Purpose
TBD - created by archiving change frontend-pages-extra. Update Purpose after archive.
## Requirements
### Requirement: GoalsPage renders a board of goal cards
The system SHALL render a goals board at `/goals` displaying goals as cards in a responsive grid layout.

#### Scenario: Goals board displays all goals
- **WHEN** the user navigates to `/goals`
- **THEN** all goals SHALL be displayed as cards in a 2–3 column responsive grid, each showing title, progress, and deadline

#### Scenario: Goal cards show visual progress
- **WHEN** a GoalCard renders
- **THEN** it SHALL show a circular progress ring (SVG) with the percentage complete, plus a thin horizontal progress bar below

#### Scenario: Goal cards show deadline info
- **WHEN** a GoalCard renders with a deadline
- **THEN** the remaining days SHALL be displayed; if the deadline is past, it SHALL show "Vencida" in red

#### Scenario: Empty state
- **WHEN** there are no goals
- **THEN** the page SHALL display "No hay metas aún" with a "Crear meta" button

### Requirement: GoalForm modal creates and edits goals
The system SHALL provide a modal form for creating and editing goals with fields: title, description, goal_type (number/binary), target value, unit, deadline, and color.

#### Scenario: Create goal via GoalForm
- **WHEN** the user clicks "Nueva meta" and fills the form
- **THEN** a new goal SHALL be created via the API and appear on the board

#### Scenario: Edit goal via GoalForm
- **WHEN** the user clicks edit on a GoalCard
- **THEN** the GoalForm SHALL open pre-filled; on save the goal SHALL be updated

### Requirement: CheckInButton increments daily progress
The system SHALL provide a check-in button on each GoalCard that marks daily progress.

#### Scenario: Check in on a numeric goal
- **WHEN** the user clicks the check-in button on a numeric goal
- **THEN** the `current` count SHALL increment by 1 and the progress ring SHALL update

#### Scenario: Check in on a binary goal
- **WHEN** the user clicks the check-in button on a binary goal
- **THEN** the goal SHALL toggle to completed (100%)

### Requirement: Delete goal
The system SHALL allow deleting goals with confirmation.

#### Scenario: Delete goal with confirmation
- **WHEN** the user clicks delete on a GoalCard
- **THEN** a confirmation prompt SHALL appear; on confirm the goal SHALL be deleted and removed from the board

### Requirement: Loading states
The system SHALL display loading skeletons while fetching goals.

#### Scenario: Loading skeleton on mount
- **WHEN** the GoalsPage mounts and data is loading
- **THEN** skeleton placeholders SHALL be displayed for each goal card

