"""Reclamo atomico de un evento entre procesos (Redis `SET NX`).

gunicorn levanta 2*CPU+1 workers y CADA uno corre sus schedulers (el lifespan
se ejecuta por worker). Sin un claim compartido, la misma push saldria N veces.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None


async def claim_once(key: str, ttl_seconds: int) -> bool:
    """True si este proceso es el primero en reclamar `key`. SET NX es atomico:
    de N workers solo uno lo gana. Sin REDIS_URL, o si Redis no responde,
    devuelve True: con un solo proceso no hay carrera, y es preferible un
    duplicado a perder el aviso (las capas de dedup que siguen lo acotan)."""
    global _redis_client
    if not settings.REDIS_URL:
        return True
    try:
        if _redis_client is None:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        claimed = await _redis_client.set(key, "1", nx=True, ex=ttl_seconds)
        return bool(claimed)
    except Exception:
        logger.warning("Scheduler: Redis no disponible para deduplicar", exc_info=True)
        _redis_client = None
        return True
