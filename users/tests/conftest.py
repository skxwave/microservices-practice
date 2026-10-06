import os

os.environ.setdefault("DB_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402

from main import app  # noqa: E402
from src import get_db  # noqa: E402
from src.redis_client import get_redis  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.keys = {}

    async def exists(self, key):
        return int(key in self.keys)

    async def set(self, key, value, ex=None, nx=False):
        if nx and key in self.keys:
            return None
        self.keys[key] = value
        return True


@pytest.fixture
def db():
    session = AsyncMock()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    app.dependency_overrides.clear()


@pytest.fixture
def redis():
    fake = FakeRedis()
    app.dependency_overrides[get_redis] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_redis, None)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
