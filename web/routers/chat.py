"""API: чат внутри приложения."""
import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from db.models import SessionLocal, ChatMessage, User
from web.auth import require_user, get_current_user

router = APIRouter(tags=["chat"])
CHANNELS = {"general": "💬 Общий", "trading": "💰 Торговля", "offtopic": "🎮 Оффтопик"}

class SendMessage(BaseModel):
    text: str
    reply_to_id: int = 0

@router.get("/chat/channels")
async def list_channels():
    return [{"id": k, "name": v} for k, v in CHANNELS.items()]

@router.get("/chat/{channel}/messages")
async def get_messages(channel: str, since_id: int = 0, limit: int = 50):
    limit = max(1, min(limit, 100))
    if since_id > 0:
        for _ in range(20):
            msgs = _fetch(channel, since_id, limit)
            if msgs:
                return msgs
            await asyncio.sleep(0.5)
        return []
    return _fetch(channel, 0, limit)

def _fetch(channel, since_id, limit):
    with SessionLocal() as session:
        q = session.query(ChatMessage, User).outerjoin(User, ChatMessage.user_id == User.id).filter(ChatMessage.channel == channel)
        if since_id > 0:
            q = q.filter(ChatMessage.id > since_id)
        rows = q.order_by(ChatMessage.id.desc()).limit(limit).all()
        return [{"id": m.id, "text": m.text, "channel": m.channel, "reply_to_id": m.reply_to_id, "created_at": m.created_at.isoformat() if m.created_at else None, "user": {"id": u.id, "display_name": u.display_name, "game_nickname": u.game_nickname, "telegram_username": u.telegram_username, "avatar_url": u.avatar_url} if u else {"id": 0, "display_name": "Аноним"}} for m, u in reversed(rows)]

@router.post("/chat/{channel}/messages")
async def send_message(channel: str, data: SendMessage, user: User = Depends(require_user)):
    text = data.text.strip()[:2000]
    if not text:
        return {"error": "Пустое сообщение"}
    # Allow DM channels (dm:id1_id2) and standard channels
    if not channel.startswith("dm:") and channel not in CHANNELS:
        return {"error": "Неизвестный канал"}
    with SessionLocal() as session:
        msg = ChatMessage(user_id=user.id, channel=channel, text=text, reply_to_id=data.reply_to_id or None)
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return {"id": msg.id, "text": msg.text, "channel": msg.channel, "created_at": msg.created_at.isoformat() if msg.created_at else None, "user": {"id": user.id, "display_name": user.display_name, "avatar_url": user.avatar_url}}

@router.get("/chat/dm/{target_user_id}")
async def init_dm(target_user_id: int, user: User = Depends(require_user)):
    """Инициировать DM канал с пользователем. Возвращает channel ID."""
    ids = sorted([user.id, target_user_id])
    channel = f"dm:{ids[0]}_{ids[1]}"
    with SessionLocal() as session:
        target = session.query(User).filter_by(id=target_user_id).first()
        target_name = target.display_name if target else "Пользователь"
    return {"channel": channel, "target_name": target_name}


