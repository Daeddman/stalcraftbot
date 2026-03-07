"""API обёртки для кланов и персонажей."""
import logging
from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION
from services.cache import api_cache

logger = logging.getLogger(__name__)


async def get_clans_list(region: str = STALCRAFT_REGION, offset: int = 0, limit: int = 20) -> dict[str, Any]:
    """GET /{region}/clans — список всех кланов региона."""
    cache_key = f"clans:{region}:{offset}:{limit}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(
            f"/{region}/clans",
            params={"offset": offset, "limit": limit},
        )
        api_cache.set(cache_key, data, ttl=120)
        return data
    except Exception as exc:
        logger.warning("Ошибка clans list: %s", exc)
        return {"error": str(exc), "totalClans": 0, "data": []}


async def get_clan_info(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/{id}/info"""
    cache_key = f"clan_info:{region}:{clan_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/clan/{clan_id}/info")
        api_cache.set(cache_key, data, ttl=120)
        return data
    except Exception as exc:
        logger.warning("Ошибка clan info %s: %s", clan_id, exc)
        return {"error": str(exc)}


async def get_clan_members(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/{id}/members"""
    cache_key = f"clan_members:{region}:{clan_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/clan/{clan_id}/members")
        api_cache.set(cache_key, data, ttl=120)
        return data
    except Exception as exc:
        logger.warning("Ошибка clan members %s: %s", clan_id, exc)
        return {"error": str(exc)}


async def get_character_profile(character: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/characters/{character}/profile"""
    cache_key = f"char_profile:{region}:{character}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/characters/{character}/profile")
        api_cache.set(cache_key, data, ttl=60)
        return data
    except Exception as exc:
        logger.warning("Ошибка character profile %s: %s", character, exc)
        return {"error": str(exc)}
