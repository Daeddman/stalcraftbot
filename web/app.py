"""
FastAPI-приложение PerekupHelper.
Раздаёт SPA-фронтенд и REST API для каталога, аукциона, отслеживания.
"""
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

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

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
ICONS_DIR = GAME_DB_DIR / STALCRAFT_REGION / "icons"
CUSTOM_ICONS_DIR = BASE_DIR / "custom_icons"
UPLOADS_DIR = BASE_DIR / "uploads"

app = FastAPI(title="PerekupHelper", docs_url=None, redoc_url=None)

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

# ── Статика ──
app.mount("/icons", StaticFiles(directory=str(ICONS_DIR)), name="icons")
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


# Любой неизвестный путь → SPA (для hash-routing это не нужно, но на всякий)
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    file = STATIC_DIR / full_path
    if file.is_file():
        return FileResponse(str(file))
    return FileResponse(str(STATIC_DIR / "index.html"))

