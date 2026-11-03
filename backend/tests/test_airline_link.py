import asyncio
from datetime import date

import httpx

from app.config import Settings
from app.services.airline_link import (
    AirlineLinkError,
    _CACHE,
    pick_airline_booking,
    pick_itinerary,
    resolve_airline_link,
)


def test_pick_ignores_agencies_and_keeps_the_airline():
    options = [
        {
            "together": {
                "book_with": "Expedia",
                "airline": False,
                "price": 90,
                "booking_request": {"url": "https://www.expedia.com/go"},
            }
        },
        {
            "together": {
                "book_with": "Iberia",
                "airline": True,
                "price": 400,
                "booking_request": {"url": "https://www.google.com/travel/clk/f", "post_data": "u=1"},
            }
        },
        {
            "together": {
                "book_with": "Iberia",
                "airline": True,
                "price": 250,
                "booking_request": {"url": "https://www.google.com/travel/clk/f", "post_data": "u=cheaper"},
            }
        },
    ]
    chosen = pick_airline_booking(options)
    assert chosen["post_data"] == "u=cheaper"
    from app.services.airline_link import airline_booking_requests

    matched = airline_booking_requests(options, target_price=400)
    assert matched[0]["post_data"] == "u=1"


def test_pick_itinerary_prefers_the_same_flight_number():
    payload = {
        "best_flights": [
            {"booking_token": "other", "flights": [{"flight_number": "BA 112"}]},
            {"booking_token": "match", "flights": [{"flight_number": "IB 6251"}]},
        ]
    }
    assert pick_itinerary(payload, "IB6251", "IB")["booking_token"] == "match"


def test_meta_refresh_is_the_airline_page():
    from app.services.airline_link import _airline_url_in_html

    page = (
        "<html><head><meta content=\"0;url='https://www.britishairways.com/nx/b/book?"
        "ond1=JFK-LHR&amp;ad=1'\"></head></html>"
    )
    url = _airline_url_in_html(page, "BA")
    assert url is not None
    assert url.startswith("https://www.britishairways.com/")
    assert "&amp;" not in url
    assert _airline_url_in_html(page, "IB") is None


def test_follow_lands_on_the_airline():
    url = asyncio.run(_resolve(_ok_transport))
    assert url == "https://www.iberia.com/us/flight-search-engine/"


def test_rejects_a_404_on_the_airline():
    try:
        asyncio.run(_resolve(_missing_transport))
    except AirlineLinkError as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected the missing airline page to be rejected")


def test_rejects_an_economy_airline_page():
    try:
        asyncio.run(_resolve(_economy_transport))
    except AirlineLinkError as exc:
        assert "business or first" in str(exc)
    else:
        raise AssertionError("expected an economy page to be rejected")


def test_rejects_a_page_that_stays_on_google():
    try:
        asyncio.run(_resolve(_google_transport))
    except AirlineLinkError as exc:
        assert "booking page" in str(exc)
    else:
        raise AssertionError("expected a Google page to be rejected")


def test_duffel_airways_has_no_site():
    try:
        asyncio.run(
            resolve_airline_link(
                airline="ZZ",
                flight_number="ZZ1",
                origin="JFK",
                destination="LHR",
                on=date(2026, 11, 23),
            )
        )
    except AirlineLinkError as exc:
        assert "Book in the app" in str(exc)
    else:
        raise AssertionError("expected Duffel Airways to be refused")


def _resolve(transport_factory):
    _CACHE.clear()
    settings = Settings(serpapi_api_key="test-key", public_base_url="http://test")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport_factory), follow_redirects=False) as client:
            return await resolve_airline_link(
                airline="IB",
                flight_number="IB6251",
                origin="JFK",
                destination="LHR",
                on=date(2026, 11, 23),
                cabin="business",
                settings=settings,
                client=client,
            )

    return run()


def _search_response(request: httpx.Request) -> httpx.Response | None:
    url = str(request.url)
    if "serpapi.com" not in url:
        return None
    if "booking_token" in url:
        return httpx.Response(
            200,
            json={
                "booking_options": [
                    {
                        "together": {
                            "book_with": "Expedia",
                            "airline": False,
                            "price": 90,
                            "booking_request": {"url": "https://www.expedia.com/go"},
                        }
                    },
                    {
                        "together": {
                            "book_with": "Iberia",
                            "airline": True,
                            "price": 400,
                            "booking_request": {"url": "https://www.google.com/travel/clk/f", "post_data": "u=abc"},
                        }
                    },
                ]
            },
        )
    return httpx.Response(
        200,
        json={"best_flights": [{"booking_token": "tok", "flights": [{"flight_number": "IB 6251"}]}]},
    )


def _ok_transport(request: httpx.Request) -> httpx.Response:
    found = _search_response(request)
    if found:
        return found
    if request.method == "POST":
        return httpx.Response(302, headers={"location": "https://www.iberia.com/us/flight-search-engine/"})
    if "iberia.com" in str(request.url):
        return httpx.Response(200, text="book")
    return httpx.Response(500, text=str(request.url))


def _missing_transport(request: httpx.Request) -> httpx.Response:
    found = _search_response(request)
    if found:
        return found
    if request.method == "POST":
        return httpx.Response(302, headers={"location": "https://www.iberia.com/us/flights/"})
    return httpx.Response(404, text="Not Found")


def _economy_transport(request: httpx.Request) -> httpx.Response:
    found = _search_response(request)
    if found:
        return found
    if request.method == "POST":
        return httpx.Response(302, headers={"location": "https://www.iberia.com/us/flights/?cabin=economy"})
    return httpx.Response(200, text="economy")


def _google_transport(request: httpx.Request) -> httpx.Response:
    found = _search_response(request)
    if found:
        return found
    return httpx.Response(200, text="<html>Still on Google Flights</html>")
