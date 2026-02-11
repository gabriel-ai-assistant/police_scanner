"""
Geocoder Service - FastAPI Application

Provides geocoding endpoints and batch processing for location extraction.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks

from app.config import settings
from app.models import (
    GeocodeRequest, GeocodeResult, Location, LocationWithContext,
    LocationListResponse, HeatmapResponse, HeatmapPoint
)
from app.nominatim import NominatimClient
from app.extractor import extract_locations, extract_locations_with_context

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database pool
_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Get or create database connection pool (async-safe with double-check lock)."""
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
            min_size=2,
            max_size=10,
            command_timeout=60
        )
    return _pool


async def close_pool():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Geocoder Service...")
    await get_pool()
    logger.info("Database connection pool created")
    yield
    logger.info("Shutting down Geocoder Service...")
    await close_pool()
    logger.info("Database pool closed")


app = FastAPI(
    title="Geocoder Service",
    description="Location extraction and geocoding service for police scanner transcripts",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "healthy", "service": "geocoder"}


@app.get("/geocode")
async def geocode_address(
    q: str = Query(..., min_length=3, description="Location query string"),
    city: Optional[str] = Query(None, description="City to bias results"),
    state: Optional[str] = Query(None, description="State to bias results")
) -> GeocodeResult:
    """
    Geocode a single address or location string.

    Uses caching and respects Nominatim rate limits (1 req/sec).
    """
    pool = await get_pool()
    client = NominatimClient(pool)

    request = GeocodeRequest(
        query=q,
        bias_city=city,
        bias_state=state
    )

    result = await client.geocode(request)
    return result


@app.get("/extract")
async def extract_from_text(
    text: str = Query(..., min_length=5, description="Text to extract locations from")
):
    """
    Extract location mentions from text.

    Returns potential addresses, streets, intersections, etc.
    """
    locations = extract_locations_with_context(text)
    return {
        "extracted": [
            {
                "raw_text": loc.raw_text,
                "location_type": loc.location_type,
                "confidence": loc.confidence,
                "context": context
            }
            for loc, context in locations
        ]
    }


@app.post("/process-transcript/{call_uid}")
async def process_transcript(
    call_uid: str,
    background_tasks: BackgroundTasks
):
    """
    Process a single transcript for location extraction and geocoding.

    Extracts locations from transcript text and queues geocoding.
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Get transcript with playlist context
        row = await conn.fetchrow("""
            SELECT t.text, t.call_uid, c.playlist_uuid
            FROM transcripts t
            JOIN bcfy_calls_raw c ON c.call_uid = t.call_uid
            WHERE t.call_uid = $1
        """, call_uid)

        if not row:
            raise HTTPException(status_code=404, detail="Transcript not found")

        text = row['text']
        playlist_uuid = row['playlist_uuid']

        if not text:
            return {"message": "No text in transcript", "locations_found": 0}

        # Extract locations
        locations = extract_locations(text)

        if not locations:
            return {"message": "No locations found in transcript", "locations_found": 0}

        # Get county info for geocoding bias
        county_info = None
        if playlist_uuid:
            county_row = await conn.fetchrow("""
                SELECT c.cntid, c.county_name, c.state_code, c.lat, c.lon
                FROM bcfy_playlists p
                JOIN LATERAL (
                    SELECT cntid FROM jsonb_array_elements_text(p.ctids) AS ct(cntid)
                    LIMIT 1
                ) cids ON true
                JOIN bcfy_counties c ON c.cntid = cids.cntid::integer
                WHERE p.uuid = $1
            """, playlist_uuid)
            if county_row:
                county_info = dict(county_row)

        # Insert locations for geocoding
        inserted = 0
        for loc in locations:
            try:
                await conn.execute("""
                    INSERT INTO locations (
                        source_type, source_id, raw_location_text, location_type,
                        playlist_uuid, county_id, geocode_attempts
                    ) VALUES ($1, $2, $3, $4, $5, $6, 0)
                    ON CONFLICT (source_type, source_id, raw_location_text) DO NOTHING
                """, 'transcript', call_uid, loc.raw_text, loc.location_type,
                    playlist_uuid, county_info['cntid'] if county_info else None)
                inserted += 1
            except Exception as e:
                logger.warning(f"Failed to insert location: {e}")

        # Queue background geocoding
        background_tasks.add_task(geocode_pending_locations)

        return {
            "message": f"Processed transcript {call_uid}",
            "locations_found": len(locations),
            "locations_inserted": inserted
        }


async def geocode_pending_locations(batch_size: int = 10):
    """Background task to geocode pending locations."""
    pool = await get_pool()
    client = NominatimClient(pool)

    async with pool.acquire() as conn:
        # Get pending locations
        rows = await conn.fetch("""
            SELECT l.id, l.raw_location_text, l.county_id,
                   c.county_name, c.state_code
            FROM locations l
            LEFT JOIN bcfy_counties c ON c.cntid = l.county_id
            WHERE l.latitude IS NULL
              AND l.geocode_attempts < $1
            ORDER BY l.created_at ASC
            LIMIT $2
        """, settings.MAX_GEOCODE_ATTEMPTS, batch_size)

        for row in rows:
            try:
                # Geocode with county context
                request = GeocodeRequest(
                    query=row['raw_location_text'],
                    bias_city=row['county_name'],
                    bias_state=row['state_code']
                )
                result = await client.geocode(request)

                # Update location with result
                await conn.execute("""
                    UPDATE locations
                    SET latitude = $2, longitude = $3, geocode_confidence = $4,
                        formatted_address = $5, street_name = $6, street_number = $7,
                        city = $8, state = $9, postal_code = $10, country = $11,
                        geocode_source = $12, geocoded_at = NOW(),
                        geocode_attempts = geocode_attempts + 1
                    WHERE id = $1
                """, row['id'], result.latitude, result.longitude, result.confidence,
                    result.formatted_address, result.street_name, result.street_number,
                    result.city, result.state, result.postal_code, result.country,
                    result.source)

                logger.info(f"Geocoded location {row['id']}: {row['raw_location_text']}")

            except Exception as e:
                logger.error(f"Failed to geocode location {row['id']}: {e}")
                await conn.execute("""
                    UPDATE locations
                    SET geocode_attempts = geocode_attempts + 1,
                        geocode_error = $2
                    WHERE id = $1
                """, row['id'], str(e))


@app.post("/backfill")
async def start_backfill(
    background_tasks: BackgroundTasks,
    limit: int = Query(100, ge=1, le=1000, description="Number of transcripts to process")
):
    """
    Start backfill processing for existing transcripts.

    Processes transcripts that don't have location entries yet.
    """
    background_tasks.add_task(run_backfill, limit)
    return {"message": f"Started backfill for up to {limit} transcripts"}


async def run_backfill(limit: int):
    """Background task to backfill locations from existing transcripts."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Get transcripts without location entries
        rows = await conn.fetch("""
            SELECT t.call_uid, t.text, c.playlist_uuid
            FROM transcripts t
            JOIN bcfy_calls_raw c ON c.call_uid = t.call_uid
            WHERE t.text IS NOT NULL
              AND t.text != ''
              AND NOT EXISTS (
                  SELECT 1 FROM locations l
                  WHERE l.source_type = 'transcript'
                    AND l.source_id = t.call_uid
              )
            ORDER BY t.created_at DESC
            LIMIT $1
        """, limit)

        logger.info(f"Starting backfill for {len(rows)} transcripts")

        for row in rows:
            try:
                text = row['text']
                call_uid = row['call_uid']
                playlist_uuid = row['playlist_uuid']

                # Extract locations
                locations = extract_locations(text)

                if not locations:
                    continue

                # Get county info
                county_id = None
                if playlist_uuid:
                    county_row = await conn.fetchrow("""
                        SELECT c.cntid
                        FROM bcfy_playlists p
                        JOIN LATERAL (
                            SELECT cntid FROM jsonb_array_elements_text(p.ctids) AS ct(cntid)
                            LIMIT 1
                        ) cids ON true
                        JOIN bcfy_counties c ON c.cntid = cids.cntid::integer
                        WHERE p.uuid = $1
                    """, playlist_uuid)
                    if county_row:
                        county_id = county_row['cntid']

                # Insert locations
                for loc in locations:
                    await conn.execute("""
                        INSERT INTO locations (
                            source_type, source_id, raw_location_text, location_type,
                            playlist_uuid, county_id
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (source_type, source_id, raw_location_text) DO NOTHING
                    """, 'transcript', call_uid, loc.raw_text, loc.location_type,
                        playlist_uuid, county_id)

                logger.debug(f"Processed transcript {call_uid}: {len(locations)} locations")

            except Exception as e:
                logger.error(f"Error processing transcript {row['call_uid']}: {e}")

    # After extraction, start geocoding
    await geocode_pending_locations(batch_size=settings.BATCH_SIZE)
    logger.info("Backfill completed")


@app.get("/stats")
async def get_stats():
    """Get geocoding statistics."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_locations,
                COUNT(*) FILTER (WHERE latitude IS NOT NULL) as geocoded,
                COUNT(*) FILTER (WHERE latitude IS NULL AND geocode_attempts < 3) as pending,
                COUNT(*) FILTER (WHERE latitude IS NULL AND geocode_attempts >= 3) as failed,
                COUNT(DISTINCT source_id) as unique_transcripts
            FROM locations
        """)

        cache_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as cache_entries,
                SUM(hit_count) as total_hits
            FROM geocode_cache
            WHERE expires_at > NOW()
        """)

        return {
            "locations": dict(stats),
            "cache": dict(cache_stats) if cache_stats else {"cache_entries": 0, "total_hits": 0}
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
