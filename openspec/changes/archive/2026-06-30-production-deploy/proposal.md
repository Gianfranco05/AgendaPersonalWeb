## Why

LifeOS está completo a nivel funcional (backend + frontend), pero solo se ejecuta en modo desarrollo con hot-reload y Vite dev server. No existe una configuración lista para producción: sin Docker multi-stage, sin nginx, sin CI, ni documentación de deploy. Este change sienta la infraestructura final para que cualquier persona (o el propio dueño) pueda levantar LifeOS en un VPS con un solo comando.

## What Changes

- **Frontend Docker multi-stage**: build con `node:20-alpine` + `npm ci && npm run build`, servir con `nginx:alpine` usando configuración optimizada (SPA fallback, gzip, cache headers, proxy reverso al backend)
- **Backend Docker multi-stage**: build con `python:3.11-slim` + dependencias, runtime con `python:3.11-slim` limpio (sin build tools), entrypoint con Gunicorn + Uvicorn workers en vez de `uvicorn dev`
- **docker-compose.prod.yml**: compose de producción con backend (gunicorn+uvicorn), frontend (nginx), volumen de datos persistente, red interna, solo expone puertos 80/443
- **GitHub Actions CI**: `.github/workflows/ci.yml` con jobs de lint + test en PRs, caché de pip y npm
- **Documentación**: actualizar `README.md` con instrucciones de producción, sección de arquitectura, tabla de tech stack
- **Verificación end-to-end**: `docker compose -f docker-compose.prod.yml up` debe funcionar

## Capabilities

### New Capabilities
- `docker-multi-stage`: Build de producción con Docker multi-stage para backend y frontend
- `docker-compose-prod`: Orquestación de producción con compose, red interna, volúmenes, healthchecks
- `ci-pipeline`: GitHub Actions CI con lint + test automáticos en PRs
- `deploy-docs`: Documentación de producción en README.md

### Modified Capabilities
- *(none — no existing spec changes at requirement level)*

## Impact

- **Frontend**: nuevo `Dockerfile` multi-stage, nueva configuración `nginx.conf`, `docker-compose.prod.yml`
- **Backend**: nuevo `Dockerfile` multi-stage, entrypoint modificado para Gunicorn, `Dockerfile` actual pasa a `Dockerfile.dev`
- **Raíz**: nuevo archivo `docker-compose.prod.yml`, nuevo directorio `.github/workflows/ci.yml`
- **Documentación**: `README.md` actualizado con sección de despliegue y arquitectura
- **No breaking**: el compose de desarrollo (`docker-compose.yml`) sigue funcionando exactamente igual
