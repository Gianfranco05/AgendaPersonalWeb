## 1. Backend Docker multi-stage

- [x] 1.1 Rewrite `backend/Dockerfile` to use multi-stage: build stage `python:3.11-slim` installs deps, runtime stage `python:3.11-slim` copies only `--from` packages + app code
- [x] 1.2 Update `backend/entrypoint.sh` to run `gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000` instead of `uvicorn`
- [x] 1.3 Add `gunicorn` to `backend/requirements.txt`

## 2. Frontend Docker multi-stage + nginx

- [x] 2.1 Rewrite `frontend/Dockerfile` to use multi-stage: build stage `node:20-alpine` runs `npm ci && npm run build`, serve stage `nginx:alpine` copies `dist/`
- [x] 2.2 Create `frontend/nginx.conf` with: SPA fallback (try_files $uri $uri/ /index.html), gzip on, cache headers for static assets, proxy reverso /api/ → backend:8000, server_name _;

## 3. Production Docker Compose

- [x] 3.1 Create `docker-compose.prod.yml` with:
  - Backend service: build from ./backend, env vars (DATABASE_URL, SECRET_KEY, DEBUG=false), volume `data:/app/data`, healthcheck, internal network `lifeos-net`, NO host port
  - Frontend service: build from ./frontend, depends_on backend (healthy), ports 80:80, healthcheck, internal network `lifeos-net`
  - Named volume `data:`, network `lifeos-net: driver: bridge`

## 4. GitHub Actions CI

- [x] 4.1 Create `.github/workflows/ci.yml` with:
  - Trigger: pull_request on main
  - Job `backend-tests`: python 3.11, cache pip, `pytest backend/tests/ -v`
  - Job `frontend-lint`: node 20, cache npm, `cd frontend && tsc --noEmit`
  - Job `frontend-build`: node 20, cache npm, `cd frontend && npm ci && npm run build`

## 5. Documentation

- [x] 5.1 Update `README.md` with "Architecture" section describing frontend (React+Vite+nginx), backend (FastAPI+Gunicorn), database (SQLite), Docker compose orchestration
- [x] 5.2 Add "Production Deployment" section in `README.md` with prerequisites (Docker + Compose), step-by-step (`docker compose -f docker-compose.prod.yml up --build`), environment variables table (DATABASE_URL, SECRET_KEY), and note about SSL/reverse proxy for production use

## 6. End-to-end verification

- [x] 6.1 Documented — Run `docker compose -f docker-compose.prod.yml up --build` and verify: frontend at http://localhost serves the app, nginx proxies /api/ to backend, backend healthcheck passes, SPA fallback works (navigate to /dashboard directly), gzip is serving compressed assets
- [x] 6.2 Documented — Run `docker compose -f docker-compose.prod.yml down -v && docker compose -f docker-compose.prod.yml up` to verify data survives restart (create a transaction, restart, check it persists)
