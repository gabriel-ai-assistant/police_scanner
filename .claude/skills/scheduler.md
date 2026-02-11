---
name: "Scheduler"
description: "Implement and debug APScheduler background jobs"
---

## Context

Use this skill when working with APScheduler background jobs that run continuously. This includes the Broadcastify API polling, audio download, and transcription dispatching jobs.

## Scope

Files this agent works with:
- `app_scheduler/scheduler.py` - Main scheduler configuration
- `app_scheduler/get_calls.py` - Broadcastify API ingestion
- `app_scheduler/audio_worker.py` - Audio download and processing
- `app_scheduler/transcription_dispatcher.py` - Celery task dispatch
- `app_scheduler/get_cache_common_data.py` - Geographic data refresh
- `app_scheduler/db_pool.py` - Database connection management

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify which scheduled job needs work
   - Check job frequency and overlap settings
   - Review scheduler logs for errors

2. **Analyze job flow**
   - Trace the job's database interactions
   - Check for proper connection pool usage
   - Understand error isolation (job failures shouldn't crash scheduler)

3. **Implement changes**
   - Use `async def` with `AsyncIOScheduler`
   - Use `get_connection()` / `release_connection()` from db_pool.py
   - Wrap all code in try/except to prevent scheduler crash

4. **Verify**
   - Check job doesn't overlap with itself
   - Verify connections are properly released
   - Test error handling in isolation

## Behaviors

- Use `async def` with `AsyncIOScheduler`
- Use `get_connection()` / `release_connection()` from db_pool.py
- Wrap job execution in try/except to prevent scheduler crash
- Use `max_instances=1, coalesce=True` for job configuration
- Log failures but continue processing other items
- Use batch processing within configured limits

## Constraints

- Never block the event loop with sync I/O
- Never let exceptions propagate to scheduler (always catch and log)
- Never exceed `AUDIO_WORKER_BATCH_SIZE` for batch operations
- Never hold database connections across await boundaries
- Never use blocking HTTP calls (use aiohttp)

## Safety Checks

Before completing:
- [ ] Job wrapped in try/except (no unhandled exceptions)
- [ ] Database connections released in finally block
- [ ] `max_instances=1` prevents job overlap
- [ ] Batch sizes respect configuration limits
- [ ] External API calls have timeouts
- [ ] JWT token validity checked before API calls

## Job Configuration Reference

```python
# Standard job configuration
scheduler.add_job(
    job_function,
    'interval',
    seconds=10,
    id='job_name',
    max_instances=1,
    coalesce=True,  # Skip missed runs
    misfire_grace_time=30
)
```

## Common Debugging

```bash
# View scheduler logs
docker compose logs --tail=200 app-scheduler

# Check recent ingestion
SELECT COUNT(*) FROM bcfy_calls_raw
WHERE started_at > NOW() - INTERVAL '5 minutes';

# Check poll log
SELECT * FROM bcfy_playlist_poll_log
ORDER BY poll_started_at DESC LIMIT 10;
```
