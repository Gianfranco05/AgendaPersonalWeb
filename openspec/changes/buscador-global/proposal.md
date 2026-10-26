## Why

La información de la persona está repartida en muchas pantallas (notas, tareas, movimientos, eventos, hábitos, metas, inversiones y las plantillas pagas que compró) y para encontrar algo hay que acordarse de en qué sección quedó y recorrer listas. Con miles de filas por usuario después de un tiempo de uso, "¿dónde anoté lo del café con Juan?" o "¿cuánto pagué en la gomería?" no tiene respuesta rápida. Un buscador global único, insensible a mayúsculas y tildes, resuelve eso en web y mobile.

## What Changes

- **Nuevo endpoint `GET /api/v1/search?q=&types=&limit=`** (autenticado, solo lectura): busca en todos los tipos a los que el usuario tiene acceso y devuelve resultados **agrupados por tipo**, cada uno con título, fragmento con rangos de resaltado (offsets, no HTML), fecha, `path` web de destino e ids para que mobile navegue.
- **Tipos buscables**: notas (título, contenido y nombres de etiquetas), tareas, movimientos (transacciones no borradas), eventos, hábitos (metas binarias/métricas), metas (progreso/ahorro), inversiones y, solo si la plantilla está comprada **y** activa, elementos de Estudio (materias y exámenes), Biblioteca (libros), Películas & Series, Trabajo (oportunidades), Viajes (viajes y equipaje), Vehículo (vehículos y mantenimientos) y Proyectos (proyectos y tareas de proyecto).
- **Reglas de consulta**: mínimo 2 y máximo 100 caracteres, hasta 5 palabras (todas deben aparecer), comodines de `LIKE` escapados, insensible a mayúsculas y tildes ("cafe" encuentra "Café", "nino" encuentra "Niño"). Ranking simple: el título que empieza con la búsqueda > título que contiene todas las palabras > coincidencia solo en el contenido; a igual nivel, más reciente primero. `limit` por grupo (default 5, máx. 20) con `has_more`.
- **Estrategia portable sin extensiones**: normalización ("fold") con `lower()` + `replace()` anidados, idéntica en PostgreSQL y SQLite, sobre consultas ya acotadas por `user_id` (índice existente). No requiere `pg_trgm`, `unaccent` ni migración; se documenta el plan B (índices trigram sobre la misma expresión, que es `IMMUTABLE`) para cuando el volumen lo pida.
- **Seguridad**: toda consulta filtrada por `user_id` (incluidas las uniones con etiquetas), plantillas pagas no compradas o desactivadas nunca aparecen (mismo criterio que `require_module` más el estado activo), rate limit propio por usuario, los términos de búsqueda no se loguean (tampoco en el access log de nginx).
- **Web**: paleta de búsqueda global (Ctrl+K / ⌘K y botón en la barra lateral y en la cabecera mobile del layout) con resultados en vivo (debounce), navegación con teclado (↑/↓/Enter/Esc), accesible (combobox ARIA), resaltado sin `dangerouslySetInnerHTML`, modo mock mantenido. Las páginas de destino abren el elemento con el query param `open` (hook `useOpenParam`) y Finanzas acepta `tab`.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): ícono de lupa en la cabecera de Inicio que abre una pantalla `Search` con resultados agrupados; tocar un resultado navega a la pantalla de su sección con el param `openId` (hook `useOpenParam`, análogo a `useCreateParam`) y abre el detalle/edición. Sin CTAs ni textos de compra para plantillas no compradas (simplemente no aparecen).

### Fuera de alcance

- Fitness, nutrición, focus, recordatorios, presupuestos, categorías y cuentas bancarias como tipos buscables (se pueden sumar después agregando una entrada al registro de fuentes).
- Búsqueda difusa/tolerante a errores de tipeo ("cafr" → "café"), stemming ("corriendo" → "correr") y búsqueda por montos o rangos de fechas.
- Historial de búsquedas recientes y sugerencias.
- Índices trigram / full-text en PostgreSQL (documentados como plan B, no se crean).

## Capabilities

### New Capabilities
- `global-search`: endpoint de búsqueda global, tipos y campos buscables, normalización insensible a mayúsculas/tildes, tokenización, escape de comodines, ranking, límites, agrupación, fragmento y resaltado, destino de cada resultado, aislamiento por usuario, gating de plantillas pagas y rate limit.
- `global-search-ui`: paleta de búsqueda web (atajo, debounce, teclado, accesibilidad, mock) con apertura del elemento en la página destino, y pantalla de búsqueda mobile con navegación al detalle.

### Modified Capabilities
<!-- Ninguna: las specs vigentes (real-api-notes, real-api-events, real-api-finance, goals-page, events-page) no cambian sus requisitos; el param `open` es aditivo y se especifica en global-search-ui. -->

## Impact

- **Backend**: nuevo módulo `backend/app/modules/buscador/` (`normalize.py`, `sources.py`, `service.py`, `schemas.py`, `api_routes.py`); router incluido en `backend/app/api/v1/router.py`; `backend/app/core/http_security.py` (limiter y dependencia `rate_limit_search`); `backend/app/modules/modulos/service.py` (helper de plantillas accesibles para búsqueda, compartiendo el criterio de `backend/app/core/entitlements.py`). Sin tablas nuevas, sin migración, sin cambios en `OWNED_TABLES`.
- **Tests**: nuevo `backend/tests/test_search.py`; `backend/tests/test_auth_gate.py` (endpoint en la lista de 401); `backend/tests/test_tenant_isolation.py`.
- **Web**: `frontend/src/components/search/` (`SearchPalette.tsx`, `SearchResultItem.tsx`, `Highlight.tsx`), `frontend/src/components/Layout.tsx`, `frontend/src/hooks/useSearch.ts`, `frontend/src/hooks/useOpenParam.ts`, `frontend/src/api/endpoints.ts` (+ mock), `frontend/src/types`, y las páginas de destino (Notes, Tasks, Events, Habits, Goals, Finance, Study, Library, Media, Work, Travel, Vehicle, Projects); `frontend/nginx*.conf` (access log sin query string para `/api/v1/search`).
- **Mobile**: `src/screens/SearchScreen.tsx`, `src/hooks/useSearch.ts`, `src/hooks/useOpenParam.ts`, `src/api/endpoints.ts`, `src/types`, `src/navigation/TabNavigator.tsx` (ruta `Search` y param `openId` en los stacks), `src/screens/DashboardScreen.tsx` (lupa) y las pantallas de destino.
- **Infra**: sin dependencias ni extensiones nuevas; Redis opcional como hoy para el rate limit.
