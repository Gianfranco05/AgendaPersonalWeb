## ADDED Requirements

### Requirement: CI pipeline runs on pull requests
The system SHALL provide a GitHub Actions CI workflow that runs on every pull request to the main branch.

#### Scenario: CI triggers on pull request
- **WHEN** a pull request is opened or updated against the `main` branch
- **THEN** the CI workflow SHALL be triggered

### Requirement: Backend tests execute in CI
The CI pipeline SHALL run Python backend tests.

#### Scenario: Backend test job runs pytest
- **WHEN** the CI workflow executes
- **THEN** there SHALL be a job that runs `pytest backend/tests/ -v`

#### Scenario: Backend tests use Python 3.11
- **WHEN** the backend test job runs
- **THEN** it SHALL use Python 3.11

#### Scenario: pip dependencies are cached
- **WHEN** the backend test job runs
- **THEN** pip dependencies SHALL be cached to speed up subsequent runs

### Requirement: Frontend lint executes in CI
The CI pipeline SHALL run TypeScript type checking and linting on the frontend.

#### Scenario: Frontend lint job runs tsc and eslint
- **WHEN** the CI workflow executes
- **THEN** there SHALL be a job that runs `tsc --noEmit` and a linter on the frontend code

#### Scenario: npm dependencies are cached
- **WHEN** the frontend lint job runs
- **THEN** npm dependencies SHALL be cached to speed up subsequent runs

### Requirement: Frontend build executes in CI
The CI pipeline SHALL verify the frontend builds successfully.

#### Scenario: Frontend build job runs npm run build
- **WHEN** the CI workflow executes
- **THEN** there SHALL be a job that runs `npm run build` in the frontend directory

### Requirement: CI fails on errors
The CI pipeline SHALL fail if any job fails.

#### Scenario: CI reports failure
- **WHEN** any job in the CI workflow fails
- **THEN** the workflow SHALL report a failure status on the pull request
