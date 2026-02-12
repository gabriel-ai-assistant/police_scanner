from datetime import datetime

from pydantic import BaseModel


class CallMetadata(BaseModel):
    """Call metadata response model."""
    call_uid: str
    feed_id: int | None = None
    tg_id: int | None = None
    tag_id: int | None = None
    url: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int | None = None
    size_bytes: int | None = None
    fetched_at: datetime | None = None
    processed: bool = False
    error: str | None = None

    # Transformed fields (added by API transformer for frontend compatibility)
    timestamp: str | None = None

    class Config:
        from_attributes = True


class CallDetail(CallMetadata):
    """Extended call detail with transcript info."""
    transcript_text: str | None = None
    transcript_confidence: float | None = None
    audio_url: str | None = None


class HourlyStats(BaseModel):
    """Hourly call statistics."""
    hour: datetime
    count: int


class FeedStats(BaseModel):
    """Statistics grouped by feed."""
    feed_id: int
    count: int
    avg_duration_ms: float | None = None
