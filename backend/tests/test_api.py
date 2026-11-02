import hashlib
import hmac
import json
from datetime import date, datetime, timedelta, timezone

import httpx

from app.config import get_settings
from app.services.check_in import get_engine
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
    assert resp.json()["scheduler_running"] is True


def test_mock_search_returns_business_offers(client):
    day = (date.today() + timedelta(days=30)).isoformat()
    resp = client.get("/api/flights/search", params={"origin": "jfk", "destination": "LHR", "date": day})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["count"] == len(body["results"]) > 0
    prices = [o["price"] for o in body["results"]]
    assert prices == sorted(prices)
    for offer in body["results"]:
        assert offer["cabin_class"] == "C"
        assert offer["deep_link"].startswith("http://testserver/demo/checkout?")
        assert offer["origin"] == "JFK" and offer["destination"] == "LHR"
        assert offer["layovers"] == len(offer["segments"]) - 1


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
