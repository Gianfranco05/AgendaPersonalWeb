## 1. Backend — Normalización y fuentes

- [x] 1.1 Crear `backend/app/modules/buscador/__init__.py` y `normalize.py` con la tabla de plegado única (`á é í ó ú ü ñ` + mayúsculas → `a e i o u u n`), `fold(col)` (SQL con `func.lower` + `func.replace` anidados, `coalesce(col, '')`), `fold_text(s)` con el mismo mapeo y largo preservado, `escape_like(s)` (`\`, `%`, `_`) y `tokenize(q)` (recorte, colapso de espacios, sin caracteres de control, 2–100 caracteres, máx. 5 tokens) (design D1, D3)
- [x] 1.2 `buscador/sources.py`: dataclass `SearchSource` (`type`, `entity`, `module_key`, `model`, `title_col`, `content_cols`, `extra_where`, `date_expr`, `parent_col`, `to_item`) y `SEARCH_SOURCES` con las 18 entidades de la tabla de Context (notas con `EXISTS` sobre `note_tags` ⨝ `tags` filtrando `tags.user_id`; transacciones con `is_deleted = false`; hábitos `goal_type IN ('binary','metric')`; metas `IN ('progress','savings')`; hijos de plantillas con `parent_col`)
- [x] 1.3 `to_item` por fuente: título mostrado (trabajo "Rol · Empresa", mantenimiento "tipo · vehículo"), `meta` crudo (D6), `date` ISO y `path` web con ids URL-encoded (design D7)
- [x] 1.4 Helper de fragmento (~140 caracteres alrededor de la primera coincidencia, corte en palabra, `…`, espacios colapsados) y de resaltado (offsets `[inicio, fin)` sobre el texto plegado, fusionando superpuestos) para `title` y `snippet`

## 2. Backend — Servicio, gating, rate limit y API

- [x] 2.1 Extraer `module_access_bypassed()` en `backend/app/core/entitlements.py` y usarla en `require_module` sin cambiar su comportamiento (los tests de módulos siguen verdes)
- [x] 2.2 `ModulesService.searchable_module_keys(user_id)` en `backend/app/modules/modulos/service.py`: base siempre; pagas si (comprada o bypass) y no desactivadas (design D4)
- [x] 2.3 `buscador/service.py`: `SearchService.search(user_id, q, types, limit)`: resolver tipos permitidos, una consulta por fuente con `WHERE user_id = :uid AND <extra> AND (AND de tokens, cada uno OR de campos con LIKE ... ESCAPE '\')`, `CASE` de ranking 0/1/2, `ORDER BY rank, date_expr DESC, id`, `LIMIT limit+1`, ejecución en serie en la misma sesión, merge de entidades del mismo `type` respetando orden y `limit`, grupos en orden fijo y omitiendo vacíos
- [x] 2.4 `buscador/schemas.py`: `SearchItem`, `SearchGroup`, `SearchResponse`; validación de `types` (enum de 14 valores, CSV) y `limit` (1–20, default 5) con 422 en español
- [x] 2.5 `backend/app/core/http_security.py`: `search_rate_limiter = _build_rate_limiter(120, 60)` y `rate_limit_search` por `user_id` respetando `RATE_LIMIT_ENABLED` (design D5)
- [x] 2.6 `buscador/api_routes.py`: `APIRouter(prefix="/search", tags=["search"])`, `GET ""` con `get_current_user` + `rate_limit_search`, header `Cache-Control: no-store`; incluirlo en `backend/app/api/v1/router.py`
- [x] 2.7 Confirmar que ningún log/metric/Sentry incluye el query string de `/search` (request logging ya usa solo `path`; revisar transacciones de Sentry y agregar scrub en `before_send` si hiciera falta)

## 3. Backend — Tests (`backend/tests/test_search.py` salvo indicación)

- [x] 3.1 Validación: `q` de 1 carácter (con espacios) → 422; 101 caracteres → 422; `limit` 0/21 → 422; `types` desconocido → 422; sin sesión → 401 (sumar `("GET", "/api/v1/search?q=ab")` a `backend/tests/test_auth_gate.py`)
- [x] 3.2 Tildes y mayúsculas: "cafe"→"Café", "josé"→"Jose", "reunion"→"REUNIÓN ANUAL" (ejercita el `lower()` ASCII de SQLite), "nina"→"niña", prefijo parcial "cafet"
- [x] 3.3 Tokens y comodines: AND de tokens; `20%` no trae "200"; `mi_a` no trae "miXarchivo"; `%%` no trae todo; tests unitarios de `fold_text`, `escape_like` y `tokenize`
- [x] 3.4 Ranking: título > contenido aunque el de contenido sea más nuevo; prefijo > contiene; más reciente primero a igual rango; `limit` aplicado después de ordenar; `has_more`
- [x] 3.5 Cobertura de tipos: cada fuente encuentra su elemento por título y por un campo de contenido; nota por nombre de etiqueta; transacción borrada no aparece; hábito vs meta en grupos distintos; hijo con `parent_id` y `path` correctos (examen, ítem de equipaje, mantenimiento, tarea de proyecto)
- [x] 3.6 Forma de la respuesta: `title_highlights` `[[0,4]]` en "Café con Juan"; fragmento ≤ ~140 caracteres con `…` y highlight dentro; HTML guardado vuelve literal; orden fijo de grupos; grupos vacíos omitidos; `Cache-Control: no-store`
- [x] 3.7 Aislamiento: datos, etiquetas y `has_more` de otro usuario nunca aparecen; agregar el caso a `backend/tests/test_tenant_isolation.py`
- [x] 3.8 Plantillas (con `BILLING_PROVIDER` configurado vía `monkeypatch` como en `test_modules.py`): no comprada → sin grupo (también con `types=` explícito → `groups=[]`); comprada y activa → aparece; comprada y desactivada → no aparece y vuelve al reactivar; producción sin cobro → no aparece; dev sin cobro → aparece (paridad con `require_module`)
- [x] 3.9 Rate limit: 121 requests en la ventana → 429 con `Retry-After`; otro usuario no afectado; con `RATE_LIMIT_ENABLED=False` no limita (resetear el limiter entre tests)
- [x] 3.10 Log: con `caplog`, una búsqueda no deja el término en los logs del request
- [x] 3.11 Confirmar que `test_infra.py::test_no_api_route_is_public_by_accident` y `test_account.py` (guarda de `OWNED_TABLES`) pasan sin cambios (no hay tablas nuevas) y correr `cd backend && python -m pytest -q` completo sin regresiones

## 4. Web — API, tipos, mock y hooks (`frontend/`)

- [x] 4.1 Tipos en `src/types`: `SearchType`, `SearchItem`, `SearchGroup`, `SearchResponse`
- [x] 4.2 `src/utils/search.ts`: `foldText` (misma tabla que el backend), `tokenize`, ranking y cálculo de highlights para el mock, con tests unitarios (incluye un test que fija la tabla de plegado para detectar divergencias con `normalize.py`)
- [x] 4.3 `src/api/endpoints.ts`: `searchAll(q, { types, limit })` → `GET /search`; en `MOCK_ENABLED`, `searchMock` sobre los datos mock existentes respetando `owned/enabled` de los módulos mock
- [x] 4.4 `src/hooks/useSearch.ts` (debounce 250 ms, sin llamada con < 2 caracteres, key `['search', q, types, limit]`, `keepPreviousData`) y `src/hooks/useOpenParam.ts` (lee `open`/`entity`/`parent`/`tab`, espera datos, llama al handler, limpia con `replace`, toast "Ese elemento ya no existe")

## 5. Web — UI (`frontend/`)

- [x] 5.1 `src/components/search/Highlight.tsx`: corta por offsets y envuelve en `<mark>` (estilos claro/oscuro), sin `dangerouslySetInnerHTML`
- [x] 5.2 `src/components/search/SearchPalette.tsx` + `SearchResultItem.tsx`: modal con foco atrapado, input, grupos con label e ícono, fecha local (`src/utils/date.ts`) y `meta` formateado, estados ayuda/cargando/vacío/error/429, "Ver más en {label}", combobox ARIA y navegación `↑/↓/Enter/Esc` con wrap
- [x] 5.3 `src/components/Layout.tsx`: montar la paleta, listener global `Ctrl+K`/`⌘K` (solo en el layout autenticado, `preventDefault`), botón "Buscar" en la barra lateral y en la cabecera mobile (`lg:hidden`)
- [x] 5.4 Páginas destino con `useOpenParam`: `Notes`, `Tasks` (KanbanBoard), `Events`, `Habits`, `Goals`, `Finance` (pestaña inicial desde `tab` + modal de transacción/inversión), `Study` (materia/examen), `Library`, `Media`, `Work`, `Travel` (viaje/ítem), `Vehicle` (vehículo/mantenimiento), `Projects` (proyecto/tarea); abrir el modal existente o, si no hay, scroll + resaltado con `id="item-<id>"`
- [x] 5.5 Tests de componentes: atajo abre/cierra y restaura foco; debounce manda una sola request; < 2 caracteres no llama; teclado recorre grupos con wrap y `Enter` navega al `path`; título con `<img onerror>` se muestra literal; "Ver más" pide `limit=20`; `useOpenParam` abre el modal y limpia la URL, e id inexistente muestra el toast
- [x] 5.6 `frontend/nginx.conf`, `nginx.dev.conf` y `nginx.tls.conf`: `location = /api/v1/search` con el mismo proxy que `/api/` y `access_log` con un `log_format` que use `$uri` (sin query string) (design D9)
- [x] 5.7 `npx vitest run --maxWorkers=2`, `npm run build` y lint sin errores (el frontend no tiene eslint configurado: se verifica con `tsc -b --noEmit`)

## 6. Mobile — API, hooks y navegación (`C:\Proyectos\vida-personal-mobile`)

- [x] 6.1 [mobile] Tipos de búsqueda en `src/types` y `searchAll(q, { types, limit })` en `src/api/endpoints.ts` (GET directo, sin `queued`)
- [x] 6.2 [mobile] `src/hooks/useSearch.ts` (debounce 300 ms, mínimo 2 caracteres, SWR) y `src/hooks/useOpenParam.ts` análogo a `useCreateParam` (`openId`, `openEntity`, `parentId`; espera datos; limpia con `setParams`; "Ese elemento ya no existe")
- [x] 6.3 [mobile] `src/navigation/TabNavigator.tsx`: tipo `OpenParam` combinado con `CreateParam` en `TasksHome`, `Notes`, `Events`, `HabitsHome`, `Goals`, `FinanceHome`, `Savings` y las pantallas de plantillas del `DashboardStack`; registrar `Search` en `DashboardStack`; mantener `investmentId` de `Investments`
- [x] 6.4 [mobile] Helper `navigateToResult(navigation, item)` con la tabla de destinos de design D8 (metas de ahorro → `FinanceTab`/`Savings` según `meta.goal_type`)

## 7. Mobile — UI (`C:\Proyectos\vida-personal-mobile`)

- [x] 7.1 [mobile] `src/screens/DashboardScreen.tsx`: botón lupa (`magnify`, `accessibilityLabel="Buscar"`, ≥ 44 dp) en la cabecera junto al existente, que navega a `Search`
- [x] 7.2 [mobile] `src/screens/SearchScreen.tsx`: `TextField` con autofocus y limpiar, `SectionList` por grupo, título resaltado con `<Text>` anidados, fragmento 2 líneas, fecha local y `formatMoney` para `meta`, estados vacío/cargando/error/sin conexión ("Necesitás conexión para buscar"), tokens Stitch claro/oscuro; sin precios ni CTAs de compra
- [x] 7.3 [mobile] Pantallas destino con `useOpenParam`: `NotesScreen`, `TasksScreen`, `EventsScreen`, `HabitsScreen`, `GoalsScreen`, `SavingsScreen`, `FinanceScreen` (transacción), y `StudyScreen`, `LibraryScreen`, `MediaScreen`, `WorkScreen`, `TravelScreen`, `VehicleScreen`, `ProjectsScreen` (seleccionar padre y abrir hijo); `InvestmentsScreen` sigue con `investmentId`
- [x] 7.4 [mobile] `npx tsc --noEmit` y tests existentes del repo mobile en verde

## 8. Verificación contra el backend real (no mock)

- [ ] 8.1 Levantar el backend contra Postgres (docker compose o PGlite vía npm) y correr por API búsquedas con tildes/mayúsculas ("cafe"/"CAFÉ", "reunion"/"REUNIÓN"), comodines (`20%`, `mi_a`) y tokens múltiples: mismos resultados que en SQLite, 422 para `q` corto/largo, nunca 500
- [ ] 8.2 En Postgres, con la base creada con collation `C` o `es_AR.UTF-8`, confirmar que "reunion" encuentra "REUNIÓN" (el plegado no depende de la collation)
- [ ] 8.3 Medir latencia con un usuario sembrado de ~5.000 filas repartidas (notas largas incluidas): p95 de `/search` sin `types` < 150 ms; registrar el número en el change
- [ ] 8.4 Con cobro configurado: usuario sin plantillas no ve grupos pagos; comprar (webhook de prueba) una plantilla → aparece; desactivarla en Módulos → desaparece
- [ ] 8.5 Web con `VITE_MOCK_ENABLED=false`: `Ctrl+K` desde varias páginas, resultados en vivo, teclado, abrir nota/tarea/evento/movimiento/inversión/examen y ver el modal correcto; URL limpia al cerrar
- [ ] 8.6 Mobile (build lan o Expo contra el backend real): lupa en Inicio, buscar, tocar un resultado de cada tab y de una plantilla comprada, sin conexión muestra el aviso, no aparece ningún texto de compra
- [ ] 8.7 nginx: una búsqueda en el stack de prod deja en el access log `/api/v1/search` sin el término
- [ ] 8.8 Correr `openspec validate buscador-global --strict` y marcar las tareas completadas
