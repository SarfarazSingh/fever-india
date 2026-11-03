"""Persist-before-send ordering with conservative handling of uncertain outcomes."""

import hashlib
import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import utcnow
from app.services.duffel import DuffelClient, DuffelError
from app.v1.flights import normalize_offer
from app.v1.models import Account, Checkout
from app.v1.schemas import Offer, OrderRequest, TripData
from app.v1.trips import save_trip


def quote_hash(offer: Offer) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "amount": offer.total_amount,
                "currency": offer.currency,
                "offer": offer.id,
                "refund": offer.refund.model_dump(),
                "change": offer.change.model_dump(),
                "slices": [s.model_dump(mode="json") for s in offer.slices],
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


def checkout_read(row: Checkout, demo: bool) -> dict:
    return {
        "id": row.id,
        "offer": row.offer,
        "quote_hash": row.quote_hash,
        "expires_at": row.expires_at.isoformat(),
        "state": row.state,
        "trip_id": row.trip_id,
        "provider_order_id": row.provider_order_id,
        "is_demo": demo,
        "message": row.data.get("message"),
        "price_changed": row.data.get("price_changed", False),
    }


def require_checkout(offer: Offer, account: Account):
    settings = get_settings()
    if account.is_demo:
        return
    if not settings.duffel_cards_approved or (
        offer.live_mode and not settings.live_checkout_enabled
    ):
        raise HTTPException(
            409,
            "In-app payment is not enabled for this account. Continue on the airline website.",
        )
    if not offer.card_eligible:
        raise HTTPException(
            409,
            "This fare does not support traveler card payment. Continue on the airline website.",
        )
    if offer.identity_documents_required:
        raise HTTPException(
            409,
            "This itinerary requires passport details. Use the airline booking option for now.",
        )


async def finish_order(
    session: AsyncSession, row: Checkout, account: Account, order: dict
) -> None:
    """Only actual supplier references and ticket documents count as confirmation."""
    ref = order.get("booking_reference")
    if not ref:
        row.state = "confirming"
        row.provider_order_id = order.get("id")
        row.data = {
            **row.data,
            "message": "The airline is still returning the booking reference. Do not book again.",
        }
        await session.commit()
        return
    offer = Offer.model_validate(row.offer)
    needs_review = False
    if order.get("slices"):
        try:
            offer = normalize_offer(
                {
                    **order,
                    "id": offer.id,
                    "expires_at": (utcnow() + timedelta(minutes=30)).isoformat(),
                    "total_amount": order.get("total_amount") or offer.total_amount,
                    "total_currency": order.get("total_currency") or offer.currency,
                }
            )
        except (ValueError, KeyError, TypeError):
            needs_review = True
    passenger = row.data["passenger"]
    refs = [ref] + [
        r["booking_reference"]
        for r in order.get("booking_references") or []
        if r.get("booking_reference")
    ]
    documents = order.get("documents") or []
    # Supplier document URLs are never sent as public links. A private endpoint retrieves them.
    trip = await save_trip(
        session,
        account,
        TripData(
            passenger_name=passenger["given_name"] + " " + passenger["family_name"],
            references=refs,
            slices=offer.slices,
            payment_status="refund_status_pending"
            if order.get("cancelled_at")
            else "pending"
            if (order.get("payment_status") or {}).get("awaiting_payment")
            else "paid",
            ticketing_status="cancelled"
            if order.get("cancelled_at")
            else "ticketed"
            if documents
            else "pending",
            total_amount=offer.total_amount,
            currency=offer.currency,
            documents=documents,
            cancelled=bool(order.get("cancelled_at")),
            needs_review=needs_review,
            notes="Fictional demo booking. No ticket was purchased."
            if account.is_demo
            else "",
        ),
        "demo" if account.is_demo else "duffel",
        trip_id=row.trip_id,
    )
    row.trip_id = trip.id
    row.provider_order_id = order.get("id")
    row.state = (
        "cancelled"
        if order.get("cancelled_at")
        else "confirmed"
        if documents
        else "confirming"
    )
    row.data = {
        **row.data,
        "last_provider_sync": utcnow().isoformat(),
        "message": "The airline reports this booking was cancelled. Confirm the refund outcome with your booking support team."
        if order.get("cancelled_at")
        else "Booking confirmed"
        if documents
        else "Reservation received; awaiting ticket issuance",
    }
    await session.commit()


async def place_order(
    session: AsyncSession, row: Checkout, account: Account, payload: OrderRequest
) -> dict:
    offer = Offer.model_validate(row.offer)
    require_checkout(offer, account)
    if row.state in {"submitting", "confirming", "confirmed", "declined", "cancelled"}:
        return checkout_read(row, account.is_demo)
    if row.expires_at <= utcnow():
        raise HTTPException(
            410, "This quote expired. Please refresh your flight search."
        )
    if payload.accepted_quote_hash != row.quote_hash:
        raise HTTPException(409, "Review and accept the latest quote before booking")
    if not account.is_demo:
        if row.data.get("priced_card_id") != payload.card_id:
            raise HTTPException(409, "Review the final card price before booking")
        priced = await DuffelClient(get_settings())._request(
            "POST",
            f"/air/offers/{offer.id}/actions/price",
            json={
                "data": {
                    "intended_services": [],
                    "intended_payment_methods": [
                        {"type": "card", "card_id": payload.card_id}
                    ],
                }
            },
        )
        fresh = normalize_offer(priced["data"])
        require_checkout(fresh, account)
        if quote_hash(fresh) != row.quote_hash:
            row.offer = fresh.model_dump(mode="json")
            row.quote_hash = quote_hash(fresh)
            row.expires_at = fresh.expires_at
            row.data = {**row.data, "price_changed": True}
            await session.commit()
            raise HTTPException(
                409,
                "The fare or itinerary information changed. Review the refreshed quote and accept it again.",
            )
        if not payload.card_id or not payload.three_d_secure_session_id:
            raise HTTPException(
                422, "Complete secure card authentication before booking"
            )
    # Compare-and-swap protects against concurrent requests, even on multiple API instances.
    existing = (
        await session.execute(
            select(Checkout.id).where(
                Checkout.attempt_key == account.id + ":" + payload.attempt_key,
                Checkout.id != row.id,
            )
        )
    ).first()
    if existing:
        raise HTTPException(
            409,
            "This booking attempt has already been used. Review the existing booking status.",
        )
    claimed = await session.execute(
        update(Checkout)
        .where(Checkout.id == row.id, Checkout.state == "review")
        .values(
            state="submitting",
            attempt_key=account.id + ":" + payload.attempt_key,
            data={
                "passenger": payload.passenger.model_dump(mode="json"),
                "submitted_at": utcnow().isoformat(),
            },
        )
    )
    await session.commit()
    await session.refresh(row)
    if claimed.rowcount != 1:
        return checkout_read(row, account.is_demo)
    if account.is_demo:
        if payload.demo_outcome == "declined":
            row.state = "declined"
            row.data = {
                **row.data,
                "message": "Demo payment declined. No card was charged.",
            }
            await session.commit()
        elif payload.demo_outcome == "uncertain":
            row.state = "confirming"
            row.data = {
                **row.data,
                "message": "Demo: awaiting airline confirmation. Do not submit another booking.",
            }
            await session.commit()
        else:
            await finish_order(
                session,
                row,
                account,
                {
                    "id": "demo-order-" + row.id,
                    "booking_reference": "DEMO" + row.id[:4].upper(),
                    "documents": [
                        {"type": "demo", "name": "Demo itinerary · no ticket issued"}
                    ],
                },
            )
        return checkout_read(row, True)
    passenger = payload.passenger.model_dump(mode="json")
    passenger["id"] = offer.passenger_id
    try:
        result = await DuffelClient(get_settings())._request(
            "POST",
            "/air/orders",
            json={
                "data": {
                    "type": "instant",
                    "selected_offers": [offer.id],
                    "passengers": [passenger],
                    "payments": [
                        {
                            "type": "card",
                            "amount": offer.total_amount,
                            "currency": offer.currency,
                            "three_d_secure_session_id": payload.three_d_secure_session_id,
                        }
                    ],
                    "metadata": {"concierge_checkout_id": row.id},
                }
            },
        )
        await finish_order(session, row, account, result["data"])
    except DuffelError as exc:
        # Explicit 4xx rejections are definitive; network/5xx responses may have created an order.
        row.state = (
            "declined"
            if exc.status_code and 400 <= exc.status_code < 500
            else "confirming"
        )
        row.data = {
            **row.data,
            "message": "The provider rejected this booking. No retry was sent."
            if row.state == "declined"
            else "Awaiting airline confirmation. Do not book again; we are checking the outcome.",
        }
        await session.commit()
    return checkout_read(row, False)
