"""
Анализатор выгодных сделок.
Для артефактов сравнивает цены в рамках одной редкости + заточки.
Для обычных предметов — просто по средней.
"""

import logging
from dataclasses import dataclass
from typing import Any

from config import DEAL_THRESHOLD_PERCENT
from db.repository import (
    get_avg_price,
    get_avg_sale_price,
    was_alert_sent,
    quality_name,
    upgrade_str,
)

logger = logging.getLogger(__name__)


@dataclass
class Deal:
    """Выгодная сделка для уведомления."""
    item_id: str
    item_name: str
    lot_id: str
    current_price: int
    avg_price: float
    avg_sale_price: float | None
    discount_percent: float
    potential_profit: int
    amount: int
    quality: int = -1
    upgrade_level: int = 0

    @property
    def quality_str(self) -> str:
        parts = []
        if self.quality >= 0:
            parts.append(quality_name(self.quality))
        if self.upgrade_level > 0:
            parts.append(f"+{self.upgrade_level}")
        return " ".join(parts) if parts else ""


def _extract_price(lot: dict[str, Any]) -> int:
    for key in ("buyoutPrice", "currentPrice", "price", "startPrice"):
        val = lot.get(key, 0)
        if val and val > 0:
            return int(val)
    return 0


def _parse_additional(lot: dict[str, Any]) -> tuple[int, int]:
    """Извлечь quality и upgrade_level из additional."""
    add = lot.get("additional", {})
    if not add:
        return -1, 0
    qlt = add.get("qlt", -1)
    if qlt is None:
        qlt = -1
    upgrade_bonus = add.get("upgrade_bonus", 0.0)
    if upgrade_bonus and upgrade_bonus > 0:
        upgrade_level = min(15, max(0, round(upgrade_bonus * 20)))
        if upgrade_level == 0 and upgrade_bonus > 0.01:
            upgrade_level = 1
    else:
        upgrade_level = 0
    return int(qlt), int(upgrade_level)


def analyze_item(
    item_id: str,
    item_name: str,
    lots: list[dict[str, Any]],
    is_artefact: bool = False,
) -> list[Deal]:
    """
    Анализирует лоты предмета и возвращает список выгодных сделок.

    Для артефактов: средняя считается ОТДЕЛЬНО по каждой комбинации (quality, upgrade_level).
    Для обычных предметов: одна общая средняя.
    """
    deals: list[Deal] = []

    if is_artefact:
        deals = _analyze_artefact_lots(item_id, item_name, lots)
    else:
        deals = _analyze_simple_lots(item_id, item_name, lots)

    return deals


def _analyze_simple_lots(
    item_id: str,
    item_name: str,
    lots: list[dict[str, Any]],
) -> list[Deal]:
    """Обычный анализ — одна средняя на все лоты."""
    avg_24h = get_avg_price(item_id, hours=24)
    avg_sale_7d = get_avg_sale_price(item_id, hours=168)
    reference_price = avg_sale_7d or avg_24h

    if not reference_price or reference_price <= 0:
        return []

    deals: list[Deal] = []
    threshold = reference_price * (DEAL_THRESHOLD_PERCENT / 100.0)

    for lot in lots:
        price = _extract_price(lot)
        lot_id = lot.get("id", "")

        if price <= 0 or price > threshold:
            continue
        if was_alert_sent(item_id, lot_id):
            continue

        discount = ((reference_price - price) / reference_price) * 100
        deals.append(Deal(
            item_id=item_id,
            item_name=item_name,
            lot_id=lot_id,
            current_price=price,
            avg_price=reference_price,
            avg_sale_price=avg_sale_7d,
            discount_percent=round(discount, 1),
            potential_profit=int(reference_price - price),
            amount=lot.get("amount", 1),
        ))

    return deals


def _analyze_artefact_lots(
    item_id: str,
    item_name: str,
    lots: list[dict[str, Any]],
) -> list[Deal]:
    """
    Анализ артефактов — средняя цена считается ОТДЕЛЬНО для каждой
    комбинации (quality, upgrade_level).
    """
    deals: list[Deal] = []

    # Кешируем средние для каждой пары (qlt, upg)
    avg_cache: dict[tuple[int, int], float | None] = {}

    for lot in lots:
        price = _extract_price(lot)
        lot_id = lot.get("id", "")

        if price <= 0:
            continue

        qlt, upg = _parse_additional(lot)

        # Получаем среднюю для ЭТОЙ комбинации quality + upgrade
        cache_key = (qlt, upg)
        if cache_key not in avg_cache:
            # Сначала пробуем среднюю продажу за 7 дней по этой редкости/заточке
            avg_sale = get_avg_sale_price(item_id, hours=168, quality=qlt, upgrade_level=upg)
            avg_lot = get_avg_price(item_id, hours=24, quality=qlt, upgrade_level=upg)
            avg_cache[cache_key] = avg_sale or avg_lot

        reference_price = avg_cache[cache_key]
        if not reference_price or reference_price <= 0:
            continue

        threshold = reference_price * (DEAL_THRESHOLD_PERCENT / 100.0)
        if price > threshold:
            continue
        if was_alert_sent(item_id, lot_id):
            continue

        discount = ((reference_price - price) / reference_price) * 100

        deal = Deal(
            item_id=item_id,
            item_name=item_name,
            lot_id=lot_id,
            current_price=price,
            avg_price=reference_price,
            avg_sale_price=avg_cache[cache_key],
            discount_percent=round(discount, 1),
            potential_profit=int(reference_price - price),
            amount=lot.get("amount", 1),
            quality=qlt,
            upgrade_level=upg,
        )
        deals.append(deal)

        qlt_str = quality_name(qlt)
        upg_str = upgrade_str(upg)
        logger.info(
            "🔥 [%s] %s%s: %d руб. (-%0.1f%%, профит ~%d)",
            item_name, qlt_str, upg_str, price, discount, deal.potential_profit,
        )

    return deals

