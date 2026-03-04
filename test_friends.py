"""
Тестовый скрипт для эндпоинта друзей Stalcraft API.
GET /{region}/friends/{character}
"""
import asyncio
import httpx

CLIENT_ID = "1624"
CLIENT_SECRET = "BctSoPOSzfOgAkMAbqZspoABnUb0qKaZLimcAUmE"
AUTH_URL = "https://exbo.net/oauth/token"
API_BASE = "https://eapi.stalcraft.net"


async def get_token() -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(AUTH_URL, data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def get_friends(region: str, character: str):
    token = await get_token()
    print(f"Token: OK")
    print(f"Запрос: GET /{region}/friends/{character}\n")

    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(
            f"{API_BASE}/{region}/friends/{character}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        print(f"Body:\n{r.text}")


if __name__ == "__main__":
    import sys
    region = sys.argv[1] if len(sys.argv) > 1 else "ru"
    character = sys.argv[2] if len(sys.argv) > 2 else "Daeddman"

    print(f"=== Stalcraft Friends API Test ===")
    print(f"Region: {region}")
    print(f"Character: {character}\n")

    asyncio.run(get_friends(region, character))

