## ADDED Requirements

### Requirement: Finance summary endpoint returns income, expenses and balance

The system SHALL provide a `GET /api/v1/finance/summary` endpoint that returns total income, total expenses, and the resulting balance for the authenticated user.

#### Scenario: Finance summary returns correct totals
- **WHEN** a GET request is sent to `/api/v1/finance/summary`
- **THEN** the response SHALL contain `total_income`, `total_expenses`, and `balance` as decimal values

### Requirement: Finance transactions list supports pagination with metadata

The system SHALL provide a `GET /api/v1/finance/transactions` endpoint that returns a paginated list of transactions with metadata (`total`, `page`, `page_size`), supporting filters by date range, transaction type, and category.

#### Scenario: Transactions list returns paginated response
- **WHEN** a GET request is sent to `/api/v1/finance/transactions?skip=0&limit=20`
- **THEN** the response SHALL contain `items` (list of transactions), `total` (total count), `page` (current page), and `page_size` (requested limit)

#### Scenario: Transactions list filters by date range
- **WHEN** a GET request is sent to `/api/v1/finance/transactions?date_from=2026-01-01&date_to=2026-06-30`
- **THEN** the response SHALL only include transactions within the specified date range

#### Scenario: Transactions list filters by type (income/expense)
- **WHEN** a GET request is sent to `/api/v1/finance/transactions?transaction_type=income`
- **THEN** the response SHALL only include transactions of type "income"

#### Scenario: Transactions list filters by category
- **WHEN** a GET request is sent to `/api/v1/finance/transactions?category_id=<id>`
- **THEN** the response SHALL only include transactions with the specified category

### Requirement: Finance transactions support CRUD operations

The system SHALL provide endpoints to create, update, and soft-delete financial transactions.

#### Scenario: Create transaction returns 201 with created data
- **WHEN** a POST request is sent to `/api/v1/finance/transactions` with valid transaction data
- **THEN** the response SHALL have status 201 and contain the created transaction

#### Scenario: Update transaction returns updated data
- **WHEN** a PUT request is sent to `/api/v1/finance/transactions/{id}` with valid update data
- **THEN** the response SHALL contain the updated transaction

#### Scenario: Delete transaction performs soft-delete
- **WHEN** a DELETE request is sent to `/api/v1/finance/transactions/{id}`
- **THEN** the transaction SHALL be marked as deleted (`is_deleted=True`, `deleted_at` set) and subsequent list queries SHALL exclude it

#### Scenario: Delete returns 204 No Content
- **WHEN** a DELETE request is sent to `/api/v1/finance/transactions/{id}`
- **THEN** the response SHALL have status 204

#### Scenario: Transaction not found returns 404
- **WHEN** a request is sent to `/api/v1/finance/transactions/{nonexistent_id}`
- **THEN** the response SHALL have status 404 with a JSON error body

### Requirement: Finance categories list endpoint

The system SHALL provide a `GET /api/v1/finance/categories` endpoint that returns all categories for the authenticated user.

#### Scenario: Categories list returns all user categories
- **WHEN** a GET request is sent to `/api/v1/finance/categories`
- **THEN** the response SHALL contain a list of categories with `id`, `name`, `color`, and `icon`

### Requirement: Notes CRUD with search and tag filtering

The system SHALL provide endpoints to list, create, update, and delete notes under `/api/v1/notes`.

#### Scenario: List notes supports search and archive filter
- **WHEN** a GET request is sent to `/api/v1/notes?search=<term>&include_archived=true`
- **THEN** the response SHALL contain notes matching the search term, optionally including archived ones

#### Scenario: Create note returns 201 with note data
- **WHEN** a POST request is sent to `/api/v1/notes` with valid title, content, and optional tags
- **THEN** the response SHALL have status 201 and contain the created note with its tags

#### Scenario: Update note returns updated data
- **WHEN** a PUT request is sent to `/api/v1/notes/{id}` with valid update fields
- **THEN** the response SHALL contain the updated note

#### Scenario: Delete note returns 204
- **WHEN** a DELETE request is sent to `/api/v1/notes/{id}`
- **THEN** the response SHALL have status 204

### Requirement: Notes tags list endpoint

The system SHALL provide a `GET /api/v1/notes/tags` endpoint that returns all tags for the authenticated user.

#### Scenario: Tags list returns all user tags
- **WHEN** a GET request is sent to `/api/v1/notes/tags`
- **THEN** the response SHALL contain a list of tags with `id` and `name`

### Requirement: Events CRUD with date range filtering

The system SHALL provide endpoints to list (with date range), create, update, and delete events under `/api/v1/events`.

#### Scenario: List events supports date range filter
- **WHEN** a GET request is sent to `/api/v1/events?date_from=2026-01-01&date_to=2026-06-30`
- **THEN** the response SHALL contain events within the specified date range

#### Scenario: Create event returns 201
- **WHEN** a POST request is sent to `/api/v1/events` with valid event data
- **THEN** the response SHALL have status 201 and contain the created event

#### Scenario: Update event returns updated data
- **WHEN** a PUT request is sent to `/api/v1/events/{id}` with valid update data
- **THEN** the response SHALL contain the updated event

#### Scenario: Delete event returns 204
- **WHEN** a DELETE request is sent to `/api/v1/events/{id}`
- **THEN** the response SHALL have status 204

### Requirement: Goals list and create with habit check-in

The system SHALL provide endpoints to list, create goals, and perform habit check-ins under `/api/v1/goals`.

#### Scenario: List goals returns all user goals
- **WHEN** a GET request is sent to `/api/v1/goals`
- **THEN** the response SHALL contain a list of goals with `id`, `title`, `goal_type`, `progress`, and `is_completed`

#### Scenario: Create goal returns 201
- **WHEN** a POST request is sent to `/api/v1/goals` with valid goal data
- **THEN** the response SHALL have status 201 and contain the created goal with 0% progress

#### Scenario: Habit check-in updates goal progress
- **WHEN** a PUT request is sent to `/api/v1/goals/{id}/checkin` with `record_date` and optional `value`
- **THEN** the goal's `current_value` SHALL increase and `progress` SHALL be recalculated

### Requirement: Settings get and update

The system SHALL provide endpoints to read and update user settings under `/api/v1/settings`.

#### Scenario: Get settings returns current preferences
- **WHEN** a GET request is sent to `/api/v1/settings`
- **THEN** the response SHALL contain `currency`, `theme_color`, `date_format`, and `google_calendar_id`

#### Scenario: Update settings returns updated preferences
- **WHEN** a PUT request is sent to `/api/v1/settings` with partial update data
- **THEN** the response SHALL contain the updated settings with all fields

### Requirement: All responses use consistent error format

The system SHALL return all error responses as JSON objects with `detail` and `status_code` fields.

#### Scenario: Not found returns 404 JSON
- **WHEN** a requested resource does not exist
- **THEN** the response SHALL be `{ "detail": "<message>", "status_code": 404 }` with Content-Type `application/json`

#### Scenario: Validation error returns 422 JSON
- **WHEN** request validation fails
- **THEN** the response SHALL have status 422 with error details in JSON format
