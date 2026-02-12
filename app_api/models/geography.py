from datetime import datetime

from pydantic import BaseModel


class Country(BaseModel):
    """Country model."""
    coid: int
    country_name: str
    country_code: str
    iso_alpha2: str | None = None
    sync: bool = False
    is_active: bool = True
    fetched_at: datetime | None = None

    class Config:
        from_attributes = True


class State(BaseModel):
    """State model."""
    stid: int
    coid: int
    state_name: str
    state_code: str
    sync: bool = False
    is_active: bool = True
    fetched_at: datetime | None = None

    class Config:
        from_attributes = True


class County(BaseModel):
    """County model."""
    cntid: int
    stid: int
    coid: int
    county_name: str
    county_header: str | None = None
    state_name: str | None = None
    state_code: str | None = None
    country_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    timezone_str: str | None = None
    sync: bool = False
    is_active: bool = True
    fetched_at: datetime | None = None

    class Config:
        from_attributes = True


class CountrySyncUpdate(BaseModel):
    """Update model for country sync status."""
    sync: bool


class StateSyncUpdate(BaseModel):
    """Update model for state sync status."""
    sync: bool


class CountySyncUpdate(BaseModel):
    """Update model for county sync status."""
    sync: bool
