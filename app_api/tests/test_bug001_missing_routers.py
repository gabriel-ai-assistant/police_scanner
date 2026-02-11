"""
BUG-001: Missing router files for notifications and webhooks.

Tests that the stub router modules exist, are importable, and expose
a valid FastAPI APIRouter instance.
"""

import importlib
import sys
import os
import pytest

# Ensure app_api is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMissingRouters:
    """BUG-001: notifications.py and webhooks.py must exist as valid routers."""

    def test_notifications_module_importable(self):
        """notifications router module should be importable."""
        from routers import notifications
        assert notifications is not None

    def test_webhooks_module_importable(self):
        """webhooks router module should be importable."""
        from routers import webhooks
        assert webhooks is not None

    def test_notifications_has_router(self):
        """notifications module must expose a 'router' attribute."""
        from routers import notifications
        assert hasattr(notifications, "router"), "notifications module missing 'router' attribute"

    def test_webhooks_has_router(self):
        """webhooks module must expose a 'router' attribute."""
        from routers import webhooks
        assert hasattr(webhooks, "router"), "webhooks module missing 'router' attribute"

    def test_notifications_router_is_apirouter(self):
        """notifications.router must be a FastAPI APIRouter."""
        from fastapi import APIRouter
        from routers import notifications
        assert isinstance(notifications.router, APIRouter)

    def test_webhooks_router_is_apirouter(self):
        """webhooks.router must be a FastAPI APIRouter."""
        from fastapi import APIRouter
        from routers import webhooks
        assert isinstance(webhooks.router, APIRouter)

    def test_main_imports_all_routers_without_error(self):
        """main.py should import all routers including notifications and webhooks."""
        # This verifies that the import line in main.py won't crash
        from routers import (
            health, calls, playlists, transcripts, analytics,
            geography, system, auth, subscriptions, keyword_groups,
            dashboard, ratings, notifications, webhooks, locations
        )
        # All should be importable without ImportError
        assert notifications.router is not None
        assert webhooks.router is not None
