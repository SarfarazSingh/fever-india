"""Fail a pilot deployment before traffic if auth, storage, or migrations are missing.

Reads backend secrets from the environment; never prints connection strings or tokens.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import text
from app.config import get_settings
from app.database import engine


async def main():
    s = get_settings()
    if not s.production or not s.database_url.startswith("postgresql"):
        raise RuntimeError("Pilot release requires staging/production PostgreSQL")
    if any([s.demo_enabled, s.legacy_api_enabled, s.auto_checkin_enabled,
            s.live_checkout_enabled, s.duffel_cards_approved, s.auth_email_otp_enabled]):
        raise RuntimeError("Unsafe or unapproved pilot feature flags are enabled")
    if s.login_methods != ["google"] or not s.email_allowlist:
        raise RuntimeError("Pilot requires allowlisted Google sign-in")
    if not s.supabase_service_role_key:
        raise RuntimeError("Private document storage requires a backend service key")
    if not s.app_url.startswith("https://") or not s.supabase_url.startswith("https://"):
        raise RuntimeError("Pilot origins must use HTTPS")
    required_prefix = "duffel_live_" if s.environment == "production" else "duffel_test_"
    if not s.duffel_access_token.startswith(required_prefix):
        raise RuntimeError("Duffel token does not match the deployment environment")
    if s.gmail_send_enabled and not (s.google_client_id and s.google_client_secret and s.token_encryption_key):
        raise RuntimeError("Gmail reminders require a configured, separate OAuth connection")
    if s.resend_api_key or s.notification_from or s.forwarding_domain:
        raise RuntimeError("Email services require a separately approved sender")
    async with httpx.AsyncClient(timeout=15) as client:
        result = await client.get(
            s.supabase_url.rstrip("/") + "/auth/v1/settings",
            headers={"apikey": s.supabase_anon_key},
        )
        if result.status_code != 200 or not result.json().get("external", {}).get("google"):
            raise RuntimeError("Supabase Google provider is not ready")
        bucket = await client.get(
            s.supabase_url.rstrip("/") + "/storage/v1/bucket/travel-documents",
            headers={
                "Authorization": "Bearer " + s.supabase_service_role_key,
                "apikey": s.supabase_service_role_key,
            },
        )
        if bucket.status_code != 200 or bucket.json().get("public") is not False:
            raise RuntimeError("Private document bucket is not ready")
    async with engine.connect() as db:
        revision = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        if revision != "0003_gmail_delivery":
            raise RuntimeError("Pilot migrations have not completed")
        missing = (await db.execute(text("""
            SELECT relname FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace
            WHERE n.nspname='public' AND relkind='r'
              AND relname IN ('accounts','login_sessions','oauth_login_attempts','trips','search_sessions')
              AND NOT relrowsecurity
        """))).scalars().all()
        if missing:
            raise RuntimeError("Private table access restrictions are not ready")
        if not (await db.execute(text("SELECT to_regclass('jobs.procrastinate_jobs')"))).scalar():
            raise RuntimeError("Durable worker queue has not been initialized")
    await engine.dispose()
    print("Pilot preflight passed: private Google auth, schema, and durable queue")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (httpx.HTTPError, OSError):
        raise SystemExit("Pilot preflight could not reach a required service")
