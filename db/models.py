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
    UniqueConstraint,
    Index,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class TrackedItem(Base):
    """Предметы, которые пользователь отслеживает (избранное — per-user)."""

    __tablename__ = "tracked_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(String(128), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, default=None, index=True)
    name = Column(String(256), nullable=False)
    category = Column(String(128), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<TrackedItem {self.item_id} user={self.user_id}>"


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
    __table_args__ = (
        UniqueConstraint("item_id", "time_sold", "price", "amount", name="uq_sale_dedup"),
        Index("ix_sale_item_time", "item_id", "time_sold"),
    )

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


# ══════════════════════════════════════════════════════════════
#  History Sync: состояние выгрузки истории по предмету
# ══════════════════════════════════════════════════════════════

class HistorySyncState(Base):
    __tablename__ = "history_sync_state"

    item_id = Column(String(128), primary_key=True)
    total_api = Column(Integer, default=0)        # total из API
    total_stored = Column(Integer, default=0)      # сколько скачано
    newest_stored_time = Column(String(64), nullable=True)  # ISO время самой новой записи
    oldest_stored_offset = Column(Integer, default=0)  # до какого offset дошли при полной выгрузке
    full_download_done = Column(Boolean, default=False)
    priority = Column(Integer, default=2)  # 0=tracked, 1=popular, 2=all
    status = Column(String(16), default="idle")  # idle/syncing/done/error
    last_sync_at = Column(DateTime, nullable=True)
    error_msg = Column(String(256), nullable=True)


# ══════════════════════════════════════════════════════════════
#  Social: Пользователи
# ══════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(128), nullable=True)
    display_name = Column(String(128), nullable=False, default="Сталкер")
    game_nickname = Column(String(128), nullable=True)
    discord = Column(String(128), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    chat_color = Column(String(7), nullable=True)  # hex цвет в чате, напр. #e57373
    reputation = Column(Integer, default=0)
    last_active_at = Column(DateTime, nullable=True)  # онлайн-статус
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Social: Подписки (фолловеры)
# ══════════════════════════════════════════════════════════════

class UserFollow(Base):
    __tablename__ = "user_follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "target_id", name="uq_follow"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    follower_id = Column(Integer, nullable=False, index=True)  # кто подписался
    target_id = Column(Integer, nullable=False, index=True)    # на кого
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Social: Уведомления (in-app)
# ══════════════════════════════════════════════════════════════

class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # кому
    type = Column(String(32), default="message")  # message / listing_reply / follow / reputation
    title = Column(String(256), default="")
    body = Column(Text, default="")
    link = Column(String(256), nullable=True)  # hash-ссылка, напр. #/chat/dm:1_2
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Social: Отзывы о сделках (reputation)
# ══════════════════════════════════════════════════════════════

class ReputationReview(Base):
    __tablename__ = "reputation_reviews"
    __table_args__ = (
        UniqueConstraint("listing_id", "reviewer_id", name="uq_review"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, nullable=False, index=True)
    reviewer_id = Column(Integer, nullable=False)   # кто оставил
    target_id = Column(Integer, nullable=False, index=True)  # кому (owner листинга)
    score = Column(Integer, default=0)  # +1 или -1
    comment = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Social: Чат
# ══════════════════════════════════════════════════════════════

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_channel_created", "channel", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    channel = Column(String(64), default="general", index=True)
    text = Column(Text, nullable=False)
    reply_to_id = Column(Integer, nullable=True)
    sticker = Column(String(64), nullable=True)  # sticker code, e.g. "zone_clear", "loot"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatReaction(Base):
    """Реакции на сообщения в чате (emoji)."""
    __tablename__ = "chat_reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction"),
        Index("ix_reaction_message", "message_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    emoji = Column(String(8), nullable=False)  # 👍 ❤️ 🔥 😂 😢 💀
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ══════════════════════════════════════════════════════════════
#  Social: Торговая площадка
# ══════════════════════════════════════════════════════════════

class MarketListing(Base):
    __tablename__ = "market_listings"
    __table_args__ = (
        Index("ix_market_status_item", "status", "item_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    item_id = Column(String(128), nullable=False, index=True)
    item_name = Column(String(256), default="")
    listing_type = Column(String(8), default="sell")  # sell / buy
    price = Column(BigInteger, nullable=False)
    amount = Column(Integer, default=1)
    quality = Column(Integer, default=-1)
    upgrade_level = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    contact_method = Column(String(32), default="telegram")
    status = Column(String(16), default="active")  # active / sold / expired / cancelled
    sold_price = Column(BigInteger, nullable=True)  # фактическая цена продажи
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)


# ══════════════════════════════════════════════════════════════
#  Уведомления о выбросе (per-user)
# ══════════════════════════════════════════════════════════════

class EmissionNotifySetting(Base):
    __tablename__ = "emission_notify_settings"

    telegram_id = Column(BigInteger, primary_key=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Создание движка и сессии ──

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Создать все таблицы в БД и мигрировать недостающие колонки."""
    # WAL mode для лучшей параллельной работы
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    Base.metadata.create_all(engine)

    # ── Auto-migrate: добавляем недостающие колонки ──
    _migrate_columns()
    # ── Migrate tracked_items: убираем UNIQUE(item_id) для per-user избранного ──
    _migrate_tracked_items_unique()


def _migrate_columns():
    """
    Сравнивает модели SQLAlchemy с реальной схемой SQLite.
    Добавляет недостающие колонки через ALTER TABLE.
    Работает только для добавления — не удаляет и не меняет типы.
    """
    import logging
    from sqlalchemy import inspect as sa_inspect, text

    log = logging.getLogger(__name__)

    inspector = sa_inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        for table_name, table_obj in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue  # create_all уже создаст новые таблицы

            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}

            for col in table_obj.columns:
                if col.name in existing_cols:
                    continue

                # Определяем SQL-тип
                col_type = col.type.compile(engine.dialect)

                # Определяем DEFAULT
                default_clause = ""
                if col.default is not None:
                    if col.default.is_scalar:
                        val = col.default.arg
                        if isinstance(val, bool):
                            default_clause = f" DEFAULT {1 if val else 0}"
                        elif isinstance(val, (int, float)):
                            default_clause = f" DEFAULT {val}"
                        elif isinstance(val, str):
                            default_clause = f" DEFAULT '{val}'"
                    # callable defaults (like datetime.now) не могут быть в DDL
                elif col.nullable is not False:
                    default_clause = " DEFAULT NULL"

                sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"
                try:
                    conn.execute(text(sql))
                    log.info("✅ Миграция: %s.%s добавлена", table_name, col.name)
                except Exception as e:
                    # Колонка может уже существовать (race condition или duplicate)
                    if "duplicate column" not in str(e).lower():
                        log.warning("⚠️ Миграция %s.%s: %s", table_name, col.name, e)

        conn.commit()


def _migrate_tracked_items_unique():
    """
    SQLite не может DROP CONSTRAINT. Если tracked_items имеет UNIQUE(item_id),
    пересоздаём таблицу без этого ограничения (для per-user избранного).
    Также назначаем старые записи (user_id=NULL) первому пользователю.
    """
    import logging
    from sqlalchemy import text

    log = logging.getLogger(__name__)

    with engine.connect() as conn:
        # Проверяем, есть ли UNIQUE constraint на item_id
        row = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tracked_items'"
        )).first()
        if not row or not row[0]:
            return

        create_sql = row[0]
        # Если в DDL нет UNIQUE на item_id — миграция не нужна
        if "UNIQUE" not in create_sql.upper() or "item_id" not in create_sql.lower():
            # Дополнительная проверка: есть ли уникальный индекс на item_id
            indices = conn.execute(text(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='tracked_items'"
            )).fetchall()
            has_unique_idx = any("UNIQUE" in (idx[0] or "").upper() and "item_id" in (idx[0] or "").lower()
                                 for idx in indices if idx[0])
            if not has_unique_idx:
                return

        log.info("🔄 Миграция tracked_items: убираем UNIQUE(item_id)...")

        try:
            # 1. Rename old table
            conn.execute(text("ALTER TABLE tracked_items RENAME TO _tracked_items_old"))

            # 2. Create new table without UNIQUE
            conn.execute(text("""
                CREATE TABLE tracked_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id VARCHAR(128) NOT NULL,
                    user_id INTEGER,
                    name VARCHAR(256) NOT NULL,
                    category VARCHAR(128) DEFAULT '',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME
                )
            """))
            conn.execute(text("CREATE INDEX ix_tracked_items_item_id ON tracked_items (item_id)"))
            conn.execute(text("CREATE INDEX ix_tracked_items_user_id ON tracked_items (user_id)"))

            # 3. Copy data (add user_id column if it didn't exist)
            # Check if old table has user_id
            old_cols = {c[1] for c in conn.execute(text("PRAGMA table_info(_tracked_items_old)")).fetchall()}
            if "user_id" in old_cols:
                conn.execute(text("""
                    INSERT INTO tracked_items (id, item_id, user_id, name, category, is_active, created_at)
                    SELECT id, item_id, user_id, name, category, is_active, created_at
                    FROM _tracked_items_old
                """))
            else:
                conn.execute(text("""
                    INSERT INTO tracked_items (id, item_id, user_id, name, category, is_active, created_at)
                    SELECT id, item_id, NULL, name, category, is_active, created_at
                    FROM _tracked_items_old
                """))

            # 4. Drop old table
            conn.execute(text("DROP TABLE _tracked_items_old"))

            conn.commit()
            log.info("✅ tracked_items пересоздана без UNIQUE(item_id)")
        except Exception as e:
            conn.rollback()
            log.error("❌ Ошибка миграции tracked_items: %s", e)

