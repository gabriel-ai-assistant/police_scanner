"""
Dashboard router for Police Scanner API.

Provides user-scoped dashboard data based on subscriptions.
"""

import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Query
import asyncpg

from config import settings
from database import get_pool
from models.auth import CurrentUser
from models.dashboard import (
    DashboardStats,
    MyFeed,
    MyFeedsResponse,
    RecentCall,
    RecentCallsResponse,
    RecentTranscript,
    RecentTranscriptsResponse,
    KeywordGroupSummary,
    KeywordSummaryResponse,
    RecentActivity,
    RecentActivityResponse,
)
from auth.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# In-memory TTL cache for dashboard stats
# ============================================================
import time as _time

_stats_cache: dict = {}  # key -> {"data": ..., "expires": float}
_STATS_TTL = 60  # seconds
_CACHE_MAX_SIZE = 1000


def _evict_cache(cache: dict) -> None:
    """Evict expired entries from cache; if still over limit, clear entirely."""
    if len(cache) <= _CACHE_MAX_SIZE:
        return
    now = _time.time()
    expired = [k for k, v in cache.items() if v["expires"] <= now]
    for k in expired:
        del cache[k]
    if len(cache) > _CACHE_MAX_SIZE:
        cache.clear()


def _cache_get(key: str):
    entry = _stats_cache.get(key)
    if entry and entry["expires"] > _time.time():
        return entry["data"]
    return None


def _cache_set(key: str, data, ttl: int = _STATS_TTL):
    _evict_cache(_stats_cache)
    _stats_cache[key] = {"data": data, "expires": _time.time() + ttl}

# S3/MinIO client for presigned URLs
_s3_client = None

def get_s3_client():
    """Get or create S3 client for MinIO."""
    global _s3_client
    if _s3_client is None:
        protocol = "https" if settings.MINIO_USE_SSL else "http"
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"{protocol}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ROOT_USER,
            aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
            config=Config(signature_version="s3v4"),
        )
    return _s3_client


# PERF FIX: Cache presigned URLs to avoid generating one per row per request.
# URLs are valid for 1 hour; we cache for 30 minutes (safe margin).
_presigned_cache: dict = {}  # s3_key -> {"url": str, "expires": float}
_PRESIGNED_TTL = 1800  # 30 minutes


def build_audio_url(s3_key: Optional[str]) -> Optional[str]:
    """Generate presigned URL for audio file in MinIO (cached)."""
    if not s3_key:
        return None

    cached = _presigned_cache.get(s3_key)
    if cached and cached["expires"] > _time.time():
        return cached["url"]

    try:
        client = get_s3_client()
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.MINIO_BUCKET,
                'Key': s3_key,
            },
            ExpiresIn=3600,  # URL valid for 1 hour
        )
        _evict_cache(_presigned_cache)
        _presigned_cache[s3_key] = {"url": url, "expires": _time.time() + _PRESIGNED_TTL}
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL for {s3_key}: {e}")
        return None


def transform_stats_response(my_feeds: int, my_calls_1h: int, my_transcripts_24h: int) -> dict:
    """Create stats response with camelCase fields."""
    return {
        "my_feeds": my_feeds,
        "my_calls_1h": my_calls_1h,
        "my_transcripts_24h": my_transcripts_24h,
        "myFeeds": my_feeds,
        "myCalls1h": my_calls_1h,
        "myTranscripts24h": my_transcripts_24h,
    }


def transform_feed_response(row: dict) -> dict:
    """Transform feed row to API response with camelCase fields."""
    result = dict(row)

    if 'uuid' in result:
        result['id'] = str(result['uuid'])
    if 'is_active' in result:
        result['isActive'] = result['is_active']
    if 'updated_at' in result and result['updated_at']:
        result['updatedAt'] = result['updated_at'].isoformat()
    if 'subscribed_at' in result and result['subscribed_at']:
        result['subscribedAt'] = result['subscribed_at'].isoformat()

    return result


def transform_call_response(row: dict) -> dict:
    """Transform call row to API response with camelCase fields."""
    result = {
        "id": row.get('call_uid', ''),
        "timestamp": row['started_at'].isoformat() if row.get('started_at') else None,
        "talkgroup": str(row['tg_id']) if row.get('tg_id') else None,
        "duration": int(row['duration_ms'] / 1000) if row.get('duration_ms') else None,
        "feed_name": row.get('playlist_name'),
        "feed_id": str(row['playlist_uuid']) if row.get('playlist_uuid') else None,
        "audio_url": build_audio_url(row.get('s3_key_v2')),
    }

    # Add camelCase versions
    result['feedName'] = result['feed_name']
    result['feedId'] = result['feed_id']
    result['audioUrl'] = result['audio_url']

    return result


def transform_transcript_response(row: dict) -> dict:
    """Transform transcript row to API response with camelCase fields."""
    result = {
        "id": row.get('id'),
        "text": row.get('text'),
        "confidence": float(row['confidence']) if row.get('confidence') else None,
        "created_at": row['created_at'].isoformat() if row.get('created_at') else None,
        "feed_name": row.get('playlist_name'),
        "feed_id": str(row['playlist_uuid']) if row.get('playlist_uuid') else None,
        "call_id": row.get('call_uid'),
    }

    # Add camelCase versions
    result['createdAt'] = result['created_at']
    result['feedName'] = result['feed_name']
    result['feedId'] = result['feed_id']
    result['callId'] = result['call_id']

    return result


def transform_keyword_group_summary(row: dict) -> dict:
    """Transform keyword group summary to API response."""
    return {
        "name": row.get('name', ''),
        "keyword_count": row.get('keyword_count', 0),
        "is_active": row.get('is_active', True),
        "keywordCount": row.get('keyword_count', 0),
        "isActive": row.get('is_active', True),
    }


def transform_activity_response(row: dict, audio_url: Optional[str]) -> dict:
    """Transform activity row to API response with camelCase fields."""
    result = {
        "id": row.get('call_uid', ''),
        "timestamp": row['started_at'].isoformat() if row.get('started_at') else None,
        "talkgroup": str(row['tg_id']) if row.get('tg_id') else None,
        "duration": int(row['duration_ms'] / 1000) if row.get('duration_ms') else None,
        "feed_name": row.get('playlist_name'),
        "feed_id": str(row['playlist_uuid']) if row.get('playlist_uuid') else None,
        "audio_url": audio_url,
        "transcript_id": row.get('transcript_id'),
        "transcript_text": row.get('transcript_text'),
        "transcript_confidence": float(row['transcript_confidence']) if row.get('transcript_confidence') else None,
        "user_rating": row.get('user_rating'),
    }

    # Add camelCase versions
    result['feedName'] = result['feed_name']
    result['feedId'] = result['feed_id']
    result['audioUrl'] = result['audio_url']
    result['transcriptId'] = result['transcript_id']
    result['transcriptText'] = result['transcript_text']
    result['transcriptConfidence'] = result['transcript_confidence']
    result['userRating'] = result['user_rating']

    return result


# ============================================================
# Dashboard Stats
# ============================================================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get dashboard statistics for the current user.

    Returns counts of user's subscribed feeds, recent calls (1h),
    and recent transcripts (24h).
    """
    # PERF FIX: Cache dashboard stats per user for 60s to avoid 3 queries per load
    cache_key = f"dashboard_stats:{user.id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    async with pool.acquire() as conn:
        # Combined into a single query to reduce round-trips
        row = await conn.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM user_subscriptions WHERE user_id = $1) as my_feeds,
                (SELECT COUNT(*) FROM bcfy_calls_raw c
                 JOIN user_subscriptions us ON c.playlist_uuid = us.playlist_uuid
                 WHERE us.user_id = $1 AND c.started_at > NOW() - INTERVAL '1 hour') as my_calls_1h,
                (SELECT COUNT(*) FROM transcripts t
                 JOIN bcfy_calls_raw c ON t.call_uid = c.call_uid
                 JOIN user_subscriptions us ON c.playlist_uuid = us.playlist_uuid
                 WHERE us.user_id = $1 AND t.created_at > NOW() - INTERVAL '24 hours') as my_transcripts_24h
            """,
            user.id
        )

        result = transform_stats_response(
            row['my_feeds'] or 0,
            row['my_calls_1h'] or 0,
            row['my_transcripts_24h'] or 0
        )
        _cache_set(cache_key, result)
        return result


# ============================================================
# My Feeds
# ============================================================

@router.get("/my-feeds", response_model=MyFeedsResponse)
async def get_my_feeds(
    limit: int = Query(default=6, ge=1, le=50),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get user's subscribed feeds for dashboard display.

    Returns feeds with listener counts and subscription dates.
    """
    async with pool.acquire() as conn:
        # Get total count
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM user_subscriptions WHERE user_id = $1",
            user.id
        )

        # Get feeds with metadata
        rows = await conn.fetch(
            """
            SELECT
                p.uuid,
                p.name,
                p.descr as description,
                p.listeners,
                p.sync as is_active,
                p.fetched_at as updated_at,
                us.created_at as subscribed_at
            FROM bcfy_playlists p
            JOIN user_subscriptions us ON p.uuid = us.playlist_uuid
            WHERE us.user_id = $1
            ORDER BY p.listeners DESC NULLS LAST
            LIMIT $2
            """,
            user.id,
            limit + 1  # Fetch one extra to determine hasMore
        )

        has_more = len(rows) > limit
        feeds = [transform_feed_response(dict(row)) for row in rows[:limit]]

        return {
            "feeds": feeds,
            "total": total or 0,
            "has_more": has_more,
            "hasMore": has_more,
        }


# ============================================================
# Recent Calls
# ============================================================

@router.get("/recent-calls", response_model=RecentCallsResponse)
async def get_recent_calls(
    limit: int = Query(default=10, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get recent calls from user's subscribed feeds.

    Returns calls with audio URLs and feed information.
    Only includes calls that have been processed and have S3 audio.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.call_uid,
                c.tg_id,
                c.started_at,
                c.duration_ms,
                c.s3_key_v2,
                p.uuid as playlist_uuid,
                p.name as playlist_name
            FROM bcfy_calls_raw c
            JOIN user_subscriptions us ON c.playlist_uuid = us.playlist_uuid
            JOIN bcfy_playlists p ON c.playlist_uuid = p.uuid
            WHERE us.user_id = $1 AND c.s3_key_v2 IS NOT NULL
            ORDER BY c.started_at DESC
            LIMIT $2
            """,
            user.id,
            limit
        )

        calls = [transform_call_response(dict(row)) for row in rows]

        return {"calls": calls}


# ============================================================
# Recent Transcripts
# ============================================================

@router.get("/recent-transcripts", response_model=RecentTranscriptsResponse)
async def get_recent_transcripts(
    limit: int = Query(default=10, ge=1, le=100),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get recent transcripts from user's subscribed feeds.

    Returns transcripts with feed and call information.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                t.id,
                t.text,
                t.confidence,
                t.created_at,
                t.call_uid,
                p.uuid as playlist_uuid,
                p.name as playlist_name
            FROM transcripts t
            JOIN bcfy_calls_raw c ON t.call_uid = c.call_uid
            JOIN user_subscriptions us ON c.playlist_uuid = us.playlist_uuid
            JOIN bcfy_playlists p ON c.playlist_uuid = p.uuid
            WHERE us.user_id = $1
            ORDER BY t.created_at DESC
            LIMIT $2
            """,
            user.id,
            limit
        )

        transcripts = [transform_transcript_response(dict(row)) for row in rows]

        return {"transcripts": transcripts}


# ============================================================
# Recent Activity (Combined Calls + Transcripts)
# ============================================================

@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = Query(default=10, ge=1, le=50),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get recent activity (calls with transcripts) from user's subscribed feeds.

    Returns unified activity items with call, transcript, and rating data.
    Sorted by timestamp DESC.
    """
    async with pool.acquire() as conn:
        # Get calls with transcripts, joined with user's ratings
        rows = await conn.fetch(
            """
            SELECT
                c.call_uid,
                c.tg_id,
                c.started_at,
                c.duration_ms,
                c.s3_key_v2,
                p.uuid as playlist_uuid,
                p.name as playlist_name,
                t.id as transcript_id,
                t.text as transcript_text,
                t.confidence as transcript_confidence,
                tr.rating as user_rating
            FROM bcfy_calls_raw c
            JOIN user_subscriptions us ON c.playlist_uuid = us.playlist_uuid
            JOIN bcfy_playlists p ON c.playlist_uuid = p.uuid
            LEFT JOIN transcripts t ON c.call_uid = t.call_uid
            LEFT JOIN transcript_ratings tr ON t.id = tr.transcript_id AND tr.user_id = $1
            WHERE us.user_id = $1 AND c.s3_key_v2 IS NOT NULL
            ORDER BY c.started_at DESC
            LIMIT $2
            """,
            user.id,
            limit
        )

        activities = []
        for row in rows:
            audio_url = build_audio_url(row.get('s3_key_v2'))
            activities.append(transform_activity_response(dict(row), audio_url))

        return {"activities": activities}


# ============================================================
# Keyword Summary
# ============================================================

@router.get("/keyword-summary", response_model=KeywordSummaryResponse)
async def get_keyword_summary(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get summary of user's keyword groups.

    This is a placeholder until the keyword matching engine is built.
    Returns user's keyword groups with counts.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                kg.name,
                kg.is_active,
                COUNT(k.id) as keyword_count
            FROM keyword_groups kg
            LEFT JOIN keywords k ON k.keyword_group_id = kg.id AND k.is_active = TRUE
            WHERE kg.user_id = $1 AND kg.is_template = FALSE
            GROUP BY kg.id, kg.name, kg.is_active
            ORDER BY kg.name
            """,
            user.id
        )

        groups = [transform_keyword_group_summary(dict(row)) for row in rows]
        total_keywords = sum(g['keyword_count'] for g in groups)

        return {
            "groups": groups,
            "total_keywords": total_keywords,
            "totalKeywords": total_keywords,
            "message": "Keyword matching coming soon",
        }
