"""
Discovery-сканер: полный обход аукциона по offset.
Находит ВСЕ лоты, включая предметы которых нет в official DB.
Вариант B: state + history (active_lots + lot_events).
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timezone

from api.client import stalcraft_client
from config import STALCRAFT_REGION
from db.models import (
    SessionLocal,
    ActiveLot,
    LotEvent,
    ItemRegistry,
    PriceSample,
    ItemPriceStats,
)

logger = logging.getLogger("discovery")

PAGE_SIZE = 200   # макс лотов за запрос (API limit)
MAX_PAGES = 500   # защита от бесконечного цикла
SCAN_DELAY = 0.35 # задержка между страницами (rate limit)


# ══════════════════════════════════════════════════════════════
#  Парсинг лотов
# ══════════════════════════════════════════════════════════════

def _extract_price(lot: dict, key: str) -> int:
    val = lot.get(key, 0)
    if val and isinstance(val, (int, float)) and val > 0:
        return int(val)
    return 0


def _parse_additional(lot: dict) -> tuple[int, int]:
    """quality (-1..5) и upgrade_level (0..15) из additional."""
    add = lot.get("additional") or {}
    qlt = add.get("qlt", -1)
    if qlt is None:
        qlt = -1
    # Заточка в поле "ptn" (potency), НЕ "upgrade_bonus"
    ptn = add.get("ptn", 0) or 0
    upgrade = min(15, max(0, int(ptn)))
    return int(qlt), int(upgrade)


# ══════════════════════════════════════════════════════════════
#  Сбор всех лотов с аукциона
# ══════════════════════════════════════════════════════════════

async def _fetch_all_lots(region: str) -> list[dict]:
    """Обходит весь аукцион по offset, возвращает все лоты."""
    all_lots: list[dict] = []
    offset = 0

    for _ in range(MAX_PAGES):
        try:
            data = await stalcraft_client.get(
                f"/{region}/auction",
                params={
                    "sort": "time_created",
                    "order": "asc",
                    "offset": offset,
                    "limit": PAGE_SIZE,
                    "additional": "true",
                },
            )
        except Exception as exc:
            logger.error("Ошибка получения страницы offset=%d: %s", offset, exc)
            break

        lots = data.get("lots", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if not lots:
            break

        all_lots.extend(lots)
        offset += PAGE_SIZE

        if len(lots) < PAGE_SIZE:
            break

        await asyncio.sleep(SCAN_DELAY)

    return all_lots


# ══════════════════════════════════════════════════════════════
#  Обработка лотов: upsert active_lots, events, registry, aggregation
# ══════════════════════════════════════════════════════════════

def _process_lots(lots: list[dict], region: str) -> dict[str, int]:
    """Обрабатывает полученные лоты. Возвращает статистику."""
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # Текущие lot_id в БД
        existing_lot_ids: set[str] = {
            r[0] for r in session.query(ActiveLot.lot_id).filter(ActiveLot.region == region).all()
        }
        seen_lot_ids: set[str] = set()
        new_items = 0
        items_prices: dict[str, list[int]] = {}   # item_id -> [prices]
        items_amounts: dict[str, int] = {}         # item_id -> total_amount

        for lot in lots:
            lot_id = lot.get("id", "") or lot.get("lot_id", "")
            item_id = lot.get("itemId", "") or lot.get("item_id", "")
            if not lot_id or not item_id:
                continue

            lot_id = str(lot_id)
            seen_lot_ids.add(lot_id)

            buyout = _extract_price(lot, "buyoutPrice")
            start_p = _extract_price(lot, "startPrice")
            current = _extract_price(lot, "currentPrice") or buyout
            amount = lot.get("amount", 1) or 1
            qlt, upg = _parse_additional(lot)
            start_time = lot.get("startTime", "")
            end_time = lot.get("endTime", "")
            additional = lot.get("additional")

            # ── Агрегация ──
            price = buyout or current
            if price > 0:
                items_prices.setdefault(item_id, []).append(price)
            items_amounts[item_id] = items_amounts.get(item_id, 0) + amount

            # ── ItemRegistry ──
            reg = session.get(ItemRegistry, item_id)
            if reg is None:
                new_items += 1
                reg = ItemRegistry(
                    item_id=item_id,
                    name=item_id,  # stub
                    source="observed",
                    is_official_db=False,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(reg)
                logger.info("🆕 Новый предмет: %s", item_id)
            else:
                reg.last_seen_at = now

            # ── ActiveLot upsert ──
            existing = session.get(ActiveLot, lot_id)
            if existing is None:
                session.add(ActiveLot(
                    lot_id=lot_id, item_id=item_id, region=region,
                    start_price=start_p, buyout_price=buyout, current_price=current,
                    amount=amount, quality=qlt, upgrade_level=upg,
                    additional_json=json.dumps(additional, ensure_ascii=False) if additional else None,
                    start_time=start_time, end_time=end_time,
                    first_seen_at=now, last_seen_at=now,
                ))
                session.add(LotEvent(
                    lot_id=lot_id, item_id=item_id, event_type="created",
                    price=buyout or current, amount=amount, event_at=now,
                ))
            else:
                changed = (existing.buyout_price != buyout or existing.current_price != current)
                existing.current_price = current
                existing.buyout_price = buyout
                existing.amount = amount
                existing.last_seen_at = now
                if changed:
                    session.add(LotEvent(
                        lot_id=lot_id, item_id=item_id, event_type="updated",
                        price=buyout or current, amount=amount, event_at=now,
                    ))

        # ── Исчезнувшие лоты ──
        disappeared = existing_lot_ids - seen_lot_ids
        for gone_id in disappeared:
            gone = session.get(ActiveLot, gone_id)
            if gone:
                session.add(LotEvent(
                    lot_id=gone_id, item_id=gone.item_id,
                    event_type="disappeared",
                    price=gone.buyout_price or gone.current_price,
                    amount=gone.amount,
                    details_json=json.dumps({"likely_sold": True}),
                    event_at=now,
                ))
                session.delete(gone)

        # ── Агрегация цен ──
        samples = 0
        for item_id, prices in items_prices.items():
            if not prices:
                continue
            prices.sort()
            min_p = prices[0]
            max_p = prices[-1]
            avg_p = int(sum(prices) / len(prices))
            med_p = int(statistics.median(prices))
            total_amt = items_amounts.get(item_id, 0)

            # PriceSample
            session.add(PriceSample(
                item_id=item_id, region=region,
                min_price=min_p, median_price=med_p,
                avg_price=avg_p, max_price=max_p,
                lots_count=len(prices), total_amount=total_amt,
                sampled_at=now,
            ))
            samples += 1

            # ItemPriceStats upsert
            stats = session.get(ItemPriceStats, item_id)
            if stats is None:
                stats = ItemPriceStats(item_id=item_id, region=region)
                session.add(stats)
            stats.min_price = min_p
            stats.median_price = med_p
            stats.avg_price = avg_p
            stats.lots_count = len(prices)
            stats.total_amount = total_amt
            stats.updated_at = now

        session.commit()

        return {
            "total_lots": len(seen_lot_ids),
            "new_items": new_items,
            "disappeared": len(disappeared),
            "samples": samples,
        }


# ══════════════════════════════════════════════════════════════
#  Публичный API
# ══════════════════════════════════════════════════════════════

async def run_discovery_scan(region: str = STALCRAFT_REGION) -> dict[str, int]:
    """Полный скан аукциона. Вызывается по расписанию."""
    logger.info("🔍 Discovery scan [%s] запущен...", region)

    lots = await _fetch_all_lots(region)
    if not lots:
        logger.warning("⚠️ 0 лотов получено")
        return {"total_lots": 0, "new_items": 0, "disappeared": 0, "samples": 0}

    logger.info("📦 Получено %d лотов", len(lots))
    stats = _process_lots(lots, region)
    logger.info(
        "✅ Discovery: lots=%d new=%d gone=%d samples=%d",
        stats["total_lots"], stats["new_items"], stats["disappeared"], stats["samples"],
    )
    return stats


def sync_official_db_to_registry() -> int:
    """Синхронизирует item_db → ItemRegistry (вызывать после item_db.load())."""
    from services.item_loader import item_db

    if not item_db.loaded:
        return 0

    now = datetime.now(timezone.utc)
    added = 0

    with SessionLocal() as session:
        for item_id in item_db._items:
            gi = item_db._items[item_id]
            reg = session.get(ItemRegistry, item_id)
            if reg is None:
                icon_url = gi.icon_path or ""
                if icon_url and not icon_url.startswith("http"):
                    icon_url = f"/icons/{icon_url.lstrip('/')}"
                reg = ItemRegistry(
                    item_id=item_id,
                    name=gi.name_ru,
                    category=gi.category,
                    icon_url=icon_url,
                    color=gi.color,
                    source="official_db",
                    is_official_db=True,
                    first_seen_at=now,
                    last_seen_at=now,
                )
                session.add(reg)
                added += 1
            else:
                # Обновляем метаданные
                if gi.name_ru and (reg.name == reg.item_id or not reg.name):
                    reg.name = gi.name_ru
                if gi.category:
                    reg.category = gi.category
                if gi.color != "DEFAULT":
                    reg.color = gi.color
                reg.is_official_db = True
                if reg.source == "observed":
                    reg.source = "official_db"
                reg.last_seen_at = now

        session.commit()

    logger.info("📋 Registry sync: +%d из official DB (всего %d)", added, len(item_db._items))
    return added

