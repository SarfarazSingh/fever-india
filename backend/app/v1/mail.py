"""Gmail reminders with durable submission state and uncertain-outcome reconciliation."""
import base64
import hashlib
import json
from email.message import EmailMessage
from email.policy import SMTP
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select, update

from app.config import get_settings
from app.database import SessionLocal
from app.models import utcnow
from app.v1.models import Account, EmailDelivery, MailConnection, Trip
from app.v1.security import decrypt

READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def has_send_access(row: MailConnection | None) -> bool:
    if not row or row.status != "connected" or not row.token_ciphertext:
        return False
    saved = json.loads(decrypt(row.token_ciphertext))
    return SEND_SCOPE in saved.get("scope", "").split()


async def gmail_access_token(db, row, client):
    s = get_settings()
    saved = json.loads(decrypt(row.token_ciphertext))
    result = await client.post("https://oauth2.googleapis.com/token", data={
        "client_id": s.google_client_id, "client_secret": s.google_client_secret,
        "refresh_token": saved["refresh_token"], "grant_type": "refresh_token",
    })
    if result.status_code >= 400 or not result.json().get("access_token"):
        row.status = "needs_reconnect"
        await db.commit()
        return None
    return result.json()["access_token"]


def delivery_message_id(delivery_id: str) -> str:
    host = urlsplit(get_settings().app_url).hostname or "travel.invalid"
    return f"<{delivery_id}@{host}>"


def message_payload(delivery, account, trip, mailbox_email):
    s = get_settings()
    message = EmailMessage(policy=SMTP)
    message["To"] = account.email
    message["From"] = mailbox_email
    message["Message-ID"] = delivery_message_id(delivery.id)
    if delivery.kind == "test":
        message["Subject"] = "Federico’s travel desk: email connection confirmed"
        body = "Your Gmail reminder connection is working. No flight was booked.\n\nOpen your travel desk: " + s.app_url
    else:
        message["Subject"] = "Your trip is coming up"
        body = (f"{trip.title} departs within 24 hours. Check the airline’s check-in window, entry requirements and your itinerary:\n"
                f"{s.app_url}/trips/{trip.id}\n\nCheck-in has not been completed by this reminder. Use the airline’s check-in link in your itinerary.")
    message.set_content(body)
    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")}


async def send_delivery(delivery_id: str):
    """Persist before sending. A timeout is reconciled, never blindly resent."""
    s = get_settings()
    if not s.gmail_send_enabled:
        return
    async with SessionLocal() as db:
        delivery = await db.get(EmailDelivery, delivery_id)
        if not delivery or delivery.state in {"sent", "failed", "cancelled"}:
            return
        account = await db.get(Account, delivery.account_id)
        connection = await db.get(MailConnection, delivery.account_id)
        trip = await db.get(Trip, delivery.trip_id) if delivery.trip_id else None
        if account.is_demo or not has_send_access(connection):
            delivery.state = "failed"
            delivery.error = "Reconnect Gmail with email sending permission."
            await db.commit()
            return
        if delivery.kind != "test" and (not trip or trip.status == "cancelled" or not account.profile.get("reminders", True)):
            delivery.state = "cancelled"
            await db.commit()
            return
        saved = json.loads(decrypt(connection.token_ciphertext))
        async with httpx.AsyncClient(timeout=15) as client:
            token = await gmail_access_token(db, connection, client)
            if not token:
                delivery.state = "failed"
                delivery.error = "Gmail needs reconnecting before email can be sent."
                await db.commit()
                return
            headers = {"Authorization": "Bearer " + token}
            if delivery.state in {"sending", "confirming"}:
                # A crash can happen after provider acceptance and before the DB commit.
                result = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=headers,
                    params={"q": "in:sent rfc822msgid:" + delivery_message_id(delivery.id).strip("<>"), "maxResults": 1})
                result.raise_for_status()
                sent = result.json().get("messages") or []
                if sent:
                    delivery.message_id = sent[0]["id"]
                    delivery.state = "sent"
                    delivery.error = None
                else:
                    delivery.state = "confirming"
                    delivery.error = "Checking whether Gmail accepted this email; it will not be resent automatically."
                await db.commit()
                return
            claimed = await db.execute(update(EmailDelivery).where(
                EmailDelivery.id == delivery.id, EmailDelivery.state == "queued").values(state="sending"))
            await db.commit()
            if claimed.rowcount != 1:
                return
            payload = message_payload(delivery, account, trip, saved.get("mailbox_email") or account.email)
            try:
                response = await client.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers=headers, json=payload)
                if response.status_code >= 500:
                    delivery.state = "confirming"
                    delivery.error = "Gmail’s response is uncertain; checking delivery before any further action."
                elif response.status_code >= 400:
                    delivery.state = "failed"
                    delivery.error = "Gmail could not send this email. Check the connection and sending quota."
                elif response.json().get("id"):
                    delivery.state = "sent"
                    delivery.message_id = response.json()["id"]
                    delivery.error = None
                else:
                    delivery.state = "confirming"
                    delivery.error = "Gmail has not returned a delivery reference yet."
            except (httpx.HTTPError, ValueError):
                delivery.state = "confirming"
                delivery.error = "Gmail’s response is uncertain; checking delivery before any further action."
            await db.commit()


async def queue_due_reminders(db):
    from datetime import timedelta
    if not get_settings().gmail_send_enabled:
        return
    trips = (await db.execute(select(Trip).where(
        Trip.departure_at > utcnow(), Trip.departure_at < utcnow() + timedelta(hours=24), Trip.status == "confirmed"))).scalars().all()
    for trip in trips:
        account = await db.get(Account, trip.account_id)
        connection = await db.get(MailConnection, trip.account_id)
        if account.is_demo or not account.profile.get("reminders", True) or not has_send_access(connection):
            continue
        key = hashlib.sha256(("gmail-reminder:" + trip.id + ":" + trip.departure_at.isoformat()).encode()).hexdigest()
        if not await db.get(EmailDelivery, key):
            db.add(EmailDelivery(id=key, account_id=account.id, trip_id=trip.id, kind="trip_reminder"))
    await db.commit()
