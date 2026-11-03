from datetime import datetime

import httpx

from app.config import get_settings
from app.services.airline_link import (
    _serpapi,
    _follow_booking,
    airline_booking_requests,
    host_is_airline,
    page_matches_cabin,
)
from app.v1.schemas import Offer, Slice
from app.v1.trips import official_site


def matches(candidate: dict, slc: Slice) -> bool:
    flights = candidate.get("flights") or []
    if len(flights) != len(slc.segments):
        return False
    for leg, segment in zip(flights, slc.segments):
        if (leg.get("flight_number") or "").replace(" ", "") != segment.flight_number:
            return False
        for field, code, time in [
            ("departure_airport", segment.origin, segment.departure_local),
            ("arrival_airport", segment.destination, segment.arrival_local),
        ]:
            data = leg.get(field) or {}
            if data.get("id") != code:
                return False
            try:
                dt = datetime.fromisoformat(data["time"])
                expected = datetime.fromisoformat(time)
                if dt.replace(tzinfo=None) != expected.replace(tzinfo=None):
                    return False
            except (ValueError, KeyError):
                return False
        if (leg.get("travel_class") or "").lower() not in {
            segment.cabin,
            segment.cabin_name.lower() if segment.cabin_name else "",
        }:
            return False
    return True


async def resolve_handoff(offer: Offer) -> dict:
    first = offer.slices[0].segments[0]
    fallback = official_site(first.airline)
    route_only = {
        "match": "route_only" if fallback else "unavailable",
        "url": fallback,
        "message": "Reselect your route, dates, and cabin on the airline website. Its prices and fare rules may differ."
        if fallback
        else "No verified airline website is available for this itinerary.",
    }
    s = get_settings()
    if not s.serpapi_api_key or len(offer.slices) > 2:
        return route_only
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False) as client:
            common = {
                "engine": "google_flights",
                "departure_id": first.origin,
                "arrival_id": offer.slices[0].segments[-1].destination,
                "outbound_date": first.departure_local[:10],
                "type": "1" if len(offer.slices) == 2 else "2",
                "travel_class": "4" if first.cabin == "first" else "3",
                "adults": "1",
                "currency": offer.currency,
                "hl": "en",
            }
            if len(offer.slices) == 2:
                common["return_date"] = offer.slices[1].segments[0].departure_local[:10]
            page = await _serpapi(client, s, common)

            def pick(page, slc, token):
                return next(
                    (
                        c
                        for c in [
                            *page.get("best_flights", []),
                            *page.get("other_flights", []),
                        ]
                        if c.get(token) and matches(c, slc)
                    ),
                    None,
                )

            if len(offer.slices) == 2:
                out = pick(page, offer.slices[0], "departure_token")
                if not out:
                    return route_only
                page = await _serpapi(
                    client, s, {**common, "departure_token": out["departure_token"]}
                )
            option = pick(page, offer.slices[-1], "booking_token")
            if not option:
                return route_only
            booking = await _serpapi(
                client, s, {**common, "booking_token": option["booking_token"]}
            )
            # A round trip must be offered together, never two unrelated purchases.
            options = booking.get("booking_options") or []
            if len(offer.slices) == 2:
                options = [o for o in options if isinstance(o.get("together"), dict)]
            for req in airline_booking_requests(options)[:3]:
                url, status = await _follow_booking(
                    client, req["url"], req.get("post_data") or "", first.airline
                )
                if (
                    status == 200
                    and host_is_airline(url, first.airline)
                    and page_matches_cabin(url, first.cabin)
                ):
                    return {
                        "match": "exact_itinerary",
                        "url": url,
                        "message": "The full flight itinerary matched. Confirm the airline’s current price and fare conditions before paying.",
                    }
    except Exception as exc:
        # Provider handoff is optional; official route search remains usable.
        import logging

        logging.getLogger(__name__).info(
            "Exact airline handoff unavailable (%s)", type(exc).__name__
        )
    return route_only
