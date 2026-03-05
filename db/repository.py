"""
CRUD-операции с базой данных.
Поддержка фильтрации по качеству (quality) и заточке (upgrade_level) для артефактов.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func

from db.models import (
    SessionLocal,
    TrackedItem,
    PriceRecord,
    SaleRecord,
    Alert,
)


# ══════════════════════════════════════════════════════════════
#  Константы редкости (качество артефактов / лотов)
#  Соответствуют рангам предметов в Stalcraft:
#  0 = Обычный (Отмычка) — Белый
#  1 = Необычный (Новичок) — Ярко-зелёный
#  2 = Особый (Сталкер) — Синий
#  3 = Редкий (Ветеран) — Розовый
#  4 = Исключительный (Мастер) — Красный
#  5 = Легендарный (Легенда) — Жёлтый/Золотой
# ══════════════════════════════════════════════════════════════

QUALITY_NAMES: dict[int, str] = {
    -1: "Неизвестно",
    0: "Обычный",
    1: "Необычный",
    2: "Особый",
    3: "Редкий",
    4: "Исключительный",
    5: "Легендарный",
}

QUALITY_SHORT: dict[int, str] = {
    -1: "???",
    0: "Обычный",
    1: "Необычный",
    2: "Особый",
    3: "Редкий",
    4: "Исключ.",
    5: "Легенд.",
}


def quality_name(qlt: int) -> str:
    return QUALITY_NAMES.get(qlt, f"#{qlt}")


def quality_short(qlt: int) -> str:
    return QUALITY_SHORT.get(qlt, f"#{qlt}")


def upgrade_str(level: int) -> str:
    return f"+{level}" if level > 0 else ""


# ══════════════════════════════════════════════════════════════
#  TrackedItem
# ══════════════════════════════════════════════════════════════


def get_active_tracked_items(user_id: int = None) -> list[TrackedItem]:
    """Активные отслеживаемые предметы для конкретного пользователя."""
    if user_id is None:
        return []  # Без авторизации — пустой список
    with SessionLocal() as session:
        stmt = (
            select(TrackedItem)
            .where(TrackedItem.is_active.is_(True))
            .where(TrackedItem.user_id == user_id)
        )
        return list(session.scalars(stmt).all())


def add_tracked_item(item_id: str, name: str, category: str = "", user_id: int = None) -> TrackedItem:
    """Добавить предмет в отслеживание для пользователя."""
    with SessionLocal() as session:
        q = select(TrackedItem).where(
            TrackedItem.item_id == item_id,
            TrackedItem.user_id == user_id,
        )
        existing = session.scalar(q)
        if existing:
            existing.is_active = True
            existing.name = name
            session.commit()
            session.refresh(existing)
            return existing

        item = TrackedItem(item_id=item_id, name=name, category=category, user_id=user_id)
        session.add(item)
        session.commit()
        session.refresh(item)
        return item


def remove_tracked_item(item_id: str, user_id: int = None) -> bool:
    """Деактивировать отслеживание предмета для пользователя."""
    with SessionLocal() as session:
        q = select(TrackedItem).where(
            TrackedItem.item_id == item_id,
            TrackedItem.user_id == user_id,
        )
        item = session.scalar(q)
        if item:
            item.is_active = False
            session.commit()
            return True
        return False


# ══════════════════════════════════════════════════════════════
#  PriceRecord
# ══════════════════════════════════════════════════════════════


def save_price_records(records: list[dict]) -> int:
    """
    Сохранить пачку ценовых записей.
    records: [{"item_id", "price", "amount", "lot_id", "time_created", "quality", "upgrade_level"}]
    """
    with SessionLocal() as session:
        count = 0
        for r in records:
            pr = PriceRecord(
                item_id=r["item_id"],
                price=r["price"],
                amount=r.get("amount", 1),
                lot_id=r.get("lot_id", ""),
                time_created=r.get("time_created", ""),
                quality=r.get("quality", -1),
                upgrade_level=r.get("upgrade_level", 0),
            )
            session.add(pr)
            count += 1
        session.commit()
        return count


def get_avg_price(
    item_id: str,
    hours: int = 24,
    quality: int | None = None,
    upgrade_level: int | None = None,
) -> float | None:
    """Средняя цена лотов. Если quality/upgrade_level заданы — фильтруем."""
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.avg(PriceRecord.price))
            .where(PriceRecord.item_id == item_id)
            .where(PriceRecord.recorded_at >= since)
        )
        if quality is not None:
            stmt = stmt.where(PriceRecord.quality == quality)
        if upgrade_level is not None:
            stmt = stmt.where(PriceRecord.upgrade_level == upgrade_level)
        result = session.scalar(stmt)
        return float(result) if result else None


def get_min_price(
    item_id: str,
    hours: int = 24,
    quality: int | None = None,
    upgrade_level: int | None = None,
) -> int | None:
    """Минимальная цена лотов."""
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.min(PriceRecord.price))
            .where(PriceRecord.item_id == item_id)
            .where(PriceRecord.recorded_at >= since)
        )
        if quality is not None:
            stmt = stmt.where(PriceRecord.quality == quality)
        if upgrade_level is not None:
            stmt = stmt.where(PriceRecord.upgrade_level == upgrade_level)
        result = session.scalar(stmt)
        return int(result) if result else None


def get_price_count(
    item_id: str,
    hours: int = 24,
    quality: int | None = None,
    upgrade_level: int | None = None,
) -> int:
    """Количество ценовых записей."""
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.count(PriceRecord.id))
            .where(PriceRecord.item_id == item_id)
            .where(PriceRecord.recorded_at >= since)
        )
        if quality is not None:
            stmt = stmt.where(PriceRecord.quality == quality)
        if upgrade_level is not None:
            stmt = stmt.where(PriceRecord.upgrade_level == upgrade_level)
        result = session.scalar(stmt)
        return int(result) if result else 0


def get_price_history_db(
    item_id: str,
    hours: int = 168,
    quality: int | None = None,
    upgrade_level: int | None = None,
) -> list[PriceRecord]:
    """Ценовые записи предмета за последние N часов (по умолчанию 7 дней)."""
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(PriceRecord)
            .where(PriceRecord.item_id == item_id)
            .where(PriceRecord.recorded_at >= since)
        )
        if quality is not None:
            stmt = stmt.where(PriceRecord.quality == quality)
        if upgrade_level is not None:
            stmt = stmt.where(PriceRecord.upgrade_level == upgrade_level)
        stmt = stmt.order_by(PriceRecord.recorded_at.desc())
        return list(session.scalars(stmt).all())


def get_quality_breakdown(item_id: str, hours: int = 168) -> list[dict]:
    """
    Разбивка цен по (quality, upgrade_level) для предмета.
    Возвращает [{quality, upgrade_level, avg_price, min_price, count}, ...]
    Пропускает quality=-1 (неизвестное).
    """
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(
                SaleRecord.quality,
                SaleRecord.upgrade_level,
                func.avg(SaleRecord.price).label("avg_price"),
                func.min(SaleRecord.price).label("min_price"),
                func.count(SaleRecord.id).label("cnt"),
            )
            .where(SaleRecord.item_id == item_id)
            .where(SaleRecord.recorded_at >= since)
            .where(SaleRecord.quality >= 0)
            .group_by(SaleRecord.quality, SaleRecord.upgrade_level)
            .order_by(SaleRecord.quality, SaleRecord.upgrade_level)
        )
        rows = session.execute(stmt).all()
        return [
            {
                "quality": r.quality,
                "upgrade_level": r.upgrade_level,
                "avg_price": float(r.avg_price),
                "min_price": int(r.min_price),
                "count": int(r.cnt),
            }
            for r in rows
        ]


# ══════════════════════════════════════════════════════════════
#  SaleRecord
# ══════════════════════════════════════════════════════════════


def save_sale_records(records: list[dict]) -> int:
    """Сохранить записи продаж из истории."""
    with SessionLocal() as session:
        count = 0
        for r in records:
            sr = SaleRecord(
                item_id=r["item_id"],
                price=r["price"],
                amount=r.get("amount", 1),
                time_sold=r.get("time", ""),
                quality=r.get("quality", -1),
                upgrade_level=r.get("upgrade_level", 0),
            )
            session.add(sr)
            count += 1
        session.commit()
        return count


def get_avg_sale_price(
    item_id: str,
    hours: int = 168,
    quality: int | None = None,
    upgrade_level: int | None = None,
) -> float | None:
    """Средняя цена продажи за последние N часов (по умолчанию 7 дней)."""
    with SessionLocal() as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.avg(SaleRecord.price))
            .where(SaleRecord.item_id == item_id)
            .where(SaleRecord.recorded_at >= since)
        )
        if quality is not None:
            stmt = stmt.where(SaleRecord.quality == quality)
        if upgrade_level is not None:
            stmt = stmt.where(SaleRecord.upgrade_level == upgrade_level)
        result = session.scalar(stmt)
        return float(result) if result else None


# ══════════════════════════════════════════════════════════════
#  Alert
# ══════════════════════════════════════════════════════════════


def was_alert_sent(item_id: str, lot_id: str) -> bool:
    """Проверить, отправляли ли уже алерт по этому лоту."""
    with SessionLocal() as session:
        result = session.scalar(
            select(Alert)
            .where(Alert.item_id == item_id)
            .where(Alert.lot_id == lot_id)
        )
        return result is not None


def save_alert(
    item_id: str,
    lot_id: str,
    price: int,
    avg_price: int,
    discount_percent: float,
    message: str,
    quality: int = -1,
    upgrade_level: int = 0,
) -> Alert:
    """Сохранить запись об отправленном алерте."""
    with SessionLocal() as session:
        alert = Alert(
            item_id=item_id,
            lot_id=lot_id,
            price=price,
            avg_price=avg_price,
            discount_percent=discount_percent,
            quality=quality,
            upgrade_level=upgrade_level,
            message=message,
        )
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert

