"""
CRUD-операции с базой данных.
"""

from sqlalchemy import select

from db.models import (
    SessionLocal,
    TrackedItem,
    Alert,
)


# ══════════════════════════════════════════════════════════════
#  TrackedItem
# ══════════════════════════════════════════════════════════════


def get_active_tracked_items(user_id: int = None) -> list[TrackedItem]:
    """Активные отслеживаемые предметы для конкретного пользователя."""
    if user_id is None:
        return []
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
#  Alert
# ══════════════════════════════════════════════════════════════


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

