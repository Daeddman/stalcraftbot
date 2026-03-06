"""
Авторизация через Telegram WebApp initData.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import logging
from urllib.parse import unquote, parse_qs
from typing import Optional

from fastapi import Request, HTTPException

from config import TELEGRAM_BOT_TOKEN
from db.models import SessionLocal, User

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str) -> Optional[dict]:
    """
    Валидирует initData от Telegram WebApp.
    Возвращает dict с user данными или None если невалидно.
    """
    if not init_data or not TELEGRAM_BOT_TOKEN:
        return None

    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [""])[0]
        if not received_hash:
            return None

        # Собираем data-check-string
        items = []
        for key in sorted(parsed.keys()):
            if key == "hash":
                continue
            items.append(f"{key}={parsed[key][0]}")
        data_check_string = "\n".join(items)

        # HMAC-SHA256
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        # Парсим user
        user_json = parsed.get("user", [""])[0]
        if user_json:
            return json.loads(unquote(user_json))
        return None

    except Exception as exc:
        logger.debug("initData validation error: %s", exc)
        return None


def get_or_create_user(telegram_id: int, **kwargs) -> User:
    """Найти или создать пользователя по telegram_id."""
    with SessionLocal() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            # Обновляем только telegram_username (всегда актуальный)
            # display_name НЕ перезаписываем — пользователь мог задать своё
            changed = False
            tg_username = kwargs.get("telegram_username")
            if tg_username and user.telegram_username != tg_username:
                user.telegram_username = tg_username
                changed = True
            if changed:
                session.commit()
            session.expunge(user)
            return user

        user = User(
            telegram_id=telegram_id,
            telegram_username=kwargs.get("telegram_username"),
            display_name=kwargs.get("display_name", "Сталкер"),
            avatar_url=kwargs.get("avatar_url"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


async def get_current_user(request: Request) -> Optional[User]:
    """FastAPI dependency: извлечь текущего пользователя из X-Telegram-InitData."""
    init_data = request.headers.get("X-Telegram-InitData", "")
    if not init_data:
        return None

    tg_user = validate_init_data(init_data)
    if not tg_user:
        return None

    telegram_id = tg_user.get("id")
    if not telegram_id:
        return None

    first = tg_user.get("first_name", "")
    last = tg_user.get("last_name", "")
    display = f"{first} {last}".strip() or "Сталкер"

    return get_or_create_user(
        telegram_id=telegram_id,
        telegram_username=tg_user.get("username"),
        display_name=display,
    )


async def require_user(request: Request) -> User:
    """FastAPI dependency: обязательная авторизация."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация через Telegram")
    return user

