import logging

import asyncssh

from app.infra.config import DreamMachineConfig

logger = logging.getLogger(__name__)


class DreamMachineShutdownError(Exception):
    pass


class DreamMachineService:
    def __init__(self, config: DreamMachineConfig):
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

        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run("poweroff", check=True)
                logger.info("Shutdown command sent to Dream Machine")
                return result.stdout or ""
        except asyncssh.Error as e:
            logger.error("SSH connection failed: %s", e)
            raise DreamMachineShutdownError(str(e)) from e
