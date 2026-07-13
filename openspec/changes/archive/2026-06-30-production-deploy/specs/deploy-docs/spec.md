## ADDED Requirements

### Requirement: README includes production deployment instructions
The README.md SHALL include a section explaining how to deploy LifeOS in production.

#### Scenario: Production instructions exist in README
- **WHEN** reading the README.md
- **THEN** there SHALL be a "Production Deployment" section with step-by-step instructions

### Requirement: README documents the architecture
The README.md SHALL include an architecture section describing the system components.

#### Scenario: Architecture section exists in README
- **WHEN** reading the README.md
- **THEN** there SHALL be an "Architecture" section describing the frontend, backend, and infrastructure components

### Requirement: README includes prerequisites
The README.md SHALL list all prerequisites needed to run the application in production.

#### Scenario: Prerequisites are documented
- **WHEN** reading the production deployment section
- **THEN** the following prerequisites SHALL be listed: Docker and Docker Compose

### Requirement: README includes environment variables
The README.md SHALL document required environment variables for production.

#### Scenario: Environment variables are documented
- **WHEN** reading the production deployment section
- **THEN** the required environment variables SHALL be listed with descriptions (DATABASE_URL, SECRET_KEY)
