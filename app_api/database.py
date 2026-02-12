import asyncio

import asyncpg
from config import settings

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool (async-safe with double-check lock)."""
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        # Double-check after acquiring lock to avoid duplicate pool creation
        if _pool is not None:
            return _pool
        _pool = await asyncpg.create_pool(
            host=settings.PGHOST,
            port=settings.PGPORT,
            user=settings.PGUSER,
            password=settings.PGPASSWORD,
            database=settings.PGDATABASE,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    return _pool


async def close_pool():
    """Close the database connection pool."""
    global _pool
    async with _pool_lock:
        if _pool is not None:
            await _pool.close()
            _pool = None
