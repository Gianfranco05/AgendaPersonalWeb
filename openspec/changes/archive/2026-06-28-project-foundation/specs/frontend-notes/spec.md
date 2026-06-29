## ADDED Requirements

### Requirement: Notes page with two-panel layout
The system SHALL render the Notes page at `/notes` with a two-panel layout: a sidebar on the left and a content editor on the right.

#### Scenario: Sidebar panel is displayed on the left
- **WHEN** the user navigates to `/notes`
- **THEN** a sidebar panel SHALL be rendered on the left side containing the notes list

#### Scenario: Editor panel is displayed on the right
- **WHEN** the user navigates to `/notes`
- **THEN** an editor panel SHALL be rendered on the right side for viewing and editing note content

### Requirement: Sidebar with note list and search
The system SHALL render a sidebar containing a list of notes with title previews and a search field that filters by title or tag.

#### Scenario: Note list displays title previews
- **WHEN** notes are loaded
- **THEN** each note in the sidebar SHALL show its title as a clickable preview item

#### Scenario: Search filters notes by title
- **WHEN** the user types a query in the search field
- **THEN** the note list SHALL filter to show only notes whose title contains the query

#### Scenario: Search filters notes by tag
- **WHEN** the user types a tag name in the search field
- **THEN** the note list SHALL filter to show only notes with that tag

### Requirement: Sidebar tag filter
The system SHALL provide tag-based filtering in the sidebar to show only notes with a selected tag.

#### Scenario: Selecting a tag filters the note list
- **WHEN** the user clicks on a tag in the sidebar
- **THEN** only notes associated with that tag SHALL be displayed

#### Scenario: Deselecting a tag shows all notes again
- **WHEN** the user deselects the active tag filter
- **THEN** all notes SHALL be displayed in the sidebar

### Requirement: Markdown editor with preview
The system SHALL provide a Markdown editor using `@uiw/react-md-editor` with a live preview pane.

#### Scenario: Editor supports Markdown syntax
- **WHEN** the user types Markdown syntax in the editor
- **THEN** the preview pane SHALL render the formatted Markdown output in real time

#### Scenario: Editor and preview are visible simultaneously
- **WHEN** a note is open in the editor
- **THEN** both the editing area and the rendered preview SHALL be visible

### Requirement: Code snippet support with syntax highlighting
The system SHALL support code snippets within notes with automatic language detection and syntax highlighting.

#### Scenario: Code blocks are syntax highlighted
- **WHEN** a note contains a fenced code block with a language identifier (e.g., ```python)
- **THEN** the preview SHALL render the code with syntax highlighting for that language

#### Scenario: Code blocks without language are rendered as plain text
- **WHEN** a note contains a fenced code block without a language identifier
- **THEN** the code SHALL be rendered as monospaced plain text

### Requirement: Create, edit, and delete note operations
The system SHALL support creating new notes, editing existing notes, and deleting notes through the API.

#### Scenario: Creating a new note
- **WHEN** the user clicks the new note button and saves content
- **THEN** the note SHALL be created via the API and appear in the sidebar list

#### Scenario: Editing an existing note
- **WHEN** the user modifies a note's content and saves
- **THEN** the note SHALL be updated via the API and the changes SHALL persist

#### Scenario: Deleting a note
- **WHEN** the user deletes a note
- **THEN** the note SHALL be removed via the API and disappear from the sidebar

### Requirement: Pin/unpin toggle per note
The system SHALL provide a toggle to pin or unpin each note, with pinned notes appearing at the top of the list.

#### Scenario: Pinning a note moves it to the top
- **WHEN** the user toggles a note as pinned
- **THEN** the note SHALL move to the top of the sidebar list above all unpinned notes

#### Scenario: Unpinning a note returns it to default order
- **WHEN** the user toggles a pinned note as unpinned
- **THEN** the note SHALL return to its position based on the default sort order

### Requirement: Archive note as soft delete
The system SHALL support archiving a note, which marks it as archived without permanently deleting it.

#### Scenario: Archiving a note hides it from the active list
- **WHEN** the user archives a note
- **THEN** the note SHALL disappear from the active notes list but remain stored in the database

### Requirement: Color picker for note card
The system SHALL provide a color picker to assign a background color to each note card in the sidebar.

#### Scenario: Color picker assigns a color to the note card
- **WHEN** the user selects a color from the color picker for a note
- **THEN** the note card in the sidebar SHALL display with the selected background color

#### Scenario: Selected color persists across sessions
- **WHEN** a color is assigned to a note and the page is refreshed
- **THEN** the note SHALL still display with the assigned color
