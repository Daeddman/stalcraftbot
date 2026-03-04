"""API роутер: выброс, кланы, персонажи."""
from fastapi import APIRouter
from api.emission import get_emission
from api.characters import get_clan_info, get_clan_members, get_character_profile

router = APIRouter(tags=["game"])


@router.get("/emission")
async def emission():
    return await get_emission()


@router.get("/clan/{clan_id}")
async def clan_info(clan_id: str):
    return await get_clan_info(clan_id)


@router.get("/clan/{clan_id}/members")
async def clan_members(clan_id: str):
    return await get_clan_members(clan_id)


@router.get("/character/{name}/profile")
async def character_profile(name: str):
    return await get_character_profile(name)

