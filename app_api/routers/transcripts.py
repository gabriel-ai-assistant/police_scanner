from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional, Dict, Any
import asyncpg
import json

from database import get_pool
from models.transcripts import Transcript, TranscriptSearchResult
from models.auth import CurrentUser
from auth.dependencies import require_auth

router = APIRouter()


def transform_transcript_response(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform transcript database row to frontend-expected format.

    Converts:
    - JSONB 'words' column → 'segments' array with {start, end, text, keywords}
    - 'created_at' → 'createdAt' (keeps original for backward compatibility)
    - 'call_uid' → 'callId' (keeps original for backward compatibility)
    """
    result = dict(row)

    # Transform JSONB words to segments array
    words_data = result.get('words')
    segments = []

    if words_data:
        # Handle JSONB data - could be dict, list, or string
        if isinstance(words_data, str):
            try:
                words_data = json.loads(words_data)
            except (json.JSONDecodeError, TypeError):
                words_data = None

        # If words_data is a list of segments
        if isinstance(words_data, list):
            segments = [
                {
                    "start": segment.get("start", 0),
                    "end": segment.get("end", 0),
                    "text": segment.get("text", ""),
                    "keywords": []  # Can be populated from text analysis if needed
                }
                for segment in words_data
                if isinstance(segment, dict)
            ]

    # Add segments to result
    result['segments'] = segments

    # Add camelCase aliases for frontend compatibility
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat() if hasattr(result['created_at'], 'isoformat') else str(result['created_at'])

    if 'call_uid' in result:
        result['callId'] = result['call_uid']

    return result


@router.get("", response_model=List[Transcript])
async def list_transcripts(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """List recent transcripts."""
    query = "SELECT * FROM transcripts WHERE 1=1"
    params = []
    param_count = 1

    if min_confidence is not None:
        query += f" AND confidence >= ${param_count}"
        params.append(min_confidence)
        param_count += 1

    query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [transform_transcript_response(dict(row)) for row in rows]


@router.get("/search", response_model=List[TranscriptSearchResult])
async def search_transcripts(
    q: str = Query("", min_length=0),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Full-text search transcripts."""
    if not q or len(q.strip()) == 0:
        # If no query, return recent transcripts
        query = """
            SELECT id, recording_id, text, words, language, model_name,
                   created_at, confidence, duration_seconds, call_uid,
                   s3_bucket, s3_key, NULL::float as rank
            FROM transcripts
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, limit, offset)
        return [transform_transcript_response(dict(row)) for row in rows]

    # Full-text search
    query = """
        SELECT id, recording_id, text, words, language, model_name,
               created_at, confidence, duration_seconds, call_uid,
               s3_bucket, s3_key, ts_rank(tsv, query) as rank
        FROM transcripts, plainto_tsquery('english', $1) query
        WHERE tsv @@ query
        ORDER BY rank DESC
        LIMIT $2 OFFSET $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, q, limit, offset)

    return [transform_transcript_response(dict(row)) for row in rows]


@router.get("/{transcript_id}", response_model=Transcript)
async def get_transcript(
    transcript_id: int,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """Get a specific transcript."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM transcripts WHERE id = $1",
            transcript_id
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return transform_transcript_response(dict(row))
