## ADDED Requirements

### Requirement: Finance page with full transaction table
The system SHALL render the Finance page at `/finances` with a complete transaction table showing date, description, category, amount, and type columns.

#### Scenario: Transaction table displays all required columns
- **WHEN** the Finance page mounts and loads transactions
- **THEN** the table SHALL include columns for date, description, category, amount, and type

#### Scenario: Transaction table populates with data from the API
- **WHEN** transactions are successfully fetched from the backend
- **THEN** each transaction row SHALL display its corresponding data in the correct columns

### Requirement: Amount column color indicates transaction type
The system SHALL color-code the amount column: green for income and red for expense.

#### Scenario: Income amounts are displayed in green
- **WHEN** a transaction row has type INCOME
- **THEN** the amount SHALL be displayed with green text styling

#### Scenario: Expense amounts are displayed in red
- **WHEN** a transaction row has type EXPENSE
- **THEN** the amount SHALL be displayed with red text styling

### Requirement: Add transaction modal with form
The system SHALL provide a button or modal to add a new transaction, opening a form with all required fields.

#### Scenario: Add transaction button opens form
- **WHEN** the user clicks the add transaction button
- **THEN** a form SHALL open with fields for description, amount, category, type, and date

#### Scenario: Submitting the form creates a transaction
- **WHEN** the user fills in the transaction form and submits
- **THEN** the transaction SHALL be created via the API and the table SHALL refresh

### Requirement: Edit and delete actions per transaction row
The system SHALL provide edit and delete actions for each transaction row in the table.

#### Scenario: Edit action opens edit form pre-filled with transaction data
- **WHEN** the user clicks the edit action on a transaction row
- **THEN** a form SHALL open with the transaction's current values pre-filled

#### Scenario: Delete action removes the transaction
- **WHEN** the user clicks the delete action on a transaction row
- **THEN** the transaction SHALL be soft-deleted via the API and disappear from the table

### Requirement: Filter by date range, category, and type
The system SHALL provide filter controls to narrow the transaction table by date range, category, and transaction type.

#### Scenario: Date range filter applies correctly
- **WHEN** the user selects a date range filter
- **THEN** only transactions within that date range SHALL be displayed

#### Scenario: Category filter applies correctly
- **WHEN** the user selects a category filter
- **THEN** only transactions matching that category SHALL be displayed

#### Scenario: Type filter toggles between income and expense
- **WHEN** the user selects INCOME as the type filter
- **THEN** only income transactions SHALL be displayed

### Requirement: Chart section with recharts
The system SHALL include a chart section using recharts with a pie chart by category and a bar chart for income vs expense over the last 6 months.

#### Scenario: Pie chart displays transaction distribution by category
- **WHEN** the chart section renders with transaction data
- **THEN** a pie chart SHALL show the proportional distribution of expenses by category

#### Scenario: Bar chart displays monthly income vs expense
- **WHEN** the chart section renders with transaction data
- **THEN** a bar chart SHALL display income and expense bars for each of the last 6 months

### Requirement: Summary cards for current month
The system SHALL display summary cards showing total income, total expense, and balance for the current month.

#### Scenario: Summary card shows total income for current month
- **WHEN** the Finance page mounts
- **THEN** a card SHALL display the sum of all income transactions for the current month

#### Scenario: Summary card shows total expense for current month
- **WHEN** the Finance page mounts
- **THEN** a card SHALL display the sum of all expense transactions for the current month

#### Scenario: Summary card shows balance for current month
- **WHEN** the Finance page mounts
- **THEN** a card SHALL display the difference between income and expense for the current month

### Requirement: Pagination for transaction table
The system SHALL paginate the transaction table at 20 rows per page.

#### Scenario: Transactions are paginated at 20 per page
- **WHEN** there are more than 20 transactions
- **THEN** only 20 transactions SHALL be displayed and pagination controls SHALL be visible

#### Scenario: Pagination controls navigate between pages
- **WHEN** the user clicks the next page control
- **THEN** the next 20 transactions SHALL be displayed
