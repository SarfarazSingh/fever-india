"""APScheduler wiring for automated check-in jobs.

Jobs live in memory; the database is the source of truth. On startup every
booking still awaiting check-in is rescheduled, so a restart never loses a job.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Booking, CheckInStatus
from app.services.check_in import run_check_in

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(
    timezone=timezone.utc,
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 6 * 3600},
)


def job_id(booking_id: int) -> str:
    return f"checkin-{booking_id}"


def checkin_time_for(departure_time: datetime) -> datetime:
    lead = timedelta(hours=get_settings().checkin_lead_hours)
    return departure_time.astimezone(timezone.utc) - lead


def schedule_checkin(booking: Booking) -> datetime:
    """Schedule (or reschedule) the check-in job and return its run time.

    If the check-in window is already open, the job runs immediately.
    """
    now = datetime.now(timezone.utc)
    run_at = max(checkin_time_for(booking.departure_time), now + timedelta(seconds=1))
    scheduler.add_job(
        run_check_in,
        trigger=DateTrigger(run_date=run_at, timezone=timezone.utc),
        args=[booking.id],
        id=job_id(booking.id),
        name=f"Check-in {booking.airline_iata}{booking.flight_number} {booking.pnr_code}",
        replace_existing=True,
    )
    logger.info("Scheduled check-in for booking %s at %s", booking.id, run_at.isoformat())
    return run_at


def cancel_checkin(booking_id: int) -> None:
    job = scheduler.get_job(job_id(booking_id))
    if job:
        job.remove()


async def rehydrate_jobs() -> int:
    """Reschedule every booking that is still waiting to be checked in."""
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        result = await session.execute(
            select(Booking).where(
                Booking.check_in_status.in_([CheckInStatus.PENDING, CheckInStatus.SCHEDULED]),
                Booking.departure_time > now,
            )
        )
        bookings = result.scalars().all()
        count = 0
        for booking in bookings:
            if booking.checkin_strategy == "flyo" and booking.external_reference:
                # Flyo accepted the job and will call the webhook; don't resubmit.
                continue
            booking.checkin_scheduled_for = schedule_checkin(booking)
            booking.check_in_status = CheckInStatus.SCHEDULED
            count += 1
        await session.commit()
    logger.info("Rehydrated %d check-in job(s)", count)
    return count
