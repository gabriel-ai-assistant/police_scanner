
import asyncpg
from database import get_pool
from fastapi import APIRouter, Depends, Query
from models.analytics import ApiMetricsSummary
from models.system import ProcessingStateSummary, SystemLog

router = APIRouter()


@router.get("/logs", response_model=list[SystemLog])
async def get_system_logs(
    component: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get recent system logs."""
    query = "SELECT * FROM system_logs WHERE 1=1"
    params = []
    param_count = 1

    if component:
        query += f" AND component = ${param_count}"
        params.append(component)
        param_count += 1

    if severity:
        query += f" AND severity = ${param_count}"
        params.append(severity)
        param_count += 1

    query += f" ORDER BY timestamp DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]


@router.get("/processing-state", response_model=ProcessingStateSummary)
async def get_processing_state(
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get processing pipeline state summary."""
    query = """
        SELECT
            SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END) as queued,
            SUM(CASE WHEN status = 'downloaded' THEN 1 ELSE 0 END) as downloaded,
            SUM(CASE WHEN status = 'transcribed' THEN 1 ELSE 0 END) as transcribed,
            SUM(CASE WHEN status = 'indexed' THEN 1 ELSE 0 END) as indexed,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
            COUNT(*) as total
        FROM processing_state
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query)

    return ProcessingStateSummary(
        queued=row["queued"] or 0,
        downloaded=row["downloaded"] or 0,
        transcribed=row["transcribed"] or 0,
        indexed=row["indexed"] or 0,
        error=row["error"] or 0,
        total=row["total"] or 0
    )


@router.get("/api-metrics", response_model=ApiMetricsSummary)
async def get_api_metrics(
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get Broadcastify API metrics."""
    query = """
        SELECT
            COUNT(*) as total_calls,
            AVG(CAST(duration_ms AS FLOAT)) as avg_duration_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::float / COUNT(*) as error_rate,
            SUM(CASE WHEN cache_hit = TRUE THEN 1 ELSE 0 END)::float / COUNT(*) as cache_hit_rate
        FROM api_call_metrics
        WHERE timestamp >= CURRENT_DATE
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query)

    return ApiMetricsSummary(
        total_calls_today=row["total_calls"] or 0,
        avg_response_time_ms=float(row["avg_duration_ms"]) if row["avg_duration_ms"] else 0.0,
        error_rate=float(row["error_rate"]) if row["error_rate"] else 0.0,
        cache_hit_rate=float(row["cache_hit_rate"]) if row["cache_hit_rate"] else 0.0
    )


@router.get("/status")
async def get_system_status(
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get detailed system status."""
    async with pool.acquire() as conn:
        # Get various counts
        calls_count = await conn.fetchval("SELECT COUNT(*) FROM bcfy_calls_raw")
        transcripts_count = await conn.fetchval("SELECT COUNT(*) FROM transcripts")
        playlists_count = await conn.fetchval("SELECT COUNT(*) FROM bcfy_playlists WHERE sync = TRUE")

        # Get recent activity
        recent_error = await conn.fetchval(
            "SELECT message FROM system_logs WHERE severity = 'ERROR' ORDER BY timestamp DESC LIMIT 1"
        )

    return {
        "status": "operational",
        "calls_total": calls_count,
        "transcripts_total": transcripts_count,
        "active_playlists": playlists_count,
        "recent_error": recent_error,
    }
