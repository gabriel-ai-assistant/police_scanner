from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class SystemLog(BaseModel):
    """System log entry."""
    id: int
    timestamp: datetime
    component: str
    event_type: str
    severity: str
    message: Optional[str] = None
    metadata: Optional[Dict] = None
    duration_ms: Optional[int] = None

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
