"""
SQLAlchemy модели для хранения данных аукциона.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    BigInteger,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class TrackedItem(Base):
    """Предметы, которые мы отслеживаем на аукционе."""

    __tablename__ = "tracked_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    category = Column(String(128), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<TrackedItem {self.item_id} '{self.name}'>"


class PriceRecord(Base):
    """Запись цены лота с аукциона (снимок)."""

    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False, index=True)
    price = Column(BigInteger, nullable=False)
    amount = Column(Integer, default=1)
    lot_id = Column(String(256), default="")
    time_created = Column(String(64), default="")
    quality = Column(Integer, default=-1)       # -1=неизв, 0=Обычный..4=Легенд, 5=Эпик
    upgrade_level = Column(Integer, default=0)  # 0..15
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<PriceRecord {self.item_id} q{self.quality} +{self.upgrade_level} price={self.price}>"


class SaleRecord(Base):
    """Историческая запись продажи (из /history)."""

    __tablename__ = "sale_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False, index=True)
    price = Column(BigInteger, nullable=False)
    amount = Column(Integer, default=1)
    time_sold = Column(String(64), default="")
    quality = Column(Integer, default=-1)
    upgrade_level = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<SaleRecord {self.item_id} q{self.quality} +{self.upgrade_level} price={self.price}>"


class Alert(Base):
    """Отправленные уведомления (чтобы не дублировать)."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False, index=True)
    lot_id = Column(String(256), default="")
    price = Column(BigInteger, nullable=False)
    avg_price = Column(BigInteger, default=0)
    discount_percent = Column(Float, default=0.0)
    quality = Column(Integer, default=-1)
    upgrade_level = Column(Integer, default=0)
    message = Column(Text, default="")
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Alert {self.item_id} q{self.quality}+{self.upgrade_level} -{self.discount_percent:.0f}%>"


# ── Создание движка и сессии ──

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Создать все таблицы в БД."""
    Base.metadata.create_all(engine)

