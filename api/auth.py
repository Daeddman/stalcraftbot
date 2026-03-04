"""
OAuth2 Client Credentials авторизация для Stalcraft API.
Автоматически обновляет access_token по истечении срока.
"""

import time
import logging
import httpx

from config import STALCRAFT_CLIENT_ID, STALCRAFT_CLIENT_SECRET, AUTH_URL

logger = logging.getLogger(__name__)


class TokenManager:
    """Управляет OAuth2-токеном с автообновлением."""

    def __init__(self) -> None:
        self._access_token: str = ""
        self._expires_at: float = 0.0

    @property
    def is_expired(self) -> bool:
        # обновляем за 60 секунд до истечения
        return time.time() >= (self._expires_at - 60)

    async def get_token(self) -> str:
        """Возвращает действующий access_token, обновляя при необходимости."""
        if not self._access_token or self.is_expired:
            await self._refresh_token()
        return self._access_token

    async def _refresh_token(self) -> None:
        """Запрашивает новый токен через Client Credentials flow."""
        logger.info("Запрашиваю новый OAuth2 токен...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": STALCRAFT_CLIENT_ID,
                    "client_secret": STALCRAFT_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self._expires_at = time.time() + expires_in

        logger.info("Токен получен, истекает через %d сек.", expires_in)


# Глобальный экземпляр
token_manager = TokenManager()

