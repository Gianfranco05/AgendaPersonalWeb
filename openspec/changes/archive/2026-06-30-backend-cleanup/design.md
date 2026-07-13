## Context

El backend de LifeOS fue migrado de HTML inline a Jinja2 templates durante la fundación del proyecto (C-01). La configuración actual es:

- `backend/app/core/templates.py` — instancia `Jinja2Templates` apuntando a `backend/app/templates/`
- `backend/app/templates/` — 18 templates HTML organizados por módulo (finanzas, anotaciones, eventos, metas, ajustes, auth)
- `backend/app/templates/base.html` — layout común con navbar, sidebar, footer
- Todos los `routes.py` ya usan `templates.TemplateResponse()` — no hay HTML inline residual
- `render_utils.py` no existe (fue eliminado o nunca fue creado)
- `slowapi` no está en `requirements.txt`
- No hay archivos basura (`=1.2.0`, `=2.116.0`, `=2.28.0`) en la raíz del backend

Este change verifica que el estado actual es correcto y agrega tests de humo para confirmar que las rutas HTML responden 200.

## Goals / Non-Goals

**Goals:**
- Verificar que no existe HTML inline residual en ningún `routes.py`
- Verificar que no existen archivos basura en la raíz del backend
- Verificar que `slowapi` no está en `requirements.txt`
- Verificar que `render_utils.py` no existe o está limpio
- Agregar tests de integración que confirmen que cada ruta HTML responde HTTP 200
- Documentar el estado post-verificación

**Non-Goals:**
- NO modificar la estructura de templates existente
- NO cambiar la lógica de rutas ni de negocio
- NO agregar nuevas funcionalidades
- NO modificar el modelo de datos

## Decisions

| # | Decisión | Alternativas | Por qué esta |
|---|----------|-------------|-------------|
| 1 | **No crear specs nuevas** | Crear spec para "template-rendering" | El comportamiento de renderizado de templates ya está cubierto por los specs existentes de backend-refinement. No hay cambios en requerimientos. |
| 2 | **Tests de humo con httpx.AsyncClient** | pytest + TestClient síncrono | AsyncClient es más realista, ya está configurado en el conftest existente, y no requiere dependencias adicionales. |
| 3 | **Verificación manual como task de validación** | Automatizar con script | La verificación de archivos basura y dependencias es más confiable haciéndola manualmente con comandos shell. Los tests de humo automatizan lo que se puede automatizar. |

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| Alguna ruta HTML podría estar rota sin que lo notemos | Los tests de humo cubren todas las rutas HTML registradas en `main.py`. Cada ruta se prueba con GET esperando 200 o 302 (redirect a login si no autenticado). |
| Archivos basura podrían estar en subdirectorios, no en raíz | La búsqueda se hace con `Get-ChildItem -Recurse` para cubrir todo el árbol del backend. |

## Migration Plan

1. **Task 1 — Verificar estado actual**: Confirmar que no hay HTML inline, no hay archivos basura, no hay `slowapi`, no hay `render_utils.py`
2. **Task 2 — Escribir tests de humo**: Crear `backend/tests/test_html_routes.py` con httpx.AsyncClient probando cada ruta HTML
3. **Task 3 — Ejecutar tests**: `pytest backend/tests/test_html_routes.py -v` — verificar que todas pasan
4. **Task 4 — Commit**: Documentar el estado post-limpiieza

## Findings During Implementation

### Bug: List comprehension en Jinja2 template
- **Archivo**: `backend/app/templates/anotaciones/formulario.html:75`
- **Error**: `jinja2.exceptions.TemplateSyntaxError: expected token ',', got 'for'`
- **Causa**: La línea `{% set note_tag_ids = [t.id for t in (note.tags if note and note.tags else [])] %}` usa sintaxis de list comprehension de Python, que Jinja2 no soporta dentro de `{% set %}`.
- **Fix**: Reemplazado por `{% set note_tag_ids = (note.tags if note and note.tags else []) | map(attribute='id') | list %}`
- **Impacto**: El template `anotaciones/formulario.html` fallaba con 500 Internal Server Error al acceder a `GET /anotaciones/nueva` con un usuario autenticado. Ninguna ruta sin autenticación se veía afectada porque el redirect ocurría antes de renderizar el template.

### Import de UserPreference en ajustes/routes.py
- Se verificó que `backend/app/modules/ajustes/routes.py` línea 18 ya tiene `from app.modules.ajustes.models import UserPreference`. El import existe y es correcto.

## Open Questions

- Ninguna — el alcance está completamente definido y no hay ambigüedad técnica.
