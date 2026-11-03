import os
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="concierge-test-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp / 'test.db'}"
os.environ["FLIGHT_PROVIDER"] = "mock"
os.environ["DUFFEL_ACCESS_TOKEN"] = "duffel_test_unit_test_only"
os.environ["FLYO_API_KEY"] = ""
os.environ["FLYO_WEBHOOK_SECRET"] = ""
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["ENVIRONMENT"] = "test"
os.environ["LEGACY_API_ENABLED"] = "true"
os.environ["AUTO_CHECKIN_ENABLED"] = "true"
os.environ["DEMO_ENABLED"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        data = c.post("/api/v1/auth/demo").json()
        c.headers["x-csrf-token"] = data["csrf_token"]
        yield c
