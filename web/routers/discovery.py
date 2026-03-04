"""API discovery: предметы из registry, цены, лоты."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Query
from sqlalchemy import func
from db.models import SessionLocal, ItemPriceStats, PriceSample, ItemRegistry, ActiveLot, LotEvent

router = APIRouter(tags=["discovery"])

@router.get("/discovery/items")
async def discovery_items(
    q: str = Query(""), category: Optional[str] = Query(None),
    sort: str = Query("name"), order: str = Query("asc"),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    has_lots: Optional[bool] = Query(None),
):
    with SessionLocal() as session:
        qry = session.query(ItemRegistry)
        if q:
            s = f"%{q.lower()}%"
            qry = qry.filter((ItemRegistry.name.ilike(s)) | (ItemRegistry.item_id.ilike(s)))
        if category:
            qry = qry.filter(ItemRegistry.category.ilike(f"%{category}%"))
        items = qry.all()
        ids = [i.item_id for i in items]
        pm, lm = {}, {}
        if ids:
            pm = {p.item_id: p for p in session.query(ItemPriceStats).filter(ItemPriceStats.item_id.in_(ids)).all()}
            lm = dict(session.query(ActiveLot.item_id, func.count(ActiveLot.lot_id)).filter(ActiveLot.item_id.in_(ids)).group_by(ActiveLot.item_id).all())
        results = []
        for it in items:
            ps = pm.get(it.item_id)
            lc = lm.get(it.item_id, 0)
            if has_lots is True and lc == 0:
                continue
            if has_lots is False and lc > 0:
                continue
            results.append({
                "item_id": it.item_id, "name": it.name or it.item_id,
                "category": it.category, "icon_url": it.icon_url,
                "color": it.color or "DEFAULT", "source": it.source,
                "is_official_db": it.is_official_db,
                "min_price": ps.min_price if ps else None,
                "avg_price": ps.avg_price if ps else None,
                "lots_count": ps.lots_count if ps else lc,
                "total_amount": ps.total_amount if ps else 0,
                "last_seen": it.last_seen_at.isoformat() if it.last_seen_at else None,
            })
        desc = order == "desc"
        sk = {
            "name": lambda x: (x["name"] or "").lower(),
            "min_price": lambda x: x["min_price"] or (10**15 if not desc else 0),
            "lots_count": lambda x: x["lots_count"] or 0,
            "last_seen": lambda x: x["last_seen"] or "",
        }
        results.sort(key=sk.get(sort, sk["name"]), reverse=desc)
        total = len(results)
        return {"total": total, "items": results[offset:offset + limit]}


@router.get("/discovery/items/{item_id}")
async def discovery_item_detail(item_id: str):
    with SessionLocal() as session:
        reg = session.get(ItemRegistry, item_id)
        if not reg:
            return {"error": "not_found"}
        ps = session.get(ItemPriceStats, item_id)
        lc = session.query(func.count(ActiveLot.lot_id)).filter(ActiveLot.item_id == item_id).scalar() or 0
        return {
            "item_id": reg.item_id, "name": reg.name or reg.item_id,
            "category": reg.category, "icon_url": reg.icon_url,
            "color": reg.color or "DEFAULT", "source": reg.source,
            "min_price": ps.min_price if ps else None,
            "avg_price": ps.avg_price if ps else None,
            "lots_count": lc,
        }


@router.get("/discovery/items/{item_id}/lots")
async def discovery_item_lots(item_id: str, sort: str = Query("buyout_price"), order: str = Query("asc")):
    with SessionLocal() as session:
        qry = session.query(ActiveLot).filter(ActiveLot.item_id == item_id)
        cm = {"buyout_price": ActiveLot.buyout_price, "quality": ActiveLot.quality, "amount": ActiveLot.amount}
        c = cm.get(sort, ActiveLot.buyout_price)
        qry = qry.order_by(c.desc() if order == "desc" else c.asc())
        lots = qry.all()
        return {"item_id": item_id, "total": len(lots), "lots": [
            {"lot_id": l.lot_id, "buyout_price": l.buyout_price, "current_price": l.current_price,
             "amount": l.amount, "quality": l.quality, "upgrade_level": l.upgrade_level,
             "start_time": l.start_time, "end_time": l.end_time} for l in lots]}


@router.get("/discovery/items/{item_id}/history")
async def discovery_history(item_id: str, days: int = Query(7, ge=1, le=90)):
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        samples = session.query(PriceSample).filter(
            PriceSample.item_id == item_id, PriceSample.sampled_at >= since
        ).order_by(PriceSample.sampled_at.asc()).all()
        return {"item_id": item_id, "samples": [
            {"time": s.sampled_at.isoformat(), "min": s.min_price, "avg": s.avg_price,
             "max": s.max_price, "lots": s.lots_count} for s in samples]}


@router.get("/discovery/items/{item_id}/events")
async def discovery_events(item_id: str, event_type: Optional[str] = Query(None), limit: int = Query(50)):
    with SessionLocal() as session:
        qry = session.query(LotEvent).filter(LotEvent.item_id == item_id)
        if event_type:
            qry = qry.filter(LotEvent.event_type == event_type)
        events = qry.order_by(LotEvent.event_at.desc()).limit(limit).all()
        return {"item_id": item_id, "total": len(events), "events": [
            {"lot_id": e.lot_id, "event_type": e.event_type, "price": e.price,
             "amount": e.amount, "time": e.event_at.isoformat() if e.event_at else None} for e in events]}


@router.get("/discovery/stats")
async def discovery_stats():
    with SessionLocal() as session:
        return {
            "total_items": session.query(func.count(ItemRegistry.item_id)).scalar() or 0,
            "official_db": session.query(func.count(ItemRegistry.item_id)).filter(ItemRegistry.is_official_db.is_(True)).scalar() or 0,
            "observed": session.query(func.count(ItemRegistry.item_id)).filter(ItemRegistry.source == "observed").scalar() or 0,
            "active_lots": session.query(func.count(ActiveLot.lot_id)).scalar() or 0,
            "priced_items": session.query(func.count(ItemPriceStats.item_id)).scalar() or 0,
        }
