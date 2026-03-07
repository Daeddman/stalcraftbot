"""API аукциона — текущие лоты и история (v2: серверная фильтрация/сортировка)."""
import asyncio
import logging
from fastapi import APIRouter
from api.auction import get_active_lots, get_price_history
from db.models import SessionLocal, SaleRecord, HistorySyncState
from sqlalchemy import desc, asc
from services.cache import auction_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auction"])



def _parse_qlt_upg(additional: dict | None) -> tuple[int, int]:
    """Извлечь quality и upgrade из additional."""
    if not additional:
        return -1, 0
    qlt = additional.get("qlt")
    if qlt is None:
        qlt = -1
    ptn = additional.get("ptn", 0) or 0
    return int(qlt), min(15, max(0, int(ptn)))


def _lot_price(lot: dict) -> int:
    """Получить цену лота для сортировки."""
    return lot.get("buyoutPrice") or lot.get("currentPrice") or lot.get("startPrice") or 0


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
    Активные лоты с серверной фильтрацией по quality и сортировкой.
    quality=-99 — все; quality=0..5 — фильтр по qlt.
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    if quality == -99:
        # Без фильтрации — простой проброс (API отсортирует сам)
        data = await get_active_lots(
            item_id, limit=limit, offset=offset,
            sort=sort, order=order, additional=True,
        )
        # Дополнительная серверная сортировка для гарантии
        lots_list = data.get("lots", [])
        if sort == "buyout_price":
            lots_list.sort(key=lambda l: _lot_price(l), reverse=(order == "desc"))
        elif sort == "time_created":
            lots_list.sort(key=lambda l: l.get("startTime", ""), reverse=(order == "desc"))
        data["lots"] = lots_list
        return data

    # ── С фильтром по quality: загружаем все лоты, фильтруем, сортируем ──
    cache_key = f"lots:{item_id}:{quality}"
    cached = auction_cache.get(cache_key)
    if cached is not None:
        all_filtered = cached
    else:
        all_filtered = await _fetch_filtered_lots(item_id, quality)
        auction_cache.set(cache_key, all_filtered, ttl=60)

    # Серверная сортировка
    if sort == "buyout_price":
        all_filtered.sort(key=lambda l: _lot_price(l), reverse=(order == "desc"))
    elif sort == "time_created":
        all_filtered.sort(
            key=lambda l: l.get("startTime", ""),
            reverse=(order == "desc"),
        )

    page = all_filtered[offset:offset + limit]
    return {
        "lots": page,
        "total": len(all_filtered),
    }


async def _fetch_filtered_lots(item_id: str, quality: int) -> list[dict]:
    """Загружает ВСЕ лоты предмета из API и фильтрует по quality."""
    all_lots = []
    api_offset = 0
    fetch_limit = 200

    while True:
        data = await get_active_lots(
            item_id, limit=fetch_limit, offset=api_offset,
            sort="buyout_price", order="asc", additional=True,
        )
        lots_batch = data.get("lots", [])
        api_total = data.get("total", 0)

        if not lots_batch:
            break

        for l in lots_batch:
            add = l.get("additional") or {}
            qlt, _ = _parse_qlt_upg(add)
            if qlt == quality:
                all_lots.append(l)

        api_offset += fetch_limit
        if api_offset >= api_total:
            break
        await asyncio.sleep(0.3)

    logger.info(
        "Lots filter: item=%s qlt=%d found=%d",
        item_id, quality, len(all_lots),
    )
    return all_lots


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
    История продаж.
    Приоритет: БД (SaleRecord) → API фоллбэк.
    sort: time_desc, time_asc, price_desc, price_asc
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Пробуем из БД
    db_result = _get_history_from_db(item_id, quality, upgrade, sort, limit, offset)
    if db_result["total"] > 0:
        return db_result

    # Фоллбэк на API
    if quality == -99 and upgrade == -99:
        data = await get_price_history(
            item_id, limit=200, offset=0, additional=True,
        )
        prices = data.get("prices", [])
        # Всегда сортируем
        if sort == "time_desc":
            prices.sort(key=lambda p: p.get("time", ""), reverse=True)
        elif sort == "time_asc":
            prices.sort(key=lambda p: p.get("time", ""))
        elif sort == "price_desc":
            prices.sort(key=lambda p: p.get("price", 0), reverse=True)
        elif sort == "price_asc":
            prices.sort(key=lambda p: p.get("price", 0))
        page = prices[offset:offset + limit]
        return {"prices": page, "total": data.get("total", len(prices))}

    # С фильтром — загружаем из API
    cache_key = f"hist:{item_id}:{quality}"
    cached = auction_cache.get(cache_key)
    if cached is not None:
        all_filtered = cached
    else:
        all_filtered = await _fetch_filtered_history(item_id, quality, upgrade)
        auction_cache.set(cache_key, all_filtered, ttl=300)

    # Сортировка
    if sort == "time_desc":
        all_filtered.sort(key=lambda p: p.get("time", ""), reverse=True)
    elif sort == "time_asc":
        all_filtered.sort(key=lambda p: p.get("time", ""))
    elif sort == "price_desc":
        all_filtered.sort(key=lambda p: p.get("price", 0), reverse=True)
    elif sort == "price_asc":
        all_filtered.sort(key=lambda p: p.get("price", 0))

    page = all_filtered[offset:offset + limit]
    return {
        "prices": page,
        "total": len(all_filtered),
    }


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
    """Агрегированные данные для графика цен (по дням).
    Приоритет: БД → API fallback.
    Если за указанный период нет данных — отдаём за всё время.
    """
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict

    use_all_time = (days <= 0)
    cutoff = "" if use_all_time else (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # 1) Пробуем из БД (SaleRecord) за указанный период
    with SessionLocal() as session:
        q = session.query(SaleRecord).filter(SaleRecord.item_id == item_id)
        if quality != -99:
            q = q.filter(SaleRecord.quality == quality)
        if not use_all_time:
            q_period = q.filter(SaleRecord.time_sold >= cutoff).order_by(asc(SaleRecord.time_sold))
            records = q_period.all()
        else:
            records = None  # force all

        # Если за период ничего нет — берём ВСЕ записи
        expanded = False
        if not records:
            records = q.order_by(asc(SaleRecord.time_sold)).all()
            expanded = not use_all_time  # only mark as expanded if wasn't already all-time

    if records:
        result = _build_chart_points(records)
        result["expanded"] = expanded
        return result

    # 2) Fallback: API history (без фильтра quality — API не поддерживает)
    if quality != -99:
        return {"points": [], "total_sales": 0, "expanded": False}

    try:
        all_prices = []
        api_offset = 0
        for _ in range(10):  # макс 2000 записей
            data = await get_price_history(
                item_id, limit=200, offset=api_offset, additional=True,
            )
            prices = data.get("prices", [])
            if not prices:
                break
            all_prices.extend(prices)
            api_total = data.get("total", 0)
            api_offset += 200
            if api_offset >= api_total:
                break
            await asyncio.sleep(0.2)

        if not all_prices:
            return {"points": [], "total_sales": 0, "expanded": False}

        # Сначала пробуем с фильтром по дате
        daily: dict[str, list[int]] = defaultdict(list)
        for p in all_prices:
            t = p.get("time", "")
            day = t[:10] if t else ""
            if day and day >= cutoff[:10]:
                price = p.get("price", 0)
                if price > 0:
                    daily[day].append(price)

        # Если за период пусто — берём всё
        expanded = False
        if not daily:
            expanded = True
            for p in all_prices:
                t = p.get("time", "")
                day = t[:10] if t else ""
                if day:
                    price = p.get("price", 0)
                    if price > 0:
                        daily[day].append(price)

        points = []
        total = 0
        for day, prices_list in sorted(daily.items()):
            prices_sorted = sorted(prices_list)
            n = len(prices_sorted)
            total += n
            points.append({
                "date": day,
                "min": prices_sorted[0],
                "max": prices_sorted[-1],
                "avg": sum(prices_sorted) // n,
                "median": prices_sorted[n // 2],
                "count": n,
            })

        return {"points": points, "total_sales": total, "expanded": expanded}

    except Exception as exc:
        logger.warning("Chart fallback error for %s: %s", item_id, exc)
        return {"points": [], "total_sales": 0, "expanded": False}


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


async def _fetch_filtered_history(item_id: str, quality: int, upgrade: int = -99) -> list[dict]:
    """Загружает историю из API и фильтрует. Сканирует до 10к записей."""
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
            qlt = add.get("qlt")
            ptn = add.get("ptn", 0) or 0
            if quality != -99 and (qlt is None or int(qlt) != quality):
                continue
            if upgrade != -99 and int(ptn) != upgrade:
                continue
            collected.append(p)

        total_scanned += len(prices)
        api_offset += fetch_limit

        if api_offset >= api_total:
            break

        await asyncio.sleep(0.3)

    logger.info(
        "History filter: item=%s qlt=%d upg=%d scanned=%d found=%d",
        item_id, quality, upgrade, total_scanned, len(collected),
    )
    return collected

