## Why

Al apagar la PC, el usuario debe apagar manualmente las luces LED del escritorio/oficina y la Ubiquiti Dream Machine. Esto es tedioso y se olvida frecuentemente. Se necesita una automatización que ejecute ambos apagados al shutdown del sistema, más un endpoint en el backend de LifeOS para triggerear el apagado de la Dream Machine bajo demanda.

## What Changes

- **Script local de shutdown**: script Python que se ejecuta al apagar la PC (vía tarea programada de Windows o servicio) y apaga:
  - Luces LED del escritorio/oficina
  - Ubiquiti Dream Machine (vía SSH o API)
- **Endpoint en backend LifeOS**: `POST /api/v1/infra/shutdown` que ejecuta el apagado de la Dream Machine desde la app web
- **Configuración centralizada**: archivo de configuración YAML/JSON para credenciales de Dream Machine y tipo/endpoint de LEDs
- **Trigger manual desde frontend**: botón en el dashboard de LifeOS para apagar Dream Machine

## Capabilities

### New Capabilities
- `pc-shutdown-automation`: Script local que se ejecuta al shutdown de la PC, apaga LEDs y Dream Machine
- `infra-control`: Endpoint REST en el backend para controlar dispositivos de infraestructura (Dream Machine, LEDs)

### Modified Capabilities
<!-- No existing specs are modified — this is a new module -->

## Impact

- **Backend**: nuevo módulo `app/infra/` con router, service y modelos Pydantic; dependencias: `asyncssh` o `paramiko` para SSH, `httpx` para HTTP
- **Frontend**: nuevo botón/widget en el Dashboard para "Apagar Dream Machine"
- **Infraestructura**: script Python + tarea programada de Windows para shutdown hook; archivo `infra_config.yaml` en el host
- **Seguridad**: credenciales de red y API de LEDs almacenadas localmente; el endpoint debe validar que no sea accesible desde afuera en producción
