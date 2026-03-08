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


async def search_clans(query: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """Загружает кланы порциями и ищет по имени/тегу."""
    q = query.lower().strip()
    if not q:
        return await get_clans_list(region=region, offset=0, limit=20)

    # Проверяем кеш полного списка
    cache_key = f"clans_all:{region}"
    all_clans = api_cache.get(cache_key)

    if all_clans is None:
        # Загружаем все кланы порциями
        all_clans = []
        offset = 0
        batch = 200
        max_total = 5000  # безопасный лимит
        while offset < max_total:
            try:
                data = await stalcraft_client.get(
                    f"/{region}/clans",
                    params={"offset": offset, "limit": batch},
                )
                chunk = data.get("data", [])
                total = data.get("totalClans", 0)
                if total > 0:
                    max_total = min(total, 10000)
                all_clans.extend(chunk)
                if len(chunk) < batch:
                    break
                offset += batch
            except Exception as exc:
                logger.warning("Ошибка загрузки кланов offset=%d: %s", offset, exc)
                break
        # Кешируем на 5 минут
        api_cache.set(cache_key, all_clans, ttl=300)
        logger.info("Загружено %d кланов для поиска", len(all_clans))

    # Фильтруем
    results = []
    for c in all_clans:
        name = (c.get("name") or "").lower()
        tag = (c.get("tag") or "").lower()
        alliance = (c.get("alliance") or "").lower()
        leader = (c.get("leader") or "").lower()
        if q in name or q in tag or q in alliance or q in leader:
            results.append(c)

    # Сортируем: точное совпадение имени → начало имени → остальное
    def sort_key(c):
        name = (c.get("name") or "").lower()
        tag = (c.get("tag") or "").lower()
        if name == q or tag == q:
            return 0
        if name.startswith(q) or tag.startswith(q):
            return 1
        return 2
    results.sort(key=sort_key)

    return {"data": results[:100], "totalClans": len(results)}


async def get_clan_info(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/{id}/info"""
    cache_key = f"clan_info:{region}:{clan_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/clan/{clan_id}/info")
        api_cache.set(cache_key, data, ttl=300)
        return data
    except Exception as exc:
        err_str = str(exc)
        logger.warning("Ошибка clan info %s: %s", clan_id, err_str)
        if "404" in err_str:
            return {"error": "Клан не найден"}
        return {"error": f"Ошибка API: {err_str[:200]}"}


async def get_clan_members(clan_id: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/clan/{id}/members"""
    cache_key = f"clan_members:{region}:{clan_id}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/clan/{clan_id}/members")
        api_cache.set(cache_key, data, ttl=300)
        return data
    except Exception as exc:
        logger.warning("Ошибка clan members %s: %s", clan_id, exc)
        return {"error": str(exc)}


async def get_character_profile(character: str, region: str = STALCRAFT_REGION) -> dict[str, Any]:
    """GET /{region}/character/{character}/profile

    Внимание: этот эндпоинт требует user token (Authorization Code flow).
    С application token (client_credentials) всегда возвращает 404.
    """
    cache_key = f"char_profile:{region}:{character}"
    cached = api_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await stalcraft_client.get(f"/{region}/character/{character}/profile")
        api_cache.set(cache_key, data, ttl=180)
        return data
    except Exception as exc:
        err_str = str(exc)
        logger.warning("Ошибка character profile %s: %s", character, err_str)
        if "404" in err_str:
            return {
                "error": "Просмотр профилей персонажей требует авторизацию игрока (OAuth2 user token). "
                         "Сейчас бот использует application token, который не имеет доступа к этому эндпоинту.",
                "requires_user_auth": True,
            }
        return {"error": f"Ошибка API: {err_str[:200]}"}
