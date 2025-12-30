"""
Keyword Groups router for Police Scanner API.

Handles keyword groups, keywords within groups, bulk import, and template cloning.
"""

import logging
import re
import uuid as uuid_lib
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
import asyncpg

from database import get_pool
from models.auth import CurrentUser
from models.keyword_groups import (
    KeywordGroup,
    KeywordGroupCreate,
    KeywordGroupUpdate,
    KeywordGroupSummary,
    KeywordGroupListResponse,
    KeywordGroupDetail,
    TemplateListResponse,
    Keyword,
    KeywordCreate,
    KeywordUpdate,
    KeywordListResponse,
    BulkKeywordImport,
    BulkImportResponse,
    CloneTemplateRequest,
    LinkedSubscription,
)
from auth.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum keywords per bulk import
MAX_BULK_IMPORT = 500


def transform_group_response(row: dict) -> dict:
    """Transform database row to API response with camelCase fields."""
    result = dict(row)

    if 'id' in result and result['id']:
        result['id'] = str(result['id'])
    if 'user_id' in result and result['user_id']:
        result['userId'] = str(result['user_id'])
    if 'is_template' in result:
        result['isTemplate'] = result['is_template']
    if 'is_active' in result:
        result['isActive'] = result['is_active']
    if 'keyword_count' in result:
        result['keywordCount'] = result['keyword_count']
    if 'subscription_count' in result:
        result['subscriptionCount'] = result['subscription_count']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updatedAt'] = result['updated_at'].isoformat()

    return result


def transform_keyword_response(row: dict) -> dict:
    """Transform keyword row to API response."""
    result = dict(row)

    if 'id' in result and result['id']:
        result['id'] = str(result['id'])
    if 'keyword_group_id' in result and result['keyword_group_id']:
        result['keywordGroupId'] = str(result['keyword_group_id'])
    if 'match_type' in result:
        result['matchType'] = result['match_type']
    if 'is_active' in result:
        result['isActive'] = result['is_active']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()

    return result


def transform_linked_subscription_response(row: dict) -> dict:
    """Transform linked subscription row to API response."""
    result = dict(row)

    if 'subscription_id' in result and result['subscription_id']:
        result['subscriptionId'] = str(result['subscription_id'])
    if 'playlist_uuid' in result and result['playlist_uuid']:
        result['playlistUuid'] = str(result['playlist_uuid'])
    if 'playlist_name' in result:
        result['playlistName'] = result['playlist_name']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()

    return result


def validate_regex(pattern: str) -> bool:
    """Check if a string is a valid regex pattern."""
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


# ============================================================
# Keyword Group CRUD
# ============================================================

@router.get("", response_model=KeywordGroupListResponse)
async def list_keyword_groups(
    include_templates: bool = Query(False, description="Include system templates"),
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List all keyword groups for the current user.

    Optionally includes system templates that can be cloned.
    """
    async with pool.acquire() as conn:
        if include_templates:
            rows = await conn.fetch(
                """
                SELECT
                    kg.id,
                    kg.name,
                    kg.description,
                    kg.is_template,
                    kg.is_active,
                    COUNT(DISTINCT k.id) FILTER (WHERE k.is_active = TRUE) as keyword_count,
                    COUNT(DISTINCT skg.id) as subscription_count
                FROM keyword_groups kg
                LEFT JOIN keywords k ON k.keyword_group_id = kg.id
                LEFT JOIN subscription_keyword_groups skg ON skg.keyword_group_id = kg.id
                WHERE kg.user_id = $1 OR kg.is_template = TRUE
                GROUP BY kg.id
                ORDER BY kg.is_template DESC, kg.created_at DESC
                """,
                user.id
            )
        else:
            rows = await conn.fetch(
                """
                SELECT
                    kg.id,
                    kg.name,
                    kg.description,
                    kg.is_template,
                    kg.is_active,
                    COUNT(DISTINCT k.id) FILTER (WHERE k.is_active = TRUE) as keyword_count,
                    COUNT(DISTINCT skg.id) as subscription_count
                FROM keyword_groups kg
                LEFT JOIN keywords k ON k.keyword_group_id = kg.id
                LEFT JOIN subscription_keyword_groups skg ON skg.keyword_group_id = kg.id
                WHERE kg.user_id = $1
                GROUP BY kg.id
                ORDER BY kg.created_at DESC
                """,
                user.id
            )

        groups = [transform_group_response(dict(row)) for row in rows]

        return {
            "groups": groups,
            "total": len(groups)
        }


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List available template keyword groups.

    Templates are system-owned groups that users can clone.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                kg.id,
                kg.name,
                kg.description,
                kg.is_template,
                kg.is_active,
                COUNT(k.id) as keyword_count,
                0 as subscription_count
            FROM keyword_groups kg
            LEFT JOIN keywords k ON k.keyword_group_id = kg.id AND k.is_active = TRUE
            WHERE kg.is_template = TRUE AND kg.is_active = TRUE
            GROUP BY kg.id
            ORDER BY kg.name
            """
        )

        templates = [transform_group_response(dict(row)) for row in rows]

        return {
            "templates": templates,
            "total": len(templates)
        }


@router.post("", response_model=KeywordGroup, status_code=status.HTTP_201_CREATED)
async def create_keyword_group(
    body: KeywordGroupCreate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Create a new keyword group.
    """
    async with pool.acquire() as conn:
        # Check for duplicate name
        existing = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE user_id = $1 AND name = $2",
            user.id,
            body.name
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Keyword group with name '{body.name}' already exists"
            )

        row = await conn.fetchrow(
            """
            INSERT INTO keyword_groups (user_id, name, description)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user.id,
            body.name,
            body.description
        )

        result = transform_group_response(dict(row))
        result['keyword_count'] = 0
        result['keywordCount'] = 0
        result['subscription_count'] = 0
        result['subscriptionCount'] = 0

        logger.info(f"User {user.email} created keyword group '{body.name}'")

        return result


@router.post("/clone", response_model=KeywordGroup, status_code=status.HTTP_201_CREATED)
async def clone_template(
    body: CloneTemplateRequest,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Clone a template keyword group.

    Creates a copy of the template with all its keywords.
    """
    try:
        template_uuid = uuid_lib.UUID(body.template_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template ID format"
        )

    async with pool.acquire() as conn:
        # Verify template exists
        template = await conn.fetchrow(
            "SELECT * FROM keyword_groups WHERE id = $1 AND is_template = TRUE",
            template_uuid
        )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Check for duplicate name
        existing = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE user_id = $1 AND name = $2",
            user.id,
            body.name
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Keyword group with name '{body.name}' already exists"
            )

        # Create new group
        new_group = await conn.fetchrow(
            """
            INSERT INTO keyword_groups (user_id, name, description)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user.id,
            body.name,
            body.description or template['description']
        )

        new_group_id = new_group['id']

        # Copy keywords from template
        await conn.execute(
            """
            INSERT INTO keywords (keyword_group_id, keyword, match_type, is_active)
            SELECT $1, keyword, match_type, is_active
            FROM keywords
            WHERE keyword_group_id = $2
            """,
            new_group_id,
            template_uuid
        )

        # Get keyword count
        keyword_count = await conn.fetchval(
            "SELECT COUNT(*) FROM keywords WHERE keyword_group_id = $1",
            new_group_id
        )

        result = transform_group_response(dict(new_group))
        result['keyword_count'] = keyword_count
        result['keywordCount'] = keyword_count
        result['subscription_count'] = 0
        result['subscriptionCount'] = 0

        logger.info(f"User {user.email} cloned template '{template['name']}' as '{body.name}'")

        return result


@router.get("/{group_id}", response_model=KeywordGroupDetail)
async def get_keyword_group(
    group_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get keyword group details with keywords and linked subscriptions.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    async with pool.acquire() as conn:
        # Get group (must be owned by user or be a template)
        group = await conn.fetchrow(
            """
            SELECT * FROM keyword_groups
            WHERE id = $1 AND (user_id = $2 OR is_template = TRUE)
            """,
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        # Get keywords
        keywords = await conn.fetch(
            """
            SELECT * FROM keywords
            WHERE keyword_group_id = $1
            ORDER BY keyword
            """,
            group_uuid
        )

        # Get linked subscriptions (only for user's own groups)
        if group['user_id']:
            linked_subs = await conn.fetch(
                """
                SELECT
                    skg.subscription_id,
                    us.playlist_uuid,
                    p.name as playlist_name,
                    skg.created_at
                FROM subscription_keyword_groups skg
                JOIN user_subscriptions us ON us.id = skg.subscription_id
                LEFT JOIN bcfy_playlists p ON p.uuid = us.playlist_uuid
                WHERE skg.keyword_group_id = $1
                ORDER BY skg.created_at DESC
                """,
                group_uuid
            )
        else:
            linked_subs = []

        result = transform_group_response(dict(group))
        result['keywords'] = [transform_keyword_response(dict(k)) for k in keywords]
        result['linked_subscriptions'] = [transform_linked_subscription_response(dict(s)) for s in linked_subs]
        result['linkedSubscriptions'] = result['linked_subscriptions']

        return result


@router.patch("/{group_id}", response_model=KeywordGroup)
async def update_keyword_group(
    group_id: str,
    body: KeywordGroupUpdate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Update a keyword group.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    async with pool.acquire() as conn:
        # Verify ownership (cannot update templates)
        existing = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        # Check for duplicate name if updating name
        if body.name:
            duplicate = await conn.fetchrow(
                "SELECT id FROM keyword_groups WHERE user_id = $1 AND name = $2 AND id != $3",
                user.id,
                body.name,
                group_uuid
            )

            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Keyword group with name '{body.name}' already exists"
                )

        # Build update query
        updates = []
        params = [group_uuid]
        param_count = 2

        if body.name is not None:
            updates.append(f"name = ${param_count}")
            params.append(body.name)
            param_count += 1

        if body.description is not None:
            updates.append(f"description = ${param_count}")
            params.append(body.description)
            param_count += 1

        if body.is_active is not None:
            updates.append(f"is_active = ${param_count}")
            params.append(body.is_active)
            param_count += 1

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        query = f"""
            UPDATE keyword_groups
            SET {', '.join(updates)}
            WHERE id = $1
            RETURNING *
        """

        row = await conn.fetchrow(query, *params)

        # Get counts
        keyword_count = await conn.fetchval(
            "SELECT COUNT(*) FROM keywords WHERE keyword_group_id = $1 AND is_active = TRUE",
            group_uuid
        )
        subscription_count = await conn.fetchval(
            "SELECT COUNT(*) FROM subscription_keyword_groups WHERE keyword_group_id = $1",
            group_uuid
        )

        result = transform_group_response(dict(row))
        result['keyword_count'] = keyword_count
        result['keywordCount'] = keyword_count
        result['subscription_count'] = subscription_count
        result['subscriptionCount'] = subscription_count

        logger.info(f"User {user.email} updated keyword group {group_id}")

        return result


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword_group(
    group_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Delete a keyword group.

    This also removes all keywords and subscription links (CASCADE).
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM keyword_groups
            WHERE id = $1 AND user_id = $2
            """,
            group_uuid,
            user.id
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        logger.info(f"User {user.email} deleted keyword group {group_id}")


# ============================================================
# Keywords CRUD
# ============================================================

@router.get("/{group_id}/keywords", response_model=KeywordListResponse)
async def list_keywords(
    group_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List all keywords in a group.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    async with pool.acquire() as conn:
        # Verify access (owner or template)
        group = await conn.fetchrow(
            """
            SELECT id FROM keyword_groups
            WHERE id = $1 AND (user_id = $2 OR is_template = TRUE)
            """,
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        rows = await conn.fetch(
            """
            SELECT * FROM keywords
            WHERE keyword_group_id = $1
            ORDER BY keyword
            """,
            group_uuid
        )

        keywords = [transform_keyword_response(dict(row)) for row in rows]

        return {
            "keywords": keywords,
            "total": len(keywords)
        }


@router.post("/{group_id}/keywords", response_model=Keyword, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    group_id: str,
    body: KeywordCreate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Add a keyword to a group.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    # Validate regex if match_type is regex
    if body.match_type == 'regex' and not validate_regex(body.keyword):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {body.keyword}"
        )

    async with pool.acquire() as conn:
        # Verify ownership (cannot add to templates)
        group = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        # Check for duplicate
        existing = await conn.fetchrow(
            """
            SELECT id FROM keywords
            WHERE keyword_group_id = $1 AND keyword = $2 AND match_type = $3
            """,
            group_uuid,
            body.keyword,
            body.match_type
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Keyword with this match type already exists in group"
            )

        row = await conn.fetchrow(
            """
            INSERT INTO keywords (keyword_group_id, keyword, match_type)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            group_uuid,
            body.keyword,
            body.match_type
        )

        logger.info(f"User {user.email} added keyword '{body.keyword}' to group {group_id}")

        return transform_keyword_response(dict(row))


@router.post("/{group_id}/keywords/bulk", response_model=BulkImportResponse)
async def bulk_import_keywords(
    group_id: str,
    body: BulkKeywordImport,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Bulk import keywords from newline-separated text.

    Skips duplicates and empty lines. Returns counts of imported/skipped.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid group ID format"
        )

    async with pool.acquire() as conn:
        # Verify ownership
        group = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        # Parse keywords
        lines = body.keywords.split('\n')
        keywords_to_add = []
        errors = []

        for line in lines:
            keyword = line.strip()
            if not keyword:
                continue

            # Validate regex if needed
            if body.match_type == 'regex' and not validate_regex(keyword):
                errors.append(f"Invalid regex: {keyword}")
                continue

            keywords_to_add.append(keyword)

            if len(keywords_to_add) >= MAX_BULK_IMPORT:
                break

        if len(lines) > MAX_BULK_IMPORT:
            errors.append(f"Truncated to {MAX_BULK_IMPORT} keywords (limit reached)")

        # Get existing keywords
        existing = await conn.fetch(
            """
            SELECT keyword, match_type FROM keywords
            WHERE keyword_group_id = $1 AND match_type = $2
            """,
            group_uuid,
            body.match_type
        )

        existing_set = {row['keyword'] for row in existing}

        # Filter out duplicates
        new_keywords = [k for k in keywords_to_add if k not in existing_set]
        skipped = len(keywords_to_add) - len(new_keywords)

        # Insert new keywords
        if new_keywords:
            await conn.executemany(
                """
                INSERT INTO keywords (keyword_group_id, keyword, match_type)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                [(group_uuid, k, body.match_type) for k in new_keywords]
            )

        logger.info(f"User {user.email} bulk imported {len(new_keywords)} keywords to group {group_id}")

        return {
            "imported": len(new_keywords),
            "skipped": skipped,
            "errors": errors
        }


@router.patch("/{group_id}/keywords/{keyword_id}", response_model=Keyword)
async def update_keyword(
    group_id: str,
    keyword_id: str,
    body: KeywordUpdate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Update a keyword.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
        kw_uuid = uuid_lib.UUID(keyword_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    # Validate regex if updating to regex type
    if body.match_type == 'regex' and body.keyword and not validate_regex(body.keyword):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {body.keyword}"
        )

    async with pool.acquire() as conn:
        # Verify group ownership
        group = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        # Verify keyword exists in group
        existing = await conn.fetchrow(
            "SELECT * FROM keywords WHERE id = $1 AND keyword_group_id = $2",
            kw_uuid,
            group_uuid
        )

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        # Build update query
        updates = []
        params = [kw_uuid]
        param_count = 2

        if body.keyword is not None:
            updates.append(f"keyword = ${param_count}")
            params.append(body.keyword)
            param_count += 1

        if body.match_type is not None:
            updates.append(f"match_type = ${param_count}")
            params.append(body.match_type)
            param_count += 1

        if body.is_active is not None:
            updates.append(f"is_active = ${param_count}")
            params.append(body.is_active)
            param_count += 1

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        query = f"""
            UPDATE keywords
            SET {', '.join(updates)}
            WHERE id = $1
            RETURNING *
        """

        row = await conn.fetchrow(query, *params)

        logger.info(f"User {user.email} updated keyword {keyword_id}")

        return transform_keyword_response(dict(row))


@router.delete("/{group_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    group_id: str,
    keyword_id: str,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Delete a keyword from a group.
    """
    try:
        group_uuid = uuid_lib.UUID(group_id)
        kw_uuid = uuid_lib.UUID(keyword_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format"
        )

    async with pool.acquire() as conn:
        # Verify group ownership
        group = await conn.fetchrow(
            "SELECT id FROM keyword_groups WHERE id = $1 AND user_id = $2",
            group_uuid,
            user.id
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword group not found"
            )

        result = await conn.execute(
            """
            DELETE FROM keywords
            WHERE id = $1 AND keyword_group_id = $2
            """,
            kw_uuid,
            group_uuid
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Keyword not found"
            )

        logger.info(f"User {user.email} deleted keyword {keyword_id}")
