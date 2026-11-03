import base64
import json
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import utcnow
from app.v1.imports import parse_draft
from app.v1.models import Account, EventReceipt, ImportDraft, MailConnection, Trip
from app.v1.schemas import Profile, TripData
from app.v1.security import current_account, consume_usage, decrypt, digest, encrypt
from app.v1.trips import save_trip

router = APIRouter(prefix="/api/v1", tags=["connections"])


async def connection_for(db, account):
    row = await db.get(MailConnection, account.id)
    if row is None:
        row = MailConnection(
            account_id=account.id, forwarding_token=secrets.token_urlsafe(24)
        )
        db.add(row)
        await db.commit()
    return row


@router.get("/connections")
async def connections(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await connection_for(session, account)
    s = get_settings()
    return {
        "gmail": {
            "status": row.status,
            "last_synced_at": row.last_synced_at,
            "configured": bool(
                s.google_client_id and s.google_client_secret and s.token_encryption_key
            ),
        },
        "forwarding_address": (row.forwarding_token + "@" + s.forwarding_domain)
        if s.forwarding_domain and not account.is_demo
        else None,
    }


@router.post("/connections/gmail/connect")
async def connect_gmail(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    if account.is_demo or not (
        s.google_client_id and s.google_client_secret and s.token_encryption_key
    ):
        raise HTTPException(
            409, "Gmail connection is not available in this environment"
        )
    row = await connection_for(session, account)
    state = secrets.token_urlsafe(48)
    row.state_hash = digest(state)
    row.state_expires_at = utcnow() + timedelta(minutes=10)
    await session.commit()
    return {
        "url": "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": s.google_client_id,
                "redirect_uri": s.gmail_redirect_uri,
                "response_type": "code",
                "scope": "https://www.googleapis.com/auth/gmail.readonly",
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
    }


@router.get("/connections/gmail/callback")
async def gmail_callback(
    state: str,
    code: str = "",
    error: str = "",
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    s = get_settings()
    row = await connection_for(session, account)
    if (
        not row.state_hash
        or not secrets.compare_digest(row.state_hash, digest(state))
        or not row.state_expires_at
        or row.state_expires_at < utcnow()
    ):
        raise HTTPException(
            400, "The Gmail connection expired. Start again from your profile."
        )
    row.state_hash = None
    await session.commit()
    if error:
        return RedirectResponse(
            s.app_url + "/preferences?gmail=cancelled", status_code=303
        )
    async with httpx.AsyncClient(timeout=15) as client:
        result = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.gmail_redirect_uri,
                "grant_type": "authorization_code",
                "code": code,
            },
        )
    if result.status_code >= 400 or not result.json().get("refresh_token"):
        raise HTTPException(
            400, "Could not securely connect Gmail. Try connecting again."
        )
    row.token_ciphertext = encrypt(json.dumps(result.json()))
    row.status = "connected"
    await session.commit()
    return RedirectResponse(s.app_url + "/preferences?gmail=connected", status_code=303)


@router.delete("/connections/gmail")
async def disconnect(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    row = await connection_for(session, account)
    if row.token_ciphertext:
        token = json.loads(decrypt(row.token_ciphertext)).get("refresh_token")
        if token:
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke", data={"token": token}
                    )
                except httpx.HTTPError:
                    pass
    row.token_ciphertext = None
    row.status = "disconnected"
    await session.commit()
    return {"ok": True}


@router.post("/connections/gmail/sync")
async def sync_now(
    account: Account = Depends(current_account),
    session: AsyncSession = Depends(get_session),
):
    await consume_usage(session, account.id, "mail sync", 30)
    row = await connection_for(session, account)
    if row.status != "connected":
        raise HTTPException(409, "Connect Gmail first")
    await sync_mailbox(session, row)
    return {"ok": True, "last_synced_at": row.last_synced_at}


def decode_message(payload):
    content = []
    if payload.get("body", {}).get("data"):
        content.append(
            base64.urlsafe_b64decode(payload["body"]["data"] + "===").decode(
                errors="replace"
            )
        )
    for part in payload.get("parts", []):
        content.extend(decode_message(part))
    return content


async def import_message(db, account, raw, source, source_id):
    receipt_id = source + ":" + account.id + ":" + source_id
    if await db.get(EventReceipt, receipt_id):
        return
    data, issues = parse_draft(raw)
    draft = ImportDraft(
        account_id=account.id,
        source=source,
        source_id=source_id,
        data=data,
        issues=issues,
    )
    db.add(draft)
    db.add(EventReceipt(id=receipt_id))
    if not issues:
        try:
            trip = await save_trip(db, account, TripData.model_validate(data), source)
            draft.confirmed_trip_id = trip.id
        except ValidationError:
            draft.issues = ["Review the extracted itinerary before importing"]
    await db.commit()


async def sync_mailbox(db: AsyncSession, row: MailConnection):
    if not row.token_ciphertext:
        return
    s = get_settings()
    account = await db.get(Account, row.account_id)
    saved = json.loads(decrypt(row.token_ciphertext))
    async with httpx.AsyncClient(timeout=20) as client:
        token = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "refresh_token": saved["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        if token.status_code >= 400:
            row.status = "needs_reconnect"
            await db.commit()
            return
        headers = {"Authorization": "Bearer " + token.json()["access_token"]}
        since = (
            "after:" + str(int((row.last_synced_at - timedelta(days=1)).timestamp()))
            if row.last_synced_at
            else "newer_than:90d"
        )
        params = {
            "q": since
            + ' {"booking confirmation" "flight confirmation" "e-ticket" "booking reference" "flight cancelled" "schedule change"}',
            "maxResults": 50,
        }
        for _ in range(5):
            listing = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=headers,
                params=params,
            )
            listing.raise_for_status()
            for item in listing.json().get("messages", []):
                if await db.get(EventReceipt, "gmail:" + account.id + ":" + item["id"]):
                    continue
                message = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
                    + item["id"],
                    headers=headers,
                    params={"format": "full"},
                )
                message.raise_for_status()
                body = "\n".join(decode_message(message.json().get("payload", {})))[
                    :100000
                ]
                if body:
                    await import_message(db, account, body, "gmail", item["id"])
            page = listing.json().get("nextPageToken")
            if not page:
                break
            params["pageToken"] = page
        if not page:
            row.last_synced_at = utcnow()
        await db.commit()


@router.post("/webhooks/inbound")
async def inbound(request: Request, session: AsyncSession = Depends(get_session)):
    from svix.webhooks import Webhook, WebhookVerificationError

    s = get_settings()
    if not s.resend_webhook_secret:
        raise HTTPException(503, "Inbound email is not configured")
    raw = await request.body()
    if len(raw) > 1_000_000:
        raise HTTPException(413, "Message too large")
    try:
        event = Webhook(s.resend_webhook_secret).verify(raw, dict(request.headers))
    except (WebhookVerificationError, ValueError):
        raise HTTPException(401, "Invalid webhook signature")
    if event.get("type") != "email.received":
        return {"ok": True}
    data = event.get("data") or {}
    recipients = data.get("to") or []
    for recipient in recipients:
        token = recipient.split("@", 1)[0]
        connection = (
            (
                await session.execute(
                    select(MailConnection).where(
                        MailConnection.forwarding_token == token
                    )
                )
            )
            .scalars()
            .first()
        )
        if not connection:
            continue
        account = await session.get(Account, connection.account_id)
        if account.is_demo:
            continue
        await consume_usage(session, account.id, "inbound email", 100)
        async with httpx.AsyncClient(timeout=15) as client:
            result = await client.get(
                "https://api.resend.com/emails/receiving/" + data["email_id"],
                headers={"Authorization": "Bearer " + s.resend_api_key},
            )
        if result.status_code >= 400:
            raise HTTPException(503, "Unable to retrieve inbound message")
        body = result.json()
        await import_message(
            session,
            account,
            (body.get("text") or body.get("html") or "")[:100000],
            "forward",
            data["email_id"],
        )
    return {"ok": True}


async def destination_guide(trip: Trip, prefs: Profile, demo: bool):
    from app.v1.places import verified_hotels

    last = trip.itinerary["slices"][0]["segments"][-1]
    city = last["destination_city"]
    result = {
        "city": city,
        "hotels": verified_hotels(last["destination"], prefs),
        "restaurants": [],
        "activities": [],
        "is_demo": demo,
        "note": "Hotel recommendations use dated official sources for classification, gym and spa; availability must be confirmed with the property.",
    }
    s = get_settings()
    if demo:
        from app.services.guides import guide_for

        old = guide_for(last["destination"])
        for kind in ["hotels", "restaurants"]:
            result[kind] = [
                {
                    "name": p.name,
                    "area": p.area,
                    "reason": p.why,
                    "url": p.url,
                    "verification": "Demo suggestion · verify details",
                    "rating": None,
                    "hotel_stars": None,
                    "gym": None,
                    "spa": None,
                }
                for p in getattr(old, kind)[:3]
            ]
        result["activities"] = [
            {
                "name": "A neighborhood walk",
                "area": city,
                "reason": "Leave an afternoon unscheduled and explore on foot.",
                "url": "https://www.google.com/maps/search/?api=1&query=" + city,
                "verification": "Demo inspiration",
            }
        ]
        return result
    if not s.google_places_api_key:
        result["note"] = (
            "Source-checked hotel recommendations are available for selected cities. Restaurant and activity discovery requires the place-data connection."
        )
        return result
    async with httpx.AsyncClient(timeout=15) as client:
        for kind, query in [
            ("restaurants", f"restaurants {city} {prefs.destination_notes}"),
            ("activities", f"cultural attractions {city} {prefs.destination_notes}"),
        ]:
            response = await client.post(
                "https://places.googleapis.com/v1/places:searchText",
                headers={
                    "X-Goog-Api-Key": s.google_places_api_key,
                    "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.websiteUri,places.googleMapsUri,places.rating,places.businessStatus,places.attributions",
                },
                json={"textQuery": query, "pageSize": 3},
            )
            if response.status_code >= 400:
                result["note"] = (
                    "Some destination data is temporarily unavailable. Try again later."
                )
                continue
            for p in response.json().get("places", []):
                if p.get("businessStatus") != "OPERATIONAL":
                    continue
                result[kind].append(
                    {
                        "name": p["displayName"]["text"],
                        "area": p.get("formattedAddress", ""),
                        "reason": "A place to consider near your destination"
                        if kind != "hotels"
                        else "Luxury hotel candidate; five-star classification, gym, and spa have not been verified.",
                        "url": p.get("websiteUri") or p.get("googleMapsUri"),
                        "rating": p.get("rating"),
                        "hotel_stars": None,
                        "gym": None,
                        "spa": None,
                        "verification": "Google Places · amenities unverified"
                        if kind == "hotels"
                        else "Google Places",
                        "attributions": p.get("attributions", []),
                    }
                )
    return result


async def send_reminders(db):
    s = get_settings()
    if not s.resend_api_key or not s.notification_from:
        return
    trips = (
        (
            await db.execute(
                select(Trip).where(
                    Trip.departure_at > utcnow(),
                    Trip.departure_at < utcnow() + timedelta(hours=24),
                    Trip.status == "confirmed",
                )
            )
        )
        .scalars()
        .all()
    )
    for trip in trips:
        account = await db.get(Account, trip.account_id)
        key = "reminder:" + trip.id + ":" + trip.departure_at.isoformat()
        if (
            account.is_demo
            or not account.profile.get("reminders", True)
            or await db.get(EventReceipt, key)
        ):
            continue
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer " + s.resend_api_key,
                    "Idempotency-Key": key,
                },
                json={
                    "from": s.notification_from,
                    "to": [account.email],
                    "subject": "Your trip is coming up",
                    "text": f"{trip.title} departs within 24 hours. Check your airline’s check-in window and review your itinerary at {s.app_url}/trips/{trip.id}.",
                },
            )
        if response.status_code < 400:
            db.add(EventReceipt(id=key))
            await db.commit()


async def store_documents(db, trip):
    s = get_settings()
    if not s.supabase_service_role_key:
        return
    documents = trip.itinerary.get("documents", [])
    changed = False
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for idx, doc in enumerate(documents):
            url = doc.get("url")
            host = (urlparse(url).hostname or "") if url else ""
            if (
                not url
                or doc.get("storage_key")
                or not (host == "duffel.com" or host.endswith(".duffel.com"))
                or urlparse(url).scheme != "https"
            ):
                continue
            response = await client.get(url)
            if response.status_code != 200 or len(response.content) > 10_000_000:
                continue
            key = f"{trip.account_id}/{trip.id}/{idx}.pdf"
            saved = await client.post(
                s.supabase_url + "/storage/v1/object/travel-documents/" + key,
                headers={
                    "Authorization": "Bearer " + s.supabase_service_role_key,
                    "Content-Type": "application/pdf",
                    "x-upsert": "true",
                },
                content=response.content,
            )
            if saved.status_code < 400:
                doc["storage_key"] = key
                changed = True
    if changed:
        trip.itinerary = {**trip.itinerary, "documents": documents}
        await db.commit()
