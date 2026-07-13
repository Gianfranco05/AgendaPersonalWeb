## ADDED Requirements

### Requirement: User can create a goal
The system SHALL allow authenticated users to create a goal with title, description, goal type (binary or numeric), target value, unit, color, icon, and optional date range.

#### Scenario: Successful goal creation
- **WHEN** an authenticated user submits valid goal data
- **THEN** the system SHALL create the goal and return it with an auto-generated id, current_value=0, is_completed=False, and timestamps

#### Scenario: Goal creation without auth
- **WHEN** an unauthenticated user attempts to create a goal
- **THEN** the system SHALL redirect to the login page

### Requirement: User can list active goals
The system SHALL return all non-completed goals for the authenticated user, ordered by creation date descending, with recent habit records (last 7 days) and streak information.

#### Scenario: List active goals returns only non-completed goals
- **WHEN** an authenticated user requests their active goals
- **THEN** the system SHALL return only goals where is_completed is False

#### Scenario: Active goals include recent records
- **WHEN** an authenticated user requests their active goals
- **THEN** each goal SHALL include habit records from the last 7 days

### Requirement: User can complete a goal
The system SHALL allow authenticated users to mark a goal as completed by setting is_completed=True and current_value=target_value.

#### Scenario: Goal completion sets correct fields
- **WHEN** an authenticated user completes a goal
- **THEN** the goal SHALL have is_completed=True and current_value equal to target_value

#### Scenario: Complete non-existent goal
- **WHEN** an authenticated user attempts to complete a goal that does not exist
- **THEN** the system SHALL redirect without error

### Requirement: User can check in a habit
The system SHALL allow authenticated users to record a daily habit check-in with a value and optional notes. If a record for today already exists, it SHALL be updated.

#### Scenario: First check-in creates a record
- **WHEN** an authenticated user checks in for a goal with no record today
- **THEN** the system SHALL create a new HabitRecord with today's date and the specified value

#### Scenario: Duplicate check-in updates existing record
- **WHEN** an authenticated user checks in for a goal that already has a record today
- **THEN** the system SHALL update the existing record's value and notes

#### Scenario: Check-in auto-completes binary goal
- **WHEN** a check-in causes current_value >= target_value for a binary goal within its date range
- **THEN** the system SHALL set is_completed=True

### Requirement: User can edit and delete a goal
The system SHALL allow authenticated users to update goal fields or delete a goal (including its habit records).

#### Scenario: Edit goal updates specified fields
- **WHEN** an authenticated user submits updated goal data
- **THEN** the system SHALL update only the provided fields

#### Scenario: Delete goal removes records
- **WHEN** an authenticated user deletes a goal
- **THEN** the system SHALL remove the goal and all its associated HabitRecords

### Requirement: Goal progress can be retrieved
The system SHALL calculate goal progress including current_value, target_value, percentage (0-100), and current streak in days.

#### Scenario: Progress shows correct percentage
- **WHEN** a goal has current_value=5 and target_value=10
- **THEN** the progress percentage SHALL be 50

#### Scenario: Streak counts consecutive days
- **WHEN** a goal has habit records for the last 3 consecutive days
- **THEN** the streak SHALL be 3

#### Scenario: Zero target value shows 0 percentage
- **WHEN** a goal has target_value=0
- **THEN** the progress percentage SHALL be 0
