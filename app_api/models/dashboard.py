from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DashboardStats(BaseModel):
    """Top-level dashboard statistics for the current user."""
    my_feeds: int = 0
    my_calls_1h: int = 0
    my_transcripts_24h: int = 0

    # Transformed fields for frontend (camelCase)
    myFeeds: Optional[int] = None
    myCalls1h: Optional[int] = None
    myTranscripts24h: Optional[int] = None

    class Config:
        from_attributes = True


class MyFeed(BaseModel):
    """A feed the user is subscribed to."""
    id: str
    name: str
    description: Optional[str] = None
    listeners: int = 0
    is_active: bool = True
    updated_at: Optional[datetime] = None
    subscribed_at: Optional[datetime] = None

    # Transformed fields for frontend (camelCase)
    isActive: Optional[bool] = None
    updatedAt: Optional[str] = None
    subscribedAt: Optional[str] = None

    class Config:
        from_attributes = True


class MyFeedsResponse(BaseModel):
    """Response for listing user's subscribed feeds."""
    feeds: List[MyFeed]
    total: int
    has_more: bool = False

    # Transformed fields for frontend
    hasMore: Optional[bool] = None

    class Config:
        from_attributes = True


class RecentCall(BaseModel):
    """A recent call from a subscribed feed."""
    id: str
    timestamp: Optional[str] = None
    talkgroup: Optional[str] = None
    duration: Optional[int] = None  # seconds
    feed_name: Optional[str] = None
    feed_id: Optional[str] = None
    audio_url: Optional[str] = None

    # Transformed fields for frontend (camelCase)
    feedName: Optional[str] = None
    feedId: Optional[str] = None
    audioUrl: Optional[str] = None

    class Config:
        from_attributes = True


class RecentCallsResponse(BaseModel):
    """Response for listing recent calls from subscribed feeds."""
    calls: List[RecentCall]

    class Config:
        from_attributes = True


class RecentTranscript(BaseModel):
    """A recent transcript from a subscribed feed."""
    id: int
    text: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    feed_name: Optional[str] = None
    feed_id: Optional[str] = None
    call_id: Optional[str] = None

    # Transformed fields for frontend (camelCase)
    createdAt: Optional[str] = None
    feedName: Optional[str] = None
    feedId: Optional[str] = None
    callId: Optional[str] = None

    class Config:
        from_attributes = True


class RecentTranscriptsResponse(BaseModel):
    """Response for listing recent transcripts from subscribed feeds."""
    transcripts: List[RecentTranscript]

    class Config:
        from_attributes = True


class KeywordGroupSummary(BaseModel):
    """Summary of a user's keyword group."""
    name: str
    keyword_count: int = 0
    is_active: bool = True

    # Transformed fields for frontend (camelCase)
    keywordCount: Optional[int] = None
    isActive: Optional[bool] = None

    class Config:
        from_attributes = True


class KeywordSummaryResponse(BaseModel):
    """Response for keyword summary (placeholder until matching engine is built)."""
    groups: List[KeywordGroupSummary]
    total_keywords: int = 0
    message: str = "Keyword matching coming soon"

    # Transformed fields for frontend
    totalKeywords: Optional[int] = None

    class Config:
        from_attributes = True


class RecentActivity(BaseModel):
    """A unified activity item combining call and transcript data."""
    id: str  # call_uid
    timestamp: Optional[str] = None
    talkgroup: Optional[str] = None
    duration: Optional[int] = None  # seconds
    feed_name: Optional[str] = None
    feed_id: Optional[str] = None
    audio_url: Optional[str] = None
    transcript_id: Optional[int] = None
    transcript_text: Optional[str] = None
    transcript_confidence: Optional[float] = None
    user_rating: Optional[bool] = None  # True=up, False=down, None=no rating

    # Transformed fields for frontend (camelCase)
    feedName: Optional[str] = None
    feedId: Optional[str] = None
    audioUrl: Optional[str] = None
    transcriptId: Optional[int] = None
    transcriptText: Optional[str] = None
    transcriptConfidence: Optional[float] = None
    userRating: Optional[bool] = None

    class Config:
        from_attributes = True


class RecentActivityResponse(BaseModel):
    """Response for listing recent activity."""
    activities: List[RecentActivity]

    class Config:
        from_attributes = True


class TranscriptRating(BaseModel):
    """A user's rating for a transcript."""
    id: str
    transcript_id: int
    rating: bool  # True = thumbs up, False = thumbs down
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Transformed fields for frontend
    transcriptId: Optional[int] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    class Config:
        from_attributes = True


class TranscriptRatingRequest(BaseModel):
    """Request to rate a transcript."""
    rating: bool  # True = thumbs up, False = thumbs down


class TranscriptRatingDeleteResponse(BaseModel):
    """Response when a rating is deleted."""
    deleted: bool = True
    message: str = "Rating removed"
