## ADDED Requirements

### Requirement: Recurring transactions from real API
When mock mode is disabled, the web and mobile clients SHALL call `GET/POST /api/v1/finance/recurring`, `GET/PUT/DELETE /api/v1/finance/recurring/{id}`, `POST /api/v1/finance/recurring/{id}/pause` and `/resume`, `POST /api/v1/finance/recurring/preview`, `GET /api/v1/finance/recurring/upcoming`, `GET /api/v1/finance/recurring/occurrences` and `POST /api/v1/finance/recurring/occurrences/{id}/confirm` and `/skip`, sending `tz_offset_minutes` on reads and `timezone_offset_minutes` on writes. The mobile client SHALL send writes through the offline queue, and preview and upcoming only when online. When mock mode is enabled, the web client SHALL serve equivalent mock data with the same shapes.

#### Scenario: Create a recurring template
- **WHEN** `createRecurring(data)` is called with mock disabled
- **THEN** it SHALL `POST` to `/api/v1/finance/recurring` including `timezone_offset_minutes`

#### Scenario: Confirm a pending occurrence
- **WHEN** `confirmOccurrence(id, {amount})` is called
- **THEN** it SHALL `POST` to `/api/v1/finance/recurring/occurrences/{id}/confirm`

#### Scenario: Recurring request error
- **WHEN** any recurring request fails
- **THEN** the hook SHALL expose the error and SWR SHALL NOT clear existing data

### Requirement: Transactions expose their recurrence
The clients SHALL read `recurrence_id` and `is_recurring` from transactions, show a "Recurrente" badge on generated transactions linking to their template (or "recurrencia eliminada" when `recurrence_id` is null), and request `GET /api/v1/finance/transactions?recurrence_id={id}` to show a template's movements.

#### Scenario: Generated transaction badge
- **WHEN** the transactions list contains a transaction with `is_recurring = true` and a `recurrence_id`
- **THEN** the row SHALL show the "Recurrente" badge linking to that template

### Requirement: Fixed-term renewal from real API
The clients SHALL call `POST /api/v1/finance/investments/{id}/renew` (through the offline queue in mobile) and `GET /api/v1/finance/investments/{id}/renewals`, and SHALL only offer the "Renovar" action when the investment's `can_renew` is true.

#### Scenario: Renew from the investments list
- **WHEN** the user confirms the renewal form of a matured fixed term
- **THEN** the client SHALL `POST` to `/api/v1/finance/investments/{id}/renew` with the chosen mode, rate, term and `timezone_offset_minutes`

### Requirement: Recurring and renewal cache invalidation
After any recurring mutation the clients SHALL revalidate the recurring list, detail, upcoming and pending occurrences cache keys; when the mutation may create transactions (create with past occurrences, rule change, resume, confirm) they SHALL also revalidate the transactions, `finance/summary`, budgets and reports keys. After a renewal they SHALL revalidate the investments list and summary, net worth, `finance/summary` and transactions.

#### Scenario: After confirming a pending occurrence
- **WHEN** a pending occurrence is confirmed successfully
- **THEN** pending occurrences, the recurring list, transactions, `finance/summary`, budgets and reports SHALL be revalidated

#### Scenario: After renewing a fixed term
- **WHEN** a renewal succeeds
- **THEN** investments, investments summary, net worth, `finance/summary` and transactions SHALL be revalidated
