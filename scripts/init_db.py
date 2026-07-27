"""初期データ投入 (ForcAD の init_db.py 参考)。

create_tables.sql / create_functions.sql を流し込み、
scripts/seed.py の定義に従ってゲーム設定・チーム・サービスを登録する。

冪等: 既存の name と一致する行は更新、無ければ追加する。
実構成を変えるときは scripts/seed.py を編集して再実行するだけでよい。

実行: python -m scripts.init_db
"""

import asyncio
import secrets
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.db import GameConfig, Service, Team
from app.storage.cache import cache_team
from app.storage.game import get_current_round, set_current_round
from scripts import seed

SCRIPTS_DIR = Path(__file__).parent


async def run_sql_file(conn, filename: str) -> None:
    sql = (SCRIPTS_DIR / filename).read_text()
    # asyncpg は prepared statement に複数文を含められないため、
    # simple query protocol を使う生コネクションのexecute()で流し込む。
    raw = await conn.get_raw_connection()
    await raw.driver_connection.execute(sql)



async def upsert_game_config(session) -> None:
    cfg = (await session.execute(select(GameConfig).limit(1))).scalar_one_or_none()
    if cfg is None:
        session.add(GameConfig(**seed.GAME))
    else:
        for k, v in seed.GAME.items():
            setattr(cfg, k, v)


async def upsert_services(session) -> None:
    for s in seed.SERVICES:
        existing = (
            await session.execute(select(Service).where(Service.name == s["name"]))
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                Service(
                    name=s["name"],
                    flag_prefix=s.get("flag_prefix", "F"),
                    ctfd_challenge_id=s["ctfd_challenge_id"],
                    ctfd_token=s["ctfd_token"],
                )
            )
        else:
            existing.ctfd_challenge_id = s["ctfd_challenge_id"]
            existing.ctfd_token = s["ctfd_token"]
            existing.flag_prefix = s.get("flag_prefix", existing.flag_prefix)


async def upsert_teams(session) -> list[Team]:
    teams: list[Team] = []
    for t in seed.TEAMS:
        existing = (
            await session.execute(select(Team).where(Team.name == t["name"]))
        ).scalar_one_or_none()
        if existing is None:
            team = Team(
                name=t["name"],
                ip=t["ip"],
                token=t.get("token") or secrets.token_hex(8),
                ctfd_team_id=t["ctfd_team_id"],
            )
            session.add(team)
            teams.append(team)
        else:
            existing.ip = t["ip"]
            existing.ctfd_team_id = t["ctfd_team_id"]
            if t.get("token"):
                existing.token = t["token"]
            teams.append(existing)
    return teams


async def main() -> None:
    # スキーマ + ストアド関数
    async with engine.begin() as conn:
        await run_sql_file(conn, "create_tables.sql")
        await run_sql_file(conn, "create_functions.sql")

    async with AsyncSessionLocal() as session:
        await upsert_game_config(session)
        await upsert_services(session)
        teams = await upsert_teams(session)
        await session.commit()

        for team in teams:
            await session.refresh(team)
            await cache_team(team)
            print(f"Team {team.name}: token={team.token} ctfd_team_id={team.ctfd_team_id}")

    # 既にゲームが進行中なら current_round は維持し、未設定時のみ -1 (未開始)
    if await get_current_round() == -1:
        await set_current_round(-1)

    print("init_db done.")


if __name__ == "__main__":
    asyncio.run(main())
