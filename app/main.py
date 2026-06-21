"""FastAPI エントリーポイント。"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.api import flags, health, scoreboard, sla
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.db import Team
from app.services.ingest import poll_loop
from app.storage.cache import cache_team
from app.storage.rotator_db import ensure_table

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時にチームトークンをRedisにウォームアップ
    async with AsyncSessionLocal() as session:
        teams = (await session.execute(select(Team))).scalars().all()
        for team in teams:
            await cache_team(team)

    # ローテーター MySQL の flags テーブルを用意 (未作成でも空振り待機できる)
    try:
        await ensure_table()
    except Exception:
        pass  # MySQL 起動直後で接続できない場合はポーラー側で再試行する

    # ローテーターMySQLを監視するポーラーをバックグラウンド起動
    poller = asyncio.create_task(poll_loop())
    try:
        yield
    finally:
        poller.cancel()


app = FastAPI(title="Score Server", version="1.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(flags.router)
app.include_router(sla.router)
app.include_router(scoreboard.router)
