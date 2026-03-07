"""API каталога предметов."""
from fastapi import APIRouter, Query
from services.item_loader import item_db
from config import CATEGORY_NAMES, RANK_NAMES
from db.models import SessionLocal, TrackedItem
from sqlalchemy import func
from services.cache import compute_cache, api_cache

router = APIRouter(tags=["catalog"])


def _cat_name(cat_id: str) -> str:
    """Русское название категории с fallback."""
    if cat_id in CATEGORY_NAMES:
        return CATEGORY_NAMES[cat_id]
    # Fallback: берём последний сегмент, заменяем _ на пробел
    last = cat_id.split("/")[-1].replace("_", " ")
    return last.capitalize()


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
                "name": _cat_name(sub),
                "count": len(item_db.get_by_category(sub)),
            })
        result.append({
            "id": cat,
            "name": _cat_name(cat),
            "count": count,
            "children": children,
        })
    return result


@router.get("/categories/{cat:path}/items")
async def get_category_items(
    cat: str,
    page: int = 1,
    per_page: int = 20,
    sort: str = "name",
):
    """Предметы в категории с пагинацией."""
    # Ограничиваем per_page чтобы не отдавать 200+ предметов
    per_page = max(1, min(per_page, 100))
    page = max(1, page)

    items = item_db.get_by_category(cat)
    if not items:
        items = item_db.get_all_in_category_tree(cat)

    # Сортировка
    if sort == "color":
        rank_order = {"RANK_LEGEND": 0, "RANK_MASTER": 1, "RANK_VETERAN": 2, "RANK_STALKER": 3, "RANK_NEWBIE": 4, "DEFAULT": 5}
        items.sort(key=lambda x: (rank_order.get(x.color, 9), x.name_ru))
    else:
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

    is_art = item.category.startswith("artefact")

    return {
        "id": item.item_id,
        "name": item.name_ru,
        "name_en": item.name_en,
        "category": item.category,
        "category_name": item.category_name,
        "color": item.color,
        "rank_name": RANK_NAMES.get(item.color, ""),
        "icon": _icon_url(item),
        "is_artefact": is_art,
        "api_supported": item.api_supported,
        "stats": stats,
    }


@router.get("/search")
async def search_items(
    q: str = Query("", min_length=1),
    limit: int = 20,
    sort: str = "relevance",
):
    results = item_db.search(q, limit=limit)
    if sort == "name":
        results.sort(key=lambda x: x.name_ru)
    elif sort == "color":
        rank_order = {"RANK_LEGEND": 0, "RANK_MASTER": 1, "RANK_VETERAN": 2, "RANK_STALKER": 3, "RANK_NEWBIE": 4, "DEFAULT": 5}
        results.sort(key=lambda x: (rank_order.get(x.color, 9), x.name_ru))
    # sort == "relevance" — оставляем порядок поисковика
    return [_item_short(i) for i in results]


@router.get("/popular")
async def popular_items(limit: int = 8):
    """Самые популярные предметы — по количеству продаж за 7 дней или по количеству отслеживаний."""
    cached = compute_cache.get(f"popular:{limit}")
    if cached is not None:
        return cached[:limit]

    from datetime import datetime, timedelta, timezone
    limit = max(1, min(limit, 20))

    result = []
    seen_ids = set()

    # Single DB session for all queries — avoid repeated open/close overhead
    with SessionLocal() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        # 1) Items with most sales in last 7 days
        try:
            from db.models import SaleRecord
            sale_rows = session.query(
                SaleRecord.item_id, func.count(SaleRecord.id).label("cnt")
            ).filter(SaleRecord.recorded_at >= cutoff).group_by(
                SaleRecord.item_id
            ).order_by(func.count(SaleRecord.id).desc()).limit(limit * 3).all()

            for item_id, cnt in sale_rows:
                if item_id in seen_ids:
                    continue
                gi = item_db.get(item_id)
                if gi:
                    d = _item_short(gi)
                    d["activity"] = cnt
                    result.append(d)
                    seen_ids.add(item_id)
                if len(result) >= limit:
                    break
        except Exception:
            pass

        # 2) Tracked items fallback
        if len(result) < limit:
            try:
                rows = session.query(
                    TrackedItem.item_id, func.count(TrackedItem.id).label("cnt")
                ).filter(TrackedItem.is_active == True).group_by(
                    TrackedItem.item_id
                ).order_by(func.count(TrackedItem.id).desc()).limit(limit * 2).all()
                for item_id, cnt in rows:
                    if item_id in seen_ids:
                        continue
                    gi = item_db.get(item_id)
                    if gi:
                        d = _item_short(gi)
                        d["activity"] = cnt
                        result.append(d)
                        seen_ids.add(item_id)
                    if len(result) >= limit:
                        break
            except Exception:
                pass

    # 3) Fill with known popular artefacts if still not enough
    if len(result) < limit:
        popular_arts = ["graviton", "kolobok", "mama", "crystal", "flash", "snowflake",
                        "kompas", "gravi", "night_star", "fireball"]
        all_items = item_db.get_all_in_category_tree("artefact")
        for a in all_items:
            if a.item_id in seen_ids:
                continue
            if any(pa in a.name_ru.lower() or pa in a.item_id.lower() for pa in popular_arts):
                d = _item_short(a)
                d["activity"] = 0
                result.append(d)
                seen_ids.add(a.item_id)
            if len(result) >= limit:
                break

    # Add trend data
    _attach_trends(result)

    compute_cache.set(f"popular:{limit}", result, ttl=300)
    return result


def _attach_trends(items: list[dict]):
    """Добавляет тренд (изменение цены за 7д) к каждому предмету — батчевый запрос."""
    from datetime import datetime, timedelta, timezone
    from db.models import SaleRecord
    if not items:
        return
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    cutoff_14d = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    ids = [i["id"] for i in items]
    try:
        with SessionLocal() as session:
            # Batch: avg price per item for last 7 days
            avg7_rows = session.query(
                SaleRecord.item_id, func.avg(SaleRecord.price)
            ).filter(
                SaleRecord.item_id.in_(ids),
                SaleRecord.time_sold >= cutoff_7d,
            ).group_by(SaleRecord.item_id).all()
            avg7_map = {r[0]: r[1] for r in avg7_rows}

            # Batch: avg price per item for 7-14 days ago
            avg14_rows = session.query(
                SaleRecord.item_id, func.avg(SaleRecord.price)
            ).filter(
                SaleRecord.item_id.in_(ids),
                SaleRecord.time_sold >= cutoff_14d,
                SaleRecord.time_sold < cutoff_7d,
            ).group_by(SaleRecord.item_id).all()
            avg14_map = {r[0]: r[1] for r in avg14_rows}

            for item_dict in items:
                iid = item_dict["id"]
                avg7 = avg7_map.get(iid)
                avg14 = avg14_map.get(iid)
                if avg7 and avg14 and avg14 > 0:
                    pct = round((avg7 - avg14) / avg14 * 100, 1)
                    item_dict["trend"] = pct
                else:
                    item_dict["trend"] = None
    except Exception:
        pass


def _icon_url(item) -> str:
    """Формирует URL иконки."""
    p = item.icon_path
    if not p or p.strip() == "":
        # Для wiki-предметов (8-char ID) пробуем кастомную иконку
        if not item.api_supported:
            return f"/custom-icons/{item.item_id}.png"
        return ""
    if p.startswith("http"):
        return p  # CDN URL
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
        "rank_name": RANK_NAMES.get(item.color, ""),
        "icon": _icon_url(item),
        "api_supported": item.api_supported,
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


@router.get("/compare")
async def compare_items(ids: str = Query("", description="item_ids через запятую")):
    """Данные для сравнения предметов (до 5 штук)."""
    id_list = [x.strip() for x in ids.split(",") if x.strip()]
    if not id_list:
        return {"error": "Укажите id предметов через запятую"}
    id_list = id_list[:5]

    results = []
    for iid in id_list:
        item = item_db.get(iid)
        if not item:
            continue
        details = item_db.get_item_details(iid)
        stats = _parse_stats(details) if details else []
        is_art = item.category.startswith("artefact")
        d = {
            "id": item.item_id,
            "name": item.name_ru,
            "category": item.category,
            "category_name": item.category_name,
            "color": item.color,
            "rank_name": RANK_NAMES.get(item.color, ""),
            "icon": _icon_url(item),
            "is_artefact": is_art,
            "stats": stats,
        }
        # Attach trend
        _attach_trends([d])
        results.append(d)

    return {"items": results}


# ── Combined home endpoint (1 request instead of 3) ──


@router.get("/home")
async def home_data():
    """Возвращает все данные главной страницы одним запросом."""
    cached = api_cache.get("home_data")
    if cached is not None:
        return cached

    from api.emission import get_emission
    from db.models import MarketListing, User as UserModel

    # Emission (cached internally at 15s)
    emi = await get_emission()

    # Popular items (cached internally at 300s)
    pop = await popular_items(limit=8)

    # Recent market listings — lightweight inline query
    mkt_items = []
    try:
        with SessionLocal() as session:
            rows = session.query(MarketListing, UserModel).outerjoin(
                UserModel, MarketListing.user_id == UserModel.id
            ).filter(
                MarketListing.status == "active"
            ).order_by(
                MarketListing.created_at.desc()
            ).limit(6).all()

            for l, u in rows:
                gi = item_db.get(l.item_id)
                mkt_items.append({
                    "id": l.id, "item_id": l.item_id,
                    "item_name": l.item_name or (gi.name_ru if gi else l.item_id),
                    "icon": _icon_url(gi) if gi else "",
                    "listing_type": l.listing_type, "price": l.price,
                    "amount": l.amount, "quality": l.quality,
                    "upgrade_level": l.upgrade_level,
                    "color": gi.color if gi else "DEFAULT",
                    "is_artefact": gi and gi.category.startswith("artefact") if gi else False,
                    "category_group": l.category_group or "other",
                    "status": l.status,
                    "created_at": l.created_at.isoformat() + "Z" if l.created_at else None,
                    "expires_at": l.expires_at.isoformat() + "Z" if l.expires_at else None,
                    "user": {"id": u.id, "display_name": u.display_name,
                             "avatar_url": u.avatar_url} if u else None,
                })
    except Exception:
        pass

    result = {
        "emission": emi,
        "popular": pop,
        "market": {"items": mkt_items, "total": len(mkt_items)},
    }
    api_cache.set("home_data", result, ttl=30)
    return result


