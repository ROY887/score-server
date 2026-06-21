"""Redis キャッシュヘルパー。

フラグ・チームトークン・ゲーム設定を Redis にキャッシュし、
DB アクセスを最小化する (ForcAD の storage 層を参考にした)。
"""

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_redis
from app.models.db import Flag, GameConfig, Team
from app.storage.keys import CacheKeys


# チームトークン ->team_id 
async def cache_team(team: Team) -> None:
    redis = get_redis()
    await redis.set(CacheKeys.team_by_token(team.token), team.id)


async def get_team_id_by_token(token: str) -> int | None:
    redis = get_redis()
    val = await redis.get(CacheKeys.team_by_token(token))
    return int(val) if val is not None else None


# フラグ 
def _serialize_flag(flag: Flag) -> str:
    return json.dumps(
        {
            "id": flag.id,
            "flag": flag.flag,
            "team_id": flag.team_id,
            "service_id": flag.service_id,
            "round": flag.round,
        }
    )


async def cache_flag(flag: Flag, ttl_seconds: int) -> None:
    redis = get_redis()
    payload = _serialize_flag(flag)
    await redis.set(CacheKeys.flag_by_str(flag.flag), payload, ex=ttl_seconds)
    await redis.set(CacheKeys.flag_by_id(flag.id), payload, ex=ttl_seconds)


async def get_flag_by_str(flag_str: str, session: AsyncSession) -> dict | None:
    """まず Redis から、なければ DB から引いてキャッシュ (ForcAD 準拠)。"""
    redis = get_redis()
    raw = await redis.get(CacheKeys.flag_by_str(flag_str))
    if raw is not None:
        return json.loads(raw)

    result = await session.execute(select(Flag).where(Flag.flag == flag_str))
    flag = result.scalar_one_or_none()
    if flag is None:
        return None

    config = await get_game_config(session)
    ttl = config["flag_lifetime"] * config["round_time"] + config["round_time"]
    await cache_flag(flag, ttl_seconds=max(ttl, 1))
    return json.loads(_serialize_flag(flag))


# --- ゲーム設定 ---
async def get_game_config(session: AsyncSession) -> dict:
    redis = get_redis()
    raw = await redis.get("game_config")
    if raw is not None:
        return json.loads(raw)

    result = await session.execute(select(GameConfig).limit(1))
    config = result.scalar_one()
    data = {
        "flag_lifetime": config.flag_lifetime,
        "round_time": config.round_time,
        "defense_point": config.defense_point,
        "volga_attacks_mode": config.volga_attacks_mode,
    }
    await redis.set("game_config", json.dumps(data), ex=30)
    return data
