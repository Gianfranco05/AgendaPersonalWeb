import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import require_superuser

from app.infra.config import get_infra_config
from app.infra.led_controller import create_led_controller
from app.infra.service import DreamMachineService, DreamMachineShutdownError

logger = logging.getLogger(__name__)

# Apaga hardware del operador por SSH: sin esto, cualquiera (incluso sin sesion)
# podia dispararlo en cuanto existiera infra_config.yaml. Solo un superusuario.
router = APIRouter(prefix="/infra", tags=["infra"], dependencies=[Depends(require_superuser)])


@router.post("/shutdown")
async def shutdown_dream_machine():
    config = get_infra_config()

    if not config.dream_machine:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dream Machine not configured",
        )

    if config.leds.devices:
        for device in config.leds.devices:
            try:
                controller = create_led_controller(
                    config.leds.type,
                    host=device.host,
                    port=device.port,
                    api_token=device.api_token,
                )
                await controller.turn_off()
                logger.info("Turned off LED device: %s", device.name)
            except Exception as e:
                logger.warning("Failed to turn off LED device %s: %s", device.name, e)

    service = DreamMachineService(config.dream_machine)
    try:
        await service.shutdown()
        return {"status": "ok", "message": "Shutdown command sent to Dream Machine"}
    except DreamMachineShutdownError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to Dream Machine: {e}",
        )
