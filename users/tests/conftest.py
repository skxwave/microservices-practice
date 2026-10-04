import os

os.environ.setdefault("DB_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402

from main import app  # noqa: E402
from src import get_db  # noqa: E402


@pytest.fixture
def db():
    session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
