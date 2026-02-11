import uuid

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    """Model for creating a new user (internal use)."""
    firebase_uid: str
    email_verified: bool = False


class User(UserBase):
    """Full user model returned from database."""
    id: str
    firebase_uid: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    # Transformed fields for frontend (camelCase)
    firebaseUid: Optional[str] = None
    emailVerified: Optional[bool] = None
    displayName: Optional[str] = None
    avatarUrl: Optional[str] = None
    isActive: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    lastLoginAt: Optional[str] = None

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Public user info (safe to expose to other users)."""
    id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str

    # Transformed fields for frontend
    displayName: Optional[str] = None
    avatarUrl: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Model for updating user profile (self-service)."""
    display_name: Optional[str] = Field(None, max_length=100)


class UserRoleUpdate(BaseModel):
    """Model for updating user role (admin only)."""
    role: str = Field(..., pattern="^(user|admin)$")


class SessionRequest(BaseModel):
    """Request body for creating a session from Firebase token."""
    id_token: str = Field(..., description="Firebase ID token from client")


class SessionResponse(BaseModel):
    """Response after successful session creation."""
    user: User
    message: str = "Session created successfully"


class AuthAuditLog(BaseModel):
    """Auth audit log entry."""
    id: int
    user_id: Optional[str] = None
    event_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime

    # Transformed fields for frontend
    userId: Optional[str] = None
    eventType: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response for listing users (admin)."""
    users: List[User]
    total: int
    limit: int
    offset: int


class CurrentUser(BaseModel):
    """Minimal user info for auth dependency."""
    id: uuid.UUID
    email: str
    role: str
    is_active: bool = True
