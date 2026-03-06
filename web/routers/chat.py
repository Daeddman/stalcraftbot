"""API: чат внутри приложения — общий, торговый, личные сообщения, реакции, стикеры."""
import time
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from db.models import (
    SessionLocal, ChatMessage, ChatReaction, User, MarketListing,
    UserNotification,
)
from sqlalchemy import func
from web.auth import require_user, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

CHANNELS = {"general": "💬 Общий", "trading": "💰 Торговый"}
MAX_PUBLIC_MESSAGES = 2000

_spam_tracker: dict[int, float] = {}
SPAM_COOLDOWN = 3.0
MAX_GENERAL_LEN = 500

# ── Доступные реакции ──
ALLOWED_REACTIONS = {"👍", "❤️", "🔥", "😂", "😢", "💀", "🎉", "💎", "☢️", "👎"}

# ── Кастомные STALCRAFT стикеры ──
STICKERS = [
    {"code": "zone_clear", "emoji": "✅", "label": "Зона чиста"},
    {"code": "emission", "emoji": "☢️", "label": "Выброс!"},
    {"code": "loot", "emoji": "💰", "label": "Лут!"},
    {"code": "artifact", "emoji": "💎", "label": "Артефакт"},
    {"code": "death", "emoji": "💀", "label": "Смерть"},
    {"code": "run", "emoji": "🏃", "label": "Бежим!"},
    {"code": "anomaly", "emoji": "⚡", "label": "Аномалия"},
    {"code": "deal", "emoji": "🤝", "label": "Сделка"},
    {"code": "scam", "emoji": "🚫", "label": "Скам"},
    {"code": "gg", "emoji": "🎮", "label": "GG"},
    {"code": "camp", "emoji": "🏕️", "label": "Лагерь"},
    {"code": "sniper", "emoji": "🔫", "label": "Снайпер"},
    {"code": "heal", "emoji": "💊", "label": "Хилка"},
    {"code": "trade", "emoji": "📦", "label": "Трейд"},
    {"code": "money", "emoji": "💵", "label": "Деньги"},
    {"code": "fire", "emoji": "🔥", "label": "Огонь"},
]

STICKER_MAP = {s["code"]: s for s in STICKERS}


class SendMessage(BaseModel):
    text: str = ""
    reply_to_id: int = 0
    listing_id: Optional[int] = None
    sticker: Optional[str] = None  # sticker code


class ReactionData(BaseModel):
    emoji: str


@router.get("/chat/channels")
async def list_channels():
    return [{"id": k, "name": v} for k, v in CHANNELS.items()]


@router.get("/chat/stickers")
async def get_stickers():
    """Список доступных стикеров."""
    return STICKERS


@router.get("/chat/{channel}/messages")
async def get_messages(channel: str, since_id: int = 0, limit: int = 50):
    limit = max(1, min(limit, 100))
    with SessionLocal() as session:
        q = session.query(ChatMessage, User).outerjoin(
            User, ChatMessage.user_id == User.id
        ).filter(ChatMessage.channel == channel)
        if since_id > 0:
            q = q.filter(ChatMessage.id > since_id)
        rows = q.order_by(ChatMessage.id.desc()).limit(limit).all()

        messages = []
        for m, u in reversed(rows):
            d = _msg_dict(m, u)
            # Загружаем реакции для этого сообщения
            d["reactions"] = _get_reactions(session, m.id)
            # Если есть reply — загружаем цитируемое сообщение
            if m.reply_to_id:
                d["reply_to"] = _get_reply_preview(session, m.reply_to_id)
            messages.append(d)

        return messages


@router.post("/chat/{channel}/messages")
async def send_message(channel: str, data: SendMessage, user: User = Depends(require_user)):
    text = (data.text or "").strip()
    sticker = data.sticker

    # Стикер вместо текста
    if sticker:
        if sticker not in STICKER_MAP:
            return {"error": "Неизвестный стикер"}
        text = text or ""
    else:
        if not text:
            return {"error": "Пустое сообщение"}

    is_dm = channel.startswith("dm:")

    if not is_dm and channel not in CHANNELS:
        return {"error": "Неизвестный канал"}

    if is_dm:
        parts = channel.replace("dm:", "").split("_")
        if len(parts) == 2:
            ids = [int(x) for x in parts]
            if user.id not in ids:
                return {"error": "Нет доступа к этому чату"}

    if channel == "general":
        text = text[:MAX_GENERAL_LEN]
        now = time.time()
        last = _spam_tracker.get(user.id, 0)
        if now - last < SPAM_COOLDOWN:
            return {"error": f"Подождите {int(SPAM_COOLDOWN - (now - last))+1} сек"}
        _spam_tracker[user.id] = now

    if channel == "trading" and not data.listing_id:
        text = text[:1000]

    with SessionLocal() as session:
        msg = ChatMessage(
            user_id=user.id, channel=channel,
            text=text[:2000],
            reply_to_id=data.reply_to_id or None,
            sticker=sticker,
        )
        session.add(msg)

        # Update online status
        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(msg)

        if not is_dm:
            _trim_channel(session, channel, MAX_PUBLIC_MESSAGES)

        result = _msg_dict(msg, user)
        result["reactions"] = []
        if msg.reply_to_id:
            result["reply_to"] = _get_reply_preview(session, msg.reply_to_id)

    if is_dm:
        _notify_dm(user, channel, text or f"[стикер: {STICKER_MAP.get(sticker, {}).get('label', sticker)}]")
    if data.listing_id:
        _notify_listing_reply(user, data.listing_id, text)

    return result


# ── Реакции ──

@router.post("/chat/messages/{message_id}/reactions")
async def toggle_reaction(message_id: int, data: ReactionData, user: User = Depends(require_user)):
    """Toggle реакции: если уже есть — удаляем, если нет — добавляем."""
    emoji = data.emoji.strip()
    if emoji not in ALLOWED_REACTIONS:
        return {"error": "Недопустимая реакция"}

    with SessionLocal() as session:
        # Проверяем что сообщение существует
        msg = session.query(ChatMessage).filter_by(id=message_id).first()
        if not msg:
            return {"error": "Сообщение не найдено"}

        existing = session.query(ChatReaction).filter_by(
            message_id=message_id, user_id=user.id, emoji=emoji
        ).first()

        if existing:
            session.delete(existing)
            action = "removed"
        else:
            session.add(ChatReaction(
                message_id=message_id, user_id=user.id, emoji=emoji,
            ))
            action = "added"

        session.commit()

        # Возвращаем обновлённые реакции
        reactions = _get_reactions(session, message_id)

        # Update online status
        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)
            session.commit()

        return {"action": action, "reactions": reactions}


@router.get("/chat/messages/{message_id}/reactions")
async def get_message_reactions(message_id: int):
    """Получить реакции для сообщения."""
    with SessionLocal() as session:
        return _get_reactions(session, message_id)


# ── Онлайн-статус (heartbeat) ──

@router.post("/heartbeat")
async def heartbeat(user: User = Depends(require_user)):
    """Обновить last_active_at для онлайн-статуса."""
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)
            session.commit()
    return {"ok": True}


@router.get("/online-users")
async def online_users():
    """Список онлайн пользователей (активны < 5 мин)."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
    with SessionLocal() as session:
        users = session.query(User).filter(
            User.last_active_at != None,
            User.last_active_at >= threshold,
        ).all()
        return [{"id": u.id, "display_name": u.display_name} for u in users]


# ── DM ──

@router.get("/chat/dm/{target_user_id}")
async def init_dm(target_user_id: int, user: User = Depends(require_user)):
    if target_user_id == user.id:
        return {"error": "Нельзя написать самому себе"}
    ids = sorted([user.id, target_user_id])
    channel = f"dm:{ids[0]}_{ids[1]}"
    with SessionLocal() as session:
        target = session.query(User).filter_by(id=target_user_id).first()
        target_name = target.display_name if target else "Пользователь"
    return {"channel": channel, "target_name": target_name}


@router.get("/chat/dm-list")
async def dm_list(user: User = Depends(require_user)):
    with SessionLocal() as session:
        from sqlalchemy import or_
        channels = session.query(ChatMessage.channel).filter(
            or_(
                ChatMessage.channel.like(f"dm:{user.id}_%"),
                ChatMessage.channel.like(f"dm:%_{user.id}"),
            )
        ).distinct().all()
        result = []
        for (ch,) in channels:
            parts = ch.replace("dm:", "").split("_")
            other_id = int(parts[0]) if int(parts[1]) == user.id else int(parts[1])
            other = session.query(User).filter_by(id=other_id).first()
            last_msg = session.query(ChatMessage).filter_by(channel=ch).order_by(
                ChatMessage.id.desc()
            ).first()
            result.append({
                "channel": ch,
                "user": _online_user_dict(other) if other else None,
                "last_message": last_msg.text[:50] if last_msg else "",
                "last_at": last_msg.created_at.isoformat() + "Z" if last_msg and last_msg.created_at else None,
            })
        result.sort(key=lambda x: x["last_at"] or "", reverse=True)
        return result


# ── Notifications ──

@router.get("/notifications")
async def get_notifications(user: User = Depends(require_user), limit: int = 20):
    with SessionLocal() as session:
        rows = session.query(UserNotification).filter_by(user_id=user.id).order_by(
            UserNotification.id.desc()
        ).limit(limit).all()
        unread = session.query(UserNotification).filter_by(user_id=user.id, is_read=False).count()
        return {
            "items": [{"id": n.id, "type": n.type, "title": n.title, "body": n.body,
                        "link": n.link, "is_read": n.is_read,
                        "created_at": n.created_at.isoformat() + "Z" if n.created_at else None} for n in rows],
            "unread": unread,
        }


@router.post("/notifications/read")
async def mark_notifications_read(user: User = Depends(require_user)):
    with SessionLocal() as session:
        session.query(UserNotification).filter_by(user_id=user.id, is_read=False).update({"is_read": True})
        session.commit()
        return {"ok": True}


# ── Helpers ──

def _msg_dict(m, u):
    sticker_data = None
    if m.sticker and m.sticker in STICKER_MAP:
        sticker_data = STICKER_MAP[m.sticker]

    return {
        "id": m.id, "text": m.text, "channel": m.channel,
        "reply_to_id": m.reply_to_id,
        "sticker": sticker_data,
        "created_at": m.created_at.isoformat() + "Z" if m.created_at else None,
        "user": _online_user_dict(u) if u else {"id": 0, "display_name": "Аноним"},
    }


def _online_user_dict(u):
    """User dict with online status."""
    if not u:
        return {"id": 0, "display_name": "Аноним"}
    is_online = False
    if u.last_active_at:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        is_online = u.last_active_at >= threshold
    return {
        "id": u.id, "display_name": u.display_name,
        "game_nickname": getattr(u, "game_nickname", None),
        "avatar_url": u.avatar_url,
        "chat_color": getattr(u, "chat_color", None),
        "reputation": getattr(u, "reputation", 0),
        "is_online": is_online,
    }


def _get_reactions(session, message_id: int) -> list[dict]:
    """Агрегированные реакции для сообщения: [{emoji, count, user_ids}]."""
    rows = session.query(
        ChatReaction.emoji,
        func.count(ChatReaction.id).label("cnt"),
        func.group_concat(ChatReaction.user_id).label("uids"),
    ).filter_by(message_id=message_id).group_by(ChatReaction.emoji).all()

    result = []
    for emoji, cnt, uids in rows:
        uid_list = [int(x) for x in (uids or "").split(",") if x]
        result.append({"emoji": emoji, "count": cnt, "user_ids": uid_list})
    return result


def _get_reply_preview(session, reply_to_id: int) -> Optional[dict]:
    """Короткое превью цитируемого сообщения."""
    msg = session.query(ChatMessage, User).outerjoin(
        User, ChatMessage.user_id == User.id
    ).filter(ChatMessage.id == reply_to_id).first()
    if not msg:
        return None
    m, u = msg
    return {
        "id": m.id,
        "text": (m.text or "")[:100],
        "sticker": STICKER_MAP.get(m.sticker) if m.sticker else None,
        "user_name": u.display_name if u else "Аноним",
        "user_color": getattr(u, "chat_color", None) if u else None,
    }


def _trim_channel(session, channel: str, max_count: int):
    count = session.query(ChatMessage).filter_by(channel=channel).count()
    if count > max_count:
        cutoff = session.query(ChatMessage.id).filter_by(channel=channel).order_by(
            ChatMessage.id.desc()
        ).offset(max_count).limit(1).scalar()
        if cutoff:
            session.query(ChatMessage).filter(
                ChatMessage.channel == channel,
                ChatMessage.id < cutoff,
            ).delete()
            # Also clean up reactions for deleted messages
            session.query(ChatReaction).filter(
                ChatReaction.message_id < cutoff,
            ).delete()
            session.commit()


def _notify_dm(sender: User, channel: str, text: str):
    parts = channel.replace("dm:", "").split("_")
    if len(parts) != 2:
        return
    ids = [int(x) for x in parts]
    target_id = ids[0] if ids[1] == sender.id else ids[1]

    with SessionLocal() as session:
        notif = UserNotification(
            user_id=target_id, type="message",
            title=f"💬 {sender.display_name}",
            body=text[:100],
            link=f"#/chat/{channel}",
        )
        session.add(notif)
        session.commit()

        target = session.query(User).filter_by(id=target_id).first()
        if target:
            _send_tg_notification(target.telegram_id,
                                  f"💬 <b>{sender.display_name}</b>:\n{text[:200]}")


def _notify_listing_reply(sender: User, listing_id: int, text: str):
    with SessionLocal() as session:
        listing = session.query(MarketListing).filter_by(id=listing_id).first()
        if not listing or listing.user_id == sender.id:
            return
        notif = UserNotification(
            user_id=listing.user_id, type="listing_reply",
            title=f"🏪 Ответ на «{listing.item_name[:30]}»",
            body=f"{sender.display_name}: {text[:100]}",
            link=f"#/market",
        )
        session.add(notif)
        session.commit()

        owner = session.query(User).filter_by(id=listing.user_id).first()
        if owner:
            _send_tg_notification(owner.telegram_id,
                                  f"🏪 <b>Ответ на «{listing.item_name[:40]}»</b>\n"
                                  f"От: {sender.display_name}\n{text[:200]}")


def _send_tg_notification(telegram_id: int, text: str):
    import asyncio
    from services.alerter import _get_bot
    from aiogram.enums import ParseMode

    bot = _get_bot()
    if not bot:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                bot.send_message(chat_id=telegram_id, text=text, parse_mode=ParseMode.HTML)
            )
    except Exception as e:
        logger.debug("TG notify error: %s", e)
