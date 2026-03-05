"""
PerekupHelper — Торговый помощник Stalcraft.
python main.py — поднимает Web App (HTTPS) + Telegram-бот + сканер.
"""

import asyncio
import logging
import sys
import os

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_BOT_TOKEN, SCAN_INTERVAL_MINUTES, WEBAPP_HOST, WEBAPP_PORT, WEBAPP_URL, DB_UPDATE_INTERVAL_HOURS
from db.models import init_db
from services.item_loader import item_db
from services.scanner import scan_auction
from services.db_updater import update_game_database, scheduled_db_update
from services.wiki_sync import sync_from_wiki
from services.discovery import run_discovery_scan, sync_official_db_to_registry
from services.history_sync import run_incremental_job, run_full_download_job, init_sync_states
from services.alerter import check_emission_and_notify
from web.routers.marketplace import expire_old_listings
from bot.handlers import router
from web.app import app as fastapi_app

# ── Логирование ──
_log_fmt = "%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=_log_fmt,
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "bot.log"),
            encoding="utf-8",
        ),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

logger = logging.getLogger("stalcraftbot")


def _suppress_proactor_errors(loop, context):
    """Подавляем безобидные ошибки ProactorEventLoop + SSL на Windows."""
    exc = context.get("exception")
    if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, OSError)):
        return  # тихо игнорируем
    # Всё остальное — логируем стандартно
    loop.default_exception_handler(context)

CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")


# ══════════════════════════════════════════════════════════════
#  SSL-сертификат (самоподписанный, для localhost)
# ══════════════════════════════════════════════════════════════

def ensure_ssl_certs() -> tuple[str, str]:
    """Создаёт самоподписанный SSL если его нет. Возвращает (cert_path, key_path)."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    cert_path = os.path.join(CERTS_DIR, "cert.pem")
    key_path = os.path.join(CERTS_DIR, "key.pem")

    if os.path.isfile(cert_path) and os.path.isfile(key_path):
        return cert_path, key_path

    logger.info("🔐 Генерирую SSL-сертификат для localhost...")

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime
    import ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "PerekupHelper"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PerekupHelper Dev"),
    ])

    # Добавляем локальный IP в SAN чтобы работало с телефона
    local_ip = _get_local_ip()
    san_entries = [
        x509.DNSName("localhost"),
        x509.DNSName("127.0.0.1"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
    ]
    if local_ip != "127.0.0.1":
        san_entries.append(x509.DNSName(local_ip))
        san_entries.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info("✅ SSL-сертификат создан в %s", CERTS_DIR)
    return cert_path, key_path


# ══════════════════════════════════════════════════════════════
#  FastAPI + Bot
# ══════════════════════════════════════════════════════════════

async def on_startup(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="🏪 Главное меню"),
        BotCommand(command="emission", description="☢️ Статус выброса"),
        BotCommand(command="emission_on", description="🔔 Вкл. уведомления о выбросе"),
        BotCommand(command="emission_off", description="🔕 Выкл. уведомления о выбросе"),
        BotCommand(command="help", description="📖 Помощь"),
    ])
    logger.info("✅ Telegram-бот запущен!")


async def run_webapp(ssl_cert: str, ssl_key: str):
    cfg = uvicorn.Config(
        fastapi_app,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        ssl_certfile=ssl_cert,
        ssl_keyfile=ssl_key,
        log_level="warning",
    )
    server = uvicorn.Server(cfg)
    await server.serve()


async def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN не задан")
        await asyncio.Event().wait()
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════

def _get_local_ip() -> str:
    """Получаем локальный IP машины в сети."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def main() -> None:
    # Подавляем спам от ProactorEventLoop на Windows
    asyncio.get_event_loop().set_exception_handler(_suppress_proactor_errors)

    logger.info("Инициализация...")
    init_db()

    # Проверяем наличие базы — если нет, скачиваем
    from config import GAME_DB_DIR, STALCRAFT_REGION
    listing_path = GAME_DB_DIR / STALCRAFT_REGION / "listing.json"
    if not listing_path.exists():
        logger.info("📥 База предметов не найдена, скачиваю с GitHub...")
        await update_game_database(force=True)
    else:
        # Проверяем обновления в фоне (не блокируем старт)
        logger.info("🔄 Проверяю обновления базы предметов...")
        await update_game_database(force=False)

    logger.info("Загрузка базы предметов...")
    item_db.load()
    if not item_db.loaded:
        logger.error("❌ Не удалось загрузить базу!")
        return
    logger.info("✅ Загружено %d предметов", item_db.total_items)

    # Синхронизируем official DB → ItemRegistry
    try:
        added = sync_official_db_to_registry()
        logger.info("📋 Registry sync: +%d предметов", added)
    except Exception as exc:
        logger.error("❌ Registry sync ошибка: %s", exc)

    # Инициализация HistorySyncState для всех предметов
    try:
        init_sync_states()
    except Exception as exc:
        logger.error("❌ init_sync_states ошибка: %s", exc)

    # SSL
    cert_path, key_path = ensure_ssl_certs()

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scan_auction, "interval",
        minutes=SCAN_INTERVAL_MINUTES,
        id="auction_scan",
        name="Сканирование аукциона",
        misfire_grace_time=60,
    )
    scheduler.add_job(
        scheduled_db_update, "interval",
        hours=DB_UPDATE_INTERVAL_HOURS,
        id="db_update",
        name="Обновление базы предметов",
        misfire_grace_time=300,
    )

    async def _wiki_sync_job():
        try:
            count = await sync_from_wiki()
            if count:
                logger.info("🔄 Wiki sync: добавлено %d предметов", count)
        except Exception as exc:
            logger.error("❌ Wiki sync ошибка: %s", exc)

    scheduler.add_job(
        _wiki_sync_job, "interval",
        hours=12,
        id="wiki_sync",
        name="Синхронизация с stalcraft.wiki",
        misfire_grace_time=300,
    )

    # Discovery-сканер (полный обход аукциона)
    async def _discovery_job():
        try:
            await run_discovery_scan()
        except Exception as exc:
            logger.error("❌ Discovery scan ошибка: %s", exc)

    scheduler.add_job(
        _discovery_job, "interval",
        seconds=45,
        id="discovery_scan",
        name="Discovery: полный обход аукциона",
        misfire_grace_time=60,
        max_instances=1,
    )

    # Инкрементальная синхронизация истории (tracked items)
    async def _incremental_sync_job():
        try:
            await run_incremental_job()
        except Exception as exc:
            logger.error("❌ Incremental sync ошибка: %s", exc)

    scheduler.add_job(
        _incremental_sync_job, "interval",
        minutes=5,
        id="incremental_sync",
        name="Инкрементальная синхронизация истории",
        misfire_grace_time=120,
        max_instances=1,
    )

    # Полная выгрузка истории (фоновая, по одному предмету за раз)
    async def _full_download_job():
        try:
            await run_full_download_job()
        except Exception as exc:
            logger.error("❌ Full download ошибка: %s", exc)

    scheduler.add_job(
        _full_download_job, "interval",
        seconds=30,
        id="full_download",
        name="Полная выгрузка истории продаж",
        misfire_grace_time=60,
        max_instances=1,
    )

    # Экспирация листингов маркетплейса
    def _expire_listings_job():
        try:
            expired = expire_old_listings()
            if expired:
                logger.info("⏰ Экспирировано %d листингов", expired)
        except Exception as exc:
            logger.error("❌ Expire listings ошибка: %s", exc)

    scheduler.add_job(
        _expire_listings_job, "interval",
        minutes=30,
        id="expire_listings",
        name="Экспирация листингов",
        misfire_grace_time=120,
    )

    # Проверка выброса и рассылка уведомлений
    async def _emission_check_job():
        try:
            await check_emission_and_notify()
        except Exception as exc:
            logger.error("❌ Emission check ошибка: %s", exc)

    scheduler.add_job(
        _emission_check_job, "interval",
        seconds=30,
        id="emission_check",
        name="Проверка выброса",
        misfire_grace_time=30,
        max_instances=1,
    )

    scheduler.start()

    # URL
    import config
    local_ip = _get_local_ip()
    public_url = WEBAPP_URL or f"https://{local_ip}:{WEBAPP_PORT}"
    config.WEBAPP_URL = public_url

    print()
    print("  ╔═══════════════════════════════════════════════════╗")
    print("  ║       🏪 PerekupHelper — Stalcraft Trader         ║")
    print("  ╠═══════════════════════════════════════════════════╣")
    print(f"  ║  HTTPS:   https://localhost:{WEBAPP_PORT}                 ║")
    print(f"  ║  Сеть:    https://{local_ip}:{WEBAPP_PORT}              ║")
    print("  ║  Telegram: /start в боте                          ║")
    print("  ╠═══════════════════════════════════════════════════╣")
    print("  ║  📱 Открой ссылку на телефоне в той же WiFi-сети  ║")
    print("  ║  ⚠️  Браузер предупредит о сертификате — это ОК   ║")
    print("  ╚═══════════════════════════════════════════════════╝")
    print()

    logger.info("🌐 HTTPS: https://localhost:%d", WEBAPP_PORT)
    logger.info("🌐 Сеть:  https://%s:%d", local_ip, WEBAPP_PORT)

    try:
        await asyncio.gather(run_webapp(cert_path, key_path), run_bot())
    finally:
        scheduler.shutdown()
        logger.info("⏹️  Остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
