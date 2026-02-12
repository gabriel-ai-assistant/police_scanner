"""
Firebase Admin SDK wrapper for authentication.

This module handles Firebase token verification and session cookie management.
"""

import logging
import os
from datetime import timedelta

import firebase_admin
from config import settings
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

# Firebase app instance (singleton)
_firebase_app: firebase_admin.App | None = None


def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK.

    Returns True if initialization was successful, False otherwise.
    Should be called once during app startup.
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.debug("Firebase already initialized")
        return True

    service_account_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH

    # Check if service account file exists
    if not os.path.exists(service_account_path):
        logger.warning(
            f"Firebase service account file not found at {service_account_path}. "
            "Authentication will not work until this file is provided."
        )
        return False

    try:
        cred = credentials.Certificate(service_account_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False


def is_firebase_initialized() -> bool:
    """Check if Firebase Admin SDK is initialized."""
    return _firebase_app is not None


async def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.

    Args:
        id_token: The Firebase ID token from the client

    Returns:
        Decoded token claims including uid, email, etc.

    Raises:
        ValueError: If token is invalid or expired
        RuntimeError: If Firebase is not initialized
    """
    if not is_firebase_initialized():
        raise RuntimeError("Firebase Admin SDK not initialized")

    try:
        # verify_id_token is synchronous but fast (just JWT verification)
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase ID token: {e}")
        raise ValueError("Invalid authentication token")
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase ID token: {e}")
        raise ValueError("Authentication token has expired")
    except auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked Firebase ID token: {e}")
        raise ValueError("Authentication token has been revoked")
    except FirebaseError as e:
        logger.error(f"Firebase error verifying token: {e}")
        raise ValueError("Authentication verification failed")


async def create_session_cookie(id_token: str, expires_in: int = None) -> str:
    """
    Create a session cookie from a Firebase ID token.

    Args:
        id_token: Valid Firebase ID token
        expires_in: Cookie expiration in seconds (default from settings)

    Returns:
        Session cookie string

    Raises:
        ValueError: If token is invalid
        RuntimeError: If Firebase is not initialized
    """
    if not is_firebase_initialized():
        raise RuntimeError("Firebase Admin SDK not initialized")

    if expires_in is None:
        expires_in = settings.SESSION_COOKIE_MAX_AGE

    try:
        # Firebase session cookie creation
        session_cookie = auth.create_session_cookie(
            id_token,
            expires_in=timedelta(seconds=expires_in)
        )
        return session_cookie
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid ID token for session cookie: {e}")
        raise ValueError("Invalid authentication token")
    except FirebaseError as e:
        logger.error(f"Firebase error creating session cookie: {e}")
        raise ValueError("Failed to create session")


async def verify_session_cookie(session_cookie: str, check_revoked: bool = True) -> dict:
    """
    Verify a Firebase session cookie.

    Args:
        session_cookie: The session cookie to verify
        check_revoked: Whether to check if the session has been revoked

    Returns:
        Decoded token claims

    Raises:
        ValueError: If cookie is invalid or expired
        RuntimeError: If Firebase is not initialized
    """
    if not is_firebase_initialized():
        raise RuntimeError("Firebase Admin SDK not initialized")

    try:
        decoded_claims = auth.verify_session_cookie(
            session_cookie,
            check_revoked=check_revoked
        )
        return decoded_claims
    except auth.InvalidSessionCookieError as e:
        logger.debug(f"Invalid session cookie: {e}")
        raise ValueError("Invalid session")
    except auth.ExpiredSessionCookieError as e:
        logger.debug(f"Expired session cookie: {e}")
        raise ValueError("Session has expired")
    except auth.RevokedSessionCookieError as e:
        logger.debug(f"Revoked session cookie: {e}")
        raise ValueError("Session has been revoked")
    except FirebaseError as e:
        logger.error(f"Firebase error verifying session cookie: {e}")
        raise ValueError("Session verification failed")


async def revoke_user_sessions(uid: str) -> None:
    """
    Revoke all sessions for a user.

    This invalidates all refresh tokens and session cookies for the user.

    Args:
        uid: Firebase user UID

    Raises:
        RuntimeError: If Firebase is not initialized
    """
    if not is_firebase_initialized():
        raise RuntimeError("Firebase Admin SDK not initialized")

    try:
        auth.revoke_refresh_tokens(uid)
        logger.info(f"Revoked all sessions for user {uid}")
    except FirebaseError as e:
        logger.error(f"Failed to revoke sessions for user {uid}: {e}")
        raise
