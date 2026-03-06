"""API отслеживания предметов (избранное — per-user)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List
from config import RANK_NAMES
from db.repository import (
    get_active_tracked_items,
    add_tracked_item,
    remove_tracked_item,
)
from db.models import User, SessionLocal, TrackedItem
from web.auth import get_current_user, require_user
from services.item_loader import item_db

router = APIRouter(tags=["tracking"])


def _track_icon(gi) -> str:
    if not gi:
        return ""
    p = gi.icon_path
    if not p or p.strip() == "":
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


class ReorderRequest(BaseModel):
    ids: List[str]


@router.get("/tracked")
async def get_tracked(user: User = Depends(get_current_user)):
    if not user:
        return []  # Не авторизован — пустой список
    items = get_active_tracked_items(user_id=user.id)
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
            "sort_order": getattr(t, 'sort_order', 0) or 0,
        })
    result.sort(key=lambda x: x["sort_order"])
    return result


@router.post("/tracked")
async def track_item(req: TrackRequest, user: User = Depends(require_user)):
    gi = item_db.get(req.item_id)
    if not gi:
        return {"error": "not_found"}
    add_tracked_item(req.item_id, gi.name_ru, gi.category, user_id=user.id)
    return {"ok": True, "name": gi.name_ru}


@router.post("/tracked/reorder")
async def reorder_tracked(req: ReorderRequest, user: User = Depends(require_user)):
    """Установить порядок избранных предметов."""
    with SessionLocal() as session:
        for idx, item_id in enumerate(req.ids):
            row = session.query(TrackedItem).filter_by(
                item_id=item_id, user_id=user.id, is_active=True
            ).first()
            if row:
                row.sort_order = idx
        session.commit()
    return {"ok": True}


@router.delete("/tracked/{item_id}")
async def untrack_item(item_id: str, user: User = Depends(require_user)):
    ok = remove_tracked_item(item_id, user_id=user.id)
    return {"ok": ok}

