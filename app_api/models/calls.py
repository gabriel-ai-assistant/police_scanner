from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CallMetadata(BaseModel):
    """Call metadata response model."""
    call_uid: str
    feed_id: Optional[int] = None
    tg_id: Optional[int] = None
    tag_id: Optional[int] = None
    url: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    size_bytes: Optional[int] = None
    fetched_at: Optional[datetime] = None
    processed: bool = False
    error: Optional[str] = None

    class Config:
        from_attributes = True


class CallDetail(CallMetadata):
    """Extended call detail with transcript info."""
    transcript_text: Optional[str] = None
    transcript_confidence: Optional[float] = None
    audio_url: Optional[str] = None


class HourlyStats(BaseModel):
    """Hourly call statistics."""
    hour: datetime
    count: int


class FeedStats(BaseModel):
    """Statistics grouped by feed."""
    feed_id: int
    count: int
    avg_duration_ms: Optional[float] = None
