## Why

El proyecto Vida Personal (LifeOS) tiene un backend FastAPI funcional al 90% pero con bugs críticos y deuda técnica acumulada. No tiene frontend React (solo HTML inline), no tiene tests, no tiene control de versiones, y la estructura de carpetas no separa backend de frontend. Este change aborda TODO el espectro: desde bugs que rompen la app hasta la fundación completa del frontend React + Docker.

## What Changes

- **BUGFIX**: Crear `finanzas/enums.py` con TransactionType, AccountType, PaymentMethod, MerchantCategory (rompen FinanzasService y TransactionRepository)
- **BUGFIX**: Incluir 3 routers faltantes en main.py (cuentas_routes, export_routes anotaciones, export_routes eventos)
- **REORGANIZACIÓN**: Mover todo el backend FastAPI a `backend/` y crear estructura `frontend/` para React + Vite
- **DOCKER**: Docker Compose único que levanta backend (FastAPI) + frontend (Vite dev server) con un solo `docker compose up`
- **CLEANUP**: Eliminar templates Jinja2 huérfanos, arreglar TimestampMixin
- **GIT**: Inicializar repositorio con .gitignore completo
- **OPSX**: Crear specs formales para cada módulo del backend y frontend
- **FRONTEND**: Inicializar React + TypeScript + Vite + Tailwind con páginas: Dashboard, Finance, Notes, Tasks
- **TESTS**: Suite de tests para backend (auth, finanzas, anotaciones, eventos) con pytest + httpx
- **CALIDAD**: Logging estructurado, manejo de errores consistente, loaders en frontend

## Capabilities

### New Capabilities
- `project-structure`: Reorganización de carpetas en backend/ y frontend/ con raíz limpia
- `docker-deployment`: Docker Compose unificado para dev y prod con healthchecks
- `backend-bugfixes`: Corrección de enums faltantes y routers no incluidos
- `backend-refinement`: Logging, manejo de errores consistente, limpieza de código huérfano
- `backend-testing`: Suite de tests con pytest + httpx para todos los módulos
- `frontend-foundation`: React + TypeScript + Vite + Tailwind inicial con routing y consumo de API
- `frontend-dashboard`: Página Dashboard con widgets de finanzas, notas y tareas
- `frontend-finance`: Página Finance con tabla de transacciones, gráficos y modal crear/editar
- `frontend-notes`: Página Notes con sidebar + editor Markdown + code snippets
- `frontend-tasks`: Página Tasks con tablero Kanban (Pendiente / En Proceso / Completado)

### Modified Capabilities
- *(ninguno — no hay specs existentes en openspec/specs/)*

## Impact

- **Estructura**: Todo el código se mueve a `backend/` (Python) y `frontend/` (React+TS). Raíz del repo contiene solo configs Docker, README, y openspec/
- **Backend**: Se modifican `main.py`, `finanzas/service.py`, `finanzas/repository.py`, se crea `finanzas/enums.py`. Se agregan 3 routers. Se agrega logging.
- **Frontend**: Creación completa desde cero con Vite + React + TS + Tailwind. Sin impacto en código existente.
- **Docker**: Nuevo `docker-compose.yml` en raíz con servicios `backend` y `frontend`. El `Dockerfile` existente se adapta.
- **Tests**: Nuevos archivos en `backend/tests/`. Sin impacto en producción.
- **Opspec**: Nuevos specs en `openspec/specs/` para cada capability listada arriba.
