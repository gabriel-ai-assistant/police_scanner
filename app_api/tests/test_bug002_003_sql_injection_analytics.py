"""
BUG-002/003: SQL injection vulnerabilities in analytics.py.

Tests that SQL queries use parameterized queries ($1, $2) instead of
string interpolation (% or f-strings).
"""

import os
import sys
import inspect
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSqlInjectionAnalytics:
    """BUG-002/003: No string interpolation in SQL queries."""

    def test_hourly_activity_no_percent_interpolation(self):
        from routers.analytics import get_hourly_activity
        source = inspect.getsource(get_hourly_activity)
        assert "% hours" not in source, "SQL still uses % string interpolation"

    def test_hourly_activity_uses_parameterized_query(self):
        from routers.analytics import get_hourly_activity
        source = inspect.getsource(get_hourly_activity)
        assert "$1" in source, "Should use $1 parameterized query"

    def test_top_talkgroups_no_fstring_interpolation(self):
        from routers.analytics import get_top_talkgroups
        source = inspect.getsource(get_top_talkgroups)
        assert "'{interval}'" not in source, "SQL still interpolates interval"

    def test_top_talkgroups_uses_parameterized_query(self):
        from routers.analytics import get_top_talkgroups
        source = inspect.getsource(get_top_talkgroups)
        assert "$1" in source and "$2" in source

    def test_no_fstring_sql_in_module(self):
        import routers.analytics as mod
        source = inspect.getsource(mod)
        assert "f\"\"\"" not in source, "f-string triple-quote SQL found"
        assert "f'''" not in source, "f-string triple-quote SQL found"
