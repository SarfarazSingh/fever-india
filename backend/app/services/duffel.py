"""Thin async client for the Duffel Flights API."""

from __future__ import annotations

from datetime import date, datetime

import httpx

from app.config import Settings

_shared_http: httpx.AsyncClient | None = None


async def close_duffel_client() -> None:
    global _shared_http
    if _shared_http is not None:
        await _shared_http.aclose()
        _shared_http = None


class DuffelError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DuffelClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        if not settings.duffel_access_token:
            raise DuffelError("DUFFEL_ACCESS_TOKEN is not set")
        self._settings = settings
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.duffel_access_token}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.duffel_base_url,
            headers=self._headers(),
            timeout=httpx.Timeout(90.0, connect=10.0),
            transport=self._transport,
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        global _shared_http
        if self._transport is not None:
            async with self._client() as client:
                try:
                    resp = await client.request(method, path, **kwargs)
                except httpx.HTTPError as exc:
                    raise DuffelError("Flight provider connection failed") from exc
        else:
            if _shared_http is None or _shared_http.is_closed:
                _shared_http = httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=8.0),
                                               limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))
            try:
                resp = await _shared_http.request(method, self._settings.duffel_base_url + path,
                                                 headers=self._headers(), **kwargs)
            except httpx.HTTPError as exc:
                raise DuffelError("Flight provider connection failed") from exc
        if resp.status_code >= 400:
            raise DuffelError(_format_error(resp), resp.status_code)
        try:
            return resp.json()
        except ValueError as exc:
            raise DuffelError("Duffel returned a non-JSON response") from exc

    async def search_offers(
        self,
        origin: str,
        destination: str,
        on: date,
        *,
        cabin: str = "business",
        return_on: date | None = None,
        max_connections: int = 1,
        departure_window: tuple[int, int] | None = None,
    ) -> dict:
        slices = [{"origin": origin, "destination": destination, "departure_date": on.isoformat()}]
        if return_on:
            slices.append({"origin": destination, "destination": origin, "departure_date": return_on.isoformat()})
        if departure_window:
            for slc in slices:
                slc["departure_time"] = {"from": f"{departure_window[0]:02d}:00", "to": f"{min(23,departure_window[1]-1):02d}:59"}
        body = {
            "data": {
                "slices": slices,
                "passengers": [{"type": "adult"}],
                "cabin_class": "first" if cabin == "first" else "business",
                "max_connections": max_connections,
            }
        }
        return await self._request("POST", "/air/offer_requests", params={"return_offers": "true", "supplier_timeout": 15000}, json=body)

    async def get_offer(self, offer_id: str) -> dict:
        payload = await self._request("GET", f"/air/offers/{offer_id}")
        return payload["data"]

    async def create_order(
        self,
        *,
        offer_id: str,
        passenger_id: str,
        given_name: str,
        family_name: str,
        email: str,
        phone_number: str,
        born_on: date,
        gender: str,
        title: str,
        amount: str,
        currency: str,
    ) -> dict:
        body = {
            "data": {
                "type": "instant",
                "selected_offers": [offer_id],
                "payments": [{"type": "balance", "amount": amount, "currency": currency}],
                "passengers": [
                    {
                        "id": passenger_id,
                        "given_name": given_name,
                        "family_name": family_name,
                        "born_on": born_on.isoformat(),
                        "gender": gender,
                        "title": title,
                        "email": email,
                        "phone_number": phone_number,
                    }
                ],
            }
        }
        payload = await self._request("POST", "/air/orders", json=body)
        return payload["data"]


def _format_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        errors = body.get("errors") or []
        if errors:
            first = errors[0]
            code = first.get("code") or first.get("type") or "error"
            message = first.get("message") or first.get("title") or str(first)
            return f"Duffel {resp.status_code} {code}: {message}"
    except ValueError:
        pass
    return f"Duffel returned HTTP {resp.status_code}: {resp.text[:300]}"


def parse_duffel_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
