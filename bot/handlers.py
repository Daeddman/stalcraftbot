"""
Telegram-бот PerekupHelper — хендлеры.
/start, /help, /emission, /emission_on, /emission_off.
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

from db.models import SessionLocal, EmissionNotifySetting

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
            "🏪 <b>PerekupHelper</b> — торговая площадка Stalcraft\n\n"
            "📊 Аукцион — лоты и история продаж\n"
            "🏪 Маркет — объявления игроков\n"
            "💬 Чат — общение и сделки\n"
            "☢️ Выброс — уведомления в реальном времени\n\n"
            "👇 Открой приложение кнопкой в меню бота"
        )
    else:
        text = (
            "🏪 <b>PerekupHelper</b> — торговая площадка Stalcraft\n\n"
            "📊 Аукцион • 🏪 Маркет • 💬 Чат • ☢️ Выброс\n\n"
            f"🌐 Приложение: <code>{url or 'http://localhost:8080'}</code>\n\n"
            "⚠️ Для Mini App нужен HTTPS.\n"
            "Задай <code>WEBAPP_URL</code> в .env"
        )

    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=_webapp_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Команды</b>\n\n"
        "/start — Главное меню\n"
        "/emission — Статус выброса\n"
        "/emission_on — Включить уведомления о выбросе\n"
        "/emission_off — Выключить уведомления о выбросе\n"
        "/help — Эта справка",
        parse_mode=ParseMode.HTML,
    )



@router.message(Command("emission"))
async def cmd_emission(message: Message) -> None:
    """Показать текущий статус выброса."""
    from api.emission import get_emission
    from datetime import datetime, timezone

    data = await get_emission()
    now = datetime.now(timezone.utc)

    cs = data.get("currentStart")
    ce = data.get("currentEnd")
    is_active = False
    start = end = None

    if cs and ce:
        try:
            start = datetime.fromisoformat(cs.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ce.replace("Z", "+00:00"))
            is_active = start <= now <= end
        except Exception:
            pass

    if is_active and end:
        remaining = end - now
        mins = int(remaining.total_seconds() // 60)
        secs = int(remaining.total_seconds() % 60)
        text = (
            "☢️ <b>Выброс идёт!</b>\n\n"
            f"⏱ Осталось: <b>{mins}:{secs:02d}</b>\n"
            "🚨 Немедленно укройтесь!"
        )
    else:
        pe = data.get("previousEnd")
        ago = "—"
        if pe:
            try:
                prev = datetime.fromisoformat(pe.replace("Z", "+00:00"))
                diff = now - prev
                hours = int(diff.total_seconds() // 3600)
                mins = int((diff.total_seconds() % 3600) // 60)
                if hours > 0:
                    ago = f"{hours}ч {mins}мин назад"
                else:
                    ago = f"{mins}мин назад"
            except Exception:
                pass
        text = (
            "✅ <b>Зона чиста</b>\n\n"
            f"🕐 Последний выброс: {ago}"
        )

    # Проверяем подписку пользователя
    tg_id = message.from_user.id
    with SessionLocal() as session:
        setting = session.query(EmissionNotifySetting).filter_by(telegram_id=tg_id).first()
        subscribed = setting and setting.enabled

    sub_text = "\n\n🔔 Уведомления: <b>включены</b>" if subscribed else "\n\n🔕 Уведомления: <b>выключены</b>"
    sub_text += "\n/emission_on — включить\n/emission_off — выключить"
    text += sub_text

    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(Command("emission_on"))
async def cmd_emission_on(message: Message) -> None:
    """Включить уведомления о выбросе."""
    tg_id = message.from_user.id
    with SessionLocal() as session:
        setting = session.query(EmissionNotifySetting).filter_by(telegram_id=tg_id).first()
        if setting:
            setting.enabled = True
        else:
            session.add(EmissionNotifySetting(telegram_id=tg_id, enabled=True))
        session.commit()
    await message.answer("🔔 Уведомления о выбросе <b>включены</b>.\nВы будете получать сообщения при начале и окончании выброса.",
                         parse_mode=ParseMode.HTML)


@router.message(Command("emission_off"))
async def cmd_emission_off(message: Message) -> None:
    """Выключить уведомления о выбросе."""
    tg_id = message.from_user.id
    with SessionLocal() as session:
        setting = session.query(EmissionNotifySetting).filter_by(telegram_id=tg_id).first()
        if setting:
            setting.enabled = False
        else:
            session.add(EmissionNotifySetting(telegram_id=tg_id, enabled=False))
        session.commit()
    await message.answer("🔕 Уведомления о выбросе <b>выключены</b>.",
                         parse_mode=ParseMode.HTML)

