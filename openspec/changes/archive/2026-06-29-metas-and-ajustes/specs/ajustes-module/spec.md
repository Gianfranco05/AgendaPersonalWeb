## ADDED Requirements

### Requirement: User can retrieve preferences
The system SHALL return the authenticated user's preferences including currency, theme_color, date_format, and google_calendar_id. If no preferences exist, the system SHALL create default preferences.

#### Scenario: Retrieve existing preferences
- **WHEN** an authenticated user with existing preferences requests their preferences
- **THEN** the system SHALL return their currency, theme_color, date_format, and google_calendar_id

#### Scenario: Auto-create preferences on first access
- **WHEN** an authenticated user without preferences requests their preferences
- **THEN** the system SHALL create default preferences (currency=ARS, theme_color=violet, date_format=DD/MM/YYYY) and return them

#### Scenario: Preferences request without auth
- **WHEN** an unauthenticated user requests preferences
- **THEN** the system SHALL redirect to the login page

### Requirement: User can update preferences
The system SHALL allow authenticated users to update their currency, theme_color, and date_format preferences with validation.

#### Scenario: Update all preference fields
- **WHEN** an authenticated user submits new currency, theme_color, and date_format values
- **THEN** the system SHALL persist all updated values

#### Scenario: Partial update only changes provided fields
- **WHEN** an authenticated user submits only a new theme_color
- **THEN** the system SHALL update only theme_color and preserve existing currency and date_format

#### Scenario: Update with invalid theme_color falls back to default
- **WHEN** an authenticated user submits an invalid theme_color value
- **THEN** the system SHALL fall back to "violet"

#### Scenario: Update with invalid currency falls back to default
- **WHEN** an authenticated user submits an invalid currency value
- **THEN** the system SHALL fall back to "ARS"
