"""ヘルスチェックForcADを参考にした"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_redis, get_session

router = APIRouter(tags=["health"])

#DBの稼働確認
@router.get("/health/")
async def health(session: AsyncSession = Depends(get_session)):
    db_ok = True
    redis_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    try:
        await get_redis().ping()
    except Exception:
        redis_ok = False

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}
