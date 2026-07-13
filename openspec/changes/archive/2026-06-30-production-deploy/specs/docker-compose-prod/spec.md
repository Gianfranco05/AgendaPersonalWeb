## ADDED Requirements

### Requirement: Production compose file exists
The system SHALL provide a `docker-compose.prod.yml` at the repository root for production deployment.

#### Scenario: docker-compose.prod.yml is at repository root
- **WHEN** inspecting the repository root
- **THEN** a `docker-compose.prod.yml` file SHALL exist

### Requirement: Backend service runs with Gunicorn
The production compose SHALL define a backend service using the multi-stage backend Dockerfile with Gunicorn configuration.

#### Scenario: Backend uses production Dockerfile
- **WHEN** building the production compose
- **THEN** the backend service SHALL build from `./backend` context using the multi-stage Dockerfile

#### Scenario: Backend exposes port 8000 internally only
- **WHEN** the production compose is running
- **THEN** the backend SHALL expose port 8000 on an internal network only (not on the host)

#### Scenario: Backend data persists in a named volume
- **WHEN** the production compose is running
- **THEN** the SQLite database SHALL be stored in a Docker named volume mounted at `/app/data`

#### Scenario: Backend has a healthcheck
- **WHEN** the production compose is running
- **THEN** a healthcheck SHALL verify the backend responds at `/health`

### Requirement: Frontend service runs with nginx
The production compose SHALL define a frontend service using the multi-stage frontend Dockerfile with nginx.

#### Scenario: Frontend uses production Dockerfile
- **WHEN** building the production compose
- **THEN** the frontend service SHALL build from `./frontend` context using the multi-stage Dockerfile

#### Scenario: Frontend is exposed on port 80
- **WHEN** the production compose is running
- **THEN** port 80 SHALL be mapped from the host to the nginx container

#### Scenario: Frontend has a healthcheck
- **WHEN** the production compose is running
- **THEN** a healthcheck SHALL verify nginx responds on port 80

### Requirement: Internal network isolates services
The production compose SHALL use a dedicated internal bridge network.

#### Scenario: Backend and frontend are on the same internal network
- **WHEN** the production compose is running
- **THEN** both backend and frontend services SHALL be connected to a custom bridge network named `lifeos-net`

#### Scenario: Backend is not exposed to the host
- **WHEN** the production compose is running
- **THEN** the backend service SHALL NOT have any host port mapping

### Requirement: Database persists across restarts
The system SHALL persist the SQLite database in a Docker named volume.

#### Scenario: Data survives container restart
- **WHEN** the backend container is stopped and restarted
- **THEN** all previously created data SHALL still be accessible

### Requirement: Single command starts production stack
The system SHALL start all production services with a single command.

#### Scenario: docker compose -f docker-compose.prod.yml up starts everything
- **WHEN** the user runs `docker compose -f docker-compose.prod.yml up` from the repository root
- **THEN** both the frontend at `http://localhost` and the backend API SHALL be accessible
