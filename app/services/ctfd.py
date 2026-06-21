"""CTFd AWD プラグインへのスコア書き込み。

CTFd の plugins/awd/__init__.py awd_update() が受け付けるフォーマットに合わせ、
/plugins/awd/api/update に POST する。
"""

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import Service, Team, TeamService
from app.models.types import TaskStatus

logger = logging.getLogger("ctfd")


async def push_to_ctfd(round_num: int, session: AsyncSession) -> None:
    """ラウンド集計を CTFd AWD プラグインへ反映する (ベストエフォート)。

    CTFd 連携は下流処理なので、ここでの失敗 (接続不可・トークン不一致など) が
    フラグ取り込み・スコア計算を止めてはならない。例外は握りつぶしてログに残す。
    """
    services = (await session.execute(select(Service))).scalars().all()

    # team_id → ctfd_team_id の対応表を一括取得
    teams = (await session.execute(select(Team))).scalars().all()
    ctfd_team_of = {t.id: t.ctfd_team_id for t in teams}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service in services:
                results = (
                    await session.execute(
                        select(TeamService).where(
                            TeamService.service_id == service.id,
                            TeamService.round == round_num,
                        )
                    )
                ).scalars().all()

                attacks: dict[str, int] = {}
                defenses: list[int] = []

                for ts in results:
                    ctfd_team_id = ctfd_team_of.get(ts.team_id)
                    if ctfd_team_id is None:
                        continue

                    if ts.attack_pts > 0:
                        attacks[str(ctfd_team_id)] = int(ts.attack_pts)

                    # SLA が UP のチームを防御成功とみなす
                    if ts.sla_status == TaskStatus.UP:
                        defenses.append(ctfd_team_id)

                resp = await client.post(
                    f"{settings.CTFD_URL}/plugins/awd/api/update",
                    json={
                        "id": service.ctfd_challenge_id,
                        "token": service.ctfd_token,
                        "attacks": attacks,
                        "defenses": defenses,
                    },
                )
                logger.info(
                    "CTFd push round=%s service=%s -> %s %s",
                    round_num,
                    service.name,
                    resp.status_code,
                    resp.text[:200],
                )
    except Exception:
        logger.warning(
            "CTFd への push に失敗 (round=%s)。取り込みは継続する。",
            round_num,
            exc_info=True,
        )
