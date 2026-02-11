from fastapi import APIRouter, Query, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta
import asyncpg

from database import get_pool
from models.analytics import (
    KeywordHit, HourlyPoint, TalkgroupHit, DashboardMetrics,
    QualityDistribution, ApiMetricsSummary
)
from models.calls import CallMetadata

router = APIRouter()


def transform_dashboard_metrics(metrics: DashboardMetrics) -> Dict[str, Any]:
    """
    Transform dashboard metrics to include frontend-expected field names.

    Adds camelCase aliases:
    - 'active_playlists' → 'feedCount', 'activeFeeds'
    - 'total_calls_24h' → 'recentCalls'
    - 'transcripts_today' → 'transcriptsToday'
    - Keeps original snake_case fields for backward compatibility
    """
    # Convert Pydantic model to dict
    result = metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics.dict()

    # Add camelCase aliases
    result['feedCount'] = result.get('active_playlists', 0)
    result['activeFeeds'] = result.get('active_playlists', 0)
    result['recentCalls'] = result.get('total_calls_24h', 0)
    result['transcriptsToday'] = result.get('transcripts_today', 0)

    return result


@router.get("/dashboard")
async def get_dashboard_metrics(
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get comprehensive dashboard metrics."""
    async with pool.acquire() as conn:
        # Get total calls in last 24h
        total_calls = await conn.fetchval(
            "SELECT COUNT(*) FROM bcfy_calls_raw WHERE started_at > NOW() - INTERVAL '24 hours'"
        )

        # Get active playlists
        active_playlists = await conn.fetchval(
            "SELECT COUNT(*) FROM bcfy_playlists WHERE sync = TRUE"
        )

        # Get transcripts today
        transcripts_today = await conn.fetchval(
            "SELECT COUNT(*) FROM transcripts WHERE created_at >= CURRENT_DATE"
        )

        # Get avg transcription confidence
        avg_confidence = await conn.fetchval(
            "SELECT AVG(confidence) FROM transcripts WHERE created_at >= CURRENT_DATE"
        ) or 0.0

        # Get processing queue size
        queue_size = await conn.fetchval(
            "SELECT COUNT(*) FROM processing_state WHERE status = 'queued'"
        ) or 0

        # Get API calls today (with fallback if table doesn't exist)
        try:
            api_calls_today = await conn.fetchval(
                "SELECT COUNT(*) FROM api_call_metrics WHERE timestamp >= CURRENT_DATE"
            ) or 0
        except asyncpg.UndefinedTableError:
            api_calls_today = 0

        # Get recent calls
        recent_calls = await conn.fetch(
            """
            SELECT call_uid, feed_id, tg_id, started_at, duration_ms
            FROM bcfy_calls_raw
            ORDER BY started_at DESC
            LIMIT 5
            """
        )

        # Get top talkgroups
        top_talkgroups = await conn.fetch(
            """
            SELECT tg_id, COUNT(*) as count
            FROM bcfy_calls_raw
            WHERE started_at > NOW() - INTERVAL '24 hours' AND tg_id IS NOT NULL
            GROUP BY tg_id
            ORDER BY count DESC
            LIMIT 10
            """
        )

    metrics = DashboardMetrics(
        total_calls_24h=total_calls or 0,
        active_playlists=active_playlists or 0,
        transcripts_today=transcripts_today or 0,
        avg_transcription_confidence=float(avg_confidence),
        processing_queue_size=queue_size,
        api_calls_today=api_calls_today,
        recent_calls=[dict(row) for row in recent_calls],
        top_talkgroups=[
            TalkgroupHit(tg_id=row["tg_id"], count=row["count"])
            for row in top_talkgroups
        ]
    )

    return transform_dashboard_metrics(metrics)


@router.get("/hourly", response_model=List[HourlyPoint])
async def get_hourly_activity(
    hours: int = Query(24, ge=1, le=168),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get hourly call activity."""
    query = """
        SELECT
            TO_CHAR(DATE_TRUNC('hour', started_at), 'HH24:00') as hour,
            COUNT(*) as count
        FROM bcfy_calls_raw
        WHERE started_at > NOW() - ($1::int * INTERVAL '1 hour')
        GROUP BY DATE_TRUNC('hour', started_at)
        ORDER BY DATE_TRUNC('hour', started_at)
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, hours)

    return [HourlyPoint(hour=row["hour"], count=row["count"]) for row in rows]


@router.get("/talkgroups/top", response_model=List[TalkgroupHit])
async def get_top_talkgroups(
    limit: int = Query(10, ge=1, le=100),
    period: str = Query("24h"),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get top active talkgroups."""
    # Convert period to hours for parameterized query
    hours_map = {
        "1h": 1,
        "24h": 24,
        "7d": 168,
    }
    interval_hours = hours_map.get(period, 24)

    query = """
        SELECT tg_id, COUNT(*) as count
        FROM bcfy_calls_raw
        WHERE started_at > NOW() - ($1::int * INTERVAL '1 hour') AND tg_id IS NOT NULL
        GROUP BY tg_id
        ORDER BY count DESC
        LIMIT $2
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, interval_hours, limit)

    return [TalkgroupHit(tg_id=row["tg_id"], count=row["count"]) for row in rows]


@router.get("/keywords", response_model=List[KeywordHit])
async def get_keyword_hits(
    limit: int = Query(10, ge=1, le=100),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get keyword hit counts (placeholder - needs keywords table)."""
    # TODO: Implement when keywords table/system is available
    return []


@router.get("/transcription-quality", response_model=QualityDistribution)
async def get_transcription_quality(
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get transcription quality distribution."""
    query = """
        SELECT
            SUM(CASE WHEN confidence > 0.85 THEN 1 ELSE 0 END) as excellent,
            SUM(CASE WHEN confidence > 0.7 AND confidence <= 0.85 THEN 1 ELSE 0 END) as good,
            SUM(CASE WHEN confidence > 0.5 AND confidence <= 0.7 THEN 1 ELSE 0 END) as fair,
            SUM(CASE WHEN confidence <= 0.5 THEN 1 ELSE 0 END) as poor
        FROM transcripts
        WHERE created_at >= CURRENT_DATE
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query)

    return QualityDistribution(
        excellent=row["excellent"] or 0,
        good=row["good"] or 0,
        fair=row["fair"] or 0,
        poor=row["poor"] or 0
    )
