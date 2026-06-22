from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# フラグローテーターの MySQL (ctf_flags) を参照するエンジン。
# aiomysql は pool_pre_ping と相性が悪い (ping() のシグネチャ差異) ため無効化する。
rotator_engine = create_async_engine(settings.ROTATOR_DATABASE_URL, echo=False)

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL, encoding="utf-8", decode_responses=True
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session: 
        yield session


def get_redis() -> aioredis.Redis:
    return redis_client

