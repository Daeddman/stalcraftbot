"""Обёртка для endpoint выброса (emission)."""
import logging
from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION
from services.cache import api_cache

logger = logging.getLogger(__name__)

_EMPTY_EMISSION = {"currentStart": None, "currentEnd": None,
                   "previousStart": None, "previousEnd": None}


async def get_emission(region: str = STALCRAFT_REGION, force: bool = False) -> dict[str, Any]:
    """GET /{region}/emission — статус выброса."""
    cache_key = f"emission:{region}"
    if not force:
        cached = api_cache.get(cache_key)
        if cached is not None:
            return cached
    try:
        data = await stalcraft_client.get(f"/{region}/emission")
        api_cache.set(cache_key, data, ttl=15)
        logger.debug("Emission API response: %s", data)
        return data
    except Exception as exc:
        logger.warning("Ошибка получения emission: %s", exc)
        cached = api_cache.get(cache_key)
        return cached or _EMPTY_EMISSION
