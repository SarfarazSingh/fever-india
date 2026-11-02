from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import CheckInStatus


class FlightSegment(BaseModel):
    airline_iata: str
    airline_name: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime  # UTC
    arrival_time: datetime  # UTC
    departure_local: datetime  # airport wall-clock time, no offset
    arrival_local: datetime


class FlightOffer(BaseModel):
    id: str
    airline_name: str
    airline_iata: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime  # UTC
    arrival_time: datetime  # UTC
    departure_local: datetime
    arrival_local: datetime
    duration_minutes: int
    layovers: int
    layover_airports: list[str] = []
    price: float
    currency: str
    cabin_class: str = "C"
    deep_link: str
    segments: list[FlightSegment]
    provider: str


class FlightSearchResponse(BaseModel):
    origin: str
    destination: str
    date: date
    cabin_class: str = "C"
    provider: str
    count: int
    results: list[FlightOffer]


class BookingCreate(BaseModel):
    user_email: EmailStr
    passenger_first_name: str = Field(min_length=1, max_length=100)
    passenger_last_name: str = Field(min_length=1, max_length=100)
    airline_iata: str = Field(min_length=2, max_length=2)
    flight_number: str = Field(min_length=1, max_length=10)
    departure_time: datetime
    pnr_code: str = Field(min_length=6, max_length=6)

    @field_validator("user_email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("passenger_first_name", "passenger_last_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("airline_iata")
    @classmethod
    def _iata(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError("airline_iata must be a 2-character IATA code")
        return v

    @field_validator("flight_number")
    @classmethod
    def _flight_number(cls, v: str) -> str:
        v = v.strip().upper().replace(" ", "")
        if not v.isalnum():
            raise ValueError("flight_number must be alphanumeric")
        return v

    @field_validator("pnr_code")
    @classmethod
    def _pnr(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError("pnr_code must be 6 alphanumeric characters")
        return v

    @field_validator("departure_time")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("departure_time must include a timezone offset (e.g. 2026-11-20T14:30:00Z)")
        return v.astimezone(timezone.utc)


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_email: str
    passenger_first_name: str
    passenger_last_name: str
    airline_iata: str
    flight_number: str
    departure_time: datetime
    pnr_code: str
    check_in_status: CheckInStatus
    boarding_pass_url: str | None
    checkin_scheduled_for: datetime | None
    checkin_strategy: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class TriggerResponse(BaseModel):
    booking_id: int
    message: str


class CheckInWebhookPayload(BaseModel):
    booking_id: int | None = None
    pnr_code: str | None = None
    passenger_last_name: str | None = None
    reference: str | None = None
    status: str = "completed"
    boarding_pass_url: str | None = None
    error: str | None = None

    @field_validator("pnr_code")
    @classmethod
    def _pnr(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v
