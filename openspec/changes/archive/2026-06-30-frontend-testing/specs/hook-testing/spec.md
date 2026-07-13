## ADDED Requirements

### Requirement: useKanban manages task CRUD with localStorage persistence
The system SHALL provide a custom hook that manages Kanban tasks with add, move, delete, and localStorage persistence.

#### Scenario: Loads mock tasks on first render
- **WHEN** useKanban is called with no data in localStorage
- **THEN** it SHALL return the default MOCK_TASKS as the initial columns

#### Scenario: Loads persisted tasks from localStorage
- **WHEN** useKanban is called with persisted tasks in localStorage
- **THEN** it SHALL return those persisted tasks instead of mock data

#### Scenario: addTask creates a pending task
- **WHEN** `addTask("New task", "Description")` is called
- **THEN** a new task with status "pending" SHALL appear in the pending column

#### Scenario: moveTask changes task status
- **WHEN** `moveTask("t1", "completed", 0)` is called
- **THEN** the task with id "t1" SHALL move to the completed column

#### Scenario: deleteTask removes a task
- **WHEN** `deleteTask("t1")` is called
- **THEN** the task with id "t1" SHALL be removed from all columns

#### Scenario: Persists tasks to localStorage after changes
- **WHEN** a task is added, moved, or deleted
- **THEN** the updated task list SHALL be written to localStorage under the key "kanban-tasks"

### Requirement: useFinance fetches summary and transactions via SWR
The system SHALL provide hooks that fetch financial data from API endpoints using SWR with automatic caching and revalidation.

#### Scenario: useFinanceSummary fetches summary data
- **WHEN** `useFinanceSummary()` is called with a SWR provider that has cached summary data
- **THEN** it SHALL return that cached summary data (income, expense, balance)

#### Scenario: useTransactions fetches paginated transactions
- **WHEN** `useTransactions({ page: 1, per_page: 20 })` is called with cached transaction data
- **THEN** it SHALL return the cached list of transactions and total count

#### Scenario: saveTransaction calls createTransaction for new records
- **WHEN** `saveTransaction(null, { amount: 100, ... }, params)` is called
- **THEN** it SHALL call `createTransaction` with the provided data and invalidate SWR caches

#### Scenario: saveTransaction calls updateTransaction for existing records
- **WHEN** `saveTransaction({ id: "1", ... }, { amount: 200, ... }, params)` is called
- **THEN** it SHALL call `updateTransaction` with id "1" and the data, then invalidate SWR caches

#### Scenario: removeTransaction deletes and invalidates caches
- **WHEN** `removeTransaction("1", params)` is called
- **THEN** it SHALL call `deleteTransaction` with id "1" and invalidate SWR caches for summary and transactions
