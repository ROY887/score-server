"""Pydantic スキーマ (リクエスト / レスポンス)。"""

from pydantic import BaseModel


# --- フラグ提出 ---
class FlagSubmitResult(BaseModel):
    flag: str
    msg: str


# --- SLA 受け取り ---
class SLAResult(BaseModel):
    team_id: int
    service_id: int
    round: int
    status: int  # TaskStatus (101=OK, 102=CORRUPT, 103=MUMBLE, 104=DOWN, 110=ERROR)


# --- スコアボード ---
class ServiceScore(BaseModel):
    attack_pts: float
    defense_pts: float
    sla_rate: float
    stolen: int
    lost: int


class TeamScore(BaseModel):
    team_id: int
    team_name: str
    services: dict[str, ServiceScore]
    total: float


class Scoreboard(BaseModel):
    round: int
    teams: list[TeamScore]


# --- 内部ロジック用 ---
class AttackResult(BaseModel):
    attacker_id: int
    submit_ok: bool = False
    message: str = ""
    attack_delta: float = 0.0
