"""
Инкрементальная и полная выгрузка истории продаж из Stalcraft API.

Стратегия:
1. incremental_sync — загружает новые продажи (newest → до уже сохранённой)
2. full_download    — продолжает полную выгрузку (offset вглубь истории)
3. run_sync_cycle   — оркестрирует по приоритету
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.auction import get_price_history
from db.models import SessionLocal, SaleRecord, HistorySyncState, TrackedItem, ItemPriceStats
from services.scanner import _parse_additional

logger = logging.getLogger(__name__)

# Пауза между запросами к API (rate limit = 10 req/s)
_API_DELAY = 0.15
_BATCH_SIZE = 200  # максимум API


# ══════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════

def _get_sync_state(session, item_id: str) -> HistorySyncState:
    st = session.query(HistorySyncState).filter_by(item_id=item_id).first()
    if not st:
        st = HistorySyncState(item_id=item_id)
        session.add(st)
        session.flush()
    return st


def _save_sales_dedup(session, item_id: str, prices: list[dict]) -> int:
    """Сохраняет продажи с дедупликацией. Возвращает кол-во новых."""
    added = 0
    for p in prices:
        add = p.get("additional") or {}
        qlt, upg = _parse_additional({"additional": add})
        time_sold = p.get("time", "")
        price = int(p.get("price", 0))
        amount = int(p.get("amount", 1))
        if not price:
            continue
        try:
            result = session.execute(
                text("""
                    INSERT OR IGNORE INTO sale_records
                    (item_id, price, amount, time_sold, quality, upgrade_level, recorded_at)
                    VALUES (:item_id, :price, :amount, :time_sold, :quality, :upgrade_level, :recorded_at)
                """),
                {
                    "item_id": item_id,
                    "price": price,
                    "amount": amount,
                    "time_sold": time_sold,
                    "quality": qlt,
                    "upgrade_level": upg,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            if result.rowcount > 0:
                added += 1
        except IntegrityError:
            session.rollback()
    try:
        session.commit()
    except Exception:
        session.rollback()
    return added


# ══════════════════════════════════════════════════════════════
#  Инкрементальная синхронизация (новые продажи)
# ══════════════════════════════════════════════════════════════

async def incremental_sync(item_id: str) -> int:
    """
    Загружает новые продажи для предмета.
    Начинает с offset=0 (newest), останавливается когда встречает
    запись с time <= newest_stored_time.
    Возвращает кол-во новых записей.
    """
    with SessionLocal() as session:
        st = _get_sync_state(session, item_id)
        newest = st.newest_stored_time
        st.status = "syncing"
        session.commit()

    total_added = 0
    offset = 0
    stop = False

    while not stop:
        data = await get_price_history(item_id, limit=_BATCH_SIZE, offset=offset, additional=True)
        prices = data.get("prices", [])
        api_total = data.get("total", 0)

        if not prices:
            break

        # Фильтруем: оставляем только новее чем newest
        to_save = []
        for p in prices:
            t = p.get("time", "")
            if newest and t <= newest:
                stop = True
                break
            to_save.append(p)

        with SessionLocal() as session:
            added = _save_sales_dedup(session, item_id, to_save)
            total_added += added

            st = _get_sync_state(session, item_id)
            st.total_api = api_total
            if to_save:
                first_time = to_save[0].get("time", "")
                if not st.newest_stored_time or first_time > st.newest_stored_time:
                    st.newest_stored_time = first_time
            st.total_stored = session.query(SaleRecord).filter_by(item_id=item_id).count()
            st.last_sync_at = datetime.now(timezone.utc)
            st.status = "idle"
            session.commit()

        offset += _BATCH_SIZE
        if offset >= api_total:
            break
        await asyncio.sleep(_API_DELAY)

    return total_added


# ══════════════════════════════════════════════════════════════
#  Полная выгрузка (продолжает с последнего offset)
# ══════════════════════════════════════════════════════════════

async def full_download_chunk(item_id: str, max_requests: int = 50) -> int:
    """
    Продолжает полную выгрузку с того offset, где остановились.
    Делает max_requests запросов за один вызов.
    Возвращает кол-во новых записей.
    """
    with SessionLocal() as session:
        st = _get_sync_state(session, item_id)
        if st.full_download_done:
            return 0
        start_offset = st.oldest_stored_offset
        st.status = "syncing"
        session.commit()

    total_added = 0
    offset = start_offset
    requests_done = 0

    while requests_done < max_requests:
        data = await get_price_history(item_id, limit=_BATCH_SIZE, offset=offset, additional=True)
        prices = data.get("prices", [])
        api_total = data.get("total", 0)
        requests_done += 1

        if not prices:
            # Достигли конца
            with SessionLocal() as session:
                st = _get_sync_state(session, item_id)
                st.full_download_done = True
                st.total_api = api_total
                st.status = "done"
                st.last_sync_at = datetime.now(timezone.utc)
                session.commit()
            break

        with SessionLocal() as session:
            added = _save_sales_dedup(session, item_id, prices)
            total_added += added

            st = _get_sync_state(session, item_id)
            st.total_api = api_total
            offset += _BATCH_SIZE
            st.oldest_stored_offset = offset
            st.total_stored = session.query(SaleRecord).filter_by(item_id=item_id).count()
            st.last_sync_at = datetime.now(timezone.utc)

            if offset >= api_total:
                st.full_download_done = True
                st.status = "done"
            else:
                st.status = "idle"
            session.commit()

        if offset >= api_total:
            break
        await asyncio.sleep(_API_DELAY)

    return total_added


# ══════════════════════════════════════════════════════════════
#  Обновление приоритетов
# ══════════════════════════════════════════════════════════════

def update_priorities():
    """Обновляет приоритеты: tracked=0, popular=1, rest=2."""
    with SessionLocal() as session:
        # Tracked items → priority 0
        tracked_ids = [t.item_id for t in session.query(TrackedItem).filter_by(is_active=True).all()]
        if tracked_ids:
            session.query(HistorySyncState).filter(
                HistorySyncState.item_id.in_(tracked_ids)
            ).update({HistorySyncState.priority: 0}, synchronize_session=False)

        # Popular (has price stats with lots) → priority 1
        popular_ids = [
            s.item_id for s in
            session.query(ItemPriceStats).filter(ItemPriceStats.lots_count > 0).all()
        ]
        for pid in popular_ids:
            if pid not in tracked_ids:
                session.query(HistorySyncState).filter_by(item_id=pid).update(
                    {HistorySyncState.priority: 1}, synchronize_session=False
                )
        session.commit()


# ══════════════════════════════════════════════════════════════
#  Цикл синхронизации
# ══════════════════════════════════════════════════════════════

async def run_incremental_job():
    """Job: инкрементальная синхронизация — подгружает новые продажи для всех предметов с sync state."""
    with SessionLocal() as session:
        # Get items that have completed full download (they need incremental updates)
        # + tracked items (priority)
        states = (
            session.query(HistorySyncState)
            .filter(HistorySyncState.full_download_done == True)
            .filter(HistorySyncState.status != "syncing")
            .order_by(HistorySyncState.priority, HistorySyncState.last_sync_at.asc().nullsfirst())
            .limit(20)
            .all()
        )
        item_ids = [s.item_id for s in states]

    if not item_ids:
        return

    total = 0
    for item_id in item_ids:
        try:
            added = await incremental_sync(item_id)
            total += added
        except Exception as exc:
            logger.warning("Incremental sync error %s: %s", item_id, exc)
            with SessionLocal() as session:
                st = _get_sync_state(session, item_id)
                st.status = "error"
                st.error_msg = str(exc)[:250]
                session.commit()

    if total:
        logger.info("📥 Incremental sync: +%d новых записей для %d предметов", total, len(item_ids))


async def run_full_download_job():
    """
    Job: продолжает полную выгрузку следующего предмета из очереди.
    Делает 20 запросов за вызов (~10 сек), потом уступает.
    """
    update_priorities()

    with SessionLocal() as session:
        # Берём следующий предмет для выгрузки (приоритет → не завершённый)
        st = (
            session.query(HistorySyncState)
            .filter(HistorySyncState.full_download_done == False)
            .filter(HistorySyncState.status != "syncing")
            .order_by(HistorySyncState.priority, HistorySyncState.oldest_stored_offset)
            .first()
        )
        if not st:
            return
        item_id = st.item_id

    try:
        added = await full_download_chunk(item_id, max_requests=50)
        if added:
            logger.info("📥 Full download %s: +%d записей", item_id, added)
    except Exception as exc:
        logger.warning("Full download error %s: %s", item_id, exc)
        with SessionLocal() as session:
            st = _get_sync_state(session, item_id)
            st.status = "error"
            st.error_msg = str(exc)[:250]
            session.commit()


def init_sync_states():
    """Создаёт HistorySyncState для всех известных предметов."""
    from services.item_loader import item_db
    with SessionLocal() as session:
        existing = {s.item_id for s in session.query(HistorySyncState.item_id).all()}
        added = 0
        for item in item_db._items.values():
            if item.item_id not in existing and item.api_supported:
                session.add(HistorySyncState(item_id=item.item_id))
                added += 1
        session.commit()
        if added:
            logger.info("📋 Создано %d sync states", added)

