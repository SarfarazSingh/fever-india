from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

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
    aircraft: str | None = None


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
    bookable: bool = False
    passenger_id: str | None = None
    expires_at: datetime | None = None
    refundable: bool | None = None
    manage_url: str | None = None
    trip_type: str = "oneway"
    return_flight_number: str | None = None
    return_origin: str | None = None
    return_destination: str | None = None
    return_departure_local: datetime | None = None
    return_arrival_local: datetime | None = None
    return_duration_minutes: int | None = None
    return_layovers: int = 0


class FlightSearchResponse(BaseModel):
    origin: str
    destination: str
    date: date
    return_date: date | None = None
    cabin_class: str = "C"
    provider: str
    count: int
    note: str = ""
    results: list[FlightOffer]


class BookingCreate(BaseModel):
    user_email: EmailStr
    passenger_first_name: str = Field(min_length=1, max_length=100)
    passenger_last_name: str = Field(min_length=1, max_length=100)
    airline_iata: str = Field(min_length=2, max_length=2)
    flight_number: str = Field(min_length=1, max_length=10)
    origin: str | None = None
    destination: str | None = None
    departure_time: datetime
    pnr_code: str = Field(min_length=5, max_length=16)

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
            raise ValueError("pnr_code must be 5–16 alphanumeric characters")
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
    origin: str | None = None
    destination: str | None = None
    manage_url: str | None = None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _fill_manage_url(self):
        if not self.manage_url:
            from app.services.links import airline_manage_url

            self.manage_url = airline_manage_url(self.airline_iata, self.pnr_code)
        return self


class PreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cabin: str = "business"
    direct_only: bool = False
    airlines: str = ""
    aircraft: str = ""
    depart_after: int = 0
    depart_before: int = 24
    flexible_only: bool = False
    seat: str = "aisle"
    hotel_stars: int = 5
    wants_gym: bool = True
    wants_spa: bool = True
    home_airport: str = "JFK"
    traveller_first_name: str = ""
    traveller_last_name: str = ""
    email: str = ""


class PreferencesUpdate(PreferencesRead):
    @field_validator("cabin")
    @classmethod
    def _cabin(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"business", "first", "either"}:
            raise ValueError("cabin must be business, first, or either")
        return v

    @field_validator("seat")
    @classmethod
    def _seat(cls, v: str) -> str:
        del v
        return "aisle"

    @field_validator("home_airport")
    @classmethod
    def _home(cls, v: str) -> str:
        v = v.strip().upper()
        if v and (len(v) != 3 or not v.isalpha()):
            raise ValueError("home_airport must be a 3-letter IATA code")
        return v

    @field_validator("airlines", "aircraft")
    @classmethod
    def _listish(cls, v: str) -> str:
        return v.strip().upper() if v else ""

    @field_validator("depart_after", "depart_before")
    @classmethod
    def _hour(cls, v: int) -> int:
        if v < 0 or v > 24:
            raise ValueError("hours must be between 0 and 24")
        return v


class EmailImport(BaseModel):
    raw_text: str = Field(min_length=20, max_length=20000)


class CalendarEvent(BaseModel):
    booking_id: int
    date: date
    title: str
    detail: str
    pnr_code: str
    destination: str | None
    manage_url: str | None


class GuidePlace(BaseModel):
    name: str
    kind: str
    area: str
    why: str
    url: str


class DestinationGuide(BaseModel):
    airport: str
    city: str
    hotels: list[GuidePlace]
    restaurants: list[GuidePlace]


class PlaceOrderRequest(BaseModel):
    offer_id: str = Field(min_length=8, max_length=64)
    passenger_id: str | None = None
    user_email: EmailStr
    passenger_first_name: str = Field(min_length=1, max_length=100)
    passenger_last_name: str = Field(min_length=1, max_length=100)
    born_on: date | None = None
    gender: str = "m"
    title: str = "mr"
    phone_number: str = "+447911123456"

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

    @field_validator("gender")
    @classmethod
    def _gender(cls, v: str) -> str:
        v = v.strip().lower()[:1]
        if v not in {"m", "f"}:
            raise ValueError("gender must be m or f")
        return v

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"mr", "ms", "mrs", "miss", "mx"}:
            raise ValueError("title must be mr, ms, mrs, miss or mx")
        return v


class PlaceOrderResponse(BaseModel):
    booking: BookingRead
    duffel_order_id: str
    live_mode: bool


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
