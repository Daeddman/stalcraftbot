"""
Асинхронный HTTP-клиент для Stalcraft API.
Включает rate limiting (token bucket), retry с exponential backoff и авто-токен.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from config import API_BASE_URL, MAX_REQUESTS_PER_SECOND
from api.auth import token_manager

logger = logging.getLogger(__name__)


class InvalidItemError(Exception):
    """API вернул 400 'Invalid item id' — предмет не поддерживается."""
    pass


class _TokenBucket:
    """Token bucket rate limiter — точнее, чем semaphore + sleep."""
    def __init__(self, rate: float):
        self._rate = rate  # tokens per second
        self._tokens = rate
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last = now
            if self._tokens < 1:
                wait = (1 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0
            else:
                self._tokens -= 1


_bucket = _TokenBucket(rate=MAX_REQUESTS_PER_SECOND)


class StalcraftClient:
    """HTTP-клиент к Stalcraft API с rate-limiting и retry."""

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=API_BASE_URL,
                timeout=15.0,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """
        Выполняет запрос к API с авто-токеном, rate limiting и retry.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            await _bucket.acquire()

            token = await token_manager.get_token()
            client = await self._get_client()

            try:
                resp = await client.request(
                    method,
                    path,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                    **kwargs,
                )

                if resp.status_code == 200:
                    return resp.json()

                if resp.status_code == 429:
                    retry_after = float(
                        resp.headers.get("Retry-After", self.BACKOFF_BASE * attempt)
                    )
                    logger.warning(
                        "Rate limit (429). Жду %.1f сек. (попытка %d/%d)",
                        retry_after, attempt, self.MAX_RETRIES,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code >= 500:
                    wait = self.BACKOFF_BASE ** attempt
                    logger.warning(
                        "Сервер вернул %d. Жду %.1f сек. (попытка %d/%d)",
                        resp.status_code, wait, attempt, self.MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 404:
                    resp.raise_for_status()

                if resp.status_code == 400:
                    try:
                        body = resp.json()
                        title = body.get("title", "")
                        if "Invalid item id" in title:
                            raise InvalidItemError(title)
                    except InvalidItemError:
                        raise
                    except Exception:
                        pass

                resp.raise_for_status()

            except httpx.TransportError as exc:
                wait = self.BACKOFF_BASE ** attempt
                logger.warning(
                    "Ошибка сети: %s. Жду %.1f сек. (попытка %d/%d)",
                    exc, wait, attempt, self.MAX_RETRIES,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(f"Не удалось выполнить запрос {method} {path} после {self.MAX_RETRIES} попыток")

    # ── Удобные методы ──

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", path, params=params)


# Глобальный экземпляр
stalcraft_client = StalcraftClient()

