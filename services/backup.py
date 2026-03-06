"""Автоматические бекапы SQLite базы данных."""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from config import DB_PATH, BASE_DIR

logger = logging.getLogger("backup")

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", str(BASE_DIR / "backups")))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "7"))


def backup_database() -> str | None:
    """
    Создаёт бекап SQLite через встроенный API (безопасен при WAL).
    Возвращает путь к файлу бекапа или None при ошибке.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"stalcraft_{ts}.db"

    try:
        src = sqlite3.connect(str(DB_PATH))
        dst = sqlite3.connect(str(backup_path))
        src.backup(dst)
        dst.close()
        src.close()

        size_mb = backup_path.stat().st_size / 1024 / 1024
        logger.info("✅ Бекап создан: %s (%.1f МБ)", backup_path.name, size_mb)

        # Удаляем старые бекапы
        _cleanup_old_backups()

        return str(backup_path)

    except Exception as exc:
        logger.error("❌ Ошибка бекапа: %s", exc)
        if backup_path.exists():
            backup_path.unlink(missing_ok=True)
        return None


def _cleanup_old_backups():
    """Удаляет бекапы старше BACKUP_RETENTION_DAYS дней."""
    if not BACKUP_DIR.exists():
        return

    cutoff = datetime.utcnow() - timedelta(days=BACKUP_RETENTION_DAYS)
    removed = 0

    for f in BACKUP_DIR.glob("stalcraft_*.db"):
        try:
            mtime = datetime.utcfromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass

    if removed:
        logger.info("🗑 Удалено %d старых бекапов", removed)


def list_backups() -> list[dict]:
    """Список существующих бекапов."""
    if not BACKUP_DIR.exists():
        return []

    result = []
    for f in sorted(BACKUP_DIR.glob("stalcraft_*.db"), reverse=True):
        result.append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
            "created": datetime.utcfromtimestamp(f.stat().st_mtime).isoformat() + "Z",
        })
    return result

