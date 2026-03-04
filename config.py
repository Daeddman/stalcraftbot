import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Пути ──
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stalcraft.db"
GAME_DB_DIR = BASE_DIR / "stalcraft-database-main" / "stalcraft-database-main"

# ── Stalcraft API ──
STALCRAFT_CLIENT_ID: str = os.getenv("STALCRAFT_CLIENT_ID", "")
STALCRAFT_CLIENT_SECRET: str = os.getenv("STALCRAFT_CLIENT_SECRET", "")
STALCRAFT_REGION: str = os.getenv("STALCRAFT_REGION", "ru")

API_BASE_URL = "https://eapi.stalcraft.net"
AUTH_URL = "https://exbo.net/oauth/token"

# ── Telegram ──
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Сканирование ──
SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "10"))
DEAL_THRESHOLD_PERCENT: int = int(os.getenv("DEAL_THRESHOLD_PERCENT", "70"))

# ── Обновление базы предметов ──
DB_UPDATE_INTERVAL_HOURS: int = int(os.getenv("DB_UPDATE_INTERVAL_HOURS", "6"))

# ── Web App ──
WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "10.156.0.2")
WEBAPP_PORT: int = int(os.getenv("WEBAPP_PORT", "8080"))
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")  # публичный HTTPS URL для Telegram WebApp

# ── Rate Limiting ──
MAX_REQUESTS_PER_SECOND: int = 2

# ── Категории предметов (красивые названия) ──
CATEGORY_NAMES: dict[str, str] = {
    "weapon": "🔫 Оружие",
    "weapon/assault_rifle": "🔫 Автоматы",
    "weapon/submachine_gun": "🔫 ПП",
    "weapon/pistol": "🔫 Пистолеты",
    "weapon/shotgun_rifle": "🔫 Дробовики",
    "weapon/sniper_rifle": "🔫 Снайперские",
    "weapon/machine_gun": "🔫 Пулемёты",
    "weapon/melee": "🗡 Холодное",
    "weapon/device": "📡 Устройства",
    "weapon/heavy": "💣 Тяжёлое",
    "armor": "🛡 Броня",
    "artefact": "💎 Артефакты",
    "attachment": "🔩 Обвесы",
    "backpacks": "🎒 Рюкзаки",
    "bullet": "🔸 Патроны",
    "containers": "📦 Контейнеры",
    "drink": "🥤 Напитки",
    "food": "🍖 Еда",
    "grenade": "💥 Гранаты",
    "medicine": "💊 Медицина",
    "misc": "📎 Разное",
    "other": "❓ Прочее",
    "weapon_modules": "⚙️ Модули оружия",
    "armor_style": "🎨 Стили брони",
    "weapon_style": "🎨 Стили оружия",
}

# ── Ранги предметов (цвета Stalcraft) ──
# Отмычка (DEFAULT) — Белый
# Новичок (NEWBIE) — Ярко-зелёный
# Сталкер (STALKER) — Синий
# Ветеран (VETERAN) — Розовый
# Мастер (MASTER) — Красный
# Легенда (LEGEND) — Жёлтый/Золотой
RANK_EMOJI: dict[str, str] = {
    "DEFAULT": "⬜",
    "RANK_NEWBIE": "🟢",
    "RANK_STALKER": "🔵",
    "RANK_VETERAN": "🩷",
    "RANK_MASTER": "🔴",
    "RANK_LEGEND": "🟡",
}

RANK_NAMES: dict[str, str] = {
    "DEFAULT": "Отмычка",
    "RANK_NEWBIE": "Новичок",
    "RANK_STALKER": "Сталкер",
    "RANK_VETERAN": "Ветеран",
    "RANK_MASTER": "Мастер",
    "RANK_LEGEND": "Легенда",
}
