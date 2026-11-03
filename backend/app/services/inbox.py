"""Pull a booking out of an airline confirmation email. No mailbox login required."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from app.schemas import BookingCreate

_PNR = re.compile(
    r"(?:PNR|Confirmation|Record\s+Locator|Booking\s+Reference|Reservation\s+Code)"
    r"(?:\s*(?:number|code|no\.?|#))?(?:\s+is)?[:\s#]+([A-Z0-9]{5,8})\b",
    re.I,
)
_FLIGHT = re.compile(r"\b([A-Z]{2})\s?(\d{1,4})\b")
_ROUTE = re.compile(r"\b([A-Z]{3})\s*(?:to|–|—|-|→|>)\s*([A-Z]{3})\b", re.I)
_WHEN = re.compile(
    r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}))?\b"
)
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_NAME = re.compile(r"(?:Passenger|Guest|Traveller|Traveler)[:\s]+([A-Z][a-z]+)\s+([A-Z][a-zA-Z'-]+)")
_IGNORE_FLIGHTS = {"BA000", "OK000"}


class EmailParseError(ValueError):
    pass


def parse_confirmation(raw: str, *, fallback_email: str = "", fallback_last: str = "Guest") -> BookingCreate:
    text = raw.replace("\r", "\n")
    matches = list(_PNR.finditer(text))
    if not matches:
        raise EmailParseError("No confirmation code found. Look for a line like 'Confirmation: ABC123'.")
    pnr = matches[-1].group(1).upper()
    for match in matches:
        code = match.group(1).upper()
        if re.fullmatch(r"[A-Z]{2,3}\d{2,4}", code):
            continue
        pnr = code
        break

    route = _ROUTE.search(text.upper())
    origin = route.group(1) if route else None
    destination = route.group(2) if route else None

    flight = None
    for match in _FLIGHT.finditer(text.upper()):
        candidate = f"{match.group(1)}{int(match.group(2))}"
        if candidate[:2] in {"AM", "PM", "ON", "AT", "TO", "OF", "OR"}:
            continue
        flight = f"{match.group(1)}{match.group(2)}"
        break
    if not flight:
        raise EmailParseError("No flight number found (for example BA178).")

    when = _WHEN.search(text)
    if not when:
        raise EmailParseError("No departure date found.")
    departure = _parse_when(when.group(1), when.group(2))

    email_match = _EMAIL.search(text)
    name = _NAME.search(text)
    first = name.group(1) if name else "Federico"
    last = name.group(2) if name else (fallback_last or "Guest")
    email = email_match.group(0) if email_match else (fallback_email or "federico@example.com")

    return BookingCreate(
        user_email=email,
        passenger_first_name=first,
        passenger_last_name=last,
        airline_iata=flight[:2],
        flight_number=flight,
        origin=origin,
        destination=destination,
        departure_time=departure,
        pnr_code=pnr[:16],
    )


def _parse_when(day: str, clock: str | None) -> datetime:
    clock = clock or "12:00"
    for fmt in ("%d %B %Y %H:%M", "%d %b %Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            local = datetime.strptime(f"{day} {clock}", fmt)
            return local.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise EmailParseError(f"Could not read the date '{day}'.")
