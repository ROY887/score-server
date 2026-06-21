"""SLA 結果受け取り (POST /sla) — SLA チェッカー (別チーム) からの呼び出し。"""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.db import SLAResultRow, TeamService
from app.models.schemas import SLAResult
from app.models.types import TaskStatus
from app.services.scoring import recalculate_defense

router = APIRouter(tags=["sla"])


@router.post("/sla")
async def receive_sla(
    body: SLAResult,
    x_internal_key: str = Header(...),
    session: AsyncSession = Depends(get_session),
):
    if x_internal_key != settings.INTERNAL_KEY:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    # sla_results に記録
    await session.execute(insert(SLAResultRow).values(**body.model_dump()))

    # team_services 行を保証してから checks / checks_passed を更新
    await session.execute(
        pg_insert(TeamService)
        .values(
            service_id=body.service_id,
            team_id=body.team_id,
            round=body.round,
        )
        .on_conflict_do_nothing(index_elements=["team_id", "service_id", "round"])
    )

    is_up = body.status == TaskStatus.UP
    await session.execute(
        update(TeamService)
        .where(
            TeamService.team_id == body.team_id,
            TeamService.service_id == body.service_id,
            TeamService.round == body.round,
        )
        .values(
            sla_status=body.status,
            checks=TeamService.checks + 1,
            checks_passed=TeamService.checks_passed + (1 if is_up else 0),
        )
    )
    await session.commit()

    # 防御ポイントを再計算
    await recalculate_defense(body.round, session)

    return {"ok": True}
