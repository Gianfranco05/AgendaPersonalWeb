# Vida Personal

Sistema web para gestionar tu vida personal: finanzas, anotaciones, eventos y metas.

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 (async)
- **Database**: SQLite (desarrollo) / PostgreSQL (producción/Docker)
- **Frontend**: HTML inline con TailwindCSS CDN + Alpine.js
- **Auth**: JWT en HTTP-only cookie + bcrypt

## Levantar con Docker (recomendado)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado.

```bash
# 1. Clonar el repo y entrar al directorio
cd vida-personal

# 2. Configurar la clave secreta (opcional, hay un default para dev)
#    En producción, generá una clave real:
#    python -c "import secrets; print(secrets.token_hex(32))"
export SECRET_KEY=tu-clave-secreta   # Linux/Mac
$env:SECRET_KEY="tu-clave-secreta"   # Windows PowerShell

# 3. Construir y levantar
docker compose up --build
```

La app queda disponible en **http://localhost:8000**

El primer `docker compose up` crea la base de datos PostgreSQL y aplica las migraciones automáticamente. Los datos persisten en volúmenes Docker entre reinicios.

### Comandos Docker utiles

```bash
# Levantar en segundo plano
docker compose up -d --build

# Ver logs
docker compose logs -f app

# Detener
docker compose down

# Detener y borrar datos (DB incluida)
docker compose down -v
```

---

## Desarrollo local con SQLite

Si preferis correr sin Docker, la app usa SQLite por defecto.

### Requisitos

- Python 3.11+

### Setup

```bash
# 1. Crear entorno virtual
cd vida-personal
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Copiar y editar variables de entorno
cp .env.example .env
# El .env default usa SQLite, no requiere configuracion adicional

# 4. Aplicar migraciones
alembic upgrade head

# 5. Iniciar el servidor
uvicorn app.main:app --reload
```

Abrir **http://localhost:8000**

### Cambiar a PostgreSQL en local

Editar `.env`:

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/vida_personal
```

Luego crear la base de datos y correr las migraciones:

```bash
# Crear DB en PostgreSQL
psql -U postgres -c "CREATE DATABASE vida_personal;"

# Aplicar migraciones
alembic upgrade head
```

> Si ya tenes datos en SQLite y querés indicarle a Alembic que la migracion inicial ya fue aplicada:
> ```bash
> alembic stamp 001_initial
> ```

---

## Estructura del Proyecto

```
vida-personal/
├── app/
│   ├── core/            # security, dependencies, base ORM
│   ├── modules/
│   │   ├── auth/        # login, register, logout
│   │   ├── finanzas/    # transacciones, categorias, reportes
│   │   ├── anotaciones/ # notas y tags
│   │   ├── eventos/     # calendario
│   │   └── metas/       # metas y habitos
│   ├── config.py        # settings via pydantic-settings
│   ├── database.py      # engine async SQLAlchemy
│   └── main.py          # app FastAPI + routers
├── migrations/          # Alembic
│   └── versions/
│       └── 001_initial.py
├── static/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh        # migraciones + uvicorn
└── requirements.txt
```

## Variables de entorno

| Variable | Default | Descripcion |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./vida_personal.db` | URL de conexion a la base de datos |
| `SECRET_KEY` | `change-this-in-production` | Clave para firmar los JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Expiración del token (24hs) |
| `DEBUG` | `true` | Modo debug (deshabilitar en prod) |

## Configurar Google Calendar (opcional)

Para conectar Google Calendar desde `/ajustes/`:

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un proyecto (o usar uno existente)
3. Ir a **APIs y Servicios → Credenciales**
4. Crear credencial: **ID de cliente de OAuth 2.0** → tipo **Aplicación web**
5. En "Orígenes autorizados": `http://localhost:8000`
6. En "URI de redireccionamiento autorizados": `http://localhost:8000/ajustes/google/callback`
7. Copiar el **ID de cliente** y **Secreto** al `.env`:

```env
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-secreto
GOOGLE_REDIRECT_URI=http://localhost:8000/ajustes/google/callback
```

8. Activar la API: **APIs y Servicios → Biblioteca → Google Calendar API → Habilitar**
9. Reiniciar la app — en `/ajustes/` aparece el botón "Conectar"

> Para producción, cambiar los URIs a tu dominio HTTPS y actualizar `GOOGLE_REDIRECT_URI`.

## Comandos Alembic

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Crear una nueva migracion
alembic revision --autogenerate -m "descripcion"

# Ver historial de migraciones
alembic history

# Revertir ultima migracion
alembic downgrade -1

# Ver version actual aplicada
alembic current
```
