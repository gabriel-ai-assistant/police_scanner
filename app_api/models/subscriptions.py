from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SubscriptionCreate(BaseModel):
    """Request body for subscribing to a playlist."""
    playlist_uuid: str = Field(..., description="UUID of the playlist to subscribe to")


class SubscriptionUpdate(BaseModel):
    """Request body for updating a subscription."""
    notifications_enabled: Optional[bool] = None


class Subscription(BaseModel):
    """Full subscription model returned from database."""
    id: str
    user_id: str
    playlist_uuid: str
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime

    # Joined data from playlists table
    playlist_name: Optional[str] = None
    playlist_descr: Optional[str] = None

    # Computed counts
    keyword_group_count: int = 0

    # Transformed fields for frontend (camelCase)
    userId: Optional[str] = None
    playlistUuid: Optional[str] = None
    notificationsEnabled: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    playlistName: Optional[str] = None
    playlistDescr: Optional[str] = None
    keywordGroupCount: Optional[int] = None

    class Config:
        from_attributes = True


class SubscriptionSummary(BaseModel):
    """Minimal subscription info for lists."""
    id: str
    playlist_uuid: str
    playlist_name: Optional[str] = None
    notifications_enabled: bool
    keyword_group_count: int = 0

    # Transformed fields for frontend
    playlistUuid: Optional[str] = None
    playlistName: Optional[str] = None
    notificationsEnabled: Optional[bool] = None
    keywordGroupCount: Optional[int] = None

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Response for listing user's subscriptions."""
    subscriptions: List[SubscriptionSummary]
    total: int


class SubscriptionStatus(BaseModel):
    """Quick status check for a playlist (is user subscribed?)."""
    playlist_uuid: str
    is_subscribed: bool
    subscription_id: Optional[str] = None

    # Transformed fields for frontend
    playlistUuid: Optional[str] = None
    isSubscribed: Optional[bool] = None
    subscriptionId: Optional[str] = None

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
    keywordGroupId: Optional[str] = None
    keywordGroupName: Optional[str] = None
    keywordCount: Optional[int] = None
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True
