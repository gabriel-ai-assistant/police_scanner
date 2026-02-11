from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import uuid as uuid_lib

from database import get_pool
from models.playlists import Playlist, PlaylistUpdate, PlaylistStats
from models.auth import CurrentUser
from auth.dependencies import require_auth, require_admin

router = APIRouter()


def transform_playlist_response(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform playlist database row to frontend-expected format.

    Converts:
    - 'uuid' → 'id' (keeps 'uuid' for backward compatibility)
    - 'sync' → 'isActive' (keeps 'sync' for backward compatibility)
    - Adds 'state' field: "active" if sync else "idle"
    - 'fetched_at' → 'updatedAt' (keeps 'fetched_at' for backward compatibility)
    """
    result = dict(row)

    # Convert UUID to string for JSON serialization
    if 'uuid' in result and result['uuid']:
        result['uuid'] = str(result['uuid'])
        result['id'] = result['uuid']

    if 'sync' in result:
        result['isActive'] = bool(result['sync'])
        # Add computed 'state' field
        result['state'] = "active" if result['sync'] else "idle"

    if 'fetched_at' in result and result['fetched_at']:
        result['updatedAt'] = result['fetched_at'].isoformat() if hasattr(result['fetched_at'], 'isoformat') else str(result['fetched_at'])
    else:
        # Fallback to current timestamp if fetched_at is NULL
        result['updatedAt'] = datetime.utcnow().isoformat()

    return result


@router.get("", response_model=List[Playlist])
async def list_playlists(
    sync_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List all playlists."""
    query = "SELECT * FROM bcfy_playlists WHERE 1=1"
    params = []
    param_count = 1

    if sync_only:
        query += f" AND sync = TRUE"

    query += f" ORDER BY listeners DESC NULLS LAST LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [transform_playlist_response(dict(row)) for row in rows]


@router.get("/{playlist_uuid}", response_model=Playlist)
async def get_playlist(
    playlist_uuid: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific playlist."""
    try:
        uuid_lib.UUID(playlist_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM bcfy_playlists WHERE uuid = $1",
            playlist_uuid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return transform_playlist_response(dict(row))


@router.patch("/{playlist_uuid}", response_model=Playlist)
async def update_playlist(
    playlist_uuid: str,
    payload: PlaylistUpdate,
    admin: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Update playlist sync status."""
    try:
        uuid_lib.UUID(playlist_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bcfy_playlists SET sync = $1 WHERE uuid = $2 RETURNING *",
            payload.sync,
            playlist_uuid
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return transform_playlist_response(dict(row))


@router.get("/stats/summary", response_model=PlaylistStats)
async def playlist_stats(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get playlist statistics."""
    query = """
        SELECT
            COUNT(*) as total_playlists,
            SUM(CASE WHEN sync = TRUE THEN 1 ELSE 0 END) as synced_playlists,
            COALESCE(SUM(listeners), 0) as total_listeners,
            COALESCE(AVG(num_groups), 0) as avg_groups_per_playlist
        FROM bcfy_playlists
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query)

    return {
        "total_playlists": row["total_playlists"],
        "synced_playlists": row["synced_playlists"] or 0,
        "total_listeners": row["total_listeners"],
        "avg_groups_per_playlist": float(row["avg_groups_per_playlist"]) if row["avg_groups_per_playlist"] else 0.0
    }
