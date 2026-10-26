## Context

- **Mobile** (`C:\Proyectos\vida-personal-mobile`, Expo SDK 57, RN 0.86, rama `feat/google-billing-modulos`):
  - `App.tsx` lee el caché SWR persistido (`loadCache`) y el override de server antes del primer render, y recién entonces monta `RootNavigator`.
  - `src/navigation/RootNavigator.tsx` decide entre `AuthNavigator`, `AcceptTermsScreen` (gate de términos, se salta con `isOfflineSession`) y `TabNavigator` (6 tabs con stacks; `SettingsStack` tiene `SettingsHome`, `Account`, `Sessions`, `Modules`, `Legal`, …).
  - `src/store/authStore.ts` (Zustand): `checkAuth` con sesión offline (`isOfflineSession` + perfil cacheado en SecureStore `vida_personal_user`), `logout` (desregistra push, limpia tokens, caché, cola offline y perfil), `changeServer`, `setOnUnauthorized`.
  - `src/lib/secureStorage.ts` envuelve `expo-secure-store` (en web cae a `localStorage`, solo para debug). `expo-crypto` ya está instalado. `src/store/themeStore.ts` usa AsyncStorage.
  - Escrituras offline: `queued(...)` en `src/api/endpoints.ts` (`updateSettings` ya es `queued('Cambio en ajustes')`); `getPendingCount()` en `src/lib/mutationQueue.ts`.
  - Push: `src/lib/notifications.ts` + `src/hooks/useNotificationTaps.ts` (montado en `TabNavigator`, navega a Finanzas › Inversiones o Ajustes › Recordatorios). Las push de vencimiento incluyen el monto en el cuerpo.
  - UI del sistema que saca la app a segundo plano: `WebBrowser.openAuthSessionAsync` (login con Google, antes de tener sesión), `Linking.openURL` en `GoogleCalendarScreen`, `Sharing.shareAsync` en `src/lib/exportFile.ts`, el diálogo de permiso de notificaciones y el propio prompt biométrico.
  - `BottomSheet` es un `Modal` de RN (ventana propia en Android). `app.json` ya tiene `android.allowBackup: false`.
  - **No hay runner de tests** en el repo mobile (ni Jest ni Vitest); solo `npx tsc --noEmit`.
- **Web** (`frontend/`): `App.tsx` con `ProtectedRoute` (gate de términos) → `Layout` (sidebar + `Outlet`). `useSettings()` (SWR key `settings`) y `saveSettings()`; `src/api/endpoints.ts` con `mockSettingsState`. El Dashboard web no tiene botón "+". Gotcha conocido: los modales dentro de un ancestro con `transform` quedan atrapados → usar portal a `document.body`.
- **Backend**: `user_preferences` (una fila por usuario, se crea en el primer `GET /settings`), `GET/PUT /api/v1/settings` en `backend/app/api/v1/settings.py` con `exclude_unset` y nulls ignorados para columnas NOT NULL. `user_preferences` ya está en `OWNED_TABLES` (export/borrado). Head de Alembic: `018_investments`.
- **Plantillas**: las base (`habits`, `tasks`, `notes`, `finance`, `fitness_nutrition`, `calendar`) están siempre activas y no se pueden desactivar (`ModulesService.set_enabled` da 400); las pagas se compran solo en la web.

## Goals / Non-Goals

**Goals:**
- Bloqueo opcional de la app mobile con biometría fuerte y PIN propio, que tape el contenido también en apps recientes, con tiempo de re-bloqueo configurable, límite de intentos persistente, salida por "Olvidé mi PIN" y funcionamiento offline.
- Lógica del bloqueo en funciones puras testeables (temporizador, intentos, validación de PIN), con Jest agregado al repo mobile.
- Tutorial de 4 pasos en web y mobile, una sola vez por usuario entre dispositivos, revisable desde Ajustes, sin textos de compra en mobile.

**Non-Goals:**
- Cifrado de datos en reposo (caché SWR en AsyncStorage, cola offline).
- Bloqueo en la web.
- Ocultar contenido de las push en la pantalla de bloqueo del sistema.
- Preguntas de bienvenida (ver Preguntas abiertas).
- Sincronizar la configuración del bloqueo entre dispositivos (es por dispositivo, a propósito).

## Decisions

### D1. Modelo de amenaza del bloqueo

Protege contra **acceso casual**: alguien que agarra el teléfono desbloqueado, lo mira en apps recientes o abre la app. **No** protege contra alguien con root/ADB que lea el almacenamiento: el caché SWR vive en AsyncStorage sin cifrar. Esto se documenta en el texto de Ajustes ("Pide tu huella o un PIN para abrir la app en este dispositivo") sin prometer cifrado. Las decisiones de hash (D3) y de intentos (D6) se dimensionan para este modelo.

### D2. Dependencias nativas nuevas

- `expo-local-authentication` (`npx expo install`; versión de SDK 57). Plugin en `app.json`: `["expo-local-authentication", { "faceIDPermission": "Permití que $(PRODUCT_NAME) use Face ID para desbloquear la app." }]`. Agrega `USE_BIOMETRIC` en Android. Face ID no funciona en Expo Go (requiere development build).
- `expo-screen-capture`: `preventScreenCaptureAsync(key)` / `allowScreenCaptureAsync(key)`; en Android aplica `FLAG_SECURE` (vista previa en recientes en blanco **y** capturas/grabación bloqueadas); en iOS `enableAppSwitcherProtectionAsync(0.8)` desenfoca el selector de apps. No pide permisos (no usamos el listener de capturas).
- Ambas requieren **un build nuevo de EAS** (código nativo): no llegan por actualización OTA. Sin plugins propios.

*Alternativa para recientes*: `Activity.setRecentsScreenshotEnabled(false)` (Android 13+) oculta la vista previa sin bloquear capturas, pero Expo no lo expone y requiere un config plugin/módulo nativo propio. Descartada en esta etapa (Pregunta abierta 4). *Alternativa*: poner `FLAG_SECURE` solo al pasar a segundo plano. Descartada: Android toma el snapshot de recientes en la transición y el evento `AppState` llega tarde; no es confiable.

### D3. PIN propio y su almacenamiento

- Formato: 4 a 6 dígitos (`^\d{4,6}$`). Se rechazan todos iguales (`0000`, `111111`) y secuencias ascendentes/descendentes (`1234`, `4321`, `012345`, `987654`). Se pide dos veces al crearlo o cambiarlo.
- Hash: `s256$<sal base64>$<hex>` con sal de 16 bytes (`Crypto.getRandomBytes(16)`) y `SHA-256(sal ‖ ":" ‖ pin)` (`Crypto.digestStringAsync`). Se compara en tiempo constante (recorrido completo de la cadena). El prefijo versiona el formato para migrar a un KDF más caro si hace falta.
- *Por qué no PBKDF2/Argon2*: `expo-crypto` no los trae, sumar una lib nativa/JS de KDF no se justifica con D1 (el hash vive en el Keystore/Keychain vía SecureStore; quien puede leerlo ya puede leer el caché sin cifrar) y miles de iteraciones de `digestStringAsync` darían segundos de espera en celulares económicos. El freno real es el límite de intentos (D6).
- Se guarda también `pinLength` para que el teclado envíe solo al completar los dígitos.

### D4. Configuración y estado persistido (por dispositivo)

Dos claves en SecureStore (en iOS con `keychainAccessible: WHEN_UNLOCKED_THIS_DEVICE_ONLY`, para que no viaje en backups a otro equipo):

```ts
// cancen_app_lock_v1
type AppLockConfig = {
  v: 1;
  userId: string;          // dueño de la configuración
  enabled: boolean;
  pinHash: string;         // s256$...
  pinLength: 4 | 5 | 6;
  biometrics: boolean;
  timeoutMs: 0 | 60_000 | 300_000 | 900_000;  // Inmediato / 1 / 5 / 15 min (default 60_000)
  hideInRecents: boolean;  // default true
};
// cancen_app_lock_attempts
type AttemptsState = { failed: number; lockedUntil: number | null; lastFailureAt: number | null };
```

- **Atada al usuario**: si la sesión resuelta (`checkAuth`/login) es de otro `userId`, la config se borra. Si la sesión es offline sin perfil cacheado (id desconocido) y hay config, **se bloquea igual** (falla cerrada).
- **Se borra** en: `logout` explícito, "Olvidé mi PIN", el 10.º fallo, `changeServer` con cambio efectivo. **Se conserva** cuando la sesión vence (401 en `setOnUnauthorized`/`checkAuth`): la persona vuelve a loguearse y su bloqueo sigue activo.
- Al loguearse (password o Google) con una config existente del mismo usuario, el estado arranca **desbloqueado** (acaba de autenticarse).
- Web (`Platform.OS === 'web'`): el módulo es no-op y la sección no se muestra.

### D5. Cuándo se bloquea (política pura)

`src/lib/appLock/policy.ts` sin imports de RN:

```ts
export function shouldLockOnResume(backgroundAt: number | null, now: number, timeoutMs: number): boolean {
  if (backgroundAt === null) return false;
  const elapsed = now - backgroundAt;
  if (elapsed < 0) return true;           // reloj atrasado a mano: se bloquea
  return elapsed >= timeoutMs;            // timeoutMs = 0 → siempre
}
```

- **Arranque en frío**: con `enabled` se bloquea siempre (Android puede matar el proceso en segundo plano: eso cuenta como arranque en frío). La config se lee en `App.tsx` dentro del mismo `Promise.all` que el caché, así el primer frame de `TabNavigator` ya sale tapado.
- **Segundo plano**: el listener de `AppState` guarda `backgroundAt = Date.now()` al pasar a `'background'` (solo en memoria) y al volver a `'active'` evalúa `shouldLockOnResume`. `'inactive'` (iOS: centro de control, llamadas) no inicia el temporizador; el desenfoque del selector lo cubre.
- **Flujos que salen de la app a propósito**: `appLockStore.allowExternalTrip()` marca el próximo viaje a segundo plano como esperado: al volver, si pasaron menos de 5 minutos, no se bloquea aunque el tiempo sea "Inmediato". Se usa en `Linking.openURL` de Google Calendar, `Sharing.shareAsync` de exportar y el pedido de permiso de notificaciones. Mientras corre el prompt biométrico (`authInProgress`) se ignoran los cambios de `AppState` que él mismo provoca (Face ID pasa por `'inactive'`; algunos OEM Android reportan `'background'`).

### D6. Intentos de PIN y espera progresiva

Funciones puras en `policy.ts`:

| Fallo n.º | Efecto |
|---|---|
| 1–5 | sin espera |
| 6 | espera 30 s |
| 7 | 1 min |
| 8 | 5 min |
| 9 | 15 min |
| 10 | cierre de sesión local (como "Olvidé mi PIN", sin pedir confirmación) |

- `registerFailure(state, now)` devuelve el estado nuevo y `{ waitMs, mustSignOut }`; `remainingWaitMs(state, now)`; `registerSuccess()` resetea. El estado se persiste **antes** de mostrar el error, así matar la app no reinicia el contador.
- Si `now < lastFailureAt` (reloj atrasado), la espera se recalcula completa desde `now`.
- Desde el fallo 6 se muestra "Te quedan N intentos antes de cerrar la sesión". Durante la espera el teclado queda deshabilitado con cuenta regresiva, pero la **biometría sigue disponible**. Un desbloqueo biométrico exitoso también resetea el contador.
- Al 10.º fallo: `logout()` (limpia tokens, caché, cola, perfil) + borrar config y contador. Si hay cambios offline pendientes se pierden: por eso el aviso con la cantidad pendiente aparece desde el fallo 8.

### D7. Biometría

- Disponible si `hasHardwareAsync() && isEnrolledAsync()` y, en Android, `getEnrolledLevelAsync() === SecurityLevel.BIOMETRIC_STRONG` (huella o rostro 3D, Clase 3; el desbloqueo facial 2D de muchos Android se puede engañar con una foto).
- `authenticateAsync({ promptMessage: 'Desbloqueá Can_cen', cancelLabel: 'Usar PIN', disableDeviceFallback: true, biometricsSecurityLevel: 'strong', requireConfirmation: false })`. `disableDeviceFallback: true`: el PIN/patrón del teléfono no abre la app; la alternativa es el PIN de la app.
- La pantalla de bloqueo lanza el prompt sola una vez al aparecer (solo con `AppState === 'active'`) y ofrece el botón "Usar huella" para reintentar. Errores `user_cancel`/`app_cancel`/`system_cancel` → queda el teclado sin mensaje; `lockout` → mensaje "Biometría bloqueada por el sistema, usá tu PIN"; `not_enrolled`/`not_available` → se desactiva el toggle en la config y se avisa una vez.
- Activar la biometría en Ajustes exige un `authenticateAsync` exitoso en ese momento.
- *Limitación*: si alguien registra una huella nueva en el teléfono, esa huella también abre la app (`expo-local-authentication` no detecta cambios de enrolamiento). *Alternativa*: guardar un centinela con `SecureStore` `requireAuthentication: true`, que el sistema invalida al cambiar la biometría (`getItemAsync` → `null`); leerlo dispara el prompt. Queda como Pregunta abierta 3 por complejidad y diferencias entre fabricantes.

### D8. Pantalla de bloqueo y capas

- `src/components/AppLockGate.tsx` se monta en `RootNavigator` junto al `NavigationContainer` y renderiza `src/screens/LockScreen.tsx` dentro de un `Modal` de RN (`animationType="none"`, `statusBarTranslucent`, `navigationBarTranslucent`, fondo opaco del tema) cuando `isAuthenticated && config.enabled && locked`. El árbol de navegación **no se desmonta** (se conserva dónde estaba y los formularios a medio llenar); el contenido de abajo recibe `importantForAccessibility="no-hide-descendants"` / `accessibilityElementsHidden` para que TalkBack/VoiceOver no lo lean.
- **Por qué `Modal`**: los `BottomSheet`, `Alert` y pickers son ventanas propias en Android; un `View` absoluto quedaría debajo de ellos. Además, `BottomSheet` lee `appLockStore.locked` y usa `visible={visible && !locked}`: en iOS no se pueden presentar dos modales a la vez, y así la hoja se oculta (sin perder su estado) mientras está el bloqueo y vuelve al desbloquear.
- Contenido: ícono de la app, "Can_cen está bloqueada", indicador de dígitos, teclado numérico propio (no el teclado del sistema: sin sugerencias ni autocompletado), botón de biometría, "Olvidé mi PIN", mensajes de error/espera. Nada de datos del usuario (ni nombre ni montos). Botón atrás de Android en la pantalla de bloqueo: manda la app a segundo plano (no desbloquea).
- `FLAG_SECURE`/desenfoque (`hideInRecents`) se aplica mientras el bloqueo esté activado, no solo cuando está bloqueada (la vista previa de recientes se toma con la app desbloqueada).

### D9. "Olvidé mi PIN"

Confirmación con `Alert`: "Vas a cerrar la sesión en este dispositivo y tendrás que volver a ingresar con tu email o Google. El bloqueo se desactiva." Si `getPendingCount() > 0`: "Tenés N cambios sin sincronizar que se van a perder." Al confirmar: `authStore.logout()` (funciona offline: los llamados al server están en `try/catch`) + borrar config y contador. Vuelve al Login.

### D10. Notificaciones y modo offline

- Las push y notificaciones locales se reciben igual; la app bloqueada no cambia el handler. El texto lo muestra el sistema según su propia configuración de pantalla de bloqueo (fuera de alcance ocultar montos: Pregunta abierta 5).
- Tocar una notificación con la app bloqueada: `useNotificationTaps` navega como siempre **detrás** del `Modal` de bloqueo; al desbloquear se ve la pantalla de destino. En arranque en frío pasa lo mismo porque `TabNavigator` monta debajo del bloqueo.
- Offline: todo es local (SecureStore + funciones puras + biometría del sistema). No hay ningún llamado al server para desbloquear.

### D11. Ajustes › Seguridad (mobile)

- `SettingsScreen` suma `SectionCard` "Seguridad" (solo si `Platform.OS !== 'web'`) con `LinkRow` "Bloqueo de la app" (hint "Activado"/"Desactivado") → `AppLockSettings` en `SettingsStack`.
- `src/screens/AppLockSettingsScreen.tsx`: switch "Pedir huella o PIN al abrir" (activar → crear PIN → ofrecer biometría si hay; desactivar → pide PIN o biometría), "Usar huella o rostro" (oculto si no hay biometría fuerte), "Bloquear después de" con `FilterChips` (Inmediato / 1 min / 5 min / 15 min), switch "Ocultar en apps recientes" con la aclaración "En Android también bloquea las capturas de pantalla", "Cambiar PIN" (pide el actual). Texto de modelo de amenaza (D1).
- `authStore.logout` y `changeServer` llaman a `appLock.clearConfig()`; `login`/`loginWithGoogle`/`checkAuth` llaman a `appLock.bindUser(user.id)` (D4).

### D12. Tutorial: persistencia

- Columna `user_preferences.onboarding_version_seen INTEGER NOT NULL server_default 0`. `SettingsResponse.onboarding_version_seen: int`; `SettingsUpdate.onboarding_version_seen: Optional[int] = Field(None, ge=0, le=1000)`; `null` explícito se ignora (igual que `include_investments_in_balance`); el server guarda `max(actual, nuevo)` para que un cliente viejo o un PUT tardío de la cola offline no lo haga bajar.
- Clientes: constante `CURRENT_ONBOARDING_VERSION = 1` (web `src/components/Onboarding/steps.ts`, mobile `src/lib/onboarding.ts`).
- Regla pura `needsOnboarding(settings, localSeen)`: `false` si `settings` es `undefined` (todavía no se sabe: no se muestra a ciegas) o si `settings` no trae `onboarding_version_seen` (backend viejo); si no, `max(settings.onboarding_version_seen, localSeen) < CURRENT_ONBOARDING_VERSION`.
- Respaldo local por usuario: mobile AsyncStorage `cancen_onboarding_seen:{userId}`, web `localStorage` `cancen_onboarding_seen:{userId}` (en `try/catch`). Al terminar o saltar: se escribe el local **primero** y después `updateSettings({ onboarding_version_seen: CURRENT })` (en mobile ya es `queued`, así que offline queda en la cola; en web un error se ignora y lo cubre el local, se reintenta en la próxima carga si el server sigue en 0).
- "Ver tutorial" desde Ajustes abre los mismos pasos en modo repaso: no escribe nada.
- Usuarios existentes: con el default 0 todos lo ven una vez al actualizar (con "Saltar"). Ver Pregunta abierta 6.
- *Alternativa*: solo local. Descartada: el usuario pidió que no se repita entre dispositivos (web + celular).
- *Alternativa*: campo en `users`/`/auth/me`. Descartada: es una preferencia y `user_preferences` ya viaja por `/settings` con SWR y caché offline en ambos clientes.

### D13. Tutorial: contenido y UI

4 pasos (título + 1–2 líneas + ícono grande; sin assets nuevos: `MaterialCommunityIcons` en mobile, `lucide-react` en web):

1. **Tu Inicio** — mobile: "Tu día de un vistazo. Con el botón + creás tareas, hábitos, movimientos y más en segundos."; web: "Tu día de un vistazo en el Dashboard. Desde el menú lateral entrás a cada sección."
2. **Hábitos** — "Marcá tus hábitos cada día, mirá tus rachas y sumá metas para lo que querés lograr."
3. **Finanzas e Inversiones** — "Registrá ingresos y gastos, armá presupuestos y seguí tus inversiones y tu patrimonio." Mobile agrega: "Podés proteger la app con huella o PIN en Ajustes › Seguridad."
4. **Tareas, notas y tu espacio** — "Organizá tareas, notas y eventos." Web: "En Módulos activás plantillas para estudio, viajes, proyectos y más." Mobile: "En Ajustes › Personalizá tu espacio elegís qué ver en Inicio." (sin "comprar", "precio", "tienda", "pago", "$", "Pro" ni "desbloquear plantillas").

Controles: "Saltar" (pasos 1–3), "Anterior" (pasos 2–4), "Siguiente" / "Empezar" (último), indicador "Paso N de 4" (`accessibilityLabel`/`aria-live`). Mobile: además deslizar horizontal (`ScrollView` `pagingEnabled`); botón atrás de Android = paso anterior (en el primero no hace nada en modo bienvenida, cierra en modo repaso).

- **Mobile**: `src/screens/OnboardingScreen.tsx` con prop/param `mode: 'welcome' | 'replay'`. En modo bienvenida es un gate de `RootNavigator` (después de términos, antes de `TabNavigator`): `needsToAcceptTerms ? AcceptTerms : needsOnboarding ? Onboarding : Tabs`. `useSettings()` se lee en `RootNavigator` (está dentro de `SWRConfig`). Si los ajustes llegan tarde (sin caché) y resulta pendiente, el gate aparece en ese momento (pasa a lo sumo una vez, típicamente al primer segundo después de registrarse). En modo repaso es la ruta `Onboarding` del `SettingsStack` ("Ver tutorial" en la sección "Ayuda" de Ajustes). El `Modal` de bloqueo queda por encima del gate.
- **Web**: `src/components/Onboarding/OnboardingModal.tsx` montado en `Layout` vía `createPortal(document.body)`, `role="dialog"`, `aria-modal`, foco atrapado, `Esc` = Saltar. "Ver tutorial" en `SettingsPage` lo abre en modo repaso (estado en un store Zustand chico o contexto). No se muestra en rutas públicas ni en `/accept-terms` (está dentro de `Layout`).
- **Mock web**: `mockSettingsState.onboarding_version_seen = CURRENT_ONBOARDING_VERSION` (visto) para no romper tests y demos existentes; los tests del modal lo fijan en 0 explícitamente.

### D14. Tests

- **Mobile**: se agrega Jest con `jest-expo` (`npx expo install jest-expo jest @types/jest -- --dev`, `"jest": { "preset": "jest-expo" }`, script `"test": "jest"`), versión alineada a SDK 57 (Jest 29; SDK 58 exigirá Jest 30). Tests de funciones puras (`policy`, `needsOnboarding`, validación de PIN), del hash con `expo-crypto` mockeado sobre `node:crypto`, y del `appLockStore` con reloj inyectado y SecureStore/AsyncStorage mockeados. Sin tests de componentes en esta etapa (no hay `@testing-library/react-native` instalado; se puede sumar después).
- **Web**: vitest + Testing Library para el modal y la integración con Ajustes.
- **Backend**: `test_ajustes.py`.

## Dependencias

- **`widgets-android`**: un widget en la pantalla de inicio muestra datos **sin pasar por el bloqueo**. Ese change debería leer `cancen_app_lock_v1.enabled` (o un flag espejo no sensible en almacenamiento compartido) y, con el bloqueo activo, mostrar el widget sin montos ("Abrí Can_cen para ver tu resumen"). Este change expone `appLock.isEnabled()` para eso; no implementa nada de widgets.
- **`habitos-recordatorios-inteligentes`**: si agrega acciones en la notificación (p. ej. "Marcar hecho"), esas acciones escriben sin desbloquear. Es aceptable (no muestran datos), pero ese change debería documentarlo; con bloqueo activo no deberían abrir pantallas con datos sin pasar por el bloqueo (el tap normal ya cae detrás del bloqueo, D10).
- **`registro-edad-minima`**: el gate del tutorial va **después** de cualquier gate de registro/edad/términos. Si ese change agrega un gate nuevo en `RootNavigator`/`ProtectedRoute`, el orden es: términos → (edad) → tutorial → app.
- **`finanzas-*` y `buscador-global`**: sin dependencia. El buscador, si abre resultados desde una notificación o atajo, queda detrás del bloqueo como cualquier pantalla.
- **Migraciones**: otros changes hermanos también agregan migraciones sobre `018_investments`. El número y `down_revision` de `0NN_onboarding_seen` se fijan al implementar contra el head real (un solo head: `alembic heads`).

## Risks / Trade-offs

- [`FLAG_SECURE` bloquea las capturas de pantalla en toda la app] → sub-ajuste "Ocultar en apps recientes" apagable con la aclaración explícita; default encendido porque el pedido es proteger datos de plata.
- [Los `Modal` de RN en Android son ventanas `Dialog` y podrían no heredar `FLAG_SECURE` de la Activity] → verificar en dispositivo real con un `BottomSheet` abierto → recientes; con D8 la hoja se oculta al bloquear, pero la vista previa se toma desbloqueada: si no hereda, documentarlo y evaluar el plugin de D2.
- [iOS: un solo modal presentado a la vez] → `BottomSheet` se oculta con `locked` (D8); un `Alert` abierto en iOS en el momento del bloqueo podría quedar encima: riesgo menor, el `Alert` no muestra datos sensibles.
- [El prompt biométrico o UIs del sistema disparan cambios de `AppState` y re-bloquean en bucle] → `authInProgress` y `allowExternalTrip()` (D5); test del store para el caso.
- [Cerrar sesión al 10.º fallo pierde la cola offline] → aviso con el conteo desde el fallo 8; 9 fallos previos con esperas acumuladas de ~21 minutos hacen improbable llegar sin querer.
- [Reloj del dispositivo manipulado para saltear esperas] → si el reloj va hacia atrás se reinicia la espera completa; adelantar el reloj sí acorta la espera (sin reloj monotónico persistente en Expo): aceptable para D1.
- [Huella nueva registrada en el teléfono también desbloquea] → limitación documentada; alternativa en Pregunta abierta 3.
- [Requiere build nuevo de EAS] → el bloqueo se entrega con el próximo build; mientras tanto la sección no aparece si el módulo nativo no está (`LocalAuthentication` ausente → `hasHardwareAsync` falla → solo PIN; `expo-screen-capture` ausente → sin `FLAG_SECURE`). El código debe chequear disponibilidad y no romper en builds viejos ni en Expo Go.
- [Tutorial que aparece de golpe si `/settings` tarda] → solo pasa sin caché (primer ingreso); se acepta antes que mostrarlo a ciegas a quien ya lo vio.
- [Usuarios existentes ven el tutorial al actualizar] → tiene "Saltar"; Pregunta abierta 6.

## Migration Plan

1. Backend: migración `0NN_onboarding_seen` (`add_column` con `server_default='0'`, `downgrade` con `batch_alter_table` para SQLite). Deploy normal (`alembic upgrade head`). Rollback: `downgrade` a la revisión anterior. Si la respuesta de `/settings` no trae el campo (backend viejo o rollback), `needsOnboarding` lo trata como **visto** (no muestra el tutorial), para no mostrarlo en cada apertura sin poder guardarlo.
2. Web: deploy junto con el backend.
3. Mobile: build nuevo de EAS (perfil `lan` para probar, luego `preview`/`production`) por las dependencias nativas. Un backend nuevo con mobile viejo no cambia nada (campo aditivo).

## Open Questions

1. **Preguntas de bienvenida** (moneda principal ARS/USD, qué querés organizar). *Recomendación*: no incluirlas ahora. `user_preferences.currency` existe pero **ninguna pantalla lo usa** (los montos van en la moneda de cada movimiento/activo), así que preguntarlo no cambiaría nada visible; y las plantillas base están siempre activas y no se pueden desactivar, así que "qué querés organizar → activar módulos base" no tiene efecto. Si se quiere, un change posterior podría usar la respuesta para ordenar los widgets de Inicio y, cuando `currency` se use de verdad (p. ej. con `finanzas-datos-mercado`), sumar la pregunta de moneda como paso 5 opcional.
2. **Tiempo de re-bloqueo por defecto**. *Recomendación*: 1 minuto (equilibrio entre seguridad y no pedir huella por cada ida y vuelta corta); opciones Inmediato/1/5/15.
3. **Detectar huellas nuevas** con el centinela de SecureStore `requireAuthentication`. *Recomendación*: no en esta etapa; reevaluar tras probar en 2–3 fabricantes.
4. **Ocultar recientes sin bloquear capturas** (config plugin propio con `setRecentsScreenshotEnabled(false)`, Android 13+). *Recomendación*: no por ahora; `FLAG_SECURE` con sub-ajuste alcanza.
5. **Montos en el texto de las push** (vencimientos de inversiones) visibles en la pantalla de bloqueo del sistema. *Recomendación*: change aparte con preferencia "Ocultar montos en notificaciones" del lado del server.
6. **Usuarios existentes**: ¿ven el tutorial una vez? *Recomendación*: sí (son pocos, antes del lanzamiento, y explica Inversiones, que es nuevo). Alternativa: backfill en la migración marcando `onboarding_version_seen = 1` a las filas existentes.
7. **Cierre de sesión al 10.º fallo**. *Recomendación*: sí; alternativa más blanda: espera de 1 h por cada fallo extra sin cerrar sesión.
8. **Biometría solo "fuerte" (Clase 3) en Android**. *Recomendación*: sí; deja afuera el desbloqueo facial 2D de gama baja, que se engaña con una foto.
