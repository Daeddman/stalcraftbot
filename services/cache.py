"""
Централизованный in-memory кеш с TTL.
Замена разрозненных dict-кешей по всему проекту.
При масштабировании до нескольких воркеров — заменить на Redis.
"""
import time
import logging
from typing import Any

logger = logging.getLogger("cache")


class TTLCache:
    """Простой кеш с TTL, maxsize и автоочисткой."""

    def __init__(self, maxsize: int = 1024, default_ttl: int = 60):
        self._store: dict[str, tuple[Any, float]] = {}
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return value

    def set(self, key: str, value: Any, ttl: int | None = None):
        if len(self._store) >= self._maxsize:
            self._evict()
        self._store[key] = (value, time.time() + (ttl or self._default_ttl))

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()

    def invalidate_prefix(self, prefix: str):
        """Удаляет все ключи с данным префиксом."""
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]

    def stats(self) -> dict:
        now = time.time()
        alive = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {
            "size": len(self._store),
            "alive": alive,
            "maxsize": self._maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / max(1, self._hits + self._misses) * 100, 1),
        }

    def _evict(self):
        """Удаляет протухшие, затем самые старые."""
        now = time.time()
        # Сначала протухшие
        expired = [k for k, (_, exp) in self._store.items() if exp <= now]
        for k in expired:
            del self._store[k]
        # Если всё ещё полно — удаляем 25% самых старых
        if len(self._store) >= self._maxsize:
            sorted_keys = sorted(self._store.keys(), key=lambda k: self._store[k][1])
            to_remove = sorted_keys[: self._maxsize // 4]
            for k in to_remove:
                del self._store[k]


# ── Глобальные экземпляры кешей ──

# Для аукционных данных (лоты, история) — discovery обновляет каждые 5 мин
auction_cache = TTLCache(maxsize=4096, default_ttl=300)

# Для API-ответов (emission, catalog, clans)
api_cache = TTLCache(maxsize=2048, default_ttl=120)

# Для тяжёлых вычислений (popular items, chart-data)
compute_cache = TTLCache(maxsize=1024, default_ttl=600)

