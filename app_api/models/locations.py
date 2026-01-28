from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class Location(BaseModel):
    """Location record from database."""
    id: UUID
    source_type: str
    source_id: str
    raw_location_text: str
    location_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geocode_confidence: Optional[float] = None
    geocode_source: Optional[str] = None
    street_name: Optional[str] = None
    street_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    formatted_address: Optional[str] = None
    playlist_uuid: Optional[UUID] = None
    county_id: Optional[int] = None
    geocoded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LocationWithContext(Location):
    """Location with additional context for display."""
    playlist_name: Optional[str] = None
    county_name: Optional[str] = None
    county_state: Optional[str] = None
    transcript_text: Optional[str] = None
    transcript_created_at: Optional[datetime] = None


class HeatmapPoint(BaseModel):
    """Aggregated point for heatmap display."""
    lat: float
    lon: float
    count: int
    most_recent: Optional[datetime] = None


class LocationListResponse(BaseModel):
    """Response for location list endpoint."""
    items: List[LocationWithContext]
    total: int
    limit: int
    offset: int


class HeatmapResponse(BaseModel):
    """Response for heatmap endpoint."""
    points: List[HeatmapPoint]
    total_locations: int
    time_window_hours: int
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None


class BoundingBox(BaseModel):
    """Geographic bounding box for map viewport."""
    sw_lat: float = Field(..., description="Southwest latitude")
    sw_lon: float = Field(..., description="Southwest longitude")
    ne_lat: float = Field(..., description="Northeast latitude")
    ne_lon: float = Field(..., description="Northeast longitude")
