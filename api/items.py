"""
Обёртки для эндпоинтов предметов и регионов Stalcraft API.
"""

from typing import Any

from api.client import stalcraft_client
from config import STALCRAFT_REGION


async def get_regions() -> list[dict[str, Any]]:
    """Список доступных регионов."""
    return await stalcraft_client.get("/regions")


async def get_item_list(region: str = STALCRAFT_REGION) -> list[dict[str, Any]]:
    """
    Получить полный список предметов (плоский список из дерева).
    API возвращает дерево категорий — мы рекурсивно извлекаем items.
    """
    data = await stalcraft_client.get(f"/{region}/items")
    return data


async def get_item_info(
    item_id: str,
    region: str = STALCRAFT_REGION,
) -> dict[str, Any]:
    """Информация о конкретном предмете."""
    return await stalcraft_client.get(f"/{region}/items/{item_id}")

