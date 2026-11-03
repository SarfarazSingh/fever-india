from datetime import datetime
from urllib.parse import urlencode
import re

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


def cabin_code(value: str | None) -> str | None:
    key = re.sub(r"[\s_-]", "", (value or "").lower())
    return {
        "economy": "economy", "economyclass": "economy",
        "premiumeconomy": "premium_economy", "premiumeconomyclass": "premium_economy",
        "business": "business", "businessclass": "business",
        "first": "first", "firstclass": "first",
    }.get(key)


def airline_search_url(offer: Offer) -> str | None:
    """Official BA route search verified against its current booking form.

    This carries the search, without selecting a substitute itinerary or fare.
    """
    first = offer.slices[0].segments[0]
    destination = offer.slices[0].segments[-1].destination
    if first.airline != "BA" or len(offer.slices) > 2:
        return None
    cabins = {segment.cabin for slc in offer.slices for segment in slc.segments}
    if len(cabins) != 1 or first.cabin not in {"business", "first", "economy", "premium_economy"}:
        return None
    query = {
        "trip": "round" if len(offer.slices) == 2 else "oneway",
        "departureDate": first.departure_local[:10],
        "from": first.origin, "to": destination,
        "travelClass": first.cabin, "adults": "1", "youngAdults": "0",
        "children": "0", "infants": "0", "bound": "outbound",
    }
    if len(offer.slices) == 2:
        back = offer.slices[1]
        if back.segments[0].origin != destination or back.segments[-1].destination != first.origin:
            return None
        query["arrivalDate"] = back.segments[0].departure_local[:10]
    return "https://www.britishairways.com/nx/b/airselect/en/esp/book/search/?" + urlencode(query)


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
        if cabin_code(leg.get("travel_class")) != segment.cabin or segment.cabin is None:
            return False
    return True


async def resolve_handoff(offer: Offer) -> dict:
    first = offer.slices[0].segments[0]
    prefilled = airline_search_url(offer)
    fallback = prefilled or official_site(first.airline)
    route_only = {
        "match": "route_only" if fallback else "unavailable",
        "url": fallback,
        "prefilled": bool(prefilled),
        "message": "Your route, dates, passenger count, and cabin are filled in. Choose your flights and fare on the airline’s results page; availability and prices may differ." if prefilled else "The airline does not offer a verified prefilled link for this itinerary. Enter your route and dates on its website; availability and prices may differ."
        if fallback
        else "No verified airline website is available for this itinerary.",
    }
    if not offer.live_mode:
        route_only["message"] = "This app is showing test inventory, not a real fare. " + route_only["message"]
        return route_only
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
                "include_airlines": first.airline,
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
