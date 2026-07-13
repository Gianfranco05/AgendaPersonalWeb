## ADDED Requirements

### Requirement: Gunicorn configuration file
The backend SHALL use a `gunicorn.conf.py` file for production server configuration.

#### Scenario: Workers calculated dynamically
- **WHEN** Gunicorn starts
- **THEN** the number of workers SHALL be `(2 * CPU_COUNT) + 1` unless overridden by `GUNICORN_WORKERS` env var

#### Scenario: Timeout configured
- **WHEN** a worker handles a request
- **THEN** the worker SHALL have a `timeout` of 120 seconds
- **AND** a `graceful_timeout` of 30 seconds

#### Scenario: Preload enabled
- **WHEN** Gunicorn starts
- **THEN** `preload_app` SHALL be enabled to share memory across workers

#### Scenario: Log access through Python logger
- **WHEN** a request is processed by Gunicorn
- **THEN** access logs SHALL go through the Python logger (not stdout directly)
- **AND** SHALL use the JSON structured logging format
