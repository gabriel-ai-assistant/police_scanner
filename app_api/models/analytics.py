from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class KeywordHit(BaseModel):
    """Keyword hit model."""
    keyword: str
    count: int


class HourlyPoint(BaseModel):
    """Hourly activity data point."""
    hour: str
    count: int


class TalkgroupHit(BaseModel):
    """Talkgroup activity model."""
    tg_id: int
    display: Optional[str] = None
    count: int


class DashboardMetrics(BaseModel):
    """Dashboard summary metrics."""
    total_calls_24h: int
    active_playlists: int
    transcripts_today: int
    avg_transcription_confidence: float
    processing_queue_size: int
    api_calls_today: int
    recent_calls: List[dict]
    top_talkgroups: List[TalkgroupHit]

    # Transformed fields (added by API transformer for frontend compatibility)
    feedCount: Optional[int] = None
    activeFeeds: Optional[int] = None
    recentCalls: Optional[int] = None
    transcriptsToday: Optional[str] = None


class QualityDistribution(BaseModel):
    """Transcription quality distribution."""
    excellent: int  # > 0.85
    good: int  # 0.7 - 0.85
    fair: int  # 0.5 - 0.7
    poor: int  # < 0.5


class ApiMetricsSummary(BaseModel):
    """API metrics summary."""
    total_calls_today: int
    avg_response_time_ms: float
    error_rate: float
    cache_hit_rate: float
