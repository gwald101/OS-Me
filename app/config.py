from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/osme"
    DEXCOM_USERNAME: str = ""
    DEXCOM_PASSWORD: str = ""
    DEXCOM_OUTSIDE_US: bool = False
    POLL_INTERVAL_MINUTES: int = 5
    TANDEM_EMAIL: str = ""
    TANDEM_PASSWORD: str = ""
    TANDEM_POLL_INTERVAL_MINUTES: int = 15
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

    @model_validator(mode="after")
    def require_dexcom_credentials(self) -> "Settings":
        if not self.DEXCOM_USERNAME or not self.DEXCOM_PASSWORD:
            raise ValueError(
                "DEXCOM_USERNAME and DEXCOM_PASSWORD must be set "
                "(check your environment variables or .env file)"
            )
        return self

    @model_validator(mode="after")
    def tandem_credentials_coupled(self) -> "Settings":
        # Tandem is optional, but email/password must come together.
        if bool(self.TANDEM_EMAIL) != bool(self.TANDEM_PASSWORD):
            raise ValueError(
                "TANDEM_EMAIL and TANDEM_PASSWORD must either both be set or both be empty"
            )
        return self

    @property
    def tandem_enabled(self) -> bool:
        return bool(self.TANDEM_EMAIL) and bool(self.TANDEM_PASSWORD)


settings = Settings()
