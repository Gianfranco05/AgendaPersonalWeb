## 1. Configuración base

- [x] 1.1 Crear `.env` en `frontend/` con `VITE_MOCK_ENABLED=false` y `VITE_API_URL` (vacío por defecto)
- [x] 1.2 Agregar entrada `/api/v1` al proxy de Vite en `vite.config.ts` apuntando a `VITE_PROXY_TARGET`
- [x] 1.3 Configurar Axios `client.ts`: leer `VITE_API_URL` para `baseURL`, agregar interceptor 401 que redirige a `/login`

## 2. Migración de endpoints

- [x] 2.1 Reemplazar `MOCK_ENABLED = true` hardcodeado por `import.meta.env.VITE_MOCK_ENABLED === 'true'` en `endpoints.ts`
- [x] 2.2 Migrar URLs de Finance: `/finanzas/api/summary` → `/api/v1/finance/summary`, `/finanzas/api/transactions` → `/api/v1/finance/transactions`, `/finanzas/api/categories` → `/api/v1/finance/categories`
- [x] 2.3 Migrar URLs de Notes: `/anotaciones/api/notes` → `/api/v1/notes`, `/anotaciones/api/tags` → `/api/v1/tags`
- [x] 2.4 Migrar URLs de Events: `/eventos/api/events` → `/api/v1/events`
- [x] 2.5 Migrar URLs de Auth en `authApi.ts`: `/auth/api/login` → `/api/v1/auth/login`, `/auth/api/logout` → `/api/v1/auth/logout`, `/auth/api/me` → `/api/v1/auth/me`

## 3. Manejo de errores en hooks

- [x] 3.1 Agregar `onError` global en SWR o wrapper `useApiSWR` que muestre toast/notificación ante errores de red
- [x] 3.2 Validar que `useFinance.ts` expone errores correctamente (no solo data undefined)
- [x] 3.3 Validar que `useNotes.ts` expone errores correctamente
- [x] 3.4 Validar que `useEvents.ts` expone errores correctamente

## 4. Auth y login

- [x] 4.1 Verificar que `authStore.ts` funciona correctamente con las nuevas rutas de `authApi.ts`
- [x] 4.2 Arreglar link `/auth/register` en `LoginPage.tsx`: reemplazar por texto sin link o eliminarlo

## 5. Tests

- [x] 5.1 Smoke test: verificar que el cliente Axios se conecta al backend y responde
- [x] 5.2 Smoke test: login flow end-to-end (login → obtener usuario → logout)

## 6. Verificación final

- [x] 6.1 Verificar que FinancePage carga transacciones reales (no mock)
- [x] 6.2 Verificar que NotesPage carga notas reales
- [x] 6.3 Verificar que Dashboard muestra widgets con datos reales
- [x] 6.4 Verificar que Tasks/Kanban sigue funcionando con localStorage (sin cambios)
