"""API аукциона — текущие лоты и история (DB-first, мгновенно)."""
import asyncio
import json
import logging
from fastapi import APIRouter
from api.auction import get_active_lots, get_price_history
from db.models import SessionLocal, SaleRecord, HistorySyncState, ActiveLot
from sqlalchemy import desc, asc
from services.cache import auction_cache, compute_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auction"])


def _lot_price(lot: dict) -> int:
    """Получить цену лота для сортировки."""
    return lot.get("buyoutPrice") or lot.get("currentPrice") or lot.get("startPrice") or 0


def _active_lot_to_dict(l: ActiveLot) -> dict:
    """Преобразует ActiveLot из БД в формат, совместимый с API."""
    additional = None
    if l.additional_json:
        try:
            additional = json.loads(l.additional_json)
        except Exception:
            pass
    if additional is None:
        additional = {}
    if l.quality >= 0:
        additional["qlt"] = l.quality
    if l.upgrade_level > 0:
        additional["ptn"] = l.upgrade_level
    return {
        "id": l.lot_id,
        "itemId": l.item_id,
        "startPrice": l.start_price or 0,
        "currentPrice": l.current_price or 0,
        "buyoutPrice": l.buyout_price or 0,
        "amount": l.amount or 1,
        "startTime": l.start_time or "",
        "endTime": l.end_time or "",
        "additional": additional,
    }


@router.get("/auction/{item_id}/lots")
async def lots(
    item_id: str,
    limit: int = 20,
    offset: int = 0,
    sort: str = "buyout_price",
    order: str = "asc",
    quality: int = -99,
):
    """
    Активные лоты — читаем из локальной БД (ActiveLot), мгновенно.
    quality=-99 — все; quality=0..5 — фильтр по qlt.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    with SessionLocal() as session:
        q = session.query(ActiveLot).filter(ActiveLot.item_id == item_id)

        if quality != -99:
            q = q.filter(ActiveLot.quality == quality)

        # Сортировка
        sort_map = {
            "buyout_price": ActiveLot.buyout_price,
            "time_created": ActiveLot.start_time,
            "amount": ActiveLot.amount,
            "quality": ActiveLot.quality,
        }
        col = sort_map.get(sort, ActiveLot.buyout_price)
        q = q.order_by(col.desc() if order == "desc" else col.asc())

        total = q.count()
        rows = q.offset(offset).limit(limit).all()
        lots_list = [_active_lot_to_dict(r) for r in rows]

    # Если в БД пусто — fallback на единичный API-запрос (не цепочку!)
    if total == 0 and quality == -99:
        try:
            data = await get_active_lots(
                item_id, limit=limit, offset=offset,
                sort=sort, order=order, additional=True,
            )
            return data
        except Exception:
            pass

    return {"lots": lots_list, "total": total}


@router.get("/auction/{item_id}/history")
async def history(
    item_id: str,
    limit: int = 20,
    offset: int = 0,
    quality: int = -99,
    upgrade: int = -99,
    sort: str = "time_desc",
):
    """
    История продаж — DB-only (мгновенно).
    Если данных нет — триггерим фоновую синхронизацию.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    db_result = _get_history_from_db(item_id, quality, upgrade, sort, limit, offset)

    if db_result["total"] > 0:
        return db_result

    # Данных нет — запускаем фоновую синхронизацию и пробуем единичный API-запрос
    _trigger_bg_sync(item_id)

    # Быстрый одноразовый запрос к API (1 запрос, не цепочка)
    try:
        data = await get_price_history(
            item_id, limit=min(limit, 200), offset=offset, additional=True,
        )
        prices = data.get("prices", [])
        if prices:
            if sort == "time_desc":
                prices.sort(key=lambda p: p.get("time", ""), reverse=True)
            elif sort == "time_asc":
                prices.sort(key=lambda p: p.get("time", ""))
            elif sort == "price_desc":
                prices.sort(key=lambda p: p.get("price", 0), reverse=True)
            elif sort == "price_asc":
                prices.sort(key=lambda p: p.get("price", 0))
            return {"prices": prices[:limit], "total": data.get("total", len(prices)), "syncing": True}
    except Exception:
        pass

    return {"prices": [], "total": 0, "syncing": True}


def _trigger_bg_sync(item_id: str):
    """Запускает фоновую синхронизацию если ещё не запущена."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from services.history_sync import incremental_sync
            asyncio.ensure_future(incremental_sync(item_id))
    except Exception:
        pass


def _get_history_from_db(
    item_id: str, quality: int, upgrade: int,
    sort: str, limit: int, offset: int,
) -> dict:
    """Читает историю продаж из sale_records."""
    with SessionLocal() as session:
        q = session.query(SaleRecord).filter(SaleRecord.item_id == item_id)

        if quality != -99:
            q = q.filter(SaleRecord.quality == quality)
        if upgrade != -99:
            q = q.filter(SaleRecord.upgrade_level == upgrade)

        total = q.count()
        if total == 0:
            return {"prices": [], "total": 0}

        if sort == "time_desc":
            q = q.order_by(desc(SaleRecord.time_sold))
        elif sort == "time_asc":
            q = q.order_by(asc(SaleRecord.time_sold))
        elif sort == "price_desc":
            q = q.order_by(desc(SaleRecord.price))
        elif sort == "price_asc":
            q = q.order_by(asc(SaleRecord.price))
        else:
            q = q.order_by(desc(SaleRecord.time_sold))

        records = q.offset(offset).limit(limit).all()

        prices = []
        for r in records:
            prices.append({
                "price": r.price,
                "amount": r.amount,
                "time": r.time_sold,
                "additional": {
                    "qlt": r.quality if r.quality >= 0 else None,
                    "ptn": r.upgrade_level if r.upgrade_level > 0 else None,
                },
            })

        return {"prices": prices, "total": total}


@router.get("/auction/{item_id}/chart-data")
async def chart_data(
    item_id: str,
    quality: int = -99,
    days: int = 30,
):
    """Агрегированные данные для графика цен — DB-only, кешируется."""
    from datetime import datetime, timedelta, timezone

    cache_key = f"chart:{item_id}:{quality}:{days}"
    cached = compute_cache.get(cache_key)
    if cached is not None:
        return cached

    use_all_time = (days <= 0)
    cutoff = "" if use_all_time else (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with SessionLocal() as session:
        q = session.query(SaleRecord).filter(SaleRecord.item_id == item_id)
        if quality != -99:
            q = q.filter(SaleRecord.quality == quality)
        if not use_all_time:
            q_period = q.filter(SaleRecord.time_sold >= cutoff).order_by(asc(SaleRecord.time_sold))
            records = q_period.all()
        else:
            records = None

        expanded = False
        if not records:
            records = q.order_by(asc(SaleRecord.time_sold)).all()
            expanded = not use_all_time

    if records:
        result = _build_chart_points(records)
        result["expanded"] = expanded
        compute_cache.set(cache_key, result, ttl=600)
        return result

    # Нет данных — запускаем синхронизацию
    _trigger_bg_sync(item_id)
    return {"points": [], "total_sales": 0, "expanded": False, "syncing": True}


def _build_chart_points(records) -> dict:
    """Строит chart points из списка SaleRecord."""
    from collections import defaultdict
    daily: dict[str, list[int]] = defaultdict(list)
    for r in records:
        day = r.time_sold[:10] if r.time_sold else ""
        if day:
            daily[day].append(r.price)

    points = []
    for day, prices_list in sorted(daily.items()):
        prices_sorted = sorted(prices_list)
        n = len(prices_sorted)
        points.append({
            "date": day,
            "min": prices_sorted[0],
            "max": prices_sorted[-1],
            "avg": sum(prices_sorted) // n,
            "median": prices_sorted[n // 2],
            "count": n,
        })

    return {"points": points, "total_sales": len(records)}


@router.get("/auction/{item_id}/sync-status")
async def sync_status(item_id: str):
    """Статус синхронизации истории предмета."""
    with SessionLocal() as session:
        st = session.query(HistorySyncState).filter_by(item_id=item_id).first()
        if not st:
            return {"synced": False, "total_api": 0, "total_stored": 0}
        return {
            "synced": st.full_download_done,
            "total_api": st.total_api,
            "total_stored": st.total_stored,
            "status": st.status,
            "last_sync": st.last_sync_at.isoformat() if st.last_sync_at else None,
        }





