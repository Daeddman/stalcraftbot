"""API: торговая площадка (маркетплейс)."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from db.models import SessionLocal, MarketListing, User
from web.auth import require_user, get_current_user
from services.item_loader import item_db

router = APIRouter(tags=["marketplace"])

class CreateListing(BaseModel):
    item_id: str
    listing_type: str = "sell"
    price: int
    amount: int = 1
    quality: int = -1
    upgrade_level: int = 0
    description: Optional[str] = None

class UpdateStatus(BaseModel):
    status: str  # sold / cancelled
    sold_price: Optional[int] = None

@router.get("/market")
async def list_market(item_id: str = "", listing_type: str = "", status: str = "active",
                      search: str = "", page: int = 1, per_page: int = 20):
    per_page = max(1, min(per_page, 50))
    offset = (page - 1) * per_page
    with SessionLocal() as session:
        q = session.query(MarketListing, User).outerjoin(User, MarketListing.user_id == User.id)
        if status:
            q = q.filter(MarketListing.status == status)
        if item_id:
            q = q.filter(MarketListing.item_id == item_id)
        if listing_type:
            q = q.filter(MarketListing.listing_type == listing_type)
        if search:
            q = q.filter(MarketListing.item_name.ilike(f"%{search}%"))
        total = q.count()
        rows = q.order_by(MarketListing.created_at.desc()).offset(offset).limit(per_page).all()
        items = []
        for l, u in rows:
            gi = item_db.get(l.item_id)
            items.append({
                "id": l.id, "item_id": l.item_id, "item_name": l.item_name or (gi.name_ru if gi else l.item_id),
                "icon": _icon(gi), "listing_type": l.listing_type, "price": l.price,
                "amount": l.amount, "quality": l.quality, "upgrade_level": l.upgrade_level,
                "description": l.description, "status": l.status,
                "sold_price": l.sold_price,
                "created_at": l.created_at.isoformat() + "Z" if l.created_at else None,
                "expires_at": l.expires_at.isoformat() + "Z" if l.expires_at else None,
                "user": {"id": u.id, "display_name": u.display_name, "game_nickname": u.game_nickname, "avatar_url": u.avatar_url, "reputation": getattr(u, 'reputation', 0)} if u else None,
            })
        return {"items": items, "total": total, "pages": max(1, -(-total // per_page))}

@router.post("/market")
async def create_listing(data: CreateListing, user: User = Depends(require_user)):
    gi = item_db.get(data.item_id)
    name = gi.name_ru if gi else data.item_id
    with SessionLocal() as session:
        listing = MarketListing(
            user_id=user.id, item_id=data.item_id, item_name=name,
            listing_type=data.listing_type, price=data.price, amount=data.amount,
            quality=data.quality, upgrade_level=data.upgrade_level,
            description=(data.description or "")[:500],
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        session.add(listing)
        session.commit()
        return {"id": listing.id, "status": "created"}

@router.put("/market/{listing_id}/status")
async def update_listing_status(listing_id: int, data: UpdateStatus, user: User = Depends(require_user)):
    if data.status not in ("sold", "cancelled"):
        return {"error": "Допустимые статусы: sold, cancelled"}
    with SessionLocal() as session:
        l = session.query(MarketListing).filter_by(id=listing_id).first()
        if not l:
            return {"error": "Не найдено"}
        if l.user_id != user.id:
            return {"error": "Не ваш лот"}
        l.status = data.status
        if data.status == "sold" and data.sold_price is not None:
            l.sold_price = data.sold_price
        l.updated_at = datetime.now(timezone.utc)
        session.commit()
        return {"id": l.id, "status": l.status}

@router.get("/market/my")
async def my_listings(user: User = Depends(require_user)):
    with SessionLocal() as session:
        rows = session.query(MarketListing).filter_by(user_id=user.id).order_by(MarketListing.created_at.desc()).all()
        result = []
        for l in rows:
            gi = item_db.get(l.item_id)
            result.append({
                "id": l.id, "item_id": l.item_id, "item_name": l.item_name,
                "icon": _icon(gi), "listing_type": l.listing_type, "price": l.price,
                "amount": l.amount, "quality": l.quality, "upgrade_level": l.upgrade_level,
                "description": l.description, "status": l.status, "sold_price": l.sold_price,
                "created_at": l.created_at.isoformat() + "Z" if l.created_at else None,
                "expires_at": l.expires_at.isoformat() + "Z" if l.expires_at else None,
            })
        return result

def _icon(gi):
    if not gi:
        return ""
    p = gi.icon_path
    if not p or p.strip() == "":
        return f"/custom-icons/{gi.item_id}.png" if not gi.api_supported else ""
    if p.startswith("http") or p.startswith("/icons/"):
        return p
    return f"/icons/{p.lstrip('/')}"

def expire_old_listings():
    """Фоновая задача: экспирация старых листингов."""
    with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        expired = session.query(MarketListing).filter(
            MarketListing.status == "active",
            MarketListing.expires_at < now,
        ).all()
        for l in expired:
            l.status = "expired"
        session.commit()
        return len(expired)

