# Can_cen

Aplicación de gestión personal — finanzas, anotaciones, eventos, metas y más.

Frontend React + Backend FastAPI, orquestados con Docker Compose.

---

## 📋 Estado del Proyecto

| Componente | Estado |
|-----------|--------|
| Backend tests | ✅ 148 pasando, 2 esperados (CORS) |
| Frontend tests | ✅ 39 pasando |
| Docker dev | ✅ `docker compose up --build` |
| Docker prod | ✅ `docker compose -f docker-compose.prod.yml up --build` |

---

## 🔰 Primera vez — Desde 0

### Opción A: Docker (recomendado — más fácil)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# 1. Clonar
git clone <repo-url>
cd vida-personal

# 2. Levantar todo (backend + frontend + base de datos)
docker compose up --build
```

- **Frontend** (nginx — build producción): http://localhost:5173
- **Backend** (FastAPI — hot-reload): http://localhost:8000
- **Health check**: http://localhost:8000/livez (liveness) y http://localhost:8000/readyz (readiness + DB)
- **Docs API**: http://localhost:8000/docs

> 💡 **Frontend con hot-reload**: si estás desarrollando el frontend y querés hot-reload, correlo localmente con `npm run dev` y el backend en Docker. El proxy de Vite redirige las llamadas al backend automáticamente.

El backend crea la base de datos SQLite automáticamente al arrancar. No requiere migraciones manuales.

Para detener: `Ctrl+C` o `docker compose down`

### Opción B: Local sin Docker

#### Backend

```bash
# 1. Crear entorno virtual e instalar dependencias
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt

# 2. Copiar variables de entorno (o editar backend/.env)
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac

# 3. Iniciar servidor
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

El frontend se conecta al backend via proxy de Vite (configurado en `vite.config.ts`). Todo debería andar sin configuración adicional.

---

## 🔁 Uso diario

Ya con el proyecto clonado y las dependencias instaladas, esto es lo único que necesitás:

### Con Docker (si ya lo usaste antes)

```bash
# Arrancar
docker compose up

# Si cambiaste código o dependencias, rebuildear
docker compose up --build

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

### Sin Docker

```bash
# Terminal 1 — Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### Scripts útiles

```bash
# Backend — Tests (SQLite local, rápidos)
cd backend && python -m pytest tests/ -v

# Frontend — Tests unitarios + componentes
cd frontend && npm run test

# Frontend — Tests con coverage
cd frontend && npm run test:coverage

# Frontend — Build producción (TypeScript check + Vite build)
cd frontend && npm run build
```

---

## 🧱 Stack

| Capa       | Tecnología |
|------------|-----------|
| Frontend   | React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4 |
| Backend    | FastAPI + SQLAlchemy 2.0 (async) + SQLite |
| Auth       | JWT en HTTP-only cookie + bcrypt |
| Testing    | pytest (backend) / Vitest + RTL (frontend) |
| Infra      | Docker Compose, nginx (producción) |

---

## 🏗️ Estructura

```
vida-personal/
├── docker-compose.yml          # Desarrollo (hot-reload)
├── docker-compose.prod.yml     # Producción (nginx + gunicorn)
├── backend/
│   ├── app/
│   │   ├── main.py             # Punto de entrada FastAPI
│   │   ├── core/               # Seguridad, middlewares, utilidades
│   │   ├── modules/            # auth, finanzas, anotaciones, eventos, metas, ajustes
│   │   └── api/v1/             # API REST JSON unificada
│   ├── migrations/             # Alembic
│   ├── tests/                  # pytest (150 tests)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                # Cliente Axios + endpoints
│   │   ├── components/         # Componentes compartidos
│   │   ├── hooks/              # Custom hooks (SWR, Kanban, etc.)
│   │   ├── pages/              # Páginas (Dashboard, Finance, Notes, etc.)
│   │   └── context/            # Auth context
│   ├── tests/                  # Tests end-to-end
│   ├── Dockerfile              # Multi-stage (node → nginx)
│   └── nginx.conf              # SPA fallback + proxy reverso
└── openspec/                   # Especificaciones del proyecto
    ├── config.yaml
    ├── specs/                  # Specs canónicos por capacidad
    └── changes/archive/        # Changes completados
```

---

## 🌐 Endpoints

| Ruta | Descripción |
|------|-----------|
| `GET /livez` · `GET /readyz` | Liveness / readiness (readyz incluye chequeo de DB) |
| `/auth/*` | Login, register, logout (HTML + API) |
| `/finanzas/*` | Transacciones, categorías, reportes |
| `/anotaciones/*` | Notas con Markdown, tags |
| `/eventos/*` | Calendario de eventos |
| `/metas/*` | Metas y hábitos con check-in |
| `/ajustes/*` | Preferencias del usuario |
| `/api/v1/*` | API REST JSON (consumida por frontend React) |

---

## 🔐 Variables de Entorno

### Backend (`backend/.env`)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./vida_personal.db` | Conexión a DB |
| `SECRET_KEY` | *(requerido en prod)* | Clave para firmar JWT |
| `DEBUG` | `true` | Modo debug |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Expiración del token (24hs) |
| `GOOGLE_CLIENT_ID` | *(opcional)* | Google Calendar OAuth |

### Frontend (`frontend/.env`)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VITE_MOCK_ENABLED` | `false` | Usar mock data en lugar de API real |
| `VITE_API_URL` | *(vacío = proxy)* | URL base de la API (producción) |

---

## 🐳 Producción

### 1. Configurar variables de entorno

```bash
cp .env.prod.example .env
# Editar .env y generar un SECRET_KEY fuerte:
python -c "import secrets; print(secrets.token_hex(32))"
```

`SECRET_KEY` es **obligatorio** (32+ caracteres); con `ENVIRONMENT=production` el backend
se niega a arrancar con una clave insegura o con `DEBUG=true`.

### 2a. HTTP (funciona out-of-the-box, sin certificados)

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

La app queda en `http://localhost` con nginx (gunicorn en el backend, migraciones Alembic
automáticas al arrancar) sirviendo el frontend estático y proxy reverso al backend.

### 2b. HTTPS (deploy real con dominio + Let's Encrypt)

```bash
# Requiere DOMAIN en .env y certificados en /etc/letsencrypt/live/$DOMAIN/ (ver docs/ssl-setup.md)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.tls.yml up --build -d
```

El override expone el 443, monta `/etc/letsencrypt` y renderiza `frontend/nginx.tls.conf`
sustituyendo `${DOMAIN}`. El puerto 80 redirige a HTTPS con HSTS habilitado.

---

## 🧪 Tests

```bash
# Backend — todos los tests
cd backend && python -m pytest tests/ -v

# Backend — solo tests de un módulo
cd backend && python -m pytest tests/test_finanzas.py -v

# Frontend — tests unitarios
cd frontend && npm run test

# Frontend — tests con coverage
cd frontend && npm run test:coverage
```

---

## License

Copyright (c) 2026 Gianfranco Canciani. Este proyecto **no es open source**: se publica bajo una licencia propia de uso no comercial y sin distribución. El texto completo, que es el que vale legalmente, está en [`LICENSE`](LICENSE).

- **Permitido**: ver, descargar, ejecutar localmente, estudiar y **modificar** el código, **solo** para uso personal, educativo o de investigación y sin fines comerciales. También podés compartir el enlace a este repositorio.
- **No permitido sin autorización expresa y por escrito del autor**: redistribuir o compartir copias (originales o modificadas) con terceros, publicar forks o versiones modificadas como proyectos propios, vender el código, sublicenciarlo, ofrecerlo como SaaS o servicio (pago o gratuito), incorporarlo en productos comerciales o usarlo con cualquier fin comercial.
- **Modificar no habilita a distribuir**: podés cambiar el código para tu propio uso, pero eso no te da permiso para publicar, compartir ni usar comercialmente tus versiones modificadas.

Para usos comerciales, distribución a terceros o cualquier uso no incluido en la licencia, contactá al autor a través de su perfil de GitHub: [github.com/Gianfranco05](https://github.com/Gianfranco05).
