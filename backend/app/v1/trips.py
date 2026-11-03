import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import utcnow
from app.services.links import MANAGE_SITES, _HOMEPAGES
from app.v1.models import Account, Trip
from app.v1.schemas import Profile, SearchRequest, TripData


def official_site(carrier: str) -> str | None:
    from app.services.airline_link import _AIRLINE_HOSTS

    hosts = _AIRLINE_HOSTS.get(carrier)
    return "https://www." + hosts[0] + "/" if hosts else _HOMEPAGES.get(carrier)


def trip_read(trip: Trip, demo: bool) -> dict:
    data = trip.itinerary
    first = data["slices"][0]["segments"][0]
    last = data["slices"][0]["segments"][-1]
    return {
        "id": trip.id,
        "title": trip.title,
        "status": trip.status,
        "source": trip.source,
        "is_demo": demo,
        "departure_at": trip.departure_at.isoformat(),
        "created_at": trip.created_at.isoformat(),
        "origin": first["origin"],
        "destination": last["destination"],
        "destination_city": last["destination_city"],
        "manage_url": MANAGE_SITES.get(first["airline"])
        or official_site(first["airline"]),
        **data,
        "documents": [
            {
                "type": d.get("type"),
                "name": d.get("name"),
                "unique_identifier": d.get("unique_identifier"),
                "available": bool(d.get("storage_key")),
            }
            for d in data.get("documents", [])
        ],
    }


def dedupe_key(data: TripData) -> str:
    first = data.slices[0].segments[0]
    return hashlib.sha256(
        (
            "|".join(sorted(data.references))
            + "|"
            + data.passenger_name.casefold()
            + "|"
            + first.departure_local[:10]
        ).encode()
    ).hexdigest()


async def save_trip(
    session: AsyncSession,
    account: Account,
    data: TripData,
    source="manual",
    trip_id: str | None = None,
) -> Trip:
    key = dedupe_key(data)
    trip = await session.get(Trip, trip_id) if trip_id else None
    if trip is not None and trip.account_id != account.id:
        raise HTTPException(404, "Trip not found")
    trip = trip or (
        (
            await session.execute(
                select(Trip).where(
                    Trip.account_id == account.id, Trip.dedupe_key == key
                )
            )
        )
        .scalars()
        .first()
    )
    if trip is None:
        # Schedule updates can change the date. Match the existing reservation and traveler,
        # requiring an overlapping flight number to avoid merging unrelated PNR reuse.
        candidates = (
            (
                await session.execute(
                    select(Trip).where(
                        Trip.account_id == account.id,
                        Trip.departure_at
                        > data.slices[0].segments[0].departure_at - timedelta(days=180),
                        Trip.departure_at
                        < data.slices[0].segments[0].departure_at + timedelta(days=180),
                    )
                )
            )
            .scalars()
            .all()
        )
        flights = {s.flight_number for slc in data.slices for s in slc.segments}
        for candidate in candidates:
            previous = candidate.itinerary
            old_flights = {
                s["flight_number"]
                for slc in previous.get("slices", [])
                for s in slc["segments"]
            }
            if (
                set(previous.get("references", [])) & set(data.references)
                and previous.get("passenger_name", "").casefold()
                == data.passenger_name.casefold()
                and flights & old_flights
            ):
                trip = candidate
                break
    first, last = data.slices[0].segments[0], data.slices[0].segments[-1]
    title = f"{first.origin_city} to {last.destination_city}"
    if trip is None:
        trip = Trip(
            account_id=account.id,
            dedupe_key=key,
            title=title,
            departure_at=first.departure_at,
            status="cancelled"
            if data.cancelled
            else "needs_attention"
            if data.needs_review
            else "confirmed",
            source=source,
            itinerary=data.model_dump(mode="json"),
        )
        session.add(trip)
    else:
        previous = trip.itinerary
        if source != "duffel" and trip.source == "duffel":
            data.payment_status = previous.get("payment_status", "external")
            data.ticketing_status = previous.get("ticketing_status", "imported")
            data.documents = previous.get("documents", [])
            data.total_amount = previous.get("total_amount")
            data.currency = previous.get("currency")
        else:
            for document in data.documents:
                match = next(
                    (
                        d
                        for d in previous.get("documents", [])
                        if document.get("unique_identifier")
                        and d.get("unique_identifier")
                        == document.get("unique_identifier")
                    ),
                    None,
                )
                if match and match.get("storage_key"):
                    document["storage_key"] = match["storage_key"]
        trip.itinerary = data.model_dump(mode="json")
        trip.title = title
        trip.departure_at = first.departure_at
        trip.status = (
            "cancelled"
            if data.cancelled
            else "needs_attention"
            if data.needs_review
            else "confirmed"
        )
    await session.commit()
    await session.refresh(trip)
    return trip


async def seed_demo(session: AsyncSession, account: Account) -> None:
    from app.v1.flights import demo_offers

    for origin, dest, days in [("MAD", "LHR", 12), ("LHR", "SIN", 34)]:
        req = SearchRequest(
            origin=origin,
            destination=dest,
            departure_date=(utcnow() + timedelta(days=days)).date(),
            return_date=(utcnow() + timedelta(days=days + 5)).date(),
            preferences=Profile(),
        )
        offers = await demo_offers(req)
        if not offers:
            continue
        offer = offers[0]
        await save_trip(
            session,
            account,
            TripData(
                passenger_name="Federico · Demo traveler",
                references=["DEMO" + str(days)],
                slices=offer.slices,
                total_amount=offer.total_amount,
                currency=offer.currency,
                ticketing_status="demo",
                notes="Fictional itinerary for exploring the app. No reservation exists.",
            ),
            source="demo",
        )


def calendar_events(trips: list[Trip]) -> list[dict]:
    events = []
    for trip in trips:
        if trip.status == "cancelled":
            continue
        for i, slc in enumerate(trip.itinerary.get("slices", [])):
            for j, seg in enumerate(slc["segments"]):
                events.append(
                    {
                        "id": f"{trip.id}-{i}-{j}",
                        "trip_id": trip.id,
                        "title": f"{seg['flight_number']} · {seg['origin']} → {seg['destination']}",
                        "date": seg["departure_local"][:10],
                        "departure_at": seg["departure_at"],
                        "arrival_at": seg["arrival_at"],
                        "departure_local": seg["departure_local"],
                        "arrival_local": seg["arrival_local"],
                        "timezone": seg["origin_timezone"],
                        "destination_timezone": seg["destination_timezone"],
                        "references": trip.itinerary["references"],
                    }
                )
    return sorted(events, key=lambda e: e["departure_at"])


def calendar_ics(events: list[dict]) -> str:
    def escape(s):
        return (
            str(s)
            .replace("\\", "\\\\")
            .replace("\r", "")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )

    def stamp(s):
        return (
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            .astimezone(ZoneInfo("UTC"))
            .strftime("%Y%m%dT%H%M%SZ")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Elsewhere//Travel Concierge//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for e in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['id']}@elsewhere",
            f"DTSTAMP:{utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{stamp(e['departure_at'])}",
            f"DTEND:{stamp(e['arrival_at'])}",
            f"SUMMARY:{escape(e['title'])}",
            f"DESCRIPTION:{escape('Reservation: ' + ', '.join(e['references']))}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    # RFC5545 fold lines at UTF-8 byte boundaries, not character boundaries.
    folded = []
    for line in lines:
        chunk = ""
        for char in line:
            if len((chunk + char).encode()) > 73:
                folded.append(chunk)
                chunk = " " + char
            else:
                chunk += char
        folded.append(chunk)
    return "\r\n".join(folded) + "\r\n"
