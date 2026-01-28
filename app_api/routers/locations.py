"""
Locations API Router

Endpoints for querying geocoded locations from police scanner transcripts.
Used for map visualization and heatmap features.
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from uuid import UUID
import asyncpg

from database import get_pool
from models.locations import (
    Location, LocationWithContext, LocationListResponse,
    HeatmapResponse, HeatmapPoint
)

router = APIRouter()


def transform_location_row(row: dict) -> dict:
    """Transform database row to location dict."""
    result = dict(row)
    # Convert Decimal to float for JSON serialization
    for key in ['latitude', 'longitude', 'geocode_confidence']:
        if result.get(key) is not None:
            result[key] = float(result[key])
    return result


@router.get("", response_model=LocationListResponse)
async def list_locations(
    feed_id: Optional[UUID] = Query(None, description="Filter by playlist/feed UUID"),
    bbox: Optional[str] = Query(None, description="Bounding box: sw_lat,sw_lon,ne_lat,ne_lon"),
    since: Optional[datetime] = Query(None, description="Only locations since this timestamp"),
    hours: Optional[int] = Query(None, ge=1, le=720, description="Locations from last N hours"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List geocoded locations with optional filtering.

    Supports filtering by:
    - feed_id: Playlist UUID
    - bbox: Geographic bounding box (sw_lat,sw_lon,ne_lat,ne_lon)
    - since: Timestamp filter
    - hours: Time window in hours
    """
    query = """
        SELECT
            l.id, l.source_type, l.source_id, l.raw_location_text, l.location_type,
            l.latitude, l.longitude, l.geocode_confidence, l.geocode_source,
            l.street_name, l.street_number, l.city, l.state, l.postal_code,
            l.country, l.formatted_address, l.playlist_uuid, l.county_id,
            l.geocoded_at, l.created_at, l.updated_at,
            p.name as playlist_name,
            c.county_name, c.state_code as county_state,
            t.text as transcript_text, t.created_at as transcript_created_at
        FROM locations l
        LEFT JOIN bcfy_playlists p ON p.uuid = l.playlist_uuid
        LEFT JOIN bcfy_counties c ON c.cntid = l.county_id
        LEFT JOIN transcripts t ON t.call_uid = l.source_id AND l.source_type = 'transcript'
        WHERE l.latitude IS NOT NULL AND l.longitude IS NOT NULL
    """
    params = []
    param_count = 1

    # Filter by feed
    if feed_id:
        query += f" AND l.playlist_uuid = ${param_count}"
        params.append(feed_id)
        param_count += 1

    # Filter by bounding box
    if bbox:
        try:
            sw_lat, sw_lon, ne_lat, ne_lon = map(float, bbox.split(','))
            query += f" AND l.latitude BETWEEN ${param_count} AND ${param_count + 1}"
            query += f" AND l.longitude BETWEEN ${param_count + 2} AND ${param_count + 3}"
            params.extend([sw_lat, ne_lat, sw_lon, ne_lon])
            param_count += 4
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid bbox format. Use: sw_lat,sw_lon,ne_lat,ne_lon")

    # Filter by time
    if hours:
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        query += f" AND l.created_at >= ${param_count}"
        params.append(since_time)
        param_count += 1
    elif since:
        query += f" AND l.created_at >= ${param_count}"
        params.append(since)
        param_count += 1

    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({query}) subq"

    # Add ordering and pagination
    query += f" ORDER BY l.created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, *params[:-2])
        rows = await conn.fetch(query, *params)

    return LocationListResponse(
        items=[LocationWithContext(**transform_location_row(dict(row))) for row in rows],
        total=total or 0,
        limit=limit,
        offset=offset
    )


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    feed_id: Optional[UUID] = Query(None, description="Filter by playlist/feed UUID"),
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    grid_precision: int = Query(3, ge=2, le=5, description="Grid precision (decimals)"),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get aggregated location data for heatmap visualization.

    Returns points aggregated by grid cells for efficient heatmap rendering.
    Grid precision controls cell size:
    - 2 = ~1km cells
    - 3 = ~100m cells (default)
    - 4 = ~10m cells
    - 5 = ~1m cells
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = f"""
        SELECT
            ROUND(latitude::numeric, $1) as lat_grid,
            ROUND(longitude::numeric, $1) as lon_grid,
            AVG(latitude) as lat,
            AVG(longitude) as lon,
            COUNT(*) as count,
            MAX(created_at) as most_recent
        FROM locations
        WHERE latitude IS NOT NULL
          AND longitude IS NOT NULL
          AND created_at >= $2
    """
    params = [grid_precision, since_time]
    param_count = 3

    if feed_id:
        query += f" AND playlist_uuid = ${param_count}"
        params.append(feed_id)
        param_count += 1

    query += " GROUP BY ROUND(latitude::numeric, $1), ROUND(longitude::numeric, $1)"
    query += " HAVING COUNT(*) > 0"
    query += " ORDER BY count DESC"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

        # Get total count and center point
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                AVG(latitude) as center_lat,
                AVG(longitude) as center_lon
            FROM locations
            WHERE latitude IS NOT NULL
              AND longitude IS NOT NULL
              AND created_at >= $1
        """ + (" AND playlist_uuid = $2" if feed_id else ""),
            *([since_time, feed_id] if feed_id else [since_time])
        )

    points = [
        HeatmapPoint(
            lat=float(row['lat']),
            lon=float(row['lon']),
            count=row['count'],
            most_recent=row['most_recent']
        )
        for row in rows
    ]

    return HeatmapResponse(
        points=points,
        total_locations=stats['total'] or 0,
        time_window_hours=hours,
        center_lat=float(stats['center_lat']) if stats['center_lat'] else None,
        center_lon=float(stats['center_lon']) if stats['center_lon'] else None
    )


@router.get("/{location_id}", response_model=LocationWithContext)
async def get_location(
    location_id: UUID,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a single location with full context."""
    query = """
        SELECT
            l.id, l.source_type, l.source_id, l.raw_location_text, l.location_type,
            l.latitude, l.longitude, l.geocode_confidence, l.geocode_source,
            l.street_name, l.street_number, l.city, l.state, l.postal_code,
            l.country, l.formatted_address, l.playlist_uuid, l.county_id,
            l.geocoded_at, l.created_at, l.updated_at,
            p.name as playlist_name,
            c.county_name, c.state_code as county_state,
            t.text as transcript_text, t.created_at as transcript_created_at
        FROM locations l
        LEFT JOIN bcfy_playlists p ON p.uuid = l.playlist_uuid
        LEFT JOIN bcfy_counties c ON c.cntid = l.county_id
        LEFT JOIN transcripts t ON t.call_uid = l.source_id AND l.source_type = 'transcript'
        WHERE l.id = $1
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, location_id)

    if not row:
        raise HTTPException(status_code=404, detail="Location not found")

    return LocationWithContext(**transform_location_row(dict(row)))


@router.get("/stats/summary")
async def get_location_stats(
    feed_id: Optional[UUID] = Query(None, description="Filter by playlist/feed UUID"),
    hours: int = Query(24, ge=1, le=720, description="Time window in hours"),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get summary statistics for locations."""
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = """
        SELECT
            COUNT(*) as total_locations,
            COUNT(*) FILTER (WHERE latitude IS NOT NULL) as geocoded,
            COUNT(DISTINCT source_id) as unique_transcripts,
            COUNT(DISTINCT playlist_uuid) as unique_feeds,
            COUNT(DISTINCT city) FILTER (WHERE city IS NOT NULL) as unique_cities,
            MIN(created_at) as oldest,
            MAX(created_at) as newest
        FROM locations
        WHERE created_at >= $1
    """
    params = [since_time]

    if feed_id:
        query += " AND playlist_uuid = $2"
        params.append(feed_id)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)

    return {
        "total_locations": row['total_locations'],
        "geocoded": row['geocoded'],
        "unique_transcripts": row['unique_transcripts'],
        "unique_feeds": row['unique_feeds'],
        "unique_cities": row['unique_cities'],
        "time_range": {
            "oldest": row['oldest'].isoformat() if row['oldest'] else None,
            "newest": row['newest'].isoformat() if row['newest'] else None
        },
        "time_window_hours": hours
    }
