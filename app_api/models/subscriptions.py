from datetime import datetime

from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    """Request body for subscribing to a playlist."""
    playlist_uuid: str = Field(..., description="UUID of the playlist to subscribe to")


class SubscriptionUpdate(BaseModel):
    """Request body for updating a subscription."""
    notifications_enabled: bool | None = None


class Subscription(BaseModel):
    """Full subscription model returned from database."""
    id: str
    user_id: str
    playlist_uuid: str
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime

    # Joined data from playlists table
    playlist_name: str | None = None
    playlist_descr: str | None = None

    # Computed counts
    keyword_group_count: int = 0

    # Transformed fields for frontend (camelCase)
    userId: str | None = None
    playlistUuid: str | None = None
    notificationsEnabled: bool | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    playlistName: str | None = None
    playlistDescr: str | None = None
    keywordGroupCount: int | None = None

    class Config:
        from_attributes = True


class SubscriptionSummary(BaseModel):
    """Minimal subscription info for lists."""
    id: str
    playlist_uuid: str
    playlist_name: str | None = None
    notifications_enabled: bool
    keyword_group_count: int = 0

    # Transformed fields for frontend
    playlistUuid: str | None = None
    playlistName: str | None = None
    notificationsEnabled: bool | None = None
    keywordGroupCount: int | None = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Response for listing user's subscriptions."""
    subscriptions: list[SubscriptionSummary]
    total: int


class SubscriptionStatus(BaseModel):
    """Quick status check for a playlist (is user subscribed?)."""
    playlist_uuid: str
    is_subscribed: bool
    subscription_id: str | None = None

    # Transformed fields for frontend
    playlistUuid: str | None = None
    isSubscribed: bool | None = None
    subscriptionId: str | None = None

    class Config:
        from_attributes = True


class LinkKeywordGroupRequest(BaseModel):
    """Request body for linking a keyword group to a subscription."""
    keyword_group_id: str = Field(..., description="UUID of the keyword group to link")


class LinkedKeywordGroup(BaseModel):
    """Keyword group linked to a subscription."""
    id: str
    keyword_group_id: str
    keyword_group_name: str
    keyword_count: int = 0
    created_at: datetime

    # Transformed fields for frontend
    keywordGroupId: str | None = None
    keywordGroupName: str | None = None
    keywordCount: int | None = None
    createdAt: str | None = None

    class Config:
        from_attributes = True
