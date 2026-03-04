"""
Автоматическое обновление локальной базы предметов Stalcraft
из GitHub-репозитория EXBO-Studio/stalcraft-database.
Скачивает ZIP-архив ветки main, распаковывает и перезагружает item_db.
"""

import asyncio
import io
import json
import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import httpx

from config import GAME_DB_DIR, STALCRAFT_REGION, BASE_DIR

logger = logging.getLogger(__name__)

# URL для скачивания архива репозитория
GITHUB_ZIP_URL = "https://github.com/EXBO-Studio/stalcraft-database/archive/refs/heads/main.zip"
# GitHub API для получения последнего коммита (чтобы проверять нужно ли обновлять)
GITHUB_API_COMMITS = "https://api.github.com/repos/EXBO-Studio/stalcraft-database/commits/main"

# Файл для хранения SHA последнего обновления
_STATE_FILE = GAME_DB_DIR.parent / ".db_update_sha"
# Файл с кастомными предметами, которых нет в оф. базе
CUSTOM_ITEMS_FILE = BASE_DIR / "custom_items.json"


def _get_last_sha() -> str | None:
    """Прочитать SHA последнего обновления."""
    try:
        if _STATE_FILE.exists():
            return _STATE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return None


def _save_sha(sha: str) -> None:
    """Сохранить SHA последнего обновления."""
    try:
        _STATE_FILE.write_text(sha, encoding="utf-8")
    except Exception as exc:
        logger.warning("Не удалось сохранить SHA обновления: %s", exc)


async def _get_remote_sha() -> str | None:
    """Получить SHA последнего коммита в main ветке."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                GITHUB_API_COMMITS,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code == 200:
                return resp.json().get("sha", "")[:12]
            elif resp.status_code == 403:
                # Rate limit — обновляем на всякий случай
                logger.debug("GitHub API rate limit, пропускаем проверку SHA")
                return None
            else:
                logger.warning("GitHub API вернул %d", resp.status_code)
                return None
    except Exception as exc:
        logger.warning("Ошибка при проверке обновлений GitHub: %s", exc)
        return None


async def _download_and_extract() -> bool:
    """Скачать ZIP-архив и распаковать в GAME_DB_DIR."""
    logger.info("⬇️  Скачиваю базу данных Stalcraft с GitHub...")

    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(GITHUB_ZIP_URL)
            if resp.status_code != 200:
                logger.error("Не удалось скачать архив: HTTP %d", resp.status_code)
                return False

            zip_data = resp.content
            logger.info("📦 Скачано %.1f МБ, распаковываю...", len(zip_data) / 1024 / 1024)

    except Exception as exc:
        logger.error("Ошибка скачивания базы: %s", exc)
        return False

    # Распаковка в фоне (чтобы не блокировать event loop)
    try:
        await asyncio.to_thread(_extract_zip, zip_data)
        return True
    except Exception as exc:
        logger.error("Ошибка распаковки базы: %s", exc)
        return False


def _extract_zip(zip_data: bytes) -> None:
    """Синхронная распаковка ZIP в нужную директорию."""
    parent_dir = GAME_DB_DIR.parent  # stalcraft-database-main/
    temp_dir = parent_dir / "_update_temp"

    # Чистим временную папку если осталась от предыдущей попытки
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Распаковываем ZIP
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        zf.extractall(temp_dir)

    # В архиве корневая папка — stalcraft-database-main/
    extracted_root = temp_dir / "stalcraft-database-main"
    if not extracted_root.exists():
        # Ищем любую папку внутри
        subdirs = [d for d in temp_dir.iterdir() if d.is_dir()]
        if subdirs:
            extracted_root = subdirs[0]
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("В архиве не найдена корневая папка базы данных")

    # Удаляем старую базу и перемещаем новую
    old_db = GAME_DB_DIR
    backup_dir = parent_dir / "_db_backup"

    # Бэкапим текущую на случай ошибки
    if old_db.exists():
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        try:
            old_db.rename(backup_dir)
        except Exception:
            shutil.rmtree(old_db, ignore_errors=True)

    # Перемещаем новую базу
    try:
        extracted_root.rename(old_db)
    except Exception:
        # Если rename не сработал (другой диск), копируем
        shutil.copytree(str(extracted_root), str(old_db))

    # Чистим
    shutil.rmtree(temp_dir, ignore_errors=True)
    if backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)

    logger.info("✅ База данных распакована в %s", old_db)


def _merge_custom_items() -> None:
    """
    Мёржит кастомные предметы из custom_items.json в обновлённую базу.
    Добавляет записи в listing.json и создаёт файлы предметов.
    """
    if not CUSTOM_ITEMS_FILE.exists():
        logger.debug("Файл кастомных предметов не найден, пропускаю мёрж")
        return

    try:
        with open(CUSTOM_ITEMS_FILE, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
    except Exception as exc:
        logger.warning("Ошибка чтения custom_items.json: %s", exc)
        return

    custom_items = custom_data.get("items", [])
    if not custom_items:
        return

    # Загружаем listing.json
    listing_path = GAME_DB_DIR / STALCRAFT_REGION / "listing.json"
    if not listing_path.exists():
        logger.warning("listing.json не найден для мёржа кастомных предметов")
        return

    with open(listing_path, "r", encoding="utf-8") as f:
        listing: list = json.load(f)

    # Существующие data-пути для быстрой проверки дубликатов
    existing_paths = {entry.get("data", "") for entry in listing}

    added = 0
    for ci in custom_items:
        listing_entry = ci.get("listing", {})
        detail = ci.get("detail", {})
        data_path = listing_entry.get("data", "")

        if not data_path:
            continue

        # Добавляем в listing если ещё нет
        if data_path not in existing_paths:
            listing.append(listing_entry)
            existing_paths.add(data_path)

        # Создаём JSON-файл предмета
        if detail:
            item_file = GAME_DB_DIR / STALCRAFT_REGION / data_path.lstrip("/")
            item_file.parent.mkdir(parents=True, exist_ok=True)
            with open(item_file, "w", encoding="utf-8") as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)

        added += 1

    # Сохраняем обновлённый listing.json
    with open(listing_path, "w", encoding="utf-8") as f:
        json.dump(listing, f, ensure_ascii=False, indent=2)

    if added:
        logger.info("📝 Добавлено %d кастомных предметов в базу", added)


async def update_game_database(force: bool = False) -> bool:
    """
    Проверить наличие обновлений и скачать если нужно.

    Args:
        force: принудительное обновление без проверки SHA.

    Returns:
        True если база была обновлена.
    """
    if not force:
        remote_sha = await _get_remote_sha()
        if remote_sha:
            local_sha = _get_last_sha()
            if local_sha == remote_sha:
                logger.debug("База данных актуальна (SHA: %s)", local_sha)
                return False
            logger.info("🔄 Обнаружено обновление базы: %s → %s", local_sha or "нет", remote_sha)
        else:
            # Не смогли проверить SHA — проверяем раз в сутки по времени файла
            if not force and _STATE_FILE.exists():
                mtime = datetime.fromtimestamp(_STATE_FILE.stat().st_mtime)
                hours_since = (datetime.now() - mtime).total_seconds() / 3600
                if hours_since < 24:
                    logger.debug("Прошло %.1f ч с последнего обновления, пропускаем", hours_since)
                    return False

    # Скачиваем и распаковываем
    success = await _download_and_extract()
    if not success:
        return False

    # Мёржим кастомные предметы (которых нет в оф. базе EXBO)
    await asyncio.to_thread(_merge_custom_items)

    # Перезагружаем базу предметов в памяти
    from services.item_loader import item_db
    item_db.load()

    # Сохраняем SHA
    remote_sha = await _get_remote_sha()
    if remote_sha:
        _save_sha(remote_sha)
    else:
        # Просто обновляем timestamp файла
        _STATE_FILE.touch()
        _save_sha(datetime.now().isoformat())

    logger.info("✅ База данных Stalcraft обновлена! Загружено %d предметов", item_db.total_items)
    return True


async def scheduled_db_update() -> None:
    """Обёртка для планировщика — обновление с обработкой ошибок."""
    try:
        updated = await update_game_database()
        if updated:
            logger.info("🔄 Плановое обновление базы завершено")
    except Exception as exc:
        logger.error("❌ Ошибка при плановом обновлении базы: %s", exc)

