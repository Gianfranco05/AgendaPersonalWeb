import os
from pathlib import Path
from typing import Optional, Literal

from pydantic import BaseModel
import yaml


class DreamMachineConfig(BaseModel):
    host: str
    port: int = 22
    username: str = "root"
    ssh_key_path: Optional[str] = None


class LedDeviceConfig(BaseModel):
    name: str
    host: str
    port: int = 80
    api_token: Optional[str] = None


class LedsConfig(BaseModel):
    type: Literal["wled", "kasa", "generic"] = "wled"
    devices: list[LedDeviceConfig] = []


class InfraConfig(BaseModel):
    dream_machine: Optional[DreamMachineConfig] = None
    leds: LedsConfig = LedsConfig()


def load_infra_config(path: Optional[str] = None) -> InfraConfig:
    if path is None:
        path = os.getenv("INFRA_CONFIG_PATH", "infra_config.yaml")

    config_path = Path(path)
    if not config_path.exists():
        return InfraConfig()

    raw = config_path.read_text(encoding="utf-8")
    raw = os.path.expandvars(raw)
    data = yaml.safe_load(raw)
    if data is None:
        return InfraConfig()
    return InfraConfig(**data)


_infra_config: Optional[InfraConfig] = None


def get_infra_config() -> InfraConfig:
    global _infra_config
    if _infra_config is None:
        _infra_config = load_infra_config()
    return _infra_config
