## 1. Backend — Modelo, migración y configuración

- [x] 1.1 Agregar `age_confirmed_at: Mapped[Optional[datetime]]` (`DateTime(timezone=True)`, nullable) a `User` en `backend/app/modules/auth/models.py`, con comentario (declaración de 16+, se guarda la primera)
- [x] 1.2 Crear `backend/migrations/versions/0NN_age_confirmation.py` con `down_revision` = head vigente al implementar (hoy `018_investments`; revisar si un change hermano ya agregó otra): `add_column` en `upgrade`, `batch_alter_table` + `drop_column` en `downgrade`
- [x] 1.3 Verificar `alembic heads` = un solo head, y `upgrade head` / `downgrade -1` / `upgrade head` en SQLite
- [x] 1.4 Subir `CURRENT_TERMS_VERSION` a `"1.1"` en `backend/app/config.py`, `backend/.env.example`, `.env.prod.example` y el default de `docker-compose.prod.yml` (`${CURRENT_TERMS_VERSION:-1.1}`)

## 2. Backend — Endpoints

- [x] 2.1 `backend/app/modules/auth/api_routes.py`: `RegisterRequest.confirm_age: bool` sin default + validator ("Tenés que confirmar que tenés 16 años o más"); `api_register` setea `age_confirmed_at`
- [x] 2.2 `AcceptTermsRequest.confirm_age: bool` sin default + mismo validator; `api_accept_terms` setea `age_confirmed_at` solo si es null, después del chequeo de versión (409)
- [x] 2.3 Agregar `age_confirmed: bool` a `UserOut` y `AuthResponse` y completarlo en todas las construcciones (login, register, me, patch me, accept-terms, verify-email) — idealmente con un helper `_user_out(user)` para no repetir campos
- [x] 2.4 Confirmar que el callback de Google sigue creando la cuenta con `terms_accepted_version` y `age_confirmed_at` en null (sin cambios de lógica)
- [x] 2.5 Registro HTML legacy apagado: `backend/app/modules/auth/routes.py` — `GET` y `POST /auth/register` responden 303 a `{PUBLIC_BASE_URL}/register` sin crear usuarios; borrar `backend/app/templates/auth/register.html`; login/logout legacy intactos

## 3. Backend — Tests

- [x] 3.1 `backend/tests/test_terms.py`: register con `confirm_age=false` → 422 y el usuario no existe; sin el campo → 422; con `true` → 201, `age_confirmed=true`, `age_confirmed_at` no nulo en la DB y versión 1.1
- [x] 3.2 accept-terms: sin `confirm_age` / `false` → 422 sin tocar versión ni fecha; con `true` → 200 y `age_confirmed=true`; versión vieja + `true` → 409 y `age_confirmed_at` sigue null; segunda aceptación (monkeypatch a una versión nueva) no pisa `age_confirmed_at` y sí actualiza `terms_accepted_at`
- [x] 3.3 Usuario existente (fixture creada directo en DB) → `GET /me` con `age_confirmed=false`; usuario con `terms_accepted_version="1.0"` queda distinto de la vigente 1.1
- [x] 3.4 `backend/tests/test_google_login.py`: alta nueva por Google → `me` con `terms_accepted_version=null` y `age_confirmed=false`; luego accept-terms con `confirm_age=true` → `age_confirmed=true`; cuenta existente con edad confirmada que entra con Google la conserva
- [x] 3.5 `backend/tests/test_auth.py` / `test_html_routes.py` (legacy): `GET` y `POST /auth/register` redirigen 303 a la SPA `/register` y no crean usuario; quitar los tests legacy de registro que ya no aplican
- [x] 3.6 Actualizar todos los payloads de `/auth/api/register` en tests (`test_auth_api.py`, `test_email_verification.py`, `test_refresh_tokens.py`, `test_tenant_isolation.py`, `test_investments.py`, `test_google_login.py`, y los que aparezcan con `grep accept_terms`) para mandar `confirm_age: true`
- [x] 3.7 `test_account.py`: el export de cuenta incluye `age_confirmed_at` en la fila del usuario
- [x] 3.8 Correr `cd backend && python -m pytest -q` completo sin regresiones (incluye la guarda de rutas públicas y `OWNED_TABLES`, que no cambian)

## 4. Web (`frontend/`)

- [x] 4.1 `src/types/auth.ts`: `age_confirmed: boolean` en `AuthUser`; `src/api/authApi.ts`: `register(..., acceptTerms)` manda `confirm_age` con el mismo valor de la casilla y `acceptTerms(version)` manda `{version, confirm_age: true}`; mantener el modo mock si cubre auth
- [x] 4.2 `src/store/authStore.ts`: guardar `age_confirmed` de register/login/me/accept-terms
- [x] 4.3 `src/components/ProtectedRoute.tsx`: gate si versión distinta **o** `age_confirmed === false`
- [x] 4.4 `src/pages/Auth/RegisterPage.tsx`: casilla única "Tengo 16 años o más y acepto los Términos y Condiciones y la Política de Privacidad." con links, ayuda de menores de 18 debajo, mensaje Zod "Tenés que confirmar tu edad y aceptar los Términos para continuar"
- [x] 4.5 `src/pages/Legal/AcceptTermsPage.tsx`: misma casilla y ayuda; título "Antes de empezar" si `terms_accepted_version` es null, "Actualizamos nuestros Términos" si no
- [x] 4.6 `src/pages/Legal/TermsPage.tsx`: versión 1.1, fecha nueva y la frase de declaración en la sección 2 (igual que `legal/terminos-y-condiciones.md`)
- [x] 4.7 Tests: `ProtectedRoute.test.tsx` (gate con versión vigente pero `age_confirmed=false`; sin gate con ambos OK), `authStore.test.ts` (accept-terms manda `confirm_age: true`), test nuevo de `RegisterPage` (no envía sin tildar, muestra el error, el payload lleva `confirm_age: true`) y de `AcceptTermsPage` (botón deshabilitado hasta tildar; texto con "16 años")
- [x] 4.8 `npx vitest run --maxWorkers=2`, `npm run build` y lint sin errores (el repo web no tiene script de lint: `npx tsc -b --noEmit` limpio)

## 5. Mobile (`C:\Proyectos\vida-personal-mobile`)

- [x] 5.1 [mobile] `src/types/index.ts`: `age_confirmed?: boolean` en `User` (opcional por perfiles cacheados viejos)
- [x] 5.2 [mobile] `src/api/endpoints.ts`: register manda `confirm_age`; `acceptTerms(version)` manda `{version, confirm_age: true}`
- [x] 5.3 [mobile] `src/store/authStore.ts`: guardar `age_confirmed` en register/login/me/accept-terms y en el perfil cacheado
- [x] 5.4 [mobile] `src/navigation/RootNavigator.tsx`: gate si versión distinta de `CURRENT_TERMS_VERSION` **o** `user.age_confirmed === false` (estricto), manteniendo la excepción de sesión offline
- [x] 5.5 [mobile] `src/screens/RegisterScreen.tsx`: casilla única con el texto de design D1, ayuda de menores de 18 y mensaje de error; sin textos de compra
- [x] 5.6 [mobile] `src/screens/AcceptTermsScreen.tsx`: casilla "Tengo 16 años o más y acepto los Términos y Condiciones, la Política de Privacidad y la Política de Reembolsos.", ayuda, título según caso (D5)
- [x] 5.7 [mobile] `src/lib/legalText.ts`: `CURRENT_TERMS_VERSION = '1.1'` y la frase de declaración en la sección 2 de `TERMS_TEXT`
- [x] 5.8 [mobile] `npx tsc --noEmit` sin errores (el repo mobile no tiene runner de tests)

## 6. Texto legal

- [x] 6.1 `legal/terminos-y-condiciones.md`: Versión 1.1, "Última actualización" = fecha del deploy, sección 2 con "Al crear tu cuenta o aceptar estos Términos declarás que tenés al menos 16 años y, si sos menor de 18, que contás con el consentimiento de tu madre, padre o tutor legal."
- [x] 6.2 Comparar los tres espejos (md, `TermsPage.tsx`, `legalText.ts`): misma frase, versión y fecha

## 7. Verificación contra backend real (no mock)

- [x] 7.1 Levantar backend real (no `VITE_MOCK_ENABLED`) y web: registrar con email sin tildar (no envía) y tildando (entra directo, sin gate)
- [x] 7.2 Con un usuario existente que aceptó 1.0 (o creado antes de la migración): al entrar ve el gate, acepta y queda en 1.1 con `age_confirmed=true`
- [x] 7.3 Alta con Google (si está configurado en el entorno): ve "Antes de empezar" con la casilla de edad y entra tras aceptar
- [x] 7.4 `curl` directo a `/auth/api/register` y `/auth/api/accept-terms` sin `confirm_age` → 422
- [ ] 7.5 [mobile] Build/Expo contra el backend real: registro y gate con la casilla nueva; usuario aceptado en web no ve el gate en mobile (pendiente: no se levantó Expo/emulador; `tsc` limpio y contrato verificado con curl/web contra el backend real)
- [ ] 7.6 Postgres: correr la migración en Postgres (PGlite vía npm como antes, o el contenedor de `docker-compose`) y un register + accept-terms contra esa base (hecho: upgrade/downgrade/upgrade de la migración en PGlite; pendiente: register + accept-terms contra esa base)
- [x] 7.7 Confirmar que `docker compose -f docker-compose.prod.yml config` resuelve `CURRENT_TERMS_VERSION=1.1`
