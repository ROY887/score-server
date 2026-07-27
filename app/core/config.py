from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://score:score@db:5432/score"
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # フラグローテーターが書き込む MySQL (ctf_flags)。score-server はここを
    # ポーリングして新ラウンドのフラグを取り込む。
    ROTATOR_DATABASE_URL: str = "mysql+aiomysql://rotator:Rotator1!@flagdb:3306/ctf_flags"
    INGEST_POLL_SECONDS: int = 5

    # CTFd AWD plugin
    CTFD_URL: str = "http://ctfd:8000"

    # ログレベル (debug / info / warning / error)
    LOG_LEVEL: str = "info"

    # フラグ受付上限
    MAX_FLAGS_PER_REQUEST: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
