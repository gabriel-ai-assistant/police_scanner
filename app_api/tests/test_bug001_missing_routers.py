"""
BUG-001: Missing router files for notifications and webhooks.

Tests that the stub router modules exist, are importable, and expose
a valid FastAPI APIRouter instance.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMissingRouters:
    """BUG-001: notifications.py and webhooks.py must exist as valid routers."""

    def test_notifications_module_importable(self):
        from routers import notifications
        assert notifications is not None

    def test_webhooks_module_importable(self):
        from routers import webhooks
        assert webhooks is not None

    def test_notifications_has_router(self):
        from routers import notifications
        assert hasattr(notifications, "router")

    def test_webhooks_has_router(self):
        from routers import webhooks
        assert hasattr(webhooks, "router")

    def test_notifications_router_is_apirouter(self):
        from fastapi import APIRouter
        from routers import notifications
        assert isinstance(notifications.router, APIRouter)

    def test_webhooks_router_is_apirouter(self):
        from fastapi import APIRouter
        from routers import webhooks
        assert isinstance(webhooks.router, APIRouter)
