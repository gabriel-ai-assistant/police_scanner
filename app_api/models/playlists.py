from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PlaylistBase(BaseModel):
    """Base playlist model."""
    name: str
    descr: Optional[str] = None
    sync: bool = False
    listeners: Optional[int] = None
    num_groups: Optional[int] = None


class PlaylistCreate(PlaylistBase):
    """Playlist creation model."""
    pass


class PlaylistUpdate(BaseModel):
    """Playlist update model."""
    sync: bool


class Playlist(PlaylistBase):
    """Full playlist model."""
    uuid: str
    ts: Optional[int] = None
    last_pos: Optional[int] = None
    fetched_at: Optional[datetime] = None

    # Transformed fields (added by API transformer for frontend compatibility)
    id: Optional[str] = None
    isActive: Optional[bool] = None
    state: Optional[str] = None
    updatedAt: Optional[str] = None

    class Config:
        from_attributes = True


class PlaylistStats(BaseModel):
    """Playlist statistics."""
    total_playlists: int
    synced_playlists: int
    total_listeners: int
    avg_groups_per_playlist: float
