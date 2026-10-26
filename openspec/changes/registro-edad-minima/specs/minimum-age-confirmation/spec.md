## ADDED Requirements

### Requirement: Registration requires the minimum-age declaration
`POST /auth/api/register` SHALL require a boolean field `confirm_age` in addition to `accept_terms`. If `confirm_age` is missing or `false`, the system SHALL respond 422, SHALL NOT create the user and SHALL NOT send the verification email. The validation message SHALL be "Tenés que confirmar que tenés 16 años o más". When registration succeeds, the system SHALL set `users.age_confirmed_at` to the current UTC time, together with `terms_accepted_version` and `terms_accepted_at`.

#### Scenario: Register without confirming age
- **WHEN** a client sends `POST /auth/api/register` with `accept_terms = true` and `confirm_age = false`
- **THEN** the system SHALL respond 422 and no user with that email SHALL exist

#### Scenario: Register omitting the field
- **WHEN** a client sends `POST /auth/api/register` with `accept_terms = true` and without `confirm_age`
- **THEN** the system SHALL respond 422 and no user SHALL be created

#### Scenario: Register confirming age
- **WHEN** a client sends `POST /auth/api/register` with `accept_terms = true` and `confirm_age = true`
- **THEN** the system SHALL respond 201, the response SHALL include `age_confirmed = true` and `terms_accepted_version` equal to the current version, and the stored user SHALL have a non-null `age_confirmed_at`

### Requirement: Legacy HTML registration is disabled
`GET /auth/register` and `POST /auth/register` SHALL NOT render the legacy form nor create users. Both SHALL respond 303 redirecting to the SPA registration page (`{PUBLIC_BASE_URL}/register`). The legacy HTML login and logout SHALL keep working.

#### Scenario: Legacy form page
- **WHEN** a client requests `GET /auth/register`
- **THEN** the system SHALL respond 303 with `Location` pointing to the SPA `/register`

#### Scenario: Legacy form submission
- **WHEN** a client posts the legacy register form with valid data
- **THEN** the system SHALL respond 303 to the SPA `/register` and SHALL NOT create any user

### Requirement: Accepting terms requires the minimum-age declaration
`POST /auth/api/accept-terms` SHALL require `confirm_age = true` in addition to `version`. If `confirm_age` is missing or `false`, the system SHALL respond 422 and SHALL NOT change `terms_accepted_version`, `terms_accepted_at` or `age_confirmed_at`. The existing version check (409 when `version` is not the current one) SHALL still apply. On success, the system SHALL set `age_confirmed_at` to the current UTC time only if it was null, and SHALL NOT overwrite an earlier confirmation.

#### Scenario: Accept terms without confirming age
- **WHEN** an authenticated user sends `POST /auth/api/accept-terms` with the current version and `confirm_age = false`
- **THEN** the system SHALL respond 422 and `GET /auth/api/me` SHALL keep the previous `terms_accepted_version` and `age_confirmed = false`

#### Scenario: Accept terms confirming age
- **WHEN** an authenticated user with `age_confirmed_at = null` sends `POST /auth/api/accept-terms` with the current version and `confirm_age = true`
- **THEN** the system SHALL respond 200 with `age_confirmed = true` and the stored `age_confirmed_at` SHALL be non-null

#### Scenario: Earlier confirmation is preserved
- **WHEN** a user who already has `age_confirmed_at` accepts a newer terms version with `confirm_age = true`
- **THEN** `age_confirmed_at` SHALL keep its original value and `terms_accepted_at` SHALL be updated

#### Scenario: Stale version still rejected
- **WHEN** a user sends `confirm_age = true` with a version different from `CURRENT_TERMS_VERSION`
- **THEN** the system SHALL respond 409 and SHALL NOT set `age_confirmed_at`

### Requirement: Age confirmation status is exposed to clients
`UserOut` (`GET/PATCH /auth/api/me`, `POST /auth/api/accept-terms`, `POST /auth/api/verify-email`) and `AuthResponse` (`POST /auth/api/login`, `POST /auth/api/register`) SHALL include `age_confirmed: bool`, `true` if and only if `users.age_confirmed_at` is not null. The raw timestamp SHALL NOT be exposed in these responses; it SHALL be included in the account data export as part of the user row.

#### Scenario: Existing user without confirmation
- **WHEN** a user created before this change (with `age_confirmed_at = null`) calls `GET /auth/api/me`
- **THEN** the response SHALL include `age_confirmed = false`

#### Scenario: Account export includes the timestamp
- **WHEN** a user who confirmed their age exports their account data
- **THEN** the exported user row SHALL include `age_confirmed_at`

### Requirement: Google sign-up confirms age through the terms gate
An account created through `GET /auth/api/google/callback` SHALL be stored with `terms_accepted_version = null` and `age_confirmed_at = null`, so that the client shows the terms gate before allowing use of the app. The age SHALL be confirmed when that user accepts the terms through `POST /auth/api/accept-terms` with `confirm_age = true`. An existing account that signs in with Google SHALL keep its stored values.

#### Scenario: First sign-in with Google
- **WHEN** a person signs in with Google for the first time
- **THEN** `GET /auth/api/me` SHALL return `terms_accepted_version = null` and `age_confirmed = false`

#### Scenario: Google user confirms in the gate
- **WHEN** that user sends `POST /auth/api/accept-terms` with the current version and `confirm_age = true`
- **THEN** `GET /auth/api/me` SHALL return the current `terms_accepted_version` and `age_confirmed = true`

### Requirement: Clients show the gate until age and current terms are confirmed
The web app (`ProtectedRoute`) and the mobile app (`RootNavigator`) SHALL redirect an authenticated user to the terms gate when `terms_accepted_version` differs from the current version OR `age_confirmed` is `false`. In mobile, an offline session whose cached profile lacks `age_confirmed` SHALL NOT be gated (same rule as the existing offline exception); the gate SHALL apply once the profile is refreshed online.

#### Scenario: Existing user with current terms but no age confirmation
- **WHEN** a user with `terms_accepted_version` equal to the current version and `age_confirmed = false` opens the app
- **THEN** the app SHALL show the terms gate instead of the requested screen

#### Scenario: Fully confirmed user
- **WHEN** a user with the current `terms_accepted_version` and `age_confirmed = true` opens the app
- **THEN** the app SHALL NOT show the gate

### Requirement: Single combined checkbox in registration and gate
The registration forms (web `RegisterPage`, mobile `RegisterScreen`) and the terms gates (web `AcceptTermsPage`, mobile `AcceptTermsScreen`) SHALL show one checkbox labeled "Tengo 16 años o más y acepto los Términos y Condiciones y la Política de Privacidad." (the mobile gate SHALL keep its mention of the Política de Reembolsos), with links to each document, and below it the helper text "Si tenés menos de 18, necesitás el consentimiento de tu madre, padre o tutor." The submit action SHALL stay disabled (or fail client-side validation) until the checkbox is checked, and checking it SHALL send both `accept_terms = true` (register only) and `confirm_age = true`.

#### Scenario: Submit without checking
- **WHEN** the person tries to register or accept without checking the box
- **THEN** the client SHALL NOT send the request: registration forms SHALL show "Tenés que confirmar tu edad y aceptar los Términos para continuar" and the gates SHALL keep the accept button disabled

#### Scenario: Submit after checking
- **WHEN** the person checks the box and submits
- **THEN** the request SHALL include `confirm_age = true`

### Requirement: Terms version 1.1 declares the minimum age
The Terms and Conditions SHALL be published as version 1.1, stating in section 2 that by creating an account or accepting the Terms the person declares being at least 16 years old and, if under 18, having the consent of their mother, father or legal guardian. `CURRENT_TERMS_VERSION` SHALL be `1.1` in the backend default, in `docker-compose.prod.yml`, in the env examples, and in the mobile bundle; the three text mirrors (`legal/terminos-y-condiciones.md`, web `TermsPage`, mobile `legalText.ts`) SHALL show the same text, version and date.

#### Scenario: Users who accepted 1.0
- **WHEN** a user with `terms_accepted_version = "1.0"` opens the app after the deploy
- **THEN** the app SHALL show the gate and, after accepting with `confirm_age = true`, the user SHALL have `terms_accepted_version = "1.1"` and `age_confirmed = true`
