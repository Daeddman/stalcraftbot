"""WebSocket-менеджер для чата — замена polling."""
import asyncio, json, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from db.models import SessionLocal, User

logger = logging.getLogger("ws_chat")
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._channels: dict[str, set[tuple[WebSocket, int]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, channel: str, user_id: int):
        await ws.accept()
        async with self._lock:
            self._channels.setdefault(channel, set()).add((ws, user_id))

    async def disconnect(self, ws: WebSocket, channel: str, user_id: int):
        async with self._lock:
            ch = self._channels.get(channel, set())
            ch.discard((ws, user_id))
            if not ch:
                self._channels.pop(channel, None)

    async def broadcast(self, channel: str, event: dict, exclude_user: int | None = None):
        ch = self._channels.get(channel, set())
        if not ch:
            return
        data = json.dumps(event, ensure_ascii=False, default=str)
        dead = []
        for ws, uid in ch.copy():
            if exclude_user and uid == exclude_user:
                continue
            try:
                await ws.send_text(data)
            except Exception:
                dead.append((ws, uid))
        if dead:
            async with self._lock:
                for item in dead:
                    self._channels.get(channel, set()).discard(item)

    def total_connections(self) -> int:
        return sum(len(c) for c in self._channels.values())

    def stats(self) -> dict:
        return {"total": self.total_connections(),
                "channels": {ch: len(c) for ch, c in self._channels.items()}}


manager = ConnectionManager()


def _auth_ws(token: str) -> int | None:
    try:
        from web.auth import _parse_init_data
        ud = _parse_init_data(token)
        if not ud:
            return None
        tg_id = ud.get("id")
        if not tg_id:
            return None
        with SessionLocal() as s:
            u = s.query(User).filter_by(telegram_id=int(tg_id)).first()
            return u.id if u else None
    except Exception:
        return None


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket, token: str = Query(""), channel: str = Query("general")):
    uid = _auth_ws(token) if token else None
    if not uid:
        await ws.accept()
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            return
        return
    await manager.connect(ws, channel, uid)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await manager.disconnect(ws, channel, uid)

