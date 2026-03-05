"""API: профили пользователей."""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from config import BASE_DIR
from db.models import SessionLocal, User
from web.auth import get_current_user, require_user

router = APIRouter(tags=["users"])

AVATARS_DIR = BASE_DIR / "uploads" / "avatars"


class ProfileUpdate(BaseModel):
    game_nickname: Optional[str] = None
    discord: Optional[str] = None
    bio: Optional[str] = None
    display_name: Optional[str] = None


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return _user_dict(user)


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
        session.commit()
        session.refresh(u)
        return _user_dict(u)


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(require_user)):
    """Загрузка аватара пользователя."""
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
async def get_user(user_id: int):
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user_id).first()
        if not u:
            return {"error": "Не найден"}
        return _user_dict(u)


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "telegram_id": u.telegram_id,
        "telegram_username": u.telegram_username,
        "display_name": u.display_name,
        "game_nickname": u.game_nickname,
        "discord": u.discord,
        "bio": u.bio,
        "avatar_url": u.avatar_url,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }

