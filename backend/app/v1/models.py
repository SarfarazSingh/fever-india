from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import UTCDateTime, utcnow


def uid() -> str:
    return str(uuid4())


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)


class OAuthLoginAttempt(Base):
    __tablename__ = "oauth_login_attempts"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    verifier_ciphertext: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class SearchRecord(Base):
    __tablename__ = "search_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    request: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, index=True
    )


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (UniqueConstraint("account_id", "dedupe_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(200))
    departure_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="confirmed")
    source: Mapped[str] = mapped_column(String(24), default="manual")
    itinerary: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow
    )


class ImportDraft(Base):
    __tablename__ = "import_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    source: Mapped[str] = mapped_column(String(24), default="paste")
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data: Mapped[dict] = mapped_column(JSON)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    confirmed_trip_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Checkout(Base):
    __tablename__ = "checkout_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    offer: Mapped[dict] = mapped_column(JSON)
    quote_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    state: Mapped[str] = mapped_column(String(30), default="review")
    attempt_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    provider_order_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    trip_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class MailConnection(Base):
    __tablename__ = "mail_connections"
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    state_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), default="disconnected")
    last_synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    forwarding_token: Mapped[str] = mapped_column(String(64), unique=True)
    verifier_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_state: Mapped[dict] = mapped_column(JSON, default=dict)


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    trip_id: Mapped[str | None] = mapped_column(ForeignKey("trips.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(24), default="trip_reminder")
    state: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)



class EventReceipt(Base):
    __tablename__ = "event_receipts"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Usage(Base):
    __tablename__ = "daily_usage"
    __table_args__ = (UniqueConstraint("account_id", "day", "kind"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[str] = mapped_column(String(80), index=True)
    day: Mapped[str] = mapped_column(String(10))
    kind: Mapped[str] = mapped_column(String(30))
    count: Mapped[int] = mapped_column(Integer, default=0)


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="requested")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
