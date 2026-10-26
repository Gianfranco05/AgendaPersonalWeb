## Why

Los Términos y Condiciones (sección 2) y la Política de Privacidad fijan una edad mínima de **16 años** (y consentimiento de madre, padre o tutor para menores de 18), pero hoy nadie la confirma: el checkbox del registro y el gate de aceptación solo dicen "Leí y acepto los Términos…". No queda constancia de que la persona declaró tener la edad mínima, y el alta con Google ni siquiera pasa por un formulario propio. Hace falta pedir esa declaración de forma explícita, exigirla en el backend (no solo en el cliente) y guardar cuándo se hizo.

## What Changes

- **Una sola casilla con la declaración de edad incluida**, en es-AR: "Tengo 16 años o más y acepto los Términos y Condiciones y la Política de Privacidad." (mobile, en el gate, conserva también la Política de Reembolsos que ya menciona). Debajo, una línea de ayuda: "Si tenés menos de 18, necesitás el consentimiento de tu madre, padre o tutor." Se usa en:
  - Registro con email/contraseña: web `RegisterPage.tsx` y mobile `RegisterScreen.tsx`.
  - Gate de aceptación de términos: web `AcceptTermsPage.tsx` y mobile `AcceptTermsScreen.tsx` (lo ven las cuentas nuevas creadas con Google, las cuentas existentes y cualquier suba de versión).
  - Formulario HTML legacy `GET/POST /auth/register` (sigue expuesto en prod vía nginx `/auth/`), que hoy crea cuentas sin aceptar términos.
- **Backend exige la confirmación**: `POST /auth/api/register` y `POST /auth/api/accept-terms` reciben un campo nuevo obligatorio `confirm_age: true`; sin él responden 422 y no crean la cuenta ni registran la aceptación. **BREAKING** para clientes viejos que no lo manden (web se despliega junto con el backend; las builds mobile viejas quedan forzadas a actualizar, igual que ya pasa con la suba de versión de términos).
- **Persistencia**: columna nueva `users.age_confirmed_at` (timestamp UTC, nullable) con migración Alembic. Se setea al registrarse y en la primera aceptación de términos que la incluya; no se pisa en aceptaciones posteriores.
- **El cliente sabe si falta**: `UserOut` y `AuthResponse` exponen `age_confirmed: bool`. El gate (web `ProtectedRoute`, mobile `RootNavigator`) se muestra si la versión aceptada no es la vigente **o** si `age_confirmed` es `false`.
- **Usuarios existentes**: se les pide en la próxima entrada (el gate los atrapa por `age_confirmed = false`). Además se sube `CURRENT_TERMS_VERSION` a **1.1** porque el texto legal cambia (ver abajo), lo que coincide con el mismo gate.
- **Texto legal**: la sección 2 de los Términos agrega que al crear la cuenta o aceptar los Términos la persona declara tener 16 años o más y, si es menor de 18, contar con el consentimiento de su madre, padre o tutor. Se actualiza en los tres espejos: `legal/terminos-y-condiciones.md`, `frontend/src/pages/Legal/TermsPage.tsx` y mobile `src/lib/legalText.ts` (con fecha y versión 1.1).
- Tests de backend (rechazo sin confirmación, persistencia, flujo Google, usuarios existentes, legacy HTML), web y mobile.

### Fuera de alcance

- Pedir fecha de nacimiento o verificar la edad con documentos: es una declaración jurada de la persona, no una verificación.
- Flujo de consentimiento parental verificable (firma, mail al tutor).
- Bloquear del lado del servidor el resto de la API a quien no aceptó términos/edad: hoy el gate de términos es solo de cliente y se mantiene así (el registro y la aceptación sí se exigen en el server).
- Historial de aceptaciones por versión (tabla aparte): se sigue el modelo actual de columnas en `users`.

## Capabilities

### New Capabilities
- `minimum-age-confirmation`: declaración de edad mínima (16+) obligatoria en el registro (API JSON, formulario legacy y alta con Google vía gate), en la aceptación de términos, su persistencia con fecha, su exposición al cliente y el gate de web y mobile.

### Modified Capabilities
<!-- Ninguna: la aceptación de términos existente no tiene spec en openspec/specs/ (real-api-auth solo cubre login/logout/me). -->

## Impact

- **Backend**: `backend/app/modules/auth/models.py` (columna), `api_routes.py` (`RegisterRequest`, `AcceptTermsRequest`, `UserOut`, `AuthResponse`, callback de Google sin cambios de lógica), `routes.py` + `templates/auth/register.html` (legacy), `backend/app/config.py`, `backend/.env.example`, `.env.prod.example` y `docker-compose.prod.yml` (default `${CURRENT_TERMS_VERSION:-1.0}` hay que subirlo a 1.1 o el bump no llega a prod), migración nueva `backend/migrations/versions/0NN_age_confirmation.py`. Export de cuenta: si exporta el perfil del usuario, sumar `age_confirmed_at`.
- **Web**: `RegisterPage.tsx`, `AcceptTermsPage.tsx`, `ProtectedRoute.tsx`, `api/authApi.ts`, `store/authStore.ts`, `types/auth.ts`, `TermsPage.tsx`, mock de auth.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): `RegisterScreen.tsx`, `AcceptTermsScreen.tsx`, `RootNavigator.tsx`, `src/api/endpoints.ts`, `src/store/authStore.ts`, `src/types/index.ts`, `src/lib/legalText.ts`.
- **Legal**: `legal/terminos-y-condiciones.md` (versión 1.1).
- Sin APIs externas ni dependencias nuevas.
