# Shutdown Hook Scripts

## shutdown_hook.py
Script Python que apaga LEDs y Dream Machine al shutdown de la PC.

### Uso manual
```bash
python scripts/shutdown_hook.py --force
```

### Flags
- `--force`: Ejecuta el shutdown de dispositivos
- `--config PATH`: Ruta al `infra_config.yaml`
- `--log-level LEVEL`: DEBUG | INFO | WARNING | ERROR

### Instalación como tarea programada
Ejecutar como **Administrador**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_shutdown_task.ps1
```

Esto registra dos tareas:
1. `LifeOS-ShutdownHook` — se ejecuta al inicio del sistema
2. `LifeOS-ShutdownHook-Event` — se ejecuta al detectar EventID 1074 (shutdown)

### Requisitos
```bash
pip install asyncssh httpx pyyaml
```
