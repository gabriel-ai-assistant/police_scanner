from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Country(BaseModel):
    """Country model."""
    coid: int
    country_name: str
    country_code: str
    iso_alpha2: Optional[str] = None
    sync: bool = False
    is_active: bool = True
    fetched_at: Optional[datetime] = None

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
    fetched_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class County(BaseModel):
    """County model."""
    cntid: int
    stid: int
    coid: int
    county_name: str
    county_header: Optional[str] = None
    state_name: Optional[str] = None
    state_code: Optional[str] = None
    country_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone_str: Optional[str] = None
    sync: bool = False
    is_active: bool = True
    fetched_at: Optional[datetime] = None

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
