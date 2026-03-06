"""Аудит-логирование действий пользователей."""
import json
import logging
from datetime import datetime
from db.models import SessionLocal

logger = logging.getLogger("audit")

# Типы действий
ACTION_CHAT_MESSAGE = "chat_message"
ACTION_CHAT_DELETE = "chat_delete"
ACTION_LISTING_CREATE = "listing_create"
ACTION_LISTING_UPDATE = "listing_update"
ACTION_LISTING_CANCEL = "listing_cancel"
ACTION_PROFILE_EDIT = "profile_edit"
ACTION_AVATAR_UPLOAD = "avatar_upload"
ACTION_FAVORITE_ADD = "favorite_add"
ACTION_FAVORITE_REMOVE = "favorite_remove"
ACTION_USER_BLOCK = "user_block"
ACTION_USER_UNBLOCK = "user_unblock"
ACTION_DM_DELETE = "dm_delete"


def log_action(
    user_id: int | None,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    details: dict | None = None,
    ip: str | None = None,
):
    """
    Записывает действие в таблицу audit_log.
    Не бросает исключений — ошибки логируются.
    """
    try:
        from db.models import AuditLog
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        with SessionLocal() as session:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else "",
                details_json=details_json,
                ip=ip,
            )
            session.add(entry)
            session.commit()
    except Exception as exc:
        logger.debug("Audit log error: %s", exc)

