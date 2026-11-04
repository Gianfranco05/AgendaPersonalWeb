## ADDED Requirements

### Requirement: Web search palette opens from anywhere
The web app SHALL provide a global search palette mounted once in the authenticated layout. It SHALL open with `Ctrl+K` (and `⌘K` on macOS) from any authenticated page, preventing the browser's default action, and with a "Buscar" button in the sidebar and in the mobile header of the layout. When open it SHALL trap focus, focus the input, close with `Esc` or by clicking outside, and restore focus to the previously focused element on close.

#### Scenario: Keyboard shortcut
- **WHEN** an authenticated user presses `Ctrl+K` on the Finanzas page
- **THEN** the palette SHALL open with the search input focused

#### Scenario: Close with Escape
- **WHEN** the palette is open and the user presses `Esc`
- **THEN** the palette SHALL close and focus SHALL return to where it was

#### Scenario: Not available on public pages
- **WHEN** a visitor on `/login` presses `Ctrl+K`
- **THEN** nothing SHALL open

### Requirement: Live results with debounce
The palette SHALL query `GET /api/v1/search` 250 ms after the user stops typing, only when the trimmed input has at least 2 characters, and SHALL show the previous results while the new ones load (no flicker). It SHALL show a hint for fewer than 2 characters, a loading indicator, an empty state ("No encontramos nada para «…»"), and an error state; a 429 SHALL show "Estás buscando muy rápido, esperá un momento". Results SHALL be grouped by type with the group label, and each group with `has_more` SHALL offer "Ver más en {label}", which repeats the search for that type with `limit=20`.

#### Scenario: Debounced request
- **WHEN** the user types "cafe" quickly (four keystrokes within 250 ms)
- **THEN** the app SHALL send a single search request for "cafe"

#### Scenario: One character
- **WHEN** the user types "c"
- **THEN** the app SHALL NOT call the API and SHALL show "Escribí al menos 2 letras"

#### Scenario: See more
- **WHEN** the `notes` group has `has_more = true` and the user activates "Ver más en Notas"
- **THEN** the app SHALL request `types=notes&limit=20` and show up to 20 notes

### Requirement: Keyboard navigation and accessibility
The palette SHALL implement the ARIA combobox pattern (`role="combobox"` with `aria-expanded`, `aria-controls` and `aria-activedescendant`; results in a `role="listbox"` with `role="option"` items). `↓`/`↑` SHALL move the active item across all groups (wrapping at the ends), `Enter` SHALL open the active item, and the mouse SHALL also select and open items. Matched text SHALL be highlighted with `<mark>` built from the response offsets, without using `dangerouslySetInnerHTML`.

#### Scenario: Navigate across groups
- **WHEN** results show 2 notes and 1 task and the active item is the second note
- **THEN** pressing `↓` SHALL make the task active, and pressing `↓` again SHALL wrap to the first note

#### Scenario: Enter opens the item
- **WHEN** a task result is active and the user presses `Enter`
- **THEN** the palette SHALL close and the app SHALL navigate to the item's `path`

#### Scenario: Markup in user content is not rendered
- **WHEN** a result title is `<img src=x onerror=alert(1)>`
- **THEN** the title SHALL be displayed as literal text and no script SHALL run

### Requirement: Web destination pages open the item from the `open` parameter
The pages `/notes`, `/tasks`, `/events`, `/habits`, `/goals`, `/finances`, `/study`, `/library`, `/media`, `/work`, `/travel`, `/vehicle` and `/projects` SHALL read the `open` query parameter (plus `entity` and `parent` where applicable, and `tab` on `/finances`), wait for their data to load, and open the item's existing edit/detail view; when the page has no such view for that entity, they SHALL scroll to the item and highlight it. The parameters SHALL then be removed from the URL with a history replace. If the id does not exist, the page SHALL show "Ese elemento ya no existe" and stay on the list.

#### Scenario: Open a note
- **WHEN** the user navigates to `/notes?open=<id of an existing note>`
- **THEN** the note's edit modal SHALL open and the URL SHALL become `/notes`

#### Scenario: Open an investment
- **WHEN** the user navigates to `/finances?tab=inversiones&open=<id>`
- **THEN** the Inversiones tab SHALL be selected and that investment's edit modal SHALL open

#### Scenario: Deleted item
- **WHEN** the user navigates to `/tasks?open=<id that no longer exists>`
- **THEN** the page SHALL show "Ese elemento ya no existe" and the task board

#### Scenario: Back does not reopen
- **WHEN** the user opened a note from search, closed the modal and the page re-renders
- **THEN** the modal SHALL NOT reopen

### Requirement: Web mock mode supports search
When `VITE_MOCK_ENABLED` is on, the search API call SHALL be served from the mock data with the same folding, tokenization, wildcard-literal and ranking rules as the backend, and SHALL only include paid plantilla types whose mock module is owned and enabled.

#### Scenario: Mock accent-insensitive search
- **WHEN** mock mode is on and the user searches "cafe"
- **THEN** mock items containing "Café" SHALL be returned grouped by type

### Requirement: Mobile search screen from the Inicio header
The mobile app SHALL show a search icon button (accessible label "Buscar", touch target ≥ 44 dp) in the Inicio (Dashboard) header that opens a `Search` screen. The screen SHALL autofocus a text field with a clear button, query the API 300 ms after typing stops with at least 2 characters, and show results in a sectioned list grouped by type with highlighted title, two-line snippet, local date and formatted `meta` (amounts with the app's money formatter). It SHALL show loading, empty and error states, and when offline it SHALL show "Necesitás conexión para buscar" without queueing anything. It SHALL NOT show prices, purchase calls-to-action or any mention of the store.

#### Scenario: Open search from Inicio
- **WHEN** the user taps the search icon in the Inicio header
- **THEN** the Search screen SHALL open with the keyboard up

#### Scenario: Offline
- **WHEN** the device has no connection and the user types "cafe"
- **THEN** the screen SHALL show "Necesitás conexión para buscar"

#### Scenario: Not purchased plantilla
- **WHEN** the user has not purchased Biblioteca
- **THEN** no Biblioteca group nor any text inviting to buy it SHALL appear

### Requirement: Mobile result opens the item's screen
Tapping a result SHALL navigate across tabs to the item's screen with navigation params, and the destination screen SHALL open the item's existing edit/detail sheet (or scroll to and highlight it) once its data is loaded, then clear the params so that returning to the screen does not reopen it. Destinations: notes → Tareas/Notes, tasks → Tareas/TasksHome, events → Tareas/Events, habits → Hábitos/HabitsHome, progress goals → Hábitos/Goals, savings goals → Finanzas/Savings, transactions → Finanzas/FinanceHome, investments → Finanzas/Investments using the existing `investmentId` param, plantillas → Inicio stack screen of the plantilla with `openId`, `openEntity` and `parentId`. If the item no longer exists the screen SHALL show "Ese elemento ya no existe".

#### Scenario: Open a transaction
- **WHEN** the user taps a transaction result
- **THEN** the app SHALL switch to the Finanzas tab, show FinanceHome and open that transaction's edit sheet

#### Scenario: Open an investment
- **WHEN** the user taps an investment result
- **THEN** the app SHALL open Investments with `investmentId` and show that investment, as the maturity push does

#### Scenario: Open a project task
- **WHEN** the user taps a project task result
- **THEN** the app SHALL open the Projects screen, select the parent project and open that task

#### Scenario: Params are cleared
- **WHEN** the user opened a note from search, closed the sheet, switched tabs and came back to Notes
- **THEN** the sheet SHALL NOT reopen
