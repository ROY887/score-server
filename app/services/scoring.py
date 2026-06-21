"""防御ポイント計算・ラウンド集計。

SLA 結果受け取り時に、対象ラウンドの防御ポイントを再計算する。
防御成功 (SLA が UP かつ そのラウンドでフラグを奪われていない) チームに
defense_point を付与する。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import TeamService
from app.models.types import TaskStatus
from app.storage.cache import get_game_config


async def recalculate_defense(round_num: int, session: AsyncSession) -> None:
    config = await get_game_config(session)
    defense_point = float(config["defense_point"])

    rows = (
        await session.execute(
            select(TeamService).where(TeamService.round == round_num)
        )
    ).scalars().all()

    for ts in rows:
        # SLA が UP かつ そのラウンドで奪われていない → 防御成功
        if ts.sla_status == TaskStatus.UP and ts.lost == 0:
            ts.defense_pts = defense_point
        else:
            ts.defense_pts = 0.0

    await session.commit()


