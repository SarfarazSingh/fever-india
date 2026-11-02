from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
BOARDING_PASS_DIR = STATIC_DIR / "boarding_passes"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    flight_provider: Literal["auto", "tequila", "amadeus", "mock"] = "auto"
    tequila_api_key: str = ""
    tequila_base_url: str = "https://api.tequila.kiwi.com"
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"
    default_currency: str = "USD"

    flyo_api_key: str = ""
    flyo_base_url: str = "https://api.flyo.ai"
    flyo_webhook_secret: str = ""
    public_base_url: str = "http://localhost:8000"

    checkin_lead_hours: float = 24
    playwright_headless: bool = True
    playwright_timeout_ms: int = 45_000

    database_url: str = "sqlite+aiosqlite:///./concierge.db"
    cors_origins: str = "*"
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value[len("postgresql://") :]
        if value.startswith("sqlite:///"):
            return "sqlite+aiosqlite:///" + value[len("sqlite:///") :]
        return value

    @field_validator("public_base_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def flyo_enabled(self) -> bool:
        return bool(self.flyo_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
