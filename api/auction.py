"""
Обёртки для аукционных эндпоинтов Stalcraft API.
Документация: https://eapi.stalcraft.net/
"""

import logging
from typing import Any

from api.client import stalcraft_client, InvalidItemError
from config import STALCRAFT_REGION

logger = logging.getLogger(__name__)


async def get_active_lots(
    item_id: str,
    region: str = STALCRAFT_REGION,
    sort: str = "buyout_price",
    order: str = "asc",
    offset: int = 0,
    limit: int = 20,
    additional: bool = False,
) -> dict[str, Any]:
    """
    Получить активные лоты предмета на аукционе.
    GET /{region}/auction/{item_id}/lots
    """
    try:
        return await stalcraft_client.get(
            f"/{region}/auction/{item_id}/lots",
            params={
                "sort": sort,
                "order": order,
                "offset": offset,
                "limit": limit,
                "additional": str(additional).lower(),
            },
        )
    except InvalidItemError:
        logger.debug("Предмет %s не поддерживается API (wiki-only)", item_id)
        return {"lots": [], "total": 0}
    except Exception as exc:
        logger.warning("Ошибка получения лотов %s: %s", item_id, exc)
        return {"lots": [], "total": 0}


async def get_price_history(
    item_id: str,
    region: str = STALCRAFT_REGION,
    offset: int = 0,
    limit: int = 20,
    additional: bool = True,
) -> dict[str, Any]:
    """
    Получить историю продаж предмета.
    GET /{region}/auction/{item_id}/history
    """
    try:
        return await stalcraft_client.get(
            f"/{region}/auction/{item_id}/history",
            params={
                "offset": offset,
                "limit": limit,
                "additional": str(additional).lower(),
            },
        )
    except InvalidItemError:
        logger.debug("Предмет %s не поддерживается API (wiki-only)", item_id)
        return {"prices": [], "total": 0}
    except Exception as exc:
        logger.warning("Ошибка получения истории %s: %s", item_id, exc)
        return {"prices": [], "total": 0}
