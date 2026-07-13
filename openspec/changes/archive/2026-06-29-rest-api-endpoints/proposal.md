## Why

Los módulos del backend (finanzas, anotaciones, eventos, metas, ajustes) ya tienen endpoints REST JSON bajo `/api/v1/` creados durante C-01, pero carecen de documentación formal del contrato de API, metadatos de paginación en listados, y soft-delete en transacciones financieras. Este change formaliza el API contract completo, unifica criterios de respuesta, y agrega las capacidades faltantes para que el frontend React pueda consumir los endpoints de forma predecible.

## What Changes

- **Agregar metadatos de paginación** a `GET /api/v1/finance/transactions` (total, page, page_size)
- **Soft-delete** en `DELETE /api/v1/finance/transactions/{id}` (marcar como eliminada, no borrar físicamente)
- **Endpoint faltante** `GET /api/v1/finance/categories` — ya existe, documentar
- **Refinar schemas de respuesta** para que todos los endpoints devuelvan consistentemente `created_at`/`updated_at` ISO 8601
- **Documentar el API contract completo** en spec formal
- No se modifican rutas HTML existentes ni modelos de datos

## Capabilities

### New Capabilities

- `rest-api-endpoints`: Contrato REST JSON unificado bajo `/api/v1/` para los 5 módulos — finanzas (summary, transactions CRUD con paginación y soft-delete, categories), anotaciones (notes CRUD con filtro por tag/búsqueda, tags), eventos (events CRUD con rango de fechas), metas (goals list+create, habit checkin), ajustes (settings get+update). Define schemas, códigos de respuesta, filtros y formato de fechas.

### Modified Capabilities

- *(Ninguna — no hay spec previo que modificar; es la primera formalización del API contract)*

## Impact

- `backend/app/api/v1/finance.py`: agregar paginación y soft-delete
- `backend/app/api/v1/notes.py`: revisar schemas inline (NoteCreateRequest, NoteUpdateRequest) para usar los del módulo
- `backend/app/main.py`: ya incluye `api_router` bajo `/api/v1` — sin cambios
- No se tocan modelos, migraciones, ni rutas HTML
