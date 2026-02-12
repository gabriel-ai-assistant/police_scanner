from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Location(BaseModel):
    """Location record from database."""
    id: UUID
    source_type: str
    source_id: str
    raw_location_text: str
    location_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geocode_confidence: float | None = None
    geocode_source: str | None = None
    street_name: str | None = None
    street_number: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    formatted_address: str | None = None
    playlist_uuid: UUID | None = None
    county_id: int | None = None
    geocoded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class LocationWithContext(Location):
    """Location with additional context for display."""
    playlist_name: str | None = None
    county_name: str | None = None
    county_state: str | None = None
    transcript_text: str | None = None
    transcript_created_at: datetime | None = None


class HeatmapPoint(BaseModel):
    """Aggregated point for heatmap display."""
    lat: float
    lon: float
    count: int
    most_recent: datetime | None = None


class LocationListResponse(BaseModel):
    """Response for location list endpoint."""
    items: list[LocationWithContext]
    total: int
    limit: int
    offset: int


class HeatmapResponse(BaseModel):
    """Response for heatmap endpoint."""
    points: list[HeatmapPoint]
    total_locations: int
    time_window_hours: int
    center_lat: float | None = None
    center_lon: float | None = None


class BoundingBox(BaseModel):
    """Geographic bounding box for map viewport."""
    sw_lat: float = Field(..., description="Southwest latitude")
    sw_lon: float = Field(..., description="Southwest longitude")
    ne_lat: float = Field(..., description="Northeast latitude")
    ne_lon: float = Field(..., description="Northeast longitude")
