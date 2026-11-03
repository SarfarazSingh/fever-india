import asyncio
import importlib.util
import sqlite3
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.v1.models import Account, ImportDraft
from app.v1.schemas import Profile

spec = importlib.util.spec_from_file_location("legacy_migration", Path(__file__).resolve().parents[1] / "scripts/migrate_legacy.py")
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def test_readonly_legacy_migration_is_repeatable_and_preserves_edits(client, tmp_path, monkeypatch):
    owner = "legacy-owner@example.com"
    monkeypatch.setattr(get_settings(), "allowed_emails", owner)
    source = tmp_path / "legacy.db"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE preferences (id INTEGER, traveller_first_name TEXT, home_airport TEXT)")
        db.execute("INSERT INTO preferences VALUES (1, 'Federico', 'MAD')")
        db.execute("CREATE TABLE bookings (id INTEGER, passenger_first_name TEXT, passenger_last_name TEXT, pnr_code TEXT, flight_number TEXT, departure_time TEXT)")
        db.execute("INSERT INTO bookings VALUES (1, 'Federico', NULL, NULL, 'BA1', NULL)")
    original = source.read_bytes()
    async def run():
        async with SessionLocal() as db:
            db.add(Account(id="legacy-owner", email=owner, is_demo=False, profile=Profile().model_dump()))
            await db.commit()
        await legacy.migrate(owner, source)
        async with SessionLocal() as db:
            account = await db.get(Account, "legacy-owner")
            assert account.profile["first_name"] == "Federico"
            account.profile = {**account.profile, "home_airport": "LHR"}
            await db.commit()
        await legacy.migrate(owner, source)
        async with SessionLocal() as db:
            rows = (await db.execute(select(ImportDraft).where(ImportDraft.account_id == "legacy-owner"))).scalars().all()
            assert len(rows) == 1
            assert rows[0].data["references"] == []
            assert rows[0].data["slices"] == []
            assert rows[0].data["needs_review"] is True
            assert (await db.get(Account, "legacy-owner")).profile["home_airport"] == "LHR"
    asyncio.run(run())
    assert source.read_bytes() == original
