#!/usr/bin/env python3
"""Shutdown hook: turns off LEDs and Dream Machine on PC shutdown."""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import asyncssh
import httpx
import yaml


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


logger = logging.getLogger("shutdown_hook")


class DreamMachineConfig:
    def __init__(self, data: dict) -> None:
        self.host: str = data.get("host", "")
        self.port: int = data.get("port", 22)
        self.username: str = data.get("username", "root")
        self.ssh_key_path: Optional[str] = data.get("ssh_key_path")


class LedDeviceConfig:
    def __init__(self, data: dict) -> None:
        self.name: str = data.get("name", "")
        self.host: str = data.get("host", "")
        self.port: int = data.get("port", 80)
        self.api_token: Optional[str] = data.get("api_token")


class LedsConfig:
    def __init__(self, data: dict) -> None:
        self.type: str = data.get("type", "wled")
        self.devices: list[LedDeviceConfig] = [
            LedDeviceConfig(d) for d in data.get("devices", [])
        ]


class InfraConfig:
    def __init__(self, data: dict) -> None:
        dm = data.get("dream_machine")
        self.dream_machine: Optional[DreamMachineConfig] = (
            DreamMachineConfig(dm) if dm else None
        )
        self.leds: LedsConfig = LedsConfig(data.get("leds", {}))


def load_config(path: Optional[str] = None) -> InfraConfig:
    if path is None:
        path = os.getenv("INFRA_CONFIG_PATH", "infra_config.yaml")

    config_path = Path(path)
    if not config_path.exists():
        logger.error("Configuration file not found: %s", config_path.resolve())
        sys.exit(1)

    raw = config_path.read_text(encoding="utf-8")
    raw = os.path.expandvars(raw)
    data = yaml.safe_load(raw)
    if data is None:
        logger.error("Empty configuration file: %s", config_path.resolve())
        sys.exit(1)

    return InfraConfig(data)


class LedController:
    async def turn_off(self) -> bool:
        raise NotImplementedError


class WledController(LedController):
    def __init__(self, device: LedDeviceConfig) -> None:
        self.base_url = f"http://{device.host}:{device.port}"

    async def turn_off(self) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/json/state",
                json={"on": False},
                timeout=5.0,
            )
            response.raise_for_status()
            logger.info("  \u2713 WLED device at %s turned off", self.base_url)
            return True


class KasaController(LedController):
    def __init__(self, device: LedDeviceConfig) -> None:
        self.base_url = f"http://{device.host}:{device.port}"
        self.api_token = device.api_token

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
            logger.info("  \u2713 Kasa device at %s turned off", self.base_url)
            return True


class GenericHttpController(LedController):
    def __init__(self, device: LedDeviceConfig) -> None:
        self.base_url = f"http://{device.host}:{device.port}"
        self.api_token = device.api_token

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
            logger.info("  \u2713 Generic device at %s turned off", self.base_url)
            return True


class LedControllerFactory:
    _controllers = {
        "wled": WledController,
        "kasa": KasaController,
        "generic": GenericHttpController,
    }

    @classmethod
    def create(cls, led_type: str, device: LedDeviceConfig) -> LedController:
        controller_cls = cls._controllers.get(led_type)
        if controller_cls is None:
            raise ValueError(f"Unsupported LED type: {led_type}")
        return controller_cls(device)


class DreamMachineSSHClient:
    def __init__(self, config: DreamMachineConfig) -> None:
        self.config = config

    async def shutdown(self) -> str:
        connect_kwargs = {
            "host": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "known_hosts": None,
        }
        if self.config.ssh_key_path:
            connect_kwargs["client_keys"] = [self.config.ssh_key_path]

        async with asyncssh.connect(**connect_kwargs) as conn:
            result = await conn.run("poweroff", check=True)
            logger.info(
                "  \u2713 Shutdown command sent to Dream Machine (%s)", self.config.host
            )
            return result.stdout or ""


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Shutdown hook: turn off LEDs and Dream Machine"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Execute shutdown even without a shutdown signal",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to infra_config.yaml",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    args = parser.parse_args()

    setup_logging(args.log_level)

    if not args.force:
        logger.warning(
            "No --force flag provided. Run with --force to execute shutdown."
        )
        sys.exit(0)

    config = load_config(args.config)

    if config.leds.devices:
        logger.info("Turning off LED devices...")
        for device in config.leds.devices:
            try:
                controller = LedControllerFactory.create(config.leds.type, device)
                await controller.turn_off()
            except ValueError as e:
                logger.error("  \u2717 %s", e)
            except Exception as e:
                logger.error("  \u2717 Failed to turn off %s: %s", device.name, e)
    else:
        logger.info("No LED devices configured, skipping.")

    if config.dream_machine:
        logger.info("Shutting down Dream Machine...")
        try:
            client = DreamMachineSSHClient(config.dream_machine)
            await client.shutdown()
        except asyncssh.Error as e:
            logger.error("  \u2717 Failed to shut down Dream Machine: %s", e)
        except Exception as e:
            logger.error("  \u2717 Unexpected error: %s", e)
    else:
        logger.info("Dream Machine not configured, skipping.")

    logger.info("Shutdown hook completed.")


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
