"""Dual-strategy automated check-in: Flyo API first, Playwright bot fallback."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum

import httpx

from app.config import STATIC_DIR, Settings, get_settings
from app.database import SessionLocal
from app.models import Booking, CheckInStatus
from app.services.bots import CheckInBotError, get_bot_for

logger = logging.getLogger(__name__)


class FlyoOutcome(str, Enum):
    COMPLETED = "completed"
    PENDING = "pending"


@dataclass
class FlyoResult:
    outcome: FlyoOutcome
    boarding_pass_url: str | None = None
    reference: str | None = None


class FlyoError(RuntimeError):
    pass


class FlyoClient:
    """Thin async client for the Flyo AI Web Check-in API."""

    PENDING_STATES = {"pending", "processing", "queued", "accepted", "in_progress"}
    COMPLETED_STATES = {"completed", "success", "checked_in", "done"}

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._transport = transport

    def callback_url(self, booking_id: int) -> str:
        return f"{self._settings.public_base_url}/api/webhooks/checkin-complete?booking_id={booking_id}"

    async def check_in(self, booking: Booking) -> FlyoResult:
        payload = {
            "pnr_code": booking.pnr_code,
            "airline_iata": booking.airline_iata,
            "passenger_last_name": booking.passenger_last_name,
            "passenger_first_name": booking.passenger_first_name,
            "flight_number": booking.flight_number,
            "departure_time": booking.departure_time.isoformat(),
            "callback_url": self.callback_url(booking.id),
            "metadata": {"booking_id": booking.id},
        }
        headers = {
            "Authorization": f"Bearer {self._settings.flyo_api_key}",
            "X-API-Key": self._settings.flyo_api_key,
            "Idempotency-Key": f"booking-{booking.id}-{booking.pnr_code}",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._settings.flyo_base_url,
                timeout=httpx.Timeout(30.0, connect=5.0),
                transport=self._transport,
            ) as client:
                resp = await client.post("/v1/checkin", json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise FlyoError(f"Flyo request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise FlyoError(f"Flyo returned HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            body = resp.json()
        except ValueError as exc:
            raise FlyoError("Flyo returned a non-JSON response") from exc

        status = str(body.get("status", "")).lower()
        url = body.get("boarding_pass_url") or (body.get("data") or {}).get("boarding_pass_url")
        reference = body.get("id") or body.get("reference") or body.get("checkin_id")

        if url and (status in self.COMPLETED_STATES or not status):
            return FlyoResult(FlyoOutcome.COMPLETED, boarding_pass_url=url, reference=reference)
        if status in self.PENDING_STATES or resp.status_code == 202:
            return FlyoResult(FlyoOutcome.PENDING, reference=reference)
        raise FlyoError(f"Flyo check-in unsuccessful (status={status or 'unknown'}): {body.get('error') or body}")


class CheckInEngine:
    def __init__(self, settings: Settings | None = None, flyo: FlyoClient | None = None):
        self.settings = settings or get_settings()
        self.flyo = flyo or FlyoClient(self.settings)
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, booking_id: int) -> asyncio.Lock:
        return self._locks.setdefault(booking_id, asyncio.Lock())

    async def run(self, booking_id: int) -> CheckInStatus | None:
        lock = self._lock_for(booking_id)
        if lock.locked():
            logger.info("Check-in for booking %s already running; skipping duplicate trigger", booking_id)
            return None
        async with lock:
            return await self._run(booking_id)

    async def _run(self, booking_id: int) -> CheckInStatus | None:
        async with SessionLocal() as session:
            booking = await session.get(Booking, booking_id)
            if booking is None:
                logger.warning("Check-in triggered for unknown booking %s", booking_id)
                return None
            if booking.check_in_status == CheckInStatus.COMPLETED:
                return booking.check_in_status

            logger.info("Starting check-in for booking %s (%s %s)", booking.id, booking.airline_iata, booking.pnr_code)
            errors: list[str] = []

            if self.settings.flyo_enabled:
                try:
                    result = await self.flyo.check_in(booking)
                    booking.checkin_strategy = "flyo"
                    booking.external_reference = result.reference
                    if result.outcome is FlyoOutcome.COMPLETED:
                        booking.check_in_status = CheckInStatus.COMPLETED
                        booking.boarding_pass_url = result.boarding_pass_url
                        booking.last_error = None
                    else:
                        booking.check_in_status = CheckInStatus.SCHEDULED
                        booking.last_error = None
                    await session.commit()
                    logger.info("Flyo check-in for booking %s: %s", booking.id, result.outcome.value)
                    return booking.check_in_status
                except FlyoError as exc:
                    logger.warning("Flyo check-in failed for booking %s: %s", booking.id, exc)
                    errors.append(str(exc))
            else:
                errors.append("Flyo API not configured")

            bot_cls = get_bot_for(booking.airline_iata)
            if bot_cls is None:
                errors.append(f"No Playwright check-in bot registered for airline {booking.airline_iata}")
                return await self._fail(session, booking, errors)

            booking.checkin_strategy = "playwright"
            try:
                result = await bot_cls(self.settings).run(booking)
            except CheckInBotError as exc:
                msg = str(exc)
                if exc.screenshot_path:
                    msg += f" (screenshot: {self._public_url(exc.screenshot_path)})"
                errors.append(msg)
                return await self._fail(session, booking, errors)
            except Exception as exc:  # noqa: BLE001 - browser launch failures etc.
                logger.exception("Playwright bot crashed for booking %s", booking.id)
                errors.append(f"Playwright error: {type(exc).__name__}: {exc}")
                return await self._fail(session, booking, errors)

            booking.check_in_status = CheckInStatus.COMPLETED
            booking.boarding_pass_url = self._public_url(result.boarding_pass_path)
            booking.last_error = None
            await session.commit()
            logger.info("Playwright check-in completed for booking %s", booking.id)
            return booking.check_in_status

    async def _fail(self, session, booking: Booking, errors: list[str]) -> CheckInStatus:
        booking.check_in_status = CheckInStatus.FAILED
        booking.last_error = " | ".join(errors)
        await session.commit()
        logger.error("Check-in failed for booking %s: %s", booking.id, booking.last_error)
        return booking.check_in_status

    def _public_url(self, path) -> str:
        relative = path.resolve().relative_to(STATIC_DIR.resolve()).as_posix()
        return f"{self.settings.public_base_url}/static/{relative}"


_engine: CheckInEngine | None = None


def get_engine() -> CheckInEngine:
    global _engine
    if _engine is None:
        _engine = CheckInEngine()
    return _engine


async def run_check_in(booking_id: int) -> None:
    """Entry point used by the scheduler and the manual trigger endpoint."""
    await get_engine().run(booking_id)
