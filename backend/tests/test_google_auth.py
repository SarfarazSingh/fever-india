import asyncio
import base64
import hashlib
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import utcnow
from app.v1.auth_google import ATTEMPT_COOKIE
from app.v1.models import OAuthLoginAttempt
from app.v1.security import COOKIE, decrypt, digest

ORIGIN = "http://127.0.0.1:5173"
OWNER = "owner@example.com"
OTHER = "reviewer@example.com"


@pytest.fixture
def google(client, monkeypatch):
    settings = get_settings()
    for name, value in {
        "auth_google_enabled": True,
        "auth_email_otp_enabled": False,
        "supabase_url": "https://identity.example.invalid",
        "supabase_anon_key": "public-key",
        "token_encryption_key": Fernet.generate_key().decode(),
        "allowed_emails": f"{OWNER},{OTHER}",
        "app_url": ORIGIN,
    }.items():
        monkeypatch.setattr(settings, name, value)
    c = TestClient(app)
    c.headers["origin"] = ORIGIN
    return c


def identity(email=OWNER, identifier="00000000-0000-4000-8000-000000000001"):
    return {
        "id": identifier, "email": email, "email_confirmed_at": "2026-11-03T00:00:00Z",
        "identities": [{"provider": "google", "identity_data": {
            "email": email, "email_verified": True,
        }}],
    }


def response(value, status=200):
    return httpx.Response(status, json=value, request=httpx.Request("POST", "https://identity.example.invalid"))


def provider(monkeypatch, user=None):
    mock = AsyncMock()
    mock.post.return_value = response({"access_token": "server-only-access", "refresh_token": "server-only-refresh"})
    mock.get.return_value = response(identity() if user is None else user)
    manager = AsyncMock()
    manager.__aenter__.return_value = mock
    monkeypatch.setattr("app.v1.auth_google.httpx.AsyncClient", lambda **kw: manager)
    return mock


def begin(c):
    started = c.post("/api/v1/auth/google/start")
    assert started.status_code == 200, started.text
    return started


def complete(c):
    return c.get("/api/v1/auth/google/callback?code=single-use-code", follow_redirects=False)


def test_configuration_and_disabled_email_flow(google):
    config = google.get("/api/v1/config").json()
    assert config["login_methods"] == ["google"]
    assert config["login_available"] is True
    assert google.post("/api/v1/auth/login", json={"email": OWNER}).status_code == 404
    assert google.post("/api/v1/auth/verify", json={"email": OWNER, "token": "123456"}).status_code == 404


def test_google_start_uses_encrypted_pkce_and_browser_cookie(google):
    started = begin(google)
    query = parse_qs(urlsplit(started.json()["url"]).query)
    assert query["provider"] == ["google"]
    assert query["scopes"] == ["openid email profile"]
    assert query["code_challenge_method"] == ["s256"]
    assert query["redirect_to"] == [ORIGIN + "/api/v1/auth/google/callback"]
    assert "gmail" not in started.text
    cookie = google.cookies.get(ATTEMPT_COOKIE)
    async def read():
        async with SessionLocal() as db:
            return await db.get(OAuthLoginAttempt, digest(cookie))
    row = asyncio.run(read())
    verifier = decrypt(row.verifier_ciphertext)
    assert verifier not in row.verifier_ciphertext
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert query["code_challenge"] == [challenge]
    assert "httponly" in started.headers["set-cookie"].lower()
    assert "samesite=lax" in started.headers["set-cookie"].lower()
    assert started.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("origin", [None, "https://attacker.invalid"])
def test_google_start_rejects_missing_or_foreign_origin(google, origin):
    google.headers.pop("origin")
    headers = {"origin": origin} if origin else {}
    assert google.post("/api/v1/auth/google/start", headers=headers).status_code == 403


def test_google_callback_creates_only_opaque_session(google, monkeypatch):
    mock = provider(monkeypatch)
    begin(google)
    result = complete(google)
    assert result.status_code == 303
    assert result.headers["location"] == ORIGIN + "/search"
    assert "server-only" not in result.text + str(result.headers)
    assert result.headers["referrer-policy"] == "no-referrer"
    assert COOKIE in google.cookies
    session = google.get("/api/v1/auth/session").json()
    assert session["account"]["email"] == OWNER
    assert session["account"]["is_demo"] is False
    assert session["features"]["gmail"] is False
    assert mock.post.call_args.kwargs["json"]["auth_code"] == "single-use-code"
    assert mock.get.call_args.kwargs["headers"]["Authorization"] == "Bearer server-only-access"
    google.headers["x-csrf-token"] = session["csrf_token"]
    assert google.post("/api/v1/auth/logout").status_code == 200
    assert google.get("/api/v1/auth/session").status_code == 401


@pytest.mark.parametrize("email", [OWNER, OTHER])
def test_both_invited_identities_can_sign_in(google, monkeypatch, email):
    identifier = "00000000-0000-4000-8000-000000000001" if email == OWNER else "00000000-0000-4000-8000-000000000002"
    provider(monkeypatch, identity(email, identifier))
    begin(google)
    assert "auth_error" not in complete(google).headers["location"]
    assert google.get("/api/v1/auth/session").json()["account"]["email"] == email


@pytest.mark.parametrize("change", ["email", "provider", "unverified", "unconfirmed"])
def test_uninvited_or_unverified_identity_is_rejected(google, monkeypatch, change):
    user = identity()
    if change == "email":
        user = identity("stranger@example.invalid")
    elif change == "provider":
        user["identities"][0]["provider"] = "email"
    elif change == "unverified":
        user["identities"][0]["identity_data"]["email_verified"] = False
    else:
        user["email_confirmed_at"] = None
    provider(monkeypatch, user)
    begin(google)
    assert complete(google).headers["location"].endswith("auth_error=not_invited")
    assert google.get("/api/v1/auth/session").status_code == 401


def test_callback_without_originating_browser_is_rejected(google, monkeypatch):
    mock = provider(monkeypatch)
    begin(google)
    outsider = TestClient(app)
    assert complete(outsider).headers["location"].endswith("auth_error=expired")
    mock.post.assert_not_called()


def test_expired_and_replayed_callback_are_rejected(google, monkeypatch):
    mock = provider(monkeypatch)
    begin(google)
    cookie = google.cookies.get(ATTEMPT_COOKIE)
    async def expire():
        async with SessionLocal() as db:
            row = await db.get(OAuthLoginAttempt, digest(cookie))
            row.expires_at = utcnow() - timedelta(seconds=1)
            await db.commit()
    asyncio.run(expire())
    assert complete(google).headers["location"].endswith("auth_error=expired")
    mock.post.assert_not_called()
    begin(google)
    cookie = google.cookies.get(ATTEMPT_COOKIE)
    assert complete(google).headers["location"] == ORIGIN + "/search"
    replay = google.get("/api/v1/auth/google/callback?code=single-use-code", headers={"cookie": f"{ATTEMPT_COOKIE}={cookie}"}, follow_redirects=False)
    assert replay.headers["location"].endswith("auth_error=expired")
    assert mock.post.call_count == 1


def test_cancelled_login_and_provider_failure_are_safe(google, monkeypatch):
    mock = provider(monkeypatch)
    begin(google)
    result = google.get("/api/v1/auth/google/callback?error=access_denied&error_description=secret", follow_redirects=False)
    assert result.headers["location"].endswith("auth_error=cancelled")
    assert "secret" not in result.text + str(result.headers)
    mock.post.assert_not_called()
    begin(google)
    cookie = google.cookies.get(ATTEMPT_COOKIE)
    mock.post.side_effect = httpx.ReadTimeout("secret authorization code")
    assert complete(google).headers["location"].endswith("auth_error=failed")
    replay = google.get("/api/v1/auth/google/callback?code=single-use-code", headers={"cookie": f"{ATTEMPT_COOKIE}={cookie}"}, follow_redirects=False)
    assert replay.headers["location"].endswith("auth_error=expired")
    assert mock.post.call_count == 1


def test_invited_accounts_keep_trips_isolated(google, monkeypatch):
    provider(monkeypatch)
    begin(google)
    complete(google)
    account = google.get("/api/v1/auth/session").json()["account"]
    from app.v1.models import Account, Trip
    from app.v1.trips import seed_demo
    async def seed():
        async with SessionLocal() as db:
            await seed_demo(db, await db.get(Account, account["id"]))
            return (await db.execute(select(Trip.id).where(Trip.account_id == account["id"]))).scalars().first()
    trip_id = asyncio.run(seed())
    provider(monkeypatch, identity(OTHER, "00000000-0000-4000-8000-000000000002"))
    second = TestClient(app)
    second.headers["origin"] = ORIGIN
    begin(second)
    complete(second)
    assert second.get(f"/api/v1/trips/{trip_id}").status_code == 404
