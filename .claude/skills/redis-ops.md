---
name: "Redis Operations"
description: "Manage Redis caching and Celery message broker"
---

## Context

Use this skill when working with Redis for caching and Celery message brokering. This includes debugging queue issues, clearing stale cache, and monitoring worker connectivity.

## Scope

Files this agent works with:
- Redis CLI via: `docker compose exec redis redis-cli`
- `app_api/database.py` - Cache operations
- `app_transcribe/worker.py` - Celery broker configuration
- Flower UI at `http://localhost:5555`

## Instructions

When invoked, follow these steps:

1. **Understand the task**
   - Identify if this is a cache or queue issue
   - Check Redis connectivity: `docker compose exec redis redis-cli PING`
   - Review queue depth or cache key patterns

2. **Diagnose the issue**
   - For queues: check `LLEN celery` for backlog
   - For cache: check key existence and TTL
   - For workers: check Flower UI for worker status

3. **Implement fix**
   - Queue issues: check worker logs, restart if needed
   - Cache issues: clear stale keys or adjust TTL
   - Connection issues: check Redis container health

4. **Verify**
   - Confirm queue is draining (for queue issues)
   - Verify cache hits/misses (for cache issues)
   - Check worker connectivity in Flower

## Behaviors

- Monitor Celery queue depth: `LLEN celery`
- Clear stale cache keys when needed
- Check worker connectivity via Flower UI
- Debug task routing issues
- Monitor memory usage: `INFO memory`

## Constraints

- Never run `FLUSHALL` or `FLUSHDB` in production
- Never modify Celery internal keys directly (celery-task-meta-*)
- Keep cache TTLs reasonable (< 1hr for mutable data)
- Never delete queue data without confirmation
- Never expose Redis credentials

## Safety Checks

Before completing:
- [ ] Redis responds to PING command
- [ ] Memory usage is within acceptable limits
- [ ] Queue backlog is not growing indefinitely
- [ ] Workers are connected and processing
- [ ] No stale task locks blocking processing

## Common Commands

```bash
# Enter Redis CLI
docker compose exec redis redis-cli

# Check queue depth
LLEN celery

# Check Redis info
INFO memory
INFO clients

# List all keys (be careful in production)
KEYS *

# Check specific key TTL
TTL cache:dashboard:stats

# Delete specific key
DEL cache:dashboard:stats

# Monitor commands in real-time
MONITOR
```

## Celery Queue Debugging

```bash
# Check worker status in Flower
open http://localhost:5555

# View active tasks
docker compose exec redis redis-cli LRANGE celery 0 10

# Check for stuck tasks
docker compose logs --tail=100 scanner-transcription | grep -i error

# Restart worker
docker compose restart scanner-transcription
```

## Cache Key Patterns

```
cache:dashboard:stats       - Dashboard statistics (TTL: 30s)
cache:geography:*           - Geographic data (TTL: 1hr)
cache:playlists:*           - Playlist data (TTL: 5min)
celery                      - Task queue (list)
celery-task-meta-*          - Task results (managed by Celery)
```
