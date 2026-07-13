## 1. Monitoreo y Error Tracking — Parte A

- [x] 1.1 Agregar `sentry-sdk` y `prometheus-client` a `backend/requirements.txt`
- [x] 1.2 Crear `backend/app/core/sentry.py` con inicialización de Sentry (DSN desde env, environment desde env, traces_sample_rate configurable)
- [x] 1.3 Integrar Sentry en `backend/app/main.py` dentro del lifespan
- [x] 1.4 Agregar `@sentry_sdk.monitor` (o middleware) para capturar excepciones no manejadas en FastAPI
- [x] 1.5 Inicializar Sentry en frontend: agregar `@sentry/react` y `@sentry/vite-plugin` al `package.json`
- [x] 1.6 Configurar Sentry en `src/main.tsx` con `VITE_SENTRY_DSN`, condicional a que exista la variable
- [x] 1.7 Crear `backend/app/core/logging_config.py` con JSON logging usando `python-json-logger`, nivel configurable por `LOG_LEVEL`
- [x] 1.8 Crear middleware de correlation ID en `backend/app/core/correlation.py` usando `contextvars` que genera UUID si no viene `X-Correlation-ID` header
- [x] 1.9 Crear middleware de request logging en `backend/app/core/request_logging.py` que registre method, path, status, duration_ms, correlation_id
- [x] 1.10 Registrar middlewares en `backend/app/main.py` (correlation → request_logging → metrics)
- [x] 1.11 Crear middleware Prometheus en `backend/app/core/metrics.py` con contadores `http_requests_total`, histograma `http_request_duration_seconds`, gauge `http_requests_in_progress`, excluyendo `/metrics`
- [x] 1.12 Agregar endpoint `/metrics` en `backend/app/main.py` que exporte métricas Prometheus
- [x] 1.13 Reemplazar `/health` existente por `/livez` (solo process alive, sin DB) y `/readyz` (verifica DB)
- [x] 1.14 Reemplazar `logging.basicConfig` en `backend/app/main.py` por el JSON logging config, integrando correlation ID

## 2. Seguridad y Nginx — Parte B

- [x] 2.1 Agregar security headers en `frontend/nginx.conf`: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy`, `Content-Security-Policy`
- [x] 2.2 Agregar rate limiting en `frontend/nginx.conf`: `limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m` para `/auth/` y `zone=api:10m rate=100r/m` para `/api/`
- [x] 2.3 Agregar `client_max_body_size 10M` en `frontend/nginx.conf`
- [x] 2.4 Agregar configuración de HTTPS en `frontend/nginx.conf`: server block en puerto 443 con `ssl_certificate`, `ssl_certificate_key`, TLS 1.2/1.3, secure ciphers, redirect HTTP→HTTPS en server block 80
- [x] 2.5 Agregar proxy_pass para `/livez` y `/readyz` en nginx.conf
- [x] 2.6 Crear documentación en `docs/ssl-setup.md` con pasos manuales para Let's Encrypt + certbot (prerequisitos: dominio, puerto 80/443 público, certbot install, certonly, renovación automática)

## 3. Configuración de Servidor — Parte C

- [x] 3.1 Crear `backend/gunicorn.conf.py` con: workers dinámicos `(2 * cpu_count) + 1`, timeout 120s, graceful_timeout 30s, preload_app, y loggers configurados para JSON logging
- [x] 3.2 Modificar `backend/entrypoint.sh` para usar `gunicorn -c gunicorn.conf.py` en vez de flags inline
- [x] 3.3 Crear `backend/.dockerignore` excluyendo `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.git/`, `.env`, `.pytest_cache/`, `tests/`, `.vscode/`
- [x] 3.4 Crear `frontend/.dockerignore` excluyendo `node_modules/`, `.git/`, `.env`, `.env.local`, `dist/`, `.vscode/`, `tests/`, `__tests__/`, `*.md`
- [x] 3.5 Agregar `restart: unless-stopped` a todos los servicios en `docker-compose.prod.yml`
- [x] 3.6 Actualizar healthchecks en `docker-compose.prod.yml` para usar `/livez` (backend) y mantener `/` (frontend)

## 4. Notificaciones y Alertas

- [x] 4.1 Crear `backend/app/core/notifier.py` con función `send_telegram_alert(message)` usando `httpx` para POST a Telegram Bot API, con graceful degradation si faltan `TELEGRAM_BOT_TOKEN` o `TELEGRAM_CHAT_ID`
- [x] 4.2 Implementar cooldown de 5 minutos en `notifier.py` para evitar notificaciones duplicadas (dict in-memory con timestamps por tipo de evento)
- [x] 4.3 Integrar notificador en healthcheck: cuando `/readyz` retorna 503, enviar alerta a Telegram (solo si pasó cooldown)
- [x] 4.4 Agregar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` a las environment variables del backend en `docker-compose.prod.yml`

## 5. Cierre

- [x] 5.1 Verificar que todos los tests existentes sigan pasando
- [ ] 5.2 Revisar que Sentry funcione: probar excepción controlada y ver en dashboard
- [ ] 5.3 Verificar `/metrics`, `/livez`, `/readyz` endpoints responden correctamente
- [ ] 5.4 Confirmar que los JSON logs incluyen correlation_id
- [ ] 5.5 Build de docker-compose.prod.yml sin errores
