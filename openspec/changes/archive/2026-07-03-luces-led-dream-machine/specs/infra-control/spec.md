## ADDED Requirements

### Requirement: REST endpoint to shut down Dream Machine
The backend SHALL expose `POST /api/v1/infra/shutdown` to trigger Dream Machine shutdown.

#### Scenario: Successful shutdown
- **WHEN** a POST request is sent to `/api/v1/infra/shutdown`
- **THEN** the system SHALL attempt to shut down the Dream Machine via SSH
- **THEN** the system SHALL return `{"status": "ok", "message": "Shutdown command sent to Dream Machine"}`
- **THEN** the Dream Machine SHALL be turned off

#### Scenario: Dream Machine unreachable
- **WHEN** the Dream Machine is unreachable or SSH fails
- **THEN** the system SHALL return `{"status": "error", "message": "Failed to connect to Dream Machine"}` with HTTP 502

#### Scenario: Missing configuration
- **WHEN** no Dream Machine is configured in `infra_config.yaml`
- **THEN** the system SHALL return `{"status": "error", "message": "Dream Machine not configured"}` with HTTP 503

### Requirement: Frontend trigger button
The frontend SHALL display a button in the Dashboard to trigger Dream Machine shutdown.

#### Scenario: Button visible in Dashboard
- **WHEN** the Dashboard page loads
- **THEN** a button labeled "Apagar Dream Machine" SHALL be visible

#### Scenario: Click triggers API call
- **WHEN** the user clicks the "Apagar Dream Machine" button
- **THEN** the system SHALL send POST to `/api/v1/infra/shutdown`
- **THEN** the system SHALL display a loading state while the request is in flight

#### Scenario: Success feedback
- **WHEN** the API returns a successful response
- **THEN** the system SHALL display a success toast/message
- **THEN** the button SHALL be enabled again

#### Scenario: Error feedback
- **WHEN** the API returns an error response
- **THEN** the system SHALL display an error toast/message with the error details
- **THEN** the button SHALL be enabled again
