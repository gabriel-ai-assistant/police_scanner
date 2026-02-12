"""
Authentication router for Police Scanner API.

Handles Firebase authentication, session management, and user operations.
"""

import json
import logging

import asyncpg
from auth.dependencies import require_admin, require_auth
from auth.firebase import (
    create_session_cookie,
    is_firebase_initialized,
    verify_firebase_token,
)
from config import settings
from database import get_pool
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from models.auth import (
    CurrentUser,
    SessionRequest,
    UserRoleUpdate,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()
admin_router = APIRouter()


def transform_user_response(row: dict) -> dict:
    """Transform database row to API response with camelCase fields."""
    result = dict(row)

    # Convert UUID to string
    if 'id' in result and result['id']:
        result['id'] = str(result['id'])

    # Add camelCase versions
    if 'firebase_uid' in result:
        result['firebaseUid'] = result['firebase_uid']
    if 'email_verified' in result:
        result['emailVerified'] = result['email_verified']
    if 'display_name' in result:
        result['displayName'] = result['display_name']
    if 'avatar_url' in result:
        result['avatarUrl'] = result['avatar_url']
    if 'is_active' in result:
        result['isActive'] = result['is_active']
    if 'created_at' in result and result['created_at']:
        result['createdAt'] = result['created_at'].isoformat()
    if 'updated_at' in result and result['updated_at']:
        result['updatedAt'] = result['updated_at'].isoformat()
    if 'last_login_at' in result and result['last_login_at']:
        result['lastLoginAt'] = result['last_login_at'].isoformat()

    return result


async def log_auth_event(
    pool: asyncpg.Pool,
    user_id: str | None,
    event_type: str,
    request: Request,
    metadata: dict | None = None
) -> None:
    """Log an authentication event to the audit log."""
    try:
        # Get client IP
        ip_address = request.client.host if request.client else None

        # Get user agent
        user_agent = request.headers.get("user-agent", "")[:500]  # Limit length

        # Serialize metadata dict to JSON string for JSONB column
        metadata_json = json.dumps(metadata) if metadata else None

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO auth_audit_log (user_id, event_type, ip_address, user_agent, metadata)
                VALUES ($1, $2, $3::inet, $4, $5)
                """,
                user_id,
                event_type,
                ip_address,
                user_agent,
                metadata_json
            )
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")


# ============================================================
# Session Management
# ============================================================

@router.post("/session")
async def create_session(
    request: Request,
    response: Response,
    body: SessionRequest,
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Create a session from a Firebase ID token.

    The client should obtain an ID token from Firebase Auth (after Google OAuth
    or email/password login) and send it here. This endpoint:
    1. Verifies the token with Firebase
    2. Creates or updates the user in the database
    3. Sets an httpOnly session cookie

    Returns the user profile.
    """
    if not is_firebase_initialized():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )

    try:
        # 1. Verify Firebase ID token
        decoded = await verify_firebase_token(body.id_token)
        firebase_uid = decoded.get("uid")
        email = decoded.get("email")

        if not firebase_uid or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token: missing user information"
            )

        # 2. Find or create user in database
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE firebase_uid = $1",
                firebase_uid
            )

            if not user:
                # Create new user
                # Check if this should be an admin (first login with ADMIN_EMAIL)
                is_admin = (
                    settings.ADMIN_EMAIL
                    and email.lower() == settings.ADMIN_EMAIL.lower()
                )

                user = await conn.fetchrow(
                    """
                    INSERT INTO users (
                        firebase_uid, email, email_verified, display_name, avatar_url, role
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                    """,
                    firebase_uid,
                    email,
                    decoded.get("email_verified", False),
                    decoded.get("name"),
                    decoded.get("picture"),
                    "admin" if is_admin else "user"
                )

                await log_auth_event(
                    pool, str(user["id"]), "registration", request,
                    {"provider": decoded.get("firebase", {}).get("sign_in_provider", "unknown")}
                )

                logger.info(f"Created new user: {email} (admin={is_admin})")
            else:
                # Update existing user's last login and possibly sync profile
                user = await conn.fetchrow(
                    """
                    UPDATE users
                    SET last_login_at = NOW(),
                        email_verified = COALESCE($2, email_verified),
                        display_name = COALESCE($3, display_name),
                        avatar_url = COALESCE($4, avatar_url)
                    WHERE firebase_uid = $1
                    RETURNING *
                    """,
                    firebase_uid,
                    decoded.get("email_verified"),
                    decoded.get("name"),
                    decoded.get("picture")
                )

            # Check if user is active
            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is disabled"
                )

            await log_auth_event(pool, str(user["id"]), "login", request)

        # 3. Create session cookie
        session_cookie = await create_session_cookie(
            body.id_token,
            expires_in=settings.SESSION_COOKIE_MAX_AGE
        )

        # 4. Set httpOnly cookie
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session_cookie,
            max_age=settings.SESSION_COOKIE_MAX_AGE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )

        return {
            "user": transform_user_response(dict(user)),
            "message": "Session created successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Log out the current user.

    Clears the session cookie.
    """
    # Log the logout event
    await log_auth_event(pool, user.id, "logout", request)

    # Clear the session cookie
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE
    )

    return {"message": "Logged out successfully"}


# ============================================================
# Current User Profile
# ============================================================

@router.get("/me")
async def get_me(
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get the current user's profile.

    Requires authentication.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user.id
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return transform_user_response(dict(row))


@router.patch("/me")
async def update_me(
    body: UserUpdate,
    user: CurrentUser = Depends(require_auth),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Update the current user's profile.

    Only display_name can be updated by the user.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET display_name = COALESCE($2, display_name)
            WHERE id = $1
            RETURNING *
            """,
            user.id,
            body.display_name
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return transform_user_response(dict(row))


# ============================================================
# Admin User Management
# ============================================================

@admin_router.get("/users")
async def list_users(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    role: str | None = Query(None, pattern="^(user|admin)$"),
    _user: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    List all users (admin only).
    """
    async with pool.acquire() as conn:
        # Build query
        if role:
            rows = await conn.fetch(
                """
                SELECT * FROM users
                WHERE role = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                role, limit, offset
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE role = $1",
                role
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit, offset
            )
            total = await conn.fetchval("SELECT COUNT(*) FROM users")

    users = [transform_user_response(dict(row)) for row in rows]

    return {
        "users": users,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@admin_router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    _admin: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get a specific user by ID (admin only).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return transform_user_response(dict(row))


@admin_router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Update a user's role (admin only).

    Cannot change your own role.
    """
    # Prevent self-demotion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )

    async with pool.acquire() as conn:
        # Get current user to log the change
        current = await conn.fetchrow(
            "SELECT role FROM users WHERE id = $1",
            user_id
        )

        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        old_role = current["role"]

        # Update role
        row = await conn.fetchrow(
            """
            UPDATE users
            SET role = $2
            WHERE id = $1
            RETURNING *
            """,
            user_id,
            body.role
        )

    # Log the role change
    await log_auth_event(
        pool, user_id, "role_change", request,
        {"old_role": old_role, "new_role": body.role, "changed_by": admin.id}
    )

    logger.info(f"Admin {admin.email} changed user {user_id} role from {old_role} to {body.role}")

    return transform_user_response(dict(row))


@admin_router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Enable or disable a user account (admin only).

    Cannot disable your own account.
    """
    # Prevent self-disable
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own status"
        )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET is_active = $2
            WHERE id = $1
            RETURNING *
            """,
            user_id,
            is_active
        )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Log the status change
    await log_auth_event(
        pool, user_id, "status_change", request,
        {"is_active": is_active, "changed_by": admin.id}
    )

    action = "enabled" if is_active else "disabled"
    logger.info(f"Admin {admin.email} {action} user {user_id}")

    return transform_user_response(dict(row))


@admin_router.get("/audit-log")
async def get_audit_log(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: str | None = None,
    event_type: str | None = None,
    _admin: CurrentUser = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_pool)
):
    """
    Get authentication audit log (admin only).
    """
    # Build query dynamically
    conditions = []
    params = []
    param_idx = 1

    if user_id:
        conditions.append(f"user_id = ${param_idx}")
        params.append(user_id)
        param_idx += 1

    if event_type:
        conditions.append(f"event_type = ${param_idx}")
        params.append(event_type)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM auth_audit_log
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params, limit, offset
        )

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM auth_audit_log WHERE {where_clause}",
            *params
        )

    # Transform response
    logs = []
    for row in rows:
        log = dict(row)
        if log.get("user_id"):
            log["userId"] = str(log["user_id"])
        if log.get("event_type"):
            log["eventType"] = log["event_type"]
        if log.get("ip_address"):
            log["ipAddress"] = str(log["ip_address"])
        if log.get("user_agent"):
            log["userAgent"] = log["user_agent"]
        if log.get("created_at"):
            log["createdAt"] = log["created_at"].isoformat()
        logs.append(log)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }
