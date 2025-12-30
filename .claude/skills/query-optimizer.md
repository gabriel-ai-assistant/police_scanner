---
name: "Query Optimizer"
description: "Analyze and optimize PostgreSQL queries for performance"
---

## Context

Use this skill when analyzing and optimizing PostgreSQL query performance. This includes identifying slow queries, recommending indexes, and rewriting queries for efficiency.

## Scope

Files this agent works with:
- `app_api/routers/*.py` - SQL queries in API endpoints
- `app_scheduler/*.py` - SQL queries in scheduler jobs
- `app_transcribe/worker.py` - SQL queries in transcription worker
- `db/monitoring_queries.sql` - Performance monitoring queries
- `db/migrations/*.sql` - Index definitions

## Instructions

When invoked, follow these steps:

1. **Identify the query**
   - Locate the slow or problematic query
   - Understand its purpose and usage frequency
   - Check current execution time

2. **Analyze the query**
   - Use EXPLAIN ANALYZE to understand execution plan
   - Identify missing indexes
   - Check for N+1 patterns

3. **Optimize**
   - Add indexes via migration file
   - Rewrite query if needed
   - Reduce selected columns

4. **Verify**
   - Re-run EXPLAIN ANALYZE
   - Confirm improved execution time
   - Check write performance not degraded

## Behaviors

- Identify N+1 query patterns
- Recommend missing indexes based on WHERE/JOIN clauses
- Suggest query rewrites for better performance
- Use EXPLAIN ANALYZE for query plan analysis
- Check for unnecessary SELECT columns
- Consider index impact on write performance

## Constraints

- Never add indexes without migration file
- Consider write performance impact of indexes
- Test query changes with representative data volumes
- Never modify queries to return different results
- Never add redundant indexes

## Safety Checks

Before completing:
- [ ] EXPLAIN ANALYZE run before and after optimization
- [ ] Index doesn't already exist
- [ ] Migration file created for new indexes
- [ ] Query results unchanged after optimization
- [ ] Write performance impact considered

## EXPLAIN ANALYZE Usage

```sql
-- Basic explain
EXPLAIN ANALYZE
SELECT * FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '24 hours';

-- With verbose output
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM transcripts
WHERE call_uid = 'abc123';
```

## Common Optimization Patterns

### Missing Index
```sql
-- Slow query
SELECT * FROM bcfy_calls_raw WHERE feed_id = 123;

-- Check for index
SELECT indexname FROM pg_indexes WHERE tablename = 'bcfy_calls_raw';

-- Add index via migration
CREATE INDEX CONCURRENTLY idx_calls_feed_id ON bcfy_calls_raw(feed_id);
```

### N+1 Query Pattern
```python
# BAD: N+1 queries
for call in calls:
    transcript = await get_transcript(call['uid'])  # N additional queries

# GOOD: Single join query
query = """
SELECT c.*, t.text
FROM bcfy_calls_raw c
LEFT JOIN transcripts t ON c.call_uid = t.call_uid
WHERE c.started_at > $1
"""
```

### Over-fetching Columns
```python
# BAD: Select all columns
SELECT * FROM bcfy_calls_raw WHERE ...

# GOOD: Select only needed columns
SELECT call_uid, started_at, duration_ms FROM bcfy_calls_raw WHERE ...
```

### Inefficient Pagination
```python
# BAD: OFFSET for deep pagination
SELECT * FROM calls ORDER BY id LIMIT 20 OFFSET 10000;

# GOOD: Keyset pagination
SELECT * FROM calls WHERE id > $1 ORDER BY id LIMIT 20;
```

## Index Recommendations

| Query Pattern | Recommended Index |
|--------------|-------------------|
| `WHERE col = value` | B-tree on col |
| `WHERE col > value` | B-tree on col |
| `WHERE col1 = x AND col2 = y` | Composite (col1, col2) |
| `WHERE col LIKE 'prefix%'` | B-tree on col |
| `WHERE col @@ to_tsquery()` | GIN on tsvector |
| `ORDER BY col` | B-tree on col |
| `WHERE bool_col = false` | Partial index |

## Performance Monitoring Query

```sql
-- Slow queries in the last hour
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- > 100ms average
ORDER BY total_exec_time DESC
LIMIT 20;

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

## Index Creation Pattern

```sql
-- Migration: 012_add_performance_indexes.sql

BEGIN;

-- Use CONCURRENTLY to avoid locking table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_feed_started
ON bcfy_calls_raw(feed_id, started_at DESC);

-- Partial index for pending items
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calls_pending
ON bcfy_calls_raw(started_at DESC)
WHERE processed = false;

COMMIT;
```
