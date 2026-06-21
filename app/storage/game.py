"""ラウンド管理。

現在ラウンドは Redis の "real_round" キーで管理する (ForcAD 準拠)。
フラグローテーション受け取り時に更新される。
"""

from app.core.database import get_redis
from app.storage.keys import CacheKeys


async def get_current_round() -> int:
    redis = get_redis()
    val = await redis.get(CacheKeys.current_round())
    return int(val) if val is not None else -1


async def set_current_round(round_num: int) -> None:
    redis = get_redis()
    await redis.set(CacheKeys.current_round(), round_num)
