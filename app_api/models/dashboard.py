from datetime import datetime

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Top-level dashboard statistics for the current user."""
    my_feeds: int = 0
    my_calls_1h: int = 0
    my_transcripts_24h: int = 0

    # Transformed fields for frontend (camelCase)
    myFeeds: int | None = None
    myCalls1h: int | None = None
    myTranscripts24h: int | None = None

    class Config:
        from_attributes = True


class MyFeed(BaseModel):
    """A feed the user is subscribed to."""
    id: str
    name: str
    description: str | None = None
    listeners: int = 0
    is_active: bool = True
    updated_at: datetime | None = None
    subscribed_at: datetime | None = None

    # Transformed fields for frontend (camelCase)
    isActive: bool | None = None
    updatedAt: str | None = None
    subscribedAt: str | None = None

    class Config:
        from_attributes = True


class MyFeedsResponse(BaseModel):
    """Response for listing user's subscribed feeds."""
    feeds: list[MyFeed]
    total: int
    has_more: bool = False

    # Transformed fields for frontend
    hasMore: bool | None = None

    class Config:
        from_attributes = True


class RecentCall(BaseModel):
    """A recent call from a subscribed feed."""
    id: str
    timestamp: str | None = None
    talkgroup: str | None = None
    duration: int | None = None  # seconds
    feed_name: str | None = None
    feed_id: str | None = None
    audio_url: str | None = None

    # Transformed fields for frontend (camelCase)
    feedName: str | None = None
    feedId: str | None = None
    audioUrl: str | None = None

    class Config:
        from_attributes = True


class RecentCallsResponse(BaseModel):
    """Response for listing recent calls from subscribed feeds."""
    calls: list[RecentCall]

    class Config:
        from_attributes = True


class RecentTranscript(BaseModel):
    """A recent transcript from a subscribed feed."""
    id: int
    text: str | None = None
    confidence: float | None = None
    created_at: datetime | None = None
    feed_name: str | None = None
    feed_id: str | None = None
    call_id: str | None = None

    # Transformed fields for frontend (camelCase)
    createdAt: str | None = None
    feedName: str | None = None
    feedId: str | None = None
    callId: str | None = None

    class Config:
        from_attributes = True


class RecentTranscriptsResponse(BaseModel):
    """Response for listing recent transcripts from subscribed feeds."""
    transcripts: list[RecentTranscript]

    class Config:
        from_attributes = True


class KeywordGroupSummary(BaseModel):
    """Summary of a user's keyword group."""
    name: str
    keyword_count: int = 0
    is_active: bool = True

    # Transformed fields for frontend (camelCase)
    keywordCount: int | None = None
    isActive: bool | None = None

    class Config:
        from_attributes = True


class KeywordSummaryResponse(BaseModel):
    """Response for keyword summary (placeholder until matching engine is built)."""
    groups: list[KeywordGroupSummary]
    total_keywords: int = 0
    message: str = "Keyword matching coming soon"

    # Transformed fields for frontend
    totalKeywords: int | None = None

    class Config:
        from_attributes = True


class RecentActivity(BaseModel):
    """A unified activity item combining call and transcript data."""
    id: str  # call_uid
    timestamp: str | None = None
    talkgroup: str | None = None
    duration: int | None = None  # seconds
    feed_name: str | None = None
    feed_id: str | None = None
    audio_url: str | None = None
    transcript_id: int | None = None
    transcript_text: str | None = None
    transcript_confidence: float | None = None
    user_rating: bool | None = None  # True=up, False=down, None=no rating

    # Transformed fields for frontend (camelCase)
    feedName: str | None = None
    feedId: str | None = None
    audioUrl: str | None = None
    transcriptId: int | None = None
    transcriptText: str | None = None
    transcriptConfidence: float | None = None
    userRating: bool | None = None

    class Config:
        from_attributes = True


class RecentActivityResponse(BaseModel):
    """Response for listing recent activity."""
    activities: list[RecentActivity]

    class Config:
        from_attributes = True


class TranscriptRating(BaseModel):
    """A user's rating for a transcript."""
    id: str
    transcript_id: int
    rating: bool  # True = thumbs up, False = thumbs down
    created_at: str | None = None
    updated_at: str | None = None

    # Transformed fields for frontend
    transcriptId: int | None = None
    createdAt: str | None = None
    updatedAt: str | None = None

    class Config:
        from_attributes = True


class TranscriptRatingRequest(BaseModel):
    """Request to rate a transcript."""
    rating: bool  # True = thumbs up, False = thumbs down


class TranscriptRatingDeleteResponse(BaseModel):
    """Response when a rating is deleted."""
    deleted: bool = True
    message: str = "Rating removed"
