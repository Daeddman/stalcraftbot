"""API: чат — общий, торговый, ЛС, реакции, стикеры, удаление, блокировка."""
import time
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from db.models import (
    SessionLocal, ChatMessage, ChatReaction, User, MarketListing,
    UserNotification, UserBlock,
)
from sqlalchemy import func, or_
from web.auth import require_user, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

CHANNELS = {"general": "💬 Общий", "trading": "💰 Торговый"}
MAX_PUBLIC_MESSAGES = 2000

_spam_tracker: dict[int, float] = {}
SPAM_COOLDOWN = 3.0
MAX_GENERAL_LEN = 500

ALLOWED_REACTIONS = {"👍", "❤️", "🔥", "😂", "😢", "💀", "🎉", "💎", "☢️", "👎"}

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
    sticker: Optional[str] = None


class ReactionData(BaseModel):
    emoji: str


# ── Helpers: blocked users ──

def _get_blocked_ids(session, user_id: int) -> set[int]:
    rows = session.query(UserBlock.blocked_id).filter_by(blocker_id=user_id).all()
    return {r[0] for r in rows}


def _get_blocked_by_ids(session, user_id: int) -> set[int]:
    rows = session.query(UserBlock.blocker_id).filter_by(blocked_id=user_id).all()
    return {r[0] for r in rows}


# ── Channels & Stickers ──

@router.get("/chat/channels")
async def list_channels():
    return [{"id": k, "name": v} for k, v in CHANNELS.items()]


@router.get("/chat/stickers")
async def get_stickers():
    return STICKERS


# ── Messages ──

@router.get("/chat/{channel}/messages")
async def get_messages(channel: str, since_id: int = 0, limit: int = 50,
                       user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 100))
    with SessionLocal() as session:
        blocked_ids = set()
        if user:
            blocked_ids = _get_blocked_ids(session, user.id) | _get_blocked_by_ids(session, user.id)

        q = session.query(ChatMessage, User).outerjoin(
            User, ChatMessage.user_id == User.id
        ).filter(ChatMessage.channel == channel)
        if since_id > 0:
            q = q.filter(ChatMessage.id > since_id)
        rows = q.order_by(ChatMessage.id.desc()).limit(limit).all()

        messages = []
        for m, u in reversed(rows):
            if not channel.startswith("dm:") and u and u.id in blocked_ids:
                continue
            d = _msg_dict(m, u)
            d["reactions"] = _get_reactions(session, m.id)
            if m.reply_to_id:
                d["reply_to"] = _get_reply_preview(session, m.reply_to_id)
            d["is_own"] = (user.id == m.user_id) if user else False
            messages.append(d)

        return messages


@router.post("/chat/{channel}/messages")
async def send_message(channel: str, data: SendMessage, user: User = Depends(require_user)):
    text = (data.text or "").strip()
    sticker = data.sticker

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
            other_id = ids[0] if ids[1] == user.id else ids[1]
            if other_id == user.id:
                return {"error": "Нельзя написать самому себе"}
            with SessionLocal() as session:
                blocked = session.query(UserBlock).filter(
                    or_(
                        (UserBlock.blocker_id == user.id) & (UserBlock.blocked_id == other_id),
                        (UserBlock.blocker_id == other_id) & (UserBlock.blocked_id == user.id),
                    )
                ).first()
                if blocked:
                    return {"error": "Невозможно отправить сообщение"}

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

        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(msg)

        if not is_dm:
            _trim_channel(session, channel, MAX_PUBLIC_MESSAGES)

        result = _msg_dict(msg, user)
        result["reactions"] = []
        result["is_own"] = True
        if msg.reply_to_id:
            result["reply_to"] = _get_reply_preview(session, msg.reply_to_id)

    if is_dm:
        _notify_dm(user, channel, text or f"[стикер: {STICKER_MAP.get(sticker, {}).get('label', sticker)}]")
    if data.listing_id:
        _notify_listing_reply(user, data.listing_id, text)

    return result


# ── Delete own message ──

@router.delete("/chat/messages/{message_id}")
async def delete_message(message_id: int, user: User = Depends(require_user)):
    with SessionLocal() as session:
        msg = session.query(ChatMessage).filter_by(id=message_id).first()
        if not msg:
            return {"error": "Сообщение не найдено"}
        if msg.user_id != user.id:
            return {"error": "Можно удалять только свои сообщения"}
        session.query(ChatReaction).filter_by(message_id=message_id).delete()
        session.delete(msg)
        session.commit()
        return {"ok": True, "id": message_id}


# ── Delete DM conversation ──

@router.delete("/chat/dm-channel/{channel:path}")
async def delete_dm_channel(channel: str, user: User = Depends(require_user)):
    if not channel.startswith("dm:"):
        channel = "dm:" + channel
    parts = channel.replace("dm:", "").split("_")
    if len(parts) != 2:
        return {"error": "Неверный формат канала"}
    ids = [int(x) for x in parts]
    if user.id not in ids:
        return {"error": "Нет доступа"}

    with SessionLocal() as session:
        msg_ids = [r[0] for r in session.query(ChatMessage.id).filter_by(channel=channel).all()]
        if msg_ids:
            session.query(ChatReaction).filter(ChatReaction.message_id.in_(msg_ids)).delete(synchronize_session=False)
        session.query(ChatMessage).filter_by(channel=channel).delete()
        session.commit()
        return {"ok": True}


# ── Block / Unblock users ──

@router.post("/users/{user_id}/block")
async def block_user(user_id: int, user: User = Depends(require_user)):
    if user_id == user.id:
        return {"error": "Нельзя заблокировать себя"}
    with SessionLocal() as session:
        existing = session.query(UserBlock).filter_by(
            blocker_id=user.id, blocked_id=user_id
        ).first()
        if existing:
            return {"ok": True, "blocked": True}
        session.add(UserBlock(blocker_id=user.id, blocked_id=user_id))
        session.commit()
        return {"ok": True, "blocked": True}


@router.delete("/users/{user_id}/block")
async def unblock_user(user_id: int, user: User = Depends(require_user)):
    with SessionLocal() as session:
        b = session.query(UserBlock).filter_by(
            blocker_id=user.id, blocked_id=user_id
        ).first()
        if b:
            session.delete(b)
            session.commit()
        return {"ok": True, "blocked": False}


@router.get("/blocked-users")
async def get_blocked_users(user: User = Depends(require_user)):
    with SessionLocal() as session:
        blocks = session.query(UserBlock, User).outerjoin(
            User, UserBlock.blocked_id == User.id
        ).filter(UserBlock.blocker_id == user.id).all()
        return [
            {
                "id": u.id if u else b.blocked_id,
                "display_name": u.display_name if u else "Удалён",
                "avatar_url": u.avatar_url if u else None,
                "blocked_at": b.created_at.isoformat() + "Z" if b.created_at else None,
            }
            for b, u in blocks
        ]


# ── Reactions ──

@router.post("/chat/messages/{message_id}/reactions")
async def toggle_reaction(message_id: int, data: ReactionData, user: User = Depends(require_user)):
    emoji = data.emoji.strip()
    if emoji not in ALLOWED_REACTIONS:
        return {"error": "Недопустимая реакция"}

    with SessionLocal() as session:
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
        reactions = _get_reactions(session, message_id)

        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)
            session.commit()

        return {"action": action, "reactions": reactions}


@router.get("/chat/messages/{message_id}/reactions")
async def get_message_reactions(message_id: int):
    with SessionLocal() as session:
        return _get_reactions(session, message_id)


# ── Heartbeat / Online ──

@router.post("/heartbeat")
async def heartbeat(user: User = Depends(require_user)):
    with SessionLocal() as session:
        u = session.query(User).filter_by(id=user.id).first()
        if u:
            u.last_active_at = datetime.now(timezone.utc)
            session.commit()
    return {"ok": True}


@router.get("/online-users")
async def online_users():
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
    with SessionLocal() as session:
        blocked = session.query(UserBlock).filter(
            or_(
                (UserBlock.blocker_id == user.id) & (UserBlock.blocked_id == target_user_id),
                (UserBlock.blocker_id == target_user_id) & (UserBlock.blocked_id == user.id),
            )
        ).first()
        if blocked:
            return {"error": "Пользователь заблокирован"}
        target = session.query(User).filter_by(id=target_user_id).first()
        target_name = target.display_name if target else "Пользователь"
    ids = sorted([user.id, target_user_id])
    channel = f"dm:{ids[0]}_{ids[1]}"
    return {"channel": channel, "target_name": target_name}


@router.get("/chat/dm-list")
async def dm_list(user: User = Depends(require_user)):
    with SessionLocal() as session:
        blocked_ids = _get_blocked_ids(session, user.id) | _get_blocked_by_ids(session, user.id)

        channels = session.query(ChatMessage.channel).filter(
            or_(
                ChatMessage.channel.like(f"dm:{user.id}_%"),
                ChatMessage.channel.like(f"dm:%_{user.id}"),
            )
        ).distinct().all()
        result = []
        for (ch,) in channels:
            parts = ch.replace("dm:", "").split("_")
            if len(parts) != 2:
                continue
            other_id = int(parts[0]) if int(parts[1]) == user.id else int(parts[1])
            if other_id == user.id:
                continue
            if other_id in blocked_ids:
                continue
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
    if target_id == sender.id:
        return

    with SessionLocal() as session:
        blocked = session.query(UserBlock).filter(
            or_(
                (UserBlock.blocker_id == sender.id) & (UserBlock.blocked_id == target_id),
                (UserBlock.blocker_id == target_id) & (UserBlock.blocked_id == sender.id),
            )
        ).first()
        if blocked:
            return

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
