"""
Асинхронный HTTP-клиент для Stalcraft API.
Включает rate limiting, retry с exponential backoff и авто-токен.
"""

import asyncio
import logging
from typing import Any

import httpx

from config import API_BASE_URL, MAX_REQUESTS_PER_SECOND
from api.auth import token_manager

logger = logging.getLogger(__name__)

# Семафор для ограничения параллельных запросов
_semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_SECOND)


class StalcraftClient:
    """HTTP-клиент к Stalcraft API с rate-limiting и retry."""

    MAX_RETRIES = 5
    BACKOFF_BASE = 1.5  # секунды

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=API_BASE_URL,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

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
            async with _semaphore:
                # Небольшая задержка для соблюдения rate-limit
                await asyncio.sleep(1.0 / MAX_REQUESTS_PER_SECOND)

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

                    # Другие ошибки — выбрасываем сразу
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

