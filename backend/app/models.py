import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UTCDateTime(TypeDecorator):
    """Timezone-aware datetime that is always stored and returned in UTC.

    SQLite has no native timezone support, so values come back naive; this
    re-attaches UTC on the way out.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CheckInStatus(str, enum.Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FlightSearch(Base):
    __tablename__ = "flight_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)
    departure_date: Mapped[date] = mapped_column(Date)
    cabin_class: Mapped[str] = mapped_column(String(1), default="C")
    provider: Mapped[str] = mapped_column(String(16), default="mock")
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_email: Mapped[str] = mapped_column(String(255), index=True)
    passenger_first_name: Mapped[str] = mapped_column(String(100))
    passenger_last_name: Mapped[str] = mapped_column(String(100))
    airline_iata: Mapped[str] = mapped_column(String(2))
    flight_number: Mapped[str] = mapped_column(String(10))
    departure_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    pnr_code: Mapped[str] = mapped_column(String(6), index=True)
    check_in_status: Mapped[CheckInStatus] = mapped_column(
        Enum(CheckInStatus, native_enum=False, length=16),
        default=CheckInStatus.PENDING,
        index=True,
    )
    boarding_pass_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    checkin_scheduled_for: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    checkin_strategy: Mapped[str | None] = mapped_column(String(16), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
