## 1. Backend — Preferencia del tutorial

- [ ] 1.1 Agregar `onboarding_version_seen: Mapped[int]` (`Integer`, `default=0`, `server_default="0"`, NOT NULL) a `UserPreference` en `backend/app/modules/ajustes/models.py`
- [ ] 1.2 Crear la migración `backend/migrations/versions/0NN_onboarding_seen.py` con `down_revision` = head real al implementar (hoy `018_investments`; revisar `alembic heads` por migraciones de changes hermanos): `add_column` con `server_default`, `downgrade` con `batch_alter_table` para SQLite
- [ ] 1.3 `backend/app/api/v1/settings.py`: `onboarding_version_seen` en `SettingsResponse` y `_to_response`; en `SettingsUpdate` `Optional[int] = Field(None, ge=0, le=1000)`; en `update_settings` ignorar null explícito y guardar `max(actual, nuevo)` (design D12)
- [ ] 1.4 Verificar que el export de cuenta (`backend/app/modules/cuenta/service.py`, `user_preferences` ya está en `OWNED_TABLES`) incluya la columna nueva sin cambios extra

## 2. Web — Tutorial (`frontend/`)

- [ ] 2.1 `src/types`: `onboarding_version_seen?: number` en `Settings`; `src/api/endpoints.ts`: mapearlo en `mapSettings` y en `mockSettingsState` con valor `CURRENT_ONBOARDING_VERSION` (visto) para no romper tests/demos; `updateSettings` mock aplica `max`
- [ ] 2.2 `src/components/Onboarding/steps.ts`: `CURRENT_ONBOARDING_VERSION = 1`, los 4 pasos de web (design D13) y la función pura `needsOnboarding(settings, localSeen)` (settings `undefined` o sin el campo → `false`)
- [ ] 2.3 `src/components/Onboarding/onboardingStorage.ts`: leer/escribir `cancen_onboarding_seen:{userId}` en `localStorage` con `try/catch`
- [ ] 2.4 `src/components/Onboarding/OnboardingModal.tsx`: `createPortal` a `document.body`, `role="dialog"`, `aria-modal`, foco atrapado, `Esc` = Saltar, "Paso N de 4" con `aria-live`, botones Saltar/Anterior/Siguiente/Empezar, íconos `lucide-react`, modo oscuro
- [ ] 2.5 Estado de apertura (modo `welcome`/`replay`) en un store Zustand chico `src/store/onboardingStore.ts`; montar el modal en `src/components/Layout.tsx` y abrirlo en modo bienvenida cuando `needsOnboarding` sea `true`
- [ ] 2.6 Al terminar/saltar en modo bienvenida: escribir el respaldo local y llamar `saveSettings({ onboarding_version_seen: CURRENT_ONBOARDING_VERSION })` ignorando errores; en modo repaso no escribir nada
- [ ] 2.7 `src/pages/Settings/SettingsPage.tsx`: botón "Ver tutorial" que abre el modal en modo repaso

## 3. Mobile — Infraestructura de tests (`C:\Proyectos\vida-personal-mobile`)

- [ ] 3.1 [mobile] `npx expo install jest-expo jest @types/jest -- --dev` (versiones de SDK 57, Jest 29), `"jest": { "preset": "jest-expo" }` y script `"test": "jest"` en `package.json`
- [ ] 3.2 [mobile] Mocks compartidos en `jest.setup.ts` (o `__mocks__/`): `expo-secure-store` y `@react-native-async-storage/async-storage` en memoria, `expo-crypto` sobre `node:crypto`, `expo-local-authentication` y `expo-screen-capture` controlables
- [ ] 3.3 [mobile] Comprobar que `npx tsc --noEmit` sigue en verde con los tipos de Jest (excluir o tipar `**/__tests__/**`)

## 4. Mobile — Lógica del bloqueo (`C:\Proyectos\vida-personal-mobile`)

- [ ] 4.1 [mobile] `npx expo install expo-local-authentication expo-screen-capture`; plugin `["expo-local-authentication", { "faceIDPermission": "..." }]` en `app.json`
- [ ] 4.2 [mobile] `src/lib/appLock/policy.ts` (sin imports de RN): `LOCK_TIMEOUTS`, `shouldLockOnResume`, tabla de esperas, `registerFailure`, `registerSuccess`, `remainingWaitMs`, `attemptsLeftBeforeSignOut`, `MAX_FAILURES = 10`, reloj hacia atrás (design D5/D6)
- [ ] 4.3 [mobile] `src/lib/appLock/pin.ts`: `validateNewPin` (4–6 dígitos, sin todos iguales ni secuencias), `hashPin` (`s256$sal$hex`, sal de 16 bytes) y `verifyPin` con comparación en tiempo constante
- [ ] 4.4 [mobile] `src/lib/appLock/storage.ts`: leer/escribir/borrar `cancen_app_lock_v1` y `cancen_app_lock_attempts` en SecureStore (iOS `WHEN_UNLOCKED_THIS_DEVICE_ONLY`), parseo defensivo (JSON inválido → sin config), no-op en web
- [ ] 4.5 [mobile] `src/lib/appLock/biometrics.ts`: `isBiometricAvailable()` (hardware + enrolada + `BIOMETRIC_STRONG` en Android) y `authenticate()` con las opciones de design D7; tolerar el módulo nativo ausente (build viejo/Expo Go) devolviendo "no disponible"
- [ ] 4.6 [mobile] `src/lib/appLock/screenGuard.ts`: aplicar/quitar `preventScreenCaptureAsync('app-lock')` y `enableAppSwitcherProtectionAsync(0.8)`/`disable…` según `enabled && hideInRecents`; tolerar módulo ausente
- [ ] 4.7 [mobile] `src/store/appLockStore.ts` (Zustand) con reloj inyectable: `hydrate()`, `bindUser(userId)`, `locked`, `onAppStateChange`, `allowExternalTrip()`, `authInProgress`, `unlockWithPin`, `unlockWithBiometrics`, `enable`, `disable`, `changePin`, `setTimeout`, `setBiometrics`, `setHideInRecents`, `forgotPin`, `clearConfig`, `isEnabled()`
- [ ] 4.8 [mobile] `App.tsx`: sumar `appLock.hydrate()` al `Promise.all` del caché para que el primer frame ya salga bloqueado
- [ ] 4.9 [mobile] `src/store/authStore.ts`: `logout` y `changeServer` (con cambio efectivo) llaman `clearConfig()`; `login`, `loginWithGoogle` y `checkAuth` llaman `bindUser(user.id)` (login → desbloqueado; otro usuario → borrar config; offline sin perfil → bloquear igual); `setOnUnauthorized` conserva la config
- [ ] 4.10 [mobile] `allowExternalTrip()` antes de `Linking.openURL` en `src/screens/GoogleCalendarScreen.tsx`, `Sharing.shareAsync` en `src/lib/exportFile.ts` y el pedido de permiso de notificaciones en `src/lib/notifications.ts`

## 5. Mobile — UI del bloqueo (`C:\Proyectos\vida-personal-mobile`)

- [ ] 5.1 [mobile] `src/components/PinPad.tsx`: teclado numérico propio, indicador de dígitos según `pinLength`, borrar, deshabilitado con cuenta regresiva, etiquetas de accesibilidad
- [ ] 5.2 [mobile] `src/screens/LockScreen.tsx`: "Can_cen está bloqueada" sin datos del usuario, prompt biométrico automático una vez (solo con `AppState` activo) y botón "Usar huella", mensajes de error/espera/intentos restantes/aviso de pendientes (design D6/D7), "Olvidé mi PIN" con confirmación y conteo de `getPendingCount()` (D9), botón atrás de Android no desbloquea
- [ ] 5.3 [mobile] `src/components/AppLockGate.tsx`: listener de `AppState`, `Modal` opaco (`animationType="none"`, `statusBarTranslucent`, `navigationBarTranslucent`) con `LockScreen` cuando `isAuthenticated && enabled && locked`; montarlo en `src/navigation/RootNavigator.tsx` junto al `NavigationContainer` y ocultar el árbol de abajo a la accesibilidad mientras está bloqueado
- [ ] 5.4 [mobile] `src/components/BottomSheet.tsx`: `visible={visible && !locked}` para que la hoja se oculte (sin perder estado) durante el bloqueo
- [ ] 5.5 [mobile] `src/screens/AppLockSettingsScreen.tsx`: switch principal (crear PIN dos veces / desactivar con PIN o biometría), "Usar huella o rostro" (solo si hay biometría fuerte; activar exige autenticar), `FilterChips` Inmediato/1/5/15 min, switch "Ocultar en apps recientes" con la aclaración de capturas, "Cambiar PIN", texto del modelo de amenaza (D1)
- [ ] 5.6 [mobile] Registrar `AppLockSettings` en `SettingsStack` (`src/navigation/TabNavigator.tsx`, `SettingsStackParamList`) y sumar la sección "Seguridad" en `src/screens/SettingsScreen.tsx` (oculta en web) con hint Activado/Desactivado

## 6. Mobile — Tutorial (`C:\Proyectos\vida-personal-mobile`)

- [ ] 6.1 [mobile] `src/types`: `onboarding_version_seen?: number` en `AppSettings`
- [ ] 6.2 [mobile] `src/lib/onboarding.ts`: `CURRENT_ONBOARDING_VERSION = 1`, los 4 pasos de mobile (design D13, sin textos de compra), `needsOnboarding(settings, localSeen)`, respaldo `cancen_onboarding_seen:{userId}` en AsyncStorage y `markOnboardingSeen(userId)` (local primero, después `updateSettings` encolado)
- [ ] 6.3 [mobile] `src/screens/OnboardingScreen.tsx` con `mode: 'welcome' | 'replay'`: `ScrollView` horizontal `pagingEnabled`, Saltar/Anterior/Siguiente/Empezar, "Paso N de 4", íconos `MaterialCommunityIcons`, safe-area, tokens claro/oscuro, botón atrás de Android = paso anterior (en repaso desde el paso 1 cierra)
- [ ] 6.4 [mobile] `src/navigation/RootNavigator.tsx`: leer `useSettings()` y el respaldo local; gate `needsToAcceptTerms ? AcceptTerms : needsOnboarding ? Onboarding(welcome) : Tabs`
- [ ] 6.5 [mobile] Ruta `Onboarding` en `SettingsStack` (modo repaso) y sección "Ayuda" › "Ver tutorial" en `src/screens/SettingsScreen.tsx`

## 7. Tests

- [ ] 7.1 Backend `backend/tests/test_ajustes.py`: default 0 en GET; PUT 1 → GET 1; `max` (2 no baja a 1); null ignorado; −1 y 5000 → 422; aislamiento entre dos usuarios; export de cuenta incluye `onboarding_version_seen`
- [ ] 7.2 Backend: correr la suite completa `cd backend && python -m pytest -q` (guardias de `OWNED_TABLES` y rutas públicas en verde)
- [ ] 7.3 Web vitest `src/components/Onboarding/__tests__/`: `needsOnboarding` (undefined, sin campo, 0, 1, respaldo local); el modal aparece con `onboarding_version_seen = 0` y no con 1; Saltar y Empezar llaman `updateSettings` con la versión y escriben `localStorage`; Anterior/Siguiente; Esc; modo repaso desde Configuración no escribe; `localStorage` que tira excepción no rompe
- [ ] 7.4 Web: `npx vitest run --maxWorkers=2` completo en verde (Layout y Dashboard existentes no ven el modal gracias al mock "visto")
- [ ] 7.5 [mobile] `src/lib/appLock/__tests__/policy.test.ts`: `shouldLockOnResume` para Inmediato/1/5/15 min con bordes (59 999 ms vs 60 000 ms, 4:59 vs 5:00), `backgroundAt` null, reloj hacia atrás; secuencia de esperas fallo 1→10; `mustSignOut` en el 10; reset por éxito; `remainingWaitMs` con reloj hacia atrás; intentos restantes
- [ ] 7.6 [mobile] `src/lib/appLock/__tests__/pin.test.ts`: válidos/inválidos (`0000`, `111111`, `1234`, `4321`, `012345`, `987654`, `12a4`, `123`, `1234567`); hash con prefijo `s256$` que no contiene el PIN; dos hashes del mismo PIN difieren y ambos verifican; PIN incorrecto no verifica
- [ ] 7.7 [mobile] `src/store/__tests__/appLockStore.test.ts`: arranque en frío bloqueado; volver antes/después del tiempo; `allowExternalTrip` (< 5 min no bloquea, ≥ 5 min sí); `authInProgress` ignora cambios de `AppState`; fallos persistidos sobreviven a re-`hydrate`; 10.º fallo y `forgotPin` llaman `logout` y borran config y contador; `bindUser` con otro usuario borra la config; login deja desbloqueado; biometría exitosa resetea el contador; módulos nativos ausentes no rompen
- [ ] 7.8 [mobile] `src/lib/__tests__/onboarding.test.ts`: `needsOnboarding` (settings desconocidos, sin campo, server 0 + local 1, server 1, versión 2); `markOnboardingSeen` escribe local antes de llamar `updateSettings`; guarda de contenido: ningún paso contiene `/compr|precio|pago|tienda|\bpro\b|\$/i`
- [ ] 7.9 [mobile] `npm test` y `npx tsc --noEmit` en verde

## 8. Verificación contra backend real (no mock)

- [ ] 8.1 Aplicar la migración en Postgres (PGlite vía npm o docker compose): `alembic upgrade head`, `downgrade -1`, `upgrade head`; `GET/PUT /api/v1/settings` con `onboarding_version_seen` contra Postgres
- [ ] 8.2 Web con `VITE_MOCK_ENABLED=false`: registrar un usuario nuevo → aparece el tutorial; Saltar; recargar y entrar desde otro navegador → no aparece; "Ver tutorial" desde Configuración funciona y no cambia el valor en la base
- [ ] 8.3 Mobile (build EAS `lan`, necesario por los módulos nativos) contra el backend real: con el usuario del 8.2 no aparece el tutorial; con otro usuario nuevo aparece, se salta en modo avión y no reaparece al reabrir; al volver la red el PUT de la cola llega al server
- [ ] 8.4 Mobile en dispositivo Android real: activar bloqueo con PIN y huella; arranque en frío bloqueado; tiempos Inmediato y 1 min; recientes en blanco (también con un `BottomSheet` abierto) y capturas bloqueadas; apagar "Ocultar en apps recientes" y comprobar que vuelven las capturas
- [ ] 8.5 Mobile: 6 fallos → espera de 30 s; matar la app durante la espera y reabrir → la espera sigue; huella durante la espera desbloquea; exportar datos con "Inmediato" no re-bloquea al volver del selector de compartir; conectar Google Calendar no re-bloquea
- [ ] 8.6 Mobile: "Olvidé mi PIN" en modo avión con un cambio pendiente → aviso con el conteo, vuelve al Login, el bloqueo queda desactivado al reingresar
- [ ] 8.7 Mobile: con la app bloqueada, tocar una push de vencimiento de inversión → aparece el bloqueo y al desbloquear se ve Finanzas › Inversiones
- [ ] 8.8 Mobile: TalkBack con la app bloqueada solo recorre la pantalla de bloqueo
- [ ] 8.9 Correr `openspec validate app-bloqueo-y-bienvenida --strict` y marcar las tareas completadas
