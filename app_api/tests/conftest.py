"""
Shared test fixtures for Police Scanner API tests.

Provides:
- FastAPI test client (no auth)
- Authenticated test client (mocked user)
- Admin test client (mocked admin user)
- Database pool mock
"""

import asyncio
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from models.auth import CurrentUser


# ---------------------------------------------------------------------------
# Mock user objects
# ---------------------------------------------------------------------------

MOCK_USER = CurrentUser(
    id="user-001",
    email="testuser@example.com",
    role="user",
    is_active=True,
)

MOCK_ADMIN = CurrentUser(
    id="admin-001",
    email="admin@example.com",
    role="admin",
    is_active=True,
)


# ---------------------------------------------------------------------------
# Dependency overrides
# ---------------------------------------------------------------------------

def _make_pool_mock():
    """Create an asyncpg pool mock that returns empty results by default."""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value="UPDATE 0")

    # Context manager for pool.acquire()
    acq = AsyncMock()
    acq.__aenter__ = AsyncMock(return_value=conn)
    acq.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acq)

    return pool, conn


# ---------------------------------------------------------------------------
# App factory with dependency overrides
# ---------------------------------------------------------------------------

def _build_app(user: Optional[CurrentUser] = None):
    """
    Import the FastAPI app and override auth + database dependencies.

    Parameters
    ----------
    user : CurrentUser | None
        If None  → no auth override (requests are unauthenticated).
        If given → require_auth and get_current_user_optional return this user.
                   If user.role == "admin", require_admin also returns this user.
    """
    # Patch Firebase init so it doesn't fail during import
    with patch("auth.firebase.initialize_firebase", return_value=False):
        from main import app

    from database import get_pool as real_get_pool
    from auth.dependencies import (
        require_auth as real_require_auth,
        require_admin as real_require_admin,
        get_current_user_optional as real_get_current_user_optional,
    )

    pool_mock, conn_mock = _make_pool_mock()

    # Override DB pool
    app.dependency_overrides[real_get_pool] = lambda: pool_mock

    if user is not None:
        # Override auth dependencies to return the given user
        app.dependency_overrides[real_require_auth] = lambda: user
        app.dependency_overrides[real_get_current_user_optional] = lambda: user

        if user.role == "admin":
            app.dependency_overrides[real_require_admin] = lambda: user
    else:
        # Remove any auth overrides so real auth kicks in
        app.dependency_overrides.pop(real_require_auth, None)
        app.dependency_overrides.pop(real_require_admin, None)
        app.dependency_overrides.pop(real_get_current_user_optional, None)

    return app, pool_mock, conn_mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def anon_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with NO authentication — should get 401 on protected routes."""
    app, _, _ = _build_app(user=None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[tuple[AsyncClient, AsyncMock], None]:
    """HTTP client authenticated as a normal user."""
    app, pool_mock, conn_mock = _build_app(user=MOCK_USER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, conn_mock
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client() -> AsyncGenerator[tuple[AsyncClient, AsyncMock], None]:
    """HTTP client authenticated as an admin user."""
    app, pool_mock, conn_mock = _build_app(user=MOCK_ADMIN)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, conn_mock
    app.dependency_overrides.clear()
