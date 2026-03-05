"""
Сканер аукциона — периодически опрашивает лоты и историю продаж
по отслеживаемым предметам и сохраняет данные в БД.
Для артефактов извлекает quality (редкость) и upgrade_level (заточку).
"""

import logging
from typing import Any

from api.auction import get_active_lots, get_price_history
from db.repository import (
    get_active_tracked_items,
    save_price_records,
    save_sale_records,
)

logger = logging.getLogger(__name__)


def _is_artefact(item_id: str) -> bool:
    """Проверка — является ли предмет артефактом (по категории в tracked)."""
    from services.item_loader import item_db
    item = item_db.get(item_id)
    return item is not None and item.category.startswith("artefact")


def _extract_price(lot: dict[str, Any]) -> int:
    """Извлечь цену из лота."""
    for key in ("buyoutPrice", "currentPrice", "price", "startPrice"):
        val = lot.get(key, 0)
        if val and val > 0:
            return int(val)
    return 0


def _parse_additional(lot: dict[str, Any]) -> tuple[int, int]:
    """
    Извлечь quality и upgrade_level из additional полей лота.
    qlt: -1..5 (качество/редкость артефакта)
    ptn: 0..15 (заточка артефакта — potency)
    """
    add = lot.get("additional", {})
    if not add:
        return -1, 0

    qlt = add.get("qlt", -1)
    if qlt is None:
        qlt = -1

    # Заточка хранится в поле "ptn" (potency), а НЕ в "upgrade_bonus"
    ptn = add.get("ptn", 0)
    if ptn is None:
        ptn = 0
    upgrade_level = min(15, max(0, int(ptn)))

    return int(qlt), int(upgrade_level)


async def scan_auction() -> None:
    """
    Основной цикл сканирования:
    1. Для каждого отслеживаемого предмета получаем активные лоты (с additional)
    2. Сохраняем цены в БД с quality/upgrade_level
    3. Получаем историю продаж и тоже сохраняем
    4. Анализируем и отправляем алерты по выгодным сделкам
    """
    tracked = get_active_tracked_items()

    if not tracked:
        logger.info("Нет отслеживаемых предметов.")
        return

    logger.info("Сканирую аукцион: %d предметов...", len(tracked))

    for item in tracked:
        try:
            await _scan_item(item.item_id, item.name)
        except Exception as exc:
            logger.error("Ошибка при сканировании %s: %s", item.item_id, exc)


async def _scan_item(item_id: str, item_name: str) -> None:
    """Сканировать один предмет: лоты + история + анализ."""

    is_art = _is_artefact(item_id)

    # ── 1. Активные лоты ──
    lots_data = await get_active_lots(
        item_id, limit=20, sort="buyout_price", order="asc", additional=True,
    )
    lots = lots_data.get("lots", []) if isinstance(lots_data, dict) else []

    if lots:
        records = []
        for lot in lots:
            qlt, upg = _parse_additional(lot) if is_art else (-1, 0)
            records.append({
                "item_id": item_id,
                "price": _extract_price(lot),
                "amount": lot.get("amount", 1),
                "lot_id": lot.get("id", ""),
                "time_created": lot.get("startTime", ""),
                "quality": qlt,
                "upgrade_level": upg,
            })
        saved = save_price_records(records)
        logger.info("[%s] Сохранено %d лотов", item_name, saved)
    else:
        logger.info("[%s] Активных лотов не найдено", item_name)

    # ── 2. История продаж ──
    try:
        history_data = await get_price_history(item_id, limit=20)
        sales = history_data.get("prices", []) if isinstance(history_data, dict) else []

        if sales:
            sale_records = []
            for sale in sales:
                qlt, upg = _parse_additional(sale) if is_art else (-1, 0)
                sale_records.append({
                    "item_id": item_id,
                    "price": _extract_price(sale),
                    "amount": sale.get("amount", 1),
                    "time": sale.get("time", ""),
                    "quality": qlt,
                    "upgrade_level": upg,
                })
            saved = save_sale_records(sale_records)
            logger.info("[%s] Сохранено %d продаж", item_name, saved)
    except Exception as exc:
        logger.warning("[%s] Не удалось получить историю: %s", item_name, exc)

