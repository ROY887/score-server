"""フラグ提出 (PUT /flags/)。

フラグの取り込みは HTTP ではなく、ローテーター MySQL のポーリングで行う
(app/services/ingest.py)。本ルーターは参加チームからの提出のみを扱う。
"""

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.services.attacks import handle_attack
from app.storage.cache import get_team_id_by_token
from app.storage.game import get_current_round

router = APIRouter(tags=["flags"])


@router.put("/flags/")
async def submit_flags(
    flags: list[str],
    x_team_token: str = Header(...),
    session: AsyncSession = Depends(get_session),
):
    #  トークンでteam_id 解決
    team_id = await get_team_id_by_token(x_team_token)
    if not team_id:
        return JSONResponse({"error": "Invalid team token."}, status_code=400)

    #  リスト上限チェック
    if len(flags) > settings.MAX_FLAGS_PER_REQUEST:
        return JSONResponse(
            {
                "error": "Must provide a list with no more than "
                f"{settings.MAX_FLAGS_PER_REQUEST} flags."
            },
            status_code=400,
        )

    current_round = await get_current_round()
    if current_round == -1:
        return JSONResponse({"error": "Game not started."}, status_code=400)

    results = []
    for flag_str in flags:
        ar = await handle_attack(team_id, flag_str, current_round, session)
        results.append({"flag": flag_str, "msg": f"[{flag_str}] {ar.message}"})

    return results
