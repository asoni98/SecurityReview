import asyncio
import logging

from redis.asyncio import Redis
from sqlalchemy.sql import text
import structlog
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.db.session import session_manager
from app.log import setup_logging

setup_logging(
    json_logs=settings.PRODUCTION, log_level="DEBUG" if settings.DEBUG else "INFO"
)

logger = structlog.stdlib.get_logger("prestart")

max_tries = 10
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def init_db():
    # Try to create session to check if DB is awake
    await logger.ainfo(
        "Attempting to connect to Postgres",
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        username=settings.POSTGRES_USER,
        database=settings.POSTGRES_DB,
    )
    async with session_manager.session() as db:
        await db.execute(text("SELECT 1"))

    await logger.ainfo("Postgres is awake")


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
async def init_redis():
    try:
        await logger.ainfo(
            "Connecting to redis", host=settings.REDIS_HOST, port=settings.REDIS_PORT
        )
        redis = Redis.from_url(
            settings.REDIS_CONNECTION_STRING.unicode_string(),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await logger.ainfo(f"Pinging redis", success=await redis.ping())
    except:
        await logger.awarning("Error attempting to connect to Redis")


async def main():
    await logger.ainfo("Initializing service")
    await init_db()
    await init_redis()
    await logger.ainfo("Service finished initializing")


if __name__ == "__main__":
    asyncio.run(main())
