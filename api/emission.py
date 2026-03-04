"""Обёртка для endpoint выброса (emission)."""
import logging
import time
from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_cache_ts: float = 0
_CACHE_TTL = 30  # секунд


async def get_emission(region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/emission — статус выброса."""
    global _cache, _cache_ts
    now = time.time()
    if _cache and now - _cache_ts < _CACHE_TTL:
        return _cache
    try:
        data = await stalcraft_client.get(f"/{region}/emission")
        _cache = data
        _cache_ts = now
        return data
    except Exception as exc:
        logger.warning("Ошибка получения emission: %s", exc)
        return _cache or {"currentStart": None, "currentEnd": None,
                          "previousStart": None, "previousEnd": None}

