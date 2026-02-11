from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncpg

from database import get_pool
from models.calls import CallMetadata, HourlyStats, FeedStats
from models.auth import CurrentUser
from auth.dependencies import require_auth

router = APIRouter()


def transform_call_response(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform call database row to frontend-expected format.

    Adds:
    - 'timestamp' field mapped from 'started_at'
    - Keeps original 'started_at' for backward compatibility
    """
    result = dict(row)

    # Add 'timestamp' alias for frontend compatibility
    if 'started_at' in result and result['started_at']:
        result['timestamp'] = result['started_at'].isoformat() if hasattr(result['started_at'], 'isoformat') else str(result['started_at'])

    return result


@router.get("", response_model=List[CallMetadata])
async def list_calls(
    feed_id: Optional[int] = Query(None),
    tg_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List recent calls with optional filtering."""
    query = "SELECT * FROM bcfy_calls_raw WHERE 1=1"
    params = []
    param_count = 1

    if feed_id is not None:
        query += f" AND feed_id = ${param_count}"
        params.append(feed_id)
        param_count += 1

    if tg_id is not None:
        query += f" AND tg_id = ${param_count}"
        params.append(tg_id)
        param_count += 1

    query += f" ORDER BY started_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [transform_call_response(dict(row)) for row in rows]


@router.get("/{call_uid}", response_model=CallMetadata)
async def get_call(
    call_uid: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific call by UID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bcfy_calls_raw WHERE call_uid = $1",
            call_uid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Call not found")

    return transform_call_response(dict(row))


@router.get("/stats/hourly", response_model=List[HourlyStats])
async def hourly_call_stats(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get hourly call volume for the last 24 hours."""
    query = """
        SELECT
            DATE_TRUNC('hour', started_at) as hour,
            COUNT(*) as count
        FROM bcfy_calls_raw
        WHERE started_at > NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', started_at)
        ORDER BY hour
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    return [{"hour": row["hour"], "count": row["count"]} for row in rows]


@router.get("/stats/by-feed", response_model=List[FeedStats])
async def feed_stats(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get call statistics grouped by feed."""
    query = """
        SELECT
            feed_id,
            COUNT(*) as count,
            AVG(CAST(duration_ms AS FLOAT)) as avg_duration_ms
        FROM bcfy_calls_raw
        WHERE feed_id IS NOT NULL
            AND started_at > NOW() - INTERVAL '24 hours'
        GROUP BY feed_id
        ORDER BY count DESC
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    return [dict(row) for row in rows]
