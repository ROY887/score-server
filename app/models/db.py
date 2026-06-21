"""SQLAlchemy モデル (scripts/create_tables.sql を Python で表現)。

ForcAD の create_tables.sql をベースに、CTFd AWD プラグイン連携用の
ctfd_team_id / ctfd_challenge_id / ctfd_token カラムを追加している。
"""

from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GameConfig(Base):
    __tablename__ = "game_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    flag_lifetime: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    round_time: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    defense_point: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    volga_attacks_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str] = mapped_column(INET, nullable=False)
    token: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    ctfd_team_id: Mapped[int] = mapped_column(Integer, nullable=False)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    flag_prefix: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    ctfd_challenge_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ctfd_token: Mapped[str] = mapped_column(Text, nullable=False)


class Flag(Base):
    __tablename__ = "flags"
    __table_args__ = (
        UniqueConstraint(
            "round", "team_id", "service_id", name="idx_flags_round_team"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ローテーターの FLAG{...} 形式 (約38文字) を許容できる幅
    flag: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    public_flag_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    private_flag_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class StolenFlag(Base):
    __tablename__ = "stolen_flags"

    flag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("flags.id"), primary_key=True
    )
    attacker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), primary_key=True
    )
    submit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeamService(Base):
    __tablename__ = "team_services"

    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), primary_key=True
    )
    round: Mapped[int] = mapped_column(Integer, primary_key=True)
    stolen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attack_pts: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    defense_pts: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sla_status: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checks_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SLAResultRow(Base):
    __tablename__ = "sla_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
