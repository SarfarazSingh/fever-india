"""Supabase Google PKCE flow; only opaque application sessions reach the browser."""

import base64
import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import get_settings
from app.database import get_session
from app.models import utcnow
from app.v1.models import Account, OAuthLoginAttempt
from app.v1.schemas import Model, Profile
from app.v1.security import consume_usage, decrypt, digest, encrypt, start_session

router = APIRouter(prefix="/api/v1/auth/google", tags=["authentication"])
logger = logging.getLogger(__name__)
ATTEMPT_COOKIE = "concierge_google_attempt"
CALLBACK_PATH = "/api/v1/auth/google/callback"


class GoogleStart(Model):
    url: str


def require_google():
    settings = get_settings()
    if "google" not in settings.login_methods:
        raise HTTPException(503, "Private Google sign-in is not configured yet")
    return settings


def callback_response(error: str | None = None):
    settings = get_settings()
    target = settings.app_url.rstrip("/") + "/search"
    if error:
        target += "?" + urlencode({"auth_error": error})
    response = RedirectResponse(target, status_code=303)
    response.delete_cookie(ATTEMPT_COOKIE, path=CALLBACK_PATH)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.post("/start", response_model=GoogleStart)
async def google_start(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    settings = require_google()
    # No existing authenticated session exists to carry a CSRF token. Require
    # the browser's exact origin before creating an anonymous login attempt.
    if request.headers.get("origin", "").rstrip("/") != settings.app_url.rstrip("/"):
        raise HTTPException(403, "Request origin is not allowed")
    await consume_usage(
        session,
        "anonymous-" + digest(request.client.host if request.client else "local"),
        "google sign in",
        30,
    )
    old_token = request.cookies.get(ATTEMPT_COOKIE)
    if old_token:
        await session.execute(
            update(OAuthLoginAttempt)
            .where(OAuthLoginAttempt.token_hash == digest(old_token))
            .values(used_at=utcnow())
        )
    token, verifier = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    session.add(
        OAuthLoginAttempt(
            token_hash=digest(token),
            verifier_ciphertext=encrypt(verifier),
            expires_at=utcnow() + timedelta(minutes=10),
        )
    )
    await session.commit()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    url = settings.supabase_url.rstrip("/") + "/auth/v1/authorize?" + urlencode(
        {
            "provider": "google",
            "redirect_to": settings.app_url.rstrip("/") + CALLBACK_PATH,
            "code_challenge": challenge.decode().rstrip("="),
            "code_challenge_method": "s256",
            "scopes": "openid email profile",
            "prompt": "select_account",
        }
    )
    response.set_cookie(
        ATTEMPT_COOKIE,
        token,
        httponly=True,
        secure=settings.production,
        samesite="lax",
        max_age=600,
        path=CALLBACK_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"url": url}


@router.get("/callback", include_in_schema=False)
async def google_callback(
    request: Request,
    code: str = Query(default="", max_length=4096),
    error: str = Query(default="", max_length=256),
    session: AsyncSession = Depends(get_session),
):
    settings = require_google()
    token = request.cookies.get(ATTEMPT_COOKIE, "")
    if not token:
        return callback_response("expired")
    # Claim and persist consumption before any provider call. A callback can
    # never be replayed, including after provider timeout or an app restart.
    ciphertext = (
        await session.execute(
            update(OAuthLoginAttempt)
            .where(
                OAuthLoginAttempt.token_hash == digest(token),
                OAuthLoginAttempt.used_at.is_(None),
                OAuthLoginAttempt.expires_at > utcnow(),
            )
            .values(used_at=utcnow())
            .returning(OAuthLoginAttempt.verifier_ciphertext)
        )
    ).scalar_one_or_none()
    await session.commit()
    if not ciphertext:
        return callback_response("expired")
    if error:
        return callback_response("cancelled")
    if not code:
        return callback_response("failed")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            exchanged = await client.post(
                settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=pkce",
                headers={"apikey": settings.supabase_anon_key},
                json={"auth_code": code, "code_verifier": decrypt(ciphertext)},
            )
            exchanged.raise_for_status()
            exchange_data = exchanged.json()
            if not isinstance(exchange_data, dict):
                return callback_response("failed")
            access_token = exchange_data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                return callback_response("failed")
            verified = await client.get(
                settings.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": "Bearer " + access_token,
                },
            )
            verified.raise_for_status()
            user = verified.json()
    except (httpx.HTTPError, ValueError, TypeError, InvalidToken) as exc:
        logger.warning("Google sign-in failed (%s)", type(exc).__name__)
        return callback_response("failed")
    if not isinstance(user, dict) or not isinstance(user.get("email"), str):
        return callback_response("failed")
    email = user["email"].strip().lower()
    identities = user.get("identities") or []
    if not isinstance(identities, list):
        return callback_response("failed")
    google_verified = any(
        identity.get("provider") == "google"
        and (identity.get("identity_data") or {}).get("email_verified") is True
        and ((identity.get("identity_data") or {}).get("email") or "").lower() == email
        for identity in identities
        if isinstance(identity, dict)
    )
    if (
        not google_verified
        or not user.get("email_confirmed_at")
        or not isinstance(user.get("id"), str)
        or not 0 < len(user["id"]) <= 80
        or email not in settings.email_allowlist
    ):
        return callback_response("not_invited")
    existing = (
        await session.execute(select(Account).where(Account.email == email))
    ).scalar_one_or_none()
    if existing and (existing.id != user["id"] or existing.is_demo):
        return callback_response("failed")
    insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
    await session.execute(
        insert(Account)
        .values(
            id=user["id"], email=email, is_demo=False,
            profile=Profile().model_dump(), created_at=utcnow(),
        )
        .on_conflict_do_nothing()
    )
    account = await session.get(Account, user["id"])
    if not account or account.email != email or account.is_demo:
        await session.rollback()
        return callback_response("failed")
    response = callback_response()
    await start_session(account, session, response)
    return response
