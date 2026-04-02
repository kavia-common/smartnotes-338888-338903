from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an async SQLAlchemy engine."""
    return create_async_engine(
        settings.postgres_url,
        pool_pre_ping=True,
        future=True,
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker."""
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


# PUBLIC_INTERFACE
async def get_db_session(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession.

    Contract:
      - yields a valid AsyncSession
      - rolls back if an exception bubbles up
      - always closes the session
    """
    async with sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
