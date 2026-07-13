## Context

LifeOS necesita controlar dispositivos de infraestructura local (Ubiquiti Dream Machine y luces LED) tanto desde un script de shutdown de la PC como desde un endpoint REST del backend. La Dream Machine expone API REST de UniFi y soporta SSH. Las luces LED pueden ser controladas vía HTTP (WiFi smart plugs, API de Yeelight/WLED, o similar).

## Goals / Non-Goals

**Goals:**
- Script local (`shutdown_hook.py`) que apague LEDs y Dream Machine al recibir señal de shutdown de Windows
- Endpoint `POST /api/v1/infra/shutdown` que apague la Dream Machine desde el backend de LifeOS
- Botón "Apagar Dream Machine" en el frontend (Dashboard)
- Configuración centralizada en `infra_config.yaml` para credenciales y endpoints

**Non-Goals:**
- No se implementa encendido programado (WoL queda para otro change)
- No se implementa monitoreo de estado de dispositivos
- No se implementa autenticación de usuario para el endpoint (app local, un solo usuario)
- No se implementa cola de tareas ni reintentos complejos

## Decisions

| Decisión | Opción elegida | Alternativas | Razón |
|----------|---------------|--------------|-------|
| Control Dream Machine | SSH vía `asyncssh` | API REST UniFi | SSH es más confiable para shutdown; no depende de tokens de sesión UniFi que expiran |
| Control LEDs | HTTP vía `httpx` (WLED API) | SSH, GPIO directo | WLED/Kasa/TP-Link tienen API HTTP simple; no requiere drivers de hardware |
| Ejecución local | Tarea programada Windows | Servicio Windows | Más simple de instalar/configurar; `shutdown.exe` puede ejecutar script como acción |
| Puerto backend | FastAPI sub-app `/api/v1/infra` | Router directo | Consistente con estructura existente del backend |
| Config | YAML local (`infra_config.yaml`) | Env vars, DB | Las credenciales de red viven en el host, no en el contenedor; YAML es legible y versionable con .env separado para secrets |
| Frontend trigger | Widget en Dashboard | Modal/Página separada | Mínimo impacto visual; un botón alcanza para esta acción |
| Shutdown local | Named pipe + script polling | Gancho en Windows事件 | Named pipe permite que el backend notifique al script local sin depender de eventos del SO |

## Risks / Trade-offs

- [**Credenciales en disco**] → `infra_config.yaml` con `.gitignore`; usar variables de entorno para passwords sensibles (SSH key, API token LEDs)
- [**SSH a Dream Machine desde contenedor**] → El script de shutdown corre en el HOST (no en Docker). El endpoint del backend puede hacer SSH desde el contenedor si la red Docker reacha la Dream Machine, o delegar al script local vía named pipe.
- [**WLED/API LEDs puede cambiar**] → Abstraer en un `LedController` con interfaz `def turn_off()` y factory por tipo de LED
- [**Tarea programada no siempre corre al shutdown real**] → Probar con evento `EventID 1074` (shutdown) + timeout de gracia; alternativa: script polling que detecta falta de heartbeat del backend

## Open Questions

- ¿Qué marca/modelo de LEDs tiene el usuario? (WLED, Yeelight, Kasa, WiFi plug genérico) — afecta el adapter concreto
- ¿La Dream Machine está en la misma red Docker que el backend? Si no, el endpoint necesita ruteo especial
