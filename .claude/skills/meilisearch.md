---
name: "MeiliSearch"
description: "Manage full-text search indexing and queries"
---

## Context

Use this skill when working with MeiliSearch full-text search functionality. This includes debugging search issues, configuring indexes, and optimizing search relevance.

## Scope

Files this agent works with:
- `app_transcribe/worker.py` - `index_to_meilisearch()` function
- `app_api/routers/transcripts.py` - Search endpoint
- MeiliSearch admin API at `http://localhost:7700`

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify if this is an indexing or search issue
   - Check MeiliSearch health: `curl http://localhost:7700/health`
   - Review index configuration and document count

2. **Analyze the index**
   - Check document count vs database count
   - Review searchable/filterable attributes
   - Examine ranking rules if relevance is an issue

3. **Implement changes**
   - For indexing: modify `index_to_meilisearch()` in worker.py
   - For search: modify search endpoint in transcripts.py
   - For config: use MeiliSearch settings API

4. **Verify**
   - Test search returns expected results
   - Verify document count matches expectations
   - Check index health after changes

## Behaviors

- Index documents with consistent schema: `{id, call_uid, text, feed_id, timestamp}`
- Use filterable attributes for faceted search
- Configure ranking rules for relevance
- Handle index creation/deletion safely
- Batch index operations (max 1000 docs per request)

## Constraints

- Never delete indexes without explicit user confirmation
- Always check index health before operations
- Never expose `MEILI_MASTER_KEY` in responses
- Never skip error handling for indexing operations
- Never modify primary key after index creation

## Safety Checks

Before completing:
- [ ] `MEILI_MASTER_KEY` environment variable is set
- [ ] Document count matches database transcript count
- [ ] Searchable attributes configured correctly
- [ ] Filterable attributes set for needed facets
- [ ] Index health check passes

## Common Commands

```bash
# Check MeiliSearch health
curl http://localhost:7700/health

# Get index stats
curl -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  http://localhost:7700/indexes/transcripts/stats

# Search test
curl -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -X POST http://localhost:7700/indexes/transcripts/search \
  -d '{"q": "test query", "limit": 10}'

# Get index settings
curl -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  http://localhost:7700/indexes/transcripts/settings
```

## Index Schema Reference

```python
document = {
    "id": transcript_id,      # Primary key (int)
    "call_uid": call_uid,     # Foreign key to bcfy_calls_raw
    "text": transcript_text,  # Searchable content
    "feed_id": feed_id,       # Filterable
    "timestamp": iso_string,  # Sortable
    "confidence": float       # Whisper confidence score
}
```
