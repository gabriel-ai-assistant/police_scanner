"""
Subscriptions router for Police Scanner API.

Handles user subscriptions to playlists and linking of keyword groups.
"""

import logging
import uuid as uuid_lib
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
import asyncpg

from database import get_pool
from models.auth import CurrentUser
from models.subscriptions import (
    Subscription,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionSummary,
    SubscriptionListResponse,
    SubscriptionStatus,
    LinkKeywordGroupRequest,
    LinkedKeywordGroup,
)
from auth.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()


def transform_subscription_response(row: dict) -> dict:
    """Transform database row to API response with camelCase fields."""
    result = dict(row)

    # Convert UUIDs to strings
    if 'id' in result and result['id']:
        result['id'] = str(result['id'])
    if 'user_id' in result and result['user_id']:
        result['userId'] = str(result['user_id'])
    if 'playlist_uuid' in result and result['playlist_uuid']:
        result['playlistUuid'] = str(result['playlist_uuid'])

    # Add camelCase versions
    if 'notifications_enabled' in result:
        result['notificationsEnabled'] = result['notifications_enabled']
    if 'playlist_name' in result:
        result['playlistName'] = result['playlist_name']
    if 'playlist_descr' in result:
        result['playlistDescr'] = result['playlist_descr']
    if 'keyword_group_count' in result:
        result['keywordGroupCount'] = result['keyword_group_count']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updatedAt'] = result['updated_at'].isoformat()

    return result


def transform_linked_group_response(row: dict) -> dict:
    """Transform linked keyword group row to API response."""
    result = dict(row)

    if 'id' in result and result['id']:
        result['id'] = str(result['id'])
    if 'keyword_group_id' in result and result['keyword_group_id']:
        result['keywordGroupId'] = str(result['keyword_group_id'])
    if 'keyword_group_name' in result:
        result['keywordGroupName'] = result['keyword_group_name']
    if 'keyword_count' in result:
        result['keywordCount'] = result['keyword_count']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()

    return result


# ============================================================
# Subscription CRUD
# ============================================================

@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List all subscriptions for the current user.

    Returns subscriptions with playlist names and keyword group counts.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                us.id,
                us.playlist_uuid,
                p.name as playlist_name,
                us.notifications_enabled,
                COUNT(skg.id) as keyword_group_count
            FROM user_subscriptions us
            LEFT JOIN bcfy_playlists p ON p.uuid = us.playlist_uuid
            LEFT JOIN subscription_keyword_groups skg ON skg.subscription_id = us.id
            WHERE us.user_id = $1
            GROUP BY us.id, us.playlist_uuid, p.name, us.notifications_enabled
            ORDER BY us.created_at DESC
            """,
            user.id
        )

        subscriptions = [transform_subscription_response(dict(row)) for row in rows]

        return {
            "subscriptions": subscriptions,
            "total": len(subscriptions)
        }


@router.post("", response_model=Subscription, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    body: SubscriptionCreate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Subscribe to a playlist.

    Creates a new subscription linking the user to a Broadcastify playlist.
    """
    # Validate UUID format
    try:
        playlist_uuid = uuid_lib.UUID(body.playlist_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid playlist UUID format"
        )

    async with pool.acquire() as conn:
        # Check if playlist exists
        playlist = await conn.fetchrow(
            "SELECT uuid, name, descr FROM bcfy_playlists WHERE uuid = $1",
            playlist_uuid
        )

        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found"
            )

        # Check if already subscribed
        existing = await conn.fetchrow(
            """
            SELECT id FROM user_subscriptions
            WHERE user_id = $1 AND playlist_uuid = $2
            """,
            user.id,
            playlist_uuid
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already subscribed to this playlist"
            )

        # Create subscription
        row = await conn.fetchrow(
            """
            INSERT INTO user_subscriptions (user_id, playlist_uuid)
            VALUES ($1, $2)
            RETURNING *
            """,
            user.id,
            playlist_uuid
        )

        result = transform_subscription_response(dict(row))
        result['playlist_name'] = playlist['name']
        result['playlistName'] = playlist['name']
        result['playlist_descr'] = playlist['descr']
        result['playlistDescr'] = playlist['descr']
        result['keyword_group_count'] = 0
        result['keywordGroupCount'] = 0

        logger.info(f"User {user.email} subscribed to playlist {playlist_uuid}")

        return result


@router.get("/status/{playlist_uuid}", response_model=SubscriptionStatus)
async def get_subscription_status(
    playlist_uuid: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Check if user is subscribed to a playlist.

    Useful for showing subscribe/unsubscribe button state.
    """
    try:
        uuid_lib.UUID(playlist_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM user_subscriptions
            WHERE user_id = $1 AND playlist_uuid = $2
            """,
            user.id,
            playlist_uuid
        )

        return {
            "playlist_uuid": playlist_uuid,
            "playlistUuid": playlist_uuid,
            "is_subscribed": row is not None,
            "isSubscribed": row is not None,
            "subscription_id": str(row['id']) if row else None,
            "subscriptionId": str(row['id']) if row else None
        }


@router.get("/{subscription_id}", response_model=Subscription)
async def get_subscription(
    subscription_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get subscription details.

    Returns subscription with playlist info and linked keyword groups.
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format"
        )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                us.*,
                p.name as playlist_name,
                p.descr as playlist_descr,
                (SELECT COUNT(*) FROM subscription_keyword_groups WHERE subscription_id = us.id) as keyword_group_count
            FROM user_subscriptions us
            LEFT JOIN bcfy_playlists p ON p.uuid = us.playlist_uuid
            WHERE us.id = $1 AND us.user_id = $2
            """,
            sub_uuid,
            user.id
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        return transform_subscription_response(dict(row))


@router.patch("/{subscription_id}", response_model=Subscription)
async def update_subscription(
    subscription_id: str,
    body: SubscriptionUpdate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Update subscription settings.

    Currently supports toggling notifications_enabled.
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format"
        )

    async with pool.acquire() as conn:
        # Verify ownership
        existing = await conn.fetchrow(
            "SELECT id FROM user_subscriptions WHERE id = $1 AND user_id = $2",
            sub_uuid,
            user.id
        )

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        # Build update query
        updates = []
        params = [sub_uuid]
        param_count = 2

        if body.notifications_enabled is not None:
            updates.append(f"notifications_enabled = ${param_count}")
            params.append(body.notifications_enabled)
            param_count += 1

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        query = f"""
            UPDATE user_subscriptions
            SET {', '.join(updates)}
            WHERE id = $1
            RETURNING *
        """

        row = await conn.fetchrow(query, *params)

        # Get playlist info and counts
        full_row = await conn.fetchrow(
            """
            SELECT
                us.*,
                p.name as playlist_name,
                p.descr as playlist_descr,
                (SELECT COUNT(*) FROM subscription_keyword_groups WHERE subscription_id = us.id) as keyword_group_count
            FROM user_subscriptions us
            LEFT JOIN bcfy_playlists p ON p.uuid = us.playlist_uuid
            WHERE us.id = $1
            """,
            sub_uuid
        )

        logger.info(f"User {user.email} updated subscription {subscription_id}")

        return transform_subscription_response(dict(full_row))


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Unsubscribe from a playlist.

    This also removes all keyword group links for this subscription (CASCADE).
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format"
        )

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM user_subscriptions
            WHERE id = $1 AND user_id = $2
            """,
            sub_uuid,
            user.id
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        logger.info(f"User {user.email} unsubscribed from {subscription_id}")


# ============================================================
# Keyword Group Links
# ============================================================

@router.get("/{subscription_id}/keyword-groups", response_model=List[LinkedKeywordGroup])
async def list_linked_keyword_groups(
    subscription_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List keyword groups linked to a subscription.
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription ID format"
        )

    async with pool.acquire() as conn:
        # Verify ownership
        existing = await conn.fetchrow(
            "SELECT id FROM user_subscriptions WHERE id = $1 AND user_id = $2",
            sub_uuid,
            user.id
        )

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        rows = await conn.fetch(
            """
            SELECT
                skg.id,
                skg.keyword_group_id,
                kg.name as keyword_group_name,
                skg.created_at,
                (SELECT COUNT(*) FROM keywords WHERE keyword_group_id = kg.id AND is_active = TRUE) as keyword_count
            FROM subscription_keyword_groups skg
            JOIN keyword_groups kg ON kg.id = skg.keyword_group_id
            WHERE skg.subscription_id = $1
            ORDER BY skg.created_at DESC
            """,
            sub_uuid
        )

        return [transform_linked_group_response(dict(row)) for row in rows]


@router.post("/{subscription_id}/keyword-groups", response_model=LinkedKeywordGroup, status_code=status.HTTP_201_CREATED)
async def link_keyword_group(
    subscription_id: str,
    body: LinkKeywordGroupRequest,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Link a keyword group to a subscription.
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
        group_uuid = uuid_lib.UUID(body.keyword_group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

    async with pool.acquire() as conn:
        # Verify subscription ownership
        subscription = await conn.fetchrow(
            "SELECT id FROM user_subscriptions WHERE id = $1 AND user_id = $2",
            sub_uuid,
            user.id
        )

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        # Verify keyword group ownership (must be user's group, not template directly)
        keyword_group = await conn.fetchrow(
            "SELECT id, name FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not keyword_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found or not owned by you"
            )

        # Check if already linked
        existing = await conn.fetchrow(
            """
            SELECT id FROM subscription_keyword_groups
            WHERE subscription_id = $1 AND keyword_group_id = $2
            """,
            sub_uuid,
            group_uuid
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Keyword group already linked to this subscription"
            )

        # Create link
        row = await conn.fetchrow(
            """
            INSERT INTO subscription_keyword_groups (subscription_id, keyword_group_id)
            VALUES ($1, $2)
            RETURNING id, keyword_group_id, created_at
            """,
            sub_uuid,
            group_uuid
        )

        # Get keyword count
        keyword_count = await conn.fetchval(
            "SELECT COUNT(*) FROM keywords WHERE keyword_group_id = $1 AND is_active = TRUE",
            group_uuid
        )

        result = transform_linked_group_response(dict(row))
        result['keyword_group_name'] = keyword_group['name']
        result['keywordGroupName'] = keyword_group['name']
        result['keyword_count'] = keyword_count
        result['keywordCount'] = keyword_count

        logger.info(f"User {user.email} linked keyword group {group_uuid} to subscription {subscription_id}")

        return result


@router.delete("/{subscription_id}/keyword-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_keyword_group(
    subscription_id: str,
    group_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Unlink a keyword group from a subscription.
    """
    try:
        sub_uuid = uuid_lib.UUID(subscription_id)
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format"
        )

    async with pool.acquire() as conn:
        # Verify subscription ownership
        subscription = await conn.fetchrow(
            "SELECT id FROM user_subscriptions WHERE id = $1 AND user_id = $2",
            sub_uuid,
            user.id
        )

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        result = await conn.execute(
            """
            DELETE FROM subscription_keyword_groups
            WHERE subscription_id = $1 AND keyword_group_id = $2
            """,
            sub_uuid,
            group_uuid
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group link not found"
            )

        logger.info(f"User {user.email} unlinked keyword group {group_id} from subscription {subscription_id}")
