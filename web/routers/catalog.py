"""API каталога предметов."""
from fastapi import APIRouter, Query
from services.item_loader import item_db
from config import CATEGORY_NAMES

router = APIRouter(tags=["catalog"])


@router.get("/categories")
async def get_categories():
    """Дерево категорий."""
    top = item_db.get_top_categories()
    result = []
    for cat in top:
        subs = item_db.get_subcategories(cat)
        count = len(item_db.get_all_in_category_tree(cat))
        children = []
        for sub in subs:
            children.append({
                "id": sub,
                "name": CATEGORY_NAMES.get(sub, sub.split("/")[-1].replace("_", " ").title()),
                "count": len(item_db.get_by_category(sub)),
            })
        result.append({
            "id": cat,
            "name": CATEGORY_NAMES.get(cat, cat.title()),
            "count": count,
            "children": children,
        })
    return result


@router.get("/categories/{cat:path}/items")
async def get_category_items(cat: str, page: int = 1, per_page: int = 20):
    """Предметы в категории с пагинацией."""
    items = item_db.get_by_category(cat)
    if not items:
        items = item_db.get_all_in_category_tree(cat)
    items.sort(key=lambda x: x.name_ru)

    total = len(items)
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]

    return {
        "items": [_item_short(i) for i in page_items],
        "total": total,
        "page": page,
        "pages": (total - 1) // per_page + 1 if total else 0,
    }


@router.get("/items/{item_id}")
async def get_item(item_id: str):
    """Полные данные предмета."""
    item = item_db.get(item_id)
    if not item:
        return {"error": "not_found"}

    details = item_db.get_item_details(item_id)
    stats = _parse_stats(details) if details else []

    from db.repository import (
        get_avg_price, get_avg_sale_price, get_quality_breakdown,
    )

    is_art = item.category.startswith("artefact")
    breakdown = get_quality_breakdown(item_id, hours=168) if is_art else []

    return {
        "id": item.item_id,
        "name": item.name_ru,
        "name_en": item.name_en,
        "category": item.category,
        "category_name": item.category_name,
        "color": item.color,
        "rank_emoji": item.rank_emoji,
        "icon": _icon_url(item),
        "is_artefact": is_art,
        "stats": stats,
        "prices": {
            "avg_24h": get_avg_price(item_id, hours=24),
            "avg_7d": get_avg_sale_price(item_id, hours=168),
        },
        "quality_breakdown": breakdown,
    }


@router.get("/search")
async def search_items(q: str = Query("", min_length=1), limit: int = 20):
    results = item_db.search(q, limit=limit)
    return [_item_short(i) for i in results]


def _icon_url(item) -> str:
    """Формирует URL иконки."""
    p = item.icon_path
    if not p or p.strip() == "":
        return ""
    if p.startswith("/icons/"):
        return p  # уже правильный путь
    return f"/icons/{p.lstrip('/')}"


def _item_short(item):
    return {
        "id": item.item_id,
        "name": item.name_ru,
        "category": item.category,
        "category_name": item.category_name,
        "color": item.color,
        "rank_emoji": item.rank_emoji,
        "icon": _icon_url(item),
    }


def _parse_stats(details: dict) -> list[dict]:
    """Парсит infoBlocks в плоский список статов."""
    stats = []
    for block in details.get("infoBlocks", []):
        for el in block.get("elements", []):
            t = el.get("type", "")
            if t == "key-value":
                key = _txt(el.get("key", {}))
                val = _txt(el.get("value", {}))
                if key and val:
                    stats.append({"key": key, "value": val, "type": "kv"})
            elif t == "numeric":
                name = _txt(el.get("name", {}))
                fmt = el.get("formatted", {}).get("value", {})
                val = fmt.get("ru") or fmt.get("en") or str(el.get("value", ""))
                color = el.get("formatted", {}).get("nameColor", "")
                if name:
                    stats.append({"key": name, "value": val, "type": "num", "color": color})
            elif t == "range":
                name = _txt(el.get("name", {}))
                fmt = el.get("formatted", {}).get("value", {})
                val = fmt.get("ru") or fmt.get("en") or ""
                color = el.get("formatted", {}).get("nameColor", "")
                if name:
                    stats.append({"key": name, "value": val, "type": "range", "color": color})
    return stats


def _txt(obj: dict) -> str:
    if not obj:
        return ""
    if obj.get("type") == "translation":
        return obj.get("lines", {}).get("ru") or obj.get("lines", {}).get("en") or ""
    if obj.get("type") == "text":
        return obj.get("text", "")
    lines = obj.get("lines", {})
    if isinstance(lines, dict):
        return lines.get("ru") or lines.get("en") or ""
    return ""


