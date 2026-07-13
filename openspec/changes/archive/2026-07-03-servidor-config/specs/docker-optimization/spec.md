## ADDED Requirements

### Requirement: Backend .dockerignore
The backend SHALL have a `.dockerignore` file to exclude unnecessary files from the Docker build context.

#### Scenario: Backend build excludes dev files
- **WHEN** Docker builds the backend image
- **THEN** the build context SHALL exclude `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.git/`, `.env`, `.pytest_cache/`, `tests/`, `.vscode/`, and `node_modules/` (if any)

### Requirement: Frontend .dockerignore
The frontend SHALL have a `.dockerignore` file to exclude unnecessary files from the Docker build context.

#### Scenario: Frontend build excludes dev files
- **WHEN** Docker builds the frontend image
- **THEN** the build context SHALL exclude `node_modules/`, `.git/`, `.env`, `.env.local`, `dist/` (excluded anyway, but explicit), `.vscode/`, `tests/`, `__tests__/`, and `*.md`

### Requirement: Restart policy in compose
The production Docker Compose file SHALL include restart policies for all services.

#### Scenario: Services restart automatically
- **WHEN** a container exits unexpectedly
- **THEN** Docker SHALL restart it with `unless-stopped` policy
