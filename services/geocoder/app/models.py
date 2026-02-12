from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GeocodeRequest(BaseModel):
    """Request to geocode a location string."""
    query: str = Field(..., description="Location text to geocode")
    bias_city: str | None = Field(None, description="City to bias results towards")
    bias_state: str | None = Field(None, description="State to bias results towards")
    bias_country: str = Field("United States", description="Country to bias results towards")


class GeocodeResult(BaseModel):
    """Result from geocoding operation."""
    latitude: float | None = None
    longitude: float | None = None
    confidence: float | None = None
    formatted_address: str | None = None
    street_name: str | None = None
    street_number: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    source: str = "nominatim"
    cached: bool = False


class ExtractedLocation(BaseModel):
    """A location extracted from transcript text."""
    raw_text: str = Field(..., description="Original text containing location")
    location_type: str = Field(..., description="Type: address, street, intersection, business, area, landmark")
    confidence: float = Field(default=0.5, description="Extraction confidence 0-1")


class LocationCreate(BaseModel):
    """Create a new location record."""
    source_type: str = Field(..., description="Source type: transcript, keyword_match")
    source_id: str = Field(..., description="ID of source record")
    raw_location_text: str = Field(..., description="Extracted location text")
    location_type: str | None = None
    playlist_uuid: UUID | None = None
    county_id: int | None = None


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
    geocode_attempts: int = 0
    geocode_error: str | None = None
    created_at: datetime
    updated_at: datetime

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
    most_recent: datetime


class LocationListResponse(BaseModel):
    """Response for location list endpoint."""
    items: list[Location]
    total: int
    limit: int
    offset: int


class HeatmapResponse(BaseModel):
    """Response for heatmap endpoint."""
    points: list[HeatmapPoint]
    total_locations: int
    time_window_hours: int
