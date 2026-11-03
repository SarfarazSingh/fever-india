from datetime import date, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Booking, Preferences
from app.schemas import (
    BookingRead,
    CalendarEvent,
    DestinationGuide,
    EmailImport,
    PreferencesRead,
    PreferencesUpdate,
)
from app.services.guides import guide_for
from app.services.inbox import EmailParseError, parse_confirmation
from app.services.links import airline_manage_url
from app.routers.bookings import _save_and_schedule

router = APIRouter(prefix="/api", tags=["profile"])


async def load_preferences(session: AsyncSession) -> Preferences:
    row = await session.get(Preferences, 1)
    if row is None:
        row = Preferences(id=1)
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


@router.get("/preferences", response_model=PreferencesRead)
async def get_preferences(session: AsyncSession = Depends(get_session)) -> Preferences:
    return await load_preferences(session)


@router.put("/preferences", response_model=PreferencesRead)
async def put_preferences(payload: PreferencesUpdate, session: AsyncSession = Depends(get_session)) -> Preferences:
    row = await load_preferences(session)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/calendar", response_model=list[CalendarEvent])
async def calendar(
    start: date | None = None,
    end: date | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[CalendarEvent]:
    result = await session.execute(select(Booking).order_by(Booking.departure_time.asc()))
    events: list[CalendarEvent] = []
    for booking in result.scalars():
        local = booking.departure_time.astimezone(timezone.utc)
        day = local.date()
        if start and day < start:
            continue
        if end and day > end:
            continue
        route = f"{booking.origin or ''} → {booking.destination or ''}".strip(" →")
        events.append(
            CalendarEvent(
                booking_id=booking.id,
                date=day,
                title=f"{booking.flight_number} {route}".strip(),
                detail=f"{booking.passenger_first_name} {booking.passenger_last_name}",
                pnr_code=booking.pnr_code,
                destination=booking.destination,
                manage_url=airline_manage_url(booking.airline_iata, booking.pnr_code),
            )
        )
    return events


@router.get("/destinations/{airport}/guide", response_model=DestinationGuide)
async def destination_guide(airport: str, session: AsyncSession = Depends(get_session)) -> DestinationGuide:
    if len(airport) != 3 or not airport.isalpha():
        raise HTTPException(status_code=422, detail="airport must be a 3-letter IATA code")
    prefs = await load_preferences(session)
    return guide_for(airport, wants_gym=prefs.wants_gym, wants_spa=prefs.wants_spa)


@router.post("/inbox/import", response_model=BookingRead, status_code=201)
async def import_email(payload: EmailImport, session: AsyncSession = Depends(get_session)) -> Booking:
    prefs = await load_preferences(session)
    try:
        booking_in = parse_confirmation(
            payload.raw_text,
            fallback_email=prefs.email,
            fallback_last=prefs.traveller_last_name or "Guest",
        )
    except EmailParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if prefs.traveller_first_name and booking_in.passenger_first_name == "Federico":
        booking_in = booking_in.model_copy(
            update={
                "passenger_first_name": prefs.traveller_first_name,
                "passenger_last_name": prefs.traveller_last_name or booking_in.passenger_last_name,
                "user_email": prefs.email or booking_in.user_email,
            }
        )
    return await _save_and_schedule(session, booking_in)
