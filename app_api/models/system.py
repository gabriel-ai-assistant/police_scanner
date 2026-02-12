from datetime import datetime

from pydantic import BaseModel


class SystemLog(BaseModel):
    """System log entry."""
    id: int
    timestamp: datetime
    component: str
    event_type: str
    severity: str
    message: str | None = None
    metadata: dict | None = None
    duration_ms: int | None = None

    class Config:
        from_attributes = True


class ProcessingStateCount(BaseModel):
    """Processing state counts."""
    status: str
    count: int


class ProcessingStateSummary(BaseModel):
    """Summary of processing pipeline state."""
    queued: int
    downloaded: int
    transcribed: int
    indexed: int
    error: int
    total: int


class HealthStatus(BaseModel):
    """Health status response."""
    status: str
    database: str
    redis: str
    version: str
    timestamp: datetime
