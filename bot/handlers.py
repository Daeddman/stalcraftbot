"""
Telegram-бот PerekupHelper — минимальные хендлеры.
/start с кнопкой Web App + /help + /scan.
"""

import logging

from aiogram import Router
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode

from db.repository import get_active_tracked_items

logger = logging.getLogger(__name__)

router = Router()


def _webapp_kb() -> InlineKeyboardMarkup:
    """Клавиатура: WebApp кнопка если HTTPS, иначе ссылка."""
    import config
    url = config.WEBAPP_URL or ""
    buttons = []

    if url.startswith("https://"):
        # Кнопка Mini App (открывается прямо внутри Telegram)
        buttons.append([InlineKeyboardButton(
            text="🏪 Открыть приложение",
            web_app=WebAppInfo(url=url),
        )])
    elif url:
        # Простая ссылка (откроется в браузере)
        buttons.append([InlineKeyboardButton(
            text="🏪 Открыть в браузере",
            url=url,
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    import config
    url = config.WEBAPP_URL or ""

    if url.startswith("https://"):
        text = (
            "🏪 <b>PerekupHelper</b>\n\n"
            "📊 Мониторинг аукциона • Поиск выгодных сделок\n"
            "📈 История цен • 🔔 Алерты ниже рынка\n\n"
            "Нажми кнопку ниже, чтобы открыть приложение 👇"
        )
    else:
        text = (
            "🏪 <b>PerekupHelper</b>\n\n"
            "📊 Мониторинг аукциона • Поиск выгодных сделок\n"
            "📈 История цен • 🔔 Алерты ниже рынка\n\n"
            f"🌐 Приложение: <code>{url or 'http://localhost:8080'}</code>\n\n"
            "⚠️ Для Mini App нужен HTTPS-туннель.\n"
            "Запусти <code>cloudflared</code> или задай <code>WEBAPP_URL</code> в .env"
        )

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=_webapp_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Команды</b>\n\n"
        "/start — Открыть приложение\n"
        "/scan — Запустить сканирование\n"
        "/help — Эта справка",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("scan"))
async def cmd_scan(message: Message) -> None:
    tracked = get_active_tracked_items()
    if not tracked:
        await message.answer("📭 Нет отслеживаемых предметов. Добавь через Web App!")
        return

    msg = await message.answer(f"🔄 Сканирую {len(tracked)} предметов...")

    from services.scanner import scan_auction
    await scan_auction()

    try:
        await msg.edit_text("✅ Сканирование завершено!")
    except Exception:
        await message.answer("✅ Сканирование завершено!")
