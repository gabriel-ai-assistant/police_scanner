from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Match type enum values
MATCH_TYPES = ['exact', 'substring', 'fuzzy', 'regex', 'phrase']


class KeywordGroupCreate(BaseModel):
    """Request body for creating a keyword group."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class KeywordGroupUpdate(BaseModel):
    """Request body for updating a keyword group."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class KeywordGroup(BaseModel):
    """Full keyword group model returned from database."""
    id: str
    user_id: Optional[str] = None  # NULL for system templates
    name: str
    description: Optional[str] = None
    is_template: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    # Computed counts
    keyword_count: int = 0
    subscription_count: int = 0

    # Transformed fields for frontend (camelCase)
    userId: Optional[str] = None
    isTemplate: Optional[bool] = None
    isActive: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    keywordCount: Optional[int] = None
    subscriptionCount: Optional[int] = None

    class Config:
        from_attributes = True


class KeywordGroupSummary(BaseModel):
    """Minimal keyword group info for lists."""
    id: str
    name: str
    description: Optional[str] = None
    is_template: bool = False
    is_active: bool = True
    keyword_count: int = 0
    subscription_count: int = 0

    # Transformed fields for frontend
    isTemplate: Optional[bool] = None
    isActive: Optional[bool] = None
    keywordCount: Optional[int] = None
    subscriptionCount: Optional[int] = None

    class Config:
        from_attributes = True


class KeywordGroupListResponse(BaseModel):
    """Response for listing keyword groups."""
    groups: List[KeywordGroupSummary]
    total: int


class TemplateListResponse(BaseModel):
    """Response for listing template keyword groups."""
    templates: List[KeywordGroupSummary]
    total: int


# Keyword models

class KeywordCreate(BaseModel):
    """Request body for creating a keyword."""
    keyword: str = Field(..., min_length=1)
    match_type: str = Field(default='substring', pattern='^(exact|substring|fuzzy|regex|phrase)$')


class KeywordUpdate(BaseModel):
    """Request body for updating a keyword."""
    keyword: Optional[str] = Field(None, min_length=1)
    match_type: Optional[str] = Field(None, pattern='^(exact|substring|fuzzy|regex|phrase)$')
    is_active: Optional[bool] = None


class Keyword(BaseModel):
    """Full keyword model returned from database."""
    id: str
    keyword_group_id: str
    keyword: str
    match_type: str
    is_active: bool = True
    created_at: datetime

    # Transformed fields for frontend (camelCase)
    keywordGroupId: Optional[str] = None
    matchType: Optional[str] = None
    isActive: Optional[bool] = None
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True


class KeywordListResponse(BaseModel):
    """Response for listing keywords in a group."""
    keywords: List[Keyword]
    total: int


# Bulk import models

class BulkKeywordImport(BaseModel):
    """Request body for bulk importing keywords."""
    keywords: str = Field(..., description="Newline-separated keywords")
    match_type: str = Field(
        default='substring',
        pattern='^(exact|substring|fuzzy|regex|phrase)$',
        description="Match type to apply to all imported keywords"
    )


class BulkImportResponse(BaseModel):
    """Response from bulk keyword import."""
    imported: int
    skipped: int
    errors: List[str]


# Clone template model

class CloneTemplateRequest(BaseModel):
    """Request body for cloning a template keyword group."""
    template_id: str = Field(..., description="UUID of the template to clone")
    name: str = Field(..., min_length=1, max_length=100, description="Name for the new group")
    description: Optional[str] = None


class LinkedSubscription(BaseModel):
    """Subscription linked to a keyword group."""
    subscription_id: str
    playlist_uuid: str
    playlist_name: Optional[str] = None
    created_at: datetime

    # Transformed fields for frontend
    subscriptionId: Optional[str] = None
    playlistUuid: Optional[str] = None
    playlistName: Optional[str] = None
    createdAt: Optional[str] = None

    class Config:
        from_attributes = True


class KeywordGroupDetail(BaseModel):
    """Detailed keyword group with keywords and linked subscriptions."""
    id: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    is_template: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    # Related data
    keywords: List[Keyword] = []
    linked_subscriptions: List[LinkedSubscription] = []

    # Transformed fields for frontend
    userId: Optional[str] = None
    isTemplate: Optional[bool] = None
    isActive: Optional[bool] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    linkedSubscriptions: Optional[List[LinkedSubscription]] = None

    class Config:
        from_attributes = True
