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
WEBAPP_HOST: str = os.getenv("WEBAPP_HOST", "")
WEBAPP_PORT: int = int(os.getenv("WEBAPP_PORT", ""))
WEBAPP_URL: str = os.getenv("WEBAPP_URL", "")  # публичный HTTPS URL для Telegram WebApp

# ── Rate Limiting ──
MAX_REQUESTS_PER_SECOND: int = 2

# ── Категории предметов (красивые названия) ──
CATEGORY_NAMES: dict[str, str] = {
    "weapon": "🔫 Оружие",
    "weapon/assault_rifle": "Автоматы",
    "weapon/submachine_gun": "Пистолеты-пулемёты",
    "weapon/pistol": "Пистолеты",
    "weapon/shotgun_rifle": "Дробовики",
    "weapon/sniper_rifle": "Снайперские",
    "weapon/machine_gun": "Пулемёты",
    "weapon/melee": "Холодное оружие",
    "weapon/device": "Устройства",
    "weapon/heavy": "Тяжёлое вооружение",
    "armor": "🛡 Броня",
    "armor/combined": "Комбинированная",
    "armor/first": "Лёгкая",
    "armor/second": "Средняя",
    "armor/third": "Тяжёлая",
    "armor/helmet": "Шлемы",
    "artefact": "💎 Артефакты",
    "artefact/electrophysical": "Электрофизические",
    "artefact/gravitational": "Гравитационные",
    "artefact/organic": "Органические",
    "artefact/thermal": "Термические",
    "attachment": "🔩 Обвесы",
    "attachment/barrel": "Ствольные",
    "attachment/collimator": "Коллиматоры",
    "attachment/flashlight": "Фонари",
    "attachment/forend": "Цевья",
    "attachment/mag": "Магазины",
    "attachment/muzzle": "Дульные",
    "attachment/pistol_grip": "Рукоятки",
    "attachment/scope": "Прицелы",
    "attachment/stock": "Приклады",
    "attachment/tactical": "Тактические",
    "backpacks": "🎒 Рюкзаки",
    "bullet": "🔸 Патроны",
    "bullet/5.45x39": "5.45x39",
    "bullet/5.56x45": "5.56x45",
    "bullet/7.62x39": "7.62x39",
    "bullet/7.62x51": "7.62x51",
    "bullet/7.62x54": "7.62x54",
    "bullet/9x18": "9x18",
    "bullet/9x19": "9x19",
    "bullet/9x39": "9x39",
    "bullet/12x70": "12x70",
    "bullet/12.7x55": "12.7x55",
    "bullet/.338": ".338 Lapua",
    "containers": "📦 Контейнеры",
    "consumables": "💉 Расходники",
    "drink": "🥤 Напитки",
    "food": "🍖 Еда",
    "grenade": "💥 Гранаты",
    "medicine": "💊 Медицина",
    "misc": "📎 Разное",
    "other": "📦 Прочее",
    "other/barter": "Бартер",
    "other/boxes": "Ящики и сейфы",
    "other/hideout": "Убежище",
    "other/misc": "Разное",
    "other/structures": "Сооружения",
    "other/trash": "Мусор",
    "other/skins": "Скины и краски",
    "other/useful": "Полезное",
    "weapon_modules": "⚙️ Модули оружия",
    "armor_style": "🎨 Скины брони",
    "weapon_style": "🎨 Скины оружия",
    "device": "📡 Устройства",
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
