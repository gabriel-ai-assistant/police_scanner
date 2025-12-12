from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TranscriptBase(BaseModel):
    """Base transcript model."""
    model_config = ConfigDict(protected_namespaces=())

    call_uid: str
    text: Optional[str] = None
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    model_name: Optional[str] = None


class Transcript(TranscriptBase):
    """Full transcript model."""
    id: int
    created_at: Optional[datetime] = None
    recording_id: Optional[int] = None

    # Transformed fields (added by API transformer for frontend compatibility)
    createdAt: Optional[str] = None
    callId: Optional[str] = None
    segments: Optional[list] = None

    class Config:
        from_attributes = True


class TranscriptSearchResult(Transcript):
    """Transcript search result with relevance rank."""
    rank: Optional[float] = None


class TranscriptionQuality(BaseModel):
    """Transcription quality metrics."""
    avg_confidence: float
    total_transcripts: int
    avg_duration_seconds: float
    language_distribution: dict
