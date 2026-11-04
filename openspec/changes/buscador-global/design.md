## Context

- **Datos buscables** (todas las tablas tienen `user_id` indexado y son 1 tenant = 1 usuario):

  | Tipo (`type`) | Módulo (`MODULE_REGISTRY`) | Tabla / entidad | Campo título | Campos de contenido | Fecha del resultado |
  |---|---|---|---|---|---|
  | `notes` | `notes` (base) | `notes` / `note` | `title` | `content`, nombres de `tags` (vía `note_tags` + `tags.user_id`) | `updated_at` |
  | `tasks` | `tasks` (base) | `tasks` / `task` | `title` | `description`, `area` | `due_date` ?? `updated_at` |
  | `transactions` | `finance` (base) | `transactions` / `transaction` (`is_deleted = false`) | `product_name` | `merchant_name`, `product_description`, `notes` | `transaction_date` (texto ISO, `IsoText`) |
  | `events` | `calendar` (base) | `events` / `event` | `title` | `description`, `location` | `start_datetime` |
  | `habits` | `habits` (base) | `goals` con `goal_type IN ('binary','metric')` / `habit` | `title` | `description` | `updated_at` |
  | `goals` | `habits` (base) | `goals` con `goal_type IN ('progress','savings')` / `goal` | `title` | `description` | `end_date` ?? `updated_at` |
  | `investments` | `finance` (base) | `investments` / `investment` | `name` | `ticker`, `institution`, `notes` | `maturity_date` ?? `updated_at` |
  | `study` | `study` (paga) | `subjects` / `subject`; `exams` / `exam` | `name`; `title` | `professor`; `notes` | `updated_at`; `exam_date` |
  | `library` | `library` (paga) | `books` / `book` | `title` | `author`, `notes` | `finished_date` ?? `started_date` ?? `updated_at` |
  | `media` | `media` (paga) | `media_items` / `media_item` | `title` | `notes` | `updated_at` |
  | `work` | `work` (paga) | `work_opportunities` / `opportunity` | `role` (título mostrado "Rol · Empresa") | `company`, `notes` | `applied_date` ?? `updated_at` |
  | `travel` | `travel` (paga) | `trips` / `trip`; `packing_items` / `packing_item` (padre `trip_id`) | `destination`; `name` | `notes`; — | `start_date` ?? `updated_at`; `updated_at` |
  | `vehicle` | `vehicle` (paga) | `vehicles` / `vehicle`; `maintenance_records` / `maintenance` (padre `vehicle_id`) | `name`; `notes` (título mostrado = tipo de registro + nombre del vehículo) | `brand`, `model`, `plate`; — | `updated_at`; `record_date` |
  | `projects` | `projects` (paga) | `projects` / `project`; `project_tasks` / `project_task` (padre `project_id`) | `name`; `title` | `description`; `notes` | `updated_at`; `due_date` ?? `updated_at` |

  Los nombres exactos de columnas se toman de `backend/app/modules/*/models.py` al implementar (las fechas `created_at`/`updated_at` existen en todas las tablas listadas).
- **Gate de plantillas**: `backend/app/core/entitlements.py::require_module` deja pasar si la plantilla es base o está comprada (`ModulePurchase`), y en dev sin cobro configurado (`not billing_enabled and not is_production`) deja pasar todo. El estado activo/inactivo vive en `EnabledModule` (`ModulesService.list_for_user` calcula `enabled`). `require_module` hoy **no** mira `enabled`.
- **Rate limit**: `backend/app/core/http_security.py::_build_rate_limiter` (Redis si hay `REDIS_URL`, memoria si no), con dependencias por IP (auth) o por `user_id` (billing).
- **Base de datos**: Postgres (asyncpg) en prod, SQLite en dev/tests (`create_all`). Head de Alembic `018_investments`. `lower()` de SQLite solo pasa a minúscula ASCII; en Postgres `lower()` depende del `LC_CTYPE` de la base (con collation `C` tampoco baja letras acentuadas).
- **Logs**: `RequestLoggingMiddleware` y las métricas Prometheus guardan solo `request.url.path` (sin query string); Sentry con `send_default_pii=False`. nginx usa el formato `combined` por defecto, que sí incluye `$request` con query string.
- **Clientes**: web con rutas por sección en `frontend/src/App.tsx` (`/notes`, `/tasks`, `/events`, `/habits`, `/goals`, `/finances` con pestañas internas por `useState`, `/study`, `/library`, `/media`, `/work`, `/travel`, `/vehicle`, `/projects`); mobile con stacks por tab en `src/navigation/TabNavigator.tsx`, `useCreateParam` para abrir el alta por param y el antecedente `Investments: { investmentId }` (abre una inversión desde la push).

## Goals / Non-Goals

**Goals:**
- Un endpoint único, rápido (p95 < 150 ms con miles de filas por usuario) y portable (mismo SQL en Postgres y SQLite).
- Insensible a mayúsculas y tildes en ambos motores sin depender de extensiones ni de la collation de la base.
- Imposible ver datos de otro usuario o de plantillas pagas no compradas/desactivadas.
- UX de búsqueda en vivo con teclado en web y una pantalla simple en mobile que abre el elemento encontrado.

**Non-Goals:**
- Relevancia sofisticada (BM25, stemming, tolerancia a errores de tipeo).
- Índices especiales o extensiones de Postgres en esta etapa.
- Buscar en fitness, nutrición, focus, recordatorios, presupuestos, categorías o cuentas.

## Decisions

### D1. Estrategia: `LIKE` sobre una expresión "fold" portable, sin extensiones ni migración

Cada consulta se acota primero por `user_id` (índice existente en todas las tablas), con lo que el universo por tabla es de cientos a pocos miles de filas: filtrar con `LIKE '%término%'` sobre eso es un recorrido de unas pocas miles de filas en memoria, del orden de milisegundos, y no necesita índice de texto. La insensibilidad a mayúsculas/tildes se logra con una expresión SQL **idéntica en ambos motores**:

```
fold(x) = replace(replace(... replace(lower(coalesce(x, '')), 'á', 'a') ..., 'Ñ', 'n')
```

con el mapeo `á→a é→e í→i ó→o ú→u ü→u ñ→n` y sus mayúsculas `Á É Í Ó Ú Ü Ñ` (14 `replace` anidados; las mayúsculas se mapean explícitamente porque `lower()` de SQLite y de Postgres con collation `C` no las bajan). Se implementa como helper `fold(col)` en `backend/app/modules/buscador/normalize.py` que arma la expresión con `func.replace`/`func.lower`, y una función Python `fold_text(s)` con **exactamente el mismo mapeo** (más `str.lower()` solo para ASCII y caracteres que no cambian de largo) para normalizar el término. El mapeo es de 1 carácter a 1 carácter, así que el texto plegado tiene el mismo largo que el original y los offsets de resaltado calculados sobre el plegado valen para el original (D6).

*Alternativas evaluadas:*
- **`ILIKE` + `pg_trgm` (GIN trigram)**: acelera `%x%` cuando hay que recorrer millones de filas de una tabla global; acá cada búsqueda ya queda acotada por `user_id` y el planner usa el índice btree de `user_id` antes que el trigram. `ILIKE` no resuelve tildes y no existe en SQLite (SQLAlchemy lo emula con `lower()`, que en SQLite no baja acentuadas): el comportamiento divergiría entre tests y prod. Necesita `CREATE EXTENSION pg_trgm` (extensión *trusted* desde PG 13: la puede crear el dueño de la base con privilegio `CREATE` sin ser superusuario; en hostings gestionados suele estar en una allowlist, pero hay que verificarlo en el proveedor elegido, que todavía no está definido).
- **Full-text (`tsvector` con config `spanish` + `unaccent`)**: aporta stemming, pero no encuentra prefijos ni fragmentos ("cafe" en "cafetería", tickers como "AAPL", patentes), requiere columnas generadas o índices por tabla (14 fuentes), `unaccent` es `STABLE` (no indexable sin un wrapper `IMMUTABLE` propio) y no tiene equivalente en SQLite: los tests no probarían el camino de prod. Demasiado costo para el volumen esperado.
- **`unaccent()` en Postgres + función Python registrada en SQLite** (`create_function` en el evento `connect`): dos implementaciones distintas = tests verdes con bugs de prod (lección de `bughunt-2026-10`: SQLite esconde bugs de PG). Descartada.
- **Columna `search_text` desnormalizada por tabla**: requiere migración en 14 tablas, mantenerla en cada escritura y backfill. Innecesario al volumen actual.

*Plan B documentado (no se implementa)*: si el p95 de `/search` supera 300 ms sostenido (métrica Prometheus existente por path), crear una migración que haga `CREATE EXTENSION IF NOT EXISTS pg_trgm` dentro de un bloque que verifique `pg_available_extensions` y capture `insufficient_privilege` (sin romper `alembic upgrade head` si el rol no puede), y agregue índices `GIN (fold(col) gin_trgm_ops)` solo en Postgres (`op.get_bind().dialect.name == 'postgresql'`). Como `fold` usa solo `lower` y `replace` (ambas `IMMUTABLE`), la misma expresión es indexable tal cual, sin wrapper. SQLite no se toca.

### D2. Módulo `buscador` con un registro declarativo de fuentes

`backend/app/modules/buscador/`:
- `normalize.py`: `fold(col)`, `fold_text(s)`, `escape_like(s)` y `tokenize(q)`.
- `sources.py`: lista `SEARCH_SOURCES: list[SearchSource]` donde cada `SearchSource` declara `type`, `entity`, `module_key`, `model`, `title_col`, `content_cols`, `extra_where` (p. ej. `is_deleted = false`, `goal_type IN (...)`), `date_expr`, `parent_col` (opcional), una función `to_item(row) -> SearchItem` (título mostrado, `meta`, `path`) y, para notas, la subconsulta de etiquetas. Varias entidades pueden compartir `type` (p. ej. `study` = materias + exámenes).
- `service.py`: `SearchService.search(user_id, q, types, limit)` resuelve tipos permitidos (D4), arma una consulta por fuente, ejecuta en serie en la misma `AsyncSession` (una sesión no admite consultas concurrentes; son ≤ 20 consultas chicas) y arma los grupos.
- `schemas.py` y `api_routes.py` (`APIRouter(prefix="/search", tags=["search"])`, `GET ""` con `get_current_user` y `rate_limit_search`), incluido en `backend/app/api/v1/router.py`.

Agregar un tipo nuevo (p. ej. reglas de `finanzas-recurrentes`) es sumar una entrada en `SEARCH_SOURCES`, sin tocar el servicio.

*Alternativa*: un `UNION ALL` de todas las fuentes en una sola consulta. Descartada: columnas heterogéneas (fechas como `Date`, `DateTime` y texto ISO), un `LIMIT` por grupo exige ventanas (`ROW_NUMBER`) y la consulta resultante es frágil; la ganancia de latencia es despreciable con el volumen esperado.

### D3. Consulta, tokenización, escape y ranking

- **Validación** (422 en español): `q` se recorta y se colapsan espacios; después de eso debe tener entre 2 y 100 caracteres; se descartan caracteres de control. Se divide en hasta 5 tokens (los extra se ignoran); cada token se pliega con `fold_text` y se escapa con `escape_like` (`\` → `\\`, `%` → `\%`, `_` → `\_`) y se usa con `ESCAPE '\'` explícito (válido en ambos motores; SQLite no tiene escape por defecto). Un `q` de solo comodines (`%%`) busca esos caracteres literales.
- **`types`**: lista separada por comas de los tipos de D-Context; un valor desconocido → 422; vacío/ausente = todos. Tipos de plantillas no accesibles se omiten en silencio (D4).
- **`limit`**: por grupo, default 5, rango 1–20 (fuera de rango → 422). Se piden `limit + 1` filas para calcular `has_more` sin `COUNT`.
- **Coincidencia**: cada token debe aparecer (AND) en alguno de los campos de la fuente (`fold(title) LIKE '%t%' OR fold(content_1) LIKE ...`). Para notas, también `EXISTS` sobre `note_tags` ⨝ `tags` con `tags.user_id = :user_id` y `fold(tags.name) LIKE`.
- **Ranking** (expresión `CASE` en SQL para que el `LIMIT` respete el orden): `0` si `fold(title)` empieza con la frase completa plegada; `1` si `fold(title)` contiene todos los tokens; `2` en otro caso (coincide en contenido/etiquetas). Orden: `rank ASC, date_expr DESC, id` (el `id` desempata para que la paginación sea estable). `date_expr` usa `coalesce` hacia `updated_at`/`created_at` para no depender de `NULLS LAST`.
- **Orden de los grupos**: fijo (notas, tareas, eventos, movimientos, hábitos, metas, inversiones, y luego las plantillas en el orden de `MODULE_REGISTRY`); los grupos sin resultados no se devuelven.

### D4. Plantillas pagas: mismo criterio que `require_module` + estado activo

Se agrega `ModulesService.searchable_module_keys(user_id) -> set[str]`: incluye siempre las base; una paga se incluye si **(a)** `require_module` la dejaría pasar (comprada, o dev sin cobro configurado) **y (b)** no está desactivada (`EnabledModule.enabled` no es `false`). Para no duplicar la regla del bypass de dev, se extrae de `entitlements.py` una función pura `module_access_bypassed() -> bool` (`not settings.billing_enabled and not settings.is_production`) usada por `require_module` y por el helper. Se resuelve una sola vez por request (dos `SELECT` chicos).

La condición (b) es más estricta que `require_module`: una plantilla desactivada no se ve en la app, así que tampoco debe aparecer en el buscador (si no, el resultado llevaría a una pantalla que el usuario apagó). Comprada pero desactivada → no aparece; al reactivarla vuelve a aparecer (no hay índice que reconstruir).

*Alternativa*: llamar a cada endpoint de plantilla. Descartada (N requests internas, sin ranking común).

### D5. Rate limit propio por usuario

`search_rate_limiter = _build_rate_limiter(max_attempts=120, window_seconds=60)` y dependencia `rate_limit_search` con key `user_id` (igual que billing: por IP castigaría NAT compartidos). Con debounce de 250–300 ms una persona tipeando rápido genera ~3 requests/s en ráfagas cortas; 120/min no se alcanza en uso real y corta un script que barra el endpoint. Respeta `RATE_LIMIT_ENABLED`. 429 con `Retry-After` y `detail` en español. Bucket separado de auth/billing.

### D6. Respuesta: grupos, fragmento y resaltado por offsets

```json
{
  "query": "cafe",
  "groups": [
    {
      "type": "notes",
      "label": "Notas",
      "has_more": true,
      "items": [
        {
          "id": "…", "type": "notes", "entity": "note",
          "title": "Café con Juan",
          "title_highlights": [[0, 4]],
          "snippet": "…quedamos en el café de la esquina para…",
          "snippet_highlights": [[16, 20]],
          "date": "2026-10-20T13:05:00Z",
          "parent_id": null,
          "path": "/notes?open=…",
          "meta": {"tags": ["personal"]}
        }
      ]
    }
  ]
}
```

- **Fragmento**: ventana de ~140 caracteres alrededor de la primera coincidencia en el primer campo de contenido que coincida, cortada en límite de palabra, con `…` al principio/fin si se recortó; si la coincidencia fue solo en el título, el fragmento es el inicio del primer contenido no vacío (o `null`). Saltos de línea y espacios repetidos se colapsan. Se calcula en Python sobre las ≤ 21 filas traídas por fuente (barato).
- **Resaltado**: listas de `[inicio, fin)` sobre `title` y `snippet`, calculadas buscando cada token en el texto plegado (D1: mismo largo). Rangos superpuestos se fusionan. **No se devuelve HTML**: los clientes arman los `<mark>`/`<Text>` (cero riesgo de XSS con contenido de notas).
- **`meta`** (opcional, por tipo, valores crudos para que el cliente formatee en es-AR): `amount`/`currency`/`type` en movimientos; `status` en tareas/libros/proyectos; `asset_type`/`currency` en inversiones; `goal_type` en hábitos y metas; `tags` en notas; `is_all_day` en eventos; `archived` en notas.
- **`date`**: ISO 8601 (`YYYY-MM-DD` para fechas, datetime UTC con `Z` para timestamps); el cliente lo muestra en hora local.
- **`path`**: ruta web de destino (D7). Mobile no usa `path`: navega por `type` + `entity` + `id` + `parent_id` (D8).
- Los datos de texto se devuelven tal cual están guardados (la normalización es solo para comparar).

### D7. Web: paleta global + apertura por `?open=`

- `frontend/src/components/search/SearchPalette.tsx` montada una vez en `Layout.tsx`; se abre con `Ctrl+K` / `⌘K` (listener global que no se dispara dentro de inputs salvo con modificador, y `preventDefault` para que el navegador no enfoque su barra) y con un botón "Buscar" en la barra lateral y en la cabecera mobile del layout. Modal con foco atrapado, `Esc` cierra, restaura el foco al cerrar.
- Input con debounce de 250 ms; con < 2 caracteres no llama y muestra ayuda ("Escribí al menos 2 letras"). `useSearch(q, types)` sobre `useApiSWR` con key `['search', q, types]` y `keepPreviousData` para que la lista no parpadee; las respuestas viejas no pisan a las nuevas (SWR ya descarta por key).
- Teclado: `↑/↓` recorre la lista aplanada de todos los grupos (con wrap), `Enter` abre el activo, `Ctrl+Enter`/clic medio no aplica (SPA). Patrón ARIA combobox: `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`, lista `role="listbox"` con `role="option"` y encabezados de grupo `role="presentation"`. Estados: cargando, sin resultados ("No encontramos nada para «…»"), error (incluido 429: "Estás buscando muy rápido, esperá un momento").
- Resaltado con `Highlight.tsx` que corta el texto por offsets y envuelve en `<mark>` (sin `dangerouslySetInnerHTML`). Cada grupo muestra "Ver más en {label}" si `has_more`, que repite la búsqueda con `types=<tipo>&limit=20`.
- Destino: `navigate(item.path)`. Hook `frontend/src/hooks/useOpenParam.ts`: lee `open` (y `tab` donde aplique) de `useSearchParams`, espera a que la lista de la página haya cargado, llama al handler de la página (abrir el modal de edición/detalle existente; si la página no tiene modal para esa entidad, hace scroll al elemento con `id="item-<id>"` y lo resalta con la animación existente), y limpia el param con `replace` para que volver atrás o re-renderizar no lo reabra. Si el id ya no existe: toast "Ese elemento ya no existe". Finanzas lee `tab` (`transacciones` | `inversiones`) para elegir la pestaña inicial.
- Mapa de `path` (lo arma el backend en `to_item`): notas `/notes?open=`, tareas `/tasks?open=`, eventos `/events?open=`, hábitos `/habits?open=`, metas `/goals?open=`, movimientos `/finances?tab=transacciones&open=`, inversiones `/finances?tab=inversiones&open=`, plantillas `/{study|library|media|work|travel|vehicle|projects}?open=<id>&entity=<entity>` (para hijos, `open` es el id del hijo y `parent=<id del padre>`).
- Modo mock: `searchMock(q, types, limit)` en `endpoints.ts` que aplica el mismo plegado/tokenización/ranking sobre los datos mock existentes (función `foldText` compartida en `frontend/src/utils/search.ts`, con test), respetando el estado `owned/enabled` de los módulos mock.

### D8. Mobile: pantalla `Search` desde la cabecera de Inicio

- Ícono de lupa (`magnify`, `accessibilityLabel="Buscar"`, ≥ 44 dp) en la cabecera de `DashboardScreen`, junto al botón existente. Navega a `Search`, registrada en `DashboardStack`.
- `SearchScreen`: `TextField` con autofocus y botón limpiar, debounce 300 ms, mínimo 2 caracteres, `SectionList` con un header por grupo, ítem con título (resaltado con `<Text>` anidados en negrita/color primario por offsets), fragmento en 2 líneas, fecha local (`localDateString`/formatos de `src/lib/format.ts`) y `meta` formateado (`formatMoney`). Estados vacío/cargando/error; sin conexión muestra "Necesitás conexión para buscar" (es un GET: no pasa por la cola offline `queued(...)`). Sin precios, CTAs ni menciones a la tienda (los tipos de plantillas no compradas simplemente no vienen).
- Navegación al tocar (cross-tab con `navigation.navigate(tab, { screen, params })`, mismo patrón que `useNotificationTaps`):

  | `type` / `entity` | Destino |
  |---|---|
  | `notes` | `TasksTab` → `Notes` `{ openId }` |
  | `tasks` | `TasksTab` → `TasksHome` `{ openId }` |
  | `events` | `TasksTab` → `Events` `{ openId }` |
  | `habits` | `HabitsTab` → `HabitsHome` `{ openId }` |
  | `goals` (`progress`) | `HabitsTab` → `Goals` `{ openId }` |
  | `goals` (`savings`, según `meta.goal_type`) | `FinanceTab` → `Savings` `{ openId }` |
  | `transactions` | `FinanceTab` → `FinanceHome` `{ openId }` |
  | `investments` | `FinanceTab` → `Investments` `{ investmentId }` (param existente de la push) |
  | `study`, `library`, `media`, `work`, `travel`, `vehicle`, `projects` | `Dashboard` → `Study`/`Library`/`Media`/`Work`/`Travel`/`Vehicle`/`Projects` `{ openId, openEntity, parentId }` |

- Hook `src/hooks/useOpenParam.ts` análogo a `useCreateParam`: lee `openId` (+ `openEntity`, `parentId`), espera a que los datos de la pantalla estén cargados, llama al handler (abre el `BottomSheet` de edición/detalle existente o hace scroll + resaltado) y limpia los params con `setParams`. Los tipos de params del `TabNavigator` se extienden con `OpenParam = { openId?: string; openEntity?: string; parentId?: string }` combinado con `CreateParam`.

### D9. Privacidad de los términos

Los términos pueden ser sensibles (salud, plata). La app ya no loguea query strings; se agrega en `frontend/nginx*.conf` un `location = /api/v1/search` (mismo `proxy_pass` que `/api/`) con `access_log` en un `log_format` que usa `$uri` en lugar de `$request`. Sentry ya tiene `send_default_pii=False`; se verifica que no adjunte el query string en transacciones de `/search` (si lo hace, `before_send` lo borra). La respuesta lleva `Cache-Control: no-store`.

## Risks / Trade-offs

- [Tildes fuera del mapeo (`à`, `ç`, `ã`) no se pliegan] → el mapeo cubre el español; se amplía agregando pares en un solo lugar (`normalize.py` y `utils/search.ts`, con test que verifica que backend y mock usan la misma tabla).
- [`LIKE '%x%'` recorre todas las filas del usuario por tabla] → con miles de filas son milisegundos; si un usuario excepcional tiene cientos de miles, el plan B (D1) agrega trigram sin cambiar el SQL. Métrica de latencia por path ya existe.
- [≤ 20 consultas por request] → son chicas y acotadas por índice; el rate limit evita abuso; `types` permite pedir menos.
- [Sin stemming: "corriendo" no encuentra "correr"] → aceptado; el usuario suele buscar por palabras que escribió. Prefijos sí funcionan ("corr").
- [Fragmentos con contenido sensible en pantalla] → es el propio usuario autenticado; no se cachea en disco (`no-store`) ni se loguea.
- [`require_module` no mira `enabled` pero el buscador sí] → divergencia intencional y documentada (D4); el test cubre ambos casos.
- [Destinos sin modal de detalle en alguna pantalla] → fallback scroll + resaltado; ninguna página queda sin destino.
- [Conflicto con changes hermanos que tocan la cabecera de Inicio mobile o las mismas pantallas] → los cambios del buscador en esas pantallas son aditivos (un ícono, un hook); ver Dependencias.

## Migration Plan

- Sin migración de base ni extensiones. Deploy normal: backend (endpoint nuevo, aditivo), luego web y build mobile. Clientes viejos no lo usan.
- Rollback: revertir el router (el endpoint desaparece) y los clientes; no hay datos que limpiar.
- nginx: el `location` nuevo se agrega en los tres `nginx*.conf`; si se revierte, vuelve al log por defecto.

## Dependencias

- **Ninguna dependencia dura** con los changes hermanos.
- `finanzas-recurrentes`: si agrega una tabla de reglas recurrentes, se puede sumar como fuente nueva en `SEARCH_SOURCES` en ese change o en uno posterior; este change no la conoce.
- `finanzas-exportar-importar`: sin interacción (no hay tablas nuevas que exportar).
- `app-bloqueo-y-bienvenida`: puede tocar `DashboardScreen`/navegación mobile; la lupa y la ruta `Search` son aditivas. Si la app está bloqueada, la pantalla de búsqueda queda detrás del bloqueo como el resto (no requiere nada de este lado).
- `widgets-android`: un widget de "buscar" queda fuera de alcance; podría abrir `Search` por deep link en el futuro.
- `habitos-recordatorios-inteligentes`, `registro-edad-minima`, `finanzas-datos-mercado`: sin interacción (si `finanzas-datos-mercado` agrega campos a `investments`, el buscador sigue buscando por `name`/`ticker`/`institution`/`notes`).

## Open Questions

Decididas por el usuario (2026-11-03): se aplicaron las recomendaciones.

1. **¿Plantilla comprada pero desactivada aparece en el buscador?** Decidido: no (D4), coherente con que la pantalla no se ve. Las plantillas no compradas tampoco aparecen.
2. **¿Incluir notas archivadas?** Decidido: sí, con `meta.archived = true` y una etiqueta "Archivada" en el resultado (buscar algo viejo es justamente el caso de uso).
3. **¿`ñ` se pliega a `n`?** Decidido: sí ("nino" encuentra "niño"); el costo es que "año" y "ano" coinciden, aceptable en un buscador personal.
4. **¿Sumar fitness/nutrición, recordatorios y categorías/cuentas como tipos?** Decidido: no en esta etapa; el registro de fuentes lo deja a una línea.
5. **¿Historial de búsquedas recientes?** Decidido: no por ahora (los términos pueden ser sensibles y guardar historial agrega una superficie de privacidad); evaluarlo después, en el dispositivo y no en el servidor.
6. **Atajo adicional `/` para abrir la paleta en web.** Decidido: solo `Ctrl+K`/`⌘K` (el `/` choca con tipeo en campos de texto y lectores de pantalla).
7. **Plantillas en mobile.** Decidido: mobile no muestra CTAs de compra, precios ni "comprar en la web"; los resultados de plantillas que el usuario no tiene simplemente no vienen del backend.

## Notas de implementación

Desviaciones y hallazgos de la implementación respecto del diseño original:

- **Fecha de los eventos**: se devuelve como hora de pared sin zona (`2026-10-20T10:00:00`), igual que la API de eventos (`to_wall_clock`); con `Z` el cliente la correría 3 horas. Los demás timestamps siguen en UTC con `Z`.
- **Cobertura de changes hermanos**: se revisaron `modules/inversiones` (ya es fuente `investments`), `modules/recurrentes` (reglas recurrentes), `modules/habitos_recordatorios` y bloqueo/bienvenida. Las reglas recurrentes y los ajustes de recordatorios **no** se agregan como tipos: el alcance del diseño son los 14 tipos y ninguna de esas entidades tiene una pantalla propia a la que abrir un resultado; sumar una fuente más es una entrada en `SEARCH_SOURCES`.
- **Logs**: `sentry.py::scrub_search_query` (nuevo) saca el query string de los eventos y transacciones de `/api/v1/search` (`before_send` y `before_send_transaction`); Sentry adjunta `request.query_string` aunque `send_default_pii` sea `False`. En dev, `DEBUG=True` activa el echo de SQLAlchemy, que sí vuelca los parámetros de las consultas (incluido el término); producción fuerza `DEBUG=false`.
- **Etiqueta de mantenimiento**: el título mostrado es "Tipo · Vehículo" con el tipo capitalizado (`Revision · Gol Trend`); la coincidencia se busca solo en `notes` (el tipo no es buscable por texto).

### Rendimiento medido (tarea 8.3)

Usuario de ~5.000 filas (1.500 notas de ~1,7 KB de promedio, más el resto de los tipos), `/search` sin `types`:

| Motor | p50 | p95 | máx |
|-------|-----|-----|-----|
| SQLite (con caché del plegado por columna) | 300 ms | 354 ms | 408 ms |
| PGlite (PG 18 en WASM, no representativo de PG nativo) | 358 ms | 528 ms | n/d |

El objetivo p95 < 150 ms NO se cumple en esta máquina. Causa medida: los 14 `replace` anidados del plegado se aplican a todo el texto del usuario (LIKE plegado sobre 1.500 notas ≈ 69 ms contra ≈ 7 ms de un `lower() LIKE` simple). `types=notes` ronda 163 ms. Pendiente (no implementado): prefiltro barato `lower(col) LIKE` con vocales, ñ y no ASCII convertidos a `_`, que no puede dar falsos negativos (el test diferencial es la red de seguridad); si no alcanza, el Plan B (pg_trgm) ya está descrito arriba. No se verificó en Postgres nativo ni con nginx real (Docker no disponible: tarea 8.7 abierta).
