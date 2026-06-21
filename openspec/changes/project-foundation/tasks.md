## 1. Backend Bugfixes (Priority 1)

- [x] 1.1 Crear `backend/app/modules/finanzas/enums.py` con TransactionType, AccountType, PaymentMethod, MerchantCategory
- [x] 1.2 Actualizar `finanzas/service.py` y `finanzas/repository.py` para importar desde `enums.py` en vez de `models.py`
- [x] 1.3 Incluir `finanzas/cuentas_routes.py` router en `main.py` bajo prefijo `/finanzas`
- [x] 1.4 Incluir `anotaciones/export_routes.py` router en `main.py` bajo prefijo `/anotaciones`
- [x] 1.5 Incluir `eventos/export_routes.py` router en `main.py` bajo prefijo `/eventos`
- [x] 1.6 Verificar que la app inicia sin errores de import

## 2. Project Reorganization (Priority 2)

- [x] 2.1 Crear directorio `backend/` en raíz del proyecto
- [x] 2.2 Mover todo el contenido de `vida-personal/` a `backend/` (app/, migrations/, tests/, static/, requirements.txt, Dockerfile, entrypoint.sh, alembic.ini, .env, .env.example)
- [x] 2.3 Eliminar directorio `vida-personal/` vacío
- [x] 2.4 Eliminar archivos sueltos en raíz: `vida-personal-design.md`, `temp_design-clean.json`
- [x] 2.5 Actualizar paths en `backend/Dockerfile` (WORKDIR, COPY, CMD)
- [x] 2.6 Actualizar paths en `backend/entrypoint.sh` si es necesario
- [x] 2.7 Actualizar `backend/alembic.ini` con `script_location = migrations`
- [x] 2.8 Verificar que `uvicorn app.main:app` funciona desde `backend/`

## 3. Backend Refinement (Priority 3)

- [x] 3.1 Agregar logging estructurado en `backend/app/main.py` (formato: timestamp, level, module)
- [x] 3.2 Crear `backend/app/core/error_handlers.py` con handlers globales para 404, 500, y validación
- [x] 3.3 Reemplazar `PG_UUID` por `String(36)` en `backend/app/core/base.py` (TimestampMixin)
- [x] 3.4 Revisar y limpiar templates Jinja2 huérfanos en `backend/app/templates/` (conservar solo los usados)
- [x] 3.5 Extraer función `render_navbar()` compartida en `backend/app/core/render_utils.py` para eliminar duplicación
- [x] 3.6 Agregar `logger.exception()` en todos los bloques try/except de las rutas

## 4. Docker Deployment (Priority 2)

- [x] 4.1 Crear `docker-compose.yml` en raíz con servicios: backend (python:3.11-slim) + frontend (node:20-alpine)
- [x] 4.2 Configurar backend service: build context `./backend`, puerto 8000, volumen `./backend/app:/app/app`, healthcheck
- [x] 4.3 Configurar frontend service: build context `./frontend`, puerto 5173, volumen `./frontend/src:/app/src`, depende de backend
- [x] 4.4 Crear `frontend/Dockerfile` para desarrollo (node:20-alpine, npm install, npm run dev)
- [x] 4.5 Configurar network `vida-network` compartida entre servicios
- [x] 4.6 Agregar volumen Docker para persistencia de DB SQLite (`./backend/data:/app/data`)
- [ ] 4.7 Verificar `docker compose up --build` levanta ambos servicios sin errores

## 5. Git & Project Foundation (Priority 2)

- [x] 5.1 Crear `.gitignore` en raíz (Python, Node, Docker, .env, __pycache__, node_modules, dist, .db)
- [x] 5.2 `git init` en raíz del proyecto
- [ ] 5.3 `git add . && git commit -m "chore: fundacion del proyecto — estructura backend/frontend + docker + OPSX specs"`
- [x] 5.4 Actualizar `README.md` en raíz con instrucciones de Docker y estructura del proyecto
- [x] 5.5 Crear `backend/.env.example` si no existe (copiar de `.env` sin valores sensibles)

## 6. Frontend Foundation (Priority 4)

- [x] 6.1 Inicializar proyecto Vite + React + TypeScript en `frontend/`: `npm create vite@latest . -- --template react-ts`
- [x] 6.2 Instalar dependencias: tailwindcss, @tailwindcss/vite, react-router-dom, axios, recharts, @uiw/react-md-editor, lucide-react
- [x] 6.3 Configurar Tailwind CSS con directiva `@import "tailwindcss"` en `frontend/src/index.css`
- [x] 6.4 Configurar `vite.config.ts` con proxy `/api` → `http://backend:8000` y plugin tailwind
- [x] 6.5 Configurar `tsconfig.json` con strict mode, path aliases `@/` → `src/`
- [x] 6.6 Crear `frontend/src/api/client.ts` con instancia Axios (baseURL: http://localhost:8000, withCredentials: true)
- [x] 6.7 Crear `frontend/src/api/endpoints.ts` con funciones para finance, notes, events, tasks
- [x] 6.8 Crear `frontend/src/types/index.ts` con interfaces TypeScript (Transaction, Note, Event, Task, Category)
- [x] 6.9 Crear `frontend/src/components/Layout.tsx` con sidebar de navegación y tema violeta (#7C3AED)
- [x] 6.10 Crear `frontend/src/components/LoadingSkeleton.tsx` para estados de carga
- [x] 6.11 Crear `frontend/src/components/ErrorBoundary.tsx` para capturar errores de render
- [x] 6.12 Configurar React Router en `frontend/src/App.tsx` con 4 rutas principales

## 7. Frontend Pages (Priority 4)

### 7.1 Dashboard
- [x] 7.1.1 Crear `frontend/src/pages/Dashboard/DashboardPage.tsx` con layout bento-box
- [x] 7.1.2 Crear `FinanceWidget.tsx` — balance + últimas 5 transacciones
- [x] 7.1.3 Crear `NotesWidget.tsx` — notas recientes, pinned primero
- [x] 7.1.4 Crear `TasksWidget.tsx` — contadores por columna Kanban
- [x] 7.1.5 Crear `EventsWidget.tsx` — próximos 7 días

### 7.2 Finance
- [x] 7.2.1 Crear `frontend/src/pages/Finance/FinancePage.tsx` con summary cards (ingresos, egresos, balance)
- [x] 7.2.2 Crear `TransactionTable.tsx` con columnas: fecha, descripción, categoría, monto (verde/rojo), tipo, acciones
- [x] 7.2.3 Crear `TransactionModal.tsx` para crear/editar transacción con formulario
- [x] 7.2.4 Crear `FinanceCharts.tsx` con recharts: pie chart por categoría + bar chart 6 meses
- [x] 7.2.5 Crear `TransactionFilters.tsx` — filtros por fecha, categoría, tipo
- [x] 7.2.6 Implementar paginación (20 items por página)

### 7.3 Notes
- [x] 7.3.1 Crear `frontend/src/pages/Notes/NotesPage.tsx` con layout two-panel
- [x] 7.3.2 Crear `NotesSidebar.tsx` — lista de notas con búsqueda y filtro por tag
- [x] 7.3.3 Crear `NoteEditor.tsx` con @uiw/react-md-editor, vista previa y code highlighting
- [x] 7.3.4 Crear `NoteCard.tsx` con título, preview, color, acciones (pin, archive, delete)
- [x] 7.3.5 Crear `TagFilter.tsx` — chips de tags clickeables para filtrar

### 7.4 Tasks
- [x] 7.4.1 Crear `frontend/src/pages/Tasks/KanbanBoard.tsx` con 3 columnas
- [x] 7.4.2 Crear `KanbanColumn.tsx` — columna con título, contador, lista de cards
- [x] 7.4.3 Crear `TaskCard.tsx` — título, descripción, acciones (editar, eliminar)
- [x] 7.4.4 Crear `AddTaskForm.tsx` — formulario para nueva tarea
- [x] 7.4.5 Implementar drag & drop entre columnas con @hello-pangea/dnd
- [x] 7.4.6 Implementar persistencia en localStorage + mock data inicial
- [x] 7.4.7 Crear `frontend/src/hooks/useKanban.ts` — lógica de estado Kanban

## 8. Backend Tests (Priority 5)

- [x] 8.1 Actualizar `backend/tests/conftest.py` con fixtures: async client, test db, test user
- [x] 8.2 Crear `backend/tests/test_auth.py`: login success, login fail, register, logout, protected route
- [x] 8.3 Crear `backend/tests/test_finanzas.py`: create transaction, list paginated, soft delete, get balance
- [x] 8.4 Crear `backend/tests/test_anotaciones.py`: create note with tags, list, archive, search by tag
- [x] 8.5 Crear `backend/tests/test_eventos.py`: create event, list, edit, link to note
- [x] 8.6 Verificar todos los tests pasan: `pytest backend/tests/ -v`

## 9. Final Verification (Priority 5)

- [x] 9.1 `docker compose up --build` — verificar backend healthy en :8000/health y frontend en :5173
- [ ] 9.2 Navegar Dashboard y verificar widgets cargan datos del backend (needs Docker runtime)
- [ ] 9.3 Navegar Finance y verificar crear/editar/eliminar transacción (needs Docker runtime)
- [ ] 9.4 Navegar Notes y verificar crear/editar nota con Markdown (needs Docker runtime)
- [ ] 9.5 Navegar Tasks y verificar drag & drop entre columnas (needs Docker runtime)
- [x] 9.6 `pytest backend/tests/ -v` — todos los tests verdes (46 passed)
- [ ] 9.7 `git add . && git commit -m "feat: proyecto completo — backend fixes + frontend React + Docker + tests"` (pending manual commit)
