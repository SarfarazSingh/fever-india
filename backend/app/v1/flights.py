"""Provider normalization and deterministic, explainable recommendation rules."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.airports import AIRPORTS, airport_tz
from app.config import get_settings
from app.models import utcnow
from app.services.duffel import DuffelClient, DuffelError
from app.services.flight_search import MockProvider, airline_name
from app.v1.schemas import (
    Condition,
    FareOption,
    Offer,
    Profile,
    SearchRequest,
    Segment,
    Slice,
)


def _condition(raw) -> Condition:
    raw = raw or {}
    return Condition(
        allowed=raw.get("allowed"),
        penalty_amount=raw.get("penalty_amount"),
        penalty_currency=raw.get("penalty_currency"),
    )


def _airport(value: dict) -> tuple[str, str, str]:
    code = value["iata_code"]
    tz = value.get("time_zone") or (str(airport_tz(code)) if airport_tz(code) else None)
    if not tz:
        raise ValueError(f"No verified timezone for airport {code}")
    ZoneInfo(tz)  # Do not guess UTC for an unrecognized airport.
    return (
        code,
        value.get("city_name")
        or (value.get("city") or {}).get("name")
        or value.get("name")
        or code,
        tz,
    )


def normalize_offer(raw: dict) -> Offer:
    slices = []
    for i, slc in enumerate(raw["slices"]):
        segments = []
        for j, seg in enumerate(slc["segments"]):
            origin, city, origin_tz = _airport(seg["origin"])
            dest, dest_city, dest_tz = _airport(seg["destination"])
            dep = datetime.fromisoformat(seg["departing_at"].replace("Z", "+00:00"))
            arr = datetime.fromisoformat(seg["arriving_at"].replace("Z", "+00:00"))
            dep = dep.replace(tzinfo=ZoneInfo(origin_tz)) if dep.tzinfo is None else dep
            arr = arr.replace(tzinfo=ZoneInfo(dest_tz)) if arr.tzinfo is None else arr
            pax = (seg.get("passengers") or [{}])[0]
            cabin = pax.get("cabin") or {}
            seat = (cabin.get("amenities") or {}).get("seat") or {}
            bags = {x["type"]: x.get("quantity") for x in pax.get("baggages") or []}
            marketing, operating = (
                seg.get("marketing_carrier") or {},
                seg.get("operating_carrier") or {},
            )
            carrier = (
                marketing.get("iata_code")
                or (raw.get("owner") or {}).get("iata_code")
                or ""
            )
            plane = seg.get("aircraft") or {}
            segments.append(
                Segment(
                    id=seg.get("id") or f"{slc.get('id', i)}-{j}",
                    origin=origin,
                    destination=dest,
                    origin_city=city,
                    destination_city=dest_city,
                    origin_timezone=origin_tz,
                    destination_timezone=dest_tz,
                    departure_at=dep.astimezone(timezone.utc),
                    arrival_at=arr.astimezone(timezone.utc),
                    departure_local=dep.astimezone(ZoneInfo(origin_tz)).isoformat(),
                    arrival_local=arr.astimezone(ZoneInfo(dest_tz)).isoformat(),
                    airline=carrier,
                    airline_name=marketing.get("name") or airline_name(carrier),
                    operating_airline=operating.get("iata_code"),
                    operating_airline_name=operating.get("name"),
                    flight_number=carrier
                    + str(seg.get("marketing_carrier_flight_number") or ""),
                    aircraft=plane.get("name") if isinstance(plane, dict) else None,
                    cabin=pax.get("cabin_class") or cabin.get("name"),
                    cabin_name=pax.get("cabin_class_marketing_name")
                    or cabin.get("marketing_name"),
                    seat_type=seat.get("type"),
                    checked_bags=bags.get("checked"),
                    carry_on_bags=bags.get("carry_on"),
                    origin_terminal=seg.get("origin_terminal"),
                    destination_terminal=seg.get("destination_terminal"),
                )
            )
        if not segments:
            raise ValueError("Empty flight slice")
        slices.append(
            Slice(
                id=slc.get("id") or str(i),
                segments=segments,
                stops=len(segments) - 1,
                duration_minutes=int(
                    (segments[-1].arrival_at - segments[0].departure_at).total_seconds()
                    / 60
                ),
            )
        )
    conditions = raw.get("conditions") or {}
    approved_carriers = {
        code.strip().upper()
        for code in get_settings().duffel_card_airlines.split(",")
        if code.strip()
    }
    # Airline card coverage is confirmed on account approval, not inferred from a fare.
    card_priced = any(
        m.get("type") == "card" for m in raw.get("intended_payment_methods") or []
    )
    fares = [
        s.get("fare_brand_name") for s in raw["slices"] if s.get("fare_brand_name")
    ]
    return Offer(
        id=raw["id"],
        provider="duffel",
        live_mode=bool(raw.get("live_mode")),
        total_amount=raw["total_amount"],
        currency=raw["total_currency"],
        expires_at=raw["expires_at"],
        slices=slices,
        refund=_condition(conditions.get("refund_before_departure")),
        change=_condition(conditions.get("change_before_departure")),
        fare_name=" / ".join(dict.fromkeys(fares)) or None,
        passenger_id=(raw.get("passengers") or [{}])[0].get("id"),
        card_eligible=card_priced
        or (raw.get("owner") or {}).get("iata_code") in approved_carriers,
        identity_documents_required=bool(
            raw.get("passenger_identity_documents_required")
        ),
    )


def all_segments(offer: Offer):
    return [seg for slc in offer.slices for seg in slc.segments]


def itinerary_key(offer: Offer) -> str:
    return json.dumps(
        [
            [
                [
                    (
                        s.origin,
                        s.destination,
                        s.flight_number,
                        s.departure_at.isoformat(),
                        s.cabin,
                        s.operating_airline,
                    )
                    for s in slc.segments
                ]
                for slc in offer.slices
            ],
            offer.currency,
        ]
    )


def _deviation(offer: Offer, prefs: Profile) -> int:
    def deviation(slc):
        hour = datetime.fromisoformat(slc.segments[0].departure_local).hour
        return max(prefs.depart_after - hour, hour - prefs.depart_before + 1, 0)

    return sum(deviation(slc) for slc in offer.slices)


def _airline_rank(offer: Offer, prefs: Profile) -> int:
    if not prefs.airlines:
        return 0
    primary = max(all_segments(offer), key=lambda s: s.arrival_at - s.departure_at)
    carrier = primary.operating_airline or primary.airline
    return (
        prefs.airlines.index(carrier)
        if carrier in prefs.airlines
        else len(prefs.airlines)
    )


def _aircraft_fit(offer: Offer, prefs: Profile) -> bool:
    if not prefs.aircraft:
        return True
    words = [
        x.strip().replace(" ", "").upper()
        for x in prefs.aircraft.split(",")
        if x.strip()
    ]
    longest = max(all_segments(offer), key=lambda s: s.arrival_at - s.departure_at)
    name = (longest.aircraft or "").replace(" ", "").upper()
    return any(word in name for word in words)


def rank_offers(
    offers: list[Offer], prefs: Profile
) -> tuple[list[Offer], dict, list[str]]:
    valid, exclusions = [], {}
    allowed = {"first"} if prefs.cabin == "first" else {"business", "first"}
    for offer in offers:
        segs = all_segments(offer)
        reasons = []
        # The premium-long-haul rule still requires known cabins everywhere.
        cabin_ok = all(seg.cabin in allowed for seg in segs)
        if prefs.allow_mixed_cabin:
            cabin_ok = all(
                max(slc.segments, key=lambda s: s.arrival_at - s.departure_at).cabin in allowed
                for slc in offer.slices
            ) and all(
                seg.cabin is not None for seg in segs
            )
        if not cabin_ok:
            reasons.append("cabin")
        if prefs.direct_only and any(s.stops for s in offer.slices):
            reasons.append("nonstop")
        if (
            prefs.airlines_required
            and prefs.airlines
            and any(
                (seg.operating_airline or seg.airline) not in prefs.airlines
                for seg in segs
            )
        ):
            reasons.append("airlines")
        if prefs.aircraft_required and not _aircraft_fit(offer, prefs):
            reasons.append("aircraft")
        if prefs.time_required and _deviation(offer, prefs):
            reasons.append("departure_time")
        if prefs.flexible_only and not (
            offer.refund.allowed is True or offer.change.allowed is True
        ):
            reasons.append("flexibility")
        if offer.expires_at <= utcnow():
            reasons.append("expired")
        if reasons:
            for reason in reasons:
                exclusions[reason] = exclusions.get(reason, 0) + 1
            continue
        offer.reasons = []
        offer.tradeoffs = []
        if all(s.stops == 0 for s in offer.slices):
            offer.reasons.append("Nonstop throughout")
        else:
            offer.tradeoffs.append("Connection required")
        if prefs.airlines and _airline_rank(offer, prefs) < len(prefs.airlines):
            offer.reasons.append("Preferred airline")
        elif prefs.airlines:
            offer.tradeoffs.append("Outside your preferred airlines")
        if all(seg.cabin in allowed for seg in segs):
            offer.reasons.append("Premium cabin on every flight")
        else:
            offer.tradeoffs.append("Mixed cabin: check each segment")
        if _deviation(offer, prefs):
            offer.tradeoffs.append("Outside your preferred departure window")
        if offer.refund.allowed is True:
            offer.reasons.append(
                "Refunds permitted"
                + (
                    " · fee applies"
                    if offer.refund.penalty_amount not in {None, "0", "0.00"}
                    else ""
                )
            )
        if offer.refund.allowed is None:
            offer.tradeoffs.append("Refund rules not provided")
        if prefs.aircraft and not _aircraft_fit(offer, prefs):
            offer.tradeoffs.append("Preferred aircraft not confirmed")
        valid.append(offer)

    def ranking(o):
        verified_seat = any(
            s.seat_type in {"lie_flat", "full_flat", "suite"} for s in all_segments(o)
        )
        return (
            sum(s.stops for s in o.slices),
            _airline_rank(o, prefs),
            _deviation(o, prefs),
            not verified_seat,
            not _aircraft_fit(o, prefs),
            o.refund.allowed is not True,
            o.change.allowed is not True,
            sum(s.duration_minutes for s in o.slices),
            o.currency,
            Decimal(o.total_amount),
            o.id,
        )

    valid.sort(key=ranking)
    grouped: dict[str, Offer] = {}
    for offer in valid:
        key = itinerary_key(offer)
        fare = {
            "id": offer.id,
            "name": offer.fare_name or "Fare option",
            "total_amount": offer.total_amount,
            "currency": offer.currency,
            "refund": offer.refund.model_dump(),
            "change": offer.change.model_dump(),
        }
        if key not in grouped:
            grouped[key] = offer
        grouped[key].fare_options.append(FareOption.model_validate(fare))
    results = list(grouped.values())
    for idx, offer in enumerate(results[:3]):
        offer.recommendation = [
            "Your best match",
            "Another thoughtful option",
            "Worth considering",
        ][idx]
    adjustment_names = {
        "cabin": "Allow mixed cabins",
        "nonstop": "Allow a connection",
        "airlines": "Make airline choice a preference",
        "aircraft": "Make aircraft choice a preference",
        "departure_time": "Widen departure times",
        "flexibility": "Include fares with unconfirmed flexibility",
        "expired": "Refresh this search",
    }
    return (
        results,
        exclusions,
        [adjustment_names[k] for k in exclusions if k in adjustment_names],
    )


async def demo_offers(req: SearchRequest) -> list[Offer]:
    """Synthetic offers are isolated to explicitly labeled demo sessions."""
    existing = await MockProvider(get_settings()).search(
        req.origin, req.destination, req.departure_date, return_on=req.return_date
    )
    result = []
    for i, old in enumerate(existing):
        groups, current = [], []
        for j, seg in enumerate(old.segments):
            if current and seg.origin == req.destination:
                groups.append(current)
                current = []
            cabin = "first" if req.preferences.cabin == "first" else "business"
            origin_tz, dest_tz = airport_tz(seg.origin), airport_tz(seg.destination)
            if not origin_tz or not dest_tz:
                continue
            current.append(
                Segment(
                    id=f"demo-{i}-{j}",
                    origin=seg.origin,
                    destination=seg.destination,
                    origin_city=AIRPORTS.get(seg.origin, (seg.origin,))[0],
                    destination_city=AIRPORTS.get(seg.destination, (seg.destination,))[
                        0
                    ],
                    origin_timezone=str(origin_tz),
                    destination_timezone=str(dest_tz),
                    departure_at=seg.departure_time,
                    arrival_at=seg.arrival_time,
                    departure_local=seg.departure_time.astimezone(
                        origin_tz
                    ).isoformat(),
                    arrival_local=seg.arrival_time.astimezone(dest_tz).isoformat(),
                    airline=seg.airline_iata,
                    airline_name=seg.airline_name,
                    operating_airline=seg.airline_iata,
                    operating_airline_name=seg.airline_name,
                    flight_number=seg.flight_number,
                    aircraft=["Airbus A350-900", "Boeing 787-9", "Boeing 777-300ER"][
                        i % 3
                    ],
                    cabin=cabin,
                    cabin_name="Business Flex" if cabin == "business" else "First",
                    seat_type="lie_flat",
                    checked_bags=2,
                    carry_on_bags=1,
                )
            )
        if current:
            groups.append(current)
        if len(groups) != (2 if req.return_date else 1):
            continue
        slices = [
            Slice(
                id=f"slice-{i}-{k}",
                segments=g,
                stops=len(g) - 1,
                duration_minutes=int(
                    (g[-1].arrival_at - g[0].departure_at).total_seconds() / 60
                ),
            )
            for k, g in enumerate(groups)
        ]
        result.append(
            Offer(
                id=old.id,
                provider="demo",
                live_mode=False,
                total_amount=f"{old.price:.2f}",
                currency=old.currency,
                expires_at=utcnow() + timedelta(minutes=20),
                slices=slices,
                passenger_id="demo-passenger",
                card_eligible=True,
                fare_name="Business Flex",
                refund=Condition(
                    allowed=i % 3 != 2,
                    penalty_amount="150.00" if i % 2 else "0.00",
                    penalty_currency=old.currency,
                ),
                change=Condition(
                    allowed=True, penalty_amount="0.00", penalty_currency=old.currency
                ),
            )
        )
    return result


async def reserve_live_search():
    """Reserve one upstream request against a shared UTC-month budget."""
    from sqlalchemy import update
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from app.database import SessionLocal
    from app.v1.models import Usage

    async with SessionLocal() as db:
        month = utcnow().date().replace(day=1).isoformat()
        insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
        key = {"account_id": "provider:duffel", "day": month, "kind": "live_search_month"}
        await db.execute(insert(Usage).values(**key, count=0).on_conflict_do_nothing(
            index_elements=["account_id", "day", "kind"]
        ))
        result = await db.execute(update(Usage).where(
            Usage.account_id == key["account_id"], Usage.day == month,
            Usage.kind == key["kind"], Usage.count < 600,
        ).values(count=Usage.count + 1))
        await db.commit()
        if result.rowcount != 1:
            raise DuffelError("Monthly live flight search limit reached.")


async def fetch_offers(req: SearchRequest, demo: bool) -> tuple[list[Offer], str, bool]:
    if demo:
        return (
            await demo_offers(req),
            "Synthetic demonstration inventory. No flights or fares are available for purchase.",
            False,
        )
    client = DuffelClient(get_settings())
    cabins = (
        ["business", "first"]
        if req.preferences.cabin == "either"
        else [req.preferences.cabin]
    )

    async def fetch(cabin):
        if get_settings().duffel_access_token.startswith("duffel_live_"):
            await reserve_live_search()
        payload = await client.search_offers(
            req.origin,
            req.destination,
            req.departure_date,
            cabin=cabin,
            return_on=req.return_date,
            max_connections=0 if req.preferences.direct_only else 1,
            departure_window=(
                req.preferences.depart_after,
                req.preferences.depart_before,
            )
            if req.preferences.time_required
            else None,
        )
        data = payload.get("data") or {}
        raw = list(data.get("offers") or [])
        # Some Duffel responses omit inline offers. Page through the request without a price-first cap.
        if not raw and data.get("id"):
            after = None
            while True:
                page = await client._request(
                    "GET",
                    "/air/offers",
                    params={
                        "offer_request_id": data["id"],
                        "limit": 200,
                        **({"after": after} if after else {}),
                    },
                )
                raw.extend(page.get("data") or [])
                after = (page.get("meta") or {}).get("after")
                if not after:
                    break
        return raw

    batches = await asyncio.gather(*(fetch(c) for c in cabins), return_exceptions=True)
    raw, errors = {}, []
    for batch in batches:
        if isinstance(batch, BaseException):
            errors.append("One requested cabin could not be searched")
        else:
            raw.update({o["id"]: o for o in batch})
    if len(errors) == len(cabins):
        raise DuffelError(
            "Flight search is temporarily unavailable. Try again shortly."
        )
    offers, skipped = [], 0
    for item in raw.values():
        try:
            offer = normalize_offer(item)
            expected = [(req.origin, req.destination, req.departure_date)]
            if req.return_date:
                expected.append((req.destination, req.origin, req.return_date))
            if len(offer.slices) != len(expected) or any(
                slc.segments[0].origin != origin
                or slc.segments[-1].destination != destination
                or datetime.fromisoformat(slc.segments[0].departure_local).date() != day
                for slc, (origin, destination, day) in zip(offer.slices, expected)
            ):
                raise ValueError("Provider itinerary does not match the requested journey")
            offers.append(offer)
        except (ValueError, KeyError, TypeError, IndexError):
            skipped += 1
    partial = bool(errors or skipped)
    coverage = "Duffel airline inventory; availability varies by carrier."
    if errors:
        coverage += " " + ". ".join(errors) + "."
    if skipped:
        coverage += f" {skipped} offers lacked usable itinerary data."
    return offers, coverage, partial
