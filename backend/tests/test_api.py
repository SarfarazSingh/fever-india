import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone

import httpx

from app.config import Settings, get_settings
from app.services.check_in import get_engine
from app.services.flight_search import DuffelProvider
from app.services.scheduler import job_id, scheduler


def _future(days: int = 5) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0)


def _booking_payload(**overrides) -> dict:
    payload = {
        "user_email": "Traveller@Example.com",
        "passenger_first_name": "Ada",
        "passenger_last_name": "Lovelace",
        "airline_iata": "dl",
        "flight_number": "DL 1",
        "departure_time": _future().isoformat(),
        "pnr_code": "abc123",
    }
    payload.update(overrides)
    return payload


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_mock_search_returns_business_offers(client):
    day = (date.today() + timedelta(days=30)).isoformat()
    resp = client.get("/api/flights/search", params={"origin": "jfk", "destination": "LHR", "date": day})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["count"] == len(body["results"])
    assert 1 <= body["count"] <= 3
    assert "Aisle requested" in body["note"]
    assert "nonstop" in body["note"].lower()
    prices = [o["price"] for o in body["results"]]
    assert prices == sorted(prices)
    for offer in body["results"]:
        assert offer["cabin_class"] in {"C", "F"}
        assert offer["layovers"] == 0
        assert offer["deep_link"].startswith("http://testserver/demo/checkout?")
        assert offer["origin"] == "JFK" and offer["destination"] == "LHR"


def test_duffel_offer_parser_maps_segments_and_price():
    provider = DuffelProvider.__new__(DuffelProvider)
    provider._settings = Settings(flight_provider="mock", duffel_access_token="")
    offer = provider._parse_offer(
        {
            "id": "off_test_1",
            "total_amount": "4321.50",
            "total_currency": "USD",
            "expires_at": "2026-12-01T12:00:00Z",
            "owner": {"iata_code": "BA", "name": "British Airways"},
            "passengers": [{"id": "pas_1"}],
            "slices": [
                {
                    "segments": [
                        {
                            "origin": {"iata_code": "JFK"},
                            "destination": {"iata_code": "LHR"},
                            "departing_at": "2026-12-15T18:00:00",
                            "arriving_at": "2026-12-16T06:10:00",
                            "marketing_carrier": {"iata_code": "BA", "name": "British Airways"},
                            "marketing_carrier_flight_number": "112",
                        }
                    ]
                }
            ],
        },
        date(2026, 12, 15),
    )
    assert offer.bookable is True
    assert offer.passenger_id == "pas_1"
    assert offer.airline_iata == "BA"
    assert offer.flight_number == "BA112"
    assert offer.price == 4321.5
    assert offer.layovers == 0
    assert offer.origin == "JFK" and offer.destination == "LHR"


def test_email_import_and_preferences(client):
    saved = client.put(
        "/api/preferences",
        json={
            "cabin": "business",
            "direct_only": True,
            "airlines": "BA,QR",
            "aircraft": "",
            "depart_after": 6,
            "depart_before": 22,
            "flexible_only": False,
            "seat": "aisle",
            "hotel_stars": 5,
            "wants_gym": True,
            "wants_spa": True,
            "home_airport": "JFK",
            "traveller_first_name": "Federico",
            "traveller_last_name": "Rossi",
            "email": "federico@example.com",
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["direct_only"] is True

    raw = (
        "Passenger: Federico Rossi\n"
        "Confirmation: KLM4421 is not it. Confirmation code: PNR88X\n"
        "Flight BA178\n"
        "JFK to LHR\n"
        "Departure 15 December 2026 18:40\n"
        "federico@example.com\n"
    )
    imported = client.post("/api/inbox/import", json={"raw_text": raw})
    assert imported.status_code == 201, imported.text
    body = imported.json()
    assert body["pnr_code"] == "PNR88X"
    assert body["flight_number"] == "BA178"
    assert body["origin"] == "JFK" and body["destination"] == "LHR"
    assert "britishairways.com" in body["manage_url"]

    cal = client.get("/api/calendar")
    assert cal.status_code == 200
    assert any(e["pnr_code"] == "PNR88X" for e in cal.json())
    guide = client.get("/api/destinations/LHR/guide")
    assert guide.status_code == 200
    assert guide.json()["hotels"]


def test_duffel_airways_link_is_refused(client):
    resp = client.get(
        "/api/flights/airline-link",
        params={
            "airline": "ZZ",
            "flight_number": "ZZ1",
            "origin": "JFK",
            "destination": "LHR",
            "date": "2026-11-23",
        },
    )
    assert resp.status_code == 404
    assert "Book in the app" in resp.json()["detail"]


def test_round_trip_is_one_fare_for_both_legs(client):
    day = date.today() + timedelta(days=40)
    back = day + timedelta(days=8)
    one_way = client.get("/api/flights/search", params={"origin": "JFK", "destination": "LHR", "date": day.isoformat()})
    both = client.get(
        "/api/flights/search",
        params={"origin": "JFK", "destination": "LHR", "date": day.isoformat(), "return_date": back.isoformat()},
    )
    assert both.status_code == 200, both.text
    body = both.json()
    assert body["return_date"] == back.isoformat()
    assert body["results"]
    one_prices = {item["id"]: item["price"] for item in one_way.json()["results"]}
    offer = body["results"][0]
    assert offer["trip_type"] == "round"
    assert offer["origin"] == "JFK" and offer["destination"] == "LHR"
    assert offer["return_origin"] == "LHR" and offer["return_destination"] == "JFK"
    assert offer["return_flight_number"]
    assert offer["return_layovers"] == 0
    for item in body["results"]:
        assert item["price"] > one_prices[item["id"]]
    too_soon = client.get(
        "/api/flights/search",
        params={"origin": "JFK", "destination": "LHR", "date": day.isoformat(), "return_date": day.isoformat()},
    )
    assert too_soon.status_code == 422


def test_preferred_airline_removes_everything_else(client):
    saved = client.put(
        "/api/preferences",
        json={
            "cabin": "business",
            "direct_only": False,
            "airlines": "XX",
            "aircraft": "",
            "depart_after": 0,
            "depart_before": 24,
            "flexible_only": False,
            "seat": "window",
            "hotel_stars": 5,
            "wants_gym": True,
            "wants_spa": True,
            "home_airport": "JFK",
            "traveller_first_name": "Federico",
            "traveller_last_name": "Rossi",
            "email": "federico@example.com",
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["seat"] == "aisle"
    day = (date.today() + timedelta(days=30)).isoformat()
    resp = client.get("/api/flights/search", params={"origin": "JFK", "destination": "LHR", "date": day})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["results"] == []
    assert "XX" in body["note"]
    restored = client.put(
        "/api/preferences",
        json={
            "cabin": "business",
            "direct_only": True,
            "airlines": "BA,QR",
            "aircraft": "",
            "depart_after": 6,
            "depart_before": 22,
            "flexible_only": False,
            "seat": "aisle",
            "hotel_stars": 5,
            "wants_gym": True,
            "wants_spa": True,
            "home_airport": "JFK",
            "traveller_first_name": "Federico",
            "traveller_last_name": "Rossi",
            "email": "federico@example.com",
        },
    )
    assert restored.status_code == 200


def test_search_rejects_bad_iata(client):
    resp = client.get("/api/flights/search", params={"origin": "J1K", "destination": "LHR", "date": "2030-01-01"})
    assert resp.status_code == 422


def test_demo_checkout_page(client):
    resp = client.get("/demo/checkout", params={"carrier": "QR", "flight": "QR701"})
    assert resp.status_code == 200
    assert "Qatar Airways" in resp.text and "Confirmation:" in resp.text


def test_register_schedules_job_24h_before_departure(client):
    departure = _future(5)
    resp = client.post("/api/bookings/register-checkin", json=_booking_payload(departure_time=departure.isoformat()))
    assert resp.status_code == 201, resp.text
    booking = resp.json()
    assert booking["check_in_status"] == "SCHEDULED"
    assert booking["pnr_code"] == "ABC123"
    assert booking["airline_iata"] == "DL"
    assert booking["flight_number"] == "DL1"
    assert booking["user_email"] == "traveller@example.com"

    job = scheduler.get_job(job_id(booking["id"]))
    assert job is not None
    assert abs((job.next_run_time - (departure - timedelta(hours=24))).total_seconds()) < 2

    listed = client.get("/api/bookings").json()
    assert any(b["id"] == booking["id"] for b in listed)


def test_register_rejects_naive_and_past_datetimes(client):
    naive = _future().replace(tzinfo=None).isoformat()
    assert client.post("/api/bookings/register-checkin", json=_booking_payload(departure_time=naive)).status_code == 422
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert client.post("/api/bookings/register-checkin", json=_booking_payload(departure_time=past)).status_code == 422


def test_webhook_marks_completed(client):
    booking = client.post(
        "/api/bookings/register-checkin", json=_booking_payload(pnr_code="WEB123", flight_number="DL44")
    ).json()
    resp = client.post(
        f"/api/webhooks/checkin-complete?booking_id={booking['id']}",
        json={"status": "completed", "boarding_pass_url": "https://cdn.flyo.example/bp.pdf", "reference": "fly_1"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["check_in_status"] == "COMPLETED"
    assert resp.json()["boarding_pass_url"] == "https://cdn.flyo.example/bp.pdf"


def test_webhook_signature_enforced(client):
    settings = get_settings()
    settings.flyo_webhook_secret = "topsecret"
    try:
        booking = client.post(
            "/api/bookings/register-checkin", json=_booking_payload(pnr_code="SIG123", flight_number="DL45")
        ).json()
        body = json.dumps({"booking_id": booking["id"], "status": "completed", "boarding_pass_url": "https://x/bp.pdf"})
        bad = client.post("/api/webhooks/checkin-complete", content=body, headers={"X-Flyo-Signature": "nope"})
        assert bad.status_code == 401
        sig = hmac.new(b"topsecret", body.encode(), hashlib.sha256).hexdigest()
        good = client.post(
            "/api/webhooks/checkin-complete",
            content=body,
            headers={"X-Flyo-Signature": f"sha256={sig}", "Content-Type": "application/json"},
        )
        assert good.status_code == 200
        assert good.json()["check_in_status"] == "COMPLETED"
    finally:
        settings.flyo_webhook_secret = ""


def test_manual_trigger_uses_flyo_primary(client):
    settings = get_settings()
    engine = get_engine()
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "completed", "id": "fly_9", "boarding_pass_url": "https://cdn/bp9.pdf"})

    settings.flyo_api_key = "test-key"
    engine.flyo._transport = httpx.MockTransport(handler)
    try:
        booking = client.post(
            "/api/bookings/register-checkin", json=_booking_payload(pnr_code="FLY999", flight_number="DL99")
        ).json()
        resp = client.post(f"/api/bookings/{booking['id']}/trigger-checkin-now")
        assert resp.status_code == 202
        updated = client.get(f"/api/bookings/{booking['id']}").json()
    finally:
        settings.flyo_api_key = ""
        engine.flyo._transport = None

    assert captured["path"] == "/v1/checkin"
    assert captured["json"]["pnr_code"] == "FLY999"
    assert captured["json"]["airline_iata"] == "DL"
    assert captured["json"]["passenger_last_name"] == "Lovelace"
    assert captured["json"]["callback_url"].endswith(f"/api/webhooks/checkin-complete?booking_id={booking['id']}")
    assert updated["check_in_status"] == "COMPLETED"
    assert updated["checkin_strategy"] == "flyo"
    assert updated["boarding_pass_url"] == "https://cdn/bp9.pdf"
    assert scheduler.get_job(job_id(booking["id"])) is None


def test_manual_trigger_without_flyo_or_bot_fails_cleanly(client):
    booking = client.post(
        "/api/bookings/register-checkin",
        json=_booking_payload(airline_iata="ZZ", flight_number="ZZ1", pnr_code="NOBOT1"),
    ).json()
    resp = client.post(f"/api/bookings/{booking['id']}/trigger-checkin-now")
    assert resp.status_code == 202
    updated = client.get(f"/api/bookings/{booking['id']}").json()
    assert updated["check_in_status"] == "FAILED"
    assert "Flyo API not configured" in updated["last_error"]
    assert "No Playwright check-in bot" in updated["last_error"]
