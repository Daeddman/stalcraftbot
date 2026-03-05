"""API: статус синхронизации истории продаж."""
from fastapi import APIRouter, Query
from sqlalchemy import func
from db.models import SessionLocal, HistorySyncState, SaleRecord

router = APIRouter(tags=["sync"])


@router.get("/sync/status")
async def sync_status():
    """Общая статистика синхронизации истории."""
    with SessionLocal() as session:
        total = session.query(func.count(HistorySyncState.item_id)).scalar() or 0
        done = session.query(func.count(HistorySyncState.item_id)).filter(
            HistorySyncState.full_download_done.is_(True)
        ).scalar() or 0
        syncing = session.query(func.count(HistorySyncState.item_id)).filter(
            HistorySyncState.status == "syncing"
        ).scalar() or 0
        errors = session.query(func.count(HistorySyncState.item_id)).filter(
            HistorySyncState.status == "error"
        ).scalar() or 0
        total_sales = session.query(func.count(SaleRecord.id)).scalar() or 0

        return {
            "total_items": total,
            "done": done,
            "syncing": syncing,
            "errors": errors,
            "idle": total - done - syncing - errors,
            "total_sales_records": total_sales,
        }


@router.get("/sync/items")
async def sync_items(
    status: str = Query("", description="idle/syncing/done/error"),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    """Постраничный список HistorySyncState."""
    with SessionLocal() as session:
        q = session.query(HistorySyncState)
        if status:
            q = q.filter(HistorySyncState.status == status)
        total = q.count()
        items = q.order_by(HistorySyncState.priority, HistorySyncState.item_id) \
            .offset((page - 1) * per_page).limit(per_page).all()

        return {
            "total": total,
            "pages": max(1, -(-total // per_page)),
            "items": [
                {
                    "item_id": s.item_id,
                    "total_api": s.total_api,
                    "total_stored": s.total_stored,
                    "full_download_done": s.full_download_done,
                    "priority": s.priority,
                    "status": s.status,
                    "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
                    "error_msg": s.error_msg,
                }
                for s in items
            ],
        }

