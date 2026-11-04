## ADDED Requirements

### Requirement: Optional app lock setting
The mobile app (Android and iOS) SHALL offer an optional app lock, disabled by default, under Ajustes › Seguridad › "Bloqueo de la app". Enabling it MUST require creating an app PIN. The configuration SHALL be stored per device and bound to the signed-in user id; it MUST NOT be synchronized to the server. The web app SHALL NOT offer or apply an app lock, and the mobile build running on web SHALL treat the lock as a no-op.

#### Scenario: Disabled by default
- **WHEN** a user signs in on a device for the first time
- **THEN** the app lock SHALL be disabled and the app SHALL open without asking for a PIN or biometrics

#### Scenario: Enabling requires a PIN
- **WHEN** the user turns on "Pedir huella o PIN al abrir"
- **THEN** the app SHALL ask for a new PIN twice and SHALL enable the lock only if both entries match and the PIN is valid

#### Scenario: Disabling requires authentication
- **WHEN** the user turns the lock off
- **THEN** the app SHALL require the current PIN or a successful biometric authentication before disabling it

#### Scenario: Not available on web
- **WHEN** the app runs with `Platform.OS === 'web'` or the user uses the web frontend
- **THEN** no Seguridad section SHALL be shown and no lock SHALL be applied

#### Scenario: Configuration of another user
- **WHEN** the session resolves to a user id different from the one stored in the lock configuration
- **THEN** the stored configuration SHALL be deleted and the app SHALL not be locked

### Requirement: App PIN format and secure storage
The app PIN SHALL be 4 to 6 digits. The app MUST reject PINs whose digits are all equal and strictly ascending or descending sequences (e.g. `1234`, `4321`, `012345`). The PIN MUST be stored only as a salted SHA-256 hash in the format `s256$<salt>$<hash>` with a random 16-byte salt, inside `expo-secure-store`; the plain PIN MUST NOT be persisted or logged anywhere. Changing the PIN SHALL require the current PIN.

#### Scenario: Trivial PIN rejected
- **WHEN** the user tries to set `0000`, `111111`, `1234` or `987654`
- **THEN** the app SHALL reject it with a message asking for a less predictable PIN

#### Scenario: Hash stored, not the PIN
- **WHEN** the user sets PIN `2580`
- **THEN** SecureStore SHALL contain a value starting with `s256$` and SHALL NOT contain the string `2580`

#### Scenario: Same PIN, different salt
- **WHEN** the same PIN is hashed twice
- **THEN** the two stored hashes SHALL differ and both SHALL verify the PIN

#### Scenario: Change PIN
- **WHEN** the user chooses "Cambiar PIN" and enters a wrong current PIN
- **THEN** the PIN SHALL NOT change and the failure SHALL count toward the attempt limit

### Requirement: Biometric unlock
When the device has strong (Class 3) biometrics enrolled, the app SHALL offer "Usar huella o rostro" via `expo-local-authentication`, with the app PIN always available as the alternative. The biometric prompt MUST disable the device credential fallback (the phone's PIN/pattern SHALL NOT unlock the app) and SHALL use `biometricsSecurityLevel: 'strong'`. Enabling biometrics SHALL require one successful biometric authentication.

#### Scenario: Biometrics offered only when available
- **WHEN** the device has no biometric hardware, nothing enrolled, or only weak biometrics on Android
- **THEN** the "Usar huella o rostro" option SHALL be hidden and only the PIN SHALL be used

#### Scenario: Automatic prompt on the lock screen
- **WHEN** the lock screen appears while the app is active and biometrics are enabled
- **THEN** the app SHALL show the biometric prompt once and SHALL offer a "Usar huella" button to retry

#### Scenario: User cancels the prompt
- **WHEN** the user taps "Usar PIN" in the biometric prompt
- **THEN** the lock screen SHALL remain with the PIN pad and no error message

#### Scenario: Biometrics removed from the device
- **WHEN** authentication returns `not_enrolled` or `not_available`
- **THEN** the app SHALL disable biometrics in the lock configuration, inform the user once, and keep PIN unlock working

### Requirement: When the app locks
With the lock enabled, the app SHALL be locked on every cold start, and when returning to the foreground after having been in the background for at least the configured timeout: immediate (0), 1, 5 or 15 minutes, default 1 minute. If the device clock moved backwards (negative elapsed time) the app SHALL lock. Transitions to the iOS `inactive` state SHALL NOT start the timer. Background trips started by the app itself (opening the browser for Google Calendar, the share sheet when exporting, the notification permission dialog) SHALL NOT lock on return if they last less than 5 minutes, and app state changes caused by the biometric prompt itself SHALL be ignored.

#### Scenario: Cold start
- **WHEN** the lock is enabled and the app process starts
- **THEN** the first rendered frame of the signed-in app SHALL be covered by the lock screen

#### Scenario: Return before the timeout
- **WHEN** the timeout is 5 minutes and the app returns to the foreground 4 minutes 59 seconds after going to the background
- **THEN** the app SHALL NOT lock

#### Scenario: Return after the timeout
- **WHEN** the timeout is 1 minute and the app returns 60 seconds or more after going to the background
- **THEN** the app SHALL lock

#### Scenario: Immediate timeout
- **WHEN** the timeout is "Inmediato" and the app returns from the background after any time
- **THEN** the app SHALL lock

#### Scenario: Clock moved backwards
- **WHEN** the current time is earlier than the recorded background time
- **THEN** the app SHALL lock

#### Scenario: Expected external trip
- **WHEN** the user exports data, the share sheet sends the app to the background and the user returns 30 seconds later with timeout "Inmediato"
- **THEN** the app SHALL NOT lock

#### Scenario: Biometric prompt does not relock
- **WHEN** the biometric prompt causes an `inactive`/`background` → `active` transition
- **THEN** the app SHALL NOT start a new lock cycle

#### Scenario: Fresh login
- **WHEN** the user signs in with email/password or Google and a lock configuration for that same user exists
- **THEN** the app SHALL start unlocked

### Requirement: Lock screen covers all content
While locked, the app SHALL show an opaque lock screen above the navigation and above any open bottom sheet, without unmounting the navigation tree. The lock screen MUST NOT show user data (name, amounts). Content underneath MUST be hidden from accessibility services. Open bottom sheets SHALL be hidden while locked and SHALL reappear with their state after unlocking. The Android back button on the lock screen SHALL NOT unlock the app.

#### Scenario: Form state preserved
- **WHEN** the user is filling an expense in a bottom sheet, the app locks, and the user unlocks
- **THEN** the bottom sheet SHALL reappear with the entered values

#### Scenario: Screen reader
- **WHEN** TalkBack or VoiceOver is active while the app is locked
- **THEN** only the lock screen elements SHALL be reachable

#### Scenario: Back button
- **WHEN** the user presses the Android back button on the lock screen
- **THEN** the app SHALL stay locked

### Requirement: Hide content in recent apps
With the lock enabled and the sub-setting "Ocultar en apps recientes" on (default on), the app SHALL prevent its content from appearing in the recent apps preview: on Android with `FLAG_SECURE` via `expo-screen-capture` (which also blocks screenshots and screen recording), on iOS with the app switcher blur protection. The setting SHALL explain that on Android it also blocks screenshots. With the lock disabled or the sub-setting off, screen capture SHALL be allowed.

#### Scenario: Recent apps on Android
- **WHEN** the lock and "Ocultar en apps recientes" are enabled and the user opens the recent apps screen
- **THEN** the app preview SHALL be blank

#### Scenario: Sub-setting off
- **WHEN** the user turns "Ocultar en apps recientes" off
- **THEN** screenshots SHALL be allowed again and the preview SHALL show the app content

#### Scenario: Native module missing
- **WHEN** the installed build does not include `expo-screen-capture` or `expo-local-authentication`
- **THEN** the app SHALL NOT crash: the lock SHALL keep working with PIN only and the recents option SHALL be hidden

### Requirement: PIN attempt limit with progressive wait
The app SHALL count failed PIN attempts persistently in SecureStore, so that closing the app does not reset the count. Failures 1–5 SHALL have no wait; failure 6 SHALL impose a 30-second wait, failure 7 one minute, failure 8 five minutes, failure 9 fifteen minutes; failure 10 SHALL sign the user out locally and delete the lock configuration. From failure 6 the app SHALL show how many attempts remain before signing out, and from failure 8 it SHALL warn about unsynchronized offline changes if any. During a wait the PIN pad SHALL be disabled with a countdown while biometric unlock remains available. A successful PIN or biometric unlock SHALL reset the count. If the device clock is earlier than the last failure, the full wait SHALL restart.

#### Scenario: Free attempts
- **WHEN** the user enters a wrong PIN for the fifth time
- **THEN** the app SHALL show an error and allow another attempt immediately

#### Scenario: First wait
- **WHEN** the user enters a wrong PIN for the sixth time
- **THEN** the PIN pad SHALL be disabled for 30 seconds and the screen SHALL say 4 attempts remain before signing out

#### Scenario: Wait survives restart
- **WHEN** the user is in a 5-minute wait, kills the app and reopens it 1 minute later
- **THEN** the remaining wait SHALL be about 4 minutes

#### Scenario: Tenth failure
- **WHEN** the user enters a wrong PIN for the tenth time
- **THEN** the app SHALL sign out locally (tokens, cache, offline queue and cached profile cleared), delete the lock configuration and attempt count, and show the login screen

#### Scenario: Success resets
- **WHEN** the user unlocks with the correct PIN or biometrics after 7 failures
- **THEN** the failure count SHALL be 0

#### Scenario: Biometrics during a wait
- **WHEN** the PIN pad is in a wait and biometrics are enabled
- **THEN** the user SHALL be able to unlock with biometrics

### Requirement: Forgot PIN
The lock screen SHALL offer "Olvidé mi PIN". After confirmation (which MUST state the number of pending offline changes that will be lost, if any) the app SHALL sign the user out locally, delete the lock configuration and the attempt count, and show the login screen. It SHALL work without network.

#### Scenario: Forgot PIN offline
- **WHEN** the device has no network and the user confirms "Olvidé mi PIN"
- **THEN** the app SHALL clear the local session and the lock configuration and show the login screen

#### Scenario: Pending changes warning
- **WHEN** there are 3 pending offline changes and the user taps "Olvidé mi PIN"
- **THEN** the confirmation SHALL say that 3 unsynchronized changes will be lost

### Requirement: Lock lifecycle with the session
Explicit sign-out and a change of server SHALL delete the lock configuration and attempt count. An expired session (401 after refresh) SHALL keep the configuration so that the same user remains protected after signing in again.

#### Scenario: Explicit logout
- **WHEN** the user taps "Cerrar sesión" in Ajustes
- **THEN** the lock configuration SHALL be deleted

#### Scenario: Session expired
- **WHEN** the session expires and the same user signs in again
- **THEN** the lock SHALL remain enabled with the same PIN and timeout

### Requirement: Notifications and offline mode while locked
Push and local notifications SHALL keep being received while the lock is enabled. Tapping a notification while locked SHALL navigate to its target behind the lock screen, and the target SHALL become visible only after unlocking. Unlocking MUST NOT require network access.

#### Scenario: Notification tap while locked
- **WHEN** the app is locked and the user taps an investment maturity notification
- **THEN** the lock screen SHALL be shown and, after unlocking, Finanzas › Inversiones SHALL be visible

#### Scenario: Unlock without network
- **WHEN** the device is in airplane mode and the user enters the correct PIN
- **THEN** the app SHALL unlock and show the cached data
