"""
Authentication module for Police Scanner API.

This module provides Firebase Auth integration with httpOnly session cookies.
"""

from .dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_auth,
)
from .firebase import (
    create_session_cookie,
    initialize_firebase,
    revoke_user_sessions,
    verify_firebase_token,
    verify_session_cookie,
)

__all__ = [
    # Firebase functions
    "initialize_firebase",
    "verify_firebase_token",
    "create_session_cookie",
    "verify_session_cookie",
    "revoke_user_sessions",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_auth",
    "require_admin",
]
