"""ローテーター MySQL からのフラグ取り込み (ポーリング)。

設計の `PUT /flags/rotate` HTTP 受信に代わり、ローテーターが MySQL に
直接書き込んだフラグをポーリングして PostgreSQL に取り込む。

ラウンドごとに:
  1. ローテーターの flags 行を読む
  2. team / service 名を score-server の内部 ID に解決 (対応表)
  3. flags / team_services に INSERT し、Redis にキャッシュ
  4. 直前ラウンドの集計を CTFd へ反映し、current_round を進める
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.db import Flag, Service, Team, TeamService
from app.services.ctfd import push_to_ctfd
from app.storage.cache import cache_flag, get_game_config
from app.storage.game import get_current_round, set_current_round
from app.storage.rotator_db import (
    ensure_table,
    get_flags_for_round,
    get_latest_round,
)

logger = logging.getLogger("ingest")


async def _name_maps(session: AsyncSession) -> tuple[dict[str, int], dict[str, int]]:
    """team名/service名 → 内部ID の対応表を作る。"""
    teams = (await session.execute(select(Team))).scalars().all()
    services = (await session.execute(select(Service))).scalars().all()
    return (
        {t.name: t.id for t in teams},
        {s.name: s.id for s in services},
    )


async def ingest_round(round_num: int, session: AsyncSession) -> int:
    """ローテーターの指定ラウンドを取り込む。取り込んだフラグ件数を返す。"""
    rows = await get_flags_for_round(round_num)
    if not rows:
        return 0

    team_id_of, service_id_of = await _name_maps(session)
    config = await get_game_config(session)
    ttl = (config["flag_lifetime"] + 1) * config["round_time"]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

    inserted: list[Flag] = []
    for r in rows:
        team_id = team_id_of.get(r["team"])
        service_id = service_id_of.get(r["service"])
        if team_id is None or service_id is None:
            logger.warning(
                "未知の team/service をスキップ: team=%s service=%s",
                r["team"],
                r["service"],
            )
            continue

        stmt = (
            pg_insert(Flag)
            .values(
                flag=r["flag"],
                team_id=team_id,
                service_id=service_id,
                round=round_num,
                expires_at=expires_at,
            )
            .on_conflict_do_nothing(index_elements=["flag"])
            .returning(Flag.id)
        )
        new_id = (await session.execute(stmt)).scalar_one_or_none()

        # 集計の受け皿となる team_services 行を用意
        await session.execute(
            pg_insert(TeamService)
            .values(service_id=service_id, team_id=team_id, round=round_num)
            .on_conflict_do_nothing(
                index_elements=["team_id", "service_id", "round"]
            )
        )

        if new_id is not None:
            obj = await session.get(Flag, new_id)
            if obj is not None:
                inserted.append(obj)

    await session.commit()

    for obj in inserted:
        await cache_flag(obj, ttl_seconds=ttl)

    return len(inserted)


async def ingest_new_rounds(session: AsyncSession) -> None:
    """current_round より先のラウンドをまとめて取り込む。"""
    latest = await get_latest_round()
    current = await get_current_round()
    start = max(current, 0) + 1

    for round_num in range(start, latest + 1):
        count = await ingest_round(round_num, session)
        logger.info("round %s 取り込み完了 (%s flags)", round_num, count)

        # 直前ラウンドの集計を CTFd へ反映してからラウンドを進める
        prev_round = round_num - 1
        if prev_round >= 1:
            await push_to_ctfd(prev_round, session)

        await set_current_round(round_num)


async def poll_loop() -> None:
    """バックグラウンドでローテーター DB を定期ポーリングする。"""
    logger.info("flag ingest poller 起動 (interval=%ss)", settings.INGEST_POLL_SECONDS)
    while True:
        try:
            await ensure_table()
            async with AsyncSessionLocal() as session:
                await ingest_new_rounds(session)
        except Exception:
            logger.exception("ingest 中にエラー")
        await asyncio.sleep(settings.INGEST_POLL_SECONDS)
