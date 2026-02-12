from datetime import datetime

from pydantic import BaseModel, Field

# Match type enum values
MATCH_TYPES = ['exact', 'substring', 'fuzzy', 'regex', 'phrase']


class KeywordGroupCreate(BaseModel):
    """Request body for creating a keyword group."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class KeywordGroupUpdate(BaseModel):
    """Request body for updating a keyword group."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class KeywordGroup(BaseModel):
    """Full keyword group model returned from database."""
    id: str
    user_id: str | None = None  # NULL for system templates
    name: str
    description: str | None = None
    is_template: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    # Computed counts
    keyword_count: int = 0
    subscription_count: int = 0

    # Transformed fields for frontend (camelCase)
    userId: str | None = None
    isTemplate: bool | None = None
    isActive: bool | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    keywordCount: int | None = None
    subscriptionCount: int | None = None

    class Config:
        from_attributes = True


class KeywordGroupSummary(BaseModel):
    """Minimal keyword group info for lists."""
    id: str
    name: str
    description: str | None = None
    is_template: bool = False
    is_active: bool = True
    keyword_count: int = 0
    subscription_count: int = 0

    # Transformed fields for frontend
    isTemplate: bool | None = None
    isActive: bool | None = None
    keywordCount: int | None = None
    subscriptionCount: int | None = None

    class Config:
        from_attributes = True


class KeywordGroupListResponse(BaseModel):
    """Response for listing keyword groups."""
    groups: list[KeywordGroupSummary]
    total: int


class TemplateListResponse(BaseModel):
    """Response for listing template keyword groups."""
    templates: list[KeywordGroupSummary]
    total: int


# Keyword models

class KeywordCreate(BaseModel):
    """Request body for creating a keyword."""
    keyword: str = Field(..., min_length=1)
    match_type: str = Field(default='substring', pattern='^(exact|substring|fuzzy|regex|phrase)$')


class KeywordUpdate(BaseModel):
    """Request body for updating a keyword."""
    keyword: str | None = Field(None, min_length=1)
    match_type: str | None = Field(None, pattern='^(exact|substring|fuzzy|regex|phrase)$')
    is_active: bool | None = None


class Keyword(BaseModel):
    """Full keyword model returned from database."""
    id: str
    keyword_group_id: str
    keyword: str
    match_type: str
    is_active: bool = True
    created_at: datetime

    # Transformed fields for frontend (camelCase)
    keywordGroupId: str | None = None
    matchType: str | None = None
    isActive: bool | None = None
    createdAt: str | None = None

    class Config:
        from_attributes = True


class KeywordListResponse(BaseModel):
    """Response for listing keywords in a group."""
    keywords: list[Keyword]
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
    errors: list[str]


# Clone template model

class CloneTemplateRequest(BaseModel):
    """Request body for cloning a template keyword group."""
    template_id: str = Field(..., description="UUID of the template to clone")
    name: str = Field(..., min_length=1, max_length=100, description="Name for the new group")
    description: str | None = None


class LinkedSubscription(BaseModel):
    """Subscription linked to a keyword group."""
    subscription_id: str
    playlist_uuid: str
    playlist_name: str | None = None
    created_at: datetime

    # Transformed fields for frontend
    subscriptionId: str | None = None
    playlistUuid: str | None = None
    playlistName: str | None = None
    createdAt: str | None = None

    class Config:
        from_attributes = True


class KeywordGroupDetail(BaseModel):
    """Detailed keyword group with keywords and linked subscriptions."""
    id: str
    user_id: str | None = None
    name: str
    description: str | None = None
    is_template: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    # Related data
    keywords: list[Keyword] = []
    linked_subscriptions: list[LinkedSubscription] = []

    # Transformed fields for frontend
    userId: str | None = None
    isTemplate: bool | None = None
    isActive: bool | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    linkedSubscriptions: list[LinkedSubscription] | None = None

    class Config:
        from_attributes = True
