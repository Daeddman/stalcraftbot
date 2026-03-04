"""
Синхронизация предметов с stalcraft.wiki API.
Находит предметы, которых нет в локальной EXBO базе, и добавляет их.
Скачивает иконки с cdn.stalcraft.wiki.

Использование:
  python -m services.wiki_sync              — синхронизация новых предметов
  python -m services.wiki_sync --force      — перезаписать даже существующие
  python -m services.wiki_sync --icons      — только скачать недостающие иконки
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
# Правильный CDN для иконок: https://cdn.stalcraft.wiki/exbo_item_parser/{category}/{exbo_id}.png
WIKI_ICON_CDN = "https://cdn.stalcraft.wiki/exbo_item_parser"

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


async def download_icon(client: httpx.AsyncClient, exbo_id: str, wiki_category: str) -> str:
    """
    Скачать иконку предмета с cdn.stalcraft.wiki.
    URL формат: https://cdn.stalcraft.wiki/exbo_item_parser/{category}/{subcategory}/{exbo_id}.png
    wiki_category примеры: "other/useful", "weapon/assault_rifle", "artefact"
    """
    parts = wiki_category.split("/")
    # Пробуем с полной категорией (other/useful) и только базовой (other)
    urls_to_try = [
        f"{WIKI_ICON_CDN}/{wiki_category}/{exbo_id}.png",
    ]
    if len(parts) > 1:
        urls_to_try.append(f"{WIKI_ICON_CDN}/{parts[0]}/{exbo_id}.png")

    for url in urls_to_try:
        try:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 100:
                # Сохраняем в папку иконок
                cat_folder = parts[0]
                sub_folder = parts[1] if len(parts) > 1 else ""

                if sub_folder:
                    icon_dir = GAME_DB_DIR / STALCRAFT_REGION / "icons" / cat_folder / sub_folder
                else:
                    icon_dir = GAME_DB_DIR / STALCRAFT_REGION / "icons" / cat_folder

                icon_dir.mkdir(parents=True, exist_ok=True)
                icon_file = icon_dir / f"{exbo_id}.png"
                icon_file.write_bytes(resp.content)

                if sub_folder:
                    return f"/icons/{cat_folder}/{sub_folder}/{exbo_id}.png"
                return f"/icons/{cat_folder}/{exbo_id}.png"
        except Exception:
            continue
    return ""


async def download_missing_icons() -> int:
    """Скачать иконки для всех кастомных предметов у которых icon_path пустой."""
    custom_data = _load_custom_items()
    items = custom_data.get("items", [])
    if not items:
        return 0

    downloaded = 0
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for ci in items:
            listing = ci.get("listing", {})
            icon = listing.get("icon", "")
            if icon:
                # Уже есть иконка — проверяем что файл существует
                icon_file = GAME_DB_DIR / STALCRAFT_REGION / icon.lstrip("/")
                if icon_file.exists():
                    continue

            exbo_id = Path(listing.get("data", "")).stem
            if not exbo_id:
                continue

            # Определяем wiki-категорию
            wiki_cat = ci.get("_wiki_category", "")
            if not wiki_cat:
                # Из data_path: /items/other/8AjTFOVB.json → other
                data_path = listing.get("data", "")
                path_parts = data_path.replace("\\", "/").split("/")
                if len(path_parts) >= 3:
                    wiki_cat = "/".join(path_parts[2:-1])
                if not wiki_cat:
                    wiki_cat = "other"

            new_icon = await download_icon(client, exbo_id, wiki_cat)
            if new_icon:
                listing["icon"] = new_icon
                downloaded += 1

            await asyncio.sleep(0.05)

    if downloaded:
        _save_custom_items(custom_data)
        logger.info("📸 Скачано %d иконок", downloaded)

        from services.db_updater import _merge_custom_items
        _merge_custom_items()

        from services.item_loader import item_db
        item_db.load()

    return downloaded


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
        try:
            categories = await fetch_wiki_categories(client)
        except Exception as exc:
            logger.error("Ошибка получения категорий wiki: %s", exc)
            return 0

        cat_slugs = set()
        for cat in categories:
            slug = cat.get("slug", "")
            if slug and slug != "new":
                cat_slugs.add(slug)

        logger.info("📂 Найдено %d категорий на wiki", len(cat_slugs))

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

                if exbo_id in existing_ids and not force:
                    continue
                if exbo_id in custom_ids and not force:
                    continue

                wiki_cat = wiki_item.get("category", cat_slug)
                color = wiki_item.get("color", "DEFAULT")
                name_obj = wiki_item.get("name", {})
                name_ru = name_obj.get("lines", {}).get("ru", "")
                name_en = name_obj.get("lines", {}).get("en", "")

                if not name_ru and not name_en:
                    continue

                cat_parts = wiki_cat.split("/")
                base_cat = cat_parts[0] if cat_parts else "other"

                data_path = f"/items/{base_cat}/{exbo_id}.json"

                # Скачиваем иконку
                icon_path = await download_icon(client, exbo_id, wiki_cat)

                listing_entry = {
                    "data": data_path,
                    "icon": icon_path,
                    "name": name_obj,
                    "color": color,
                    "status": {"state": ""},
                }

                detail = {
                    "id": exbo_id,
                    "category": base_cat,
                    "name": name_obj,
                    "color": color,
                    "status": {"state": ""},
                    "infoBlocks": [],
                }

                custom_data["items"].append({
                    "listing": listing_entry,
                    "detail": detail,
                    "_wiki_category": wiki_cat,
                })
                custom_ids.add(exbo_id)
                added += 1

            await asyncio.sleep(0.3)

    if added:
        _save_custom_items(custom_data)
        logger.info("✅ Добавлено %d новых предметов с wiki", added)

        from services.db_updater import _merge_custom_items
        _merge_custom_items()

        from services.item_loader import item_db
        item_db.load()
        logger.info("📦 База перезагружена: %d предметов", item_db.total_items)
    else:
        logger.info("✅ Все предметы с wiki уже есть в базе")

    return added


async def main():
    """CLI-запуск синхронизации."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if "--icons" in sys.argv:
        count = await download_missing_icons()
        print(f"Скачано иконок: {count}")
    else:
        force = "--force" in sys.argv
        count = await sync_from_wiki(force=force)
        print(f"Добавлено предметов: {count}")

        # После добавления — качаем недостающие иконки
        icon_count = await download_missing_icons()
        print(f"Скачано иконок: {icon_count}")


if __name__ == "__main__":
    asyncio.run(main())
