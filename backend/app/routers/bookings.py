from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Booking, CheckInStatus
from app.schemas import BookingCreate, BookingRead, TriggerResponse
from app.services.check_in import run_check_in
from app.services.scheduler import cancel_checkin, schedule_checkin

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("/register-checkin", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def register_checkin(payload: BookingCreate, session: AsyncSession = Depends(get_session)) -> Booking:
    if payload.departure_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="departure_time is in the past")

    existing = await session.execute(
        select(Booking).where(
            Booking.pnr_code == payload.pnr_code,
            Booking.passenger_last_name == payload.passenger_last_name,
            Booking.flight_number == payload.flight_number,
        )
    )
    booking = existing.scalars().first()
    if booking is None:
        booking = Booking(**payload.model_dump())
        session.add(booking)
    else:
        for field, value in payload.model_dump().items():
            setattr(booking, field, value)
        booking.boarding_pass_url = None
        booking.last_error = None
        booking.external_reference = None
        booking.checkin_strategy = None

    booking.check_in_status = CheckInStatus.PENDING
    await session.flush()

    booking.checkin_scheduled_for = schedule_checkin(booking)
    booking.check_in_status = CheckInStatus.SCHEDULED
    await session.commit()
    await session.refresh(booking)
    return booking


@router.post(
    "/{booking_id}/trigger-checkin-now",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_checkin_now(
    booking_id: int,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> TriggerResponse:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.check_in_status == CheckInStatus.COMPLETED:
        return TriggerResponse(booking_id=booking.id, message="Already checked in")

    if booking.check_in_status == CheckInStatus.FAILED:
        booking.check_in_status = CheckInStatus.SCHEDULED
        booking.last_error = None
        await session.commit()

    cancel_checkin(booking.id)
    background.add_task(run_check_in, booking.id)
    return TriggerResponse(booking_id=booking.id, message="Check-in started")


@router.get("", response_model=list[BookingRead])
async def list_bookings(
    email: str | None = Query(None, description="Filter by traveller email"),
    session: AsyncSession = Depends(get_session),
) -> list[Booking]:
    stmt = select(Booking).order_by(Booking.departure_time.asc())
    if email:
        stmt = stmt.where(Booking.user_email == email.strip().lower())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(booking_id: int, session: AsyncSession = Depends(get_session)) -> Booking:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking(booking_id: int, session: AsyncSession = Depends(get_session)) -> None:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    cancel_checkin(booking.id)
    await session.delete(booking)
    await session.commit()
