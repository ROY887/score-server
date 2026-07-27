"""スコアボード(GET /scoreboard)と攻撃ヒント(GET /attack_data)。"""

from collections import defaultdict

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.db import Flag, Service, Team, TeamService
from app.storage.cache import get_team_id_by_token
from app.storage.game import get_current_round

router = APIRouter(tags=["scoreboard"])



@router.get("/scoreboard")
async def scoreboard(session: AsyncSession = Depends(get_session)):
    current_round = await get_current_round()

    teams = (await session.execute(select(Team))).scalars().all()
    services = (await session.execute(select(Service))).scalars().all()
    service_name = {s.id: s.name for s in services}

    # チームとサービスで全ラウンド累計
    rows = (await session.execute(select(TeamService))).scalars().all()
    agg: dict[int, dict[int, dict]] = defaultdict(lambda: defaultdict(dict))
    for ts in rows:
        cur = agg[ts.team_id].setdefault(
            ts.service_id,
            {
                "attack_pts": 0.0,
                "defense_pts": 0.0,
                "stolen": 0,
                "lost": 0,
                "checks": 0,
                "checks_passed": 0,
            },
        )
        cur["attack_pts"] += ts.attack_pts
        cur["defense_pts"] += ts.defense_pts
        cur["stolen"] += ts.stolen
        cur["lost"] += ts.lost
        cur["checks"] += ts.checks
        cur["checks_passed"] += ts.checks_passed

    result_teams = []
    for team in teams:
        svc_scores = {}
        total = 0.0
        for service in services:
            data = agg.get(team.id, {}).get(service.id)
            if data is None:
                continue
            sla_rate = (
                data["checks_passed"] / data["checks"] if data["checks"] else 0.0
            ) 
            svc_scores[service_name[service.id]] = {
                "attack_pts": data["attack_pts"],
                "defense_pts": data["defense_pts"],
                "sla_rate": round(sla_rate, 3),
                "stolen": data["stolen"],
                "lost": data["lost"],
            }
            total += data["attack_pts"] + data["defense_pts"]

        result_teams.append(
            {
                "team_id": team.id,
                "team_name": team.name,
                "services": svc_scores,
                "total": round(total, 2),
            }
        )

    result_teams.sort(key=lambda t: t["total"], reverse=True)
    return {"round": current_round, "teams": result_teams}


@router.get("/attack_data")
async def attack_data(
    x_team_token: str = Header(...),
    session: AsyncSession = Depends(get_session),
):
    
   #pfr フラグの public_flag_data を公開する (ForcAD の get_attack_data() 準拠)。
   # 形式: { "service_name": { "team_ip": ["hint1", ...] } }
   
    team_id = await get_team_id_by_token(x_team_token)
    if not team_id:
        return JSONResponse({"error": "Invalid team token."}, status_code=400)

    current_round = await get_current_round()
    if current_round == -1:
        return JSONResponse({"error": "Game not started."}, status_code=400)

    services = (await session.execute(select(Service))).scalars().all()
    service_name = {s.id: s.name for s in services}
    teams = (await session.execute(select(Team))).scalars().all()
    team_ip = {t.id: str(t.ip) for t in teams}

    # 現ラウンドで有効なフラグの public_flag_data を集計
    flags = (
        await session.execute(
            select(Flag).where(Flag.round == current_round, Flag.public_flag_data != "")
        )
    ).scalars().all()

    out: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for f in flags:
        sname = service_name.get(f.service_id)
        ip = team_ip.get(f.team_id)
        if sname and ip:
            out[sname][ip].append(f.public_flag_data)

    return out
