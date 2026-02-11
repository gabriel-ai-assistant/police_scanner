# Code Patterns Reference

Quick reference for consistent code patterns across the Police Scanner Platform.

## Python (Backend)

### Database Queries
```python
# AsyncPG (app_api, app_scheduler)
async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT * FROM table WHERE id = $1", param)
    row = await conn.fetchrow("SELECT * FROM table WHERE id = $1", param)
    await conn.execute("INSERT INTO table (col) VALUES ($1)", value)

# Psycopg2 (app_transcribe - sync)
cursor = conn.cursor()
cursor.execute("SELECT * FROM table WHERE id = %s", (param,))
rows = cursor.fetchall()
conn.commit()
cursor.close()
```

### Error Handling
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = await risky_operation()
except SpecificError as e:
    logger.warning(f"Expected error: {e}")
    return fallback_value
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

### Pydantic Models
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MyModel(BaseModel):
    required_field: str
    optional_field: Optional[int] = None
    validated_field: int = Field(..., ge=1, le=1000)

    class Config:
        from_attributes = True  # For ORM compatibility
```

### Response Transformation
```python
def transform_response(row: dict) -> dict:
    result = dict(row)
    # snake_case → camelCase for frontend
    if 'started_at' in result:
        result['startedAt'] = result['started_at'].isoformat() if result['started_at'] else None
    return result
```

### Async Job Pattern
```python
async def scheduled_job():
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            # Do work
            pass
    except Exception as e:
        logger.error(f"Job failed: {e}")
    finally:
        # Cleanup if needed
        pass
```

## TypeScript (Frontend)

### TanStack Query
```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['resource', params],
  queryFn: () => fetchResource(params),
  staleTime: 60_000,
  refetchInterval: refreshInterval,
});
```

### API Client
```typescript
export async function fetchResource(params: Params): Promise<Resource[]> {
  try {
    const response = await api.get<Resource[]>('/endpoint', { params });
    return response.data ?? [];
  } catch (error) {
    console.error('API error:', error);
    return [];
  }
}
```

### Component Pattern
```typescript
interface Props {
  data: Item[];
  onAction?: (item: Item) => void;
}

export function MyComponent({ data, onAction }: Props) {
  if (!data.length) return <EmptyState />;
  return (
    <div className="grid gap-4">
      {data.map(item => (
        <Card key={item.id} onClick={() => onAction?.(item)}>
          {item.name}
        </Card>
      ))}
    </div>
  );
}
```

### Loading/Error Pattern
```typescript
if (isLoading) return <LoadingScreen />;
if (error) return <ErrorState onRetry={refetch} />;
return <SuccessContent data={data} />;
```

## SQL (Database)

### Index Creation
```sql
-- Standard index
CREATE INDEX CONCURRENTLY idx_table_column ON table(column);

-- Partial index
CREATE INDEX CONCURRENTLY idx_table_filtered
    ON table(column) WHERE condition = TRUE;

-- Composite index
CREATE INDEX CONCURRENTLY idx_table_multi
    ON table(col1, col2 DESC);

-- GIN for full-text
CREATE INDEX CONCURRENTLY idx_table_fts
    ON table USING GIN(tsvector_column);
```

### Migration Template
```sql
-- Migration: NNN_description.sql
BEGIN;

-- Up
ALTER TABLE table ADD COLUMN new_col TYPE;
CREATE INDEX CONCURRENTLY idx_name ON table(new_col);

COMMIT;

-- Down (comments)
-- DROP INDEX idx_name;
-- ALTER TABLE table DROP COLUMN new_col;
```

## Naming Conventions

| Layer | Convention | Example |
|-------|------------|---------|
| Database | snake_case | `call_uid`, `started_at` |
| Python | snake_case | `call_uid`, `started_at` |
| TypeScript | camelCase | `callUid`, `startedAt` |
| API Response | camelCase | `{"callUid": "...", "startedAt": "..."}` |
| CSS/Tailwind | kebab-case | `text-gray-500`, `flex-col` |

## File Organization

```
app_api/
├── routers/     # One file per resource
├── models/      # Pydantic schemas per resource
├── database.py  # Connection pool
└── config.py    # Settings

frontend/src/
├── pages/       # One file per route
├── components/  # Reusable UI
├── api/         # API clients per resource
├── types/       # TypeScript interfaces
└── lib/         # Utilities
```
