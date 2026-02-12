from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
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
    last_login_at: datetime | None = None

    # Transformed fields for frontend (camelCase)
    firebaseUid: str | None = None
    emailVerified: bool | None = None
    displayName: str | None = None
    avatarUrl: str | None = None
    isActive: bool | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    lastLoginAt: str | None = None

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Public user info (safe to expose to other users)."""
    id: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: str

    # Transformed fields for frontend
    displayName: str | None = None
    avatarUrl: str | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Model for updating user profile (self-service)."""
    display_name: str | None = Field(None, max_length=100)


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
    user_id: str | None = None
    event_type: str
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict | None = None
    created_at: datetime

    # Transformed fields for frontend
    userId: str | None = None
    eventType: str | None = None
    ipAddress: str | None = None
    userAgent: str | None = None
    createdAt: str | None = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Response for listing users (admin)."""
    users: list[User]
    total: int
    limit: int
    offset: int


class CurrentUser(BaseModel):
    """Minimal user info for auth dependency."""
    id: str
    email: str
    role: str
    is_active: bool = True
