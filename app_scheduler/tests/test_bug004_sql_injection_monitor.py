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
        from monitor_data_integrity import check_stuck_calls
        source = inspect.getsource(check_stuck_calls)
        assert "% hours" not in source

    def test_check_stuck_calls_uses_parameterized_query(self):
        from monitor_data_integrity import check_stuck_calls
        source = inspect.getsource(check_stuck_calls)
        assert "$1" in source

    def test_check_error_patterns_no_percent_interpolation(self):
        from monitor_data_integrity import check_error_patterns
        source = inspect.getsource(check_error_patterns)
        assert "% hours" not in source

    def test_check_null_playlist_uuid_no_percent_interpolation(self):
        from monitor_data_integrity import check_null_playlist_uuid
        source = inspect.getsource(check_null_playlist_uuid)
        assert "% hours" not in source

    def test_get_recent_system_logs_no_percent_interpolation(self):
        from monitor_data_integrity import get_recent_system_logs
        source = inspect.getsource(get_recent_system_logs)
        assert "% minutes" not in source

    def test_full_module_no_percent_sql_pattern(self):
        """No line should end with % hours) or % minutes) pattern."""
        import monitor_data_integrity as mod
        source = inspect.getsource(mod)
        for i, line in enumerate(source.split('\n'), 1):
            s = line.strip()
            assert not s.endswith('% hours)'), f"Line {i}: SQL % interpolation"
            assert not s.endswith('% minutes)'), f"Line {i}: SQL % interpolation"
