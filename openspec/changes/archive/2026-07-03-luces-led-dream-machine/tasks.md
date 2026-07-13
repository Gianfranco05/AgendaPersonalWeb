## 1. Configuración

- [x] 1.1 Crear `infra_config.yaml` de ejemplo con secciones para Dream Machine y LEDs
- [x] 1.2 Crear modelo Pydantic `InfraConfig` para validar la configuración
- [x] 1.3 Agregar `asyncssh` y `httpx` a las dependencias del backend (pyproject.toml/requirements.txt)
- [x] 1.4 Crear `.env.example` con variables para secrets (SSH key path, LED API token)

## 2. Backend — Módulo infra

- [x] 2.1 Crear `app/infra/router.py` con endpoint `POST /api/v1/infra/shutdown`
- [x] 2.2 Crear `app/infra/service.py` con `DreamMachineService` (conexión SSH, ejecución `poweroff`)
- [x] 2.3 Crear `app/infra/led_controller.py` con `LedController` abstracto y `WledController` concreto
- [x] 2.4 Crear `app/infra/config.py` que cargue `infra_config.yaml` y exponga `InfraConfig`
- [x] 2.5 Registrar el router de infra en la app principal de FastAPI (vía `app/api/v1/router.py`)
- [x] 2.6 Manejar errores: host unreachable (502), SSH auth fail (502), LED timeout (502), missing config (503)

## 3. Script local — Shutdown hook

- [x] 3.1 Crear `shutdown_hook.py` que lea `infra_config.yaml` y ejecute apagado de LEDs + Dream Machine
- [x] 3.2 Implementar `DreamMachineSSHClient` en el script (reutilizable desde backend o standalone)
- [x] 3.3 Implementar `LedControllerFactory` que instancie el controller según tipo configurado
- [x] 3.4 Agregar logging con timestamps y nivel configurable
- [x] 3.5 Agregar flag `--force` para prueba manual sin señal de shutdown
- [x] 3.6 Crear tarea programada de Windows que ejecute `shutdown_hook.py` al evento de shutdown (`register_shutdown_task.ps1`)

## 4. Frontend — Botón en Dashboard

- [x] 4.1 Crear componente `InfraWidget` con botón "Apagar Dream Machine"
- [x] 4.2 Agregar estado de carga y feedback visual (toast success/error)
- [x] 4.3 Integrar `InfraWidget` en `DashboardPage.tsx`
- [x] 4.4 Llamar a `POST /api/v1/infra/shutdown` con Axios al hacer clic

## 5. Integración y verificación

- [x] 5.1 Tests de backend: `test_infra.py` (success, 502, 503, LED failure non-fatal)
- [x] 5.2 Tests de frontend: `InfraWidget.test.tsx` (render, loading, success, error)
- [x] 5.3 Widget mock agregado a `DashboardPage.test.tsx` para no romper tests existentes
- [x] 5.4 Documentación de setup en `scripts/README.md` + `.gitignore` actualizado
