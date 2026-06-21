# Vida Personal (LifeOS)

Aplicación de gestión personal — finanzas, notas, eventos, metas y más.

## Estructura del Proyecto

```
├── docker-compose.yml       # Orquestación de servicios
├── backend/                 # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py          # Punto de entrada
│   │   ├── core/            # Seguridad, handlers, utilidades
│   │   └── modules/         # auth, finanzas, anotaciones, eventos, metas, ajustes
│   ├── migrations/          # Alembic
│   ├── tests/               # pytest
│   └── Dockerfile
├── frontend/                # React + Vite + TypeScript + Tailwind
│   ├── src/
│   ├── public/
│   └── Dockerfile
└── openspec/                # Especificaciones del proyecto
```

## Quickstart con Docker

```bash
# Levantar todos los servicios
docker compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## Desarrollo Local

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
