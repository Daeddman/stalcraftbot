"""Обёртка для endpoint выброса (emission)."""
import asyncio
import logging
from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION
from services.cache import api_cache

logger = logging.getLogger(__name__)

_EMPTY_EMISSION = {"currentStart": None, "currentEnd": None,
                   "previousStart": None, "previousEnd": None}


async def get_emission(region: str = STALCRAFT_REGION, force: bool = False) -> dict[str, Any]:
    """GET /{region}/emission — статус выброса. Кеш 45с (checker обновляет каждые 30с)."""
    cache_key = f"emission:{region}"
    if not force:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return cached
    try:
        data = await asyncio.wait_for(
            stalcraft_client.get(f"/{region}/emission"),
            timeout=5.0,
        )
        api_cache.set(cache_key, data, ttl=45)
        logger.debug("Emission API response: %s", data)
        return data
    except asyncio.TimeoutError:
        logger.warning("Emission API timeout")
        cached = api_cache.get(cache_key)
        return cached or _EMPTY_EMISSION
    except Exception as exc:
        logger.warning("Ошибка получения emission: %s", exc)
        cached = api_cache.get(cache_key)
        return cached or _EMPTY_EMISSION
