from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas import FlightSearchResponse
from app.services.flight_search import search_business_flights

router = APIRouter(prefix="/api/flights", tags=["flights"])


@router.get("/search", response_model=FlightSearchResponse)
async def search_flights(
    origin: str = Query(..., min_length=3, max_length=3, examples=["JFK"]),
    destination: str = Query(..., min_length=3, max_length=3, examples=["LHR"]),
    date: date = Query(..., description="Departure date, YYYY-MM-DD"),
    session: AsyncSession = Depends(get_session),
) -> FlightSearchResponse:
    try:
        return await search_business_flights(origin, destination, date, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
