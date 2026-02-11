---
name: "Celery Worker"
description: "Implement and debug Celery transcription tasks"
---

## Context

Use this skill when working with Celery background tasks for audio transcription. This includes debugging task failures, adding new processing steps, and optimizing transcription workflow.

## Scope

Files this agent works with:
- `app_transcribe/worker.py` - Main Celery task definitions
- `app_transcribe/transcribe_audio.py` - Whisper transcription logic
- `app_transcribe/parse_and_alert.py` - Post-processing and alerting
- `app_transcribe/requirements.txt` - Worker dependencies

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify which Celery task needs work
   - Check task state machine in `processing_state` table
   - Review recent task logs for error patterns

2. **Analyze the pipeline**
   - Trace data flow: S3 download → Whisper → DB insert → MeiliSearch
   - Check for idempotency via `check_transcript_exists()`
   - Understand retry behavior and failure handling

3. **Implement changes**
   - Use `psycopg2` with `RealDictCursor` (sync, not async)
   - Update `processing_state` table on state transitions
   - Handle MeiliSearch failures gracefully (log, don't fail)

4. **Verify**
   - Check task can be retried safely (idempotent)
   - Verify state machine updates correctly
   - Test error handling paths

## Behaviors

- Use `psycopg2` with `RealDictCursor` (sync, not async)
- Update `processing_state` table on task state changes
- Log with emoji prefixes: ✅ success, ❌ error, 🕒 progress
- Handle MeiliSearch indexing failures gracefully (log, don't fail task)
- Use `task_acks_late=True` pattern for reliability
- Increment `retry_count` on each failure

## Constraints

- Never use `asyncpg` or `async def` (Celery is synchronous)
- Always update `retry_count` on failures
- Never store credentials in task arguments
- Never fail entire task on MeiliSearch errors (optional indexing)
- Never skip idempotency checks

## Safety Checks

Before completing:
- [ ] Task is idempotent (safe to retry)
- [ ] `processing_state` updated on all code paths
- [ ] Audio file existence verified before processing
- [ ] Whisper output validated before database insert
- [ ] No credentials in task arguments or logs
- [ ] MeiliSearch failures logged but don't crash task

## Common Debugging

```python
# Check queue depth
docker compose exec redis redis-cli LLEN celery

# View worker logs
docker compose logs --tail=200 scanner-transcription

# Check processing state
SELECT call_uid, state, retry_count, error_message
FROM processing_state
WHERE state != 'indexed'
ORDER BY updated_at DESC LIMIT 20;
```
