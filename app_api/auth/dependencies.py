"""
FastAPI authentication dependencies.

These dependencies extract and validate user sessions from requests.
"""

import logging
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
import asyncpg

from config import settings
from database import get_pool
from models.auth import CurrentUser
from .firebase import verify_session_cookie, is_firebase_initialized

logger = logging.getLogger(__name__)


async def get_current_user_optional(
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool)
) -> Optional[CurrentUser]:
    """
    Extract user from session cookie.

    Returns None if no valid session (for optional auth endpoints).
    """
    # Check if Firebase is initialized
    if not is_firebase_initialized():
        logger.debug("Firebase not initialized, skipping auth")
        return None

    # Get session cookie
    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_cookie:
        return None

    try:
        # Verify session cookie with Firebase
        decoded = await verify_session_cookie(session_cookie)
        firebase_uid = decoded.get("uid")

        if not firebase_uid:
            logger.warning("Session cookie missing uid claim")
            return None

        # Look up user in database
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, role, is_active
                FROM users
                WHERE firebase_uid = $1 AND is_active = TRUE
                """,
                firebase_uid
            )

        if not row:
            logger.debug(f"User with firebase_uid {firebase_uid} not found in database")
            return None

        return CurrentUser(
            id=uuid.UUID(str(row["id"])) if not isinstance(row["id"], uuid.UUID) else row["id"],
            email=row["email"],
            role=row["role"],
            is_active=row["is_active"]
        )

    except ValueError as e:
        # Invalid/expired session - not an error, just not authenticated
        logger.debug(f"Invalid session: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


async def get_current_user(
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool)
) -> Optional[CurrentUser]:
    """
    Alias for get_current_user_optional.

    Use this for endpoints that work with or without authentication.
    """
    return await get_current_user_optional(request, pool)


async def require_auth(
    user: Optional[CurrentUser] = Depends(get_current_user_optional)
) -> CurrentUser:
    """
    Require authenticated user.

    Raises 401 if not authenticated.
    Use as a dependency on protected endpoints.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_admin(
    user: CurrentUser = Depends(require_auth)
) -> CurrentUser:
    """
    Require admin role.

    Raises 403 if user is not an admin.
    Use as a dependency on admin-only endpoints.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
