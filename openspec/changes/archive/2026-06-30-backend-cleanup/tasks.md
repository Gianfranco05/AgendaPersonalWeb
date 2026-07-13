## 1. Verificación de estado actual

- [x] 1.1 Verificar que no existe `render_utils.py` en `backend/app/core/`
- [x] 1.2 Verificar que `slowapi` no está en `backend/requirements.txt`
- [x] 1.3 Verificar que no hay archivos basura (`=1.2.0`, `=2.116.0`, `=2.28.0`) en la raíz del backend
- [x] 1.4 Verificar que `Jinja2Templates` está configurado en `core/templates.py`
- [x] 1.5 Verificar que todas las rutas HTML usan `TemplateResponse` y no contienen HTML inline
- [x] 1.6 Verificar que todos los templates HTML existen en sus directorios correspondientes

## 2. Tests de humo para rutas HTML

- [x] 2.1 Leer el patrón de tests existente en `backend/tests/conftest.py` y `backend/tests/test_finanzas.py`
- [x] 2.2 Crear `backend/tests/test_html_routes.py` con pruebas para cada ruta HTML:
  - GET `/auth/login` y `/auth/register` — 200 sin auth
  - GET `/finanzas/`, `/finanzas/transacciones`, `/finanzas/categorias`, `/finanzas/reportes` — 302 sin auth, 200 con auth
  - GET `/anotaciones/`, `/anotaciones/nueva`, `/anotaciones/etiquetas` — 302 sin auth, 200 con auth
  - GET `/eventos/`, `/eventos/nuevo` — 302 sin auth, 200 con auth
  - GET `/metas/`, `/metas/nueva` — 302 sin auth, 200 con auth
  - GET `/ajustes/` — 302 sin auth, 200 con auth
- [x] 2.3 Ejecutar `pytest backend/tests/test_html_routes.py -v` y confirmar que todas las pruebas pasan

## 3. Documentación y cierre

- [x] 3.1 Documentar el hallazgo de que la migración Jinja2 ya estaba completa (todo el scope de templates ya implementado)
- [x] 3.2 Verificar que el archivo CHANGES.md refleja correctamente el scope real de C-04
