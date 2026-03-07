"""API роутер: выброс, кланы, персонажи, лидерборд."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from api.emission import get_emission
from api.characters import get_clan_info, get_clan_members, get_character_profile, get_clans_list
from db.models import SessionLocal, EmissionNotifySetting, User, MarketListing, ReputationReview, UserFollow
from web.auth import get_current_user, require_user
from sqlalchemy import func
from services.cache import compute_cache

router = APIRouter(tags=["game"])


@router.get("/emission")
async def emission():
    return await get_emission()


@router.get("/emission/debug")
async def emission_debug():
    """Диагностика emission checker."""
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
    if not user:
        return {"enabled": False, "authenticated": False}
    with SessionLocal() as session:
        s = session.query(EmissionNotifySetting).filter_by(telegram_id=user.telegram_id).first()
        return {"enabled": s.enabled if s else False, "authenticated": True}


@router.post("/emission/settings")
async def toggle_emission(user: User = Depends(require_user)):
    with SessionLocal() as session:
        s = session.query(EmissionNotifySetting).filter_by(telegram_id=user.telegram_id).first()
        if s:
            s.enabled = not s.enabled
        else:
            s = EmissionNotifySetting(telegram_id=user.telegram_id, enabled=True)
            session.add(s)
        session.commit()
        return {"enabled": s.enabled}


# ═══════════════════════════════════════════════
#  Кланы
# ═══════════════════════════════════════════════

@router.get("/clans")
async def clans_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Список всех кланов региона."""
    return await get_clans_list(offset=offset, limit=limit)


@router.get("/clan/{clan_id}")
async def clan_info(clan_id: str):
    return await get_clan_info(clan_id)


@router.get("/clan/{clan_id}/members")
async def clan_members(clan_id: str):
    return await get_clan_members(clan_id)


@router.get("/character/{name}/profile")
async def character_profile(name: str):
    return await get_character_profile(name)


# ═══════════════════════════════════════════════
#  Лидерборд трейдеров
# ═══════════════════════════════════════════════

CLAN_RANKS = {
    "RECRUIT": "Рекрут",
    "PLAYER": "Игрок",
    "OFFICER": "Офицер",
    "LEADER": "Лидер",
}

@router.get("/leaderboard")
async def leaderboard(
    sort: str = Query("deals", description="deals|reputation|volume"),
    period: str = Query("all", description="week|month|all"),
):
    """Лидерборд трейдеров по сделкам/репутации/объёму."""
    cache_key = f"leaderboard:{sort}:{period}"
    cached = compute_cache.get(cache_key)
    if cached is not None:
        return cached

    with SessionLocal() as session:
        # Определяем период
        cutoff = None
        if period == "week":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        elif period == "month":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        # Получаем всех пользователей
        users = session.query(User).all()
        user_map = {u.id: u for u in users}
        user_ids = list(user_map.keys())

        if not user_ids:
            return {"items": [], "total": 0}

        # Считаем сделки (sold listings)
        deals_q = session.query(
            MarketListing.user_id,
            func.count(MarketListing.id).label("cnt"),
            func.coalesce(func.sum(MarketListing.sold_price), func.sum(MarketListing.price)).label("vol"),
        ).filter(
            MarketListing.user_id.in_(user_ids),
            MarketListing.status == "sold",
        )
        if cutoff:
            deals_q = deals_q.filter(MarketListing.updated_at >= cutoff)
        deals_q = deals_q.group_by(MarketListing.user_id)
        deals_rows = {uid: (cnt, vol or 0) for uid, cnt, vol in deals_q.all()}

        # Считаем отзывы
        reviews_q = session.query(
            ReputationReview.target_id,
            func.count(ReputationReview.id).label("cnt"),
            func.sum(ReputationReview.score).label("total_score"),
        ).filter(ReputationReview.target_id.in_(user_ids))
        if cutoff:
            reviews_q = reviews_q.filter(ReputationReview.created_at >= cutoff)
        reviews_q = reviews_q.group_by(ReputationReview.target_id)
        reviews_map = {uid: (cnt, ts or 0) for uid, cnt, ts in reviews_q.all()}

        # Считаем подписчиков
        followers_q = session.query(
            UserFollow.target_id,
            func.count(UserFollow.id).label("cnt"),
        ).filter(UserFollow.target_id.in_(user_ids)).group_by(UserFollow.target_id)
        followers_map = {uid: cnt for uid, cnt in followers_q.all()}

        # Собираем результат
        items = []
        for uid, u in user_map.items():
            deals_cnt, deals_vol = deals_rows.get(uid, (0, 0))
            reviews_cnt, reviews_score = reviews_map.get(uid, (0, 0))
            followers_cnt = followers_map.get(uid, 0)

            # Пропускаем неактивных
            if deals_cnt == 0 and (u.reputation or 0) == 0 and reviews_cnt == 0:
                continue

            items.append({
                "id": u.id,
                "display_name": u.display_name,
                "avatar_url": u.avatar_url,
                "game_nickname": u.game_nickname,
                "reputation": u.reputation or 0,
                "deals_count": deals_cnt,
                "deals_volume": int(deals_vol),
                "reviews_count": reviews_cnt,
                "followers_count": followers_cnt,
            })

        # Сортировка
        if sort == "reputation":
            items.sort(key=lambda x: x["reputation"], reverse=True)
        elif sort == "volume":
            items.sort(key=lambda x: x["deals_volume"], reverse=True)
        else:
            items.sort(key=lambda x: x["deals_count"], reverse=True)

        # Присваиваем позиции
        for i, item in enumerate(items):
            item["rank"] = i + 1

        result = {"items": items[:100], "total": len(items)}
        compute_cache.set(cache_key, result, ttl=120)
        return result
