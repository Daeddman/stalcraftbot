"""API обёртки для кланов и персонажей."""
import logging
from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION

logger = logging.getLogger(__name__)


async def get_clan_info(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/info/{clan}"""
    try:
        return await stalcraft_client.get(f"/{region}/clan/info/{clan_id}")
    except Exception as exc:
        logger.warning("Ошибка clan info %s: %s", clan_id, exc)
        return {"error": str(exc)}


async def get_clan_members(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/members/{clan}"""
    try:
        return await stalcraft_client.get(f"/{region}/clan/members/{clan_id}")
    except Exception as exc:
        logger.warning("Ошибка clan members %s: %s", clan_id, exc)
        return {"error": str(exc)}


async def get_character_profile(character: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/characters/{character}/profile"""
    try:
        return await stalcraft_client.get(f"/{region}/characters/{character}/profile")
    except Exception as exc:
        logger.warning("Ошибка character profile %s: %s", character, exc)
        return {"error": str(exc)}

