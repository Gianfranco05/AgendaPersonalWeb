## ADDED Requirements

### Requirement: Finance summary from real API
The system SHALL fetch finance summary data from `GET /api/v1/finance/summary` when mock mode is disabled.

#### Scenario: Successful summary fetch
- **WHEN** `useFinanceSummary()` is called and mock is disabled
- **THEN** it SHALL fetch from `GET /api/v1/finance/summary` and return `FinanceSummary`

#### Scenario: Summary fetch error
- **WHEN** the backend returns an error for `/api/v1/finance/summary`
- **THEN** `useFinanceSummary()` SHALL expose the error via SWR's `error` state

### Requirement: Transactions CRUD from real API
The system SHALL perform transactions CRUD against real backend endpoints under `/api/v1/finance/transactions` when mock mode is disabled.

#### Scenario: Fetch transactions list
- **WHEN** `fetchTransactions()` is called with optional filters
- **THEN** it SHALL fetch from `GET /api/v1/finance/transactions` with query params

#### Scenario: Create transaction
- **WHEN** `createTransaction()` is called
- **THEN** it SHALL `POST` to `/api/v1/finance/transactions` with the transaction body

#### Scenario: Update transaction
- **WHEN** `updateTransaction(id, data)` is called
- **THEN** it SHALL `PUT` to `/api/v1/finance/transactions/{id}` with the partial data

#### Scenario: Delete transaction
- **WHEN** `deleteTransaction(id)` is called
- **THEN** it SHALL `DELETE` to `/api/v1/finance/transactions/{id}`

#### Scenario: Transaction error
- **WHEN** any transaction request fails
- **THEN** the hook SHALL expose the error and SWR SHALL NOT clear existing data

### Requirement: Categories from real API
The system SHALL fetch categories from `GET /api/v1/finance/categories` when mock mode is disabled.

#### Scenario: Successful categories fetch
- **WHEN** `fetchCategories()` is called and mock is disabled
- **THEN** it SHALL fetch from `GET /api/v1/finance/categories`

### Requirement: Finance cache invalidation
After creating, updating, or deleting a transaction, the system SHALL invalidate both the summary and transactions SWR cache keys.

#### Scenario: After mutation
- **WHEN** `saveTransaction()` or `removeTransaction()` succeeds
- **THEN** SHALL revalidate both `finance/summary` and `finance/transactions` keys
