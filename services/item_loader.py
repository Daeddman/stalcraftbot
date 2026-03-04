"""
Загрузчик локальной базы предметов Stalcraft из JSON-файлов.
Парсит listing.json и item-файлы, предоставляет быстрый поиск.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import GAME_DB_DIR, STALCRAFT_REGION, CATEGORY_NAMES, RANK_EMOJI

logger = logging.getLogger(__name__)


@dataclass
class GameItem:
    """Предмет из игровой базы данных."""
    item_id: str           # короткий id (например '5ld1g')
    name_ru: str           # русское название
    name_en: str           # английское название
    category: str          # категория (weapon/assault_rifle, armor, artefact ...)
    color: str             # ранг/цвет (RANK_VETERAN, RANK_MASTER ...)
    icon_path: str         # путь к иконке (относительный)
    data_path: str         # путь к json-файлу (относительный)
    status: str = ""       # статус (NON_DROP, PERSONAL_ON_USE ...)
    stats: dict = field(default_factory=dict)  # кеш для статистик

    @property
    def rank_emoji(self) -> str:
        return RANK_EMOJI.get(self.color, "⬜")

    @property
    def api_supported(self) -> bool:
        """Короткие ID (≤5 символов) поддерживаются Stalcraft API, 8-символьные wiki-ID — нет."""
        return len(self.item_id) <= 5

    @property
    def category_name(self) -> str:
        return CATEGORY_NAMES.get(self.category, self.category)

    @property
    def display_name(self) -> str:
        return f"{self.rank_emoji} {self.name_ru}"

    @property
    def icon_full_path(self) -> Path:
        return GAME_DB_DIR / STALCRAFT_REGION / self.icon_path.lstrip("/")

    @property
    def data_full_path(self) -> Path:
        return GAME_DB_DIR / STALCRAFT_REGION / self.data_path.lstrip("/")


class ItemDatabase:
    """Быстрый индекс всех предметов из локальной БД."""

    def __init__(self) -> None:
        self._items: dict[str, GameItem] = {}            # id -> GameItem
        self._by_category: dict[str, list[GameItem]] = {}  # category -> [items]
        self._search_index: list[tuple[str, GameItem]] = []  # (lower_name, item)
        self._categories: list[str] = []
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def total_items(self) -> int:
        return len(self._items)

    def load(self) -> None:
        """Загрузить все предметы из listing.json."""
        listing_path = GAME_DB_DIR / STALCRAFT_REGION / "listing.json"

        if not listing_path.exists():
            logger.error("Файл listing.json не найден: %s", listing_path)
            return

        logger.info("Загружаю базу предметов из %s...", listing_path)

        with open(listing_path, "r", encoding="utf-8") as f:
            raw_items: list[dict] = json.load(f)

        for raw in raw_items:
            try:
                item = self._parse_listing_entry(raw)
                if item:
                    self._items[item.item_id] = item

                    # Индекс по категории
                    if item.category not in self._by_category:
                        self._by_category[item.category] = []
                    self._by_category[item.category].append(item)

                    # Индекс для поиска
                    self._search_index.append((item.name_ru.lower(), item))
                    if item.name_en:
                        self._search_index.append((item.name_en.lower(), item))
            except Exception as exc:
                logger.debug("Ошибка парсинга предмета: %s", exc)

        # Сортируем категории
        self._categories = sorted(self._by_category.keys())
        self._loaded = True

        logger.info("Загружено %d предметов в %d категориях",
                     len(self._items), len(self._categories))

    def _parse_listing_entry(self, raw: dict) -> GameItem | None:
        """Парсит одну запись из listing.json."""
        data_path = raw.get("data", "")
        icon_path = raw.get("icon", "")
        name_obj = raw.get("name", {})
        lines = name_obj.get("lines", {})
        color = raw.get("color", "DEFAULT")
        status_obj = raw.get("status", {})
        status = status_obj.get("state", "")

        name_ru = lines.get("ru", "")
        name_en = lines.get("en", "")

        # Некоторые предметы содержат ключ перевода вместо имени
        if name_ru and name_ru.startswith("item."):
            name_ru = ""
        if name_en and name_en.startswith("item."):
            name_en = ""

        if not name_ru and not name_en:
            # Попробуем вытащить из JSON-файла предмета
            try:
                data_file = GAME_DB_DIR / STALCRAFT_REGION / data_path.lstrip("/")
                if data_file.exists():
                    with open(data_file, "r", encoding="utf-8") as df:
                        detail = json.load(df)
                    dname = detail.get("name", {}).get("lines", {})
                    name_ru = dname.get("ru", "")
                    name_en = dname.get("en", "")
            except Exception:
                pass

        if not name_ru and not name_en:
            # Последняя попытка — делаем читаемое из ключа перевода
            raw_name = lines.get("ru") or lines.get("en") or ""
            if raw_name:
                # item.amm.556st_frontline.name → 556st frontline
                parts = raw_name.replace("item.", "").replace(".name", "").split(".")
                name_ru = " ".join(parts[-1:]).replace("_", " ").title()
                name_en = name_ru
            if not name_ru:
                return None

        # Извлекаем item_id из пути: /items/weapon/assault_rifle/5ld1g.json -> 5ld1g
        item_id = Path(data_path).stem

        # Извлекаем категорию: /items/weapon/assault_rifle/5ld1g.json -> weapon/assault_rifle
        parts = data_path.replace("\\", "/").split("/")
        # /items/category/.../file.json
        if len(parts) >= 3:
            category = "/".join(parts[2:-1])  # всё между /items/ и файлом
        else:
            category = "other"

        return GameItem(
            item_id=item_id,
            name_ru=name_ru or name_en,
            name_en=name_en or name_ru,
            category=category,
            color=color,
            icon_path=icon_path,
            data_path=data_path,
            status=status,
        )

    def get(self, item_id: str) -> GameItem | None:
        """Получить предмет по ID."""
        return self._items.get(item_id)

    def is_api_supported(self, item_id: str) -> bool:
        """Проверить, поддерживается ли предмет официальным Stalcraft API."""
        item = self._items.get(item_id)
        if item:
            return item.api_supported
        return len(item_id) <= 5

    def get_categories(self) -> list[str]:
        """Список всех категорий."""
        return self._categories

    def get_top_categories(self) -> list[str]:
        """Верхний уровень категорий (weapon, armor, artefact ...)."""
        top = set()
        for cat in self._categories:
            top.add(cat.split("/")[0])
        return sorted(top)

    def get_subcategories(self, parent: str) -> list[str]:
        """Подкатегории для заданной категории."""
        subs = []
        for cat in self._categories:
            if cat.startswith(parent + "/") and cat != parent:
                subs.append(cat)
        return sorted(subs)

    def get_by_category(self, category: str) -> list[GameItem]:
        """Предметы в категории."""
        return self._by_category.get(category, [])

    def get_all_in_category_tree(self, prefix: str) -> list[GameItem]:
        """Все предметы в категории и подкатегориях."""
        result = []
        for cat, items in self._by_category.items():
            if cat == prefix or cat.startswith(prefix + "/"):
                result.extend(items)
        return result

    def search(self, query: str, limit: int = 20) -> list[GameItem]:
        """Поиск предметов по названию (RU/EN)."""
        q = query.lower().strip()
        if not q:
            return []

        exact = []
        starts = []
        contains = []
        seen = set()

        for lower_name, item in self._search_index:
            if item.item_id in seen:
                continue
            if lower_name == q:
                exact.append(item)
                seen.add(item.item_id)
            elif lower_name.startswith(q):
                starts.append(item)
                seen.add(item.item_id)
            elif q in lower_name:
                contains.append(item)
                seen.add(item.item_id)

        results = exact + starts + contains
        return results[:limit]

    def get_item_details(self, item_id: str) -> dict[str, Any] | None:
        """Загрузить полные данные предмета из его JSON-файла."""
        item = self.get(item_id)
        if not item:
            return None

        json_path = item.data_full_path
        if not json_path.exists():
            return None

        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def format_item_stats(self, item_id: str) -> str:
        """Форматировать статистики предмета в красивый текст."""
        details = self.get_item_details(item_id)
        if not details:
            return "Нет данных"

        item = self.get(item_id)
        lines = [f"<b>{item.display_name}</b>"]
        lines.append(f"<i>{item.category_name}</i>")
        lines.append("")  # пустая строка-разделитель

        has_stats = False
        info_blocks = details.get("infoBlocks", [])
        for block in info_blocks:
            elements = block.get("elements", [])
            for el in elements:
                el_type = el.get("type", "")

                if el_type == "key-value":
                    key = self._extract_text(el.get("key", {}))
                    value = self._extract_text(el.get("value", {}))
                    if key and value:
                        lines.append(f"  <b>{key}:</b> {value}")
                        has_stats = True

                elif el_type == "numeric":
                    name = self._extract_text(el.get("name", {}))
                    formatted = el.get("formatted", {})
                    value_map = formatted.get("value", {})
                    # Пробуем ru, потом en, потом raw value
                    value = (
                        value_map.get("ru")
                        or value_map.get("en")
                        or str(el.get("value", ""))
                    )
                    if name and value:
                        lines.append(f"  <b>{name}:</b> {value}")
                        has_stats = True

                elif el_type == "text":
                    text = self._extract_text(el)
                    if text:
                        lines.append(f"  <i>{text}</i>")
                        has_stats = True

        if not has_stats:
            lines.append("  <i>Нет характеристик</i>")

        return "\n".join(lines)

    def _extract_text(self, obj: dict) -> str:
        """Извлечь русский текст из translation/text объекта, с fallback на en."""
        if not obj:
            return ""
        obj_type = obj.get("type", "")
        if obj_type == "translation":
            lines = obj.get("lines", {})
            return lines.get("ru") or lines.get("en") or ""
        elif obj_type == "text":
            return obj.get("text", "")
        # Fallback для нестандартных объектов
        lines = obj.get("lines", {})
        if isinstance(lines, dict):
            return lines.get("ru") or lines.get("en") or ""
        return ""


# ── Глобальный экземпляр ──
item_db = ItemDatabase()

