"""
BUG-005: get_call returns error dict instead of raising HTTPException.

Tests that a missing call returns 404 HTTPException, not a dict.
"""

import os
import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_get_call_raises_404_when_not_found():
    """get_call should raise HTTPException(404) when call_uid doesn't exist."""
    from fastapi import HTTPException
    from routers.calls import get_call

    # Mock the pool and connection
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)

    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    with pytest.raises(HTTPException) as exc_info:
        await get_call(call_uid="nonexistent-uid", pool=mock_pool)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_call_does_not_return_error_dict():
    """get_call must NOT return {'error': ...} for missing calls."""
    import inspect

    from routers.calls import get_call

    source = inspect.getsource(get_call)
    assert '{"error"' not in source, "get_call still returns error dict"
    assert "HTTPException" in source, "get_call should use HTTPException"


@pytest.mark.asyncio
async def test_get_call_returns_data_when_found():
    """get_call should return transformed call data when call exists."""
    from datetime import datetime

    from routers.calls import get_call

    mock_row = {
        "call_uid": "test-123",
        "feed_id": 1,
        "tg_id": 100,
        "started_at": datetime(2024, 1, 1, 12, 0),
        "duration_ms": 5000,
    }

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=mock_row)

    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await get_call(call_uid="test-123", pool=mock_pool)
    assert result["call_uid"] == "test-123"
    assert "timestamp" in result  # transform_call_response adds this
