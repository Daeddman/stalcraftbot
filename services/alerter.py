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
