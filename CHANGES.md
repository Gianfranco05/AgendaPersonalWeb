# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Vida Personal (LifeOS)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están archivadas en `openspec/changes/archive/`).
2. Leer los specs existentes en `openspec/specs/` o `openspec/changes/` indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-complete
  │
  ├── C-02 rest-api-endpoints          ← FASE 1 — en paralelo
  ├── C-03 metas-and-ajustes           ←
  └── C-04 backend-cleanup             ←
        │
        ├── C-05 frontend-real-api     ← necesita C-02
        │     │
        │     ├── C-07 frontend-testing    ← necesita C-05
        │     └── C-09 frontend-optimize   ← necesita C-05 + C-07
        │
        ├── C-06 frontend-pages-extra  ← necesita C-02 + C-03
        │
        └── C-08 backend-more-tests    ← necesita C-03
              │
              └── C-10 production-deploy    ← necesita C-09 + C-04 + C-08
```

### Paralelismo por fase

```
GATE 0: ninguna
  → C-01 (solo)

GATE 1: C-01 ✓                     ← PRIMER FORK (3 paralelos)
  → C-02 rest-api-endpoints              [Agente A]
  → C-03 metas-and-ajustes               [Agente B]
  → C-04 backend-cleanup                 [Agente C]

GATE 2: C-02 + C-03 ✓              ← SEGUNDO FORK
  → C-05 frontend-real-api                [Agente A]
  → C-06 frontend-pages-extra             [Agente C]

GATE 3: C-05 ✓                     ← TERCER FORK
  → C-07 frontend-testing                 [Agente B]
  └ C-03 + C-04 ✓
    → C-08 backend-more-tests             [Agente C]

GATE 4: C-07 + C-05 ✓
  → C-09 frontend-optimize                [Agente A]

GATE 5: C-09 + C-04 + C-08 ✓
  → C-10 production-deploy                [Agente A]
```

### Camino crítico (8 changes — mínimo irreducible)

```
C-01 → C-02 → C-05 → C-09 → C-10
                               ↑
                        (C-04 y C-08 convergen acá)
```

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core) │ Agente B (Backend Aux) │ Agente C (Frontend/QA)
─────┼─────────────────────────┼────────────────────────┼──────────────────────────
  1  │ C-01 foundation-complete│          —              │          —
  2  │ C-02 rest-api-endpoints │ C-03 metas-and-ajustes │ C-04 backend-cleanup
  3  │ C-05 frontend-real-api  │          —              │ C-06 frontend-pages-extra
  4  │ C-09 frontend-optimize  │ C-07 frontend-testing   │ C-08 backend-more-tests
  5  │ C-10 production-deploy  │          —              │          —
```

---

## FASE 0 — Cierre de Fundación

> Cerrar el change `project-foundation` existente. Verificar que Docker funciona y que todo el stack está operativo.

### [C-01] `complete-foundation`
- **Estado**: `[x]` completado — archivado el 28/06/2026
- **Scope**: Terminar las tareas pendientes del change `project-foundation` (5 tasks) y archivarlo
  - Verificar `docker compose up --build` — backend healthy en `:8000/health`, frontend en `:5173`
  - Verificar Dashboard carga widgets con datos del backend
  - Verificar Finance: crear/editar/eliminar transacción
  - Verificar Notes: crear/editar nota con Markdown
  - Verificar Tasks: drag & drop entre columnas Kanban
  - Archivar el change `project-foundation` en `openspec/changes/archive/`
  - Hacer commit con los cambios pendientes y el archivo
- **Dependencias**: ninguna (es terminar lo que ya está)
- **Governance**: MEDIO
- **Leer antes**:
  - `openspec/changes/project-foundation/tasks.md` (tareas 4.7, 9.2-9.5)
  - `openspec/changes/project-foundation/design.md` (arquitectura actual)
  - `openspec/config.yaml` (stack y convenciones)

---

## FASE 1 — Backend: API REST unificada + Módulos pendientes + Limpieza

> Tres changes que pueden ejecutarse en paralelo. Todos dependen de que C-01 esté archivado. No dependen entre sí.

### [C-02] `rest-api-endpoints`
- **Estado**: `[x]` completado — archivado el 29/06/2026
- **Scope**: Crear endpoints REST JSON unificados bajo `/api/v1/` para todos los módulos
  - Crear `backend/app/api/v1/` con routers: `finance.py`, `notes.py`, `events.py`, `goals.py`, `settings.py`
  - `GET /api/v1/finance/summary` — resumen financiero (balance, ingresos, egresos, periodo)
  - `GET /api/v1/finance/transactions` — lista paginada con filtros (fecha, categoría, tipo)
  - `POST /api/v1/finance/transactions` — crear transacción con validación Pydantic
  - `PUT /api/v1/finance/transactions/{id}` — actualizar transacción
  - `DELETE /api/v1/finance/transactions/{id}` — soft-delete
  - `GET /api/v1/finance/categories` — lista de categorías con totales
  - `GET /api/v1/notes` — lista de notas con filtro por tag, búsqueda
  - `POST /api/v1/notes` — crear nota con tags y color
  - `PUT /api/v1/notes/{id}` — actualizar nota (pin, archive, contenido)
  - `DELETE /api/v1/notes/{id}` — eliminar nota
  - `GET /api/v1/notes/tags` — lista de tags
  - `GET /api/v1/events` — eventos con rango de fechas (upcoming, monthly)
  - `POST /api/v1/events` — crear evento
  - `PUT /api/v1/events/{id}` — actualizar evento
  - `DELETE /api/v1/events/{id}` — eliminar evento
  - `GET /api/v1/goals` — metas activas con progreso
  - `POST /api/v1/goals` — crear meta
  - `PUT /api/v1/goals/{id}/checkin` — registrar hábito
  - `GET /api/v1/settings` — preferencias del usuario
  - `PUT /api/v1/settings` — actualizar preferencias
  - Incluir todos los routers en `main.py` bajo prefijo `/api/v1`
  - No modificar las rutas HTML existentes — coexistencia pacífica
  - Tests: smoke test de cada endpoint, validación 422, auth gate, paginación
- **Dependencias**: C-01
- **Governance**: ALTO (la API REST es el contrato que consume el frontend)
- **Leer antes**:
  - `openspec/changes/project-foundation/specs/backend-refinement/spec.md`
  - `openspec/changes/project-foundation/design.md` §API Endpoints
  - `openspec/config.yaml` (stack y convenciones)
  - `backend/app/main.py` (routers actuales)
  - `backend/app/modules/finanzas/routes.py` (patrón de rutas existente)

---

### [C-03] `metas-and-ajustes`
- **Estado**: `[x]` completado — archivado el 29/06/2026
- **Scope**: Completar los módulos `metas` y `ajustes` con capa de servicio, repositorio, schemas Pydantic y tests
  - **Metas**:
    - Crear `backend/app/modules/metas/schemas.py` — GoalCreate, GoalUpdate, GoalOut, HabitRecordCreate, GoalProgress
    - Crear `backend/app/modules/metas/repository.py` — GoalRepository con CRUD + checkin + completar
    - Crear `backend/app/modules/metas/service.py` — GoalsService con lógica de progreso, rachas, check-in
    - Refactorizar `metas/routes.py` para usar service + repository en vez de DB inline
    - Agregar endpoint `GET /metas/api/goals` JSON (para consumo frontend)
    - Crear `backend/tests/test_metas.py`: crear meta, listar, check-in, completar, auth gate
  - **Ajustes**:
    - Crear `backend/app/modules/ajustes/schemas.py` — UserPreferenceUpdate, UserPreferenceOut
    - Crear `backend/app/modules/ajustes/repository.py` — UserPreferenceRepository
    - Crear `backend/app/modules/ajustes/service.py` — SettingsService con validación
    - Refactorizar `ajustes/routes.py` para usar service + repository
    - Agregar endpoint `GET /ajustes/api/preferences` JSON
    - Crear `backend/tests/test_ajustes.py`: obtener preferencias, actualizar, auth gate
  - Type hints: corregir `user_id: UUID` → `str` en repositorios existentes para coincidir con `String(36)`
- **Dependencias**: C-01
- **Governance**: MEDIO
- **Leer antes**:
  - `openspec/changes/project-foundation/specs/backend-refinement/spec.md`
  - `backend/app/modules/metas/models.py` (modelos existentes)
  - `backend/app/modules/ajustes/models.py` (modelos existentes)
  - `backend/app/modules/auth/repository.py` (patrón de repositorio a seguir)

---

### [C-04] `backend-cleanup`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Verificar que la migración a Jinja2 templates está completa y agregar tests de humo
  - Verificar que no existe HTML inline residual en ningún módulo (confirmado — 0 archivos)
  - Verificar que no existen archivos basura en raíz del backend (confirmado — 0 archivos)
  - Verificar que `slowapi` no está en `requirements.txt` (confirmado)
  - Verificar que `render_utils.py` no existe (confirmado)
  - Verificar que `Jinja2Templates` está configurado en `core/templates.py` (confirmado)
  - Verificar que todos los templates HTML existen en sus directorios (confirmado — 18 templates)
  - **Bug encontrado y corregido**: `formulario.html` tenía una list comprehension Python (`[t.id for t in ...]`) inválida en Jinja2 — reemplazada por `map(attribute='id') | list`
  - **Import faltante**: `routes.py` de ajustes ya tenía `from app.modules.ajustes.models import UserPreference` (confirmado existente)
  - Tests de humo: 26 tests en `test_html_routes.py` cubriendo auth, finanzas, anotaciones, eventos, metas, ajustes
  - Tests pasando: 26/26
- **Dependencias**: C-01
- **Governance**: MEDIO
- **Leer antes**:
  - `openspec/changes/project-foundation/specs/backend-refinement/spec.md`
  - `backend/app/main.py` (configuración de templates)
  - `backend/app/core/render_utils.py` (helpers existentes)
  - `backend/app/modules/finanzas/routes.py` (el más grande — referencia de todo el HTML inline)

---

## FASE 2 — Frontend: Conexión real + Páginas faltantes

> El frontend actual funciona con mock data. Estos changes lo conectan al backend real y agregan las pantallas que faltan.

### [C-05] `frontend-real-api`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Conectar el frontend al backend real deshabilitando el modo mock, arreglando auth y corrigiendo bugs
  - Cambiar `MOCK_ENABLED = true` a variable de entorno `VITE_MOCK_ENABLED` (default `false`)
  - Verificar que todos los endpoints de `endpoints.ts` coinciden con las rutas `/api/v1/` reales
  - Arreglar `client.ts` — `baseURL` debe usar `VITE_API_URL` o el proxy de Vite
  - Auth: exponer `authApi.ts` correctamente; verificar login/logout/me funcionan con backend real
  - LoginPage:
    - Arreglar link `/auth/register` — redirige a 404 (no existe ruta en App.tsx ni en el backend como SPA)
    - Opción 1: crear ruta `/register` en App.tsx con un RegisterPage placeholder → redirige a `/login`
    - Opción 2: sacar el link directo y mostrar mensaje "contactá al administrador" (single-user local)
  - Verificar que el proxy de Vite en `vite.config.ts` cubre TODOS los prefijos `/api/v1/...`
  - Agregar manejo de errores de red en todos los hooks SWR (cuando backend no responde)
  - Validar que `useFinance.ts` funciona con datos reales del backend
  - Validar que los hooks `useNotes.ts` y `useEvents.ts` se importan y usan en sus respectivas páginas (reemplazar llamadas directas)
  - Tasks/Kanban: queda con localStorage + mock data (no hay backend de tasks)
  - Tests: smoke test de conexión, login flow end-to-end
- **Dependencias**: C-02 (necesita los endpoints `/api/v1/` reales)
- **Governance**: ALTO (conecta frontend y backend — si esto falla, no hay app)
- **Leer antes**:
  - `frontend/src/api/endpoints.ts` (mocks actuales)
  - `frontend/src/api/client.ts` (config Axios)
  - `frontend/src/api/authApi.ts` (auth endpoints)
  - `frontend/vite.config.ts` (proxy config)
  - `frontend/src/hooks/useFinance.ts` (hooks SWR)

---

### [C-06] `frontend-pages-extra`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Agregar páginas faltantes en el frontend para cubrir todos los módulos del backend
  - **Página Eventos/Calendario**:
    - Crear `frontend/src/pages/Events/EventsPage.tsx` — vista de calendario mensual
    - Crear `EventForm.tsx` — modal para crear/editar evento con fecha, hora, descripción
    - Crear `EventList.tsx` — lista de eventos próximos
    - Agregar ruta `/events` en `App.tsx` con link en sidebar `Layout.tsx`
    - Consumir `GET/POST/PUT/DELETE /api/v1/events`
  - **Página Metas**:
    - Crear `frontend/src/pages/Goals/GoalsPage.tsx` — tablero de metas con progreso visual
    - Crear `GoalCard.tsx` — card con nombre, descripción, barra de progreso, racha actual
    - Crear `GoalForm.tsx` — modal para crear/editar meta
    - Crear `CheckInButton.tsx` — botón de check-in diario para hábitos
    - Agregar ruta `/goals` en `App.tsx` con link en sidebar
    - Consumir `GET/POST /api/v1/goals`, `PUT /api/v1/goals/{id}/checkin`
  - **Página Ajustes** (opcional, de baja prioridad):
    - Crear `frontend/src/pages/Settings/SettingsPage.tsx`
    - Formulario simple de preferencias del usuario
    - Agregar ruta `/settings` en `App.tsx`
  - **Sidebar**: Actualizar `Layout.tsx` con links a Events, Goals, Settings
  - **RegisterPage**: Crear componente mínimo que redirija a `/login` (single-user)
  - Tests: render de cada página, navegación entre rutas
- **Dependencias**: C-02 (endpoints REST), C-03 (metas/ajustes endpoints)
- **Governance**: BAJO
- **Leer antes**:
  - `frontend/src/pages/Dashboard/DashboardPage.tsx` (patrón de página)
  - `frontend/src/components/Layout.tsx` (sidebar con links)
  - `openspec/changes/project-foundation/specs/frontend-dashboard/spec.md`
  - `frontend/src/pages/Finance/FinancePage.tsx` (patrón CRUD completo)

---

## FASE 3 — Testing y Calidad

> Una vez que el frontend está conectado al backend real y los módulos están completos, agregar tests en ambos lados.

### [C-07] `frontend-testing`
- **Estado**: `[x]` completado — archivado el 30/06/2026 (39 tests, 83% coverage)
- **Scope**: Configurar y escribir tests unitarios y de componentes para el frontend
  - Instalar y configurar Vitest + React Testing Library + jsdom
  - Configurar `vitest.config.ts` con alias `@/` → `src/` como en `vite.config.ts`
  - Tests de componentes:
    - `Layout.spec.tsx` — sidebar renderiza, navegación funciona, active state
    - `LoadingSkeleton.spec.tsx` — renderiza variantes (card, table, text)
    - `ErrorBoundary.spec.tsx` — captura errores, muestra fallback
    - `ProtectedRoute.spec.tsx` — autenticado vs no autenticado
    - `FinanceWidget.spec.tsx` — renderiza balance, transacciones, estado vacío
    - `TransactionModal.spec.tsx` — formulario, validación, submit
    - `KanbanBoard.spec.tsx` — drag & drop entre columnas, render inicial
    - `NoteEditor.spec.tsx` — renderiza editor, toolbar
  - Tests de hooks:
    - `useKanban.spec.ts` — addTask, moveTask, deleteTask, persistencia localStorage
    - `useFinance.spec.ts` — SWR mocking, data fetching
  - Tests de páginas (smoke):
    - `DashboardPage.spec.tsx` — renderiza widgets
    - `FinancePage.spec.tsx` — renderiza tabla + charts + filters
  - Tests de API client:
    - `client.spec.ts` — Axios interceptor, baseURL, withCredentials
  - Coverage target: mínimo 50% en componentes compartidos
  - Agregar script `npm run test` y `npm run test:coverage` en `package.json`
- **Dependencias**: C-05 (frontend estable con API real)
- **Governance**: BAJO
- **Leer antes**:
  - `frontend/src/components/Layout.tsx` (componentes compartidos)
  - `frontend/src/hooks/useKanban.ts` (hook custom)
  - `frontend/package.json` (dependencias)

---

### [C-08] `backend-more-tests`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Agregar tests faltantes para metas, ajustes, y tests de integración para la API REST
  - Tests de integración para endpoints `/api/v1/` (C-02):
    - `test_api_finance.py`: CRUD transacciones, summary, categories, paginación, filtros
    - `test_api_notes.py`: CRUD notas, tags, búsqueda, pin/archive
    - `test_api_events.py`: CRUD eventos, rango de fechas
  - Tests de módulos completados (C-03):
    - `test_metas.py`: crear meta, listar, check-in diario, completar, streak
    - `test_ajustes.py`: obtener preferencias, actualizar, validación
  - Tests de seguridad:
    - `test_auth_gate.py`: cada endpoint protegido sin cookie → 401
    - `test_cors.py`: CORS headers correctos
  - Tests de carga (opcional):
    - `test_pagination.py`: 100 transacciones, páginas correctas
  - Mejorar `conftest.py` con fixtures para la API REST (test client con prefijo `/api/v1`)
  - Verificar que `pytest backend/tests/ -v` pasa completo (target: 70+ tests)
- **Dependencias**: C-03 (metas/ajustes completos), C-02 (API REST)
- **Governance**: BAJO
- **Leer antes**:
  - `backend/tests/conftest.py` (fixtures actuales)
  - `backend/tests/test_finanzas.py` (patrón de tests existente)
  - `openspec/changes/project-foundation/specs/backend-testing/spec.md`

---

## FASE 4 — Optimización y Producción

### [C-09] `frontend-optimize`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Optimizar el bundle, agregar lazy loading, mejorar performance
  - Code-splitting con `React.lazy()` + `Suspense` para páginas pesadas:
    - `FinancePage` (lazy — pesa por recharts)
    - `NotesPage` (lazy — pesa por @uiw/react-md-editor)
    - `KanbanBoard` (lazy)
    - `EventsPage` (lazy — si fue creada en C-06)
  - Dynamic import de `recharts` solo en FinancePage
  - Dynamic import de `@uiw/react-md-editor` solo en NotesPage
  - Agregar indicador de carga (`LoadingSkeleton`) para cada chunk lazy
  - Analizar bundle con `vite build --analyze` o `rollup-plugin-visualizer`
  - Configurar compresión gzip/brotli en Vite build
  - Configurar分包 (manual chunks) en `vite.config.ts` para vendor separado:
    - `vendor-react.js` — react, react-dom, react-router-dom
    - `vendor-ui.js` — lucide-react, recharts, @uiw/react-md-editor
    - `vendor-utils.js` — axios, swr, zustand, zod, react-hook-form
  - Verificar que el build de producción es < 500KB gzip
- **Dependencias**: C-05, C-07 (frontend estable y testeado)
- **Governance**: BAJO
- **Leer antes**:
  - `frontend/vite.config.ts` (config actual)
  - `frontend/src/App.tsx` (routing — dónde poner lazy)
  - `frontend/package.json` (dependencias)

---

### [C-10] `production-deploy`
- **Estado**: `[x]` completado — archivado el 30/06/2026
- **Scope**: Preparar el proyecto para producción con Docker multi-stage, nginx, CI/CD y documentación
  - **Frontend Docker multi-stage**:
    - Stage 1: `node:20-alpine` → `npm ci && npm run build`
    - Stage 2: `nginx:alpine` → servir `dist/` con configuración optimizada
    - Configuración nginx: SPA fallback, compresión gzip, caché de assets, proxy reverso a backend
  - **Backend Docker multi-stage**:
    - Stage 1: `python:3.11-slim` → instalar dependencias
    - Stage 2: `python:3.11-slim` → solo app + dependencias (sin build tools)
  - **docker-compose.prod.yml**:
    - Backend con Gunicorn + Uvicorn workers
    - Frontend con nginx (no dev server)
    - Volumen de datos persistente
    - Red interna, solo expone puerto 80/443
  - **GitHub Actions CI**:
    - `.github/workflows/ci.yml` — lint + test en PRs
    - Jobs: backend-tests (pytest), frontend-lint (tsc --noEmit, eslint), frontend-build
    - Cache de pip y npm para builds rápidos
  - **GitHub Actions CD** (opcional):
    - Deploy automático a VPS/droplet con Docker Compose
    - Secrets: `DATABASE_URL`, `SECRET_KEY`
  - **Documentación**:
    - Actualizar `README.md` con instrucciones de producción
    - Agregar sección de arquitectura, decisión de tecnología
  - Verificar `docker compose -f docker-compose.prod.yml up` funciona end-to-end
- **Dependencias**: C-09 (frontend build optimizado), C-04 (backend limpio), C-08 (tests pasando)
- **Governance**: ALTO (toca configuración de producción, deploy)
- **Leer antes**:
  - `docker-compose.yml` (compose actual de desarrollo)
  - `backend/Dockerfile` (Dockerfile actual)
  - `frontend/Dockerfile` (Dockerfile actual)
  - `openspec/changes/project-foundation/specs/docker-deployment/spec.md`

---

## Resumen del Roadmap

| Change | Nombre | Governance | Dependencias | Prioridad |
|--------|--------|-----------|--------------|-----------|
| C-01 | `complete-foundation` | MEDIO | — | 🔴 Alta |
| C-02 | `rest-api-endpoints` | ALTO | C-01 | 🔴 Alta |
| C-03 | `metas-and-ajustes` | MEDIO | C-01 | 🔴 Alta |
| C-04 | `backend-cleanup` | MEDIO | C-01 | 🟡 Media |
| C-05 | `frontend-real-api` | ALTO | C-02 | 🔴 Alta |
| C-06 | `frontend-pages-extra` | BAJO | C-02, C-03 | 🟡 Media |
| C-07 | `frontend-testing` | BAJO | C-05 | 🟢 Baja |
| C-08 | `backend-more-tests` | BAJO | C-03 | 🟢 Baja |
| C-09 | `frontend-optimize` | BAJO | C-05, C-07 | 🟢 Baja |
| C-10 | `production-deploy` | ALTO | C-09, C-04, C-08 | 🟡 Media |

**10 changes** organizados en **5 fases**, con **4 gates de paralelismo**.

---

## Recomendación

**Arrancá por C-01** — cerrar el change `project-foundation`. Después, en paralelo:

- **Agente A**: C-02 (REST API) → C-05 (frontend real) → C-09 (optimización) → C-10 (producción)
- **Agente B**: C-03 (metas/ajustes) → C-07 (frontend tests) o C-08 (backend tests)
- **Agente C**: C-04 (backend cleanup) → C-06 (frontend pages extra)

Para arrancar: `/opsx:propose complete-foundation`
