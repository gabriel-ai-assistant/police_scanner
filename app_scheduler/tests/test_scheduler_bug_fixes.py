"""
Tests for bug fixes in app_scheduler.
Uses source-level inspection to avoid import issues with missing deps.
"""
import os
import re

SCHED_DIR = os.path.join(os.path.dirname(__file__), "..")


def _read(relpath):
    with open(os.path.join(SCHED_DIR, relpath)) as f:
        return f.read()


# ─── BUG-004: monitor_data_integrity must not use string interpolation in SQL ───

class TestBUG004NoSQLInterpolation:
    def test_no_percent_formatting_in_sql(self):
        source = _read("monitor_data_integrity.py")
        matches = re.findall(r'"""\s*%\s*\w+', source)
        assert len(matches) == 0, \
            f"Found SQL string interpolation via %: {matches}"

    def test_check_stuck_calls_parameterized(self):
        source = _read("monitor_data_integrity.py")
        # Extract check_stuck_calls function
        match = re.search(r'async def check_stuck_calls\(.*?\nasync def ', source, re.DOTALL)
        func = match.group() if match else source
        assert '% hours' not in func, \
            "check_stuck_calls uses '% hours' string interpolation"

    def test_check_error_patterns_parameterized(self):
        source = _read("monitor_data_integrity.py")
        match = re.search(r'async def check_error_patterns\(.*?\nasync def ', source, re.DOTALL)
        func = match.group() if match else ""
        assert '% hours' not in func, \
            "check_error_patterns uses '% hours' string interpolation"

    def test_check_null_playlist_uuid_parameterized(self):
        source = _read("monitor_data_integrity.py")
        match = re.search(r'async def check_null_playlist_uuid\(.*?\nasync def ', source, re.DOTALL)
        func = match.group() if match else ""
        assert '% hours' not in func, \
            "check_null_playlist_uuid uses '% hours' string interpolation"

    def test_get_recent_system_logs_parameterized(self):
        source = _read("monitor_data_integrity.py")
        match = re.search(r'async def get_recent_system_logs\(.*?\nasync def ', source, re.DOTALL)
        func = match.group() if match else ""
        assert '% minutes' not in func, \
            "get_recent_system_logs uses '% minutes' string interpolation"


# ─── BUG-035: Scheduler shutdown must call close_pool ───

class TestBUG035SchedulerShutdown:
    def test_scheduler_references_close_pool(self):
        source = _read("scheduler.py")
        assert "close_pool" in source, \
            "scheduler.py does not reference close_pool for shutdown cleanup"

    def test_scheduler_imports_close_pool(self):
        source = _read("scheduler.py")
        assert re.search(r'from\s+\w+\s+import.*close_pool|import.*close_pool', source), \
            "scheduler.py does not import close_pool"
