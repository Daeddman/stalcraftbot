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


# ══════════════════════════════════════════════════════════════
#  Discovery: Registry предметов (живёт независимо от official DB)
# ══════════════════════════════════════════════════════════════

class ItemRegistry(Base):
    """
    Любой предмет, о котором мы знаем.
    source: official_db | wiki | observed | manual
    """
    __tablename__ = "items_registry"

    item_id = Column(String(128), primary_key=True)
    name = Column(String(256), nullable=True)
    category = Column(String(128), nullable=True)
    icon_url = Column(String(512), nullable=True)
    color = Column(String(64), default="DEFAULT")
    source = Column(String(32), default="observed")
    is_official_db = Column(Boolean, default=False)
    extra_json = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Discovery: Активные лоты (текущий снимок — upsert по lot_id)
# ══════════════════════════════════════════════════════════════

class ActiveLot(Base):
    __tablename__ = "active_lots"

    lot_id = Column(String(256), primary_key=True)
    item_id = Column(String(128), nullable=False, index=True)
    region = Column(String(8), default="ru")

    start_price = Column(BigInteger, nullable=True)
    buyout_price = Column(BigInteger, nullable=True)
    current_price = Column(BigInteger, nullable=True)
    amount = Column(Integer, default=1)

    quality = Column(Integer, default=-1)
    upgrade_level = Column(Integer, default=0)
    additional_json = Column(Text, nullable=True)

    start_time = Column(String(64), nullable=True)
    end_time = Column(String(64), nullable=True)

    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Discovery: События лотов (created / updated / disappeared)
# ══════════════════════════════════════════════════════════════

class LotEvent(Base):
    __tablename__ = "lot_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_id = Column(String(256), nullable=False, index=True)
    item_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # created | updated | disappeared
    price = Column(BigInteger, nullable=True)
    amount = Column(Integer, nullable=True)
    details_json = Column(Text, nullable=True)
    event_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Discovery: Агрегированные ценовые сэмплы (для графиков)
# ══════════════════════════════════════════════════════════════

class PriceSample(Base):
    __tablename__ = "price_samples"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False, index=True)
    region = Column(String(8), default="ru")

    min_price = Column(BigInteger, nullable=True)
    median_price = Column(BigInteger, nullable=True)
    avg_price = Column(BigInteger, nullable=True)
    max_price = Column(BigInteger, nullable=True)
    lots_count = Column(Integer, default=0)
    total_amount = Column(Integer, default=0)

    sampled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Discovery: Текущая статистика цены (быстрый доступ — upsert)
# ══════════════════════════════════════════════════════════════

class ItemPriceStats(Base):
    __tablename__ = "item_price_stats"

    item_id = Column(String(128), primary_key=True)
    region = Column(String(8), default="ru")

    min_price = Column(BigInteger, nullable=True)
    median_price = Column(BigInteger, nullable=True)
    avg_price = Column(BigInteger, nullable=True)
    lots_count = Column(Integer, default=0)
    total_amount = Column(Integer, default=0)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Создание движка и сессии ──

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Создать все таблицы в БД."""
    # WAL mode для лучшей параллельной работы
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    Base.metadata.create_all(engine)

