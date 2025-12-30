---
name: "Pydantic Models"
description: "Create and maintain Pydantic request/response schemas"
---

## Context

Use this skill when creating or modifying Pydantic models for the FastAPI backend. These models define the contract between API endpoints and clients.

## Scope

Files this agent works with:
- `app_api/models/*.py` - All Pydantic model definitions

## Instructions

When invoked, follow these steps:

1. **Understand the requirement**
   - Identify what data structure is needed
   - Check if similar models exist to inherit from
   - Determine if this is request, response, or both

2. **Design the model**
   - Map database columns to Pydantic fields
   - Determine which fields are optional
   - Add validators for complex fields

3. **Implement**
   - Create model class extending BaseModel
   - Add type hints for all fields
   - Configure model settings (from_attributes, etc.)

4. **Verify**
   - Check model matches database schema
   - Test serialization/deserialization
   - Verify OpenAPI docs generate correctly

## Behaviors

- Define separate models for Create, Update, and Response DTOs
- Use `Optional[T] = None` for nullable fields
- Add `Config` class with `from_attributes = True` for ORM mode
- Match field names to database column names (snake_case)
- Add Field validators for complex validation
- Include Field examples for OpenAPI documentation

## Constraints

- Never use `Any` type - always define proper types
- Never duplicate models - inherit or compose
- Always include example values in Field() for OpenAPI docs
- Never expose sensitive fields (passwords, tokens) in response models
- Never skip validation for user input

## Safety Checks

Before completing:
- [ ] Model fields match database schema
- [ ] Response models include all needed fields
- [ ] Nested model references exist
- [ ] Sensitive fields excluded from responses
- [ ] Validators handle edge cases

## Model Patterns

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

# Response model (what API returns)
class CallResponse(BaseModel):
    call_uid: str
    feed_id: int
    started_at: datetime
    duration_ms: Optional[int] = None
    transcript: Optional[str] = None

    class Config:
        from_attributes = True  # Enables ORM mode

# Create model (what client sends to create)
class CallCreate(BaseModel):
    feed_id: int = Field(..., example=123)
    audio_url: str = Field(..., example="https://example.com/audio.mp3")

# Update model (partial update support)
class CallUpdate(BaseModel):
    transcript: Optional[str] = None
    processed: Optional[bool] = None

# With validator
class TranscriptCreate(BaseModel):
    call_uid: str
    text: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @validator('text')
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or whitespace')
        return v.strip()
```

## Response Transformation Pattern

```python
def transform_call_response(row: dict) -> dict:
    """Transform database row to camelCase response."""
    return {
        "callUid": row["call_uid"],
        "feedId": row["feed_id"],
        "startedAt": row["started_at"].isoformat() if row["started_at"] else None,
        "durationMs": row["duration_ms"],
    }
```
