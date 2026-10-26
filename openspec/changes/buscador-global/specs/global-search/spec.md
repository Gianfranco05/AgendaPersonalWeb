## ADDED Requirements

### Requirement: Authenticated global search endpoint
The system SHALL expose `GET /api/v1/search` with query parameters `q` (required), `types` (optional, comma-separated) and `limit` (optional). The endpoint SHALL require an authenticated user, SHALL be read-only, SHALL respond with `Cache-Control: no-store` and SHALL return a JSON object `{query, groups}` where `query` is the normalized query as received (trimmed, whitespace collapsed) and `groups` is a list of `{type, label, has_more, items}`. Groups with no matching items SHALL be omitted. Groups SHALL appear in this fixed order: `notes`, `tasks`, `events`, `transactions`, `habits`, `goals`, `investments`, `study`, `library`, `media`, `work`, `travel`, `vehicle`, `projects`.

#### Scenario: Unauthenticated request
- **WHEN** a client without a valid session calls `GET /api/v1/search?q=cafe`
- **THEN** the system SHALL respond 401 and SHALL NOT run any search query

#### Scenario: Results grouped by type
- **WHEN** a user who has a note titled "Café con Juan" and a task titled "Comprar café" searches `q=cafe`
- **THEN** the response SHALL contain a `notes` group and a `tasks` group, in that order, each with the matching item

#### Scenario: No matches
- **WHEN** a user searches a term that matches nothing
- **THEN** the system SHALL respond 200 with `groups = []`

### Requirement: Query validation and limits
The system SHALL trim `q`, collapse internal whitespace and drop control characters; the result SHALL have between 2 and 100 characters, otherwise the system SHALL respond 422 with a message in Spanish. The system SHALL split `q` into at most 5 whitespace-separated tokens and ignore the rest. `limit` SHALL default to 5 and SHALL be an integer between 1 and 20 (per group), otherwise 422. `types` values SHALL be among the fourteen types listed above; an unknown value SHALL produce 422; an empty or missing `types` SHALL mean all types. Each group SHALL return at most `limit` items and SHALL set `has_more = true` when more matches exist.

#### Scenario: Query too short
- **WHEN** a user searches `q=" a "`
- **THEN** the system SHALL respond 422

#### Scenario: Query too long
- **WHEN** a user searches a `q` of 101 characters
- **THEN** the system SHALL respond 422

#### Scenario: Limit out of range
- **WHEN** a user searches with `limit=21` or `limit=0`
- **THEN** the system SHALL respond 422

#### Scenario: Unknown type
- **WHEN** a user searches with `types=notes,passwords`
- **THEN** the system SHALL respond 422

#### Scenario: Per-group limit and has_more
- **WHEN** a user with 7 notes containing "reunión" searches `q=reunion&types=notes&limit=5`
- **THEN** the `notes` group SHALL contain exactly 5 items and `has_more = true`

#### Scenario: Restrict to some types
- **WHEN** a user with matching notes and tasks searches with `types=tasks`
- **THEN** the response SHALL contain only the `tasks` group

### Requirement: Case- and accent-insensitive matching identical on PostgreSQL and SQLite
The system SHALL compare text after folding both the stored value and each token: lower-casing plus mapping `á é í ó ú ü ñ` and `Á É Í Ó Ú Ü Ñ` to `a e i o u u n`. The folding SHALL be implemented with the same SQL expression (`lower` and `replace`) on PostgreSQL and SQLite, SHALL NOT depend on database extensions or collation, and SHALL NOT require a database migration. Every token SHALL appear (substring match) in at least one searchable field of the item for the item to match.

#### Scenario: Missing accent in the query
- **WHEN** a user with a note titled "Café" searches `q=cafe`
- **THEN** the note SHALL be returned

#### Scenario: Accent in the query, none in the data
- **WHEN** a user with a task titled "Llamar a Jose" searches `q=josé`
- **THEN** the task SHALL be returned

#### Scenario: Upper-case accented data
- **WHEN** a user with an event titled "REUNIÓN ANUAL" searches `q=reunion`
- **THEN** the event SHALL be returned (including on SQLite, whose `lower()` does not lower non-ASCII letters)

#### Scenario: Ñ folding
- **WHEN** a user with a note titled "Cumple de la niña" searches `q=nina`
- **THEN** the note SHALL be returned

#### Scenario: All tokens required
- **WHEN** a user with notes "Café con Juan" and "Café solo" searches `q=cafe juan`
- **THEN** only "Café con Juan" SHALL be returned

#### Scenario: Partial word
- **WHEN** a user with a transaction whose merchant is "Cafetería Central" searches `q=cafet`
- **THEN** the transaction SHALL be returned

### Requirement: LIKE wildcards are treated literally
The system SHALL escape `\`, `%` and `_` in every token and SHALL use an explicit `ESCAPE` clause, so that those characters match literally on both database engines.

#### Scenario: Percent sign
- **WHEN** a user with notes "Descuento 20%" and "Descuento 200" searches `q=20%`
- **THEN** only "Descuento 20%" SHALL be returned

#### Scenario: Underscore
- **WHEN** a user with notes "mi_archivo" and "miXarchivo" searches `q=mi_a`
- **THEN** only "mi_archivo" SHALL be returned

#### Scenario: Only wildcards
- **WHEN** a user searches `q=%%`
- **THEN** the system SHALL return only items containing the literal text "%%" (and SHALL NOT return every item)

### Requirement: Simple ranking
Within each group the system SHALL order items by rank and then by date descending (then by `id` for stability): rank 0 when the folded title starts with the whole folded query, rank 1 when the folded title contains all tokens, rank 2 otherwise (match only in content fields or note tags). The `limit` SHALL be applied after ordering.

#### Scenario: Title match beats content match
- **WHEN** a user has a note titled "Presupuesto viaje" (older) and a note titled "Ideas" whose content mentions "presupuesto" (newer), and searches `q=presupuesto`
- **THEN** "Presupuesto viaje" SHALL be listed before "Ideas"

#### Scenario: Prefix beats contains
- **WHEN** a user has tasks "Pagar luz" and "Recordar pagar luz" and searches `q=pagar`
- **THEN** "Pagar luz" SHALL be listed first

#### Scenario: Most recent first at equal rank
- **WHEN** two notes both have "gym" in their title and none starts with it
- **THEN** the one with the most recent `updated_at` SHALL be listed first

### Requirement: Searchable types and fields
The system SHALL search the following, always restricted to rows of the authenticated user: `notes` (title, content, and names of the note's tags), `tasks` (title, description, area), `transactions` (product name, merchant name, product description, notes; excluding soft-deleted transactions), `events` (title, description, location), `habits` (goals with `goal_type` `binary` or `metric`: title, description), `goals` (goals with `goal_type` `progress` or `savings`: title, description), `investments` (name, ticker, institution, notes), `study` (subjects: name, professor; exams: title, notes), `library` (books: title, author, notes), `media` (media items: title, notes), `work` (opportunities: role, company, notes), `travel` (trips: destination, notes; packing items: name), `vehicle` (vehicles: name, brand, model, plate; maintenance records: notes), `projects` (projects: name, description; project tasks: title, notes).

#### Scenario: Note found by tag name
- **WHEN** a user has a note titled "Ideas" tagged "Facultad" and searches `q=facultad`
- **THEN** the note SHALL be returned with rank 2

#### Scenario: Deleted transaction is not returned
- **WHEN** a user soft-deletes a transaction "Nafta YPF" and searches `q=nafta`
- **THEN** that transaction SHALL NOT be returned

#### Scenario: Habit and goal are separate groups
- **WHEN** a user has a binary goal "Leer 20 minutos" and a progress goal "Leer 12 libros" and searches `q=leer`
- **THEN** the first SHALL be in the `habits` group and the second in the `goals` group

#### Scenario: Child entity of a paid plantilla
- **WHEN** a user who owns the `travel` plantilla has a packing item "Cargador" in trip "Bariloche" and searches `q=cargador`
- **THEN** the `travel` group SHALL contain an item with `entity = "packing_item"`, `parent_id` equal to the trip id

### Requirement: Result item shape, snippet and highlights
Each item SHALL include `id`, `type`, `entity`, `title`, `title_highlights`, `snippet` (nullable), `snippet_highlights`, `date` (ISO 8601: `YYYY-MM-DD` for dates, UTC datetime for timestamps), `parent_id` (nullable), `path` (web route) and an optional `meta` object with raw values (e.g. `amount`, `currency` and `type` for transactions; `status` for tasks; `goal_type` for habits and goals; `asset_type` for investments; `tags` and `archived` for notes). The snippet SHALL be a window of about 140 characters around the first match in content, with collapsed whitespace and `…` where truncated. Highlights SHALL be merged, non-overlapping `[start, end)` character offsets into `title` and `snippet` covering every token occurrence. The system SHALL NOT return HTML markup in any field.

#### Scenario: Snippet around the match
- **WHEN** a note has a 2,000-character content with "factura" near the end and the user searches `q=factura`
- **THEN** the item's `snippet` SHALL contain "factura", SHALL be at most about 140 characters, SHALL start with `…` and `snippet_highlights` SHALL point at "factura" inside the snippet

#### Scenario: Highlights on accented text
- **WHEN** the user searches `q=cafe` and the title is "Café con Juan"
- **THEN** `title_highlights` SHALL be `[[0, 4]]`

#### Scenario: Stored HTML is returned as text
- **WHEN** a note's title is `<b>hola</b>` and the user searches `q=hola`
- **THEN** `title` SHALL be the literal string `<b>hola</b>` and no field SHALL contain markup added by the server

### Requirement: Destination of each result
The system SHALL set `path` to the web route that opens the item: `/notes?open=<id>`, `/tasks?open=<id>`, `/events?open=<id>`, `/habits?open=<id>`, `/goals?open=<id>`, `/finances?tab=transacciones&open=<id>`, `/finances?tab=inversiones&open=<id>`, and for plantillas `/<study|library|media|work|travel|vehicle|projects>?open=<id>&entity=<entity>` plus `&parent=<parent_id>` for child entities. The identifiers in `path` SHALL be URL-encoded.

#### Scenario: Investment path
- **WHEN** a search returns an investment with id `abc`
- **THEN** its `path` SHALL be `/finances?tab=inversiones&open=abc`

#### Scenario: Exam path
- **WHEN** a search returns an exam with id `e1` of subject `s1`
- **THEN** its `path` SHALL be `/study?open=e1&entity=exam&parent=s1`

### Requirement: Strict per-user isolation
Every search query, including the tag subquery for notes, SHALL be filtered by the authenticated user's `user_id`. The system SHALL NOT return, count or reflect in `has_more` any row belonging to another user.

#### Scenario: Another user's data
- **WHEN** user A has a note "Proyecto secreto" and user B searches `q=secreto`
- **THEN** B's response SHALL NOT include A's note

#### Scenario: Another user's tag
- **WHEN** user A has a tag "Secreto" attached to A's note, and user B has a note "Ideas" with no tags, and B searches `q=secreto`
- **THEN** B's response SHALL be empty

#### Scenario: has_more is not influenced by other users
- **WHEN** user A has 10 notes with "gym" and user B has 2, and B searches `q=gym&types=notes&limit=5`
- **THEN** B's `notes` group SHALL have 2 items and `has_more = false`

### Requirement: Paid plantillas only when accessible and active
The system SHALL include the types `study`, `library`, `media`, `work`, `travel`, `vehicle` and `projects` only when the corresponding plantilla is accessible under the same rule as `require_module` (purchased, or the development bypass when billing is not configured and the environment is not production) AND is not disabled by the user. A requested type that is not accessible SHALL be silently omitted (no 402, no group). Base types SHALL always be searchable.

#### Scenario: Not purchased
- **WHEN** billing is enabled, a user has not purchased `library` but has rows in `books` (e.g. created before a refund), and searches a term matching a book
- **THEN** the response SHALL NOT contain a `library` group

#### Scenario: Explicitly requested but not purchased
- **WHEN** billing is enabled and a user who has not purchased `study` searches with `types=study`
- **THEN** the system SHALL respond 200 with `groups = []`

#### Scenario: Purchased and active
- **WHEN** billing is enabled and a user who purchased `media` has a media item "Dune" and searches `q=dune`
- **THEN** the response SHALL contain a `media` group with "Dune"

#### Scenario: Purchased but disabled
- **WHEN** a user purchased `media` and disabled it in Módulos, then searches `q=dune`
- **THEN** the response SHALL NOT contain a `media` group; after re-enabling it, the same search SHALL contain it

#### Scenario: Production without billing configured
- **WHEN** the environment is production, billing is not configured, and a user searches a term matching rows of a paid plantilla
- **THEN** the paid plantilla's group SHALL NOT be returned

### Requirement: Search rate limit
The system SHALL rate-limit `GET /api/v1/search` per authenticated user (not per IP) with a dedicated bucket of 120 requests per 60 seconds, backed by Redis when configured and in memory otherwise, honoring `RATE_LIMIT_ENABLED`. When exceeded, the system SHALL respond 429 with a `Retry-After` header and a Spanish message. The bucket SHALL be independent of the auth and billing limiters.

#### Scenario: Limit exceeded
- **WHEN** a user makes 121 searches within 60 seconds with rate limiting enabled
- **THEN** the 121st request SHALL receive 429 with `Retry-After`

#### Scenario: Other users unaffected
- **WHEN** user A has exhausted the search limit
- **THEN** user B's searches SHALL still succeed

### Requirement: Search terms are not logged
The system SHALL NOT write the search terms to application logs, metrics labels or error reports, and the production nginx configuration SHALL log `/api/v1/search` requests without the query string.

#### Scenario: Application log line
- **WHEN** a user searches `q=psicologo`
- **THEN** the request log line SHALL contain the path `/api/v1/search` and SHALL NOT contain `psicologo`
