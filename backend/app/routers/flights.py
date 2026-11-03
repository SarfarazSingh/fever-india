from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.routers.profile import load_preferences
from app.schemas import FlightSearchResponse
from app.services.airline_link import AirlineLinkError, resolve_airline_link
from app.services.flight_search import MissingProviderError, ProviderError, search_business_flights

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.get("/airline-link")
async def airline_link(
    airline: str = Query(..., min_length=2, max_length=3),
    flight_number: str = Query(..., min_length=3, max_length=8),
    origin: str = Query(..., min_length=3, max_length=3),
    destination: str = Query(..., min_length=3, max_length=3),
    date: date = Query(...),
    cabin: str = Query("business"),
    return_date: date | None = Query(None),
    return_flight: str = Query(""),
) -> dict:
    try:
        url = await resolve_airline_link(
            airline=airline,
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            on=date,
            cabin=cabin,
            return_on=return_date,
            return_flight=return_flight,
        )
    except AirlineLinkError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"url": url}


@router.get("/search", response_model=FlightSearchResponse)
async def search_flights(
    origin: str = Query(..., min_length=3, max_length=3, examples=["JFK"]),
    destination: str = Query(..., min_length=3, max_length=3, examples=["LHR"]),
    date: date = Query(..., description="Departure date, YYYY-MM-DD"),
    return_date: date | None = Query(None, description="Return date for a round trip"),
    use_profile: bool = Query(True, description="Apply the saved traveller preferences"),
    session: AsyncSession = Depends(get_session),
) -> FlightSearchResponse:
    prefs = await load_preferences(session) if use_profile else None
    try:
        return await search_business_flights(
            origin,
            destination,
            date,
            session=session,
            cabin=prefs.cabin if prefs else "business",
            direct_only=prefs.direct_only if prefs else False,
            airlines=prefs.airlines if prefs else "",
            aircraft=prefs.aircraft if prefs else "",
            depart_after=prefs.depart_after if prefs else 0,
            depart_before=prefs.depart_before if prefs else 24,
            flexible_only=prefs.flexible_only if prefs else False,
            return_on=return_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MissingProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
