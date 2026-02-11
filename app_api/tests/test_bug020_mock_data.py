"""
BUG-020: Mock/hardcoded data returned in keyword_hits endpoint.

Tests that get_keyword_hits doesn't return hardcoded fake data.
"""

import os
import sys
import inspect
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMockDataRemoved:
    """BUG-020: No hardcoded mock data in analytics endpoints."""

    def test_keyword_hits_no_hardcoded_data(self):
        """get_keyword_hits must not return hardcoded keyword data."""
        from routers.analytics import get_keyword_hits
        source = inspect.getsource(get_keyword_hits)

        # Should not contain hardcoded keywords
        assert '"pursuit"' not in source, "Hardcoded 'pursuit' keyword still present"
        assert '"accident"' not in source, "Hardcoded 'accident' keyword still present"
        assert '"alarm"' not in source, "Hardcoded 'alarm' keyword still present"

    def test_keyword_hits_source_returns_empty_or_query(self):
        """get_keyword_hits should return empty list or query the database."""
        from routers.analytics import get_keyword_hits
        source = inspect.getsource(get_keyword_hits)

        # Should either return [] or contain a SQL query
        has_empty_return = "return []" in source
        has_query = "SELECT" in source or "conn.fetch" in source

        assert has_empty_return or has_query, \
            "Should return empty list (with TODO) or query database"
