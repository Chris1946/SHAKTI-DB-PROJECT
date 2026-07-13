"""
PulseTrace Backend — Database Connection Management

Provides async SQLAlchemy engine and session factory with
connection pooling. Uses the dependency injection pattern
for FastAPI route handlers.

Usage in routes:
    from app.database.connection import get_db

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

logger = logging.getLogger(__name__)

# ---- Engine ----
# The engine manages a pool of database connections.
# asyncpg is the async PostgreSQL driver.
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.db_echo,
)

# ---- Session Factory ----
# Each request gets its own session from this factory.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session.

    The session is automatically closed when the request completes.
    Commits must be called explicitly in service functions.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict:
    """Run a simple health check query against the database.

    Returns:
        dict with 'status' ('healthy' or 'unhealthy') and 'latency_ms'.
    """
    import time

    start = time.monotonic()
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        latency = (time.monotonic() - start) * 1000
        return {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.error("Database health check failed: %s", exc)
        return {
            "status": "unhealthy",
            "latency_ms": round(latency, 2),
            "error": str(exc),
        }


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool.

    Called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connection pool disposed")
