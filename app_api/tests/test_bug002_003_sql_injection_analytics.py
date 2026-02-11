"""
BUG-002/003: SQL injection vulnerabilities in analytics.py.

Tests that SQL queries use parameterized queries ($1, $2) instead of
string interpolation (% or f-strings).
"""

import ast
import os
import sys
import pytest
import inspect
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def get_source(func):
    """Get dedented source of a function."""
    return textwrap.dedent(inspect.getsource(func))


class TestSqlInjectionAnalytics:
    """BUG-002/003: No string interpolation in SQL queries."""

    def test_hourly_activity_no_percent_interpolation(self):
        """get_hourly_activity must not use % string formatting in SQL."""
        from routers.analytics import get_hourly_activity
        source = get_source(get_hourly_activity)
        # Should not contain '% hours' or '%s' pattern in SQL context
        assert "% hours" not in source, "SQL still uses % string interpolation"
        assert '"%s' not in source, "SQL still uses %s formatting"

    def test_hourly_activity_uses_parameterized_query(self):
        """get_hourly_activity must use $1 bind parameter."""
        from routers.analytics import get_hourly_activity
        source = get_source(get_hourly_activity)
        assert "$1" in source, "Should use $1 parameterized query"

    def test_top_talkgroups_no_fstring_interpolation(self):
        """get_top_talkgroups must not use f-string in SQL."""
        from routers.analytics import get_top_talkgroups
        source = get_source(get_top_talkgroups)
        # Should not contain f-string with INTERVAL '{...}'
        assert "f\"\"\"" not in source and "f'''" not in source, \
            "SQL still uses f-string interpolation"
        assert "'{interval}'" not in source, "SQL still interpolates interval variable"

    def test_top_talkgroups_uses_parameterized_query(self):
        """get_top_talkgroups must use $1, $2 bind parameters."""
        from routers.analytics import get_top_talkgroups
        source = get_source(get_top_talkgroups)
        assert "$1" in source, "Should use $1 parameterized query"
        assert "$2" in source, "Should use $2 parameterized query"

    def test_no_string_interpolation_in_any_query(self):
        """Scan the entire analytics module for unsafe SQL patterns."""
        import routers.analytics as mod
        source = inspect.getsource(mod)
        # Check for common SQL injection patterns
        dangerous_patterns = [
            ('""" %', "percent formatting after triple-quote SQL"),
            ("% hours", "percent interpolation with hours"),
            ("'{interval}'", "f-string interval interpolation"),
        ]
        for pattern, description in dangerous_patterns:
            assert pattern not in source, f"Found unsafe pattern: {description}"
