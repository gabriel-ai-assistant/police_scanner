"""
BUG-013: update_user_status uses query param instead of request body.

Tests that the endpoint uses a Pydantic model for the request body.
"""

import os
import sys
import inspect
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestStatusEndpointBody:
    """BUG-013: update_user_status must accept is_active via request body."""

    def test_user_status_update_model_exists(self):
        """UserStatusUpdate Pydantic model must exist."""
        from models.auth import UserStatusUpdate
        assert UserStatusUpdate is not None

    def test_user_status_update_model_has_is_active(self):
        """UserStatusUpdate must have an is_active bool field."""
        from models.auth import UserStatusUpdate

        instance = UserStatusUpdate(is_active=True)
        assert instance.is_active is True

        instance2 = UserStatusUpdate(is_active=False)
        assert instance2.is_active is False

    def test_update_user_status_signature_has_body_param(self):
        """update_user_status must accept a body parameter, not bare is_active."""
        from routers.auth import update_user_status

        sig = inspect.signature(update_user_status)
        params = list(sig.parameters.keys())

        # Should have 'body' parameter, not bare 'is_active'
        assert "is_active" not in params, \
            "is_active should not be a direct parameter (use body model)"
        assert "body" in params, \
            "Should have 'body' parameter for UserStatusUpdate model"

    def test_update_user_status_body_type_annotation(self):
        """body parameter should be typed as UserStatusUpdate."""
        from routers.auth import update_user_status
        from models.auth import UserStatusUpdate

        sig = inspect.signature(update_user_status)
        body_param = sig.parameters.get("body")
        assert body_param is not None
        assert body_param.annotation is UserStatusUpdate, \
            f"body should be typed as UserStatusUpdate, got {body_param.annotation}"
