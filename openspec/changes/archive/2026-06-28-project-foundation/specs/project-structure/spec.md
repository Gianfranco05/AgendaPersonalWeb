## ADDED Requirements

### Requirement: Project root structure with backend/ and frontend/ directories
The system SHALL organize all source code into two top-level directories: `backend/` for the FastAPI application and `frontend/` for the Vite + React application.

#### Scenario: Repository root contains only configuration and documentation
- **WHEN** the repository is initialized
- **THEN** the root directory SHALL contain only `docker-compose.yml`, `.gitignore`, `README.md`, and the `openspec/` directory

#### Scenario: Backend directory exists with complete FastAPI application
- **WHEN** the project structure is created
- **THEN** the `backend/` directory SHALL exist as a top-level directory alongside `frontend/`

#### Scenario: Frontend directory exists with complete React application
- **WHEN** the project structure is created
- **THEN** the `frontend/` directory SHALL exist as a top-level directory alongside `backend/`

### Requirement: backend/ contains the complete FastAPI application
The system SHALL place all Python application code, tests, database migrations, and static assets inside the `backend/` directory.

#### Scenario: FastAPI application code resides under backend/app/
- **WHEN** inspecting the `backend/` directory
- **THEN** it SHALL contain `app/`, `tests/`, `migrations/`, and `static/` subdirectories

#### Scenario: All existing FastAPI modules are inside backend/app/
- **WHEN** the application starts
- **THEN** all modules including auth, finanzas, anotaciones, eventos, metas, and ajustes SHALL be importable from `app.modules.*`

### Requirement: frontend/ contains Vite + React + TypeScript project
The system SHALL place the complete React frontend application inside the `frontend/` directory with Vite as the build tool and TypeScript configured.

#### Scenario: Frontend project scaffolding exists
- **WHEN** inspecting the `frontend/` directory
- **THEN** it SHALL contain `src/`, `public/`, `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, and `index.html`

#### Scenario: React application entry point exists
- **WHEN** the frontend dev server starts
- **THEN** `frontend/src/main.tsx` SHALL mount the React application to the DOM
