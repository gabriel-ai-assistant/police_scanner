from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class GeocodeRequest(BaseModel):
    """Request to geocode a location string."""
    query: str = Field(..., description="Location text to geocode")
    bias_city: Optional[str] = Field(None, description="City to bias results towards")
    bias_state: Optional[str] = Field(None, description="State to bias results towards")
    bias_country: str = Field("United States", description="Country to bias results towards")


class GeocodeResult(BaseModel):
    """Result from geocoding operation."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: Optional[float] = None
    formatted_address: Optional[str] = None
    street_name: Optional[str] = None
    street_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
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
    location_type: Optional[str] = None
    playlist_uuid: Optional[UUID] = None
    county_id: Optional[int] = None


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
    geocode_attempts: int = 0
    geocode_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

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
    most_recent: datetime


class LocationListResponse(BaseModel):
    """Response for location list endpoint."""
    items: List[Location]
    total: int
    limit: int
    offset: int


class HeatmapResponse(BaseModel):
    """Response for heatmap endpoint."""
    points: List[HeatmapPoint]
    total_locations: int
    time_window_hours: int
