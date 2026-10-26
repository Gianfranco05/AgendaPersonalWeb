## Context

- **Aceptación de términos hoy** (`backend/app/modules/auth/`): `users.terms_accepted_version` + `terms_accepted_at` (migración `015_terms_acceptance`). `POST /auth/api/register` exige `accept_terms: bool` sin default (ausente = 422) y un validator que rechaza `false`; graba la versión vigente (`settings.CURRENT_TERMS_VERSION`, hoy `"1.0"`). `POST /auth/api/accept-terms` recibe `{version}` y devuelve 409 si no es la vigente (el cliente manda la versión que está mostrando). `UserOut`/`AuthResponse` exponen `terms_accepted_version` y `current_terms_version`.
- **Gate en los clientes** (no hay bloqueo en el server): web `ProtectedRoute` redirige a `/accept-terms` si `terms_accepted_version !== current_terms_version` (versión que viene del server); `AcceptTermsPage` manda `current_terms_version` del server. Mobile `RootNavigator` compara contra `CURRENT_TERMS_VERSION` **embebida** en `src/lib/legalText.ts` y salta el gate en sesión offline (`isOfflineSession`); `AcceptTermsScreen` manda la versión embebida.
- **Alta con Google** (`GET /auth/api/google/callback`): crea `User` sin `terms_accepted_version` → el cliente muestra el gate. Es el único lugar donde una cuenta de Google puede declarar la edad: no hay formulario propio, y el botón de Google existe tanto en Login como en Register.
- **Registro HTML legacy** (`backend/app/modules/auth/routes.py::register` + `templates/auth/register.html`): sigue montado y nginx de prod proxya `/auth/` al backend, así que `POST /auth/register` crea cuentas sin términos (y ahora sin edad). Tiene tests en `backend/tests/test_auth.py` y `test_html_routes.py`. **Decisión del usuario: se apaga** (ver D7).
- **Configuración**: `docker-compose.prod.yml` pasa `CURRENT_TERMS_VERSION=${CURRENT_TERMS_VERSION:-1.0}`: el default del compose pisa el de `config.py`, así que una suba de versión tiene que tocarse ahí también (más `backend/.env.example` y `.env.prod.example`).
- **Export de cuenta** (`backend/app/modules/cuenta/service.py`) serializa la fila completa de `users` con `_serialize_row`: una columna nueva entra sola.
- **Texto legal** en tres espejos a mano: `legal/terminos-y-condiciones.md` (Versión 1.0, 24/09/2026), `frontend/src/pages/Legal/TermsPage.tsx`, mobile `src/lib/legalText.ts`. Todos ya dicen "al menos 16 años" y lo del consentimiento para menores de 18; la Política de Privacidad también.

## Goals / Non-Goals

**Goals:**
- Que ninguna cuenta nueva (email/contraseña, Google) pueda usar la app sin haber declarado tener 16+.
- Exigirlo en el server en los dos endpoints que registran consentimiento, con constancia de fecha.
- Pedírselo a las cuentas existentes en la próxima entrada, sin migración de datos manual.
- UI simple: una casilla, texto claro en es-AR.

**Non-Goals:**
- Fecha de nacimiento, verificación de identidad o consentimiento parental verificable.
- Bloqueo server-side del resto de la API para quien no aceptó (el gate sigue siendo de cliente, como hoy).
- Tabla de historial de aceptaciones.

## Decisions

### D1. Una sola casilla en la UI, dos campos en la API

La casilla dice: **"Tengo 16 años o más y acepto los Términos y Condiciones y la Política de Privacidad."** (con links; el gate mobile mantiene "…y la Política de Reembolsos"). Debajo, texto de ayuda chico: "Si tenés menos de 18, necesitás el consentimiento de tu madre, padre o tutor." Error de validación del cliente: "Tenés que confirmar tu edad y aceptar los Términos para continuar".

Al tildarla el cliente manda `accept_terms: true` y `confirm_age: true` (en el gate, `version` + `confirm_age: true`).

- *Por qué una casilla*: la edad mínima es una condición de los propios Términos, la declaración queda explícita en el texto que se tilda, y dos casillas suman fricción sin agregar evidencia distinta. Es el patrón habitual ("Tengo X años o más y acepto…").
- *Por qué un campo aparte en la API*: deja en el contrato y en los tests que la edad se declaró, distingue el error ("confirmá tu edad") del de términos, y hace que un cliente viejo que no conoce la declaración falle en vez de registrar una edad que nunca mostró.
- *Alternativa descartada*: reinterpretar `accept_terms: true` como "acepta y declara edad". Sin cambio de contrato, pero un cliente viejo (que muestra la casilla vieja sin la edad) quedaría registrando una declaración que la persona nunca vio.

### D2. Persistencia: `users.age_confirmed_at`

Columna `DateTime(timezone=True)`, nullable, en `users` (mismo modelo que `terms_accepted_at`). Nada de booleano aparte: `age_confirmed = age_confirmed_at IS NOT NULL`.

- Se setea en `register` y en `accept-terms` **solo si está en null**: conserva la primera declaración (la edad solo crece; la fecha relevante es la del alta o la primera vez que se pidió). La fecha de cada aceptación de versión ya queda en `terms_accepted_at`.
- *Alternativa*: guardarla "junto" a la aceptación pisándola cada vez. Descartada: perdería la fecha de la declaración original sin ganar nada.
- *Alternativa*: tabla de historial `terms_acceptances` (versión, fecha, edad). Más fiel como evidencia, pero cambia el modelo actual y no se pidió; queda como mejora futura.
- La API expone solo `age_confirmed: bool` en `UserOut` y `AuthResponse` (no hace falta mandar la fecha a los clientes). El export de cuenta la incluye solo por serializar la fila.

### D3. Validación en el backend

- `RegisterRequest.confirm_age: bool` **sin default** (igual que `accept_terms`, por el gotcha documentado ahí: Pydantic v2 no valida defaults) + `field_validator` que rechaza `false` con "Tenés que confirmar que tenés 16 años o más".
- `AcceptTermsRequest.confirm_age: bool` sin default, mismo validator. Se exige **siempre**, aunque el usuario ya tenga `age_confirmed_at`: la casilla del gate siempre incluye la edad, así el contrato es uno solo.
- Orden en `accept-terms`: 422 de validación (FastAPI, antes del handler) → 409 por versión vieja → grabar. Si falla cualquiera, no se toca ninguna columna.
- `register` valida antes de buscar el email / crear el usuario / mandar el mail de verificación (lo garantiza el schema).

### D4. Google: la edad se declara en el gate

El callback no cambia: la cuenta nueva queda con `terms_accepted_version = null` y `age_confirmed_at = null`, y el gate (que ya se le muestra) ahora incluye la edad. No se exige la casilla antes del botón "Registrarse con Google": el mismo botón está en Login, así que el gate es el único punto que cubre todos los caminos. Una cuenta existente que entra con Google conserva lo que tenga; si le falta la edad, el gate la atrapa por D5.

### D5. Gate: versión distinta **o** edad sin confirmar

- Web `ProtectedRoute`: `user.terms_accepted_version !== user.current_terms_version || user.age_confirmed === false`.
- Mobile `RootNavigator`: misma condición contra la versión embebida; se compara `age_confirmed === false` (estricto) para que un perfil cacheado viejo sin el campo no dispare el gate offline; online el perfil se refresca y trae el campo.
- `AcceptTermsPage`/`AcceptTermsScreen`: título según el caso — "Antes de empezar" si `terms_accepted_version` es null (cuenta nueva de Google), "Actualizamos nuestros Términos" si no — y la casilla de D1.
- Los stores (`acceptTerms`) mandan `confirm_age: true` y guardan `age_confirmed` del response; `register` manda `confirm_age` y guarda `age_confirmed`.

### D6. Usuarios existentes y versión 1.1

Se sube `CURRENT_TERMS_VERSION` a **1.1** porque el texto de la sección 2 cambia (agrega la declaración: "Al crear tu cuenta o aceptar estos Términos declarás que tenés al menos 16 años y, si sos menor de 18, que contás con el consentimiento de tu madre, padre o tutor legal."). Fecha de actualización = la del deploy.

- Efecto: todos los usuarios (incluidos los que ya aceptaron 1.0) pasan por el gate una vez, aceptan 1.1 y declaran edad. Es el mismo resultado que daría solo la condición `age_confirmed === false` de D5; D5 queda igual como red (por ejemplo, cuentas legacy o una versión futura que no toque la edad).
- Hay que subirlo en: `backend/app/config.py`, `docker-compose.prod.yml` (`${CURRENT_TERMS_VERSION:-1.1}`), `backend/.env.example`, `.env.prod.example`, mobile `legalText.ts`, y el encabezado de los tres textos.
- *Alternativa*: no subir versión y no tocar el texto (D5 alcanza para pedir la edad). Más liviano, pero la declaración no quedaría escrita en los Términos que se aceptan. Ver Preguntas abiertas.

### D7. Registro HTML legacy: se apaga y redirige a la SPA

**Decisión del usuario** (reemplaza la propuesta original de endurecerlo con una casilla). `GET /auth/register` y `POST /auth/register` ya no muestran el formulario ni crean usuarios: ambos responden **303** a `{PUBLIC_BASE_URL}/register` (la misma base pública que usan los links de los mails; en prod nginx sirve SPA y backend en el mismo origen y en dev apunta a Vite). La ruta POST se conserva solo como redirección (sin leer el formulario, sin crear nada) para que un cliente viejo no reciba un 405 confuso. Se borra `templates/auth/register.html`; el link "Registrate aqui" de `login.html` sigue apuntando a `/auth/register` y por la redirección cae en la SPA. Login y logout HTML legacy no cambian. Los tests legacy de registro se reemplazan por tests de la redirección; no cambia nginx ni la guarda de rutas públicas (las rutas HTML no son `/api/v1`).

### D8. Migración

Archivo nuevo `backend/migrations/versions/0NN_age_confirmation.py`: `op.add_column("users", sa.Column("age_confirmed_at", sa.DateTime(timezone=True), nullable=True))`; `downgrade` con `batch_alter_table` para SQLite. Sin backfill: los existentes quedan en null y los atrapa el gate. El número y `down_revision` se fijan al implementar según el head de ese momento (hoy `018_investments`; varios changes hermanos también agregan migraciones).

## Risks / Trade-offs

- [Builds mobile viejas no mandan `confirm_age`: registro y aceptación dan 422; con la versión 1.1 el gate además da 409 "Actualizá la app"] → la app mobile todavía no está publicada para el público; publicar backend y build mobile juntos. Web se despliega con el backend.
- [La declaración es autodeclarada; un menor puede mentir] → es lo que piden los Términos (declaración, no verificación); la Política de Privacidad ya prevé eliminar cuentas de menores de 16 detectadas.
- [Todos los usuarios ven el gate una vez tras el deploy] → aceptable y esperado; el título "Actualizamos nuestros Términos" lo explica.
- [Tres espejos del texto legal se desincronizan] → tarea explícita de diff entre los tres y test web/mobile que busca "16 años" en la casilla.
- [Default `1.0` en `docker-compose.prod.yml` deja prod en 1.0 aunque `config.py` diga 1.1 → la web pediría 1.0 y mobile 1.1 (409 eterno)] → subirlo en el compose y verificarlo en la verificación real.
- [Conflicto de numeración de migraciones con changes hermanos] → número y `down_revision` al implementar; `alembic heads` debe dar uno solo.

## Migration Plan

1. Deploy backend (migración `0NN_age_confirmation` por `alembic upgrade head`) + web en el mismo despliegue, con `CURRENT_TERMS_VERSION=1.1`.
2. Build EAS mobile con `legalText.ts` en 1.1 y la casilla nueva.
3. Rollback: `alembic downgrade` al head anterior borra la columna (se pierde la fecha de las declaraciones hechas: aceptable) y revertir el deploy; con versión 1.0 de nuevo, quienes aceptaron 1.1 verían el gate otra vez (comparación por igualdad), lo cual es inofensivo.

## Dependencias

- Ninguna funcional con los changes hermanos. Solo comparte `backend/migrations/versions/` (numeración) con los que agreguen migraciones, y `RootNavigator.tsx` mobile con `app-bloqueo-y-bienvenida` (bloqueo de app / bienvenida): el gate de términos tiene que seguir evaluándose antes de la bienvenida post-registro; si ambos tocan el mismo bloque, el segundo en implementarse hace el merge.

## Decisiones del usuario (ex Open Questions)

1. Una sola casilla: "Tengo 16 años o más y acepto los Términos y Condiciones y la Política de Privacidad." (+ ayuda de menores de 18). Confirmado.
2. Subir a la versión 1.1 de los Términos con la declaración escrita; todos re-aceptan una vez. Confirmado.
3. Registro HTML legacy: **se apaga y redirige a `/register` de la SPA** (no se endurece). Ver D7.
4. Sin usuarios reales en builds mobile viejas: backend y build mobile salen juntos.
5. Sin historial por versión: solo `age_confirmed_at` de la primera declaración.
