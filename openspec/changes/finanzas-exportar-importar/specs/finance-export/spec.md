## ADDED Requirements

### Requirement: Finance export endpoint
The backend SHALL expose `GET /api/v1/finance/export` for authenticated users with query parameters `format` (`xlsx` or `pdf`, required), `date_from`, `date_to`, `type` (`income`|`expense`), `category_id` (a category id or `none` for uncategorized), `account_id`, `include_investments` (bool, default false) and `tz_offset_minutes` (−840..840, default 0). When `date_from`/`date_to` are omitted the range SHALL default to the first day of the user's current local month through the user's local today. The report SHALL only contain the requesting user's non-deleted transactions matching the filters. The response SHALL be an attachment with `Content-Disposition` filename `cancen-finanzas-<date_from>_<date_to>.<ext>`, the proper media type, `Content-Length` and `Cache-Control: no-store`.

#### Scenario: Excel export with default range
- **WHEN** an authenticated user requests `GET /finance/export?format=xlsx` without dates
- **THEN** the response SHALL be 200 with media type `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` containing only that user's transactions of the current local month

#### Scenario: PDF export with filters
- **WHEN** a user requests `format=pdf&type=expense&category_id=<own category>`
- **THEN** the response SHALL be a PDF whose movements are only that category's expenses in the range

#### Scenario: Invalid parameters
- **WHEN** `format` is missing or not `xlsx`/`pdf`, `date_to < date_from`, the range exceeds 5 years, or `category_id`/`account_id` does not belong to the user
- **THEN** the endpoint SHALL respond 422 (invalid values) or 404 (foreign category/account) without generating a file

#### Scenario: Unauthenticated request
- **WHEN** the request has no valid session
- **THEN** the endpoint SHALL respond 401

### Requirement: Export content and totals
The export SHALL contain: a summary (period, applied filters, generation timestamp in the user's local time, and income, expenses, balance and count per currency), the list of movements (date, time, type, description, merchant, category, payment method label, account, currency, signed amount with expenses negative, notes, import batch), totals by category and currency, and totals by month and currency. Amounts in different currencies SHALL never be summed together. Totals SHALL be computed from the same rows listed in the movements section. When `include_investments=true` it SHALL add active investments and the net worth breakdown (cash, investments, total in ARS and USD, or a "no rate" indication when a rate is missing) using the user's current rates.

#### Scenario: Totals match detail
- **WHEN** a report contains 3 ARS expenses of 100, 200 and 300 and 1 ARS income of 1000
- **THEN** the ARS totals SHALL be income 1000.00, expenses 600.00, balance 400.00, count 4

#### Scenario: Multiple currencies
- **WHEN** the range has ARS and USD movements
- **THEN** totals SHALL be reported separately per currency and no combined total SHALL be shown

#### Scenario: Investments section
- **WHEN** `include_investments=true` and the user has active investments
- **THEN** the export SHALL include an investments section, the net worth breakdown and the rates used (source and date); with `include_investments=false` it SHALL NOT

#### Scenario: Recurring templates
- **WHEN** `include_investments=true` and the user has recurring templates
- **THEN** the export SHALL list only that user's templates (name, type, amount, currency, frequency, next date, status)

### Requirement: Excel format
The `.xlsx` file SHALL have one sheet per section in the order Resumen, Movimientos, Por categoría, Por mes and (optional) Inversiones and Recurrentes; header rows bold with frozen panes and autofilter; amounts written as numeric cells with a two-decimal thousands format; dates written as date cells formatted `DD/MM/YYYY`; workbook creator `Can_cen`.

#### Scenario: Numeric amounts
- **WHEN** the Movimientos sheet is read back with openpyxl
- **THEN** the amount cells SHALL be numbers (not strings) and the date cells SHALL be dates

#### Scenario: Sheets present
- **WHEN** an export without investments is generated
- **THEN** the workbook SHALL contain exactly the sheets Resumen, Movimientos, Por categoría and Por mes

### Requirement: Formula injection protection
Every text cell written to the `.xlsx` (descriptions, merchants, categories, notes, batch names, filter labels) whose value starts with `=`, `+`, `-`, `@`, tab, carriage return or line feed SHALL be prefixed with a single quote and stored as a string cell, so that no spreadsheet program interprets it as a formula. Numeric cells SHALL NOT be altered.

#### Scenario: Malicious description
- **WHEN** a transaction description is `=HYPERLINK("http://x","clic")`
- **THEN** the exported cell SHALL be a string cell with value `'=HYPERLINK("http://x","clic")` and the workbook SHALL contain no formula cells

#### Scenario: Negative amount untouched
- **WHEN** an expense of 150.00 is exported
- **THEN** its amount cell SHALL be the number -150.00, not an escaped string

### Requirement: PDF format
The PDF SHALL be A4 with the Can_cen brand (logotype "C_C" and the name "Can_cen") and period in the header of every page, a footer "Generado el dd/mm/aaaa hh:mm · Página X de Y", the same sections as the Excel, the movements table header repeated on every page, and Argentine formatting (`$ 1.234,56`, `US$ 1.234,56`, `25/10/2026`) produced without changing the process locale. User text that cannot be represented in the PDF font (for example emojis) SHALL be removed instead of failing.

#### Scenario: es-AR formatting
- **WHEN** a report includes an ARS amount of 1234.5
- **THEN** the PDF text SHALL show `$ 1.234,50`

#### Scenario: Long report pagination
- **WHEN** a report has 300 movements
- **THEN** the PDF SHALL span several pages each showing the table header and "Página X de Y"

#### Scenario: Emoji in category
- **WHEN** a category name contains an emoji
- **THEN** the PDF SHALL be generated successfully without that character

### Requirement: Export limits and resource protection
The export SHALL count matching movements before generating and respond 422 with a Spanish message asking to narrow the range when they exceed 20,000 for `xlsx` or 5,000 for `pdf`. File generation SHALL run outside the event loop (threadpool) into a spooled temporary file. Exports SHALL be rate limited per user (10 per 5 minutes) responding 429 with `Retry-After`.

#### Scenario: Too many rows for PDF
- **WHEN** a PDF export matches 5,001 movements
- **THEN** the endpoint SHALL respond 422 and no file SHALL be generated

#### Scenario: Rate limit
- **WHEN** a user requests an 11th export within 5 minutes with rate limiting enabled
- **THEN** the endpoint SHALL respond 429 with a `Retry-After` header

### Requirement: Export UI on web and mobile
The web Finance page SHALL offer an "Exportar" action opening a form with date range (default current month), type, category, account (prefilled from the active table filters), format (Excel/PDF) and "Incluir inversiones y patrimonio", which downloads the file and shows server errors (422/429) in Spanish. The mobile app SHALL offer an "Exportar" tool in the Finance tools grid with the same options that saves the file in the app cache and opens the system share sheet with the correct MIME type. Export SHALL require connectivity on mobile and SHALL NOT go through the offline write queue.

#### Scenario: Web download
- **WHEN** the user submits the export form choosing Excel
- **THEN** the browser SHALL download the `.xlsx` with the filename from `Content-Disposition`

#### Scenario: Mobile share
- **WHEN** the user taps "Generar y compartir" choosing PDF on Android
- **THEN** the app SHALL write the PDF to the cache directory and open the share sheet with `application/pdf`

#### Scenario: Mobile offline
- **WHEN** the device has no connection
- **THEN** the app SHALL show "Necesitás conexión para exportar" and SHALL NOT enqueue the request
