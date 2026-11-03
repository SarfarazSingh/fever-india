from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Profile(Model):
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    home_airport: str = Field(default="MAD", pattern=r"^[A-Z]{3}$")
    cabin: Literal["business", "first", "either"] = "business"
    direct_only: bool = False
    airlines: list[str] = Field(default_factory=list, max_length=20)
    airlines_required: bool = False
    aircraft: str = Field(default="", max_length=100)
    aircraft_required: bool = False
    depart_after: int = Field(default=0, ge=0, le=23)
    depart_before: int = Field(default=24, ge=1, le=24)
    time_required: bool = False
    flexible_only: bool = False
    allow_mixed_cabin: bool = False
    seat: Literal["aisle", "window", "none"] = "aisle"
    wants_gym: bool = True
    wants_spa: bool = True
    hotel_stars: int = Field(default=5, ge=1, le=5)
    destination_notes: str = Field(default="", max_length=1000)
    reminders: bool = True

    @field_validator("airlines")
    @classmethod
    def validate_airlines(cls, value):
        if any(not (len(x) == 2 and x.isalnum() and x == x.upper()) for x in value):
            raise ValueError("Use two-character airline codes, such as BA or QR")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_window(self):
        if self.depart_after >= self.depart_before:
            raise ValueError("Departure window must end after it starts")
        return self


class SearchRequest(Model):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    return_date: date | None = None
    preferences: Profile

    @model_validator(mode="after")
    def validate_journey(self):
        if self.origin == self.destination:
            raise ValueError("Choose two different airports")
        if self.departure_date < date.today():
            raise ValueError("Departure date is in the past")
        if self.return_date and self.return_date <= self.departure_date:
            raise ValueError("Return must be after departure")
        if (self.departure_date - date.today()).days > 365:
            raise ValueError("Search within the next 365 days")
        return self


class Condition(Model):
    allowed: bool | None = None
    penalty_amount: str | None = None
    penalty_currency: str | None = None


class FareOption(Model):
    id: str
    name: str
    total_amount: str
    currency: str
    refund: Condition
    change: Condition


class Segment(Model):
    id: str
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    origin_city: str
    destination_city: str
    origin_timezone: str
    destination_timezone: str
    departure_at: datetime
    arrival_at: datetime
    departure_local: str
    arrival_local: str
    airline: str
    airline_name: str
    operating_airline: str | None = None
    operating_airline_name: str | None = None
    flight_number: str
    aircraft: str | None = None
    cabin: str | None = None
    cabin_name: str | None = None
    seat_type: str | None = None
    checked_bags: int | None = None
    carry_on_bags: int | None = None
    origin_terminal: str | None = None
    destination_terminal: str | None = None

    @field_validator("origin_timezone", "destination_timezone")
    @classmethod
    def validate_timezone(cls, v):
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown airport timezone") from exc
        return v

    @model_validator(mode="after")
    def times(self):
        if self.departure_at.tzinfo is None or self.arrival_at.tzinfo is None:
            raise ValueError("Flight timestamps require timezone offsets")
        if self.arrival_at <= self.departure_at:
            raise ValueError("Arrival must follow departure")
        self.departure_local = self.departure_at.astimezone(
            ZoneInfo(self.origin_timezone)
        ).isoformat()
        self.arrival_local = self.arrival_at.astimezone(
            ZoneInfo(self.destination_timezone)
        ).isoformat()
        return self


class Slice(Model):
    id: str
    segments: list[Segment] = Field(min_length=1)
    duration_minutes: int
    stops: int

    @model_validator(mode="after")
    def canonical(self):
        self.stops = len(self.segments) - 1
        self.duration_minutes = int(
            (
                self.segments[-1].arrival_at - self.segments[0].departure_at
            ).total_seconds()
            / 60
        )
        return self


class Offer(Model):
    id: str
    provider: str
    live_mode: bool
    total_amount: str
    currency: str
    expires_at: datetime
    slices: list[Slice] = Field(min_length=1)
    refund: Condition = Field(default_factory=Condition)
    change: Condition = Field(default_factory=Condition)
    fare_name: str | None = None
    passenger_id: str | None = None
    card_eligible: bool = False
    identity_documents_required: bool = False
    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    fare_options: list[FareOption] = Field(default_factory=list)

    @field_validator("total_amount")
    @classmethod
    def valid_amount(cls, v):
        amount = Decimal(v)
        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid amount")
        return str(amount)


class SearchResponse(Model):
    id: str
    status: Literal["queued", "searching", "complete", "partial", "failed"]
    progress: str
    live_mode: bool
    results: list[Offer] = Field(default_factory=list)
    total_offers: int = 0
    matching_itineraries: int = 0
    next_cursor: int | None = None
    exclusions: dict[str, int] = Field(default_factory=dict)
    adjustments: list[str] = Field(default_factory=list)
    coverage: str = "Awaiting provider response"
    error: str | None = None
    request: SearchRequest


class Passenger(Model):
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    born_on: date
    phone_number: str = Field(pattern=r"^\+[1-9][0-9]{6,14}$")
    gender: Literal["m", "f"]
    title: Literal["mr", "ms", "mrs", "miss", "dr"]

    @field_validator("given_name", "family_name")
    @classmethod
    def nonblank(cls, v):
        if not v.strip():
            raise ValueError("Name must not be blank")
        return v.strip()

    @field_validator("born_on")
    @classmethod
    def adult(cls, v):
        age = (date.today() - v).days / 365.2425
        if age < 18 or age > 120:
            raise ValueError("The initial release supports adult travelers")
        return v


class CheckoutRequest(Model):
    search_id: str
    offer_id: str


class OrderRequest(Model):
    checkout_id: str
    attempt_key: str = Field(min_length=16, max_length=100)
    accepted_quote_hash: str
    passenger: Passenger
    card_id: str = Field(default="", max_length=100)
    three_d_secure_session_id: str = Field(default="", max_length=100)
    demo_outcome: Literal["success", "declined", "uncertain"] = "success"


class TripData(Model):
    passenger_name: str = Field(min_length=1, max_length=200)
    references: list[str] = Field(min_length=1, max_length=10)
    slices: list[Slice] = Field(min_length=1, max_length=8)
    payment_status: str = "external"
    ticketing_status: str = "imported"
    checkin_status: str = "not_open"
    total_amount: str | None = None
    currency: str | None = None
    documents: list[dict] = Field(default_factory=list)
    notes: str = Field(default="", max_length=3000)
    needs_review: bool = False
    cancelled: bool = False

    @field_validator("references")
    @classmethod
    def valid_refs(cls, refs):
        result = []
        for ref in refs:
            ref = ref.strip().upper()
            if not (5 <= len(ref) <= 20 and ref.isalnum()):
                raise ValueError("Booking references must be 5–20 letters or digits")
            result.append(ref)
        return list(dict.fromkeys(result))

    @model_validator(mode="after")
    def valid_itinerary(self):
        for slc in self.slices:
            for prev, nxt in zip(slc.segments, slc.segments[1:]):
                if (
                    prev.destination != nxt.origin
                    or prev.arrival_at >= nxt.departure_at
                ):
                    raise ValueError("Connections must follow the previous flight")
        return self
