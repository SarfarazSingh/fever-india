"""Resolve the airline's own booking page from a Google Flights handoff.

Guessed airline paths 404. Google Flights does not put the airline URL in the
search link. The booking option marked as the airline is a POST to
google.com/travel/clk, which redirects to the carrier.
"""

from __future__ import annotations

import html
import re
import time
from datetime import date
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from app.config import Settings, get_settings

SERPAPI_URL = "https://serpapi.com/search.json"
_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = 3 * 60 * 60
_BROWSER = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Hosts that are not the airline, even if Google lists them as a way to buy.
_BLOCKED_HOSTS = (
    "google.",
    "gstatic.",
    "googleapis.",
    "expedia.",
    "kayak.",
    "booking.com",
    "momondo.",
    "cheapoair.",
    "kiwi.com",
    "trip.com",
    "orbitz.",
    "priceline.",
    "gotogate.",
    "edreams.",
    "mytrip.",
    "lastminute.",
    "skyscanner.",
    "travelocity.",
    "agoda.",
    "hopper.",
    "flightnetwork.",
    "budgetair.",
    "tripadvisor.",
)

_AIRLINE_HOSTS: dict[str, tuple[str, ...]] = {
    "AA": ("aa.com",),
    "AC": ("aircanada.com",),
    "AF": ("airfrance.com", "airfrance.fr", "airfrance.us"),
    "AI": ("airindia.com",),
    "AS": ("alaskaair.com",),
    "AY": ("finnair.com",),
    "AZ": ("ita-airways.com",),
    "BA": ("britishairways.com",),
    "CX": ("cathaypacific.com",),
    "DL": ("delta.com",),
    "EK": ("emirates.com",),
    "ET": ("ethiopianairlines.com",),
    "EY": ("etihad.com",),
    "FI": ("icelandair.com",),
    "IB": ("iberia.com",),
    "JL": ("jal.co.jp", "jal.com"),
    "JU": ("airserbia.com",),
    "KE": ("koreanair.com",),
    "KL": ("klm.com", "klm.us", "klm.nl"),
    "LH": ("lufthansa.com",),
    "LX": ("swiss.com",),
    "NH": ("ana.co.jp",),
    "NZ": ("airnewzealand.com", "airnewzealand.co.nz"),
    "OS": ("austrian.com",),
    "QF": ("qantas.com",),
    "QR": ("qatarairways.com",),
    "SN": ("brusselsairlines.com",),
    "SQ": ("singaporeair.com",),
    "TK": ("turkishairlines.com",),
    "TP": ("flytap.com",),
    "UA": ("united.com",),
    "VS": ("virginatlantic.com", "virgin-atlantic.com"),
    "AT": ("royalairmaroc.com",),
}


class AirlineLinkError(Exception):
    def __init__(self, message: str, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


def handoff_url(
    base: str,
    carrier: str,
    flight_number: str,
    origin: str,
    destination: str,
    on: date,
    cabin: str = "business",
    return_on: date | None = None,
    return_flight: str = "",
) -> str:
    """Address our own lookup. Duffel Airways has no public booking site."""
    code = (carrier or "").upper()
    if code == "ZZ" or not flight_number:
        return ""
    query_params = {
        "airline": code,
        "flight_number": re.sub(r"\s+", "", flight_number).upper(),
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": on.isoformat(),
        "cabin": "first" if cabin == "first" else "business",
    }
    if return_on:
        query_params["return_date"] = return_on.isoformat()
        if return_flight:
            query_params["return_flight"] = re.sub(r"\s+", "", return_flight).upper()
    query = urlencode(query_params)
    return f"{base.rstrip('/')}/api/flights/airline-link?{query}"


def pick_itinerary(payload: dict, flight_number: str, airline: str = "", *, token: str = "booking_token") -> dict | None:
    want = _norm_flight(flight_number)
    code = airline.upper()
    groups = list(payload.get("best_flights") or []) + list(payload.get("other_flights") or [])
    same_number: list[dict] = []
    same_airline: list[dict] = []
    for item in groups:
        if not item.get(token):
            continue
        numbers = [_norm_flight(str(leg.get("flight_number") or "")) for leg in item.get("flights") or []]
        if code and not any(number.startswith(code) for number in numbers):
            continue
        same_airline.append(item)
        if want and want in numbers:
            same_number.append(item)
    if same_number:
        return same_number[0]
    return None


def booking_cabin(ticket: dict) -> str | None:
    """Read the booking option's cabin, which can differ from the search cabin."""
    label = " ".join(str(ticket.get(k) or "") for k in ("travel_class", "option_title")).lower()
    if re.search(r"premium[\s_-]*economy", label):
        return "premium_economy"
    if re.search(r"\beconomy\b|\bmain cabin\b", label):
        return "economy"
    if re.search(r"\bbusiness\b|\bclub (world|europe)\b|\bupper class\b", label):
        return "business"
    if re.search(r"\bfirst\b", label):
        return "first"
    return None


def airline_booking_requests(options: list, target_price: float | None = None, *, required_cabin: str | None = None) -> list[dict]:
    """Carrier handoffs. Prefer the fare closest to the flight we showed."""
    found: list[tuple[float, dict]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        for ticket in _tickets(option):
            if not ticket.get("airline"):
                continue
            request = ticket.get("booking_request") or {}
            if not request.get("url"):
                continue
            if required_cabin:
                actual_cabin = booking_cabin(ticket)
                if actual_cabin is not None and actual_cabin != required_cabin:
                    continue
                request = {**request, "cabin_verified": actual_cabin == required_cabin}
            try:
                price = float(ticket.get("price"))
            except (TypeError, ValueError):
                price = 1e18
            found.append((price, request))

    def rank(price: float) -> tuple[float, float]:
        if target_price is None:
            return (price, price)
        return (abs(price - float(target_price)), price)

    found.sort(key=lambda item: rank(item[0]))
    return [request for _, request in found]


def pick_airline_booking(options: list) -> dict | None:
    requests = airline_booking_requests(options)
    return requests[0] if requests else None


_ECONOMY_MARKERS = (
    "cabin=economy",
    "cabin=eco",
    "cabin=y",
    "cabin=w",
    "cabin=m",
    "class=economy",
    "travelclass=economy",
    "travel_class=economy",
    "cabinclass=economy",
    "premium-economy",
    "premium_economy",
    "premiumeconomy",
    "/economy",
)


def page_matches_cabin(url: str, cabin: str, *, require_explicit: bool = False) -> bool:
    """True when the airline page is business or first, never economy."""
    # Airline metasearch links can specify each direction separately (cabin1,
    # cabin2). Never accept an explicitly downgraded fare from those links.
    aliases = {"eco": "economy", "economy": "economy", "y": "economy", "m": "economy", "w": "premium_economy", "premiumeconomy": "premium_economy", "business": "business", "club": "business", "c": "business", "j": "business", "first": "first", "f": "first"}
    confirmed = False
    for key, values in parse_qs(urlparse(url).query).items():
        if not re.fullmatch(r"cabin\d*|cabinclass|travelclass|travel_class", key.lower()):
            continue
        for value in values:
            actual = aliases.get(re.sub(r"[\s_-]", "", value.lower()))
            if actual and actual != cabin:
                return False
            if actual == cabin:
                confirmed = True
    if require_explicit and not confirmed:
        return False
    text = url.lower().replace("%20", "").replace("+", "")
    if any(marker in text for marker in _ECONOMY_MARKERS):
        return False
    if cabin == "first" and "business" in text and "first" not in text:
        return False
    return True


def host_is_airline(url: str, carrier: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host or _blocked(host):
        return False
    expected = _AIRLINE_HOSTS.get(carrier.upper())
    if not expected:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in expected)


async def resolve_airline_link(
    *,
    airline: str,
    flight_number: str,
    origin: str,
    destination: str,
    on: date,
    cabin: str = "business",
    return_on: date | None = None,
    return_flight: str = "",
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    code = airline.upper()
    if code == "ZZ":
        raise AirlineLinkError("Duffel Airways has no public booking site. Book in the app.")
    settings = settings or get_settings()
    if not settings.serpapi_api_key:
        raise AirlineLinkError("Airline lookup is not configured.", 503)

    cabin_name = "first" if cabin == "first" else "business"
    key = "|".join(
        [
            code,
            _norm_flight(flight_number),
            _norm_flight(return_flight),
            origin.upper(),
            destination.upper(),
            on.isoformat(),
            return_on.isoformat() if return_on else "",
            cabin_name,
        ]
    )
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0), follow_redirects=False)
    try:
        common = {
            "engine": "google_flights",
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": on.isoformat(),
            "type": "1" if return_on else "2",
            "travel_class": "4" if cabin_name == "first" else "3",
            "adults": "1",
            "currency": "USD",
            "hl": "en",
            "gl": "us",
        }
        if return_on:
            common["return_date"] = return_on.isoformat()
        search = await _serpapi(client, settings, common)
        if return_on:
            outbound = pick_itinerary(search, flight_number, code, token="departure_token")
            if not outbound:
                raise AirlineLinkError(f"Google Flights has no {code} round trip for these dates.")
            returns = await _serpapi(client, settings, {**common, "departure_token": outbound["departure_token"]})
            itinerary = pick_itinerary(returns, return_flight or flight_number, code)
        else:
            itinerary = pick_itinerary(search, flight_number, code)
        if not itinerary:
            raise AirlineLinkError(f"Google Flights has no {code} booking for this date.")
        options = await _serpapi(client, settings, {**common, "booking_token": itinerary["booking_token"]})
        requests = airline_booking_requests(options.get("booking_options") or [], itinerary.get("price"))
        if not requests:
            raise AirlineLinkError(f"{code} is not selling this flight on its own site.")
        final = ""
        saw_wrong_cabin = False
        for booking in requests[:6]:
            landed, status = await _follow_booking(client, booking["url"], booking.get("post_data") or "", code)
            if status == 404 or not host_is_airline(landed, code):
                continue
            if not page_matches_cabin(landed, cabin_name):
                saw_wrong_cabin = True
                continue
            final = landed
            break
        if not final:
            if saw_wrong_cabin:
                raise AirlineLinkError("The airline page was not business or first.")
            raise AirlineLinkError("The airline did not return a booking page.")
        _CACHE[key] = (time.time(), final)
        return final
    finally:
        if owns_client:
            await client.aclose()


async def _serpapi(client: httpx.AsyncClient, settings: Settings, params: dict) -> dict:
    query = dict(params)
    query["api_key"] = settings.serpapi_api_key
    response = await client.get(SERPAPI_URL, params=query)
    if response.status_code >= 400:
        raise AirlineLinkError("Google Flights lookup failed.", 502)
    payload = response.json()
    if payload.get("error"):
        raise AirlineLinkError(str(payload["error"]), 502)
    return payload


async def _follow_booking(client: httpx.AsyncClient, url: str, post_data: str, carrier: str) -> tuple[str, int]:
    headers = {"User-Agent": _BROWSER, "Accept": "text/html,application/xhtml+xml"}
    current = url
    method = "POST" if post_data else "GET"
    body: str | None = post_data or None
    status = 0
    for _ in range(8):
        target=urlparse(current)
        host=(target.hostname or "").lower()
        if target.scheme!="https" or not (host in {"google.com","www.google.com"} or host_is_airline(current,carrier)):
            return current,400
        if method == "POST":
            response = await client.post(
                current,
                content=body,
                headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            response = await client.get(current, headers=headers)
        status = response.status_code
        if status in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                break
            current = str(httpx.URL(current).join(location))
            method = "GET"
            body = None
            continue
        if status == 200 and not host_is_airline(current, carrier):
            landed = _airline_url_in_html(response.text, carrier)
            if landed:
                return landed, 200
        break
    return current, status


def _airline_url_in_html(page: str, carrier: str) -> str | None:
    text = html.unescape(page[:80_000])
    for match in re.finditer(r"https://[^\s\"'<>]+", text):
        candidate = match.group(0).rstrip(".,);")
        if host_is_airline(candidate, carrier):
            return candidate
    return None


def _tickets(option: dict) -> list[dict]:
    together = option.get("together") if isinstance(option.get("together"), dict) else None
    if together and together.get("booking_request"):
        return [together]
    tickets = []
    for key in ("departing", "returning"):
        ticket = option.get(key)
        if isinstance(ticket, dict) and ticket.get("booking_request"):
            tickets.append(ticket)
    return tickets


def _norm_flight(value: str) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def _blocked(host: str) -> bool:
    return any(part in host for part in _BLOCKED_HOSTS)
