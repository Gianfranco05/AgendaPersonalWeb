## ADDED Requirements

### Requirement: Import preview upload
The backend SHALL expose `POST /api/v1/finance/imports/preview` (authenticated, multipart) accepting `file`, optional `preset`, optional `account_id` (must belong to the user) and optional `tz_offset_minutes`. It SHALL parse the file without creating transactions, store an import batch with status `preview` that expires 24 hours later, and return the detected preset, the mapping and its source (`preset`, `remembered`, `heuristic` or `user`), headers, header row, the first raw sample rows, every parsed row with its status and errors, counts per status, totals per currency of the valid rows, warnings and the expiration time.

#### Scenario: Mercado Pago release report detected
- **WHEN** a user uploads a CSV with columns `DATE,SOURCE_ID,RECORD_TYPE,DESCRIPTION,NET_CREDIT_AMOUNT,NET_DEBIT_AMOUNT,CURRENCY`
- **THEN** the preview SHALL report preset `mercadopago_release`, create no transaction and return a batch with status `preview`

#### Scenario: Generic bank file
- **WHEN** a user uploads a CSV with three account-info lines followed by `Fecha;Concepto;Débito;Crédito;Saldo`
- **THEN** the preview SHALL detect the header on the fourth line, use preset `generic` with a heuristic mapping of date, description, debit and credit, and ignore the balance column

#### Scenario: Foreign account
- **WHEN** `account_id` belongs to another user
- **THEN** the endpoint SHALL respond 404

### Requirement: Upload validation and safety
The import SHALL reject files larger than 2 MiB (413, enforced while reading the stream and not only by `Content-Length`), with more than 5,000 data rows or 50 columns (422), and any content that is not CSV text or an XLSX zip determined by content inspection (415, with a specific message for legacy `.xls`). XLSX files SHALL be checked before parsing for zip bombs (at most 200 entries, 25 MiB total uncompressed, compression ratio at most 100), path traversal entries and macros, and SHALL be parsed with XML entity protection. Formulas SHALL never be evaluated: only cached values SHALL be read, and a formula cell without a cached value SHALL produce a row error. CSV SHALL be decoded as UTF-8 (with or without BOM) falling back to Windows-1252, with the delimiter detected among `,`, `;`, tab and `|`. Cell text SHALL be truncated to 500 characters.

#### Scenario: Oversized file
- **WHEN** a 3 MiB file is uploaded
- **THEN** the endpoint SHALL respond 413 and store no batch

#### Scenario: Legacy xls
- **WHEN** an OLE `.xls` file is uploaded
- **THEN** the endpoint SHALL respond 415 asking to save it as `.xlsx` or `.csv`

#### Scenario: Zip bomb
- **WHEN** an `.xlsx` whose entries decompress to more than 25 MiB is uploaded
- **THEN** the endpoint SHALL reject it without fully decompressing it

#### Scenario: Formula without cached value
- **WHEN** an `.xlsx` amount cell contains `=1+1` with no cached value
- **THEN** that row SHALL have status `error` with a message about formulas and nothing SHALL be evaluated

#### Scenario: Windows-1252 CSV
- **WHEN** a CSV encoded in Windows-1252 contains `Débito`
- **THEN** the header SHALL be read correctly as `Débito`

### Requirement: Presets and remembered mapping
The system SHALL provide presets `mercadopago_release` (only `RECORD_TYPE = release` rows imported; debit/credit from `NET_DEBIT_AMOUNT`/`NET_CREDIT_AMOUNT`; currency `CURRENCY`; reference `SOURCE_ID`; known `DESCRIPTION` codes translated to Spanish), `mercadopago_account_money` (signed `SETTLEMENT_NET_AMOUNT`, falling back to `TRANSACTION_AMOUNT` signed by `TRANSACTION_TYPE`) and `generic` (column mapping proposed from Spanish header heuristics), listed by `GET /api/v1/finance/imports/presets`. Presets SHALL match English column identifiers and their translated aliases. A mapping SHALL support date, optional time, one or more description columns, amount mode `signed`, `debit_credit` or `amount_and_type`, currency column or default currency, reference, rows to skip, date format, decimal separator and sign inversion. When a confirmed batch of the same user has the same header signature, its mapping SHALL be reused and reported as `remembered`.

#### Scenario: Informational rows skipped
- **WHEN** a Mercado Pago release file includes `initial_available_balance`, `total` and `available_balance` rows
- **THEN** those rows SHALL have status `skipped` and SHALL NOT be importable

#### Scenario: Remembered mapping
- **WHEN** a user confirmed a generic import with a custom mapping and later uploads a file with the same headers
- **THEN** the new preview SHALL apply that mapping with `mapping_source = "remembered"`

#### Scenario: Remembered mapping is per user
- **WHEN** another user uploads a file with the same headers
- **THEN** the first user's mapping SHALL NOT be applied

### Requirement: Remapping without re-upload
The backend SHALL expose `PUT /api/v1/finance/imports/{id}/mapping` accepting `preset`, `header_row`, `mapping`, `account_id` and `tz_offset_minutes`, recomputing the full preview from the stored raw table without a new upload. An expired preview SHALL respond 410; a batch that is not in `preview` status SHALL respond 409.

#### Scenario: Change decimal separator
- **WHEN** the user sets `decimal_separator` to `.` on a preview
- **THEN** the response SHALL recompute every amount with that separator

#### Scenario: Expired preview
- **WHEN** the mapping is updated 25 hours after the preview was created
- **THEN** the endpoint SHALL respond 410

### Requirement: Date, amount, sign and currency parsing
Dates SHALL be parsed from ISO datetimes with offset (converted to the user's local date and time using `tz_offset_minutes`), `yyyy-mm-dd`, `dd/mm/yyyy`, `dd-mm-yyyy`, `dd.mm.yyyy`, `dd/mm/yy`, Excel date cells and Excel serial numbers, defaulting to day-first and switching to month-first only when the column proves it; valid dates SHALL be between 2000-01-01 and one year after today. Amounts SHALL accept Argentine and English formats (`1.234,56`, `1234,56`, `1,234.56`, `1234.56`), currency symbols (`$`, `US$`, `U$S`, `€`) and negatives as leading or trailing minus or parentheses, honoring an explicit decimal separator when given, quantized to 2 decimals and bounded by the money limit. Zero amounts SHALL be skipped. Negative signed amounts and debits SHALL become expenses; positive amounts and credits SHALL become incomes; amounts SHALL be stored positive. Currencies SHALL be normalized (`$`→ARS, `U$S`/`US$`→USD, `€`→EUR) and limited to ARS, USD, EUR, BRL, UYU and CLP, defaulting to the destination account currency or ARS.

#### Scenario: Argentine number
- **WHEN** a signed amount cell is `-1.234,56`
- **THEN** the row SHALL be an expense of 1234.56

#### Scenario: Parentheses negative
- **WHEN** an amount cell is `($ 2.500,00)`
- **THEN** the row SHALL be an expense of 2500.00

#### Scenario: Mercado Pago timezone
- **WHEN** a row date is `2026-10-03T23:30:00-04:00` and `tz_offset_minutes = -180`
- **THEN** the transaction date SHALL be `2026-10-04` with time `00:30:00`

#### Scenario: Day-first default
- **WHEN** a date column contains `03/10/2026` and `15/10/2026`
- **THEN** they SHALL be parsed as October 3 and October 15, 2026

#### Scenario: Both debit and credit filled
- **WHEN** a row has values in both the debit and the credit columns
- **THEN** that row SHALL have status `error`

#### Scenario: Amount above limit
- **WHEN** an amount exceeds 9.999.999.999,99
- **THEN** that row SHALL have status `error`

### Requirement: Suggested category
Each valid row SHALL include a suggested category and its source: first the category most used by the same user for the same normalized description and type in the last 24 months (`history`), then the most used category for the first significant keyword of the description (`history`), then a keyword rule mapping known Argentine merchants to a merchant category and to a user category whose name matches that merchant category's synonyms (`rule`), otherwise none (`none`). Suggestions SHALL only reference the requesting user's categories.

#### Scenario: History wins
- **WHEN** the user previously categorized "SUPERMERCADO COTO 123" as "Comida" and imports "Supermercado Coto 456"
- **THEN** the suggestion SHALL be "Comida" with source `history`

#### Scenario: Keyword rule
- **WHEN** a user with a category "Transporte" and no history imports "UBER *TRIP"
- **THEN** the suggestion SHALL be "Transporte" with source `rule` and merchant category `transportation`

#### Scenario: No cross-user history
- **WHEN** only another user has history for a description
- **THEN** that history SHALL NOT influence the suggestion

### Requirement: Duplicate detection
Each row SHALL get a row hash from date, type, amount, currency, normalized description, reference and its occurrence number among identical rows of the same file. A row whose hash matches a non-deleted transaction of the same user SHALL have status `duplicate`. A row with a non-deleted transaction of the same user with the same type, amount and currency, date within ±1 day and similar description SHALL have status `possible_duplicate` with a reference to that transaction. Both statuses SHALL be excluded by default. A file identical (same SHA-256) to a confirmed, not undone batch SHALL produce a warning.

#### Scenario: Re-uploading the same file
- **WHEN** a user confirms a file and uploads it again
- **THEN** every previously imported row SHALL have status `duplicate` and the preview SHALL warn that the file was already imported

#### Scenario: Two identical rows in one file
- **WHEN** a file contains two identical rows (same date, amount and description)
- **THEN** both SHALL be importable on the first import and both SHALL be `duplicate` when the same file is uploaded again

#### Scenario: Manual transaction similar
- **WHEN** the user manually loaded "Netflix" for 5.999,00 on 2026-10-05 and imports "NETFLIX.COM" for 5.999,00 on 2026-10-06
- **THEN** the imported row SHALL be `possible_duplicate` referencing the manual transaction

### Requirement: Confirm import
The backend SHALL expose `POST /api/v1/finance/imports/{id}/confirm` with a list of `{index, include, category_id?, type?, description?}`. It SHALL create transactions only for included rows whose status is `ok` or `possible_duplicate`, rejecting with 422 any included `error` or `duplicate` row and any override with a foreign category, invalid type or description outside 1–255 characters. All transactions and the batch status change to `confirmed` SHALL be committed in a single database transaction. Before inserting it SHALL re-check row hashes against the database and skip rows already present, counting them as duplicates. Created transactions SHALL carry `import_batch_id` and `import_row_hash`, the destination account data (bank name, account type, last 4) when an account was chosen, the merchant category from rules and the payment method `transfer` for Mercado Pago presets or `other` for generic. The stored raw table SHALL be cleared. Confirming a batch not in `preview` SHALL respond 409; an expired one 410.

#### Scenario: Successful confirm
- **WHEN** the user confirms 10 included valid rows
- **THEN** 10 transactions SHALL be created for that user with `import_batch_id` set and the batch SHALL be `confirmed` with `imported_count = 10`

#### Scenario: Concurrent duplicate confirm
- **WHEN** two previews of the same file are confirmed one after the other
- **THEN** the second confirm SHALL create no transactions for rows already imported and count them as duplicates

#### Scenario: Including an error row
- **WHEN** the request includes a row with status `error`
- **THEN** the endpoint SHALL respond 422 and create nothing

### Requirement: Import history and undo
The backend SHALL expose `GET /api/v1/finance/imports` (the user's confirmed and undone batches, newest first, limit up to 50), `GET /api/v1/finance/imports/{id}` and `DELETE /api/v1/finance/imports/{id}`. Deleting a `preview` batch SHALL discard it (204). Deleting a `confirmed` batch SHALL undo it: soft-delete (`is_deleted`, `deleted_at` in UTC) all its non-deleted transactions, including those edited after import, set status `undone` and return the batch with the number of affected and edited transactions. Undoing an `undone` batch SHALL respond 409. Undone rows SHALL no longer count as duplicates.

#### Scenario: Undo
- **WHEN** the user undoes a batch that created 10 transactions, 2 of them edited later
- **THEN** the 10 transactions SHALL be soft-deleted, the batch SHALL be `undone`, and the response SHALL report 2 edited

#### Scenario: Re-import after undo
- **WHEN** the user uploads the same file after undoing its batch
- **THEN** the rows SHALL have status `ok`, not `duplicate`

#### Scenario: Balance after undo
- **WHEN** a batch is undone
- **THEN** `GET /finance/summary` SHALL no longer include its amounts

### Requirement: Import data isolation, cleanup and account lifecycle
Every import endpoint SHALL only access the requesting user's batches, transactions, categories and accounts; foreign batch ids SHALL respond 404. Expired preview batches SHALL be deleted when the same user creates a new preview, and a user SHALL have at most 5 open previews (the oldest is discarded). Preview and remap SHALL be rate limited per user (20 per 10 minutes, 429). The `import_batches` table SHALL be included in account export (without the `raw_table` column) and in account deletion, ordered after `transactions` and before `bank_accounts`.

#### Scenario: Foreign batch
- **WHEN** user B calls confirm, mapping, get or delete on user A's batch
- **THEN** the endpoint SHALL respond 404 and A's batch SHALL be unchanged

#### Scenario: Account export
- **WHEN** a user with import batches exports their account data
- **THEN** the JSON SHALL include `import_batches` without `raw_table`

#### Scenario: Account deletion
- **WHEN** a user with confirmed imports deletes their account
- **THEN** their transactions and import batches SHALL be deleted without foreign key errors in PostgreSQL

### Requirement: Import UI on web and mobile
The web app SHALL provide an import page at `/finances/import` with three steps — upload (CSV/XLSX drop zone with client-side size check, source selector, optional destination account and Mercado Pago download help), preview (mapping panel calling the remap endpoint, table with per-row checkbox, status chips, suggested category selector with its source, income/expense toggle, status filter and selected totals per currency) and confirm (summary and result) — plus an import history with "Deshacer" that warns how many transactions were edited. The mobile app SHALL provide an "Importar" tool in the Finance grid opening an import screen that picks a file with `expo-document-picker`, uploads it, shows the preview as a list with the same row actions, allows adjusting columns in a bottom sheet, confirms, and lists history with undo. Imports SHALL require connectivity on mobile and SHALL NOT use the offline queue. The web mock mode SHALL simulate preview, confirm, history and undo.

#### Scenario: Web preview interaction
- **WHEN** the user unchecks a row and changes another row's category, then confirms
- **THEN** the confirm request SHALL send `include=false` for the first and the chosen `category_id` for the second

#### Scenario: Mobile pick and preview
- **WHEN** the user picks a CSV on Android whose MIME type is `text/comma-separated-values`
- **THEN** the app SHALL upload it and show the preview returned by the server

#### Scenario: Undo from history
- **WHEN** the user taps "Deshacer" on a confirmed batch and accepts the warning
- **THEN** the batch SHALL show as undone and the transactions list and balance SHALL refresh
