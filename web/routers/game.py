"""API роутер: выброс, кланы, персонажи."""
from fastapi import APIRouter, Depends
from api.emission import get_emission
from api.characters import get_clan_info, get_clan_members, get_character_profile
from db.models import SessionLocal, EmissionNotifySetting, User
from web.auth import get_current_user, require_user

router = APIRouter(tags=["game"])


@router.get("/emission")
async def emission():
    return await get_emission()


@router.get("/emission/debug")
async def emission_debug():
    """Диагностика emission checker — текущее состояние, подписчики, raw API."""
    from services.alerter import get_emission_debug
    from api.emission import get_emission as _get_emi

    checker = get_emission_debug()
    raw = await _get_emi(force=True)

    with SessionLocal() as session:
        subs = session.query(EmissionNotifySetting).all()
        sub_list = [{"telegram_id": s.telegram_id, "enabled": s.enabled} for s in subs]

    return {
        "checker_state": checker,
        "api_raw": raw,
        "subscribers": sub_list,
        "subscriber_count_enabled": sum(1 for s in sub_list if s["enabled"]),
    }


@router.get("/emission/settings")
async def emission_settings(user: User = Depends(get_current_user)):
    """Получить настройки уведомлений о выбросе."""
    if not user:
        return {"enabled": False, "authenticated": False}
    with SessionLocal() as session:
        s = session.query(EmissionNotifySetting).filter_by(telegram_id=user.telegram_id).first()
        return {"enabled": s.enabled if s else False, "authenticated": True}


@router.post("/emission/settings")
async def toggle_emission(user: User = Depends(require_user)):
    """Переключить уведомления о выбросе."""
    with SessionLocal() as session:
        s = session.query(EmissionNotifySetting).filter_by(telegram_id=user.telegram_id).first()
        if s:
            s.enabled = not s.enabled
        else:
            s = EmissionNotifySetting(telegram_id=user.telegram_id, enabled=True)
            session.add(s)
        session.commit()
        return {"enabled": s.enabled}


@router.get("/clan/{clan_id}")
async def clan_info(clan_id: str):
    return await get_clan_info(clan_id)


@router.get("/clan/{clan_id}/members")
async def clan_members(clan_id: str):
    return await get_clan_members(clan_id)


@router.get("/character/{name}/profile")
async def character_profile(name: str):
    return await get_character_profile(name)

