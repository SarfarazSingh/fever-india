import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
# Packaged assets (web UI) always come from the repo. Writable output goes to
# /tmp on Vercel, where the function filesystem is otherwise read-only.
ASSET_DIR = BASE_DIR / "static"
STATIC_DIR = Path("/tmp/concierge-static") if os.environ.get("VERCEL") else ASSET_DIR
BOARDING_PASS_DIR = STATIC_DIR / "boarding_passes"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    flight_provider: Literal["auto", "duffel", "tequila", "amadeus", "mock"] = "duffel"
    duffel_access_token: str = ""
    duffel_base_url: str = "https://api.duffel.com"
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
    serpapi_api_key: str = ""

    checkin_lead_hours: float = 24
    playwright_headless: bool = True
    playwright_timeout_ms: int = 45_000

    database_url: str = "sqlite+aiosqlite:///./concierge.db"
    cors_origins: str = "*"
    log_level: str = "INFO"
    environment: Literal["development", "test", "staging", "production"] = "development"
    demo_enabled: bool = True
    live_checkout_enabled: bool = False
    duffel_cards_approved: bool = False
    duffel_card_airlines: str = ""
    legacy_api_enabled: bool = False
    auto_checkin_enabled: bool = False
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    auth_google_enabled: bool = False
    auth_email_otp_enabled: bool = False
    allowed_emails: str = ""
    app_url: str = "http://127.0.0.1:5173"
    token_encryption_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    gmail_send_enabled: bool = False
    gmail_redirect_uri: str = "http://localhost:8000/api/v1/connections/gmail/callback"
    resend_api_key: str = ""
    resend_webhook_secret: str = ""
    forwarding_domain: str = ""
    notification_from: str = ""
    google_places_api_key: str = ""
    sentry_dsn: str = ""
    search_daily_limit: int = 100
    places_daily_limit: int = 30
    session_days: int = 7
    worker_concurrency: int = Field(default=1, ge=1, le=4)

    @property
    def production(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def login_methods(self) -> list[str]:
        if not self.supabase_url or not self.supabase_anon_key:
            return []
        methods = []
        if self.auth_google_enabled and self.token_encryption_key:
            methods.append("google")
        if self.auth_email_otp_enabled:
            methods.append("email_otp")
        return methods

    @property
    def email_allowlist(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.allowed_emails.split(",")
            if email.strip()
        }

    @property
    def psycopg_dsn(self) -> str:
        url = urlsplit(
            self.database_url.replace("postgresql+asyncpg://", "postgresql://")
        )
        query = dict(parse_qsl(url.query))
        if "ssl" in query:
            query["sslmode"] = query.pop("ssl")
        if self.production:
            query.setdefault("sslmode", "require")
        return urlunsplit(url._replace(query=urlencode(query)))

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value[len("postgres://") :]
        if value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]
        if value.startswith("postgresql+asyncpg://"):
            url = urlsplit(value)
            query = dict(parse_qsl(url.query))
            if "sslmode" in query:
                query["ssl"] = query.pop("sslmode")
            return urlunsplit(url._replace(query=urlencode(query)))
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

    @property
    def duffel_enabled(self) -> bool:
        return bool(self.duffel_access_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
