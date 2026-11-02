"""Business Class flight search across pluggable metasearch providers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Protocol
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.airports import local_to_utc, utc_to_local
from app.config import Settings, get_settings
from app.models import FlightSearch
from app.schemas import FlightOffer, FlightSearchResponse, FlightSegment

logger = logging.getLogger(__name__)

BUSINESS_CABIN = "C"

AIRLINE_NAMES: dict[str, str] = {
    "AA": "American Airlines",
    "AC": "Air Canada",
    "AF": "Air France",
    "AI": "Air India",
    "AS": "Alaska Airlines",
    "AY": "Finnair",
    "AZ": "ITA Airways",
    "BA": "British Airways",
    "CX": "Cathay Pacific",
    "DL": "Delta Air Lines",
    "EK": "Emirates",
    "ET": "Ethiopian Airlines",
    "EY": "Etihad Airways",
    "IB": "Iberia",
    "JL": "Japan Airlines",
    "KE": "Korean Air",
    "KL": "KLM Royal Dutch Airlines",
    "LH": "Lufthansa",
    "LX": "SWISS",
    "NH": "ANA All Nippon Airways",
    "NZ": "Air New Zealand",
    "OS": "Austrian Airlines",
    "QF": "Qantas",
    "QR": "Qatar Airways",
    "SQ": "Singapore Airlines",
    "TK": "Turkish Airlines",
    "UA": "United Airlines",
    "VS": "Virgin Atlantic",
}

AIRLINE_BOOKING_SITES: dict[str, str] = {
    "AA": "https://www.aa.com/booking/find-flights",
    "AF": "https://wwws.airfrance.us/search/offers",
    "BA": "https://www.britishairways.com/travel/book/public/en_us",
    "CX": "https://www.cathaypacific.com/cx/en_US/book-a-trip.html",
    "DL": "https://www.delta.com/flight-search/book-a-flight",
    "EK": "https://www.emirates.com/us/english/book/",
    "KL": "https://www.klm.us/search/offers",
    "LH": "https://www.lufthansa.com/us/en/flight-search",
    "QR": "https://www.qatarairways.com/en-us/book.html",
    "SQ": "https://www.singaporeair.com/en_UK/us/plan-travel/book-flight/",
    "TK": "https://www.turkishairlines.com/en-us/flights/booking/",
    "UA": "https://www.united.com/en/us/fsr/choose-flights",
}


def airline_name(code: str) -> str:
    return AIRLINE_NAMES.get(code.upper(), code.upper())


class ProviderError(RuntimeError):
    pass


class FlightProvider(Protocol):
    name: str

    async def search(self, origin: str, destination: str, on: date) -> list[FlightOffer]: ...


def _build_offer(
    *,
    offer_id: str,
    segments: list[FlightSegment],
    price: float,
    currency: str,
    deep_link: str,
    provider: str,
    validating_carrier: str | None = None,
) -> FlightOffer:
    first, last = segments[0], segments[-1]
    carrier = (validating_carrier or first.airline_iata).upper()
    marketing_segment = next((s for s in segments if s.airline_iata == carrier), first)
    duration = int((last.arrival_time - first.departure_time).total_seconds() // 60)
    return FlightOffer(
        id=offer_id,
        airline_name=airline_name(carrier),
        airline_iata=carrier,
        flight_number=marketing_segment.flight_number,
        origin=first.origin,
        destination=last.destination,
        departure_time=first.departure_time,
        arrival_time=last.arrival_time,
        departure_local=first.departure_local,
        arrival_local=last.arrival_local,
        duration_minutes=duration,
        layovers=len(segments) - 1,
        layover_airports=[s.destination for s in segments[:-1]],
        price=round(price, 2),
        currency=currency,
        cabin_class=BUSINESS_CABIN,
        deep_link=deep_link,
        segments=segments,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# Kiwi.com Tequila
# ---------------------------------------------------------------------------


class TequilaProvider:
    name = "tequila"

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client

    async def search(self, origin: str, destination: str, on: date) -> list[FlightOffer]:
        day = on.strftime("%d/%m/%Y")
        params = {
            "fly_from": origin,
            "fly_to": destination,
            "date_from": day,
            "date_to": day,
            "selected_cabins": BUSINESS_CABIN,
            "adults": 1,
            "curr": self._settings.default_currency,
            "max_stopovers": 2,
            "sort": "price",
            "limit": 30,
        }
        try:
            resp = await self._client.get(
                f"{self._settings.tequila_base_url}/v2/search",
                params=params,
                headers={"apikey": self._settings.tequila_api_key, "accept": "application/json"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Tequila request failed: {exc}") from exc

        body = resp.json()
        currency = body.get("currency", self._settings.default_currency)
        offers: list[FlightOffer] = []
        for item in body.get("data", []):
            try:
                offers.append(self._parse_itinerary(item, currency))
            except (KeyError, ValueError, IndexError) as exc:
                logger.debug("Skipping malformed Tequila itinerary %s: %s", item.get("id"), exc)
        return offers

    def _parse_itinerary(self, item: dict, currency: str) -> FlightOffer:
        segments: list[FlightSegment] = []
        for leg in item["route"]:
            if leg.get("return", 0):
                continue
            carrier = leg["airline"]
            dep_utc = _parse_iso(leg["utc_departure"])
            arr_utc = _parse_iso(leg["utc_arrival"])
            segments.append(
                FlightSegment(
                    airline_iata=carrier,
                    airline_name=airline_name(carrier),
                    flight_number=f"{carrier}{leg['flight_no']}",
                    origin=leg["flyFrom"],
                    destination=leg["flyTo"],
                    departure_time=dep_utc,
                    arrival_time=arr_utc,
                    departure_local=_parse_iso(leg["local_departure"]).replace(tzinfo=None),
                    arrival_local=_parse_iso(leg["local_arrival"]).replace(tzinfo=None),
                )
            )
        if not segments:
            raise ValueError("itinerary has no outbound segments")
        airlines = item.get("airlines") or [segments[0].airline_iata]
        return _build_offer(
            offer_id=f"tq-{item['id']}",
            segments=segments,
            price=float(item["price"]),
            currency=currency,
            deep_link=item["deep_link"],
            provider=self.name,
            validating_carrier=airlines[0],
        )


# ---------------------------------------------------------------------------
# Amadeus Self-Service
# ---------------------------------------------------------------------------


class AmadeusProvider:
    name = "amadeus"
    _token: str | None = None
    _token_expiry: float = 0.0
    _token_lock = asyncio.Lock()

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client

    async def _access_token(self) -> str:
        cls = type(self)
        async with cls._token_lock:
            if cls._token and time.monotonic() < cls._token_expiry - 60:
                return cls._token
            try:
                resp = await self._client.post(
                    f"{self._settings.amadeus_base_url}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._settings.amadeus_client_id,
                        "client_secret": self._settings.amadeus_client_secret,
                    },
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(f"Amadeus auth failed: {exc}") from exc
            payload = resp.json()
            cls._token = payload["access_token"]
            cls._token_expiry = time.monotonic() + float(payload.get("expires_in", 1799))
            return cls._token

    async def search(self, origin: str, destination: str, on: date) -> list[FlightOffer]:
        token = await self._access_token()
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": on.isoformat(),
            "adults": 1,
            "travelClass": "BUSINESS",
            "currencyCode": self._settings.default_currency,
            "max": 30,
        }
        try:
            resp = await self._client.get(
                f"{self._settings.amadeus_base_url}/v2/shopping/flight-offers",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Amadeus search failed: {exc}") from exc

        body = resp.json()
        carriers = body.get("dictionaries", {}).get("carriers", {})
        for code, name in carriers.items():
            AIRLINE_NAMES.setdefault(code, name.title())
        offers: list[FlightOffer] = []
        for item in body.get("data", []):
            try:
                offers.append(self._parse_offer(item, on))
            except (KeyError, ValueError, IndexError) as exc:
                logger.debug("Skipping malformed Amadeus offer %s: %s", item.get("id"), exc)
        return offers

    def _parse_offer(self, item: dict, on: date) -> FlightOffer:
        itinerary = item["itineraries"][0]
        segments: list[FlightSegment] = []
        for seg in itinerary["segments"]:
            carrier = seg["carrierCode"]
            dep_code = seg["departure"]["iataCode"]
            arr_code = seg["arrival"]["iataCode"]
            dep_local = datetime.fromisoformat(seg["departure"]["at"])
            arr_local = datetime.fromisoformat(seg["arrival"]["at"])
            segments.append(
                FlightSegment(
                    airline_iata=carrier,
                    airline_name=airline_name(carrier),
                    flight_number=f"{carrier}{seg['number']}",
                    origin=dep_code,
                    destination=arr_code,
                    departure_time=local_to_utc(dep_code, dep_local),
                    arrival_time=local_to_utc(arr_code, arr_local),
                    departure_local=dep_local,
                    arrival_local=arr_local,
                )
            )
        validating = (item.get("validatingAirlineCodes") or [segments[0].airline_iata])[0]
        price = item["price"]
        return _build_offer(
            offer_id=f"am-{item['id']}",
            segments=segments,
            price=float(price["grandTotal"]),
            currency=price.get("currency", self._settings.default_currency),
            deep_link=airline_deep_link(validating, segments[0].origin, segments[-1].destination, on),
            provider=self.name,
            validating_carrier=validating,
        )


def airline_deep_link(carrier: str, origin: str, destination: str, on: date) -> str:
    """Prefilled search URL on the carrier's own site (Amadeus has no deep links)."""
    base = AIRLINE_BOOKING_SITES.get(carrier.upper())
    query = urlencode(
        {"origin": origin, "destination": destination, "departureDate": on.isoformat(), "cabin": "business", "adults": 1}
    )
    if base:
        return f"{base}?{query}"
    return "https://www.google.com/travel/flights?" + urlencode(
        {"q": f"business class {carrier} {origin} to {destination} {on.isoformat()}"}
    )


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

# carrier -> (hub, flight number base, price multiplier)
_MOCK_CARRIERS: list[tuple[str, str, int, float]] = [
    ("QR", "DOH", 700, 1.05),
    ("EK", "DXB", 200, 1.10),
    ("SQ", "SIN", 20, 1.25),
    ("LH", "FRA", 400, 0.95),
    ("BA", "LHR", 100, 1.00),
    ("DL", "ATL", 1, 0.90),
    ("UA", "EWR", 900, 0.88),
    ("TK", "IST", 1, 0.80),
    ("AF", "CDG", 10, 0.97),
    ("CX", "HKG", 800, 1.15),
]


class MockProvider:
    """Deterministic, realistic Business Class offers for offline development."""

    name = "mock"

    def __init__(self, settings: Settings):
        self._settings = settings

    async def search(self, origin: str, destination: str, on: date) -> list[FlightOffer]:
        seed = int(hashlib.sha256(f"{origin}{destination}{on.isoformat()}".encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        base_hours = rng.uniform(6.5, 14.5)
        base_price = 1800 + base_hours * rng.uniform(220, 340)

        hub_carriers = [c for c in _MOCK_CARRIERS if c[1] in (origin, destination)]
        others = [c for c in _MOCK_CARRIERS if c not in hub_carriers]
        carriers = hub_carriers + rng.sample(others, k=max(0, 7 - len(hub_carriers)))
        offers: list[FlightOffer] = []
        for idx, (code, hub, fn_base, multiplier) in enumerate(carriers):
            nonstop = hub in (origin, destination)
            dep_local = datetime.combine(on, datetime.min.time()) + timedelta(
                hours=rng.choice([7, 9, 11, 13, 16, 18, 20, 22]), minutes=rng.choice([0, 10, 25, 40, 55])
            )
            dep_utc = local_to_utc(origin, dep_local)
            flight_no = f"{code}{fn_base + rng.randint(0, 98)}"

            if nonstop:
                arr_utc = dep_utc + timedelta(hours=base_hours, minutes=rng.randint(-25, 25))
                segments = [self._segment(code, flight_no, origin, destination, dep_utc, arr_utc)]
                price = base_price * multiplier * 1.12
            else:
                leg1 = base_hours * rng.uniform(0.35, 0.6)
                leg2 = base_hours * 1.08 - leg1
                hub_arr = dep_utc + timedelta(hours=leg1)
                hub_dep = hub_arr + timedelta(hours=rng.uniform(1.25, 4.0))
                arr_utc = hub_dep + timedelta(hours=leg2)
                second_no = f"{code}{fn_base + rng.randint(100, 199)}"
                segments = [
                    self._segment(code, flight_no, origin, hub, dep_utc, hub_arr),
                    self._segment(code, second_no, hub, destination, hub_dep, arr_utc),
                ]
                price = base_price * multiplier * 0.92

            offer_id = f"mock-{code}-{origin}{destination}-{on.strftime('%Y%m%d')}-{idx}"
            offers.append(
                _build_offer(
                    offer_id=offer_id,
                    segments=segments,
                    price=price + rng.uniform(-120, 120),
                    currency=self._settings.default_currency,
                    deep_link=self._demo_checkout_link(code, flight_no, origin, destination, on, price),
                    provider=self.name,
                    validating_carrier=code,
                )
            )
        offers.sort(key=lambda o: o.price)
        return offers

    @staticmethod
    def _segment(code: str, number: str, origin: str, dest: str, dep: datetime, arr: datetime) -> FlightSegment:
        dep = dep.replace(second=0, microsecond=0)
        arr = (arr + timedelta(minutes=(5 - arr.minute % 5) % 5)).replace(second=0, microsecond=0)
        return FlightSegment(
            airline_iata=code,
            airline_name=airline_name(code),
            flight_number=number,
            origin=origin,
            destination=dest,
            departure_time=dep,
            arrival_time=arr,
            departure_local=utc_to_local(origin, dep),
            arrival_local=utc_to_local(dest, arr),
        )

    def _demo_checkout_link(
        self, carrier: str, flight_no: str, origin: str, dest: str, on: date, price: float
    ) -> str:
        query = urlencode(
            {
                "carrier": carrier,
                "flight": flight_no,
                "origin": origin,
                "destination": dest,
                "date": on.isoformat(),
                "price": f"{price:.0f}",
                "currency": self._settings.default_currency,
                "airline_url": airline_deep_link(carrier, origin, dest, on),
            }
        )
        return f"{self._settings.public_base_url}/demo/checkout?{query}"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_IATA_RE = re.compile(r"^[A-Z]{3}$")


def normalize_iata(code: str) -> str:
    code = code.strip().upper()
    if not _IATA_RE.match(code):
        raise ValueError(f"'{code}' is not a valid 3-letter IATA airport code")
    return code


def select_provider(settings: Settings, client: httpx.AsyncClient) -> FlightProvider:
    choice = settings.flight_provider
    if choice == "tequila" or (choice == "auto" and settings.tequila_api_key):
        if not settings.tequila_api_key:
            logger.warning("FLIGHT_PROVIDER=tequila but TEQUILA_API_KEY is empty; using mock data")
            return MockProvider(settings)
        return TequilaProvider(settings, client)
    if choice == "amadeus" or (choice == "auto" and settings.amadeus_client_id and settings.amadeus_client_secret):
        if not (settings.amadeus_client_id and settings.amadeus_client_secret):
            logger.warning("FLIGHT_PROVIDER=amadeus but Amadeus credentials are empty; using mock data")
            return MockProvider(settings)
        return AmadeusProvider(settings, client)
    return MockProvider(settings)


async def search_business_flights(
    origin: str,
    destination: str,
    on: date,
    session: AsyncSession | None = None,
    settings: Settings | None = None,
) -> FlightSearchResponse:
    settings = settings or get_settings()
    origin, destination = normalize_iata(origin), normalize_iata(destination)
    if origin == destination:
        raise ValueError("origin and destination must differ")

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
        provider = select_provider(settings, client)
        try:
            offers = await provider.search(origin, destination, on)
        except ProviderError as exc:
            logger.warning("%s provider failed (%s); falling back to mock data", provider.name, exc)
            provider = MockProvider(settings)
            offers = await provider.search(origin, destination, on)

    offers = [o for o in offers if o.cabin_class == BUSINESS_CABIN]

    if session is not None:
        session.add(
            FlightSearch(
                origin=origin,
                destination=destination,
                departure_date=on,
                cabin_class=BUSINESS_CABIN,
                provider=provider.name,
                result_count=len(offers),
            )
        )
        await session.commit()

    return FlightSearchResponse(
        origin=origin,
        destination=destination,
        date=on,
        cabin_class=BUSINESS_CABIN,
        provider=provider.name,
        count=len(offers),
        results=offers,
    )


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
