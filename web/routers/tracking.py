"""API отслеживания предметов."""
from fastapi import APIRouter
from pydantic import BaseModel
from config import RANK_NAMES
from db.repository import (
    get_active_tracked_items,
    add_tracked_item,
    remove_tracked_item,
    get_avg_price,
    get_avg_sale_price,
)
from services.item_loader import item_db

router = APIRouter(tags=["tracking"])


def _track_icon(gi) -> str:
    if not gi:
        return ""
    p = gi.icon_path
    if not p or p.strip() == "":
        # Для wiki-предметов пробуем кастомную иконку
        if not gi.api_supported:
            return f"/custom-icons/{gi.item_id}.png"
        return ""
    if p.startswith("http"):
        return p
    if p.startswith("/icons/"):
        return p
    return f"/icons/{p.lstrip('/')}"


class TrackRequest(BaseModel):
    item_id: str


@router.get("/tracked")
async def get_tracked():
    items = get_active_tracked_items()
    result = []
    for t in items:
        gi = item_db.get(t.item_id)
        result.append({
            "item_id": t.item_id,
            "name": t.name,
            "category": t.category,
            "icon": _track_icon(gi),
            "color": gi.color if gi else "DEFAULT",
            "rank_name": RANK_NAMES.get(gi.color, "") if gi else "",
            "api_supported": gi.api_supported if gi else True,
            "avg_24h": get_avg_price(t.item_id, hours=24),
            "avg_7d": get_avg_sale_price(t.item_id, hours=168),
        })
    return result


@router.post("/tracked")
async def track_item(req: TrackRequest):
    gi = item_db.get(req.item_id)
    if not gi:
        return {"error": "not_found"}
    add_tracked_item(req.item_id, gi.name_ru, gi.category)
    return {"ok": True, "name": gi.name_ru}


@router.delete("/tracked/{item_id}")
async def untrack_item(item_id: str):
    ok = remove_tracked_item(item_id)
    return {"ok": ok}

