"""フラグ提出処理 (ForcAD の lib/storage/attacks.py handle_attack() を移植)。

判定順序は ForcAD をそのまま踏襲:
  1. フラグ取得 (Redis 優先)  → なければ Invalid
  2. 自チームフラグ  → 拒否
  3. 有効期限 (round_diff > lifetime) → 拒否
  4. volga_attacks_mode (自サービス DOWN なら拒否)
  5. ストアド関数で原子的にスコア更新 (二重提出は DB PK で防止)
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import AttackResult
from app.models.types import TaskStatus
from app.storage.cache import get_flag_by_str, get_game_config


async def _get_latest_sla_status(
    session: AsyncSession, team_id: int, service_id: int
) -> int | None:
    row = await session.execute(
        text(
            "SELECT sla_status FROM team_services "
            "WHERE team_id = :t AND service_id = :s "
            "ORDER BY round DESC LIMIT 1"
        ),
        {"t": team_id, "s": service_id},
    )
    res = row.first()
    return res[0] if res else None


async def handle_attack(
    attacker_id: int,
    flag_str: str,
    current_round: int,
    session: AsyncSession,
) -> AttackResult:
    result = AttackResult(attacker_id=attacker_id)

    # 1. フラグ取得 (Redis → DB)
    flag = await get_flag_by_str(flag_str, session)
    if flag is None:
        result.message = "Invalid flag"
        return result

    # 2. 自チームフラグチェック
    if flag["team_id"] == attacker_id:
        result.message = "This flag is your own"
        return result

    # 3. 有効期限チェック
    config = await get_game_config(session)
    if current_round - flag["round"] > config["flag_lifetime"]:
        result.message = "Flag is too old"
        return result

    # 4. volga_attacks_mode チェック
    if config["volga_attacks_mode"]:
        status = await _get_latest_sla_status(
            session, attacker_id, flag["service_id"]
        )
        if status != TaskStatus.UP:
            result.message = "Your service is down"
            return result

    # 5. ストアド関数でアトミックにスコア更新
    row = await session.execute(
        text("SELECT * FROM handle_flag_stolen(:attacker, :flag_id, :round)"),
        {"attacker": attacker_id, "flag_id": flag["id"], "round": current_round},
    )
    res = row.first()
    await session.commit()

    if not res.success:
        result.message = res.message  # "Flag already stolen"
        return result

    result.submit_ok = True
    result.message = res.message
    result.attack_delta = res.attack_delta
    return result
