## ADDED Requirements

### Requirement: Finance export and import from real API
When mock mode is disabled, the web and mobile clients SHALL call `GET /api/v1/finance/export` as a binary download (`responseType` blob on web, arraybuffer on mobile) using the filename from `Content-Disposition`, and SHALL call `GET /api/v1/finance/imports/presets`, `POST /api/v1/finance/imports/preview` (multipart), `PUT /api/v1/finance/imports/{id}/mapping`, `POST /api/v1/finance/imports/{id}/confirm`, `GET /api/v1/finance/imports`, `GET /api/v1/finance/imports/{id}` and `DELETE /api/v1/finance/imports/{id}`, sending `tz_offset_minutes` where accepted. When mock mode is enabled, the web client SHALL serve equivalent mock data with the same shapes. `TransactionResponse` SHALL additively expose `import_batch_id` (nullable) and existing clients SHALL keep working.

#### Scenario: Export download
- **WHEN** `downloadFinanceExport({ format: 'xlsx', ... })` is called with mock disabled
- **THEN** it SHALL `GET /api/v1/finance/export` with the given query and return the file as a Blob with its filename

#### Scenario: Preview upload
- **WHEN** `previewImport(file, { preset, accountId })` is called
- **THEN** it SHALL `POST` a multipart body to `/api/v1/finance/imports/preview` with `file`, `preset`, `account_id` and `tz_offset_minutes`

#### Scenario: Mock mode
- **WHEN** mock mode is enabled and `previewImport` is called
- **THEN** it SHALL return a mock preview including at least one `duplicate` and one `error` row without any network request

### Requirement: Import cache invalidation
After an import is confirmed or undone, the clients SHALL revalidate the `finance/imports`, `finance/summary`, `finance/transactions` and `finance/reports` cache keys (and `finance/net-worth` when present), the same way as after creating or deleting a transaction.

#### Scenario: After confirm
- **WHEN** `confirmImport()` succeeds
- **THEN** the summary, transactions, reports and imports keys SHALL be revalidated

#### Scenario: After undo
- **WHEN** `undoImport()` succeeds
- **THEN** the summary, transactions, reports and imports keys SHALL be revalidated
