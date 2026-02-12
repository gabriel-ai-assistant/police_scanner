"""
Tests for bug fixes in app_api.

Each test is designed to FAIL if the corresponding fix is reverted.
Uses source-level inspection to avoid heavy dependencies (firebase_admin, boto3).
"""
import os
import re
import sys
from uuid import UUID

# Ensure app_api is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

API_DIR = os.path.join(os.path.dirname(__file__), "..")


def _read_source(relpath):
    """Read source file relative to app_api/."""
    with open(os.path.join(API_DIR, relpath)) as f:
        return f.read()


# ─── BUG-001: notifications and webhooks routers must exist ───

class TestBUG001RouterImports:
    def test_notifications_router_exists(self):
        path = os.path.join(API_DIR, "routers", "notifications.py")
        assert os.path.isfile(path), "routers/notifications.py does not exist"

    def test_webhooks_router_exists(self):
        path = os.path.join(API_DIR, "routers", "webhooks.py")
        assert os.path.isfile(path), "routers/webhooks.py does not exist"

    def test_notifications_has_router_object(self):
        source = _read_source("routers/notifications.py")
        assert "router" in source, "notifications.py missing 'router' definition"

    def test_webhooks_has_router_object(self):
        source = _read_source("routers/webhooks.py")
        assert "router" in source, "webhooks.py missing 'router' definition"


# ─── BUG-002/003: Analytics must use parameterized queries ───

class TestBUG002_003ParameterizedQueries:
    def test_hourly_activity_no_string_interpolation(self):
        source = _read_source("routers/analytics.py")
        # The bug: """...INTERVAL '%s hours'""" % hours
        assert re.search(r'"""\s*%\s*hours', source) is None, \
            "analytics.py uses '% hours' string interpolation in SQL"

    def test_no_percent_formatting_in_sql(self):
        source = _read_source("routers/analytics.py")
        matches = re.findall(r'"""\s*%\s*\w+', source)
        assert len(matches) == 0, \
            f"Found SQL string interpolation via %: {matches}"


# ─── BUG-005: GET /calls/{{id}} must return 404 ───

class TestBUG005CallNotFound:
    def test_get_call_returns_404_not_200(self):
        source = _read_source("routers/calls.py")
        # Find the get_call function
        match = re.search(r'async def get_call\(.*?\n(?=\nasync def |\nrouter\.|\Z)', source, re.DOTALL)
        assert match, "get_call function not found"
        func_source = match.group()
        assert "404" in func_source or "HTTP_404_NOT_FOUND" in func_source, \
            "get_call does not return 404 status for missing calls"
        assert '{"error"' not in func_source and "{'error'" not in func_source, \
            "get_call still returns error dict instead of raising HTTPException"


# ─── BUG-007/008: Secured endpoints must use require_auth ───

class TestBUG007_008AuthRequired:
    def _source_has_auth(self, relpath):
        source = _read_source(relpath)
        return "require_auth" in source or "require_admin" in source

    def test_dashboard_requires_auth(self):
        assert self._source_has_auth("routers/dashboard.py")

    def test_subscriptions_requires_auth(self):
        assert self._source_has_auth("routers/subscriptions.py")

    def test_ratings_requires_auth(self):
        assert self._source_has_auth("routers/ratings.py")

    def test_calls_requires_auth(self):
        """Calls router should have auth on write endpoints or all endpoints."""
        # At minimum, the router should reference auth dependencies
        source = _read_source("routers/calls.py")
        # This may or may not require auth depending on design;
        # check if it was listed in bug report
        # BUG-007/008 says "calls" should be secured
        assert "require_auth" in source or "Depends(get_current_user" in source, \
            "calls router missing auth dependency"


# ─── BUG-009: MINIO_ENDPOINT default ───

class TestBUG009MinioDefault:
    def test_minio_endpoint_default_not_hardcoded_ip(self):
        from config import Settings
        field_info = Settings.model_fields["MINIO_ENDPOINT"]
        assert field_info.default != "192.168.1.152:9000", \
            f"MINIO_ENDPOINT still defaults to hardcoded IP: {field_info.default}"

    def test_minio_endpoint_default_is_minio_9000(self):
        from config import Settings
        field_info = Settings.model_fields["MINIO_ENDPOINT"]
        assert field_info.default == "minio:9000", \
            f"MINIO_ENDPOINT default should be 'minio:9000', got '{field_info.default}'"


# ─── BUG-010: SESSION_COOKIE_SECURE default ───

class TestBUG010CookieSecure:
    def test_session_cookie_secure_defaults_true(self):
        from config import Settings
        field_info = Settings.model_fields["SESSION_COOKIE_SECURE"]
        assert field_info.default is True, \
            f"SESSION_COOKIE_SECURE defaults to {field_info.default}, should be True"


# ─── BUG-012: CurrentUser.id should be UUID ───

class TestBUG012UUIDType:
    def test_current_user_id_is_uuid(self):
        from models.auth import CurrentUser
        field_info = CurrentUser.model_fields["id"]
        annotation = field_info.annotation
        assert annotation is UUID or (hasattr(annotation, '__origin__') and UUID in getattr(annotation, '__args__', ())), \
            f"CurrentUser.id annotation is {annotation}, expected UUID"


# ─── BUG-013: update_user_status must accept JSON body ───

class TestBUG013UserStatusBody:
    def test_update_user_status_uses_body(self):
        source = _read_source("routers/auth.py")
        # Find the function signature
        match = re.search(r'async def update_user_status\((.*?)\):', source, re.DOTALL)
        assert match, "update_user_status function not found"
        sig = match.group(1)
        # Bug: is_active: bool as bare param (becomes query param)
        # Fix: use a Pydantic model or Body()
        if re.search(r'is_active\s*:\s*bool\s*[,\)]', sig):
            assert 'Body(' in sig, \
                "update_user_status still takes is_active as bare bool query param"


# ─── BUG-019: DashboardMetrics.transcriptsToday should be int ───

class TestBUG019TranscriptsTodayType:
    def test_transcripts_today_accepts_int(self):
        from models.analytics import DashboardMetrics
        field_info = DashboardMetrics.model_fields["transcriptsToday"]
        annotation = field_info.annotation
        # Should not be str or Optional[str]
        import typing
        # Unwrap Optional
        if hasattr(annotation, '__origin__') and annotation.__origin__ is typing.Union:
            args = [a for a in annotation.__args__ if a is not type(None)]
            assert str not in args, \
                "transcriptsToday is Optional[str], should be Optional[int]"
            assert int in args, \
                f"transcriptsToday should include int type, got {args}"
        else:
            assert annotation is not str, \
                "transcriptsToday annotation is str, should be int"
