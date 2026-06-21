## ADDED Requirements

### Requirement: Vite + React + TypeScript project initialized in frontend/
The system SHALL have a fully initialized Vite + React + TypeScript project in the `frontend/` directory ready for development.

#### Scenario: package.json exists with React, Vite, and TypeScript dependencies
- **WHEN** inspecting `frontend/package.json`
- **THEN** it SHALL list `react`, `react-dom`, `vite`, `typescript`, and `@vitejs/plugin-react` as dependencies

#### Scenario: Vite dev server starts successfully
- **WHEN** running `npm run dev` inside the `frontend/` directory
- **THEN** the Vite dev server SHALL start and serve the React application

### Requirement: Tailwind CSS configured with design tokens matching backend theme
The system SHALL configure Tailwind CSS with design tokens that align with the backend application's visual theme.

#### Scenario: Tailwind CSS is configured and functional
- **WHEN** a component uses a Tailwind utility class
- **THEN** the corresponding CSS SHALL be generated and applied correctly

#### Scenario: Design tokens are defined in tailwind.config.js
- **WHEN** inspecting `tailwind.config.js`
- **THEN** custom theme extensions SHALL be present for colors, spacing, and typography matching the backend's design

### Requirement: React Router with routes for all pages
The system SHALL configure React Router with routes for the four main pages: Dashboard, Finance, Notes, and Tasks.

#### Scenario: Root path renders Dashboard
- **WHEN** the user navigates to `/`
- **THEN** the Dashboard page component SHALL be rendered

#### Scenario: /finances path renders Finance page
- **WHEN** the user navigates to `/finances`
- **THEN** the Finance page component SHALL be rendered

#### Scenario: /notes path renders Notes page
- **WHEN** the user navigates to `/notes`
- **THEN** the Notes page component SHALL be rendered

#### Scenario: /tasks path renders Tasks page
- **WHEN** the user navigates to `/tasks`
- **THEN** the Tasks page component SHALL be rendered

### Requirement: Axios instance configured with baseURL and credentials
The system SHALL provide a pre-configured Axios HTTP client instance pointed at the backend service with credential forwarding enabled.

#### Scenario: Axios instance uses backend baseURL
- **WHEN** a request is made using the shared Axios instance
- **THEN** the request base URL SHALL be `http://backend:8000`

#### Scenario: Axios instance sends credentials with requests
- **WHEN** any request is made through the Axios instance
- **THEN** credentials (cookies) SHALL be included via `withCredentials: true`

### Requirement: TypeScript strict mode enabled
The system SHALL enable TypeScript strict mode to enforce full type safety across the frontend codebase.

#### Scenario: tsconfig.json has strict mode enabled
- **WHEN** inspecting `tsconfig.json`
- **THEN** `strict: true` SHALL be set in compiler options

#### Scenario: Type errors prevent build
- **WHEN** a component has a type error
- **THEN** the TypeScript compiler SHALL report the error and the build SHALL fail

### Requirement: Shared Layout component with sidebar navigation
The system SHALL provide a shared `Layout` component that wraps all pages with a consistent sidebar navigation.

#### Scenario: Layout renders sidebar with navigation links
- **WHEN** the Layout component mounts
- **THEN** a sidebar SHALL be rendered with links to Dashboard, Finance, Notes, and Tasks

#### Scenario: Active route is highlighted in sidebar
- **WHEN** the user is on the Finance page
- **THEN** the Finance navigation item in the sidebar SHALL be visually highlighted

### Requirement: Loading states for all API-dependent views
The system SHALL display loading indicators in every view that depends on API data while requests are in flight.

#### Scenario: Loading skeleton shows while fetching data
- **WHEN** a page mounts and begins fetching data from the API
- **THEN** a loading skeleton or spinner SHALL be displayed until the data arrives

#### Scenario: Loading state is cleared after data arrives
- **WHEN** the API response is received successfully
- **THEN** the loading indicator SHALL be replaced with the actual content

### Requirement: Error boundary component for graceful error handling
The system SHALL provide an Error Boundary component that catches React rendering errors and displays a fallback UI instead of a blank screen.

#### Scenario: Error boundary catches rendering error
- **WHEN** a child component throws an error during rendering
- **THEN** the error boundary SHALL catch it and display a user-friendly error message

#### Scenario: Error boundary does not crash the entire app
- **WHEN** an error occurs in one page component wrapped by the error boundary
- **THEN** other pages and the navigation SHALL remain functional
