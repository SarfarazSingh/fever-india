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

from app.airports import distance_km, local_to_utc, utc_to_local
from app.config import Settings, get_settings
from app.models import FlightSearch
from app.schemas import FlightOffer, FlightSearchResponse, FlightSegment
from app.services.airline_link import handoff_url

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
    bookable: bool = False,
    passenger_id: str | None = None,
    expires_at: datetime | None = None,
    refundable: bool | None = None,
    manage_url: str | None = None,
    cabin_class: str = BUSINESS_CABIN,
    return_segments: list[FlightSegment] | None = None,
) -> FlightOffer:
    return_segments = return_segments or []
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
        trip_type="round" if return_segments else "oneway",
        return_flight_number=return_segments[0].flight_number if return_segments else None,
        return_origin=return_segments[0].origin if return_segments else None,
        return_destination=return_segments[-1].destination if return_segments else None,
        return_departure_local=return_segments[0].departure_local if return_segments else None,
        return_arrival_local=return_segments[-1].arrival_local if return_segments else None,
        return_duration_minutes=(
            int((return_segments[-1].arrival_time - return_segments[0].departure_time).total_seconds() // 60)
            if return_segments
            else None
        ),
        return_layovers=max(0, len(return_segments) - 1),
        price=round(price, 2),
        currency=currency,
        cabin_class=cabin_class,
        deep_link=deep_link,
        segments=[*segments, *return_segments],
        provider=provider,
        bookable=bookable,
        passenger_id=passenger_id,
        expires_at=expires_at,
        refundable=refundable,
        manage_url=manage_url,
    )


# ---------------------------------------------------------------------------
# Duffel
# ---------------------------------------------------------------------------


class DuffelProvider:
    name = "duffel"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        from app.services.duffel import DuffelClient

        self._settings = settings
        self._duffel = DuffelClient(settings)

    async def search(
        self, origin: str, destination: str, on: date, *, cabin: str = "business", return_on: date | None = None
    ) -> list[FlightOffer]:
        from app.services.duffel import DuffelError

        self._cabin = "first" if cabin == "first" else "business"
        self._return_on = return_on
        try:
            payload = await self._duffel.search_offers(origin, destination, on, cabin=self._cabin, return_on=return_on)
        except DuffelError as exc:
            raise ProviderError(str(exc)) from exc

        data = payload.get("data") or {}
        offers: list[FlightOffer] = []
        for item in data.get("offers") or []:
            try:
                offers.append(self._parse_offer(item, on))
            except (KeyError, ValueError, IndexError, TypeError) as exc:
                logger.debug("Skipping malformed Duffel offer %s: %s", item.get("id"), exc)
        offers.sort(key=lambda o: o.price)
        return offers[:25]

    def _parse_offer(self, item: dict, on: date) -> FlightOffer:
        from app.services.duffel import parse_duffel_datetime

        owner = item.get("owner") or {}
        carrier = (owner.get("iata_code") or "").upper()
        if owner.get("name"):
            AIRLINE_NAMES.setdefault(carrier, owner["name"])

        slice_groups: list[list[FlightSegment]] = []
        for slc in item.get("slices") or []:
            grouped: list[FlightSegment] = []
            for seg in slc.get("segments") or []:
                origin_code = (seg["origin"]["iata_code"] if isinstance(seg.get("origin"), dict) else seg["origin"]).upper()
                dest_code = (
                    seg["destination"]["iata_code"] if isinstance(seg.get("destination"), dict) else seg["destination"]
                ).upper()
                marketing = seg.get("marketing_carrier") or {}
                seg_carrier = (marketing.get("iata_code") or carrier).upper()
                if marketing.get("name"):
                    AIRLINE_NAMES.setdefault(seg_carrier, marketing["name"])
                number = str(seg.get("marketing_carrier_flight_number") or seg.get("operating_carrier_flight_number") or "")
                aircraft = (seg.get("aircraft") or {}).get("name") if isinstance(seg.get("aircraft"), dict) else None
                dep_raw = parse_duffel_datetime(seg["departing_at"])
                arr_raw = parse_duffel_datetime(seg["arriving_at"])
                if dep_raw.tzinfo is None:
                    dep_utc, dep_local = local_to_utc(origin_code, dep_raw), dep_raw.replace(tzinfo=None)
                else:
                    dep_utc, dep_local = dep_raw.astimezone(timezone.utc), utc_to_local(origin_code, dep_raw)
                if arr_raw.tzinfo is None:
                    arr_utc, arr_local = local_to_utc(dest_code, arr_raw), arr_raw.replace(tzinfo=None)
                else:
                    arr_utc, arr_local = arr_raw.astimezone(timezone.utc), utc_to_local(dest_code, arr_raw)
                grouped.append(
                    FlightSegment(
                        airline_iata=seg_carrier,
                        airline_name=airline_name(seg_carrier),
                        flight_number=f"{seg_carrier}{number}".replace(" ", ""),
                        origin=origin_code,
                        destination=dest_code,
                        departure_time=dep_utc,
                        arrival_time=arr_utc,
                        departure_local=dep_local,
                        arrival_local=arr_local,
                        aircraft=aircraft,
                    )
                )
            if grouped:
                slice_groups.append(grouped)
        if not slice_groups:
            raise ValueError("offer has no segments")
        segments = slice_groups[0]
        return_segments = slice_groups[1] if len(slice_groups) > 1 else []

        passengers = item.get("passengers") or []
        passenger_id = passengers[0].get("id") if passengers and isinstance(passengers[0], dict) else None
        expires = item.get("expires_at")
        refund = ((item.get("conditions") or {}).get("refund_before_departure") or {}).get("allowed")
        code = "F" if getattr(self, "_cabin", "business") == "first" else BUSINESS_CABIN
        return _build_offer(
            offer_id=item["id"],
            segments=segments,
            price=float(item["total_amount"]),
            currency=item.get("total_currency") or self._settings.default_currency,
            deep_link=airline_deep_link(
                carrier or segments[0].airline_iata,
                segments[0].origin,
                segments[-1].destination,
                segments[0].departure_local.date(),
                cabin=getattr(self, "_cabin", "business"),
                flight_number=segments[0].flight_number,
                return_on=return_segments[0].departure_local.date() if return_segments else None,
                return_flight=return_segments[0].flight_number if return_segments else "",
            ),
            provider=self.name,
            validating_carrier=carrier or None,
            bookable=True,
            passenger_id=passenger_id,
            expires_at=parse_duffel_datetime(expires) if expires else None,
            refundable=bool(refund) if refund is not None else None,
            cabin_class=code,
            return_segments=return_segments,
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
            deep_link=airline_deep_link(
                validating,
                segments[0].origin,
                segments[-1].destination,
                on,
                flight_number=segments[0].flight_number,
            ),
            provider=self.name,
            validating_carrier=validating,
        )


def airline_deep_link(
    carrier: str,
    origin: str,
    destination: str,
    on: date,
    cabin: str = "business",
    flight_number: str = "",
    return_on: date | None = None,
    return_flight: str = "",
) -> str:
    """Our lookup address. The click resolves it to the airline's own page."""
    return handoff_url(
        get_settings().public_base_url,
        carrier,
        flight_number,
        origin,
        destination,
        on,
        cabin,
        return_on=return_on,
        return_flight=return_flight,
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


def _block_hours(km: float) -> float:
    """Typical gate-to-gate time for a widebody at ~830 km/h plus taxi/climb."""
    return km / 830 + 0.6


class MockProvider:
    """Deterministic, realistic Business Class offers for offline development."""

    name = "mock"

    def __init__(self, settings: Settings):
        self._settings = settings

    async def search(
        self, origin: str, destination: str, on: date, *, cabin: str = "business", return_on: date | None = None
    ) -> list[FlightOffer]:
        seed = int(hashlib.sha256(f"{origin}{destination}{on.isoformat()}".encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        direct_km = distance_km(origin, destination) or rng.uniform(5000, 11000)
        base_price = 1500 + direct_km * 0.42 * rng.uniform(0.9, 1.15)

        # Hub carriers fly nonstop; others connect through their hub when the
        # detour is plausible and the hub isn't in the same metro area.
        routes: list[tuple[tuple[str, str, int, float], bool]] = [
            (c, True) for c in _MOCK_CARRIERS if c[1] in (origin, destination)
        ]
        connecting = []
        for carrier in _MOCK_CARRIERS:
            hub = carrier[1]
            if hub in (origin, destination):
                continue
            d1, d2 = distance_km(origin, hub), distance_km(hub, destination)
            if d1 is None or d2 is None or min(d1, d2) < 250 or (d1 + d2) / direct_km > 1.25:
                continue
            connecting.append(carrier)
        rng.shuffle(connecting)
        routes += [(c, False) for c in connecting[: max(0, 7 - len(routes))]]
        if len(routes) < 3:
            # Thin route: add partner-operated nonstops so the demo always has choice.
            spare = [c for c in _MOCK_CARRIERS if all(c != r[0] for r in routes)]
            routes += [(c, True) for c in rng.sample(spare, k=3 - len(routes))]

        offers: list[FlightOffer] = []
        for idx, ((code, hub, fn_base, multiplier), nonstop) in enumerate(routes):
            dep_local = datetime.combine(on, datetime.min.time()) + timedelta(
                hours=rng.choice([7, 9, 11, 13, 16, 18, 20, 22]), minutes=rng.choice([0, 10, 25, 40, 55])
            )
            dep_utc = local_to_utc(origin, dep_local)
            flight_no = f"{code}{fn_base + rng.randint(0, 98)}"

            if nonstop:
                arr_utc = dep_utc + timedelta(hours=_block_hours(direct_km), minutes=rng.randint(-15, 20))
                segments = [self._segment(code, flight_no, origin, destination, dep_utc, arr_utc)]
                price = base_price * multiplier * 1.12
            else:
                hub_arr = dep_utc + timedelta(hours=_block_hours(distance_km(origin, hub)))
                hub_dep = hub_arr + timedelta(hours=rng.uniform(1.25, 3.5))
                arr_utc = hub_dep + timedelta(hours=_block_hours(distance_km(hub, destination)))
                second_no = f"{code}{fn_base + rng.randint(100, 199)}"
                segments = [
                    self._segment(code, flight_no, origin, hub, dep_utc, hub_arr),
                    self._segment(code, second_no, hub, destination, hub_dep, arr_utc),
                ]
                price = base_price * multiplier * 0.92

            price += rng.uniform(-120, 120)
            inbound: list[FlightSegment] = []
            if return_on:
                ret_no = f"{code}{fn_base + 300 + idx}"
                ret_dep_local = datetime.combine(return_on, datetime.min.time()) + timedelta(hours=11, minutes=20)
                ret_dep = local_to_utc(destination, ret_dep_local)
                ret_arr = ret_dep + timedelta(hours=_block_hours(direct_km))
                inbound = [self._segment(code, ret_no, destination, origin, ret_dep, ret_arr)]
                price = round(price * 1.7, 2)
            offer_id = f"mock-{code}-{origin}{destination}-{on.strftime('%Y%m%d')}-{idx}"
            offers.append(
                _build_offer(
                    offer_id=offer_id,
                    segments=segments,
                    return_segments=inbound,
                    price=price,
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


class MissingProviderError(RuntimeError):
    pass


def select_provider(settings: Settings, client: httpx.AsyncClient) -> FlightProvider:
    choice = settings.flight_provider
    if choice == "mock":
        return MockProvider(settings)
    if choice == "duffel" or (choice == "auto" and settings.duffel_enabled):
        if not settings.duffel_enabled:
            raise MissingProviderError("FLIGHT_PROVIDER=duffel but DUFFEL_ACCESS_TOKEN is empty")
        return DuffelProvider(settings, client)
    if choice == "tequila" or (choice == "auto" and settings.tequila_api_key):
        if not settings.tequila_api_key:
            raise MissingProviderError("FLIGHT_PROVIDER=tequila but TEQUILA_API_KEY is empty")
        return TequilaProvider(settings, client)
    if choice == "amadeus" or (choice == "auto" and settings.amadeus_client_id and settings.amadeus_client_secret):
        if not (settings.amadeus_client_id and settings.amadeus_client_secret):
            raise MissingProviderError("FLIGHT_PROVIDER=amadeus but Amadeus credentials are empty")
        return AmadeusProvider(settings, client)
    if choice == "auto":
        raise MissingProviderError(
            "No flight API is configured. Set DUFFEL_ACCESS_TOKEN in backend/.env "
            "(or FLIGHT_PROVIDER=mock for offline demo data)."
        )
    return MockProvider(settings)


_RECOMMENDATION_LIMIT = 3


def _cabin_word(cabin: str) -> str:
    if cabin == "first":
        return "first"
    if cabin == "either":
        return "business or first"
    return "business"


def _cabin_ok(offer: FlightOffer, cabin: str) -> bool:
    code = (offer.cabin_class or "").upper()
    if cabin == "first":
        return code in {"F", "FIRST"}
    if cabin == "either":
        return code in {"C", "F", "BUSINESS", "FIRST"}
    return code in {"C", "BUSINESS"}


def _airline_ok(offer: FlightOffer, wanted: set[str]) -> bool:
    if not wanted:
        return True
    if offer.airline_iata in wanted:
        return True
    return any(segment.airline_iata in wanted for segment in offer.segments)


def _aircraft_ok(offer: FlightOffer, plane: str) -> bool:
    if not plane:
        return True
    names = " ".join((segment.aircraft or "") for segment in offer.segments).upper()
    return plane in names or any(part in names for part in plane.split())


def _time_ok(offer: FlightOffer, depart_after: int, depart_before: int) -> bool:
    hour = offer.departure_local.hour
    return depart_after <= hour < depart_before


def _nonstop(offer: FlightOffer) -> bool:
    return offer.layovers == 0 and offer.return_layovers == 0


def _airline_rank(offer: FlightOffer, wanted: list[str]) -> int:
    if not wanted:
        return 0
    if offer.airline_iata in wanted:
        return wanted.index(offer.airline_iata)
    for segment in offer.segments:
        if segment.airline_iata in wanted:
            return wanted.index(segment.airline_iata)
    return len(wanted)


def _and(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def recommend_offers(
    offers: list[FlightOffer],
    *,
    cabin: str = "business",
    airlines: str = "",
    aircraft: str = "",
    depart_after: int = 0,
    depart_before: int = 24,
    flexible_only: bool = False,
) -> tuple[list[FlightOffer], str]:
    """Keep flights that match every saved rule, then the best three nonstops."""
    wanted_list = [code.strip().upper() for code in airlines.split(",") if code.strip()]
    wanted = set(wanted_list)
    plane = aircraft.strip().upper()
    cabin_name = _cabin_word(cabin)
    if not offers:
        return [], f"No {cabin_name} flights on this route for those dates."

    steps: list[tuple[str, object]] = [
        ("cabin", lambda offer: _cabin_ok(offer, cabin), f"No {cabin_name} flights on this route for those dates."),
    ]
    if wanted_list:
        listed = ", ".join(wanted_list)
        steps.append(("airlines", lambda offer: _airline_ok(offer, wanted), f"No {cabin_name} flights on {listed}."))
    if plane:
        steps.append(("aircraft", lambda offer: _aircraft_ok(offer, plane), f"No {cabin_name} flights on {plane}."))
    if depart_after > 0 or depart_before < 24:
        window = f"{depart_after:02d}:00 and {depart_before:02d}:00"
        steps.append(
            (
                "time",
                lambda offer: _time_ok(offer, depart_after, depart_before),
                f"Nothing in {cabin_name} departs between {window}.",
            )
        )
    if flexible_only:
        steps.append(
            ("flexible", lambda offer: offer.refundable is not False, f"No flexible {cabin_name} fares match.")
        )

    current = list(offers)
    for _name, keep, empty_note in steps:
        nxt = [offer for offer in current if keep(offer)]
        if current and not nxt:
            return [], empty_note
        current = nxt

    nonstops = [offer for offer in current if _nonstop(offer)]
    pool = nonstops or current
    pool.sort(key=lambda offer: (_airline_rank(offer, wanted_list), offer.price))
    chosen = pool[:_RECOMMENDATION_LIMIT]

    count_word = {1: "One", 2: "Two", 3: "Three"}.get(len(chosen), str(len(chosen)))
    noun = "flight" if len(chosen) == 1 else "flights"
    matched: list[str] = []
    if wanted_list:
        matched.append("your airlines")
    if depart_after > 0 or depart_before < 24:
        matched.append("your times")
    if plane:
        matched.append("your aircraft")
    if flexible_only:
        matched.append("flexible fares")
    match = f" that match {_and(matched)}" if matched else ""
    if nonstops:
        note = f"{count_word} nonstop {cabin_name} {noun}{match}. Aisle requested."
    else:
        note = f"No nonstop matched. {count_word} {cabin_name} {noun} with a connection{match}. Aisle requested."
    return chosen, note


def apply_preferences(
    offers: list[FlightOffer],
    *,
    cabin: str = "business",
    direct_only: bool = False,
    airlines: str = "",
    aircraft: str = "",
    depart_after: int = 0,
    depart_before: int = 24,
    flexible_only: bool = False,
) -> list[FlightOffer]:
    del direct_only
    chosen, _note = recommend_offers(
        offers,
        cabin=cabin,
        airlines=airlines,
        aircraft=aircraft,
        depart_after=depart_after,
        depart_before=depart_before,
        flexible_only=flexible_only,
    )
    return chosen


async def search_business_flights(
    origin: str,
    destination: str,
    on: date,
    session: AsyncSession | None = None,
    settings: Settings | None = None,
    *,
    cabin: str = "business",
    direct_only: bool = False,
    airlines: str = "",
    aircraft: str = "",
    depart_after: int = 0,
    depart_before: int = 24,
    flexible_only: bool = False,
    return_on: date | None = None,
) -> FlightSearchResponse:
    settings = settings or get_settings()
    origin, destination = normalize_iata(origin), normalize_iata(destination)
    if origin == destination:
        raise ValueError("origin and destination must differ")
    if return_on is not None and return_on <= on:
        raise ValueError("return date must be after the departure date")

    cabins = ["business", "first"] if cabin == "either" else [cabin if cabin in {"business", "first"} else "business"]
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
        provider = select_provider(settings, client)
        offers: list[FlightOffer] = []
        seen: set[str] = set()
        for one in cabins:
            try:
                batch = await provider.search(origin, destination, on, cabin=one, return_on=return_on)
            except TypeError:
                if return_on:
                    raise ProviderError("This search provider cannot price a round trip.")
                batch = await provider.search(origin, destination, on)
            for offer in batch:
                if offer.id not in seen:
                    seen.add(offer.id)
                    offers.append(offer)

    offers, note = recommend_offers(
        offers,
        cabin=cabin,
        airlines=airlines,
        aircraft=aircraft,
        depart_after=depart_after,
        depart_before=depart_before,
        flexible_only=flexible_only,
    )
    del direct_only

    if session is not None:
        session.add(
            FlightSearch(
                origin=origin,
                destination=destination,
                departure_date=on,
                cabin_class=cabin if cabin in {"C", "F"} else ("F" if cabin == "first" else BUSINESS_CABIN),
                provider=provider.name,
                result_count=len(offers),
            )
        )
        await session.commit()

    return FlightSearchResponse(
        origin=origin,
        destination=destination,
        date=on,
        return_date=return_on,
        cabin_class=BUSINESS_CABIN,
        provider=provider.name,
        count=len(offers),
        note=note,
        results=offers,
    )


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
