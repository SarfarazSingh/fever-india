"""Conservative extraction: incomplete confirmations are review drafts, never guessed bookings."""

import html
import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.airports import AIRPORTS, airport_tz
from app.v1.schemas import Segment, Slice, TripData
from app.services.flight_search import airline_name


def parse_draft(raw: str) -> tuple[dict, list[str]]:
    text = html.unescape(re.sub(r"<[^>]+>", "\n", raw))
    refs = list(
        dict.fromkeys(
            re.findall(
                r"(?:confirmation(?:\s+(?:code|number))?|booking\s+reference|PNR|record\s+locator)\s*[:#]\s*([A-Z0-9]{5,20})\b",
                text,
                re.I,
            )
        )
    )
    name = re.search(r"(?:passenger|travell?er)\s*:\s*([^\n\r]+)", text, re.I)
    data = {
        "passenger_name": name.group(1).strip()[:200] if name else "",
        "references": [r.upper() for r in refs],
        "slices": [],
        "payment_status": "external",
        "ticketing_status": "imported",
        "checkin_status": "not_open",
        "documents": [],
        "notes": "",
        "needs_review": False,
        "cancelled": bool(
            re.search(
                r"(?:booking|reservation|flight)\s+(?:has been\s+)?cancelled",
                text,
                re.I,
            )
        ),
    }
    issues = []
    structured_complete = False
    # Accept explicit JSON-LD FlightReservation data from airline confirmations.
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        raw,
        re.S | re.I,
    ):
        try:
            payload = json.loads(match.group(1))
            entries = payload if isinstance(payload, list) else [payload]
            for item in entries:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") != "FlightReservation":
                    continue
                f = item.get("reservationFor") or {}
                p = item.get("underName") or {}
                if not isinstance(f, dict) or not isinstance(p, dict):
                    issues.append("Review the structured traveler and flight details")
                    continue
                data["passenger_name"] = p.get("name") or data["passenger_name"]
                if item.get("reservationNumber"):
                    data["references"] = [item["reservationNumber"]]
                flight = str(f.get("flightNumber") or "").replace(" ", "")
                code = (f.get("airline") or {}).get("iataCode") or flight[:2]
                if not flight.startswith(code):
                    flight = code + flight
                _add_segment(
                    data,
                    flight,
                    (f.get("departureAirport") or {}).get("iataCode"),
                    (f.get("arrivalAirport") or {}).get("iataCode"),
                    f.get("departureTime"),
                    f.get("arrivalTime"),
                    issues,
                )
                structured_complete = bool(
                    data["slices"]
                    and data["references"]
                    and data["passenger_name"]
                    and not issues
                )
                if "Cancelled" in str(item.get("reservationStatus", "")):
                    data["cancelled"] = True
        except (ValueError, TypeError, KeyError):
            issues.append("Structured flight data needs review")
    if not data["slices"]:
        blocks = re.split(
            r"(?=\bFlight\s*[:#]?\s*[A-Z0-9]{2}\s*\d{1,4}\b)", text, flags=re.I
        )
        for block in blocks:
            flight = re.search(
                r"\bFlight\s*[:#]?\s*([A-Z0-9]{2})\s*(\d{1,4})\b", block, re.I
            )
            route = re.search(r"\b([A-Z]{3})\s*(?:→|to|->|–|—)\s*([A-Z]{3})\b", block)
            dep = re.search(r"Departure\s*:\s*([^\n\r]+)", block, re.I)
            arr = re.search(r"Arrival\s*:\s*([^\n\r]+)", block, re.I)
            if flight and route and dep and arr:
                _add_segment(
                    data,
                    flight.group(1).upper() + flight.group(2),
                    route.group(1),
                    route.group(2),
                    dep.group(1).strip(),
                    arr.group(1).strip(),
                    issues,
                )
    if not data["references"]:
        issues.append("Add the actual airline booking reference")
    if not data["passenger_name"]:
        issues.append("Add the passenger name exactly as booked")
    if not data["slices"]:
        issues.append("Add the flight route, departure, arrival, and airport timezones")
    if data["slices"] and not structured_complete:
        issues.append("Confirm all flight segments and both directions are included")
    return data, list(dict.fromkeys(issues))


def _add_segment(data, number, origin, dest, departure, arrival, issues):
    try:
        dep = datetime.fromisoformat(departure.replace("Z", "+00:00"))
        arr = datetime.fromisoformat(arrival.replace("Z", "+00:00"))
        ot, dt = airport_tz(origin), airport_tz(dest)
        if not ot or not dt:
            raise ValueError("Missing airport timezone")
        dep = dep.replace(tzinfo=ot) if dep.tzinfo is None else dep
        arr = arr.replace(tzinfo=dt) if arr.tzinfo is None else arr
        seg = Segment(
            id=f"import-{len(data['slices'])}",
            origin=origin,
            destination=dest,
            origin_city=AIRPORTS[origin][0],
            destination_city=AIRPORTS[dest][0],
            origin_timezone=str(ot),
            destination_timezone=str(dt),
            departure_at=dep.astimezone(timezone.utc),
            arrival_at=arr.astimezone(timezone.utc),
            departure_local=dep.astimezone(ot).isoformat(),
            arrival_local=arr.astimezone(dt).isoformat(),
            airline=number[:2],
            airline_name=airline_name(number[:2]),
            flight_number=number,
        )
        # Retain each explicit flight, joining contiguous connections into slices.
        if (
            data["slices"]
            and data["slices"][-1]["segments"][-1]["destination"] == origin
        ):
            prev = data["slices"][-1]
            prev_time = datetime.fromisoformat(
                prev["segments"][-1]["arrival_at"].replace("Z", "+00:00")
            )
            if 0 < (dep - prev_time).total_seconds() < 12 * 3600:
                prev["segments"].append(seg.model_dump(mode="json"))
                prev["stops"] += 1
                start = datetime.fromisoformat(
                    prev["segments"][0]["departure_at"].replace("Z", "+00:00")
                )
                prev["duration_minutes"] = int((arr - start).total_seconds() / 60)
                return
        slc = Slice(
            id=f"import-slice-{len(data['slices'])}",
            segments=[seg],
            stops=0,
            duration_minutes=int((arr - dep).total_seconds() / 60),
        )
        data["slices"].append(slc.model_dump(mode="json"))
    except (ValueError, TypeError, KeyError):
        issues.append(f"Review the dates, times, and airport timezones for {number}")
