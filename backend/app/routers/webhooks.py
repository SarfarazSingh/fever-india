import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import Booking, CheckInStatus
from app.schemas import BookingRead, CheckInWebhookPayload
from app.services.check_in import FlyoClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _verify_signature(secret: str, body: bytes, signature: str | None) -> None:
    if not secret:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Flyo-Signature header")
    provided = signature.removeprefix("sha256=").strip()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/checkin-complete", response_model=BookingRead)
async def checkin_complete(
    request: Request,
    booking_id: int | None = Query(None),
    x_flyo_signature: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Booking:
    body = await request.body()
    _verify_signature(get_settings().flyo_webhook_secret, body, x_flyo_signature)

    try:
        payload = CheckInWebhookPayload.model_validate_json(body or b"{}")
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    target_id = payload.booking_id or booking_id
    booking: Booking | None = None
    if target_id is not None:
        booking = await session.get(Booking, target_id)
    if booking is None and payload.pnr_code:
        stmt = select(Booking).where(Booking.pnr_code == payload.pnr_code)
        if payload.passenger_last_name:
            stmt = stmt.where(Booking.passenger_last_name.ilike(payload.passenger_last_name))
        booking = (await session.execute(stmt.order_by(Booking.departure_time.desc()))).scalars().first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found for webhook")

    status_value = payload.status.lower()
    if status_value in FlyoClient.COMPLETED_STATES and payload.boarding_pass_url:
        booking.check_in_status = CheckInStatus.COMPLETED
        booking.boarding_pass_url = payload.boarding_pass_url
        booking.last_error = None
    elif status_value in FlyoClient.PENDING_STATES:
        booking.check_in_status = CheckInStatus.SCHEDULED
    else:
        booking.check_in_status = CheckInStatus.FAILED
        booking.last_error = payload.error or f"Flyo reported status '{payload.status}' without a boarding pass"

    booking.checkin_strategy = booking.checkin_strategy or "flyo"
    if payload.reference:
        booking.external_reference = payload.reference
    await session.commit()
    await session.refresh(booking)
    logger.info("Webhook updated booking %s to %s", booking.id, booking.check_in_status.value)
    return booking
