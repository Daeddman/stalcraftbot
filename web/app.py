"""
FastAPI-приложение PerekupHelper.
Раздаёт SPA-фронтенд и REST API для каталога, аукциона, отслеживания.
"""
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import GAME_DB_DIR, STALCRAFT_REGION, BASE_DIR
import web.routers.catalog as catalog
import web.routers.auction as auction
import web.routers.tracking as tracking
import web.routers.discovery as discovery
import web.routers.game as game
import web.routers.users as users
import web.routers.chat as chat
import web.routers.marketplace as marketplace
import web.routers.sync as sync
import web.routers.health as health
import web.routers.ws_chat as ws_chat

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
ICONS_DIR = GAME_DB_DIR / STALCRAFT_REGION / "icons"
THUMBS_DIR = GAME_DB_DIR / STALCRAFT_REGION / "icon-thumbs"
CUSTOM_ICONS_DIR = BASE_DIR / "custom_icons"
UPLOADS_DIR = BASE_DIR / "uploads"

# Версия для cache-busting (timestamp при старте сервера)
APP_VERSION = str(int(time.time()))

app = FastAPI(title="PerekupHelper", docs_url=None, redoc_url=None)


# ── Middleware: кеширование и no-cache ──
_CACHEABLE_API = ("/api/home", "/api/popular", "/api/emission", "/api/categories")
_CACHEABLE_PREFIX = ("/api/auction/", "/api/items/", "/api/search", "/api/clans", "/api/leaderboard")

class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.endswith((".js", ".css", ".html")) or path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif any(path == p for p in _CACHEABLE_API):
            response.headers["Cache-Control"] = "public, max-age=30"
        elif any(path.startswith(p) for p in _CACHEABLE_PREFIX):
            response.headers["Cache-Control"] = "public, max-age=15"
        return response


app.add_middleware(CacheControlMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API роутеры ──
app.include_router(catalog.router, prefix="/api")
app.include_router(auction.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(discovery.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(marketplace.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(health.router, prefix="/api")
# WebSocket — без /api prefix
app.include_router(ws_chat.router)

# ── Статика ──
app.mount("/icons", StaticFiles(directory=str(ICONS_DIR)), name="icons")
# Миниатюры иконок (64x64) — создаём директорию при старте
THUMBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/icon-thumbs", StaticFiles(directory=str(THUMBS_DIR)), name="icon_thumbs")
# Кастомные иконки (wiki-предметы, загруженные вручную)
if CUSTOM_ICONS_DIR.exists():
    app.mount("/custom-icons", StaticFiles(directory=str(CUSTOM_ICONS_DIR)), name="custom_icons")
# Загруженные файлы (аватары и т.д.)
os.makedirs(UPLOADS_DIR / "avatars", exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/version")
async def version():
    return {"v": APP_VERSION}


# Любой неизвестный путь → SPA (для hash-routing это не нужно, но на всякий)
# ВАЖНО: статические маршруты (/static, /icons и т.д.) обслуживаются mount-ами выше,
# но catch-all route может перехватить их раньше. Поэтому явно исключаем.
_STATIC_PREFIXES = ("static/", "icons/", "custom-icons/", "uploads/", "api/")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    # Если путь начинается со статического префикса — 404, а не index.html
    if any(full_path.startswith(p) for p in _STATIC_PREFIXES):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "not_found"}, status_code=404)
    return FileResponse(str(STATIC_DIR / "index.html"))

