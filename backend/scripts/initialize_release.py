"""Serialize API/worker deployment hooks on their PostgreSQL session connection."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
from app.config import get_settings


def main():
    settings = get_settings()
    if not settings.production:
        raise RuntimeError("Release initialization requires staging or production")
    root = Path(__file__).resolve().parents[1]
    steps = [
        ("migrations", ["-m", "alembic", "upgrade", "head"]),
        ("private storage", ["scripts/secure_database.py"]),
        ("durable queue", ["scripts/init_queue.py"]),
        ("pilot readiness", ["scripts/release_preflight.py"]),
    ]
    with psycopg.connect(settings.psycopg_dsn, autocommit=True) as db:
        db.execute("SELECT pg_advisory_lock(791230018)")
        try:
            for name, args in steps:
                result = subprocess.run(
                    [sys.executable, *args], cwd=root, capture_output=True, text=True
                )
                if result.returncode:
                    raise RuntimeError(f"Release initialization failed during {name}")
                print(f"Release {name}: ready", flush=True)
        finally:
            db.execute("SELECT pg_advisory_unlock(791230018)")


if __name__ == "__main__":
    main()
