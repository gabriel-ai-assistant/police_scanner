"""
BUG-012: CurrentUser.id stored as str instead of UUID.

Tests that the CurrentUser model uses uuid.UUID for the id field.
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestUuidTypeHandling:
    """BUG-012: CurrentUser.id must be uuid.UUID type."""

    def test_current_user_id_field_is_uuid_type(self):
        """CurrentUser model's id field should accept UUID."""
        from models.auth import CurrentUser

        test_uuid = uuid.uuid4()
        user = CurrentUser(
            id=test_uuid,
            email="test@example.com",
            role="user",
            is_active=True,
        )
        assert isinstance(user.id, uuid.UUID), \
            f"CurrentUser.id should be uuid.UUID, got {type(user.id)}"

    def test_current_user_id_accepts_uuid_string(self):
        """CurrentUser model should accept UUID string and coerce to UUID."""
        from models.auth import CurrentUser

        test_uuid_str = "12345678-1234-5678-1234-567812345678"
        user = CurrentUser(
            id=test_uuid_str,
            email="test@example.com",
            role="user",
            is_active=True,
        )
        assert isinstance(user.id, uuid.UUID)
        assert str(user.id) == test_uuid_str

    def test_current_user_id_rejects_invalid_string(self):
        """CurrentUser model should reject non-UUID strings."""
        from models.auth import CurrentUser
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CurrentUser(
                id="not-a-uuid",
                email="test@example.com",
                role="user",
                is_active=True,
            )

    def test_current_user_id_not_str_annotation(self):
        """CurrentUser.id field annotation must not be str."""
        import typing

        from models.auth import CurrentUser

        hints = typing.get_type_hints(CurrentUser)
        assert hints["id"] is not str, \
            "CurrentUser.id type hint should be uuid.UUID, not str"
        assert hints["id"] is uuid.UUID, \
            f"CurrentUser.id type hint should be uuid.UUID, got {hints['id']}"
