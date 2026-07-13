## Context

LifeOS tiene un `docker-compose.yml` funcional para desarrollo con hot-reload, volúmenes de código fuente, y Vite dev server. Para producción se necesita:

- Imágenes Docker optimizadas (multi-stage, sin build tools en runtime)
- Servidor web real (nginx) para el frontend con SPA fallback, gzip, caché
- Servidor WSGI real (Gunicorn + Uvicorn workers) para el backend
- Red interna aislada, solo puertos 80/443 expuestos
- CI pipeline que ejecute lint + tests automáticamente en cada PR
- Documentación clara para que cualquier desarrollador pueda hacer deploy

## Goals / Non-Goals

**Goals:**
- Frontend Docker multi-stage: build con node:20-alpine → servir con nginx:alpine
- Backend Docker multi-stage: build con python:3.11-slim → runtime python:3.11-slim
- `docker-compose.prod.yml` con Gunicorn + nginx + red interna
- `.github/workflows/ci.yml` con lint + test en PRs
- `README.md` actualizado con instrucciones de producción y arquitectura
- Verificar que `docker compose -f docker-compose.prod.yml up` funciona end-to-end

**Non-Goals:**
- HTTPS/SSL (se puede agregar después con reverse proxy tipo Caddy/Traefik)
- CI/CD con deploy automático (solo CI por ahora; CD se documenta como opcional)
- Migración de base de datos (SQLite sigue igual, usar migraciones Alembic existentes)
- Escalado horizontal (app monousuario, no lo necesita)

## Decisions

| Decisión | Opción elegida | Alternativa | Razón |
|----------|---------------|-------------|-------|
| Servidor frontend en prod | nginx:alpine | Servir con node (express), Caddy | nginx:alpine es ~5MB, maduro, configuración SPA simple, compresión nativa |
| Servidor backend en prod | Gunicorn + Uvicorn workers | Solo Uvicorn, Hypercorn | Gunicorn maneja process management y sigterm correctamente; Uvicorn workers dan performance ASGI |
| Composición producción | Archivo separado `docker-compose.prod.yml` | Mismo compose con profiles/overrides | Archivo separado es más explícito, evita confusiones, se puede tener ambos coexistiendo |
| Red interna | bridge network personalizada | network mode host, default bridge | Aislamiento: frontend SOLO ve backend, no hay exposición innecesaria |
| CI runner | GitHub Actions | GitLab CI, Jenkins | El repo está en GitHub, es gratis, integración nativa |
| Caché CI | pip cache + npm cache con action/cache | Sin caché | Reduce builds de ~3min a ~30s en promedio |

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| El multi-stage build del backend duplica espacio en disco durante build | Docker cache layer sharing minimiza el impacto; el output final es solo runtime |
| Config de nginx incorrecta rompe SPA routing | Test con curl a rutas `/login`, `/dashboard` después del build |
| Gunicorn no lee bien variables de entorno de docker-compose | Usar archivo `.env` en el compose o pasar variables explicitamente en `environment:` |
| CI falla por diferencias entre entorno local y CI | CI usa las mismas imágenes Docker; matrix de Python/node versions fijas |
| `docker-compose.prod.yml` crece y se vuelve difícil de mantener | Separar config común y de prod es explícito; documentar cada sección |

## Migration Plan

1. Crear `backend/Dockerfile` multi-stage (build → runtime)
2. Crear `frontend/Dockerfile` multi-stage (build → nginx)
3. Crear `frontend/nginx.conf` con SPA fallback, gzip, caché, proxy reverso
4. Crear `docker-compose.prod.yml`
5. Crear `.github/workflows/ci.yml`
6. Actualizar `README.md` con sección de producción
7. Verificar end-to-end: `docker compose -f docker-compose.prod.yml up`

## Open Questions

- ¿Usar variable de entorno para `SERVER_NAME` en nginx o hardcodear `localhost`? → Decisión: usar `server_name _;` (catch-all) para flexibilidad, el deployer configura su dominio externamente.
- ¿Incluir GitHub Actions CD opcional (deploy automático a VPS)? → Incluir como workflow separado `deploy.yml` comentado/opcional para no complicar el CI principal.
