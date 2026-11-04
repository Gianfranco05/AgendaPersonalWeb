## Why

Can_cen guarda datos de plata (balance, cuentas, inversiones, patrimonio) y en el celular cualquiera que agarre el teléfono desbloqueado los ve con solo abrir la app; además, la vista previa de "apps recientes" de Android muestra la última pantalla. Por otro lado, quien se registra cae directo en Inicio sin saber qué hace el "+", dónde están Hábitos o Inversiones ni qué son las plantillas: no hay ninguna bienvenida.

## What Changes

- **Bloqueo de la app con huella/rostro o PIN (solo Android/iOS, opcional, apagado por defecto)**, que se activa en Ajustes › Seguridad:
  - Activarlo exige crear un **PIN propio de la app** (4 a 6 dígitos, se pide dos veces, se rechazan los triviales como `0000` o `1234`). El PIN se guarda **solo como hash con sal** en `expo-secure-store` (Keystore/Keychain del dispositivo), nunca en texto.
  - Opción "Usar huella o rostro" con `expo-local-authentication` (dependencia nueva) si el dispositivo tiene biometría fuerte registrada; el PIN de la app queda siempre como alternativa. No se usa el PIN/patrón del teléfono como alternativa (quien sabe desbloquear el teléfono no tiene por qué entrar a la app).
  - Bloquea **al abrir la app en frío** y **al volver de segundo plano** pasado el tiempo elegido: Inmediato, 1, 5 o 15 minutos (por defecto 1 minuto).
  - **Pantalla de bloqueo** opaca encima de toda la navegación (el contenido no se desmonta ni se ve, tampoco para el lector de pantalla). **Apps recientes**: con el bloqueo activo, por defecto se oculta el contenido en la vista previa con `expo-screen-capture` (dependencia nueva; en Android es `FLAG_SECURE`, que además bloquea capturas de pantalla; en iOS, desenfoque del selector). Se puede apagar ese sub-ajuste.
  - **Intentos de PIN** con espera progresiva persistida (cerrar la app no la reinicia): 5 intentos libres, después 30 s, 1 min, 5 min y 15 min; al 10.º fallo se cierra la sesión local.
  - **"Olvidé mi PIN"** → confirma, cierra la sesión (avisando si hay cambios offline sin sincronizar) y borra la configuración del bloqueo; se vuelve a entrar con email/contraseña o Google.
  - **Notificaciones**: se siguen recibiendo igual; tocar una con la app bloqueada abre la pantalla de destino *detrás* del bloqueo y se ve recién al desbloquear.
  - **Offline**: el bloqueo es 100 % local, funciona sin red.
  - **Web**: no aplica (documentado; la sesión web ya vence y se cierra desde "Dispositivos").
- **Tutorial de bienvenida (web y mobile)**: 4 pantallas cortas la primera vez que se entra (Inicio y el "+" / resumen; Hábitos; Finanzas e Inversiones; Tareas, Notas y Plantillas), con "Saltar", "Anterior"/"Siguiente" y "Empezar". En mobile sin ningún texto de compra, precio ni tienda.
  - Se muestra **una sola vez por usuario en todos sus dispositivos**: se guarda en el server (`user_preferences.onboarding_version_seen`) con respaldo local para que no reaparezca offline mientras el cambio espera en la cola.
  - Se puede volver a ver desde Ajustes ("Ver tutorial") en web y mobile.
  - Versionado (`CURRENT_ONBOARDING_VERSION`): si el tutorial cambia mucho, se puede volver a mostrar subiendo la versión.
- **Backend**: columna nueva `onboarding_version_seen` en `user_preferences` y campo aditivo en `GET/PUT /api/v1/settings`. Sin tablas nuevas.
- **Preguntas de bienvenida** (moneda principal, qué querés organizar): **no** entran en este change; se dejan como recomendación en Preguntas abiertas del design.

### Fuera de alcance

- Cifrar el caché offline (AsyncStorage) o la base local: el bloqueo es una traba de interfaz contra el acceso casual, no cifrado de datos en reposo (ver design, modelo de amenaza).
- Ocultar los montos del texto de las push en la pantalla de bloqueo del sistema.
- Bloqueo en la web (PIN o WebAuthn).
- Recuperar el PIN sin cerrar sesión, o sincronizar el PIN entre dispositivos (cada dispositivo tiene el suyo).
- Tours guiados con globos sobre la interfaz real (el tutorial son pantallas propias).

## Capabilities

### New Capabilities
- `app-lock`: bloqueo opcional de la app mobile con biometría y PIN propio: configuración, almacenamiento seguro del PIN, cuándo se bloquea (apertura y regreso de segundo plano con tiempo configurable), pantalla de bloqueo y apps recientes, límite de intentos con espera progresiva, "Olvidé mi PIN", notificaciones, modo offline y no-aplicación en web.
- `onboarding-tutorial`: tutorial de bienvenida en web y mobile: contenido y navegación, persistencia por usuario en el server (`onboarding_version_seen`) con respaldo local, modo offline, volver a verlo desde Ajustes y restricción de textos de compra en mobile.

### Modified Capabilities
<!-- Ninguna: `GET/PUT /api/v1/settings` no tiene spec vigente en openspec/specs/; el campo nuevo se especifica en `onboarding-tutorial`. -->

## Impact

- **Backend**: `backend/app/modules/ajustes/models.py` (`onboarding_version_seen`), `backend/app/api/v1/settings.py` (`SettingsResponse`/`SettingsUpdate`), migración nueva `backend/migrations/versions/0NN_onboarding_seen.py` (número según el head al implementar; hoy `018_investments`). Tests en `backend/tests/test_ajustes.py`.
- **Web** (`frontend/`): `src/components/Onboarding/` (modal de pasos), montaje en `src/components/Layout.tsx`, `src/pages/Settings/SettingsPage.tsx` ("Ver tutorial"), `src/types` y `src/api/endpoints.ts` (+ mock), `src/hooks/useSettings.ts`. Tests vitest.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): dependencias `expo-local-authentication` y `expo-screen-capture` (+ plugin con `faceIDPermission` en `app.json`; requiere build nuevo de EAS, no llega por OTA); `src/lib/appLock/*` (política pura, PIN, almacenamiento, biometría), `src/store/appLockStore.ts`, `src/components/AppLockGate.tsx`, `src/screens/LockScreen.tsx`, `src/screens/AppLockSettingsScreen.tsx`, `src/screens/OnboardingScreen.tsx`, `App.tsx`, `src/navigation/RootNavigator.tsx` y `TabNavigator.tsx`, `src/screens/SettingsScreen.tsx`, `src/store/authStore.ts` (logout limpia el bloqueo), `src/lib/googleAuth.ts` y `src/lib/exportFile.ts` (suspender el auto-bloqueo durante el navegador/compartir). Se agrega Jest con `jest-expo` (el repo mobile no tiene runner de tests hoy).
- **Infra**: sin variables de entorno nuevas ni APIs externas.
