import os
import tempfile
from pathlib import Path

import pytest

_tmp = Path(tempfile.mkdtemp(prefix="concierge-test-"))
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp / 'test.db'}"
os.environ["FLIGHT_PROVIDER"] = "mock"
os.environ["FLYO_API_KEY"] = ""
os.environ["FLYO_WEBHOOK_SECRET"] = ""
os.environ["PUBLIC_BASE_URL"] = "http://testserver"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
