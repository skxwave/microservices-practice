from redis.asyncio import Redis

from src.config import settings

client: Redis | None = None


async def start_redis():
    global client
    client = Redis.from_url(settings.redis_url)


async def stop_redis():
    await client.aclose()


def get_redis() -> Redis:
    return client
