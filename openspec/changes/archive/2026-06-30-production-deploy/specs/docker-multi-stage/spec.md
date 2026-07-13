## ADDED Requirements

### Requirement: Frontend multi-stage Docker build
The system SHALL provide a multi-stage Dockerfile for the frontend with a build stage and a serve stage.

#### Scenario: Build stage uses node:20-alpine
- **WHEN** building the frontend Docker image
- **THEN** the first stage SHALL use `node:20-alpine` as the base image

#### Scenario: Build stage runs npm ci and npm run build
- **WHEN** the build stage executes
- **THEN** it SHALL run `npm ci` to install dependencies and `npm run build` to produce a production build in the `dist/` directory

#### Scenario: Serve stage uses nginx:alpine
- **WHEN** the build completes
- **THEN** the second stage SHALL use `nginx:alpine` as the base image

#### Scenario: Build artifacts are copied from build stage
- **WHEN** the final image is assembled
- **THEN** the `dist/` directory SHALL be copied from the build stage into the nginx document root

### Requirement: Backend multi-stage Docker build
The system SHALL provide a multi-stage Dockerfile for the backend with a build stage and a runtime stage.

#### Scenario: Build stage uses python:3.11-slim
- **WHEN** building the backend Docker image
- **THEN** the first stage SHALL use `python:3.11-slim` as the base image

#### Scenario: Build stage installs dependencies
- **WHEN** the build stage executes
- **THEN** it SHALL copy `requirements.txt` and run `pip install --no-cache-dir -r requirements.txt`

#### Scenario: Runtime stage uses python:3.11-slim
- **WHEN** the build completes
- **THEN** the second stage SHALL use `python:3.11-slim` as the base image

#### Scenario: Installed packages are copied from build stage
- **WHEN** the final image is assembled
- **THEN** installed Python packages SHALL be copied from the build stage into the runtime stage

#### Scenario: Only application code is present in runtime
- **WHEN** inspecting the runtime image
- **THEN** no build tools (gcc, libpq-dev) SHALL be present

### Requirement: Backend runs with Gunicorn + Uvicorn in production
The system SHALL run the backend using Gunicorn with Uvicorn workers in production mode.

#### Scenario: Backend starts with gunicorn
- **WHEN** the production container starts
- **THEN** the entrypoint SHALL execute `gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`

#### Scenario: Database migrations run on startup
- **WHEN** the production container starts
- **THEN** alembic upgrade head SHALL execute before the application starts
