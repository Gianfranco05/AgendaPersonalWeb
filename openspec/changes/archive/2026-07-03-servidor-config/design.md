## Context

LifeOS corre en Docker Compose con backend FastAPI (Gunicorn/Uvicorn), frontend React/Vite y nginx como reverse proxy. Actualmente no hay monitoreo, error tracking, HTTPS, rate limiting, ni configuración de servidor profesional. Todos los gaps identificados requieren cambios en backend, frontend, nginx y Docker.

## Goals / Non-Goals

**Goals:**
- Agregar error tracking con Sentry en backend y frontend
- Implementar logging estructurado JSON con correlation ID
- Exponer métricas Prometheus y healthchecks diferenciados
- Configurar nginx con HTTPS, security headers y rate limiting
- Profesionalizar configuración de Gunicorn y Docker
- Implementar sistema de alertas mínimo por Telegram

**Non-Goals:**
- No se implementa autenticación compleja (single user)
- No se agrega base de datos adicional
- No se implementa un dashboard de monitoreo (solo endpoints expuestos)
- No se configura Prometheus server ni Grafana (solo el endpoint)

## Decisions

### DSN management via env vars
Sentry DSN, Telegram tokens, y otras credenciales van en variables de entorno, no en el repositorio. Backend usa `SENTRY_DSN`, frontend usa `VITE_SENTRY_DSN`. La app funciona sin ellas (graceful degradation).

### Prometheus metrics via middleware
En lugar de decorar cada endpoint, se usa un middleware Starlette que instrumenta automáticamente todas las rutas, excluyendo `/metrics` para evitar recursión. Esto mantiene el código existente limpio.

### Correlation ID via middleware + contextvars
La librería `contextvars` de Python (stdlib) propaga el correlation ID sin pasar parámetros explícitos. El middleware genera/extrae el UUID y lo almacena en un contextvar. El logger accede a esa variable para incluirla en cada línea JSON.

### Gunicorn workers dinámicos
`(2 * CPU_COUNT) + 1` es la fórmula estándar para workers Gunicorn en apps I/O bound. Se puede override con `GUNICORN_WORKERS`. Se usa `preload_app` para compartir memoria.

### Nginx rate limiting por IP
Se usa la directiva `limit_req_zone` de nginx con clave `$binary_remote_addr` para rate limiting a nivel IP. Límites diferenciados: 10 req/min para `/auth/` y 100 req/min para `/api/`.

### HTTPS deferido a documentación
Configurar Let's Encrypt requiere dominio + puertos públicos. La configuración de nginx incluye el setup SSL (listen 443, cert paths, ciphers) pero la obtención real del certificado queda documentada como paso manual. Esto evita falsa seguridad de "lo configuré pero no probé".

### Alertas vía Telegram
Un módulo Python liviano que usa `httpx` para POST al API de Telegram. Se ejecuta desde un healthcheck loop (script separado o cron). Implementa cooldown de 5 minutos para evitar spam.

### JSON logging con python-json-logger
Se usa la librería `python-json-logger` para formatear los logs como JSON. Gunicorn se configura para usar el logger de Python (no stdout raw) para mantener el formato unificado.

## Architecture
```
                          ┌──────────────┐
                          │   Frontend    │
                          │  (React/Vite) │
                          │  + Sentry SDK │
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │    nginx      │← HTTPS, Security Headers, Rate Limit
                          │  (proxy_pass) │
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │   Backend     │
                          │  (FastAPI)    │
                          │  + Sentry SDK │
                          │  + Metrics     │← /metrics Prometheus
                          │  + Healthcheck │← /livez, /readyz
                          │  + JSON Logs  │← Correlation ID
                          │  + Gunicorn   │← gunicorn.conf.py
                          └──────┬───────┘
                                 │
                          ┌──────▼───────┐
                          │  PostgreSQL   │
                          └──────────────┘

Notificaciones (Telegram) → script Python separado o healthcheck loop
```

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| Sentry SDK puede afectar performance | `traces_sample_rate` configurable; arrancar con 0.1 y ajustar |
| Rate limiting puede bloquear usuario legítimo | Limites generosos (10/min auth, 100/min api); el usuario es único |
| Let's Encrypt certs expiran cada 90 días | Documentar renovación automática con certbot + cron/systemd timer |
| Telegram bot token expuesto en env vars | Solo en el servidor, no en el repo; rotación manual si es necesario |
| Demasiado scope para un change | Los gaps CRÍTICOS (1-4, Sentry + HTTPS) se implementan primero como prioridad |

## Migration Plan

1. **Fase 1 (CRÍTICOS)**: Sentry backend + frontend, HTTPS nginx config, healthchecks, restart policy
2. **Fase 2 (ALTOS)**: Rate limiting, security headers, Gunicorn config, .dockerignore
3. **Fase 3 (MEDIOS)**: JSON logging, Prometheus metrics, correlation ID, notificaciones Telegram

Rollback: Las configuraciones de nginx se revierten con el backup del archivo. Los middlewares nuevos son aditivos — quitarlos no afecta funcionalidad existente. Las dependencias nuevas (sentry-sdk, prometheus-client) se revierten con `pip uninstall`.

## Open Questions

- Usar certbot manual vs proxy-pass con acme.sh?
- Usar httpx o requests para el webhook de Telegram? (preferimos httpx por async)
- Dónde correr el healthcheck loop: script Python aparte o integrado en la app?
