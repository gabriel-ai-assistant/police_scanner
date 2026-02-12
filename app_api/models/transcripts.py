from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TranscriptBase(BaseModel):
    """Base transcript model."""
    model_config = ConfigDict(protected_namespaces=())

    call_uid: str
    text: str | None = None
    confidence: float | None = None
    duration_seconds: float | None = None
    language: str | None = None
    model_name: str | None = None


class Transcript(TranscriptBase):
    """Full transcript model."""
    id: int
    created_at: datetime | None = None
    recording_id: int | None = None

    # Transformed fields (added by API transformer for frontend compatibility)
    createdAt: str | None = None
    callId: str | None = None
    segments: list | None = None

    class Config:
        from_attributes = True


class TranscriptSearchResult(Transcript):
    """Transcript search result with relevance rank."""
    rank: float | None = None


class TranscriptionQuality(BaseModel):
    """Transcription quality metrics."""
    avg_confidence: float
    total_transcripts: int
    avg_duration_seconds: float
    language_distribution: dict
