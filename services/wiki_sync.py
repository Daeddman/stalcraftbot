"""
Синхронизация предметов с stalcraft.wiki API.
Находит предметы, которых нет в локальной EXBO базе, и добавляет их.
Также скачивает иконки с wiki CDN.

Использование:
  python -m services.wiki_sync          — синхронизация
  python -m services.wiki_sync --force  — перезаписать даже существующие
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx

from config import GAME_DB_DIR, STALCRAFT_REGION, BASE_DIR

logger = logging.getLogger(__name__)

WIKI_API = "https://stalcraft.wiki/api/exbo"
WIKI_CDN = "https://stalcraft-wiki-cdn.b-cdn.net"

# Маппинг slug категорий wiki → наши категории в EXBO базе
WIKI_CAT_MAP = {
    "weapon": "weapon",
    "armor": "armor",
    "artefact": "artefact",
    "attachment": "attachment",
    "backpacks": "backpacks",
    "bullet": "bullet",
    "containers": "containers",
    "drink": "drink",
    "food": "food",
    "grenade": "grenade",
    "medicine": "medicine",
    "other": "other",
    "misc": "misc",
}

CUSTOM_ITEMS_FILE = BASE_DIR / "custom_items.json"


def _load_existing_ids() -> set[str]:
    """Загружает все exbo_id из listing.json."""
    listing_path = GAME_DB_DIR / STALCRAFT_REGION / "listing.json"
    if not listing_path.exists():
        return set()
    with open(listing_path, "r", encoding="utf-8") as f:
        listing = json.load(f)
    ids = set()
    for entry in listing:
        # id из пути: /items/other/abc123.json → abc123
        data_path = entry.get("data", "")
        if data_path:
            ids.add(Path(data_path).stem)
    return ids


def _load_custom_items() -> dict:
    """Загружает текущий custom_items.json."""
    if CUSTOM_ITEMS_FILE.exists():
        with open(CUSTOM_ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"_comment": "Кастомные предметы, которых нет в офиц. базе EXBO-Studio.", "items": []}


def _save_custom_items(data: dict) -> None:
    with open(CUSTOM_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def fetch_wiki_categories(client: httpx.AsyncClient) -> list[dict]:
    """Получить список категорий с wiki."""
    resp = await client.get(f"{WIKI_API}/categories/")
    resp.raise_for_status()
    return resp.json()


async def fetch_wiki_items(client: httpx.AsyncClient, category_slug: str) -> list[dict]:
    """Получить предметы категории с wiki."""
    resp = await client.get(f"{WIKI_API}/items/", params={"category": category_slug})
    if resp.status_code == 200:
        data = resp.json()
        return data if isinstance(data, list) else []
    return []


async def download_icon(client: httpx.AsyncClient, exbo_id: str, category: str) -> str | None:
    """Попробовать скачать иконку предмета с wiki CDN."""
    # Wiki хранит иконки по пути /images/items/{exbo_id}.png
    urls_to_try = [
        f"{WIKI_CDN}/images/items/{exbo_id}.png",
        f"{WIKI_CDN}/images/items/{exbo_id}.webp",
    ]

    for url in urls_to_try:
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 100:
                # Сохраняем в папку иконок
                # category format: "other/useful" → parent = "other"
                cat_folder = category.split("/")[0] if "/" in category else category
                icon_dir = GAME_DB_DIR / STALCRAFT_REGION / "icons" / cat_folder
                icon_dir.mkdir(parents=True, exist_ok=True)

                ext = ".png" if url.endswith(".png") else ".png"
                icon_path = icon_dir / f"{exbo_id}{ext}"
                icon_path.write_bytes(resp.content)
                return f"/icons/{cat_folder}/{exbo_id}{ext}"
        except Exception:
            continue
    return ""


async def sync_from_wiki(force: bool = False) -> int:
    """
    Синхронизировать предметы из stalcraft.wiki в нашу локальную базу.
    Returns: количество добавленных предметов.
    """
    logger.info("🔄 Синхронизация предметов с stalcraft.wiki...")

    existing_ids = _load_existing_ids()
    custom_data = _load_custom_items()
    custom_ids = {
        Path(ci.get("listing", {}).get("data", "")).stem
        for ci in custom_data.get("items", [])
        if ci.get("listing", {}).get("data")
    }

    added = 0

    async with httpx.AsyncClient(
        timeout=30,
        headers={"Accept-Language": "ru", "Accept": "application/json"},
        follow_redirects=True,
    ) as client:
        # Получаем категории
        try:
            categories = await fetch_wiki_categories(client)
        except Exception as exc:
            logger.error("Ошибка получения категорий wiki: %s", exc)
            return 0

        # Собираем уникальные slug'и
        cat_slugs = set()
        for cat in categories:
            slug = cat.get("slug", "")
            if slug and slug != "new":  # "new" — не реальная категория
                cat_slugs.add(slug)

        logger.info("📂 Найдено %d категорий на wiki", len(cat_slugs))

        # Для каждой категории получаем предметы
        for cat_slug in sorted(cat_slugs):
            try:
                items = await fetch_wiki_items(client, cat_slug)
            except Exception as exc:
                logger.warning("Ошибка получения предметов [%s]: %s", cat_slug, exc)
                continue

            for wiki_item in items:
                exbo_id = wiki_item.get("exbo_id", "")
                if not exbo_id:
                    continue

                # Пропускаем если уже есть
                if exbo_id in existing_ids and not force:
                    continue
                if exbo_id in custom_ids and not force:
                    continue

                # Извлекаем данные
                wiki_cat = wiki_item.get("category", cat_slug)
                color = wiki_item.get("color", "DEFAULT")
                name_obj = wiki_item.get("name", {})
                name_ru = name_obj.get("lines", {}).get("ru", "")
                name_en = name_obj.get("lines", {}).get("en", "")

                if not name_ru and not name_en:
                    continue

                # Определяем путь в нашей структуре
                # wiki_cat бывает "other/useful", "weapon/assault_rifle" и тд
                cat_parts = wiki_cat.split("/")
                base_cat = cat_parts[0] if cat_parts else "other"
                item_folder = base_cat  # храним в корне категории

                data_path = f"/items/{item_folder}/{exbo_id}.json"
                icon_path = ""

                # Wiki CDN не хранит иконки по exbo_id, пропускаем скачивание

                # Формируем listing entry
                listing_entry = {
                    "data": data_path,
                    "icon": icon_path,
                    "name": name_obj,
                    "color": color,
                    "status": {"state": ""},
                }

                # Формируем detail JSON
                detail = {
                    "id": exbo_id,
                    "category": item_folder,
                    "name": name_obj,
                    "color": color,
                    "status": {"state": ""},
                    "infoBlocks": [],
                }

                # Добавляем в custom_items
                custom_data["items"].append({
                    "listing": listing_entry,
                    "detail": detail,
                })
                custom_ids.add(exbo_id)
                added += 1

            # Не спамим запросами
            await asyncio.sleep(0.3)

    if added:
        _save_custom_items(custom_data)
        logger.info("✅ Добавлено %d новых предметов с wiki", added)

        # Сразу мёржим в базу
        from services.db_updater import _merge_custom_items
        _merge_custom_items()

        # Перезагружаем item_db
        from services.item_loader import item_db
        item_db.load()
        logger.info("📦 База перезагружена: %d предметов", item_db.total_items)
    else:
        logger.info("✅ Все предметы с wiki уже есть в базе")

    return added


async def main():
    """CLI-запуск синхронизации."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    force = "--force" in sys.argv
    count = await sync_from_wiki(force=force)
    print(f"Добавлено: {count}")


if __name__ == "__main__":
    asyncio.run(main())

