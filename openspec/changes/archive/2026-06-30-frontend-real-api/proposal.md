## Why

El frontend de LifeOS opera actualmente con `MOCK_ENABLED = true` hardcodeado y rutas de API antiguas (`/finanzas/api/`, `/anotaciones/api/`, `/eventos/api/`). El backend real ya está implementado con endpoints bajo `/api/v1/`. Esta change conecta el frontend al backend real, reemplazando datos mock por datos verdaderos de finanzas, notas y eventos.

## What Changes

- Reemplazar `MOCK_ENABLED = true` hardcodeado por variable de entorno `VITE_MOCK_ENABLED` (default `false`)
- Corregir todas las URLs en `endpoints.ts`: migrar de `/finanzas/api/*` → `/api/v1/finance/*`, `/anotaciones/api/*` → `/api/v1/notes/*`, `/eventos/api/*` → `/api/v1/events/*`
- Corregir `authApi.ts`: migrar de `/auth/api/*` → `/api/v1/auth/*`
- Configurar `client.ts` con `baseURL` desde `VITE_API_URL` o el proxy de Vite
- Verificar que el proxy de Vite en `vite.config.ts` cubra `/api/v1/` correctamente
- Arreglar en `LoginPage.tsx` el link `/auth/register` que redirige a 404 (cambiarlo a `#` o eliminarlo, dado que no hay registro público en app local de 1 usuario)
- Agregar manejo de errores de red en los hooks SWR (`useFinance.ts`, `useNotes.ts`, `useEvents.ts`)
- Tasks/Kanban: se mantiene con localStorage + mock data (fuera del alcance de esta change)
- Tests: smoke test de conexión al backend y login flow end-to-end

## Capabilities

### New Capabilities
- `real-api-connection`: Configuración de Axios client con baseURL dinámica, manejo global de errores HTTP, y proxy de Vite para `/api/v1/`
- `real-api-finance`: Conexión real de los módulos Finance (summary + transactions) al backend
- `real-api-notes`: Conexión real del módulo Notes al backend
- `real-api-events`: Conexión real del módulo Events al backend
- `real-api-auth`: Autenticación real (login/logout/me) contra el backend

### Modified Capabilities
_(No hay specs existentes — es la primera vez que se crean)_

## Impact

- `frontend/src/api/endpoints.ts` — rutas de API, eliminación de mock data
- `frontend/src/api/client.ts` — baseURL y configuración de Axios
- `frontend/src/api/authApi.ts` — rutas de auth
- `frontend/vite.config.ts` — rutas del proxy
- `frontend/src/hooks/useFinance.ts` — manejo de errores SWR
- `frontend/src/hooks/useNotes.ts` — manejo de errores SWR
- `frontend/src/hooks/useEvents.ts` — manejo de errores SWR
- `frontend/src/features/auth/LoginPage.tsx` — link de registro roto
- Archivos `.env` nuevos o modificados con `VITE_MOCK_ENABLED` y `VITE_API_URL`
- Tasks/Kanban queda fuera del alcance
