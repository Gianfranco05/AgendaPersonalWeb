## Why

El backend de LifeOS fue migrado de HTML inline a Jinja2 templates durante C-01 (project-foundation), pero quedan residuos: archivos basura en la raíz del backend, dependencias sin uso en requirements.txt, y código huérfano. Este change limpia esos residuos y verifica que todo siga funcionando después de la migración.

Además, se documenta el estado actual de la migración a Jinja2 para confirmar que la refactorización está completa y que no hay regresiones en las rutas HTML.

## What Changes

- Verificar que todas las rutas HTML existentes usan `TemplateResponse` y no contienen HTML inline
- Verificar que no existen archivos basura (`=1.2.0`, `=2.116.0`, `=2.28.0`) en la raíz del backend
- Verificar que `slowapi` no está en `requirements.txt`
- Verificar que `render_utils.py` no tiene código huérfano o no existe
- Verificar que `Jinja2Templates` está correctamente configurado en `core/templates.py`
- Ejecutar tests de humo en rutas HTML para confirmar que responden 200
- Documentar el estado post-limpiieza

## Capabilities

### New Capabilities
- Ninguna — este change no introduce nuevas capacidades, solo limpia y verifica

### Modified Capabilities
- Ninguna — no hay cambios en requerimientos a nivel spec

## Impact

- **Código afectado**: No se modifica código funcional. Solo se eliminan archivos basura y dependencias muertas.
- **Dependencias**: Se verifica que `requirementS.txt` no tiene entradas huérfanas.
- **Tests**: Se agregan tests de humo para rutas HTML (verificar 200 en cada endpoint).
- **Riesgo**: Mínimo — no se tocan rutas, modelos, ni lógica de negocio.
