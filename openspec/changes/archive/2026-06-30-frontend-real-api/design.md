## Context

El frontend usa `MOCK_ENABLED = true` hardcodeado y URLs estilo `/finanzas/api/` que no existen en el backend real. El backend FastAPI expone rutas bajo `/api/v1/`. No hay manejo de errores de red en los hooks SWR, y el link `/auth/register` en LoginPage rompe porque no hay ruta de registro.

## Goals / Non-Goals

**Goals:**
- Conectar Finance, Notes y Events al backend real via endpoints `/api/v1/...`
- Reemplazar mock flag hardcodeado por env var `VITE_MOCK_ENABLED`
- Manejo consistente de errores HTTP y de red en hooks SWR
- Auth funcional contra backend real (login/logout/me)
- Proxy de Vite configurado para `/api/v1/`
- Arreglar link roto de registro en LoginPage

**Non-Goals:**
- No se toca el módulo Tasks/Kanban (sigue con localStorage + mock data)
- No se modifican tipos de datos ni schemas del backend
- No se agrega registro de usuarios (app local de 1 usuario)
- No se agrega testing de componentes ni integración (solo smoke tests de conexión)

## Decisions

### 1. Estrategia de migración de URLs

- **Decisión**: Cambiar todas las URLs en `endpoints.ts` y `authApi.ts` a `/api/v1/{recurso}/...`
- **Motivo**: El backend real usa `/api/v1/`. Reflejar las rutas reales hace que el código sea autodocumentado y evita doble mapeo.
- **Alternativa considerada**: Mantener rutas viejas con reglas de reescritura en el proxy de Vite. Se descartó porque agrega complejidad invisible y rompe la claridad del código.
- **Mapeo**: `/finanzas/api/summary` → `/api/v1/finance/summary`, `/finanzas/api/transactions` → `/api/v1/finance/transactions`, `/anotaciones/api/notes` → `/api/v1/notes`, `/eventos/api/events` → `/api/v1/events`, `/anotaciones/api/tags` → `/api/v1/tags`, `/finanzas/api/categories` → `/api/v1/finance/categories`, `/auth/api/*` → `/api/v1/auth/*`

### 2. Proxy de Vite

- **Decisión**: Agregar entrada `/api/v1` al proxy apuntando al backend, manteniendo las entradas existentes como fallback
- **Motivo**: El proxy actual tiene entradas por módulo (`/finanzas`, `/anotaciones`, etc.) que ya no se van a usar. Se conservan por si hacen falta en desarrollo. La nueva entrada `/api/v1` cubre todas las rutas reales.

### 3. Env vars

- **Decisión**: `VITE_MOCK_ENABLED` (default `false`) en lugar de la constante hardcodeada
- **Motivo**: Permite switchear a mock data para desarrollo offline sin tocar código
- **Archivo**: `.env` en `frontend/` con `VITE_MOCK_ENABLED=false` y `VITE_API_URL` (opcional, si no se usa proxy)

### 4. Manejo de errores en SWR

- **Decisión**: Crear un wrapper `useSWRApi` o usar `onError` de SWR global para capturar errores de red y mostrar toast/notificación
- **Motivo**: SWR no maneja errores de red por defecto más allá del estado `error`. Se necesita feedback visual para el usuario.
- **Implementación**: Hook `useApiSWR` que envuelve `useSWR` con `shouldRetryOnError: true` y un callback global de error.

### 5. Auth store

- **Decisión**: El `login()` de Zustand (`authStore`) ya llama a `authApi.login()`. Solo se corrigen las rutas en `authApi.ts`.
- **Motivo**: La capa de estado global ya está bien separada; solo fallan las URLs.

### 6. Link de registro

- **Decisión**: Cambiar `<a href="/auth/register">` a `<span>` sin link, dado que no hay registro público
- **Motivo**: El backend no expone `/api/v1/auth/register` porque es app local mono-usuario. Ocultar el link evita confusión.

## Risks / Trade-offs

- **Riesgo**: El backend puede tener diferencias en la forma exacta de los campos (snake_case vs camelCase) → **Mitigación**: Axios intercambia JSON sin transform, pero si el backend usa snake_case y el frontend camelCase en los tipos, hay que mapear. Verificar durante implementación.
- **Riesgo**: Errores 401 no manejados pueden dejar al usuario en un estado inconsistente → **Mitigación**: Interceptor de Axios que redirige a login si detecta 401.
- **Riesgo**: `VITE_API_URL` sin proxy requiere CORS configurado en el backend → **Mitigación**: Por defecto se usa el proxy de Vite. `VITE_API_URL` es optativo.
