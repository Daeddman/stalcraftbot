"""API: торговая площадка (маркетплейс v2)."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db.models import SessionLocal, MarketListing, PriceOffer, User, ReputationReview, UserNotification
from web.auth import require_user, get_current_user
from services.item_loader import item_db
from sqlalchemy import func

router = APIRouter(tags=["marketplace"])

# ── Category group detection ──
def _cat_group(item_id: str) -> str:
    gi = item_db.get(item_id)
    if not gi:
        return "other"
    cat = gi.category
    if cat.startswith("artefact"):
        return "artefact"
    if cat.startswith("weapon"):
        return "weapon"
    if cat.startswith("armor") or cat.startswith("outfit"):
        return "armor"
    if cat.startswith("attachment"):
        return "attachment"
    return "other"


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

class OfferCreate(BaseModel):
    price: int
    message: Optional[str] = None

class OfferAction(BaseModel):
    status: str  # accepted / declined


@router.get("/market")
async def list_market(
    item_id: str = "",
    listing_type: str = "",
    status: str = "active",
    search: str = "",
    category: str = "",
    min_price: int = 0,
    max_price: int = 0,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 20,
):
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
        if category and category != "all":
            q = q.filter(MarketListing.category_group == category)
        if min_price > 0:
            q = q.filter(MarketListing.price >= min_price)
        if max_price > 0:
            q = q.filter(MarketListing.price <= max_price)

        total = q.count()

        # Sorting
        if sort == "price_asc":
            q = q.order_by(MarketListing.price.asc())
        elif sort == "price_desc":
            q = q.order_by(MarketListing.price.desc())
        else:  # newest
            q = q.order_by(MarketListing.created_at.desc())

        rows = q.offset(offset).limit(per_page).all()
        items = []
        for l, u in rows:
            gi = item_db.get(l.item_id)
            is_art = gi and gi.category.startswith("artefact") if gi else False
            # Count offers on this listing
            offer_cnt = session.query(func.count(PriceOffer.id)).filter(
                PriceOffer.listing_id == l.id, PriceOffer.status == "pending"
            ).scalar() or 0
            items.append({
                "id": l.id, "item_id": l.item_id, "item_name": l.item_name or (gi.name_ru if gi else l.item_id),
                "icon": _icon(gi), "listing_type": l.listing_type, "price": l.price,
                "amount": l.amount, "quality": l.quality, "upgrade_level": l.upgrade_level,
                "description": l.description, "status": l.status,
                "category_group": l.category_group or "other",
                "color": gi.color if gi else "DEFAULT",
                "is_artefact": is_art,
                "sold_price": l.sold_price,
                "offers_count": offer_cnt,
                "created_at": l.created_at.isoformat() + "Z" if l.created_at else None,
                "expires_at": l.expires_at.isoformat() + "Z" if l.expires_at else None,
                "user": _user_short(u, session) if u else None,
            })
        return {"items": items, "total": total, "pages": max(1, -(-total // per_page))}


def _user_short(u, session):
    """Build user dict with reputation stats."""
    rep = u.reputation if hasattr(u, 'reputation') else 0
    # Count completed deals
    deals = session.query(func.count(MarketListing.id)).filter(
        MarketListing.user_id == u.id, MarketListing.status == "sold"
    ).scalar() or 0
    # Count reviews
    reviews = session.query(func.count(ReputationReview.id)).filter(
        ReputationReview.target_id == u.id
    ).scalar() or 0
    return {
        "id": u.id,
        "display_name": u.display_name,
        "game_nickname": getattr(u, 'game_nickname', None),
        "avatar_url": u.avatar_url,
        "reputation": rep,
        "deals_count": deals,
        "reviews_count": reviews,
    }


@router.get("/market/seller/{user_id}/stats")
async def seller_stats(user_id: int):
    """Публичная статистика продавца."""
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user_id).first()
        if not u:
            return {"error": "Пользователь не найден"}
        deals = session.query(func.count(MarketListing.id)).filter(
            MarketListing.user_id == user_id, MarketListing.status == "sold"
        ).scalar() or 0
        active = session.query(func.count(MarketListing.id)).filter(
            MarketListing.user_id == user_id, MarketListing.status == "active"
        ).scalar() or 0
        reviews = session.query(ReputationReview).filter_by(target_id=user_id).order_by(
            ReputationReview.created_at.desc()
        ).limit(10).all()
        pos = sum(1 for r in reviews if r.score > 0)
        neg = sum(1 for r in reviews if r.score < 0)
        review_list = [{
            "score": r.score, "comment": r.comment,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        } for r in reviews]
        return {
            "deals_count": deals,
            "active_count": active,
            "reputation": u.reputation if hasattr(u, 'reputation') else 0,
            "positive_reviews": pos,
            "negative_reviews": neg,
            "recent_reviews": review_list,
        }


@router.post("/market")
async def create_listing(data: CreateListing, user: User = Depends(require_user)):
    gi = item_db.get(data.item_id)
    name = gi.name_ru if gi else data.item_id
    cat_group = _cat_group(data.item_id)
    with SessionLocal() as session:
        listing = MarketListing(
            user_id=user.id, item_id=data.item_id, item_name=name,
            listing_type=data.listing_type, price=data.price, amount=data.amount,
            quality=data.quality, upgrade_level=data.upgrade_level,
            description=(data.description or "")[:500],
            category_group=cat_group,
            expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        session.add(listing)
        session.commit()
        # Audit
        try:
            from services.audit import log_action, ACTION_LISTING_CREATE
            log_action(user.id, ACTION_LISTING_CREATE, "listing", str(listing.id),
                       {"item_id": data.item_id, "price": data.price})
        except Exception:
            pass
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
        # Audit
        try:
            from services.audit import log_action, ACTION_LISTING_UPDATE
            log_action(user.id, ACTION_LISTING_UPDATE, "listing", str(l.id),
                       {"status": data.status, "sold_price": data.sold_price})
        except Exception:
            pass
        return {"id": l.id, "status": l.status}


# ══ Offers (торг) ══

@router.post("/market/{listing_id}/offer")
async def create_offer(listing_id: int, data: OfferCreate, user: User = Depends(require_user)):
    """Предложить свою цену на объявление."""
    with SessionLocal() as session:
        listing = session.query(MarketListing).filter_by(id=listing_id, status="active").first()
        if not listing:
            return {"error": "Объявление не найдено или неактивно"}
        if listing.user_id == user.id:
            return {"error": "Нельзя предложить цену на своё объявление"}
        if data.price <= 0:
            return {"error": "Цена должна быть больше 0"}
        # Check existing pending offer from this user
        existing = session.query(PriceOffer).filter_by(
            listing_id=listing_id, user_id=user.id, status="pending"
        ).first()
        if existing:
            # Update existing offer
            existing.price = data.price
            existing.message = (data.message or "")[:256]
            existing.updated_at = datetime.now(timezone.utc)
            session.commit()
            offer_id = existing.id
        else:
            offer = PriceOffer(
                listing_id=listing_id,
                user_id=user.id,
                seller_id=listing.user_id,
                price=data.price,
                message=(data.message or "")[:256],
            )
            session.add(offer)
            session.commit()
            offer_id = offer.id

        # Notify seller
        try:
            notif = UserNotification(
                user_id=listing.user_id,
                type="offer",
                title="💰 Новое предложение цены",
                body=f"{user.display_name} предлагает {data.price:,} ₽ за {listing.item_name}",
                link=f"#/market-my",
            )
            session.add(notif)
            session.commit()
        except Exception:
            pass

        return {"id": offer_id, "status": "pending"}


@router.get("/market/{listing_id}/offers")
async def list_offers(listing_id: int, user: User = Depends(require_user)):
    """Список предложений на объявление (только владелец видит)."""
    with SessionLocal() as session:
        listing = session.query(MarketListing).filter_by(id=listing_id).first()
        if not listing:
            return {"error": "Не найдено"}
        if listing.user_id != user.id:
            return {"error": "Только владелец видит предложения"}
        offers = session.query(PriceOffer, User).outerjoin(
            User, PriceOffer.user_id == User.id
        ).filter(PriceOffer.listing_id == listing_id).order_by(
            PriceOffer.price.desc()
        ).all()
        return [{
            "id": o.id, "price": o.price, "message": o.message, "status": o.status,
            "created_at": o.created_at.isoformat() + "Z" if o.created_at else None,
            "user": {"id": u.id, "display_name": u.display_name, "avatar_url": u.avatar_url} if u else None,
        } for o, u in offers]


@router.put("/market/offer/{offer_id}")
async def respond_offer(offer_id: int, data: OfferAction, user: User = Depends(require_user)):
    """Принять или отклонить предложение (только продавец)."""
    if data.status not in ("accepted", "declined"):
        return {"error": "Допустимо: accepted, declined"}
    with SessionLocal() as session:
        offer = session.query(PriceOffer).filter_by(id=offer_id).first()
        if not offer:
            return {"error": "Предложение не найдено"}
        if offer.seller_id != user.id:
            return {"error": "Только владелец объявления может управлять предложениями"}
        offer.status = data.status
        offer.updated_at = datetime.now(timezone.utc)
        session.commit()

        # Notify buyer
        try:
            status_text = "✅ принято" if data.status == "accepted" else "❌ отклонено"
            listing = session.query(MarketListing).filter_by(id=offer.listing_id).first()
            item_name = listing.item_name if listing else "предмет"
            notif = UserNotification(
                user_id=offer.user_id,
                type="offer_response",
                title=f"Предложение {status_text}",
                body=f"Ваше предложение {offer.price:,} ₽ за {item_name} {status_text}",
                link=f"#/market",
            )
            session.add(notif)
            session.commit()
        except Exception:
            pass

        return {"id": offer.id, "status": offer.status}


@router.get("/market/my")
async def my_listings(user: User = Depends(require_user)):
    with SessionLocal() as session:
        rows = session.query(MarketListing).filter_by(user_id=user.id).order_by(MarketListing.created_at.desc()).all()
        result = []
        for l in rows:
            gi = item_db.get(l.item_id)
            offers_cnt = session.query(func.count(PriceOffer.id)).filter(
                PriceOffer.listing_id == l.id, PriceOffer.status == "pending"
            ).scalar() or 0
            result.append({
                "id": l.id, "item_id": l.item_id, "item_name": l.item_name,
                "icon": _icon(gi), "listing_type": l.listing_type, "price": l.price,
                "amount": l.amount, "quality": l.quality, "upgrade_level": l.upgrade_level,
                "description": l.description, "status": l.status, "sold_price": l.sold_price,
                "offers_count": offers_cnt,
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

