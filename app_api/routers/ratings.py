"""
Transcript ratings router for Police Scanner API.

Provides CRUD operations for transcript ratings (thumbs up/down).
"""

import logging

import asyncpg
from auth.dependencies import require_auth
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException, status
from models.auth import CurrentUser
from models.dashboard import (
    TranscriptRating,
    TranscriptRatingDeleteResponse,
    TranscriptRatingRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def transform_rating_response(row: dict) -> dict:
    """Transform rating row to API response with camelCase fields."""
    result = dict(row)

    if 'id' in result and result['id']:
        result['id'] = str(result['id'])
    if 'transcript_id' in result:
        result['transcriptId'] = result['transcript_id']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updatedAt'] = result['updated_at'].isoformat()

    return result


@router.get("/{transcript_id}", response_model=TranscriptRating)
async def get_rating(
    transcript_id: int,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get the current user's rating for a transcript.

    Returns 404 if no rating exists.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, transcript_id, rating, created_at, updated_at
            FROM transcript_ratings
            WHERE user_id = $1 AND transcript_id = $2
            """,
            user.id,
            transcript_id
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rating found for this transcript"
        )

    return transform_rating_response(dict(row))


@router.put("/{transcript_id}", response_model=TranscriptRating | TranscriptRatingDeleteResponse)
async def upsert_rating(
    transcript_id: int,
    body: TranscriptRatingRequest,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Create or update a rating for a transcript.

    Toggle behavior:
    - If the same rating exists, it will be removed
    - If a different rating exists, it will be updated
    - If no rating exists, a new one is created
    """
    async with pool.acquire() as conn:
        # First, check if transcript exists
        transcript = await conn.fetchval(
            "SELECT id FROM transcripts WHERE id = $1",
            transcript_id
        )

        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found"
            )

        # Check for existing rating
        existing = await conn.fetchrow(
            """
            SELECT id, rating FROM transcript_ratings
            WHERE user_id = $1 AND transcript_id = $2
            """,
            user.id,
            transcript_id
        )

        if existing:
            if existing['rating'] == body.rating:
                # Same rating - toggle OFF (delete)
                await conn.execute(
                    "DELETE FROM transcript_ratings WHERE id = $1",
                    existing['id']
                )
                return {"deleted": True, "message": "Rating removed"}
            else:
                # Different rating - update
                row = await conn.fetchrow(
                    """
                    UPDATE transcript_ratings
                    SET rating = $3
                    WHERE user_id = $1 AND transcript_id = $2
                    RETURNING id, transcript_id, rating, created_at, updated_at
                    """,
                    user.id,
                    transcript_id,
                    body.rating
                )
                return transform_rating_response(dict(row))
        else:
            # No existing rating - create new
            row = await conn.fetchrow(
                """
                INSERT INTO transcript_ratings (user_id, transcript_id, rating)
                VALUES ($1, $2, $3)
                RETURNING id, transcript_id, rating, created_at, updated_at
                """,
                user.id,
                transcript_id,
                body.rating
            )
            return transform_rating_response(dict(row))


@router.delete("/{transcript_id}")
async def delete_rating(
    transcript_id: int,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Remove the current user's rating for a transcript.
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM transcript_ratings
            WHERE user_id = $1 AND transcript_id = $2
            """,
            user.id,
            transcript_id
        )

    # Check if anything was deleted
    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rating found to delete"
        )

    return {"message": "Rating deleted"}
