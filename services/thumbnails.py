"""Генерация миниатюр иконок предметов для быстрой загрузки."""
import logging, os
from pathlib import Path
from config import GAME_DB_DIR, STALCRAFT_REGION

logger = logging.getLogger("thumbnails")
THUMB_SIZE = (64, 64)
ICONS_DIR = GAME_DB_DIR / STALCRAFT_REGION / "icons"
THUMBS_DIR = GAME_DB_DIR / STALCRAFT_REGION / "icon-thumbs"


def generate_thumbnails() -> int:
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow не установлен — миниатюры не будут сгенерированы")
        return 0
    if not ICONS_DIR.exists():
        return 0
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for root, dirs, files in os.walk(ICONS_DIR):
        rel = Path(root).relative_to(ICONS_DIR)
        dest_dir = THUMBS_DIR / rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        for fname in files:
            if not fname.lower().endswith(".png"):
                continue
            src = Path(root) / fname
            dst = dest_dir / fname
            if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                continue
            try:
                img = Image.open(src)
                img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
                img.save(dst, "PNG", optimize=True)
                created += 1
            except Exception:
                pass
    if created:
        logger.info("🖼 Сгенерировано %d миниатюр", created)
    return created

