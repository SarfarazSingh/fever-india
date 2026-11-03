"""Opaque server-side sessions. Credentials and mailbox tokens never reach JS."""

import hashlib
import secrets
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import utcnow
from app.v1.models import Account, LoginSession, Usage

COOKIE = "concierge_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def current_account(
    request: Request, session: AsyncSession = Depends(get_session)
) -> Account:
    token = request.cookies.get(COOKIE, "")
    row = await session.get(LoginSession, digest(token)) if token else None
    if row is None or row.expires_at <= utcnow():
        raise HTTPException(401, "Sign in to your private concierge")
    account = await session.get(Account, row.account_id)
    settings = get_settings()
    if account is None or (
        not account.is_demo and account.email not in settings.email_allowlist
    ):
        raise HTTPException(403, "This account is not on the private guest list")
    if account.is_demo and (not settings.demo_enabled or settings.production):
        raise HTTPException(403, "Demo access is disabled")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(csrf, row.csrf_token):
            raise HTTPException(
                403, "Your session needs refreshing. Reload and try again."
            )
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.app_url.rstrip("/"):
            raise HTTPException(403, "Request origin is not allowed")
    request.state.account_id = account.id
    return account


async def start_session(
    account: Account, session: AsyncSession, response: Response
) -> str:
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    settings = get_settings()
    session.add(
        LoginSession(
            token_hash=digest(token),
            account_id=account.id,
            csrf_token=csrf,
            expires_at=utcnow() + timedelta(days=settings.session_days),
        )
    )
    await session.commit()
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=settings.production,
        samesite="lax",
        max_age=settings.session_days * 86400,
        path="/",
    )
    return csrf


async def owned(session: AsyncSession, model, identifier: str, account: Account):
    row = await session.get(model, identifier)
    if row is None or row.account_id != account.id:
        raise HTTPException(404, "Record not found")
    return row


async def consume_usage(
    session: AsyncSession, account_id: str, kind: str, limit: int
) -> None:
    """Atomic quota consumption, including across API workers."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    day = utcnow().date().isoformat()
    insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
    stmt = insert(Usage).values(account_id=account_id, day=day, kind=kind, count=0)
    await session.execute(
        stmt.on_conflict_do_nothing(index_elements=["account_id", "day", "kind"])
    )
    stmt = (
        update(Usage)
        .where(
            Usage.account_id == account_id,
            Usage.day == day,
            Usage.kind == kind,
            Usage.count < limit,
        )
        .values(count=Usage.count + 1)
    )
    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount == 0:
        raise HTTPException(429, f"Daily {kind} limit reached. Try again tomorrow.")


def encrypt(value: str) -> str:
    from cryptography.fernet import Fernet

    key = get_settings().token_encryption_key
    if not key:
        raise HTTPException(503, "Secure token storage has not been configured")
    return Fernet(key.encode()).encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    from cryptography.fernet import Fernet

    return (
        Fernet(get_settings().token_encryption_key.encode())
        .decrypt(value.encode())
        .decode()
    )
