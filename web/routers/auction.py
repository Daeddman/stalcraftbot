"""API аукциона — текущие лоты и история."""
from fastapi import APIRouter
from api.auction import get_active_lots, get_price_history
from db.repository import get_quality_breakdown, get_avg_price, get_avg_sale_price

router = APIRouter(tags=["auction"])


@router.get("/auction/{item_id}/lots")
async def lots(item_id: str, limit: int = 20, offset: int = 0):
    data = await get_active_lots(item_id, limit=limit, offset=offset, additional=True)
    return data


@router.get("/auction/{item_id}/history")
async def history(item_id: str, limit: int = 20, offset: int = 0):
    data = await get_price_history(item_id, limit=limit, offset=offset, additional=True)
    return data


@router.get("/auction/{item_id}/prices")
async def price_summary(item_id: str):
    """Сводка цен из нашей БД (средние, разбивка по качеству)."""
    return {
        "avg_24h": get_avg_price(item_id, hours=24),
        "avg_7d": get_avg_sale_price(item_id, hours=168),
        "breakdown": get_quality_breakdown(item_id, hours=168),
    }

