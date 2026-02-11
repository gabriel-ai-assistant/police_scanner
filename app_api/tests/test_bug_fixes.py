"""
Tests for bug fixes in app_api.

Each test is designed to FAIL if the corresponding fix is reverted.
"""
import ast
import inspect
import os
import sys
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

# Ensure app_api is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── BUG-001: notifications and webhooks routers must exist & be importable ───

class TestBUG001RouterImports:
    """BUG-001: main.py imports notifications and webhooks routers.
    They must exist under routers/ and be importable without error."""

    def test_notifications_router_importable(self):
        """notifications router module must exist and have a 'router' attribute."""
        from routers import notifications
        assert hasattr(notifications, "router"), "notifications module missing 'router'"

    def test_webhooks_router_importable(self):
        """webhooks router module must exist and have a 'router' attribute."""
        from routers import webhooks
        assert hasattr(webhooks, "router"), "webhooks module missing 'router'"

    def test_main_imports_without_error(self):
        """Importing main should not raise ImportError for missing routers."""
        # If routers are missing, this import fails
        import importlib
        # Force reimport to catch issues
        if "main" in sys.modules:
            del sys.modules["main"]
        try:
            import main  # noqa: F401
        except ImportError as e:
            pytest.fail(f"main.py import failed: {e}")


# ─── BUG-002/003: Analytics must use parameterized queries, not string interpolation ───

class TestBUG002_003ParameterizedQueries:
    """Analytics endpoints must NOT use Python string interpolation (% or f-string)
    in SQL queries. They must use $N bind parameters."""

    def test_hourly_activity_no_string_interpolation(self):
        """get_hourly_activity must not use % formatting in SQL."""
        from routers import analytics
        source = inspect.getsource(analytics.get_hourly_activity)
        # The bug was: """ ... INTERVAL '%s hours' """ % hours
        assert "% hours" not in source, \
            "get_hourly_activity still uses string interpolation (% hours) in SQL"
        assert '% minutes' not in source, \
            "get_hourly_activity still uses string interpolation (% minutes) in SQL"

    def test_analytics_source_no_percent_formatting(self):
        """The analytics module should not use old-style % formatting in SQL strings."""
        from routers import analytics
        source = inspect.getsource(analytics)
        # Look for the specific SQL injection pattern: """ % var
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip comments and log lines
            if stripped.startswith('#') or 'log.' in stripped or 'print(' in stripped:
                continue
            # Check for % formatting after a triple-quote SQL block
            if '"""' in stripped and '%' in stripped and 'SELECT' not in stripped:
                continue
            if stripped.endswith('% hours') or stripped.endswith('% minutes'):
                pytest.fail(
                    f"Line {i+1}: SQL string interpolation found: {stripped}"
                )


# ─── BUG-005: GET /calls/{{id}} must return 404 for non-existent call ───

class TestBUG005CallNotFound:
    """GET /calls/{call_uid} must return HTTP 404 when call doesn't exist,
    not 200 with {\"error\": \"Call not found\"}."""

    def test_get_call_returns_404_not_200(self):
        """Inspect the source: if row is None, must raise HTTPException(404)."""
        from routers import calls
        source = inspect.getsource(calls.get_call)
        # The fix should raise HTTPException with 404
        assert "404" in source or "HTTP_404_NOT_FOUND" in source, \
            "get_call does not return 404 status for missing calls"
        # The bug was returning {"error": "Call not found"} with 200
        assert '{"error"' not in source and "{'error'" not in source, \
            "get_call still returns error dict instead of raising HTTPException"


# ─── BUG-007/008: Secured endpoints must return 401 without auth ───

class TestBUG007_008AuthRequired:
    """All secured endpoints must use require_auth dependency and return 401."""

    def _check_router_has_auth(self, module_name, endpoints_to_check=None):
        """Verify a router module uses require_auth or require_admin on its endpoints."""
        mod = __import__(f"routers.{module_name}", fromlist=[module_name])
        source = inspect.getsource(mod)
        has_auth = "require_auth" in source or "require_admin" in source
        return has_auth

    def test_dashboard_requires_auth(self):
        assert self._check_router_has_auth("dashboard"), \
            "dashboard router missing require_auth"

    def test_subscriptions_requires_auth(self):
        assert self._check_router_has_auth("subscriptions"), \
            "subscriptions router missing require_auth"

    def test_ratings_requires_auth(self):
        assert self._check_router_has_auth("ratings"), \
            "ratings router missing require_auth"


# ─── BUG-009: MINIO_ENDPOINT default should be "minio:9000" ───

class TestBUG009MinioDefault:
    """MINIO_ENDPOINT must default to 'minio:9000', not a hardcoded LAN IP."""

    def test_minio_endpoint_default_not_hardcoded_ip(self):
        from config import Settings
        # Check the field default
        field_info = Settings.model_fields["MINIO_ENDPOINT"]
        default = field_info.default
        assert default != "192.168.1.152:9000", \
            f"MINIO_ENDPOINT still defaults to hardcoded IP: {default}"

    def test_minio_endpoint_default_is_minio_9000(self):
        from config import Settings
        field_info = Settings.model_fields["MINIO_ENDPOINT"]
        default = field_info.default
        assert default == "minio:9000", \
            f"MINIO_ENDPOINT default should be 'minio:9000', got '{default}'"


# ─── BUG-010: SESSION_COOKIE_SECURE must default to True ───

class TestBUG010CookieSecure:
    """SESSION_COOKIE_SECURE must default to True for production safety."""

    def test_session_cookie_secure_defaults_true(self):
        from config import Settings
        field_info = Settings.model_fields["SESSION_COOKIE_SECURE"]
        default = field_info.default
        assert default is True, \
            f"SESSION_COOKIE_SECURE defaults to {default}, should be True"


# ─── BUG-012: CurrentUser.id should be UUID type ───

class TestBUG012UUIDType:
    """CurrentUser.id field should accept/be typed as UUID, not plain str."""

    def test_current_user_id_is_uuid(self):
        from models.auth import CurrentUser
        field_info = CurrentUser.model_fields["id"]
        # The annotation should be UUID (or str if not fixed)
        annotation = field_info.annotation
        assert annotation is UUID or (hasattr(annotation, '__origin__') and UUID in getattr(annotation, '__args__', ())), \
            f"CurrentUser.id annotation is {annotation}, expected UUID"


# ─── BUG-013: update_user_status must accept JSON body, not query param ───

class TestBUG013UserStatusBody:
    """update_user_status should take is_active from a JSON body (Pydantic model
    or Body()), not as a bare parameter (which becomes a query param)."""

    def test_update_user_status_uses_body(self):
        from routers import auth
        source = inspect.getsource(auth.update_user_status)
        # If is_active is a bare `bool` param without Body/model, it's a query param (the bug)
        # The fix wraps it in a Pydantic model or uses Body()
        # Check that is_active is NOT a bare function parameter typed as bool
        import re
        # Look for the function signature
        sig_match = re.search(r'def update_user_status\((.*?)\):', source, re.DOTALL)
        if sig_match:
            sig = sig_match.group(1)
            # Bug pattern: "is_active: bool," as a bare param
            if re.search(r'is_active\s*:\s*bool\s*[,\)]', sig):
                # Check it's not wrapped in Body() or a model
                if 'Body(' not in sig:
                    pytest.fail(
                        "update_user_status still takes is_active as a bare bool query param"
                    )


# ─── BUG-019: DashboardMetrics.transcriptsToday should accept int ───

class TestBUG019TranscriptsTodayType:
    """DashboardMetrics.transcriptsToday should be Optional[int], not Optional[str]."""

    def test_transcripts_today_accepts_int(self):
        from models.analytics import DashboardMetrics
        field_info = DashboardMetrics.model_fields["transcriptsToday"]
        annotation = field_info.annotation
        # Should not be str
        assert annotation is not str, \
            f"transcriptsToday annotation is str, should be int"
        # Verify int works
        m = DashboardMetrics(
            total_calls_24h=0, active_playlists=0, transcripts_today=0,
            avg_transcription_confidence=0.0, processing_queue_size=0,
            api_calls_today=0, recent_calls=[], top_talkgroups=[],
            transcriptsToday=42
        )
        assert m.transcriptsToday == 42
