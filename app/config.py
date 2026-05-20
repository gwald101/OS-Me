from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/osme"
    DEXCOM_USERNAME: str = ""
    DEXCOM_PASSWORD: str = ""
    DEXCOM_OUTSIDE_US: bool = False
    POLL_INTERVAL_MINUTES: int = 5
    LOG_LEVEL: str = "INFO"
    DEFAULT_LOW_THRESHOLD: int = 70
    DEFAULT_HIGH_THRESHOLD: int = 180
    STALE_READING_ALERT_MINUTES: int = 15

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_async_scheme(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
