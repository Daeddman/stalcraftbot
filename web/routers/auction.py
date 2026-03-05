"""API аукциона — текущие лоты и история."""
import asyncio
import time
import logging
from fastapi import APIRouter
from api.auction import get_active_lots, get_price_history
from db.repository import get_quality_breakdown, get_avg_price, get_avg_sale_price

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auction"])

# ── Кеш отфильтрованной истории (item_id, quality) → {prices, ts} ──
_hist_cache: dict[tuple[str, int], dict] = {}
_HIST_CACHE_TTL = 120  # секунд


@router.get("/auction/{item_id}/lots")
async def lots(
    item_id: str, limit: int = 20, offset: int = 0,
    sort: str = "buyout_price", order: str = "asc",
):
    limit = max(1, min(limit, 200))
    data = await get_active_lots(
        item_id, limit=limit, offset=offset,
        sort=sort, order=order, additional=True,
    )
    return data


@router.get("/auction/{item_id}/history")
async def history(
    item_id: str, limit: int = 20, offset: int = 0,
    quality: int = -99,
):
    """
    История продаж.
    Если quality != -99 → серверная фильтрация:
    загружаем до 10к записей из API, фильтруем по qlt, кешируем 2 мин.
    """
    limit = max(1, min(limit, 100))

    if quality == -99:
        # Без фильтра — прямой проброс в API
        data = await get_price_history(
            item_id, limit=limit, offset=offset, additional=True,
        )
        return data

    # ── С фильтром по качеству ──
    cache_key = (item_id, quality)
    cached = _hist_cache.get(cache_key)
    if cached and time.time() - cached["ts"] < _HIST_CACHE_TTL:
        # Берём из кеша
        all_filtered = cached["prices"]
    else:
        # Загружаем и фильтруем
        all_filtered = await _fetch_filtered_history(item_id, quality)
        _hist_cache[cache_key] = {"prices": all_filtered, "ts": time.time()}
        # Чистим старые записи кеша
        _cleanup_hist_cache()

    page = all_filtered[offset:offset + limit]
    return {
        "prices": page,
        "total": len(all_filtered),
    }


async def _fetch_filtered_history(item_id: str, quality: int) -> list[dict]:
    """
    Загружает историю продаж из API и фильтрует по quality.
    Сканирует до 10000 записей (50 батчей по 200).
    """
    fetch_limit = 200
    max_scan = 10000
    collected = []
    api_offset = 0
    total_scanned = 0

    while total_scanned < max_scan:
        batch = await get_price_history(
            item_id, limit=fetch_limit, offset=api_offset, additional=True,
        )
        prices = batch.get("prices", [])
        api_total = batch.get("total", 0)
        if not prices:
            break

        for p in prices:
            add = p.get("additional") or {}
            qlt = add.get("qlt", -1)
            if qlt is not None and int(qlt) == quality:
                collected.append(p)

        total_scanned += len(prices)
        api_offset += fetch_limit

        if api_offset >= api_total:
            break

        # Задержка для rate-limit
        await asyncio.sleep(0.35)

    logger.info(
        "History filter: item=%s qlt=%d scanned=%d found=%d",
        item_id, quality, total_scanned, len(collected),
    )
    return collected


def _cleanup_hist_cache():
    """Удаляем записи старше TTL."""
    now = time.time()
    expired = [k for k, v in _hist_cache.items() if now - v["ts"] > _HIST_CACHE_TTL * 3]
    for k in expired:
        del _hist_cache[k]


@router.get("/auction/{item_id}/prices")
async def price_summary(item_id: str):
    """Сводка цен из нашей БД (средние, разбивка по качеству)."""
    return {
        "avg_24h": get_avg_price(item_id, hours=24),
        "avg_7d": get_avg_sale_price(item_id, hours=168),
        "breakdown": get_quality_breakdown(item_id, hours=168),
    }

