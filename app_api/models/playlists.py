from datetime import datetime

from pydantic import BaseModel


class PlaylistBase(BaseModel):
    """Base playlist model."""
    name: str
    descr: str | None = None
    sync: bool = False
    listeners: int | None = None
    num_groups: int | None = None


class PlaylistCreate(PlaylistBase):
    """Playlist creation model."""
    pass


class PlaylistUpdate(BaseModel):
    """Playlist update model."""
    sync: bool


class Playlist(PlaylistBase):
    """Full playlist model."""
    uuid: str
    ts: int | None = None
    last_pos: int | None = None
    fetched_at: datetime | None = None

    # Transformed fields (added by API transformer for frontend compatibility)
    id: str | None = None
    isActive: bool | None = None
    state: str | None = None
    updatedAt: str | None = None

    class Config:
        from_attributes = True


class PlaylistStats(BaseModel):
    """Playlist statistics."""
    total_playlists: int
    synced_playlists: int
    total_listeners: int
    avg_groups_per_playlist: float
