"""フラグローテーターの MySQL (ctf_flags) を読み取るヘルパー。

ローテーターは `flags(id, round, team, service, flag, created_at)` テーブルに
直接書き込む。score-server はここをポーリングして新ラウンドを取り込む。
ローテーター側は一切変更しない (読み取り専用)。
"""

from sqlalchemy import text

from app.core.database import rotator_engine

# ローテーター (engineering-design-5th-grade/db.py) と同一スキーマ。
# ローテーター起動前でもポーリングが空振りできるよう、起動時に用意しておく。
_CREATE_FLAGS_TABLE = """
CREATE TABLE IF NOT EXISTS flags (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    round       INT UNSIGNED    NOT NULL,
    team        VARCHAR(64)     NOT NULL,
    service     VARCHAR(64)     NOT NULL,
    flag        VARCHAR(128)    NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_round_team_service (round, team, service)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


async def ensure_table() -> None:
    """flags テーブルが無ければ作成する (ローテーターと同一スキーマ)。"""
    async with rotator_engine.begin() as conn:
        await conn.execute(text(_CREATE_FLAGS_TABLE))


async def get_latest_round() -> int:
    """ローテーター側の最新ラウンド番号。フラグ未投入なら 0。"""
    async with rotator_engine.connect() as conn:
        res = await conn.execute(
            text("SELECT COALESCE(MAX(round), 0) AS r FROM flags")
        )
        return int(res.scalar_one())


async def get_flags_for_round(round_num: int) -> list[dict]:
    """指定ラウンドのフラグ一覧を取得する。"""
    async with rotator_engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT team, service, flag FROM flags WHERE round = :r"
            ),
            {"r": round_num},
        )
        return [
            {"team": row.team, "service": row.service, "flag": row.flag}
            for row in res
        ]
