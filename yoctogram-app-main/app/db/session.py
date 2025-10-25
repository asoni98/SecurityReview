from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
import structlog

from app.core.config import settings

logger = structlog.stdlib.get_logger("db.session")


# https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308
class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        await logger.adebug("Connecting to database using DatabaseSessionManager")
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                await logger.aerror("Error in DatabaseSessionManager connection")
                raise

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        await logger.adebug("Creating session using DatabaseSessionManager")
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            await logger.aerror("Error in DatabaseSessionManager session")
            raise
        finally:
            await session.close()


session_manager = DatabaseSessionManager(
    settings.POSTGRES_CONNECTION_STRING.unicode_string()
)
