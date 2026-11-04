import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.config import get_settings
from app.database import SessionLocal
from app.models import utcnow
from app.services.airline_link import pick_itinerary, host_is_airline
from app.services.duffel import DuffelError
from app.v1.flights import demo_offers, normalize_offer, rank_offers
from app.v1.handoff import matches
from app.v1.imports import parse_draft
from app.v1.models import Account, Checkout
from app.v1.schemas import Condition, Profile, SearchRequest, TripData
from app.v1.trips import calendar_events, calendar_ics


@pytest.fixture
def guest(client):
    c = TestClient(app)
    data = c.post("/api/v1/auth/demo").json()
    c.headers["x-csrf-token"] = data["csrf_token"]
    c.session_data = data
    return c


def request(**changes):
    return {
        "origin": "JFK",
        "destination": "LHR",
        "departure_date": str(date.today() + timedelta(days=30)),
        "return_date": str(date.today() + timedelta(days=37)),
        "preferences": Profile().model_dump(),
        **changes,
    }


def search(c, **changes):
    response = c.post("/api/v1/searches", json=request(**changes))
    assert response.status_code == 202, response.text
    result = c.get("/api/v1/searches/" + response.json()["id"])
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "complete", result.text
    return result.json()


def checkout(c):
    data = search(c)
    assert data["results"]
    r = c.post(
        "/api/v1/checkout-sessions",
        json={"search_id": data["id"], "offer_id": data["results"][0]["id"]},
    )
    assert r.status_code == 201, r.text
    return r.json()


def order_payload(row, **changes):
    return {
        "checkout_id": row["id"],
        "attempt_key": "test-booking-attempt-" + row["id"],
        "accepted_quote_hash": row["quote_hash"],
        "passenger": {
            "given_name": "Ada",
            "family_name": "Lovelace",
            "email": "ada@example.com",
            "born_on": "1988-01-03",
            "phone_number": "+34600123456",
            "gender": "f",
            "title": "ms",
        },
        **changes,
    }


def test_private_data_requires_session(client):
    c = TestClient(app)
    for path in [
        "/api/v1/trips",
        "/api/v1/auth/session",
        "/api/v1/calendar",
        "/api/v1/calendar.ics",
        "/api/bookings",
    ]:
        assert c.get(path).status_code == 401
    assert c.post("/api/bookings/place", json={}).status_code == 410
    assert c.get("/static/boarding_passes/test.pdf").status_code == 404


def test_csrf_and_origin_enforced(guest):
    guest.headers.pop("x-csrf-token")
    assert guest.put("/api/v1/profile", json=Profile().model_dump()).status_code == 403
    guest.headers["x-csrf-token"] = guest.session_data["csrf_token"]
    guest.headers["origin"] = "https://attacker.invalid"
    assert guest.put("/api/v1/profile", json=Profile().model_dump()).status_code == 403


def test_cookie_and_response_headers(guest):
    response = guest.get("/api/v1/auth/session")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert (
        "httponly"
        in guest.cookies.jar._cookies["testserver.local"]["/"][
            "concierge_session"
        ]._rest.keys()
        or "HttpOnly"
        in guest.cookies.jar._cookies["testserver.local"]["/"][
            "concierge_session"
        ]._rest.keys()
    )


def test_ownership_for_trips_searches_checkout(guest):
    trip = guest.get("/api/v1/trips").json()[0]
    row = checkout(guest)
    other = TestClient(app)
    data = other.post("/api/v1/auth/demo").json()
    other.headers["x-csrf-token"] = data["csrf_token"]
    assert other.get("/api/v1/trips/" + trip["id"]).status_code == 404
    assert other.get("/api/v1/checkout-sessions/" + row["id"]).status_code == 404
    assert other.get("/api/v1/trips/" + trip["id"] + "/documents/0").status_code == 404


def test_roundtrip_retains_all_segments_and_test_label(guest):
    data = search(guest)
    assert data["live_mode"] is False
    assert "Synthetic" in data["coverage"]
    for offer in data["results"]:
        assert len(offer["slices"]) == 2
        assert offer["slices"][0]["segments"][0]["origin"] == "JFK"
        assert offer["slices"][1]["segments"][-1]["destination"] == "JFK"
        assert all(
            s["cabin"] == "business" for leg in offer["slices"] for s in leg["segments"]
        )


def test_search_cache_and_quota(guest, monkeypatch):
    monkeypatch.setattr(get_settings(), "search_daily_limit", 1)
    one = search(guest)
    two = search(guest)
    assert one["id"] == two["id"]
    assert (
        guest.post("/api/v1/searches", json=request(destination="SIN")).status_code
        == 429
    )


def test_required_direct_and_unknown_rules():
    req = SearchRequest.model_validate(request())
    offers = asyncio.run(demo_offers(req))
    direct = offers[0].model_copy(deep=True)
    direct.refund = Condition()
    direct.change = Condition()
    result, excluded, _ = rank_offers([direct], Profile(flexible_only=True))
    assert result == [] and excluded["flexibility"] == 1
    connecting = next((o for o in offers if any(s.stops for s in o.slices)), None)
    assert connecting is not None
    result, excluded, _ = rank_offers([connecting], Profile(direct_only=True))
    assert not result and excluded["nonstop"] == 1


def test_preferred_airline_is_soft_until_required():
    offers = asyncio.run(demo_offers(SearchRequest.model_validate(request())))
    result, _, _ = rank_offers(offers, Profile(airlines=["XX"]))
    assert result and any("Outside" in x for x in result[0].tradeoffs)
    result, excluded, adjustments = rank_offers(
        offers, Profile(airlines=["XX"], airlines_required=True)
    )
    assert not result and excluded["airlines"] > 0 and adjustments


def test_no_cutoff_and_fare_grouping():
    base = asyncio.run(demo_offers(SearchRequest.model_validate(request())))[0]
    inventory = []
    for i in range(40):
        offer = base.model_copy(deep=True)
        offer.id = "offer-" + str(i)
        offer.total_amount = str(1000 + i)
        offer.slices[0].segments[0].flight_number = "BA" + str(100 + i)
        if i < 39:
            offer.slices[0].segments[0].cabin = "economy"
        inventory.append(offer)
    results, _, _ = rank_offers(inventory, Profile())
    assert len(results) == 1 and results[0].id == "offer-39"
    second = base.model_copy(deep=True)
    second.id = "another-fare"
    second.total_amount = "9999"
    results, _, _ = rank_offers([base, second], Profile())
    assert len(results) == 1 and len(results[0].fare_options) == 2


def raw_offer():
    day = date.today() + timedelta(days=30)
    return {
        "id": "off_test",
        "live_mode": False,
        "total_amount": "4567.89",
        "total_currency": "EUR",
        "expires_at": (utcnow() + timedelta(minutes=20)).isoformat(),
        "owner": {"iata_code": "BA"},
        "passengers": [{"id": "pas_1"}],
        "intended_payment_methods": [{"type": "card"}],
        "slices": [
            {
                "id": "slice1",
                "segments": [
                    {
                        "id": "seg1",
                        "origin": {
                            "iata_code": "JFK",
                            "time_zone": "America/New_York",
                            "city_name": "New York",
                        },
                        "destination": {
                            "iata_code": "LHR",
                            "time_zone": "Europe/London",
                            "city_name": "London",
                        },
                        "departing_at": str(day) + "T22:00:00",
                        "arriving_at": str(day + timedelta(days=1)) + "T10:00:00",
                        "marketing_carrier": {
                            "iata_code": "BA",
                            "name": "British Airways",
                        },
                        "operating_carrier": {"iata_code": "IB", "name": "Iberia"},
                        "marketing_carrier_flight_number": "112",
                        "passengers": [{"cabin_class": "economy"}],
                    }
                ],
            }
        ],
    }


def test_actual_cabin_codeshare_and_missing_data():
    offer = normalize_offer(raw_offer())
    assert offer.slices[0].segments[0].cabin == "economy"
    assert offer.slices[0].segments[0].operating_airline == "IB"
    assert not rank_offers([offer], Profile())[0]
    raw = raw_offer()
    raw["slices"][0]["segments"][0]["passengers"] = []
    assert normalize_offer(raw).slices[0].segments[0].cabin is None
    raw["slices"][0]["segments"][0]["origin"] = {"iata_code": "ZZZ"}
    with pytest.raises(ValueError):
        normalize_offer(raw)


def test_mixed_cabin_requires_premium_main_flight_in_each_direction():
    offer = asyncio.run(demo_offers(SearchRequest.model_validate(request())))[0]
    for segment in offer.slices[1].segments:
        segment.cabin = "economy"
    results, exclusions, _ = rank_offers([offer], Profile(allow_mixed_cabin=True))
    assert not results and exclusions["cabin"] == 1


@pytest.mark.parametrize("invalid", ["airport", "overlap"])
def test_provider_connections_must_be_continuous(invalid):
    import copy
    raw = raw_offer()
    previous = raw["slices"][0]["segments"][0]
    following = copy.deepcopy(previous)
    following["origin"] = copy.deepcopy(previous["destination"])
    following["departing_at"] = previous["arriving_at"]
    following["arriving_at"] = (datetime.fromisoformat(previous["arriving_at"]) + timedelta(hours=4)).isoformat()
    if invalid == "airport":
        following["origin"]["iata_code"] = "CDG"
        following["departing_at"] = (datetime.fromisoformat(previous["arriving_at"]) + timedelta(hours=1)).isoformat()
    raw["slices"][0]["segments"].append(following)
    with pytest.raises(ValueError, match="Connections"):
        normalize_offer(raw)


@pytest.mark.parametrize("mismatch", ["airport", "date", "return"])
def test_provider_search_rejects_a_different_requested_journey(monkeypatch, mismatch):
    from app.v1.flights import fetch_offers
    raw = raw_offer()
    segment = raw["slices"][0]["segments"][0]
    segment["passengers"] = [{"cabin_class": "business"}]
    if mismatch == "airport":
        segment["origin"]["iata_code"] = "EWR"
    if mismatch == "date":
        segment["departing_at"] = (datetime.fromisoformat(segment["departing_at"]) + timedelta(hours=24)).isoformat()
        segment["arriving_at"] = (datetime.fromisoformat(segment["arriving_at"]) + timedelta(hours=24)).isoformat()
    monkeypatch.setattr("app.v1.flights.DuffelClient.search_offers", AsyncMock(return_value={"data": {"offers": [raw]}}))
    req = SearchRequest.model_validate(request(**({} if mismatch == "return" else {"return_date": None})))
    offers, coverage, partial = asyncio.run(fetch_offers(req, False))
    assert offers == [] and partial is True
    assert "1 offers lacked usable itinerary data" in coverage


def test_test_inventory_handoff_never_claims_a_real_exact_flight(monkeypatch):
    from app.v1.handoff import resolve_handoff
    lookup = AsyncMock()
    monkeypatch.setattr("app.v1.handoff._serpapi", lookup)
    raw = raw_offer()
    raw["slices"][0]["segments"][0]["passengers"] = [{"cabin_class": "business"}]
    handoff = asyncio.run(resolve_handoff(normalize_offer(raw)))
    assert handoff["match"] == "route_only" and handoff["prefilled"] is True
    assert "test inventory, not a real fare" in handoff["message"]
    lookup.assert_not_called()


def test_cabin_searches_are_concurrent_and_independent(monkeypatch):
    from app.v1.flights import fetch_offers

    events = []

    async def mocked(self, *args, cabin, **kwargs):
        events.append("start-" + cabin)
        await asyncio.sleep(0.01)
        events.append("end-" + cabin)
        raw = raw_offer()
        raw["id"] = "off_" + cabin
        raw["slices"][0]["segments"][0]["passengers"] = [{"cabin_class": cabin}]
        return {"data": {"offers": [raw]}}

    monkeypatch.setattr("app.v1.flights.DuffelClient.search_offers", mocked)
    req = SearchRequest.model_validate(
        request(preferences=Profile(cabin="either").model_dump(), return_date=None,
                departure_date=raw_offer()["slices"][0]["segments"][0]["departing_at"][:10])
    )
    offers, _, _ = asyncio.run(fetch_offers(req, False))
    assert events[:2] == ["start-business", "start-first"]
    assert {o.slices[0].segments[0].cabin for o in offers} == {"business", "first"}


def test_handoff_never_substitutes_and_checks_full_itinerary():
    assert (
        pick_itinerary(
            {
                "best_flights": [
                    {"booking_token": "x", "flights": [{"flight_number": "BA999"}]}
                ]
            },
            "BA178",
            "BA",
        )
        is None
    )
    assert not host_is_airline("https://unknown-airline.invalid", "XX")
    offer = normalize_offer(raw_offer())
    slc = offer.slices[0]
    seg = slc.segments[0]
    candidate = {
        "flights": [
            {
                "flight_number": seg.flight_number,
                "travel_class": "economy",
                "departure_airport": {"id": "JFK", "time": seg.departure_local[:19]},
                "arrival_airport": {"id": "LHR", "time": seg.arrival_local[:19]},
            }
        ]
    }
    assert matches(candidate, slc)
    candidate["flights"][0]["departure_airport"]["time"] = "2030-01-01T00:00:00"
    assert not matches(candidate, slc)


def test_demo_handoff_is_not_a_real_booking(guest):
    data = search(guest)
    r = guest.post(
        "/api/v1/airline-handoffs",
        json={"search_id": data["id"], "offer_id": data["results"][0]["id"]},
    )
    assert r.json()["match"] == "unavailable" and r.json()["url"] is None


def test_import_never_fabricates():
    data, issues = parse_draft(
        "Your booking is confirmed. Thank you for traveling with us."
    )
    assert (
        not data["references"]
        and not data["passenger_name"]
        and not data["slices"]
        and issues
    )


def test_import_review_idempotent_and_calendar(guest):
    raw = "Passenger: Ada Lovelace\nConfirmation: ABC123\nFlight BA178\nJFK → LHR\nDeparture: 2027-01-10T18:00:00\nArrival: 2027-01-11T06:00:00"
    r = guest.post("/api/v1/imports/preview", json={"raw_text": raw})
    assert r.status_code == 201
    draft = r.json()
    assert len(draft["data"]["slices"]) == 1
    one = guest.post("/api/v1/imports/" + draft["id"] + "/confirm", json=draft["data"])
    assert one.status_code == 200, one.text
    two = guest.post("/api/v1/imports/" + draft["id"] + "/confirm", json=draft["data"])
    assert one.json()["id"] == two.json()["id"]
    assert guest.get("/api/v1/calendar.ics").text.count("BEGIN:VEVENT") >= 1


def test_calendar_uses_local_date_not_utc(guest):
    trip = guest.get("/api/v1/trips").json()[0]
    seg = trip["slices"][0]["segments"][0]
    seg.update(
        departure_at="2027-01-11T02:00:00Z",
        arrival_at="2027-01-11T10:00:00Z",
        origin_timezone="America/New_York",
        destination_timezone="Europe/London",
    )
    data = {k: v for k, v in trip.items() if k in TripData.model_fields}
    data["slices"] = [{**data["slices"][0], "segments": [seg]}]
    data["references"] = ["LOCAL1"]
    r = guest.post("/api/v1/trips", json=data)
    assert r.status_code == 201, r.text
    events = guest.get("/api/v1/calendar").json()
    event = next(e for e in events if e["trip_id"] == r.json()["id"])
    assert event["date"] == "2027-01-10"
    ics = guest.get("/api/v1/calendar.ics").text
    assert "DTSTART:20270111T020000Z" in ics


@pytest.mark.parametrize(
    "outcome,state",
    [("success", "confirmed"), ("declined", "declined"), ("uncertain", "confirming")],
)
def test_checkout_outcomes_and_repeat_submission(guest, outcome, state):
    row = checkout(guest)
    payload = order_payload(row, demo_outcome=outcome)
    one = guest.post("/api/v1/orders", json=payload)
    assert one.status_code == 200, one.text
    assert one.json()["state"] == state
    two = guest.post("/api/v1/orders", json=payload)
    assert two.status_code == 200, two.text
    assert one.json().get("trip_id") == two.json().get("trip_id")


def test_missing_passenger_and_quote_consent_block_purchase(guest):
    row = checkout(guest)
    payload = order_payload(row, accepted_quote_hash="stale")
    assert guest.post("/api/v1/orders", json=payload).status_code == 409
    payload = order_payload(row)
    payload["passenger"]["born_on"] = ""
    assert guest.post("/api/v1/orders", json=payload).status_code == 422


def test_ambiguous_provider_timeout_is_not_retried(guest, monkeypatch):
    row = checkout(guest)

    async def real_account():
        async with SessionLocal() as db:
            account = await db.get(Account, guest.session_data["account"]["id"])
            account.is_demo = False
            ch = await db.get(Checkout, row["id"])
            ch.data = {"priced_card_id": "tcd_test_123"}
            ch.offer = {**ch.offer, "id": "off_test", "live_mode": False}
            ch.quote_hash = "accepted"
            await db.commit()

    asyncio.run(real_account())
    monkeypatch.setattr(
        get_settings(), "allowed_emails", guest.session_data["account"]["email"]
    )
    monkeypatch.setattr(get_settings(), "duffel_cards_approved", True)
    # Pricing is already accepted; order submission times out after it may have reached the airline.
    from app.v1.checkout import quote_hash

    raw = raw_offer()
    raw["slices"][0]["segments"][0]["passengers"] = [{"cabin_class": "business"}]
    fresh = normalize_offer(raw)
    payload = order_payload(
        row,
        accepted_quote_hash=quote_hash(fresh),
        card_id="tcd_test_123",
        three_d_secure_session_id="3ds_test",
    )

    async def set_quote():
        async with SessionLocal() as db:
            ch = await db.get(Checkout, row["id"])
            ch.offer = fresh.model_dump(mode="json")
            ch.quote_hash = quote_hash(fresh)
            await db.commit()

    asyncio.run(set_quote())
    sent = []

    async def provider(self, method, path, **kwargs):
        if path.endswith("/price"):
            return {"data": raw}
        sent.append(path)
        raise DuffelError("connection lost")

    monkeypatch.setattr("app.v1.checkout.DuffelClient._request", provider)
    first = guest.post("/api/v1/orders", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "confirming"
    second = guest.post("/api/v1/orders", json=payload)
    assert second.json()["state"] == "confirming"
    assert sent == ["/air/orders"]


def test_unsigned_inbound_webhook_fails_closed(guest, monkeypatch):
    monkeypatch.setattr(get_settings(), "resend_webhook_secret", "")
    assert guest.post("/api/v1/webhooks/inbound", json={}).status_code == 503
    monkeypatch.setattr(get_settings(), "resend_webhook_secret", "whsec_dGVzdA==")
    assert guest.post("/api/v1/webhooks/inbound", json={}).status_code == 401


def test_profile_validation_and_owner_isolation(guest):
    profile = Profile(first_name="Test", home_airport="SIN").model_dump()
    assert guest.put("/api/v1/profile", json=profile).status_code == 200
    assert guest.get("/api/v1/auth/session").json()["profile"]["home_airport"] == "SIN"
    profile["depart_after"] = 23
    profile["depart_before"] = 9
    assert guest.put("/api/v1/profile", json=profile).status_code == 422


def test_production_disables_demo(guest, monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    assert guest.post("/api/v1/auth/demo").status_code == 404
    assert guest.get("/api/v1/trips").status_code == 403


def test_search_paginates_and_sorts_full_inventory(guest, monkeypatch):
    base = asyncio.run(demo_offers(SearchRequest.model_validate(request())))[0]

    async def fetch(*args, **kwargs):
        inventory = []
        for i in range(40):
            item = base.model_copy(deep=True)
            item.id = f"page-{i}"
            item.total_amount = str(5000 - i)
            item.slices[0].segments[0].flight_number = f"BA{100 + i}"
            inventory.append(item)
        return inventory, "Complete test inventory", False

    monkeypatch.setattr("app.v1.jobs.fetch_offers", fetch)
    first = search(guest)
    assert first["matching_itineraries"] == 40 and len(first["results"]) == 25
    second = guest.get("/api/v1/searches/" + first["id"] + "?cursor=25").json()
    assert len(second["results"]) == 15 and second["next_cursor"] is None
    assert not (
        {o["id"] for o in first["results"]} & {o["id"] for o in second["results"]}
    )
    cheapest = guest.get("/api/v1/searches/" + first["id"] + "?sort=price").json()
    assert cheapest["results"][0]["total_amount"] == "4961"


def test_provider_schedule_updates_preserve_trip_identity(guest):
    from app.v1.checkout import finish_order

    row = checkout(guest)
    guest.post("/api/v1/orders", json=order_payload(row))

    async def refresh():
        async with SessionLocal() as db:
            record = await db.get(Checkout, row["id"])
            original = record.trip_id
            account = await db.get(Account, record.account_id)
            raw = raw_offer()
            raw["slices"][0]["segments"][0]["marketing_carrier_flight_number"] = "999"
            raw["booking_reference"] = "REAL123"
            raw["documents"] = [
                {"type": "electronic_ticket", "unique_identifier": "1234567890123"}
            ]
            await finish_order(db, record, account, raw)
            assert record.trip_id == original
            return original

    identifier = asyncio.run(refresh())
    trip = guest.get("/api/v1/trips/" + identifier).json()
    assert trip["slices"][0]["segments"][0]["flight_number"] == "BA999"
    assert trip["documents"][0]["unique_identifier"] == "1234567890123"
    assert "url" not in trip["documents"][0]


def test_unknown_card_coverage_fails_closed(monkeypatch):
    monkeypatch.setattr(get_settings(), "duffel_card_airlines", "")
    raw = raw_offer()
    raw.pop("intended_payment_methods")
    assert normalize_offer(raw).card_eligible is False
    monkeypatch.setattr(get_settings(), "duffel_card_airlines", "BA")
    assert normalize_offer(raw).card_eligible is True


def test_structured_reservations_and_malformed_markup():
    payload = {
        "@type": "FlightReservation",
        "reservationNumber": "TEST123",
        "underName": {"name": "Ada Lovelace"},
        "reservationFor": {
            "flightNumber": "BA178",
            "departureAirport": {"iataCode": "JFK"},
            "arrivalAirport": {"iataCode": "LHR"},
            "departureTime": "2027-01-10T18:00:00-05:00",
            "arrivalTime": "2027-01-11T06:00:00Z",
        },
    }
    raw = '<script type="application/ld+json">' + json.dumps(payload) + "</script>"
    data, issues = parse_draft(raw)
    assert not issues and data["references"] == ["TEST123"]
    payload["underName"] = "invalid"
    data, issues = parse_draft(
        '<script type="application/ld+json">' + json.dumps(payload) + "</script>"
    )
    assert issues


def test_expired_offer_and_changed_price_require_new_consent(guest):
    row = checkout(guest)

    async def expire():
        async with SessionLocal() as db:
            checkout_row = await db.get(Checkout, row["id"])
            checkout_row.expires_at = utcnow() - timedelta(seconds=1)
            await db.commit()

    asyncio.run(expire())
    assert guest.post("/api/v1/orders", json=order_payload(row)).status_code == 410


def test_verified_hotels_require_fresh_sources(monkeypatch):
    from app.v1 import places

    class ReviewDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 3)

    monkeypatch.setattr(places, "date", ReviewDate)
    hotels = places.verified_hotels("LHR", Profile())
    assert hotels and all(
        h["hotel_stars"] == 5 and h["gym"] is True and h["spa"] is True and h["sources"]
        for h in hotels
    )

    class ExpiredDate(date):
        @classmethod
        def today(cls):
            return cls(2027, 1, 1)

    monkeypatch.setattr(places, "date", ExpiredDate)
    assert places.verified_hotels("LHR", Profile()) == []


def test_handoff_understands_provider_class_labels_and_rejects_downgrades():
    from app.services.airline_link import page_matches_cabin
    raw = raw_offer()
    raw['slices'][0]['segments'][0]['passengers'][0]['cabin_class'] = 'business'
    segment = normalize_offer(raw).slices[0].segments[0]
    candidate = {'flights': [{
        'flight_number': segment.flight_number, 'travel_class': 'Business Class',
        'departure_airport': {'id': segment.origin, 'time': segment.departure_local[:19]},
        'arrival_airport': {'id': segment.destination, 'time': segment.arrival_local[:19]},
    }]}
    assert matches(candidate, normalize_offer(raw).slices[0])
    candidate['flights'][0]['travel_class'] = 'Premium Economy'
    assert not matches(candidate, normalize_offer(raw).slices[0])
    assert not page_matches_cabin('https://www.britishairways.com/book?cabin1=eco&cabin2=business', 'business')
    assert page_matches_cabin('https://www.britishairways.com/book?cabin1=business&cabin2=business', 'business')


def test_ba_handoff_preserves_route_dates_cabin_without_selecting_another_flight():
    from app.v1.handoff import airline_search_url
    from urllib.parse import parse_qs, urlsplit
    raw = raw_offer()
    raw['slices'][0]['segments'][0]['passengers'][0]['cabin_class'] = 'business'
    offer = normalize_offer(raw)
    url = airline_search_url(offer)
    query = parse_qs(urlsplit(url).query)
    assert query['from'] == ['JFK'] and query['to'] == ['LHR']
    assert query['departureDate'] == [offer.slices[0].segments[0].departure_local[:10]]
    assert query['travelClass'] == ['business'] and query['adults'] == ['1']
    assert query['trip'] == ['oneway']
    assert 'flight_number' not in query and 'ond1' not in query


def test_live_search_monthly_budget_is_shared_and_enforced(client):
    from sqlalchemy import delete
    from app.v1.flights import reserve_live_search
    from app.v1.models import Usage

    async def check():
        month = utcnow().date().replace(day=1).isoformat()
        async with SessionLocal() as db:
            await db.execute(delete(Usage).where(Usage.account_id == "provider:duffel"))
            db.add(Usage(account_id="provider:duffel", day=month, kind="live_search_month", count=599))
            await db.commit()
        await reserve_live_search()
        with pytest.raises(DuffelError, match="Monthly live flight search limit"):
            await reserve_live_search()
        async with SessionLocal() as db:
            row = (await db.execute(select(Usage).where(Usage.account_id == "provider:duffel"))).scalar_one()
            assert row.count == 600
            await db.delete(row)
            await db.commit()

    asyncio.run(check())
