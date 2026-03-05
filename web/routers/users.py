"""API: профили пользователей, подписки, репутация."""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from config import BASE_DIR
from db.models import SessionLocal, User, UserFollow, ReputationReview, MarketListing, UserNotification
from web.auth import get_current_user, require_user

router = APIRouter(tags=["users"])

AVATARS_DIR = BASE_DIR / "uploads" / "avatars"

# Predefined chat colors
CHAT_COLORS = [
    "#e57373", "#f06292", "#ba68c8", "#9575cd", "#7986cb",
    "#64b5f6", "#4fc3f7", "#4dd0e1", "#4db6ac", "#81c784",
    "#aed581", "#dce775", "#fff176", "#ffd54f", "#ffb74d", "#ff8a65",
]


class ProfileUpdate(BaseModel):
    game_nickname: Optional[str] = None
    discord: Optional[str] = None
    bio: Optional[str] = None
    display_name: Optional[str] = None
    chat_color: Optional[str] = None


class ReviewData(BaseModel):
    listing_id: int
    score: int  # +1 or -1
    comment: Optional[str] = None


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return _full_user_dict(user)


@router.put("/me")
async def update_me(data: ProfileUpdate, user: User = Depends(require_user)):
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user.id).first()
        if data.display_name is not None:
            u.display_name = data.display_name[:128]
        if data.game_nickname is not None:
            u.game_nickname = data.game_nickname[:128] or None
        if data.discord is not None:
            u.discord = data.discord[:128] or None
        if data.bio is not None:
            u.bio = data.bio[:500] or None
        if data.chat_color is not None:
            if data.chat_color in CHAT_COLORS or (data.chat_color.startswith("#") and len(data.chat_color) == 7):
                u.chat_color = data.chat_color
        session.commit()
        session.refresh(u)
        return _full_user_dict(u)


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(require_user)):
    os.makedirs(AVATARS_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "png"
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        return {"error": "Допустимые форматы: png, jpg, webp, gif"}
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        return {"error": "Максимальный размер: 2 МБ"}
    fname = f"{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    path = AVATARS_DIR / fname
    with open(path, "wb") as f:
        f.write(content)
    avatar_url = f"/uploads/avatars/{fname}"
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user.id).first()
        u.avatar_url = avatar_url
        session.commit()
    return {"avatar_url": avatar_url}


@router.get("/users/{user_id}")
async def get_user(user_id: int, user: User = Depends(get_current_user)):
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user_id).first()
        if not u:
            return {"error": "Не найден"}
        d = _public_user_dict(u)
        # Add follow info
        if user:
            f = session.query(UserFollow).filter_by(follower_id=user.id, target_id=user_id).first()
            d["is_following"] = f is not None
            d["is_self"] = user.id == user_id
        else:
            d["is_following"] = False
            d["is_self"] = False
        # Followers count
        d["followers_count"] = session.query(UserFollow).filter_by(target_id=user_id).count()
        return d


@router.get("/chat-colors")
async def get_chat_colors():
    return CHAT_COLORS


# ── Follow / Unfollow ──

@router.post("/users/{user_id}/follow")
async def follow_user(user_id: int, user: User = Depends(require_user)):
    if user_id == user.id:
        return {"error": "Нельзя подписаться на себя"}
    with SessionLocal() as session:
        existing = session.query(UserFollow).filter_by(follower_id=user.id, target_id=user_id).first()
        if existing:
            return {"ok": True, "following": True}
        session.add(UserFollow(follower_id=user.id, target_id=user_id))
        # Notify target
        session.add(UserNotification(
            user_id=user_id, type="follow",
            title="👤 Новый подписчик",
            body=f"{user.display_name} подписался на вас",
            link=f"#/user/{user.id}",
        ))
        session.commit()
        return {"ok": True, "following": True}


@router.delete("/users/{user_id}/follow")
async def unfollow_user(user_id: int, user: User = Depends(require_user)):
    with SessionLocal() as session:
        f = session.query(UserFollow).filter_by(follower_id=user.id, target_id=user_id).first()
        if f:
            session.delete(f)
            session.commit()
        return {"ok": True, "following": False}


# ── Reputation / Reviews ──

@router.post("/review")
async def leave_review(data: ReviewData, user: User = Depends(require_user)):
    if data.score not in (1, -1):
        return {"error": "Оценка: +1 или -1"}
    with SessionLocal() as session:
        listing = session.query(MarketListing).filter_by(id=data.listing_id).first()
        if not listing:
            return {"error": "Объявление не найдено"}
        if listing.status != "sold":
            return {"error": "Отзыв можно оставить только после продажи"}
        if listing.user_id == user.id:
            return {"error": "Нельзя оставить отзыв себе"}
        existing = session.query(ReputationReview).filter_by(
            listing_id=data.listing_id, reviewer_id=user.id
        ).first()
        if existing:
            return {"error": "Вы уже оставили отзыв"}
        review = ReputationReview(
            listing_id=data.listing_id,
            reviewer_id=user.id,
            target_id=listing.user_id,
            score=data.score,
            comment=(data.comment or "")[:256],
        )
        session.add(review)
        # Update reputation
        target = session.query(User).filter_by(id=listing.user_id).first()
        if target:
            target.reputation = (target.reputation or 0) + data.score
        session.commit()
        return {"ok": True, "new_reputation": target.reputation if target else 0}


@router.get("/users/{user_id}/reviews")
async def get_reviews(user_id: int):
    with SessionLocal() as session:
        rows = session.query(ReputationReview, User).outerjoin(
            User, ReputationReview.reviewer_id == User.id
        ).filter(ReputationReview.target_id == user_id).order_by(
            ReputationReview.id.desc()
        ).limit(50).all()
        return [
            {"id": r.id, "score": r.score, "comment": r.comment,
             "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
             "reviewer": {"id": u.id, "display_name": u.display_name} if u else None}
            for r, u in rows
        ]


# ── Helpers ──

def _full_user_dict(u: User) -> dict:
    """Full user dict (for /me endpoint — includes private fields)."""
    return {
        "id": u.id,
        "telegram_id": u.telegram_id,
        "telegram_username": u.telegram_username,
        "display_name": u.display_name,
        "game_nickname": u.game_nickname,
        "discord": u.discord,
        "bio": u.bio,
        "avatar_url": u.avatar_url,
        "chat_color": u.chat_color,
        "reputation": u.reputation or 0,
        "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
    }


def _public_user_dict(u: User) -> dict:
    """Public user dict — NO telegram_username for safety."""
    return {
        "id": u.id,
        "display_name": u.display_name,
        "game_nickname": u.game_nickname,
        "discord": u.discord,
        "bio": u.bio,
        "avatar_url": u.avatar_url,
        "chat_color": u.chat_color,
        "reputation": u.reputation or 0,
        "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
    }
