## Why

La app corre en producción con Docker pero carece de capas esenciales de producción: no hay monitoreo, error tracking, HTTPS, rate limiting, ni configuración de servidor profesional. Si la app tira un 500, nadie se entera. Si alguien ataca `/auth/` por fuerza bruta, no hay protección. Este change transforma el stack de servidor de "anda en mi máquina" a "producción real".

## What Changes

- Agregar Sentry SDK para error tracking en backend y frontend
- Middleware de request logging en FastAPI (método, path, status, duración)
- Endpoint `/metrics` con Prometheus
- Endpoints `/livez` y `/readyz` separados
- JSON logging estructurado
- Correlation ID por request (uuid trazable)
- HTTPS con Let's Encrypt + certbot en nginx
- Security headers en nginx (CSP, HSTS, X-Frame-Options, etc.)
- Rate limiting en nginx para `/auth/` y `/api/`
- `client_max_body_size` explícito
- `gunicorn.conf.py` con workers dinámicos, timeout y graceful-timeout
- `.dockerignore` para backend y frontend
- `restart: unless-stopped` en docker-compose.prod.yml
- Sistema de notificaciones mínimo vía webhook de Telegram

## Capabilities

### New Capabilities
- `sentry-error-tracking`: Integración de Sentry en backend (FastAPI) y frontend (React) con captura de excepciones y breadcrumbs
- `structured-logging`: JSON logging estructurado con correlation ID por request
- `prometheus-metrics`: Endpoint `/metrics` con métricas de request count, duración y errores
- `healthchecks`: Endpoints `/livez` (liveness) y `/readyz` (readiness) separados con lógica diferenciada
- `request-logging`: Middleware que loguea método, path, status, duración y correlation ID
- `nginx-security`: HTTPS, security headers, rate limiting y límites de body en nginx
- `gunicorn-config`: Archivo `gunicorn.conf.py` con workers dinámicos, timeout, graceful-timeout y preload
- `docker-optimization`: `.dockerignore` para backend y frontend, restart policy en compose
- `notifications-alerts`: Sistema de notificaciones vía webhook Telegram para alertas de salud del servidor

### Modified Capabilities
*Ninguna — todas las capabilities son nuevas.*

## Impact

- **Backend**: Nuevas dependencias (sentry-sdk, prometheus-client), nuevos middlewares, nuevo endpoint `/metrics`, nuevos endpoints de healthcheck, nuevo archivo `gunicorn.conf.py`, nuevo `.dockerignore`
- **Frontend**: Nueva dependencia (sentry), inicialización de Sentry en entry point
- **Nginx**: Nueva configuración de HTTPS, security headers, rate limiting — requiere certbot o documentación de setup manual
- **Docker**: Nuevo `.dockerignore` en backend/ y frontend/, modificación de `docker-compose.prod.yml` con restart policy
- **Sin breaking changes**: todos los cambios son aditivos, no rompen funcionalidad existente
