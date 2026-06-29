## ADDED Requirements

### Requirement: Single docker-compose.yml at root with backend and frontend services
The system SHALL provide a unified `docker-compose.yml` at the repository root that orchestrates both backend and frontend services.

#### Scenario: docker-compose.yml is at repository root
- **WHEN** inspecting the repository root
- **THEN** a `docker-compose.yml` file SHALL exist defining both `backend` and `frontend` services

#### Scenario: docker compose up starts both services
- **WHEN** the user runs `docker compose up`
- **THEN** both the backend and frontend containers SHALL start and become healthy

### Requirement: Backend service configuration
The system SHALL define the backend service in docker-compose.yml using Python 3.11, exposing port 8000, mounting application code as a volume, and running uvicorn.

#### Scenario: Backend service uses Python 3.11 image
- **WHEN** the backend container starts
- **THEN** it SHALL run on Python 3.11

#### Scenario: Backend service exposes port 8000
- **WHEN** the backend container is running
- **THEN** port 8000 SHALL be accessible from the host machine

#### Scenario: Backend app directory is mounted as volume
- **WHEN** a file in `backend/app/` is modified on the host
- **THEN** the change SHALL be immediately reflected inside the running backend container

#### Scenario: Backend service runs uvicorn
- **WHEN** the backend container starts
- **THEN** uvicorn SHALL be executed with `--host 0.0.0.0 --port 8000`

### Requirement: Frontend service configuration
The system SHALL define the frontend service in docker-compose.yml using Node 20 Alpine, exposing port 5173, mounting source code as a volume, and running Vite dev server.

#### Scenario: Frontend service uses Node 20 Alpine image
- **WHEN** the frontend container starts
- **THEN** it SHALL run on Node 20 Alpine

#### Scenario: Frontend service exposes port 5173
- **WHEN** the frontend container is running
- **THEN** port 5173 SHALL be accessible from the host machine

#### Scenario: Frontend src directory is mounted as volume
- **WHEN** a file in `frontend/src/` is modified on the host
- **THEN** Vite hot module replacement SHALL reflect the change immediately

#### Scenario: Frontend service runs Vite dev server
- **WHEN** the frontend container starts
- **THEN** `vite` SHALL be executed in dev mode with `--host 0.0.0.0`

### Requirement: Health checks on both services
The system SHALL configure Docker health checks for both backend and frontend services to verify they are operational.

#### Scenario: Backend health check returns healthy
- **WHEN** the backend service is running
- **THEN** a health check against the backend endpoint SHALL return a healthy status

#### Scenario: Frontend health check returns healthy
- **WHEN** the frontend service is running
- **THEN** a health check against the Vite dev server SHALL return a healthy status

### Requirement: Database persists in Docker volume
The system SHALL persist the SQLite database file using a Docker named volume so data survives container restarts.

#### Scenario: Database data survives container restart
- **WHEN** the backend container is stopped and restarted
- **THEN** all previously created transactions, notes, and events SHALL still be accessible

### Requirement: docker compose up starts everything with one command
The system SHALL ensure that a single `docker compose up` command starts all services without requiring additional manual steps.

#### Scenario: Single command launches entire application
- **WHEN** the user runs `docker compose up` from the repository root
- **THEN** both the backend API at `http://localhost:8000` and the frontend at `http://localhost:5173` SHALL be accessible
