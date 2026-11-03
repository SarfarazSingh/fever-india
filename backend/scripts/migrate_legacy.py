"""Repeatable, owner-scoped legacy migration, optionally from a read-only SQLite backup.

Run after the owner signs in. Never guess missing itinerary fields or references.
"""

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.config import get_settings
from app.database import SessionLocal
from app.models import Booking, Preferences
from app.v1.models import Account, EventReceipt, ImportDraft
from app.v1.schemas import Profile


def read_sqlite(path: Path):
    path = path.resolve(strict=True)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        names = {r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        preferences = source.execute("SELECT * FROM preferences WHERE id=1").fetchone() if "preferences" in names else None
        bookings = [dict(r) for r in source.execute("SELECT * FROM bookings")] if "bookings" in names else []
        return dict(preferences) if preferences else None, bookings


def preference_profile(old):
    mapping = {
        "traveller_first_name": "first_name", "traveller_last_name": "last_name",
        "home_airport": "home_airport", "cabin": "cabin", "direct_only": "direct_only",
        "aircraft": "aircraft", "depart_after": "depart_after", "depart_before": "depart_before",
        "flexible_only": "flexible_only", "wants_gym": "wants_gym", "wants_spa": "wants_spa",
    }
    data = {target: old[source] for source, target in mapping.items() if old.get(source) is not None}
    if old.get("airlines"):
        data["airlines"] = [a.strip() for a in old["airlines"].split(",") if a.strip()]
    return Profile.model_validate(data).model_dump()


async def migrate(email: str, source_sqlite: Path | None = None):
    if email not in get_settings().email_allowlist:
        raise RuntimeError("The owner must be in ALLOWED_EMAILS")
    external = read_sqlite(source_sqlite) if source_sqlite else None
    async with SessionLocal() as db:
        account = (await db.execute(select(Account).where(Account.email == email))).scalar_one_or_none()
        if not account or account.is_demo:
            raise RuntimeError("The owner must sign in before migration")
        if external is not None:
            old, bookings = external
        else:
            previous = await db.get(Preferences, 1)
            old = {c.name: getattr(previous, c.name) for c in Preferences.__table__.columns} if previous else None
            bookings = [{c.name: getattr(row, c.name) for c in Booking.__table__.columns} for row in (await db.execute(select(Booking))).scalars()]
        receipt_id = "legacy-profile-" + account.id
        if old and not await db.get(EventReceipt, receipt_id):
            try:
                account.profile = preference_profile(old)
                db.add(EventReceipt(id=receipt_id))
            except ValueError:
                print("Legacy preferences require review; current profile retained")
        migrated = 0
        for booking in bookings:
            source_id = "legacy-" + str(booking["id"])
            exists = (await db.execute(select(ImportDraft.id).where(
                ImportDraft.account_id == account.id, ImportDraft.source_id == source_id,
            ))).first()
            if exists:
                continue
            name = " ".join(str(booking.get(k) or "").strip() for k in ["passenger_first_name", "passenger_last_name"]).strip()
            reference = booking.get("pnr_code")
            departure = booking.get("departure_time")
            db.add(ImportDraft(
                account_id=account.id, source="legacy", source_id=source_id,
                data={
                    "passenger_name": name or None,
                    "references": [reference] if reference else [],
                    "slices": [],
                    "notes": "Legacy flight: " + str(booking.get("flight_number") or "not recorded") + "; departure as recorded: " + str(departure or "not recorded"),
                    "needs_review": True,
                },
                issues=["Legacy records did not retain complete itinerary data. Verify references and add every segment and arrival time before confirming."],
            ))
            migrated += 1
        await db.commit()
        print(f"Created {migrated} owner-scoped review drafts; source records retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--source-sqlite", type=Path)
    args = parser.parse_args()
    asyncio.run(migrate(args.email.strip().lower(), args.source_sqlite))
