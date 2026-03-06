"""
Система уведомлений — отправка алертов о выгодных сделках в Telegram.
Использует aiogram Bot напрямую для красивых сообщений с кнопками.
"""

import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db.repository import save_alert

logger = logging.getLogger(__name__)

# Ленивая инициализация бота для алертов
_bot: Bot | None = None


def _get_bot() -> Bot | None:
    global _bot
    if not TELEGRAM_BOT_TOKEN:
        return None
    if _bot is None:
        _bot = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot


def _price_fmt(price: int | float) -> str:
    return f"{int(price):,}".replace(",", " ")


async def send_deal_alert(deal) -> bool:
    """Отправить красивое уведомление о выгодной сделке."""
    # Строка редкости/заточки для артефактов
    rarity_line = ""
    if hasattr(deal, 'quality_str') and deal.quality_str:
        rarity_line = f"🎯 Редкость: <b>{deal.quality_str}</b>\n"

    message = (
        f"🔥 <b>Выгодная сделка!</b>\n\n"
        f"📦 <b>{deal.item_name}</b>\n"
        f"{rarity_line}"
        f"💰 Цена: <b>{_price_fmt(deal.current_price)}</b> руб.\n"
        f"📊 Средняя: {_price_fmt(deal.avg_price)} руб.\n"
        f"📉 Скидка: <b>-{deal.discount_percent:.1f}%</b>\n"
        f"💵 Потенц. профит: ~<b>{_price_fmt(deal.potential_profit)}</b> руб.\n"
    )

    if deal.avg_sale_price:
        message += f"🏷 Ср. продажа (7д): {_price_fmt(deal.avg_sale_price)} руб.\n"

    # Сохраняем алерт в БД
    quality = getattr(deal, 'quality', -1)
    upgrade_level = getattr(deal, 'upgrade_level', 0)
    save_alert(
        item_id=deal.item_id,
        lot_id=deal.lot_id,
        price=deal.current_price,
        avg_price=int(deal.avg_price),
        discount_percent=deal.discount_percent,
        message=message,
        quality=quality,
        upgrade_level=upgrade_level,
    )

    # Отправляем через aiogram
    bot = _get_bot()
    if not bot or not TELEGRAM_CHAT_ID:
        logger.info("АЛЕРТ (Telegram не настроен):\n%s", message)
        return False

    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Смотреть на аукционе",
                callback_data=f"auction:{deal.item_id}",
            )],
            [InlineKeyboardButton(
                text="📦 Карточка предмета",
                callback_data=f"item:{deal.item_id}",
            )],
        ])

        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
        logger.info("✅ Алерт отправлен: %s -%s%%", deal.item_name, deal.discount_percent)
        return True
    except Exception as exc:
        logger.error("Ошибка отправки алерта: %s", exc)
        return False


async def send_status_message(text: str) -> bool:
    """Отправить произвольное сообщение."""
    bot = _get_bot()
    if not bot or not TELEGRAM_CHAT_ID:
        return False
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        return True
    except Exception as exc:
        logger.error("Ошибка отправки: %s", exc)
        return False


# ══════════════════════════════════════════════════════════════
#  Уведомления о выбросе
# ══════════════════════════════════════════════════════════════

_last_emission_active: bool | None = None  # None = неизвестно, True = идёт, False = чисто


def get_emission_debug() -> dict:
    """Диагностика состояния emission checker."""
    return {
        "last_known_state": _last_emission_active,
        "description": {
            None: "Не инициализирован (ожидает первую проверку)",
            True: "Выброс идёт",
            False: "Зона чиста",
        }.get(_last_emission_active, "???"),
    }


def _parse_emission_time(s: str):
    """Парсит дату из Stalcraft API (несколько форматов)."""
    from datetime import datetime, timezone
    if not s:
        return None
    # Убираем Z и пробуем разные варианты
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            val = s.replace("Z", "+00:00")
            dt = datetime.strptime(val, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Последний вариант — fromisoformat
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def check_emission_and_notify():
    """
    Проверяет статус выброса и рассылает уведомления подписчикам
    при изменении состояния (начался / закончился).
    """
    global _last_emission_active
    from api.emission import get_emission
    from db.models import SessionLocal, EmissionNotifySetting
    from datetime import datetime, timezone

    try:
        data = await get_emission(force=True)
    except Exception as exc:
        logger.warning("Emission check error: %s", exc)
        return

    if not data:
        logger.warning("Emission: пустой ответ API")
        return

    # Определяем текущее состояние
    now = datetime.now(timezone.utc)
    cs = data.get("currentStart")
    ce = data.get("currentEnd")
    is_active = False

    if cs and ce:
        start = _parse_emission_time(cs)
        end = _parse_emission_time(ce)
        if start and end:
            is_active = start <= now <= end
            logger.debug("Emission: start=%s end=%s now=%s active=%s", start, end, now, is_active)
        else:
            logger.warning("Emission: не удалось распарсить даты cs=%r ce=%r", cs, ce)

    # Первый запуск
    if _last_emission_active is None:
        _last_emission_active = is_active
        logger.info("☢️ Emission init: active=%s (raw: cs=%r, ce=%r)", is_active, cs, ce)
        # Если выброс уже идёт при старте — сразу шлём уведомление
        if is_active:
            logger.info("☢️ Emission: выброс уже идёт при старте, шлём уведомление")
            await _send_emission_notifications(
                "☢️ <b>Выброс идёт!</b>\n\n🚨 Немедленно укройтесь в безопасном месте!",
                is_active=True,
            )
        return

    # Нет изменений
    if is_active == _last_emission_active:
        return

    prev = _last_emission_active
    _last_emission_active = is_active
    logger.info("☢️ Emission changed: %s → %s", prev, is_active)

    # Готовим сообщение
    if is_active:
        text = "☢️ <b>Выброс начался!</b>\n\n🚨 Немедленно укройтесь в безопасном месте!"
    else:
        text = "✅ <b>Выброс завершён</b>\n\n🌤 Зона снова безопасна. Можно выходить."

    await _send_emission_notifications(text, is_active=is_active)


async def _send_emission_notifications(text: str, is_active: bool):
    """Рассылает уведомление о выбросе всем подписчикам."""
    from db.models import SessionLocal, EmissionNotifySetting

    bot = _get_bot()
    if not bot:
        logger.warning("☢️ Emission: бот не инициализирован (token=%s)", bool(TELEGRAM_BOT_TOKEN))
        return

    with SessionLocal() as session:
        subscribers = session.query(EmissionNotifySetting).filter_by(enabled=True).all()
        tg_ids = [s.telegram_id for s in subscribers]

    logger.info("☢️ Emission notify: подписчиков=%d, tg_ids=%s", len(tg_ids), tg_ids)

    if not tg_ids:
        if TELEGRAM_CHAT_ID:
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=ParseMode.HTML)
                logger.info("☢️ Emission: отправлено в основной чат %s", TELEGRAM_CHAT_ID)
            except Exception as exc:
                logger.error("Emission send to main chat error: %s", exc)
        else:
            logger.warning("☢️ Emission: нет подписчиков и нет TELEGRAM_CHAT_ID")
        return

    sent = 0
    for tg_id in tg_ids:
        try:
            await bot.send_message(chat_id=tg_id, text=text, parse_mode=ParseMode.HTML)
            sent += 1
            logger.debug("☢️ Emission: отправлено %s", tg_id)
        except Exception as exc:
            logger.warning("Emission notify error for %s: %s", tg_id, exc)

    event = "начался" if is_active else "завершён"
    logger.info("☢️ Выброс %s — уведомлено %d/%d", event, sent, len(tg_ids))

