## ADDED Requirements

### Requirement: Shutdown hook script
The system SHALL provide a Python script (`shutdown_hook.py`) that executes on Windows shutdown.

#### Scenario: Script triggered by shutdown event
- **WHEN** Windows initiates shutdown (EventID 1074) or user runs the script manually
- **THEN** the script SHALL read `infra_config.yaml` and turn off all configured LED devices

#### Scenario: Script ignores non-shutdown execution
- **WHEN** the script runs without a shutdown signal or `--force` flag
- **THEN** it SHALL log a warning and exit without turning off devices

### Requirement: LED device control
The script SHALL support controlling LED devices via HTTP API.

#### Scenario: Turn off WLED device
- **WHEN** the script executes and a WLED device is configured in `infra_config.yaml`
- **THEN** it SHALL send `POST /json/state` with `{"on": false}` to the device IP

#### Scenario: Turn off generic WiFi plug
- **WHEN** the script executes and a generic HTTP switch is configured
- **THEN** it SHALL send a configurable HTTP request (method, URL, body) to turn it off

#### Scenario: Unsupported LED type logs error
- **WHEN** the script encounters a LED type it does not recognize
- **THEN** it SHALL log an error and skip that device without crashing

### Requirement: Dream Machine shutdown via SSH
The script SHALL shut down the Ubiquiti Dream Machine via SSH.

#### Scenario: Successful SSH shutdown
- **WHEN** the script can establish SSH connection to the Dream Machine
- **THEN** it SHALL execute `poweroff` command via SSH and log success

#### Scenario: SSH connection failure
- **WHEN** the SSH connection to the Dream Machine fails (timeout, auth error, unreachable)
- **THEN** the script SHALL log the error and continue (non-fatal)

### Requirement: Configuration file
The system SHALL read `infra_config.yaml` from a configurable path.

#### Scenario: Valid configuration loaded
- **WHEN** the configuration file exists and is valid YAML
- **THEN** the script SHALL parse `devices.leds` and `devices.dream_machine` sections

#### Scenario: Missing configuration file
- **WHEN** the configuration file does not exist or is invalid YAML
- **THEN** the script SHALL exit with an error message indicating the path expected
