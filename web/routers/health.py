"""Health check endpoint — мониторинг состояния системы."""
import time
import logging
from fastapi import APIRouter, Request
from db.models import SessionLocal, SaleRecord, HistorySyncState
from sqlalchemy import text, func

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health")
async def health(request: Request):
    """Полная диагностика состояния системы."""
    now = time.time()
    uptime_sec = now - _START_TIME

    # DB check
    db_ok = False
    db_tables = 0
    total_sales = 0
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            db_ok = True
            rows = session.execute(text(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            )).scalar()
            db_tables = rows or 0
            total_sales = session.query(func.count(SaleRecord.id)).scalar() or 0
    except Exception as exc:
        logger.warning("Health DB check failed: %s", exc)

    # Scheduler
    scheduler = getattr(request.app.state, "scheduler", None)
    sched_info = {}
    if scheduler:
        try:
            jobs = scheduler.get_jobs()
            sched_info = {
                "running": scheduler.running,
                "jobs_count": len(jobs),
                "jobs": [
                    {
                        "id": j.id,
                        "name": j.name,
                        "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
                    }
                    for j in jobs
                ],
            }
        except Exception:
            sched_info = {"running": False, "error": "unavailable"}
    else:
        sched_info = {"running": False, "error": "not_attached"}

    # Bot token check
    from config import TELEGRAM_BOT_TOKEN
    bot_configured = bool(TELEGRAM_BOT_TOKEN)

    # Sync status
    sync_info = {}
    try:
        with SessionLocal() as session:
            total_items = session.query(func.count(HistorySyncState.item_id)).scalar() or 0
            done = session.query(func.count(HistorySyncState.item_id)).filter(
                HistorySyncState.full_download_done.is_(True)
            ).scalar() or 0
            sync_info = {
                "total_items": total_items,
                "synced": done,
                "percent": round(done / total_items * 100, 1) if total_items else 0,
            }
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "uptime_seconds": round(uptime_sec),
        "uptime_human": _fmt_uptime(uptime_sec),
        "db": {
            "ok": db_ok,
            "tables": db_tables,
            "total_sales": total_sales,
        },
        "scheduler": sched_info,
        "bot": {"configured": bot_configured},
        "history_sync": sync_info,
        "timestamp": now,
    }


def _fmt_uptime(sec: float) -> str:
    d = int(sec // 86400)
    h = int(sec % 86400 // 3600)
    m = int(sec % 3600 // 60)
    parts = []
    if d:
        parts.append(f"{d}д")
    if h:
        parts.append(f"{h}ч")
    parts.append(f"{m}м")
    return " ".join(parts)

