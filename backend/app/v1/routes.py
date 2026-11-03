import hashlib
import json
import secrets
from datetime import timedelta
from pathlib import Path
from decimal import Decimal
from typing import Literal

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from pydantic import EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import utcnow
from app.services.duffel import DuffelClient, DuffelError
from app.v1.checkout import checkout_read, place_order, quote_hash, require_checkout
from app.v1.flights import normalize_offer
from app.v1.imports import parse_draft
from app.v1.models import (
    Account,
    Checkout,
    ImportDraft,
    LoginSession,
    MailConnection,
    SearchRecord,
    ServiceRequest,
    Trip,
)
from app.v1.schemas import (
    CheckoutRequest,
    Model,
    Offer,
    OrderRequest,
    Profile,
    SearchRequest,
    SearchResponse,
    TripData,
)
from app.v1.security import (
    COOKIE,
    consume_usage,
    current_account,
    digest,
    owned,
    start_session,
)
from app.v1.trips import calendar_events, calendar_ics, save_trip, seed_demo, trip_read

router = APIRouter(prefix="/api/v1", tags=["concierge"])


class LoginRequest(Model):
    email: EmailStr


class VerifyRequest(LoginRequest):
    token: str = Field(pattern=r"^[0-9]{6,8}$")


class PublicConfig(Model):
    demo_available: bool
    login_available: bool
    login_methods: list[Literal["google", "email_otp"]]
    environment: Literal["development", "test", "staging", "production"]


class ImportRequest(Model):
    raw_text: str = Field(min_length=20, max_length=100000)


class ServiceBody(Model):
    kind: str = Field(pattern=r"^(change|cancel|support)$")
    message: str = Field(min_length=10, max_length=3000)


class PriceBody(Model):
    card_id: str = Field(min_length=8, max_length=100)


def features(demo=False):
    s = get_settings()
    return {
        "demo": demo,
        "checkout": demo or s.duffel_cards_approved,
        "live_checkout": s.live_checkout_enabled and s.duffel_cards_approved,
        "gmail": bool(
            s.google_client_id and s.google_client_secret and s.token_encryption_key
        ),
        "places": bool(s.google_places_api_key),
        "notifications": bool(s.resend_api_key and s.notification_from),
        "forwarding": bool(
            s.forwarding_domain and s.resend_api_key and s.resend_webhook_secret
        ),
    }


@router.get("/config", response_model=PublicConfig)
async def config():
    s = get_settings()
    return {
        "demo_available": s.demo_enabled and not s.production,
        "login_available": bool(s.login_methods),
        "login_methods": s.login_methods,
        "environment": s.environment,
    }


@router.post("/auth/demo")
async def demo_login(
    response: Response, request: Request, session: AsyncSession = Depends(get_session)
):
    settings = get_settings()
    if not settings.demo_enabled or settings.production:
        raise HTTPException(404, "Not found")
    await consume_usage(
        session,
        "anonymous-" + digest(request.client.host if request.client else "local"),
        "demo login",
        30,
    )
    account = Account(
        email=f"demo-{secrets.token_hex(12)}@example.invalid",
        is_demo=True,
        profile=Profile(
            first_name="Federico", home_airport="MAD", airlines=["IB", "BA", "QR"]
        ).model_dump(),
    )
    session.add(account)
    await session.flush()
    csrf = await start_session(account, session, response)
    await seed_demo(session, account)
    return {
        "csrf_token": csrf,
        "account": {"id": account.id, "email": account.email, "is_demo": True},
        "profile": account.profile,
        "features": features(True),
    }


@router.post("/auth/login")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    if "email_otp" not in s.login_methods:
        raise HTTPException(404, "Email sign-in is disabled")
    await consume_usage(
        session,
        "anonymous-" + digest(request.client.host if request.client else "local"),
        "sign in",
        20,
    )
    if not s.supabase_url or not s.supabase_anon_key:
        raise HTTPException(503, "Private sign-in is not configured yet")
    # Same response for unknown addresses; never expose the guest list.
    if str(payload.email).lower() in s.email_allowlist:
        async with httpx.AsyncClient(timeout=15) as client:
            result = await client.post(
                s.supabase_url + "/auth/v1/otp",
                headers={"apikey": s.supabase_anon_key},
                json={"email": str(payload.email).lower(), "create_user": True},
            )
        if result.status_code >= 400:
            raise HTTPException(
                503, "Could not send a sign-in code. Try again shortly."
            )
    return {"message": "If this address is invited, a sign-in code is on its way."}


@router.post("/auth/verify")
async def verify(
    payload: VerifyRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    if "email_otp" not in s.login_methods:
        raise HTTPException(404, "Email sign-in is disabled")
    await consume_usage(
        session,
        "anonymous-" + digest(request.client.host if request.client else "local"),
        "verify",
        30,
    )
    if str(payload.email).lower() not in s.email_allowlist or not s.supabase_url:
        raise HTTPException(401, "Invalid sign-in code")
    async with httpx.AsyncClient(timeout=15) as client:
        result = await client.post(
            s.supabase_url + "/auth/v1/verify",
            headers={"apikey": s.supabase_anon_key},
            json={
                "email": str(payload.email).lower(),
                "token": payload.token,
                "type": "email",
            },
        )
    if result.status_code >= 400:
        raise HTTPException(401, "Invalid or expired sign-in code")
    user = result.json().get("user") or {}
    if (user.get("email") or "").lower() != str(payload.email).lower() or not user.get(
        "id"
    ):
        raise HTTPException(401, "Could not verify account")
    account = (
        (
            await session.execute(
                select(Account).where(Account.email == str(payload.email).lower())
            )
        )
        .scalars()
        .first()
    )
    if account is None:
        account = Account(
            id=user["id"],
            email=str(payload.email).lower(),
            profile=Profile().model_dump(),
        )
        session.add(account)
        await session.flush()
    csrf = await start_session(account, session, response)
    return {
        "csrf_token": csrf,
        "account": {"id": account.id, "email": account.email, "is_demo": False},
        "profile": account.profile,
        "features": features(),
    }


@router.get("/auth/session")
async def me(
    request: Request,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(LoginSession, digest(request.cookies[COOKIE]))
    return {
        "csrf_token": row.csrf_token,
        "account": {
            "id": account.id,
            "email": account.email,
            "is_demo": account.is_demo,
        },
        "profile": Profile.model_validate(account.profile),
        "features": features(account.is_demo),
    }


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        delete(LoginSession).where(
            LoginSession.token_hash == digest(request.cookies[COOKIE])
        )
    )
    await session.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.put("/profile", response_model=Profile)
async def profile(
    payload: Profile,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    account.profile = payload.model_dump()
    await session.commit()
    return payload


def search_read(row: SearchRecord, cursor=0, limit=25, sort="best") -> SearchResponse:
    data = row.result or {}
    results = list(data.get("results", []))
    if sort == "price":
        results.sort(key=lambda o: (o["currency"], Decimal(o["total_amount"])))
    elif sort == "fastest":
        results.sort(key=lambda o: sum(s["duration_minutes"] for s in o["slices"]))
    return SearchResponse(
        id=row.id,
        status=row.status,
        progress={
            "queued": "Preparing your search",
            "searching": "Checking airline inventory",
            "complete": "Your options are ready",
            "partial": "Some airline data could not be retrieved",
            "failed": "Search could not be completed",
        }[row.status],
        live_mode=data.get("live_mode", False),
        results=results[cursor : cursor + limit],
        total_offers=data.get("total_offers", 0),
        matching_itineraries=len(results),
        next_cursor=cursor + limit if cursor + limit < len(results) else None,
        exclusions=data.get("exclusions", {}),
        adjustments=data.get("adjustments", []),
        coverage=data.get("coverage", "Awaiting provider response"),
        error=row.error,
        request=row.request,
    )


@router.post("/searches", response_model=SearchResponse, status_code=202)
async def search(
    payload: SearchRequest,
    background: BackgroundTasks,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    from app.v1.jobs import dispatch_search

    fingerprint = hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()
    cached = (
        (
            await session.execute(
                select(SearchRecord)
                .where(
                    SearchRecord.account_id == account.id,
                    SearchRecord.fingerprint == fingerprint,
                    SearchRecord.created_at > utcnow() - timedelta(seconds=90),
                    SearchRecord.status.in_(
                        ["queued", "searching", "complete", "partial"]
                    ),
                )
                .order_by(SearchRecord.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if cached:
        return search_read(cached)
    await consume_usage(
        session, account.id, "search", get_settings().search_daily_limit
    )
    row = SearchRecord(
        account_id=account.id,
        fingerprint=fingerprint,
        request=payload.model_dump(mode="json"),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    background.add_task(dispatch_search, row.id)
    return search_read(row)


@router.get("/searches/{search_id}", response_model=SearchResponse)
async def get_search(
    search_id: str,
    cursor: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    sort: Literal["best", "price", "fastest"] = "best",
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    return search_read(
        await owned(session, SearchRecord, search_id, account), cursor, limit, sort
    )


async def find_offer(session, account, search_id, offer_id):
    row = await owned(session, SearchRecord, search_id, account)
    for offer in (row.result or {}).get("inventory", []):
        if offer["id"] == offer_id:
            return Offer.model_validate(offer)
    raise HTTPException(404, "Offer not found in this search")


@router.post("/airline-handoffs")
async def handoff(
    payload: CheckoutRequest,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    from app.v1.handoff import resolve_handoff

    offer = await find_offer(session, account, payload.search_id, payload.offer_id)
    if account.is_demo:
        return {
            "match": "unavailable",
            "url": None,
            "message": "Demo itineraries cannot be booked. Sign in with live inventory to continue at an airline.",
        }
    await consume_usage(
        session, account.id, "airline lookup", get_settings().search_daily_limit
    )
    return await resolve_handoff(offer)


@router.get("/trips")
async def trips(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    records = (
        (
            await session.execute(
                select(Trip)
                .where(Trip.account_id == account.id)
                .order_by(Trip.departure_at)
            )
        )
        .scalars()
        .all()
    )
    return [trip_read(t, account.is_demo) for t in records]


@router.post("/trips", status_code=201)
async def add_trip(
    payload: TripData,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    return trip_read(await save_trip(session, account, payload), account.is_demo)


@router.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    return trip_read(await owned(session, Trip, trip_id, account), account.is_demo)


@router.patch("/trips/{trip_id}")
async def edit_trip(
    trip_id: str,
    payload: TripData,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await owned(session, Trip, trip_id, account)
    row.itinerary = payload.model_dump(mode="json")
    row.departure_at = payload.slices[0].segments[0].departure_at
    row.status = (
        "cancelled"
        if payload.cancelled
        else "needs_attention"
        if payload.needs_review
        else "confirmed"
    )
    await session.commit()
    return trip_read(row, account.is_demo)


@router.post("/trips/{trip_id}/service-requests", status_code=201)
async def service(
    trip_id: str,
    payload: ServiceBody,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    await owned(session, Trip, trip_id, account)
    row = ServiceRequest(
        account_id=account.id,
        trip_id=trip_id,
        kind=payload.kind,
        message=payload.message,
    )
    session.add(row)
    await session.commit()
    return {
        "id": row.id,
        "status": row.status,
        "message": "Your request is saved. No change or cancellation has been made. Use the airline link for urgent assistance.",
    }


@router.get("/calendar")
async def calendar(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (await session.execute(select(Trip).where(Trip.account_id == account.id)))
        .scalars()
        .all()
    )
    return calendar_events(rows)


@router.get("/calendar.ics")
async def export_calendar(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (await session.execute(select(Trip).where(Trip.account_id == account.id)))
        .scalars()
        .all()
    )
    return Response(
        calendar_ics(calendar_events(rows)),
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="elsewhere-trips.ics"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/imports/preview", status_code=201)
async def preview_import(
    payload: ImportRequest,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    await consume_usage(session, account.id, "import", 100)
    data, issues = parse_draft(payload.raw_text)
    row = ImportDraft(account_id=account.id, data=data, issues=issues)
    session.add(row)
    await session.commit()
    return {"id": row.id, "data": data, "issues": issues}


@router.get("/imports")
async def pending_imports(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(ImportDraft)
                .where(
                    ImportDraft.account_id == account.id,
                    ImportDraft.confirmed_trip_id.is_(None),
                )
                .order_by(ImportDraft.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {"id": r.id, "data": r.data, "issues": r.issues, "source": r.source}
        for r in rows
    ]


@router.post("/imports/{draft_id}/confirm")
async def confirm_import(
    draft_id: str,
    payload: TripData,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await owned(session, ImportDraft, draft_id, account)
    if row.confirmed_trip_id:
        return trip_read(
            await owned(session, Trip, row.confirmed_trip_id, account), account.is_demo
        )
    trip = await save_trip(session, account, payload, row.source)
    row.confirmed_trip_id = trip.id
    await session.commit()
    return trip_read(trip, account.is_demo)


@router.post("/checkout-sessions", status_code=201)
async def new_checkout(
    payload: CheckoutRequest,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    offer = await find_offer(session, account, payload.search_id, payload.offer_id)
    require_checkout(offer, account)
    active = (
        (
            await session.execute(
                select(Checkout)
                .where(
                    Checkout.account_id == account.id,
                    Checkout.offer["id"].as_string() == offer.id,
                    Checkout.state.in_(
                        ["review", "submitting", "confirming", "confirmed"]
                    ),
                    Checkout.expires_at > utcnow(),
                )
                .order_by(Checkout.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if active:
        return checkout_read(active, account.is_demo)
    if not account.is_demo:
        offer = normalize_offer(await DuffelClient(get_settings()).get_offer(offer.id))
        require_checkout(offer, account)
    if offer.expires_at <= utcnow():
        raise HTTPException(
            410, "The offer expired. Search again for current availability."
        )
    row = Checkout(
        account_id=account.id,
        offer=offer.model_dump(mode="json"),
        quote_hash=quote_hash(offer),
        expires_at=offer.expires_at,
        data={"price_changed": False},
    )
    session.add(row)
    await session.commit()
    return checkout_read(row, account.is_demo)


@router.get("/checkout-sessions/{checkout_id}")
async def get_checkout(
    checkout_id: str,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    return checkout_read(
        await owned(session, Checkout, checkout_id, account), account.is_demo
    )


@router.post("/checkout-sessions/{checkout_id}/component-key")
async def component_key(
    checkout_id: str,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await owned(session, Checkout, checkout_id, account)
    require_checkout(Offer.model_validate(row.offer), account)
    if account.is_demo:
        return {"component_client_key": None}
    result = await DuffelClient(get_settings())._request(
        "POST", "/identity/component_client_keys", json={"data": {}}
    )
    return result["data"]


@router.post("/checkout-sessions/{checkout_id}/price")
async def price_checkout(
    checkout_id: str,
    payload: PriceBody,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await owned(session, Checkout, checkout_id, account)
    if row.state != "review":
        raise HTTPException(409, "This booking attempt has already started")
    require_checkout(Offer.model_validate(row.offer), account)
    if not account.is_demo:
        result = await DuffelClient(get_settings())._request(
            "POST",
            f"/air/offers/{row.offer['id']}/actions/price",
            json={
                "data": {
                    "intended_services": [],
                    "intended_payment_methods": [
                        {"type": "card", "card_id": payload.card_id}
                    ],
                }
            },
        )
        offer = normalize_offer(result["data"])
        row.data = {
            "price_changed": quote_hash(offer) != row.quote_hash,
            "priced_card_id": payload.card_id,
        }
        row.offer = offer.model_dump(mode="json")
        row.quote_hash = quote_hash(offer)
        row.expires_at = offer.expires_at
        await session.commit()
    return checkout_read(row, account.is_demo)


@router.post("/orders")
async def order(
    payload: OrderRequest,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await owned(session, Checkout, payload.checkout_id, account)
    await consume_usage(session, account.id, "booking submission", 50)
    return await place_order(session, row, account, payload)


@router.get("/trips/{trip_id}/guide")
async def guide(
    trip_id: str,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    from app.v1.integrations import destination_guide

    trip = await owned(session, Trip, trip_id, account)
    if not account.is_demo:
        await consume_usage(
            session, account.id, "places", get_settings().places_daily_limit
        )
    return await destination_guide(
        trip, Profile.model_validate(account.profile), account.is_demo
    )


@router.get("/trips/{trip_id}/documents/{index}")
async def document(
    trip_id: str,
    index: int,
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    from urllib.parse import urlparse

    trip = await owned(session, Trip, trip_id, account)
    docs = trip.itinerary.get("documents", [])
    if index < 0 or index >= len(docs) or account.is_demo:
        raise HTTPException(404, "Document unavailable")
    key = docs[index].get("storage_key")
    s = get_settings()
    if not key or not s.supabase_service_role_key:
        raise HTTPException(409, "This document is awaiting secure storage")
    # Only owner-scoped storage keys can be signed, never arbitrary supplier URLs.
    if not key.startswith(account.id + "/"):
        raise HTTPException(404, "Document unavailable")
    async with httpx.AsyncClient(timeout=10) as client:
        result = await client.post(
            s.supabase_url + "/storage/v1/object/sign/travel-documents/" + key,
            headers={"Authorization": "Bearer " + s.supabase_service_role_key},
            json={"expiresIn": 60},
        )
    if result.status_code >= 400:
        raise HTTPException(503, "Could not retrieve this document")
    return {"url": s.supabase_url + "/storage/v1" + result.json()["signedURL"]}


@router.delete("/account/data")
async def delete_data(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    active = (
        await session.execute(
            select(Checkout.id)
            .where(
                Checkout.account_id == account.id,
                Checkout.state.in_(["submitting", "confirming"]),
            )
            .limit(1)
        )
    ).first()
    if active:
        raise HTTPException(409, "Resolve pending bookings before deleting travel data")
    from app.v1.integrations import disconnect

    await disconnect(account, session)
    keys = []
    for trip in (
        await session.execute(select(Trip).where(Trip.account_id == account.id))
    ).scalars():
        keys.extend(
            d["storage_key"]
            for d in trip.itinerary.get("documents", [])
            if d.get("storage_key", "").startswith(account.id + "/")
        )
    s = get_settings()
    if keys and s.supabase_service_role_key:
        async with httpx.AsyncClient(timeout=15) as client:
            result = await client.request(
                "DELETE",
                s.supabase_url + "/storage/v1/object/travel-documents",
                headers={"Authorization": "Bearer " + s.supabase_service_role_key},
                json={"prefixes": keys},
            )
        if result.status_code >= 400:
            raise HTTPException(
                503,
                "Could not remove stored documents. Please try data deletion again.",
            )
    for model in [
        ServiceRequest,
        ImportDraft,
        Checkout,
        Trip,
        SearchRecord,
        MailConnection,
    ]:
        await session.execute(delete(model).where(model.account_id == account.id))
    account.profile = Profile().model_dump()
    await session.commit()
    return {"ok": True}
