## ADDED Requirements

### Requirement: Notes CRUD from real API
The system SHALL perform notes CRUD against real backend endpoints under `/api/v1/notes` when mock mode is disabled.

#### Scenario: Fetch all notes
- **WHEN** `fetchNotes()` is called and mock is disabled
- **THEN** it SHALL fetch from `GET /api/v1/notes`

#### Scenario: Create note
- **WHEN** `createNote()` is called
- **THEN** it SHALL `POST` to `/api/v1/notes` with the note body

#### Scenario: Update note
- **WHEN** `updateNote(id, data)` is called
- **THEN** it SHALL `PUT` to `/api/v1/notes/{id}` with the partial data

#### Scenario: Delete note
- **WHEN** `deleteNote(id)` is called
- **THEN** it SHALL `DELETE` to `/api/v1/notes/{id}`

### Requirement: Tags from real API
The system SHALL fetch tags from `GET /api/v1/tags` when mock mode is disabled.

#### Scenario: Successful tags fetch
- **WHEN** `fetchTags()` is called and mock is disabled
- **THEN** it SHALL fetch from `GET /api/v1/tags`

### Requirement: Notes error handling
When an API request for notes fails, the hook SHALL expose the error without clearing previously loaded data.

#### Scenario: Notes fetch error
- **WHEN** the backend returns an error for notes
- **THEN** `useNotes()` SHALL expose the error and keep stale data
