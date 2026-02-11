"""
BUG-004: SQL injection in monitor_data_integrity.py.

Tests that all SQL queries use parameterized queries instead of
string interpolation with % operator.
"""

import inspect
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSqlInjectionMonitor:
    """BUG-004: No string interpolation in monitor SQL queries."""

    def test_check_stuck_calls_no_percent_interpolation(self):
        """check_stuck_calls must not use % string formatting."""
        from monitor_data_integrity import check_stuck_calls
        source = inspect.getsource(check_stuck_calls)
        assert "% hours" not in source, "SQL still uses % string interpolation"
        assert "%s" not in source or "%s" not in source.split("\"\"\"")[1], \
            "SQL still uses %s formatting"

    def test_check_stuck_calls_uses_parameterized_query(self):
        """check_stuck_calls must use $1 bind parameter."""
        from monitor_data_integrity import check_stuck_calls
        source = inspect.getsource(check_stuck_calls)
        assert "$1" in source, "Should use $1 parameterized query"

    def test_check_error_patterns_no_percent_interpolation(self):
        """check_error_patterns must not use % string formatting."""
        from monitor_data_integrity import check_error_patterns
        source = inspect.getsource(check_error_patterns)
        assert "% hours" not in source, "SQL still uses % string interpolation"

    def test_check_error_patterns_uses_parameterized_query(self):
        """check_error_patterns must use $1 bind parameter."""
        from monitor_data_integrity import check_error_patterns
        source = inspect.getsource(check_error_patterns)
        assert "$1" in source, "Should use $1 parameterized query"

    def test_check_null_playlist_uuid_no_percent_interpolation(self):
        """check_null_playlist_uuid must not use % string formatting."""
        from monitor_data_integrity import check_null_playlist_uuid
        source = inspect.getsource(check_null_playlist_uuid)
        assert "% hours" not in source, "SQL still uses % string interpolation"

    def test_get_recent_system_logs_no_percent_interpolation(self):
        """get_recent_system_logs must not use % string formatting."""
        from monitor_data_integrity import get_recent_system_logs
        source = inspect.getsource(get_recent_system_logs)
        assert "% minutes" not in source, "SQL still uses % string interpolation"

    def test_full_module_no_sql_interpolation(self):
        """Entire module should have no % interpolation in SQL contexts."""
        import monitor_data_integrity as mod
        source = inspect.getsource(mod)
        # Find all SQL string blocks and check for % interpolation
        # The pattern '""" % var' is the dangerous one
        lines = source.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') and '%' in stripped:
                # This is a closing triple-quote with % — dangerous
                assert False, f"Line {i+1}: SQL string interpolation found: {stripped}"
            if stripped.endswith('% hours)') or stripped.endswith('% minutes)'):
                assert False, f"Line {i+1}: SQL % interpolation found: {stripped}"
