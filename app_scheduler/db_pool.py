#!/usr/bin/env python3
"""
Database connection pooling for efficient connection reuse.
Eliminates the overhead of creating new connections on every cycle.
"""

import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None

async def get_pool():
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("PGHOST"),
            port=int(os.getenv("PGPORT", 5432)),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            database=os.getenv("PGDATABASE"),
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _pool

async def get_connection():
    """Get a connection from the pool."""
    pool = await get_pool()
    return await pool.acquire()

async def release_connection(conn):
    """Return a connection to the pool."""
    pool = await get_pool()
    await pool.release(conn)

async def close_pool():
    """Close the connection pool (for cleanup)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
