from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
import asyncpg

from database import get_pool
from models.transcripts import Transcript, TranscriptSearchResult

router = APIRouter()


@router.get("", response_model=List[Transcript])
async def list_transcripts(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    min_confidence: Optional[float] = Query(None, ge=0, le=1),
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

    return [dict(row) for row in rows]


@router.get("/search", response_model=List[TranscriptSearchResult])
async def search_transcripts(
    q: str = Query("", min_length=0),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
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
        return [dict(row) for row in rows]

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

    return [dict(row) for row in rows]


@router.get("/{transcript_id}", response_model=Transcript)
async def get_transcript(
    transcript_id: int,
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

    return dict(row)
