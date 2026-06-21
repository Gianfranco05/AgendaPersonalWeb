## Context

El proyecto Vida Personal (LifeOS) tiene un backend FastAPI funcional con 6 módulos (auth, finanzas, anotaciones, eventos, metas, ajustes) renderizando HTML server-side. El código funciona pero tiene bugs, deuda técnica, y carece completamente de frontend moderno y tests. No tiene control de versiones. La base de datos (SQLite/PostgreSQL) y migraciones Alembic están correctamente configuradas.

## Goals / Non-Goals

**Goals:**
- Reparar bugs críticos: enums faltantes en finanzas, routers no incluidos
- Reorganizar el proyecto en `backend/` (FastAPI) y `frontend/` (React+Vite)
- Dockerizar: `docker compose up` levanta todo
- Inicializar git con .gitignore completo
- Crear specs OPSX para todos los módulos
- Inicializar frontend React + TypeScript + Vite + Tailwind con 4 páginas
- Escribir suite de tests backend con pytest + httpx
- Agregar logging estructurado y manejo de errores consistente

**Non-Goals:**
- NO modificar la API REST existente (solo agregar routers faltantes)
- NO cambiar el modelo de datos ni migraciones
- NO implementar auth en el frontend (single-user local)
- NO hacer deploy a producción (solo desarrollo local con Docker)

## Decisions

| # | Decisión | Alternativas | Por qué esta |
|---|----------|-------------|-------------|
| 1 | **Estructura `backend/` + `frontend/`** en raíz | Monorepo con packages/ o todo junto | Separación clara de stacks, cada uno con su Dockerfile, independencia de builds |
| 2 | **Frontend: React + Vite + Tailwind** (no Next.js) | Next.js, Remix, Svelte | Vite es más simple para SPA local, sin SSR necesario. Tailwind v4 con CDN inicial, luego build |
| 3 | **Frontend: React Router para routing** | TanStack Router, Next.js file-based | Simple, conocido, suficiente para 4 páginas |
| 4 | **Frontend: Axios para HTTP** | fetch nativo, TanStack Query | Axios da interceptors, mejor DX para manejo de errores |
| 5 | **Frontend: recharts para gráficos** | Chart.js, visx, Nivo | recharts es React-native, simple, buena documentación |
| 6 | **Frontend: @uiw/react-md-editor** para Markdown | EasyMDE, Tiptap, lexical | Ligero, integración React directa, soporte code highlighting |
| 7 | **Frontend: lucide-react para íconos** | Heroicons, Phosphor | Tree-shakeable, amplio set, diseño limpio |
| 8 | **Docker: un solo compose con backend + frontend** | Compose separados, kubernetes | Simpleza para dev local, single command up |
| 9 | **Backend: logging con `logging` stdlib + formato estructurado** | loguru, structlog | Sin dependencias extra, suficiente para debug local |
| 10 | **Backend: errores con `JSONResponse` consistente** | Exception handlers globales | Simple, predecible, sin magic |
| 11 | **Backend: enums en `finanzas/enums.py`** (archivo separado) | Definirlos en models.py | Separación de responsabilidades, models solo define tablas |
| 12 | **Tests: pytest + httpx.AsyncClient + SQLite in-memory** | pytest-asyncio con TestClient | AsyncClient es más realista, SQLite in-memory es rápido |
| 13 | **OPSX: specs por capability, no por módulo existente** | Un spec por módulo backend | Los specs describen capacidades del sistema, no estructura de archivos |

## Arquitectura Final

```
proyecto/
├── docker-compose.yml          # Unificado: backend + frontend
├── .gitignore
├── README.md
├── openspec/                   # OPSX (existente)
│   ├── config.yaml
│   ├── specs/                  # Specs creados en este change
│   └── changes/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── core/               # security, dependencies, base
│   │   ├── modules/            # auth, finanzas, anotaciones, eventos, metas, ajustes
│   │   └── templates/          # Solo base.html si se usa
│   ├── migrations/
│   ├── tests/
│   └── static/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                # Axios client + endpoints
│       ├── components/         # UI components compartidos
│       ├── hooks/              # Custom hooks
│       ├── pages/
│       │   ├── Dashboard/
│       │   ├── Finance/
│       │   ├── Notes/
│       │   └── Tasks/
│       └── types/              # TypeScript interfaces
└── scripts/                    # (opcional)
```

## Frontend Routing

```
/               → Dashboard (widgets: finance summary, recent notes, tasks preview)
/finances      → FinancePage (tabla transacciones + gráficos + modal CRUD)
/notes         → NotesPage (sidebar tags + editor Markdown + code snippets)
/tasks         → KanbanBoard (Pendiente / En Proceso / Completado, mock data inicial)
```

## API Endpoints (backend existente + ajustes)

| Método | Ruta | Usado por Frontend |
|--------|------|-------------------|
| `GET` | `/finanzas/` | Dashboard ← redirigido desde backend |
| `GET` | `/api/v1/finance/summary` | Dashboard widget, FinancePage |
| `GET` | `/api/v1/finance/transactions` | FinancePage tabla |
| `POST` | `/api/v1/finance/transactions` | FinancePage crear |
| `PUT` | `/api/v1/finance/transactions/{id}` | FinancePage editar |
| `DELETE` | `/api/v1/finance/transactions/{id}` | FinancePage eliminar |
| `GET` | `/api/v1/notes` | Dashboard widget, NotesPage |
| `POST` | `/api/v1/notes` | NotesPage crear |
| `PUT` | `/api/v1/notes/{id}` | NotesPage editar |
| `DELETE` | `/api/v1/notes/{id}` | NotesPage eliminar |
| `GET` | `/anotaciones/api/tags` | NotesPage tags |
| `GET` | `/eventos/api/events` | Dashboard eventos próximos |
| `GET` | `/metas/` | Dashboard metas activas |

**Nota**: Los endpoints actuales del backend retornan HTML. Para el frontend React, necesitamos endpoints JSON. Se agregan rutas `/api/v1/` en el backend sin modificar las rutas HTML existentes.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| El backend actual no tiene endpoints JSON — solo renderiza HTML | Agregar rutas `/api/v1/` con `response_class=JSONResponse` sin tocar las rutas HTML existentes. Coexistencia pacífica. |
| El frontend React requiere Node.js en Docker | Usar imagen `node:20-alpine` para frontend dev server, `python:3.11-slim` para backend. Compose orquesta ambos. |
| La migración de carpetas puede romper imports relativos | Actualizar todos los imports de `app.` a mantenerlos igual (el backend se mueve entero, la estructura interna no cambia). Ajustar paths en Dockerfile. |
| Los tests no existen, escribir desde cero lleva tiempo | Priorizar tests de smoke (conexión DB, healthcheck) y CRUD básico. Cobertura incremental. |
| La app no tiene auth real (JWT en cookie HTTP-only) | El frontend SPA no necesita manejar auth — el backend maneja cookies automáticamente. Axios con `withCredentials: true`. |
| TimestampMixin usa PG_UUID incompatible con SQLite | Reemplazar `PG_UUID` por `String(36)` o eliminar el mixin y usar definiciones inline como ya hacen los modelos. |

## Migration Plan

1. **Paso 1**: Crear `backend/finanzas/enums.py` (sin mover nada aún)
2. **Paso 2**: Agregar routers faltantes en `main.py`
3. **Paso 3**: Mover todo el contenido de `vida-personal/` a `backend/`
4. **Paso 4**: Actualizar Dockerfile paths
5. **Paso 5**: Crear estructura `frontend/` con Vite + React
6. **Paso 6**: Crear `docker-compose.yml` unificado en raíz
7. **Paso 7**: Probar `docker compose up`
8. **Paso 8**: Escribir tests
9. **Paso 9**: `git init` + primer commit

**Rollback**: Si algo falla, mover `backend/` de vuelta a `vida-personal/`. Las migraciones de DB no se tocan, los datos persisten en volúmenes Docker.

## Open Questions

- [ ] ¿Las rutas `/api/v1/` deben ser réplicas exactas de las rutas HTML existentes o endpoints simplificados?
  - **Decisión preliminar**: Endpoints simplificados que devuelven JSON puro (sin HTML wrapper)
- [ ] ¿El frontend debe tener hot reload en Docker?
  - **Decisión preliminar**: Sí, mount de volumen `./frontend/src:/app/src` para development
- [ ] ¿Mantenemos el backend sirviendo HTML en `/` o delegamos todo al frontend?
  - **Decisión preliminar**: El backend sigue en `:8000` con su UI HTML. El frontend en `:5173` para desarrollo. Docker compose expone ambos puertos.
