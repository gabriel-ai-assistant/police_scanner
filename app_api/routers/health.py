from fastapi import APIRouter, Depends
from datetime import datetime
import asyncpg

from ..database import get_pool
from ..models.system import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Check API and dependencies health status."""
    pool = await get_pool()

    # Test database connection
    db_status = "healthy"
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # TODO: Add Redis health check if implemented
    redis_status = "not_configured"

    return HealthStatus(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        redis=redis_status,
        version="1.0.0",
        timestamp=datetime.utcnow()
    )


@router.get("/metrics/dashboard")
async def dashboard_metrics_endpoint():
    """Legacy endpoint for dashboard metrics - redirects to analytics endpoint."""
    return {"error": "Use /api/analytics/dashboard instead"}
