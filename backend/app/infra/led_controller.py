from abc import ABC, abstractmethod
import logging

import httpx

logger = logging.getLogger(__name__)


class LedController(ABC):
    @abstractmethod
    async def turn_off(self) -> bool:
        ...


class WledController(LedController):
    def __init__(self, host: str, port: int = 80, api_token: str | None = None):
        self.base_url = f"http://{host}:{port}"

    async def turn_off(self) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/json/state",
                json={"on": False},
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info("WLED device at %s turned off", self.base_url)
            return True


class KasaController(LedController):
    def __init__(self, host: str, port: int = 80, api_token: str | None = None):
        self.base_url = f"http://{host}:{port}"
        self.api_token = api_token

    async def turn_off(self) -> bool:
        async with httpx.AsyncClient() as client:
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            response = await client.post(
                f"{self.base_url}/",
                json={"system": {"set_relay_state": {"state": False}}},
                headers=headers,
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info("Kasa device at %s turned off", self.base_url)
            return True


class GenericHttpController(LedController):
    def __init__(self, host: str, port: int = 80, api_token: str | None = None):
        self.base_url = f"http://{host}:{port}"
        self.api_token = api_token

    async def turn_off(self) -> bool:
        async with httpx.AsyncClient() as client:
            headers = {}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            response = await client.post(
                f"{self.base_url}/off",
                headers=headers,
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info("Generic device at %s turned off", self.base_url)
            return True


def create_led_controller(
    led_type: str,
    host: str,
    port: int = 80,
    api_token: str | None = None,
) -> LedController:
    controllers = {
        "wled": WledController,
        "kasa": KasaController,
        "generic": GenericHttpController,
    }
    cls = controllers.get(led_type)
    if cls is None:
        raise ValueError(f"Unsupported LED type: {led_type}")
    return cls(host=host, port=port, api_token=api_token)
