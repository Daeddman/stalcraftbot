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
        data = await get_emission()
    except Exception as exc:
        logger.debug("Emission check error: %s", exc)
        return

    # Определяем текущее состояние
    now = datetime.now(timezone.utc)
    cs = data.get("currentStart")
    ce = data.get("currentEnd")
    is_active = False
    if cs and ce:
        try:
            start = datetime.fromisoformat(cs.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ce.replace("Z", "+00:00"))
            is_active = start <= now <= end
        except Exception:
            pass

    # Первый запуск — запоминаем без уведомлений
    if _last_emission_active is None:
        _last_emission_active = is_active
        return

    # Нет изменений
    if is_active == _last_emission_active:
        return

    _last_emission_active = is_active

    # Готовим сообщение
    if is_active:
        text = "☢️ <b>Выброс начался!</b>\n\n🚨 Немедленно укройтесь в безопасном месте!"
    else:
        text = "✅ <b>Выброс завершён</b>\n\n🌤 Зона снова безопасна. Можно выходить."

    # Рассылаем подписчикам
    bot = _get_bot()
    if not bot:
        return

    with SessionLocal() as session:
        subscribers = session.query(EmissionNotifySetting).filter_by(enabled=True).all()
        tg_ids = [s.telegram_id for s in subscribers]

    if not tg_ids:
        # Если нет подписчиков, отправляем хотя бы в основной чат
        if TELEGRAM_CHAT_ID:
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=ParseMode.HTML)
            except Exception:
                pass
        return

    sent = 0
    for tg_id in tg_ids:
        try:
            await bot.send_message(chat_id=tg_id, text=text, parse_mode=ParseMode.HTML)
            sent += 1
        except Exception as exc:
            logger.debug("Emission notify error for %s: %s", tg_id, exc)

    event = "начался" if is_active else "завершён"
    logger.info("☢️ Выброс %s — уведомлено %d/%d", event, sent, len(tg_ids))

